# UCAS Configuration Reference (ucas.yaml)

UCAS uses `ucas.yaml` files at multiple layers (System, User, Project, Agent, Mod). These files are merged using a **Sandwich Merge** strategy.

## Merge Strategies (Key Suffixes)
You can control how individual keys are merged by adding a suffix to the key:

| Suffix | Name | Description |
|--------|------|-------------|
| (none) | Merge | Merges dictionaries or overwrites single values (default). |
| `+` | Add | Appends to lists or merges dictionaries. |
| `-` | Remove | Removes items from lists or keys from dictionaries. |
| `!` | Force | Explicitly overwrites whatever was there before. |
| `?` | Default| Sets the value only if it doesn't already exist. |
| `~` | Update | Sets the value only if it *does* already exist. |

Example: `mods+:` appends to the existing mod list.

---

## Top-Level Keys

| Key | Type | Description |
|-----|------|-------------|
| `name` | string | Unique identifier for the mod or agent. |
| `description`| string | Human-readable explanation (shown in `ls-mods`). |
| `strict` | boolean| If `true` in project/system layers, disables User/System discovery. |
| `mod_path` | string/list| Extra directories to search for mods. |
| `mods` | list | List of mod names to load. |
| `env` | dict | Environment variables to inject into the session. |
| `prompt` | string | Base instruction text (often in agent configs). |
| `model` | string | Suggested model (e.g., `claude-3-5-sonnet`). |
| `provider` | string | Suggested provider (e.g., `anthropic`). |
| `mails` | boolean| Enables `.ucas/mails` for the project if set to `true`. |
| `mail-addressbook` | dict | Custom contacts mapping `address: description`. |
| `team_autostart` | boolean| If `true`, automatically runs `ucas team run` when mail arrives and no team is running. |

---

## Special Configuration Blocks

### `acli` (CLI Adapter)
Defines how to translate agent intent into a specific CLI command.
- `executable`: Path to the CLI tool (e.g., `pi`).
- `prompt_arg`: Flag for passing the prompt (e.g., `--prompt`).
- `prompt_file`: Alternative flag for passing prompt via a temporary file.
- `provider_flag`: Flag for provider selection.
- `model_flag`: Flag for model selection.
- `skills_dir`: Flag for passing skill directories.
- `session_arg`: Template for session persistence (e.g., `--session-id {uuid}`).
- `model_mapping`: Dictionary for translating UCAS model names to CLI-specific names.
- `ignore_unknown`: If `true`, passes unknown models through without error.

### `run` (Execution Layer)
Defines where and how the final command is executed.
- `template`: Shell command template using `{cmd}` (e.g., `xterm -e {cmd}`).
- `script`: Path to a Python script that handles execution (e.g., `tmux_runner.py`).
- `executable`: Path to a binary that handles execution.
- `stop_template`: Command to kill the session.
- `stop_script` / `stop_executable`: Scripts/bins for cleanup.
- `single`: If `true`, this runner cannot be used for teams.

### `team` (Group Definition)
Defines a group of agents working together.
- `name`: Override name for the team.
- `agents` / `members`: Dictionary mapping `member_name: spec`.
    - Spec can be a string (agent name), list (agent + mods), or dict.
- `mods`: Team-wide mods applied to all members.
- `prompt`: Team-wide instruction prepended to all members.
- `sleep_seconds`: Delay between starting each team member.

### `hooks` (Lifecycle)
Commands executed at specific stages.
- `install`: Run once when the agent/mod is first used.
- `prerun`: Run before the main command in every session.
- `postrun`: Run after the main command exits.

---

## Variables and Expansion

- `__DIR__`: Inside any `ucas.yaml`, this string is replaced by the absolute path to the directory containing that file.
- `$VAR` / `${VAR}`: Environment variables (including standard UCAS variables like `UCAS_AGENT`, `UCAS_PROJECT_ROOT`) are expanded in prompts and templates.

### Session Templates
The `acli.session_arg` and `run.template` support:
- `{uuid}`: Session UUID.
- `{agent}`: Agent name.
- `{team}`: Team name.
- `{project_root}`: Absolute project path.
- `{cmd}`: The final assembled command (run templates only).
- `{window_name}`: Generated window ID for terminal muxers.
- `{session_name}`: Generated session ID (often `project-team`).
