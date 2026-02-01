"""
Command building and tmux execution.
"""

import os
import sys
import shlex
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .resolver import get_acli_config


class LaunchError(Exception):
    """Error during command launch."""
    pass


def prepare_context(
    agent_name: str, 
    agent_path: Path, 
    team_name: Optional[str] = None,
    team_index: int = 0,
    team_size: int = 1
) -> Dict[str, str]:
    """
    Prepare environment variables for mod execution.
    Creates UCAS_AGENT_NOTES directory.
    """
    project_root = Path.cwd().resolve()
    notes_dir = project_root / '.ucas' / 'notes' / agent_name
    notes_dir.mkdir(parents=True, exist_ok=True)

    # Generate a session ID if not provided (e.g. from parent team process)
    session_id = os.environ.get('UCAS_SESSION_ID')
    if not session_id:
        session_id = str(uuid.uuid4())

    context = {
        'UCAS_AGENT': agent_name,
        'UCAS_TEAM': team_name or '',
        'UCAS_TEAM_INDEX': str(team_index),
        'UCAS_TEAM_SIZE': str(team_size),
        'UCAS_AGENT_DIR': str(agent_path.resolve()),
        'UCAS_AGENT_NOTES': str(notes_dir.resolve()),
        'UCAS_PROJECT_ROOT': str(project_root),
        'UCAS_SESSION_ID': session_id
    }
    return context


def expand_session_template(template: str, context: Dict[str, str]) -> str:
    """
    Expand session path template with context variables.
    Supports: {uuid}, {agent}, {team}, {project_root}, $HOME, $VAR
    """
    replacements = {
        '{uuid}': context['UCAS_SESSION_ID'],
        '{agent}': context['UCAS_AGENT'],
        '{team}': context.get('UCAS_TEAM', ''),
        '{project_root}': context['UCAS_PROJECT_ROOT']
    }
    
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    # Expand environment variables like $HOME, $USER, etc.
    result = os.path.expandvars(result)
    
    # Expand ~ to home directory (if any remain after $HOME expansion)
    result = os.path.expanduser(result)
    
    # Make relative paths absolute (relative to project root) and normalize
    # Only if it looks like a path (starts with / or ./ or ../)
    if result.startswith(('/','./','../')):
        path = Path(result)
        if not path.is_absolute():
            path = Path(context['UCAS_PROJECT_ROOT']) / path
        result = str(path.resolve())
    
    return result


def get_context_export_str(context: Dict[str, str]) -> str:
    """Return a string of exports for shell injection. Skips empty values."""
    parts = []
    for k, v in context.items():
        if v:  # Skip empty strings
            parts.append(f"export {k}={shlex.quote(v)}")
    return ' && '.join(parts)


class HookRunner:
    """Runs lifecycle hooks with injected context."""
    def __init__(self, context: Dict[str, str], debug: bool = False):
        self.context = context
        self.debug = debug
        self.env = os.environ.copy()
        self.env.update(context)

    def run(self, hooks: Dict[str, Any], stage: str):
        """Run all commands for a given stage."""
        cmds = hooks.get(stage)
        if not cmds:
            return

        if isinstance(cmds, str):
            cmds = [cmds]

        for cmd in cmds:
            if self.debug:
                print(f"[HOOK] Running {stage}: {cmd}", file=sys.stderr)
            try:
                # Run in shell to support env var expansion and multiple commands
                subprocess.run(cmd, shell=True, env=self.env, check=True)
            except subprocess.CalledProcessError as e:
                raise LaunchError(f"Hook '{stage}' failed: {cmd} (exit code {e.returncode})")

