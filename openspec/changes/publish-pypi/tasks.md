## 1. Rename module and update imports

- [ ] 1.1 Rename `src/uc_mcp/` → `src/uc_mcp_gen/`
- [ ] 1.2 Update `pyproject.toml`: `name`, `[project.scripts]`, `[tool.hatch.build.targets.wheel]`
- [ ] 1.3 Update `src/uc_mcp_gen/__main__.py`: `prog="uc-mcp-gen"`
- [ ] 1.4 Update all test imports: `from uc_mcp` → `from uc_mcp_gen`
- [ ] 1.5 Run `uv run pytest -v` — 72 passed

## 2. Add PyPI metadata to `pyproject.toml`

- [ ] 2.1 Add `description`, `license`, `readme`, `authors`, `keywords`, `classifiers`
- [ ] 2.2 Add `[project.urls]` with Homepage, Repository, Issues (use renamed repo URL)
- [ ] 2.3 Run `uv build` — wheel and sdist build cleanly

## 3. Add GitHub Actions publish workflow

- [ ] 3.1 Create `.github/workflows/publish.yml`
  - Trigger: `push` on tags `v*.*.*`
  - Job `test`: `uv run pytest -v`
  - Job `publish`: needs `test`, OIDC `id-token: write`, `uv build`, `pypa/gh-action-pypi-publish`
- [ ] 3.2 Verify workflow YAML is valid

## 4. Update docs

- [ ] 4.1 Update `README.md` — primary usage is `uvx uc-mcp-gen generate ...`
- [ ] 4.2 Update `CLAUDE.md` — module map, commands use `uc_mcp_gen` / `uc-mcp-gen`
- [ ] 4.3 Update `examples/slack-app/README.md` — generation command uses `uc-mcp-gen`

## 5. Final verification

- [ ] 5.1 `uv run pytest -v` — 72 passed, 0 failed
- [ ] 5.2 `uv run uc-mcp-gen --help` — shows `generate`
- [ ] 5.3 `uv build` — no errors
- [ ] 5.4 Commit and push to `feat/codegen-generate`

## 6. One-time manual steps (Tanner)

- [ ] 6.1 Register PyPI trusted publisher at https://pypi.org/manage/account/publishing/
  - Package name: `uc-mcp-gen`
  - Owner: `IceRhymers`
  - Repo: `uc-mcp-gen` (after GitHub rename)
  - Workflow: `publish.yml`
  - Environment: (leave blank)
- [ ] 6.2 Rename GitHub repo: Settings → Repository name → `uc-mcp-gen`
- [ ] 6.3 First publish: `git tag v0.1.0 && git push --tags`
