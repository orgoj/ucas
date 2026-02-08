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
    team_parser.add_argument('team', nargs='?', help='Team name (optional if defined in project config)')
    team_parser.add_argument('mods', nargs='*', help='Global team mods')

    # stop-team
    stop_parser = subparsers.add_parser('stop-team', help='Stop a team')
    stop_parser.add_argument('team', nargs='?', help='Team name (optional if defined in project config)')
    stop_parser.add_argument('mods', nargs='*', help='Mods')

    # ls-mods
    subparsers.add_parser('ls-mods', help='List available mods')

    # mail
    mail_parser = subparsers.add_parser('mail', help='Mail system')
    mail_subparsers = mail_parser.add_subparsers(dest='mail_command', help='Mail commands')
    
    # mail send
    send_parser = mail_subparsers.add_parser('send', help='Send mail')
    send_parser.add_argument('recipient', help='Recipient name (or ALL)')
    send_parser.add_argument('subject', help='Subject line')
    send_parser.add_argument('--body', help='Message body (optional, otherwise reads from stdin)')
    send_parser.add_argument('--reply', help='ID of message being replied to')
    
    # mail list
    list_parser = mail_subparsers.add_parser('list', help='List mails')
    list_parser.add_argument('--all', action='store_true', help='Include read messages')
    list_parser.add_argument('--sent', action='store_true', help='Show sent messages')
    list_parser.add_argument('--table', action='store_true', help='Output in human-readable table')
    list_parser.add_argument('--json', action='store_true', help='Output in JSON format (default)')
    
    # mail read
    read_parser = mail_subparsers.add_parser('read', help='Read mail')
    read_parser.add_argument('id', help='Mail ID')
    read_parser.add_argument('--table', action='store_true', help='Output in human-readable format')
    read_parser.add_argument('--json', action='store_true', help='Output in JSON format (default)')
    
    # mail check
    check_parser = mail_subparsers.add_parser('check', help='Check for new mail')
    check_parser.add_argument('--idle', action='store_true', help='Wait for new mail')

    # mail addressbook
    addr_parser = mail_subparsers.add_parser('addressbook', help='List known contacts')
    addr_parser.add_argument('--table', action='store_true', help='Output in human-readable table')
    addr_parser.add_argument('--json', action='store_true', help='Output in JSON format (default)')
    
    # mail gui
    gui_parser = mail_subparsers.add_parser('gui', help='Open mail GUI')
    gui_parser.add_argument('agent_name', nargs='?', help='Optional agent name to impersonate')

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
