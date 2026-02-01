"""
Sandwich merge logic: System → Agent → Mods → Overrides.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

from .yaml_parser import parse_yaml
from .resolver import get_layer_config_paths, load_config


def merge_configs(
    agent_path: Path,
    mod_paths: List[Path],
    debug: bool = False
) -> Dict[str, Any]:
    """
    Perform 11-layer sandwich merge.

    Merge order:
    1. $UCAS_HOME/ucas.yaml        # System defaults
    2. ~/.ucas/ucas.yaml           # User defaults
    3. ./.ucas/ucas.yaml           # Project defaults
    4. agent/ucas.yaml             # Main agent
    5-N. mod/ucas.yaml             # Mods in CLI order
    ─────────────────────────────────
    N+1. $UCAS_HOME/ucas-override.yaml  # System veto
    N+2. ~/.ucas/ucas-override.yaml     # User veto
    N+3. ./.ucas/ucas-override.yaml     # Project veto (strongest)
    """
    result = {}

    # Get layer config paths
    (sys_cfg, sys_ovr), (usr_cfg, usr_ovr), (prj_cfg, prj_ovr) = get_layer_config_paths()

    # Layer 1-3: Default configs
    layers = []

    if sys_cfg:
        layers.append(('System defaults', sys_cfg))
    if usr_cfg:
        layers.append(('User defaults', usr_cfg))
    if prj_cfg:
        layers.append(('Project defaults', prj_cfg))

    # Layer 4: Agent config
    agent_config = agent_path / 'ucas.yaml'
    if agent_config.exists():
        layers.append((f'Agent: {agent_path.name}', agent_config))

    # Layer 5-N: Mod configs
    for mod_path in mod_paths:
        mod_config = mod_path / 'ucas.yaml'
        if mod_config.exists():
            layers.append((f'Mod: {mod_path.name}', mod_config))

    # Apply bottom layers
    for layer_name, config_path in layers:
        if debug:
            print(f"[MERGE] Loading {layer_name}: {config_path}", file=sys.stderr)
        config = parse_yaml(config_path.read_text())
        result = _merge_dicts(result, config, debug, layer_name)

    # Layer N+1 to N+3: Override configs (veto power)
    override_layers = []
    if sys_ovr:
        override_layers.append(('System override', sys_ovr))
    if usr_ovr:
        override_layers.append(('User override', usr_ovr))
    if prj_ovr:
        override_layers.append(('Project override', prj_ovr))

    for layer_name, config_path in override_layers:
        if debug:
            print(f"[MERGE] Loading {layer_name}: {config_path}", file=sys.stderr)
        config = parse_yaml(config_path.read_text())
        result = _merge_dicts(result, config, debug, layer_name)

    return result


def _merge_dicts(base: Dict[str, Any], overlay: Dict[str, Any], debug: bool, layer_name: str) -> Dict[str, Any]:
    """
    Merge two dicts using suffix-based strategies:
    - key+: Merge/Append (recursive for dicts, concatenate for lists)
    - key-: Remove (remove from list or delete from dict)
    - key!: Override (force replacement)
    - key?: Default (only set if missing in base)
    - key~: Update (only set if already exists in base)
    - key: Default merge (deep for dicts, last-wins for others)
    """
    result = base.copy()

    for raw_key, value in overlay.items():
        # Identify strategy from suffix
        strategy = ""
        key = raw_key
        if raw_key.endswith(("+", "-", "!", "?", "~")):
            strategy = raw_key[-1]
            key = raw_key[:-1]

        # Handle specialized keys (legacy compat/shortcuts)
        if key in ('skills', 'mods') and not strategy:
            strategy = '+'  # Skills and mods always append by default
        elif key == 'hooks' and not strategy:
            strategy = '+'  # Hooks always append by default

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
                    # Remove items from list
                    result[key] = [item for item in result[key] if item not in value]
                elif isinstance(result[key], dict):
                    # Remove keys from dict
                    if isinstance(value, list):
                        for k in value:
                            result[key].pop(k, None)
                    elif isinstance(value, dict):
                        for k in value:
                            result[key].pop(k, None)
                else:
                    # Scalar removal (delete key)
                    result.pop(key, None)
        elif strategy == '+':  # MERGE / APPEND
            if key in result:
                if isinstance(result[key], list) and isinstance(value, list):
                    result[key] = result[key] + value
                elif isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = _merge_dicts(result[key], value, debug, f"{layer_name}.{key}")
                else:
                    # Fallback to overwrite if types conflict
                    result[key] = value
            else:
                result[key] = value
        else:  # DEFAULT MERGE Logic
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                # Recursively merge dicts by default
                result[key] = _merge_dicts(result.get(key, {}), value, debug, f"{layer_name}.{key}")
            else:
                # Last wins for other types
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
