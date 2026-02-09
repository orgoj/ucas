"""
UCAS Doctor - Diagnostic tool for UCAS installation and configuration.
"""

import sys
import socket
from pathlib import Path
from typing import List, Tuple, Dict


def check_installation() -> List[Tuple[bool, str, str]]:
    """Check if UCAS is properly installed."""
    checks = []
    
    ucas_dir = Path.home() / ".ucas"
    if ucas_dir.exists():
        checks.append((True, "~/.ucas", str(ucas_dir)))
    else:
        checks.append((False, "~/.ucas", "Missing - run 'ucas install'"))
    
    config_file = Path.home() / ".ucas" / "ucas.yaml"
    if config_file.exists():
        checks.append((True, "User config", str(config_file)))
    else:
        checks.append((False, "User config", "Missing - run 'ucas install'"))
    
    desktop_entry = Path.home() / ".local" / "share" / "applications" / "ucas-mail.desktop"
    if desktop_entry.exists():
        checks.append((True, "Desktop entry", str(desktop_entry)))
    else:
        checks.append((False, "Desktop entry", "Missing - run 'ucas install'"))
    
    return checks


def check_mail_notification() -> Tuple[bool, str, str]:
    """Check if mail notification is configured."""
    config_file = Path.home() / ".ucas" / "ucas.yaml"
    
    if not config_file.exists():
        return False, "Mail notification", "User config missing"
    
    try:
        from .yaml_parser import parse_yaml
        config = parse_yaml(config_file.read_text())
        
        mail_notifications = config.get('mail', {}).get('notifications', {})
        if not mail_notifications:
            return False, "Mail notification", "No mail.notifications section"
        
        on_new_mail = mail_notifications.get('on_new_mail', '').strip()
        if not on_new_mail:
            return False, "Mail notification", "on_new_mail command not set"
        
        # Check if notify-send is available
        from shutil import which
        if not which('notify-send'):
            return True, "Mail notification", f"Configured but notify-send not found (install libnotify-bin)"
        
        return True, "Mail notification", f"Configured: {on_new_mail}"
    
    except Exception as e:
        return False, "Mail notification", f"Error: {e}"


def check_hostname() -> Tuple[bool, str, str]:
    """Check hostname for Message-ID format."""
    try:
        hostname = socket.gethostname()
        return True, "Hostname", hostname
    except Exception as e:
        return False, "Hostname", f"Error: {e}"


def run_doctor() -> Dict:
    """Run all diagnostic checks."""
    return {
        'installation': check_installation(),
        'hostname': check_hostname(),
        'mail_notification': check_mail_notification(),
    }


def print_doctor_results(results: Dict, verbose: bool = False):
    """Print doctor check results."""
    print("=" * 60)
    print("UCAS DOCTOR - Installation Diagnostic")
    print("=" * 60)
    
    all_passed = True
    
    # Hostname
    passed, label, msg = results['hostname']
    status = "✓" if passed else "✗"
    all_passed = all_passed and passed
    print(f"{status} {label:30} : {msg}")
    
    # Installation checks
    print(f"\nInstallation:")
    for passed, label, msg in results['installation']:
        status = "✓" if passed else "✗"
        all_passed = all_passed and passed
        print(f"  {status} {label:20} : {msg}")
    
    # Mail notification
    passed, label, msg = results['mail_notification']
    status = "✓" if passed else "✗"
    all_passed = all_passed and passed
    print(f"\n{status} {label:30} : {msg}")
    
    print("=" * 60)
    if all_passed:
        print("All checks passed! ✓")
    else:
        print("Some checks failed. Run 'ucas install --force' to reinstall.")
    sys.exit(0 if all_passed else 1)
