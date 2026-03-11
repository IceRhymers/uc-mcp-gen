## Context

`uc-mcp-proxy` is already on PyPI. The generator (`uc-mcp-server`) should follow the same pattern so users can run it with `uvx` without cloning the repo. The package is renamed to `uc-mcp-gen` to signal it is a code generation tool, matching the `uc-mcp-proxy` sibling naming convention.

## Goals / Non-Goals

**Goals:**
- `uvx uc-mcp-gen generate <spec> --connection <conn>` works from anywhere
- Package name, Python module, and CLI entry point are consistent: `uc-mcp-gen` / `uc_mcp_gen` / `uc-mcp-gen`
- PyPI metadata matches `uc-mcp-proxy` quality (license, authors, keywords, classifiers, URLs)
- GitHub Actions publishes to PyPI on every version tag via OIDC trusted publisher (no stored secrets)
- All 72 tests continue to pass

**Non-Goals:**
- Changing the `generate` command behaviour or generated output
- Publishing to a private registry
- Changing the generated app's internal structure

## Decisions

### D1: Rename Python package from `uc_mcp` to `uc_mcp_gen`

The proxy uses `uc_mcp_proxy`. Consistency requires `uc_mcp_gen` for the generator. All internal imports (`from uc_mcp.codegen...`) update to (`from uc_mcp_gen.codegen...`). The source directory moves from `src/uc_mcp/` to `src/uc_mcp_gen/`.

### D2: CLI entry point renamed from `uc-mcp` to `uc-mcp-gen`

`pyproject.toml` `[project.scripts]` changes from `uc-mcp = "uc_mcp.__main__:main"` to `uc-mcp-gen = "uc_mcp_gen.__main__:main"`. The `prog` name in argparse updates accordingly.

### D3: GitHub Actions OIDC publish workflow

A `.github/workflows/publish.yml` workflow triggers on `v*` tags. Uses PyPI trusted publisher (OIDC) — no API token stored in GitHub secrets. Requires a one-time trusted publisher registration on PyPI for the `IceRhymers/uc-mcp-server` (or renamed) repo.

Workflow steps:
1. Checkout
2. `uv build`
3. Publish with `pypa/gh-action-pypi-publish` using OIDC

### D4: `pyproject.toml` metadata matches `uc-mcp-proxy`

Add: `description`, `license`, `readme`, `authors`, `keywords`, `classifiers`, `[project.urls]`. Keep existing `dependencies` and `dev` group unchanged except removing `pex` (not needed for a pure codegen tool).

### D5: GitHub repo rename is out of scope

Tanner will rename the GitHub repo via GitHub Settings after this change lands. No code changes required for that — GitHub auto-redirects.

## Affected Files

```
RENAME src/uc_mcp/ → src/uc_mcp_gen/
MODIFY pyproject.toml         — name, scripts entry, metadata
MODIFY src/uc_mcp_gen/__main__.py  — prog name in argparse
MODIFY src/uc_mcp_gen/codegen/generator.py — import path (if any self-refs)
ADD    .github/workflows/publish.yml
MODIFY CLAUDE.md              — updated package name, uvx command
MODIFY README.md              — updated install/usage with uvx
```
