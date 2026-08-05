import React from 'react';

// =============================================================================
// ABSENCE — the library's grammar for A THING THAT IS NOT THERE.
// CRAFT ADVANCE 2026-08-05 ("The Net Comes First").
//
// WHY THIS IS A SYSTEM AND NOT A PROP. This shelf has paid for the same lesson
// twice and solved it once, inline, for one animal:
//
//   2026-07-26  records.tsx ThreePipeCutaway drew a capped pipe meaning "no
//               record comes back". TWO panel judges found it did not read as
//               an absence at sampled frames. The manifest still carries that
//               as a live known weakness.
//   2026-07-30  underice.tsx RingedSealGhost solved it properly for a seal:
//               a DASHED contour (a solid outline reads as a style choice, a
//               dashed one reads as not filled in), a TRUE VOID interior with
//               no hatch, and a CALLER-SUPPLIED LABEL so the absence is named
//               rather than inferred.
//
// That solution was correct and it was welded to one species. Any later film
// needing to draw a thing that is not there had to re-improvise it, which is
// exactly how the 07-26 weakness stayed open. So it is generalised here.
//
// THE FOURTH THING, added by this run. The three rules above make an absence
// read as unfilled. They do not stop it reading as UNFINISHED, which is the
// specific way the ThreePipeCutaway failed: a static dashed outline in a world
// of form-shaded solids looks like an asset that did not render. The fix is
// MOTION THAT ONLY AN ABSENCE HAS. The dash phase crawls, and the interior
// carries a slow sparse drift going nowhere. A solid never does that, so the
// eye reads "this one is a different KIND of thing" rather than "this one is
// broken".
//
// The label is a REQUIRED prop, not an optional one. That is deliberate and it
// is the whole 07-30 lesson: an unlabelled absence is indistinguishable from an
// oversight, and a caller who has to type the label has to decide what the
// missing thing IS.
// =============================================================================

const hash = (s: string) => Math.abs([...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 7));
const uid = (s: string) => 'ab' + hash(s).toString(36);

/** the void is never pure black: it is the page showing through, one step down */
export const VOID_TINT = 'rgba(16,26,23,0.10)';

export interface UnnamedProps {
  /** the silhouette, as an SVG path in the caller's own local coordinates */
  d: string;
  /** REQUIRED. What is missing. An unlabelled absence reads as an oversight. */
  label: string;
  f: number;
  x?: number;
  y?: number;
  scale?: number;
  /** contour colour. Defaults to the ink of the world it sits in. */
  color?: string;
  /** 0 = fully dashed (an absence), 1 = solid (a normal outline). Animate it to FILL IN. */
  solid?: number;
  /** 0..1 how much the interior drifts. 0 gives a dead hole, which is the failure mode. */
  drift?: number;
  /** decorrelates the dash crawl and the drift between instances */
  phase?: number;
  /** where the label sits relative to the form's own box */
  labelSide?: 'below' | 'above' | 'right';
  labelSize?: number;
  /** bounding width of the path, so the label can centre itself without measuring */
  wide?: number;
  /** bounding height, for below/above placement */
  tall?: number;
  strokeWidth?: number;
}

/**
 * Render ANY silhouette as a STATED ABSENCE.
 *
 * The contract, and every clause of it is a defect somebody already found:
 *   1. DASHED, never solid, and the dash phase CRAWLS.
 *   2. TRUE VOID interior. No hatch, no fill, no tint beyond the faintest
 *      page-through, because a hatched absence reads as a material.
 *   3. A DRIFT inside the void, slow and sparse and going nowhere.
 *   4. A LABEL, always, supplied by the caller.
 */
