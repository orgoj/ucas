"""
Project management module - registry and project operations.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from .yaml_parser import load_yaml, save_yaml


# Constants
REGISTRY_FILE = Path.home() / ".ucas" / "projects.yaml"
REGISTRY_VERSION = "1.0"
UCAS_DIR = ".ucas"
PROJECT_CONFIG_FILE = "ucas.yaml"


# =============================================================================
# Registry Operations (alias + path only)
# =============================================================================

def load_registry() -> Dict[str, Any]:
    """Load project registry from ~/.ucas/projects.yaml."""
    if not REGISTRY_FILE.exists():
        # Create empty registry
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        empty_registry = {
            "version": REGISTRY_VERSION,
            "projects": []
        }
        save_registry(empty_registry)
        return empty_registry

    try:
        registry = load_yaml(str(REGISTRY_FILE))
        # Ensure basic structure
        if "projects" not in registry:
            registry["projects"] = []
        if "version" not in registry:
            registry["version"] = REGISTRY_VERSION
        return registry
    except Exception as e:
        print(f"Warning: Failed to load registry: {e}", file=sys.stderr)
        return {"version": REGISTRY_VERSION, "projects": []}


def save_registry(registry: Dict[str, Any]) -> None:
    """Save project registry to ~/.ucas/projects.yaml."""
    try:
        REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
        save_yaml(str(REGISTRY_FILE), registry)
    except Exception as e:
        print(f"Error: Failed to save registry: {e}", file=sys.stderr)
        sys.exit(1)


def get_project_by_alias(alias: str) -> Optional[Dict[str, str]]:
    """Find project by alias in registry. Returns None if not found."""
    registry = load_registry()
    for project in registry.get("projects", []):
        if project.get("alias") == alias:
            return project
    return None


def register_project(path: Path, alias: str) -> Dict[str, str]:
    """
    Register a project in the registry.
    Returns the registered project dict.
    Raises exception if alias already exists.
    """
    path = path.resolve()
    registry = load_registry()

    # Check for alias collision
    existing = get_project_by_alias(alias)
    if existing:
        existing_path = existing.get("path", "")
        if str(existing_path) == str(path):
            # Same project, already registered
            return existing
        # Different project with same alias
        raise ValueError(f"Alias '{alias}' already used by {existing_path}")

    # Check if path already registered (with different alias)
    for project in registry.get("projects", []):
        if project.get("path") == str(path):
            print(f"Warning: Project {path} already registered as '{project['alias']}'", file=sys.stderr)
            return project

    # Add new project
    project_entry = {
        "alias": alias,
        "path": str(path)
    }
    registry["projects"].append(project_entry)
    save_registry(registry)
    return project_entry


def unregister_project(alias: str) -> bool:
    """Remove project from registry by alias. Returns True if removed."""
    registry = load_registry()
    projects = registry.get("projects", [])
    original_count = len(projects)

    registry["projects"] = [
        p for p in projects if p.get("alias") != alias
    ]

    if len(registry["projects"]) < original_count:
        save_registry(registry)
        return True
    return False


def resolve_project(spec: str) -> Optional[Path]:
    """
    Resolve project spec to absolute path.
    Spec can be:
    - alias (looks up in registry)
    - relative path
    - absolute path
    Returns None if not found.
    """
    # Try alias first
    project = get_project_by_alias(spec)
    if project:
        return Path(project["path"])

    # Try as path
    path = Path(spec).expanduser()
    if path.exists():
        return path.resolve()

    # Try relative path from cwd
    rel_path = Path.cwd() / spec
    if rel_path.exists():
        return rel_path.resolve()

    return None


# =============================================================================
# Project Config Operations (.ucas/ucas.yaml)
# =============================================================================

def get_ucas_dir(project_root: Optional[Path] = None) -> Path:
    """Get .ucas directory path. If not provided, find from current directory."""
    if project_root:
        return project_root / UCAS_DIR

    # Find .ucas from current directory
    cwd = Path.cwd()
    while cwd != cwd.parent:
        ucas_dir = cwd / UCAS_DIR
        if ucas_dir.exists():
            return ucas_dir
        cwd = cwd.parent

    # Check current dir as fallback
    ucas_dir = Path.cwd() / UCAS_DIR
    if ucas_dir.exists():
        return ucas_dir

    return None


def load_project_config(project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load ucas.yaml from project .ucas directory."""
    ucas_dir = get_ucas_dir(project_root)
    if not ucas_dir:
        return {}

    config_file = ucas_dir / PROJECT_CONFIG_FILE
    if not config_file.exists():
        return {}

    try:
        return load_yaml(str(config_file))
    except Exception as e:
        print(f"Warning: Failed to load project config: {e}", file=sys.stderr)
        return {}


