# Parametric DispatchDaily video contract

`DispatchDaily` is one fixed 1080x1920, 30 fps Remotion composition. A daily
run changes `out/dispatch/episode_props.json`; it does not author or patch TSX.
The exact structural contract is `config/episode_props.schema.json`, and the
runtime source of truth is the strict Zod parser in
`video-engine/src/DispatchDailySchema.ts`.

## What props control

- episode identity, date, provenance label, palette, and reduced-motion mode;
- a contiguous 112–130 second frame timeline, including 12–15 seconds of credits;
- six to sixteen scenes selected from fixed deterministic primitives;
- captions, word timings, semantic symbol assets, source bindings, and credits.

All objects reject unknown fields. The runtime also rejects duplicate IDs,
timeline gaps or overlaps, references to undeclared sources/assets, captions or
word timings that enter the credits, historical scenes without sources, and
synthetic canaries carrying source bindings. `calculateMetadata` parses the same
props before it accepts their duration, and the component parses again before
drawing a frame.

## Crop and accessibility contract

The master is always 1080x1920. Story action lives between x=72..1008 and the
centered 1:1 safe box y=420..1500. Captions occupy y=1328..1484, remain inside
the square crop, use two high-contrast rows at most, and are exposed as an ARIA
label. The existing delivery path may therefore derive 1080x1080 square and
720x1280 mobile cuts without changing the composition. Reduced motion is a
declared deterministic prop, never a host-dependent media query.

## Frozen fixtures

- `dispatch-2026-08-12.json` is a source-bound reconstruction from the archived
  August 12 run. It is not the published cut.
- `dispatch-2026-08-13.json` is a source-bound reconstruction from the checked-in
  August 13 records. It is not the published cut.
- `dispatch-2026-08-28.json` is explicitly synthetic because no authored episode
  record for that date is present here. It contains no factual source bindings.

All three load during composition discovery, so a malformed frozen fixture
breaks the smoke test rather than silently drifting.

## Bounded verification

From `video-engine/`:

```bash
npm run typecheck
npm run compositions
```

`npm run smoke:parametric` runs both commands. Composition discovery validates
the imported fixtures and resolves `DispatchDaily` as a 1080x1920, 30 fps,
3,600-frame composition. It does not render or publish a video.
