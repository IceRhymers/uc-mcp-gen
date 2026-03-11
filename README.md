# uc-mcp-server

A CLI that compiles an OpenAPI spec directly into a self-contained [Databricks App](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html) bundle — a runnable MCP server with one concrete Python function per API operation. Auth and routing are handled by a [Databricks Unity Catalog connection](https://docs.databricks.com/en/connect/unity-catalog/index.html).

## How It Works

1. Point `uc-mcp generate` at an OpenAPI spec (local file or URL, YAML or JSON)
2. Provide a UC connection name
3. Get a self-contained Databricks App bundle back — ready to deploy with `databricks bundle deploy`

The generated `main.py` has zero dependency on `uc_mcp`. It's a plain FastMCP server where every API operation becomes a typed `async def` tool function, with all HTTP calls proxied through your UC connection.

## Install

```bash
uv sync
```

## Usage

```bash
uc-mcp generate <spec> --connection <conn-name> [--name <service-name>] [-o <output-dir>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `spec` | Path or URL to OpenAPI spec (`.yaml`, `.yml`, `.json`, or remote URL) |
| `--connection` | UC connection name in your Databricks workspace |
| `--name` | Service name (kebab-case). Derived from spec title if omitted. |
| `-o / --output` | Output directory. Defaults to `generated_mcp_servers/<name>-app`. |

**Examples:**

```bash
# From a local YAML spec
uc-mcp generate openapi.yaml --connection my-slack-conn -o ./slack-app

# From a local JSON spec
uc-mcp generate openapi.json --connection my-api-conn

# From a remote spec
uc-mcp generate https://api.example.com/openapi.yaml --connection my-conn -o ./example-app
```

## Generated Bundle

```
<output>/
├── databricks.yml           Databricks Asset Bundle manifest
├── app.yaml                 App startup config — sets UC_CONNECTION_NAME
├── pyproject.toml           App dependencies (mcp, databricks-sdk, starlette, uvicorn)
└── src/app/
    ├── __init__.py
    └── main.py              Self-contained FastMCP server
```

Deploy with:

```bash
cd <output>
databricks bundle deploy
databricks bundle run
```

## Auth

The generated `main.py` handles three auth scenarios automatically:

| Scenario | Mechanism |
|---|---|
| Databricks Apps (user-facing) | `X-Forwarded-Access-Token` header → per-user `WorkspaceClient` |
| Databricks Model Serving | Model Serving credentials context |
| Service principal / local dev | Default `WorkspaceClient()` from environment |

All tool calls are routed through `client.serving_endpoints.http_request(conn=CONNECTION_NAME, ...)` — your UC connection handles the downstream API auth.

## Running Tests

```bash
uv run pytest -v
```