def save_project_config(project_root: Path, config: Dict[str, Any]) -> None:
    """Save ucas.yaml to project .ucas directory."""
    ucas_dir = project_root / UCAS_DIR
    ucas_dir.mkdir(parents=True, exist_ok=True)
    config_file = ucas_dir / PROJECT_CONFIG_FILE

    try:
        save_yaml(str(config_file), config_file)
    except Exception as e:
        raise RuntimeError(f"Failed to save project config: {e}")


def get_team_started(project_root: Optional[Path] = None) -> str:
    """Get team_started value from project config."""
    config = load_project_config(project_root)
    return config.get("team_started", "NONE")


def set_team_started(project_root: Path, team: str) -> None:
    """Set team_started value in project config."""
    config = load_project_config(project_root)
    config["team_started"] = team
    save_project_config(project_root, config)


# =============================================================================
# Tag Operations
# =============================================================================

def parse_tags(tags: List) -> List[Union[str, Dict[str, str]]]:
    """
    Parse tags list. Tags can be:
    - string (e.g., "dev")
    - dict with name and team (e.g., {"name": "review", "team": "analytic"})
    Returns normalized list.
    """
    parsed = []
    for tag in tags:
        if isinstance(tag, dict):
            parsed.append(tag)
        elif isinstance(tag, str):
            parsed.append(tag)
    return parsed


def find_tag(tags: List, tag_name: str) -> Optional[Dict[str, str]]:
    """
    Find tag by name in tags list.
    Returns the tag dict if found (with team info), None otherwise.
    """
    for tag in tags:
        if isinstance(tag, dict) and tag.get("name") == tag_name:
            return tag
        elif tag == tag_name:
            return tag
    return None


def get_team_for_tag(tags: List, tag_name: str) -> str:
    """
    Get team name for a given tag.
    Returns the team name if tag has one, otherwise "DEFAULT".
    """
    tag = find_tag(tags, tag_name)
    if tag and isinstance(tag, dict):
        return tag.get("team", "DEFAULT")
    return "DEFAULT"


def project_has_tag(project_path: Path, tag_name: str) -> bool:
    """Check if project has a specific tag."""
    config = load_project_config(project_path)
    tags = config.get("tags", [])
    parsed = parse_tags(tags)
    return find_tag(parsed, tag_name) is not None


def project_matches_any_tag(project_path: Path, tag_names: List[str]) -> bool:
    """Check if project has any of the given tags."""
    config = load_project_config(project_path)
    tags = config.get("tags", [])
    parsed = parse_tags(tags)

    for tag_name in tag_names:
        if find_tag(parsed, tag_name):
            return True
    return False


# =============================================================================
# Team Operations
# =============================================================================

def get_default_team(project_root: Path) -> Optional[str]:
    """
    Get the default team name for a project.
    First tries to find a team named DEFAULT, otherwise returns first team.
    """
    config = load_project_config(project_root)
    team_block = config.get("team", {})

    if "DEFAULT" in team_block:
        return "DEFAULT"

    # Return first team if available
    agents = team_block.get("agents", {})
    if agents:
        return "DEFAULT"  # Default team name

    return None


def get_team_agents(project_root: Path, team_name: str) -> List[str]:
    """
    Get list of agents in a team.
    Returns empty list if team not found.
    """
    config = load_project_config(project_root)

    # Check in team block
    team_block = config.get("team", {})
    if team_name in team_block:
        # It's a team definition
        team_def = team_block[team_name]
        if isinstance(team_def, dict):
            agents = team_def.get("agents", {})
            return list(agents.keys())

    # Check for top-level team.agents structure
    if team_name == "DEFAULT" and "agents" in team_block:
        agents = team_block["agents"]
        return list(agents.keys())

    return []


# =============================================================================
# Project Listing
# =============================================================================