export const Unnamed: React.FC<UnnamedProps> = ({
  d, label, f, x = 0, y = 0, scale = 1, color = '#101A17',
  solid = 0, drift = 1, phase = 0, labelSide = 'below', labelSize = 22,
  wide = 200, tall = 120, strokeWidth = 3,
}) => {
  const id = uid(`${label}${x}${y}`);
  // The dash crawl is deliberately on an irrational period against the drift so
  // the two never re-phase and the form never reads as a loop.
  const crawl = -(f * 0.55 + phase * 37) % 1000;
  // solid=1 collapses the gap to zero, so the SAME path can animate from an
  // absence into a filled outline without swapping components mid-shot.
  const dashOn = 11 + solid * 40;
  const dashOff = Math.max(0, 9 * (1 - solid));

  // Three interior motes on coprime-ish periods. They are the only thing inside.
  const motes = [0, 1, 2].map((i) => {
    const p = phase * 1.7 + i * 2.3;
    return {
      cx: Math.sin(f / (61 + i * 13) + p) * wide * 0.22,
      cy: Math.cos(f / (73 + i * 11) + p * 1.4) * tall * 0.18,
      r: 2.2 + i * 0.5,
      o: (0.28 - i * 0.06) * drift,
    };
  });

  const labelY = labelSide === 'below' ? tall * 0.5 + labelSize + 10
    : labelSide === 'above' ? -(tall * 0.5 + 12) : 0;
  const labelX = labelSide === 'right' ? wide * 0.5 + 14 : 0;
  const anchor = labelSide === 'right' ? 'start' : 'middle';

  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <defs>
        <clipPath id={`${id}-clip`}>
          <path d={d} />
        </clipPath>
      </defs>

      {/* 2. the interior is a TRUE VOID. This is the page showing through, not a fill. */}
      <path d={d} fill={VOID_TINT} />

      {/* 3. the drift. Without this the void is a dead hole and reads as unrendered. */}
      {drift > 0 && (
        <g clipPath={`url(#${id}-clip)`}>
          {motes.map((m, i) => (
            <circle key={i} cx={m.cx} cy={m.cy} r={m.r} fill={color} opacity={m.o} />
          ))}
        </g>
      )}

      {/* 1. the DASHED contour, crawling */}
      <path
        d={d}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        strokeLinecap="round"
        strokeDasharray={`${dashOn} ${dashOff}`}
        strokeDashoffset={crawl}
        opacity={0.86}
      />

      {/* 4. the LABEL. Required, so the absence is named rather than inferred. */}
      <text
        x={labelX}
        y={labelY}
        textAnchor={anchor}
        fill={color}
        opacity={0.8}
        style={{font: `700 ${labelSize}px "JetBrains Mono", ui-monospace, monospace`, letterSpacing: 1}}
      >
        {label}
      </text>
    </g>
  );
};

/**
 * A FIELD of absences, for the beat where the missing thing is a POPULATION
 * rather than one item.
 *
 * Deterministic imul-free hash scatter, never Math.random, so the field is
 * identical on every frame and every re-render. The whole point of the shot it
 * was built for is that the field runs off the top of frame, so `rows` is
 * allowed to overflow the box on purpose.
 */
export const UnnamedField: React.FC<{
  d: string;
  f: number;
  count: number;
  x: number;
  y: number;
  w: number;
  h: number;
  cell?: number;
  color?: string;
  scale?: number;
  /** 0..1, how many of them have resolved into named solids (from the left) */
  resolved?: number;
}> = ({d, f, count, x, y, w, h, cell = 86, color = '#101A17', scale = 0.34, resolved = 0}) => {
  const cols = Math.max(1, Math.floor(w / cell));
  const items = [];
  for (let i = 0; i < count; i++) {
    const c = i % cols;
    const r = Math.floor(i / cols);
    const j = hash(`f${i}`);
    const jx = ((j % 17) - 8) * 0.9;
    const jy = ((Math.floor(j / 17) % 17) - 8) * 0.9;
    const isSolid = i / count < resolved;
    items.push(
      <g key={i} transform={`translate(${c * cell + jx},${r * cell + jy}) scale(${scale})`}>
        <path
          d={d}
          fill={isSolid ? color : VOID_TINT}
          stroke={color}
          strokeWidth={isSolid ? 6 : 11}
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeDasharray={isSolid ? undefined : '30 24'}
          strokeDashoffset={isSolid ? undefined : -(f * 0.5 + i * 13) % 1000}
          opacity={isSolid ? 0.95 : 0.88}
        />
      </g>,
    );
  }
  return <g transform={`translate(${x},${y})`} clipPath={undefined}>{items}</g>;
};
