## Why

`uc-mcp-server` currently ships two complete paths for creating Databricks MCP servers: the original YAML interpreter path (`from-openapi` → YAML → `app` → runtime engine) and the new codegen path (`generate` → concrete Python DAB). Maintaining both creates confusion about which approach to use, doubles the surface area to maintain, and keeps a runtime dependency on `pyyaml` and `jsonschema` that serve no purpose once the codegen path is the only supported route.

The codegen path is strictly better: the OpenAPI spec is the source of truth, the generated DAB is self-contained Python, errors surface at generation time instead of server startup, and the deployed artifact has no dependency on `uc_mcp` at all. There is no scenario where a user should prefer the interpreter path for new work.

## What Changes

- Delete the five runtime modules: `schema.py`, `connection.py`, `engine.py`, `server.py`, `codegen/app_generator.py`
- Inline the two helpers `generator.py` borrows from `from_openapi.py` (`_load_openapi_spec`, `_make_tool_name`) directly into `generator.py`, then delete `codegen/from_openapi.py`
- Remove the `serve`, `validate`, `from-openapi`, `app`, and `build` subcommands from `__main__.py`; `generate` is the only remaining command
- Remove `pyyaml` and `jsonschema` from `pyproject.toml` runtime dependencies
- Delete the `definitions/` directory and all YAML fixtures
- Delete the test files that covered the deleted modules
- Update `CLAUDE.md` and `README.md` to reflect the single-path architecture
- Confirm generated code retains `ForwardedTokenMiddleware` (X-Forwarded-Access-Token) and UC connection auth — these are unchanged

## Capabilities

### Removed Capabilities
- `serve`: YAML-driven local stdio MCP server
- `validate`: YAML definition schema validation
- `from-openapi`: OpenAPI spec → YAML definition file
- `app`: YAML definition → Databricks App bundle (interpreter model)
- `build`: PEX/SCIE packaging of YAML-driven server

### Unchanged Capabilities
- `generate`: OpenAPI spec → self-contained Databricks App bundle (concrete Python, no YAML)

## Impact

| File | Action |
|------|--------|
| `src/uc_mcp/schema.py` | Delete |
| `src/uc_mcp/connection.py` | Delete |
| `src/uc_mcp/engine.py` | Delete |
| `src/uc_mcp/server.py` | Delete |
| `src/uc_mcp/codegen/app_generator.py` | Delete |
| `src/uc_mcp/codegen/from_openapi.py` | Delete (helpers inlined into generator.py) |
| `src/uc_mcp/__main__.py` | Remove all commands except `generate` |
| `src/uc_mcp/codegen/generator.py` | Inline `_load_openapi_spec` + `_make_tool_name` |
| `pyproject.toml` | Remove `pyyaml`, `jsonschema` from dependencies |
| `definitions/` | Delete entire directory |
| `tests/test_schema.py` | Delete |
| `tests/test_connection.py` | Delete |
| `tests/test_engine.py` | Delete |
| `tests/test_server.py` | Delete |
| `tests/test_from_openapi.py` | Delete |
| `tests/test_app_generator.py` | Delete |
| `tests/fixtures/simple_definition.yaml` | Delete |
| `tests/fixtures/slack_definition.yaml` | Delete |
| `tests/fixtures/invalid_definitions/` | Delete |
| `CLAUDE.md` | Rewrite for single-path architecture |
| `README.md` | Rewrite for single-path architecture |
