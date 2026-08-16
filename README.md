# Verantis MCP

<!-- mcp-name: io.github.m9labs-railscope/verantis-mcp -->

**The verified directory for machine payments — as an MCP tool.**

Give any MCP-capable agent (Claude, Cursor, agent frameworks) the ability to check
what it's about to pay *before* it pays. Verantis continuously probes machine-payable
services across **x402** and **MPP**, measures on-chain reputation, and publishes a
recomputable record. This server is a thin client of the public
[Verantis API](https://api.verantis.ai) — standard library only, no dataset needed.

Learn more: **[verantis.ai](https://verantis.ai)** · methodology: [verantis.ai/methodology](https://verantis.ai/methodology)

## Tools

| Tool | What it does |
|------|--------------|
| `find_paid_service` | Search the verified directory (x402 / MPP). Filter by verified-only, price, chain, protocol, category, reputation. |
| `get_service` | Full record + verification provenance for one domain. |
| `check_wallet` | **Pre-payment guard** — pass the recipient wallet a service asked you to pay; get its earned reputation tier, on-chain buyer retention, and which services it fronts. |
| `directory_stats` | Index-level stats: services, verification breakdown, freshness. |

## What it can and can't do

- **Can:** read the public directory; check a service or wallet before your agent pays.
- **Can't:** move money, see your keys, or read your files.
- Only ever calls `api.verantis.ai` — nothing else.
- Writes nothing (hosted endpoint) / only a random anonymous install id (local `pip`/`uvx`).
- No account, no API key. MIT-licensed. Read-only.
- How we measure: [verantis.ai/methodology](https://verantis.ai/methodology)

## Install & connect

Two ways to connect — pick one.

### Local (stdio) — via [`uvx`](https://docs.astral.sh/uv/), no install step

**Claude Desktop** (`claude_desktop_config.json`) or any MCP client:

```json
{
  "mcpServers": {
    "verantis": {
      "command": "uvx",
      "args": ["verantis-mcp"]
    }
  }
}
```

Prefer pip? `pip install verantis-mcp`, then use `"command": "verantis-mcp"` with no args.

**Cursor** (`~/.cursor/mcp.json`): same block under `mcpServers`.

### Hosted (no install) — connect by URL

For any client that supports remote / streamable-HTTP MCP servers, point it
straight at the hosted endpoint — nothing to install, no Python:

```json
{
  "mcpServers": {
    "verantis": { "url": "https://api.verantis.ai/mcp" }
  }
}
```

Clients that only speak local stdio can bridge with `npx mcp-remote https://api.verantis.ai/mcp`.

Restart your client, and the four tools appear.

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `VERANTIS_API_BASE` | `https://api.verantis.ai` | Point the client at a different Verantis API. |

## Notes

Informational only; not financial, investment, or legal advice. Classifications
describe what live probes and on-chain reads observed at a point in time and can
change. Reputation is *earned* from real on-chain settlement, not assumed. Verantis
has no rail of its own, no token, and no stake in any listed service.

MIT licensed.
