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
