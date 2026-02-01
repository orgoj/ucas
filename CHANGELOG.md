# Changelog

All notable changes to this project will be documented in this file.
 
## [0.5.0] - 2026-02-01

### Added
- **Multiple Mod Search Paths**: Support for `mod_path: []` in `ucas.yaml` to expand the mod library.
- **Dynamic Search Path Expansion**: Agents and mods can now dynamically add search paths during resolution.
- **Strict Mode**: Added `strict: true` option to disable default fallbacks to User/System layers.
- **Improved Resolver**: Refactored `ucas/resolver.py` to support dynamic search paths and absolute/relative path resolution.
- **Expanded Test Suite**: Added `tests/test_mod_paths.py` with 6 new tests covering all mod resolution scenarios.

### Changed
- Refactored `_prepare_and_run_member` in `ucas/__main__.py` to use new dynamic resolution logic.
- Updated `ucas/merger.py` to treat `mod_path` as an aggregation key (automatic `+` strategy).
- Cleaned up test output by disabling debug logs by default in `tests/test_mod_paths.py`.


## [0.4.0] - 2026-02-01

### Added
- **Suffix-based Merge Strategies**: New powerful syntax for granular configuration merging.
    - `key+`: Merge/Append (recursive for dicts, concatenate for lists).
    - `key-`: Remove (remove items from list or delete keys from dict).
    - `key!`: Override (force replacement).
    - `key?`: Default (only set if missing in base).
    - `key~`: Selective Update (only set if key already exists in base).
- **Practical Tests**: Comprehensive test suite in `tests/test_merger_strategies.py` including practical multi-layer scenarios.
- **Improved Documentation**: Detailed "Merge Strategies" section added to README.md.
- **Convenience**: Added `run_tests.sh` to quickly execute the entire test suite.

### Changed
- Refactored `ucas/merger.py` to use generic strategy handlers.
- Updated `skills`, `mods`, and `hooks` to use the `+` strategy by default for backward compatibility.
