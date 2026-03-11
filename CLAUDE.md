# UC MCP Server

CLI tool that compiles an OpenAPI spec into a self-contained Databricks App bundle — a runnable MCP server with one concrete Python function per API operation. No intermediate YAML, no runtime dependency on `uc_mcp`.

## Structure

```
src/uc_mcp/
├── __main__.py              CLI (generate subcommand only)
└── codegen/
    ├── generator.py         OpenAPI spec → Databricks App bundle (DAB) orchestrator
    └── python_emitter.py    Internal tool defs → main.py source string
tests/
├── test_python_emitter.py   41 tests for python_emitter.py
├── test_generator.py        22 tests for generator.py
├── test_generate_cli.py     9 tests for __main__.py
└── fixtures/
    ├── simple_openapi.yaml  YAML OpenAPI fixture (3 operations)
    └── simple_openapi.json  JSON OpenAPI fixture (same spec)
```

## Module Dependency Chain

```
python_emitter.py   ← Foundation: type mapping + code emission
    ↓
generator.py        ← Orchestration: spec loading, tool extraction, file writing
    ↓
__main__.py         ← CLI: generate subcommand calling generator.generate()
```

## Key Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest -v

# Run one test file
uv run pytest tests/test_generator.py -v

# Run one test by name
uv run pytest -k "test_json_spec" -v

# Run with coverage
uv run pytest --cov=uc_mcp --cov-report=term-missing

# Generate a Databricks App bundle from an OpenAPI spec
uv run uc-mcp generate spec.yaml --connection my-uc-conn -o ./my-app
uv run uc-mcp generate https://api.example.com/openapi.json --connection my-uc-conn
```

## Generated Bundle Structure

```
<output>/
├── databricks.yml           Databricks Asset Bundle manifest
├── app.yaml                 Databricks App config (sets UC_CONNECTION_NAME env var)
├── pyproject.toml           App project (mcp, databricks-sdk, starlette, uvicorn)
└── src/app/
    ├── __init__.py
    └── main.py              Self-contained FastMCP server — no uc_mcp dependency
```

## TDD Workflow

All changes follow RED → GREEN → REFACTOR.

| Change Area | Test File | Source File |
|---|---|---|
| Type mapping, code emission, signatures | `test_python_emitter.py` | `codegen/python_emitter.py` |
| Spec loading, tool extraction, file tree | `test_generator.py` | `codegen/generator.py` |
| CLI subcommand, argument parsing | `test_generate_cli.py` | `__main__.py` |

## Adding Support for a New OpenAPI Feature

1. Add a failing test in the appropriate test file (RED)
2. Implement minimum change in `python_emitter.py` or `generator.py` (GREEN)
3. Run `uv run pytest -v` — all tests must pass
4. Refactor if needed, keeping tests green

## Auth in Generated Code

The emitted `main.py` includes:

- `_ForwardedTokenMiddleware` — extracts `X-Forwarded-Access-Token` header, stores in context var
- `_get_workspace_client()` — returns per-user `WorkspaceClient(token=..., auth_type="pat")` when token present, Databricks Model Serving credentials as fallback, default `WorkspaceClient()` as final fallback
- All tool calls routed through `client.serving_endpoints.http_request(conn=CONNECTION_NAME, ...)`

`CONNECTION_NAME` is set at generation time from `--connection` and injected into the app via `UC_CONNECTION_NAME` environment variable (configured in `app.yaml`).
