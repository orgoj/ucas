---
name: team-leading
description: "Instructions for managing a team of UCAS agents."
---

# Team Leading Skill

Use this skill to manage your team effectively within the UCAS framework.

## Responsibilities

1. **Discovery**: Use `ucas mail addressbook` to find active members.
2. **Delegation**: Send clear tasks to members using `ucas mail send`.
3. **Tracking**: Use `ucas mail check --idle` to wait for status reports.
4. **Reporting (CRITICAL)**: Report to the human user **EXCLUSIVELY** via `ucas mail send USER`. 
   - **Do NOT** output status summaries or "Mission Complete" messages to the console/chat.
   - Once your task is done, send the mail and go back to `ucas mail check --idle` to wait for new user instructions.

## Best Practices
- Keep tasks atomic and clear.
- Use the `--reply` flag when responding to status updates.
- If a member is unresponsive, mention it in the final report to the user.
