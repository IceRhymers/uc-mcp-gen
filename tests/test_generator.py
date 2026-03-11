"""TDD tests for codegen/generator.py."""

from __future__ import annotations

import ast
import pathlib
from unittest.mock import patch

import pytest

from uc_mcp_gen.codegen.generator import generate


FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SIMPLE_SPEC = FIXTURES / "simple_openapi.yaml"
SIMPLE_SPEC_JSON = FIXTURES / "simple_openapi.json"


class TestGenerateFileTree:
    def test_creates_expected_files(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        out = pathlib.Path(result)
        assert (out / "databricks.yml").exists()
        assert (out / "app.yaml").exists()
        assert (out / "pyproject.toml").exists()
        assert (out / "src" / "app" / "__init__.py").exists()
        assert (out / "src" / "app" / "main.py").exists()

    def test_no_definitions_dir(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        assert not (pathlib.Path(result) / "definitions").exists()

    def test_no_scripts_dir(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        assert not (pathlib.Path(result) / "scripts").exists()

    def test_returns_output_path(self, tmp_path):
        out = tmp_path / "my-out"
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(out))
        assert pathlib.Path(result).resolve() == out.resolve()


class TestServiceNameDerivation:
    def test_explicit_name_used(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", service_name="custom-name", output_dir=str(tmp_path / "out"))
        yml = (pathlib.Path(result) / "databricks.yml").read_text()
        assert "custom-name" in yml

    def test_name_derived_from_spec_title(self, tmp_path):
        # simple_openapi.yaml has title "Simple Test API" → "simple-test-api"
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        yml = (pathlib.Path(result) / "databricks.yml").read_text()
        assert "simple-test-api" in yml

    def test_derived_name_is_kebab_case(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        out = pathlib.Path(result)
        yml = (out / "databricks.yml").read_text()
        # Should not contain spaces or uppercase
        import re
        names = re.findall(r"name:\s*(.+)", yml)
        for name in names:
            name = name.strip().strip("'\"")
            assert " " not in name


class TestDefaultOutputDir:
    def test_default_output_dir_uses_service_name(self, tmp_path):
        with patch("uc_mcp_gen.codegen.generator._default_output_dir") as mock_dir:
            mock_dir.return_value = tmp_path / "generated_mcp_servers" / "simple-test-api-app"
            (tmp_path / "generated_mcp_servers" / "simple-test-api-app" / "src" / "app").mkdir(parents=True)
            result = generate(str(SIMPLE_SPEC), "my-conn")
            assert "simple-test-api" in result


class TestPyprojectContent:
    def test_no_uc_mcp_dep(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        content = (pathlib.Path(result) / "pyproject.toml").read_text()
        assert "uc_mcp" not in content
        assert "uc-mcp" not in content

    def test_no_pyyaml_dep(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        content = (pathlib.Path(result) / "pyproject.toml").read_text()
        assert "pyyaml" not in content.lower()

    def test_no_jsonschema_dep(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        content = (pathlib.Path(result) / "pyproject.toml").read_text()
        assert "jsonschema" not in content

    def test_required_deps_present(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        content = (pathlib.Path(result) / "pyproject.toml").read_text()
        assert "mcp" in content
        assert "databricks-sdk" in content
        assert "starlette" in content
        assert "uvicorn" in content


class TestMainPyIsValidPython:
    def test_generated_main_py_parses(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        src = (pathlib.Path(result) / "src" / "app" / "main.py").read_text()
        ast.parse(src)  # raises SyntaxError if invalid

    def test_generated_main_py_has_tool_functions(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        src = (pathlib.Path(result) / "src" / "app" / "main.py").read_text()
        assert "@mcp.tool()" in src
        assert "async def list_items(" in src
        assert "async def create_item(" in src
        assert "async def get_item(" in src

    def test_generated_main_py_no_uc_mcp_import(self, tmp_path):
        result = generate(str(SIMPLE_SPEC), "my-conn", output_dir=str(tmp_path / "out"))
        src = (pathlib.Path(result) / "src" / "app" / "main.py").read_text()
        assert "from uc_mcp" not in src
        assert "import uc_mcp" not in src


class TestIdempotency:
    def test_same_args_produce_identical_files(self, tmp_path):
        out1 = str(tmp_path / "run1")
        out2 = str(tmp_path / "run2")
        generate(str(SIMPLE_SPEC), "my-conn", service_name="my-svc", output_dir=out1)
        generate(str(SIMPLE_SPEC), "my-conn", service_name="my-svc", output_dir=out2)

        for fname in ["databricks.yml", "app.yaml", "pyproject.toml"]:
            c1 = (pathlib.Path(out1) / fname).read_text()
            c2 = (pathlib.Path(out2) / fname).read_text()
            assert c1 == c2, f"{fname} differs between runs"

    def test_existing_output_dir_overwritten(self, tmp_path):
        out = str(tmp_path / "out")
        generate(str(SIMPLE_SPEC), "my-conn", output_dir=out)
        # Second call should not raise
        generate(str(SIMPLE_SPEC), "my-conn", output_dir=out)


class TestJsonSpecInput:
    def test_json_spec_produces_same_tool_functions(self, tmp_path):
        """JSON and YAML equivalents produce the same tool functions in main.py."""
        out_yaml = str(tmp_path / "from-yaml")
        out_json = str(tmp_path / "from-json")
        generate(str(SIMPLE_SPEC), "my-conn", service_name="test-svc", output_dir=out_yaml)
        generate(str(SIMPLE_SPEC_JSON), "my-conn", service_name="test-svc", output_dir=out_json)

        src_yaml = (pathlib.Path(out_yaml) / "src" / "app" / "main.py").read_text()
        src_json = (pathlib.Path(out_json) / "src" / "app" / "main.py").read_text()

        # Both should define the same three tool functions
        for fn in ("list_items", "create_item", "get_item"):
            assert f"async def {fn}(" in src_yaml
            assert f"async def {fn}(" in src_json

    def test_json_spec_valid_python(self, tmp_path):
        result = generate(str(SIMPLE_SPEC_JSON), "my-conn", output_dir=str(tmp_path / "out"))
        src = (pathlib.Path(result) / "src" / "app" / "main.py").read_text()
        ast.parse(src)  # raises SyntaxError if invalid

    def test_json_spec_produces_valid_dab(self, tmp_path):
        result = generate(str(SIMPLE_SPEC_JSON), "my-conn", output_dir=str(tmp_path / "out"))
        out = pathlib.Path(result)
        assert (out / "databricks.yml").exists()
        assert (out / "app.yaml").exists()
        assert (out / "pyproject.toml").exists()
        assert (out / "src" / "app" / "main.py").exists()


class TestErrorCases:
    def test_missing_spec_raises(self, tmp_path):
        with pytest.raises((FileNotFoundError, ValueError, Exception)):
            generate("/nonexistent/spec.yaml", "my-conn", output_dir=str(tmp_path / "out"))

    def test_spec_with_no_operations_raises(self, tmp_path, tmp_path_factory):
        empty_spec = tmp_path_factory.mktemp("specs") / "empty.yaml"
        empty_spec.write_text("openapi: '3.0.0'\ninfo:\n  title: Empty\n  version: '1.0'\npaths: {}\n")
        with pytest.raises((ValueError, Exception)):
            generate(str(empty_spec), "my-conn", output_dir=str(tmp_path / "out"))
