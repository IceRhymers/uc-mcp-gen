# uc-mcp-server

A data-driven framework for proxying HTTP APIs through [Databricks Unity Catalog connections](https://docs.databricks.com/en/connect/unity-catalog/index.html) as MCP tools. Define your API adapters in YAML — no per-service Python code required.

## How It Works

1. Write a **YAML definition** describing an API's endpoints (method, path, parameters)
2. The framework validates it against a JSON Schema, builds MCP tools dynamically, and proxies HTTP requests through a Databricks UC connection
3. Claude (or any MCP client) can call these tools — auth and routing are handled by UC

## Install

```bash
uv sync
```

## CLI Usage

```bash
# Start an MCP server on stdio
uv run uc-mcp serve definitions/slack.yaml -v

# Validate a YAML definition
uv run uc-mcp validate definitions/slack.yaml

# Generate a definition from an OpenAPI spec
uv run uc-mcp from-openapi <spec-url-or-file> --connection <conn-name> -o definitions/<service>.yaml

# Generate a self-contained Databricks App bundle
uv run uc-mcp app definitions/slack.yaml -o generated_mcp_servers/slack-app
```

## Writing a Definition

Definitions live in `definitions/` and follow the schema at [`definitions/_schema.yaml`](definitions/_schema.yaml).

```yaml
name: my-service
connection: my-uc-connection
tools:
  - name: get_item
    description: Get an item by ID
    method: GET
    path: /items/{item_id}
    input_schema:
      type: object
      properties:
        item_id:
          type: string
          description: The item ID
      required: [item_id]
```

See [`definitions/slack.yaml`](definitions/slack.yaml) for a real-world example.

## Running Tests

```bash
uv run pytest -v
```

## Project Structure

```
src/uc_mcp/           Core framework
├── schema.py         YAML definition validation
├── connection.py     UC connection HTTP proxy
├── engine.py         Dynamic tool registration
├── server.py         MCP server builder
├── __main__.py       CLI entry point
└── codegen/          Code generation tools
    ├── from_openapi.py   OpenAPI → YAML definition
    └── app_generator.py  Generate Databricks App bundle
definitions/          YAML adapter definitions
tests/                pytest test suite
```
