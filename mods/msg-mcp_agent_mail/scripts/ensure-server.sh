#!/usr/bin/env bash
# UCAS Script: ensure-server.sh
# Zajišťuje, že MCP Agent Mail server běží.

SERVER_DIR="/home/michael/work/ai/Dicklesworthstone/mcp_agent_mail"
PORT=8765

if lsof -i :$PORT > /dev/null 2>&1; then
    echo "MCP Agent Mail server is already running on port $PORT."
    exit 0
fi

echo "Starting MCP Agent Mail server..."
cd "$SERVER_DIR" || { echo "Error: Could not find server directory $SERVER_DIR"; exit 1; }

# Spuštění serveru pomocí 'uv run' a explicitního modulu cli.
# Voláme command 'serve-http'.
nohup uv run python -m mcp_agent_mail.cli serve-http > /tmp/mcp-mail-server.log 2>&1 &

# Čekání na start (max 15 sekund)
for i in {1..30}; do
    if lsof -i :$PORT > /dev/null 2>&1; then
        echo "Server started successfully on port $PORT."
        exit 0
    fi
    sleep 0.5
done

echo "Error: Server failed to start. Check /tmp/mcp-mail-server.log for details."
tail -n 20 /tmp/mcp-mail-server.log
exit 1
