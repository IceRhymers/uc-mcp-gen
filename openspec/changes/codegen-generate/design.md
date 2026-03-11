## Context

The current app bundle is a generic interpreter: it loads `definitions/{name}.yaml` at startup, walks the tool list, and registers handlers dynamically. The deployed app depends on `uc_mcp` (schema.py, engine.py, server.py) and a YAML file that must travel with it. Any schema error in the YAML surfaces at runtime when the server starts, not at generation time.

The codegen model inverts this. `uc-mcp generate` reads the OpenAPI spec once, emits a concrete `main.py` with one `@mcp.tool()` function per operation, and writes a complete DAB. The YAML definition layer disappears from the deployed artifact. Errors (unsupported types, malformed specs) surface during generation, not at startup.

## Goals / Non-Goals

**Goals:**
- Single command: spec + connection name → deployable DAB
- Generated Python is human-readable and self-contained
- Real type signatures on every tool function (derived from OpenAPI types)
- Zero `uc_mcp` imports in generated code
- No YAML at runtime
- Existing commands untouched

**Non-Goals:**
- Replacing `serve`/`validate`/`app` (YAML path stays)
- Full OpenAPI type fidelity (nested objects → `dict`, arrays → `list` — good enough for MCP)
- Response schema validation (not the proxy's job)
- Custom tool support (not in spec → not generated; use `from-openapi` + `app` if needed)

## Decisions

### D1: `python_emitter.py` takes internal tool defs, not raw OpenAPI

`from_openapi.py` already parses OpenAPI operations into a list of intermediate dicts. `python_emitter.py` consumes those same structures. This keeps parsing and emission separate, makes each testable in isolation, and avoids duplicating OpenAPI walking logic.

The internal tool definition shape used by the emitter:
```python
{
    "name": str,            # snake_case function name
    "description": str,
    "method": str,          # GET | POST | PUT | PATCH | DELETE
    "path": str,            # /items/{item_id}
    "path_params": [str],   # names of path placeholder params
    "query_params": [str],  # names of query string params
    "body_params": [        # from requestBody schema properties
        {"name": str, "type": str, "required": bool, "description": str}
    ],
    "all_params": [         # ordered: path → query → body, required first
        {"name": str, "type": str, "required": bool, "description": str}
    ],
}
```

### D2: OpenAPI types map to four Python types

Full OpenAPI type fidelity is not worth the complexity. The mapping:

| OpenAPI type | Python type |
|-------------|-------------|
| `string` | `str` |
| `integer` | `int` |
| `number` | `float` |
| `boolean` | `bool` |
| `array` | `list` |
| `object`, missing, `$ref` | `dict` |

Unknown types default to `dict`. This covers the vast majority of real-world API parameters.

### D3: Required params → positional, optional → keyword with `None` default

Matches normal Python conventions and makes the generated function signatures meaningful:
```python
async def get_item(item_id: str, include_deleted: bool = False) -> str:
```
Path params are always required (positional). Query and body params follow `required` from the OpenAPI spec.

### D4: Path interpolation uses f-strings in generated code

`/items/{item_id}` becomes a Python f-string at the call site:
```python
return _uc_request("GET", f"/items/{item_id}", ...)
```
This is more readable than building paths at runtime with `re.sub`. Path params are consumed from the function arguments and not re-passed in body or query.

### D5: `_uc_request` is inlined in generated main.py, not imported

The generated `main.py` is self-contained. `_uc_request` is a module-level helper emitted at the top of the file. It wraps `WorkspaceClient().serving_endpoints.http_request()` directly, identical in behavior to `UCConnection.request()` but with no `uc_mcp` dependency.

### D6: `generator.py` owns the DAB file tree, `python_emitter.py` owns only source generation

`python_emitter.py` returns a `str` (the full `main.py` source). `generator.py` calls it and writes the file tree:
```
<output>/
├── databricks.yml
├── app.yaml
├── pyproject.toml
└── src/app/
    ├── __init__.py
    └── main.py          ← from python_emitter
```

No `definitions/` directory. No `_schema.yaml`. No engine files.

### D7: `pyproject.toml` in generated DAB has minimal deps

```toml
dependencies = ["mcp>=1.0", "databricks-sdk>=0.30.0", "starlette", "uvicorn"]
```

No `pyyaml`, no `jsonschema`, no `uc_mcp`. The generated app is ~4 packages.

### D8: TDD order follows the module dependency chain

```
test_python_emitter.py  →  codegen/python_emitter.py
test_generator.py       →  codegen/generator.py
test_generate_cli.py    →  __main__.py (generate subcommand)
```

Each layer is fully tested before the next is started.

## Affected Files

```
src/uc_mcp/codegen/python_emitter.py   NEW
src/uc_mcp/codegen/generator.py        NEW
src/uc_mcp/__main__.py                 add generate subcommand
tests/test_python_emitter.py           NEW
tests/test_generator.py                NEW
tests/test_generate_cli.py             NEW
```
