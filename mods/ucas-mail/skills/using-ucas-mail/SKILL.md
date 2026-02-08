---
name: using-ucas-mail
description: "This skill should be used when the user asks to send a message, check inbox, list emails, or communicate with other agents via UCAS mail."
---

# Using UCAS Mail

Use this skill to communicate with other agents or the human user via the internal file-based mail system.

## Workflow

1.  **Check Mail**: Always start by checking for messages.
    - If waiting for a task: `ucas mail check --idle` (This command blocks! Use a high timeout, e.g., 600s)
    - To check immediately: `ucas mail check` (Returns 0 if new mail exists)

2.  **List Messages**: See what's in your inbox.
    ```bash
    ucas mail list
    ```
    Output is JSON. Use `jq` or built-in JSON parsing.
    For human-readable table, use `ucas mail list --table`.

3.  **Read Message**: Get the content of a specific message.
    ```bash
    ucas mail read <ID>
    ```
    Output is JSON.
    *Note: Reading a message automatically moves it to the `read` folder.*

4.  **Reply / Send Message**: Send a response or new message.
    **ALWAYS use the `--body` argument for clarity.**
    ```bash
    ucas mail send <RECIPIENT> "<SUBJECT>" --body "<MESSAGE_CONTENT>"
    ```
    To reply to a specific message, add `--reply <ID>`.

5.  **Find Contacts**: If you don't know the recipient's name.
    ```bash
    ucas mail addressbook
    ```
    Output is JSON. Use `ucas mail addressbook --table` for human-readable output.

## Critical Rules

- **NEVER** read files in `.ucas/notes/` directly. Use `ucas mail read`.
- **ALWAYS** use `ucas mail check --idle` when waiting for instructions. Do not loop `sleep` and `list`.
- **ALWAYS** use `--body` for sending messages. Do not rely on STDIN unless piping output.
- If a message body is empty, reply asking for clarification.
