import React from 'react';
import {INK} from './lighting';

// ============================================================================
// VISION — the MACHINE-VISION OVERLAY layer (CRAFT ADVANCE 2026-08-07)
//
// Why this exists: this channel keeps telling stories about machines that
// PERCEIVE (the satellite eye, the seismic ear, the plate reader, and now a
// robot that finds a fish's brain), and every one of those runs hand-rolled
// its own reticle inside its own episode file. Nothing compounded. This makes
// perception itself a first-class, parameterised library layer.
//
// The design rule that matters: a perception overlay is the ONLY EMISSIVE
// thing in a frame. It does not reflect the scene's light, it emits its own.
// So it is drawn with hairline strokes and a bloom that never washes out the
// subject underneath, and its color should appear nowhere else in the film.
//
// Anatomy, per docs/craft/DISPATCH_STANDARD.md §0: a reticle that has already
// locked is a still photograph. SearchReticle therefore never stops moving —
// it samples on an irrational period so a hold of any length still breathes.
// ============================================================================

export const CYAN = '#39d7e6';

const H = (n: number) => (Math.imul(n + 17, 2654435761) >>> 0) / 4294967295;

/** Deterministic drifting search point. Never rests, so a long hold cannot go quiet. */
export function searchDrift(f: number, seed = 0, amp = 26): {dx: number; dy: number} {
  const p = seed * 2.399963;
  return {
    dx: amp * (0.62 * Math.sin(f / 11.3 + p) + 0.38 * Math.sin(f / 4.7 + p * 1.7)),
    dy: amp * (0.55 * Math.cos(f / 13.9 + p * 1.3) + 0.31 * Math.sin(f / 6.1 + p * 2.2)),
  };
}

/**
 * The searching reticle. `lock` 0..1 drives it from hunting (wide, jittering,
 * sampling ghosts) to locked (tight, still-but-breathing, corner ticks in).
 */
export const SearchReticle: React.FC<{
  x: number; y: number; f: number; lock?: number; seed?: number;
  r?: number; color?: string; ghosts?: number; label?: string;
}> = ({x, y, f, lock = 0, seed = 0, r = 62, color = CYAN, ghosts = 5, label}) => {
  const L = Math.max(0, Math.min(1, lock));
  const d = searchDrift(f, seed, 26 * (1 - L));
  const rad = r * (1 - 0.42 * L);
  // corner ticks converge from outside; overshoot slightly at ~0.8 then settle
  const over = L < 0.8 ? L / 0.8 : 1 + (1 - (L - 0.8) / 0.2) * 0.08;
  const gap = rad * (1.85 - 1.0 * Math.min(1, over));
  const breathe = 1 + 0.018 * Math.sin(f / 9.1 + seed);
  return (
    <g transform={`translate(${x + d.dx},${y + d.dy})`} opacity={0.96}>
      {/* rejected candidates ghost out around the search — only while hunting */}
      {L < 0.92 && Array.from({length: ghosts}).map((_, i) => {
        const g = searchDrift(f + i * 37, seed + i * 3 + 1, 78 * (1 - L));
        const a = (1 - L) * 0.3 * (0.4 + 0.6 * H(i + seed));
        return <circle key={i} cx={g.dx} cy={g.dy} r={7} fill="none" stroke={color}
                       strokeWidth={2} opacity={a} />;
      })}
      {/* the bloom: soft, never washes the subject */}
      <circle r={rad * 1.5 * breathe} fill={color} opacity={0.06 + 0.10 * L} />
      {/* the ring. A PERFECT CIRCLE: the only one in this film. */}
      <circle r={rad * breathe} fill="none" stroke={color} strokeWidth={2.4}
              opacity={0.55 + 0.45 * L} strokeDasharray={L > 0.9 ? undefined : '7 9'} />
      <circle r={2.6 + 2.2 * L} fill={color} />
      {/* four converging corner ticks */}
      {[0, 90, 180, 270].map((a) => (
        <g key={a} transform={`rotate(${a})`}>
          <path d={`M${gap},-12 L${gap},12`} stroke={color} strokeWidth={3}
                opacity={0.35 + 0.65 * L} strokeLinecap="round" />
        </g>
      ))}
      {label && (
        <text x={0} y={rad + 34} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
              fontSize={22} fill={color} opacity={0.5 + 0.5 * L} letterSpacing={2}>{label}</text>
      )}
    </g>
  );
};

