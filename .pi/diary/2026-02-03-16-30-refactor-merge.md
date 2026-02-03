# Session Diary

**Date**: 2026-02-03 16:30
**Session ID**: 2026-02-03-16-30-refactor-merge
**Project**: /home/michael/work/ai/PROJECTS/ucas

## Task Summary
The user wanted to organize skills into blocks (mods) and implement a subcommand `ucas ls-mods` to list them by layer. The session evolved into a major refactoring of the merge logic and launcher to ensure robustness against configuration collisions and improve developer experience.

## Work Done
- **Organization**: Created `ucas.yaml` files for all user mods in `~/.ucas/mods`.
- **Feature**: Implemented `ucas ls-mods` with `-q` (quiet) and `-v` (verbose) support.
- **Refactoring**: Moved `--debug`, `--dry-run`, and `-q` to global CLI options.
- **Architecture**: Redesigned merge logic to use `acli!:` and `run!:` blocks to prevent key collisions (especially the `name` key).
- **Architecture**: Implemented a "dumb" launcher that strictly follows the merged YAML instead of trying to "detect" entities by name.
- **KISS Feature**: Added `__DIR__` variable support in `ucas.yaml` for absolute path resolution within mods.
- **Defaults**: Moved default ACLI and Runner into the system `mods+` list.
- **Documentation**: Completely rewrote `README.md` and updated `CHANGELOG.md`.
- **Governance**: Updated `CLAUDE.md` with strict rules on execution and communication.

## Design Decisions
- **Metadata vs. Function**: Metadata (`name`, `description`) stays at the root of `ucas.yaml` for `ls-mods`, while functional config is moved to `acli!:` and `run!:` to isolate them during merge.
- **Dumb Launcher**: The launcher no longer guesses what to run; it executes whatever is in the final `acli` and `run` blocks.
- **`__DIR__` Resolution**: Performed at load time in `resolver.py` to keep the rest of the system decoupled from mod file locations.
- **Global Options**: Moved `dry-run` and `debug` to the root parser because they apply to all execution commands.

## Challenges & Solutions
| Challenge | Solution |
|-----------|----------|
| Configuration collisions on the `name` key | Isolated functional parts into `acli!:` and `run!:` blocks using the forced-override (`!`) suffix. |
| Locating scripts within mods after merge | Introduced `__DIR__` placeholder in YAML, replaced with the absolute mod path during loading. |
| Wrong runner/ACLI being selected | Removed selection logic based on names; the launcher now simply uses the results of the "Sandwich Merge". |

## Mistakes & Corrections
### Where I Made Errors:
- **Execution Command**: Used `python3 ucas-bin` repeatedly instead of the project's required `./ucas-bin`.
- **Communication Style**: Applied changes without explaining them first, violating the user's preference for senior-level collaboration.
- **Selection Logic**: Initially tried to fix runner selection by adding more complex "smart" detection instead of making the launcher "dumb" and robust.
- **CLI Design**: Initially added `-q` and `--debug` as local options for subcommands instead of global options.
- **Tooling**: Attempted to use `cat` for file appending/editing instead of the dedicated `edit` tool.

### What Caused the Mistakes:
- **Missing Project Context**: Didn't internalize the "ALWAYS explain first" and "./ucas-bin only" rules until they were explicitly added to `CLAUDE.md`.
- **Over-engineering**: Tried to keep the code "smart" instead of following the KISS principle requested by the user.

## Lessons Learned
### Technical Lessons:
- **Argparse Positioning**: Global options must be added to the main parser before `add_subparsers`.
- **KISS Merge**: Suffix-based merge strategies (`+`, `!`) are powerful, but they work best when the data structure is designed to isolate different concerns (e.g., separate blocks for different roles).
- **String Replacement in YAML**: Replacing placeholders in raw text before parsing is a very effective and simple way to handle dynamic paths.

### Process Lessons:
- **Explain First**: In high-stakes refactoring, explaining the plan and getting approval saves time and avoids rollback.
- **Follow Metadata**: Always check `CLAUDE.md` and `README.md` for specific execution and environment rules.

### To Remember for CLAUDE.md:
- **Execution**: NEVER use `python3` for the app, ONLY `./ucas-bin`.
- **Communication**: Explain and wait for approval before ANY file modification.
- **Tooling**: Strictly use `edit` for modifications.

## Skills Used
### Used in this session:
- [x] Skill: `~/.pi/agent/skills/pi-dots/dot-init/SKILL.md` - Used implicitly to track task state.
- [x] Skill: `~/.pi/agent/skills/selflearn-diary/SKILL.md` - Creating this entry.

## User Preferences Observed
### Git & PR Preferences:
- Commit messages should summarize the refactoring clearly.

### Code Quality Preferences:
- KISS (Keep It Simple, Stupid) is the primary architectural goal.
- Robustness through simple, predictable behavior rather than "smart" heuristics.
- Clean, flattened YAML structures.

### Technical Preferences:
- No redundant logic (e.g., don't define defaults in code if they can be defined in config).
- Senior-level approach to CLI design (global flags).

## Code Patterns Used
- **Dumb Launcher**: Using merge results directly.
- **Variable Injection**: Pre-parsing string replacement (`__DIR__`).
- **Forced Override Blocks**: Using `key!:` to ensure the last mod in the chain has total control over a specific configuration block.

## Notes
The project is now much more modular. The transition to `/home/michael/work/ai/PROJECTS/ucas-tests` for testing is a good sign of moving towards validation.
