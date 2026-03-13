"""Orchestrate the full OpenAPI spec → Databricks App bundle pipeline.

Single public function: ``generate()``. No YAML definition file is written;
the emitted ``main.py`` is self-contained and has no dependency on ``uc_mcp``.
"""

from __future__ import annotations

import os
import pathlib
import re
import stat
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
            body_params: list[dict] = []
            all_params: list[dict] = []

            # Parameters
            for param in operation.get("parameters", []):
                p_in = param.get("in", "query")
                # Skip header params and token params — auth is handled by the UC connection
                if p_in == "header" or param["name"] == "token":
                    continue

                p_name = param["name"]
                # OAS3: schema.type; Swagger 2.0: type directly on param
                p_schema = param.get("schema", {})
                raw_type = p_schema.get("type") or param.get("type")
                p_type = _map_type(raw_type)
                p_required = bool(param.get("required"))
                p_desc = param.get("description", "")

                bp = {
                    "name": p_name,
                    "type": p_type,
                    "required": p_required,
                    "description": p_desc,
                }

                if p_in == "path":
                    path_params.append(p_name)
                elif p_in == "query":
                    query_params.append(p_name)
                elif p_in == "formData":
                    body_params.append(bp)

                all_params.append(bp)

            # Request body (OAS3 style — appends to any formData entries above)
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


def _render_deploy_sh() -> str:
    return '''\
#!/usr/bin/env bash
# Deploy script for Databricks Asset Bundle.
#
# Usage: bash scripts/deploy.sh [COMMAND]
#
# Commands:
#   validate   Validate the bundle configuration
#   deploy     Deploy the bundle to the workspace
#   start      Start the app compute (skips if already ACTIVE)
#   stop       Stop the app compute
#   app-deploy Deploy the app source code
#   full       deploy → start → app-deploy (default)
#   help       Print this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BUNDLE_ROOT"

# ── Parse arguments ──────────────────────────────────────────────────────

COMMAND="${1:-full}"

# ── Prerequisites ────────────────────────────────────────────────────────

check_prereqs() {
  if ! command -v databricks &>/dev/null; then
    echo "Error: \'databricks\' CLI not found. Install: https://docs.databricks.com/dev-tools/cli/install.html"
    exit 1
  fi
  if ! command -v jq &>/dev/null; then
    echo "Error: \'jq\' not found. Install: https://jqlang.github.io/jq/download/"
    exit 1
  fi
}

# ── Bundle helpers ───────────────────────────────────────────────────────

get_app_name() {
  databricks bundle summary -o json | jq -r \'.resources.apps | to_entries | first | .value.name\'
}

get_workspace_path() {
  databricks bundle summary -o json | jq -r \'.workspace.file_path\'
}

# ── Subcommands ──────────────────────────────────────────────────────────

cmd_validate() {
  echo "==> Validating bundle..."
  databricks bundle validate
  echo "    Bundle is valid."
}

cmd_deploy() {
  echo "==> Deploying bundle..."
  databricks bundle deploy
  echo "    Bundle deployed."
}

cmd_start() {
  local app_name
  app_name="$(get_app_name)"
  echo "==> Starting app \'$app_name\'..."

  local state
  state="$(databricks apps get "$app_name" -o json 2>/dev/null | jq -r \'.compute_status.state // empty\')" || true

  if [[ "$state" == "ACTIVE" ]]; then
    echo "    App is already ACTIVE — skipping start."
    return
  fi

  databricks apps start "$app_name"
  echo "    Start initiated."
}

cmd_stop() {
  local app_name
  app_name="$(get_app_name)"
  echo "==> Stopping app \'$app_name\'..."
  databricks apps stop "$app_name"
  echo "    Stop initiated."
}

cmd_app_deploy() {
  local app_name workspace_path
  app_name="$(get_app_name)"
  workspace_path="$(get_workspace_path)"
  echo "==> Deploying app source for \'$app_name\'..."
  databricks apps deploy "$app_name" --source-code-path "$workspace_path"
  echo "    App deploy initiated."
}

cmd_full() {
  cmd_deploy
  cmd_start
  cmd_app_deploy
}

cmd_help() {
  echo "Usage: bash scripts/deploy.sh [COMMAND]"
  echo ""
  echo "Commands:"
  echo "  validate    Validate the bundle configuration"
  echo "  deploy      Deploy the bundle to the workspace"
  echo "  start       Start the app compute (skips if ACTIVE)"
  echo "  stop        Stop the app compute"
  echo "  app-deploy  Deploy the app source code"
  echo "  full        deploy → start → app-deploy (default)"
  echo "  help        Print this help message"
}

# ── Dispatch ─────────────────────────────────────────────────────────────

check_prereqs

case "$COMMAND" in
  validate)   cmd_validate ;;
  deploy)     cmd_deploy ;;
  start)      cmd_start ;;
  stop)       cmd_stop ;;
  app-deploy) cmd_app_deploy ;;
  full)       cmd_full ;;
  help)       cmd_help ;;
  *)          echo "Unknown command: $COMMAND"; cmd_help; exit 1 ;;
esac
'''


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
    (out / "scripts").mkdir(parents=True, exist_ok=True)

    # Generate main.py
    main_py = emit_module(tools, connection_name, service_name, spec_path)

    # Write files
    (out / "databricks.yml").write_text(_render_databricks_yml(service_name, spec_path))
    (out / "app.yaml").write_text(_render_app_yaml(connection_name))
    (out / "pyproject.toml").write_text(_render_pyproject_toml(service_name))
    (out / "src" / "app" / "__init__.py").write_text("")
    (out / "src" / "app" / "main.py").write_text(main_py)
    deploy_sh = out / "scripts" / "deploy.sh"
    deploy_sh.write_text(_render_deploy_sh())
    deploy_sh.chmod(deploy_sh.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return str(out)
