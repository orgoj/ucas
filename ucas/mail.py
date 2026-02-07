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
from typing import List, Dict, Optional

# Constants
USER_AGENT_NAME = "user"
USER_MAIL_DIR = Path.home() / ".ucas" / "mail"

def _get_project_root() -> Path:
    """Find the project root (where .ucas exists) or current directory."""
    # Try to find .ucas in current or parent directories
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
        
    # Check if agent_name contains a path (e.g. agent@/path/to/project)
    if "@" in agent_name:
        parts = agent_name.split("@")
        if len(parts) == 2:
            name, path_str = parts
            # Handle host:path later if needed, for now assume local path
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

def _get_sender_info() -> tuple[str, Path]:
    """Determine current sender name and their mail directory."""
    agent_name = os.environ.get("UCAS_AGENT")
    if agent_name:
        # We are inside an agent
        agent_dir = os.environ.get("UCAS_AGENT_NOTES")
        if agent_dir:
            return agent_name, Path(agent_dir) / "mail"
        else:
            # Fallback if variable is missing but name is set
            return agent_name, _get_agent_mail_dir(agent_name)
    else:
        # We are the user
        return USER_AGENT_NAME, USER_MAIL_DIR

def send_mail(recipient: str, subject: str, body: str, reply_id: Optional[str] = None):
    """Send a mail to a recipient."""
    sender_name, sender_mail_dir = _get_sender_info()
    
    # Prepare mail object
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
    
    # Determine recipients
    targets = []
    
    if recipient.upper() == "ALL":
        # Scan project for all agents
        root = _get_project_root()
        notes_dir = root / ".ucas" / "notes"
        if notes_dir.exists():
            for agent_dir in notes_dir.iterdir():
                if agent_dir.is_dir() and agent_dir.name != USER_AGENT_NAME:
                    targets.append((agent_dir.name, agent_dir / "mail"))
    else:
        targets.append((recipient, _get_agent_mail_dir(recipient)))
    
    # Send to all targets
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

    # Save to sender's sent folder
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
    sender_name, mail_dir = _get_sender_info()
    
    if not mail_dir.exists():
        print(f"No mail directory found for {sender_name} at {mail_dir}")
        return

    folders = []
    if show_sent:
        folders.append("sent")
    else:
        folders.append("inbox")
        if show_all:
            folders.append("read")
            
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
    
    if not mails:
        print("No messages.")
        return

    # Print table
    print(f"{'ID':<20} {'DATE':<20} {'FROM':<15} {'FOLDER':<8} {'SUBJECT'}")
    print("-" * 80)
    for m in mails:
        folder_mark = m['_folder']
        print(f"{m.get('id'):<20} {m.get('date_str', ''):<20} {m.get('from', ''):<15} {folder_mark:<8} {m.get('subject', '')}")

def read_mail(mail_id: str):
    """Read a specific mail by ID. Moves from inbox to read."""
    sender_name, mail_dir = _get_sender_info()
    
    # Search in all folders
    found_file = None
    found_folder = None
    
    for folder in ["inbox", "read", "sent"]:
        path = mail_dir / folder / f"{mail_id}.json"
        if path.exists():
            found_file = path
            found_folder = folder
            break
            
    if not found_file:
        # Try partial match
        for folder in ["inbox", "read", "sent"]:
            files = list((mail_dir / folder).glob(f"*{mail_id}*.json"))
            if files:
                found_file = files[0]
                found_folder = folder
                break
    
    if not found_file:
        print(f"Mail ID {mail_id} not found.")
        return

    try:
        with open(found_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"From:    {data.get('from')}")
        print(f"To:      {data.get('to')}")
        print(f"Date:    {data.get('date_str')}")
        print(f"Subject: {data.get('subject')}")
        print("-" * 40)
        print(data.get('body'))
        print("-" * 40)
        
        # If in inbox and we are the recipient, move to read
        if found_folder == "inbox":
            read_dir = mail_dir / "read"
            _ensure_mail_dirs(mail_dir)
            new_path = read_dir / found_file.name
            
            # Update read status in JSON
            data['read'] = True
            with open(found_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            shutil.move(str(found_file), str(new_path))
            print("\n(Message moved to read folder)")
            
    except Exception as e:
        print(f"Error reading mail: {e}")

def check_mail(idle: bool = False):
    """Check for new mail in inbox."""
    sender_name, mail_dir = _get_sender_info()
    inbox = mail_dir / "inbox"
    
    if not inbox.exists():
        if idle:
            # Create it if we are waiting
            _ensure_mail_dirs(mail_dir)
        else:
            print("No mail directory.")
            sys.exit(1)
            
    def has_mail():
        return any(inbox.glob("*.json"))
        
    if idle:
        print(f"Waiting for mail in {inbox}...")
        while True:
            if has_mail():
                print("You have new mail! Check it with `ucas mail list`")
                sys.exit(0)
            time.sleep(5)
    else:
        if has_mail():
            print("You have new mail! Check it with `ucas mail list`")
            sys.exit(0)
        else:
            sys.exit(1)
