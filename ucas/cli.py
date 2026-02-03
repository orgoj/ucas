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
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet output (minimalist)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show loaded config files')
    parser.add_argument('--debug', action='store_true', help='Verbose merge tracing')
    parser.add_argument('--dry-run', action='store_true', help='Show command without executing')

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # run command
    run_parser = subparsers.add_parser('run', help='Run an agent with optional mods')
    run_parser.add_argument('agent', help='Agent name to run')
    run_parser.add_argument('mods', nargs='*', help='Mods to apply (e.g., +mod-git +debug-mod)')

    # run-team command (for Slice 5)
    team_parser = subparsers.add_parser('run-team', help='Run a team of agents')
    team_parser.add_argument('team', help='Team name to run')
    team_parser.add_argument('mods', nargs='*', help='Mods to apply to all team members')

    # stop-team command
    stop_parser = subparsers.add_parser('stop-team', help='Stop a running team')
    stop_parser.add_argument('team', help='Team name to stop')
    stop_parser.add_argument('mods', nargs='*', help='Mods to apply (to resolve the same runner)')

    # ls-mods command
    ls_mods_parser = subparsers.add_parser('ls-mods', help='List available mods')
    ls_mods_parser.add_argument('--debug', action='store_true', help='Show debug information')

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
