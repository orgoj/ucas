---
name: creating-skills
description: "Scaffold a new skill (Project-Local or User-Global). For simple tasks, use the fast-track (SKILL.md only); for complex workflows, follow the full structured process with references and scripts."
---

# Creating New Skills

Use this skill to define a new repeatable capability for the agent. Skills transform the agent from a general-purpose assistant into a specialized agent equipped with procedural knowledge, workflows, and tools.

## 1. Classification: Simple vs. Complex Skill

Before starting, determine the complexity to avoid over-engineering small tasks.

- **Simple Skill (Fast-track)**:
  - **Criteria**: Purely informational, single-step logic, or small set of rules with no external scripts/assets.
  - **Action**: Create only `SKILL.md`. Skip the directory structure and complex planning. Keep the body short (<500 words).
- **Complex Skill (Standard process)**:
  - **Criteria**: Multi-step workflows, requires validation scripts, large reference docs, or boilerplate assets.
  - **Action**: Follow the full structured process described below.

## Anatomy of a Skill (Complex)

Every complex skill consists of a required `SKILL.md` file and optional bundled resources:

```text
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter metadata (required)
│   │   ├── name: (required)
│   │   └── description: (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for tasks requiring deterministic reliability.
    ├── references/ - Documentation to be loaded into context only when needed.
    ├── examples/   - Working code examples or sample outputs.
    └── assets/     - Static files (images, templates, fonts) used in output.
```

## Progressive Disclosure Design

Skills use a three-level loading system to manage context efficiently:
1. **Metadata (name + description)**: Always in context (~100 words). Determines if the skill triggers.
2. **SKILL.md body**: Loaded when the skill triggers (Target: 1,500-2,000 words).
3. **Bundled resources**: Loaded or executed only as needed by the agent.

## Determination of Type and Location

- **Local (Project-Specific)**:
  - Path: `./.pi/skills/<name>/SKILL.md`
  - Use case: Logic depends on specific project architecture or conventions.
- **Global (User-Wide)**:
  - Path: `~/.pi/agent/skills/<name>/SKILL.md`
  - Use case: Generic logic applicable across projects (e.g., git, docker, language-specific tasks).

## 2. Planning and Analysis (Complex Skills Only)

To create an effective complex skill, identify concrete examples of how it will be used.
- **Identify Triggers**: What specific phrases would a user say to trigger this? (e.g., "rotate this PDF").
- **Identify Resources**:
    - **Scripts**: What code is being rewritten repeatedly? (e.g., `scripts/validate_schema.py`).
    - **References**: What large documentation should be available but not always in context? (e.g., `references/api_docs.md`).
    - **Examples**: What boilerplate or sample files would be helpful?

### Create Directory Structure
Use kebab-case and the **gerund form** for the skill name (e.g., `creating-skills`, `managing-configs`).

```bash
mkdir -p <PATH_TO_SKILL_DIR>/{references,examples,scripts,assets}
```

## 3. Write SKILL.md

### Writing Style Requirements
- **Imperative/Infinitive Form**: Use verb-first instructions (e.g., "To accomplish X, do Y" instead of "You should do X").
- **Third-Person Description**: The frontmatter `description` MUST use third person and include specific trigger phrases.

### SKILL.md Template

```markdown
---
name: <gerund-form-name>
description: "This skill should be used when the user asks to <trigger-phrase-1>, <trigger-phrase-2>, or <trigger-phrase-3>. [Briefly describe what it provides]."
---

# <Human Readable Title>

[Purpose of the skill in a few sentences. Address the agent as 'you' in the body, but use imperative form for instructions.]

## Parameters
[Optional: Describe required or optional parameters/arguments.]

## Requirements
[Optional: Prerequisites (e.g., "Must be in root of git repo").]

## Workflow / Steps

### 1. Analysis
[Verb-first instructions for analyzing the task...]

### 2. Execution
[Verb-first instructions for performing the task...]

## Additional Resources

### Reference Files
- **`references/patterns.md`** - Detailed patterns and edge cases.

### Examples
- **`examples/sample-config.yaml`** - Working configuration example.

### Scripts
- **`scripts/validate.sh`** - Utility to verify output.
```

## 4. Verification and Validation

1. **Check Description**: Does it use third person and include concrete trigger phrases?
2. **Check Body Style**: Are instructions written in imperative form?
3. **Progressive Disclosure**: Is the `SKILL.md` body lean (ideally <2,000 words)? Have details been moved to `references/`?
4. **Check Paths**: Confirm the location is correct for the intended scope.
5. **Verify Resources**: Ensure all referenced files in `SKILL.md` actually exist.

## Best Practices and Common Mistakes

### ✅ DO:
- Use third-person in description ("This skill should be used when...").
- Include specific trigger phrases ("create X", "configure Y").
- Keep `SKILL.md` lean (1,500-2,000 words) and move details to `references/`.
- Write in **imperative/infinitive form** (verb-first).
- Provide working examples in `examples/`.

### ❌ DON'T:
- Use second person ("You should...") anywhere in instructions.
- Have vague trigger conditions in the frontmatter.
- Put everything in one giant `SKILL.md` file (>3,000 words).
- Leave resources (scripts, references) unreferenced in the main body.
