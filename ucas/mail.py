"""
Mail system for UCAS agents and users.
Handles sending, listing, reading, and checking messages using standard .eml format.
"""

import os
import sys
import json
import time
import glob
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import email
from email import policy
from email.message import EmailMessage
from email.utils import formatdate, parsedate_to_datetime
from . import settings

# Constants
USER_AGENT_NAME = "USER"
MAIL_SUBDIR = "mails" # Plural as requested
PROJECT_LIST_FILE = Path.home() / ".ucas" / "mail-projects.txt"

def _get_project_root() -> Path:
    """Find the project root (where .ucas exists) or current directory."""
    cwd = Path.cwd()
    root = cwd
    while root != root.parent:
        if (root / ".ucas").exists():
            return root
        root = root.parent
    return cwd

def _get_user_mail_dir() -> Path:
    """Get the global mail directory for the user."""
    return Path.home() / ".ucas" / MAIL_SUBDIR / USER_AGENT_NAME

def _get_agent_mail_dir(agent_name: str, project_root: Optional[Path] = None) -> Path:
    """Get the mail directory for a specific agent. Supports agent@/path/to/project."""
    if agent_name == USER_AGENT_NAME:
        return _get_user_mail_dir()
    
    if not project_root:
        project_root = _get_project_root()
        
    if "@" in agent_name:
        parts = agent_name.split("@")
        if len(parts) == 2:
            name, path_str = parts
            target_root = Path(path_str).expanduser()
            if not target_root.is_absolute():
                 base = project_root if project_root else _get_project_root()
                 target_root = (base / target_root).resolve()
            
            return target_root / ".ucas" / MAIL_SUBDIR / name
    
    return project_root / ".ucas" / MAIL_SUBDIR / agent_name

def _ensure_mail_dirs(base_dir: Path):
    """Ensure inbox, read, sent, archive directories exist."""
    for subdir in ["inbox", "read", "sent", "archive"]:
        (base_dir / subdir).mkdir(parents=True, exist_ok=True)

def _generate_mail_id() -> str:
    """Generate a unique mail ID based on timestamp and random hash."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    random_part = hashlib.md5(os.urandom(16)).hexdigest()[:4]
    return f"{timestamp}-{random_part}"

def _get_sender_info(override_agent: Optional[str] = None) -> Tuple[str, Path]:
    """Determine current sender name and their mail directory."""
    if override_agent:
        return override_agent, _get_agent_mail_dir(override_agent)

    agent_name = os.environ.get("UCAS_AGENT")
    notes_path = os.environ.get("UCAS_AGENT_NOTES")
    
    if agent_name:
        if notes_path:
            p_notes = Path(notes_path).resolve()
            if ".ucas" in str(p_notes):
                try:
                    p_root = Path(str(p_notes).split(".ucas")[0])
                    return agent_name, _get_agent_mail_dir(agent_name, p_root)
                except:
                    pass
        
        return agent_name, _get_agent_mail_dir(agent_name)
    else:
        return USER_AGENT_NAME, _get_user_mail_dir()

def _update_project_list(project_root: Path):
    """Append project path to user's mail-projects.txt if not present."""
    try:
        PROJECT_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not PROJECT_LIST_FILE.exists():
            PROJECT_LIST_FILE.touch()
            
        current_paths = set(PROJECT_LIST_FILE.read_text().splitlines())
        abs_path = str(project_root.resolve())
        
        if abs_path not in current_paths:
            with open(PROJECT_LIST_FILE, "a") as f:
                f.write(f"{abs_path}\n")
    except Exception:
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

    date_str = msg.get('Date')
    timestamp = 0
    if date_str:
        try:
            dt = parsedate_to_datetime(date_str)
            timestamp = dt.timestamp()
        except:
            timestamp = path.stat().st_mtime
    else:
        timestamp = path.stat().st_mtime

    return {
        "id": path.stem, 
        "timestamp": timestamp,
        "date_str": date_str or datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        "from": msg.get('From'),
        "to": msg.get('To'),
        "subject": msg.get('Subject'),
        "body": body,
        "from_project": msg.get('X-Ucas-Project'),
        "in_reply_to": msg.get('X-Ucas-In-Reply-To') or msg.get('In-Reply-To'),
        "_folder": folder,
        "_path": str(path)
    }

