# Universal CLI Agent System (UCAS)

Universal CLI Agent System is a tool for managing and launching AI agents and teams with a modular, configuration-driven approach.

## Key Features

- **Sandwich Merge**: Multi-layer configuration (System → User → Project → Agent → Mods → Overrides).
- **Modular Skills**: Add capabilities via mods (e.g., `+git`, `+docker`).
- **Run Wrappers**: Execute agents in different environments (`tmux`, `bash`, `xterm`).
- **Dynamic Context**: Environment variables and paths injected into every agent session.
- **__DIR__ Variable**: Automatically resolve paths relative to the mod's directory in `ucas.yaml`.

## Installation

```bash
# Recommended: symlink the binary
ln -s $(pwd)/ucas-bin ~/bin/ucas
```

## Basic Usage

### List Available Mods
```bash
ucas ls-mods         # Detailed list with descriptions
ucas -q ls-mods      # Names only, grouped by layer
ucas -v ls-mods      # Show paths to mod directories
```

### Run an Agent
```bash
ucas run generic                   # Default run (tmux + claude)
ucas run generic +skill +acli-pi   # Run using Pi CLI with skills
ucas run generic +run-bash         # Run directly in current terminal
```

### Run a Team
```bash
ucas team run my-dev-team   # Start a team
ucas team status            # Check status of running teams
ucas team stop my-dev-team  # Stop a team
```

**Team Autostart**: Teams can be configured to start automatically when a mail arrives if no team is running. Add `team_autostart: true` to your `ucas.yaml`.

### Agent Mail System
Communicate with agents using the built-in EML-based mail system.
Requires `mails: true` in your project configuration to enable agent mailboxes.

- **Address Book**: Use `ucas mail addressbook` to find contacts. Descriptions for local agents are fetched from their `ucas.yaml`.
- **Cross-Project Communication**: Send mail to agents in other folders using `agent-name@/path/to/project`.
- **Auto-Reply**: Replying to a message (`--reply <ID>`) automatically resolves the recipient.

```bash
# List available contacts
ucas mail addressbook

# Send a message (recipient optional if replying)
echo "Hello Agent" | ucas mail send agent-name "Subject"

# Check inbox (notifies if new mail is waiting)
ucas mail list

# Read a message (moves to read folder)
ucas mail read <ID>

# Archive a message
ucas mail archive <ID>
```

## Global Options

- `-q`, `--quiet`: Minimize output (useful for scripting).
- `-v`, `--verbose`: Show which configuration files are being loaded.
- `--debug`: Show detailed merge tracing and internal commands.
- `--dry-run`: Show the final command without executing it.

## Configuration (ucas.yaml)

UCAS is highly configurable using `ucas.yaml` files. You can find the full list of available keys, merge strategies, and variable expansions in the official [Configuration Reference](CONFIGURATION.md).

### Quick Example (Mod)
```yaml
name: my-mod
description: A useful capability
acli!: # Force-overwrite ACLI block
  executable: my-cli
  prompt_arg: --prompt
  skills_dir: --tools
```

## Mod Layers

1. **Project**: `./.ucas/mods/`
2. **User**: `~/.ucas/mods/`
3. **System**: `<install-dir>/mods/` or `$UCAS_HOME/mods/`

## Development

Run tests with:
```bash
./run_tests.sh
```

Always use `./ucas-bin` for local execution during development.
