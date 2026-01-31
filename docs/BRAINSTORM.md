# UCAS: Technical Specification v1.0 (Master Edition)

## 1. Philosophy and Role

**UCAS** (Universal CLI Agent System) is an **intelligent assembler** and **launcher**.

*   **Role:** To find definitions (Agent, Mod, ACLI), merge them according to priority, build an execution command, and run it in `tmux`.
*   **Principle:** Strict separation of Data (Agent) from the Tool (ACLI).
*   **Architecture:** Three layers (Project > User > System).

---

## 2. Command Line (CLI)

The program is invoked as `ucas` with the following syntax:

### Commands

1.  **Run an Agent:**
    ```bash
    ucas run [AGENT_NAME] +[MOD1] +[MOD2] ... [OPTIONS]
    # Example: ucas run php-master +git-mod +acli-claude --debug
    ```

2.  **Run a Team:**
    ```bash
    ucas run-team [TEAM_NAME] [OPTIONS]
    # Example: ucas run-team backend --dry-run
    ```

### Switches (Options)

*   `--dry-run`: **Simulation.** Performs the entire process of searching, merging, and generating the prompt, but **does not start tmux**. It prints the final assembled command to stdout (for verification).
*   `--debug`: **Verbose mode.** Prints detailed logic of the "Sandwich Merge" (which file overrode which key, where each skill was found).

---

## 3. Directory Structure (The Three-Layer Database)

UCAS searches for configurations in this priority order (from highest to lowest).

### 1. Layer: PROJECT (Local Context)

*Highest priority. Specific to the current task.*
**Path:** `./.ucas/` (in the current directory)

```text
./.ucas/
├── ucas.yaml               # Project Base (Env, Defaults)
├── ucas-override.yaml      # Project Veto (Override ACLI)
├── tmp/                    # (Auto) Generated prompts (karel.merged.md)
├── mem/                    # (Auto) Agent memory
├── teams/                  # Local teams
└── agents/                 # Local mods and agents
```

### 2. Layer: USER (Personal Config)

*Medium priority. User's personal settings.*
**Path:** `~/.ucas/`

```text
~/.ucas/
├── ucas.yaml               # User Defaults
├── ucas-override.yaml      # User Veto
├── teams/                  # Global teams
└── agents/                 # Personal library
```

### 3. Layer: SYSTEM / REPO (Factory Defaults)

*Lowest priority. Distribution base.*
**Path:** `/opt/ucas/` (or `$UCAS_HOME`)

```text
$UCAS_HOME/
├── ucas.yaml               # System Defaults (allowed_acli, default_acli)
├── ucas-override.yaml      # System Veto (rarely used)
├── teams/                  # Example teams
└── agents/                 # System Library
    ├── acli-claude/        # ACLI for Claude
    ├── acli-zai/           # ACLI for Z.AI
    ├── basic-chat/         # Default agents
    └── utils/              # Common mods
```

---

## 4. Entities and Definitions

### I. AGENT (The Know-How)

Pure data. **Has no `executable`.**

*   **Contents:** `PROMPT.md`, `skills/` (scripts), `ucas.yaml`.
*   **Example `ucas.yaml`:**
    ```yaml
    default_acli: "acli-claude"   # Agent's preference (must be in allowed_acli)
    ```

*Note: Models are handled by the ACLI, not the agent. The Agent says WHAT it wants to do, the ACLI handles HOW.*

*   **Skills:** Each agent can have a `skills/` directory - all are aggregated into the PATH.

### II. MOD (The Overlay)

**Any agent can be used as a mod.** It has the same structure as an agent. Used to layer capabilities onto another agent.

### III. ACLI (The Runner)

A tool abstraction. **Identified by the presence of the `executable` key.**

*   **Contents:** `ucas.yaml` with an executable, argument mapping, and model mapping.
*   **Example `ucas.yaml`:**
    ```yaml
    executable: "claude"     # The presence of this key = ACLI
    arg_mapping:
      prompt_file: "--system"
      skills_dir: "--tools"
      model_flag: "--model"

    model_mapping:
      # Agent requests → ACLI receives
      "gpt-5.2-pro": "opus-4.5"
      "codex": "opus-4.5"
      "gpt-4": "sonnet-3.5"
      "default": "sonnet-3.5"    # Fallback when no mapping exists
    ```

### Model Mapping - Logic

UCAS translates the agent's model request to one supported by the selected ACLI:

