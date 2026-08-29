# VISUAL FLOW: the constant-motion, all-senses brain

A companion to CINEMATIC_SCENE_CRAFT.md. That doc governs the MACRO rhythm (cut between distinct
worlds, smooth morphs, MOVE vs CUT). THIS doc governs the thing that keeps a muted viewer watching
second to second: the picture NEVER RESTS, every sentence of narration is DRAWN, and every visual
event you can hear is PAIRED WITH A SOUND. Sight and sound move together, and neither one coasts.

The producer note that created this file: "In a good video you engage all the senses. To keep
someone watching you change what they SEE about every five seconds, and you make sure the
illustration is constantly illustrating the STORY, not just moving. And what they hear has to move
with it." So: plan the flow in preproduction (not after), and verify it by machine and by a critic.

Distilled from studying The Infographics Show (Dark Matter Design), Kurzgesagt / Epic Mountain, and
the explainer-craft and audio-visual-perception literature. Sources at the bottom.

---

## 1. THE THREE CADENCES (all three run at once)

1. MICRO / NEVER-REST (the new rule this doc adds): a STORY-ADVANCING visual change lands at least
   every 5 seconds, and ideally every 2.5 to 4 seconds. "Story-advancing" means a new element enters,
   a value ticks, a state flips, a label discloses, the camera pushes to reveal, or a mark travels.
   Drift and grain do NOT count. Nothing on screen holds unchanged for more than 5 seconds, ever.
2. MACRO / SCENE CHANGE (already enforced, see CINEMATIC_SCENE_CRAFT.md + config/shot_structure.yaml):
   cut or morph to a genuinely different WORLD every ~8 to 12 seconds; >=4 shots across the ~60s.
3. SOUND (this doc, §5): every story-advancing visual event gets a motivated sound within ~1 frame,
   under an EQ-carved, ducked VO. If you can see it happen, you should be able to hear it happen.

The MICRO cadence is the one that was missing. EVENT_CADENCE (no dead window > 5s) and BEAT_DENSITY
(>=12 beats/60s) measure it AFTER the fact from pixels. This doc makes it a PLANNING discipline: the
beat map schedules a change on a clock, and the gates check the plan and the render against that clock.

THE NUMBERS (sourced, convergent across independent practitioner + platform analyses):
- A NEW visible element (text, icon, annotation, counter tick, zoom, highlight) every 3 to 5 seconds:
  floor 3s (a viewer needs ~3s to absorb a shot), ceiling ~5s (attention starts to drift past it).
- The "5-second block" retention test: scan the timeline for any 5s window with no cut, no zoom, no
  new text, no sound event; that gap is where viewers leave. We are 9:16 vertical short-form, where the
  static-hold ceiling is TIGHTER (~4s) and hard cuts often land every 3 to 4s.
- Full scene change: ~15 to 25s on long-form explainer, ~10 to 20s on short-form. Our editorial dispatch
  sits tighter still (a different world every ~8 to 12s, per shot_structure.yaml) because it is 60s and fast.
- YouTube Shorts data point: the top-100 Shorts averaged ~2.5s per clip and saw ~35% higher completion
  than 4s+ clips. So 5s is the CEILING; the TARGET median beat gap is ~2.5 to 4s.

---

## 2. SAY IT, SHOW IT (no orphan narration)

The single most important rule for an illustration-led piece: EVERY SENTENCE OF THE VO EARNS A
VISUAL. If the narrator says it, the screen shows it, literally where a literal picture exists and
with a clean metaphor where it does not. Narration playing over an unchanging diagram is an "orphan"
and it is the top retention killer.

- VOICE-FIRST. Lock the VO first, then time the picture to it (the Infographics Show / Kurzgesagt
  pipeline). Our engine already renders to the VO word-timings (words60.json); the BEAT MAP must
  cover that timeline so no stretch of speech goes un-illustrated.
- COVERAGE TEST. Lay the VO sentences next to the beat map. Every sentence maps to at least one beat
  whose `shows` depicts what that sentence is about. A sentence with no matching visual is a defect.