def build_project_list(include_all_info: bool = True) -> List[Dict[str, Any]]:
    """
    Build full project list from registry.
    If include_all_info is True, also loads description, tags, team info from project configs.
    """
    registry = load_registry()
    projects = []

    for project in registry.get("projects", []):
        project_info = {
            "alias": project["alias"],
            "path": project["path"]
        }

        if include_all_info:
            project_path = Path(project["path"])
            config = load_project_config(project_path)

            project_info["description"] = config.get("description", "")
            project_info["tags"] = config.get("tags", [])
            project_info["team_started"] = config.get("team_started", "NONE")

            # Get team agents if a team is started
            if project_info["team_started"] != "NONE":
                project_info["team_agents"] = get_team_agents(
                    project_path,
                    project_info["team_started"]
                )
            else:
                project_info["team_agents"] = []

        projects.append(project_info)

    return projects


def format_tags_for_display(tags: List) -> str:
    """Format tags list for display in table."""
    if not tags:
        return ""

    parts = []
    for tag in tags:
        if isinstance(tag, dict):
            name = tag.get("name", "")
            team = tag.get("team", "")
            if team:
                parts.append(f"{name}:{team}")
            else:
                parts.append(name)
        else:
            parts.append(str(tag))

    return f"[{','.join(parts)}]"


# =============================================================================
# Terminal Operations
# =============================================================================

def get_terminal_command() -> Optional[str]:
    """
    Get terminal command to use.
    Priority: xdg-terminal, x-terminal-emulator
    Returns None if no terminal found.
    """
    # Try xdg-terminal (primary)
    if shutil.which("xdg-terminal"):
        return "xdg-terminal"

    # Try x-terminal-emulator (fallback)
    if shutil.which("x-terminal-emulator"):
        return "x-terminal-emulator"

    return None


def open_terminal_in_path(path: Path) -> bool:
    """
    Open terminal in specified path.
    Returns True if successful, False otherwise.
    """
    term_cmd = get_terminal_command()
    if not term_cmd:
        print(f"Error: No terminal found. Please install xdg-terminal or x-terminal-emulator.",
              file=sys.stderr)
        return False

    path = path.expanduser().resolve()
    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        return False

    try:
        if term_cmd == "xdg-terminal":
            subprocess.Popen([term_cmd, "--working-directory", str(path)])
        else:
            subprocess.Popen([term_cmd], cwd=str(path))
        return True
    except Exception as e:
        print(f"Error: Failed to open terminal: {e}", file=sys.stderr)
        return False


# =============================================================================
# Initialization Operations
# =============================================================================

def generate_default_config(description: str = "", tags: Optional[List] = None) -> Dict[str, Any]:
    """Generate default ucas.yaml configuration for new project."""
    if tags is None:
        tags = [{"name": "autostart", "team": "DEFAULT"}]

    return {
        "description": description,
        "tags": tags,
        "team_started": "NONE",
        "team": {
            "agents": {
                "assistant": {
                    "mods": ["basic-chat"]
                }
            }
        }
    }


def get_gitignore_content(strategy: str) -> str:
    """
    Generate .ucas/.gitignore content based on strategy.
    Strategy can be: "all", "selective", or "none"
    """
    if strategy == "all":
        return "# Ignore entire .ucas/ directory\n"
    elif strategy == "selective":
        return """# Ignore mail storage
mails/
.mails/

# Ignore notes
notes/

# Keep config
!.gitignore
!ucas.yaml

# Ignore temporary files
tmp/

# Ignore mods (optional)
# mods/
"""
    elif strategy == "none":
        return ""
    else:
        raise ValueError(f"Unknown gitignore strategy: {strategy}")


# =============================================================================
# Command Handlers
# =============================================================================

