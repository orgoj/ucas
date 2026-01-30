# UCAS: Technical Specification v1.0 (Master Edition)

## 1. Filosofie a Role

**UCAS** (Unified Configurable Agent Starter) je **inteligentní assembler** a **launcher**.

* **Role:** Najít definice (Agent, Mod, ACLI), sloučit je podle priorit, sestavit exekuční příkaz a spustit ho v `tmux`.
* **Princip:** Striktní oddělení Dat (Agent) od Nástroje (ACLI).
* **Architektura:** Tři vrstvy (Project > User > System).

---

## 2. Příkazová Řádka (CLI)

Program se volá jako `ucas` s následující syntaxí:

### Příkazy

1. **Spuštění Agenta:**
```bash
ucas run [AGENT_NAME] +[MOD1] +[MOD2] ... [OPTIONS]
# Příklad: ucas run php-master +git-mod +acli-claude --debug

```


2. **Spuštění Týmu:**
```bash
ucas run-team [TEAM_NAME] [OPTIONS]
# Příklad: ucas run-team backend --dry-run

```



### Přepínače (Options)

* `--dry-run`: **Simulace.** Provede celý proces hledání, mergování a generování promptu, ale **nespustí tmux**. Vypíše finální sestavený příkaz na stdout (pro kontrolu).
* `--debug`: **Verbose mode.** Vypisuje detailní logiku "Sandwich Merge" (který soubor přebil který klíč, kde se našel jaký skill).

---

## 3. Adresářová Struktura (The Three-Layer Database)

UCAS vyhledává konfigurace v tomto pořadí priorit (od nejvyšší po nejnižší).

### 1. Vrstva: PROJEKT (Local Context)

*Nejvyšší priorita. Specifické pro daný úkol.*
**Cesta:** `./.ucas/` (v aktuálním adresáři)

```text
./.ucas/
├── ucas.yaml               # Project Base (Env, Defaults)
├── ucas-override.yaml      # Project Veto (Override ACLI)
├── tmp/                    # (Auto) Generované prompty (karel.merged.md)
├── mem/                    # (Auto) Paměť agentů
├── teams/                  # Lokální týmy
└── agents/                 # Lokální mody a agenti

```

### 2. Vrstva: USER (Personal Config)

*Střední priorita. Osobní nastavení uživatele.*
**Cesta:** `~/.ucas/`

```text
~/.ucas/
├── ucas.yaml               # User Defaults
├── ucas-override.yaml      # User Veto
├── teams/                  # Globální týmy
└── agents/                 # Osobní knihovna

```

### 3. Vrstva: SYSTEM / REPO (Factory Defaults)

*Nejnižší priorita. Distribuční základ.*
**Cesta:** `/opt/ucas/` (nebo `$UCAS_HOME`)

```text
$UCAS_HOME/
├── ucas.yaml               # System Defaults (allowed_acli, default_acli)
├── ucas-override.yaml      # System Veto (zřídka)
├── teams/                  # Ukázkové týmy
└── agents/                 # System Library
    ├── acli-claude/        # ACLI pro Claude
    ├── acli-zai/           # ACLI pro Z.AI
    ├── basic-chat/         # Defaultní agenti
    └── utils/              # Společné mody

```

---

## 4. Entity a Definice

### I. AGENT (The Know-How)

Čistá data. **Nemá executable.**

* **Obsah:** `PROMPT.md`, `skills/` (skripty), `ucas.yaml`.
* **Příklad `ucas.yaml`:**
```yaml
default_acli: "acli-claude"   # Preference agenta (musí být v allowed_acli)
```

*Poznámka: Modely řeší ACLI, ne agent. Agent říká CO chce dělat, ACLI řeší JAK.*

* **Skills:** Každý agent může mít adresář `skills/` - všechny se agregují do PATH.

### II. MOD (The Overlay)

**Každý agent může být použit jako mod.** Strukturou shodný s agentem. Slouží k vrstvení schopností na jiného agenta.

### III. ACLI (The Runner)

Abstrakce nástroje. **Pozná se podle přítomnosti `executable` klíče.**

* **Obsah:** `ucas.yaml` s executable, mapováním argumentů a mapováním modelů.
* **Příklad `ucas.yaml`:**
```yaml
executable: "claude"     # Přítomnost tohoto klíče = ACLI
arg_mapping:
  prompt_file: "--system"
  skills_dir: "--tools"
  model_flag: "--model"

model_mapping:
  # Agent požaduje → ACLI dostane
  "gpt-5.2-pro": "opus-4.5"
  "codex": "opus-4.5"
  "gpt-4": "sonnet-3.5"
  "default": "sonnet-3.5"    # Fallback když není mapování
```

