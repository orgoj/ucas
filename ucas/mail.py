"""
Mail system for UCAS agents and users.
Handles sending, listing, reading, and checking messages.
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

# Constants
USER_AGENT_NAME = "user"
USER_MAIL_DIR = Path.home() / ".ucas" / "mail"

def _get_project_root() -> Path:
    """Find the project root (where .ucas exists) or current directory."""
    cwd = Path.cwd()
    root = cwd
    while root != root.parent:
        if (root / ".ucas").exists():
            return root
        root = root.parent
    return cwd

def _get_agent_mail_dir(agent_name: str, project_root: Optional[Path] = None) -> Path:
    """Get the mail directory for a specific agent."""
    if agent_name == USER_AGENT_NAME:
        return USER_MAIL_DIR
    
    if not project_root:
        project_root = _get_project_root()
        
    if "@" in agent_name:
        parts = agent_name.split("@")
        if len(parts) == 2:
            name, path_str = parts
            if ":" not in path_str:
                target_root = Path(path_str).expanduser().resolve()
                return target_root / ".ucas" / "notes" / name / "mail"

    return project_root / ".ucas" / "notes" / agent_name / "mail"

def _ensure_mail_dirs(base_dir: Path):
    """Ensure inbox, read, sent directories exist."""
    for subdir in ["inbox", "read", "sent"]:
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
    if agent_name:
        agent_dir = os.environ.get("UCAS_AGENT_NOTES")
        if agent_dir:
            return agent_name, Path(agent_dir) / "mail"
        else:
            return agent_name, _get_agent_mail_dir(agent_name)
    else:
        return USER_AGENT_NAME, USER_MAIL_DIR

# --- Public API for Data Retrieval ---

def get_messages(agent_name: Optional[str] = None, folders: List[str] = None) -> List[Dict]:
    """Get list of messages for an agent."""
    sender_name, mail_dir = _get_sender_info(agent_name)
    
    if not mail_dir.exists():
        return []

    if not folders:
        folders = ["inbox"]

    mails = []
    for folder in folders:
        path = mail_dir / folder
        if path.exists():
            for mail_file in path.glob("*.json"):
                try:
                    with open(mail_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        data['_folder'] = folder
                        mails.append(data)
                except:
                    continue
    
    # Sort by timestamp descending
    mails.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    return mails

def get_message_content(mail_id: str, agent_name: Optional[str] = None) -> Tuple[Optional[Dict], Optional[Path], Optional[str]]:
    """Get message content and file path. Returns (data, filepath, foldername)."""
    sender_name, mail_dir = _get_sender_info(agent_name)
    
    for folder in ["inbox", "read", "sent"]:
        path = mail_dir / folder / f"{mail_id}.json"
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f), path, folder
            except:
                pass
            
    # Try partial match
    for folder in ["inbox", "read", "sent"]:
        files = list((mail_dir / folder).glob(f"*{mail_id}*.json"))
        if files:
            try:
                with open(files[0], 'r', encoding='utf-8') as f:
                    return json.load(f), files[0], folder
            except:
                pass
                
    return None, None, None

def mark_as_read(mail_id: str, agent_name: Optional[str] = None):
    """Move message from inbox to read folder."""
    data, path, folder = get_message_content(mail_id, agent_name)
    if not data or not path or folder != "inbox":
        return

    sender_name, mail_dir = _get_sender_info(agent_name)
    read_dir = mail_dir / "read"
    _ensure_mail_dirs(mail_dir)
    new_path = read_dir / path.name
    
    data['read'] = True
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    shutil.move(str(path), str(new_path))

# --- CLI Actions ---

def send_mail(recipient: str, subject: str, body: str, reply_id: Optional[str] = None, sender_override: Optional[str] = None):
    """Send a mail to a recipient."""
    sender_name, sender_mail_dir = _get_sender_info(sender_override)
    
    mail_id = _generate_mail_id()
    timestamp = int(time.time())
    
    mail_data = {
        "id": mail_id,
        "timestamp": timestamp,
        "date_str": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        "from": sender_name,
        "to": recipient,
        "subject": subject,
        "body": body,
        "read": False
    }
    
    if reply_id:
        mail_data["in_reply_to"] = reply_id

    mail_filename = f"{mail_id}.json"
    
    targets = []
    if recipient.upper() == "ALL":
        root = _get_project_root()
        notes_dir = root / ".ucas" / "notes"
        if notes_dir.exists():
            for agent_dir in notes_dir.iterdir():
                if agent_dir.is_dir() and agent_dir.name != USER_AGENT_NAME:
                    targets.append((agent_dir.name, agent_dir / "mail"))
    else:
        targets.append((recipient, _get_agent_mail_dir(recipient)))
    
    sent_count = 0
    for target_name, target_dir in targets:
        try:
            _ensure_mail_dirs(target_dir)
            target_file = target_dir / "inbox" / mail_filename
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(mail_data, f, indent=2, ensure_ascii=False)
            sent_count += 1
        except Exception as e:
            print(f"Error sending to {target_name}: {e}", file=sys.stderr)

    if sent_count > 0:
        try:
            _ensure_mail_dirs(sender_mail_dir)
            sent_file = sender_mail_dir / "sent" / mail_filename
            with open(sent_file, 'w', encoding='utf-8') as f:
                json.dump(mail_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save to sent folder: {e}", file=sys.stderr)
            
    print(f"Mail sent to {sent_count} recipient(s).")

def list_mail(show_all: bool = False, show_sent: bool = False):
    """List mails in inbox (default), read (with --all), or sent (with --sent)."""
    folders = []
    if show_sent:
        folders.append("sent")
    else:
        folders.append("inbox")
        if show_all:
            folders.append("read")
            
    mails = get_messages(folders=folders)
    
    if not mails:
        print("No messages.")
        return

    print(f"{'ID':<20} {'DATE':<20} {'FROM':<15} {'FOLDER':<8} {'SUBJECT'}")
    print("-" * 80)
    for m in mails:
        folder_mark = m['_folder']
        print(f"{m.get('id'):<20} {m.get('date_str', ''):<20} {m.get('from', ''):<15} {folder_mark:<8} {m.get('subject', '')}")

def read_mail(mail_id: str):
    """Read a specific mail by ID. Moves from inbox to read."""
    data, path, folder = get_message_content(mail_id)
    
    if not data:
        print(f"Mail ID {mail_id} not found.")
        return

    print(f"From:    {data.get('from')}")
    print(f"To:      {data.get('to')}")
    print(f"Date:    {data.get('date_str')}")
    print(f"Subject: {data.get('subject')}")
    print("-" * 40)
    print(data.get('body'))
    print("-" * 40)
    
    if folder == "inbox":
        mark_as_read(mail_id)
        print("\n(Message moved to read folder)")

def get_address_book() -> List[Dict[str, str]]:
    """Get list of known contacts."""
    contacts = [
        {"address": "user", "type": "System", "desc": "Human User"},
        {"address": "ALL", "type": "Broadcast", "desc": "All agents in project"}
    ]
    
    # Scan local agents
    root = _get_project_root()
    notes_dir = root / ".ucas" / "notes"
    
    current_agent = os.environ.get("UCAS_AGENT")
    
    if notes_dir.exists():
        for item in notes_dir.iterdir():
            if item.is_dir() and item.name != USER_AGENT_NAME:
                if item.name == current_agent:
                    continue # Skip self
                
                contacts.append({
                    "address": item.name,
                    "type": "Agent",
                    "desc": "Local Agent"
                })
                
    return contacts

def print_address_book():
    """Print address book to stdout."""
    contacts = get_address_book()
    
    print(f"{'ADDRESS':<20} {'TYPE':<15} {'DESCRIPTION'}")
    print("-" * 60)
    for c in contacts:
        print(f"{c['address']:<20} {c['type']:<15} {c['desc']}")

def check_mail(idle: bool = False):
    """Check for new mail in inbox."""
    sender_name, mail_dir = _get_sender_info()
    inbox = mail_dir / "inbox"
    
    if not inbox.exists():
        if idle:
            _ensure_mail_dirs(mail_dir)
        else:
            print("No mail directory.")
            sys.exit(1)
            
    def has_mail():
        return any(inbox.glob("*.json"))
        
    def list_new_mails():
        """Helper to print new mail details."""
        print("\n*** NEW MAIL RECEIVED ***")
        # Reuse get_messages for consistent formatting, but restrict to inbox
        # We need to import get_messages if it's not available in scope, 
        # but check_mail is defined in the same module.
        # Wait, get_messages is defined above.
        
        # We need to call get_messages with agent_name=None to imply current env
        msgs = get_messages(folders=['inbox'])
        
        if msgs:
            # Sort by timestamp ascending (oldest first) so agent processes in order?
            # Or descending (newest first)? Usually newest is most urgent?
            # Let's show newest first.
            msgs.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
            
            for m in msgs:
                print(f"ID:      {m.get('id')}")
                print(f"From:    {m.get('from')}")
                print(f"Subject: {m.get('subject')}")
                print(f"Command: ucas mail read {m.get('id')}")
                print("-" * 40)
        else:
            print("False alarm? No messages found.")

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
