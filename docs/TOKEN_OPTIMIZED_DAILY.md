# Token-optimized daily controller

This is the bounded Phase-C controller for the optimization canary. It reduces
repeated model context and enforces a finite call/revision budget while leaving
the existing correctness, render, evidence, preflight, panel, and canary safety
contracts intact.

It does not enable production, external delivery, or the live site. At this
commit, the active `DispatchDaily` Remotion component is still the frozen
August 13 replay fixture documented in `CORRECTNESS_FOUNDATION.md`. The
controller is therefore safe to inspect and exercise with fixture artifacts,
but a fresh episode also requires the separately reviewed parametric component.

## Measured context boundary

The estimator is intentionally simple and reproducible:
`ceil(UTF-8 bytes / 4)`. It is a planning metric, not a claim about a provider's
bill. Provider-reported usage and cost are recorded separately after each call.

| Input | Deterministic estimate |
|---|---:|
| Historical master routine alone | 33,308 tokens |
| Historical minimum standing context | 35,227 tokens |
| Historical fully referenced inventory | 101,057 tokens |
| New controller prompt | 566 tokens |
| New standing context | 528 tokens |
| New total static block | 1,094 tokens |
| Real August 28 compact story packet | 3,130 tokens |

The static block is 96.9% smaller than the measured 35,227-token standing
baseline. It is hash-keyed once and reused. The story packet is dynamic and
separate, so later calls do not reload the repository, archived runs, the
legacy master prompt, or broad craft documentation.

## Hard daily contract

`config/daily_controller.json` is the controller authority:

- America/Anchorage daily date;
- 112–130 seconds at 30 fps;
- 262–282 spoken words;
- exactly three video roles: 1080×1920 master, 1080×1080 square, and 720×1280
  mobile;
- 1080×1350/4:5 explicitly forbidden;
- normal plan: eight model calls (maximum nine);
- worst case: fourteen model calls, including six total judge calls;
- hard cap: fifteen calls, 95,000 uncached input tokens, 220,000 cache-read
  tokens, 36,000 output tokens, and $10.00 per run unless the operator lowers
  it at initialization;
- zero broad searches when the Carousel fact pack exists; no more than ten in
  the bounded fallback; and
- one repair at most. A second failed panel ends `BLOCKED_QUALITY`, not a
  below-bar release.

The logical tiers are provider-independent. The one showrunner uses the high
tier; production, validation, repair, and judges use the mid tier; optional
triage uses the cheap tier. Evaluation telemetry reports those as
`frontier`, `balanced`, and `fast` without hard-coding a vendor or a price.

## Compact fact-pack reuse

The normal path reads, without editing, these same-date Carousel artifacts:

- `runs/<date>/selection.md`
- `runs/<date>/claims.json`
- `runs/<date>/scout_merge.md`
- `runs/<date>/run_state.json`

The builder retains up to twelve source-backed claims, source URLs, the selected
angle and why-it-matters excerpt, plus SHA-256 provenance for all four inputs.
The emitted packet is strict JSON and cannot exceed 5,000 estimated tokens.

```powershell
python scripts/dispatch_story_packet.py `
  --date 2026-08-28 `
  --carousel-root ..\alaskaaicarousels

python scripts/dispatch_controller.py build-context
```

If any fact-pack file is missing, the builder stops unless it receives one
strict fallback file with at most five candidates, exactly one selected
candidate, source-backed claims, and `broad_searches_used` no greater than ten.
It never performs an unmetered search itself.

## State machine and call accounting

Start from a clean committed canary branch. Initialization records the exact
branch, HEAD, origin, controller config hash, and source-clean snapshot.

```powershell
python scripts/dispatch_controller.py init `
  --run-id 2026-08-29-canary `
  --date 2026-08-29 `
  --cost-budget-usd 10

python scripts/dispatch_controller.py advance `
  --outcome pass `
  --evidence out/dispatch/daily_scope_snapshot.json
```

Then build the story packet and context, and complete `packet_context` with both
canonical paths as evidence. Later phases are:

```text
planning
  -> packet_context
  -> fact_validation
  -> angle
  -> vo_storyboard_episode_props
  -> gates
  -> render_preflight
  -> judges_round_1
       pass -> SHIP
       fail -> repair -> judges_round_2
                              pass -> SHIP
                              fail -> BLOCKED_QUALITY
```

Each transition hash-binds its evidence. The authoring transition requires
exactly `vo_script.txt`, `storyboard.json`, and `episode_props.json`; it counts
the VO words and derives runtime from `total / fps` before render work can
begin. A failed judge transition requires exactly three card files. A passing
transition additionally requires the canonical panel verdict and `SHIP_NOW`,
and reruns the existing `ship_gate.py check`; the controller cannot mint its
own ship decision.

Every paid call uses a two-step reservation:

```powershell
python scripts/dispatch_controller.py reserve-call `
  --role showrunner `
  --estimated-input-tokens 8000 `
  --maximum-output-tokens 3000 `
  --estimated-cost-usd 1.50

python scripts/dispatch_controller.py complete-call `
  --reservation-id <id-from-reserve> `
  --prompt-tokens <provider-usage> `
  --input-tokens <provider-usage> `
  --output-tokens <provider-usage> `
  --cache-read-tokens <provider-usage> `
  --cache-write-tokens <provider-usage> `
  --cost-usd <provider-cost>
```

The reservation checks phase, role, per-call limits, total calls, tokens, and
cost before the model is invoked. `token_telemetry.jsonl` is append-only; a
partial, duplicate, orphaned, or malformed event fails closed. An actual
overage remains recorded honestly and blocks every later reservation.

`export-eval` converts completed events into the strict offline replay schema:
one dated fixture, normal or worst-case scenario, exact frontier/balanced/fast
calls, tool counts, revisions, preserved outputs, and gate outcomes. Frozen
replay evaluation owns the fixture set and fixes its scenarios: August 12 and
August 13 are `normal`; August 28 is `worst_case`. The exporter rejects a
mismatched label rather than making two evaluations incomparable.

## Daily versus weekly scope

`daily_scope_guard.py` denies source changes during a run, including:

- prompts and agent definitions;
- scripts and config;
- shared visual libraries;
- `DispatchDaily.tsx` and `Root.tsx`; and
- any other path outside ignored `out/dispatch/` runtime artifacts.

There is no maintenance flag or bypass. Prompt, agent, controller, gate, and
shared-template improvements belong on a separate weekly maintenance branch,
with normal review and focused tests. The daily controller cannot enter that
mode.

## Focused offline verification

These checks do not render, call a model, search, publish, email, or access a
production service:

```powershell
python -m unittest discover -s scripts -p "test_token_controller.py" -v
python -m py_compile `
  scripts/dispatch_story_packet.py `
  scripts/daily_scope_guard.py `
  scripts/dispatch_controller.py
python -m json.tool config/daily_controller.json > $null
python -m json.tool config/schemas/dispatch_story_packet.schema.json > $null
```
