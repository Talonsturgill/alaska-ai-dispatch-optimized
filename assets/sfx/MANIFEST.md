# SFX bank — designed foley with variants (scripts/build_sfx_library.py)

Deterministic numpy sound design (crc32-seeded), 44.1k/16-bit stereo, -6 dBFS
peaks. Each kind ships SIX sibling takes (`<kind>_v1..v6.wav`) sampled from a
param family — scripts/sfx_bank.py shuffle-bags them (no-repeat-last-2) so no
two plays of a kind in an episode (or across weeks) are the same take.
Layering: transient + body + Schroeder room tail (+ sweetener). Metal is modal
(f_n = n*f0*sqrt(1+B*n^2)); paper is granular; snap is Karplus-Strong.
License: original synthesis, no third-party material.

To UPGRADE any kind with real recordings: put curated CC0/public-domain takes
at `assets/sfx/real/<kind>*.wav` (e.g. clank_a.wav, clank_b.wav) and log source
+ license here. sfx_bank.py then shuffle-bags the real takes for that kind
instead of the synth ones, automatically.

- `thud_v1..v6.wav` — 0.69-0.74s — designed synth — no attribution needed
- `stamp_v1..v6.wav` — 0.74-0.82s — designed synth — no attribution needed
- `boom_v1..v6.wav` — 2.06-2.25s — designed synth — no attribution needed
- `pop_v1..v6.wav` — 0.09-0.09s — designed synth — no attribution needed
- `snap_v1..v6.wav` — 0.58-0.58s — designed synth — no attribution needed
- `tick_v1..v6.wav` — 0.24-0.24s — designed synth — no attribution needed
- `ding_v1..v6.wav` — 1.10-1.10s — designed synth — no attribution needed
- `chime_v1..v6.wav` — 2.17-2.17s — designed synth — no attribution needed
- `clank_v1..v6.wav` — 1.35-1.35s — designed synth — no attribution needed
- `chain_v1..v6.wav` — 1.05-1.06s — designed synth — no attribution needed
- `whoosh_v1..v6.wav` — 0.85-0.96s — designed synth — no attribution needed
- `riser_v1..v6.wav` — 0.92-1.05s — designed synth — no attribution needed
- `creak_v1..v6.wav` — 0.82-0.82s — designed synth — no attribution needed
- `paper_v1..v6.wav` — 0.69-0.79s — designed synth — no attribution needed
- `paw_v1..v6.wav` — 0.34-0.34s — designed synth — no attribution needed
- `klaxon_v1..v6.wav` — 0.50-0.50s — designed synth — no attribution needed
- `caw_v1..v6.wav` — 1.08-1.15s — designed synth — no attribution needed

## Real recordings (assets/sfx/real/ — win over synth, per kind)

30 file(s), regenerated from real/manifest.json, which carries the
source URL, pack, sha256 and retrieval date for each one.

Licence: CC0-1.0. Author: Kenney (kenney.nl).
CC0 requires no attribution; credit is given anyway. Committing CC0 material
here is clean.

- `chime_*` — 4 take(s) — interface-sounds
- `clank_*` — 6 take(s) — impact-sounds
- `ding_*` — 5 take(s) — impact-sounds
- `paw_*` — 5 take(s) — impact-sounds
- `pop_*` — 4 take(s) — interface-sounds
- `thud_*` — 6 take(s) — impact-sounds

Do NOT add Sonniss/Pixabay/Mixkit files here (commercial use OK, but
redistribution, which is what committing is, is prohibited). BBC RemArc is
non-commercial: never use it. CC0-only in this directory.
