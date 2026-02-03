---
name: communicating-via-mcp-mail
description: "This skill should be used when the user asks to communicate with other agents, send messages, check the agent inbox, or coordinate tasks between agents. It provides a command-line interface for the MCP Agent Mail system."
---

# MCP Agent Mail Skill

## HOW TO READ YOUR MESSAGES
To see your messages AND their content (message body), just run:
```bash
am-client inbox
```
The output is JSON. Look for the `"body_md"` field to see the message text.

## HOW TO SEND MESSAGES
```bash
am-client send --to <AgentName> --subject "<Subject>" --body "<Content>"
```
Example: `am-client send --to GreenLake --subject "Task" --body "Done."`

## RULES
1. **Always use flags**: `--to`, `--subject`, `--message-id` are MANDATORY.
2. **Identity**: You are **$UCAS_AGENT**. Your team is **$UCAS_TEAM**.
3. **Team members**: BlueStone, GreenLake.
