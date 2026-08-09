import React from 'react';

/**
 * THE SIMULATION GRAMMAR — how this engine draws a thing that exists only as a MODEL.
 * =================================================================================
 * CRAFT ADVANCE 2026-08-09 ("The Method, Not The Metal").
 *
 * WHY THIS IS A LIBRARY AND NOT A SCENE HELPER. This channel has drawn a modelled thing
 * four times and improvised it four separate times: the 2026-07-25 landslide digital twin,
 * the 07-30 glider's dead-reckoned position, the 08-06 capacity ceiling that was a ceiling
 * and not a count, and now a Virtual Pilot Plant. `absence.tsx` exists for exactly this
 * reason on the other half of the problem — the shelf paid twice for "how do you draw a
 * thing that is not there" before somebody made it a component. This is that fix applied to
 * "how do you draw a thing that is not REAL YET", which is a different claim and needs a
 * different grammar.
 *
 * ABSENCE says: this should be here and is not.
 * SIMULATION says: this is here, it is exact, and it is made of arithmetic.
 *
 * THE CONTRACT. Four clauses, and each one is a defect somebody has already found:
 *
 *   1. HAIRLINE STROKES OF UNIFORM WIDTH THAT IGNORE THE SCENE'S LIGHT. A form-shaded model
 *      reads as a real object, which is the whole confusion this component exists to prevent.
 *      The stroke does not thicken toward the light and does not thin away from it.
 *
 *   2. NO CONTACT AND NO SHADOW, EVER. A cast shadow is the single strongest cue that a thing
 *      is physically present, which is why DISPATCH_STANDARD section 1 makes it mandatory for
 *      everything real. So it is forbidden here, and the component simply has no prop for it.
 *
 *   3. A CONTINUOUS RE-SOLVE. The linework redraws on an irrational period. This is the clause
 *      absence.tsx paid for with its drift layer: a STATIC wireframe in a world of form-shaded
 *      solids does not read as "a model", it reads as an asset that failed to render. A model
 *      is a thing that is being computed, so it has to look like it is being computed.
 *
 *   4. A REQUIRED `fidelity` PROP, NOT OPTIONAL. The caller has to state how well the modelled
 *      thing is actually known, because on this film that is the argument. Low fidelity
 *      visibly loosens the linework: the segments hunt around their true position instead of
 *      sitting on it. Making it required means a scene cannot draw a model without deciding
 *      how much it trusts it.
 *
 * DETERMINISM: every wobble comes from an imul hash of (segment index, frame bucket, seed).
 * Never Math.random — a re-render must produce the identical frame.
 */

/** The reserved hue. NOTHING PHYSICAL IN THIS FILM MAY BE PAINTED THIS COLOUR. */
export const SIM = '#C6F24A';
export const SIM_DEEP = '#7FA32B';

/** deterministic hash -> [-1, 1] */
const wob = (a: number, b: number, seed: number): number => {
  let h = Math.imul(a + 0x9e37, 0x85ebca6b) ^ Math.imul(b + 0x27d4, 0xc2b2ae35);
  h = Math.imul(h ^ (h >>> 13), 0x165667b1);
  return (((h ^ (h >>> 16)) >>> 0) / 4294967295) * 2 - 1;
};

/**
 * THE RE-SOLVE JITTER, exported because scenes need to park other things on the same
 * motion so a simulated readout and a simulated outline agree with each other.
 *
 * `fidelity` 1 = the model sits still on its true position (well known).
 * `fidelity` 0 = it hunts around it by several pixels and never settles (barely known).
 * The period is irrational against the dash crawl so the two never re-phase.
 */
export function resolveJitter(f: number, idx: number, fidelity: number, seed = 0): {dx: number; dy: number} {
  const loose = Math.max(0, Math.min(1, 1 - fidelity));
  if (loose < 0.001) return {dx: 0, dy: 0};
  // step the target every ~7 frames, then EASE toward it, so it hunts rather than vibrates
  const step = f / 6.7;
  const i = Math.floor(step);
  const frac = step - i;
  const e = frac * frac * (3 - 2 * frac); // smoothstep between successive targets
  const ax = wob(idx, i, seed), ay = wob(idx + 977, i, seed);
  const bx = wob(idx, i + 1, seed), by = wob(idx + 977, i + 1, seed);
  const amp = 5.5 * loose;
  return {dx: (ax + (bx - ax) * e) * amp, dy: (ay + (by - ay) * e) * amp};
}