```
1. Agent has: requested_model: "gpt-5.2-pro"
2. Selected ACLI has: model_mapping
3. UCAS translates: "gpt-5.2-pro" → "opus-4.5"
4. Resulting command: claude --model opus-4.5 --system ...
```

### Example: A "Cheap" Claude ACLI

A user can create their own ACLI variant to save costs:

```yaml
# ~/.ucas/agents/acli-claude-cheap/ucas.yaml
executable: "claude"
arg_mapping:
  prompt_file: "--system"
  model_flag: "--model"

model_mapping:
  # Map everything to Haiku = cheap
  "opus-4.5": "haiku-3.5"
  "sonnet-3.5": "haiku-3.5"
  "gpt-5.2-pro": "haiku-3.5"
  "default": "haiku-3.5"
```

Then in the project:
```yaml
# ./.ucas/ucas.yaml
allowed_acli: ["acli-claude-cheap"]
```

And all agents in this project will run on Haiku, regardless of their `requested_model`.

*Note: An ACLI is just an agent with an `executable` → it can be defined at any layer (system/user/project). A project can redefine `acli-claude-cheap` for its own purposes without affecting other projects. Search order: Project → User → System, first one found wins.*

---

## 5. Priority Logic (The Sandwich Merge)

UCAS loads configurations and performs a `dict.update` (each subsequent layer overrides previous values).

### Complete Stack (in loading order)

```
LOAD ORDER (last one wins):

 1. $UCAS_HOME/ucas.yaml        # System Defaults
 2. ~/.ucas/ucas.yaml           # User Defaults
 3. team/ucas.yaml              # Team config (only for run-team)
 4. ./.ucas/ucas.yaml           # Project Defaults
 5. agent/ucas.yaml             # Main agent
 6. mod1/ucas.yaml              # First mod from CLI
 7. mod2/ucas.yaml              # Second mod from CLI (overrides mod1)
 8. ...                         # Other mods in order from CLI args
────────────────────────────────────────────────────
 9. $UCAS_HOME/ucas-override.yaml   # System Veto
10. ~/.ucas/ucas-override.yaml      # User Veto
11. ./.ucas/ucas-override.yaml      # Project Veto (STRONGEST)
```

### Rules (clearly defined merge behavior)

*   **General rule for YAML keys:** "last wins" — values from a later-loaded layer overwrite previous ones (dict.update style). This applies to standard scalar/dict keys.
*   **Lists / special fields:**
    *   `skills` (directories) are **aggregated** (all are collected). Each `skills` directory gets its own CLI argument according to the `acli.arg_mapping`, and these arguments are combined/merged as defined by the ACLI.
    *   `allowed_acli`: Behaves according to KISS - if a project explicitly sets it, that list is used (it overrides). If the project defines nothing, a union of user+system is used.
*   **Mods:** Mods are applied in the exact order they are listed on the CLI; for conflicts, the "last wins" rule applies.
*   **Override layers (9-11):** These are always applied at the end and have the power to force values (the project override is the strongest). Override files can contain any keys; we will monitor usage in practice and potentially introduce `override_*` conventions.
*   **Team layer (3):** Only used with `ucas run-team`.
*   **Entity search:** An Agent/Mod is searched for in Project → User → System (first-found wins when searching for files). When an entity is found, its `ucas.yaml` is loaded according to the LOAD ORDER, and its values are applied according to the rules above.

---

## 6. ACLI Selection Logic (The Selector)

Everything is resolved within a single **Merged Config** while respecting the available CLI tools.

### Configuration

```yaml
# ~/.ucas/ucas.yaml (User)
allowed_acli: ["acli-claude", "acli-zai"]  # What I have paid for/available
default_acli: "acli-claude"                 # My preference

# ./.ucas/ucas.yaml (Project)
allowed_acli: ["acli-zai"]                  # Restriction for this project
```

### Resolution (Evaluation)

After the complete Sandwich Merge, a `final_config` is created. The ACLI selection proceeds as follows (precisely and deterministically):

1.  `override_acli` present?
    → If set (in any `ucas-override.yaml`), it is used without checking `allowed_acli` (veto power).

2.  `executable` already in `final_config`?
    → If yes (perhaps because the user specified `+acli-xxx` on the CLI), it's considered a candidate — next, we verify the binary exists (see error handling).

3.  `default_acli` from the agent?
    → If it exists and is in `allowed_acli`, it is used. If not in `allowed_acli`, continue.

