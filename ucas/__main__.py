"""
UCAS entry point: python -m ucas
"""

import sys
from pathlib import Path
from typing import List, Dict, Any

from .cli import parse_args
from .resolver import find_entity, is_acli, load_config, get_layer_config_paths
from .merger import merge_configs, collect_skills
from .launcher import (
    select_acli, build_command, run_tmux, LaunchError, 
    prepare_context, HookRunner, get_context_export_str
)


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
    # Find agent
    agent_path = find_entity(agent_name)
    if not agent_path:
        raise LaunchError(f"Agent '{agent_name}' not found")

    if debug:
        print(f"[DEBUG] Found agent: {agent_path}", file=sys.stderr)

    # Find mods
    mod_paths = []
    for mod_name in mods:
        mod_path = find_entity(mod_name)
        if not mod_path:
            raise LaunchError(f"Mod '{mod_name}' not found")
        mod_paths.append(mod_path)
        if debug:
            print(f"[DEBUG] Found mod: {mod_path}", file=sys.stderr)

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
        debug
    )

    # Update context with dynamic info
    context['UCAS_ACLI_EXE'] = acli_config.get('executable', '')
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

    # Dry-run or execute
    if dry_run:
        print(f"{prefix}Command: {final_command}")
    else:
        # Run install hooks in host environment first
        hook_runner.run(hooks, 'install')
        
        run_tmux(final_command, member_name, context, debug)


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

    mod_paths = []
    for mod_name in cli_mods:
        m_path = find_entity(mod_name)
        if not m_path:
            raise LaunchError(f"Mod '{mod_name}' not found")
        mod_paths.append(m_path)

    # Note: run_agent strictly runs a single member. 
    # If the entity is a team, it will still just run its 'base' personality if it has one.
    _prepare_and_run_member(
        member_name=name,
        agent_name=name,
        mods=cli_mods,
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

    run_config_team(name, team_def, [], args)


if __name__ == '__main__':
    main()
