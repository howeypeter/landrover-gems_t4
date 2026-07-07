---
name: repo-git-state
description: Git/repo hygiene state — branch, what's tracked, .gitignore/.gitattributes, README setup, and the UTF-16 gotcha
metadata:
  type: project
---

**As of 2026-07-07.** Repo hygiene set up; **nothing meaningful is committed yet.**

## Git state
- It IS a git repo. Current branch: **`v0.0.1`**. Branches: `main`, `v0.0.1`
  (current), `remotes/origin/main`. Remote `origin` exists (only `main` pushed).
- **Only ONE file is tracked/committed: `README.md`** (originally a GitHub
  auto-generated stub). Everything else — all 68 Python files, both READMEs,
  CLAUDE.md, INTERFACES.md, GUI_INTERFACES.md, firmware, memory, etc. — is
  **untracked** (`??`). It's all safe on disk but not in git history.
- ⚠️ **Next session: the work is not durably saved in git.** A stray
  `git checkout`/`reset --hard`/`clean` could wipe untracked files. Recommend a
  first real commit: `git add -A && git commit -m "..."` on `v0.0.1`.
- Branch switches so far did NOT lose anything (untracked files travel across
  switches). Verified via full test run (93 passed) after the switch.

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