### Model Mapping - Logika

UCAS přeloží požadavek agenta na model podporovaný vybraným ACLI:

```
1. Agent má: requested_model: "gpt-5.2-pro"
2. Vybraný ACLI má: model_mapping
3. UCAS přeloží: "gpt-5.2-pro" → "opus-4.5"
4. Výsledný příkaz: claude --model opus-4.5 --system ...
```

### Příklad: Levný Claude ACLI

Uživatel si vytvoří vlastní ACLI variantu pro úsporu nákladů:

```yaml
# ~/.ucas/agents/acli-claude-cheap/ucas.yaml
executable: "claude"
arg_mapping:
  prompt_file: "--system"
  model_flag: "--model"

model_mapping:
  # Všechno mapuj na Haiku = levné
  "opus-4.5": "haiku-3.5"
  "sonnet-3.5": "haiku-3.5"
  "gpt-5.2-pro": "haiku-3.5"
  "default": "haiku-3.5"
```

Pak stačí v projektu:
```yaml
# ./.ucas/ucas.yaml
allowed_acli: ["acli-claude-cheap"]
```

A všichni agenti v tomto projektu pojedou na Haiku, bez ohledu na jejich `requested_model`.

*Poznámka: ACLI je jen agent s `executable` → lze ho definovat na libovolné vrstvě (system/user/project). Projekt si může předefinovat `acli-claude-cheap` po svém, aniž by ovlivnil ostatní projekty. Hledání: Project → User → System, první nalezený vyhrává.*



---

## 5. Prioritní Logika (The Sandwich Merge)

UCAS načítá konfigurace a provádí `dict.update` (každý další přebíjí předchozí hodnoty).

### Kompletní Stack (v pořadí načítání)

```
LOAD ORDER (poslední vyhrává):

 1. $UCAS_HOME/ucas.yaml        # System Defaults
 2. ~/.ucas/ucas.yaml           # User Defaults
 3. team/ucas.yaml              # Team config (jen při run-team)
 4. ./.ucas/ucas.yaml           # Project Defaults
 5. agent/ucas.yaml             # Hlavní agent
 6. mod1/ucas.yaml              # První mod z CLI
 7. mod2/ucas.yaml              # Druhý mod z CLI (přebije mod1)
 8. ...                         # Další mody v pořadí z CLI args
────────────────────────────────────────────────────
 9. $UCAS_HOME/ucas-override.yaml   # System Veto
10. ~/.ucas/ucas-override.yaml      # User Veto
11. ./.ucas/ucas-override.yaml      # Project Veto (NEJSILNĚJŠÍ)
```

### Pravidla

* **Base vrstvy (1-8):** Postupně se načítají a přebíjejí. Mody se aplikují v pořadí z CLI.
* **Override vrstvy (9-11):** Vždy na konci. Slouží k vynucení pravidel (např. `override_acli`).
* **Team vrstva (3):** Pouze při `ucas run-team`, jinak se přeskakuje.
* **Hledání entit:** Agent/Mod se hledá v Project → User → System (první nalezený vyhrává).

---

## 6. Logika Výběru ACLI (The Selector)

Vše se vyřeší v rámci jednoho **Merged Configu** s respektováním dostupných CLI nástrojů.

### Konfigurace

```yaml
# ~/.ucas/ucas.yaml (User)
allowed_acli: ["acli-claude", "acli-zai"]  # Co mám zaplacené/dostupné
default_acli: "acli-claude"                 # Moje preference

# ./.ucas/ucas.yaml (Project)
allowed_acli: ["acli-zai"]                  # Omezení pro tento projekt
```

### Resolution (Vyhodnocení)

Po Sandwich Merge má UCAS `final_config` a postupuje takto:

```
1. override_acli? 
   → použij (veto - bez kontroly allowed)

2. executable už v configu? 
   → hotovo (přišlo z +acli-mod v CLI)

3. default_acli z agenta?
   → JE v allowed_acli? → použij
   → NENÍ? → pokračuj

4. default_acli z user/project?
   → JE v allowed_acli? → použij

5. fallback: první z allowed_acli

6. Nic? → ERROR
```

### Příklady použití

**Agent chce Codex, já mám jen Claude a Z.AI:**
```
Agent:   default_acli: "acli-codex"
User:    allowed_acli: ["acli-claude", "acli-zai"]
→ Codex NENÍ v allowed → fallback na acli-claude
```

**Agent chce Claude, já ho mám:**
```
Agent:   default_acli: "acli-claude"
User:    allowed_acli: ["acli-claude", "acli-zai"]
→ Claude JE v allowed → použije se Claude
```

