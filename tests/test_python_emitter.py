"""TDD tests for codegen/python_emitter.py — RED phase first."""

from __future__ import annotations

import ast

import pytest

from uc_mcp_gen.codegen.python_emitter import (
    _emit_header,
    _emit_path,
    _emit_request_call,
    _emit_signature,
    _emit_tool_function,
    _emit_uc_request_helper,
    _map_type,
    emit_module,
)


# ── Fixtures ──────────────────────────────────────────────────────────────


def _tool(
    name="list_items",
    description="List all items.",
    method="GET",
    path="/items",
    path_params=None,
    query_params=None,
    body_params=None,
    all_params=None,
):
    """Build a minimal internal tool definition dict."""
    if all_params is None:
        all_params = []
        for p in (path_params or []):
            all_params.append({"name": p, "type": "str", "required": True, "description": ""})
        for p in (query_params or []):
            all_params.append({"name": p, "type": "int", "required": False, "description": ""})
        for bp in (body_params or []):
            all_params.append(bp)
    return {
        "name": name,
        "description": description,
        "method": method,
        "path": path,
        "path_params": path_params or [],
        "query_params": query_params or [],
        "body_params": body_params or [],
        "all_params": all_params,
    }


# ── TestMapType ───────────────────────────────────────────────────────────


class TestMapType:
    def test_string(self):
        assert _map_type("string") == "str"

    def test_integer(self):
        assert _map_type("integer") == "int"

    def test_number(self):
        assert _map_type("number") == "float"

    def test_boolean(self):
        assert _map_type("boolean") == "bool"

    def test_array(self):
        assert _map_type("array") == "list"

    def test_object(self):
        assert _map_type("object") == "dict"

    def test_none_defaults_to_dict(self):
        assert _map_type(None) == "dict"

    def test_unknown_defaults_to_dict(self):
        assert _map_type("future_type") == "dict"


# ── TestEmitSignature ─────────────────────────────────────────────────────


class TestEmitSignature:
    def test_no_params(self):
        t = _tool()
        sig = _emit_signature(t)
        assert sig == "async def list_items() -> str:"

    def test_required_path_param(self):
        t = _tool(path_params=["item_id"], all_params=[
            {"name": "item_id", "type": "str", "required": True, "description": ""},
        ])
        sig = _emit_signature(t)
        assert "item_id: str" in sig
        assert "= " not in sig.split("item_id: str")[1].split(",")[0].split(")")[0]

    def test_optional_query_param_bool_default(self):
        t = _tool(all_params=[
            {"name": "include_deleted", "type": "bool", "required": False, "description": ""},
        ])
        sig = _emit_signature(t)
        assert "include_deleted: bool = False" in sig

    def test_optional_query_param_int_default(self):
        t = _tool(all_params=[
            {"name": "limit", "type": "int", "required": False, "description": ""},
        ])
        sig = _emit_signature(t)
        assert "limit: int = 0" in sig

    def test_optional_query_param_float_default(self):
        t = _tool(all_params=[
            {"name": "price", "type": "float", "required": False, "description": ""},
        ])
        sig = _emit_signature(t)
        assert "price: float = 0" in sig

    def test_optional_str_param_none_default(self):
        t = _tool(all_params=[
            {"name": "filter", "type": "str", "required": False, "description": ""},
        ])
        sig = _emit_signature(t)
        assert "filter: str | None = None" in sig

    def test_required_before_optional(self):
        t = _tool(all_params=[
            {"name": "item_id", "type": "str", "required": True, "description": ""},
            {"name": "limit", "type": "int", "required": False, "description": ""},
        ])
        sig = _emit_signature(t)
        # required before optional
        assert sig.index("item_id") < sig.index("limit")

    def test_return_type_always_str(self):
        t = _tool()
        assert _emit_signature(t).endswith("-> str:")


# ── TestEmitPath ──────────────────────────────────────────────────────────


class TestEmitPath:
    def test_no_path_params_plain_string(self):
        result = _emit_path("/items", [])
        assert result == '"/items"'

    def test_single_path_param_fstring(self):
        result = _emit_path("/items/{item_id}", ["item_id"])
        assert result == 'f"/items/{item_id}"'

    def test_two_path_params(self):
        result = _emit_path("/users/{user_id}/posts/{post_id}", ["user_id", "post_id"])
        assert result == 'f"/users/{user_id}/posts/{post_id}"'

    def test_no_extra_quotes_inside_fstring(self):
        result = _emit_path("/a/{b}", ["b"])
        assert result.startswith('f"')
        assert result.endswith('"')


# ── TestEmitRequestCall ───────────────────────────────────────────────────


