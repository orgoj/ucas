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
    try:
        config = load_config(entity_path)
        # Support suffixes like acli! or executable!
        keys = list(config.keys())
        has_exe = any(k.startswith('executable') for k in keys)
        if not has_exe and any(k.startswith('acli') for k in keys):
            # Check inside nested acli block
            acli_key = next(k for k in keys if k.startswith('acli'))
            acli_block = config[acli_key]
            if isinstance(acli_block, dict):
                has_exe = any(k.startswith('executable') for k in acli_block.keys())
        return has_exe
    except Exception:
        return False


def is_run_mod(entity_path: Path) -> bool:
    """Check if entity is a run mod (has 'run' block)."""
    try:
        config = load_config(entity_path)
        return any(k.startswith('run') for k in config.keys())
    except Exception:
        return False


def get_acli_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract ACLI configuration, supporting suffixes and flattening arg_mapping."""
    acli_block = {}
    found = False
    for k in config:
        if k.startswith('acli') and (len(k) == 4 or k[4] in ('+', '-', '!', '?', '~')):
            acli_block = config[k]
            found = True
            break
    
    if not found:
        # If no acli block, use the config itself as potential ACLI def
        acli_block = config

    if not isinstance(acli_block, dict):
        return {}

    # Flatten arg_mapping for backward compatibility
    if 'arg_mapping' in acli_block:
        mapping = acli_block['arg_mapping']
        if isinstance(mapping, dict):
            acli_block = acli_block.copy()
            for k, v in mapping.items():
                if k not in acli_block:
                    acli_block[k] = v
    
    return acli_block


def get_run_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract run configuration, supporting suffixes."""
    for k in config:
        if k.startswith('run') and (len(k) == 3 or k[3] in ('+', '-', '!', '?', '~')):
            return config[k]
    
    # Fallback if it looks like a runner (must have script or template)
    # We avoid 'executable' fallback here because it's ambiguous with ACLIs
    if any(k in config for k in ('script', 'template')):
        return config

    return {}


def load_config_file(config_file: Path) -> dict:
    """Load a config file with __DIR__ replacement."""
    if not config_file.exists():
        return {}

    try:
        text = config_file.read_text()
        # KISS: Replace __DIR__ with absolute path before parsing
        text = text.replace("__DIR__", str(config_file.parent.resolve()))
        return parse_yaml(text)
    except Exception as e:
        raise ValueError(f"Failed to parse {config_file}: {e}")


def load_config(entity_path: Path) -> dict:
    """Load ucas.yaml config from entity directory with __DIR__ replacement."""
    return load_config_file(entity_path / 'ucas.yaml')


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
