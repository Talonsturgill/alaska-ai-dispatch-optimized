# WORKLOG — THE TWO-MINUTE UPGRADE (90s → 120s Dispatch)

**READ THIS FIRST if you are resuming with no memory of the task.** This file is the
durable plan and progress ledger, written to survive context compaction. The design
rationale lives in `docs/craft/TWO_MINUTE_UPGRADE.md` (the plan of record); this file
is the *state*: what is done, what is next, what was measured, and what must not break.

Branch: `tsturg/sweet-cray-rg1lsr`, based on `origin/main` at `de0a126`.
Started 2026-08-05. **SHIPPED 2026-08-05 as PR #94, merged to `main`.**

**STATUS: the machine is upgraded; the format has not yet produced a film.** Every task
below is DONE. What remains is not work, it is OBSERVATION: the 2026-08-06 run is the
first one that will use this, and §7 lists what to watch. Delete this file once that run
has shipped a two-minute film and nothing in §7 turned out to be wrong.

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

### 2a. CORRECTION — read this before trusting any wpm number

An earlier context recorded "the house VO rate is 161.5 wpm, so the routine's 137.5 claim
is stale by 17 percent". **That was wrong, and the reason it was wrong is a live bug this
branch fixes.**

During the 08-05 run I hand-patched `out/dispatch/vo_direction.json` to add a VO line, and
rebuilt `assembled_prompt` by cutting at the first occurrence of the substring
`Transcript:`. That substring occurs inside the preamble's own sentence (`The lines above
"Transcript:" are direction; never speak them`), so the cut destroyed the AUDIO PROFILE,
the DIRECTOR'S NOTES, the Style line, the **Pace line**, and the `Transcript:` delimiter
itself. The 08-05 film was narrated with **no direction of any kind**. That is why it came
in as the fastest read ever recorded, and 161.5 wpm is an artifact of the bug, not a house
rate.

`docs/craft/VO_DIRECTION.md` says outright: "The brisk-pace line is REQUIRED (default reads
drag ~30% too slow without it)." It turns out the failure runs the other way too.

**Measured across all seven archived runs whose prompt was intact:**

| run | words | secs | wpm | pace instruction |
|---|---|---|---|---|
| 2026-07-26 | 144 | 55.3 | 156.2 | BRISK |
| 2026-07-29 | 132 | 57.6 | 137.5 | BRISK |
| 2026-07-30 | 152 | 66.7 | 136.8 | none |
| 2026-07-31 | 218 | 90.7 | 144.2 | BRISK |
| 2026-08-01 | 219 | 96.7 | 135.8 | BRISK |
| 2026-08-02 | 219 | 96.2 | 136.6 | BRISK |
| 2026-08-03 | 206 | 81.2 | 152.3 | MEASURED, "about 138 wpm" |
| 2026-08-05 | 232 | 86.2 | **161.5** | **NONE — prompt destroyed by the bug above** |

Two things fall out of that table, and both matter more than the headline number:

1. **The pace instruction has weak control.** 08-03 asked for "about 138 words per minute"
   and got 152.3. Asking for a number does not deliver it. Do not plan around it.
2. **LONGER PIECES RUN AT A TIGHTER, SLOWER RATE.** The two fast outliers (156.2, 152.3)
   are the two shortest pieces. The three pieces near 90 seconds cluster at
   **135.8 / 136.6 / 144.2**, mean **138.9**. A 120-second piece belongs to that cluster,
   not to the 55-second one. This is the sample the word band must be derived from.

### 2c. WHAT ACTUALLY CONTROLS THE RATE (measured 2026-08-05 by `scripts/vo_length_probe.py`)

The §2a table implies the rate is noisy. It is not noisy in the way that matters. Three
takes of the SAME 288-word prompt came back at **104.8 / 105.2 / 106.3 seconds**, a
**1.4 percent spread**. The rate is highly reproducible *within* a prompt.

It varies **between** prompts, a lot: the same script and the same verbatim "Pace: BRISK"
sentence produced 136 wpm in the archive and 165 wpm in the probe. The difference is the
rest of the director's notes, which **the vo-director agent rewrites from scratch every
run**. So the format's runtime currently depends on how verbose one agent felt that day,
which is not a property anything should depend on.

Two consequences, and they are the design of this upgrade:

1. **The word band is only meaningful if the notes are standardized.** Deriving a word
   count from a rate that moves 20 percent with prose style is deriving it from noise.
2. **The 12.5 percent take spread seen on 08-05 (86.6 / 86.8 / 97.4) was one outlier
   take, not the normal distribution.** Selecting takes on runtime still helps, but it is
   a safety net, not the primary control.

**The primary control is a standardized, duration-anchored Pace paragraph.** Status of
that experiment: see task 2b in the table.

### 2b. The numbers this upgrade is actually built on

**These are now DIRECTLY MEASURED at 120 seconds, not extrapolated.** `vo_length_probe.py`
synthesized the 288-word probe script five times.

| fact | value | evidence |
|---|---|---|
| **VO word band** | **280 to 300 words**, target **288** | 288 words with the ANCHORED pace line delivered **121.3s and 119.9s**. Both in band. |
| **runtime band** | **112 to 130s**, target **120** | the two anchored takes landed 119.9-121.3, well inside |
| rate, anchored pace | **142.5 and 144.1 wpm** | the two takes above |
| rate, house BRISK pace | **164.8 / 164.3 / 162.6 wpm** → 104.8 / 105.2 / 106.3s | the SAME 288 words. This is why the pace line must be anchored. |
| **truncation at 288 words** | **NONE.** 288/288 words aligned, 23/23 lines timed | the risk the whole plan was gated on |
| **alignment at 120s** | **CLEAN.** monotonic, speech_end 120.82s, first word 0.0s, 61 cues, 0 degenerate, min dwell 0.7s | the second gating risk |
| render cost | ~2664 frames final-res in 6-8 min → 3600 frames ≈ **9-11 min** | acceptable |
| deliverable size | 34.7 MB @86.2s → ≈ **48 MB @120s** | ceiling is 100 MB. Fine. |

**Two defects found by the probe and fixed on this branch** (neither is caused by the
length change; both are made dangerous by it):

- **A line-initial `[short pause]` was SPOKEN ALOUD.** The same tag mid-line, after
  punctuation, was not. VO_DIRECTION's placement rules must forbid a line-initial tag.
- **Year normalization scored clean takes as errors.** `_year_words` mapped every
  1000-2999 number to two 2-digit groups, so `2008` became "twenty eight" where the house
  script says "two thousand eight", and `1,000` became "ten hundred" where the script says
  "a thousand". The probe's anchored takes scored 0.074 and 0.077 against a **0.08 fail
  ceiling**, almost entirely on this. At 288 words there are more numbers to trip it, so a
  clean take was one mishearing from a spurious re-synth.

**Superseded numbers.** Anything saying 295-320 words (from the bug-inflated 161.5 rate)
or 270-290 (from the archive extrapolation) is stale. The measured answer is **280-300,
target 288, with an anchored pace line**. Without the anchored pace line 288 words runs
105 seconds, not 120.

**The superseded plan said 295-320 words.** That came from the bug-inflated 161.5 rate, and
at the real rate 300 words would run **132.5s on a slow read, over the ceiling**. If you
find 295-320 anywhere, it is stale; the number is **270-290**.

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
| `config/state.yaml` | `dispatch_target_seconds: 90`, `dispatch_seconds_band: [84,96]`, `dispatch_vo_words_band: [190,215]` | DONE |
| `config/visual_flow.yaml` | `beats.min/max 18/30`, `rehook_windows_s` (2), `open_loop_*`, `sfx.min_events_total 12` | DONE |
| `config/shot_structure.yaml` | `min_shots 6`, `target_shots [7,10]` | DONE |
| `scripts/storyboard_check.py` | reveals split by HALF when `piece_end >= 75` (~line 373); no throughline check | DONE |
| `scripts/flow_check.py` | L145 reads `rehook_windows_s` as a list (already good); L148 exempts windows a piece doesn't span (already good); L166 open-loop binding at `piece_end >= 75`; single loop only | DONE |
| `scripts/align_captions.py` | L37 `--total` default `90.0` | DONE |
| `prompts/dispatch_routine.md` | §4.2 word band + the stale 137.5 wpm claim + 84-96 band + 18-30 beats + 2 rehooks + 1 open loop; §4.3; the Gate 0 block; the room briefs | DONE |
| `docs/craft/ENGAGEMENT.md` | §2.6 is the 90-second format section; needs a §2.7 for 120s | DONE |
| `config/dispatch_rubric.yaml` | **DELIBERATELY UNCHANGED** (see constraint 4) | N/A |

**Post-review corrections (2026-08-05, `/code-review` on the merged branch).** Three real
defects were found in the shipped work and fixed on top; see §8.

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
| 2 | **VERIFY THE TTS RISK EMPIRICALLY.** | **DONE — PASSED** | `scripts/vo_length_probe.py`. 288 words, 5 synths: no truncation, 288/288 words aligned, 23/23 lines timed, monotonic, speech_end 120.82s, 61 cues, 0 degenerate. |
| 2a | **Fix the prompt-integrity bug** found while designing the probe (see §2a). `repair_prompt` in `vo_synth_gemini.py` REBUILDS a prompt missing the `Transcript:` delimiter, the Style/Pace/AUDIO PROFILE blocks, or whose Pace line does not name the runtime. | DONE | Verified against the real 08-05 destroyed prompt and a generic-pace archived prompt (both repaired), and an already-correct 120s prompt (left untouched). It REPAIRS rather than refuses: see §9. |
| 2b | **Standardize the Pace paragraph on an explicit runtime anchor.** The identical 288-word script ran **105s** with "Pace: BRISK" and **121.3s / 119.9s** with a pace line naming the target. Naming the runtime is worth ~15 percent of pace and is the only reliable length control found. | DONE | written into `VO_DIRECTION.md` step 7 as the required Pace text, with the measurement table and the reasoning |
| 2c | **Runtime-aware take selection** in `vo_soundcheck.pick_best`: among passing takes prefer those inside the tight band from `state.yaml`, quality decides within that set, and if none is in band take the one closest to target. Makes `dispatch_target_seconds` / the tight band do something in code for the first time. | DONE | regression-checked against the 08-05 run: picks take 1 (86.80s), exactly what shipped |
| 2d | **Year-normalization fix + line-initial-tag rule**, both found by the probe. | DONE | anchored takes went 0.074/0.077 -> 0.039/0.042 against a 0.08 fail ceiling |
| 3 | Config numbers: `state.yaml` (120 / 112-130 / 280-300), `visual_flow.yaml` (beats 24-40, SFX 16, 3 rehooks, 2 loops), `shot_structure.yaml` (8 / 9-13), `align_captions.py --total` | DONE | |
| 4 | Gate logic: `storyboard_check.py` (thirds rule + throughline), `flow_check.py` (second open loop, long-loop span/pay floor, LENGTH-DERIVED beat floor) | DONE | all gated on piece length, so shorter boards are untouched |
| 5 | Doctrine: `ENGAGEMENT.md` §2.7 (the 120-second format, four acts A-G) + `dispatch_routine.md` §4.2/§4.3/Gate 0/Phase 5, and the plan of record's own stale numbers corrected | DONE | the prompt now says DO NOT plan from a wpm figure, and explains why |
| 6 | **The rooms.** | DONE | angle room: must answer whether the thesis has a SECOND MOVEMENT. Writers room: every pitch owes a 4-part RETENTION PLAN (the Act 3 test, the throughline object, the two loops, the padding test) and the room argues THE TWO-MINUTE QUESTION as its own round; the scorer weighs it. Both Gate-0 critics briefed, and both must name the weakest third even when they ship. |
| 7 | Verify: conforming 120s board passes, padded fails, legacy 08-05 still passes | **DONE — PASSING** | `scripts/format_gate_selftest.py`. Legacy 0 problems, padded caught by all 5 two-minute rules by name, conforming 0 problems. RE-RUN THIS after any gate edit. |
| 7b | Sweep for anything else that breaks at 120s: engine frame counts, `VIDEO_SECS`, the music bed, the quality gate, `render.sh` | DONE | all derive from the VO or loop; the music bed loops to 200s. Added a STALE PER-RUN DATA guard to `dispatch_mix.py` (BED_ARC/EVENTS must cover the film) — it fires on the real 08-05 case, where the arc ended at 83.7s of an 88.8s film. |
| 8 | Ship: commit, push, ready (NOT draft) PR, merge to `main` before the 08-06 run fires | **DONE** | PR #94 merged to `main` 2026-08-05. Verified on `main`: state.yaml reads 120 / 112-130 / 280-300 and the self-test passes. |

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

---

## 7. WHAT THE FIRST TWO-MINUTE RUN MUST VERIFY

The upgrade is measured and self-tested, but no film has been made at this length yet.
These are the specific things a probe and a synthetic board cannot tell you. If one of
them goes wrong, fix it in the machine rather than by hand in the run, and record it here.

1. **Does the delivered VO land in 112-130s?** The probe says 280-300 words with the
   anchored pace paragraph gives 119.9-121.3s. A real run writes its own Style line around
   that paragraph, and the Style line is the thing that moved the archive from 136 to 165
   wpm. If the take lands outside the band, the FIRST suspect is the notes, not the word
   count. Check `vo_report.json` for the take durations and which one `pick_best` chose.
2. **Does `_assert_prompt_intact` fire on a legitimate prompt?** It was tested against ten
   archived prompts and three synthetic defects, but never against a prompt the vo-director
   writes fresh under the new instructions. A false positive here BLOCKS the run. If it
   fires wrongly, loosen the specific clause; do not disable the guard.
3. **Does the writers room actually produce a retention plan, or does it fill in the
   fields?** This is the owner's stated priority and the part with no code enforcement.
   Read the four parts in the winning treatment and ask whether Act 3 is a test or a
   restatement.
4. **Is the throughline object visible, not just declared?** The gate checks that states
   exist, are spread, and land in the button. It cannot check that a viewer can SEE the
   difference. This is the storyboard-critic's job and the first place to look if the film
   feels long.
5. **Render and mix at 3600 frames.** Estimated 9-11 min for the final render; the music
   bed loops to 200s so it covers. Watch for the new `!! STALE PER-RUN DATA` warning from
   `dispatch_mix.py` — at this length an un-rewritten BED_ARC leaves ~40s with no bed
   automation, which is exactly the stretch the format is fighting to hold.
6. **The panel is grading a two-minute film against an unchanged rubric.** That was
   deliberate, so a score move is attributable to the format rather than to a moved bar.
   If the median drops, read WHY before touching the rubric: the interesting question is
   whether the back half earned itself, and the judges' prose will say so.

---

## 8. POST-REVIEW CORRECTIONS (the shipped upgrade had three real holes)

A code review of the merged branch found nine issues; the three that mattered were
verified by reproduction, not taken on description.

1. **The two-minute rules could be silently skipped by a legal two-minute film.** Every
   length gate measured "how long is this film" as the START timestamp of the last beat,
   which is short by the last beat's duration plus the outro hold (4.2s on the shipped
   08-05 board). A legal 112.8s film whose last beat starts at 108.6s read as 108.6s, fell
   under the 110s threshold, and skipped the throughline gate, the reveal-per-third rule,
   the 60s loop span, the 85s payoff floor and the mandatory second open loop. Reproduced:
   only the rehook rule fired, because its windows are absolute. Fixed by
   `piece_runtime()` / `_piece_runtime()`, which trust the board's `total_seconds` first.
2. **Nothing in code failed a film for being the wrong LENGTH.** The soundcheck's window
   is deliberately wide (~62-176s) and the tight band lived only in prose. The exact
   failure that lets through is the default one at this length: the old BRISK pace line on
   288 words gives 105s, three takes running, and the run would have shipped a
   105-second film believing it was two minutes. Now the pace paragraph is repaired to name
   the runtime BEFORE any TTS is spent, and an out-of-band take re-rolls once then ships
   the best with the miss recorded. See §9 — the first version of this fix hard-failed,
   which was wrong.
3. **`min_shots` was raised as a flat number** while the beat floor was deliberately made
   length-derived for exactly this reason, and it retroactively failed the legal 7-shot
   2026-07-30 board. Now derived from runtime and the oner ceiling.

Smaller: the probe's `monotonic` / `lines_timed` / `degenerate_cues` / `aligned_words`
checks are structural invariants of `_align_wholefile` and can never fail, so they are now
labelled as such and excluded from the verdict (the real evidence is duration, WER and
speech_end); the probe defaulted to the superseded `brisk` pace mode; `BED_ARC` used strict
tuple unpacking on hand-edited per-run data; the self-test's filler beats could inherit a
`rehook` and silence their own assertion; `beats.max` was config no code read.

---

## 9. NO HARD FAILS (owner directive, 2026-08-05)

> "no hard fails, fix it, anything that is wrong, should just get fixed, the definition of
> done is a video delivered daily, no matter what, don't start writing urself escape
> hatches cause u tend to do that."

The first pass at the review fixes added TWO `SystemExit`s to the VO path (a damaged
prompt, an out-of-band runtime). That was wrong, and the repo already said so: `no_exit.py`
is THE ONE OUTCOME LAW, and its own docstring says it "can only ever refuse a STOP. It can
never refuse a SHIP." I had put brand new stops directly in the delivery path.

**The standing rule for this pipeline: a defect the machine can describe is a defect the
machine should REPAIR.** Every one of those conditions was mechanically recoverable:

| was a stop | now |
|---|---|
| damaged / generic prompt | `repair_prompt` rebuilds it from the plan plus the canonical template, salvaging whatever notes survive, and forces the runtime-naming Pace paragraph |
| plan stale vs script | `_reconcile_plan_with_script` rebuilds the plan from the script (the locked copy), carrying per-line direction across for unchanged lines |
| runtime out of band | re-rolls one round on the repaired prompt, then ships the best take and records the miss in `vo_report.json`, which the panel and the dated email both read |

The ONLY remaining `SystemExit` in `vo_synth_gemini.py` is a missing API key, which is a
true hard blocker: there is nothing to repair and no audio to be had.

**If you are tempted to add a gate here, add a repair instead.** A visible miss on a
delivered film beats a clean stop, every time. `format_gate_selftest.py` asserts the
generated pace paragraph stays byte-identical to the one that was actually measured, so
the repair cannot silently start shipping an untimed instruction.