- LITERAL FIRST. "1,750 quakes" -> a counter ticking to 1,750. "a 250 km seam" -> a line drawing to
  length with a scale label. "diving under Alaska" -> the slab tilts and descends. Reach for metaphor
  only when the literal thing cannot be drawn, and keep the metaphor honest.
- SILENT-FIRST still rules: if you mute the VO and the pictures alone carry the story, you are done.
  Say-it-show-it is how you get there, because the pictures ARE the sentences.

---

## 3. THE BEAT SCHEMA (machine-checkable, in storyboard.json)

Beats stop being loose prose. Each beat in `storyboard.json > beats[]` is an object on a clock:

    {
      "t": "9.0-13.5",              # start and end seconds; start-to-start gap to the next beat <= 5.0
      "vo": "they fell into one line, 250 km long",   # the VO phrase this beat illustrates (coverage)
      "shows": "the 1,750 scattered points slide and CONNECT into one glowing crimson line",  # the NEW on-screen thing
      "sfx": "a rising sweep as the points converge, a soft lock-tick when the line snaps straight", # the paired sound
      "means": "the pattern is a line, not a cloud",   # why it matters
      "choreo": {                     # HOW the motion is organized (docs/craft/CHOREOGRAPHY.md)
        "primary": "the points slide and connect into the line, synced to the VO phrase",
        "reaction": "the connect-snap emits a pulse; nearby station pins recoil and settle",
        "ambient": "graticule shimmer + drifting dust motes + slow cloud-shadow sweep continue under it"
      }
    }

Rules the plan must satisfy (enforced by scripts/storyboard_check.py, see §9):
- 12 to 16 beats across ~60s; every beat has t, vo, shows, sfx, means.
- start-to-start gap between consecutive beats <= 5.0s (the NEVER-REST ceiling); target 2.5 to 4s.
- beats cover the VO timeline start to finish (no un-illustrated speech gap > 5s).
- every beat's `sfx` names a concrete, motivated sound (not "music"); it becomes a row in the audio
  script's event list and a checked event in the mix (§5, §9).
- every beat declares `choreo: {primary, reaction, ambient}` — concrete, cause-and-effect motion
  choreography, not vibes ("stuff moves" fails the critic). See CHOREOGRAPHY.md §9.

The prose beat map in storyboard.md stays for humans; storyboard.json carries the checkable version.

---

## 4. NEVER LET THE FRAME REST (superseded by the CHOREOGRAPHY doctrine for HOW)

The never-rest cadence stands: land a NEW story-advancing move on the beat clock, nothing on
screen rests longer than 5s. But the 2026-07-11 postmortem retired this section's old "one at a
time" prescription — one element ticking over a held frame is exactly the slideshow tell. HOW the
motion is organized now lives in **docs/craft/CHOREOGRAPHY.md** (read it before storyboarding):

- FOUR CHANNELS run concurrently every shot: one VO-synced PRIMARY action + a REACTION the
  primary visibly causes + 2-3 low-amplitude AMBIENT life loops + a perpetual ATMOSPHERE bed.
- ARRIVAL PHYSICS on everything: anticipation, eased entrance (linear banned), 3-6% overshoot
  + settle, follow-through 2-4 frames behind, cascades staggered 2-3 frames along one path.
- CAUSE-AND-EFFECT LAW: every primary provokes an attributable reaction (displacement, impulse
  broadcast, parenting, call-and-response chain, instrument reaction).
- SUBJECT PERFORMANCE: the hero has a business arc per shot; the camera ARRIVES on the action.
- WORLD ARC: one monotonic state ramp per shot; one scheduled world event per Dispatch (~2/3);
  the end state visibly differs from the start.

The old move vocabulary (pop-in, counter/meter, traveling mark, camera push, state flip, world
swap, progressive disclosure) remains the PRIMARY-channel menu — but each move now enters with
physics, causes a reaction, and plays over a living bed, per the choreography numerics table.

