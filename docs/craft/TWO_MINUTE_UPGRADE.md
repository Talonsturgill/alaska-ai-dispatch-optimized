# THE TWO-MINUTE UPGRADE — plan of record

Owner directive, 2026-08-05: *"upgrade the videos from around ninety seconds to around two
minutes... nothing changes except for the length... but we gotta make sure that we hold
engagement... this all starts with the preplanning. Those guys in the beginning, they gotta be
talking to each other and saying what are we gonna do for two minutes to hold engagement."*

This file is the plan and the record of what changed. It exists because the 60→90 upgrade left
stale numbers scattered in prose that later runs believed (the 137.5 wpm claim below is one), and
because a format change touches nine files that each read as authoritative alone.

---

## 0. The one thing that actually has to be true

A 120-second film is not a 90-second film with more in it. It is a film with **a second half that
has to earn its own attention**. At 90s the viewer's implicit question at 70s is "where is this
going". At 120s the question at 80s is **"how much longer is this"**, and nothing in the current
format answers it.

Everything below is either a retention mechanism aimed at that question, or a number that had to
move because the runtime moved.

---

## 1. Measured facts this plan is built on (not assumptions)

> **CORRECTED 2026-08-05, after the probe.** This section originally read "the house VO rate is
> 161.5 wpm, so the routine's 137.5 claim is stale by 17 percent", and derived a word band of
> 295-320 from it. **Both were wrong.** The 161.5 figure came from a take whose prompt had been
> destroyed by a bad string patch, so it was narrated with no pace direction at all. Deriving a
> word count from it would have produced a film 12 seconds over the ceiling on a slow read. The
> numbers below are what `scripts/vo_length_probe.py` actually measured at 120 seconds.

| fact | measured | how |
|---|---|---|
| **VO word band** | **280 to 300 words**, target 288 | 288 words delivered **121.3s and 119.9s** with the anchored pace line |
| **runtime band** | **112 to 130s**, target 120 | both probe takes landed inside with room to spare |
| pace control | **the Pace line is worth ~15 percent of runtime** | the SAME 288 words ran 104.8 / 105.2 / 106.3s with "BRISK", and 121.3 / 119.9s with a line naming two minutes |
| within-prompt variance | **1.4 percent** | three takes of one prompt: 104.8 / 105.2 / 106.3s. The read is not a lottery. |
| between-prompt variance | **136 to 165 wpm** | the same verbatim "BRISK" sentence across the archive. The director's notes are rewritten every run, so the runtime depended on how verbose one agent felt that day. This is the thing the anchored pace paragraph fixes. |
| truncation at 288 words | **none** | 288/288 words aligned, 23/23 lines timed |
| alignment at 120s | **clean** | monotonic, speech_end 120.82s, first word 0.0s, 61 cues, 0 degenerate |
| render cost | ~2664 frames final-res in 6 to 8 min | 3600 frames ≈ 9 to 11 min. Acceptable. |
| deliverable size | 34.7 MB at 86.2s | ≈ 48 MB at 120s, well under the 100 MB ceiling. 720p rendition ≈ 8 MB. |

**Word band derivation.** Not extrapolated from a rate. A 288-word script was synthesized five
times and measured, and 280-300 is the band around what landed. The rate follows from the pace
paragraph rather than the other way round, which is why `docs/craft/VO_DIRECTION.md` step 7 now
carries that paragraph as required text.

---

## 2. The engagement architecture

### 2.1 FOUR ACTS, and the new one is THE TEST

The 90s format is setup / complication / turn. The extra thirty seconds does **not** go to a longer
setup or a slower turn, both of which are how a long film dies. It goes to a new third act in which
**the film puts its own thesis under pressure and the pressure is drawn**.

| act | window | job |
|---|---|---|
| ACT 1 | 0 to 30s | the question and the mechanism |
| ACT 2 | 30 to 60s | THE COMPLICATION: the second fact that recontextualises the first |
| **ACT 3** | **60 to 95s** | **THE TEST: the fair counter-point gets a SCENE, not a clause. The strongest case against the thesis is drawn at full strength, and the film either survives it or narrows honestly in front of the viewer.** |
| ACT 4 | 95 to 120s | the turn, the argument, the button |

Act 3 is the answer to "what do we do for two minutes". This channel already writes a fair
counter-point into every film and then spends four seconds on it. At 90s that is the right budget.
At 120s it is the most interesting thirty seconds available, because a piece that argues against
itself and survives is more convincing at 120s than a piece that asserts for 120s.

**THE PADDING TEST, restated for four acts:** for every Act 3 beat, ask whether a 90-second cut
would have been WORSE without it. A beat that merely restates Act 2 more slowly is padding, and
padding at 120 seconds costs more than the fact was worth.

### 2.2 THREE rehook windows

`[[25, 38], [55, 72], [88, 104]]`

The 25-38s cliff does not go away. The 55-72s sibling does not go away. A third opens at 88-104s,
once the viewer has been watching a minute and a half with no sense of the remaining runtime.
`flow_check.py` already reads this as a list and exempts windows a piece does not span, so shorter
pieces are unaffected.