export interface SimulatedProps {
  /** the silhouette, as SVG path data in the caller's own local coordinates */
  d: string;
  /**
   * REQUIRED. 0..1, how well the modelled thing is actually known. This is not a style
   * knob. A caller that has to type it has to decide what the model is worth.
   */
  fidelity: number;
  f: number;
  x?: number;
  y?: number;
  scale?: number;
  /** decorrelates the crawl and the jitter between instances */
  phase?: number;
  /** 0..1, how much of the outline has been drawn. Animate it to DRAW ITSELF into being. */
  drawn?: number;
  color?: string;
  strokeWidth?: number;
  /** optional interior fill at very low alpha, for a model that is meant to read as occupied */
  occupied?: number;
  children?: React.ReactNode;
}

/**
 * Render ANY silhouette as A STATED MODEL.
 *
 * Deliberately has NO shadow prop, NO contact prop and NO light prop. Those absences are
 * the contract, not an oversight, and adding one later would quietly turn this back into a
 * way of drawing real objects.
 */
export const Simulated: React.FC<SimulatedProps> = ({
  d, fidelity, f, x = 0, y = 0, scale = 1, phase = 0, drawn = 1,
  color = SIM, strokeWidth = 2.2, occupied = 0, children,
}) => {
  const loose = Math.max(0, Math.min(1, 1 - fidelity));
  // Clause 3: the outline is always being computed. The crawl runs on an irrational
  // period against resolveJitter's 6.7-frame step so the two never re-phase.
  const crawl = -(f * 0.9 + phase * 53) % 4000;
  // `drawn` gates how much of the path exists yet, which is how the twin builds itself.
  const dr = Math.max(0, Math.min(1, drawn));
  const j = resolveJitter(f, Math.round(phase * 17), fidelity, 3);
  // a loose model breathes its opacity too, because an uncertain value is not a steady one
  const flick = 1 - loose * 0.22 * (0.5 + 0.5 * Math.sin(f / 5.3 + phase));

  return (
    <g transform={`translate(${x + j.dx},${y + j.dy}) scale(${scale})`} opacity={flick}>
      {occupied > 0 && (
        <path d={d} fill={color} opacity={0.07 * occupied} stroke="none" />
      )}
      {/* the emission halo. NOT a light on the scene: it never reaches another object,
          which is how a viewer reads it as self-lit rather than lit. */}
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth * 3.2}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={0.1}
        pathLength={1000}
        strokeDasharray={`${dr * 1000} 1000`}
      />
      {/* Clause 1: hairline, uniform, unlit. */}
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        pathLength={1000}
        strokeDasharray={`${dr * 1000} 1000`}
      />
      {/* the re-solve tick: a short bright arc that keeps travelling the outline, so even a
          held model is visibly being recomputed rather than sitting as a still photograph */}
      <path
        d={d}
        fill="none"
        stroke="#EAFFB0"
        strokeWidth={strokeWidth * 0.9}
        strokeLinecap="round"
        pathLength={1000}
        strokeDasharray={`${28 + loose * 40} ${972 - loose * 40}`}
        strokeDashoffset={crawl}
        opacity={dr > 0.98 ? 0.75 : 0}
      />
      {children}
    </g>
  );
};

/**
 * A POPULATION OF MEASUREMENTS — the model seen as what it is actually made of.
 *
 * `filled` is how many of the `cells` have a measurement behind them. The empty ones are
 * drawn as empty rather than omitted, because the gap between the grid's size and its
 * fill is the only honest way to draw "compressed measurements, and little to compress".
 */
export const SimField: React.FC<{
  f: number; x: number; y: number; w: number; h: number;
  cols: number; rows: number; filled: number;
  phase?: number; color?: string; sweep?: number;
}> = ({f, x, y, w, h, cols, rows, filled, phase = 0, color = SIM, sweep = 1}) => {
  const cw = w / cols, ch = h / rows;
  const total = cols * rows;
  const nFill = Math.round(Math.max(0, Math.min(1, filled)) * total);
  // the scan runs left to right on its own slow period and lights only what is filled
  const scanX = ((f * 2.1 + phase * 90) % (w + 240)) - 120;
  const cells: React.ReactNode[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      // deterministic scatter of WHICH cells are filled, so it never looks like a bar
      const rank = ((Math.imul(i + 31, 2654435761) >>> 0) % total);
      const isFilled = rank < nFill;
      const cx = x + c * cw, cy = y + r * ch;
      const lit = sweep > 0 && Math.abs(cx + cw / 2 - (x + scanX)) < 46 ? 1 : 0;
      cells.push(
        <rect
          key={i}
          x={cx + 1.5}
          y={cy + 1.5}
          width={cw - 3}
          height={ch - 3}
          fill={isFilled ? color : 'none'}
          fillOpacity={isFilled ? 0.2 + 0.55 * lit : 0}
          stroke={color}
          strokeWidth={0.9}
          strokeOpacity={isFilled ? 0.75 : 0.24}
        />,
      );
    }
  }
  return <g>{cells}</g>;
};
