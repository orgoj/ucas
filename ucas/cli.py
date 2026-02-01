"""
CLI argument parsing for UCAS.
"""

import argparse
import sys


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='ucas',
        description='Universal CLI Agent System - intelligent assembler and launcher'
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # run command
    run_parser = subparsers.add_parser('run', help='Run an agent with optional mods')
    run_parser.add_argument('agent', help='Agent name to run')
    run_parser.add_argument('mods', nargs='*', help='Mods to apply (e.g., +mod-git +debug-mod)')
    run_parser.add_argument('--dry-run', action='store_true', help='Show command without executing')
    run_parser.add_argument('--debug', action='store_true', help='Verbose merge tracing')

    # run-team command (for Slice 5)
    team_parser = subparsers.add_parser('run-team', help='Run a team of agents')
    team_parser.add_argument('team', help='Team name to run')
    team_parser.add_argument('mods', nargs='*', help='Mods to apply to all team members')
    team_parser.add_argument('--dry-run', action='store_true', help='Show commands without executing')
    team_parser.add_argument('--debug', action='store_true', help='Verbose merge tracing')

    # stop-team command
    stop_parser = subparsers.add_parser('stop-team', help='Stop a running team')
    stop_parser.add_argument('team', help='Team name to stop')
    stop_parser.add_argument('mods', nargs='*', help='Mods to apply (to resolve the same runner)')
    stop_parser.add_argument('--dry-run', action='store_true', help='Show stop command without executing')
    stop_parser.add_argument('--debug', action='store_true', help='Verbose merge tracing')

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Process mods: extract +mod arguments
    if args.command in ('run', 'run-team') and args.mods:
        processed_mods = []
        for mod in args.mods:
            if mod.startswith('+'):
                processed_mods.append(mod[1:])  # Remove + prefix
            else:
                processed_mods.append(mod)
        args.mods = processed_mods

    return args