**Sranda projekt - jen levné CLI:**
```
Project: allowed_acli: ["acli-zai"]
Agent:   default_acli: "acli-claude"
User:    allowed_acli: ["acli-claude", "acli-zai"]
→ Project přebil user allowed → Claude NENÍ povolen → fallback na acli-zai
```

**Vynucení konkrétního CLI:**
```
Project: override_acli: "acli-zai"
Agent:   default_acli: "acli-claude"
→ Override = veto → použije se acli-zai (bez ohledu na allowed)
```

**Detekce ACLI:** Entita je ACLI pokud její `ucas.yaml` obsahuje klíč `executable`.

---

## 7. Algoritmus Exekuce (The Workflow)

**Vstup:** `ucas run php-master +git-mod --dry-run`

### Krok 1: Resolver (Search)

* Rekurzivně prohledá `agents` složky ve všech 3 vrstvách.
* Najde cesty k `php-master` a `git-mod`.

### Krok 2: Merge (The Brain)

* **ENV:** Spojí ENV proměnné ze všech vrstev (Sandwich).
* **SKILLS:** Najde složky `skills/` u Agenta i Modů.
* **PROMPT:** Spojí `PROMPT.md` Agenta a Modů (oddělovač `---`).
* **ACLI:** Vybere vítězný ACLI Mod (např. `acli-claude`) a načte jeho mapování.

### Krok 3: Generate (Artifacts)

* Uloží sloučený prompt do `./.ucas/tmp/[session].merged.md`.
* Sestaví `$PATH` = `[AgentSkills] : [ModSkills] : $PATH`.

### Krok 4: Launch (Tmux/Dry-Run)

* Načte definici vítězného ACLI (`executable` + `arg_mapping`).
* Dosadí vygenerované cesty do argumentů.
* **Pokud `--dry-run`:** Vypíše příkaz na stdout a skončí.
* **Pokud Run:**
```bash
tmux new-window -n "php-master" "export PATH=...; claude --system ./.ucas/tmp/merged.md --tools ..."

```



---

## 8. Týmy (Orchestration)

* **Příkaz:** `ucas run-team [TEAM_NAME]`
* **Definice:** YAML soubor v `teams/[TEAM_NAME]/ucas.yaml`.
* **Struktura:**
```yaml
name: "backend-squad"
members:
  karel:
    agent: "php-master"
    mods: ["git-mod", "debug-mod"]
  pepa:
    agent: "sql-guru"

```


* **Proces:** Iteruje členy a pro každého spustí **Algoritmus Exekuce** (body 1-7). Každý člen dostane své okno v tmux.

---

## 9. Technické Požadavky

### Python Kompatibilita

* **Minimální verze:** Python 3.6+
* **Žádné externí závislosti** - pouze stdlib

### Mini YAML Parser

Vlastní implementace YAML parseru (bez PyYAML závislosti).

**Podporované typy:**
- dict (nested)
- list
- string (s/bez uvozovek)
- bool (true/false/yes/no)
- null
- komentáře (#)

**Nepodporované (YAGNI):**
- anchors/aliases
- multiline strings
- complex keys
- tags

---

## 10. Implementační Plán (MVP Scope)

### Modul `yaml_parser.py`

* Mini YAML parser (viz sekce 9)
* `parse(text) -> dict`: Hlavní funkce

### Modul `cli.py`

* Parsování CLI argumentů (argparse)
* Rozpoznání `run` vs `run-team` příkazu
* Extrakce agent name, modů (`+mod`), flagů (`--dry-run`, `--debug`)

### Modul `resolver.py`

* `find_entity(name)`: Hledání ve vrstvách Project → User → System (první nalezený)
* `is_acli(entity)`: Detekce ACLI podle přítomnosti `executable` klíče

### Modul `merger.py`

* `load_sandwich(agent, mods, is_team)`: Načtení configů ve správném pořadí (1-11)
* `merge_configs(configs)`: Update dictů, agregace skills paths

### Modul `launcher.py`

* `select_acli(merged_config, cli_mods)`: Prioritní výběr ACLI (sekce 6)
* `build_command(acli, merged_config)`: Dosazení do `arg_mapping`
* `generate_prompt(agent, mods)`: Concatenace PROMPT.md souborů
* `run_tmux(command, name)`: Spuštění v novém tmux okně

### Rozsah MVP

- `ucas run [agent] +[mod]` - spuštění agenta
- `ucas run-team [team]` - loop přes členy, volá interní `run()`
- `--dry-run` - výpis příkazu bez spuštění
- `--debug` - verbose merge tracing
- Třívrstvé hledání entit
- Kompletní sandwich merge
