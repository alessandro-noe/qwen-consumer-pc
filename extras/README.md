# extras — optional agent tools

Not needed to run the model or the proxy. `scripts/install.ps1` registers Kael and the skill library as MCP servers in `opencode.json`;
remove them there if you do not want them.

| File | What it does | Status |
|---|---|---|
| `kael_mcp.py` | MCP server: an error memory that saves a fix **only if a test command proves it** (the test is re-run at save time); mandatory `verifica` before saying "done"; STOP after 3 identical failures. Memory file: `extras/memoria/errori.jsonl` (git-ignored). | used in the agent benchmarks |
| `biblioteca_mcp.py` | MCP server: indexes your skills (this repo's `opencode/.opencode/skills`, plus `~/.claude/skills`, `~/.claude/plugins` and `~/.config/opencode/skills` if present, plus `BIBLIOTECA_RADICI`) at near-zero context cost; optional Kev-4B picks the right skill or says "none". Adapted skills are saved in `skill_adattate/` (git-ignored). | works; not benchmarked end to end |
| `esecutore.py` | Browser executor: the big model plans each page, Kev-4B picks the element; irreversible actions (send, pay, delete) require confirmation **in code**. Needs `playwright` and Microsoft Edge. | 10/10 on the local test site (`benchmarks/sito_prova`), no speed gain on small pages |

Run any of them with `python extras/<file>.py`. They talk to the model at `http://127.0.0.1:8090` and to Kev at `http://127.0.0.1:9931` (`KEV_URL`).
