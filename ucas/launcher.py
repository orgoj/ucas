"""
Command building and execution wrappers.
"""

import re
import shlex
import shutil
import subprocess
import uuid
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


from . import settings
# Imports for _prepare_and_run_member
from .resolver import get_acli_config, get_run_config, find_entity
from .merger import merge_configs, collect_skills, resolve_entities


from .exceptions import LaunchError


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
    """Expand session path template with context variables."""
    replacements = {
        '{uuid}': context['UCAS_SESSION_ID'],
        '{agent}': context['UCAS_AGENT'],
        '{team}': context.get('UCAS_TEAM', ''),
        '{project_root}': context['UCAS_PROJECT_ROOT']
    }
    
    result = template
    for placeholder, value in replacements.items():
        result = result.replace(placeholder, value)
    
    result = os.path.expandvars(result)
    result = os.path.expanduser(result)
    
    if result.startswith(('/','./','../')):
        path = Path(result)
        if not path.is_absolute():
            path = Path(context['UCAS_PROJECT_ROOT']) / path
        result = str(path.resolve())
    
    return result


def get_context_export_str(context: Dict[str, str]) -> str:
    """Return a string of exports for shell injection."""
    parts = []
    for k, v in context.items():
        if v:
            parts.append(f"export {k}={shlex.quote(v)}")
    return ' && '.join(parts)


class HookRunner:
    """Runs lifecycle hooks with injected context."""
    def __init__(self, context: Dict[str, str]):
        self.context = context
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
            if settings.DEBUG:
                print(f"[HOOK] Running {stage}: {cmd}", file=sys.stderr)
            try:
                subprocess.run(cmd, shell=True, env=self.env, check=True)
            except subprocess.CalledProcessError as e:
                raise LaunchError(f"Hook '{stage}' failed: {cmd} (exit code {e.returncode})")


def translate_model(requested_model: Optional[str], acli_def: Dict[str, Any]) -> Optional[str]:
    """Translate model name using ACLI mapping."""
    if not requested_model:
        return None

    model_mapping = acli_def.get('model_mapping', {})
    ignore_unknown = acli_def.get('ignore_unknown', False)

    if requested_model == 'default' and 'default' not in model_mapping:
        return None

    if requested_model in model_mapping:
        translated = model_mapping[requested_model]
        if settings.DEBUG:
            print(f"[MODEL] Translated {requested_model} → {translated}", file=sys.stderr)
        return translated

    if 'default' in model_mapping:
        translated = model_mapping['default']
        if settings.DEBUG:
            print(f"[MODEL] Using default mapping for {requested_model} → {translated}", file=sys.stderr)
        return translated

    if not ignore_unknown:
        raise LaunchError(f"Model '{requested_model}' not found in ACLI model_mapping")
    
    return requested_model


def build_command(
    agent_path: Path,
    mod_paths: List[Path],
    merged_config: Dict[str, Any],
    skills_dirs: List[Path],
    context: Dict[str, str],
    prompt: Optional[str] = None
) -> str:
    """Build final command string from ACLI block."""
    acli_def = get_acli_config(merged_config)
    executable = acli_def.get('executable')
    if not executable:
        raise LaunchError("No ACLI 'executable' defined in final configuration")

    cmd_parts = [executable]
    
    # 1. System Prompt Override (PROMPT_SYSTEM.md)
    sys_override = get_merged_system_override(mod_paths, context)
    if not sys_override:
        # Default identity if no override
        sys_override = get_identity_prompt(context)
        
    if 'system_prompt_arg' in acli_def:
        cmd_parts.append(acli_def['system_prompt_arg'])
        cmd_parts.append(sys_override)

    # 2. System Prompt Add (Append) (PROMT_SYSTEM_ADD.md or PROMPT_SYSTEM_ADD.md)
    sys_add = get_merged_system_add(mod_paths, context)
    if sys_add and 'system_prompt_add_arg' in acli_def:
        cmd_parts.append(acli_def['system_prompt_add_arg'])
        cmd_parts.append(sys_add)

    # 3. Legacy PROMPT.md (from agent/mods)
    prompt_text = get_merged_prompt(agent_path, mod_paths, merged_config, context)

    # Add prompt argument
    if 'prompt_arg' in acli_def and prompt_text:
        cmd_parts.append(acli_def['prompt_arg'])
        cmd_parts.append(prompt_text)
    
    # LEGACY: support prompt_file
    elif 'prompt_file' in acli_def and prompt_text:
        tmp_dir = Path.cwd() / '.ucas' / 'tmp'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = tmp_dir / f"{context.get('UCAS_AGENT', agent_path.name)}.merged.md"
        prompt_file.write_text(prompt_text)
        cmd_parts.append(acli_def['prompt_file'])
        cmd_parts.append(str(prompt_file))

    # Add provider argument
    requested_provider = merged_config.get('requested_provider')
    if requested_provider and 'provider_flag' in acli_def:
        cmd_parts.append(acli_def['provider_flag'])
        cmd_parts.append(requested_provider)

    # Add model argument
    requested_model = merged_config.get('requested_model')
    if requested_model:
        translated_model = translate_model(requested_model, acli_def)
        if translated_model and 'model_flag' in acli_def:
            cmd_parts.append(acli_def['model_flag'])
            cmd_parts.append(translated_model)

    # Add skills arguments
    if skills_dirs and 'skills_dir' in acli_def:
        for skills_dir in skills_dirs:
            cmd_parts.append(acli_def['skills_dir'])
            cmd_parts.append(str(skills_dir))
    
    if 'session_arg' in acli_def:
        session_expanded = expand_session_template(acli_def['session_arg'], context)
        path_match = re.search(r'["\']?(/[^"\']*\.json)["\']?', session_expanded)
        if path_match:
            os.makedirs(os.path.dirname(path_match.group(1)), exist_ok=True)
        cmd_parts.extend(shlex.split(session_expanded))

    if prompt:
        cmd_parts.append(prompt)

    return ' '.join(shlex.quote(p) for p in cmd_parts)


