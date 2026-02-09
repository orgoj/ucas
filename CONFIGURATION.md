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
| `mail` | dict | Mail system configuration (see `mail` block below). |

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

### `mail` (Mail System)
Configuration for the built-in mail system.
- `notifications`: Notification settings for new mail.
    - `on_new_mail`: Command template to execute when USER receives new mail.

**Notification placeholders**: The `on_new_mail` template supports these variables:
- `{subject}` - Email subject line
- `{from}` - Sender address
- `{id}` - Message ID
- `{date}` - Date string

**Example configuration**:
```yaml
mail:
  notifications:
    on_new_mail: "notify-send 'UCAS Mail' '{subject} from {from}' -u normal"
```

**Note**: Notifications are only triggered for the `USER` agent, not for other agents.

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

---

## Project Management Configuration

UCAS includes a project management system for tracking and managing multiple UCAS projects.

### Project Registry

The registry is stored at `~/.ucas/projects.yaml` and contains a minimal mapping of project aliases to paths:

```yaml
version: "1.0"
projects:
  - alias: myproject
    path: /home/user/work/myproject
```

**Registry Fields:**
- `alias`: Unique identifier used by commands (e.g., `ucas term myproject`)
- `path`: Absolute path to the project directory

All other project metadata (description, tags, team status) is stored in the project's `.ucas/ucas.yaml`.

### Project Configuration Keys

These keys can be added to `.ucas/ucas.yaml` for project management:

| Key | Type | Description |
|-----|------|-------------|
| `description` | string | Human-readable project description |
| `tags` | list | Project tags for categorization and autostart |
| `team_started` | string | Track last running team (NONE = not running) |

### Tags

Tags can be simple strings or objects with team specification:

```yaml
tags:
  - dev                                    # Simple tag
  - {name: autostart, team: DEFAULT}     # Tag with team
```

- **Simple tag**: Just a label for categorization
- **Tag with team**: Specifies which team to start when using `ucas autostart`

### Commands

#### `ucas init` [--non-interactive]

Initialize a UCAS project in the current directory.

**Interactive prompts:**
1. Project description (optional)
2. Gitignore strategy (A=all, B=selective, C=none)
3. Open editor (y/N)

**Actions:**
- Creates `.ucas/` directory
- Creates `.ucas/ucas.yaml` with default team
- Creates `.ucas/.gitignore` based on strategy
- Registers project in `~/.ucas/projects.yaml`

#### `ucas list` [--json] [--running] [--agents]

List all registered projects.

**Output:** Table with ALIAS, PATH, DESCRIPTION, TAGS, TEAM columns
- `--json`: Output as JSON
- `--running`: Show only projects with running teams (team_started != NONE)
- `--agents`: Include list of agents defined in the team (independent of --running)

#### `ucas term ALIAS|PATH`

Open a system terminal in the specified project.

**Terminal detection:** `xdg-terminal` (primary) → `x-terminal-emulator` (fallback)

#### `ucas autostart TAG1 TAG2 ...`

Start teams in projects matching any of the specified tags.

**Logic:**
1. Finds all projects with matching tags
2. For each project, determines the team to run (from tag object or DEFAULT)
3. Runs `ucas team run <team>` in the project
4. Updates `team_started` in project config

### Team Tracking

The `team_started` field is automatically updated:

- Set to team name when `ucas team run` completes
- Set to `NONE` when `ucas team stop` completes
- Used by `ucas list --running` to show active projects

