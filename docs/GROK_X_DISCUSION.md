Ano, díky za vysvětlení – teď to dává mnohem jasnější obrázek. UCAS (Universal CLI Agent System) jde opravdu jiným směrem než Gas Town a spousta dalších multi-agent nástrojů z roku 2025/2026. Zatímco většina (Gas Town, Conductor, Vibe Kanban, OpenClaw swarmy atd.) se soustředí na **high-throughput paralelismus** (spousta agentů najednou, rychlé generování kódu, auto-merge), ty jdeš cestou **udržitelného, modulárního a komunikačního manažera**, kde je klíčové:

- **Předplatné-friendly** – agenti běží dlouhodobě, ne YOLO burn API tokenů za hodinu
- **Modulární definice** – libovolný CLI tool se stane "mode" / skill → agent + CLI = jen další vrstva
- **Komunikace jako core feature** – EML mail systém mezi agenty, projekty a potenciálně mezi počítači (cross-project addressing `agent@/path`, auto-reply, team autostart na nový mail)

To je v současném ekosystému (únor 2026) poměrně unikátní a řeší reálné bolesti, které mají lidé s Gas Town-style swamy.

### Porovnání Gas Town vs. UCAS (z pohledu tvého popisu)

| Aspekt                        | Gas Town (Steve Yegge)                              | UCAS (tvůj koncept)                                      |
|-------------------------------|-----------------------------------------------------|------------------------------------------------------------------|
| **Hlavní cíl**                | Maximální throughput – paralelní coding swarm (20–30+ agentů) | Udržitelná orchestrace + komunikace mezi agenty/projekty/machines |
| **API spotřeba**              | Extrémně vysoká (často $100–300+/hod při plném běhu) | Nízká – dlouhodobí agenti na předplatném (Claude/Gemini/Pi), žádný burn |
| **Paralelismus**              | Brut force – stovky tasků najednou, auto-merge PRs | Kontrolovaný – týmový management (`team run/stop/status`), ne swarm |
| **Komunikace mezi agenty**    | Pasivní přes git/Beads (state sharing), žádný messaging | Aktivní EML mail systém – adresování, inbox, auto-reply, cross-project |
| **Cross-project / cross-machine** | Velmi omezené (jen git repo sdílení)               | Vestavěné – `agent-name@/path/to/project`, potenciál pro síť (budoucnost?) |
| **Modularita**                | Role-based (Mayor, Deacon, Refinery…), ale pevně coding-focused | Plně modulární – +git, +docker, +libovolný CLI jako skill/mod |
| **Viditelnost & kontrola**    | Špatná – mental model drift, agenti pracují dny bez dozoru | Lepší – status, mail inbox, dry-run, team management |
| **Typické použití**           | Velké refaktory / feature bomby v monorepu (senior dev experiment) | Dlouhodobé projekty, knowledge compounding, agent-to-agent spolupráce |
| **Cena udržitelnosti**        | Nízká (lidi to pálí jen na burst)                  | Vysoká – běží týdny/měsíce bez šílených nákladů |
| **Maturity (nyní)**           | Experiment s diskuzí (HN/Reddit/X), ale kritika chaosu | Early stage (44 commitů, 0★), ale koncept silný a řeší reálné problémy |

### Proč je tvůj přístup teď zajímavý (únor 2026)
Většina lidí, co zkusila Gas Town / swarmy / 10+ paralelních Claude Code instancí, nakonec říká:
- „Super rychlé na první 2–3 dny, pak chaos + burn rate + nepoužitelné PRs.“
- Chtějí **compounding knowledge** (jako flywheel), ne jen throughput.
- Chtějí **komunikaci mezi agenty** – nejen sdílený git, ale skutečné zprávy, požadavky, notifikace.
- Chtějí **multi-project setup** – agent v projektu A pošle task agentovi v projektu B (např. shared utilita, docs, security audit).
- Chtějí to **levně a dlouhodobě** – předplatné Claude / Gemini / Pi → ideální pro UCAS.