/** A mark that has NOT landed: dotted, unlit, and slowly rotating so it reads as waiting. */
export const PendingMark: React.FC<{
  x: number; y: number; f: number; r?: number; color?: string; label?: string; op?: number;
}> = ({x, y, f, r = 54, color = CYAN, label, op = 1}) => (
  <g transform={`translate(${x},${y})`} opacity={op}>
    <circle r={r} fill="none" stroke={color} strokeWidth={2.6} opacity={0.42}
            strokeDasharray="9 13" strokeDashoffset={-f * 0.5} />
    <circle r={r * 0.16} fill="none" stroke={color} strokeWidth={2.2} opacity={0.42} />
    {label && (
      <text x={0} y={r + 32} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
            fontSize={20} fill={color} opacity={0.45} letterSpacing={2}>{label}</text>
    )}
  </g>
);

/**
 * N targets, each with its TRUE point in an independently placed spot.
 * This is the whole thesis of the 2026-08-07 dispatch as a component: the
 * target is not where a template says it is, so `offsets` are passed in per
 * target rather than derived from the shape.
 */
export const CandidateField: React.FC<{
  targets: {x: number; y: number; tx: number; ty: number}[];
  f: number; reveal?: number; color?: string;
}> = ({targets, f, reveal = 1, color = CYAN}) => (
  <g>
    {targets.map((t, i) => {
      const on = Math.max(0, Math.min(1, reveal * targets.length - i));
      if (on <= 0) return null;
      return (
        <g key={i} opacity={on}>
          {/* where a fixed template would have guessed: always the same relative spot */}
          <circle cx={t.x} cy={t.y} r={9} fill="none" stroke="#ffffff" strokeWidth={2}
                  opacity={0.22 * on} strokeDasharray="4 5" />
          {/* where the point ACTUALLY is */}
          <SearchReticle x={t.tx} y={t.ty} f={f} lock={on} seed={i * 5 + 2} r={44} color={color} />
        </g>
      );
    })}
  </g>
);

/** A soft confidence pulse. Fires once on a lock; use sparingly. */
export const ConfidenceBloom: React.FC<{x: number; y: number; t: number; color?: string}> = ({
  x, y, t, color = CYAN,
}) => {
  const k = Math.max(0, Math.min(1, t));
  if (k <= 0 || k >= 1) return null;
  return <circle cx={x} cy={y} r={40 + k * 130} fill="none" stroke={color}
                 strokeWidth={3 * (1 - k)} opacity={0.5 * (1 - k)} />;
};

/** Hairline scan grid, for a shot that is explicitly the machine's own view. */
export const VisionGrid: React.FC<{f: number; op?: number; color?: string}> = ({
  f, op = 0.14, color = CYAN,
}) => (
  <g opacity={op}>
    {Array.from({length: 13}).map((_, i) => (
      <line key={`v${i}`} x1={i * 90} y1={0} x2={i * 90} y2={1920} stroke={color} strokeWidth={1} />
    ))}
    {Array.from({length: 22}).map((_, i) => (
      <line key={`h${i}`} x1={0} y1={i * 90} x2={1080} y2={i * 90} stroke={color} strokeWidth={1} />
    ))}
    <rect x={0} y={((f * 3) % 1920)} width={1080} height={3} fill={color} opacity={0.5} />
  </g>
);

/** Ink-outlined chip used to LABEL a claim as the company's, never as fact. */
export const ClaimChip: React.FC<{
  x: number; y: number; text: string; sub?: string; op?: number; w?: number;
}> = ({x, y, text, sub, op = 1, w}) => {
  const width = w ?? Math.max(220, text.length * 21 + 64);
  return (
    <g transform={`translate(${x},${y})`} opacity={op}>
      <rect x={-width / 2 + 6} y={-30 + 7} width={width} height={sub ? 92 : 60} fill={INK} opacity={0.28} />
      <rect x={-width / 2} y={-30} width={width} height={sub ? 92 : 60} fill="#f2ece0"
            stroke={INK} strokeWidth={4} />
      <rect x={-width / 2} y={-30} width={width} height={12} fill="#a9793c" />
      <text x={0} y={16} textAnchor="middle" fontFamily="Archivo, Arial Black, sans-serif"
            fontWeight={900} fontSize={30} fill={INK} letterSpacing={0.5}>{text}</text>
      {sub && (
        <text x={0} y={50} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
              fontSize={19} fill={INK} opacity={0.72} letterSpacing={2}>{sub}</text>
      )}
    </g>
  );
};
