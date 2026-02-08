
import os
import shutil
import pytest
from pathlib import Path
from ucas import mail, settings, team
from unittest.mock import MagicMock, patch
from email.message import EmailMessage

@pytest.fixture
def mail_env(tmp_path):
    """Setup a temporary mail environment."""
    # Define a fake project root
    project_root = tmp_path / "project"
    project_root.mkdir()
    
    # Mock _get_project_root to return our tmp path
    with patch("ucas.mail._get_project_root", return_value=project_root):
        yield project_root

def test_generate_mail_id():
    mid = mail._generate_mail_id()
    assert "-" in mid
    assert len(mid) > 10

def test_ensure_mail_dirs(mail_env):
    agent_dir = mail_env / ".ucas" / "mails" / "test-agent"
    mail._ensure_mail_dirs(agent_dir)
    
    assert (agent_dir / "inbox").exists()
    assert (agent_dir / "sent").exists()
    assert (agent_dir / "read").exists()
    assert (agent_dir / "archive").exists()

def test_get_agent_mail_dir_local(mail_env):
    # Test local agent
    path = mail._get_agent_mail_dir("agent1", mail_env)
    assert path == mail_env / ".ucas" / "mails" / "agent1"
    
    # Test USER
    # Note: USER dir is typically global ~/.ucas, but logic might vary.
    # mail.USER_MAIL_DIR is a global constant, so it won't be inside our tmp_path unless we mock the constant or logic.
    # The function checks explicit constant match first.
    pass 

def test_get_agent_mail_dir_cross_project(mail_env, tmp_path):
    other_project = tmp_path / "other"
    other_project.mkdir()
    
    # agent@/abs/path
    agent_name = f"agent2@{other_project}"
    path = mail._get_agent_mail_dir(agent_name, mail_env)
    assert path == other_project / ".ucas" / "mails" / "agent2"

def test_send_and_read_mail(mail_env, capsys):
    # Setup
    sender = "agent1"
    recipient = "agent2"
    
    with patch.dict(os.environ, {"UCAS_AGENT": sender}):
        mail.send_mail(recipient, "Test Subject", "Test Body")
        
    captured = capsys.readouterr()
    assert "Mail sent to 1 recipient(s)." in captured.out
    
    # Check recipient inbox
    recip_dir = mail_env / ".ucas" / "mails" / "agent2" / "inbox"
    assert len(list(recip_dir.glob("*.eml"))) == 1
    
    # Check sender sent
    sender_dir = mail_env / ".ucas" / "mails" / "agent1" / "sent"
    assert len(list(sender_dir.glob("*.eml"))) == 1
    
    # Read mail
    # We need to list messages to get ID
    msgs = mail.get_messages("agent2")
    assert len(msgs) == 1
    msg_id = msgs[0]['id']
    
    # Read content
    content, _, _ = mail.get_message_content(msg_id, "agent2")
    assert content['subject'] == "Test Subject"
    assert content['body'].strip() == "Test Body"

def test_address_book_config(mail_env):
    # Create ucas.yaml in project root with address book
    (mail_env / ".ucas").mkdir(parents=True, exist_ok=True)
    yaml_content = """
mail-addressbook:
  bob: "The Builder"
  alice@/tmp: "Wonderland"
    """
    (mail_env / ".ucas" / "ucas.yaml").write_text(yaml_content)
    
    # Mock loading config - complicated due to imports in function
    # We'll rely on the fact that get_address_book imports from resolver/merger
    # which read files from disk.
    
    # We also need to mock os.getcwd() because resolver uses Path.cwd()
    # Mock get_layer_config_paths to point to our temp project config
    fake_layers = (
        (None, None), # System
        (None, None), # User
        (mail_env / ".ucas" / "ucas.yaml", None) # Project
    )
    
    with patch("ucas.resolver.get_layer_config_paths", return_value=fake_layers):
        contacts = mail.get_address_book()
        
        # Check for configured entries
        bob = next((c for c in contacts if c['address'] == 'bob'), None)
        assert bob is not None
        assert bob['desc'] == "The Builder"
        
        alice = next((c for c in contacts if c['address'] == 'alice@/tmp'), None)
        assert alice is not None
        assert alice['desc'] == "Wonderland"

