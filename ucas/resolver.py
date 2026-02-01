"""
Entity resolution across Project → User → System layers.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from .yaml_parser import parse_yaml


def get_search_paths(extra_paths: Optional[List[str]] = None, strict: bool = False) -> List[Path]:
    """
    Get search paths in order: 
    1. Project default: ./.ucas/mods/
    2. Extra paths from configs: mod_path: []
    3. User layer: ~/.ucas/mods/ (unless strict)
    4. System layer: $UCAS_HOME/mods/ (unless strict)
    """
    paths = []

    # 1. Project layer: ./.ucas/mods/ (ALWAYS FIRST)
    project_path = Path.cwd() / '.ucas' / 'mods'
    if project_path.exists():
        paths.append(project_path)

    # 2. Extra paths from configs
    if extra_paths:
        for p in extra_paths:
            path = Path(p)
            if not path.is_absolute():
                # Relative to CWD (Project Root)
                path = Path.cwd() / path
            if path.exists() and path.is_dir():
                if path not in paths:
                    paths.append(path)

    if not strict:
        # 3. User layer: ~/.ucas/mods/
        user_path = Path.home() / '.ucas' / 'mods'
        if user_path.exists():
            if user_path not in paths:
                paths.append(user_path)

        # 4. System layer: $UCAS_HOME/mods/ or package location
        ucas_home = os.environ.get('UCAS_HOME')
        if not ucas_home:
            # Default to package installation directory
            package_dir = Path(__file__).parent.parent
            ucas_home = str(package_dir)

        system_path = Path(ucas_home) / 'mods'
        if system_path.exists():
            if system_path not in paths:
                paths.append(system_path)

    return paths


def find_entity(name: str, search_paths: Optional[List[Path]] = None) -> Optional[Path]:
    """
    Find an entity (agent/mod/ACLI/team) across layers.
    Returns path to entity directory or None.
    First match wins.
    """
    # Validate entity name - no spaces allowed
    if ' ' in name:
        raise ValueError(f"Entity name '{name}' contains spaces. Entity names must not contain spaces.")
    
    if search_paths is None:
        search_paths = get_search_paths()

    for base_path in search_paths:
        entity_path = base_path / name
        if entity_path.exists() and entity_path.is_dir():
            # Check if ucas.yaml exists
            config_file = entity_path / 'ucas.yaml'
            if config_file.exists():
                return entity_path

    return None


def is_acli(entity_path: Path) -> bool:
    """Check if entity is an ACLI (has 'executable' key in config)."""
    config_file = entity_path / 'ucas.yaml'
    if not config_file.exists():
        return False

    try:
        config = parse_yaml(config_file.read_text())
        # Support both nested 'acli: { executable: ... }' and flat 'executable: ...'
        return 'executable' in config or ('acli' in config and 'executable' in config.get('acli', {}))
    except Exception:
        return False


def is_run_mod(entity_path: Path) -> bool:
    """Check if entity is a run mod (has 'run' block)."""
    config_file = entity_path / 'ucas.yaml'
    if not config_file.exists():
        return False

    try:
        config = parse_yaml(config_file.read_text())
        return 'run' in config
    except Exception:
        return False


def get_acli_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract ACLI configuration, supporting both nested and flat structures."""
    if 'acli' in config:
        return config['acli']
    # Backward compatibility: return config itself if flat structure
    return config


def get_run_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract run configuration."""
    return config.get('run', {})


def load_config(entity_path: Path) -> dict:
    """Load ucas.yaml config from entity directory."""
    config_file = entity_path / 'ucas.yaml'
    if not config_file.exists():
        return {}

    try:
        return parse_yaml(config_file.read_text())
    except Exception as e:
        raise ValueError(f"Failed to parse {config_file}: {e}")


def get_layer_config_paths() -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """
    Get paths to layer config files (ucas.yaml and ucas-override.yaml).
    Returns: (system_paths, user_paths, project_paths)
    Each element is a tuple: (ucas.yaml, ucas-override.yaml)
    """
    system_config = None
    system_override = None
    user_config = None
    user_override = None
    project_config = None
    project_override = None

    # System layer
    ucas_home = os.environ.get('UCAS_HOME')
    if not ucas_home:
        # Default to package installation directory
        package_dir = Path(__file__).parent.parent
        ucas_home = str(package_dir)

    system_base = Path(ucas_home)
    sc = system_base / 'ucas.yaml'
    if sc.exists():
        system_config = sc
    so = system_base / 'ucas-override.yaml'
    if so.exists():
        system_override = so

    # User layer
    user_base = Path.home() / '.ucas'
    uc = user_base / 'ucas.yaml'
    if uc.exists():
        user_config = uc
    uo = user_base / 'ucas-override.yaml'
    if uo.exists():
        user_override = uo

    # Project layer
    project_base = Path.cwd() / '.ucas'
    pc = project_base / 'ucas.yaml'
    if pc.exists():
        project_config = pc
    po = project_base / 'ucas-override.yaml'
    if po.exists():
        project_override = po

    return (
        (system_config, system_override),
        (user_config, user_override),
        (project_config, project_override)
    )
