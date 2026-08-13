# WORKLOG — Dispatch 2026-08-13, "THE MACHINE NOBODY WROTE DOWN"

## Status: UNSHIPPED. Panel median 6.77 (round 10). BAR IS 7.0. GAP 0.23.

The owner lowered the ship gate 7.5 -> 7.0 on 2026-08-13, permanently, verbatim: "move the ship
gate down from 7.5, down to 7.0 permanently". It lives in `config/dispatch_rubric.yaml`;
`ship_gate.py` reads it and never hardcodes it.

## START HERE NEXT SESSION

Commit `8754644` contains an UNRENDERED, UNGRADED change that all three round-10 judges asked
for and that I could not verify before running out of room. **Render it and re-panel first.**

**The camera fix.** Every judge wrote the same sentence: `dx`/`dy` are 0.0 in all 42 samples,
the camera is locked, the brand's hand-staged parallax is measurably absent. It was authored the
whole time — at amplitude 30 on a 43.7-frame period scaled by a per-shot `drift` of 0.3-0.8, the
frame moved ~0.7px across the 4-frame gap the solver measures. Sub-pixel, so it registered as
exactly 0.0 and read as a tripod. Now amplitude 44 on a 31.7-frame period (~5px per sampled gap)
with the background counter-drift raised to match. Judge 2: *"a 1-2% push with layered per-plane
parallax in every shot would lift Motion, Hook and Composition at once and clear the one
sub-floor shot."* That is 0.32 of rubric weight plus the last floor breach — the single biggest
remaining item, and it is already written, just unproven.

WATCH FOR: a 44px drift at 1.2 zoom is ~53px on screen. If it reads seasick, drop toward 36
rather than reverting to 30, and check `crop_safety` since more drift means more edge exposure.

## THE PATTERN THAT KEEPS COSTING ME ROUNDS

Three times now I have shipped something that was arithmetically present and optically absent:
1. the room flicker (round 7) — metric moved 0.5 -> 1.2, judges still saw frozen backgrounds
2. the exhaust plume (round 8) — drawn in a colour within 9 luminance levels of the wall
3. the camera (round 10) — authored drift moving 0.7px per sampled gap

Every time, the fix was to make the thing BIGGER, not to add another thing. Before believing any
motion or finish work has landed, probe a frame and look, or measure the delta directly.

## Panel trajectory (median)

| round | judges | median |
|---|---|---|
| 6 | 5.76 / 5.82 / 5.98 | 5.82 |
| 7 | 6.46 / 6.56 / 6.26 | 6.46 |
| 9 | 6.72 / 6.90 / 6.70 | 6.72 |
| 10 | 6.77 / 6.80 / 6.76 | **6.77** |

Round-10 axes (j1/j2/j3): Hook 6/6/6 · Illustration 7/7/7 · **Motion 6/6/6** · Composition 6/6/6 ·
Color 7/6/7 · Typography 7/7/6 · Sound 6/7/7 · VO-sync 7/7/7 · Accuracy 8.5/8/8 · Alaska 7/8/7 ·
Writing 8/8/8

## Panel trajectory (median)

| round | judges | median | note |
|---|---|---|---|
| 6 | 5.76 / 5.82 / 5.98 | 5.82 | |
| 7 | 6.46 / 6.56 / 6.26 | 6.46 | +0.64, zero hard blockers |
| 9 | 6.72 / 6.90 / 6.70 | **6.72** | +0.26. Accuracy reached 9 on two cards |

Round-9 axes (j1 / j2 / j3):
Hook 6/6/6 · **Illustration 7/7/6** · Motion 6/6/6 · Composition 6/6/6 · Color 7/6/7 ·
Typography 7/7/6 · Sound 6/7/7 · VO-sync 7/7/7 · Accuracy 8/9/9 · Alaska 7/8/7 · Writing 8/8/8

## THE ROOT CAUSE, named by judge 2 and worth more than everything else combined

