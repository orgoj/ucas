"""
Team management and execution.
"""

import sys
import os
import time
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from . import settings
from . import mail
from .launcher import prepare_and_run_member, stop_runner, prepare_context
from .exceptions import LaunchError
from .merger import merge_configs, resolve_entities, _merge_dicts
from .resolver import find_entity, load_config_file, get_layer_config_paths, get_search_paths, get_run_config

def handle_team_command(args):
    """Dispatch team commands."""
    if args.team_command == 'run':
        run_team(args)
    elif args.team_command == 'stop':
        stop_team(args)
    elif args.team_command == 'status':
        show_status(args)
    else:
        print("Use: ucas team {run,stop,status} ...")
        sys.exit(1)


def _init_mails(merged_config: Dict[str, Any], team_members: List[str]):
    """Initialize mail system for the project if enabled."""
    if merged_config.get('mails') is not True:
        return

    project_root = Path.cwd()
    mail._update_project_list(project_root)
    
    # Create directories for all members (only lowercase names allowed)
    for member in team_members:
        if not member.islower():
            continue
            
        agent_mail_dir = project_root / ".ucas" / "mails" / member
        mail._ensure_mail_dirs(agent_mail_dir)
        
        # perfection: Notify if new mail is waiting
        inbox = agent_mail_dir / "inbox"
        new_cnt = len(list(inbox.glob("*.eml")))
        if new_cnt > 0:
            print(f"📩 [{member}] You have {new_cnt} new message(s) in your inbox.")
        
    if settings.VERBOSE:
        print(f"[MAIL] Initialized mailboxes for {len(team_members)} members at {project_root}")


def run_team(args):
    """Run a team of agents."""
    # 1. Resolve configuration layers
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, load_config_file(cfg), settings.DEBUG, f"Base:{layer_name}")
            
    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    search_paths = get_search_paths(extra_paths, base_config.get('strict', False))

    # 2. Resolve Mods (including Team Mod if specified)
    team_mod_paths = []
    
    # If args.team is specified, treat it as a mod that might contain team definition
    if args.team:
        m_path = find_entity(args.team, search_paths)
        if not m_path:
            raise LaunchError(f"Team Mod '{args.team}' not found")
        team_mod_paths.append(m_path)
        # Dynamic search path update is handled inside resolve_entities or we do it here?
        # resolve_entities is not used here yet.
        # We need to update search paths manually or create a helper if we want consistency.
        # But we can use _update_search_paths from merger if we import it, or just use find_entity logic.
        # Let's import _update_search_paths from merger.
        from .merger import _update_search_paths
        _update_search_paths(search_paths, m_path)

    # Add CLI mods
    for mod_item in (args.mods or []):
        m_path = find_entity(mod_item, search_paths)
        if not m_path:
            raise LaunchError(f"Mod '{mod_item}' not found")
        team_mod_paths.append(m_path)
        from .merger import _update_search_paths
        _update_search_paths(search_paths, m_path)

    # 3. Perform Merge
    project_root = Path.cwd()
    
    # Resolve default mods from base_config
    raw_default_mods = base_config.get('mods', [])
    default_mod_names = raw_default_mods if isinstance(raw_default_mods, list) else [raw_default_mods]
    default_mod_paths = []
    for m_name in default_mod_names:
        p = find_entity(m_name, search_paths)
        if p: default_mod_paths.append(p)

    merged_config = merge_configs(project_root, default_mod_paths, team_mod_paths)
    
    # 4. Extract Team Definition
    team_def = merged_config.get('team')
    if not team_def:
        if merged_config.get('agents') or merged_config.get('members'):
            team_def = merged_config
        else:
            raise LaunchError("No 'team' block or agents definition found in final configuration")

    # 5. Run Members
    team_name = team_def.get('name') or args.team or project_root.name
    members = team_def.get('agents') or team_def.get('members', {})
    team_wide_mods = team_def.get('mods', [])
    member_names = list(members.keys())
    
    print(f"Starting team '{team_name}' with {len(member_names)} members...")
    
    # Initialize Mails
    _init_mails(merged_config, member_names)

    for idx, name in enumerate(member_names):
        spec = members[name]
        # Parse member spec
        if isinstance(spec, list):
            base, mmods, prompt, model, provider = spec[0], spec[1:], None, None, None
        elif isinstance(spec, str):
            base, mmods, prompt, model, provider = spec, [], None, None, None
        elif isinstance(spec, dict):
            agent_list = spec.get('mods') or spec.get('agent', [])
            if isinstance(agent_list, list):
                base, mmods = agent_list[0], agent_list[1:]
            else:
                base, mmods = agent_list, spec.get('mods', [])
            prompt, model, provider = spec.get('prompt'), spec.get('model'), spec.get('provider')
        
        effective_mods = []
        if args.team:
            effective_mods.append(args.team)
        effective_mods.extend(team_wide_mods)
        effective_mods.extend(args.mods or [])
        effective_mods.extend(mmods)
        
        prepare_and_run_member(
            member_name=name, agent_name=base, mods=effective_mods,
            prefix=f"[{name}] ",
            team_name=team_name, team_index=idx, team_size=len(member_names),
            prompt=prompt or team_def.get('prompt'), model=model, provider=provider
        )
        
        if team_def.get('sleep_seconds', 0) > 0 and idx < len(member_names)-1 and not settings.DRY_RUN:
            time.sleep(team_def['sleep_seconds'])