def initialize_project(interactive: bool = True) -> None:
    """Initialize UCAS project in current directory."""
    cwd = Path.cwd()
    ucas_dir = cwd / UCAS_DIR
    alias = cwd.name

    print(f"Initializing UCAS project in: {cwd}")

    # Check if already initialized
    if ucas_dir.exists():
        existing_config = load_project_config(cwd)

        # Check what's missing
        missing_fields = []
        if "description" not in existing_config:
            missing_fields.append("description")
        if "tags" not in existing_config:
            missing_fields.append("tags")
        if "team_started" not in existing_config:
            missing_fields.append("team_started")
        if "team" not in existing_config:
            missing_fields.append("team")

        if missing_fields:
            print(f"\nProject already initialized (found .ucas/ directory)")
            if interactive:
                if input("Upgrade/fix configuration? (y/N): ").strip().lower() == 'y':
                    upgrade_project_config(cwd, existing_config, missing_fields)
            else:
                print("Use 'ucas init' interactively to upgrade.")
        else:
            print("Project already initialized. Everything looks good.")
        return

    # Interactive initialization
    description = ""
    gitignore_strategy = "all"
    open_editor = False

    if interactive:
        # 1. Description
        desc_input = input("Enter project description (optional, press Enter to skip): ").strip()
        if desc_input:
            description = desc_input

        # 2. Gitignore strategy
        print("\nGitignore strategy:")
        print("  A) Ignore all .ucas/ (simple)")
        print("  B) Ignore only mails/ and notes/ (commit config)")
        print("  C) No gitignore")
        git_choice = input("Choose strategy (A/B/C) [default: A]: ").strip().upper() or "A"

        if git_choice == "B":
            gitignore_strategy = "selective"
        elif git_choice == "C":
            gitignore_strategy = "none"
        elif git_choice != "A":
            print("Invalid choice, using default (A)")
            gitignore_strategy = "all"

        # 3. Open editor
        editor_choice = input("\nOpen ucas.yaml in editor? (y/N): ").strip().lower()
        open_editor = editor_choice == 'y'
    else:
        print("Non-interactive mode: using defaults")

    # Create .ucas directory
    ucas_dir.mkdir(exist_ok=True)

    # Generate default config
    config = generate_default_config(description=description)
    save_project_config(cwd, config)
    print(f"Created {ucas_dir / PROJECT_CONFIG_FILE}")

    # Create gitignore
    if gitignore_strategy != "none":
        gitignore_content = get_gitignore_content(gitignore_strategy)
        gitignore_file = ucas_dir / ".gitignore"
        gitignore_file.write_text(gitignore_content)
        print(f"Created {gitignore_file}")

    # Register project
    try:
        register_project(cwd, alias)
        print(f"Registered project as '{alias}'")
    except ValueError as e:
        # Alias conflict - suggest alternative
        suggested_alias = f"{alias}-2"
        if interactive:
            alt_choice = input(f"Alias conflict: {e}\nUse '{suggested_alias}' instead? (y/N): ").strip().lower()
            if alt_choice == 'y':
                register_project(cwd, suggested_alias)
                alias = suggested_alias
                print(f"Registered project as '{alias}'")
            else:
                print("Project not registered. You can register manually later.")
        else:
            print(f"Warning: {e}")
            print("Project not registered.")

    # Open editor if requested
    if open_editor:
        editor = os.environ.get("EDITOR", "vim")
        config_file = ucas_dir / PROJECT_CONFIG_FILE
        print(f"Opening {config_file} in {editor}...")
        try:
            subprocess.call([editor, str(config_file)])
        except Exception as e:
            print(f"Warning: Failed to open editor: {e}", file=sys.stderr)

    print(f"\nUCAS project initialized successfully!")
    print(f"  Alias: {alias}")
    print(f"  Config: {ucas_dir / PROJECT_CONFIG_FILE}")


def upgrade_project_config(project_root: Path, existing_config: Dict[str, Any], missing_fields: List[str]) -> None:
    """Upgrade existing project configuration with missing fields."""
    print("\nUpgrading configuration...")

    # Add default values for missing fields
    if "description" in missing_fields:
        desc = input("Enter project description (optional, press Enter to skip): ").strip()
        existing_config["description"] = desc

    if "tags" in missing_fields:
        print("\nTags can categorize your project and enable autostart.")
        use_autostart = input("Add autostart tag? (y/N): ").strip().lower() == 'y'
        if use_autostart:
            existing_config["tags"] = [{"name": "autostart", "team": "DEFAULT"}]
        else:
            existing_config["tags"] = []

    if "team_started" in missing_fields:
        existing_config["team_started"] = "NONE"

    if "team" in missing_fields:
        create_default_team = input("Create DEFAULT team with assistant agent? (y/N): ").strip().lower() == 'y'
        if create_default_team:
            existing_config["team"] = {
                "agents": {
                    "assistant": {
                        "mods": ["basic-chat"]
                    }
                }
            }
        else:
            existing_config["team"] = {}

    save_project_config(project_root, existing_config)
    print("Configuration upgraded.")


def list_projects(json_output: bool = False, running_only: bool = False, show_agents: bool = False) -> None:
    """List all registered projects."""
    projects = build_project_list(include_all_info=True)

    # Filter running projects if requested
    if running_only:
        projects = [p for p in projects if p.get("team_started", "NONE") != "NONE"]

    if json_output:
        print_json_projects(projects)
    else:
        print_table_projects(projects, show_agents)