def select_acli(merged_config: Dict[str, Any], debug: bool = False) -> str:
    """
    Select ACLI based on simplified logic:
    1. override_acli → veto power (from override files)
    2. Check if this IS an ACLI definition (has acli.name)
    3. Use first allowed_acli as default (single item = forced)
    
    allowed_acli list serves as:
    - Validation: selected ACLI must be in list
    - Default: first item is default
    - Force: single item forces that ACLI
    """
    # 1. Check override_acli (veto power)
    if 'override_acli' in merged_config:
        acli = merged_config['override_acli']
        if debug:
            print(f"[ACLI] Using override_acli: {acli}", file=sys.stderr)
        return acli

    # 2. Check if this IS an ACLI definition (has acli.name after merge)
    acli_def = merged_config.get('acli', {})
    if 'name' in acli_def:
        acli_name = acli_def['name']
        if debug:
            print(f"[ACLI] This is an ACLI definition: {acli_name}", file=sys.stderr)
        return acli_name

    # 3. Use first allowed_acli as default
    allowed = merged_config.get('allowed_acli', [])
    if allowed:
        acli = allowed[0]
        if debug:
            if len(allowed) == 1:
                print(f"[ACLI] Forced ACLI (only one in allowed list): {acli}", file=sys.stderr)
            else:
                print(f"[ACLI] Using default ACLI (first in allowed list): {acli}", file=sys.stderr)
        return acli

    raise LaunchError("No ACLI found: no override_acli, acli.name, or allowed_acli")


def select_run_mod(merged_config: Dict[str, Any], debug: bool = False) -> str:
    """
    Select run mod based on logic:
    1. override_run → veto power
    2. Check if this is a run-mod definition (has run.name)
    3. Use first allowed_run as default
    """
    if 'override_run' in merged_config:
        run_mod = merged_config['override_run']
        if debug:
            print(f"[RUN] Using override_run: {run_mod}", file=sys.stderr)
        return run_mod

    run_def = merged_config.get('run', {})
    if 'name' in run_def:
        run_name = run_def['name']
        if debug:
            print(f"[RUN] This is a run-mod definition: {run_name}", file=sys.stderr)
        return run_name

    allowed = merged_config.get('allowed_run', [])
    if allowed:
        run_mod = allowed[0]
        if debug:
            print(f"[RUN] Using default run-mod: {run_mod}", file=sys.stderr)
        return run_mod

    # Default fallback if nothing else is specified
    return "run-bash"


def translate_model(requested_model: Optional[str], acli_def: Dict[str, Any], debug: bool = False) -> Optional[str]:
    """
    Translate agent's requested_model using ACLI's model_mapping.
    acli_def should be the extracted ACLI configuration (already processed by get_acli_config).

    Logic:
    1. Check if requested_model exists in model_mapping
    2. If not found, use model_mapping["default"] if exists
    3. If no mapping and no default:
       - ignore_unknown: false (or missing) → FATAL ERROR
       - ignore_unknown: true → return None (skip model flag) + WARNING
    """
    if not requested_model:
        return None

    model_mapping = acli_def.get('model_mapping', {})
    ignore_unknown = acli_def.get('ignore_unknown', False)

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
    context: Dict[str, str],
    debug: bool = False
) -> str:
    """
    Build command string by substituting into ACLI's arg_mapping.
    acli_config should be the full config (will extract ACLI section internally).
    """
    # Extract ACLI configuration (supports nested and flat structures)
    acli_def = get_acli_config(acli_config)
    
    executable = acli_def.get('executable')
    if not executable:
        raise LaunchError("ACLI config missing 'executable' field")

    arg_mapping = acli_def.get('arg_mapping', {})

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
        translated_model = translate_model(requested_model, acli_def, debug)
        if translated_model and 'model_flag' in arg_mapping:
            cmd_parts.append(arg_mapping['model_flag'])
            cmd_parts.append(translated_model)

    # Add skills arguments
    if skills_dirs and 'skills_dir' in arg_mapping:
        for skills_dir in skills_dirs:
            cmd_parts.append(arg_mapping['skills_dir'])
            cmd_parts.append(str(skills_dir))
    
    # Handle session management: session_arg contains complete argument with template
    # Example: session_arg: --session "$HOME/.pi/sessions/{uuid}.json"
    if 'session_arg' in acli_def:
        session_template = acli_def['session_arg']
        # Expand template with context variables
        session_expanded = expand_session_template(session_template, context)
        
        # Create parent directory if path contains directory
        # Extract potential paths from the expanded string
        import re
        path_match = re.search(r'["\']?(/[^"\']*\.json)["\']?', session_expanded)
        if path_match:
            session_file = path_match.group(1)
            session_dir = os.path.dirname(session_file)
            if session_dir:
                os.makedirs(session_dir, exist_ok=True)
        
        # Add expanded argument to command
        # Note: session_arg can contain multiple parts like: --session "path"
        # We use shlex.split to properly handle quoted strings
        import shlex as shlex_module
        session_parts = shlex_module.split(session_expanded)
        cmd_parts.extend(session_parts)
        
        if debug:
            print(f"[SESSION] Session arg: {session_expanded}", file=sys.stderr)

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


