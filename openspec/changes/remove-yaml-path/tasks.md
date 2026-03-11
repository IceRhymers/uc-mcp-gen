## 1. Delete runtime modules and their tests

- [ ] 1.1 Delete `src/uc_mcp/schema.py`
- [ ] 1.2 Delete `src/uc_mcp/connection.py`
- [ ] 1.3 Delete `src/uc_mcp/engine.py`
- [ ] 1.4 Delete `src/uc_mcp/server.py`
- [ ] 1.5 Delete `src/uc_mcp/codegen/app_generator.py`
- [ ] 1.6 Delete `tests/test_schema.py`
- [ ] 1.7 Delete `tests/test_connection.py`
- [ ] 1.8 Delete `tests/test_engine.py`
- [ ] 1.9 Delete `tests/test_server.py`
- [ ] 1.10 Delete `tests/test_app_generator.py`

## 2. Inline helpers and delete `from_openapi.py`

- [ ] 2.1 Copy `_load_openapi_spec` and `_make_tool_name` implementations into `generator.py`
- [ ] 2.2 Remove the `from uc_mcp.codegen.from_openapi import ...` line from `generator.py`
- [ ] 2.3 Delete `src/uc_mcp/codegen/from_openapi.py`
- [ ] 2.4 Delete `tests/test_from_openapi.py`

## 3. Clean up `__main__.py`

- [ ] 3.1 Remove `serve` subparser and handler block
- [ ] 3.2 Remove `validate` subparser and handler block
- [ ] 3.3 Remove `from-openapi` subparser and handler block
- [ ] 3.4 Remove `app` subparser and handler block
- [ ] 3.5 Remove `build` subparser and handler block
- [ ] 3.6 Verify `uc-mcp --help` shows only `generate`

## 4. Remove unused dependencies and fixtures

- [ ] 4.1 Remove `jsonschema>=4.0` from `pyproject.toml` dependencies (keep `pyyaml`)
- [ ] 4.2 Delete `definitions/` directory
- [ ] 4.3 Delete `tests/fixtures/simple_definition.yaml`
- [ ] 4.4 Delete `tests/fixtures/slack_definition.yaml`
- [ ] 4.5 Delete `tests/fixtures/invalid_definitions/`
- [ ] 4.6 Add `tests/fixtures/simple_openapi.json` — JSON equivalent of `simple_openapi.yaml`
- [ ] 4.7 Add test to `test_generator.py`: `generate()` with JSON fixture produces valid DAB with same tool functions

## 5. Update docs

- [ ] 5.1 Rewrite `CLAUDE.md` — module map, commands, TDD table for codegen-only
- [ ] 5.2 Rewrite `README.md` — single-path workflow, no YAML commands

## 6. Final verification

- [ ] 6.1 Run `uv run pytest -v` — 69 tests, 0 failures
- [ ] 6.2 Confirm `src/uc_mcp/` contains only `__init__.py`, `__main__.py`, `codegen/`
- [ ] 6.3 Confirm `src/uc_mcp/codegen/` contains only `__init__.py`, `generator.py`, `python_emitter.py`
- [ ] 6.4 Confirm `pyproject.toml` has no `jsonschema`
- [ ] 6.5 Commit on `feat/codegen-generate`
