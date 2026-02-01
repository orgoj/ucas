# msg-mcp_agent_mail

Modul pro integraci UCAS s komunikačním systémem [mcp_agent_mail](https://github.com/Dicklesworthstone/mcp_agent_mail). Umožňuje agentům v týmu posílat a přijímat zprávy, koordinovat činnost a sdílet status.

## Funkce

- **Automatická registrace**: Každý agent se při startu automaticky zaregistruje v systému pod svým jménem v týmu.
- **Skill `mcp-mail`**: Poskytuje agentům nástroje pro práci s poštou (`am-client`).
- **Předkonfigurovaný klient**: Automaticky vytváří základní konfiguraci v `~/.mcp-agent-mail/client-config`.

## Použití pro agenty

Agenti mají k dispozici skill `mcp-mail`, který jim umožňuje používat příkaz `am-client`.

### Příklady příkazů:

- **Odeslání zprávy**:
  `am-client send --to Rudolf --subject "Hotovo" --body "Práce na modulu byla dokončena."`
- **Kontrola schránky**:
  `am-client inbox`
- **Čekání na důležité zprávy**:
  `am-client check-unread` (skončí chybou, pokud existují nepřečtené urgentní zprávy)

## Konfigurace a Tokeny

Výchozí konfigurace předpokládá, že server běží lokálně na `http://localhost:8765/mcp/` bez autentizace.

### Nastavení Bearer Tokenu:

Pokud váš server vyžaduje autentizaci (Bearer Token), můžete ho nastavit dvěma způsoby:

1.  **Pomocí CLI**:
    ```bash
    am-client config set-token VASE_TAJNE_HESLO
    ```
2.  **Environment proměnná (při první instalaci)**:
    Před prvním spuštěním agenta s tímto modem nastavte proměnnou:
    ```bash
    export AM_BEARER_TOKEN=VASE_TAJNE_HESLO
    ```

### Změna URL serveru:

Pokud server běží na jiném stroji:
```bash
am-client config set-url http://192.168.1.10:8765/mcp/
```

## Souborová struktura

- `ucas.yaml`: Definice modulu a lifecycle hooky.
- `skills/mcp-mail/`: Standardní skill pro AI agenty.
- `~/.mcp-agent-mail/client-config`: Místo uložení konfigurace klienta.
