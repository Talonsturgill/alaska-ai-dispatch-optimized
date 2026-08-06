import React from 'react';
import {spring, interpolate} from 'remotion';

// =============================================================================
// MOTION — the animation-principles layer (squash & stretch, anticipation,
// overshoot, secondary follow-through). Every judge pass on the first episodes
// said some version of "sprites scale but don't articulate; nothing follows
// through." This module fixes that at the KIT level so every element inherits
// real animation physics instead of a linear scale-in.
//
//   entrance()      one-call juiced entrance: anticipation dip -> overshoot ->
//                   settle, with volume-preserving squash/stretch and a vertical
//                   velocity you can feed straight into lighting.MotionBlur.
//   followThrough() damped oscillation for attached parts (flags, arms, tags,
//                   antennae) that keeps moving after the parent stops.
//   squashStretch() volume-preserving deformation from a velocity scalar.
//   accentKick()    a short punch (scale or rotation) at an exact frame — built
//                   for VO emphasis accents (see lib/voice.tsx).
//
// All pure functions of frame -> deterministic under Remotion's parallel render.
// =============================================================================

export type SpringPreset = {damping: number; stiffness: number; mass?: number};
export const POP: SpringPreset = {damping: 10, stiffness: 160};      // snappy UI pop
export const SNAP: SpringPreset = {damping: 14, stiffness: 220};     // hard smash-in
export const SETTLE: SpringPreset = {damping: 16, stiffness: 90};    // gentle ease

export interface Entrance {
  /** overall scale to apply (includes overshoot) */
  scale: number;
  /** volume-preserving deform: use transform scale(sx, sy) AFTER `scale` */
  sx: number;
  sy: number;
  /** vertical offset px (drop-in travel), 0 when settled */
  dy: number;
  /** per-frame vertical velocity px — feed to MotionBlur vy */
  vy: number;
  /** 0..1 progress (spring value, overshoots past 1) */
  t: number;
  /** true once visually present (skip rendering before to save nodes) */
  on: boolean;
}

/**
 * The one-call juiced entrance. Anticipation (small pre-dip), spring overshoot,
 * squash on arrival, stretch during fast travel, settle. Drop-in distance and
 * spring preset tunable. Usage:
 *   const e = entrance(f, fps, 20, {drop: 140});
 *   <MotionBlur vy={e.vy}><g transform={`translate(0,${e.dy}) scale(${e.scale})
 *     scale(${e.sx},${e.sy})`}>...</g></MotionBlur>
 */
export function entrance(
  frame: number, fps: number, delay: number,
  opts: {drop?: number; preset?: SpringPreset; anticipation?: boolean} = {},
): Entrance {
  const {drop = 0, preset = POP, anticipation = true} = opts;
  const f = frame - delay;
  if (f < -8) return {scale: 0, sx: 1, sy: 1, dy: drop, vy: 0, t: 0, on: false};
  // anticipation: tiny shrink in the 8 frames before launch (only when visible from 0)
  if (f < 0) {
    const a = anticipation ? interpolate(f, [-8, 0], [1, 0.92]) : 1;
    return {scale: drop > 0 ? 0 : a, sx: 1, sy: 1, dy: drop, vy: 0, t: 0, on: drop === 0};
  }
  const t = spring({frame: f, fps, config: preset});
  const tPrev = spring({frame: Math.max(0, f - 1), fps, config: preset});
  const dy = drop * (1 - t);
  const vy = drop * (t - tPrev); // px per frame of travel
  // squash/stretch from normalized velocity: stretch while moving, squash at impact
  const v = Math.min(1, Math.abs(vy) / 28);
  const impact = Math.max(0, t - 1); // overshoot amount = arrival energy
  const k = v * 0.18 - impact * 0.35; // + stretch in flight, - squash on overshoot
  const sy = 1 + k;
  const sx = 1 / Math.max(0.6, sy); // preserve area
  return {scale: Math.min(t, 1) + impact * 0.6, sx, sy, dy, vy, t, on: true};
}

/** Volume-preserving squash/stretch from a signed velocity scalar (px/frame). */
export function squashStretch(v: number, gain = 0.012): {sx: number; sy: number} {
  const k = Math.max(-0.3, Math.min(0.3, v * gain));
  const sy = 1 + k;
  return {sx: 1 / Math.max(0.7, sy), sy};
}

/**
 * Damped oscillation for SECONDARY MOTION: a part attached to something that
 * just moved keeps swinging and settles late. Returns an angle (deg) or offset
 * you multiply into a rotate/translate of the attached part.
 *   const swing = followThrough(f, fps, delay, {amp: 14});
 *   <g transform={`rotate(${swing} ${pivotX} ${pivotY})`}>flag</g>
 */
