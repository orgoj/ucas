---
name: testing-ucas-teams
description: "This skill should be used when testing UCAS agent teams, checking their status, or verifying communication."
---

# Testing UCAS Teams

Use this skill to manage the lifecycle of testing agent teams and verifying their interactions.

## Workflow

### 1. Start the Team
Run the team from within the project directory.
```bash
ucas team run [team_name]
```

### 2. Monitor Progress
Use the status command to see what agents are doing without attaching to tmux.
```bash
# General summary
ucas team status

# Detailed view for a specific agent (shows last 80 lines of output)
ucas team status [agent_name]

# Follow specific number of lines
ucas team status [agent_name] --lines 100
```

### 3. Verify Communication
Check the user inbox to see if agents are reporting correctly.
```bash
ucas mail list --table
```

### 4. Stop the Team
Always clean up after testing.
```bash
ucas team stop [team_name]
```

## Best Practices
- Use `ucas team status` frequently to detect stuck agents.
- Check the `Idle` column in status to see if agents are waiting too long.
- If an agent is halucinating, try to send them a corrective mail:
  ```bash
  ucas mail send [agent_name] "Correction" --body "Follow the mission steps explicitly."
  ```
