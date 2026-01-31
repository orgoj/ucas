# Analysis of Kiro CLI

*   **URL:** [https://kiro.dev](https://kiro.dev)
*   **GitHub:** [https://github.com/withkiro/kiro-cli](https://github.com/withkiro/kiro-cli) (successor to Amazon Q Developer CLI)
*   **License:** Apache 2.0 (core components) / Proprietary service

---

### Comparison with UCAS Requirements

**Fulfills:**
*   **A. Complex orchestration:** Excellent; supports multi-agent orchestration systems (Architect, Coder, Reviewer) and hierarchical subagents.
*   **D. Definition of teams:** Native support for coordinating specialized agents to work together on complex software projects.
*   **G. License and price:** The CLI and many core integration components are open-source (Apache 2.0).
*   **I. Maximální volnost exekuce:** High; turns the terminal into an AI-powered environment, allowing chat-based control over the development process and local execution.

**Fails:**
*   **B. Simple onboarding:** While the CLI is easy to install, it often requires authentication with GitHub or AWS and is deeply tied to the Kiro.dev backend services. Not a fully independent "git clone + run" local tool.
*   **C. Configuration in repo:** Focused on specialized agents with defined "tool permissions" and context, but lacks the specific repo-based, layered YAML system for the entire project ecosystem that UCAS aims for.
*   **E. Dynamic composition:** Composition is through specialized "Architect/Coder" roles rather than the `agent + mod` dynamic CLI parameter aggregation and layering logic.
*   **F. Independence from payment model:** Historically and technically linked to the commercial backend services of Moonshot/AWS/Kiro. It is not designed to neutrally manage independent subscription-based CLI toolchains.
*   **H. Systémová stopa (Footprint):** Moderate; requires a Node.js runtime and has a significant footprint due to its integration with IDEs and its large set of pre-built "Skills."

---

### Quick Summary

Kiro CLI (formerly Amazon Q Developer CLI) is a robust command-line interface that provides an AI-powered development environment. It enables multi-agent orchestration for tasks like code generation, refactoring, and automated testing, allowing developers to interact with specialized AI agents directly in their terminal.

#### Key Characteristics:
*   **Multi-Agent Orchestration:** Coordinates specialized agents (e.g., Architect, Tester) to work collectively on high-level goals.
*   **Subagent Capability:** Allows users to launch and manage subagents from within a single Kiro session.
*   **Terminal Integration:** Seamlessly integrates with the local terminal, allowing the agents to "read" state and "execute" commands.
*   **Customizable Agents:** Developers can define custom agents with specific tool permissions, context, and prompts.
*   **Enterprise Heritage:** Built on the foundations of Amazon Q Developer, it features a high level of polish and integration with commercial development workflows.

---

### Detailed Description

#### The Evolution from Cloud-First to Terminal-First

Kiro CLI represents a significant evolution in AI-assisted development. While many tools began as web-based chat boxes, Kiro (and its predecessor at Amazon) recognized that for high-stakes software engineering, the agent must be present in the development environment. The Kiro CLI is not just an interface to a model; it is a "Terminal Shell Wrapper" that adds a layer of intelligence to everything the developer does.

This philosophy of "Intelligence at the Source" aligns with the UCAS goal of creating a "Semantic Skladatel." However, Kiro achieves this by providing a comprehensive, somewhat opinionated platform, whereas UCAS aims for an agnostic, lightweight structure that can wrap any existing tool or workflow.

#### Architecture: Supervisors and Specialized Workers

Kiro's architecture follows a "Supervisor-Subagent" pattern. When a user requests a complex feature, Kiro doesn't just start typing. It often invokes an "Architect" agent to analyze the current system and propose a plan. This plan is then handed down to "Coder" subagents, which execute the specific file changes.

This hierarchical approach provides a high degree of Requirement A (Complex Orchestration). It ensures that the high-level design remains consistent even as multiple low-level changes are made. This "Team of Agents" model is exactly what Requirement D (Team Definition) is looking for, but in Kiro, the orchestration logic is largely managed by their proprietary backend services rather than being defined locally in a simple YAML file.

#### Customization and "Context Bloat" Prevention

A major problem with early LLM agents was "context bloat"—the agent would eventually forget its goal or get confused by too much irrelevant code. Kiro addresses this by allowing developers to create "Custom Agents."

In Kiro, you can define exactly what a specific agent is allowed to see and do. You might create a "Security Audit Agent" that only has access to your library files and a set of static analysis tools. This "Permissioned Agency" is a sophisticated form of orchestration that ensures each part of the team stays focused and specialized.

#### Integration with the Ecosystem (Requirement I)

Kiro CLI excels at Requirement I because it is built to be "transport-agnostic." It can integrate with VS Code, JetBrains, and terminal emulators like Warp or iTerm2. This allows the AI to "see" what the developer is doing in real-time. 

However, this "Integration" often comes at the cost of Requirement H (Footprint). Kiro is a multi-component system that requires several installed helpers and background processes to achieve its magic. UCAS, by contrast, aims to achieve similar results using "Agnostic Wrappers" (like standard `tmux` commands) which are already present on the system, minimizing the need for custom binary helpers.

#### Comparison with UCAS requirements

**Requirement B (Simple Onboarding)**: To use Kiro CLI, you generally need to log in, often with a GitHub or AWS account. This dependency on external authentication and backend services makes it less of a "sovereign" tool than the vision for UCAS. UCAS wants to be a tool you can run on a remote server with no internet access (provided the models are local).

**Requirement E (Dynamic Composition)**: Kiro's composition is "structural." You have a project, and you invoke Kiro within it. UCAS's composition is "behavioral." You can run the same agent but "layer" it with a `+debugging-mod` or a `+multi-server-wrapper` at the moment of execution. This CLI-level agility is a core differentiator for UCAS.

**Requirement F (Payment Model)**: Kiro is a commercial-first offering. While the CLI is open, the higher-level orchestration features often require a subscription to the Kiro.dev platform. UCAS aims to be a purely free/open alternative that allows the user to bring their own models and services (Requirement G).

#### Summary of Analysis

Kiro CLI is a powerful, professional-grade tool for agentic development. Its ability to coordinate multiple specialized agents and its deep terminal integration make it one of the most advanced "AI Shells" available today.

However, its reliance on a commercial backend, its somewhat "heavy" footprint, and its lack of dynamic, CLI-layered composition make it a different kind of tool from UCAS. UCAS is the "Agnostic Orchestrator" for the power user who wants a lightweight, open-source, and highly composable system that they can truly "own" and version-control.

#### Technical Details of Implementation

Kiro CLI is primarily written in TypeScript and Node.js. It features a sophisticated state-management system that allows it to maintain the context of a "session" across multiple terminal commands. It uses a custom protocol to communicate between the CLI wrapper and the AI backend, ensuring that only the necessary code snippets are sent for processing, which improves both latency and security. The "Subagent" feature is implemented as a recursive call to the Kiro runtime, allowing for depth-first or breadth-first task decomposition.