def _deliver_mail(target_name: str, target_dir: Path, msg: EmailMessage) -> bool:
    """Deliver a message to an agent's inbox."""
    try:
        _ensure_mail_dirs(target_dir)
        mail_filename = f"{msg['Message-ID'].strip('<>').split('@')[0]}.eml"
        target_file = target_dir / "inbox" / mail_filename
        
        with open(target_file, 'wb') as f:
            f.write(msg.as_bytes())
        
        _handle_autostart(target_dir)
        return True
    except Exception as e:
        print(f"Error sending to {target_name}: {e}", file=sys.stderr)
        return False

def _handle_autostart(target_dir: Path):
    """Check for team_autostart in project config and trigger if needed."""
    if ".ucas" not in str(target_dir):
        return
        
    try:
        parts = str(target_dir).split(".ucas")
        project_root = Path(parts[0])
        config_path = project_root / ".ucas" / "ucas.yaml"
        
        if config_path.exists():
            from .resolver import load_config_file
            from .team import is_team_running, run_team_programmatically
            
            config = load_config_file(config_path)
            if config.get('team_autostart') is True:
                if not is_team_running(project_root):
                    if settings.VERBOSE:
                        print(f"[AUTOSTART] Triggering team for {project_root}")
                    run_team_programmatically(project_root)
    except Exception as e:
        if settings.DEBUG:
            print(f"[DEBUG] Autostart error: {e}", file=sys.stderr)

# --- Public API for Data Retrieval ---

def get_messages(agent_name: Optional[str] = None, folders: List[str] = None) -> List[Dict]:
    """Get list of messages for an agent."""
    current_agent = os.environ.get("UCAS_AGENT")
    
    if agent_name:
        target_agent = agent_name
    else:
        target_agent = current_agent if current_agent else USER_AGENT_NAME

    if current_agent and target_agent == USER_AGENT_NAME:
        return []

    mail_dir = _get_agent_mail_dir(target_agent)

    if not mail_dir.exists():
        return []

    if not folders:
        folders = ["inbox"]

    mails = []
    for folder in folders:
        path = mail_dir / folder
        if path.exists():
            for mail_file in path.glob("*.eml"):
                try:
                    mails.append(_parse_eml(mail_file, folder))
                except Exception:
                    continue
    
    mails.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return mails

def get_message_content(mail_id: str, agent_name: Optional[str] = None) -> Tuple[Optional[Dict], Optional[Path], Optional[str]]:
    """Get message content and file path. Returns (data, filepath, foldername)."""
    current_agent = os.environ.get("UCAS_AGENT")
    
    if agent_name:
        target_agent = agent_name
    else:
        target_agent = current_agent if current_agent else USER_AGENT_NAME

    if current_agent and target_agent == USER_AGENT_NAME:
        return None, None, None

    mail_dir = _get_agent_mail_dir(target_agent)
    
    for folder in ["inbox", "read", "sent", "archive"]:
        path = mail_dir / folder / f"{mail_id}.eml"
        if path.exists():
            try:
                return _parse_eml(path, folder), path, folder
            except:
                pass
        
        files = list((mail_dir / folder).glob(f"{mail_id}*.eml"))
        if files:
            try:
                return _parse_eml(files[0], folder), files[0], folder
            except:
                pass

    return None, None, None

def mark_as_read(mail_id: str, agent_name: Optional[str] = None):
    """Move message from inbox to read folder."""
    data, path, folder = get_message_content(mail_id, agent_name)
    if not data or not path or folder != "inbox":
        return

    mail_dir = path.parent.parent
    read_dir = mail_dir / "read"
    _ensure_mail_dirs(mail_dir)
    new_path = read_dir / path.name
    
    shutil.move(str(path), str(new_path))

def archive_mail(mail_id: str, agent_name: Optional[str] = None):
    """Move message to archive folder."""
    data, path, folder = get_message_content(mail_id, agent_name)
    if not data or not path or folder == "archive":
        return

    mail_dir = path.parent.parent
    archive_dir = mail_dir / "archive"
    _ensure_mail_dirs(mail_dir)
    new_path = archive_dir / path.name
    
    shutil.move(str(path), str(new_path))

# --- CLI Actions ---

