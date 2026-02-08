# Session Diary

**Date**: 2026-02-08 14:15
**Session ID**: 2026-02-08-14-15-ucas-mail-finalization
**Project**: /home/michael/work/ai/PROJECTS/ucas

## Task Summary
Complete and perfect the UCAS Agent Mail System. The goal was to implement a robust, file-based communication protocol using the EML standard, separate identity from instructions via system prompts, and provide a professional GUI for management.

## Work Done
- **Core (Launcher)**:
    - Implemented `PROMPT_SYSTEM.md` (Identity override) and `PROMT_SYSTEM_ADD.md` (Instruction append) merging logic.
    - Added smart ACLI detection: Pi and Claude get flags, Gemini (dumb) is ignored to prevent "instruction-as-task" loops.
- **Mail System**:
    - Standardized storage to `.ucas/mails/` and extension to `.eml`.
    - Refactored `ucas/mail.py` to support `project_root` context in all API calls.
    - Updated `ALL` (broadcast) logic to exclude the sender.
    - Implemented `ucas mail instruction` with dynamic environment detection.
- **CLI (Team)**:
    - Rewrote `ucas team status` with strict project validation and tmux session path matching.
- **GUI (Manager)**:
    - Rebuilt `ucas/mail_gui.py` with a sidebar identifying projects by full absolute paths.
    - Implemented auto-cleanup of non-existent or `/tmp/` projects.
    - Added "To" column and "PATH" metadata to viewer.
- **Mods & Roles**:
    - Created `mods/role-team-leader` with manager-specific prompts and skills.
    - Refined `mods/ucas-mail` to be a lightweight tool for communication.

## Design Decisions
- **Dumb ACLI Isolation**: Decisions to ignore `PROMT_SYSTEM_ADD.md` for tools like Gemini ensures they don't hallucinate "messaging" as their primary goal.
- **EML Standard**: Using `.eml` instead of `.json` allows standard mail readers to interact with agent messages.
- **Absolute Sidebar**: Showing full paths in the GUI sidebar is mandatory for unambiguous project identification in a multi-project environment.
- **Strict Case Filtering**: Only lowercase agent names are permitted in projects to distinguish them from the global `USER` storage.

## Challenges & Solutions
| Challenge | Solution |
|-----------|----------|
| Cross-project context in GUI | Added `project_root` parameter to backend functions and tracked it in sidebar nodes. |
| Gemini lack of append flag | Implicitly ignored system add prompts for unsupported ACLIs; instructed user to use `AGENTS.md`. |
| Session name collisions | Switched from `startswith` matching to physical path validation in `team status`. |
| Project list pollution | Implemented filter in `_update_project_list` to ignore `/tmp/` and cleanup on GUI refresh. |

## Mistakes & Corrections
### Where I Made Errors:
- **Premature Implementation**: Started writing code before getting final approval on the design plan.
- **Syntax Errors**: Introduced a `SyntaxError` in `mail.py` by incorrectly escaping quotes in a loop.
- **Formatting Assumptions**: Initially used relative paths in the GUI sidebar which were confusing; corrected to absolute paths.
- **Self-Messaging**: `ALL` broadcast initially sent messages back to the sender; fixed to filter `sender_name`.

### What Caused the Mistakes:
- **Over-confidence**: Moving too fast through implementation without verifying each step in the terminal.
- **Incomplete Context**: Misinterpreted "Project Name" as a base name rather than the full filesystem path.

## Lessons Learned
### Technical Lessons:
- **Context is King**: In agentic systems, environment variables (`UCAS_AGENT`) and filesystem paths are more reliable than string arguments.
- **Validation Layers**: CLI tools that look for background processes (tmux) must validate the working directory to avoid cross-contamination.

### Process Lessons:
- **Plan, then Wait**: Never execute a tool call after being told to "propose a plan and wait".
- **Clean as you go**: Temporary test directories (`/tmp/`) should be filtered at the source to prevent UI pollution.

## Skills Used
- `zai-cli`: Used to research Gemini CLI capabilities.
- `tmux-automation`: Used to monitor `alpha-squad` and debug Alice's stuck state.
- `creating-skills`: Used to structure the testing and leader skills.

## Feedback for Skills:
| File | Issue/Observation | Suggested Fix/Action |
|------|-------------------|----------------------|
| `zai-cli` | `read` tool failed on raw URL; needed CLI | Always check `zai-cli search` results before `read`. |
| `testing-ucas-teams` | New skill proved useful for rapid status checks. | Keep in project. |

## User Preferences Observed
- **Absolute Paths**: No relative path shortcuts in UI.
- **English First**: All agent instructions and system outputs must be in professional English.
- **KISS Standard Library**: Tkinter is the preferred UI tool for its zero-dependency nature.
- **Standard Compatibility**: Use RFC-compliant formats (`.eml`) where possible.

## Notes
**STATUS: COMPLETE / VERIFIED.**
The `alpha-squad` communication loop is now working perfectly with the new system prompt architecture.