Enforced: beats declare `choreo: {primary, reaction, ambient}` (flow_check fails beats without
it), and quality_gate's LIVING_SCREEN check requires >=3 camera-compensated disjoint motion
regions in >=80% of 2s windows (config/visual_flow.yaml > choreo).

---

## 5. SOUND PAIRED TO THE PICTURE (engage the ear)

Sight without sound is half a video. Give the ear the same beat the eye gets.

THE FIVE ELEMENTAL SFX (the explainer grammar):
- POP / bloom -> an element ENTERS (label, pin, icon, card).
- WHOOSH / sweep -> a TRANSITION or camera move. Start it 10 to 20 ms BEFORE the visual move begins;
  the ear leads, and the lead makes the move feel alive instead of stamped on.
- RISER -> energy build INTO a reveal; the riser peak lands exactly on the reveal frame.
- HIT / sting -> a KEY STAT or section punctuation (the number, the name, the turn).
- AMBIENT bed -> constant, low, connective (the room tone of the world: geologic rumble, sea, wind).

PAIRING + DENSITY RULES:
- Every story-advancing visual event gets ONE motivated sound within ~1 frame (~40 ms). Events that do
  not advance the story run silent; the silence is a choice, not an absence.
- LAW OF TWO-AND-A-HALF (Walter Murch): the ear tracks at most ~2 to 3 SIMILAR sounds at once; beyond
  that they fuse into mush. Never stack more than 2 to 3 same-class SFX. Spend density on DIFFERENT
  classes (one tonal, one percussive, one ambient), not multiples of one.
- SEMANTIC CONGRUENCE BEATS TIMING PRECISION. A conceptually right sound 2 to 3 frames late still reads;
  a perfectly timed but wrong sound degrades recall (measured). Pick the right sound, then nail the frame.
- SILENCE IS A DESIGNED EVENT. Pull SFX and dip music ~10 dB for 1 to 2s right before a big reveal or on
  a full VO pause, then bring the world back. The contrast doubles the landing.

MIX HIERARCHY (VO always wins):
- VO is the anchor. Key SFX sit about 10 to 15 dB under VO; music bed about 15 to 20 dB under VO.
- Leave 50 to 100 ms after the last spoken word before a prominent SFX; place distinct SFX in VO pauses.
- EQ the music (and any SFX) to duck the 2 to 4 kHz speech-intelligibility band while the VO speaks.
- Program loudness -14 LUFS, true peak <= -1.0 dBTP (already the audio gate).

Our engine already builds a dedicated SFX stem cut to the shot boundaries. The upgrade (§9): after
take resolution and master completion, the audio script EMITS one enriched ledger at
`out/dispatch/sfx_events.json`. It binds every performed take/timing/gain/pitch fact to the exact
`master.wav` bytes. The retired `audio/sfx_events.json` split ledger is a hard failure.

---

## 6. THE MUSIC ARC ACROSS 60 SECONDS

Music is not wallpaper; it is a single 5-phase arc scaled to a minute, adding ONE layer per section:
1. EXPOSITION (0 to ~10s): one texture or filtered melody under the hook.
2. RISING (build sections): add a harmony/pad layer, then a rhythmic layer, one per shot as tension builds.
3. CLIMAX (the reveal / thesis beat): peak density; percussion fully present only here.
4. FALLING (the honest-limit / consequence beat): thin the texture back out.
5. DENOUEMENT (outro): resolve clean, fade under the wordmark.
Duck DYNAMICALLY under VO (sidechain), never a single static level. Instrumental, no competing vocals.

---

## 7. THE INFOGRAPHICS SHOW FORMULA, ADAPTED TO A 60s ALASKA DISPATCH

1. OPEN WITH A STAKE in the first 1 to 2s: a question or a hard fact that only finishing resolves (an
   open loop / Zeigarnik). Never open with context.
