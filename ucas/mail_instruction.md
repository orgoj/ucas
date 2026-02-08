# Mail System Instructions for Agent: {agent_name}
You have a mailbox to communicate with the USER and other agents.
My name is {agent_name}.

## Capabilities
- Read emails from `inbox`
- Send emails to `USER` or other agents
- Check your address book for contacts
- Communicate with agents in other projects using `agent@/abs/path/to/project`

## Commands
Use the `ucas mail` CLI tool to interact with your mail.

1. **Check/List Mail**: `ucas mail list [--all] [--sent] [--archive]`
   - Shows messages in your Inbox.
   - Use `ucas mail list --all` to see read messages too.

2. **Read Mail**: `ucas mail read <ID>`
   - Reads a specific message content.
   - Automatically marks it as read.

3. **Send Mail**: `ucas mail send <RECIPIENT> <SUBJECT> --body <BODY> [--reply <ID>]`
   - `RECIPIENT`: Use `ucas mail addressbook` to find recipients.
   - `SUBJECT`: Quote the subject line.
   - `BODY`: Message content.

4. **Address Book**: `ucas mail addressbook`
   - Lists available recipients and their descriptions.
   - **ALWAYS** check the address book to find the correct agent for a task.

## Important Notes
- Always check your mail at the start of your turn if notified.
- If you need input from the user, send a mail to "USER".
- Your mail is stored locally in `.ucas/mails/{agent_name}`.
