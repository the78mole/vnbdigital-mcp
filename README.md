# vnbdigital-mcp

MCP server for accessing the [vnbdigital.de](https://www.vnbdigital.de) database
of German distribution grid operators (Verteilnetzbetreiber, VNB).

Built on top of the verified [vnbdigital-client](https://github.com/the78mole/vnbdigital-client)
library and exposes the data via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io).

## Tools

### vnbdigital.de lookups

| Tool | Description |
|------|-------------|
| `get_operator` | Basic master data for an operator by BDEW code or vnbdigital ID |
| `get_operator_details` | Full details including services, documents and logo |
| `get_operators` | Batch lookup for up to 50 IDs in a single call |
| `search` | Free-text search (postcode, name, city, region) |
| `search_by_coordinates` | Find responsible operators for a GPS coordinate (lat/lon) |
| `search_by_postcode` | Find responsible operators for a German postcode |
| `get_nsp_operator` | Low-voltage (Niederspannung) operator for a postcode or coordinate |
| `get_msp_operator` | Medium-voltage (Mittelspannung) operator for a postcode or coordinate |

### BDEW register lookups (bdew-codes.de)

| Tool | Description |
|------|-------------|
| `bdew_lookup_by_company_code` | Look up a company by its 6–7 digit BDEW CompanyUId |
| `bdew_lookup_by_market_code` | Look up a company by a 13-digit BDEW market function code |
| `bdew_get_market_function_detail` | Fetch address and contact details for a market function entry |

> **Note:** Company names in the BDEW register do not always match those on vnbdigital.de.
> Use both sources together for cross-referencing.

## Installation

### Prerequisites

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/)

### Install dependencies

```bash
uv sync
```

### Start the server (development)

```bash
uv run vnbdigital-mcp
# or
uv run python -m vnbdigital_mcp.server
```

### Test with MCP Inspector

```bash
uv run mcp dev src/vnbdigital_mcp/server.py
```

## Configuration in VS Code / Claude Desktop

Add the server to your MCP configuration (`.vscode/mcp.json` or `claude_desktop_config.json`):

```json
{
  "servers": {
    "vnbdigital": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/vnbdigital-mcp",
        "run", "vnbdigital-mcp"
      ],
      "env": {
        "PATH": "${userHome}/.local/bin:${env:PATH}"
      }
    }
  }
}
```

> **Note:** VS Code does not always inherit `~/.local/bin` in its PATH.
> The `env.PATH` entry above ensures `uv` is found.
> For VS Code workspaces you can use `"${workspaceFolder}"` instead of the absolute path.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VNBDIGITAL_API_URL` | `https://www.vnbdigital.de/gateway/graphql` | GraphQL endpoint |
| `VNBDIGITAL_TIMEOUT` | `30` | HTTP timeout in seconds |
| `BDEW_LOOKUP_URL` | `https://bdew-codes.de` | Base URL for BDEW lookups |

## Example Queries

### Operator by ID

```text
Known example IDs:
- 179  → ESTW - Erlanger Stadtwerke AG
- 180  → Stadtwerke Eschwege GmbH
- 99   → Stadtwerke Bramsche GmbH
```

### Operators for a location

`get_nsp_operator` and `get_msp_operator` accept either a 5-digit postcode
or a `"lat,lon"` coordinate string:

```python
get_nsp_operator("97816")            # by postcode
get_nsp_operator("49.998037,9.58033")  # by coordinates
```

### BDEW lookup

```python
bdew_lookup_by_company_code(660188)          # → A&A Stromallianz GmbH
bdew_lookup_by_market_code("9903445000000")  # → same company, one market function
bdew_get_market_function_detail(141)         # → address/contact for that market function
```

## Local Development

```bash
# Set up project environment
uv sync

# Linting & formatting
uv run ruff format .
uv run ruff check --fix .

# Tests
uv run pytest
```

## License

MIT
