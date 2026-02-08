# Changelog

All notable changes to this project will be documented in this file.

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
