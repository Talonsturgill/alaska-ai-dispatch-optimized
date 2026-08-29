# Alaska AI Dispatch optimization canary

> **CANARY REPOSITORY — PRODUCTION SIDE EFFECTS ARE PERMANENTLY UNAVAILABLE**

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

1. `origin` must have one canonical github.com fetch URL, no configured
   `pushurl`, and one identical push URL resolving to the canary repository.
   No production remote is retained in the checkout.
2. `config/execution_policy.json` is committed in `canary` mode.
3. `scripts/canary_guard.py` permits local work and canary-repository pushes,
   but blocks production publishing, Gmail, and other external uploads.
4. `.claude/settings.json` and `.claude/settings.local.json` deny both Gmail and
   GitHub MCP connectors; repository writes use the validated canary origin.
5. The highest-precedence banner in `CLAUDE.md` and
   `prompts/dispatch_routine.md` overrides their inherited production-era
   delivery instructions.
6. The canary safety workflow exercises the policy on every push and pull
   request.

Check the boundary before a run:

```bash
python scripts/canary_guard.py status
python scripts/canary_guard.py self-test
python -m unittest discover -s scripts -p "test_canary_*.py" -v
```

The expected status is `mode=canary`, `production_override=none`, and
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

## No production override

There is no command-line bypass, environment latch, secret, alternate remote,
or arbitrary action route. Owner approval for a future production release means
reviewing and deliberately porting approved changes into the production
repository. It does not mean weakening this lab's policy at runtime.

## If a guard blocks

Treat the block as the correct canary result. Do not rename a production action,
edit the policy, switch remotes, use a connector directly, or find
an alternate upload host. Keep the output local or publish it to this canary
repository and report the blocked production step plainly.
