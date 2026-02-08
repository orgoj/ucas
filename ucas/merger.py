"""
Sandwich merge logic: System → Defaults Mods → Agent → Explicit Mods → Overrides.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import sys

from .exceptions import MergerError
from . import settings
from .resolver import get_layer_config_paths, load_config_file, get_search_paths, find_entity, load_config


def merge_configs(
    agent_path: Path,
    default_mod_paths: List[Path],
    explicit_mod_paths: List[Path]
) -> Dict[str, Any]:
    """
    Perform multi-layer sandwich merge with correct priorities.
    """
    result = {}

    # Get layer config paths
    (sys_cfg, sys_ovr), (usr_cfg, usr_ovr), (prj_cfg, prj_ovr) = get_layer_config_paths()

    # 1. Base configs (System -> User -> Project)
    base_layers = []
    if sys_cfg: base_layers.append(('System defaults', sys_cfg))
    if usr_cfg: base_layers.append(('User defaults', usr_cfg))
    if prj_cfg: base_layers.append(('Project defaults', prj_cfg))

    for layer_name, config_path in base_layers:
        config = load_config_file(config_path)
        result = _merge_dicts(result, config, settings.DEBUG, layer_name)

    # 2. Default Mods (those from base configs)
    for mod_path in default_mod_paths:
        mod_config = mod_path / 'ucas.yaml'
        if mod_config.exists():
            if settings.VERBOSE or settings.DEBUG:
                print(f"[MERGE] Loading Default Mod: {mod_path.name}: {mod_config}", file=sys.stderr)
            config = load_config_file(mod_config)
            result = _merge_dicts(result, config, settings.DEBUG, f'Default Mod: {mod_path.name}')

    # 3. Agent config (can override base defaults and default mods)
    agent_config = agent_path / 'ucas.yaml'
    if agent_config.exists():
        if settings.VERBOSE or settings.DEBUG:
            print(f"[MERGE] Loading Agent: {agent_path.name}: {agent_config}", file=sys.stderr)
        config = load_config_file(agent_config)
        result = _merge_dicts(result, config, settings.DEBUG, f'Agent: {agent_path.name}')

    # 4. Explicit mods (from CLI or team definition) - highest priority mod
    for mod_path in explicit_mod_paths:
        mod_config = mod_path / 'ucas.yaml'
        if mod_config.exists():
            if settings.VERBOSE or settings.DEBUG:
                print(f"[MERGE] Loading Mod: {mod_path.name}: {mod_config}", file=sys.stderr)
            config = load_config_file(mod_config)
            result = _merge_dicts(result, config, settings.DEBUG, f'Mod: {mod_path.name}')

    # 5. Overrides (System -> User -> Project) - final veto
    override_layers = []
    if sys_ovr: override_layers.append(('System override', sys_ovr))
    if usr_ovr: override_layers.append(('User override', usr_ovr))
    if prj_ovr: override_layers.append(('Project override', prj_ovr))

    for layer_name, config_path in override_layers:
        config = load_config_file(config_path)
        result = _merge_dicts(result, config, settings.DEBUG, layer_name)

    return result


def _merge_dicts(base: Dict[str, Any], overlay: Dict[str, Any], debug: bool, layer_name: str) -> Dict[str, Any]:
    """
    Merge two dicts using suffix-based strategies.
    """
    result = base.copy()

    for raw_key, value in overlay.items():
        # Identify strategy from suffix
        strategy = ""
        key = raw_key
        if raw_key.endswith(("+", "-", "!", "?", "~")):
            strategy = raw_key[-1]
            key = raw_key[:-1]

        # Apply strategy
        if strategy == '!':  # OVERRIDE
            result[key] = value
        elif strategy == '?':  # DEFAULT (Set if missing)
            if key not in result:
                result[key] = value
        elif strategy == '~':  # UPDATE (Set if exists)
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = _merge_dicts(result[key], value, debug, f"{layer_name}.{key}")
                else:
                    result[key] = value
        elif strategy == '-':  # REMOVE
            if key in result:
                if isinstance(result[key], list) and isinstance(value, list):
                    result[key] = [item for item in result[key] if item not in value]
                elif isinstance(result[key], dict):
                    if isinstance(value, list):
                        for k in value: result[key].pop(k, None)
                    elif isinstance(value, dict):
                        for k in value: result[key].pop(k, None)
                else:
                    result.pop(key, None)
        elif strategy == '+':  # MERGE / APPEND
            if key in result:
                if isinstance(result[key], list) and isinstance(value, list):
                    result[key] = result[key] + value
                elif isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = _merge_dicts(result[key], value, debug, f"{layer_name}.{key}")
                else:
                    result[key] = value
            else:
                result[key] = value
        else:  # DEFAULT MERGE Logic
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = _merge_dicts(result.get(key, {}), value, debug, f"{layer_name}.{key}")
            else:
                if debug and key in result:
                    print(f"  [MERGE] {layer_name} overwrites '{key}': {result[key]} → {value}", file=sys.stderr)
                result[key] = value

    return result


def collect_skills(agent_path: Path, mod_paths: List[Path]) -> List[Path]:
    """
    Collect all skills directories from agent and mods.
    Returns list of absolute paths to skills/ directories.
    """
    skills_dirs = []

    # Agent skills
    agent_skills = agent_path / 'skills'
    if agent_skills.exists() and agent_skills.is_dir():
        skills_dirs.append(agent_skills.resolve())

    # Mod skills
    for mod_path in mod_paths:
        mod_skills = mod_path / 'skills'
        if mod_skills.exists() and mod_skills.is_dir():
            skills_dirs.append(mod_skills.resolve())

    return skills_dirs


# MergerError is now in .exceptions


def resolve_entities(agent_name: str, mods: List[str]) -> Tuple[Path, List[Path], List[Path], Dict[str, Any]]:
    """Resolve agent and mods with dynamic search path expansion."""
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, load_config_file(cfg), settings.DEBUG, f"Base:{layer_name}")

    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    
    search_paths = get_search_paths(extra_paths, base_config.get('strict', False))
    
    # 1. Resolve Agent
    agent_path = find_entity(agent_name, search_paths)
    if not agent_path:
        raise MergerError(f"Agent '{agent_name}' not found")

    # Dynamic search path update from agent
    _update_search_paths(search_paths, agent_path)

    # 2. Resolve Mods sequentially, updating search paths after each
    mod_paths = []
    for mod_item in mods:
        mod_name = mod_item['name'] if isinstance(mod_item, dict) else mod_item
        m_path = find_entity(mod_name, search_paths)
        if not m_path:
            raise MergerError(f"Mod '{mod_name}' not found")
        mod_paths.append(m_path)
        
        _update_search_paths(search_paths, m_path)

    return agent_path, mod_paths, search_paths, base_config


def _update_search_paths(search_paths: List[Path], entity_path: Path):
    """Read entity config and prepend any mod_path to search_paths."""
    cfg = load_config(entity_path)
    new_paths = cfg.get('mod_path', [])
    if isinstance(new_paths, str):
        new_paths = [new_paths]
    
    for p in reversed(new_paths): # reversed so they keep order when prepending
        p_path = Path(p)
        if not p_path.is_absolute():
            p_path = (entity_path / p).resolve()
        
        if p_path.exists() and p_path.is_dir():
            if p_path not in search_paths:
                if settings.DEBUG: print(f"[RESOLVER] Adding dynamic search path: {p_path}", file=sys.stderr)
                search_paths.insert(0, p_path)