def expand_variables(text: str, context: Dict[str, str]) -> str:
    """Expand $VAR and ${VAR}."""
    full_context = os.environ.copy()
    full_context.update(context)
    result = text
    for k, v in full_context.items():
        result = result.replace(f"${k}", str(v))
        result = result.replace(f"${{{k}}}", str(v))
    return result


def get_identity_prompt(context: Dict[str, str]) -> str:
    """Get the default identity block."""
    agent_name = context.get('UCAS_AGENT', 'unknown')
    team_name = context.get('UCAS_TEAM', '')
    
    identity = f"SYSTEM OVERRIDE: Your name is **{agent_name}**.\n"
    identity += f"You are a specialized AI agent in the UCAS framework.\n"
    identity += f"Your mission identity: **{agent_name}**\n"
    if team_name:
        identity += f"Assigned Team: **{team_name}**\n"
    identity += f"\nIMPORTANT: You must NOT identify as 'pi', 'Claude', or 'Gemini'. Always use **{agent_name}**.\n"
    return identity


def get_merged_prompt(
    agent_path: Path,
    mod_paths: List[Path],
    merged_config: Dict[str, Any],
    context: Dict[str, str]
) -> str:
    """Concatenate PROMPT.md files."""
    prompt_parts = []
    
    agent_prompt = agent_path / 'PROMPT.md'
    if agent_prompt.exists():
        prompt_parts.append(agent_prompt.read_text())

    for mod_path in mod_paths:
        mod_prompt = mod_path / 'PROMPT.md'
        if mod_prompt.exists():
            prompt_parts.append(mod_prompt.read_text())

    if not prompt_parts:
        return ""

    merged_content = "\n\n---\n\n".join(p.strip() for p in prompt_parts if p.strip())
    return expand_variables(merged_content, context)


def get_merged_system_override(mod_paths: List[Path], context: Dict[str, str]) -> str:
    """Concatenate PROMPT_SYSTEM.md files from mods."""
    parts = []
    for mod_path in mod_paths:
        f = mod_path / 'PROMPT_SYSTEM.md'
        if f.exists():
            parts.append(f.read_text())

    if not parts:
        return ""

    merged_content = "\n\n---\n\n".join(p.strip() for p in parts if p.strip())
    return expand_variables(merged_content, context)


def get_merged_system_add(mod_paths: List[Path], context: Dict[str, str]) -> str:
    """Concatenate PROMT_SYSTEM_ADD.md or PROMPT_SYSTEM_ADD.md files from mods."""
    parts = []
    for mod_path in mod_paths:
        # Check for both spellings (to be robust against typos)
        for name in ['PROMT_SYSTEM_ADD.md', 'PROMPT_SYSTEM_ADD.md']:
            f = mod_path / name
            if f.exists():
                parts.append(f.read_text())
                break # Only use one if both exist in same mod

    if not parts:
        return ""

    merged_content = "\n\n---\n\n".join(p.strip() for p in parts if p.strip())
    return expand_variables(merged_content, context)


