"""
CLI argument parsing for UCAS.
"""

import argparse
import sys
from . import settings


def parse_args(argv=None):
    """Parse command-line arguments and set global settings."""
    if argv is None:
        argv = sys.argv[1:]

    # Neprůstřelné nastavení globálních flagů bez ohledu na argparse
    settings.DRY_RUN = '--dry-run' in argv
    settings.DEBUG = '--debug' in argv
    settings.VERBOSE = '-v' in argv or '--verbose' in argv
    settings.QUIET = '-q' in argv or '--quiet' in argv

    parser = argparse.ArgumentParser(
        prog='ucas',
        description='Universal CLI Agent System'
    )
    
    # Definujeme je i v argparse, aby neházel chybu 'unrecognized arguments'
    parser.add_argument('-q', '--quiet', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('-v', '--verbose', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--dry-run', action='store_true', help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # run
    run_parser = subparsers.add_parser('run', help='Run an agent')
    run_parser.add_argument('agent', help='Agent name')
    run_parser.add_argument('mods', nargs='*', help='Mods (+mod)')

    # run-team
    team_parser = subparsers.add_parser('run-team', help='Run a team')
    team_parser.add_argument('team', help='Team name')
    team_parser.add_argument('mods', nargs='*', help='Global team mods')

    # stop-team
    stop_parser = subparsers.add_parser('stop-team', help='Stop a team')
    stop_parser.add_argument('team', help='Team name')
    stop_parser.add_argument('mods', nargs='*', help='Mods')

    # ls-mods
    subparsers.add_parser('ls-mods', help='List available mods')

    # Ignorujeme známé globální flagy při parsování subpříkazů
    known_argv = [a for a in argv if a not in ('--dry-run', '--debug', '-v', '--verbose', '-q', '--quiet')]
    args = parser.parse_args(known_argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Process mods prefix
    if args.command in ('run', 'run-team', 'stop-team') and hasattr(args, 'mods'):
        args.mods = [m[1:] if m.startswith('+') else m for m in args.mods]

    return args
