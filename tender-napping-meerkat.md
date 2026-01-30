# UCAS Implementation Plan

## Overview

**UCAS** (Universal CLI Agent System) - an intelligent assembler and launcher that finds Agent/Mod/ACLI definitions, merges them via "Sandwich Merge", and executes in tmux.

**Approach:** Vertical slices - each slice is a working increment.
**Testing:** Manual first, automated tests after design stabilizes.
**Documentation:** After MVP complete.

---

## Project Structure

```
ucas/
├── ucas/                    # Main package
│   ├── __init__.py
│   ├── __main__.py          # Entry point (python -m ucas)
│   ├── cli.py               # Argument parsing
│   ├── yaml_parser.py       # Mini YAML parser (no PyYAML)
│   ├── resolver.py          # Entity search across layers
│   ├── merger.py            # Sandwich merge logic
│   └── launcher.py          # Command building & tmux execution
├── agents/                  # System Library ($UCAS_HOME/agents/)
│   ├── acli-claude/
│   │   └── ucas.yaml
│   ├── acli-zai/
│   │   └── ucas.yaml
│   ├── basic-chat/
│   │   ├── ucas.yaml
│   │   └── PROMPT.md
│   └── utils/
├── teams/                   # Example teams
├── ucas.yaml                # System defaults
├── pyproject.toml
└── README.md
```

---

## Slice 1: Minimal Dry-Run

**Goal:** `ucas run basic-chat --dry-run` prints assembled command.

**Files to create:**

1. **ucas/yaml_parser.py** - Full mini YAML parser
   - Flow lists `[a, b, c]`
   - Nested dicts/lists
   - Strings, booleans, null, comments
   - Strict errors with line numbers
   - No multiline strings, anchors, or tags

2. **ucas/cli.py** - Parse `run <agent> --dry-run`

3. **ucas/resolver.py** - System layer search only
   - `find_entity(name)` → path to agent/ACLI directory
   - `is_acli(path)` → checks for `executable` key

4. **ucas/merger.py** - Minimal merge (system + agent)

5. **ucas/launcher.py**
   - `select_acli()` - pick from `allowed_acli`
   - `build_command()` - substitute into `arg_mapping`
   - `translate_model()` - translate agent's `requested_model` via ACLI's `model_mapping`
     - Check mapping exists, use "default" key as fallback
     - Handle `ignore_unknown` flag (false → ERROR, true → skip model flag + WARNING)
   - `generate_prompt()` - copy PROMPT.md to `.ucas/tmp/`

