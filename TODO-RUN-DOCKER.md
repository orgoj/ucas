# TODO: run-docker Implementation

The `run-docker` mod aims to provide an isolated execution environment for agents. Implementation is deferred due to complexity in path management and volume mounting.

## Requirements & Challenges

- **Project Mounting**: The active project root must be mounted into the container.
- **Mod & Skills Resolution**:
    - Agents often use multiple mods and skills from different locations (System, User, Project, or extra search paths).
    - These locations may contain symlinks.
    - **Strategy A (Copy)**: Create a self-contained bundle in `./.ucas/tmp/<AGENT_NAME>` with all required files, then mount this bundle. This makes the environment immutable during execution (better for stability, worse for development).
    - **Strategy B (Bind Mounts)**: Detect all involved directories and bind mount them. This is complex due to varying base paths and potential symlink resolution.
- **Session Persistence**:
    - The `session_arg` path (often in `~/.pi/sessions/` or similar) must be mounted to ensure sessions are preserved across runs.
    - Host-path mirroring (mounting host paths at same location in container) is preferred for absolute path compatibility.
- **Non-blocking Execution**:
    - `run-docker` must be `single: false` to allow team orchestration.
    - It should likely launch a new terminal (e.g., `xterm -e docker run -it ... &`) to provide user interactivity without blocking the `ucas` loop.

## Deferred Tasks
- [ ] Research best container image for common ACLIs.
- [ ] Implement path detection and automatic `--volume` generation.
- [ ] Handle UID/GID mapping for file permission consistency.