def send_mail(recipient: str, subject: str, body: str, reply_id: Optional[str] = None, sender_override: Optional[str] = None):
    """Send a mail to a recipient."""
    current_agent = os.environ.get("UCAS_AGENT")
    
    if current_agent and sender_override == USER_AGENT_NAME:
        print("Error: Agents cannot send mail as USER.", file=sys.stderr)
        return

    sender_name, sender_mail_dir = _get_sender_info(sender_override)
    project_root = _get_project_root()
    
    full_sender = f"{sender_name}@{project_root}" if sender_name != USER_AGENT_NAME else sender_name

    if (not recipient or not subject) and reply_id:
        orig_data, _, _ = get_message_content(reply_id)
        if orig_data:
            if not recipient:
                recipient = orig_data.get('from')
            if not subject:
                orig_subj = orig_data.get('subject', 'No Subject')
                subject = orig_subj if orig_subj.startswith("Re:") else f"Re: {orig_subj}"
    
    if not recipient or not subject:
        print("Error: Recipient and Subject are required.", file=sys.stderr)
        return

    mail_id = _generate_mail_id()
    _update_project_list(project_root)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = full_sender
    msg['To'] = recipient
    msg['X-Ucas-Project'] = str(project_root)
    msg['Date'] = formatdate(localtime=True)
    msg['Message-ID'] = f"<{mail_id}@ucas>"
    
    if reply_id:
        msg['In-Reply-To'] = f"<{reply_id}@ucas>"
        msg['X-Ucas-In-Reply-To'] = reply_id
    
    msg.set_content(body)
    
    mail_filename = f"{mail_id}.eml"
    
    targets = []
    if recipient.upper() == "ALL":
        mails_dir = project_root / ".ucas" / MAIL_SUBDIR
        if mails_dir.exists():
            for agent_dir in mails_dir.iterdir():
                if agent_dir.is_dir() and agent_dir.name != USER_AGENT_NAME:
                    targets.append((agent_dir.name, agent_dir))
    else:
        if recipient == USER_AGENT_NAME:
            targets.append((USER_AGENT_NAME, _get_user_mail_dir()))
        else:
            targets.append((recipient, _get_agent_mail_dir(recipient, project_root)))
    
    sent_count = 0
    for target_name, target_dir in targets:
        if _deliver_mail(target_name, target_dir, msg):
            sent_count += 1

    if sent_count > 0:
        try:
            _ensure_mail_dirs(sender_mail_dir)
            sent_file = sender_mail_dir / "sent" / mail_filename
            with open(sent_file, 'wb') as f:
                f.write(msg.as_bytes())
        except Exception as e:
            print(f"Warning: Could not save to sent folder: {e}", file=sys.stderr)
            
    print(f"Mail sent to {sent_count} recipient(s).")

def list_mail(show_all: bool = False, show_sent: bool = False, show_archive: bool = False, json_output: bool = True):
    """List mails."""
    folders = []
    if show_sent:
        folders.append("sent")
    elif show_archive:
        folders.append("archive")
    else:
        folders.append("inbox")
        if show_all:
            folders.append("read")
            
    mails = get_messages(folders=folders)
    
    if json_output:
        print(json.dumps(mails, indent=2, ensure_ascii=False))
        return
    
    if not mails:
        print("No messages.")
        return

    print(f"{'ID':<20} {'DATE':<20} {'FROM':<30} {'FOLDER':<8} {'SUBJECT'}")
    print("-" * 100)
    
    for m in mails:
        folder_mark = m['_folder']
        sender = m['from']
        print(f"{m.get('id'):<20} {m.get('date_str', ''):<20} {sender:<30} {folder_mark:<8} {m.get('subject', '')}")

def read_mail(mail_id: str, json_output: bool = True):
    """Read a specific mail by ID. Moves from inbox to read."""
    data, path, folder = get_message_content(mail_id)
    
    if not data:
        err = {"error": f"Mail ID {mail_id} not found"}
        if json_output:
            print(json.dumps(err, indent=2))
        else:
            print(f"Mail ID {mail_id} not found.")
        return

    if json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"From:    {data.get('from')}")
        print(f"To:      {data.get('to')}")
        print(f"Date:    {data.get('date_str')}")
        print(f"Subject: {data.get('subject')}")
        print("-" * 40)
        print(data.get('body'))
        print("-" * 40)
    
    if folder == "inbox":
        mark_as_read(mail_id)
        if not json_output:
            print("\n(Message moved to read folder)")