4.  `default_acli` from user/project?
    → If it exists and is in `allowed_acli`, it is used.

5.  Fallback: the first item from `allowed_acli` (if none of the above matched).

6.  If no ACLI is found → ERROR.

Further notes:
-   `+acli-xxx` from the CLI is treated like any other mod: its `ucas.yaml` is added to the load sequence, and the final selector decides (KISS).
-   If the selected ACLI contains an `executable`, UCAS verifies that the binary is available. If not, the default behavior is a fatal `error`. (Future fallback mechanisms can be added later.)
-   `model_mapping`: If the ACLI doesn't have a mapping for the requested model and the `default` key does not exist:
    -   `ignore_unknown: false` (or missing) → **ERROR** (fatal, UCAS will not run the ACLI)
    -   `ignore_unknown: true` → does not pass the model flag to the CLI + **logs a WARNING** (the ACLI will use its own default model)

### Usage Examples

**Agent wants Codex, but I only have Claude and Z.AI:**
```
Agent:   default_acli: "acli-codex"
User:    allowed_acli: ["acli-claude", "acli-zai"]
→ Codex is NOT in allowed → fallback to acli-claude
```

**Agent wants Claude, and I have it:**
```
Agent:   default_acli: "acli-claude"
User:    allowed_acli: ["acli-claude", "acli-zai"]
→ Claude IS in allowed → Claude is used
```

**Fun project - only cheap CLIs:**
```
Project: allowed_acli: ["acli-zai"]
Agent:   default_acli: "acli-claude"
User:    allowed_acli: ["acli-claude", "acli-zai"]
→ Project overrode user's allowed list → Claude is NOT allowed → fallback to acli-zai
```

**Forcing a specific CLI:**
```
Project: override_acli: "acli-zai"
Agent:   default_acli: "acli-claude"
→ Override = veto → acli-zai is used (regardless of allowed)
```

**ACLI Detection:** An entity is an ACLI if its `ucas.yaml` contains the `executable` key.

---

## 7. Execution Algorithm (The Workflow)

**Input:** `ucas run php-master +git-mod --dry-run`

### Step 1: Resolver (Search)

*   Recursively searches the `agents` folders in all 3 layers.
*   Finds the paths to `php-master` and `git-mod`.

### Step 2: Merge (The Brain)

*   **ENV:** Merges ENV variables from all layers (Sandwich).
*   **SKILLS:** Finds `skills/` folders in the Agent and Mods and **aggregates** them (all are added). Each `skills` directory gets its own CLI argument based on `acli.arg_mapping`, and these CLI arguments are combined as defined by the ACLI.
*   **PROMPT:** Concatenates the `PROMPT.md` files of the Agent and Mods with a `---` separator, in order: agent (base) → mod1 → mod2 … (i.e., CLI order). We do not support "patch/replace" for prompts in the MVP — only concatenation.
*   **ACLI:** Selects the winning ACLI mod according to the selection logic (see below) and loads its mappings.

### Step 3: Generate (Artifacts)

*   Saves the merged prompt to `./.ucas/tmp/[session].merged.md`.
*   Constructs the `$PATH` from the `skills` directories so that the "later mod on CLI has priority" rule holds. In practice, this means: modifiers are added to PATH in reverse CLI order (so the last mod on the CLI is added first to the PATH), followed by the `agent` skills, and then the existing `$PATH`. This ensures that files in a later mod shadow files in earlier mods.

### Step 4: Launch (Tmux/Dry-Run)

*   Loads the definition of the winning ACLI (`executable` + `arg_mapping`).
*   Substitutes the generated paths into the arguments.
*   **If `--dry-run`:** Prints the exact assembled command to stdout, including the complete `PATH` export and all used CLI arguments, and then exits.
*   **If Run:** UCAS attempts to run the command in a wrapper (default is `tmux`).
    *   UCAS verifies `tmux` is available before running. If `tmux` is not installed → fatal error.
    -   Implementation-wise, we maintain a wrapper abstraction (`tmux` is just one wrapper). The wrapper could be defined at the project/user level in the future, so `tmux` could be replaced with another mechanism without changing the command-building logic.
    -   Example of what the call will look like (the exact command printed in `--dry-run`):
      ```bash
      export PATH=/path/to/last-mod-skills:/path/to/prev-mod-skills:/path/to/agent-skills:$PATH; claude --system ./.ucas/tmp/merged.md --tools /path/to/skills1 --model opus-4.5
      ```

