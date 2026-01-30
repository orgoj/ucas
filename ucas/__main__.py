"""
UCAS entry point: python -m ucas
"""

import sys
from pathlib import Path
from typing import List

from .cli import parse_args
from .resolver import find_entity, is_acli, load_config
from .merger import merge_configs, collect_skills
from .launcher import select_acli, build_command, run_tmux, LaunchError


def _prepare_and_run_member(
    member_name: str,
    agent_name: str,
    mods: List[str],
    dry_run: bool,
    debug: bool,
    prefix: str = ""
) -> None:
    """
    Prepare and run a single agent member.
    Shared logic between run_agent and run_team.

    Args:
        member_name: Name for tmux window
        agent_name: Name of agent to run
        mods: List of mod names to apply
        dry_run: If True, print command instead of executing
        debug: Enable debug output
        prefix: Optional prefix for dry-run output (e.g., "[member1] ")
    """
    # Find agent
    agent_path = find_entity(agent_name, 'agents')
    if not agent_path:
        raise LaunchError(f"Agent '{agent_name}' not found")

    if debug:
        print(f"[DEBUG] Found agent: {agent_path}", file=sys.stderr)

    # Find mods
    mod_paths = []
    for mod_name in mods:
        mod_path = find_entity(mod_name, 'agents')
        if not mod_path:
            raise LaunchError(f"Mod '{mod_name}' not found")
        mod_paths.append(mod_path)
        if debug:
            print(f"[DEBUG] Found mod: {mod_path}", file=sys.stderr)

    # Merge configs
    merged_config = merge_configs(agent_path, mod_paths, debug)

    # Select ACLI
    acli_name = select_acli(merged_config, debug)

    # Load ACLI config
    acli_path = find_entity(acli_name, 'agents')
    if not acli_path:
        raise LaunchError(f"ACLI '{acli_name}' not found")

    if not is_acli(acli_path):
        raise LaunchError(f"'{acli_name}' is not an ACLI (missing 'executable' field)")

    acli_config = load_config(acli_path)

    # Collect skills
    skills_dirs = collect_skills(agent_path, mod_paths)

    # Build command
    command = build_command(
        agent_path,
        mod_paths,
        merged_config,
        acli_config,
        skills_dirs,
        debug
    )

    # Dry-run or execute
    if dry_run:
        print(f"{prefix}Command: {command}")
    else:
        run_tmux(command, member_name, debug)


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
    _prepare_and_run_member(
        member_name=args.agent,
        agent_name=args.agent,
        mods=args.mods or [],
        dry_run=args.dry_run,
        debug=args.debug
    )


def run_team(args):
    """Run a team of agents."""
    import time

    # Find team
    team_path = find_entity(args.team, 'teams')
    if not team_path:
        raise LaunchError(f"Team '{args.team}' not found")

    if args.debug:
        print(f"[DEBUG] Found team: {team_path}", file=sys.stderr)

    # Load team config
    team_config = load_config(team_path)

    members = team_config.get('members', {})
    if not members:
        raise LaunchError(f"Team '{args.team}' has no members defined")

    sleep_seconds = team_config.get('sleep_seconds', 0)

    # Run each member
    member_names = list(members.keys())
    for idx, member_name in enumerate(member_names):
        member_spec = members[member_name]
        agent_name = member_spec.get('agent')
        if not agent_name:
            raise LaunchError(f"Team member '{member_name}' has no agent specified")

        mods = member_spec.get('mods', [])

        if args.debug:
            print(f"[TEAM] Running member '{member_name}': {agent_name} +{' +'.join(mods) if mods else '(no mods)'}", file=sys.stderr)

        # Prepare and run member
        _prepare_and_run_member(
            member_name=member_name,
            agent_name=agent_name,
            mods=mods,
            dry_run=args.dry_run,
            debug=args.debug,
            prefix=f"[{member_name}] "
        )

        # Sleep between starts (except after last member)
        is_last = (idx == len(member_names) - 1)
        if sleep_seconds > 0 and not is_last and not args.dry_run:
            if args.debug:
                print(f"[TEAM] Sleeping {sleep_seconds}s before next member...", file=sys.stderr)
            time.sleep(sleep_seconds)


if __name__ == '__main__':
    main()