export function followThrough(
  frame: number, fps: number, delay: number,
  opts: {amp?: number; freq?: number; decay?: number} = {},
): number {
  const {amp = 12, freq = 2.6, decay = 2.2} = opts;
  const t = (frame - delay) / fps;
  if (t <= 0) return 0;
  return amp * Math.exp(-decay * t) * Math.sin(2 * Math.PI * freq * t);
}

/**
 * A short accent kick at an exact frame (for VO emphasis beats): rises fast,
 * decays over ~0.4s. Returns 0..1; scale/rotate/glow by it.
 */
export function accentKick(frame: number, fps: number, atFrame: number, dur = 0.42): number {
  const t = (frame - atFrame) / fps;
  if (t < 0 || t > dur) return 0;
  const up = Math.min(1, t / 0.06);
  const down = 1 - (t - 0.06) / (dur - 0.06);
  return Math.max(0, Math.min(up, down));
}

/** Continuous idle sway (breeze/breath) with per-instance phase, cheap + organic. */
export function idleSway(frame: number, phase = 0, amp = 2.5, period = 46): number {
  return amp * Math.sin((frame + phase * 13.7) / period * 2 * Math.PI)
    + amp * 0.4 * Math.sin((frame + phase * 7.3) / (period * 0.37) * 2 * Math.PI);
}

/**
 * vitals() — THE LIVING-IDLE PRIMITIVE (2026-07-26).
 *
 * Why this exists: the scorer panel flagged "held figures/heroes read thin on idle
 * life" on 2026-07-24 AND again on 2026-07-25, and both runs DEFERRED it. The
 * Character rig had already earned a layered weight-shift idle, but every
 * characterized-object hero in kit.tsx floated on a SINGLE fixed-period sine
 * (`const bob = 5 * Math.sin(f / 17)`). One sine at one period is why they read
 * mechanical: over any half-second window it barely moves, and two heroes on
 * screen bob in lockstep.
 *
 * The structural fix is a shared primitive rather than another doctrine note, so
 * a hero cannot be authored WITHOUT life. Three desynced layers on deliberately
 * IRRATIONAL period ratios (they never re-phase, so the loop never reads as a
 * loop): a slow primary drift, a mid breath, and a small fast micro-tremor.
 *
 *   `phase` — per-instance seed so two heroes in one shot never move in lockstep.
 *   `gain`  — scales the whole signal (0 freezes it: use for a deliberate
 *             held-breath//frozen story beat, matching Sourdough's `frozen`).
 *
 * Returns pixel/scale/degree-ready channels:
 *   bob    — vertical drift in px (feed the hero's translate y)
 *   swayX  — lateral weight-shift in px
 *   breath — a scale multiplier around 1 (feed a scaleY or whole-body scale)
 *   tilt   — degrees of body roll that TRACKS swayX, so the shift reads as
 *            weight moving, not a sprite sliding
 *   micro  — a raw -1..1 fast tremor for attached secondary parts (antennae,
 *            tags, cables) that should lag the body
 */
export function vitals(
  frame: number,
  phase = 0,
  gain = 1,
): {bob: number; swayX: number; breath: number; tilt: number; micro: number} {
  const p = phase * 2.399963; // golden-angle spread: nearby seeds decorrelate fast
  // Irrational period ratios (no common multiple => no visible re-phasing).
  const slow = Math.sin(frame / 37.3 + p);
  const mid = Math.sin(frame / 19.7 + p * 1.61);
  const fast = Math.sin(frame / 8.9 + p * 2.71);
  const bob = gain * (3.1 * slow + 1.3 * mid + 0.45 * fast);
  const swayX = gain * (2.2 * Math.sin(frame / 53.1 + p * 0.83) + 0.7 * mid);
  const breath = 1 + gain * 0.014 * (0.75 * mid + 0.25 * slow);
  // tilt tracks the lateral shift (weight moves, the body answers) with a small lag
  const tilt = gain * (1.15 * Math.sin(frame / 53.1 + p * 0.83 - 0.35) + 0.3 * fast);
  return {bob, swayX, breath, tilt, micro: fast};
}

