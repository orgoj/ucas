"""
UCAS entry point: python -m ucas
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .cli import parse_args
from .launcher import (
    build_command, run_command, LaunchError, 
    prepare_context, HookRunner, get_context_export_str,
    validate_runner, stop_runner, expand_variables,
    get_runner_preview
)
from .resolver import (
    find_entity, load_config, get_layer_config_paths, 
    get_search_paths
)
from .merger import merge_configs, collect_skills, _merge_dicts
from .yaml_parser import parse_yaml


def resolve_entities(agent_name: str, mods: List[str], debug: bool = False) -> Tuple[Path, List[Path]]:
    """Resolve agent and mods with dynamic search path expansion."""
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, parse_yaml(cfg.read_text()), debug, f"Base:{layer_name}")

    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    search_paths = get_search_paths(extra_paths, base_config.get('strict', False))
    
    agent_path = find_entity(agent_name, search_paths)
    if not agent_path:
        raise LaunchError(f"Agent '{agent_name}' not found")

    mod_paths = []
    for mod_item in mods:
        mod_name = mod_item['name'] if isinstance(mod_item, dict) else mod_item
        m_path = find_entity(mod_name, search_paths)
        if not m_path:
            raise LaunchError(f"Mod '{mod_name}' not found")
        mod_paths.append(m_path)

    return agent_path, mod_paths


def _prepare_and_run_member(
    member_name: str,
    agent_name: str,
    mods: List[str],
    dry_run: bool,
    verbose: bool,
    debug: bool,
    prefix: str = "",
    team_name: str = None,
    team_index: int = 0,
    team_size: int = 1,
    prompt: str = None,
    model: str = None,
    provider: str = None
) -> None:
    """Prepare and run a single agent member."""
    agent_path, mod_paths = resolve_entities(agent_name, mods, debug)
    merged_config = merge_configs(agent_path, mod_paths, verbose, debug)
    
    if model: merged_config['requested_model'] = model
    if provider: merged_config['requested_provider'] = provider

    context = prepare_context(member_name, agent_path, team_name, team_index, team_size)
    
    env_config = merged_config.get('env', {})
    for k, v in env_config.items():
        context[k] = expand_variables(v, context) if isinstance(v, str) else str(v)

    skills_dirs = collect_skills(agent_path, mod_paths)
    
    main_cmd = build_command(
        agent_path,
        mod_paths,
        merged_config,
        skills_dirs,
        context,
        prompt,
        debug
    )

    acli_def = merged_config.get('acli', {})
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
    run_def = merged_config.get('run', {})
    if not run_def:
        raise LaunchError("No 'run' block found in final configuration")

    if dry_run:
        runner_preview = get_runner_preview(run_def, final_command, member_name, context)
        print(f"{prefix}[DRY-RUN] {runner_preview}")
    else:
        HookRunner(context, debug).run(hooks, 'install')
        run_command(run_def, final_command, member_name, context, debug)


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
    except LaunchError as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.debug: raise
        sys.exit(1)


def run_agent(args):
    """Run a single agent."""
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, parse_yaml(cfg.read_text()), args.debug, f"Base:{layer_name}")
    
    raw_default_mods = base_config.get('mods', [])
    all_mods = (raw_default_mods if isinstance(raw_default_mods, list) else [raw_default_mods]) + (args.mods or [])
    
    _prepare_and_run_member(
        member_name=args.agent,
        agent_name=args.agent,
        mods=all_mods,
        dry_run=args.dry_run,
        verbose=args.verbose,
        debug=args.debug
    )


def run_team(args):
    """Run a team of agents."""
    entity_path = find_entity(args.team)
    if not entity_path: raise LaunchError(f"Team '{args.team}' not found")
    
    merged_config = merge_configs(entity_path, [], args.debug)
    team_def = merged_config.get('team') or merged_config
    
    import time
    members = team_def.get('agents') or team_def.get('members', {})
    team_wide_mods = team_def.get('mods', [])
    member_names = list(members.keys())
    
    for idx, name in enumerate(member_names):
        spec = members[name]
        if isinstance(spec, list):
            base, mmods, prompt, model, provider = spec[0], spec[1:], None, None, None
        elif isinstance(spec, str):
            base, mmods, prompt, model, provider = spec, [], None, None, None
        elif isinstance(spec, dict):
            agent_list = spec.get('mods') or spec.get('agent', [])
            if isinstance(agent_list, list):
                base, mmods = agent_list[0], agent_list[1:]
            else:
                base, mmods = agent_list, spec.get('mods', [])
            prompt, model, provider = spec.get('prompt'), spec.get('model'), spec.get('provider')
        
        _prepare_and_run_member(
            member_name=name, agent_name=base, mods=team_wide_mods + (args.mods or []) + mmods,
            dry_run=args.dry_run, verbose=args.verbose, debug=args.debug, prefix=f"[{name}] ",
            team_name=args.team, team_index=idx, team_size=len(member_names),
            prompt=prompt or team_def.get('prompt'), model=model, provider=provider
        )
        if team_def.get('sleep_seconds', 0) > 0 and idx < len(member_names)-1 and not args.dry_run:
            time.sleep(team_def['sleep_seconds'])


def stop_team(args):
    """Stop a team."""
    entity_path = find_entity(args.team)
    if not entity_path: raise LaunchError(f"Team '{args.team}' not found")
    
    mod_paths = [find_entity(m) for m in (args.mods or []) if find_entity(m)]
    merged_config = merge_configs(entity_path, mod_paths, args.debug)
    run_def = merged_config.get('run')
    if not run_def: raise LaunchError("No 'run' block found to stop")
    
    stop_runner(run_def, prepare_context("stop", entity_path, args.team), args.dry_run, args.debug)


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
                    mods.append((item.name, cfg.get('description', '')))
                except: mods.append((item.name, ''))
        if not mods: continue
        if args.quiet:
            print(f"# {label}")
            for n, _ in mods: print(n)
        else:
            print(f"--- {label.upper()} MODS ({path}) ---")
            for n, d in mods: print(f"{n:20} - {d}" if d else n)
        print()


if __name__ == '__main__':
    main()
