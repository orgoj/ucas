"""
UCAS entry point: python -m ucas
"""

import sys
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

from . import settings
from . import mail
from .cli import parse_args
from .launcher import (
    build_command, run_command, LaunchError, 
    prepare_context, HookRunner, get_context_export_str,
    validate_runner, stop_runner, expand_variables,
    get_runner_preview
)
from .resolver import (
    find_entity, load_config, get_layer_config_paths, 
    get_search_paths, load_config_file, get_acli_config,
    get_run_config
)
from .merger import merge_configs, collect_skills, _merge_dicts


def resolve_entities(agent_name: str, mods: List[str]) -> Tuple[Path, List[Path], List[Path], Dict[str, Any]]:
    """Resolve agent and mods with dynamic search path expansion."""
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, load_config_file(cfg), settings.DEBUG, f"Base:{layer_name}")

    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    
    search_paths = get_search_paths(extra_paths, base_config.get('strict', False))
    
    # 1. Resolve Agent
    agent_path = find_entity(agent_name, search_paths)
    if not agent_path:
        raise LaunchError(f"Agent '{agent_name}' not found")

    # Dynamic search path update from agent
    _update_search_paths(search_paths, agent_path)

    # 2. Resolve Mods sequentially, updating search paths after each
    mod_paths = []
    for mod_item in mods:
        mod_name = mod_item['name'] if isinstance(mod_item, dict) else mod_item
        m_path = find_entity(mod_name, search_paths)
        if not m_path:
            raise LaunchError(f"Mod '{mod_name}' not found")
        mod_paths.append(m_path)
        
        _update_search_paths(search_paths, m_path)

    return agent_path, mod_paths, search_paths, base_config


def _update_search_paths(search_paths: List[Path], entity_path: Path):
    """Read entity config and prepend any mod_path to search_paths."""
    cfg = load_config(entity_path)
    new_paths = cfg.get('mod_path', [])
    if isinstance(new_paths, str):
        new_paths = [new_paths]
    
    for p in reversed(new_paths): # reversed so they keep order when prepending
        p_path = Path(p)
        if not p_path.is_absolute():
            p_path = (entity_path / p).resolve()
        
        if p_path.exists() and p_path.is_dir():
            if p_path not in search_paths:
                if settings.DEBUG: print(f"[RESOLVER] Adding dynamic search path: {p_path}", file=sys.stderr)
                search_paths.insert(0, p_path)


