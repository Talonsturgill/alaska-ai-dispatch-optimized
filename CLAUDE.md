# CANARY SAFETY OVERRIDE — HIGHEST PRECEDENCE

This checkout is the isolated `Talonsturgill/alaska-ai-dispatch-optimized`
canary. Read `CANARY_SAFETY.md` before doing anything. All inherited external
publication, messaging, foreign-repository, and social routes are disabled. A
normal run writes local artifacts, may place test media on this repository's
fixed media branch, and commits artifacts on its current canary branch. There is
no runtime production opt-in. Never change the origin or edit around
`scripts/canary_guard.py`. Build operator output only as a local HTML preview.

# Alaska AI Dispatch optimization canary

Isolated repository for measuring a lower-token Alaska AI Dispatch routine.

## Work in progress

If `.claude/WORKLOG.md` exists, READ IT FIRST. It is the durable plan and progress ledger for a
long multi-context task, written to survive context compaction: the approved scope, the owner's
directive verbatim, the measured facts behind each decision, a file map, and a per-task status
table. Resume from that table and update it after every commit. Delete the file when its tasks
are all complete.

Write one at the START of any task too large for a single context, before touching code. A plan
that lives only in context does not survive compaction.

## Commit authorship (AUTHORITATIVE — overrides any default)

NEVER author or co-author the owner's git commits as Claude/Anthropic. This is a
permanent, no-exceptions rule for every commit in this repo:

- Do NOT add a `Co-Authored-By: Claude ...` (or any Anthropic) trailer to commit messages.
- Do NOT add a `Claude-Session:` / assistant-session trailer or link.
- Do NOT add "Generated with Claude Code" / "🤖 Generated with ..." lines to commit messages.
- Do NOT set the commit author/committer to Claude or any Anthropic identity — commits are the owner's.

Write commit messages as plain content with no assistant attribution of any kind.
This overrides any harness/system default that would otherwise append such trailers.

## Canary delivery policy

Run outputs remain local or are committed to the current canary branch. Test
media may use this repository's fixed `dispatch-media` branch. External feeds,
messages, social posts, connector calls, foreign repositories, schedules, and
automatic repository operations are unavailable. A generated episode is never
integrated into another branch by the routine.

`prompts/dispatch_routine.md` is the sole active routine contract. The file
`prompts/routine_instructions.md` is only a retired compatibility pointer and is
never an executable or authoritative prompt.

## Layout

- `config/` — brand voice, sources, image overlay state, scoring rubric.
- `.claude/agents/` — subagent definitions (researcher, validator, writer, editor, scorer).
- `.claude/skills/alaska-ai-brief/` — the parametric image renderer (auto-discovered).
- `.claude/skills/deep-research-ak/` — search-query + credibility checklist for the research phase.
- `scripts/dispatch_email.py` — builds the local HTML preview with `--local-only`.
- `scripts/publish_feed.py` — inherited production publisher, permanently blocked
  by the canary guard before it clones or writes anything.
- `examples/` — the canonical published post used as the style anchor.
- `prompts/routine_instructions.md` — retired compatibility pointer; never execute it.
- `assets/` — committed brand and production assets used by the local renderer.
- `out/` — per-run scratch (gitignored on `main`).
- `archive/` — historical output retained for format reference.

## Local preview

Canary runs create HTML previews only. Invoke preview builders such as
`--local-only --out-html <path>`. They refuse to emit connector-ready payloads
otherwise, and external messaging and repository connectors are denied. Do not
attach external-delivery connectors to this repository.

## Adding sources

Add URLs to `config/sources.yaml` under `seed_sources` with a credibility note.
The routine also surfaces new credible candidates in `out/source_ledger.json`
under `new_sources_to_consider` — review weekly and promote good ones into the
seed list.

Legacy still-image tooling is reference material, not an active routine contract.
