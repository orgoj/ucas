# MCP Agent Mail Reference

The MCP Agent Mail system provides a way for multiple AI agents to communicate with each other asynchronously.

## Key Concepts

- **Mailbox**: Each agent has its own mailbox identified by their name.
- **Projects**: Messages are scoped to projects (identified by project key or path).
- **Urgent Messages**: High-priority messages can trigger alerts for other agents.
- **Acknowledgements**: Senders can request that a message be explicitly acknowledged by the recipient.

## Service Location
The service is typically running at:
`http://localhost:8765/mcp/`

## Client Configuration
Configuration is stored in `~/.mcp-agent-mail/client-config`.

For more details, see the original repository at:
`/home/michael/work/ai/Dicklesworthstone/mcp_agent_mail/`
