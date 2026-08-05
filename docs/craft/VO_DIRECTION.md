# THE VO DIRECTION PROCESS — how to write expression on purpose (not by guessing)

The narrator must sound like a real person: warm, varied, human, tone rising and falling with the
meaning. Gemini native TTS can do that, but ONLY if the delivery is DESIGNED. This is the repeatable
method the VO director follows to turn a finished script into an expressive, synth-ready read. It is
a process with checks, not a vibe. The sound check (scripts/vo_soundcheck.py) enforces the result.

Engine facts this process is built on (verified against ai.google.dev/gemini-api/docs, July 2026):
- Model: `gemini-3.1-flash-tts-preview` (most expressive, the audio-tag system) is primary;
  `gemini-2.5-pro-preview-tts` (Google's "professional narration / natural prosody" model, same
  price) is the fallback on 500s. Voice: `Sulafat` (warm) is the locked default.
- Emotion is steered by the STYLE PROMPT (director's notes), NOT by emotion tags. Google warns some
  emotion tags get SPOKEN ALOUD ("vocalized markup") and that vague prompts make the model read the
  notes aloud. So notes carry the emotion; inline tags are reserved for pacing/breath.
- The whole VO is ONE call (a 60s script is far under the 8,192-token input limit). One call is what
  gives natural sentence-to-sentence flow. Never synthesize line-by-line and glue clips.
- TTS is nondeterministic (no seed/temperature) and randomly 500s. So: render N takes, sound-check
  each, keep the best. All output carries a SynthID watermark (disclose it in credits).

## Step 1 — Set the narrator (once per piece)

Pick ONE narrator profile and keep it for the whole read; it grounds the model. Default:
`config/voices.yaml` narrator block (name, one-line persona, accent, baseline pace). Default persona:
"Nora, an Alaska public-radio host: warm, grounded, quietly witty." A named narrator performs more
consistently than an unnamed one.

## Step 2 — Read the script against the ANGLE, mark the arc

Read the locked VO script and the episode `angle` (Phase 3.5). Mark the emotional arc: where the hook
pulls, where it builds, where it turns, where it lands. Expression serves the angle. A celebratory
angle rises; a cautionary one leans in; a wry one keeps a half-smile. Do not impose a mood the angle
doesn't earn.

## Step 3 — Tag every line's INTENT (fixed taxonomy)

For each line/sentence, label its communicative job. Intent drives delivery:

| Intent | Job | Default delivery |
|---|---|---|
| HOOK | pull the viewer in | curious, forward lean, a touch brighter |
| SETUP | give context | even, informative, unhurried but moving |
| STAT | land a number | slight slow on the number, emphasis on the figure, don't rush it |
| REVEAL/CONTRAST | the flip or surprise | a beat before, then a shift in energy from the line before |
| WRY/ASIDE | dry humor, irony | lighter, a half-smile, slightly quicker throwaway |
| STAKES | why it matters | grounded, a little slower, warmer or firmer |
| BUTTON/CTA | the closing line/question | direct to camera, land it clean, warm |

## Step 4 — Map intent to concrete DELIVERY per line

For each line choose, deliberately:
1. EMPHASIS: the ONE load-bearing word the meaning hangs on. Mark it. (Emphasis is achieved by the
   style-prompt direction and word order, not by SHOUTING or ALL-CAPS in the spoken text.)
2. ENERGY: a level 1-5 (1 = quiet/reflective, 5 = bright/urgent). Write it down.
3. PACE: inherit the brisk baseline; only slow a specific line if STAT or STAKES earns it.
4. BREATH/PAUSE: mark where a natural breath or a `[short pause]` genuinely helps a beat land. Sparse.

## Step 5 — The CONTRAST rule (this is what kills monotone)

No two adjacent lines may sit at the same ENERGY level. Human reads fluctuate; flat reads are the
tell. If the arc leaves two neighbors equal, nudge one (a wry aside after a stat, a lift into the
hook, a settle into the stakes). The sound check measures pitch variance against a floor; this step
is how you clear it by design, not luck.

## Step 6 — Choose the MINIMAL, VETTED markup

Emotion goes in the director's notes (Step 7). Inline tags are used sparingly and ONLY from the
vetted palette below (confirmed to perform, not get spoken, for our voice). Over-tagging fights the
model. Rule of thumb: at most one inline tag per 1-2 sentences; many lines need none.

VETTED INLINE PALETTE (start here; promote a new tag only after the sound check proves it is not
spoken for Sulafat across a few takes):
- Pacing/breath: `[short pause]`, `[sighs]` (rare), a genuine `[laughs]` only if the line truly earns it.
- Light performance cues that tested clean on Sulafat: `[curious]` (hook), `[wry]` (aside). Use once
  or twice, not every line.
- BANNED as inline (put these in the notes instead, they risk being read aloud): [excited], [serious],
  [warmly], [happy], [sad], and any multi-word direction like [sarcastically, one slow word...].
- Placement rules: lowercase in square brackets, inline immediately before the span; separate tags
  with text or punctuation; NEVER place two tags adjacent.
- **NEVER START A LINE WITH A TAG.** A tag needs spoken words in front of it on the same line.
  MEASURED 2026-08-05: in one probe take the model spoke the words "short pause" aloud, and the
  only tag it did that to was the one line-initial `[short pause]` in the script. The identical
  tag mid-line, after a period, was read correctly in the same take and in every other take.
  A tag opening a line looks like a heading; a tag after "...isn't the gap. [short pause] Somebody
  already..." looks like a stage direction inside prose. Move it after the first clause, or drop it
  and let the period do the work.

## Step 7 — Assemble the PROMPT (exact structure)

```
Read ONLY the transcript below aloud as speech. The lines above "Transcript:" are direction; never speak them.
# AUDIO PROFILE: <narrator name + one-line persona>
### DIRECTOR'S NOTES
Style: <warm, natural, conversational, the angle's emotional register, dry wit where earned>
Pace: MEASURED and unhurried. THIS IS A TWO MINUTE PIECE, about one hundred and twenty seconds, and
the read must FILL it, so give every sentence room to land and take a real breath at every period.
Do not rush the numbers. Vary the tone line to line so no two sentences sound the same.
Emphasis: lean on the key word in each line; let numbers land.
Transcript:
<the annotated script: the exact spoken words + the sparse vetted inline tags from Steps 4-6>
```

The preamble + the `Transcript:` delimiter are REQUIRED (they stop the model reading the notes aloud).
`scripts/vo_synth_gemini.py` REPAIRS a prompt that is missing either one, or missing the Style /
Pace / AUDIO PROFILE blocks, or whose transcript does not match the plan's lines, or whose Pace
line does not NAME the target runtime. See `repair_prompt`. It rebuilds from the plan, salvaging
whatever of the notes is still good, and prints and records every repair in `vo_report.json`.

It repairs rather than refuses ON PURPOSE, and an earlier version of it got this wrong. THE ONE
OUTCOME LAW (`scripts/no_exit.py`) says the only terminal state is a delivered video, and a
damaged prompt is not a reason to have no video: every part of the prompt is recoverable from the
plan plus the template below, so recovering it is mechanical. Do not turn this back into a gate.

The repair exists because on 2026-08-05 a hand-patch of this prompt cut it at the first occurrence
of the substring `Transcript:` — which appears inside the preamble's own sentence — and silently
deleted every block above. The film shipped narrated with no direction at all.
**Never split this prompt on the bare substring; split on the newline-delimited form.**

### THE PACE LINE MUST NAME THE RUNTIME. It is the only reliable length control we have.

MEASURED 2026-08-05 by `scripts/vo_length_probe.py`, same model, same voice, same 288-word script:

| pace line | takes | rate |
|---|---|---|
| the old "BRISK and energetic..." | 104.8s, 105.2s, 106.3s | 163-165 wpm |
| the anchored line above, naming 120 seconds | **121.3s, 119.9s** | 142-144 wpm |

A 15 percent pace difference from one sentence, and it is the difference between a 105-second
film and a 120-second one. Two further findings from the same probe:

- **Within one prompt the rate is stable to 1.4 percent.** The read is not a lottery. What moved
  the rate across the archive from 136 to 165 wpm was the DIRECTOR'S NOTES being rewritten from
  scratch every run, so the format's runtime depended on how verbose one agent felt that day.
  Keep the Pace paragraph verbatim; write your own Style line.
- **The fast read is a worse read.** At 165 wpm the ASR misheard "the day it arrives" as "the
  data", "profiled him" as "profile tim", and "summer" as "somewhere". At 143 wpm none of those
  errors occurred. Slowing down buys intelligibility, not just seconds.

**The pace paragraph is GENERATED from `config/state.yaml`** by `vo_synth_gemini._pace_line()`, so
changing the format target moves it automatically. `scripts/format_gate_selftest.py` asserts the
generated text stays byte-identical to the string that was actually measured, so the two cannot
drift apart and leave the pipeline shipping a pace instruction nobody ever timed.

**If the format's target runtime changes, re-run the probe.** Do not extrapolate a word count from
an old rate; the rate is a property of this paragraph.

## Step 8 — Emit the plan, then synth, then CHECK, then maybe re-plan

Write `out/dispatch/vo_direction.json`:
`{ narrator, notes, style_prompt, lines: [{ idx, text, intent, emphasis, energy, tags, pause_before }],
   assembled_prompt }`

Then scripts/vo_synth_gemini.py renders N takes (3.1-flash primary, 2.5-pro fallback, retry on 500),
and scripts/vo_soundcheck.py scores each and keeps the best. The check enforces THIS process:
- Word accuracy (ASR vs the spoken script): catches drops / the 500 text fallback.
- No spoken tags/notes: catches leakage (Step 6/7 failure).
- Monotone floor (pitch std-dev): catches a flat read (Step 5 failure) — if it fails, add contrast
  to the plan and re-synth, do not just re-roll blindly.
- Duration + loudness: pace on target, broadcast-safe level.

If the best take still fails a check, the FIX IS IN THE PLAN (more contrast, move an emphasis, drop a
leaking tag), then re-synth. That feedback loop is what makes this a process and not a one-shot guess.
