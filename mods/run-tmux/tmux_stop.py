#!/usr/bin/env python3
import argparse
import subprocess
import sys
import shutil

def main():
    parser = argparse.ArgumentParser(description="UCAS Tmux Stopper")
    parser.add_argument("--cmd", help="Command (unused)")
    parser.add_argument("--session-name", required=True, help="Tmux session name")
    parser.add_argument("--window-name", help="Tmux window name (unused)")
    parser.add_argument("--agent", help="Agent name")
    parser.add_argument("--team", help="Team name")
    parser.add_argument("--project-root", help="Project root")
    parser.add_argument("--session-id", help="Session UUID")

    args, unknown = parser.parse_known_args()

    if not shutil.which('tmux'):
        print("Error: tmux not found.", file=sys.stderr)
        sys.exit(1)

    # Check session
    has_session = subprocess.run(['tmux', 'has-session', '-t', args.session_name], 
                                capture_output=True)
    
    if has_session.returncode == 0:
        print(f"Stopping tmux session '{args.session_name}'...")
        try:
            subprocess.run(['tmux', 'kill-session', '-t', args.session_name], check=True)
            print(f"✓ Session '{args.session_name}' killed.")
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to kill session: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Session '{args.session_name}' not found. Nothing to stop.")

if __name__ == "__main__":
    main()