// ---------------------------------------------------------------------------
// humanIdle() — STILLNESS PUNCTUATED BY EVENTS (2026-08-06)
//
// WHY THIS EXISTS, and why it is a different SHAPE of thing rather than better
// numbers. The owner, on the shipped films: characters "float around and move in
// a weird cyclical way, they don't move like normal humans, or have any
// mannerisms ... a bit boring".
//
// That is the correct diagnosis and the git history proves the point. Idle life
// has been "fixed" four times: 07-24 and 07-25 (both deferred), 07-26 after a
// judge measured a figure PIXEL-IDENTICAL across an 8-frame strip, 07-29 logged
// as a "REPEAT-OFFENDER FIX (third strike)", and 08-04 concluding "the
// amplitudes were never the problem, the PERIODS were". Every one of those fixes
// retuned sine constants. vitals() is five sines; Character's idle is three more.
//
// A sum of sines cannot look human no matter what you set the constants to,
// because it is smooth everywhere, symmetric in time, and NEVER AT REST. A person
// standing is mostly still. They hold a posture, then make a discrete move, then
// hold again. The move is fast out of the hold and slow into the next one, and it
// overshoots slightly before settling. None of those properties survive being
// written as A*sin(t/k), so tuning A and k forever cannot converge.
//
// So this models the behaviour instead of the waveform:
//
//   REST IS THE DEFAULT. Between events the figure is genuinely still, and that
//     stillness is what makes the next move read as a move.
//   EVENTS ARE DISCRETE AND IRREGULAR. Weight shifts land on discrete targets
//     (a hip, centre, the other hip) at seeded 2.6..8.0s intervals, never on a
//     period that can beat against another figure's.
//   MOVES ARE ASYMMETRIC AND OVERSHOOT. settle() leaves fast and arrives slow
//     with one small overshoot, which is what a mass on a joint actually does.
//   PARTS LAG. The head starts 0.08s after the torso, so the body leads and the
//     head follows. That single delay is most of what reads as "alive".
//   BREATH HAS A HOLD. Real breathing pauses at the top of the inhale. A sine
//     does not, which is why sine-breathing reads as a pulsing balloon.
//
// Drop-in compatible with vitals(): same five channels, same meanings, plus head
// and blink. gain=0 freezes everything for a deliberate held-breath beat.
// ---------------------------------------------------------------------------