---

## 8. Teams (Orchestration)

*   **Command:** `ucas run-team [TEAM_NAME]`
*   **Definition:** A YAML file at `teams/[TEAM_NAME]/ucas.yaml`.
*   **Structure:**
    ```yaml
    name: "backend-squad"
    members:
      karel:
        agent: "php-master"
        mods: ["git-mod", "debug-mod"]
      pepa:
        agent: "sql-guru"
    ```

*   **Process:** Iterates through the members and runs the **Execution Algorithm** (steps 1-7) for each one sequentially (one after another), not in parallel. This behavior prevents a large number of agents from starting at once and overloading the desktop.
    *   A `sleep` (delay) between starts is possible, configurable at the project/team/user level (e.g., `team.sleep_seconds: 5`). Defaults to no delay if the member configuration specifies nothing.
    *   Each member gets its own window/output according to the wrapper (tmux). If a window with the same name exists, UCAS creates a new window with an added timestamp to avoid collisions.

---

## 9. Technical Requirements

### Python Compatibility

*   **Minimum version:** Python 3.6+
*   **No external dependencies** - only the stdlib.

### Mini YAML Parser

A custom YAML parser implementation (no PyYAML dependency). The goal is KISS — supporting only the necessary constructs with clear error messages.

Supported behavior and syntax:
-   Indentation with spaces only (tabs are forbidden)
-   Flow-style lists (inline): `[a, b, c]`
-   Simple dicts and lists (nested)
-   Strings (with/without quotes)
-   Booleans (true/false/yes/no)
-   null
-   Comments (#)

Explicitly unsupported:
-   Multiline strings are not supported (`PROMPT.md` is used for multilines)
-   Anchors/aliases are not supported
-   Complex keys and YAML tags are not supported

The parser must be strict and return clear errors with line numbers. KISS: a minimal, deterministic subset of YAML, sufficient for `ucas.yaml` configurations. Inline dictionaries `{k: v}` are not needed for the MVP (can be added later if needed).

---

## 10. Implementation Plan (MVP Scope)

### `yaml_parser.py` Module

*   Mini YAML parser (see section 9)
*   `parse(text) -> dict`: Main function

### `cli.py` Module

*   Parse CLI arguments (argparse)
*   Distinguish `run` vs `run-team` commands
*   Extract agent name, mods (`+mod`), and flags (`--dry-run`, `--debug`)

### `resolver.py` Module

*   `find_entity(name)`: Search in layers Project → User → System (first one found wins)
*   `is_acli(entity)`: Detect ACLI by the presence of the `executable` key

### `merger.py` Module

*   `load_sandwich(agent, mods, is_team)`: Load configs in the correct order (1-11)
*   `merge_configs(configs)`: Update dicts, aggregate skills paths

### `launcher.py` Module

*   `select_acli(merged_config, cli_mods)`: Priority-based ACLI selection (section 6)
*   `build_command(acli, merged_config)`: Substitute into `arg_mapping`
*   `generate_prompt(agent, mods)`: Concatenate PROMPT.md files
*   `run_tmux(command, name)`: Run in a new tmux window

### MVP Scope

-   `ucas run [agent] +[mod]` - run an agent
-   `ucas run-team [team]` - loop through members, internally calls `run()`
-   `--dry-run` - print command without execution
-   `--debug` - verbose merge tracing
-   Three-layer entity searching
-   Complete sandwich merge

# IDEAS + EXAMPLES

-   use Dippy for message injection into all supported agents?
    -   dippy has support for multiple CLIs
    -   maybe it could return additional info about the message

## Example `ucas-override.yaml` (project-level — forces an ACLI)
```yaml
# ./.ucas/ucas-override.yaml
# Forces claude with Haiku in the project
override_acli: "acli-claude-cheap"
# Optionally, ignore_unknown: true allows not passing unknown models
ignore_unknown: true
```

## Example `ucas-override.yaml` (user-level)
```yaml
# ~/.ucas/ucas-override.yaml
# Default is claude, but allow claude-zai if someone requests it
allowed_acli: ["acli-claude", "acli-claude-zai"]
# will error if it doesn't find a model mapping
ignore_unknown: false
```

Note: these examples serve as a reference; override files can contain any keys and will be applied last (project override is the strongest). It is recommended to monitor real-world usage and potentially add standardized `override_*` keys in the future.