def validate_runner(run_def: Dict[str, Any], context: Dict[str, str]) -> None:
    """Validate runner for team execution."""
    team_name = context.get('UCAS_TEAM')
    is_single = run_def.get('single', False)
    runner_name = run_def.get('name', 'unknown')
    
    if team_name and is_single:
        raise LaunchError(
            f"Runner '{runner_name}' is marked as 'single: true' and cannot be used for team execution. "
            f"Please use a multi-session runner like 'run-tmux'."
        )


def stop_runner(run_def: Dict[str, Any], context: Dict[str, str], run_dir: Path, dry_run: bool = False, debug: bool = False) -> None:
    """
    Execute stop command using run-mod definition.
    Supports: stop_script, stop_executable, stop_template.
    """
    # Create environment
    env = os.environ.copy()
    env.update(context)
    env['UCAS_RUN_DIR'] = str(run_dir.resolve())

    # Build command parts
    final_cmd_parts = []
    
    stop_script = run_def.get('stop_script')
    stop_executable = run_def.get('stop_executable')
    stop_template = run_def.get('stop_template')

    if stop_script:
        script_path = Path(stop_script)
        if not script_path.is_absolute():
            script_path = (run_dir / script_path).resolve()
            
        if script_path.suffix == '.py':
            final_cmd_parts = [sys.executable, str(script_path)]
        else:
            final_cmd_parts = [str(script_path)]
            
        # Append common data as CLI arguments (similar to run but without {cmd})
        final_cmd_parts.extend(get_run_args("", "stop", context))
    elif stop_executable:
        exe_path = Path(stop_executable)
        if not exe_path.is_absolute() and stop_executable.startswith('./'):
            exe_path = (run_dir / exe_path).resolve()
        
        final_cmd_parts = [str(exe_path)]
        final_cmd_parts.extend(get_run_args("", "stop", context))
    elif stop_template:
        # Lightweight shell template
        expanded_cmd = expand_run_template(stop_template, "", "stop", context)
        if dry_run:
            print(f"[DRY-RUN] Would run stop template: {expanded_cmd.strip()}")
            return
            
        try:
            subprocess.run(expanded_cmd, shell=True, check=True, env=env)
            return
        except subprocess.CalledProcessError as e:
            raise LaunchError(f"Stop template execution failed: {e}")
    else:
        # If no stop command is defined, it might not be a bug but just a "dumb" runner
        if debug:
            print(f"[RUN] No stop command defined for runner '{run_def.get('name')}'", file=sys.stderr)
        return

    if dry_run:
        print(f"[DRY-RUN] Would run stop: {' '.join(shlex.quote(p) for p in final_cmd_parts)}")
        return

    if debug:
        print(f"[EXEC] Running stop: {' '.join(shlex.quote(p) for p in final_cmd_parts)}", file=sys.stderr)

    try:
        subprocess.run(final_cmd_parts, check=True, env=env)
    except subprocess.CalledProcessError as e:
        raise LaunchError(f"Stop command execution failed: {e}")


