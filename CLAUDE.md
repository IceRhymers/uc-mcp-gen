# UC MCP Server

Data-driven framework that proxies HTTP APIs through Databricks UC connections. YAML definitions are the adapters — no per-service Python code.

## Structure

```
src/uc_mcp/
├── __main__.py              CLI (serve, validate, from-openapi, build, app)
├── schema.py                YAML definition validation (jsonschema + dataclasses)
├── connection.py            UCConnection wrapping w.serving_endpoints.http_request()
├── engine.py                Dynamic tool registration: YAML → MCP tools
├── server.py                Assembles MCP Server from definition + connection
├── _schema.yaml             JSON Schema governing all definitions
└── codegen/
    ├── app_generator.py     Generate self-contained Databricks App bundle
    └── from_openapi.py      OpenAPI spec → YAML definition
definitions/                 YAML adapter definitions (the "code" for each service)
├── _schema.yaml             JSON Schema for definitions
└── slack.yaml               Slack tools
tests/                       pytest test suite
├── conftest.py              Shared fixtures (mock WorkspaceClient, paths)
├── test_schema.py           Schema validation
├── test_connection.py       UCConnection with mocked Databricks SDK
├── test_engine.py           Dynamic tool registration + handler execution
├── test_server.py           Integration: YAML → running MCP server
├── test_from_openapi.py     OpenAPI → YAML conversion
├── test_app_generator.py    App bundle generation
└── fixtures/                Test YAML definitions
```

## Module Dependency Chain

Changes flow downward. Always start tests at the lowest affected layer.

```
schema.py          ← Foundation: dataclasses + validation
    ↓
connection.py      ← Transport: UCConnection wraps Databricks SDK
    ↓
engine.py          ← Core: dynamic tool registration from parsed YAML
    ↓
server.py          ← Assembly: wires engine + connection into MCP Server
    ↓
__main__.py        ← CLI: subcommands calling the above
    ↓
codegen/*.py       ← Generation: OpenAPI spec → YAML definitions, app bundles
```

## Key Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest -v

# Run one test file
uv run pytest tests/test_engine.py -v

# Run one test by name
uv run pytest -k "test_build_path_simple" -v

# Run with coverage
uv run pytest --cov=uc_mcp --cov-report=term-missing

# Validate a definition
uv run uc-mcp validate definitions/slack.yaml

# Serve (manual testing against a real Databricks workspace)
uv run uc-mcp serve definitions/slack.yaml -v

# Generate from OpenAPI spec
uv run uc-mcp from-openapi spec.json --connection conn-name -o output.yaml

# Generate Databricks App bundle
uv run uc-mcp app definitions/slack.yaml -o generated_mcp_servers/slack-app
```

## Adding a New Service

1. Create `definitions/<service>.yaml` following `definitions/_schema.yaml`
2. Validate: `uv run uc-mcp validate definitions/<service>.yaml`
3. Add test fixtures and TDD cycle (see below)

## TDD Workflow

All changes follow RED → GREEN → REFACTOR. Use `/uc-mcp-tdd` skill for guided TDD.

| Change Area | Test File | Source File |
|------------|-----------|-------------|
| YAML schema, dataclasses, validation | `test_schema.py` | `schema.py` |
| HTTP transport, request/response | `test_connection.py` | `connection.py` |
| Tool registration, path building, response formatting | `test_engine.py` | `engine.py` |
| MCP server assembly, end-to-end | `test_server.py` | `server.py` |
| OpenAPI conversion | `test_from_openapi.py` | `codegen/from_openapi.py` |
| App bundle generation | `test_app_generator.py` | `codegen/app_generator.py` |