def _prepare_and_run_member(
    member_name: str,
    agent_name: str,
    mods: List[str],
    prefix: str = "",
    team_name: str = None,
    team_index: int = 0,
    team_size: int = 1,
    prompt: str = None,
    model: str = None,
    provider: str = None
) -> None:
    """Prepare and run a single agent member."""
    # 1. First resolution to get search paths and base_config
    agent_path, explicit_mod_paths, search_paths, base_config = resolve_entities(agent_name, mods)
    
    # 2. Identify default mods from base_config
    raw_default_mods = base_config.get('mods', [])
    default_mod_names = raw_default_mods if isinstance(raw_default_mods, list) else [raw_default_mods]
    
    # 3. Resolve default mod paths
    default_mod_paths = []
    for m_name in default_mod_names:
        p = find_entity(m_name, search_paths)
        if p: default_mod_paths.append(p)

    # 4. Perform sandwich merge with correct priorities:
    # System -> Default Mods -> Agent -> Explicit Mods -> Overrides
    merged_config = merge_configs(agent_path, default_mod_paths, explicit_mod_paths)
    
    # 5. Add default ACLI if missing (look up again if needed)
    acli_def = get_acli_config(merged_config)
    if not acli_def.get('executable'):
        def_acli = merged_config.get('default_acli') or base_config.get('default_acli')
        if def_acli:
            acli_path = find_entity(def_acli, search_paths)
            if acli_path:
                explicit_mod_paths.append(acli_path)
                merged_config = merge_configs(agent_path, default_mod_paths, explicit_mod_paths)

    # 6. Add default RUN if missing
    run_def = get_run_config(merged_config)
    if not run_def:
        def_run = merged_config.get('default_run') or base_config.get('default_run') or 'run-tmux'
        run_path = find_entity(def_run, search_paths)
        if run_path:
            explicit_mod_paths.append(run_path)
            merged_config = merge_configs(agent_path, default_mod_paths, explicit_mod_paths)

    if model: merged_config['requested_model'] = model
    if provider: merged_config['requested_provider'] = provider

    context = prepare_context(member_name, agent_path, team_name, team_index, team_size)
    
    env_config = merged_config.get('env', {})
    for k, v in env_config.items():
        context[k] = expand_variables(v, context) if isinstance(v, str) else str(v)

    all_mod_paths = default_mod_paths + explicit_mod_paths
    skills_dirs = collect_skills(agent_path, all_mod_paths)
    
    main_cmd = build_command(
        agent_path,
        all_mod_paths,
        merged_config,
        skills_dirs,
        context,
        prompt
    )

    acli_def = get_acli_config(merged_config)
    context['UCAS_ACLI_EXE'] = acli_def.get('executable', '')

    all_cmds = [get_context_export_str(context)]
    hooks = merged_config.get('hooks', {})
    
    prerun = hooks.get('prerun', [])
    if isinstance(prerun, str): prerun = [prerun]
    all_cmds.extend(prerun)
    all_cmds.append(main_cmd)
    
    postrun = hooks.get('postrun', [])
    if isinstance(postrun, str): postrun = [postrun]
    all_cmds.extend(postrun)
    
    final_command = ' && '.join(all_cmds)
    run_def = get_run_config(merged_config)
    if not run_def:
        raise LaunchError("No 'run' block found in final configuration")

    if settings.DRY_RUN:
        if settings.DEBUG: print(f"[DEBUG] Dry run enabled, getting preview...", file=sys.stderr)
        runner_preview = get_runner_preview(run_def, final_command, member_name, context)
        print(f"{prefix}[DRY-RUN] {runner_preview}")
    else:
        if settings.DEBUG: print(f"[DEBUG] Real run, executing...", file=sys.stderr)
        HookRunner(context).run(hooks, 'install')
        run_command(run_def, final_command, member_name, context)


def main():
    """Main entry point."""
    args = parse_args()
    try:
        if args.command == 'run':
            run_agent(args)
        elif args.command == 'run-team':
            run_team(args)
        elif args.command == 'stop-team':
            stop_team(args)
        elif args.command == 'ls-mods':
            ls_mods(args)
        elif args.command == 'mail':
            handle_mail(args)
    except LaunchError as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if settings.DEBUG: raise
        sys.exit(1)