class TestEmitRequestCall:
    def test_get_no_params(self):
        t = _tool(method="GET")
        call = _emit_request_call(t)
        assert call == 'return _uc_request("GET", "/items")'

    def test_get_with_query_params(self):
        t = _tool(method="GET", query_params=["limit", "offset"], all_params=[
            {"name": "limit", "type": "int", "required": False, "description": ""},
            {"name": "offset", "type": "int", "required": False, "description": ""},
        ])
        call = _emit_request_call(t)
        assert '"GET"' in call
        assert "query_params=" in call
        assert '"limit": limit' in call
        assert '"offset": offset' in call

    def test_post_with_body_params(self):
        t = _tool(method="POST", body_params=[
            {"name": "name", "type": "str", "required": True, "description": ""},
        ], all_params=[
            {"name": "name", "type": "str", "required": True, "description": ""},
        ])
        call = _emit_request_call(t)
        assert '"POST"' in call
        assert "body=" in call
        assert '"name": name' in call

    def test_path_params_not_in_body_or_query(self):
        t = _tool(
            method="GET",
            path="/items/{item_id}",
            path_params=["item_id"],
            all_params=[
                {"name": "item_id", "type": "str", "required": True, "description": ""},
            ],
        )
        call = _emit_request_call(t)
        assert "query_params" not in call
        assert "body=" not in call

    def test_path_with_param_uses_fstring(self):
        t = _tool(
            method="GET",
            path="/items/{item_id}",
            path_params=["item_id"],
            all_params=[
                {"name": "item_id", "type": "str", "required": True, "description": ""},
            ],
        )
        call = _emit_request_call(t)
        assert 'f"/items/{item_id}"' in call


# ── TestEmitToolFunction ──────────────────────────────────────────────────


class TestEmitToolFunction:
    def test_decorator_present(self):
        t = _tool()
        fn = _emit_tool_function(t)
        assert "@mcp.tool()" in fn

    def test_docstring_present(self):
        t = _tool(description="List all items.")
        fn = _emit_tool_function(t)
        assert '"""List all items."""' in fn

    def test_no_docstring_when_description_empty(self):
        t = _tool(description="")
        fn = _emit_tool_function(t)
        assert '"""' not in fn

    def test_no_docstring_when_description_none(self):
        t = _tool(description=None)
        fn = _emit_tool_function(t)
        assert '"""' not in fn

    def test_ends_with_blank_line(self):
        t = _tool()
        fn = _emit_tool_function(t)
        assert fn.endswith("\n\n")

    def test_name_with_dashes_replaced(self):
        t = _tool(name="list-items")
        fn = _emit_tool_function(t)
        assert "def list_items(" in fn

    def test_return_statement_present(self):
        t = _tool()
        fn = _emit_tool_function(t)
        assert "return _uc_request(" in fn

    def test_docstring_includes_param_descriptions(self):
        t = _tool(all_params=[
            {"name": "channel", "type": "str", "required": True, "description": "Channel ID to fetch"},
            {"name": "limit", "type": "int", "required": False, "description": "Max results to return"},
        ])
        fn = _emit_tool_function(t)
        assert "channel: Channel ID to fetch" in fn
        assert "limit: Max results to return" in fn

    def test_docstring_skips_params_without_description(self):
        t = _tool(all_params=[
            {"name": "channel", "type": "str", "required": True, "description": "Channel ID"},
            {"name": "limit", "type": "int", "required": False, "description": ""},
        ])
        fn = _emit_tool_function(t)
        assert "channel: Channel ID" in fn
        # limit has no description so should not appear in the Args section
        assert "        limit:" not in fn

    def test_docstring_with_params_is_valid_python(self):
        t = _tool(description="List messages", all_params=[
            {"name": "channel", "type": "str", "required": True, "description": "The channel ID"},
            {"name": "limit", "type": "int", "required": False, "description": "Max results"},
        ])
        fn = _emit_tool_function(t)
        # Wrap in a stub module so ast.parse can validate
        src = "async def stub():\n    pass\n" + fn
        ast.parse(src)


# ── TestEmitModule ────────────────────────────────────────────────────────


class TestEmitModule:
    def _make_tools(self):
        return [
            _tool(name="list_items", method="GET", path="/items"),
            _tool(name="create_item", method="POST", path="/items", body_params=[
                {"name": "name", "type": "str", "required": True, "description": "Item name"},
            ], all_params=[
                {"name": "name", "type": "str", "required": True, "description": "Item name"},
            ]),
        ]

    def test_valid_python(self):
        src = emit_module(self._make_tools(), "my-conn", "my-service", "spec.json")
        ast.parse(src)  # raises SyntaxError if invalid

    def test_empty_tools_valid_python(self):
        src = emit_module([], "my-conn", "my-service", "spec.json")
        ast.parse(src)

    def test_empty_tools_no_tool_functions(self):
        src = emit_module([], "my-conn", "my-service", "spec.json")
        assert "@mcp.tool()" not in src

    def test_header_present(self):
        src = emit_module(self._make_tools(), "my-conn", "my-service", "spec.json")
        assert "Generated by uc-mcp generate" in src

    def test_spec_source_in_header(self):
        src = emit_module(self._make_tools(), "my-conn", "my-service", "spec.json")
        assert "spec.json" in src

    def test_connection_name_in_module(self):
        src = emit_module(self._make_tools(), "my-conn", "my-service", "spec.json")
        assert "my-conn" in src

    def test_uc_request_helper_present(self):
        src = emit_module(self._make_tools(), "my-conn", "my-service", "spec.json")
        assert "def _uc_request(" in src

    def test_tool_functions_present(self):
        src = emit_module(self._make_tools(), "my-conn", "my-service", "spec.json")
        assert "async def list_items(" in src
        assert "async def create_item(" in src

    def test_fastmcp_instantiation(self):
        src = emit_module(self._make_tools(), "my-conn", "my-service", "spec.json")
        assert 'FastMCP("my-service")' in src