def validate_runner(run_def: Dict[str, Any], context: Dict[str, str]) -> None:
    """Validate runner for team execution."""
    if context.get('UCAS_TEAM') and run_def.get('single', False):
        raise LaunchError(f"Runner is marked as 'single' and cannot be used for teams.")


def stop_runner(run_def: Dict[str, Any], context: Dict[str, str]) -> None:
    """Execute stop command from run block."""
    env = os.environ.copy()
    env.update(context)

    stop_script = run_def.get('stop_script')
    stop_executable = run_def.get('stop_executable')
    stop_template = run_def.get('stop_template')

    if stop_script:
        cmd = [sys.executable, stop_script] if stop_script.endswith('.py') else [stop_script]
        cmd.extend(get_run_args("", "stop", context))
    elif stop_executable:
        cmd = [stop_executable]
        cmd.extend(get_run_args("", "stop", context))
    elif stop_template:
        cmd_str = expand_run_template(stop_template, "", "stop", context)
        if settings.DRY_RUN:
            print(f"[DRY-RUN] Would run stop template: {cmd_str}")
            return
        subprocess.run(cmd_str, shell=True, check=True, env=env)
        return
    else:
        return

    if settings.DRY_RUN:
        print(f"[DRY-RUN] Would run stop: {' '.join(shlex.quote(p) for p in cmd)}")
    else:
        subprocess.run(cmd, check=True, env=env)


def run_command(run_def: Dict[str, Any], cmd: str, member_name: str, context: Dict[str, str]) -> None:
    """Execute final command from run block."""
    final_cmd_str = get_runner_preview(run_def, cmd, member_name, context)
    if settings.DEBUG: print(f"[EXEC] Running: {final_cmd_str}", file=sys.stderr)
    
    env = os.environ.copy()
    env.update(context)

    if run_def.get('template'):
        subprocess.run(final_cmd_str, shell=True, check=True, env=env)
    else:
        # For script/executable we need to split the command for subprocess.run
        import shlex
        subprocess.run(shlex.split(final_cmd_str), check=True, env=env)


def get_runner_preview(run_def: Dict[str, Any], cmd: str, member_name: str, context: Dict[str, str]) -> str:
    """Get the command string that the runner would execute."""
    script = run_def.get('script')
    executable = run_def.get('executable')
    template = run_def.get('template')

    if script:
        full_cmd = [sys.executable, script] if script.endswith('.py') else [script]
        full_cmd.extend(get_run_args(cmd, member_name, context))
        return ' '.join(shlex.quote(p) for p in full_cmd)
    elif executable:
        full_cmd = [executable]
        full_cmd.extend(get_run_args(cmd, member_name, context))
        return ' '.join(shlex.quote(p) for p in full_cmd)
    elif template:
        return expand_run_template(template, cmd, member_name, context)
    else:
        raise LaunchError("Run block missing 'script', 'executable', or 'template'")


def get_run_args(cmd: str, member_name: str, context: Dict[str, str]) -> List[str]:
    """Standard arguments for run-mod scripts."""
    root = Path(context['UCAS_PROJECT_ROOT'])
    team = context.get('UCAS_TEAM', '')
    session_name = f"{root.name}-{team}" if team else root.name
    window_name = f"{member_name}-{datetime.now().strftime('%H%M%S')}"

    return [
        '--cmd', cmd,
        '--agent', context['UCAS_AGENT'],
        '--team', team,
        '--project-root', str(root),
        '--session-id', context['UCAS_SESSION_ID'],
        '--session-name', session_name,
        '--window-name', window_name
    ]


def expand_run_template(template: str, cmd: str, member_name: str, context: Dict[str, str]) -> str:
    """Expand run template variables."""
    root = Path(context['UCAS_PROJECT_ROOT'])
    team = context.get('UCAS_TEAM', '')
    session_name = f"{root.name}-{team}" if team else root.name
    window_name = f"{member_name}-{datetime.now().strftime('%H%M%S')}"

    repls = {
        '{cmd}': cmd,
        '{agent}': context['UCAS_AGENT'],
        '{team}': team,
        '{project_root}': str(root),
        '{session_id}': context['UCAS_SESSION_ID'],
        '{window_name}': window_name,
        '{session_name}': session_name
    }
    
    res = template
    for k, v in repls.items():
        if k != '{cmd}': res = res.replace(k, v)
    res = res.replace('{cmd}', cmd)
    return os.path.expandvars(res)