def print_json_projects(projects: List[Dict[str, Any]]) -> None:
    """Print projects as JSON."""
    import json
    print(json.dumps({"projects": projects}, indent=2, ensure_ascii=False))


def print_table_projects(projects: List[Dict[str, Any]], show_agents: bool = False) -> None:
    """Print projects as formatted table."""
    if not projects:
        print("No projects found.")
        print("\nUse 'ucas init' to initialize a project.")
        return

    # Column widths
    alias_width = 15
    path_width = 40
    desc_width = 25
    tags_width = 25
    team_width = 15
    agents_width = 30 if show_agents else 0

    # Header
    header = f"{'ALIAS':<{alias_width}} {'PATH':<{path_width}} {'DESCRIPTION':<{desc_width}} {'TAGS':<{tags_width}} {'TEAM':<{team_width}}"
    if show_agents:
        header += f" {'AGENTS':<{agents_width}}"

    print(header)
    print("-" * len(header))

    # Rows
    for proj in projects:
        alias = proj.get("alias", "")
        path = proj.get("path", "")

        # Truncate path
        if len(path) > path_width:
            path = "..." + path[-(path_width-3):]

        description = proj.get("description", "")
        if len(description) > desc_width:
            description = description[:desc_width-3] + "..."

        tags_str = format_tags_for_display(proj.get("tags", []))
        if len(tags_str) > tags_width:
            tags_str = tags_str[:tags_width-3] + "..."

        team_started = proj.get("team_started", "NONE")
        team_display = "-" if team_started == "NONE" else team_started

        row = f"{alias:<{alias_width}} {path:<{path_width}} {description:<{desc_width}} {tags_str:<{tags_width}} {team_display:<{team_width}}"

        if show_agents:
            agents = proj.get("team_agents", [])
            agents_str = ", ".join(agents)
            if len(agents_str) > agents_width:
                agents_str = agents_str[:agents_width-3] + "..."
            row += f" {agents_str:<{agents_width}}"

        print(row)


def handle_term_command(project_spec: str) -> None:
    """Handle 'ucas term' command."""
    # Resolve project
    project_path = resolve_project(project_spec)
    if not project_path:
        print(f"Error: Project '{project_spec}' not found.", file=sys.stderr)
        print("Use 'ucas list' to see registered projects.", file=sys.stderr)
        sys.exit(1)

    # Open terminal
    if open_terminal_in_path(project_path):
        print(f"Opened terminal in: {project_path}")
    else:
        sys.exit(1)


def handle_autostart_command(tag_names: List[str]) -> None:
    """Handle 'ucas autostart' command."""
    projects = build_project_list(include_all_info=True)

    # Filter projects with matching tags
    matching_projects = []
    for proj in projects:
        project_path = Path(proj["path"])
        if project_matches_any_tag(project_path, tag_names):
            matching_projects.append(proj)

    if not matching_projects:
        print(f"No projects found with tags: {', '.join(tag_names)}")
        return

    print(f"Starting projects with tags: {', '.join(tag_names)}")
    print("-" * 60)

    for proj in matching_projects:
        project_path = Path(proj["path"])
        alias = proj.get("alias", project_path.name)

        # Find matching tag and determine team
        tags = proj.get("tags", [])
        parsed_tags = parse_tags(tags)
        team_to_run = "DEFAULT"

        for tag_name in tag_names:
            tag = find_tag(parsed_tags, tag_name)
            if tag and isinstance(tag, dict):
                team_to_run = tag.get("team", "DEFAULT")
                print(f"  {alias}: tag '{tag_name}' → team '{team_to_run}'")
                break

        # Start team
        print(f"  → Starting team '{team_to_run}' in {alias}...")

        # Change to project directory and run team
        try:
            import os
            original_cwd = os.getcwd()
            os.chdir(str(project_path))

            # Import team module and run
            from . import team as team_module
            team_args = type('obj', (object,), {
                'team_command': 'run',
                'team': team_to_run,
                'mods': []
            })
            team_module.handle_team_command(team_args)

            os.chdir(original_cwd)

            # Update team_started
            set_team_started(project_path, team_to_run)

        except Exception as e:
            print(f"  Error: Failed to start team: {e}", file=sys.stderr)

    print("\nDone.")
