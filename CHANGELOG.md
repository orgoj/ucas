# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2026-02-03

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
