"""
Mail system for UCAS agents and users.
Handles sending, listing, reading, and checking messages using standard .eml format.
Everything is context-aware using project absolute paths.
"""

import os
import sys
import json
import socket
import subprocess
import shlex
import time
import glob
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
import email
from email import policy
from email.message import EmailMessage
from email.utils import formatdate, parsedate_to_datetime
from . import settings
from .merger import merge_configs

# Constants
USER_AGENT_NAME = "USER"
MAIL_SUBDIR = "mails"
PROJECT_LIST_FILE = Path.home() / ".ucas" / "mail-projects.txt"
_UCAS_HOSTNAME = socket.gethostname()

def _get_project_root() -> Path:
    """Find the project root (where .ucas exists) or current directory."""
    cwd = Path.cwd()
    root = cwd
    while root != root.parent:
        if (root / ".ucas").exists():
            return root.resolve()
        root = root.parent
    return cwd.resolve()

def _get_user_mail_dir() -> Path:
    """Get the global mail directory for the user."""
    return (Path.home() / ".ucas" / MAIL_SUBDIR / USER_AGENT_NAME).resolve()

def _get_agent_mail_dir(agent_name: str, project_root: Optional[Path] = None) -> Path:
    """Get the mail directory for a specific agent."""
    if agent_name == USER_AGENT_NAME:
        return _get_user_mail_dir()
    
    if "@" in agent_name:
        parts = agent_name.split("@")
        if len(parts) == 2:
            name, path_str = parts
            target_root = Path(path_str).expanduser().resolve()
            return target_root / ".ucas" / MAIL_SUBDIR / name

    if not project_root:
        project_root = _get_project_root()
    else:
        project_root = Path(project_root).resolve()
    
    return project_root / ".ucas" / MAIL_SUBDIR / agent_name

def _ensure_mail_dirs(base_dir: Path):
    """Ensure inbox, read, sent, archive directories exist."""
    for subdir in ["inbox", "read", "sent", "archive"]:
        (base_dir / subdir).mkdir(parents=True, exist_ok=True)

def _generate_mail_id() -> str:
    """Generate a unique mail ID."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    random_part = hashlib.md5(os.urandom(16)).hexdigest()[:4]
    return f"{timestamp}-{random_part}"

def _get_sender_info(override_agent: Optional[str] = None, project_root: Optional[Path] = None) -> Tuple[str, Path]:
    """Determine current sender name and their mail directory."""
    if override_agent:
        return override_agent, _get_agent_mail_dir(override_agent, project_root)

    agent_name = os.environ.get("UCAS_AGENT")
    if agent_name:
        return agent_name, _get_agent_mail_dir(agent_name, project_root)
    return USER_AGENT_NAME, _get_user_mail_dir()

def _update_project_list(project_root: Path):
    """Register project path for the GUI."""
    try:
        abs_path = str(Path(project_root).resolve())
        if abs_path.startswith("/tmp/"):
            return
            
        PROJECT_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        current_paths = set(PROJECT_LIST_FILE.read_text().splitlines()) if PROJECT_LIST_FILE.exists() else set()
        if abs_path not in current_paths:
            with open(PROJECT_LIST_FILE, "a") as f:
                f.write(f"{abs_path}\n")
    except:
        pass

def _parse_eml(path: Path, folder: str) -> Dict:
    """Parse an EML file into a dictionary."""
    with open(path, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_content()
                break
    else:
        body = msg.get_content()

    return {
        "id": path.stem,
        "timestamp": path.stat().st_mtime,
        "date_str": msg.get('Date') or "",
        "from": msg.get('From'),
        "to": msg.get('To'),
        "subject": msg.get('Subject'),
        "body": body,
        "from_project": msg.get('X-Ucas-Project'),
        "in_reply_to": msg.get('X-Ucas-In-Reply-To'),
        "_folder": folder,
        "_path": str(path)
    }

def _deliver_mail(target_dir: Path, msg: EmailMessage) -> bool:
    """Deliver a message to an agent's inbox."""
    try:
        _ensure_mail_dirs(target_dir)
        mail_filename = f"{msg['Message-ID'].strip('<>').split('@')[0]}.eml"
        with open(target_dir / "inbox" / mail_filename, 'wb') as f:
            f.write(msg.as_bytes())
        return True
    except:
        return False