Tvůj EML mail + cross-project addressing + modulární CLI skills jde přesně tímhle směrem. Je to bližší k „agentic OS“ nebo „agent Slack/mail server“ než k „Kubernetes pro agenty“ (což je Gas Town).

### Možné next steps / vylepšení (jen nápady)
- **Síťová komunikace** – pokud to ještě není, přidat jednoduchý server (websocket / HTTP endpoint) pro cross-machine mail → agenti na různých PC/laptopy/VM.
- **Integrace s existujícími** – např. bridge na OpenCode / Aider / Codex CLI jako mod (spustit je jako sub-proces a parsovat výstup do mailu).
- **Knowledge base** – mail archiv + search → agenti si mohou ptát „co jsme řešili minule v projektu X?“
- **Human-in-the-loop** – mail notifikace na Slack/Discord/terminal pro tebe, abys mohl odpovídat / schvalovat.
- **Observability** – jednoduchý dashboard (třeba textový TUI) ukazující running týmy, pending maily, API usage.

---

Ano, ten koncept, který popisuješ, je super – přesně řeší bolesti současných multi-agent systémů, kde se většina zaměřuje na "rychlý výkon na jednom projektu" (jako Gas Town nebo Vibe Kanban), ale ignoruje dlouhodobou přenositelnost, sdílení znalostí napříč projekty a udržitelnost. UCAS (podle aktuálního stavu na GitHubu v únoru 2026 – 44 commitů, modulární config s "sandwich merge", EML mail pro komunikaci, mods pro skills) je ideální základ pro to, co navrhuješ: agenti jako přenositelné "hromady promptů" orchestrované UCASem, běžící současně na více projektech, sbírající zkušenosti a kopírovatelné mezi systémy/machines.

### Proč to dává smysl v kontextu trendů 2026
- **Od throughputu k compounding knowledge**: Lidi jako v "flywheel" komunitě (Emmanuel, Maggie Appleton na X) kritizují swamy za chaos, ale chválí systémy, kde agenti buildí na minulých zkušenostech (např. shared memory v Agent Mail nebo beads v Gas Town). Tvůj přístup – agenti jako přenositelné prompty + orchestrace – jde dál: nejen na jednom projektu, ale napříč ekosystémem (projekty, machines).
- **Modulární napříč projekty**: Místo "jednorázového swarmu" (jako v Gas Town), UCAS umožňuje agenty běžet dlouhodobě (předplatné-friendly, nízký API burn), komunikovat mezi sebou (EML mail s cross-project addressing jako `agent@/path/to/project`), a sdílet mods/skills (+git, +docker, +custom CLI).
- **Přenositelnost jako core**: Agenti jsou jen config (prompty v ucas.yaml) – snadno kopírovatelné (cp/rsync mezi machines), upgradovatelné (sdílené mod layers v ~/.ucas/mods/ nebo system-wide).

### Jak to realizovat: Přenositelnost, multi-project a sbírání zkušeností
- **Přenos agentů mezi systémy**: Protože agent je "jen hromada promptů" (v yaml s vrstvami System/User/Project/Agent/Mods), stačí kopírovat ucas.yaml + relevantní mods. UCAS by mohl přidat command jako `ucas export agent-name --to-file` (vytvoří tar/zip s configem, mailem history a learnings) a `ucas import --from-file`. Pro cross-machine: rozšířit EML mail na síťový protokol (např. simple HTTP endpoint nebo webhook pro mail delivery mezi IP/hosts) – agenti by si pak mohli "volat" přes síť, nejen lokálně.
- **Současný běh na různých projektech**: Už teď UCAS podporuje `ucas team run` pro týmy agentů, s autostartem na mail. Pro multi-project: přidat globální orchestraci, např. `ucas global run --projects /path1,/path2` – agenti běží paralelně v různých dirs, sdílejí mail inbox (shared ~/.ucas/mail/) a sbírají zkušenosti do centrálního logu (např. JSON DB pro "learnings" – co se naučili z tasků, failing pokusů, úspěšných fixes).
- **Sbírání zkušeností**: Agenti by mohli automaticky logovat interakce (maily, výstupy) do shared knowledge base (např. v ~/.ucas/learnings.db nebo git repo). Každý agent by měl "memory mod" (+memory), který injectuje relevantní past learnings do promptu (např. "Na základě minulého tasku v projektu X: [snippet]"). To by umožnilo compounding – agent se zlepšuje napříč projekty, ne resetuje se.
- **Kopírování mezi systémy**: Pro "klonování" agenta: `ucas clone agent-name --to /new/project` nebo `--to-host user@remote:~/project` (přes ssh/rsync). Zkušenosti by šly exportovat jako fine-tuned prompty (např. summarize learnings do nového yaml layeru).