def select_run_mod(merged_config: Dict[str, Any]) -> str:
    """Select the run mod to use based on configuration."""
    # 1. Direct 'run' block that is a full definition
    run_def = merged_config.get('run')
    if isinstance(run_def, dict) and 'name' in run_def:
        return run_def['name']

    # 2. explicit override
    if 'override_run' in merged_config:
        return merged_config['override_run']
    
    # 3. default
    if 'default_run' in merged_config:
        return merged_config['default_run']
    
    # 4. First allowed
    allowed = merged_config.get('allowed_run', [])
    if allowed:
        return allowed[0]
    
    return 'run-tmux'  # Hardcoded default fallback


def prepare_and_run_member(
    member_name: str,
    agent_name: str,
    mods: List[str],
    prefix: str = "",
    team_name: str = None,
    team_index: int = 0,
    team_size: int = 1,
    prompt: str = None,
    model: str = None,
    provider: str = None
) -> None:
    """Prepare and run a single agent member."""
    # 1. First resolution to get search paths and base_config
    agent_path, explicit_mod_paths, search_paths, base_config = resolve_entities(agent_name, mods)
    
    # 2. Identify default mods from base_config
    raw_default_mods = base_config.get('mods', [])
    default_mod_names = raw_default_mods if isinstance(raw_default_mods, list) else [raw_default_mods]
    
    # 3. Resolve default mod paths
    default_mod_paths = []
    for m_name in default_mod_names:
        p = find_entity(m_name, search_paths)
        if p: default_mod_paths.append(p)

    # 4. Perform sandwich merge with correct priorities:
    # System -> Default Mods -> Agent -> Explicit Mods -> Overrides
    merged_config = merge_configs(agent_path, default_mod_paths, explicit_mod_paths)
    
    # 5. Add default ACLI if missing (look up again if needed)
    acli_def = get_acli_config(merged_config)
    if not acli_def.get('executable'):
        def_acli = merged_config.get('default_acli') or base_config.get('default_acli')
        if def_acli:
            acli_path = find_entity(def_acli, search_paths)
            if acli_path:
                explicit_mod_paths.append(acli_path)
                merged_config = merge_configs(agent_path, default_mod_paths, explicit_mod_paths)

    # 6. Add default RUN if missing
    run_def = get_run_config(merged_config)
    if not run_def:
        def_run = merged_config.get('default_run') or base_config.get('default_run') or 'run-tmux'
        run_path = find_entity(def_run, search_paths)
        if run_path:
            explicit_mod_paths.append(run_path)
            merged_config = merge_configs(agent_path, default_mod_paths, explicit_mod_paths)

    if model: merged_config['requested_model'] = model
    if provider: merged_config['requested_provider'] = provider

    context = prepare_context(member_name, agent_path, team_name, team_index, team_size)
    
    env_config = merged_config.get('env', {})
    for k, v in env_config.items():
        context[k] = expand_variables(v, context) if isinstance(v, str) else str(v)

    all_mod_paths = default_mod_paths + explicit_mod_paths
    skills_dirs = collect_skills(agent_path, all_mod_paths)
    
    main_cmd = build_command(
        agent_path,
        all_mod_paths,
        merged_config,
        skills_dirs,
        context,
        prompt
    )

    acli_def = get_acli_config(merged_config)
    context['UCAS_ACLI_EXE'] = acli_def.get('executable', '')
    context['UCAS_MAIN_COMMAND'] = main_cmd

    all_cmds = [get_context_export_str(context)]
    hooks = merged_config.get('hooks', {})
    
    prerun = hooks.get('prerun', [])
    if isinstance(prerun, str): prerun = [prerun]
    all_cmds.extend(prerun)
    all_cmds.append(main_cmd)
    
    postrun = hooks.get('postrun', [])
    if isinstance(postrun, str): postrun = [postrun]
    all_cmds.extend(postrun)
    
    final_command = ' && '.join(all_cmds)
    run_def = get_run_config(merged_config)
    if not run_def:
        raise LaunchError("No 'run' block found in final configuration")
    
    # Validation step for team context
    validate_runner(run_def, context)

    if settings.DRY_RUN:
        if settings.DEBUG: print(f"[DEBUG] Dry run enabled, getting preview...", file=sys.stderr)
        runner_preview = get_runner_preview(run_def, final_command, member_name, context)
        print(f"{prefix}[DRY-RUN] {runner_preview}")
    else:
        if settings.DEBUG: print(f"[DEBUG] Real run, executing...", file=sys.stderr)
        HookRunner(context).run(hooks, 'install')
        run_command(run_def, final_command, member_name, context)