def stop_team(args):
    """Stop a team."""
    (sys_cfg, _), (usr_cfg, _), (prj_cfg, _) = get_layer_config_paths()
    base_config = {}
    for layer_name, cfg in [('System', sys_cfg), ('User', usr_cfg), ('Project', prj_cfg)]:
        if cfg:
            base_config = _merge_dicts(base_config, load_config_file(cfg), settings.DEBUG, f"Base:{layer_name}")
            
    extra_paths = base_config.get('mod_path', [])
    if isinstance(extra_paths, str): extra_paths = [extra_paths]
    search_paths = get_search_paths(extra_paths, base_config.get('strict', False))

    team_mod_paths = []
    if args.team:
        m_path = find_entity(args.team, search_paths)
        if not m_path: raise LaunchError(f"Team Mod '{args.team}' not found")
        team_mod_paths.append(m_path)

    # Note: args.mods might not be available in stop command namespace properly in previous CLI?
    # CLI parser definitions:
    # team_stop = team_subparsers.add_parser('stop', ...)
    # team_stop.add_argument('team', ...)
    # NO MODS argument for stop in new CLI design.
    
    project_root = Path.cwd()
    merged_config = merge_configs(project_root, [], team_mod_paths)
    
    run_def = get_run_config(merged_config)
    
    if not run_def:
        def_run = merged_config.get('default_run') or base_config.get('default_run') or 'run-tmux'
        run_path = find_entity(def_run, search_paths)
        if run_path:
             merged_config = merge_configs(project_root, [], team_mod_paths + [run_path])
             run_def = get_run_config(merged_config)

    if not run_def: raise LaunchError("No 'run' block found to stop")
    
    team_name = merged_config.get('team', {}).get('name') or args.team or project_root.name
    
    stop_runner(run_def, prepare_context("stop", project_root, team_name))


def _get_tmux_sessions() -> List[Dict]:
    """Get all tmux sessions and windows."""
    try:
        # Format: session_name window_name window_index pane_current_path pane_idle
        cmd = ['tmux', 'list-panes', '-a', '-F', '#{session_name}|#{window_name}|#{window_index}|#{pane_current_path}|#{pane_idle}|#{pane_dead}|#{pane_pid}']
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            return []
        
        items = []
        for line in res.stdout.splitlines():
            parts = line.split('|')
            if len(parts) >= 7:
                items.append({
                    'session': parts[0],
                    'window': parts[1],
                    'index': parts[2],
                    'path': parts[3],
                    'idle': parts[4],
                    'dead': parts[5],
                    'pid': parts[6]
                })
        return items
    except FileNotFoundError:
        return []

