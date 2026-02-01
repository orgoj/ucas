# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

UCAS (Universal CLI Agent System) is a vendor-agnostic agent orchestration system built on the KISS principle. It's an intelligent assembler that finds Agent/Mod/ACLI definitions, merges them via "Sandwich Merge", and executes them in tmux.

**Core Differentiator**: Dynamic CLI composition - run `ucas run generic +git +webresearch` to aggregate models, parameters, environment variables, and skills at execution time without modifying configuration files.

**Zero Dependencies**: Python 3.6+ stdlib only, with a custom YAML parser to avoid external dependencies.

## Core Architecture Philosophy

**CRITICAL UNDERSTANDING**: UCAS is built on two fundamental principles:

### 1. General Merge + Interpretation
UCAS core does **NOT** have hardcoded behavior for specific features. Instead:
- **Merge**: Combine YAML configs from multiple layers (system → project → agent → mods → overrides)
- **Interpret**: Read resulting YAML and execute what it says

```
┌─────────────────────────────────────────┐
│  UCAS Core (Python)                     │
│  • Merge YAML layers                    │
│  • Interpret merged config              │
│  • Execute commands                     │
│  • NO feature-specific logic            │
└─────────────────────────────────────────┘
                  ▲
                  │ reads & merges
                  │
┌─────────────────────────────────────────┐
│  Configuration (YAML)                   │
│  • Defines ALL behavior                 │
│  • Each mod/ACLI specifies its needs    │
│  • session_arg, arg_mapping, etc.       │
└─────────────────────────────────────────┘
```

### 2. Behavior Defined in Mods/ACLIs
**Everything** is configured in YAML, not code:
- How to pass skills? → `arg_mapping.skills_dir` in ACLI YAML
- How to manage sessions? → `session_arg` template in ACLI YAML
- What hooks to run? → `hooks` in mod YAML
- What models to use? → `model_mapping` in ACLI YAML

**This is what makes UCAS infinitely extensible** - you can add any feature by creating a mod/ACLI with the right YAML, without touching Python code.

### Example: Adding Session Management
❌ **WRONG** (hardcoded):
```python
if acli_name == 'pi':
    cmd += f' --session {session_path}'
elif acli_name == 'claude':
    cmd += f' --session-id {uuid}'
```

✅ **CORRECT** (YAML-driven):
```yaml
# acli-pi/ucas.yaml
acli:
  session_arg: --session "$HOME/.pi/sessions/{uuid}.json"

# acli-claude/ucas.yaml
acli:
  session_arg: --session-id {uuid}
```

```python
# launcher.py - generic interpretation
if 'session_arg' in acli_def:
    session_expanded = expand_session_template(acli_def['session_arg'], context)
    cmd_parts.extend(shlex.split(session_expanded))
```

**Remember**: If you're adding if/elif logic for specific ACLIs or features, you're breaking the architecture. Add a YAML field instead.

## KISS Development Principles

**CRITICAL**: These principles must be followed for ALL development:

1. **YAML-Driven Configuration** - Everything configurable must be in YAML, not hardcoded in Python
   - ✅ GOOD: `session_arg: --session "$HOME/.pi/sessions/{uuid}.json"` in YAML
   - ❌ BAD: Separate `session_path` and `session_arg` fields requiring complex logic

2. **Minimal Run Logic** - The `launcher.py` and `__main__.py` should have minimal hardcoded behavior
   - Configuration defines behavior, code just executes it
   - Use template expansion (`{uuid}`, `{agent}`, `$HOME`) instead of special cases
   - If you need 2+ fields to configure one feature, you're doing it wrong

3. **Template-Based Extensibility** - Use string templates with placeholders for flexibility
   - Support: `{uuid}`, `{agent}`, `{team}`, `{project_root}`, `$HOME`, `$VAR`
   - One template string can express complex patterns
   - Example: `--flag "$HOME/path/{agent}/{uuid}.ext"`

4. **Merge System Handles Structure** - Trust the YAML merge system
   - Nested structures (like `acli:`) merge naturally
   - No special normalization code needed
   - Backward compatibility via helper functions (`get_acli_config()`)

5. **Shell-Correct Syntax** - Use `$HOME` not `~` for variables in command strings
   - `~` only works in interactive shells
   - Use `os.path.expandvars()` for `$VAR` expansion
   - Use `shlex.split()` for proper quote handling

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

# Run with mods (adds to default mods from config)
ucas run basic-chat +mod-git +debug-mod

# Override ACLI (while keeping default mods)
ucas run basic-chat +acli-claude

# Run a team
ucas run-team backend-squad
```

**Default Mods**: You can define default mods in `ucas.yaml` that are automatically included in every run:
```yaml
mods:
  - ucas  # Always included unless overridden
