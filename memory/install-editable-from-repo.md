---
name: install-editable-from-repo
description: The gems_t4 command MUST be pip-installed editable from the OneDrive repo, NOT a Downloads ZIP — a stale copy causes phantom bugs.
metadata:
  type: project
---

**The `gems_t4` console command must be installed editable from the canonical
OneDrive repo, not from a downloaded GitHub ZIP.** (2026-09-04)

On 2026-09-04 a real hardware bug hunt was doubled by an environment trap: the
scoop Python's `gems_t4` was `pip install -e` from
`C:\Users\howey\Downloads\landrover-gems_t4-main\...` (an old GitHub ZIP,
package version 0.0.5), while all edits were being made in the repo at
`C:\Users\howey\OneDrive\Documents\Claude\Projects\LandRoverV1`. So fixes never
reached the running command. It *looked* intermittent because running from
inside the OneDrive repo dir shadows the install via cwd on `sys.path`, so the
same command sometimes ran the repo and sometimes ran the stale ZIP.

**Symptom:** a fix verified by `pytest` in the repo has no effect on the
`gems_t4 ...` command; tracebacks show file paths under `Downloads\...`.

**Check:** `python -m pip show gems_t4` -> "Editable project location" must be
the OneDrive repo. Or `gems_t4 --version` / a traceback's file paths.

**Fix:** `<python> -m pip install -e "C:/Users/howey/OneDrive/Documents/Claude/Projects/LandRoverV1"`
(use the SAME interpreter the `gems_t4.exe` uses — here scoop's Python, not the
`.venv`). Then delete the orphaned Downloads copy so it can't be re-selected.

Related: [[repo-git-state]], [[real-gems-protocol]].
