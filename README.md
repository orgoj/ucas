# UCAS - Universal CLI Agent System

**UCAS** is an intelligent assembler and launcher that finds Agent/Mod/ACLI definitions, merges them via "Sandwich Merge", and executes in tmux.

## Quick Start

### Installation

```bash
# Option 1: Symlink in ~/bin (recommended for development)
ln -s /path/to/ucas/ucas-bin ~/bin/ucas
ucas run basic-chat

# Option 2: Run directly with Python
python -m ucas run basic-chat

# Option 3: Install as package
pip install -e .
ucas run basic-chat

# Note: UCAS_HOME is optional - defaults to package installation directory
# Only set UCAS_HOME if you want to override the default system agents location
export UCAS_HOME=/custom/location
```

### Basic Usage

```bash
# Run an agent
ucas run basic-chat

# Run an agent with mods
ucas run basic-chat +git-mod +debug-mod

# Run a team
ucas run-team backend-squad

# Dry-run (show command without executing)
ucas run basic-chat --dry-run

# Debug mode (verbose merge tracing)
ucas run basic-chat --debug
```

## Project Structure

```
ucas/
├── ucas/                    # Main package
│   ├── yaml_parser.py       # Mini YAML parser
│   ├── resolver.py          # Entity search across layers
│   ├── merger.py            # Sandwich merge logic
│   └── launcher.py          # Command building & tmux execution
├── agents/                  # System Library ($UCAS_HOME/agents/)
│   ├── acli-claude/
│   │   └── ucas.yaml
│   ├── basic-chat/
│   │   ├── ucas.yaml
│   │   └── PROMPT.md
│   └── git-mod/
│       ├── ucas.yaml
│       ├── PROMPT.md
│       └── skills/
├── teams/                   # Team definitions
│   └── example-team/
│       └── ucas.yaml
└── ucas.yaml                # System defaults
```

## Configuration Layers

UCAS uses an 11-layer "Sandwich Merge" system:

**Bottom Layers (defaults):**
1. `$UCAS_HOME/ucas.yaml` - System defaults (defaults to package location)
2. `~/.ucas/ucas.yaml` - User defaults
3. `./.ucas/ucas.yaml` - Project defaults
4. `agent/ucas.yaml` - Main agent
5-N. `mod/ucas.yaml` - Mods in CLI order

**Top Layers (overrides with veto power):**
- `$UCAS_HOME/ucas-override.yaml` - System veto
- `~/.ucas/ucas-override.yaml` - User veto
- `./.ucas/ucas-override.yaml` - Project veto (strongest)

**System Layer Auto-Detection:**
- If `UCAS_HOME` is set, uses `$UCAS_HOME/agents/`
- If not set, uses `<package-install-dir>/agents/`
- This means UCAS_HOME is **optional** - it auto-discovers system agents

## Key Features

### Model Mapping
ACLIs translate agent's `requested_model` to supported models:

```yaml
# acli-claude/ucas.yaml
model_mapping:
  gpt-4: sonnet-3.5
  gpt-5.2-pro: opus-4.5
  default: sonnet-3.5

ignore_unknown: false  # Error on unknown models
```

### Skills Aggregation
Skills from agent and all mods are collected and passed to the ACLI:

```bash
ucas run basic-chat +git-mod +docker-mod
# Results in: --tools /path/to/basic-chat/skills --tools /path/to/git-mod/skills --tools /path/to/docker-mod/skills
```

### ACLI Selection
Priority order:
1. `override_acli` (from override files - veto power)
2. `executable` (if this is an ACLI definition)
3. Agent's `default_acli` (if in `allowed_acli`)
4. First item in `allowed_acli`

## Example Configurations

### Agent Definition
```yaml
# agents/basic-chat/ucas.yaml
name: basic-chat
requested_model: gpt-4
default_acli: acli-claude
```

### Mod Definition
```yaml
# agents/git-mod/ucas.yaml
name: git-mod
description: Adds git operation capabilities
```

### ACLI Definition
```yaml
# agents/acli-claude/ucas.yaml
name: acli-claude
executable: claude

arg_mapping:
  prompt_file: --system
  skills_dir: --tools
  model_flag: --model

model_mapping:
  gpt-4: sonnet-3.5
  default: sonnet-3.5
```

### Team Definition
```yaml
# teams/example-team/ucas.yaml
name: example-team
sleep_seconds: 1

members:
  agent1:
    agent: basic-chat
  agent2:
    agent: basic-chat
    mods:
      - git-mod
```

## Implementation Status

- ✅ **Slice 1**: Minimal dry-run
- ✅ **Slice 2**: Real tmux execution
- ✅ **Slice 3**: Mods support with prompt concatenation
- ✅ **Slice 4**: Three-layer search with overrides
- ✅ **Slice 5**: Teams support

## Technical Decisions

1. **No external dependencies** - Python 3.6+ stdlib only, custom YAML parser
2. **Skills as arguments** - No PATH manipulation, skills passed via `arg_mapping.skills_dir`
3. **First match wins** - Entity search stops at first found (Project → User → System)
4. **Last wins merge** - Dict keys overwritten by later layers
5. **Skills aggregated** - All `skills/` directories collected and passed

## License

MIT
