"""Orchestrate the full OpenAPI spec → Databricks App bundle pipeline.

Single public function: ``generate()``. No YAML definition file is written;
the emitted ``main.py`` is self-contained and has no dependency on ``uc_mcp``.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

from uc_mcp_gen.codegen.python_emitter import _map_type, emit_module


# ── Internal helpers ──────────────────────────────────────────────────────


def _load_openapi_spec(spec_path: str) -> dict[str, Any]:
    """Load an OpenAPI spec from a YAML/JSON file or URL.

    Uses yaml.safe_load which handles both YAML and JSON (JSON is valid YAML).
    """
    import yaml

    if spec_path.startswith("http://") or spec_path.startswith("https://"):
        import urllib.request
        with urllib.request.urlopen(spec_path) as resp:
            return yaml.safe_load(resp.read())
    else:
        with open(spec_path) as f:
            return yaml.safe_load(f)


def _make_tool_name(operation_id: str | None, method: str, path: str) -> str:
    """Generate a snake_case tool name from operation ID or method+path."""
    if operation_id:
        name = operation_id.lower()
        name = re.sub(r"[^a-z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name).strip("_")
        return name
    segments = [s for s in path.strip("/").split("/") if s]
    cleaned = [re.sub(r"[{}]", "", seg) for seg in segments]
    return f"{method.lower()}_{'_'.join(cleaned)}"


def _slugify(title: str) -> str:
    """Convert a spec title to a kebab-case service name."""
    name = title.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")
    return name


def _default_output_dir(service_name: str) -> pathlib.Path:
    return pathlib.Path("generated_mcp_servers") / f"{service_name}-app"


def _extract_tools(spec: dict[str, Any]) -> list[dict]:
    """Convert OpenAPI paths into internal tool definition dicts.

    Each tool dict has Python type strings (already mapped via _map_type).
    """
    tools: list[dict] = []

    for path, path_item in spec.get("paths", {}).items():
        for http_method in ("get", "post", "put", "patch", "delete"):
            if http_method not in path_item:
                continue
            operation = path_item[http_method]
            op_id = operation.get("operationId")
            tool_name = _make_tool_name(op_id, http_method, path)
            description = operation.get("summary") or operation.get("description") or ""

            path_params: list[str] = []
            query_params: list[str] = []
            all_params: list[dict] = []

            # Parameters
            for param in operation.get("parameters", []):
                p_name = param["name"]
                p_schema = param.get("schema", {})
                p_type = _map_type(p_schema.get("type"))
                p_required = bool(param.get("required"))
                p_desc = param.get("description", "")
                p_in = param.get("in", "query")

                if p_in == "path":
                    path_params.append(p_name)
                elif p_in == "query":
                    query_params.append(p_name)

                all_params.append({
                    "name": p_name,
                    "type": p_type,
                    "required": p_required,
                    "description": p_desc,
                })

            # Request body
            body_params: list[dict] = []
            request_body = operation.get("requestBody", {})
            content = request_body.get("content", {})
            json_content = content.get("application/json", {})
            body_schema = json_content.get("schema", {})
            body_required = set(body_schema.get("required", []))

            for b_name, b_schema in body_schema.get("properties", {}).items():
                b_type = _map_type(b_schema.get("type"))
                bp = {
                    "name": b_name,
                    "type": b_type,
                    "required": b_name in body_required,
                    "description": b_schema.get("description", ""),
                }
                body_params.append(bp)
                all_params.append(bp)

            # Sort all_params: required first
            all_params.sort(key=lambda p: (0 if p["required"] else 1))

            tools.append({
                "name": tool_name,
                "description": description,
                "method": http_method.upper(),
                "path": path,
                "path_params": path_params,
                "query_params": query_params,
                "body_params": body_params,
                "all_params": all_params,
            })

    return tools


def _render_databricks_yml(service_name: str, spec_source: str) -> str:
    return f"""\
bundle:
  name: {service_name}

resources:
  apps:
    {service_name.replace('-', '_')}:
      name: {service_name}
      description: MCP server generated from {spec_source}
      source_code_path: .
"""


def _render_app_yaml(connection_name: str) -> str:
    return f"""\
command:
  - uv
  - run
  - python
  - -m
  - app.main

env:
  - name: UC_CONNECTION_NAME
    value: {connection_name}
"""


def _render_pyproject_toml(service_name: str) -> str:
    return f"""\
[project]
name = "{service_name}"
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
"""


# ── Public API ────────────────────────────────────────────────────────────


def generate(
    spec_path: str,
    connection_name: str,
    service_name: str | None = None,
    output_dir: str | None = None,
) -> str:
    """Generate a self-contained Databricks App bundle from an OpenAPI spec.

    Args:
        spec_path: Path or URL to OpenAPI spec (JSON or YAML).
        connection_name: UC connection name in the Databricks workspace.
        service_name: Service name (kebab-case). Derived from spec title if omitted.
        output_dir: Output directory path. Defaults to
            ``generated_mcp_servers/<service-name>-app``.

    Returns:
        The output directory path as a string.

    Raises:
        FileNotFoundError: If the spec file is not found.
        ValueError: If the spec has no operations.
    """
    # Load spec
    try:
        spec = _load_openapi_spec(spec_path)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not parse spec: {exc}") from exc

    # Extract tools
    tools = _extract_tools(spec)
    if not tools:
        raise ValueError(f"No operations found in spec: {spec_path}")

    # Derive service name
    if not service_name:
        title = spec.get("info", {}).get("title", connection_name)
        service_name = _slugify(title)

    # Derive output dir
    out = pathlib.Path(output_dir) if output_dir else _default_output_dir(service_name)

    # Create directory tree
    (out / "src" / "app").mkdir(parents=True, exist_ok=True)

    # Generate main.py
    main_py = emit_module(tools, connection_name, service_name, spec_path)

    # Write files
    (out / "databricks.yml").write_text(_render_databricks_yml(service_name, spec_path))
    (out / "app.yaml").write_text(_render_app_yaml(connection_name))
    (out / "pyproject.toml").write_text(_render_pyproject_toml(service_name))
    (out / "src" / "app" / "__init__.py").write_text("")
    (out / "src" / "app" / "main.py").write_text(main_py)

    return str(out)