```

## Architecture

UCAS is a **general-purpose merge + interpret engine**. The core modules perform generic operations (merge YAML, expand templates, run commands) without knowledge of specific ACLIs or features.

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

**ucas/launcher.py** - Command building & tmux execution (generic interpretation)
- `select_acli()`: Reads `allowed_acli` list (first = default, single = forced)
- `translate_model()`: Uses ACLI's `model_mapping` to translate models
- `build_command()`: Interprets `arg_mapping` and `session_arg` from ACLI config
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
- `UCAS_SESSION_ID`: Unique UUID4 for the current execution session
- `UCAS_ACLI_EXE`: The resolved ACLI executable
- `UCAS_MAIN_COMMAND`: The full command line used to launch the primary agent

### Lifecycle Hooks

Mods can define executable hooks:
- `install`: Run once in host environment (e.g., `npm install`)
- `prerun`: Run in tmux window before main agent starts
- `postrun`: Run in tmux window after main agent exits

Hook execution chain: `exports && prerun && main_cmd && postrun` (failures stop the chain)

## Mod Organization

### System-Wide Mods (`./mods/`)
- **Location**: `./mods/` in the UCAS repository
- **Purpose**: Reusable mods shared across all projects
- **Examples**: `acli-pi`, `acli-gemini`, `acli-claude`, `mod-git`, `generic`
- **Version Control**: Committed to the UCAS repository

### Project-Specific Mods (`./.ucas/mods/`)
- **Location**: `./.ucas/mods/` in your project directory
- **Purpose**: Project-specific tools and configurations
- **Examples**: `ucas` (for UCAS development), project-specific skills
- **Version Control**: Committed to your project repository
- **Priority**: Searched before system-wide mods

### Default Mods Configuration
You can configure default mods at different levels:
```yaml
# System-wide default: ./ucas.yaml
mods:
  - common-tools

# Project-specific default: ./.ucas/ucas.yaml
mods:
  - ucas  # Project development tools
```

## Entity Types

### Agent Definition
```yaml
name: basic-chat
requested_model: gpt-4
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
# Pi ACLI definition

acli:
  name: acli-pi  # Identifies this ACLI after merge
  executable: pi
  
  arg_mapping:
    prompt_file: --append-system-prompt
    skills_dir: --skill
    model_flag: --model
  
  model_mapping:
    gpt-4: gemini-2.5-flash
    default: gemini-2.5-flash
  
  ignore_unknown: false
  
  # Optional: session management with template expansion
  session_arg: --session "$HOME/.pi/sessions/{uuid}.json"
```

**Note**: 
- `acli.name` field identifies which ACLI was selected after merge
- Directory name (e.g. `mods/acli-pi/`) is used for resolution
- Flat structure (without `acli:` wrapper) is still supported for backward compatibility

**ACLI Selection Logic**:
- Uses first item in `allowed_acli` list as default
- Single item in `allowed_acli` = forced ACLI
- `override_acli` in override file = veto power

**Session Management**: Use `session_arg` with complete argument template including placeholders:
- `{uuid}` - Session UUID (UCAS_SESSION_ID)
- `{agent}` - Agent name
- `{team}` - Team name (if applicable)
- `{project_root}` - Project root directory
- `$HOME`, `$VAR` - Environment variables

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

1. **KISS - YAML-driven configuration** - All behavior defined in YAML, minimal hardcoded logic
2. **Template-based extensibility** - Use `{placeholders}` and `$VAR` for flexible configuration
3. **No external dependencies** - Python 3.6+ stdlib only
4. **Skills as arguments** - No PATH manipulation, passed via `arg_mapping.skills_dir`
5. **First match wins** - Entity search stops at first found directory
6. **Dynamic path expansion** - Agents/mods can add search paths during resolution
7. **Last wins merge** - Later layers override earlier ones (except with override files)
8. **Skills/Hooks aggregated** - All `skills/` directories and `hooks` commands are collected
9. **Nested structure support** - `acli:` block for clear separation, backward compatible with flat

## Common Patterns

### Adding a New Agent
1. Create directory in `mods/<agent-name>/`
2. Add `ucas.yaml` with `name`, `requested_model`
3. Optionally add `PROMPT.md` for system prompt
4. Optionally add `skills/` directory for tools

### Adding a New Mod
1. Create directory in `mods/<mod-name>/`
2. Add `ucas.yaml` with `name`, `description`
3. Optionally add `PROMPT.md` for additional instructions
4. Optionally add `skills/` directory for additional tools
5. Optionally add `hooks` for lifecycle automation

### Adding a New ACLI
1. Create directory in `mods/<acli-name>/`
2. Add `ucas.yaml` with nested `acli:` structure:
   ```yaml
   # My Agent ACLI definition
   
   acli:
     name: acli-myagent  # Identifies this ACLI after merge
     executable: myagent
     arg_mapping:
       prompt_file: --system-prompt
       skills_dir: --tools
       model_flag: --model
     model_mapping:
       gpt-4: my-agent-premium
       default: my-agent-free
     ignore_unknown: false
     
     # Optional: session management
     session_arg: --session "$HOME/.myagent/sessions/{uuid}.json"
   ```
3. `acli.name` identifies the ACLI post-merge; directory name (e.g., `mods/acli-myagent/`) is used for resolution
4. Use `$HOME` not `~` for environment variables in templates
5. Use template placeholders: `{uuid}`, `{agent}`, `{team}`, `{project_root}`
6. **CRITICAL**: Keep it KISS - `session_arg` should be complete argument string, not split into multiple fields

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
