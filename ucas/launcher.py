"""
Command building and tmux execution.
"""

import os
import sys
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class LaunchError(Exception):
    """Error during command launch."""
    pass


def select_acli(merged_config: Dict[str, Any], debug: bool = False) -> str:
    """
    Select ACLI based on Section 6 of spec:
    1. override_acli → veto power (from override files)
    2. executable already in config? (ACLI definition itself)
    3. Agent's default_acli in allowed_acli?
    4. User/project default_acli
    5. Fallback: first allowed_acli
    """
    # 1. Check override_acli (veto power)
    if 'override_acli' in merged_config:
        acli = merged_config['override_acli']
        if debug:
            print(f"[ACLI] Using override_acli: {acli}", file=sys.stderr)
        return acli

    # 2. Check if executable exists (this IS an ACLI)
    if 'executable' in merged_config:
        acli = merged_config.get('name', 'unknown')
        if debug:
            print(f"[ACLI] This is an ACLI definition: {acli}", file=sys.stderr)
        return acli

    # 3. Check agent's default_acli
    agent_default = merged_config.get('default_acli')
    allowed = merged_config.get('allowed_acli', [])

    if agent_default and agent_default in allowed:
        if debug:
            print(f"[ACLI] Using agent's default_acli: {agent_default}", file=sys.stderr)
        return agent_default

    # 4. Use first allowed_acli
    if allowed:
        acli = allowed[0]
        if debug:
            print(f"[ACLI] Using first allowed_acli: {acli}", file=sys.stderr)
        return acli

    raise LaunchError("No ACLI found: no override_acli, default_acli, or allowed_acli")


def translate_model(requested_model: Optional[str], acli_config: Dict[str, Any], debug: bool = False) -> Optional[str]:
    """
    Translate agent's requested_model using ACLI's model_mapping.

    Logic:
    1. Check if requested_model exists in model_mapping
    2. If not found, use model_mapping["default"] if exists
    3. If no mapping and no default:
       - ignore_unknown: false (or missing) → FATAL ERROR
       - ignore_unknown: true → return None (skip model flag) + WARNING
    """
    if not requested_model:
        return None

    model_mapping = acli_config.get('model_mapping', {})
    ignore_unknown = acli_config.get('ignore_unknown', False)

    # Check direct mapping
    if requested_model in model_mapping:
        translated = model_mapping[requested_model]
        if debug:
            print(f"[MODEL] Translated {requested_model} → {translated}", file=sys.stderr)
        return translated

    # Check default mapping
    if 'default' in model_mapping:
        translated = model_mapping['default']
        if debug:
            print(f"[MODEL] Using default mapping for {requested_model} → {translated}", file=sys.stderr)
        return translated

    # No mapping found
    if not ignore_unknown:
        raise LaunchError(
            f"Model '{requested_model}' not found in ACLI model_mapping and no default provided. "
            f"Available models: {list(model_mapping.keys())}"
        )
    else:
        print(f"[WARNING] Model '{requested_model}' not found in ACLI model_mapping. "
              f"Skipping model flag (ignore_unknown=true).", file=sys.stderr)
        return None


def build_command(
    agent_path: Path,
    mod_paths: List[Path],
    merged_config: Dict[str, Any],
    acli_config: Dict[str, Any],
    skills_dirs: List[Path],
    debug: bool = False
) -> str:
    """
    Build command string by substituting into ACLI's arg_mapping.
    """
    executable = acli_config.get('executable')
    if not executable:
        raise LaunchError("ACLI config missing 'executable' field")

    arg_mapping = acli_config.get('arg_mapping', {})

    # Start with executable
    cmd_parts = [executable]

    # Generate merged prompt file
    prompt_file = generate_prompt(agent_path, mod_paths, merged_config, debug)

    # Add prompt_file argument
    if 'prompt_file' in arg_mapping and prompt_file:
        cmd_parts.append(arg_mapping['prompt_file'])
        cmd_parts.append(str(prompt_file))

    # Add model argument (if requested and mapped)
    requested_model = merged_config.get('requested_model')
    if requested_model:
        translated_model = translate_model(requested_model, acli_config, debug)
        if translated_model and 'model_flag' in arg_mapping:
            cmd_parts.append(arg_mapping['model_flag'])
            cmd_parts.append(translated_model)

    # Add skills arguments
    if skills_dirs and 'skills_dir' in arg_mapping:
        for skills_dir in skills_dirs:
            cmd_parts.append(arg_mapping['skills_dir'])
            cmd_parts.append(str(skills_dir))

    return ' '.join(shlex.quote(p) for p in cmd_parts)


def generate_prompt(
    agent_path: Path,
    mod_paths: List[Path],
    merged_config: Dict[str, Any],
    debug: bool = False
) -> Optional[Path]:
    """
    Concatenate PROMPT.md files: agent → mod1 → mod2 ...
    Save to .ucas/tmp/<agent>.merged.md
    """
    # Collect prompt files
    prompt_parts = []

    agent_prompt = agent_path / 'PROMPT.md'
    if agent_prompt.exists():
        prompt_parts.append((f"Agent: {agent_path.name}", agent_prompt.read_text()))

    for mod_path in mod_paths:
        mod_prompt = mod_path / 'PROMPT.md'
        if mod_prompt.exists():
            prompt_parts.append((f"Mod: {mod_path.name}", mod_prompt.read_text()))

    if not prompt_parts:
        return None

    # Concatenate with separators
    merged_content = ""
    for i, (source, content) in enumerate(prompt_parts):
        if i > 0:
            merged_content += "\n\n---\n\n"
        if debug:
            merged_content += f"# {source}\n\n"
        merged_content += content

    # Save to .ucas/tmp/
    tmp_dir = Path.cwd() / '.ucas' / 'tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)

    output_file = tmp_dir / f"{agent_path.name}.merged.md"
    output_file.write_text(merged_content)

    if debug:
        print(f"[PROMPT] Generated merged prompt: {output_file}", file=sys.stderr)

    return output_file


def run_tmux(command: str, name: str, debug: bool = False) -> None:
    """
    Execute command in a new tmux window.
    """
    # Verify tmux exists
    if not shutil.which('tmux'):
        raise LaunchError("tmux not found. Please install tmux to run agents.")

    # Create window name with timestamp to avoid collisions
    timestamp = datetime.now().strftime("%H%M%S")
    window_name = f"{name}-{timestamp}"

    # Create new tmux window
    tmux_cmd = [
        'tmux', 'new-window',
        '-n', window_name,
        command
    ]

    if debug:
        print(f"[TMUX] Running: {' '.join(tmux_cmd)}", file=sys.stderr)

    try:
        subprocess.run(tmux_cmd, check=True)
        print(f"✓ Launched '{name}' in tmux window: {window_name}")
    except subprocess.CalledProcessError as e:
        raise LaunchError(f"Failed to create tmux window: {e}")
