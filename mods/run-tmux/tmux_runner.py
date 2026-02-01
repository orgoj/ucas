#!/usr/bin/env python3
import argparse
import subprocess
import sys
import shutil

def main():
    parser = argparse.ArgumentParser(description="UCAS Tmux Runner")
    parser.add_argument("--cmd", required=True, help="Command to run")
    parser.add_argument("--session-name", required=True, help="Tmux session name")
    parser.add_argument("--window-name", required=True, help="Tmux window name")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--team", help="Team name")
    parser.add_argument("--project-root", help="Project root")
    parser.add_argument("--session-id", help="Session UUID")

    args, unknown = parser.parse_known_args()

    if not shutil.which('tmux'):
        print("Error: tmux not found.", file=sys.stderr)
        sys.exit(1)

    # 1. Ensure session exists
    has_session = subprocess.run(['tmux', 'has-session', '-t', args.session_name], 
                                capture_output=True)
    if has_session.returncode != 0:
        subprocess.run(['tmux', 'new-session', '-d', '-s', args.session_name], check=True)

    # 2. Create new window and run command
    # We use new-window -n <name> -t <session> <cmd>
    tmux_cmd = [
        'tmux', 'new-window',
        '-t', args.session_name,
        '-n', args.window_name,
        args.cmd
    ]
    
    try:
        subprocess.run(tmux_cmd, check=True)
        print(f"✓ Launched '{args.agent}' in tmux session '{args.session_name}' window '{args.window_name}'")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to create tmux window: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
