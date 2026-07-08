---
name: repo-git-state
description: Git/repo hygiene state — branch, what's tracked, .gitignore/.gitattributes, README setup, and the UTF-16 gotcha
metadata:
  type: project
---

**As of 2026-07-07 (v0.0.4).** Everything is committed and the repo lives on
GitHub (`howeypeter/landrover-gems_t4`).

## Git state
- Work proceeds on **version branches `v0.0.x`** (currently `v0.0.4`, the
  bugfix/quality branch) with `main` as the merge destination. Branches
  `v0.0.1`–`v0.0.4` exist; `v0.0.1`–`v0.0.3` are pushed to `origin`.
- The Python **package version tracks the release tag** as of v0.0.4
  (`pyproject.toml` / `gems_t4/__init__.py` / `--version` all say 0.0.4 —
  before that they said 0.1.0, a mismatch found by the v0.0.3 regression
  sweep). Keep them in lockstep when cutting a version.
- **Release-notes convention:** `RELEASE_NOTES.md` = the CURRENT release;
  `RELEASE_NOTES_v0.0.x.md` = archive. When cutting a new version, `git mv`
  the old `RELEASE_NOTES.md` to its versioned name first.
- v0.0.4 removed `diagrams/p38-gems-network.svg` (`git rm`; user-reported
  incorrect) and added `tests_regression/` — a 233-test independent suite
  outside pyproject `testpaths` (run `pytest tests_regression` explicitly).

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
