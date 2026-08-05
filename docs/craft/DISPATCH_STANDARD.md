# THE DISPATCH STANDARD

**Read this BEFORE you build a frame. Not after the panel finds it.**

This file exists because the run was relying on rounds of review to reach the bar instead
of authoring to the bar in the first place (owner, 2026-08-05: *"it seems like the video
should just be way better before it ever gets to the judges, we're relying on so many
rounds of improvements and it's masking the fact that whoever is creating the video just
needs to be upgraded based on everything that the judges have been saying"*).

Everything below is a defect that a judge actually found, in a real round, with a
measurement. None of it is theory. If you build to this list, the first cut arrives at
roughly the score the fifth cut used to, and the panel gets to spend its attention on the
things that are genuinely a matter of taste.

**The rule for this file: every time the panel finds something that was knowable in
advance, it comes back here.** A finding that recurs across runs is a failure of this
document, not of the judge.

---

## 0. The two questions to ask before building any shot

1. **What moves, continuously, for the whole time this shot is on screen?** Not "what
   event happens" — what is never still. Shots hold for 6 to 11 seconds. An event at the
   top and an event at the bottom leaves a dead middle, and dead middles are where every
   retention note comes from.
2. **What is the one thing a viewer is meant to look at, and is it the best-finished
   thing in the frame?** The recurring illustration note is never "this is badly drawn."
   It is always "the hero reads plainer than the props around it."

---

## 1. Props and hands (illustration craft, weight 0.16 — the heaviest axis)

- **Every prop a character holds must be parented to a documented hand anchor.** Do not
  place a prop near a hand and eyeball it. The rig's poses publish their anchors; use them.
  `carry` puts the fist at `(X + 120*S*facing, Y - 190*S)` for a figure at
  `translate(X,Y) scale(S)`.
- **A holdable prop's transform origin is its GRIP POINT**, not its centre of mass. If the
  origin is the middle of the object, "put it in the hand" becomes a rotation problem you
  have to solve by eye every time, and you will get it wrong. `DripTorch` is the worked
  example.
- **Draw the prop after the figure and close fingers over it** in the figure's own skin
  tone, with a contact/AO tick where the fist meets the handle. A hand behind a handle
  reads as a hand near a handle.
- **Everything resting on the ground gets a contact shadow.** Boots, posts, dropped tools,
  machines, card stacks. The single most repeated craft finding in this film's history is
  an object with no AO pool while three objects beside it have one. If it touches ground,
  it casts.
- **Nothing floats.** If a sign, card or plate is in the air, either a hand holds it or a
  stake holds it. "It fades in" is not support.
- **Finish parity.** Do not put a flat single-fill surface in a frame with a gradient-lit,
  ink-outlined, rivet-detailed one. That includes hands, boots, treelines and map fills.
  On small forms (a 15px palm) a bounding-box gradient spans too few pixels to read — use a
  core-shade crescent and a cast tick instead.

## 2. Motion (weight 0.12)

- **Every held figure needs idle life**: a breath cycle and a lateral weight shift, phase
  offset per figure so two people in a frame are never in lockstep.
- **The weight shift is applied ABOVE the feet.** Applying it at the character root slides
  the boots and their contact shadows along the ground, which reads as skating. Torso
  carries the full shift, legs about a third, boots stay planted.
- **A gesture is not a pose.** If a character points, the arm must arrive: windup below
  zero, extension, overshoot past the target, settle. An arm that is already extended in
  the first frame of its shot and holds for six seconds is a pose wearing a gesture's
  clothes, and judges have called it out every time.
- **Point at things that exist.** If the gesture lands on an object, drive the gesture from
  the same value that brings the object in.
- **No shot may go quiet.** Anything held longer than ~6s needs a continuous animation that
  spans the WHOLE hold, not one that completes in the first third and then sits.

## 3. Composition and staging (weight 0.08 — historically the lowest-scoring axis)

- **The 9:16 master is the graded cut. Compose FOR it.** The square is derived by
  `crop=1080:1080:0:420`. Content outside y 420..1500 is free canvas that stages the
  vertical and never appears in the square — use it (atmosphere and ridges above, near
  foreground below). Do not build for the square band and let the rest be padding.
- **No overlay may occlude a character silhouette.** Compute it, do not eyeball it: the
  hard hat crown sits at `1180 - 454*scale` in scene space. A card that amputates the
  hero's head held for 2.8 seconds is the kind of thing that reads as broken, not as busy.
- **No shot should be more than ~40% unmodulated empty fill.** Judges measure this with a
  low-gradient-area metric and the dead zones always coincide with the longest holds, which
  is the worst possible alignment.
- **The persistent brand mark is not exempt from staging.** Keep it off the hero, off the
  map, off information cards, and on one anchor. A mark that wanders between shots or cuts
  a coastline reads as an artifact.
- **Depth planes must stack possibly.** Ground may not have sky below it. If a background
  layer closes at a fixed y, check what is under it before the next plane starts.

## 4. Typography and on-screen strings (weight 0.06, but a blocker class)

- **Size the plate to the string, never the reverse.** Mono advance is exact
  (0.602em), so a mono string's width is arithmetic, not judgement:
  `len * size * 0.602 + letterSpacing * (len - 1)`. Minimum 14px clear on both sides.
- **Run `scripts/text_fit_check.py` BEFORE rendering.** It reads source and needs no
  frames. Read its coverage line, not just its exit code: a pass with the string you care
  about sitting in the "not measured" list is not a pass on that string.
- **Re-measure the plate every time you change the type.** Every single overflow in this
  film's history came from enlarging type to answer a legibility note without re-measuring
  the box behind it.
- **Watch descenders between stacked runs.** A 66px figure's comma descends ~14px and will
  strike a qualifier line set 24px below its baseline.
- **A mark that negates must negate the right thing.** A strike through a word cancels that
  word. If the point is an absence, strike the empty slot, not the label naming it.

## 5. Captions and audio (weight 0.10 sound, plus caption blockers)

- **Caption text comes from the SCRIPT. Caption timing comes from the AUDIO. Both must
  match the DELIVERED stem.** ASR transcripts are for placing words in time and nothing
  else.
- **After any VO re-synth, every artifact that states the narration moves together**:
  `vo.wav`, `vo_lines.json`, `vo_script.txt`, `vo_script.json`, `captions.json`,
  `words.json`. Missing one of these has produced a hard blocker twice, both times because
  the caption said something the voice did not.
- **Re-align after patching audio.** A `words.json` older than the `vo.wav` it describes is
  a stale artifact that will burn wrong text on screen.
- **Never write a measurement into the evidence pack by hand.** `audio_report.json` carried
  a hand-typed claim that the VO left "one gap over 0.35s"; there were 21. It sent three
  rounds of fixes in the wrong direction. Generate it (`scripts/audio_report.py`).
- **LRA comes from genuinely quiet moments.** Raising the bed INTO gaps narrows the spread
  and does not help. If the loudness range is flat, the fix is real air, which means
  trimming VO, which is cheap: `vo_patch_lines.py` fits a shorter line inside its existing
  slot and no downstream boundary moves.

## 6. Accuracy and the ledger (weight 0.10)

- **`on_screen` records the string the film PAINTS, not the claim it supports.** If the
  film paints a chip reading `CURRICULUM`, that is the on_screen value.
- **`spoken` records what the delivered audio SAYS**, verified against the stem, not what
  the script planned.
- **`verbatim_source` takes exactly three forms and each declares itself**: a literal
  quotation opening with a quote mark and containing no added emphasis or elision; a
  structured field citation written `field: "value"`; or a labelled non-quotation that says
  so in its first words. A pointer like "same sentence as c7" is none of these.
- **Reconcile the ledger against the delivered cut before the ship step, not after.** Four
  records described a cut that no longer existed as recently as round 12.
- **An attributed subtitle must be safe to read as a quote.** If you compress a source
  sentence, either restore the clause or drop the attribution tag.

## 7. Hook (weight 0.12)

- **Something must MOVE in the first half second**, and a plate easing in does not count —
  a judge read a 0.3s scale-and-settle entrance as "a placard slide". Use a real interrupt:
  an ignition, a hard snap with overshoot, a value slamming to its stop.
- **Do not arrive fully painted.** If the composition is complete at frame 1, the first
  seconds have nothing to give.
- **Bookend it.** The strongest thing this film does is return to the opening image
  inverted. Build the open knowing what the button will do to it.

---

## The pre-render checklist

Run these before you spend twelve minutes on a render, in this order. All are cheap and
all read source or existing artifacts:

```
python3 scripts/text_fit_check.py         # plated strings fit, with coverage stated
npx tsc --noEmit -p video-engine/tsconfig.json
```

And after the render, before the panel:

```
bash   scripts/encode_deliverables.sh     # aspect + delivered-audio asserts
python3 scripts/audio_report.py           # measured, never hand-written
python3 scripts/dead_space_check.py --every 30
python3 scripts/crop_safety.py            # the derived square, mechanically
python3 scripts/build_evidence.py
```

A gate that reports zero measurements is a failure, not a pass. Every one of these prints
what it actually checked; read that line.

---

## 8. Things the 2026-08-05 panel found that were knowable in advance

Added under this file's own maintenance rule. Each one is a defect a judge actually
found on "The Net Comes First", with the measurement, and each was avoidable.

- **A scene built only out of `interpolate()` events is a slideshow.** An event that has
  finished is a still photograph, and §2's "no shot may go quiet" was read as being about
  long holds when it is really about EVERY frame. A frame-difference sweep of that film's
  first delivered cut found 76.6 percent of frames at or above 99 percent identical to the
  frame before, with a 13.5 second unbroken run. **Every scene wrapper carries a continuous
  slow push (about 1.00 to 1.10 across the shot) plus a lateral drift on an irrational
  period, and one always-running ambient layer, before any event is authored.** Measure it,
  do not eyeball it:
  `ffmpeg -i cut.mp4 -vf "scale=160:284,tblend=all_mode=difference,blackframe=amount=0:threshold=6" -f null -`
  and read the pblack values. Anything over about 60 percent means the film is mostly still.
- **A silhouette used by the absence grammar must carry the whole subject.** `lib/absence.tsx`
  strokes a path with no fill, so whatever the path omits simply is not there. A beetle's
  elytra outline, unfilled, is an egg, and that film's hook AND its signature shot were both
  built on the dashed form. Export a full silhouette (body plus head, limbs and antennae) for
  anything that will be drawn as an absence, and look at it dashed before building on it.
- **Evidence-pack filmstrip anchors are PER-RUN DATA.** `scripts/build_evidence.py`'s strip
  list still held the previous film's beat names, so two strips sampled the same shot and a
  judge correctly reported that one beat "reuses the identical still" from another. It was
  the sampler pointing twice at one scene. A run that changes the film changes those anchors
  in the same commit, and the offsets are CONTACT times, not line starts plus a guess.
- **A `Character` rig next to form-shaded props needs an explicit `ContactShadow` and
  comparable staging scale.** Three judges independently wrote that the human read flatter
  than the cabinet beside him. The rig is form-shaded internally, so the tell is not the
  shading, it is that everything around him casts and he did not.
- **A gate that rules a net-new asset a duplicate of the shelf is usually answered by moving
  its SHAPE LANGUAGE, not by arguing behaviour.** Gate 0D correctly called the first
  `NameEngine` a second `AshReader`. The differences on offer were behavioural and a viewer
  cannot see behaviour in a silhouette. Putting the machine on the opposite side of the
  film's own shape grammar fixed it and made the film better.

- **VERIFY A FIX RENDERED BEFORE YOU DEFEND IT TO A JUDGE.** This cost four panel rounds on
  2026-08-05. Three judges said the newsprint beat was frozen; the run reported it fixed
  twice, and both reports were false. The edits were string replacements written against
  source text an earlier edit had already changed, so they matched nothing and silently
  no-opped. **A no-op edit is indistinguishable from a delivered fix from the orchestrator's
  side**, and the panel is the only thing that catches it, which is the most expensive
  possible place to catch it. After any fix to a specific beat: re-render, re-cut that
  beat's strip, and LOOK at it. If the judges disagree with you about a frame, they are
  looking at the frame and you are looking at your intention.
- **"It measurably changes every frame" is not the same as "it moves".** The same beat
  measured 100 percent of frames changing while being visually static, because the change
  was dust and a sub-pixel push. The judge's arithmetic is the right test: a moving element
  should traverse a visible fraction of the frame inside the 8-frame, 0.27 second window the
  evidence pack samples. If it moves 40px in a 1080px frame, it is a rounding error to a
  viewer. Size the motion to the window it will be judged in.
- **Check what is actually on screen at the moment you are fixing.** The machine meant to
  carry that beat had opacity 0 for the first five seconds of its own shot, so the newspaper
  was the entire frame and nothing in it moved. Before animating a scene, list what is
  visible at the timecode in question.
