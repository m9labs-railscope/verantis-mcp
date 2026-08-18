#!/usr/bin/env python3
"""
Verantis MCP server — the verified directory for machine payments.

A Model Context Protocol (stdio) server so any MCP-capable agent (Claude,
Cursor, agent frameworks) can, before it pays:
  find_paid_service   search the verified directory of x402 / MPP services
  get_service         full record + verification provenance for one domain
  directory_stats     index-level stats
  check_wallet        pre-payment guard: check a recipient wallet's earned
                      reputation and on-chain buyer retention BEFORE paying

Thin client of the public Verantis API (https://api.verantis.ai) — stdlib only,
no dependencies, no dataset needed. Point elsewhere with VERANTIS_API_BASE.
Neutral, continuously verified, recomputable. https://verantis.ai
"""

import json
import os
import sys
import uuid
import urllib.request
import urllib.parse
import urllib.error

API_BASE = os.environ.get("VERANTIS_API_BASE",
                          "https://api.verantis.ai").rstrip("/")
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "find_paid_service",
        "annotations": {"title": "Find a paid service", "readOnlyHint": True, "openWorldHint": True},
        "description": (
            "Search Verantis's verified directory of machine-payable "
            "services (x402, MPP). Results are UNIFIED per service (host): "
            "each carries its settlement rails ('rails': base / solana / "
            "tempo), and every rail has its OWN reputation, price, and buyer "
            "retention — never blended. Pass 'chain' and 'matched_rail' marks "
            "that chain's rail so you see the reputation for the rail you'll "
            "actually pay on. 'coming_soon' lists advertised chains not yet "
            "measured. Prefer verified=true before paying anyone."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "what you need, e.g. 'twitter data', 'web search', 'rpc ethereum'"},
                "verified_only": {"type": "boolean", "default": True,
                                  "description": "only services that passed the latest live probe"},
                "max_price_usd": {"type": "number",
                                  "description": "max price per call in USD"},
                "chain": {"type": "string",
                          "description": "settlement network, e.g. base, solana, polygon, tempo"},
                "protocol": {"type": "string", "enum": ["x402", "mpp"], "description": "restrict to one payment protocol: x402 or mpp"},
                "limit": {"type": "integer", "default": 10, "description": "maximum number of results to return (default 10)"},
                "min_score": {"type": "integer",
                              "description": "minimum trust score 0-100 — set high (e.g. 85) for money-moving tasks"},
                "max_latency_ms": {"type": "integer",
                                   "description": "reject services slower than this (ms)"},
                "exclude_concentrated": {"type": "boolean", "default": False,
                                         "description": "exclude services from operators with many listings under one registrable owner (a neutral concentration signal, not a fraud claim)"},
                "proven_only": {"type": "boolean", "default": False,
                                "description": "only services that have EARNED reputation over time (excludes 'new' services and 'watch' services whose on-chain payments are concentrated / not yet broadly distributed). Reputation is earned via consistent history + on-chain buyer retention; a brand-new well-behaved service is verified but new, not top-trust."},
                "require_fresh": {"type": "boolean", "default": False,
                                  "description": "live re-probe stale results before returning — use before paying real money; adds ~1s per stale service"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_service",
        "annotations": {"title": "Get a service record", "readOnlyHint": True, "openWorldHint": True},
        "description": ("Full unified record for one service host: every "
                        "settlement rail it accepts on, each with its own "
                        "reputation, price, buyers, volume and history, plus "
                        "coming-soon chains. Pass the host (domain)."),
        "inputSchema": {
            "type": "object",
            "properties": {"domain": {"type": "string", "description": "the service host / domain to look up, e.g. api.nansen.ai"}},
            "required": ["domain"],
        },
    },
    {
        "name": "directory_stats",
        "annotations": {"title": "Directory statistics", "readOnlyHint": True, "openWorldHint": True},
        "description": "Index-level statistics: services, verification breakdown, data freshness.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_wallet",
        "annotations": {"title": "Check a recipient wallet", "readOnlyHint": True, "openWorldHint": True},
        "description": (
            "Check a recipient wallet BEFORE your agent pays it — a pre-payment "
            "guard. Pass the pay-to address a service asked you to pay; returns "
            "whether Verantis knows the wallet, its EARNED reputation tier, and "
            "human-readable reasons. A wallet IS a settlement rail, so the reply "
            "names the rail it settles on ('rail': chain + protocols), its host, "
            "on-chain buyer retention (distinct buyers, repeat rate, distribution), "
            "and the host's OTHER rails ('also_settles_on'). If 'shared_wallet' is "
            "true the address fronts many services (a relay/treasury) so the "
            "reputation reflects the pool, not one service — treat with care. An "
            "unknown or low-reputation recipient is a reason to pause."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "pay_to": {"type": "string",
                           "description": "recipient wallet address (0x… for Base/EVM, base58 for Solana)"},
            },
            "required": ["pay_to"],
        },
    },
]