6. **agents/basic-chat/** - Test agent with `requested_model: "gpt-4"`
7. **agents/acli-claude/** - Claude ACLI definition with `model_mapping`:
   ```yaml
   executable: "claude"
   arg_mapping:
     prompt_file: "--system"
     skills_dir: "--tools"
     model_flag: "--model"
   model_mapping:
     "gpt-4": "sonnet-3.5"
     "gpt-5.2-pro": "opus-4.5"
     "default": "sonnet-3.5"
   ```
8. **ucas.yaml** - System defaults (`allowed_acli`, `default_acli`)

**Verify:** `python -m ucas run basic-chat --dry-run` prints command.

---

## Slice 2: Real Execution

**Goal:** `ucas run basic-chat` executes in tmux.

**Changes:**

1. **ucas/launcher.py** - Add `run_tmux(command, name)`
   - Verify `tmux` binary exists (fatal error if not)
   - Create new tmux window
   - Window naming with timestamp collision avoidance

2. **Command format:**
   ```bash
   claude --system .ucas/tmp/merged.md \
          --tools /path/to/agent/skills \
          --model sonnet-3.5
   ```

**Note:** No PATH manipulation. Skills passed only via ACLI's `arg_mapping.skills_dir`.

**Verify:** `python -m ucas run basic-chat` opens tmux window running claude.

---

## Slice 3: Mods Support

**Goal:** `ucas run agent +mod1 +mod2` merges configs, prompts, and skills.

**Changes:**

1. **ucas/cli.py** - Parse `+mod` arguments, preserve order

2. **ucas/merger.py** - Full sandwich merge
   - Load order: system → agent → mod1 → mod2 → ...
   - Dict keys: "last wins"
   - Skills: aggregate all `skills/` directories

3. **ucas/launcher.py** - Prompt concatenation
   - Concatenate PROMPT.md: agent → mod1 → mod2 (separated by `---`)
   - Save to `.ucas/tmp/<agent>.merged.md`

4. **agents/git-mod/** - Test mod with skills/

**Verify:** `python -m ucas run basic-chat +git-mod --dry-run` shows merged command with multiple `--tools`.

---

## Slice 4: Three-Layer Search

**Goal:** Full Project → User → System resolution with overrides.

**Changes:**

1. **ucas/resolver.py** - Multi-layer search
   - Order: `./.ucas/agents/` → `~/.ucas/agents/` → `$UCAS_HOME/agents/`
   - First match wins

2. **ucas/merger.py** - Complete 11-layer sandwich:
   ```
   1. $UCAS_HOME/ucas.yaml        # System defaults
   2. ~/.ucas/ucas.yaml           # User defaults
   3. ./.ucas/ucas.yaml           # Project defaults
   4. agent/ucas.yaml             # Main agent
   5-N. mod/ucas.yaml             # Mods in CLI order
   ─────────────────────────────────
   N+1. $UCAS_HOME/ucas-override.yaml  # System veto
   N+2. ~/.ucas/ucas-override.yaml     # User veto
   N+3. ./.ucas/ucas-override.yaml     # Project veto (strongest)
   ```

3. **ACLI selection** (Section 6 of spec):
   - `override_acli` → veto power
   - `executable` already in config?
   - Agent's `default_acli` in `allowed_acli`?
   - User/project `default_acli`
   - Fallback: first `allowed_acli`

4. **ucas/launcher.py** - Model mapping logic (full implementation)
   - `translate_model(requested_model, acli_config)`:
     1. Check if `requested_model` exists in ACLI's `model_mapping`
     2. If not found, use `model_mapping["default"]` if exists
     3. If no mapping and no default:
        - `ignore_unknown: false` (or missing) → **FATAL ERROR** (stop execution)
        - `ignore_unknown: true` → skip `--model` flag, **log WARNING**
     4. Return translated model name

5. **ucas/cli.py** - Add `--debug` flag (verbose merge tracing)

**Verify:**
- Create `.ucas/ucas-override.yaml` with `override_acli`, confirm it wins
- Test agent with unknown model + `ignore_unknown: false` → error
- Test agent with unknown model + `ignore_unknown: true` → warning, no model flag

---

## Slice 5: Teams

**Goal:** `ucas run-team backend-squad` runs multiple agents sequentially.

**Changes:**

1. **ucas/cli.py** - Add `run-team <team-name>` command

2. **ucas/resolver.py** - Team search in `teams/` directories

3. **ucas/launcher.py** - Team execution
   - Iterate members sequentially
   - Optional `sleep_seconds` between starts
   - Each member gets own tmux window

4. **ucas/merger.py** - Team layer (position 3, after User, before Project)

5. **teams/example-team/** - Test team definition:
   ```yaml
   name: "example-team"
   members:
     agent1:
       agent: "basic-chat"
     agent2:
       agent: "basic-chat"
       mods: ["git-mod"]
   ```

**Verify:** `python -m ucas run-team example-team --dry-run` prints commands for all members.

---

## Documentation (After MVP)

1. **README.md** - Quick start, installation, basic usage
2. **docs/USAGE.md** - User guide, CLI reference, examples
3. **docs/CONFIGURATION.md** - Config reference, ACLI selection logic
4. **docs/ARCHITECTURE.md** - Developer guide, module overview

---

## Key Technical Decisions

1. **No external dependencies** - Python 3.6+ stdlib only, custom YAML parser
2. **Skills as arguments** - No PATH manipulation, skills passed via `arg_mapping.skills_dir`
3. **First match wins** - Entity search stops at first found (Project → User → System)
4. **Last wins merge** - Dict keys overwritten by later layers
5. **Skills aggregated** - All `skills/` directories collected and passed
6. **Model mapping** - ACLI translates agent's `requested_model` to supported model
   - Defined in ACLI's `model_mapping` dict
   - Fallback via "default" key
   - Error handling via `ignore_unknown` flag

---

## Verification Checklist

- [ ] Slice 1: `python -m ucas run basic-chat --dry-run` prints command with translated model
- [ ] Slice 2: `python -m ucas run basic-chat` runs in tmux
- [ ] Slice 3: `python -m ucas run basic-chat +git-mod --dry-run` shows merged skills
- [ ] Slice 4: Override files respected, `--debug` shows merge trace, model_mapping works
  - [ ] Agent with `gpt-4` → translates to `sonnet-3.5`
  - [ ] Agent with unknown model + `ignore_unknown: false` → error
  - [ ] Agent with unknown model + `ignore_unknown: true` → warning
- [ ] Slice 5: `python -m ucas run-team example-team` runs all members
