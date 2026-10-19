---
name: adatta-skill
description: Trasforma una skill scritta per un altro modello (Claude) in una versione per te, compatta e verificabile. Usala dopo aver usato una skill originale della biblioteca, poi salvala con skill_salva_adattata.
metadata:
  origine: agente-locale (idea dell'utente, 2026-10-18)
---
# Adapt a skill for yourself

Goal: same know-how, fewer tokens, only tools you really have, always verifiable.

Write the adapted version in compact English (`key: value`, short imperative lines, no filler). Keep:
- when: the situations where the skill applies (1-2 lines).
- steps: the concrete procedure, in order. Keep exact names: files, commands, libraries, CSS values, numbers.
- rules: the hard constraints (do / never). Keep every "never" of the original.
- check: how to prove the result is right (a command, a test, a screenshot to look at, a checklist). Mandatory.
- files: supporting files of the original folder you may read when needed (paths only, not their content).

Remove or replace:
- tools you do not have (image generation with Gemini/nano-banana, Claude-only tools like WebFetch/Agent/TodoWrite):
  write what to do instead (e.g. "use a placeholder image https://placehold.co/WxH", "ask the user").
- marketing text, long examples, repeated explanations.

Size: 200-8000 characters (usually 1000-3000). Then call `biblioteca.skill_salva_adattata(name, text)`.
If the task done with the skill failed, do NOT save: an adapted skill must come from a use that worked.
