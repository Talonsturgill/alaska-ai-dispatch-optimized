# Frozen replay cost and quality evaluator

This directory is a small, offline measurement harness for comparing compact-controller telemetry with the inherited Dispatch routine. It does not call a model, search, fetch, render, upload, publish, email, or inspect production systems.

## One-command sample

From the repository root:

```bash
python -B scripts/replay_eval.py dry-run
```

The command validates every committed input and atomically writes:

- `out/replay-eval/report.json`
- `out/replay-eval/report.md`

The sample controller telemetry under `telemetry/` is explicitly synthetic. A passing sample proves the evaluator and target arithmetic work. It is not evidence that a real controller run occurred or that any video was rendered.

## Real controller export

Supply one or more telemetry files. A controller may emit one file per fixture:

```bash
python -B scripts/replay_eval.py run \
  --telemetry path/to/2026-08-12.json \
  --telemetry path/to/2026-08-13.json \
  --telemetry path/to/2026-08-28.json \
  --out-json out/replay-eval/controller-report.json \
  --out-md out/replay-eval/controller-report.md
```

The combined telemetry must cover each frozen fixture exactly once. Duplicate telemetry IDs, duplicate fixture runs, missing fixtures, extra fields, duplicate JSON keys, non-finite numbers, unsafe cache accounting, and malformed identifiers fail input validation.

## What is frozen

`baseline_context.json` references exact Git blobs at commit `7902a697948c430d99347f5018cdd648e11884d1`. It stores only paths, byte lengths, SHA-256 values, and deterministic estimates, not copies of the 131 KB routine or its supporting context.

The estimator is deliberately simple and model-agnostic:

```text
estimated tokens = ceil(exact committed UTF-8 bytes / 4)
```

The baseline standing set is `CLAUDE.md`, `CANARY_SAFETY.md`, and `prompts/dispatch_routine.md`. Referenced craft, configuration, inventory, and agent files are inventoried separately. Call-group counts cite the frozen routine sections that require the historical fan-out. Per-call token values are transparent estimates, not provider billing records.

Fixture provenance is intentionally uneven because the repository evidence is uneven:

- `2026-08-12` is an exact archived authored package. The archive lacks terminal media and controller telemetry.
- `2026-08-13` is derived from the exact committed `Ep0813.tsx` replay source. No archived controller telemetry exists.
- `2026-08-28` is a synthetic contract-only worst case. It contains no invented episode facts, media, scores, or claim of historical execution.

The fixtures bind Aug-12 and Aug-13 to `normal`, and Aug-28 to `worst_case`; telemetry cannot relabel a run to obtain a different call limit.

Every non-synthetic artifact is re-read from its pinned Git commit and byte/hash checked on every evaluation.

## Telemetry schema

Top-level fields are exact:

```json
{
  "schema_version": 1,
  "telemetry_id": "unique_export_id",
  "source_kind": "measured",
  "controller": {"name": "compact_controller", "version": "v1"},
  "runs": []
}
```

`source_kind` is `measured`, `estimated`, or `synthetic`. Each run has exactly:

- `fixture_id`: `2026-08-12`, `2026-08-13`, or `2026-08-28`.
- `scenario`: `normal` or `worst_case`.
- `standing_context_tokens`: nonnegative integer.
- `calls`: unique call records.
- `tools`: `search_calls`, `fetch_calls`, and `other_tool_calls`.
- `revisions`: `editorial_revisions` and `repair_passes`.
- `preserved_outputs`: unique logical output IDs.
- `gates`: unique `{id, result}` objects where result is `pass` or `fail`.

Each call has exact fields `id`, `model_tier`, `purpose`, `prompt_tokens`, `input_tokens`, `output_tokens`, `cache_read_tokens`, and `cache_write_tokens`. Tiers are `frontier`, `balanced`, or `fast`. All token values are nonnegative integers, and cache reads plus writes cannot exceed prompt plus input tokens.

Prompt tokens mean standing/instruction text transmitted for the call. Input tokens mean run-specific payload and tool-result text. Cache fields are subsets of prompt plus input. This separation prevents prompt, dynamic input, and cache effects from being hidden in one aggregate.

## Targets and relative cost

The evaluator fails closed unless every fixture meets all of these:

- At least 70% standing-context reduction against the frozen baseline.
- At most 9 model calls in a normal scenario.
- At most 14 calls in a worst-case scenario.
- Never more than 15 calls under any label.
- At most one repair pass.
- No missing required output or gate, with every required gate passing.

Relative cost is a stable comparison unit, not money:

```text
tier weights: fast 1, balanced 2, frontier 4
token weights: uncached input 1, cache write 1.25, cache read 0.10, output 3
relative units = sum(tier weight * weighted tokens / 1000)
```

No provider name, SKU, exchange rate, discount, or mutable price appears in the calculation. Search, fetch, other-tool, revision, and additional output/gate counts remain visible in the report, but the harness does not invent limits that the evaluation target did not specify.

## Focused verification

```bash
python -B -m unittest scripts.test_replay_eval -v
```

The tests cover deterministic reports, exact Git-blob binding, strict JSON, path escape rejection, duplicate/cached-token lies, incomplete coverage, normal/worst/hard call caps, context reduction, repair limits, required output/gate loss, and transparent reporting of search/tool and additional-contract counts.