### 2.3 TWO open loops, deliberately staggered

One loop cannot hold 120 seconds. Today's film plants at 7.5s and pays at 46s, which is correct at
90s and leaves **seventy seconds of inertia** at 120s.

- **PRIMARY**: planted by 20s, paid at **85s or later**. Span >= 60s. This is what makes minute two
  a place where something is still owed.
- **SECONDARY**: planted between 35 and 60s, paid at least 25s later, and **not within 8s of the
  primary payoff**. Two payoffs landing together leaves a vacuum behind them.

### 2.4 A scale-class reveal in EACH THIRD

Was: one in each half above 75s. Now: one in each third above 110s. Three "whoa" beats, because one
cannot carry two minutes and a final third without its own reveal coasts to the button.

### 2.5 THE THROUGHLINE OBJECT (new, and the piece I am least willing to drop)

**One object, introduced in the first 10 seconds, that visibly changes state at every act boundary
and lands in the button.**

This is the orientation mechanism. At 120s a viewer cannot tell how far in they are, and a
throughline object answers that without a progress bar: it has a visible start state, it is visibly
different at 30s, 60s and 95s, and its final state is the film's argument.

The 08-05 film had one by accident (the beetle: filled → stripped to a dashed contour → named
again at the button) and both dissenting judges named that pairing as the image they remembered.
Making it explicit and board-declared turns an accident into a mechanism.

Declared as `throughline {object, states: [{at_s, state}], lands_in_button}`, required at >= 110s.

---

## 3. The numbers that move

| knob | 90s | 120s | file |
|---|---|---|---|
| target seconds | 90 | **120** | `config/state.yaml` |
| runtime band | 84-96 | **112-130** | `config/state.yaml` (read by `vo_soundcheck.py`) |
| VO words | 190-215 | **280-300** | `config/state.yaml`, `dispatch_routine.md` §4.2 |
| beats | 18-30 | **24-40**, and now DERIVED from piece length rather than a flat number | `config/visual_flow.yaml`, `flow_check.py` |
| max beat gap | 5.0s | **5.0s (unchanged)** | the never-rest ceiling is a constant, not a function of length |
| rehook windows | 2 | **3** | `config/visual_flow.yaml` |
| open loops | 1 | **2** | `config/visual_flow.yaml`, `flow_check.py` |
| scale reveals | 1 per half | **1 per third** | `storyboard_check.py` |
| shots | min 6, target 7-10 | **min 8, target 9-13** | `config/shot_structure.yaml` |
| max shot seconds | 16 | **16 (unchanged)** | a 16s shot is a oner at any length |
| SFX events | min 12 | **min 16** | `config/visual_flow.yaml` |

---

## 4. What deliberately does NOT change

- **The quality gates and the rubric.** The owner's read was right. `dispatch_rubric.yaml` scores
  craft, not length, and its axes are already the right questions to ask of a 120s film. Raising a
  bar at the same time as a format change would make it impossible to tell which change caused a
  score move.
- **The ship gate, the story gate, `no_exit.py`.** Length-agnostic.
- **The never-rest ceiling (5s) and the oner ceiling (16s).** Both are properties of attention, not
  of runtime.
- **Every writing rule**, including the two added earlier today.
- **The delivery path**: same aspects, same encodes, same feed, same email.

---

## 5. Risks, and how each is retired before this ships

| risk | why it matters | how it is retired |
|---|---|---|
| **Gemini TTS truncates or drifts on a long single call** | the whole pipeline is one call; a truncation ships a short film with wrong captions | **RETIRED.** 288 words synthesized five times, no truncation, 288/288 words aligned. |
| whole-file forced alignment degrades at 120s | captions would desync, a hard blocker | **RETIRED.** Monotonic, 23/23 lines timed, 61 cues, none degenerate, speech_end 120.82s. |
| a legal 120s board is rejected by a gate | tomorrow's run blocks | **RETIRED.** `format_gate_selftest.py`: conforming board, 0 runtime problems. |
| a legacy/shorter board breaks | the archive and any re-run | **RETIRED.** Same self-test: the shipped 08-05 board, 0 runtime problems. The beat floor is derived from length precisely so this stays true. |
| deliverable size / render time | upload limits, session length | arithmetic above; both fine |

---

## 6. Order of work

1. ~~Plan (this file).~~ DONE
2. ~~Verify the TTS risk empirically.~~ **DONE, PASSED.** `scripts/vo_length_probe.py`.
3. ~~Config numbers.~~ DONE
4. ~~Gate logic.~~ DONE
5. ~~Doctrine + routine prompt.~~ DONE
6. ~~The rooms.~~ DONE. The angle room now has to answer whether the thesis has a second
   movement; the writers room owes a four-part RETENTION PLAN per pitch and argues it as its own
   round; both Gate-0 critics are briefed on the two-minute sequence problem.
7. ~~Verify.~~ **DONE, PASSING.** `scripts/format_gate_selftest.py`.
8. Ship.

Live state and the per-task table live in `.claude/WORKLOG.md` while this is in flight.
