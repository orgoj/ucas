"""
UCAS entry point: python -m ucas
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .cli import parse_args
from .launcher import (
    select_acli, build_command, run_command, LaunchError, 
    prepare_context, HookRunner, get_context_export_str,
    select_run_mod, expand_run_template, validate_runner
)
from .resolver import (
    find_entity, is_acli, load_config, get_layer_config_paths, 
    get_search_paths, get_acli_config, is_run_mod, get_run_config
)
from .merger import merge_configs, collect_skills, _merge_dicts
from .yaml_parser import parse_yaml


def resolve_entities(agent_name: str, mods: List[str], debug: bool = False) -> Tuple[Path, List[Path]]:
    """
    Resolve agent and mods with dynamic search path expansion.
    """
    # 1. Base config merge to get mod_path/strict
    (sys_cfg, sys_ovr), (usr_cfg, usr_ovr), (prj_cfg, prj_ovr) = get_layer_config_paths()
    base_config = {}
    
    # Merge order: System -> User -> Project (Sandwich base)
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            config = parse_yaml(cfg.read_text())
            base_config = _merge_dicts(base_config, config, debug, f"Base:{layer_name}")

    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    strict = base_config.get('strict', False)
    
    search_paths = get_search_paths(extra_paths, strict)
    
    if debug:
        print(f"[DEBUG] Initial search paths: {[str(p) for p in search_paths]}", file=sys.stderr)

    # 2. Resolve Agent
    agent_path = find_entity(agent_name, search_paths)
    if not agent_path:
        raise LaunchError(f"Agent '{agent_name}' not found")

    if debug:
        print(f"[DEBUG] Found agent: {agent_path}", file=sys.stderr)

    # Expand search paths from Agent
    agent_config = load_config(agent_path)
    if 'mod_path' in agent_config:
        new_paths = agent_config['mod_path']
        if isinstance(new_paths, str): new_paths = [new_paths]
        for p in new_paths:
            path = Path(p)
            if not path.is_absolute():
                path = agent_path / path
            if path.exists() and path.is_dir():
                if path not in search_paths:
                    search_paths.append(path)
                    if debug:
                        print(f"[DEBUG] Added search path from agent: {path}", file=sys.stderr)

    # 3. Resolve Mods
    mod_paths = []
    for mod_item in mods:
        # Extract name if it's a dict (e.g. {name: mod-name, description: ...})
        mod_name = mod_item['name'] if isinstance(mod_item, dict) else mod_item
        
        m_path = find_entity(mod_name, search_paths)
        if not m_path:
            raise LaunchError(f"Mod '{mod_name}' not found")
        mod_paths.append(m_path)
        if debug:
            print(f"[DEBUG] Found mod: {m_path}", file=sys.stderr)

        # Expand search paths from Mod
        m_config = load_config(m_path)
        if 'mod_path' in m_config:
            new_paths = m_config['mod_path']
            if isinstance(new_paths, str): new_paths = [new_paths]
            for p in new_paths:
                path = Path(p)
                if not path.is_absolute():
                    path = m_path / path
                if path.exists() and path.is_dir():
                    if path not in search_paths:
                        search_paths.append(path)
                        if debug:
                             print(f"[DEBUG] Added search path from mod '{mod_name}': {path}", file=sys.stderr)

    return agent_path, mod_paths


def _prepare_and_run_member(
    member_name: str,
    agent_name: str,
    mods: List[str],
    dry_run: bool,
    debug: bool,
    prefix: str = "",
    team_name: str = None
) -> None:
    """
    Prepare and run a single agent member.
    Shared logic between run_agent and run_team.
    """
    # Resolve entities with dynamic paths
    agent_path, mod_paths = resolve_entities(agent_name, mods, debug)

    # Merge configs
    merged_config = merge_configs(agent_path, mod_paths, debug)

    # Prepare context and hooks
    context = prepare_context(agent_name, agent_path, team_name)
    hook_runner = HookRunner(context, debug)
    hooks = merged_config.get('hooks', {})

    # Select ACLI
    acli_name = select_acli(merged_config, debug)

    # Load ACLI config
    acli_path = find_entity(acli_name)
    if not acli_path:
        raise LaunchError(f"ACLI '{acli_name}' not found")

    if not is_acli(acli_path):
        raise LaunchError(f"'{acli_name}' is not an ACLI (missing 'executable' field)")

    acli_config = load_config(acli_path)

    # Collect skills
    skills_dirs = collect_skills(agent_path, mod_paths)

    # Build main command
    main_cmd = build_command(
        agent_path,
        mod_paths,
        merged_config,
        acli_config,
        skills_dirs,
        context,
        debug
    )

    # Update context with dynamic info (support nested ACLI structure)
    acli_def = get_acli_config(acli_config)
    context['UCAS_ACLI_EXE'] = acli_def.get('executable', '')
    context['UCAS_MAIN_COMMAND'] = main_cmd

    # Chain hooks for tmux execution
    # Logic: exports && prerun && main_cmd && postrun
    # Note: Using && means failures stop the chain.
    all_cmds = [get_context_export_str(context)]
    
    prerun = hooks.get('prerun', [])
    if isinstance(prerun, str): prerun = [prerun]
    all_cmds.extend(prerun)
    
    all_cmds.append(main_cmd)
    
    postrun = hooks.get('postrun', [])
    if isinstance(postrun, str): postrun = [postrun]
    all_cmds.extend(postrun)
    
    # Final command to execute in tmux
    final_command = ' && '.join(all_cmds)

    # Select run-mod
    run_name = select_run_mod(merged_config, debug)
    
    # Resolve run-mod config
    run_path = find_entity(run_name)
    if not run_path:
        raise LaunchError(f"Run-mod '{run_name}' not found")
    
    run_config_full = load_config(run_path)
    run_def = get_run_config(run_config_full)

    # Validate runner (even for dry-run)
    validate_runner(run_def, context)

    # Dry-run or execute
    if dry_run:
        # For dry-run, we still want to show what would be executed
        # We can call a simplified version or just show the run name
        print(f"{prefix}Run-mod: {run_name} (targeting: {final_command})")
    else:
        # Run install hooks in host environment first
        hook_runner.run(hooks, 'install')
        
        run_command(run_def, final_command, member_name, context, run_path, debug)


def main():
    """Main entry point."""
    args = parse_args()

    try:
        if args.command == 'run':
            run_agent(args)
        elif args.command == 'run-team':
            run_team(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)
    except LaunchError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.debug:
            raise
        sys.exit(1)


def run_agent(args):
    """Run a single agent with optional mods."""
    name = args.agent
    cli_mods = args.mods or []

    entity_path = find_entity(name)
    if not entity_path:
        raise LaunchError(f"Agent/Mod '{name}' not found in mods/ library.")

    if args.debug:
        print(f"[DEBUG] Found entity on disk: {entity_path}", file=sys.stderr)

    # Load base config to get default mods
    (sys_cfg, sys_ovr), (usr_cfg, usr_ovr), (prj_cfg, prj_ovr) = get_layer_config_paths()
    base_config = {}
    
    # Merge order: System -> User -> Project (Sandwich base)
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            config = parse_yaml(cfg.read_text())
            base_config = _merge_dicts(base_config, config, args.debug, f"Base:{layer_name}")
    
    # Extract default mods names/specs from config
    raw_default_mods = base_config.get('mods', [])
    if isinstance(raw_default_mods, str):
        raw_default_mods = [raw_default_mods]
    
    # Keep as list of entities (can be strings or dictionaries with metadata)
    default_mods = raw_default_mods
    
    # Combine default mods with CLI mods (CLI mods come after defaults)
    all_mods = default_mods + cli_mods
    
    if args.debug and default_mods:
        print(f"[DEBUG] Default mods from config: {default_mods}", file=sys.stderr)
        print(f"[DEBUG] All mods (default + CLI): {all_mods}", file=sys.stderr)

    # Note: run_agent strictly runs a single member. 
    # If the entity is a team, it will still just run its 'base' personality if it has one.
    _prepare_and_run_member(
        member_name=name,
        agent_name=name,
        mods=all_mods,
        dry_run=args.dry_run,
        debug=args.debug
    )



def run_config_team(team_name: str, team_def: Dict[str, Any], cli_mods: List[str], args):
    """Execution logic for a team defined in configuration."""
    import time

    # User's example uses 'agents' key for members
    members = team_def.get('agents') or team_def.get('members')
    if not members:
        raise LaunchError(f"Team '{team_name}' has no agents/members defined")

    team_wide_mods = team_def.get('mods', [])
    sleep_seconds = team_def.get('sleep_seconds', 0)

    # Run each member
    member_names = list(members.keys())
    for idx, member_name in enumerate(member_names):
        member_spec = members[member_name]
        
        # "Only Mods" philosophy: member definition is primarily defined by its mods.
        # karel: [basic-chat, api-mod] OR karel: { mods: [basic-chat], ... }
        if isinstance(member_spec, list):
            base_agent = member_spec[0]
            member_mods = member_spec[1:]
        elif isinstance(member_spec, str):
            base_agent = member_spec
            member_mods = []
        elif isinstance(member_spec, dict):
            # Look for 'mods' first (Unified approach), fallback to 'agent' (Legacy)
            agent_list = member_spec.get('mods') or member_spec.get('agent')
            if not agent_list:
                raise LaunchError(f"Team member '{member_name}' has no mods/agent specified")
            
            if isinstance(agent_list, list):
                base_agent = agent_list[0]
                member_mods = agent_list[1:]
            else:
                base_agent = agent_list
                # If they used 'agent: string', check if they also have 'mods: list' (legacy)
                if 'agent' in member_spec and isinstance(member_spec.get('mods'), list):
                    member_mods = member_spec['mods']
                else:
                    member_mods = []
        else:
            raise LaunchError(f"Invalid member definition for '{member_name}'")

        # Total Aggregated Mods
        all_mods = team_wide_mods + cli_mods + member_mods

        if args.debug:
            print(f"[TEAM] Member '{member_name}': {base_agent} +{' +'.join(all_mods) if all_mods else '(no mods)'}", file=sys.stderr)

        # Prepare and run member
        _prepare_and_run_member(
            member_name=member_name,
            agent_name=base_agent,
            mods=all_mods,
            dry_run=args.dry_run,
            debug=args.debug,
            prefix=f"[{member_name}] ",
            team_name=team_name
        )

        # Sleep between starts (except after last member)
        is_last = (idx == len(member_names) - 1)
        if sleep_seconds > 0 and not is_last and not args.dry_run:
            if args.debug:
                print(f"[TEAM] Sleeping {sleep_seconds}s before next member...", file=sys.stderr)
            time.sleep(sleep_seconds)


def run_team(args):
    """Run a team of agents (Simplified: Team is a Mod)."""
    name = args.team
    
    # 1. Resolve team name as a mod
    entity_path = find_entity(name)
    if not entity_path:
        raise LaunchError(f"Team mod '{name}' not found in mods/ library.")

    # 2. Standard Sandwich Merge for this mod
    # This pulls in defaults from System/User/Project layers and merges with mod's ucas.yaml.
    merged_config = merge_configs(entity_path, [], args.debug)

    # 3. Check for singular 'team' key
    team_def = merged_config.get('team')
    if not team_def:
        # Fallback to 'members'/'agents' for backward compatibility if it's a team mod directory
        # but the user didn't wrap it in 'team:' key yet.
        if 'agents' in merged_config or 'members' in merged_config:
            team_def = merged_config
        else:
            raise LaunchError(f"Mod '{name}' does not define a 'team' (missing 'team' key).")

    if args.debug:
        print(f"[TEAM] Found team definition in: {entity_path}", file=sys.stderr)

    run_config_team(name, team_def, args.mods or [], args)


if __name__ == '__main__':
    main()
