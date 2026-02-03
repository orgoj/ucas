---
name: managing-ucas-mods
description: "This skill should be used when the user asks to create a new UCAS mod, modify an existing one, or understand how mods work. It covers mod directory structure, ucas.yaml configuration, and mod layers."
---

# Managing UCAS Mods

This skill provides procedural knowledge for developing and managing mods for the Universal CLI Agent System (UCAS).

## Requirements
- Access to the `mods/` directory.

## Workflow

### 1. Creating a New Mod
To create a new mod, follow these steps:
1. Create a directory in `mods/<mod-name>`.
2. Create a `ucas.yaml` file inside that directory.
3. Define the `name` and `description` in `ucas.yaml`.
4. Add any overrides if necessary (`acli!`, `run!`, `env!`).

### 2. Mod Structure
A typical mod directory looks like this:
```
mods/<mod-name>/
├── ucas.yaml (required)
├── README.md (optional, for documentation)
├── skills/ (optional, directory containing agent skills)
│   └── <skill-name>/
│       └── SKILL.md
└── scripts/ (optional, for custom runners or tools)
```

### 3. ucas.yaml Configuration
- **name**: Internal name of the mod.
- **description**: Short description shown in `ucas ls-mods`.
- **acli!**: Overrides agent CLI settings.
- **run!**: Overrides runner settings.
- **env!**: Sets environment variables.

Use `__DIR__` in paths to refer to the mod's directory.

### 4. Mod Layers
- **System**: `<install-dir>/mods/`
- **User**: `~/.ucas/mods/`
- **Project**: `./.ucas/mods/` (Note: in this repo, core mods are in `mods/`)

### 5. Testing
After creating a mod, verify it with:
```bash
./ucas-bin ls-mods
./ucas-bin run <agent> +<mod-name> --dry-run
```

## Examples

### Basic Mod
```yaml
name: my-skill
description: Adds a specific capability
```

### Mod with executable override
```yaml
name: custom-pi
acli!:
  executable: /path/to/pi
```