# --- Public API ---

def get_messages(agent_name: Optional[str] = None, folders: List[str] = None, project_root: Optional[Path] = None) -> List[Dict]:
    """Get list of messages for an agent."""
    name, mail_dir = _get_sender_info(agent_name, project_root)
    if not mail_dir.exists():
        return []
    
    mails = []
    for folder in (folders or ["inbox"]):
        path = mail_dir / folder
        if path.exists():
            for mail_file in path.glob("*.eml"):
                try:
                    mails.append(_parse_eml(mail_file, folder))
                except:
                    continue
    mails.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return mails

def get_message_content(mail_id: str, agent_name: Optional[str] = None, project_root: Optional[Path] = None) -> Tuple[Optional[Dict], Optional[Path], Optional[str]]:
    """Get message content and file path. Returns (data, filepath, foldername)."""
    name, mail_dir = _get_sender_info(agent_name, project_root)
    for folder in ["inbox", "read", "sent", "archive"]:
        path = mail_dir / folder / f"{mail_id}.eml"
        if path.exists():
            return _parse_eml(path, folder), path, folder
        files = list((mail_dir / folder).glob(f"{mail_id}*.eml"))
        if files:
            return _parse_eml(files[0], folder), files[0], folder
    return None, None, None

def mark_as_read(mail_id: str, agent_name: Optional[str] = None, project_root: Optional[Path] = None):
    """Move message from inbox to read folder."""
    data, path, folder = get_message_content(mail_id, agent_name, project_root)
    if data and path and folder == "inbox":
        read_dir = path.parent.parent / "read"
        read_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(read_dir / path.name))

def archive_mail(mail_id: str, agent_name: Optional[str] = None, project_root: Optional[Path] = None):
    """Move message to archive folder."""
    data, path, folder = get_message_content(mail_id, agent_name, project_root)
    if data and path and folder != "archive":
        archive_dir = path.parent.parent / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(archive_dir / path.name))

def send_mail(recipient: str, subject: str, body: str, reply_id: Optional[str] = None, sender_override: Optional[str] = None, project_root: Optional[Path] = None):
    """Send a mail to a recipient."""
    if not project_root:
        project_root = _get_project_root()
    sender_name, sender_mail_dir = _get_sender_info(sender_override, project_root)
    
    full_sender = f"{sender_name}@{project_root}" if sender_name != USER_AGENT_NAME else sender_name

    if (not recipient or not subject) and reply_id:
        orig, _, _ = get_message_content(reply_id, agent_name=sender_name, project_root=project_root)
        if orig:
            if not recipient:
                recipient = orig.get('from')
            if not subject:
                subj = orig.get('subject', 'No Subject')
                subject = "Re: " + subj.replace("Re: ", "")
    
    if not recipient or not subject:
        print("Error: Recipient and Subject required.", file=sys.stderr)
        return

    mail_id = _generate_mail_id()
    _update_project_list(project_root)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = full_sender
    msg['To'] = recipient
    msg['X-Ucas-Project'] = str(project_root)
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = f"<{mail_id}@ucas-{_UCAS_HOSTNAME}>"
    if reply_id:
        msg['X-Ucas-In-Reply-To'] = reply_id
    msg.set_content(body)
    
    if recipient.upper() == "ALL":
        mails_dir = project_root / ".ucas" / MAIL_SUBDIR
        targets = []
        if mails_dir.exists():
            for agent_dir in mails_dir.iterdir():
                if agent_dir.is_dir() and agent_dir.name.islower():
                    if agent_dir.name == sender_name:
                        continue
                    targets.append((agent_dir.name, agent_dir))
    else:
        if recipient == USER_AGENT_NAME:
            targets = [(USER_AGENT_NAME, _get_user_mail_dir())]
        else:
            targets = [(recipient, _get_agent_mail_dir(recipient, project_root))]

    sent_count = sum(1 for _, d in targets if _deliver_mail(d, msg))
    if sent_count > 0:
        _ensure_mail_dirs(sender_mail_dir)
        with open(sender_mail_dir / "sent" / f"{mail_id}.eml", 'wb') as f:
            f.write(msg.as_bytes())
    print(f"Mail sent to {sent_count} recipient(s).")