def handle_mail(args):
    """Handle mail commands."""
    if not args.mail_command:
        # If no subcommand, show help (via parser.print_help() if possible or just exit)
        # But we don't have parser here. Let's assume list inbox by default?
        # No, subcommand is required by argparse generally unless we make it optional.
        # But for now, let's assume it was parsed.
        print("Use: ucas mail {send,list,read,check} ...")
        sys.exit(1)

    if args.mail_command == 'send':
        if args.body:
            body = args.body
        else:
            # Read body from stdin
            if sys.stdin.isatty():
                print("Enter message body (Ctrl+D to finish):")
            body = sys.stdin.read()
            
        mail.send_mail(args.recipient, args.subject, body, reply_id=args.reply)
        
    elif args.mail_command == 'list':
        # Default to JSON unless --table is specified
        json_output = not args.table
        mail.list_mail(show_all=args.all, show_sent=args.sent, json_output=json_output)
        
    elif args.mail_command == 'read':
        # Default to JSON unless --table is specified
        json_output = not args.table
        mail.read_mail(args.id, json_output=json_output)
        
    elif args.mail_command == 'check':
        mail.check_mail(idle=args.idle)
        
    elif args.mail_command == 'addressbook':
        # Default to JSON
        json_output = not args.table
        mail.print_address_book(json_output=json_output)
        
    elif args.mail_command == 'gui':
        try:
            from . import mail_gui
            mail_gui.run_gui(args.agent_name)
        except ImportError:
            print("Error: Tkinter not found. Please install python3-tk.", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error launching GUI: {e}", file=sys.stderr)
            sys.exit(1)


def run_agent(args):
    """Run a single agent."""
    _prepare_and_run_member(
        member_name=args.agent,
        agent_name=args.agent,
        mods=args.mods or []
    )


def run_team(args):
    """Run a team of agents."""
    # 1. Resolve configuration layers
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, load_config_file(cfg), settings.DEBUG, f"Base:{layer_name}")
            
    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    search_paths = get_search_paths(extra_paths, base_config.get('strict', False))

    # 2. Resolve Mods (including Team Mod if specified)
    team_mod_paths = []
    
    # If args.team is specified, treat it as a mod that might contain team definition
    if args.team:
        m_path = find_entity(args.team, search_paths)
        if not m_path:
            raise LaunchError(f"Team Mod '{args.team}' not found")
        team_mod_paths.append(m_path)
        _update_search_paths(search_paths, m_path)

    # Add CLI mods
    for mod_item in (args.mods or []):
        m_path = find_entity(mod_item, search_paths)
        if not m_path:
            raise LaunchError(f"Mod '{mod_item}' not found")
        team_mod_paths.append(m_path)
        _update_search_paths(search_paths, m_path)

    # 3. Perform Merge: System -> User -> Project -> [Team Mod] -> [CLI Mods]
    # We pass a dummy agent_path because merge_configs expects one, but for team resolution it's not strictly needed
    # unless __DIR__ is used relative to agent. Let's use project root as dummy if needed.
    # Actually merge_configs uses agent_path as base for __DIR__ resolution for agent layer.
    # Here we don't have an agent layer yet.
    
    # Let's manually construct the merge chain as we did in _prepare_and_run_member
    # But here we want the final config to find the 'team' block.
    
    # merge_configs(agent_path, default_mods, explicit_mods)
    # We can pass Project Root as agent_path to satisfy the signature?
    # Or just use the first found mod path?
    # Let's use Project Root.
    project_root = Path.cwd()
    
    # Resolve default mods from base_config
    raw_default_mods = base_config.get('mods', [])
    default_mod_names = raw_default_mods if isinstance(raw_default_mods, list) else [raw_default_mods]
    default_mod_paths = []
    for m_name in default_mod_names:
        p = find_entity(m_name, search_paths)
        if p: default_mod_paths.append(p)

    merged_config = merge_configs(project_root, default_mod_paths, team_mod_paths)
    
    # 4. Extract Team Definition
    team_def = merged_config.get('team')
    if not team_def:
        # Fallback: check if merged_config ITSELF is a team definition (has agents/members)
        if merged_config.get('agents') or merged_config.get('members'):
            team_def = merged_config
        else:
            raise LaunchError("No 'team' block or agents definition found in final configuration")

    # 5. Run Members
    team_name = team_def.get('name') or args.team or project_root.name
    members = team_def.get('agents') or team_def.get('members', {})
    team_wide_mods = team_def.get('mods', [])
    member_names = list(members.keys())
    
    print(f"Starting team '{team_name}' with {len(member_names)} members...")
    
    for idx, name in enumerate(member_names):
        spec = members[name]
        # Parse member spec
        if isinstance(spec, list):
            base, mmods, prompt, model, provider = spec[0], spec[1:], None, None, None
        elif isinstance(spec, str):
            base, mmods, prompt, model, provider = spec, [], None, None, None
        elif isinstance(spec, dict):
            # Dict spec
            agent_list = spec.get('mods') or spec.get('agent', [])
            if isinstance(agent_list, list):
                base, mmods = agent_list[0], agent_list[1:]
            else:
                base, mmods = agent_list, spec.get('mods', [])
            prompt, model, provider = spec.get('prompt'), spec.get('model'), spec.get('provider')
        
        # Combine mods: [Team Mod] + [Team Wide] + [CLI Mods] + [Member Specific]
        effective_mods = []
        if args.team:
            effective_mods.append(args.team)
        effective_mods.extend(team_wide_mods)
        effective_mods.extend(args.mods or [])
        effective_mods.extend(mmods)
        
        _prepare_and_run_member(
            member_name=name, agent_name=base, mods=effective_mods,
            prefix=f"[{name}] ",
            team_name=team_name, team_index=idx, team_size=len(member_names),
            prompt=prompt or team_def.get('prompt'), model=model, provider=provider
        )
        
        if team_def.get('sleep_seconds', 0) > 0 and idx < len(member_names)-1 and not settings.DRY_RUN:
            time.sleep(team_def['sleep_seconds'])


