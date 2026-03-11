## Context

The YAML interpreter path was the original architecture: a runtime engine that reads a YAML definition file, dynamically registers MCP tools, and handles requests via `UCConnection`. The codegen path replaces this with a compiler model: parse once at generation time, emit concrete Python, deploy self-contained code. Now that the codegen path exists and covers all use cases, the interpreter path is dead weight.

## Goals / Non-Goals

**Goals:**
- Single command (`generate`), single architecture (codegen)
- No runtime dependency on `pyyaml`, `jsonschema`, or `uc_mcp`
- Generated code retains full auth: `ForwardedTokenMiddleware` + UC connection per-request
- All remaining tests pass; deleted test files cover only deleted code
- Package size and dependency footprint reduced

**Non-Goals:**
- Changing the `generate` command behaviour
- Changing the generated DAB structure
- Deprecation warnings or migration helpers (hard cut)

## Decisions

### D1: Inline `_load_openapi_spec` and `_make_tool_name` into `generator.py`

`generator.py` currently imports two private helpers from `from_openapi.py`. Rather than keeping `from_openapi.py` alive for two functions, inline them directly into `generator.py`. They are small (< 20 lines each) and have no other callers once the YAML path is removed. This eliminates the dependency entirely.

### D2: Delete test files wholesale, not test-by-test

The deleted test files (`test_schema.py`, `test_connection.py`, `test_engine.py`, `test_server.py`, `test_from_openapi.py`, `test_app_generator.py`) cover only the deleted modules. There is no partial overlap with the remaining code. File deletion is the correct action — no surgical test removal needed.

### D3: `pyyaml` stays; both JSON and YAML OpenAPI specs are supported

`generator.py` uses `yaml.safe_load()` to load OpenAPI specs. Because JSON is a strict subset of YAML, `yaml.safe_load()` correctly parses both `.json` and `.yaml`/`.yml` files without any branching logic. `pyyaml` must remain in `pyproject.toml`.

This means `uc-mcp generate` accepts:
- `spec.yaml` / `spec.yml` — YAML OpenAPI spec (file)
- `spec.json` — JSON OpenAPI spec (file)
- `https://api.example.com/openapi.yaml` — YAML spec via URL
- `https://api.example.com/openapi.json` — JSON spec via URL

A `tests/fixtures/simple_openapi.json` fixture is added and `test_generator.py` gains a scenario asserting JSON spec input produces identical output to the equivalent YAML spec. `pyyaml` is removed only as a **runtime dependency of generated apps** — the generated `pyproject.toml` already excludes it.

### D4: `jsonschema` is removed entirely

`jsonschema` was only used in `schema.py` for YAML definition validation. With `schema.py` deleted, `jsonschema` has no remaining callers and is removed from `pyproject.toml`.

### D5: Auth in generated code is confirmed unchanged

`python_emitter.py` emits `_ForwardedTokenMiddleware` and `_get_workspace_client()` which together provide:
- Per-user identity via `X-Forwarded-Access-Token` header → `WorkspaceClient(token=..., auth_type="pat")`
- Databricks Model Serving user credentials fallback
- Default `WorkspaceClient()` (app service principal) as final fallback

UC connection auth: all tool calls go through `client.serving_endpoints.http_request(conn=CONNECTION_NAME, ...)`. This is unchanged by this spec.

### D6: `definitions/` directory deleted

`definitions/` contains `slack.yaml` and `_schema.yaml`. Both are YAML interpreter artifacts. The codegen path has no use for them. The `definitions/` pattern in generated DABs (from the old `app_generator.py`) is already absent from `generate` output.

### D7: README rewritten to single-path, not just updated

The existing README still mentions `serve`, `validate`, `from-openapi`, `app` in its implicit mental model even after the command table is updated. A clean rewrite for the codegen-only world is cleaner than surgical edits that may leave residual old-path framing.

## Affected Files

```
DELETE src/uc_mcp/schema.py
DELETE src/uc_mcp/connection.py
DELETE src/uc_mcp/engine.py
DELETE src/uc_mcp/server.py
DELETE src/uc_mcp/codegen/app_generator.py
DELETE src/uc_mcp/codegen/from_openapi.py
DELETE definitions/
DELETE tests/test_schema.py
DELETE tests/test_connection.py
DELETE tests/test_engine.py
DELETE tests/test_server.py
DELETE tests/test_from_openapi.py
DELETE tests/test_app_generator.py
DELETE tests/fixtures/simple_definition.yaml
DELETE tests/fixtures/slack_definition.yaml
DELETE tests/fixtures/invalid_definitions/

MODIFY src/uc_mcp/__main__.py       — keep only `generate` subcommand
MODIFY src/uc_mcp/codegen/generator.py — inline _load_openapi_spec + _make_tool_name
MODIFY pyproject.toml               — remove jsonschema dep
MODIFY CLAUDE.md                    — rewrite for codegen-only
MODIFY README.md                    — rewrite for codegen-only
```
