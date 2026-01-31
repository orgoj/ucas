# UCAS Project Roadmap & TODO

This document outlines the planned features and tasks for the UCAS project. Its purpose is to guide development and capture the project's long-term vision.

## Core Mission
The guiding principle for UCAS is to be **radically simple and fully automatic**. The ideal user experience is:
1.  A developer installs the `ucas` binary once.
2.  They clone any project that uses UCAS.
3.  They run a single command: `ucas start`.

The system must handle everything else automatically: find the default team, install any missing agents from their sources, and run each agent's self-initialization routine. The end result is a zero-friction setup that ensures a consistent environment for everyone on the team.

---

## Tier 1: Core CLI Functionality
These commands are essential for basic project management and introspection.

-   **`ucas init`**
    -   **Action:** Create a `.ucas/` directory in the current project.
    -   **Details:** Generate a minimal `ucas.yaml` configuration from a built-in template and create a default `main` team with a generic starter agent.

-   **`ucas status`**
    -   **Action:** Display a comprehensive summary of the current UCAS environment.
    -   **Details:** Should report on the presence of a `.ucas` project directory, list discovered teams and agents, show the resolved `UCAS_HOME` path, and print the final, merged configuration for the project for debugging purposes.

-   **`ucas list-agents`**
    -   **Action:** List all agents discoverable from the current project context (Project > User > System).

-   **`ucas list-teams`**
    -   **Action:** List all teams discoverable from the current project context.

---

## Tier 2: Agent & Team Lifecycle Management
This tier focuses on the "zero-friction automation" goal, making agents and teams self-sufficient.

-   **Agent Self-Installation & Initialization**
    -   **Concept:** Agents need a mechanism to declare dependencies and setup procedures (e.g., in `ucas.yaml` or a dedicated `install.sh` script).
    -   **Installer Subsystem:** `ucas` will detect if an agent is being run for the first time and trigger its installation/initialization process.
    -   **Controlled Initialization:** Implement `ucas init-agent <agent_name>` and `ucas init-team <team_name>` commands to allow for manual, controlled setup.
    -   **User-Assisted Init:** Support a flag (e.g., `requires_manual_init: true`) that forces a user to run the init command manually before the agent can be used, for tasks requiring user input or API keys.

-   **Remote Agent & Team Sources**
    -   **Concept:** Teams should be able to define remote sources for their agents.
    -   **Implementation:** The team's `ucas.yaml` will support a `sources` or `repositories` key containing a list of Git repository URLs.
    -   **Workflow:** Before launching a team, `ucas` will check for required agents. If an agent is not found locally, it will search the configured repositories, clone the agent into a local cache, and make it available.

-   **Team Pre-flight Checks**
    -   **Action:** Before executing `ucas run-team` or `ucas start`, perform a validation check on all agents within the team.
    -   **Details:** Verify that all required agents are present or downloadable and check if they have been successfully initialized, preventing mid-run failures.

---

## Tier 3: Advanced Features & Ideas
Longer-term ideas for enhancing security and usability.

-   **Execution Policies**
    -   **`allow_agents: ["glob-pattern-*"]`**: A YAML list of glob patterns. If defined, only agents matching these patterns will be allowed to run.
    -   **`deny_agents: ["*unstable*"]`**: A YAML list of glob patterns to explicitly forbid certain agents from running.
    -   **`allow_install: ["trusted-source/*"]`**: A policy to control which agents are permitted to run their installation routines.

---

## System Agents & Mods to Implement
A backlog of standard agents and mods to be developed and included with UCAS.

-   **`com-mcp-agent-mail`**: An agent for email interaction.
    -   *Reference:* `https://github.com/Dicklesworthstone/mcp_agent_mail`
-   **`task-br-worker`**: A generic task-execution worker agent.
-   **`task-br-planner`**: A high-level planning agent that can break down tasks for workers.
-   **`role-manager`**: A prompt-based agent that manages other agents. Requires a communication mod (`com-*`).
-   **`role-managed`**: A prompt-based agent designed to be managed by a `role-manager`.