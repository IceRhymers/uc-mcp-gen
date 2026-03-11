# Spec: remove-yaml-path

## Purpose

Remove all YAML interpreter path code and tests. Leave `uc-mcp generate` as the sole command and `codegen/generator.py` + `codegen/python_emitter.py` as the only source modules (plus the inlined helpers from `from_openapi.py`).

---

## Requirements

### R1: Deleted source modules

The following files must not exist after this change:

- `src/uc_mcp/schema.py`
- `src/uc_mcp/connection.py`
- `src/uc_mcp/engine.py`
- `src/uc_mcp/server.py`
- `src/uc_mcp/codegen/app_generator.py`
- `src/uc_mcp/codegen/from_openapi.py`

### R2: Deleted test files

The following files must not exist after this change:

- `tests/test_schema.py`
- `tests/test_connection.py`
- `tests/test_engine.py`
- `tests/test_server.py`
- `tests/test_from_openapi.py`
- `tests/test_app_generator.py`

### R3: Deleted fixtures

The following must not exist after this change:

- `tests/fixtures/simple_definition.yaml`
- `tests/fixtures/slack_definition.yaml`
- `tests/fixtures/invalid_definitions/` (entire directory)
- `definitions/` (entire directory at repo root)

### R4: `__main__.py` — `generate` only

`__main__.py` retains only the `generate` subcommand. The `serve`, `validate`, `from-openapi`, `app`, and `build` subparser registrations and their handler blocks are removed. Running `uc-mcp --help` lists only `generate`.

### R5: `generator.py` — inlined helpers

`generator.py` no longer imports from `from_openapi.py`. The two helpers are inlined:

- `_load_openapi_spec(spec_path: str) -> dict` — load YAML or JSON from file path or HTTP URL
- `_make_tool_name(operation_id: str | None, method: str, path: str) -> str` — derive snake_case tool name

Behaviour is identical to the original implementations.

### R6: `pyproject.toml` — remove `jsonschema`, keep `pyyaml`

`jsonschema` is removed from the `dependencies` list. `pyyaml` remains — `generator.py` uses `yaml.safe_load()` which handles both JSON and YAML OpenAPI specs (JSON is valid YAML). `mcp`, `databricks-sdk` remain unchanged.

### R6a: Both JSON and YAML OpenAPI spec files are accepted

`_load_openapi_spec()` in `generator.py` accepts:
- Local YAML files (`.yaml`, `.yml`)
- Local JSON files (`.json`)
- Remote YAML or JSON URLs

A `tests/fixtures/simple_openapi.json` fixture is added containing the same spec as `simple_openapi.yaml`. `test_generator.py` includes a test asserting that `generate()` called with the JSON fixture produces a valid DAB with the same tool functions as the YAML fixture.

### R7: All remaining tests pass

After deletions and modifications, `uv run pytest -v` completes with zero failures. The surviving test files are:

- `tests/test_python_emitter.py` (41 tests)
- `tests/test_generator.py` (19 tests)
- `tests/test_generate_cli.py` (9 tests)

Total: 69 tests, all passing.

### R8: Generated code auth unchanged

`python_emitter.py` is not modified. The emitted `main.py` continues to include:

- `_ForwardedTokenMiddleware` — extracts `X-Forwarded-Access-Token` and stores in context var
- `_get_workspace_client()` — returns per-user `WorkspaceClient` when token present, ModelServing credentials in model serving env, default `WorkspaceClient` otherwise
- All tool calls routed through `client.serving_endpoints.http_request(conn=CONNECTION_NAME, ...)`

### R9: `CLAUDE.md` reflects single-path architecture

Updated module map, key commands, and TDD table reflect only the remaining files. No references to `schema.py`, `connection.py`, `engine.py`, `server.py`, `serve`, `validate`, `from-openapi`, `app`, `build`.

### R10: `README.md` reflects single-path architecture

Rewritten. The only workflow documented is:

```bash
uc-mcp generate <spec> --connection <conn> [-o <output>] [--name <name>]
```

Installation, how-it-works, and auth sections updated accordingly. No references to the old commands or YAML definitions.

---

## Scenarios

| # | Assertion | Expected |
|---|-----------|----------|
| S1 | `ls src/uc_mcp/` | Only `__init__.py`, `__main__.py`, `codegen/` |
| S2 | `ls src/uc_mcp/codegen/` | Only `__init__.py`, `generator.py`, `python_emitter.py` |
| S3 | `uc-mcp --help` | Only `generate` listed |
| S4 | `uc-mcp serve ...` | Command not found error |
| S5 | `uv run pytest -v` | 70 passed, 0 failed |
| S6 | `cat pyproject.toml` | No `jsonschema`; `pyyaml` present |
| S7 | Generated `main.py` | Contains `_ForwardedTokenMiddleware` and `CONNECTION_NAME` |
| S8 | `ls definitions/` | Directory does not exist |
| S9 | `import uc_mcp.schema` | ImportError |
| S10 | `import uc_mcp.codegen.from_openapi` | ImportError |
| S11 | `generate(simple_openapi.json, ...)` | Valid DAB, same tool functions as YAML input |
| S12 | `generate(https://.../openapi.json, ...)` | URL JSON spec loads and generates correctly |
