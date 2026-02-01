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
ucas run basic-chat +mod-git +debug-mod

# Run a team
ucas run-team backend-squad

# Dry-run (show command without executing)
ucas run basic-chat --dry-run

# Debug mode (verbose merge tracing)
ucas run basic-chat --debug
```

## Project Structure

```
├── mods/                    # System Library (Agents, Mods, and definitions)
│   ├── acli-claude/
│   │   └── ucas.yaml
│   ├── basic-chat/
│   │   ├── ucas.yaml
│   │   └── PROMPT.md
│   ├── mod-git/
│   │   ├── ucas.yaml
│   │   ├── PROMPT.md
│   │   └── skills/
│   ├── msg-mcp_agent_mail/  # Messaging between agents
│   │   ├── ucas.yaml
│   │   ├── README.md
│   │   └── skills/
└── ucas.yaml                # System defaults (can also define teams)
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

### Custom Mod Search Paths

You can expand the mod search library by defining `mod_path` in any `ucas.yaml` file.

```yaml
# ./.ucas/ucas.yaml
mod_path:
  - ./external-mods
  - /opt/shared/ucas-library
```

Behavior:
1. **Dynamic Expansion**: If an agent or a mod defines `mod_path`, those paths are added to the search list for subsequent mod resolutions.
2. **Relative Paths**: Paths defined in a mod's `ucas.yaml` are relative to that mod's directory. Paths in project/user/system configs are relative to the project root.
3. **Strict Mode**: Set `strict: true` in a config layer to disable searching in User and System layers.

```yaml
# strict project-only mode
strict: true
```

**System Layer Auto-Detection:**
- If `UCAS_HOME` is set, uses `$UCAS_HOME/mods/`
- If not set, uses `<package-install-dir>/mods/`
- This means UCAS_HOME is **optional** - it auto-discovers system agents

## Merge Strategies

By default, UCAS uses "Last Wins" for scalars and "Recursive Merge" for dictionaries. However, you can explicitly control the merge behavior for any key using suffixes:

| Suffix | Strategy | Behavior |
| :--- | :--- | :--- |
| `key+` | **Merge/Append** | Concatenates lists; deep merges dictionaries. |
| `key-` | **Remove** | Removes items from a list or keys from a dictionary/scalar. |
| `key!` | **Override** | Forces replacement of the base value. |
| `key?` | **Default** | Sets the value only if the key is missing in the base. |
| `key~` | **Update** | Sets the value only if the key already exists in the base. |

> [!IMPORTANT]
> **Minimalist (Dumb) Merge Philosophy**: UCAS does not automatically assume any merge strategy based on the key name (e.g., `skills` or `hooks` are no longer auto-appended). If you want to merge or append, you **must** use the explicit suffixes (`+`, `-`, etc.). Otherwise, the standard rule applies: scalar/list overwrite, dictionary deep merge.

**Example:**
```yaml
# Layer 1 (Base)
l1: [a, b]
o1: { a: 1 }

# Layer 2 (Overlay)
l1+: [c]       # Result: l1: [a, b, c]
o1-: [a]       # Result: o1: {}
new_val?: 42   # Result: new_val: 42
```


## Key Features

### 🚀 Dynamic CLI Composition (Killer Feature)
UCAS stands alone in its ability to compose behaviors at the command line. Instead of creating 50 different config files for every permutation of skills, you maintain small, focused components and layer them as needed:

```bash
# Ad-hoc skill aggregation:
ucas run generic +git +webresearch
```
UCAS dynamically merges the system prompts, aggregates tool directories, and maps environmental variables from all components into the final process.

### 🛡️ Run Mods (Execution Wrappers)
UCAS treats the execution environment as a first-class citizen through "Run Mods". This generalizes how commands are launched, allowing for flexible orchestration like running in `tmux`, `bash`, or even custom Python scripts. 

A run-mod is a mod that defines a `run:` block:
```yaml
run:
  name: my-runner
  script: ./runner.py  # Relative to mod dir
```

When an agent is launched, the selected run-mod's script or template is executed, and it is responsible for the final command invocation. This allows for total freedom of transport (SSH, Docker, Screen, etc.) defined entirely in YAML.

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
ucas run basic-chat +mod-git +docker-mod
# Results in: --tools /path/to/basic-chat/skills --tools /path/to/mod-git/skills --tools /path/to/docker-mod/skills
```

### Lifecycle Hooks
Mods can define executable hooks to automate setup and execution flows:
- `install`: Run once in the host environment (useful for `npm install` etc).
- `prerun`: Run in the tmux window immediately before the main agent starts.
- `postrun`: Run in the tmux window after the main agent exits.

### Execution Context (Environment Variables)
UCAS injects the following context into all hooks and the main process:
- `UCAS_AGENT`: Current agent name.
- `UCAS_TEAM`: Current team name (if running as part of a team).
- `UCAS_AGENT_DIR`: Absolute path to the mod's definition directory.
- `UCAS_AGENT_NOTES`: Project-specific storage path (`./.ucas/notes/<agent>/`).
- `UCAS_PROJECT_ROOT`: Absolute path to the current project.
- `UCAS_SESSION_ID`: Unique ID for the current execution session.
- `UCAS_ACLI_EXE`: The resolved ACLI executable.
- `UCAS_MAIN_COMMAND`: The full command line used to launch the primary agent.
- `UCAS_RUN_DIR`: Absolute path to the directory where the active `run-mod` is defined.

```

### Run Mod Selection
Similar to ACLIs, the runner is determined by:
1. `override_run` (veto power)
2. `run.name` (if the merged entity defines a runner)
3. First item in `allowed_run` list (= default)

```yaml
# ucas.yaml defaults
allowed_run:
  - run-bash
  - run-tmux
```

## Example Configurations

### Agent Definition
```yaml
# mods/basic-chat/ucas.yaml
name: basic-chat
requested_model: gpt-4
```

### Mod Definition
```yaml
# mods/mod-git/ucas.yaml
name: mod-git
description: Adds git operation capabilities
```

### Run Mod Definition
Run mods can use templates or scripts. Python scripts are recommended for cross-platform portability.

#### Template-based
```yaml
run:
  name: run-bash
  template: |
    bash -c "{cmd}"
```

#### Script-based (with CLI args)
```yaml
run:
  name: run-tmux
  script: ./tmux_runner.py

mods+:
  - name: run-tmux
    description: Execute commands in a new tmux window
```
Data is passed to scripts via CLI flags: `--cmd`, `--agent`, `--team`, `--project-root`, `--session-id`, `--session-name`, `--window-name`.

### Team Definition
Any mod can define a team orchestration by including a `team` key in its `ucas.yaml`:

```yaml
# team-alpha/ucas.yaml
team:
  mods: [messaging-mod] # Global mods for all members
  agents:
    karel:
      mods: [basic-chat, api-mod, mod-git]
      # other member flags can go here
    lucie:
      mods: [basic-chat, aws-mod]
```

Executing a team:
```bash
ucas run-team backend-squad
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
3. **First match wins** - Entity search for mods/agents stops at first found directory. Default order: Project → Custom Paths → User → System.
4. **Dynamic Path Expansion** - Agents and mods can add new search paths during resolution via `mod_path: []`.
5. **Mod-based Teams** - A team is just a mod containing a `team` definition. It follows the standard Sandwich Merge.
6. **No Hardcoded Merge Strategies** - UCAS is "dumb" and requires explicit suffixes (`+`, `-`, etc.) for any non-default merging.
7. **Mod Tracking** - Every applied mod contributes its metadata to a cumulative `mods` list in the final configuration.

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
