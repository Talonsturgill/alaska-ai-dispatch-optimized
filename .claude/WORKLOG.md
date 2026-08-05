# WORKLOG — THE TWO-MINUTE UPGRADE (90s → 120s Dispatch)

**READ THIS FIRST if you are resuming with no memory of the task.** This file is the
durable plan and progress ledger, written to survive context compaction. The design
rationale lives in `docs/craft/TWO_MINUTE_UPGRADE.md` (the plan of record); this file
is the *state*: what is done, what is next, what was measured, and what must not break.

Branch: `tsturg/sweet-cray-rg1lsr`, based on `origin/main` at `de0a126`.
Started 2026-08-05. Delete this file when every task below is DONE and shipped.

---

## 1. The owner's directive, verbatim (2026-08-05, voice)

> "this last video that you output was probably your best one yet, and it did a good job
> of proving that you're able to go longer while holding engagement. So we wanna go ahead
> and have you first, uh, plan out properly, and then go ahead and execute the following.
> You're gonna now upgrade the videos from around ninety seconds to around two minutes,
> and your task is to make sure that we follow all the same constructs, everything,
> basically. Nothing changes except for the length of the video, but we gotta make sure
> that we hold engagement. All the same rules apply. We don't break anything in the
> automation or the repo or the website or anything. You know, we're careful. But most
> important thing is in going from ninety seconds to two minutes, we must make sure that
> we hold engagement. So you gotta remember, this all starts with the preplanning. Those
> guys in the beginning, they gotta be talking to each other and saying, you know, what
> are we gonna do for two minutes to hold engagement? How are we gonna plan out, you know,
> like a storyboard and a video that lasts two minutes, and we gotta be thinking about
> that from the get go. And, you know, same thing with the quality gate. I don't know. I
> don't think you really have to update the quality gates. Those can probably stay the
> same. Um, you know better than me, so you do what you think is best. But get me to the
> outcome with a two minute video that's ultimately very engaging and awesome. You don't
> have to redo the old video that we did. We just wanna make these upgrades now so that on
> tomorrow's run, we can see our first two minute video. But you... just make sure that
> you go slow. This is a massive task and massive upgrade that I don't want you to mess
> up."

Follow-up (2026-08-05): *"and make sure ur plan fully survives compaction of this chat
that is inevitable"* — hence this file.

### What that translates to as hard constraints

1. **Length is the ONLY thing that changes.** Voice, visual system, delivery path,
   aspects, encodes, feed, email, writing rules: untouched.
2. **Engagement is the acceptance criterion**, not runtime. A 120s film that sags is a
   failure even if it measures 120.0s.
3. **Retention is designed in PRE-PLANNING**, not patched later. The angle room, the
   directors room, and the Gate-0 critics must be arguing about the two-minute retention
   problem *before* a frame exists. The owner named this specifically and it is the part
   most likely to be skipped under time pressure.
4. **Quality gates / rubric stay as they are.** The owner deferred to my judgment and I
   agree with his instinct: `dispatch_rubric.yaml` grades craft, not length. Changing the
   bar at the same time as the format would make a score move unattributable.
5. **Break nothing.** The website, the videos feed, the routine, the archive, older
   boards. Every gate must still pass the shipped 2026-08-05 board.
6. **Go slow. Verify empirically, do not reason.** The TTS risk is retired by a real
   synth, not by an argument.
7. **Tomorrow's run (2026-08-06) is the deadline** and it must produce the first
   two-minute film. Everything must be merged to `main` before it fires, because the
   routine checks out `main`.

---

## 2. Measured facts this upgrade is built on

Do not re-derive these; they cost real synths and renders.

| fact | measured value | note |
|---|---|---|
| house VO rate | **161.5 wpm** (232 words / 86.2s on the shipped 08-05 take) | `dispatch_routine.md` §4.2 claimed 137.5 wpm "MEASURED". Stale by 17%. Every word-count estimate built on it was wrong. |
| take-to-take spread, SAME script | 86.6s / 86.8s / 97.4s = **143 to 161 wpm** | never recorded before. This is why the runtime band must be wider than a naive scaling of 84-96. |
| derived word band for 120s | **295-320 words** | 300 words @161wpm = 112s; @143wpm = 126s. |
| derived runtime band | **112-130s** | must absorb the measured take variance or good reads get re-synthed. |
| render cost | ~2664 frames final-res in 6-8 min → 3600 frames ≈ **9-11 min** | acceptable. |
| deliverable size | 34.7 MB @86.2s → ≈ **48 MB @120s** | ceiling is 100 MB. Fine. |

---

## 3. The engagement architecture (summary; full rationale in the plan of record)

- **FOUR ACTS.** Act 1 (0-30) question + mechanism. Act 2 (30-60) the complication.
  **Act 3 (60-95) THE TEST — the fair counter-point gets a SCENE, not a clause; the film
  argues against itself and either survives or narrows honestly on screen.** Act 4
  (95-120) turn + button. Act 3 is the answer to "what do we do for two minutes".
- **THREE rehook windows**: `[[25,38],[55,72],[88,104]]`.
- **TWO staggered open loops**: PRIMARY planted ≤20s, paid ≥85s, span ≥60s. SECONDARY
  planted 35-60s, paid ≥25s later, and NOT within 8s of the primary payoff.
