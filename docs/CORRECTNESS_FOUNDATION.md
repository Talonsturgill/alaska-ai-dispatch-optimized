# Dispatch correctness foundation

This canary treats identity, timing, review evidence, and distribution bytes as
closed contracts. A familiar filename, a modification time, or a successful
process is never proof that an artifact belongs to the current run.

## Current composition limitation

`DispatchDaily` is the sole active, case-sensitive ASCII composition ID. In
B1 it is explicitly a **2026-08-13 replay/correctness fixture**, not a generic
daily story template. `video-engine/src/DispatchDaily.tsx` wraps the frozen
`Ep0813` film. Historical films remain available only under explicit legacy
IDs. Changing props can change timing and captions, but cannot author a new
story. A genuinely parametric story-bearing template is deferred work.

## Supported runtime

The Python contracts and tests are cross-platform. The production media shell
pipeline is supported on Linux or WSL because it deliberately uses Bash,
`flock`, `mktemp`, GNU `stat`, `sha256sum`, FFmpeg, and FFprobe. Do not
interpret a PowerShell parse or a partial Git Bash run as validation of those
scripts. Use Linux/WSL for render, mix, encode, evidence, and media checks.

## Supported order and run identity

From a clean, committed canary branch:

```bash
python3 scripts/run_guard.py init \
  --run-id 2026-08-29-canary \
  --composition DispatchDaily

# Produce out/dispatch/episode_props.json for this run, then bind it once.
python3 scripts/run_guard.py bind-inputs
python3 scripts/run_guard.py require-composition --composition DispatchDaily

# Choose exactly one final-render entry point. All write the same canonical file.
bash scripts/render.sh final DispatchDaily
# or: bash scripts/render_parallel.sh DispatchDaily
# or: npm --prefix video-engine run render

python3 scripts/render_contract.py check
python3 scripts/dispatch_mix.py
bash scripts/encode_deliverables.sh
python3 scripts/build_evidence.py
python3 scripts/ship_gate.py record --judges 8.5,8.7,8.9 --notes "panel notes"
python3 scripts/ship_gate.py check
```

The atomic schema-v3 run stamp records run ID/date, exact composition, canary
mode and repository, canonical origin/worktree, branch, full stamped Git HEAD,
registry and Root hashes, active source/dependency hashes, the complete TS/TSX
engine hash, render-input hashes, and the registered props path/hash. Existing
scratch props are unbound at `init`; `bind-inputs` is the explicit boundary.

The current HEAD may equal the stamped HEAD or be its descendant. Descendant
artifact/receipt commits are safe only while every bound registry, Root,
source, dependency, engine, render input, and props hash remains identical.
Unrelated ancestry is rejected. This resolves the post-stamp artifact-commit
deadlock without trusting mtime. Copied stamps, branch/worktree/origin drift,
case or Unicode composition substitutions, duplicate-key/non-object JSON,
symlink escapes, and changed bound inputs fail concisely.

## Exact duration and canonical render

`episode_props.json#total/fps` is the only duration authority. `total`
includes the credits tail and must equal story frames plus credits frames.
The mix, SFX sidecar, mute render receipt, manifest, and all three delivered
videos carry that same duration. A mismatch greater than one frame plus probe
rounding fails.

There is one final mute render:
`out/dispatch/render/video_mute.mp4`. Every final entry point runs
`render_contract.py prepare` before Remotion and `record` after it.
Preparation validates identity, rejects retired alternate paths, and removes
only the canonical old output and receipt, so a failed render cannot expose an
older valid file. The receipt binds run/composition, full stamp digest, stamped
HEAD, props path/hash, exact episode facts, media facts, bytes, and SHA-256.

## Distribution bytes

`config/deliverables.json` defines exactly five shipped roles:

