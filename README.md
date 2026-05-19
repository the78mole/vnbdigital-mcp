# vnbdigital-mcp

MCP-Server für den Zugriff auf die [vnbdigital.de](https://www.vnbdigital.de)-Datenbank
mit Informationen über deutsche Verteilnetzbetreiber (VNB).

Der Server basiert auf dem verifizierten [vnbdigital-client](https://github.com/the78mole/vnbdigital-client)
und stellt die Daten über das [Model Context Protocol (MCP)](https://modelcontextprotocol.io) bereit.

## Tools

| Tool | Beschreibung |
|------|-------------|
| `get_operator` | Basis-Stammdaten eines VNB per BDEW-Code/ID |
| `get_operator_details` | Detailinfos inkl. Dienste, Dokumente, Logo |
| `get_operators` | Batch-Abfrage für bis zu 50 IDs gleichzeitig |

## Installation

### Voraussetzungen

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/)

### Abhängigkeiten installieren

```bash
uv sync
```

### Server starten (Entwicklung)

```bash
uv run vnbdigital-mcp
# oder
uv run python -m vnbdigital_mcp.server
```

### Mit MCP Inspector testen

```bash
uv run mcp dev src/vnbdigital_mcp/server.py
```

## Konfiguration in VS Code / Claude Desktop

Füge den Server zu deiner MCP-Konfiguration hinzu:

```json
{
  "servers": {
    "vnbdigital": {
      "command": "/home/daniel/.local/bin/uv",
      "args": [
        "--directory", "/path/to/vnbdigital-mcp",
        "run", "vnbdigital-mcp"
      ]
    }
  }
}
```

> **Hinweis:** VS Code erbt `~/.local/bin` oft nicht im PATH. Den absoluten Pfad zu `uv`
> ermitteln mit `which uv`. Optional können `VNBDIGITAL_API_URL` und `VNBDIGITAL_TIMEOUT`
> als `env`-Einträge ergänzt werden.

## Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `VNBDIGITAL_API_URL` | `https://www.vnbdigital.de/gateway/graphql` | GraphQL-Endpunkt |
| `VNBDIGITAL_TIMEOUT` | `30` | HTTP-Timeout in Sekunden |

## Beispiel-Abfragen

### Operator per ID

```
BDEW-Codes einiger bekannter Netzbetreiber:
- 179  → Netz Lübeck GmbH
- 180  → Stadtwerke Duisburg AG (Netz)
- 99   → Bayernwerk Netz GmbH
```

### Batch-Abfrage

Das Tool `get_operators` akzeptiert eine Liste von IDs und gibt alle
Ergebnisse in einem Aufruf zurück.

## Lokale Entwicklung

```bash
# Projekt-Umgebung aufbauen
uv sync --extra dev

# Linting & Formatierung
uv run ruff format .
uv run ruff check --fix .

# Tests
uv run pytest
```

## Lizenz

MIT
