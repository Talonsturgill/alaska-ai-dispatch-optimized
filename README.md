# Alaska AI Dispatch optimization canary

This public repository is an isolated, token-optimization test bed seeded from
the Alaska AI Dispatch production history. It exists to compare output quality
and cost without touching the live Alaska AI HQ publication pipeline.

Production delivery is not merely off by default; it is unavailable from this
repository. There is no runtime opt-in or environment override. Normal runs may
write local artifacts and push source or test media only to
`Talonsturgill/alaska-ai-dispatch-optimized`.

Read [CANARY_SAFETY.md](CANARY_SAFETY.md) before running anything.

## Safe start

```bash
python scripts/canary_guard.py status
python scripts/canary_guard.py self-test
python -m unittest discover -s scripts -p "test_canary_*.py" -v
bash scripts/setup_env.sh
```

The guard verifies that `origin` has one canonical github.com fetch URL, no
configured `pushurl`, one identical push URL, and the exact canary repository.
The setup script deliberately installs no post-commit or automatic-push hook.

## Canary outputs

- Rendered artifacts stay under `out/` unless deliberately committed.
- `scripts/upload_video.py` can publish test media only to this repository's
  `dispatch-media` branch. It has no external-host fallback.
- `scripts/dispatch_email.py --pre-panel-preview --local-only --out-html <nonterminal-path>`
  creates a visibly non-terminal review preview. The canonical
  `out/dispatch/dispatch-preview.html` path is reserved for a fully validated,
  verdict-bound delivery preview.
- `scripts/publish_feed.py`, Gmail receipts, Gmail and GitHub connectors,
  production repositories, the live site feed, social publishing, Cloudflare,
  databases, schedules, and secrets are blocked.

## Sources of truth

- `config/execution_policy.json` defines the complete action policy.
- `config/compositions.json` defines the one active composition identity.
- `config/deliverables.json` defines the five-file distribution contract.
- `scripts/canary_guard.py` enforces it.
- `prompts/dispatch_routine.md` currently governs only the frozen B1
  replay/correctness fixture. Fresh-story daily generation remains Phase C.
- `video-engine/` contains the Remotion engine.
- `CANARY_SAFETY.md` documents the boundary and failure behavior.
- `docs/CORRECTNESS_FOUNDATION.md` documents run identity, manifested bytes,
  and the strict, reusable `DispatchDaily` parametric composition.

Production deployment must be reviewed and implemented separately in the
production repositories. Do not weaken this lab to turn a canary into a release.

The Bash/FFmpeg media pipeline is supported on Linux or WSL. Cross-platform
Python contract tests and Windows-safe verification commands are documented in
`docs/CORRECTNESS_FOUNDATION.md`.
