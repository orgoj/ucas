#!/bin/bash
export UCAS_HOME=$(pwd)
export PYTHONPATH=$(pwd)

# Create dummy project structure
mkdir -p .ucas/notes/agent1/mail/inbox
mkdir -p .ucas/notes/agent2/mail/inbox

# Send mail from agent1 to agent2
export UCAS_AGENT=agent1
export UCAS_AGENT_NOTES=$(pwd)/.ucas/notes/agent1
echo "Test Body" | python3 -m ucas mail send agent2 "Test Subject"

# Check if agent2 received it
ls -l .ucas/notes/agent2/mail/inbox/

# List mail for agent2
export UCAS_AGENT=agent2
export UCAS_AGENT_NOTES=$(pwd)/.ucas/notes/agent2
python3 -m ucas mail list

# Read mail
ID=$(ls .ucas/notes/agent2/mail/inbox/ | head -n 1 | sed 's/.json//')
python3 -m ucas mail read $ID

# Check if moved to read
ls -l .ucas/notes/agent2/mail/read/

# Check mail for agent2 (should be empty now)
python3 -m ucas mail check || echo "No mail"

# Send another mail
export UCAS_AGENT=agent1
echo "New mail" | python3 -m ucas mail send agent2 "New Subject"

# Check mail for agent2 (should find one)
export UCAS_AGENT=agent2
python3 -m ucas mail check && echo "Found mail"