_CLIENT_ID = None


def _client_id():
    """Stable anonymous install id (random UUID, stored locally). Lets Verantis
    count distinct installations; not identifying, not authentication."""
    global _CLIENT_ID
    if _CLIENT_ID:
        return _CLIENT_ID
    path = os.path.join(os.path.expanduser("~"), ".verantis_mcp_id")
    try:
        if os.path.exists(path):
            _CLIENT_ID = open(path).read().strip()
        if not _CLIENT_ID:
            _CLIENT_ID = uuid.uuid4().hex
            with open(path, "w") as f:
                f.write(_CLIENT_ID)
    except Exception:
        _CLIENT_ID = _CLIENT_ID or uuid.uuid4().hex
    return _CLIENT_ID


def _api_get(path, params=None):
    url = f"{API_BASE}{path}"
    if params:
        clean = {k: v for k, v in params.items() if v is not None and v != ""}
        if clean:
            url += "?" + urllib.parse.urlencode(clean)
    req = urllib.request.Request(url, headers={"User-Agent": "verantis-mcp/0.2",
                                                "X-Verantis-Client": _client_id()})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def call_tool(name, args):
    if name == "find_paid_service":
        params = {
            "q": args.get("query"),
            "verified": "true" if args.get("verified_only", True) else "false",
            "max_price": args.get("max_price_usd"),
            "chain": args.get("chain"),
            "protocol": args.get("protocol"),
            "category": args.get("category"),
            "limit": args.get("limit", 10),
            "min_score": args.get("min_score"),
            "proven_only": "true" if args.get("proven_only") else None,
            "_source": "mcp",
        }
        data = _api_get("/v1/entities", params)
        results = data.get("entities", [])
        if not results:
            return {"results": [], "note": (
                "No services matched. If verified_only was true, retrying "
                "with verified_only=false shows unverified listings — "
                "use those at your own risk.")}
        return {"results": results,
                "data_generated_at": data.get("data_generated_at")}
    if name == "get_service":
        try:
            return _api_get(
                f"/v1/entities/{urllib.parse.quote(args['domain'])}",
                {"_source": "mcp"})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"error": "unknown domain", "domain": args.get("domain")}
            raise
    if name == "directory_stats":
        return _api_get("/v1/stats")
    if name == "check_wallet":
        pay_to = (args.get("pay_to") or "").strip()
        if not pay_to:
            return {"error": "pay_to (recipient wallet address) is required"}
        return _api_get("/v1/check", {"pay_to": pay_to, "_source": "mcp"})
    return {"error": f"unknown tool {name}"}


def reply(id_, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": id_}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        method, id_ = req.get("method"), req.get("id")

        if method == "initialize":
            reply(id_, {
                "protocolVersion": req.get("params", {}).get(
                    "protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "verantis",
                               "version": "0.1.3"},
            })
        elif method == "notifications/initialized":
            continue  # notification, no response
        elif method == "tools/list":
            reply(id_, {"tools": TOOLS})
        elif method == "tools/call":
            p = req.get("params", {})
            try:
                result = call_tool(p.get("name"), p.get("arguments") or {})
                reply(id_, {"content": [
                    {"type": "text", "text": json.dumps(result, indent=1)}]})
            except Exception as e:
                reply(id_, {"content": [
                    {"type": "text", "text": json.dumps({"error": str(e)})}],
                    "isError": True})
        elif id_ is not None:
            reply(id_, error={"code": -32601,
                              "message": f"method not found: {method}"})


if __name__ == "__main__":
    main()