| Role | Canonical path | Dimensions | Streams |
|---|---|---:|---:|
| `vertical_hosted` | `out/dispatch/dispatch_master_hosted.mp4` | 1080x1920 | 1 video, 1 audio |
| `square` | `out/dispatch/dispatch_square.mp4` | 1080x1080 | 1 video, 1 audio |
| `mobile` | `out/dispatch/dispatch_master_720.mp4` | 720x1280 | 1 video, 1 audio |
| `poster_square` | `out/dispatch/poster.png` | 1080x1080 | 1 image stream |
| `poster_thumb_vertical` | `out/dispatch/poster_thumb_vertical.jpg` | 540x960 | 1 image stream |

`dispatch_mastering_source.mp4` is an explicitly non-shipped muxing source.
`dispatch_master.mp4`, 4:5/1080x1350 output, the old square thumb, old mute
paths, and `dispatch_loop.sh` are retired and hard-fail.

The manifest re-probes dimensions, exact credits-inclusive duration, codecs and
stream counts, and recomputes byte count and SHA-256 for all five files. Paths
must be unique ASCII repository-relative POSIX paths with no drive, UNC,
backslash, traversal, collision, or symlink escape. Same-size,
mtime-preserving mutations therefore fail.

## Evidence, panel, and release policy

`build_evidence.py` writes an evidence manifest bound to the exact
`vertical_hosted` bytes and immutable delivery-manifest digest. It records its
generator path/version/source hash/parameters and the bytes/SHA-256 of every
review image and JSON report. Adding, deleting, or changing evidence invalidates
the verdict.

The root SFX sidecar binds current run/composition, exact episode duration,
every event, and exact `master.wav` bytes. Events must be a canonical list,
have finite nonnegative in-duration times and lowercase ASCII kinds, and the
sidecar must postdate its audio master.

`ship_gate.py record` accepts exactly three finite scores in 0..10 and computes
the median internally. There is no supplied-median argument. The verdict binds
the current rubric bytes/hash/threshold, an active owner release only when its
run ID and date exactly match, five artifacts, delivery digest/media facts,
evidence manifest, SFX/audio, and fail-closed blankness attestation. Blankness
requires successful FFprobe and exactly the requested number of successfully
decoded samples. Any decode/dependency/non-finite failure blocks concisely.

## Immutable publication and terminal previews

Published object names include role, run ID, and the complete artifact SHA-256.
Publication receipts bind role/run/composition, delivery digest, artifact
path/bytes/hash, media commit SHA, and the exact commit-SHA raw GitHub URL.
Receipt reuse with different media or cross-role name/URL collisions is
rejected. Consumers fetch the complete remote object and recompute bytes/hash;
a HEAD response or mutable branch URL is insufficient.

The uploader, feed publisher, terminal email preview, and no-exit check require
a fully validated current-run ship verdict. The final local preview must be
`out/dispatch/dispatch-preview.html` and has its own verdict/manifest/
publication-bound receipt. `--pre-panel-preview` is visibly labeled
**PRE-PANEL / NOT TERMINAL** and is forbidden from that canonical path.
`--date` may only equal the stamp's `date`; the wall clock never chooses the
run date.

## Safe verification

These commands do not render, call models, use paid services, publish, email, or
contact production.

Linux/WSL:

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' -v
python3 -m compileall -q scripts
python3 scripts/canary_guard.py self-test
python3 -m json.tool config/compositions.json >/dev/null
python3 -m json.tool config/deliverables.json >/dev/null
./video-engine/node_modules/.bin/tsc --noEmit -p video-engine/tsconfig.json
npm --prefix video-engine exec -- remotion compositions video-engine/src/index.ts
```

Windows PowerShell (contract/static verification only):

```powershell
python -m unittest discover -s scripts -p "test_*.py" -v
python -m compileall -q scripts
python scripts/canary_guard.py self-test
python -m json.tool config/compositions.json > $null
python -m json.tool config/deliverables.json > $null
.\video-engine\node_modules\.bin\tsc.cmd --noEmit -p video-engine\tsconfig.json
npm --prefix video-engine exec -- remotion compositions video-engine/src/index.ts
```

The real-media regression discovers FFmpeg with `shutil.which`; it skips with
an explicit reason when FFmpeg/FFprobe are not on the test process's PATH.