2. VOICE FIRST; time every visual to the locked VO.
3. ONE IDEA PER SHOT, and let the shot's label read like a chapter (a sense of progress retains).
4. ILLUSTRATE THE NARRATION LITERALLY, then keep it moving (§2, §4).
5. NEVER LET THE FRAME REST (§1, §4).
6. SOUND IS SENTENCE-LEVEL PUNCTUATION (§5); music is a steady, arced floor (§6).
7. FRAME IT AS A MINI-DOC with momentum (a "here is what happened" spine), not a lecture.
8. END DESIGNED: wordmark + tagline + source, motion running to the last frame, clean resolve.

(What we do NOT copy: their flat recycled-asset template look. Our divergence + illustration-craft
bars still hold. We take their FLOW and SOUND discipline, not their house style.)

---

## 8. ANTI-PATTERNS (any one of these is a defect)

- ORPHAN NARRATION: the VO says something the screen is not showing. Fix: give that sentence a beat.
- STATIC HOLD > 5s: the picture stops advancing while the VO or music continues. Fix: schedule a change.
- MOTION WITHOUT MEANING: drift/zoom that reveals nothing, to fake "activity." Fix: make the move reveal.
- ONE DENSE TABLEAU: the whole diagram appears at once and the VO talks over it. Fix: progressive disclosure.
- SFX CLUTTER ("1998 PowerPoint on caffeine"): a sound on everything, or 4+ similar sounds at once. Fix:
  restraint + the Law of Two-and-a-Half; a sound only on story-advancing events.
- SILENT PICTURE: visual events with no paired sound. Fix: pair the five elemental SFX to the beats.
- MUSIC FIGHTING VO: a bed that masks consonants. Fix: duck + EQ the 2 to 4 kHz band under speech.

---

## 9. HOW IT IS ENFORCED (plan it, then verify it, same as divergence + shot structure)

PREPRODUCTION (Phase 4.5 storyboard):
- The beat map is written to the §3 schema: 12 to 16 timed beats, each with vo + shows + sfx + means,
  start-to-start gaps <= 5s, covering the VO timeline.

GATE 0A OBJECTIVE (scripts/storyboard_check.py) adds FLOW checks:
- every beat has t/vo/shows/sfx/means; beat start-to-start gap <= 5.0s; beats cover the runtime with no
  un-illustrated gap > 5s; every beat sfx is concrete (not "music"/empty).

GATE 0B TASTE + a NEW `flow-critic` agent (no-spawn):
- reads the VO script against the beat map and asks: is every sentence illustrated (say-it-show-it)?
  does something story-advancing change at least every 5s? does each beat name a motivated sound? It
  runs again in post on the rendered montage: does the picture actually flow, or does it stall?

GATE A OBJECTIVE (quality_gate.py) keeps EVENT_CADENCE + BEAT_DENSITY + SCENE_STRUCTURE and adds:
- SFX_EVENTS: validate `out/dispatch/sfx_events.json` (emitted after the master), and confirm each
  performed event produced a measurable level lift in those exact master bytes, with >= 1 event per shot. A silent
  picture (events planned, none audible) FAILS.

None of these thresholds get relaxed to pass. If the plan or the render misses the flow bar, you
redesign or re-render, exactly as with the divergence and oner gates.

---

## SOURCES
- The Infographics Show / Dark Matter Design: founder interview (TorrentFreak 2024), company profile
  (RocketReach), format + pacing analyses (Ad-Hoc News), animator pipeline (Two Fresh voiceover-first),
  vidIQ channel stats.
- Kurzgesagt / Epic Mountain sound design (10.studio, epic-mountain.com, Kottke).
- SFX + audio-visual craft: SFXEngine (sync, VO tips, timing), RMCAD, HookSounds, The Sketch Effect,
  Krotos, Michael Musco (layered scoring), Ableton Making Music (dramatic arc).
- Perception + engagement research: Walter Murch Law of Two-and-a-Half (StudioBinder / Melissa Pons),
  PLOS ONE (audio-visual congruency and recall), MDPI (audio-visual congruence and short-video
  engagement), PMC (perceived audio-visual synchrony).
- Loudness: -14 LUFS program (YouTube), AES/Apple VO references.
