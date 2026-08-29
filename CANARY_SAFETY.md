# Alaska AI Dispatch optimization canary

> **CANARY REPOSITORY — PRODUCTION SIDE EFFECTS ARE OFF BY DEFAULT**

This repository is the isolated test bed for the token-optimized Alaska AI
Dispatch routine. It is intentionally separate from the production
`Talonsturgill/alaska-ai-weekly` repository.

The normal canary run may:

- read public sources;
- write local files under this checkout;
- commit and push source or generated test artifacts to
  `Talonsturgill/alaska-ai-dispatch-optimized`; and
- publish test media only to a branch of this canary repository.

The normal canary run must not:

- push to `Talonsturgill/alaska-ai-weekly`;
- clone, edit, push, or merge `Talonsturgill/alaskaaicarousels`;
- update `alaskaaihq.com` or its video feed;
- create or send Gmail messages or drafts;
- upload to rclone, R2, Drive, S3, tmpfiles.org, or another external host;
- post to LinkedIn, TikTok, Facebook, or another social service; or
- mutate secrets, routine settings, schedules, databases, or Cloudflare.

## Safety layers

1. `origin` must resolve to the canary repository. The historical source remote
   is fetch-only and has a deliberately invalid push URL.
2. `config/execution_policy.json` is committed in `canary` mode.
3. `scripts/canary_guard.py` permits local work and canary-repository pushes,
   but blocks production publishing, Gmail, and other external uploads.
4. `.claude/settings.json` and `.claude/settings.local.json` deny the Gmail MCP.
5. The highest-precedence banner in `CLAUDE.md` and
   `prompts/dispatch_routine.md` overrides their inherited production-era
   delivery instructions.
6. The canary safety workflow exercises the policy on every push and pull
   request.

Check the boundary before a run:

```bash
python scripts/canary_guard.py status
python scripts/canary_guard.py self-test
python -m unittest scripts/test_canary_guard.py
```

The expected status is `mode=canary`, `production_opt_in=false`, and
`origin=Talonsturgill/alaska-ai-dispatch-optimized`.

## Local email preview

The Dispatch email builders may still render an HTML preview for inspection,
but they will not emit a connector-ready Gmail payload in canary mode:

```bash
python scripts/dispatch_email.py ... \
  --local-only --out-html out/dispatch/email-preview.html
```

The historical weekly builder follows the same `--local-only --out-html`
contract. `scripts/record_draft.py` is blocked because a receipt is supposed to
attest that Gmail accepted a real draft.

## Deliberate production override

There is no command-line bypass. The guard recognizes a two-part environment
latch only so an owner-authorized recovery can be audited without editing out
the safety code. **A routine or agent must never set either variable on its own.**
Both may be set only when the owner explicitly authorizes production side
effects for that exact run in the current conversation.

The variable names and acknowledgement value are recorded in
`config/execution_policy.json`; `status` reports only whether the complete latch
is active, never secret values. Delete the variables immediately after the
authorized run. Creating this canary repository is not authorization to use the
latch.

## If a guard blocks

Treat the block as the correct canary result. Do not rename a production action,
edit the policy, set the latch, switch remotes, use a connector directly, or find
an alternate upload host. Keep the output local or publish it to this canary
repository and report the blocked production step plainly.
