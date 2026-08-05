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

| fact | measured | where the old number was wrong |
|---|---|---|
| house VO rate | **161.5 wpm** on the delivered 08-05 take (232 words / 86.2s) | `dispatch_routine.md` §4.2 said "137.5 words per minute, MEASURED from real synths". It is off by 17 percent and every word-count estimate built on it was wrong. |
| take-to-take spread | **143 to 161 wpm** on the SAME script (three takes: 86.6s, 86.8s, 97.4s) | never recorded anywhere. This is why the runtime band has to be wider than the 84-96 the 90s format used. |
| render cost | ~2664 frames final-res in 6 to 8 min | 3600 frames ≈ 9 to 11 min. Acceptable. |
| deliverable size | 34.7 MB at 86.2s | ≈ 48 MB at 120s, well under the 100 MB ceiling. 720p rendition ≈ 8 MB. |

**Word band derivation.** Targeting the middle of the take spread (~152 wpm) rather than the fast
end, so a slow take does not blow the ceiling:

- 300 words at 161 wpm (fast take) = 112s
- 300 words at 143 wpm (slow take) = 126s

So: **target 120s, band 112 to 130s, words 295 to 320.** A band that cannot absorb the measured
take variance would force a re-synth on perfectly good reads, which is how the old 84-96 band would
have behaved at this length.

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
| VO words | 190-215 | **295-320** | `config/state.yaml`, `dispatch_routine.md` §4.2 |
| beats | 18-30 | **24-40** | `config/visual_flow.yaml` |
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
| **Gemini TTS truncates or drifts on a ~310-word single call** | the whole pipeline is one call; a truncation ships a short film with wrong captions | SYNTH A REAL 310-WORD SCRIPT AND MEASURE IT. Not reasoning, a take. |
| whole-file forced alignment degrades at 120s | captions would desync, a hard blocker | measure `transcript_match` and cue count on that same take |
| a legal 120s board is rejected by a gate | tomorrow's run blocks | run every gate against a synthetic conforming 120s board |
| a legacy/shorter board breaks | the archive and any re-run | run every gate against the shipped 08-05 board and confirm it still passes |
| deliverable size / render time | upload limits, session length | arithmetic above; both fine |

---

## 6. Order of work

1. Plan (this file).
2. Verify the TTS risk empirically. **Nothing else proceeds until a ~310-word take exists and
   measures clean.**
3. Config numbers (`state.yaml`, `visual_flow.yaml`, `shot_structure.yaml`).
4. Gate logic (`storyboard_check.py` thirds + throughline, `flow_check.py` second loop).
5. Doctrine (`ENGAGEMENT.md` §2.7) and the routine prompt (§4.2, §4.3, Gate 0).
6. The rooms: angle room, directors room, storyboard-critic, flow-critic all briefed on the
   two-minute retention problem, because the owner is right that this starts in pre-planning.
7. Verify: conforming 120s board passes, padded board fails, 08-05 board still passes.
8. Ship.
