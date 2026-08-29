# Dispatch correctness foundation

This canary treats run identity and distribution bytes as closed contracts. A
filename, modification time, or successful render process is not proof that an
artifact belongs to the current run.

## Current composition limitation

`DispatchDaily` is the sole active, case-sensitive ASCII composition ID. In
this B1 foundation it is explicitly a **2026-08-13 replay/correctness fixture**,
not a generic daily story template. `video-engine/src/DispatchDaily.tsx` wraps
the frozen `Ep0813` film and accepts only timing/caption props plus its fixed
fixture ID. Historical films remain available only under explicit legacy IDs.

Do not evaluate this branch as though changing props can author a new story.
A genuinely parametric story-bearing daily template is later work. This phase
establishes the identity and artifact invariants that template must obey.

## Run identity

Start from a committed canary branch with an unchanged engine source tree:

```bash
python scripts/run_guard.py init \
  --run-id 2026-08-29-canary \
  --composition DispatchDaily

# Write the current run's episode_props.json, then bind it exactly once.
python scripts/run_guard.py bind-inputs
python scripts/run_guard.py require-composition --composition DispatchDaily
```

The atomic schema-v2 stamp records the run ID/date, composition, canary mode,
repository and canonical origin, canonical worktree root, branch, full Git
HEAD, registry and Root hashes, active wrapper and dependency hashes, the
complete TS/TSX source-tree hash, and the registered props path/hash. Existing
scratch props are intentionally not trusted at `init`; `bind-inputs` is the
explicit provenance boundary.

Any worktree, branch, HEAD, origin, registry, Root, source-tree, dependency,
props-path, or props-byte drift invalidates the run. JSON duplicate keys,
non-object stamps, non-finite numbers, non-canonical paths, copied stamps, and
case or Unicode substitutions fail concisely.

## Distribution bytes

`config/deliverables.json` defines exactly five shipped roles:

| Role | Canonical path | Dimensions | Streams |
|---|---|---:|---:|
| `vertical_hosted` | `out/dispatch/dispatch_master_hosted.mp4` | 1080x1920 | 1 video, 1 audio |
| `square` | `out/dispatch/dispatch_square.mp4` | 1080x1080 | 1 video, 1 audio |
| `mobile` | `out/dispatch/dispatch_master_720.mp4` | 720x1280 | 1 video, 1 audio |
| `poster_square` | `out/dispatch/poster.png` | 1080x1080 | 1 image stream |
| `poster_thumb_vertical` | `out/dispatch/poster_thumb_vertical.jpg` | 540x960 | 1 image stream |

`dispatch_mastering_source.mp4` is an explicitly non-shipped internal muxing
source. `dispatch_master.mp4`, every 4:5/1080x1350 output, the old square thumb,
and `dispatch_loop.sh` are retired and fail closed.

After encoding, `scripts/deliverable_contract.py build` writes an atomic
manifest. Every later check re-probes dimensions, duration, stream counts and
recomputes byte count and SHA-256 for all five artifacts. Paths must be unique,
ASCII, repository-relative POSIX paths with no symlink escape. Same-size and
mtime-preserving mutations therefore fail.

The uploader accepts only one manifested role, downloads the published object
back in full, and records a publication receipt only when the remote byte count
and SHA-256 equal the local artifact. Feed and preview consumers require those
exact receipts. The canary safety policy still blocks production feed/email
delivery.

## Panel and SFX binding

The ship verdict stores five artifact hashes, immutable manifest digest, media
and audio facts, evidence hashes, and SFX facts in separate fields. Evidence
images and JSON reports are hashed. The root SFX sidecar is strict JSON, must
postdate the audio master, validates every event, and carries the exact
`master.wav` byte count and SHA-256. A post-panel mutation to any deliverable,
evidence file, SFX sidecar, or bound audio master invalidates the verdict.

## Safe validation

These checks use temporary repositories, mock media facts, and one tiny local
ffmpeg fixture. They do not call models, networks, publishers, or production:

```bash
python -m unittest discover -s scripts -p "test_*.py" -v
python -m compileall -q scripts
python scripts/canary_guard.py self-test
python -m json.tool config/compositions.json
python -m json.tool config/deliverables.json
```
