## 1. `codegen/python_emitter.py` — TDD (test_python_emitter.py first)

- [x] 1.1 Write `test__map_type` — all OpenAPI primitives + None + unknown default to `dict`
- [x] 1.2 Implement `_map_type(openapi_type)` — pass 1.1
- [x] 1.3 Write `test__emit_signature` — required path params first, optional with type-appropriate defaults, return type `-> str`
- [x] 1.4 Implement `_emit_signature(tool)` — pass 1.3
- [x] 1.5 Write `test__emit_path` — plain string when no path params, f-string when path params present, two-placeholder case
- [x] 1.6 Implement `_emit_path(path, path_params)` — pass 1.5
- [x] 1.7 Write `test__emit_request_call` — GET with query params, POST with body, path params excluded from body/query
- [x] 1.8 Implement `_emit_request_call(tool)` — pass 1.7
- [x] 1.9 Write `test__emit_tool_function` — decorator present, docstring present, no docstring when description empty, blank line after
- [x] 1.10 Implement `_emit_tool_function(tool)` — pass 1.9
- [x] 1.11 Write `test_emit_module` — output passes `ast.parse`, empty tools case valid, header present, helper present
- [x] 1.12 Implement `emit_module(tools, connection_name, service_name, spec_source)` — pass 1.11

## 2. `codegen/generator.py` — TDD (test_generator.py first)

- [x] 2.1 Write `test_generate_creates_file_tree` — mock emitter + from_openapi, verify all 6 files written to correct paths
- [x] 2.2 Write `test_generate_service_name_from_title` — no `--name` → slugified from `info.title`
- [x] 2.3 Write `test_generate_default_output_dir` — no `-o` → `generated_mcp_servers/<name>-app`
- [x] 2.4 Write `test_generate_pyproject_no_uc_mcp` — `pyproject.toml` content has no `uc_mcp`, `pyyaml`, `jsonschema`
- [x] 2.5 Write `test_generate_idempotent` — two calls with same args produce identical file contents
- [x] 2.6 Write `test_generate_missing_spec` — raises appropriate error
- [x] 2.7 Write `test_generate_no_operations` — raises appropriate error
- [x] 2.8 Implement `generate(spec_path, connection_name, service_name, output_dir)` — pass 2.1–2.7
- [x] 2.9 Write `test_generate_main_py_is_valid_python` — generated `main.py` passes `ast.parse` (integration, uses fixture spec)

## 3. `__main__.py` — add `generate` subcommand

- [x] 3.1 Write `test_generate_cli_missing_connection` — argparse error when `--connection` absent
- [x] 3.2 Write `test_generate_cli_calls_generator` — mock `generator.generate`, verify called with correct args
- [x] 3.3 Write `test_generate_cli_prints_output_path` — stdout contains "Generated: <path>" on success
- [x] 3.4 Write `test_generate_cli_exits_1_on_error` — generator raises → exit code 1, stderr message
- [x] 3.5 Add `generate` subparser to `__main__.py` with `spec`, `--connection`, `--name`, `-o` args — pass 3.1–3.4

## 4. Final verification

- [x] 4.1 Run full test suite — zero regressions on existing tests
- [x] 4.2 Manual smoke test: `uc-mcp generate` against a real/fixture OpenAPI spec, inspect generated files
- [x] 4.3 Verify generated `main.py` passes `ast.parse` end-to-end
- [x] 4.4 Verify generated `pyproject.toml` has no `uc_mcp`, `pyyaml`, or `jsonschema`
- [x] 4.5 Commit on `feat/codegen-generate`
