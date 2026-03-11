# Spec: generate-command

## Purpose

`uc-mcp generate` is a single CLI command that takes an OpenAPI spec and a UC connection name and writes a complete, self-contained Databricks App bundle to an output directory. No intermediate YAML. No `uc_mcp` dependency in the generated artifact.

---

## CLI Interface

```
uc-mcp generate <spec> --connection <name> [--name <service>] [-o <output>]
```

| Argument | Required | Description |
|----------|----------|-------------|
| `spec` | yes | Path or URL to OpenAPI spec (JSON or YAML) |
| `--connection` | yes | UC connection name in the Databricks workspace |
| `--name` | no | Service name (kebab-case). Defaults to spec `info.title` slugified |
| `-o / --output` | no | Output directory. Defaults to `generated_mcp_servers/<name>-app` |

Exit codes: `0` on success, `1` on any error (spec not found, unparseable, no operations).

---

## Requirements

### R1: `generator.py` orchestration

`codegen/generator.py` exposes:

```python
def generate(
    spec_path: str,
    connection_name: str,
    service_name: str | None = None,
    output_dir: str | None = None,
) -> pathlib.Path:
    """Generate DAB. Returns the output directory path."""
```

Steps (in order):
1. Load and parse OpenAPI spec via `from_openapi.py` loader
2. Extract tool definitions via `from_openapi.py` converter
3. Derive `service_name` from `spec.info.title` if not provided (lowercase, spaces → `-`, non-alphanumeric stripped)
4. Derive `output_dir` from service name if not provided
5. Call `python_emitter.emit_module(tools, connection_name, service_name, spec_path)` → `main_py_source`
6. Write DAB file tree (see R2)
7. Return resolved output path

### R2: Generated DAB file tree

```
<output_dir>/
├── databricks.yml
├── app.yaml
├── pyproject.toml
└── src/
    └── app/
        ├── __init__.py
        └── main.py
```

No `definitions/` directory. No `scripts/` directory. No `_schema.yaml`.

### R3: `databricks.yml` content

```yaml
bundle:
  name: <service-name>

resources:
  apps:
    <service-name>:
      name: <service-name>
      description: MCP server generated from <spec_source>
      source_code_path: .
```

### R4: `app.yaml` content

```yaml
command:
  - uv
  - run
  - python
  - -m
  - app.main

env:
  - name: UC_CONNECTION_NAME
    value: <connection_name>
```

### R5: `pyproject.toml` content

```toml
[project]
name = "<service-name>"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0",
    "databricks-sdk>=0.30.0",
    "starlette",
    "uvicorn",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/app"]
```

No `pyyaml`, no `jsonschema`, no `uc_mcp`.

### R6: `src/app/__init__.py`

Empty file.

### R7: `src/app/main.py`

Content from `python_emitter.emit_module(...)`. Must be written as UTF-8.

### R8: Output directory creation

`generator.py` creates `<output_dir>/src/app/` (and all intermediate dirs) before writing files. If the output directory already exists, files are overwritten without error.

### R9: `__main__.py` `generate` subcommand

Added to the existing `argparse` subparser alongside `serve`, `validate`, `from-openapi`, `app`:

```python
gen_parser = subparsers.add_parser("generate", help="Generate a Databricks App bundle from an OpenAPI spec")
gen_parser.add_argument("spec", help="Path or URL to OpenAPI spec")
gen_parser.add_argument("--connection", required=True, help="UC connection name")
gen_parser.add_argument("--name", default=None, help="Service name (default: derived from spec title)")
gen_parser.add_argument("-o", "--output", default=None, help="Output directory")
```

On success, prints: `Generated: <output_dir>`
On error, prints error message to stderr and exits 1.

### R10: Error cases

| Condition | Behaviour |
|-----------|-----------|
| Spec file not found | Exit 1, message: `Error: spec file not found: <path>` |
| Spec URL fetch fails | Exit 1, message: `Error: failed to fetch spec: <url>` |
| Spec is not valid JSON/YAML | Exit 1, message: `Error: could not parse spec` |
| Spec has no operations | Exit 1, message: `Error: no operations found in spec` |
| `--connection` not provided | argparse error (standard) |

### R11: Idempotency

Running `generate` twice with the same arguments produces identical output. No timestamps or non-deterministic content in generated files (except the spec source path, which is the input).

---

## Scenarios

| # | Input | Expected |
|---|-------|----------|
| S1 | Valid spec file, all flags | DAB written to specified output dir |
| S2 | Valid spec URL, all flags | DAB written (spec loaded over HTTP) |
| S3 | No `--name` | service name derived from `info.title` |
| S4 | No `-o` | output at `generated_mcp_servers/<name>-app` |
| S5 | Missing spec file | exit 1, error message |
| S6 | Spec with 0 operations | exit 1, error message |
| S7 | Run twice, same args | identical files both times |
| S8 | Existing output dir | files overwritten, no error |
| S9 | Generated `main.py` | passes `ast.parse` |
| S10 | Generated `pyproject.toml` | no `uc_mcp`, `pyyaml`, or `jsonschema` in deps |