def list_mail(show_all=False, show_sent=False, show_archive=False, json_output=True):
    """List mails."""
    folders = ["sent"] if show_sent else (["archive"] if show_archive else (["inbox", "read"] if show_all else ["inbox"]))
    mails = get_messages(folders=folders)
    
    if json_output:
        print(json.dumps(mails, indent=2, ensure_ascii=False))
        return
    
    if not mails:
        print("No messages.")
        return

    print(f"{'ID':<20} {'DATE':<20} {'FROM':<30} {'TO':<30} {'FOLDER':<8} {'SUBJECT'}")
    print("-" * 140)
    for m in mails:
        print(f"{m.get('id'):<20} {m.get('date_str')[:19]:<20} {m.get('from'):<30} {m.get('to'):<30} {m['_folder']:<8} {m.get('subject')}")

def read_mail(mail_id: str, json_output=True):
    """Read a specific mail by ID. Moves from inbox to read."""
    data, path, folder = get_message_content(mail_id)
    if not data:
        if json_output:
            print(json.dumps({"error": "Not found"}))
        else:
            print("Not found.")
        return
    
    if json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for k in ['From', 'To', 'Date', 'Subject']:
            print(f"{k:<8}: {data.get(k.lower())}")
        print("-" * 40 + "\n" + data.get('body', '') + "\n" + "-" * 40)
        
    if folder == "inbox":
        mark_as_read(mail_id)

