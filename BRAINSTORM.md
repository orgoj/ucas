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
├── ucas.yaml               # System Defaults (fallback_acli: acli-pi)
├── ucas-override.yaml      # System Veto (zřídka)
├── teams/                  # Ukázkové týmy
└── agents/                 # System Library
    ├── acli-pi/            # Defaultní ACLI
    ├── acli-claude/        # Defaultní ACLI
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
type: "agent"
recommend:
  acli: "acli-claude"   # Jen preference, ne příkaz
  model: "sonnet-3.5"
skills: ["./skills"]    # Automaticky přidáno do PATH

```



### II. MOD (The Overlay)

Modifikace agenta. Strukturou shodný s agentem. Slouží k vrstvení schopností.

### III. ACLI (The Runner)

Abstrakce nástroje. **Jediné místo s definicí `executable`.**

* **Obsah:** `ucas.yaml` s mapováním argumentů.
* **Příklad `ucas.yaml`:**
```yaml
type: "acli"
executable: "claude"     # Reálná binárka v systému
arg_mapping:
  prompt_file: "--system"
  skills_dir: "--tools"
  model_flag: "--model"

```



---

## 5. Prioritní Logika (The Sandwich Merge)

UCAS načítá konfigurace a provádí `dict.update` (přebíjí starší hodnoty).

### A. Základna (Base Layer)

*Načítá se vždy.*

1. `$UCAS_HOME/ucas.yaml` (System Defaults)
2. `~/.ucas/ucas.yaml` (User Defaults)
3. `./.ucas/ucas.yaml` (Project Defaults)

### B. Aktéři (The Actor Layer)

*Načítá se podle příkazu `ucas run [AGENT] +[MOD]`.*
4.  **Agent Config** (hledá se v Project -> User -> System)
5.  **Mod Configs** (v pořadí z CLI args)

### C. Veto (Override Layer)

*Načítá se nakonec pro vynucení pravidel.*
6.  `$UCAS_HOME/ucas-override.yaml` (System Veto)
7.  `~/.ucas/ucas-override.yaml` (User Veto)
8.  `./.ucas/ucas-override.yaml` (Project Veto - Nejsilnější)

---

## 6. Logika Výběru ACLI (The Selector)

UCAS musí rozhodnout, který **ACLI Mod** se použije pro spuštění. Rozhoduje se po kompletním Mergi stacku:

1. **Project Override:** `force_acli` v `./.ucas/ucas-override.yaml`. -> **VÍTĚZ**
2. **CLI Argument:** `ucas run ... +acli-gemini`. -> **VÍTĚZ**
3. **Agent Recommendation:** `recommend: { acli: ... }` v agentovi. -> **VÍTĚZ**
4. **User Fallback:** `default_acli` v `~/.ucas/ucas.yaml`. -> **VÍTĚZ**
5. **System Fallback:** `fallback_acli` v `$UCAS_HOME/ucas.yaml`. -> **VÍTĚZ**

*Pokud ani po tomto kroku není vybrán ACLI -> ERROR.*

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

## 9. Implementační Plán (The "One Hour" Scope)

### Modul `resolver.py`

* `find_path(name)`: Hloubkové hledání ve vrstvách Project -> User -> System.

### Modul `merger.py`

* `load_sandwich()`: Načtení configů ve správném pořadí.
* `merge_logic()`: Update dictů, append listů, union setů (skills).

### Modul `launcher.py`

* `resolve_acli()`: Implementace prioritního výběru.
* `build_command()`: Dosazení do `arg_mapping`.
* `run_tmux()`: Volání `subprocess`.
