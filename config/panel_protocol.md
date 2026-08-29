# PANEL PROTOCOL — how the 3-judge panel is convened, and why it is convened this way

## Closed evidence precondition

A panel may be convened only after `python3 scripts/build_evidence.py` has
recreated `out/evidence/`, invoked every terminal producer, and written the
producer/source/version/parameter-bound `evidence_manifest.json`. Then
`python3 scripts/preflight.py` must exit 0 against that exact manifest and the
current delivery manifest. `scripts/make_review_sheets.py` produces early-look
material only; its output is never panel evidence and cannot support a verdict.

Judges receive only the artifact set named and hash-bound by the current evidence
manifest. A missing, extra, stale, mutated, or independently assembled file means
the panel does not start. After any render, mix, encode, or evidence change, rebuild
the pack and re-run preflight before asking a judge to score.

Written 2026-07-31 after a run in which the panel's numbers drifted downward across
re-grades of a film that was measurably improving. The owner named it: "it seemed like you
started to get some judging drift."

## The evidence that there was drift

Same film, improving each round, every claimed fix verified by the judges themselves:

| judge | r14 | r15 | r16 | r17 |
|-------|-----|-----|-----|-----|
| 1 | 7.50 | 7.25 | 7.58 | 7.20 |
| 2 | 7.70 | 7.60 | **7.86 (ship)** | 7.20 |
| 3 | 7.80 | 7.57 | 7.61 | 7.38 |

Judge 2 passed the film at 7.86 and then scored a strictly better cut at 7.20. Judge 1 moved
Composition 7.0 -> 5.0 -> 6.5 between cuts that differed by a specular highlight and a
nameplate treatment. Judge 3 said the quiet part out loud: *"My 7.38 is below my round-16
7.61 not because the film regressed: composition and writing both rose on your fixes, and I
stopped discounting the static turn, which I had been generous about for two rounds."*

That is not noise. It is a scale that floats.

## The three causes, and what each one gets

**1. Every panel was a fresh judge with no anchor.** A new instance each round has the
rubric's word-descriptors and nothing else. "7 = competent" is not a measurement, it is a
vibe, and vibes drift. Word-descriptors cannot pin a scale; only examples can.

> FIX: `config/panel_anchors.md` holds a small set of ANCHOR ARTIFACTS — real frames and
> strips from past runs with their agreed axis scores. Every judge prompt includes the
> anchors for the axes that judge owns. A judge scoring Composition 6 must be able to say why
> the frame in front of them is worse than the anchor scored 7.

**2. A re-grade had no memory of its own previous card.** Nothing forced a judge to notice
they had moved an axis by two points on an unchanged element, so re-calibration happened
silently and read as a finding about the film.

> FIX: a re-grade prompt MUST carry that judge's own previous axis scores, with this
> instruction: *"Any axis you move by more than 1.0 from your last card, you must name the
> element that changed and say whether the film moved or your standard did. Both are
> legitimate. Silently doing the second while reporting the first is not."*

**3. The prompts fed a "what changed" list, which steered attention.** Telling a judge which
five things were fixed reliably sends them hunting somewhere else, so each round harvested a
fresh crop of defects from previously unexamined territory. That is useful for finding bugs
and ruinous for a stable score.

> FIX: separate the two jobs. The score is formed from the evidence pack ALONE, and is
> written down first. The change list is disclosed only AFTER the axis scores are committed,
> and it drives a `fix_verification` block that cannot alter the scores above it.

## What the orchestrator does with the numbers

- The verdict is the MEDIAN of three. That already dampens one judge's drift.
- **A drop of more than 0.4 in the median between rounds, on a cut with no reverted change,
  is a PANEL event, not a film event.** Re-run the panel once before acting on it. If the
  second panel agrees, it is real.
- Never re-grade a cut that has not been re-rendered. A re-grade of identical bytes measures
  the panel, and this run did it repeatedly.

## The rule this protocol does NOT contain

Nothing here permits a run to stop, to ship below bar, or to decide a score is "really"
higher than measured. Drift is a reason to measure better. It is never a reason to argue with
the measurement, and a run that finds itself explaining why the panel is wrong should re-run
the panel rather than write the explanation.