def get_address_book() -> List[Dict[str, str]]:
    """
    Get list of known contacts.
    Combines:
    1. USER (System)
    2. Local Agents in .ucas/mails (read description from mod if available)
    3. Entries in `mail-addressbook` from ucas.yaml (Merged Config)
    """
    contacts = [
        {"address": USER_AGENT_NAME, "type": "System", "desc": "Human User"},
        {"address": "ALL", "type": "Broadcast", "desc": "All agents in project"}
    ]

    current_agent = os.environ.get("UCAS_AGENT")
    root = _get_project_root()

    # Needs to import config loaders. Importing inside function to avoid circular imports if any
    try:
        from .resolver import get_layer_config_paths, load_config_file, get_search_paths, find_entity, load_config
        from .merger import _merge_dicts

        # Load merged config to get mail-addressbook
        (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
        merged_config = {}
        for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
            if cfg:
                merged_config = _merge_dicts(merged_config, load_config_file(cfg), False, f"Base:{layer_name}")

        # Load search paths to find local agent mods for descriptions
        extra_paths = merged_config.get('mod_path', [])
        if isinstance(extra_paths, str):
            extra_paths = [extra_paths]
        search_paths = get_search_paths(extra_paths, merged_config.get('strict', False))

        mails_dir = root / ".ucas" / MAIL_SUBDIR
        if mails_dir.exists():
            for item in mails_dir.iterdir():
                if item.is_dir() and item.name.islower():
                    # Skip USER and skip if this is current agent
                    if item.name == USER_AGENT_NAME:
                        continue
                    if item.name == current_agent:
                        continue

                    # Try to find mod for this agent to get description
                    desc = "Local Agent"
                    mod_path = find_entity(item.name, search_paths)
                    if mod_path:
                        try:
                            mod_cfg = load_config(mod_path)
                            if mod_cfg.get('description'):
                                desc = mod_cfg.get('description')
                        except:
                            pass

                    contacts.append({
                        "address": item.name,
                        "type": "Agent",
                        "desc": desc
                    })

        # Load configured mail-addressbook entries (external contacts)
        configured_book = merged_config.get('mail-addressbook', {})
        if isinstance(configured_book, dict):
            for addr, desc in configured_book.items():
                # Check if already exists (from local agents)
                existing = next((c for c in contacts if c['address'] == addr), None)
                if existing:
                    # Override description if it was "Local Agent"
                    if existing['desc'] == "Local Agent":
                        existing['desc'] = desc
                else:
                    # Add new entry
                    address_type = "External" if "@" in addr else "Configured"
                    contacts.append({
                        "address": addr,
                        "type": address_type,
                        "desc": desc
                    })

    except Exception:
        pass

    return contacts

def _get_mail_config() -> Dict[str, Any]:
    """Get merged mail configuration from all layers."""
    try:
        project_root = _get_project_root()
        merged = merge_configs(project_root, [], [], project_root=project_root)
        return merged.get('mail', {})
    except Exception:
        return {}


def _run_notification(msg_data: Dict[str, Any], project_root: Optional[Path] = None):
    """Execute user-configured notification command when new mail arrives."""
    mail_config = _get_mail_config()
    notification_config = mail_config.get('notifications', {})
    command_template = notification_config.get('on_new_mail', '').strip()

    if not command_template:
        return  # No notification configured

    # Substitute variables
    variables = {
        'subject': msg_data.get('subject', '') or 'No subject',
        'from': msg_data.get('from', '') or 'Unknown',
        'id': msg_data.get('id', ''),
        'date': msg_data.get('date_str', ''),
    }

    try:
        command = command_template
        for key, value in variables.items():
            escaped_value = shlex.quote(value)
            command = command.replace(f'{{{key}}}', escaped_value)

        subprocess.run(command, shell=True, check=False, capture_output=True)
    except Exception:
        # Silently fail on notification errors to not break mail delivery
        pass


def print_address_book(json_output=True):
    """Print address book."""
    contacts = get_address_book()
    if json_output:
        print(json.dumps(contacts, indent=2, ensure_ascii=False))
        return

    print(f"{'ADDRESS':<30} {'TYPE':<10} {'DESCRIPTION'}")
    print("-" * 80)
    for c in contacts:
        print(f"{c['address']:<30} {c['type']:<10} {c['desc']}")

def get_instruction(agent_name: Optional[str] = None) -> str:
    """Return instructions for the agent on how to use mail."""
    name = agent_name or os.environ.get("UCAS_AGENT") or USER_AGENT_NAME
    return f"""# UCAS Mail System Instructions for {name}

Use `ucas mail check --idle` to wait for tasks. Use `ucas mail send` with `--body`. 

## JSON OUTPUT
- `ucas mail list`, `ucas mail read`, and `ucas mail addressbook` return JSON by default.
- **DO NOT** use the `--json` flag with `ucas mail send` or `ucas mail check`.

## COMMUNICATION
- NEVER use `ucas run` to send messages to other agents. Use ONLY `ucas mail send`.
- Report to the human user (USER) only via `ucas mail send USER`."""

def check_mail(idle=False):
    """Check for new mail."""
    info = _get_sender_info()
    inbox = info[1] / "inbox"
    if not inbox.exists():
        if idle:
            _ensure_mail_dirs(inbox.parent)
        else:
            sys.exit(1)

    if idle:
        print(f"Waiting for mail in {inbox}...")
        while not any(inbox.glob("*.eml")):
            time.sleep(5)

    if any(inbox.glob("*.eml")):
        # Important: call get_messages with agent_name explicitly from info
        msgs = get_messages(agent_name=info[0], folders=['inbox'])
        if msgs:
            # Run notification for USER agent only
            if info[0] == USER_AGENT_NAME:
                for msg in msgs:
                    _run_notification(msg, project_root=_get_project_root())

            print("\n*** NEW MAIL RECEIVED ***")
            for m in msgs:
                print(f"ID:      {m['id']}")
                print(f"From:    {m['from']}")
                print(f"Subject: {m['subject']}")
                print(f"Command: ucas mail read {m['id']}")
                print("-" * 40)
            sys.exit(0)
    sys.exit(1)
