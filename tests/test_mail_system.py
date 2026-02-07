import unittest
import os
import sys
import shutil
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

# Add project root to path to import ucas
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from ucas import mail

class TestMailSystem(unittest.TestCase):
    def setUp(self):
        # Create a temporary project structure
        self.test_dir = tempfile.mkdtemp()
        self.project_root = Path(self.test_dir)
        self.ucas_dir = self.project_root / ".ucas"
        self.notes_dir = self.ucas_dir / "notes"
        self.notes_dir.mkdir(parents=True)
        
        # Create agent directories
        self.agent1_dir = self.notes_dir / "agent1"
        self.agent2_dir = self.notes_dir / "agent2"
        self.agent1_dir.mkdir()
        self.agent2_dir.mkdir()
        
        # Mock environment and project root
        self.env_patcher = patch.dict(os.environ, {
            "UCAS_AGENT": "agent1", 
            "UCAS_AGENT_NOTES": str(self.agent1_dir)
        })
        self.env_patcher.start()
        
        self.root_patcher = patch('ucas.mail._get_project_root', return_value=self.project_root)
        self.root_patcher.start()
        
        # Capture stdout/stderr
        self.held_stdout = StringIO()
        self.stdout_patcher = patch('sys.stdout', self.held_stdout)
        self.stdout_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()
        self.root_patcher.stop()
        self.stdout_patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_send_mail(self):
        # agent1 sends to agent2
        mail.send_mail("agent2", "Subject 1", "Body 1")
        
        # Check agent2 inbox
        inbox2 = self.agent2_dir / "mail" / "inbox"
        self.assertTrue(inbox2.exists())
        files = list(inbox2.glob("*.json"))
        self.assertEqual(len(files), 1)
        
        with open(files[0], 'r') as f:
            data = json.load(f)
            self.assertEqual(data['from'], "agent1")
            self.assertEqual(data['to'], "agent2")
            self.assertEqual(data['subject'], "Subject 1")
            self.assertEqual(data['body'], "Body 1")
            self.assertFalse(data['read'])

        # Check agent1 sent
        sent1 = self.agent1_dir / "mail" / "sent"
        self.assertTrue(sent1.exists())
        files_sent = list(sent1.glob("*.json"))
        self.assertEqual(len(files_sent), 1)

    def test_list_mail(self):
        # Create a mail manually in agent1's inbox
        inbox1 = self.agent1_dir / "mail" / "inbox"
        inbox1.mkdir(parents=True)
        mail_data = {
            "id": "123", "timestamp": 1000, "date_str": "2024-01-01",
            "from": "agent2", "to": "agent1", "subject": "Hello", "body": "Hi", "read": False
        }
        with open(inbox1 / "123.json", 'w') as f:
            json.dump(mail_data, f)
            
        mail.list_mail()
        output = self.held_stdout.getvalue()
        self.assertIn("123", output)
        self.assertIn("agent2", output)
        self.assertIn("Hello", output)

    def test_read_mail(self):
        # Create a mail in agent1's inbox
        inbox1 = self.agent1_dir / "mail" / "inbox"
        inbox1.mkdir(parents=True)
        mail_data = {
            "id": "msg-1", "timestamp": 1000, "date_str": "2024-01-01",
            "from": "agent2", "to": "agent1", "subject": "Secret", "body": "Hidden Info", "read": False
        }
        with open(inbox1 / "msg-1.json", 'w') as f:
            json.dump(mail_data, f)
            
        # Read it
        mail.read_mail("msg-1")
        output = self.held_stdout.getvalue()
        self.assertIn("Hidden Info", output)
        
        # Verify moved to read
        read1 = self.agent1_dir / "mail" / "read"
        self.assertTrue((read1 / "msg-1.json").exists())
        self.assertFalse((inbox1 / "msg-1.json").exists())
        
        # Verify marked as read
        with open(read1 / "msg-1.json", 'r') as f:
            data = json.load(f)
            self.assertTrue(data['read'])

    def test_check_mail(self):
        # No mail initially
        with self.assertRaises(SystemExit) as cm:
            mail.check_mail()
        self.assertEqual(cm.exception.code, 1)
        
        # Add mail
        inbox1 = self.agent1_dir / "mail" / "inbox"
        inbox1.mkdir(parents=True)
        with open(inbox1 / "test.json", 'w') as f:
            f.write("{}")
            
        with self.assertRaises(SystemExit) as cm:
            mail.check_mail()
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("You have new mail", self.held_stdout.getvalue())

    def test_send_to_all(self):
        mail.send_mail("ALL", "Announcement", "Everyone listen")
        
        # Check agent2 inbox (agent1 is sender, so shouldn't receive it, but others should)
        # Note: logic for ALL iterates over directories in notes/. 
        # agent1 is sender. agent2 is another dir.
        
        files2 = list((self.agent2_dir / "mail" / "inbox").glob("*.json"))
        self.assertEqual(len(files2), 1)
        
        # Sender shouldn't send to self in ALL? 
        # The logic in mail.py: if agent_dir.name != USER_AGENT_NAME: targets.append...
        # It doesn't exclude self currently unless self is USER.
        # Let's check agent1 inbox.
        files1 = list((self.agent1_dir / "mail" / "inbox").glob("*.json"))
        # Depending on implementation, it might send to self if self is in notes/
        
        # Implementation check:
        # for agent_dir in notes_dir.iterdir():
        #    if agent_dir.is_dir() and agent_dir.name != USER_AGENT_NAME:
        
        # agent1 is in notes, so it sends to self too.
        self.assertEqual(len(files1), 1)


if __name__ == '__main__':
    unittest.main()
