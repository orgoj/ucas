# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UCAS (Universal CLI Agent System) is a vendor-agnostic agent orchestration system built on the KISS principle. It's an intelligent assembler that finds Agent/Mod/ACLI definitions, merges them via "Sandwich Merge", and executes them in tmux.

**Core Differentiator**: Dynamic CLI composition - run `ucas run generic +git +webresearch` to aggregate models, parameters, environment variables, and skills at execution time without modifying configuration files.

**Zero Dependencies**: Python 3.6+ stdlib only, with a custom YAML parser to avoid external dependencies.

## Development Commands

### Running Tests
```bash
# Run all tests
./run_tests.sh

# Run specific test file
python3 -m unittest tests.test_merger_strategies

# Run with verbose output
python3 -m unittest discover -v -s tests -p 'test_*.py'
```

### Running UCAS
```bash
# Option 1: Symlink in ~/bin (recommended for development)
ln -s /path/to/ucas/ucas-bin ~/bin/ucas
ucas run basic-chat

# Option 2: Run directly with Python
python -m ucas run basic-chat

# Option 3: Install as package
pip install -e .
ucas run basic-chat
```

### Testing Configuration Changes
```bash
# Dry-run (show command without executing)
ucas run basic-chat --dry-run

# Debug mode (verbose merge tracing)
ucas run basic-chat --debug

# Run with mods
ucas run basic-chat +mod-git +debug-mod

# Run a team
ucas run-team backend-squad
```

## Architecture

### Core Modules

**ucas/yaml_parser.py** - Custom YAML parser (no dependencies)
- Minimal YAML parser supporting basic types, lists, dicts
- Handles edge cases like empty lines, comments, indentation

**ucas/resolver.py** - Entity resolution across layers
- `find_entity()`: Searches for agents/mods/ACLIs across Project → Custom Paths → User → System
- `get_search_paths()`: Builds search path list with dynamic expansion
- `is_acli()`: Identifies ACLI definitions (has `executable` field)
- First match wins strategy

**ucas/merger.py** - Sandwich merge logic
- `merge_configs()`: 11-layer merge (3 default + agent + N mods + 3 override)
- `_merge_dicts()`: Implements suffix-based merge strategies (+, -, !, ?, ~)
- `collect_skills()`: Aggregates skills directories from agent and mods

**ucas/launcher.py** - Command building & tmux execution
- `select_acli()`: Priority-based ACLI selection (override → executable → default → allowed)
- `translate_model()`: Maps requested_model using ACLI's model_mapping
- `build_command()`: Assembles final CLI command from arg_mapping
- `generate_prompt()`: Concatenates PROMPT.md files from agent + mods
- `run_tmux()`: Executes in new tmux window with environment context

**ucas/__main__.py** - Entry point and orchestration
- `resolve_entities()`: Dynamic search path expansion during resolution
- `run_agent()`: Single agent execution
- `run_team()`: Multi-agent team orchestration

### Configuration Layers (Sandwich Merge)

```
      ▲  TOP (Overrides - Highest Priority)
      │
  [ Project Override: ./.ucas/ucas-override.yaml ]
  [ User Override:    ~/.ucas/ucas-override.yaml    ]
  [ System Override:  $UCAS_HOME/ucas-override.yaml ]
      │
//---- Final Merged Config is Assembled Here ----\\
      │
  [ Mod N:            path/to/mod_n/ucas.yaml       ]
  [ ...                                             ]
  [ Mod 1:            path/to/mod_1/ucas.yaml       ]
  [ Agent:            path/to/agent/ucas.yaml       ]
  [ Project Default:  ./.ucas/ucas.yaml             ]
  [ User Default:     ~/.ucas/ucas.yaml             ]
  [ System Default:   $UCAS_HOME/ucas.yaml          ]
      │
      ▼  BOTTOM (Defaults - Lowest Priority)
```

### Entity Search Resolution

1. **Base search paths**: Project (`./.ucas/mods/`) → Custom paths (`mod_path`) → User (`~/.ucas/mods/`) → System (`$UCAS_HOME/mods/`)
2. **Dynamic expansion**: Agents and mods can define `mod_path` to add search directories
3. **Strict mode**: Set `strict: true` to disable User/System layer searches
4. **First match wins**: Resolution stops at first found directory