- **A scale-class reveal in EACH THIRD** (was: each half, above 75s).
- **THE THROUGHLINE OBJECT** (new): one object introduced ≤10s that visibly changes state
  at every act boundary and lands in the button. It is the orientation mechanism — at
  120s the viewer cannot tell how far in they are, and this answers that without a
  progress bar. The 08-05 film had one by accident (the beetle: filled → dashed contour →
  named) and both dissenting judges named that pairing as the image they remembered.
- **THE PADDING TEST, restated:** for every Act 3 beat, ask whether a 90-second cut would
  have been WORSE without it. A beat that restates Act 2 more slowly is padding, and
  padding at 120s costs more than the fact was worth.

---

## 4. File map — everything length-dependent, and its status

Surveyed exhaustively on 2026-08-05. If a file is not on this list it does not encode
runtime.

| file | what is length-dependent | status |
|---|---|---|
| `config/state.yaml` | `dispatch_target_seconds: 90`, `dispatch_seconds_band: [84,96]`, `dispatch_vo_words_band: [190,215]` | TODO |
| `config/visual_flow.yaml` | `beats.min/max 18/30`, `rehook_windows_s` (2), `open_loop_*`, `sfx.min_events_total 12` | TODO |
| `config/shot_structure.yaml` | `min_shots 6`, `target_shots [7,10]` | TODO |
| `scripts/storyboard_check.py` | reveals split by HALF when `piece_end >= 75` (~line 373); no throughline check | TODO |
| `scripts/flow_check.py` | L145 reads `rehook_windows_s` as a list (already good); L148 exempts windows a piece doesn't span (already good); L166 open-loop binding at `piece_end >= 75`; single loop only | TODO |
| `scripts/align_captions.py` | L37 `--total` default `90.0` | TODO |
| `prompts/dispatch_routine.md` | §4.2 word band + the stale 137.5 wpm claim + 84-96 band + 18-30 beats + 2 rehooks + 1 open loop; §4.3; the Gate 0 block; the room briefs | TODO |
| `docs/craft/ENGAGEMENT.md` | §2.6 is the 90-second format section; needs a §2.7 for 120s | TODO |
| `config/dispatch_rubric.yaml` | **DELIBERATELY UNCHANGED** (see constraint 4) | N/A |

**Already well-parameterised — do not "fix":** `vo_soundcheck.py` reads its duration
window from `config/state.yaml > dispatch_seconds_band`. `flow_check.py` reads
`rehook_windows_s` as a list and skips windows a piece does not span, so adding a third
window is backward-compatible by construction.

---

## 5. TASK TABLE — update after every commit

| # | task | status | evidence / notes |
|---|---|---|---|
| 1 | Plan of record written (`docs/craft/TWO_MINUTE_UPGRADE.md`) | DONE | committed on this branch |
| 1b | This worklog, so the plan survives compaction | DONE | committed on this branch |
| 2 | **VERIFY THE TTS RISK EMPIRICALLY.** Synth a real ~310-word script in ONE Gemini call. Measure: duration, `transcript_match`, no truncation, cue count, and whether whole-file forced alignment stays monotonic at 120s. **NOTHING ELSE PROCEEDS UNTIL THIS PASSES.** | IN PROGRESS | |
| 3 | Config numbers: `state.yaml`, `visual_flow.yaml`, `shot_structure.yaml`, `align_captions.py --total` | TODO | |
| 4 | Gate logic: `storyboard_check.py` (thirds rule + throughline declaration), `flow_check.py` (second open loop) | TODO | |
| 5 | Doctrine: `ENGAGEMENT.md` §2.7 (the 120-second format) + `dispatch_routine.md` §4.2/§4.3/Gate 0, incl. correcting the stale 137.5 wpm to 161.5 | TODO | |
| 6 | **The rooms.** Angle room, directors room, storyboard-critic, flow-critic all briefed on the two-minute retention problem. This is the owner's stated priority. | TODO | |
| 7 | Verify: (a) a synthetic conforming 120s board PASSES every gate; (b) a PADDED 120s board FAILS; (c) the shipped 08-05 board STILL PASSES | TODO | |
| 8 | Ship: commit, push, ready (NOT draft) PR, merge to `main` before the 08-06 run fires | TODO | |

---

## 6. Rules that bind this work (from repo CLAUDE.md — do not violate)

- **NO Claude/Anthropic attribution** in commits or PRs. No `Co-Authored-By`, no
  `Claude-Session:`, no "Generated with Claude Code". Commit as the owner:
  `git -c user.name="Talon Sturgill" -c user.email="Talon.sturgill@gmail.com" commit`.
- **No model identifier** in any pushed artifact.
- PR must be **ready, not draft**, and **merged to `main` in the same session**.
- These routines **DRAFT ONLY, never send**.
- Stop and ask before: rewriting published history on `main`, anything that SENDS,
  deleting/overwriting shipped `runs/` artifacts.
- House writing rules still apply to everything written here and in prompts: ordinal
  dates ("August 10th"), no em/en dashes, no emojis, straight quotes.