/** Deterministic 0..1 from two numbers. No Math.random: renders must be reproducible. */
function h01(a: number, b: number): number {
  const x = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * Normalised asymmetric settle, 0 at u=0 and exactly 1 at u=1.
 * Leaves the old value fast, overshoots once, arrives slow. This is the single
 * most important function here: it is the difference between a body moving and a
 * value being interpolated.
 */
function settle(u: number): number {
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  const e = Math.exp(-4.2 * u) * Math.cos(5.6 * u);
  const e1 = Math.exp(-4.2) * Math.cos(5.6);
  return (1 - e) / (1 - e1);
}

/** Where a stepped channel sits now, given its seeded event schedule. */
function stepped(
  t: number, seed: number, minGap: number, maxGap: number,
  pick: (i: number, prev: number) => number, dur = 0.36,
): number {
  let evT = 0, prev = 0, cur = 0, start = -999, d = dur;
  for (let i = 0; i < 64; i++) {
    const gap = minGap + (maxGap - minGap) * h01(seed, i);
    const next = evT + gap;
    if (next > t) break;
    prev = cur;
    cur = pick(i, cur);
    start = next;
    d = dur * (0.8 + 0.5 * h01(seed + 3.1, i));
    evT = next;
  }
  return prev + (cur - prev) * settle((t - start) / d);
}

export interface HumanIdle {
  bob: number; swayX: number; breath: number; tilt: number; micro: number;
  /** head offsets in px; already lagged behind the torso */
  headX: number; headY: number;
  /** true on the frames an eyelid is down */
  blink: boolean;
  /** -1..1 which hip the weight is currently on, for a rig that wants it */
  weight: number;
}

export function humanIdle(frame: number, seed = 0, gain = 1, fps = 30): HumanIdle {
  const t = frame / fps;
  const s = seed * 2.399963 + 1.7; // golden-angle spread so neighbours decorrelate

  // WEIGHT. Discrete targets, long holds. A person does not slide continuously
  // between hips, they commit to one and stay there.
  const LEAN = [-1, -0.55, 0, 0.55, 1];
  const weight = stepped(t, s, 2.6, 8.0, (i, prev) => {
    let c = LEAN[Math.floor(h01(s + 7.3, i) * LEAN.length) % LEAN.length];
    if (Math.abs(c - prev) < 0.25) c = prev > 0 ? -0.55 : 0.55; // never re-pick the same hip
    return c;
  }, 0.40);

  // The torso answers the weight, and a shift costs a little height as the hip drops.
  const swayX = gain * 7.5 * weight;
  const tilt = gain * 2.6 * weight;
  const dip = gain * 1.6 * Math.abs(weight);

  // HEAD. Its own slower schedule of small look-arounds, PLUS a lagged copy of the
  // torso. The lag is the mannerism: body first, head after.
  const headLag = stepped(t - 0.08, s, 2.6, 8.0, (i, prev) => {
    let c = LEAN[Math.floor(h01(s + 7.3, i) * LEAN.length) % LEAN.length];
    if (Math.abs(c - prev) < 0.25) c = prev > 0 ? -0.55 : 0.55;
    return c;
  }, 0.40);
  const glance = stepped(t, s + 11.9, 1.9, 6.4,
    (i) => (h01(s + 5.5, i) - 0.5) * 2, 0.22);
  const headX = gain * (2.6 * headLag + 3.4 * glance);
  const headY = gain * -1.1 * Math.abs(glance);

  // BREATH. Rise, HOLD at the top, longer fall. The hold is what a sine cannot do.
  const cyc = 3.4 + 0.9 * h01(s, 99);
  const bp = ((t / cyc) % 1 + 1) % 1;
  let br: number;
  if (bp < 0.40) br = settle(bp / 0.40);
  else if (bp < 0.52) br = 1;
  else br = 1 - settle((bp - 0.52) / 0.48);
  const breath = 1 + gain * 0.011 * br;
  const bob = gain * (-1.5 * br) - dip;

  // BLINK. Irregular, per-figure, and fast. The rig this replaces used
  // ((f + 11) % 92) < 5 with NO phase term, so every character in a shot blinked
  // on the same frame, exactly every 3.067s, forever. Two people blinking in
  // perfect unison is one of the strongest uncanny signals there is, and it was
  // in every film this engine has shipped.
  let blink = false;
  {
    let evT = 0;
    for (let i = 0; i < 64; i++) {
      const gap = 1.8 + 4.9 * h01(s + 21.7, i);
      evT += gap;
      if (evT > t + 0.5) break;
      // occasional double-blink, which real faces do and metronomes never do
      const dbl = h01(s + 31.3, i) < 0.18;
      const on = t - evT;
      if ((on >= 0 && on < 0.11) || (dbl && on >= 0.20 && on < 0.30)) { blink = true; break; }
    }
  }

  // micro: tiny continuous tremor ONLY for attached secondary parts (tags, cables,
  // antennae) that should shimmer. Deliberately too small to move a body.
  const micro = Math.sin(t * 6.7 + s) * 0.35 + Math.sin(t * 11.3 + s * 1.7) * 0.15;

  return {bob, swayX, breath, tilt, micro, headX, headY, blink, weight};
}

/** Soft drop shadow group for HUD chips so they sit IN the lit scene (manifest note). */
export const ChipShadow: React.FC<{dx?: number; dy?: number; opacity?: number; children: React.ReactNode}> = ({
  dx = 5, dy = 9, opacity = 0.28, children,
}) => (
  <g>
    <g transform={`translate(${dx},${dy})`} opacity={opacity} style={{filter: 'brightness(0)'} as any}>
      {children}
    </g>
    {children}
  </g>
);

// ============================================================================
// ENGAGEMENT primitives (docs/craft/ENGAGEMENT.md §3-4, upgrade #3 2026-07-20).
// The research-backed motion vocabulary: named easing tokens (linear easing is
// BANNED outside continuous loops), the anticipate->disclose->hold reveal
// grammar, and the stagger cascade. All pure functions of frame/fps so they
// stay deterministic.
// ============================================================================

// Named easing tokens. Use with Remotion's interpolate(..., {easing: Easing.bezier(...EASE.enter)}).
// enter: strong ease-out (fast start, long soft tail) — every entrance.
// move: ease-in-out — on-screen repositioning.
// overshoot: passes the target then settles — ONE element per frame, usually the key number.
export const EASE = {
  enter: [0.16, 1, 0.3, 1] as const,
  move: [0.65, 0, 0.35, 1] as const,
  overshoot: [0.68, -0.55, 0.27, 1.55] as const,
} as const;

// anticipate(): the telegraph before a payoff. Returns a small OPPOSING offset
// (0..1 of `amp`, as a signed factor) for the `frames`-long wind-up ending at
// `payoffFrame`; 0 after the payoff starts. Apply against the payoff direction
// (e.g. scale 1 - 0.06 * anticipate(...) before a scale-up pop).
// Research: 6-12 frames at 30fps; longer build = suspense, shorter = snap.
export function anticipate(frame: number, payoffFrame: number, frames = 9): number {
  const start = payoffFrame - frames;
  if (frame < start || frame >= payoffFrame) return 0;
  const t = (frame - start) / frames;
  return Math.sin(t * Math.PI * 0.5);          // ramps 0 -> 1 into the payoff
}

// holdPayoff(): the still beat AFTER a reveal lands — the pause IS the
// punctuation. Returns 1 while inside the hold window (no new motion should
// start), else 0. Doctrine band: 0.4-0.8s.
export function holdPayoff(frame: number, fps: number, revealEndFrame: number, holdS = 0.6): number {
  return frame >= revealEndFrame && frame < revealEndFrame + holdS * fps ? 1 : 0;
}

// staggerDelay(): frames of delay for item i in a cascade. 60-90ms/item turns
// a simultaneous pop-in into a reading path. Caps the total cascade so late
// items never overrun the shot.
export function staggerDelay(i: number, fps: number, stepMs = 75, maxTotalS = 1.2): number {
  return Math.min(i * (stepMs / 1000), maxTotalS) * fps;
}
