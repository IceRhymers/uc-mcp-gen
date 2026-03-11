## Why

The current workflow for shipping an API as a Databricks MCP server requires two steps and an intermediate file the user must maintain: `from-openapi` produces a YAML definition, then `app` generates the Databricks App bundle from that YAML. The YAML is an interpreter artifact — it exists because the deployed app reads it at runtime to register tools dynamically. This creates fragility: the YAML can drift from the spec, errors surface at runtime rather than generation time, and users must understand an extra abstraction that adds no value for the common case of "point at an OpenAPI spec and get a working MCP server."

The deeper issue is architectural: the current app bundle is a generic runtime engine (schema.py + engine.py + server.py) that interprets config. A compiler model — where the OpenAPI spec is consumed once at generation time and concrete Python is emitted — eliminates the runtime config layer entirely. The deployed artifact is just Python functions with real type signatures; no `uc_mcp` import, no YAML, no dynamic dispatch.

## What Changes

- Add `uc-mcp generate <spec> --connection <conn> [-o <output>] [--name <name>]` subcommand
- Add `codegen/python_emitter.py` — converts tool definitions into concrete Python source (typed function per tool, `_uc_request` helper, `ForwardedTokenMiddleware`, Starlette/uvicorn app shell)
- Update `codegen/generator.py` (new file) — orchestrates spec → tool defs → Python → DAB file tree
- The generated DAB has no dependency on `uc_mcp`, no YAML at runtime, minimal deps (`mcp`, `databricks-sdk`, `starlette`, `uvicorn`)
- Existing `serve`, `validate`, `from-openapi`, `app` commands are unchanged

## Capabilities

### New Capabilities
- `generate`: Single-command pipeline from OpenAPI spec to self-contained Databricks App bundle. Emits concrete Python with typed tool functions — no runtime YAML, no dynamic dispatch, no `uc_mcp` dependency in deployed code.

### Unchanged Capabilities
- `serve`, `validate`, `from-openapi`, `app`: All existing commands and their behavior are preserved. The YAML-driven interpreter path remains fully functional.

## Impact

| File | Change |
|------|--------|
| `src/uc_mcp/codegen/python_emitter.py` | New — Python source generation from tool definitions |
| `src/uc_mcp/codegen/generator.py` | New — orchestrates full spec → DAB pipeline |
| `src/uc_mcp/__main__.py` | Add `generate` subcommand |
| `tests/test_python_emitter.py` | New — TDD test suite for emitter |
| `tests/test_generator.py` | New — TDD test suite for generator |
| All existing files | No changes |
