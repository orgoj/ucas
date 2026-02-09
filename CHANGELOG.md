# Changelog

All notable changes to this project will be documented in this file.

## [0.9.3] - 2026-02-09

### Added
- **Project Management System**: New comprehensive project tracking and management.
  - `ucas init` - Initialize UCAS project in current directory
    - Interactive prompts for description, gitignore strategy, editor
    - Creates `.ucas/ucas.yaml` with default team and settings
    - Registers project in `~/.ucas/projects.yaml`
    - Supports re-init with upgrade/fix mode
  - `ucas list` - List all registered projects
    - Table output with ALIAS, PATH, DESCRIPTION, TAGS, TEAM columns
    - `--json` flag for JSON output
    - `--running` flag to show only projects with active teams
    - `--agents` flag to show team members (independent of --running)
  - `ucas term ALIAS|PATH` - Open system terminal in project
    - Uses `xdg-terminal` (primary) or `x-terminal-emulator` (fallback)
    - Supports both alias lookup and direct path resolution
  - `ucas autostart TAG1 TAG2 ...` - Start teams in projects by tags
    - Finds projects matching any of the specified tags
    - Resolves team from tag object or defaults to DEFAULT
    - Automatically updates `team_started` tracking

### Changed
- **Project Registry**: New `~/.ucas/projects.yaml` stores minimal alias→path mapping
- **Project Metadata**: New `.ucas/ucas.yaml` fields:
  - `description` - Human-readable project description
  - `tags` - Project tags for categorization and autostart
    - Supports simple tags and tag objects with team specification
    - Example: `[{name: autostart, team: DEFAULT}]`
  - `team_started` - Tracks last running team (NONE = not running)

### Fixed
- **YAML Parser**: Added proper escaping for quotes and backslashes in `save_yaml()`
- **Team Tracking**: `ucas team run` now sets `team_started`, `ucas team stop` resets to NONE

### Added to Documentation
- **CONFIGURATION.md**: New "Project Management Configuration" section
  - Project registry structure
  - Project configuration keys (description, tags, team_started)
  - Tags documentation (simple vs team-specified)
  - Complete command reference for all new commands
- **CLAUDE.md**: Added critical warning about read-only mode in planning/execution

---

## [0.9.3] - 2026-02-09

### Added
- **UCAS Installation**: New `ucas install` command sets up UCAS for current user.
  - Creates `~/.ucas/` directory structure
  - Sets up `mods/`, `mails/USER/`, `notes/` directories
  - Generates `~/.ucas/ucas.yaml` with mail notification template
  - Creates desktop entry at `~/.local/share/applications/ucas-mail.desktop` for clickable notifications
- **UCAS Doctor**: New `ucas doctor` command checks installation status.
  - Verifies Python version, hostname, installation directories
  - Checks user configuration and mail notification setup
  - Validates desktop entry status
- **Mail Notifications**: User-configurable notifications for new mail.
  - `mail.notifications.on_new_mail` in `~/.ucas/ucas.yaml` configures notification command
  - Supports placeholders: `{subject}`, `{from}`, `{id}`, `{date}`
  - Notifications only trigger for USER agent, not for other agents
  - Compatible with `notify-send` and other desktop notification tools
- **Message-ID with Hostname**: All outgoing emails now include hostname in Message-ID.
  - Format: `<{mail_id}@ucas-{hostname}>`
  - Ensures unique identifiers across multiple machines
- **Enhanced Address Book**: Full `mail-addressbook` integration restored.
  - Local agents from `.ucas/mails/` with descriptions from mod configs
  - External contacts from `mail-addressbook` in merged configuration
  - Mod descriptions override default "Local Agent" label

### Changed
- **Installers**: New modules `ucas/installer.py` and `ucas/doctor.py` for user setup and diagnostics.

### Fixed
- **Address Book Config Test**: Restored `get_address_book()` functionality with config reading.
- **Agent Mail Dir Fallback**: Added test for `_get_agent_mail_dir()` with `project_root=None`.