### Nápad na "Školu pro agenty" – dotáhnutí konceptu
To je geniální! "Škola pro agenty" by mohla být rozšíření UCAS jako framework pro budování reusable agentů – nejen pro jeden tým, ale komunitní/enterprise-level. Představ si to jako:

- **Struktura**: Centrální repo (např. GitHub org pro UCAS mods/agent templates) s "třídami" (kategorie agentů: beginner/specialist/expert). Každý agent začíná jako base prompt (nováček), sbírá zkušenosti z projektů (trénink), a "promuje" – updatuje se na lepší verzi (např. auto-generate nový yaml layer z logů).
- **Mechaniky**:
  - **Tréninkový mod**: Nový mod +school, který spouští simulované tasky (např. benchmarky z open datasets) a ukládá metrics (úspěšnost, rychlost, kvalita outputu).
  - **Certifikace**: Agent "absolvuje" pokud splní criteria (např. 90% success na 10 taskech) – pak se exportuje jako reusable template.
  - **Komunita**: Sdílené "školy" – uživatelé uploadují své trained agenty do public repo (např. ucas-school.org), s tags jako "git-expert" nebo "docker-master". UCAS by měl `ucas install agent --from-school git-expert`.
  - **Napříč projekty**: Škola by generovala agenty optimalizované pro cross-project use – např. agent naučený na web dev projektu se adaptuje na ML projekt přes shared mods.
- **Výhody**: Řeší "cold start" problém – nový projekt dostane předtrénovaného agenta, ne prázdný prompt. Plus, je to udržitelné (nízký API usage během tréninku, pokud použiješ lokální modely jako Pi nebo open-source).

### Rychlé srovnání: UCAS s přenositelností vs. současné trendy

| Feature                  | UCAS (tvůj koncept + rozšíření) | Gas Town / Swamy | Flywheel-style (Agent Mail) |
|--------------------------|---------------------------------|------------------|-----------------------------|
| **Přenositelnost agentů** | Vysoká (kopírování yaml/promptů, export/import) | Nízká (jen git beads, projekt-specific) | Střední (shared memory, ale ne cross-machine) |
| **Multi-project běh**    | Ano (cross-project mail, global run) | Ne (jeden monorepo) | Ano (multi-project loops) |
| **Sbírání zkušeností**   | Ano (logy/learnings DB, compounding) | Částečně (beads) | Ano (flywheel loops) |
| **Modulární napříč systémy** | Ano (mods + síťový mail) | Ne | Částečně (custom scripts) |
| **Škola/reusability**    | Potenciál (templates + trénink) | Žádný | Žádný (ad-hoc) |

Tohle by UCAS posunulo od "jen orchestrátoru" k plnohodnotnému ekosystému pro budování agentů. Pokud máš už nějaký PoC na cross-machine nebo learnings log, nebo chceš brainstormovat konkrétní commandy/mody (např. jak implementovat +school), řekni – rád pomůžu dotáhnout detaily! 😄

--
