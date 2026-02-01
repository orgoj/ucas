# Changelog

All notable changes to this project will be documented in this file.

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