def is_team_running(project_root: Path) -> bool:
    """Check if any team is running for the given project."""
    all_panes = _get_tmux_sessions()
    prefix = project_root.name
    # Check for exact session match or session-team match
    return any(p['session'] == prefix or p['session'].startswith(prefix + '-') for p in all_panes)

def run_team_programmatically(project_root: Path, team_name: Optional[str] = None):
    """Run a team without requiring CLI args object."""
    class FakeArgs:
        def __init__(self):
            self.team = team_name
            self.mods = []
            self.team_command = 'run'
    
    # Save current CWD and switch to project root temporarily
    old_cwd = os.getcwd()
    try:
        os.chdir(str(project_root))
        run_team(FakeArgs())
    finally:
        os.chdir(old_cwd)

def _capture_pane(session: str, window: str, lines: int = 15) -> str:
    """Capture last N lines of a pane."""
    try:
        cmd = ['tmux', 'capture-pane', '-p', '-e', '-S', f'-{lines}', '-t', f'{session}:{window}']
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.stdout
    except:
        return ""

def show_status(args):
    """Show status of teams."""
    # 1. Ensure we are in a UCAS project
    project_root = mail._get_project_root()
    if not (project_root / ".ucas").exists():
        print(f"Error: Not in a UCAS project (no .ucas directory found in {project_root})", file=sys.stderr)
        sys.exit(1)

    all_panes = _get_tmux_sessions()
    
    # UCAS run-tmux session name format: {project_root.name}-{team} or {project_root.name}
    prefix = project_root.name
    
    # Identify relevant sessions by checking the current path of the panes
    # (Panes in run-tmux are started in the project root or agent notes dir)
    project_root_str = str(project_root.resolve())
    
    relevant_panes = []
    for p in all_panes:
        pane_path = p['path']
        # Path must be inside project_root
        if pane_path == project_root_str or pane_path.startswith(project_root_str + os.sep):
            relevant_panes.append(p)
    
    if not relevant_panes:
        print(f"No active sessions found for project '{prefix}' at {project_root_str}.")
        return

    target = args.target # could be Team or Agent
    lines = args.lines 
    if lines is None:
        lines = 15 # Default summary
        if target:
            lines = 80 # Default detail if target specified

    # Group by session (Team)
    teams = {}
    for p in relevant_panes:
        s = p['session']
        if s not in teams: teams[s] = []
        teams[s].append(p)

    for session_name, panes in teams.items():
        team_name = session_name[len(prefix)+1:] if session_name.startswith(prefix + '-') else "Default"
        
        # If target specified, filter
        if target:
            # Check if target matches team name
            if target != team_name and target != session_name:
                # Check if target matches any agent (window name)
                matching_panes = [p for p in panes if target in p['window']]
                if not matching_panes:
                    continue # This session doesn't have the target
                
                # Show detail for this agent
                for p in matching_panes:
                    print(f"Agent: {p['window']} (PID: {p['pid']})")
                    print(f"Status: {'DEAD' if p['dead']=='1' else 'RUNNING'}")
                    print(f"Idle: {p['idle']}s")
                    print("-" * 40)
                    print(_capture_pane(p['session'], p['window'], lines))
                    print("-" * 40)
                return

        print(f"Team: {team_name} (Session: {session_name})")
        print(f"{'AGENT':<20} {'PID':<8} {'STATUS':<10} {'IDLE':<10} {'LAST OUTPUT'}")
        print("-" * 80)
        
        # Dedup panes by window (tmux list-panes lists all panes, run-tmux usually has 1 pane per window)
        seen_windows = set()
        for p in panes:
            if p['window'] in seen_windows: continue
            seen_windows.add(p['window'])
            
            status = "DEAD" if p['dead'] == '1' else "RUNNING"
            # Get last line
            last_lines = _capture_pane(p['session'], p['window'], 1).strip().splitlines()
            last_line = last_lines[-1] if last_lines else ""
            if len(last_line) > 30: last_line = last_line[:27] + "..."
            
            print(f"{p['window']:<20} {p['pid']:<8} {status:<10} {p['idle']+'s':<10} {last_line}")
        print()
