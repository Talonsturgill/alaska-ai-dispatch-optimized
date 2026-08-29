# Canary limitations after Phase C acceptance

This repository remains an isolated, non-production correctness/replay canary.
Phase C's parametric `DispatchDaily`, compact daily controller, and offline
replay evaluator are implemented and accepted here. No paid live model run,
full 120-second render, or publication has occurred.

The following known sixth-pass findings are deliberately deferred so this
checkpoint can support the token-optimization experiment without another broad
architecture rewrite:

- Terminal judge cards are strict, current-byte, rubric-derived, capability-
  checked records, but they are not yet runtime-attested scorer executions.
  `ship_gate.py` still accepts three validated card paths. A future
  `panel_runner` must capture three distinct runtime-issued invocation IDs,
  immutable challenges/context, model/session metadata, raw response hashes,
  and card hashes, and the ship gate must accept only that runner receipt. Until
  then, the card contract prevents accidental schema/math/evidence drift but is
  not cryptographic or malicious-host proof against hand-authored cards.
- `panel_ledger.py` keys rounds by round number and judge ID rather than the full
  current run identity. Do not reuse a prior run's ledger; remove the run-scoped
  output before a new canary replay. Run-bound panel receipts remain deferred
  with the panel runner.
- `.github/workflows/canary-safety.yml` still runs the narrow canary policy
  tests. The expanded correctness/static/TypeScript/Remotion/real-FFmpeg CI
  matrix is deferred. Run those checks locally before treating a later branch
  as review-ready.
- `docs/LAUNCH.md` and `docs/ROUTINE_SPEC.md` are inherited production-era
  documents and are not executable in this canary. Do not follow their Gmail,
  rclone, production-repository, schedule, or delivery instructions. The sole
  active contract is `prompts/dispatch_routine.md` under `CANARY_SAFETY.md`.
- `config/panel_protocol.md` still contains historical panel-anchor discussion;
  there is no `config/panel_anchors.md` in B1. No judge may claim such anchors
  were supplied.

Implemented in this checkpoint: stronger lossy-AAC-tolerant waveform/spectral/
cepstral identity with exact copied AAC packet identity and decode-time hash
stability; exact shared credit-label derivation; expanded preflight binding for
engine/package/compiler/prompts/agents; evidence-capability-aware video axes;
and fail-closed retirement of the obsolete autonomous repair agent.
