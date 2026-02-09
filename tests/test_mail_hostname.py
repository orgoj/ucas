"""
Test for Message-ID hostname format.
"""
import email
import socket
import pytest
from pathlib import Path
from ucas import mail
from unittest.mock import patch
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


def test_message_id_hostname(mail_env):
    """Test that Message-ID includes actual hostname."""
    import socket

    # Get actual hostname (we'll verify it's included in Message-ID)
    actual_hostname = socket.gethostname()

    mail.send_mail("agent2", "Test Subject", "Test Body")

    # Check agent2 inbox
    recip_dir = mail_env / ".ucas" / "mails" / "agent2" / "inbox"
    assert len(list(recip_dir.glob("*.eml"))) == 1

    # Parse the message and check Message-ID
    eml_file = list(recip_dir.glob("*.eml"))[0]
    msg = EmailMessage()
    with open(eml_file, 'rb') as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)

    message_id = msg.get('Message-ID')
    assert message_id is not None
    assert actual_hostname in message_id
    assert message_id.endswith(f"@ucas-{actual_hostname}>")


def test_hostname_constant(mail_env):
    """Test that _UCAS_HOSTNAME constant is set."""
    # Mock socket.gethostname to return a known value
    with patch("ucas.mail.socket.gethostname", return_value="test-machine"):
        import importlib
        import ucas.mail
        importlib.reload(ucas.mail)

        assert ucas.mail._UCAS_HOSTNAME == "test-machine"
