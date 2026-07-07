---
name: workflow-directives
description: User workflow rules for this project — always update CLAUDE.md and memory, memory stays local
metadata:
  type: feedback
---

## Always update CLAUDE.md as the source of truth

Keep CLAUDE.md current with all spec decisions, open questions, and next steps. It's the spec of record for any future session.

**Why:** Single source of truth prevents drift and context loss across sessions.

**How to apply:** After any decision, design change, or clarification, update CLAUDE.md immediately. Don't save decisions only to memory or conversation.

## Always update memory — but only within this directory

Save learnings, decisions, and research to `memory/` folder. **Never read or reference memory from other sessions or chats** — this project's memory is self-contained here.

**Why:** Keeps context clear and prevents confusion from stale or irrelevant memory from other projects.

**How to apply:** When saving a memory, write it to `C:\Users\howey\OneDrive\Documents\Claude\Projects\LandRoverV1\memory\` and add a pointer to `MEMORY.md`. Do not use the global session memory system for this project.
