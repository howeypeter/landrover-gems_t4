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
  `v0.0.1`–`v0.0.5` exist; all pushed to `origin`. **v0.0.5 is committed
  (`599a8bb`) and pushed but NOT yet merged to main — the user handles the
  merge/tag themselves.**
- The Python **package version tracks the release tag** (`pyproject.toml` /
  `gems_t4/__init__.py` / `--version` all say **0.0.5** as of this branch —
  aligned since v0.0.4, before that 0.1.0). Keep them in lockstep when cutting a
  version; `tests_regression/test_regr_cli.py::test_version_flag` now asserts
  all three match.
- **Release-notes convention:** `RELEASE_NOTES.md` = the CURRENT release;
  `RELEASE_NOTES_v0.0.x.md` = archive. When cutting a new version, `git mv`
  the old `RELEASE_NOTES.md` to its versioned name first. (v0.0.5 archived
  v0.0.4 this way → `RELEASE_NOTES_v0.0.4.md`.)
- `tests_regression/` (added v0.0.4) is an independent suite outside pyproject
  `testpaths` — run `pytest tests_regression` explicitly; **234 tests** as of
  v0.0.5 (was 233; updated for the 12-screen/6-menu-item contract).
- **Deliberately left UNTRACKED (user's call, 2026-07-11):** the Phase-3
  hardware shopping lists (`PICO_SHOPPING_LIST.*`, `PHASE3_SHOPPING_LIST*.md`)
  and three framework/packaging research notes under `memory/`
  (`FRAMEWORK_EVAL_SUMMARY.md`, `framework-pico-serial-eval.md`,
  `packaging-distribution-research.md`). Still on disk; user said not to track.

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