### Merge Strategies (Suffix-Based)

| Suffix | Strategy | Behavior |
|--------|----------|----------|
| `key+` | Merge/Append | Concatenates lists; deep merges dictionaries |
| `key-` | Remove | Removes items from list or keys from dict |
| `key!` | Override | Forces replacement of base value |
| `key?` | Default | Sets value only if key is missing in base |
| `key~` | Update | Sets value only if key already exists in base |
| (none) | Default | Recursive merge for dicts, last-wins for scalars |

**Auto-append keys**: `skills`, `mods`, `mod_path`, `hooks` always use `+` strategy by default.

### Execution Context Variables

UCAS injects these environment variables into hooks and the main process:
- `UCAS_AGENT`: Current agent name
- `UCAS_TEAM`: Current team name (if running as part of a team)
- `UCAS_AGENT_DIR`: Absolute path to the mod's definition directory
- `UCAS_AGENT_NOTES`: Project-specific storage path (`./.ucas/notes/<agent>/`)
- `UCAS_PROJECT_ROOT`: Absolute path to the current project
- `UCAS_SESSION_ID`: Unique ID for the current execution session
- `UCAS_ACLI_EXE`: The resolved ACLI executable
- `UCAS_MAIN_COMMAND`: The full command line used to launch the primary agent

### Lifecycle Hooks

Mods can define executable hooks:
- `install`: Run once in host environment (e.g., `npm install`)
- `prerun`: Run in tmux window before main agent starts
- `postrun`: Run in tmux window after main agent exits

Hook execution chain: `exports && prerun && main_cmd && postrun` (failures stop the chain)

## Entity Types

### Agent Definition
```yaml
name: basic-chat
requested_model: gpt-4
default_acli: acli-claude
```

### Mod Definition
```yaml
name: mod-git
description: Adds git operation capabilities
mod_path:  # Optional: extend search paths
  - ./external-mods
hooks:
  install: npm install
  prerun: echo "Starting..."
```

### ACLI Definition
```yaml
name: acli-claude
executable: claude

arg_mapping:
  prompt_file: --system
  skills_dir: --tools
  model_flag: --model

model_mapping:
  gpt-4: sonnet-3.5
  default: sonnet-3.5

ignore_unknown: false  # Error on unknown models
```

### Team Definition
```yaml
team:
  mods: [messaging-mod]  # Global mods for all members
  sleep_seconds: 2       # Delay between member starts
  agents:
    karel:
      mods: [basic-chat, api-mod, mod-git]
    lucie:
      mods: [basic-chat, aws-mod]
```

## Key Design Principles

1. **No external dependencies** - Python 3.6+ stdlib only
2. **Skills as arguments** - No PATH manipulation, passed via `arg_mapping.skills_dir`
3. **First match wins** - Entity search stops at first found directory
4. **Dynamic path expansion** - Agents/mods can add search paths during resolution
5. **Last wins merge** - Later layers override earlier ones (except with override files)
6. **Skills/Hooks aggregated** - All `skills/` directories and `hooks` commands are collected

## Common Patterns

### Adding a New Agent
1. Create directory in `mods/<agent-name>/`
2. Add `ucas.yaml` with `name`, `requested_model`, `default_acli`
3. Optionally add `PROMPT.md` for system prompt
4. Optionally add `skills/` directory for tools

### Adding a New Mod
1. Create directory in `mods/<mod-name>/`
2. Add `ucas.yaml` with `name`, `description`
3. Optionally add `PROMPT.md` for additional instructions
4. Optionally add `skills/` directory for additional tools
5. Optionally add `hooks` for lifecycle automation

### Testing Configuration Merging
1. Use `--debug` flag to see merge trace
2. Use `--dry-run` to see final command without execution
3. Check `.ucas/tmp/<agent>.merged.md` for prompt concatenation

### Debugging Resolution Issues
1. Enable `--debug` to see search paths and found entities
2. Check search order: Project → Custom → User → System
3. Verify entity has `ucas.yaml` file
4. Use `strict: true` to isolate to project layer only

## Testing Guidelines

- Tests use Python's `unittest` framework
- Test fixtures in `tests/fixtures/`
- Mock home directory and environment variables for isolation
- Each test file focuses on one module (merger, resolver, etc.)
- Integration tests in `tests/test_dry_run.py`
