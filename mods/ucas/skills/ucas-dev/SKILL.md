---
name: ucas-dev
description: "This skill should be used when the user asks to create or modify skills within UCAS mods. It ensures that new skills follow the directory structure, metadata requirements (name matching dirname), and documentation standards defined in the project."
---

# UCAS Skill Development

This skill provides procedures for creating and maintaining skills within the UCAS (Universal CLI Agent System) ecosystem.

## Requirements
- Must follow the pattern defined in `.claude/skills/creating-skills/SKILL.md`.
- **CRITICAL**: The `name` field in the YAML frontmatter MUST exactly match the directory name of the skill.

## Workflow

### 1. Planning the Skill Location
Identify where the skill belongs:
- **Project-Specific**: `mods/ucas/skills/ucas-dev/skills/<skill-name>/`
- **Mod-Specific**: `mods/<mod-name>/skills/<skill-name>/`
- **User-Global**: `~/.ucas/mods/<mod-name>/skills/<skill-name>/`

### 2. Creating the Structure
Create the directory using kebab-case:
```bash
mkdir -p <SKILL_PATH>/SKILL.md
```
For complex skills, also create: `references/`, `examples/`, `scripts/`, `assets/`.

### 3. Writing the Metadata
The YAML frontmatter MUST include:
- `name`: Must be identical to the `<skill-name>` directory.
- `description`: Third-person description starting with "This skill should be used when the user asks to...".

### 4. Implementation
- Use imperative/infinitive form for instructions.
- Reference internal resources using relative paths.
- Ensure all mentioned scripts are executable.

## Validation Checklist
- [ ] Does the `name` field match the directory name?
- [ ] Is the `description` in the third person with clear triggers?
- [ ] Are the instructions written in the imperative form (verb-first)?
- [ ] Are all referenced resource files present?

## Examples
- "Create a new skill for Python testing in the ucas-dev mod."
- "Update the security audit skill to include new search patterns."
- "Scaffold a new global skill for managing docker containers."
