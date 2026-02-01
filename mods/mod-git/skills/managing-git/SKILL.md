---
name: managing-git
description: "This skill should be used when the user asks to manage git repository, check status, commit changes, or view history. It provides structured commands and workflows for version control."
---

# Managing Git

Use this skill to help the user with git-related tasks.

## Workflow

### 1. Analysis
Before making any changes, always check the current state of the repository.
- Use `git status` to see staged/unstaged changes.
- Use `git log -n 5` to see recent history.
- Use `git diff` to review specific changes.

### 2. Execution
Stage and commit changes as requested.
- Use `git add <files>` to stage changes.
- Use `git commit -m "<message>"` to commit changes.
- Use `git push` or `git pull` if remote operations are needed.