## [0.9.2] - 2026-02-08

### Added
- **Team Autostart**: Enable `team_autostart: true` in `ucas.yaml` to trigger `ucas team run` automatically upon receiving mail if no team is running.
- **Smart Address Book**: 
  - Centralized discovery of USER and team members.
  - Supports `mail-addressbook` configuration in `ucas.yaml` for external contacts.
  - Automatically fetches descriptions for local agents from their mod configurations.
- **Cross-Project Mail**: Native support for `agent@/path` addressing.
- **Auto-Reply Improvements**: 
  - `ucas mail send --reply <ID>` now automatically resolves both recipient AND subject (prefixed with `Re:`).
  - CLI arguments `recipient` and `subject` are now optional when `--reply` is present.
- **Startup Notifications**: `ucas team run` now alerts users to pending mail for team members.
- **Centralized Exceptions**: Moved `LaunchError` and `MergerError` to `ucas/exceptions.py` to resolve circular dependencies.
- Comprehensive test suite for the mail system (`tests/test_mail.py`).

### Changed
- **Security**: AI agents are now blocked from launching the Mail GUI (`ucas mail gui`).
- **Compatibility**: Restored support for `UCAS_AGENT_NOTES` to determine project root for agent mailboxes.
- **CLI**: The `--json` flag is now correctly respected in `mail list`, `mail read`, and `mail addressbook`.
- Refactored `send_mail` for delivery abstraction.
- Enhanced instructions template for better agent guidance.
- Updated project version to 0.9.2.

## [0.9.1] - 2026-02-08

### Changed
- **BREAKING**: Replaced `ucas run-team` with `ucas team run`.
- **BREAKING**: Replaced `ucas stop-team` with `ucas team stop`.
- **BREAKING**: Mail storage format changed from JSON to standard EML.
- **BREAKING**: Mail paths optimized (User mail in `~/.ucas/mails/USER`, project mails in `.ucas/mails`).
- Refactored `using-ucas-mail` skill to dynamically fetch instructions via CLI.

### Added
- `ucas team status`: Show status of running teams and agents.
- `ucas mail instruction`: Print instructions for agents on using the mail system.
- `ucas mail archive`: Move messages to archive folder.
- `ucas mail list --archive`: View archived messages.
- `mails: true` configuration in project `ucas.yaml` to enable project-level mailboxes.

## [0.9.0] - 2026-02-08

### Added
- **Agent Mail System**: A new file-based communication system for agents and users.
  - `ucas mail send`: Send messages to agents (local or in other projects) or the user.
  - `ucas mail list`: List inbox, read, and sent messages.
  - `ucas mail read`: Read message content and move to read folder.
  - `ucas mail check`: Check for new messages (with `--idle` support).
  - New `ucas-mail` mod with `mail` skill for agents to interact with the system.
  - Integration with `UCAS_AGENT_NOTES` for mail storage.

## [0.8.0] - 2026-02-03

### Added
- New subcommand `ucas ls-mods` to list available mods across project, user, and system layers.
- Support for `-q`/`--quiet` and `-v`/`--verbose` global options.
- Support for `__DIR__` variable in `ucas.yaml` files, resolving to the mod's absolute directory path.
- Implementation of `acli!:` and `run!:` blocks for robust, collision-free configuration merging.
- Improved `--dry-run` output showing the exact command the runner would execute.
- Global `--debug` flag for detailed merge tracing and internal command visibility.

### Changed
- Refactored launcher to be "tupý" (dumb) - it now executes whatever is present in the final merged `acli` and `run` blocks.
- Moved default ACLI (`acli-claude`) and Runner (`run-tmux`) into the system-level `mods+` list.
- Flattened ACLI configuration structure (removed `arg_mapping` nesting).
- Updated all built-in mods to the new robust format.

### Fixed
- Fixed collisions where multiple mods with the same `name` key would overwrite each other's functional configuration.
- Fixed an issue where the wrong runner was selected when multiple runners were present in the mod chain.
- Corrected model translation logic to properly handle 'default' models.
