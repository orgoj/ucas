# UCAS - Universal CLI Agent System

### Core Philosophy & Goal

UCAS (Universal CLI Agent System) is built on the **"Keep It Simple, Stupid" (KISS)** principle. Its primary goal is to provide a straightforward, vendor-agnostic way to define, run, and share conversational AI agents and teams.

The project was born out of frustration with the current landscape of agent CLIs, each with its own proprietary skill marketplaces, configuration formats, and limitations. UCAS aims to be the "glue" that binds them, focusing on three key areas:

1.  **Portability and Reusability**: Agents and teams are defined in a simple, human-readable `ucas.yaml` format. This allows entire agent/team setups to be archived, shared, and version-controlled with ease.
2.  **Zero-Friction Automation**: The system is designed to automate as much of the setup process as possible, eliminating manual steps and ensuring consistency.
3.  **Flexible Orchestration**: Easily run single agents, agents with modifications ("mods"), or complex multi-agent "teams" in a coordinated manner.

> [!IMPORTANT]
> **The UCAS Differentiator: Dynamic CLI Composition**
> Unlike any other tool, UCAS allows **ad-hoc behavior modification** at the command line. Run `ucas run generic +git +webresearch` and the system dynamically aggregates the models, parameters, environment variables, and skills at execution time. No need to modify a single configuration file to experiment with different agent capabilities.

By standardizing the definition and launch process, UCAS enables developers to build and reuse agent configurations across different projects and platforms without being locked into a single vendor's ecosystem.

---

### Primary Use Case: One-Command Developer Onboarding

The power of UCAS's automation is best illustrated by the developer onboarding scenario. The goal is to get a new team member productive immediately through a "clone and go" workflow:

1.  A developer installs the `ucas` binary (a single, one-time setup).
2.  They clone a project repository managed by UCAS.
3.  They run a single command: `ucas start`.

This one command triggers the full automation pipeline: UCAS discovers all required agents for the project, automatically fetches any that are missing from local or remote sources (like a corporate git repository), and runs each agent's self-initialization process to install its dependencies.

The result is a perfectly replicated, fully-functional development environment identical to everyone else's on the team, achieved with zero manual configuration within the project.

---

### Scenario 2: Bootstrapping a New Project with a Shared Team

UCAS also accelerates the creation of new projects. Instead of building from scratch, you can leverage a library of pre-defined, shareable teams:

1.  Start a new project: `mkdir my-new-app && cd my-new-app`.
2.  Find a public or private repository containing a UCAS team definition (e.g., `github.com/some-org/ucas-dev-team`).
3.  Add this team to your project with a simple command, like `ucas team-add github.com/some-org/ucas-dev-team`.
4.  Run `ucas start`.

Just as in the first scenario, UCAS takes over. It downloads the team definition, fetches all the specified agents, and runs their initial setup. In minutes, you have a sophisticated, multi-agent system running in your new project, ready for customization.

This workflow makes it possible to create and share team definitions for any purpose—be it open-source, internal corporate use, or personal projects—drastically reducing the time it takes to start a new endeavor.

---

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

UCAS uses a multi-layer "Sandwich Merge" system to build the final configuration. Layers are applied from bottom to top, with later layers overriding earlier ones.

```
      ▲  TOP (Overrides - Highest Priority)
      │
  [ Project Override: ./.ucas/ucas-override.yaml ]
  [ User Override:    ~/.ucas/ucas-override.yaml    ]
  [ System Override:  $UCAS_HOME/ucas-override.yaml ]
      │
//---- Final Merged Config is Assembled Here ----\\\\
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

### 🚀 Dynamic CLI Composition (Killer Feature)
UCAS stands alone in its ability to compose behaviors at the command line. Instead of creating 50 different config files for every permutation of skills, you maintain small, focused components and layer them as needed:

```bash
# Ad-hoc skill aggregation:
ucas run generic +git +webresearch
```
UCAS dynamically merges the system prompts, aggregates tool directories, and maps environmental variables from all components into the final process.

### 🛡️ Execution Wrappers (Freedom of Transport)
UCAS treats the execution environment as a first-class citizen. Want to run an agent in a specific `tmux` pane, over an `ssh` tunnel, or inside a temporary `docker` container? Just specify the wrapper in your configuration layering.

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

## Roadmap

UCAS is actively developed. Here are some of the key features and improvements planned for the near future, reflecting the project's goal of total automation:

-   **Enhanced CLI Commands:**
    -   `ucas init`: To quickly scaffold a `.ucas` directory and configuration in a new project.
    -   `ucas status`: To display a summary of the project's configuration, resolved paths, and available agents/teams.
    -   `ucas list-agents` / `ucas list-teams`: To discover available entities.
    -   `ucas team-add <repo>`: To easily import team definitions from remote repositories.

-   **Automatic Agent Installation:**
    -   Agents will be able to define their own dependencies and installation steps.
    -   On first run, `ucas` will trigger an agent's self-initialization process, fully automating its setup.

-   **Smarter Team Management:**
    -   Team definitions will support specifying agent sources (e.g., Git repositories), allowing `ucas` to automatically clone them if they are not found locally.
    -   A pre-flight check will validate a team's integrity before launching.

-   **Policy and Security:**
    -   Configuration options like `allow_agents` and `deny_agents` to enforce policies on which agents are permitted to run.
    -   Allow install

## License

MIT
