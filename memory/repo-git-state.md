---
name: repo-git-state
description: Git/repo hygiene state — branch, what's tracked, .gitignore/.gitattributes, README setup, and the UTF-16 gotcha
metadata:
  type: project
---

**As of 2026-07-11 (v0.0.5).** The repo lives on GitHub
(`howeypeter/landrover-gems_t4`).

## Git state
- Work proceeds on **version branches `v0.0.x`** (currently **`v0.0.5`**, the
  TCP/network-transport release) with `main` as the merge destination. Branches
  `v0.0.1`–`v0.0.5` exist; all pushed to `origin`. **v0.0.5 merged into `main`
  2026-07-11** (`git merge --no-ff v0.0.5`, merge commit `2ab5eb6`, pushed to
  `origin/main`). No conflicts — `main` had only diverged by its own PR-merge
  wrapper commit, already content-identical to what v0.0.5 carried forward.
  `main` is now the current/authoritative branch; no separate tag was cut (the
  version lives in `pyproject.toml`/`__version__`, not a git tag, per the
  existing convention).
- The Python **package version tracks the release tag** (`pyproject.toml` /
  `gems_t4/__init__.py` / `--version` all say **0.0.5** as of this branch —
  aligned since v0.0.4, before that 0.1.0). Keep them in lockstep when cutting a
  version; `tests_regression/test_regr_cli.py::test_version_flag` now asserts
  all three match.
- **Release notes: REMOVED 2026-07-11.** The standalone `RELEASE_NOTES*.md`
  files (current + v0.0.1–v0.0.4 archives) were `git rm`'d to declutter the
  project root (they survive in git history). Release history now = git tags +
  version-branch commit messages + CLAUDE.md "Build status". Do NOT re-add
  RELEASE_NOTES files; the old "current + versioned archive" convention is
  retired.
- `tests_regression/` (added v0.0.4) is an independent suite outside pyproject
  `testpaths` — run `pytest tests_regression` explicitly; **235 tests** as of
  the 2026-07-11 QA quick fixes (was 234; +1 for the dtc-clear-confirm test,
  count assertions bumped 37→40 live params).
- **DELETED (user's call, 2026-07-11):** the Phase-3 hardware shopping lists
  (`docs/PICO_SHOPPING_LIST.*`, `docs/PHASE3_SHOPPING_LIST*.md`) and three
  framework/packaging research notes under `memory/`
  (`FRAMEWORK_EVAL_SUMMARY.md`, `framework-pico-serial-eval.md`,
  `packaging-distribution-research.md`) were first left untracked, then
  deleted outright (never having been in git, they're gone for good — no
  history to recover from). Don't recreate these unless the user asks again.
- **Root markdown policy (2026-07-11, user decision): only `CLAUDE.md`,
  `README.md`, `INSTALL.md` at the repo root.** Everything else moved into
  `docs/`: `INTERFACES.md`/`GUI_INTERFACES.md` (`git mv`'d — tracked, no code
  reads them by path, doc-only move) and the untracked shopping lists (plain
  `mv`, stayed untracked). New `INSTALL.md` was created at the root — split out
  of README.md's old "Install & run"/"Windows build"/"Hardware" sections, which
  are now short pointers to it. Do not add new root-level `.md` files going
  forward; put them in `docs/` and link to them from README.md/CLAUDE.md.

## .gitignore (added/expanded this session)
Ignores: `.venv/`, `__pycache__/`, `*.py[cod]`, `*.egg-info/`, build/dist,
`.pytest_cache/`/`.mypy_cache/`/`.ruff_cache/`, `*.bin`, `backups/`,
`scratch_shots/`, OneDrive/Windows junk (Thumbs.db, Desktop.ini, $RECYCLE.BIN),
editor junk, firmware build output (`*.uf2`/`*.elf`/`build/`). Verified `.venv`
etc. are ignored. ~100 real files will be tracked on first `git add -A`.

## .gitattributes (added this session)
`* text=auto eol=lf` + binary rules (png/jpg/pdf/bin/uf2/elf). Reason: Windows
git has **`core.autocrlf = true`**, which warned it would rewrite our LF files to
CRLF ("LF will be replaced by CRLF"). Pinning `eol=lf` keeps LF in repo AND
working tree, deterministic across machines, silences the warning. Confirmed the
warning is gone via `git add --all --dry-run`.

## READMEs — dual setup (decided this session)
- **`README.md`** = concise Markdown GitHub landing page (renders natively; links
  to the HTML). **`README.html`** = full styled version (open in a browser;
  GitHub can't render `.html` inline — would need GitHub Pages).
- You CANNOT embed the styled HTML into README.md — GitHub strips `<style>`/CSS
  classes/`<iframe>`. So: Markdown landing page + link to HTML is the pattern.
- Keep the two roughly in sync when docs change.
- ⚠️ **UTF-16 gotcha:** something in this environment (OneDrive/editor) keeps
  re-encoding `README.md` to **UTF-16LE**. It was fixed to UTF-8 with an explicit
  Python re-encode (`open(...,encoding='utf-16-le').read()` → write utf-8). The
  Write tool matches the existing file's encoding, so if README.md flips back to
  UTF-16, re-convert to UTF-8 (GitHub renders UTF-8 Markdown correctly; UTF-16
  can look broken). Check with `file README.md`.

Related: [[implementation-status]], [[phase5-programming]], [[workflow-directives]].
