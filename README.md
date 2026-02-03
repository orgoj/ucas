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
ucas run-team my-dev-team
```

## Global Options

- `-q`, `--quiet`: Minimize output (useful for scripting).
- `-v`, `--verbose`: Show which configuration files are being loaded.
- `--debug`: Show detailed merge tracing and internal commands.
- `--dry-run`: Show the final command without executing it.

## Configuration (ucas.yaml)

UCAS uses `ucas.yaml` files at various levels.

### Mod Definition Example
```yaml
name: my-mod
description: A useful capability
acli!: # Force-overwrite ACLI block
  executable: my-cli
  prompt_arg: --prompt
  skills_dir: --tools
```

### Runner Definition Example
```yaml
name: my-runner
run!: # Force-overwrite RUN block
  script: "__DIR__/runner.py" # __DIR__ resolves to mod folder
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
