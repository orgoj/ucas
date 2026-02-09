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
from . import team
from .cli import parse_args
from .launcher import (
    prepare_and_run_member, HookRunner, get_context_export_str,
    validate_runner, stop_runner, expand_variables,
    get_runner_preview
)
from .exceptions import LaunchError, MergerError
# We might need resolve_entities if run_agent uses it from here?
# run_agent uses prepare_and_run_member which is now in launcher.
from .resolver import (
    load_config, get_layer_config_paths, 
    get_search_paths, load_config_file
)
from .merger import merge_configs, collect_skills, _merge_dicts, resolve_entities


def main():
    """Main entry point."""
    args = parse_args()
    try:
        if args.command == 'run':
            run_agent(args)
        elif args.command == 'team':
            team.handle_team_command(args)
        elif args.command == 'ls-mods':
            ls_mods(args)
        elif args.command == 'mail':
            handle_mail(args)
        elif args.command == 'install':
            from . import installer
            results = installer.run_install(force=args.force)
            installer.print_install_results(results, verbose=settings.VERBOSE)
        elif args.command == 'doctor':
            from . import doctor
            results = doctor.run_doctor()
            doctor.print_doctor_results(results, verbose=settings.VERBOSE)
        elif args.command == 'init':
            from . import project
            project.initialize_project(interactive=not args.non_interactive)
        elif args.command == 'list':
            from . import project
            project.list_projects(json_output=args.json, running_only=args.running, show_agents=args.agents)
        elif args.command == 'term':
            from . import project
            project.handle_term_command(args.project)
        elif args.command == 'autostart':
            from . import project
            project.handle_autostart_command(args.tags)
        # Compatibility/Legacy commands removed from CLI parser but if they were there:
        # they are not in args.command anymore.
    except LaunchError as e:
        print(f"Error: {e}", file=sys.stderr); sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if settings.DEBUG: raise
        sys.exit(1)


def handle_mail(args):
    """Handle mail commands."""
    if not args.mail_command:
        print("Use: ucas mail {send,list,read,check,archive,instruction,addressbook,gui} ...")
        sys.exit(1)

    if args.mail_command == 'send':
        recipient = args.recipient or args.to
        subject = args.subject or args.subject_flag
        
        if args.body:
            body = args.body
        else:
            # Read body from stdin
            if sys.stdin.isatty():
                print("Enter message body (Ctrl+D to finish):")
            body = sys.stdin.read()
            
        mail.send_mail(recipient, subject, body, reply_id=args.reply)
        
    elif args.mail_command == 'list':
        # Respect --json flag, fallback to not --table
        json_output = args.json if hasattr(args, 'json') else not args.table
        mail.list_mail(show_all=args.all, show_sent=args.sent, show_archive=args.archive, json_output=json_output)
        
    elif args.mail_command == 'read':
        # Respect --json flag, fallback to not --table
        json_output = args.json if hasattr(args, 'json') else not args.table
        mail.read_mail(args.id, json_output=json_output)

    elif args.mail_command == 'archive':
        mail.archive_mail(args.id)
        
    elif args.mail_command == 'check':
        mail.check_mail(idle=args.idle)
        
    elif args.mail_command == 'addressbook':
        # Respect --json flag
        json_output = args.json if hasattr(args, 'json') else not args.table
        mail.print_address_book(json_output=json_output)
        
    elif args.mail_command == 'instruction':
        print(mail.get_instruction(args.agent_name or "USER"))

    elif args.mail_command == 'gui':
        if os.environ.get("UCAS_AGENT"):
            print("Error: Mail GUI is not available for AI agents. It is for human use only.", file=sys.stderr)
            sys.exit(1)
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
    prepare_and_run_member(
        member_name=args.agent,
        agent_name=args.agent,
        mods=args.mods or []
    )


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
