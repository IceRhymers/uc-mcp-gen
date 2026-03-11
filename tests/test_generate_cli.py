"""TDD tests for the `uc-mcp generate` CLI subcommand."""

from __future__ import annotations

import pathlib
import sys
from unittest.mock import patch

import pytest

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
SIMPLE_SPEC = str(FIXTURES / "simple_openapi.yaml")


def _run_main(args: list[str]) -> int:
    """Run main() with given argv, return exit code."""
    from uc_mcp.__main__ import main
    with patch.object(sys, "argv", ["uc-mcp"] + args):
        try:
            main()
            return 0
        except SystemExit as e:
            return int(e.code) if e.code is not None else 0


class TestGenerateCliMissingConnection:
    def test_missing_connection_exits_nonzero(self, tmp_path, capsys):
        code = _run_main(["generate", SIMPLE_SPEC, "-o", str(tmp_path / "out")])
        assert code != 0

    def test_missing_connection_no_crash(self, tmp_path, capsys):
        # Should exit cleanly, not raise an unhandled exception
        try:
            _run_main(["generate", SIMPLE_SPEC, "-o", str(tmp_path / "out")])
        except SystemExit:
            pass  # expected


class TestGenerateCliCallsGenerator:
    def test_calls_generator_with_spec(self, tmp_path):
        out = str(tmp_path / "out")
        with patch("uc_mcp.codegen.generator.generate", return_value=out) as mock_gen:
            _run_main(["generate", SIMPLE_SPEC, "--connection", "my-conn", "-o", out])
            mock_gen.assert_called_once()
            call_kwargs = mock_gen.call_args
            assert call_kwargs[0][0] == SIMPLE_SPEC or call_kwargs[1].get("spec_path") == SIMPLE_SPEC or SIMPLE_SPEC in str(call_kwargs)

    def test_passes_connection_name(self, tmp_path):
        out = str(tmp_path / "out")
        with patch("uc_mcp.codegen.generator.generate", return_value=out) as mock_gen:
            _run_main(["generate", SIMPLE_SPEC, "--connection", "slack-conn", "-o", out])
            mock_gen.assert_called_once()
            args, kwargs = mock_gen.call_args
            assert "slack-conn" in args or kwargs.get("connection_name") == "slack-conn"

    def test_passes_output_dir(self, tmp_path):
        out = str(tmp_path / "out")
        with patch("uc_mcp.codegen.generator.generate", return_value=out) as mock_gen:
            _run_main(["generate", SIMPLE_SPEC, "--connection", "c", "-o", out])
            mock_gen.assert_called_once()
            args, kwargs = mock_gen.call_args
            assert out in args or kwargs.get("output_dir") == out

    def test_passes_service_name_when_given(self, tmp_path):
        out = str(tmp_path / "out")
        with patch("uc_mcp.codegen.generator.generate", return_value=out) as mock_gen:
            _run_main(["generate", SIMPLE_SPEC, "--connection", "c", "--name", "my-svc", "-o", out])
            mock_gen.assert_called_once()
            args, kwargs = mock_gen.call_args
            assert "my-svc" in args or kwargs.get("service_name") == "my-svc"


class TestGenerateCliOutput:
    def test_prints_generated_path_on_success(self, tmp_path, capsys):
        out = str(tmp_path / "out")
        with patch("uc_mcp.codegen.generator.generate", return_value=out):
            _run_main(["generate", SIMPLE_SPEC, "--connection", "c", "-o", out])
        captured = capsys.readouterr()
        assert out in captured.out

    def test_exits_1_on_generator_error(self, tmp_path, capsys):
        out = str(tmp_path / "out")
        with patch("uc_mcp.codegen.generator.generate", side_effect=ValueError("No operations")):
            code = _run_main(["generate", SIMPLE_SPEC, "--connection", "c", "-o", out])
        assert code == 1

    def test_error_message_logged(self, tmp_path, caplog):
        import logging
        out = str(tmp_path / "out")
        with patch("uc_mcp.codegen.generator.generate", side_effect=ValueError("No operations")):
            with caplog.at_level(logging.ERROR):
                _run_main(["generate", SIMPLE_SPEC, "--connection", "c", "-o", out])
        assert "No operations" in caplog.text