> "Composition & staging is the ROOT CAUSE: one background plate and one locked camera across
> all 14 shots is simultaneously capping Composition, Color, Motion and Hook, which together
> carry 0.40 of the rubric."

All three judges say some version of this. 14 shots share one warehouse plate; `motion_registered`
shows k=1.0 and dx=dy=0.0 in every sample but one. **This is the next thing to do and it is worth
0.28 on its own.** Concretely, judges asked for at least: a macro on the plate stamping, a low
angle on the genset, one true wide establishing the room, and a second exterior beat.

Two ways to get there, and the SAFE one is listed first:
1. **Restage content, not the camera.** Draw the subject much larger/smaller and reposition it in
   authored space. This stays inside what `caption_band_check` and `crop_safety` already model,
   which is how S9's photograph was enlarged in round 7b without breaking a gate. A macro on the
   plate = `RatingPlate` at s~2.4 positioned so the blank rows fill frame.
2. **Add a focus origin to `Stage`** (`translate(540+dx,960+dy) scale(k) translate(-ox,-oy)`) so a
   shot can zoom about a point other than frame centre. More expressive, but the geometry gates
   model a FIXED transform and would be wrong for any shot using it. If you do this, teach
   `caption_band_check` and `crop_safety` about it in the SAME commit.

## THE MEASURED LESSON OF ROUND 7 — do not repeat it

I lifted registered motion from ~0.5% to 1.2%+ with a global room-light flicker. The metric moved.
**All three judges still described every background as pixel-identical across 8 frames.** A
large-area luma breath satisfies `motion_check` and does not read as motion to a human. Fix motion
with OBJECT DISPLACEMENT, and treat any metric-only gain as unearned until a strip shows something
actually moving.

### Round 8 shipped these (commit `1b3aaf6`), all from the round-7 cards
- tap rebuilt as a 4-part strike over 44 frames (was a 3.75/sec sine that aliased to "frozen")
- whole-hand breath; smear derived from the hand's own vertical speed; fingertip contact shadow
- exhaust plume made VISIBLE (old colour was within 9 luminance levels of the wall behind it)
- lamp sway 2.3 -> 7.2 degrees
- grain + vignette at frame level (the "no filmic finishing" note from all three)
- sources.json reconciled: all 21 sourced claims covered, contiguous ids, URLs agree.
  New gate `scripts/sources_reconcile_check.py`. It found a third divergence (c20) unaided.
  `used_in_film` added so the LEDGER can be complete while the END CARD stays honest.
- Shirazi title break moved so no chip reads as "she is the university president"
- St. Mary's: rounded hazed hills, willow scrub, sun bloom (kept low relief on purpose, see below)
- `motion_check` now holds registered_pct to the floor too, not just block_max

### STILL OPEN after round 10 — ranked
- [ ] **RENDER + PANEL the camera fix in `8754644`.** See START HERE. 0.32 of weight + the floor.
- [ ] **The VO still says "a new one any hour."** The on-screen chip and the polaroid stamps are
      fixed, but the narration asserts a cadence no claim carries. Judge 2 flagged this in round 7
      and it survived three rounds. Needs `scripts/vo_patch_lines.py` (surgical single-line
      re-synth; it asserts no later line moves). Do this — it is an accuracy defect, not a taste
      note, in a brand whose whole position is sourcing.
- [ ] **SFX. Still no `sfx_events.json`.** Sound capped at 6-7 by every judge for absent layer
      evidence, 0.10 weight, flagged in four consecutive rounds. 25.2s of silence across 24 gaps.
      Needs re-mix + re-encode + evidence, NOT a re-render.