def stop_team(args):
    """Stop a team."""
    # Similar logic to run_team to find the context
    # But simplified: we just need to resolve mods to find the runner to call stop_runner
    
    # 1. Resolve configuration layers
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, load_config_file(cfg), settings.DEBUG, f"Base:{layer_name}")
            
    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    search_paths = get_search_paths(extra_paths, base_config.get('strict', False))

    # 2. Resolve Mods
    team_mod_paths = []
    if args.team:
        m_path = find_entity(args.team, search_paths)
        if not m_path: raise LaunchError(f"Team Mod '{args.team}' not found")
        team_mod_paths.append(m_path)

    for mod_item in (args.mods or []):
        m_path = find_entity(mod_item, search_paths)
        if not m_path: raise LaunchError(f"Mod '{mod_item}' not found")
        team_mod_paths.append(m_path)
    
    project_root = Path.cwd()
    merged_config = merge_configs(project_root, [], team_mod_paths) # Defaults not needed for stop?
    
    # 3. Find runner
    run_def = get_run_config(merged_config)
    
    # If no run def found, try to add default runner
    if not run_def:
        def_run = merged_config.get('default_run') or base_config.get('default_run') or 'run-tmux'
        run_path = find_entity(def_run, search_paths)
        if run_path:
             merged_config = merge_configs(project_root, [], team_mod_paths + [run_path])
             run_def = get_run_config(merged_config)

    if not run_def: raise LaunchError("No 'run' block found to stop")
    
    # Try to find team name
    team_name = merged_config.get('team', {}).get('name') or args.team or project_root.name
    
    stop_runner(run_def, prepare_context("stop", project_root, team_name))


def ls_mods(args):
    """List available mods."""
    ucas_home = os.environ.get('UCAS_HOME') or str(Path(__file__).parent.parent)
    layers = [
        ('project', Path.cwd() / '.ucas' / 'mods'),
        ('user', Path.home() / '.ucas' / 'mods'),
        ('system', Path(ucas_home) / 'mods')
    ]
    for label, path in layers:
        if not path.exists(): continue
        mods = []
        for item in sorted(path.iterdir()):
            if item.is_dir():
                try:
                    cfg = load_config(item)
                    has_skill = (item / 'skills').is_dir()
                    has_prompt = (item / 'PROMPT.md').is_file()
                    has_acli = any(k.startswith('acli') for k in cfg)
                    has_run = any(k.startswith('run') for k in cfg)
                    
                    flags = ""
                    flags += "S" if has_skill else "."
                    flags += "A" if has_acli else "."
                    flags += "R" if has_run else "."
                    flags += "P" if has_prompt else "."
                    
                    mods.append((item.name, cfg.get('description', ''), flags))
                except: mods.append((item.name, '', "...."))
        if not mods: continue
        if settings.QUIET:
            print(f"# {label}")
            for n, _, f in mods:
                f_str = f" [{f}]" if f != "...." else ""
                print(f"{n}{f_str}")
        else:
            print(f"--- {label.upper()} MODS ({path}) ---")
            for n, d, f in mods:
                flag_tag = f"[{f}]"
                print(f"{flag_tag} {n:20} - {d}" if d else f"{flag_tag} {n}")
        print()


if __name__ == '__main__':
    main()