def test_auto_reply_recipient(mail_env):
    # Setup: agent2 sends to agent1
    (mail_env / ".ucas" / "mails" / "agent2").mkdir(parents=True, exist_ok=True)
    with patch.dict(os.environ, {"UCAS_AGENT": "agent2"}):
        mail.send_mail("agent1", "Initial", "Hello")
    
    # agent1 sees the mail
    msgs = mail.get_messages("agent1")
    msg_id = msgs[0]['id']
    sender_addr = msgs[0]['from'] # Should be agent2@PATH
    
    # agent1 replies without specifying recipient
    with patch.dict(os.environ, {"UCAS_AGENT": "agent1"}):
        # recipient=None
        mail.send_mail(None, "Re: Initial", "Hi back", reply_id=msg_id)
    
    # agent2 should receive the reply
    replies = mail.get_messages("agent2")
    assert len(replies) == 1
    assert replies[0]['subject'] == "Re: Initial"
    assert replies[0]['to'] == sender_addr

def test_full_from_address(mail_env):
    with patch.dict(os.environ, {"UCAS_AGENT": "agent1"}):
        mail.send_mail("agent2", "Subj", "Body")
    
    msgs = mail.get_messages("agent2")
    # From should be agent1@path
    assert "@" in msgs[0]['from']
    assert str(mail_env) in msgs[0]['from']

def test_team_autostart(mail_env):
    # Setup project with autostart
    config_file = mail_env / ".ucas" / "ucas.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("team_autostart: true\n")
    
    (mail_env / ".ucas" / "mails" / "agent1").mkdir(parents=True, exist_ok=True)
    
    with patch("ucas.team.is_team_running", return_value=False) as mock_running, \
         patch("ucas.team.run_team_programmatically") as mock_run:
        
        # Send mail to agent1@mail_env
        msg = EmailMessage()
        msg['Subject'] = "Auto"
        msg['From'] = "User"
        msg['To'] = "agent1"
        msg['Message-ID'] = "<test@ucas>"
        
        mail._deliver_mail("agent1", mail_env / ".ucas" / "mails" / "agent1", msg)
        
        # Should have called mock_run
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == mail_env

def test_ucas_agent_notes_compatibility(mail_env):
    # Setup agent1 mailbox
    (mail_env / ".ucas" / "mails" / "agent1").mkdir(parents=True, exist_ok=True)
    
    # Mock UCAS_AGENT_NOTES pointing to the project
    notes_dir = mail_env / ".ucas" / "notes" / "agent1"
    notes_dir.mkdir(parents=True, exist_ok=True)
    
    with patch.dict(os.environ, {
        "UCAS_AGENT": "agent1",
        "UCAS_AGENT_NOTES": str(notes_dir)
    }):
        # It should derive project root from notes_path
        name, mail_dir = mail._get_sender_info()
        assert name == "agent1"
        assert str(mail_env) in str(mail_dir)
        assert ".ucas/mails/agent1" in str(mail_dir)

def test_relative_cross_project_robustness(mail_env):
    # agent@./other
    # Test Finding 4: project_root=None fallback
    (mail_env / "other" / ".ucas" / "mails" / "target").mkdir(parents=True, exist_ok=True)
    
    with patch("ucas.mail._get_project_root", return_value=mail_env):
        m_dir = mail._get_agent_mail_dir("target@./other", project_root=None)
        assert (mail_env / "other" / ".ucas" / "mails" / "target").resolve() == m_dir.resolve()

def test_auto_reply_subject(mail_env):
    # Setup: agent2 sends to agent1
    (mail_env / ".ucas" / "mails" / "agent2").mkdir(parents=True, exist_ok=True)
    with patch.dict(os.environ, {"UCAS_AGENT": "agent2"}):
        mail.send_mail("agent1", "Topic", "Hello")
    
    msgs = mail.get_messages("agent1")
    msg_id = msgs[0]['id']
    
    # agent1 replies without recipient AND without subject
    with patch.dict(os.environ, {"UCAS_AGENT": "agent1"}):
        # mail.send_mail(recipient=None, subject=None, ...)
        mail.send_mail(None, None, "Hi back", reply_id=msg_id)
    
    # agent2 should receive the reply with auto-subject
    replies = mail.get_messages("agent2")
    assert len(replies) == 1
    assert replies[0]['subject'] == "Re: Topic"

