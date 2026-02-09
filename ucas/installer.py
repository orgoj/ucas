"""
UCAS Installer - Sets up UCAS for the current user.
"""

import os
from pathlib import Path
from typing import List, Tuple, Dict


def get_ucas_home() -> Path:
    """Get UCAS home directory."""
    ucas_home = os.environ.get('UCAS_HOME')
    if not ucas_home:
        # Default to package location
        package_dir = Path(__file__).parent.parent
        ucas_home = str(package_dir)
    return Path(ucas_home)


def create_user_directories() -> List[str]:
    """Create ~/.ucas directory structure."""
    created = []
    ucas_dir = Path.home() / ".ucas"
    
    # Main directories
    for subdir in ["mods", "mails", "notes"]:
        path = ucas_dir / subdir
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
    
    # Create USER mail directory with subfolders
    user_mail = ucas_dir / "mails" / "USER"
    for folder in ["inbox", "sent", "read", "archive"]:
        (user_mail / folder).mkdir(parents=True, exist_ok=True)
    
    created.append(str(user_mail))
    
    return created


def create_user_config() -> Tuple[bool, str]:
    """Create ~/.ucas/ucas.yaml with mail notification template."""
    config_path = Path.home() / ".ucas" / "ucas.yaml"
    
    if config_path.exists():
        return False, f"Config already exists: {config_path}"
    
    config_content = """# UCAS User Configuration
# Settings here apply to all projects

# Mail notification - configure desktop notifications for new mail
mail:
  notifications:
    # Command to run when USER receives new mail
    # Supported placeholders: {subject}, {from}, {id}, {date}
    # Example: notify-send "UCAS Mail" "{subject} from {from}" -u normal
    on_new_mail: ""
"""
    
    config_path.write_text(config_content)
    return True, str(config_path)


def create_desktop_entry() -> Tuple[bool, str]:
    """Create desktop entry for clickable notifications."""
    desktop_dir = Path.home() / ".local" / "share" / "applications"
    desktop_path = desktop_dir / "ucas-mail.desktop"
    
    if desktop_path.exists():
        return False, f"Desktop entry already exists: {desktop_path}"
    
    desktop_dir.mkdir(parents=True, exist_ok=True)
    
    entry_content = """[Desktop Entry]
Name=UCAS Mail
Exec=ucas mail gui
Icon=mail-message
Type=Application
Categories=Utility;
StartupNotify=false
"""
    
    desktop_path.write_text(entry_content)
    return True, str(desktop_path)


def check_installation() -> List[Tuple[bool, str]]:
    """Check what's already installed."""
    checks = []
    
    ucas_dir = Path.home() / ".ucas"
    checks.append((ucas_dir.exists(), "~/.ucas directory"))
    
    config_file = Path.home() / ".ucas" / "ucas.yaml"
    checks.append((config_file.exists(), "User config file"))
    
    desktop_entry = Path.home() / ".local" / "share" / "applications" / "ucas-mail.desktop"
    checks.append((desktop_entry.exists(), "Desktop entry"))
    
    return checks


def run_install(force: bool = False) -> Dict:
    """Run UCAS installation for the user."""
    results = {
        'created_dirs': [],
        'created_config': None,
        'created_desktop': None,
        'skipped': [],
    }
    
    # Check what already exists
    existing = check_installation()
    all_exist = all(passed for passed, _ in existing)
    
    if all_exist and not force:
        results['message'] = "UCAS is already installed. Use --force to reinstall."
        return results
    
    # Create directories
    dirs = create_user_directories()
    results['created_dirs'] = dirs
    
    # Create config
    if force or not (Path.home() / ".ucas" / "ucas.yaml").exists():
        created, path = create_user_config()
        if created:
            results['created_config'] = path
        else:
            results['skipped'].append(f"Config: {path}")
    
    # Create desktop entry
    if force or not (Path.home() / ".local" / "share" / "applications" / "ucas-mail.desktop").exists():
        created, path = create_desktop_entry()
        if created:
            results['created_desktop'] = path
        else:
            results['skipped'].append(f"Desktop entry: {path}")
    
    if results['created_dirs'] or results['created_config'] or results['created_desktop']:
        results['message'] = "UCAS installed successfully!"
    else:
        results['message'] = "Nothing new installed (all components exist)."
    
    return results


def print_install_results(results: Dict, verbose: bool = False):
    """Print installation results."""
    print("=" * 60)
    print("UCAS INSTALLATION")
    print("=" * 60)
    
    if results.get('message'):
        print(f"\n{results['message']}\n")
    
    if results['created_dirs']:
        print("Created directories:")
        for d in results['created_dirs']:
            print(f"  • {d}")
        print()
    
    if results['created_config']:
        print(f"Created config: {results['created_config']}")
        print(f"  Edit this file to configure mail notifications.")
        print()
    
    if results['created_desktop']:
        print(f"Created desktop entry: {results['created_desktop']}")
        print(f"  Desktop notifications can now launch the GUI.")
        print()
    
    if results['skipped']:
        print("Skipped (already exists):")
        for item in results['skipped']:
            print(f"  • {item}")
        print()
    
    print("=" * 60)
    print("Next steps:")
    print("  1. Edit ~/.ucas/ucas.yaml to configure mail notifications")
    print("  2. Run 'ucas doctor' to verify installation")
    print("  3. Run 'ucas mail gui' to open the mail interface")
    print("=" * 60)