def run_command(run_def: Dict[str, Any], cmd: str, member_name: str, context: Dict[str, str], run_dir: Path, debug: bool = False) -> None:
    """
    Execute final command using run-mod definition.
    Supports: script, executable, template.
    """
    # Validate runner (redundant check for safety)
    validate_runner(run_def, context)

    # Create environment
    env = os.environ.copy()
    env.update(context)
    env['UCAS_RUN_DIR'] = str(run_dir.resolve())

    # Build command parts
    final_cmd_parts = []
    
    script = run_def.get('script')
    executable = run_def.get('executable')
    template = run_def.get('template')

    if script:
        script_path = Path(script)
        if not script_path.is_absolute():
            script_path = (run_dir / script_path).resolve()
            
        if script_path.suffix == '.py':
            final_cmd_parts = [sys.executable, str(script_path)]
        else:
            final_cmd_parts = [str(script_path)]
            
        # Append data as CLI arguments
        final_cmd_parts.extend(get_run_args(cmd, member_name, context))
    elif executable:
        exe_path = Path(executable)
        if not exe_path.is_absolute() and executable.startswith('./'):
            exe_path = (run_dir / exe_path).resolve()
        
        final_cmd_parts = [str(exe_path)]
        final_cmd_parts.extend(get_run_args(cmd, member_name, context))
    elif template:
        # Lightweight shell template
        expanded_cmd = expand_run_template(template, cmd, member_name, context)
        if debug:
            print(f"[EXEC] Running template: {expanded_cmd}", file=sys.stderr)
        
        try:
            subprocess.run(expanded_cmd, shell=True, check=True, env=env)
            return
        except subprocess.CalledProcessError as e:
            raise LaunchError(f"Template execution failed: {e}")
    else:
        raise LaunchError("Run-mod definition missing 'script', 'executable', or 'template'")

    if debug:
        print(f"[EXEC] Running: {' '.join(shlex.quote(p) for p in final_cmd_parts)}", file=sys.stderr)

    try:
        subprocess.run(final_cmd_parts, check=True, env=env)
    except subprocess.CalledProcessError as e:
        raise LaunchError(f"Command execution failed: {e}")


def get_run_args(cmd: str, member_name: str, context: Dict[str, str]) -> List[str]:
    """Return common arguments for run-mod scripts."""
    project_root = Path(context['UCAS_PROJECT_ROOT'])
    team_name = context.get('UCAS_TEAM', '')
    
    session_name = project_root.name
    if team_name:
        session_name = f"{session_name}-{team_name}"
        
    timestamp = datetime.now().strftime("%H%M%S")
    window_name = f"{member_name}-{timestamp}"

    return [
        '--cmd', cmd,
        '--agent', context['UCAS_AGENT'],
        '--team', team_name,
        '--project-root', context['UCAS_PROJECT_ROOT'],
        '--session-id', context['UCAS_SESSION_ID'],
        '--session-name', session_name,
        '--window-name', window_name
    ]


def expand_run_template(template: str, cmd: str, member_name: str, context: Dict[str, str]) -> str:
    """
    Expand run template with context and command variables.
    Supports: {cmd}, {agent}, {team}, {project_root}, {session_id}, {window_name}, {session_name}
    """
    project_root_path = Path(context['UCAS_PROJECT_ROOT'])
    project_name = project_root_path.name
    team_name = context.get('UCAS_TEAM', '')
    
    # Session name: project-team or just project
    session_name = project_name
    if team_name:
        session_name = f"{project_name}-{team_name}"
    
    timestamp = datetime.now().strftime("%H%M%S")
    window_name = f"{member_name}-{timestamp}"

    replacements = {
        '{cmd}': cmd,
        '{agent}': context['UCAS_AGENT'],
        '{team}': team_name,
        '{project_root}': context['UCAS_PROJECT_ROOT'],
        '{session_id}': context['UCAS_SESSION_ID'],
        '{window_name}': window_name,
        '{session_name}': session_name
    }
    
    result = template
    for placeholder, value in replacements.items():
        # Handle {cmd} specially to avoid unwanted expansions if it contains {}
        if placeholder == '{cmd}':
            continue
        result = result.replace(placeholder, str(value))
    
    # Replace {cmd} last
    result = result.replace('{cmd}', cmd)
    
    # Expand environment variables
    result = os.path.expandvars(result)
    
    return result
