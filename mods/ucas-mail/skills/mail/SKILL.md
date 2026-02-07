# UCAS Mail System

Use this skill to communicate with other agents or the human user via the internal mail system.
The system is file-based and simple (KISS).

## Commands

### 1. Check for New Mail
Check if you have any unread messages in your inbox.
```bash
ucas mail check
```
Returns 0 if new mail exists, 1 otherwise.
Output: "You have new mail! Check it with `ucas mail list`"

### 2. List Messages
List messages in your inbox.
```bash
ucas mail list
```
Use `--all` to see read messages, `--sent` to see sent messages.
The output shows ID, Date, From, and Subject.

### 3. Read a Message
Read the content of a specific message by its ID.
```bash
ucas mail read <ID>
```
Reading a message automatically moves it from `inbox` to `read` folder.

### 4. Send a Message
Send a message to another agent or the user.
The body of the message is read from STDIN.

**Syntax:**
```bash
ucas mail send <RECIPIENT> "<SUBJECT>" <<EOF
<BODY>
EOF
```

**Recipients:**
- `AGENT_NAME`: Agent in the same team/project.
- `user`: The human user (saved to `~/.ucas/mail`).
- `ALL`: All agents in the current project.

**Example:**
```bash
ucas mail send user "Task Complete" <<EOF
I have finished the analysis of the data.
Please check the report in output.txt.
EOF
```

### 5. Wait for Mail (Idle)
If you are waiting for a reply, use the idle check which blocks until mail arrives.
```bash
ucas mail check --idle
```

## Workflow
1. At the start of a task, run `ucas mail check`.
2. If new mail exists, run `ucas mail list` then `ucas mail read <ID>`.
3. To reply, use `ucas mail send`.
4. If waiting for input, loop with `ucas mail check --idle` (or just check periodically).