def get_address_book() -> List[Dict[str, str]]:
    """Get list of known contacts."""
    contacts = [
        {"address": USER_AGENT_NAME, "type": "System", "desc": "Human User"},
        {"address": "ALL", "type": "Broadcast", "desc": "All agents in project"}
    ]
    
    current_agent = os.environ.get("UCAS_AGENT")
    root = _get_project_root()
    
    try:
        from .resolver import get_layer_config_paths, load_config_file, get_search_paths, find_entity, load_config
        from .merger import _merge_dicts
        
        (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
        merged_config = {}
        for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
            if cfg:
                merged_config = _merge_dicts(merged_config, load_config_file(cfg), False, f"Base:{layer_name}")
        
        extra_paths = merged_config.get('mod_path', [])
        if isinstance(extra_paths, str): extra_paths = [extra_paths]
        search_paths = get_search_paths(extra_paths, merged_config.get('strict', False))
        
        mails_dir = root / ".ucas" / MAIL_SUBDIR
        if mails_dir.exists():
            for item in mails_dir.iterdir():
                if item.is_dir() and item.name != USER_AGENT_NAME:
                    if item.name == current_agent:
                        continue 
                    
                    desc = "Local Agent"
                    m_path = find_entity(item.name, search_paths)
                    if m_path:
                        try:
                            m_cfg = load_config(m_path)
                            if m_cfg.get('description'):
                                desc = m_cfg.get('description')
                        except:
                            pass
                    
                    contacts.append({
                        "address": item.name,
                        "type": "Agent",
                        "desc": desc
                    })
        
        configured_book = merged_config.get('mail-addressbook', {})
        if isinstance(configured_book, dict):
            for addr, desc in configured_book.items():
                if not any(c['address'] == addr for c in contacts):
                    contacts.append({
                        "address": addr,
                        "type": "External" if "@" in addr else "Configured",
                        "desc": desc
                    })
                else:
                    for c in contacts:
                        if c['address'] == addr and c['desc'] == "Local Agent":
                            c['desc'] = desc

    except Exception:
        pass

    return contacts

def print_address_book(json_output: bool = True):
    """Print address book."""
    contacts = get_address_book()
    
    if json_output:
        print(json.dumps(contacts, indent=2, ensure_ascii=False))
        return
    
    print(f"{'ADDRESS':<30} {'TYPE':<10} {'DESCRIPTION'}")
    print("-" * 80)
    for c in contacts:
        print(f"{c['address']:<30} {c['type']:<10} {c['desc']}")

def get_instruction(agent_name: str) -> str:
    """Return instructions for the agent on how to use mail."""
    return f"""# UCAS Mail System Instructions for {agent_name}

You are equipped with a file-based messaging system for team collaboration.

## CORE COMMANDS

1. CHECK FOR MAIL (CRITICAL)
   Run this when you are waiting for tasks or replies. It blocks until mail arrives.
   $ ucas mail check --idle

2. LIST MESSAGES
   $ ucas mail list
   (Returns JSON list of messages in your inbox)

3. READ MESSAGE
   $ ucas mail read <ID>
   (Returns message details as JSON and moves it to 'read' folder)

4. SEND MESSAGE
   $ ucas mail send <RECIPIENT> "<SUBJECT>" --body "Your message content here"
   (Use the recipient name from addressbook or 'USER')

5. ADDRESS BOOK
   $ ucas mail addressbook
   (Discover team members)

## RULES
- Always prefer JSON output for parsing.
- Use --idle when waiting; do not loop manually.
- Use --body for all outgoing messages.
- If you receive an empty body, ask the sender for clarification.
"""

def check_mail(idle: bool = False):
    """Check for new mail in inbox."""
    _update_project_list(_get_project_root())
    
    sender_name, mail_dir = _get_sender_info()
    inbox = mail_dir / "inbox"
    
    if not inbox.exists():
        if idle:
            _ensure_mail_dirs(mail_dir)
        else:
            sys.exit(1)
            
    def has_mail():
        return any(inbox.glob("*.eml"))
        
    def list_new_mails():
        """Helper to print new mail details."""
        print("\n*** NEW MAIL RECEIVED ***")
        msgs = get_messages(folders=['inbox'])
        msgs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        for m in msgs:
            print(f"ID:      {m.get('id')}")
            print(f"From:    {m.get('from')}")
            print(f"Subject: {m.get('subject')}")
            print(f"Command: ucas mail read {m.get('id')}")
            print("-" * 40)

    if idle:
        print(f"Waiting for mail in {inbox}...")
        while True:
            if has_mail():
                list_new_mails()
                sys.exit(0)
            time.sleep(5)
    else:
        if has_mail():
            list_new_mails()
            sys.exit(0)
        else:
            sys.exit(1)
