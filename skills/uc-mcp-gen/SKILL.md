---
name: uc-mcp-gen
description: >
  Generate, deploy, or troubleshoot a Databricks App MCP server from an OpenAPI spec.
  Use this when working with uc-mcp-gen CLI, Unity Catalog connections, Databricks Apps,
  or bundle deployment. Covers the full generate → deploy workflow and key Databricks concepts.
user-invocable: true
allowed-tools: Bash, Read
---

# uc-mcp-gen: Generate MCP Servers for Databricks

## What This Does

`uc-mcp-gen` takes an OpenAPI spec and generates a self-contained Databricks App bundle — a runnable MCP server where every API operation becomes a typed tool that Claude can call. Auth and routing go through a Unity Catalog (UC) connection, so you never expose API keys in your code.

## Key Concepts You Need to Know

### Unity Catalog (UC) Connection

A UC connection is a named credential stored in your Databricks workspace that proxies HTTP requests to an external API. It handles auth to the downstream API (OAuth, API key, etc.) so your generated server never touches secrets directly.

**To create a UC connection:**
1. Go to your Databricks workspace → Catalog Explorer → External Locations & Connections → Connections
2. Click "Create connection" → choose "HTTP"
3. Enter the base URL of the API (e.g. `https://slack.com/api`) and configure auth
4. Give it a name (e.g. `slack`) — this is your `--connection` value

Or via CLI:
```bash
databricks connections create \
  --name slack \
  --connection-type HTTP \
  --options '{"url": "https://slack.com/api", "auth_type": "bearer", "token": "<your-token>"}'
```

### Databricks Apps

A Databricks App is a containerized web application that runs inside your workspace with access to UC connections and workspace identity. The generated MCP server runs as a Databricks App, which means:
- No infrastructure to manage
- Auth handled by the platform
- Users get per-user credentials via `X-Forwarded-Access-Token`

### Databricks Asset Bundles (DABs)

The generated output is a DAB — a folder with a `databricks.yml` manifest that defines your app. You deploy it with the Databricks CLI.

**Install the Databricks CLI:**
```bash
pip install databricks-cli
# or
brew install databricks/tap/databricks
```

**Authenticate:**
```bash
databricks configure
# or set DATABRICKS_HOST and DATABRICKS_TOKEN env vars
```

## Step-by-Step: Generate and Deploy

### 1. Get an OpenAPI Spec

You need a URL or local file path to an OpenAPI 3.x spec (YAML or JSON).

Examples:
- Slack: `https://raw.githubusercontent.com/slackapi/slack-api-specs/master/web-api/slack_web_openapi_v2.json`
- GitHub: `https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.yaml`
- Any public API that publishes an OpenAPI spec

### 2. Create a UC Connection

Make sure your UC connection exists in your workspace (see above). Note the connection name.

### 3. Generate the Bundle

```bash
# Install uc-mcp-gen (recommended: run without installing)
uvx uc-mcp-gen generate <spec-path-or-url> --connection <connection-name>

# Examples:
uvx uc-mcp-gen generate openapi.yaml --connection my-slack-conn -o ./slack-app
uvx uc-mcp-gen generate https://api.example.com/openapi.yaml --connection my-conn
```

Options:
- `spec` — path or URL to OpenAPI spec (required)
- `--connection` — UC connection name (required)
- `--name` — service name in kebab-case (optional, derived from spec title)
- `-o / --output` — output directory (optional, defaults to `generated_mcp_servers/<name>-app`)

### 4. Deploy to Databricks

```bash
cd <output-directory>
databricks bundle deploy
databricks bundle run
```

### 5. Connect Claude to Your MCP Server

Once deployed, Databricks Apps gives you an endpoint URL. Add it to your Claude configuration:

```json
{
  "mcpServers": {
    "my-service": {
      "url": "https://<workspace>.azuredatabricks.net/apps/<app-name>/mcp"
    }
  }
}
```

## Generated File Structure

```
<output>/
├── databricks.yml        # DAB manifest — defines the app
├── app.yaml              # Startup config — sets UC_CONNECTION_NAME
├── pyproject.toml        # Dependencies (mcp, databricks-sdk, starlette, uvicorn)
└── src/app/
    ├── __init__.py
    └── main.py           # Self-contained FastMCP server — no dependency on uc-mcp-gen
```

The generated `main.py` is completely standalone. You can read and modify it directly.

## Auth Scenarios (Handled Automatically)

| Context | How auth works |
|---|---|
| Databricks App (user-facing) | `X-Forwarded-Access-Token` → per-user WorkspaceClient |
| Model Serving | Databricks Model Serving credentials |
| Local dev / service principal | Default WorkspaceClient from environment |

## Troubleshooting

**"No operations found in spec"**
The spec may be OpenAPI 2.x (Swagger). Convert to 3.x first using `swagger2openapi`.

**Bundle deploy fails — permissions**
Make sure your Databricks user has `CAN_MANAGE` on the target app and your UC connection exists.

**Generated tools have wrong types**
Check your OpenAPI spec — `uc-mcp-gen` maps `string → str`, `integer → int`, `number → float`, `boolean → bool`, `array → list`, `object → dict`. Complex `$ref` schemas default to `dict`.

**UC connection auth fails**
Verify the connection in Catalog Explorer. Test it with a direct HTTP request through the Databricks CLI.

## Running Tests (for development)

```bash
uv sync
uv run pytest -v
```