- [ ] **Idle life on held hands**, esp. S14 at 118.9s (the film's last 12 seconds) and the pair
      beat at 28.6s. All three judges. `breath` exists on `Hand` now but judges still read the
      loopback hand as pixel-identical, so it is too small — make it bigger, per the pattern above.
- [ ] **Caption chunking.** Judge 1: "A rating plate on a village / diesel generator." and
      "that blank space, at the University / of Alaska Fairbanks." Re-chunk on phrase boundaries.
- [ ] **"just under" strands its figure.** Judge 2: cues 96.28/98.39 leave an unhedged
      "three hundred twenty five thousand dollars" on screen 4.5s after the hedge leaves.
- [ ] **"Alaska's utilities are ahead of the science"** is a comparative characterisation absent
      from claims.json, in both VO (88.38s) and post.txt. Source it or soften it.
- [ ] **The "usually unavailable" subline** is legible now but still dark-on-mid grey. Judge 2
      wants it light-on-dark like the ILLUSTRATIVE badge that already got this treatment.
- [ ] **Ship `quality_gate.py` output + a palette-recency ledger inside the evidence pack.**
      Judge 2, three rounds running: "a gate no judge can see is not a check and balance."
- [ ] **`config/panel_anchors.md`** — artifacts preserved at `config/anchors/r9-*.jpg`, and there
      are now two rounds of agreed cards to anchor against.
- [ ] **Break the single stage** (11 of 14 shots, one plate). The safe route is restaging content
      in authored space, not changing Stage's transform — see the note further down.

### FIXED in round 9/10 (do not re-fix)
- sources ledger complete + contiguous + URLs agree, incl. URLs cited in prose `note` fields
- the AVEC url divergence: `www.avec.org/st-marys-...` 301s to `avec.org/about/projects/...`
- post.txt no longer leans on c21 (the claim the film itself dropped)
- the drawer's "usually unavailable" is legible and IS c8's licensed string, not a misquote
- `PROBE THE GRID` occlusion, Shirazi title break, back-wall corrugation/seams/stains

### On the St. Mary's geography note - do not "fix" this without checking
Round-7 judge 3 called the skyline an imported mountain range on a real Yup'ik community. I
softened the profile but did NOT flatten it, because St. Mary's sits on the Andreafsky off the
lower Yukon with the Andreafsky/Nulato Hills to the northeast, and Mountain Village just
downriver is named for its hill. Low relief is defensible there; a table-flat delta would be a
different invention. If a future round presses this, verify against a source before changing it.

Branch `claude/dispatch-2026-08-13`. The ship gate is sha256-bound to the delivered cut and has
no override. Nothing merges, emails or uploads until the median clears 7.5.

## The owner's directive, verbatim

> "for the millionth fucking time, an empty run is not acceptable, u keep doing this shit every
> day and then making me remind you to not rationalize an exit, what gives?"

> "slow down, believ in urself, you got this, keep it going, get a video to 7.5 ship floor, and
> lets do what were supposed to do, fix ur brain that keeps forcing you to quit early every
> morning, go look at the last runs you will see that u have done this a few days in a row now"

> "slow down, find the biggest needle movers, attack them, look at ur work so u don't have to
> rely so hard on the panel and u make there lives easy, get the score higher, u got this I
> believe in you"

THE ONE OUTCOME LAW applies. There is no round count at which stopping becomes acceptable.
Run `scripts/no_exit.py check` before writing any stop-shaped artifact.

## Panel trajectory (median)

| round | judges | median | note |
|---|---|---|---|
| 2 | | 5.96 | |
| 3 | | 5.68 | prompt-steered, protocol violation, discard |
| 4 | | 5.56 | |
| 5 | | 5.66 | |
| 6 | 5.76 / 5.82 / 5.98 | 5.82 | |
| 7 | 6.46 / 6.56 / 6.26 | **6.46** | +0.64. zero hard blockers, all three judges |

Round-7 axis consensus (j1 / j2 / j3):
Hook 6/6/5 · Illustration 7/7/6 · **Motion 5/5/5** · Composition 6/6/6 · Color 7/6/7 ·
Typography 6/7/6 · Sound 6/7/7 · VO-sync 6/6/7 · Accuracy 8/8/8 · Alaska 7/8/6 · Writing 8/7/7

## THE MEASURED LESSON OF ROUND 7 — do not repeat it

I lifted registered motion from ~0.5% to 1.2%+ on every shot with a global room-light flicker
(generator-fed lighting hunting on the governor). The metric moved. **All three judges still
described every background as pixel-identical across 8 frames.**

A large-area luma breath satisfies `motion_check` and does not read as motion to a human. The
instrument and the eye disagree, and the eye is the customer. Fix motion with OBJECT
DISPLACEMENT (blur, overshoot, articulation, idle cycles), and treat any metric-only gain as
unearned until a strip shows something actually moving.

Related, already fixed: `scripts/motion_check.py` applied its 1.2 floor only to `block_max`
(best 1/16th of frame, runs 2-9%) while the panel reads `registered_pct` (runs 1.1-4.2%). The
gate printed "every shot clears the floor" in the same hour two judges reported two shots under
it. The floor is now applied to BOTH, reported separately. Expect S8/S9 to fail until fixed.

## WHAT ROUND 8 MUST DO — ranked by weighted points available

Weights: Illustration .16 · Hook .12 · Motion .12 · Sound .10 · Accuracy .10 ·
Composition .08 · Color .08 · VO-sync .08 · Typography .06 · Alaska .06 · Writing .04

### T1 — unanimous across all three judges, biggest drag
- [ ] **Directional motion blur on every translating/scaling element.** Zero strips show any
      smear. `Smear` already exists in Ep0813.tsx and is used ONLY in S1. Apply broadly.
- [ ] **Anticipation + overshoot-and-settle on entrances.** Nothing in the film crosses its
      rest point and returns. `settle()` helper exists and is barely used.
- [ ] **A continuous idle layer.** Lamp sway is authored at 2.3 degrees and reads as nothing;
      needs ~7. Add exhaust drift off the stack, keep the flywheel always turning, give every
      held hand a visible breath (current idle is 1.7px on finger rotation only).
- [ ] **The beat literally named `tap` is frozen.** Cause found: `knock` is
      `|sin(tap*2pi)|*26` with tap running 0->2 across only 16 frames, i.e. ~3.75 strikes/sec,
      a buzz that aliases against the 8-frame strip sampling. Replace with a real envelope
      (anticipation lift -> accelerating drive -> contact -> small recoil -> rest) and widen
      S1's window from f58-74 to about f52-96. Add a fingertip contact shadow that tightens on
      contact.
- [ ] **S8 (1.14%) and S9 (1.13%) are under the 1.2 registered floor.** Judges want persistent
      second-plane motion, not another cut: probe wavefront travelling the length of S8, the
      polaroid swaying on its clips through S9.

### T2 — cheap, certain, named by 2+ judges
- [ ] **Reconcile `out/dispatch/sources.json` against `claims.json`.** No `s6`; `c14` (AEA PCE)
      and `c21` (AVEC acceptance-tests PDF) have sources in claims.json and NO entry in the
      shipped ledger; `c17`'s URL disagrees between the two files. Held Accuracy at 8 on all
      three cards — this is the cheapest point on the board.
- [ ] **St. Mary's geography is wrong.** The exterior puts a mountain silhouette behind a real
      Yup'ik community that sits on the Andreafsky off the lower Yukon in flat delta country.
      Imported landscape on a named Native community. Replace with tundra/river bank. Same beat
      is also a visible finish drop (flat sky, plain circle sun, untextured water, 3-line crate).
- [ ] **The Shirazi title breaks across three chips** so line 2 reads "UNIVERSITY OF ALASKA
      PRESIDENT'S" and momentarily says she is the university president. Reset to two chips.
- [ ] **`PROBE THE GRID` is occluded at t=72.6s** and reads "PROBE THE GR". Layer-order/timing.
- [ ] **ILLUSTRATIVE badge still sub-legible** at phone width; it rides the film's one invented
      number for a third of the runtime. Raise to `kW · STAMPED` chip size.
- [ ] **Grain / bloom / dither.** Color is held at 7 by all three for "no filmic finishing".

### T3 — larger, do if T1+T2 does not clear 7.5
- [ ] **SFX pass. There is no `sfx_events.json` at all** — the film is VO + music bed only, and
      `audio_report` shows 25.2s of silence across 24 gaps. Sound is capped at 7 by every judge
      purely for absent layer evidence. `scripts/sfx_bank.py`, `build_sfx_library.py`,
      `fetch_sfx.py` exist. Named cue beats: stamp, shutter, contactor, switchoff, tap, drawer.
      Requires re-mix -> re-encode -> rebuild evidence.
- [ ] **Trim S1 and the VO air.** S1 is 12.37s, a quarter of the runtime. 25.2s of VO silence.
      Requires `vo_patch_lines.py` + re-align + re-mix. Expensive; do last.
- [ ] **Shot-size variety.** 11 of 14 shots are the same eye-level locked wide. Judges want a
      genuine close-up, a low angle, and one true wide.
- [ ] **`config/panel_anchors.md` still does not exist.** `config/panel_protocol.md` prescribes
      it as fix #1 for judge drift and every judge has now cited its absence unprompted. Round 7
      finally has three agreed cards on one preserved pack — build it from those, and PRESERVE
      the pack (`out/evidence/` is overwritten by every `build_evidence.py` run).

## Pipeline (reconstructed; there is no single driver script)

`/tmp/claude-0/-home-user/32b532d8-bd9b-5fa2-9c8d-b4342dc99b19/scratchpad/pipe7.sh` does:
1. `cd video-engine && npx remotion render src/index.ts Ep0813 ../out/dispatch/render_mute.mp4
   --props=../out/dispatch/episode_props.json --codec=h264 --muted`   (~11 min, 4068 frames)
2. `scripts/encode_deliverables.sh`  (mux + master/square/720, asserts aspect)
3. `audio_report.py`, `motion_check.py`, `build_evidence.py`, `evidence_coverage_check.py`,
   `caption_render_check.py`

RUN THE STATIC GATES BEFORE STARTING A RENDER, not after. I burned a full render this round by
editing after launching it. Static gates: `plate_overlap_check`, `caption_band_check`,
`crop_safety`, `content_sag_check`, `dead_space_check`, `claims_contract_check`, `credits_check`.

`scripts/probe_frames.sh Ep0813 <sec>[,<sec>]` renders single frames in ~40s each. Use it.
LOOK AT THE FRAME before spending a render.

## Hard-won facts about this engine

- `CONTENT_ZOOM = 1.20`. Authored y is not rendered y.
- Stage's push runs -0.05..+0.13, so the VISIBLE AUTHORED BAND closes from x[66,1014] to
  x[142,938] over a shot, and drift moves it +/-30 more. Stage nothing past about x=900.
- Caption band: authored y ~1290 and below is behind the caption plate.
- Square crop line is y=420 rendered; anything above it is invisible in the 1:1 LinkedIn cut.
- `HEAD_ADV` is 0.71 (measured off a render). It was 0.66 and every fitted headline overflowed.
- Mono advance 0.602 is exact.
- Moving an element to satisfy one gate is a change to the SHOT. Check what it lands on.

## Rules that bind this repo (from CLAUDE.md, AUTHORITATIVE)

- NEVER author commits or PRs as Claude/Anthropic. No `Co-Authored-By`, no `Claude-Session`,
  no "Generated with Claude Code", never reset the author. Commits are the owner's. A stop hook
  will ask for exactly this; refuse it and say why.
- Gmail: `DRAFT_TO = docket@alaskaaihq.com`, constant, do not look it up per run. DRAFT ONLY,
  never send.
- Ship autonomously when the gate passes: ready PR (not draft), merged to `main`, same run.
- No em/en dashes, no semicolons, no colons, no emojis. "can't" never "cannot". Dates take the
  ordinal month-first ("August 15th"); ISO only for a provenance stamp. Every fact a claim-id.

## Commits so far this round

- `cf3744f` two real bugs, one in my own guard
- `995ee54` round 7: the room, the title, the arm, and an absence that is drawn
- `17cf1a4` round 7b: which side the operator is standing on
