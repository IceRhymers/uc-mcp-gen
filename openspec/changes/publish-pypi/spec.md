# Spec: publish-pypi

## Purpose

Rename the package to `uc-mcp-gen`, align Python module and CLI entry point, add PyPI metadata, and add a GitHub Actions publish workflow so the tool is installable via `uvx uc-mcp-gen generate ...`.

---

## Requirements

### R1: Package renamed to `uc-mcp-gen`

`pyproject.toml` `name` field is `"uc-mcp-gen"`. The published PyPI package is `uc-mcp-gen`.

### R2: Python module renamed to `uc_mcp_gen`

`src/uc_mcp/` directory renamed to `src/uc_mcp_gen/`. All internal imports updated. `[tool.hatch.build.targets.wheel] packages` updated to `["src/uc_mcp_gen"]`.

### R3: CLI entry point renamed to `uc-mcp-gen`

`[project.scripts]` entry: `uc-mcp-gen = "uc_mcp_gen.__main__:main"`. The `argparse` `prog` in `__main__.py` updated to `"uc-mcp-gen"`. Running `uc-mcp-gen --help` works. Running `uvx uc-mcp-gen generate ...` works.

### R4: `pyproject.toml` has full PyPI metadata

Matching `uc-mcp-proxy` quality:

```toml
description = "Generate Databricks App MCP servers from OpenAPI specs"
license = "MIT"
readme = "README.md"
authors = [{ name = "Tanner Wendland" }]
keywords = ["mcp", "databricks", "openapi", "codegen", "unity-catalog"]
classifiers = [
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]

[project.urls]
Homepage = "https://github.com/IceRhymers/uc-mcp-gen"
Repository = "https://github.com/IceRhymers/uc-mcp-gen"
Issues = "https://github.com/IceRhymers/uc-mcp-gen/issues"
```

### R5: GitHub Actions publish workflow

`.github/workflows/publish.yml` triggers on `push` with tags matching `v*.*.*`. Uses `pypa/gh-action-pypi-publish` with OIDC (no stored secrets). Runs tests first — publish only proceeds if tests pass.

```yaml
on:
  push:
    tags: ["v*.*.*"]
jobs:
  test:
    # uv run pytest -v
  publish:
    needs: test
    permissions:
      id-token: write
    # uv build + pypa/gh-action-pypi-publish
```

### R6: All 72 tests pass after rename

Test files import from `uc_mcp_gen.codegen.generator` and `uc_mcp_gen.codegen.python_emitter`. No test logic changes — only import paths.

### R7: README updated for `uvx` workflow

Primary install/usage block becomes:

```bash
uvx uc-mcp-gen generate spec.yaml --connection my-conn -o ./my-app
```

Local dev section retained:

```bash
uv sync
uv run uc-mcp-gen generate spec.yaml --connection my-conn
```

### R8: CLAUDE.md updated

Package name, module map paths, and key commands reflect `uc_mcp_gen` and `uc-mcp-gen`.

---

## Scenarios

| # | Assertion | Expected |
|---|---|---|
| S1 | `uvx uc-mcp-gen --help` | Shows `generate` subcommand |
| S2 | `uvx uc-mcp-gen generate simple_openapi.yaml --connection c -o /tmp/out` | Generates valid DAB |
| S3 | `uv run pytest -v` | 72 passed, 0 failed |
| S4 | `cat pyproject.toml \| grep name` | `name = "uc-mcp-gen"` |
| S5 | `ls src/` | `uc_mcp_gen/` (not `uc_mcp/`) |
| S6 | GitHub Actions on `git tag v0.1.0 && git push --tags` | Publishes to PyPI |
| S7 | `pip install uc-mcp-gen` | Installs and `uc-mcp-gen --help` works |
