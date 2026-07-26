import React from 'react';
import {INK, tones, FormGradient, RimLight, ContactShadow} from './lighting';
import {vitals} from './motion';

// ============================================================================
// PAPER — the records-room substance + the library's FIRST INTERIOR BIOME.
// NET-NEW 2026-07-26 ("The Field That Stopped in 2019").
//
// Why this exists: lib/biomes.tsx shipped ELEVEN biomes and every one of them is
// outdoors. lib/materials.tsx shipped eight substance overlays and none of them
// is paper. This dispatch happens entirely inside an office, inside a mailbox,
// inside a records field, so both gaps are load-bearing rather than decorative.
//
// Gate 0D rated this run's flatness risk HIGH: a high-key flat-lit interior with
// three cream tokens in one narrow value band is the textbook recipe for a beige
// page. Everything here is built to defeat that specifically:
//   - a numeric value ladder between depth planes (never adjectival)
//   - a real dark anchor available in every frame (the slate cabinet mass)
//   - contact shadow under everything touching the desk, since under flat light
//     contact shadow is the only depth cue that survives
//   - visible air (a lit dust column + a front parallax drift of loose sheets),
//     doing the work that low-angle falloff did on the last three dispatches
// ============================================================================

// The binding palette from out/dispatch/art_direction.json.
export const PAPER = {
  front: '#E8E2D4',      // bond-paper cream, front sheet plane
  mid: '#D2C7B0',        // aged manila, desk-level plane   (~11% L below front)
  desk: '#BBAF96',       // desk laminate                    (~11% L below mid)
  institution: '#4A5A66', // municipal blue-grey — THE DARK ANCHOR
  ink: '#2F3E46',
  hero: '#6E7F8C',       // institutional pewter, machine bodies
  brass: '#8A7A52',      // DULL institutional brass. Deliberately low chroma.
  stamp: '#1B4FA8',      // stamp-ink indigo — the state's certainty
  seal: '#D14A2E',       // naturalization-seal vermilion — RESERVED for the citizen
} as const;

/**
 * PaperFiber — the paper SUBSTANCE overlay (the materials.tsx gap).
 * Fiber tooth + a pale ruled grid, so a sheet reads as printed stock rather than
 * a flat fill. Deterministic (imul hash), never Math.random.
 */
export const PaperFiber: React.FC<{id: string; rule?: boolean; ruleColor?: string}> = ({
  id, rule = true, ruleColor = '#9FB4C7',
}) => {
  const speck = Array.from({length: 26}, (_, i) => {
    const h = Math.imul(i + 7, 2654435761) >>> 0;
    return {x: (h % 100), y: ((h >>> 7) % 100), r: 0.35 + ((h >>> 13) % 5) / 10};
  });
  return (
    <defs>
      <pattern id={id} width="100" height="100" patternUnits="userSpaceOnUse">
        {rule && (
          <g opacity={0.16}>
            {[20, 44, 68, 92].map((y) => (
              <line key={y} x1="0" y1={y} x2="100" y2={y} stroke={ruleColor} strokeWidth="1.1" />
            ))}
          </g>
        )}
        <g opacity={0.13} fill={INK}>
          {speck.map((s, i) => <circle key={i} cx={s.x} cy={s.y} r={s.r} />)}
        </g>
      </pattern>
    </defs>
  );
};

/**
 * Sheet — a single sheet of paper with REAL BODY.
 * The numeric shadow contract from the art direction: 2px edge, drop shadow
 * offset 4 down / 2 right at 22% opacity, and an optional curled corner with a
 * 30% under-shadow. This is the only thing making paper read as a solid, so the
 * numbers live in code rather than in prose.
 */
export const Sheet: React.FC<{
  x: number; y: number; w: number; h: number; fill?: string; rot?: number;
  curl?: number; fiber?: string; children?: React.ReactNode;
}> = ({x, y, w, h, fill = PAPER.front, rot = 0, curl = 0, fiber, children}) => (
  <g transform={`translate(${x},${y}) rotate(${rot})`}>
    <rect x={4} y={6} width={w} height={h} fill={INK} opacity={0.22} />
    <rect x={0} y={0} width={w} height={h} fill={fill} stroke={INK} strokeWidth={2} />
    {fiber && <rect x={0} y={0} width={w} height={h} fill={`url(#${fiber})`} />}
    {curl > 0 && (
      <g>
        <path d={`M${w},${h} L${w - 26 * curl},${h} Q${w},${h - 12 * curl} ${w},${h - 26 * curl} Z`}
              fill={INK} opacity={0.30} />
        <path d={`M${w},${h} L${w - 22 * curl},${h} Q${w - 4},${h - 10 * curl} ${w},${h - 22 * curl} Z`}
              fill={fill} stroke={INK} strokeWidth={2} />
      </g>
    )}
    {children}
  </g>
);

/**
 * PaperOfficeBG — the fluorescent-lit records room. The library's first interior.
 * Depth is carried by four planes with an ENFORCED value ladder, a dark cabinet
 * wall as the frame's anchor, a lit dust column, and a front drift of sheets.
 *
 * `drift` 0..1 scales the front-plane paper drift (the visible-air layer).
 * `parallax` shifts the planes for a camera move.
 */
export const PaperOfficeBG: React.FC<{f: number; parallax?: number; drift?: number}> = ({
  f, parallax = 0, drift = 1,
}) => {
  const cab = tones(PAPER.institution);
  const px = parallax;
  // fluorescent tube: a slow shimmer, never a strobe
  const tube = 0.88 + 0.12 * Math.sin(f / 23) + 0.04 * Math.sin(f / 6.3);
  const motes = Array.from({length: 22}, (_, i) => {
    const h = Math.imul(i + 31, 2246822519) >>> 0;
    const sp = 0.25 + ((h >>> 5) % 40) / 100;
    return {
      x: 180 + ((h % 760)),
      y: ((h >>> 9) % 900) + ((f * sp) % 900),
      r: 1.2 + ((h >>> 17) % 3) * 0.5,
      o: 0.10 + ((h >>> 21) % 20) / 100,
    };
  });
  const sheets = Array.from({length: 5}, (_, i) => {
    const h = Math.imul(i + 71, 2654435761) >>> 0;
    const sp = 0.5 + ((h >>> 3) % 30) / 40;
    return {
      x: -220 + ((h % 1500) + f * sp * 1.7) % 1600,
      y: 1560 + ((h >>> 11) % 300),
      rot: -22 + ((h >>> 7) % 45),
      w: 120 + ((h >>> 15) % 60),
    };
  });
  return (
    <g>
      <PaperFiber id="pofib" />
      <FormGradient id="cabg" t={cab} />
      {/* PLANE 4, deepest: the cabinet wall. THE DARK ANCHOR. */}
      <g transform={`translate(${-px * 0.18},0)`}>
        <rect x={-200} y={-200} width={1480} height={1180} fill={cab.shade} />
        {/* one-point perspective bank of drawers */}
        {Array.from({length: 5}).map((_, c) =>
          Array.from({length: 4}).map((_, r) => {
            const w = 210, h = 172;
            const x = 40 + c * 216, y = 120 + r * 178;
            return (
              <g key={`${c}-${r}`}>
                <rect x={x} y={y} width={w} height={h} fill="url(#cabg)" stroke={INK} strokeWidth={3} />
                <rect x={x + 14} y={y + 16} width={w - 28} height={20} fill={cab.shade} stroke={INK} strokeWidth={2} />
                <rect x={x + w / 2 - 30} y={y + h - 52} width={60} height={13} rx={5}
                      fill={PAPER.brass} stroke={INK} strokeWidth={2.4} />
                <line x1={x} y1={y + h} x2={x + w} y2={y + h} stroke={INK} strokeWidth={2} opacity={0.5} />
              </g>
            );
          }),
        )}
        {/* aerial veil so the wall sits BEHIND, not beside */}
        <rect x={-200} y={-200} width={1480} height={1180} fill={PAPER.front} opacity={0.13} />
      </g>

      {/* PLANE 3: the lit dust column — visible air */}
      <g opacity={tube}>
        <path d="M300,-160 L800,-160 L980,1180 L120,1180 Z" fill={PAPER.front} opacity={0.10} />
        {motes.map((m, i) => (
          <circle key={i} cx={m.x} cy={m.y % 1180} r={m.r} fill={PAPER.front} opacity={m.o} />
        ))}
      </g>

      {/* PLANE 2: the desk surface */}
      <g transform={`translate(${-px * 0.5},0)`}>
        <rect x={-200} y={1080} width={1480} height={900} fill={PAPER.desk} />
        <rect x={-200} y={1080} width={1480} height={900} fill="url(#pofib)" opacity={0.55} />
        <rect x={-200} y={1080} width={1480} height={14} fill={INK} opacity={0.34} />
      </g>

      {/* PLANE 1, front: drifting loose sheets (the parallax air layer) */}
      {drift > 0 && (
        <g opacity={0.5 * drift}>
          {sheets.map((s, i) => (
            <g key={i} transform={`translate(${s.x},${s.y}) rotate(${s.rot})`}>
              <rect x={0} y={0} width={s.w} height={s.w * 1.3} fill={PAPER.front}
                    stroke={INK} strokeWidth={2} opacity={0.85} />
            </g>
          ))}
        </g>
      )}
    </g>
  );
};

/**
 * TaperedCone — the TRUE THREE-QUARTER CONE.
 *
 * HARD-WON RULE, carried forward from the 2026-07-25 SeismicStation failure: pass
 * one drew that gramophone horn as a flat face-on ellipse and it read as a
 * lollipop. A cone must be built as real geometry: straight taper side walls, a
 * HOLLOW DARK interior, a rolled rim, and receding interior throat rings. This
 * film contains TWO such cones (the machine's intake mouth and its stem), so the
 * failure has two chances to recur and neither is acceptable.
 *
 * `mouthW` and `stemW` are independent on purpose: the entire thesis of this
 * dispatch is that one widened and the other did not.
 */
export const TaperedCone: React.FC<{
  x: number; y: number; mouthW: number; stemW: number; len: number;
  tint?: string; rim?: string; rings?: number;
}> = ({x, y, mouthW, stemW, len, tint = PAPER.hero, rim = PAPER.brass, rings = 4}) => {
  const t = tones(tint);
  const id = `cone${Math.round(x)}_${Math.round(y)}_${Math.round(mouthW)}`;
  const mh = mouthW * 0.30;   // ellipse minor axis at the mouth (3/4 view)
  const sh = stemW * 0.30;
  return (
    <g transform={`translate(${x},${y})`}>
      <FormGradient id={id} t={t} />
      {/* body: straight taper walls between the two ellipse rims */}
      <path d={`M${-mouthW / 2},0 L${-stemW / 2},${len} A${stemW / 2},${sh} 0 0 0 ${stemW / 2},${len} L${mouthW / 2},0 Z`}
            fill={`url(#${id})`} stroke={INK} strokeWidth={4} />
      {/* HOLLOW DARK interior at the mouth */}
      <ellipse cx={0} cy={0} rx={mouthW / 2} ry={mh} fill={INK} opacity={0.86} />
      <ellipse cx={0} cy={0} rx={mouthW / 2} ry={mh} fill="none" stroke={INK} strokeWidth={4} />
      {/* receding interior throat rings — the depth cue that kills the lollipop read */}
      {Array.from({length: rings}).map((_, i) => {
        const k = (i + 1) / (rings + 1);
        const rx = (mouthW / 2) * (1 - k * 0.62);
        const ry = mh * (1 - k * 0.62);
        return (
          <ellipse key={i} cx={0} cy={k * 16} rx={rx} ry={ry} fill="none"
                   stroke={t.key} strokeWidth={1.6} opacity={0.30 - i * 0.05} />
        );
      })}
      {/* rolled rim */}
      <ellipse cx={0} cy={0} rx={mouthW / 2} ry={mh} fill="none" stroke={rim} strokeWidth={7} />
      <ellipse cx={0} cy={-2} rx={mouthW / 2} ry={mh} fill="none" stroke={INK} strokeWidth={2.2} opacity={0.6} />
      <RimLight d={`M${-mouthW / 2},0 L${-stemW / 2},${len}`} />
    </g>
  );
};

/**
 * StateLetter — the letter, WITH NO FACE.
 *
 * Gate 0B ruled the first pass a violation of this board's own discipline rule:
 * a characterized envelope with eyes that winced was a gag performed BY the
 * object that carried a citizenship challenge to thousands of real Alaskans.
 * The reluctance now lives entirely in PHYSICS — `open` drives a flap that
 * hesitates against the paper's own stiffness before it gives. No eyes, no
 * mouth, no performance.
 */
export const StateLetter: React.FC<{
  f: number; x: number; y: number; scale?: number; open?: number;
  line?: string; faceDown?: boolean;
}> = ({f, x, y, scale = 1, open = 0, line = '', faceDown = false}) => {
  const v = vitals(f, 1.0, 0.35);
  // hesitation: the flap eases, catches near 55%, then releases
  const o = Math.max(0, Math.min(1, open));
  const hes = o < 0.55 ? o * 0.8 : 0.44 + (o - 0.55) * 1.24;
  const t = tones(PAPER.front);
  const id = `ltr${Math.round(x)}_${Math.round(y)}`;
  return (
    <g transform={`translate(${x},${y + v.bob * 0.5}) scale(${scale}) rotate(${v.tilt * 0.3})`}>
      <FormGradient id={id} t={t} />
      <ContactShadow cx={0} cy={266} rx={215} opacity={0.34} />
      <PaperFiber id={`${id}fib`} />
      {/* body */}
      <rect x={-210} y={-130} width={420} height={262} fill={`url(#${id})`} stroke={INK} strokeWidth={4} />
      <rect x={-210} y={-130} width={420} height={262} fill={`url(#${id}fib)`} />
      {!faceDown && (
        <>
          {/* rectilinear embossed state block — NOT an oval seal. The oval is the
              citizen's alone (Gate 0D: v1 spent the human shape in frame one). */}
          <rect x={-186} y={-108} width={78} height={54} fill={PAPER.brass} stroke={INK} strokeWidth={3} />
          <rect x={-178} y={-100} width={62} height={38} fill="none" stroke={INK} strokeWidth={2} opacity={0.7} />
          {/* stamp-ink letterhead rule */}
          <line x1={-186} y1={-38} x2={186} y2={-38} stroke={PAPER.stamp} strokeWidth={5} />
          {/* the carried line */}
          {line && (
            <text x={-186} y={16} fontFamily="Archivo, Inter, sans-serif" fontWeight={800}
                  fontSize={30} fill={INK} letterSpacing={0.4}>{line}</text>
          )}
          {[52, 78, 104].map((yy, i) => (
            <line key={yy} x1={-186} y1={yy} x2={i === 2 ? 60 : 186} y2={yy}
                  stroke={INK} strokeWidth={3} opacity={0.28} />
          ))}
        </>
      )}
      {/* the flap, with real thickness and a rolled edge */}
      {/* the flap: a downward triangle when closed, FLIPPING UP about its hinge as it
          opens. A 2D scaleY flip is the honest envelope read; rotating the lid down across
          the body (pass 1) buried the line the hook exists to show. */}
      <g transform={`translate(0,-130) scale(1,${1 - 1.86 * hes}) translate(0,130)`}>
        <path d="M-210,-130 L0,10 L210,-130 Z" fill={t.shade} stroke={INK} strokeWidth={4}
              strokeLinejoin="round" />
        <path d="M-210,-130 L0,10 L210,-130" fill="none" stroke={t.key} strokeWidth={3} opacity={0.75} />
      </g>
    </g>
  );
};

/**
 * FullTapeMachine — the answering machine that carries the whole 3,048 count.
 * The count is made felt against a KNOWN OBJECT WITH FIXED CAPACITY rather than
 * as a ratio, which is how this film honours the ban on dividing 200 into 15,200.
 * `fill` 0..1 fills the tape; at 1 the reels seize and the FULL tag springs up.
 */
export const FullTapeMachine: React.FC<{
  f: number; x: number; y: number; scale?: number; fill?: number;
}> = ({f, x, y, scale = 1, fill = 0}) => {
  const t = tones(PAPER.hero);
  const v = vitals(f, 3.0, 0.6);
  const k = Math.max(0, Math.min(1, fill));
  const seized = k >= 0.995;
  const spin = seized ? 0 : (f * (5.5 - k * 4.6)) % 360;
  const id = `ftm${Math.round(x)}`;
  const tag = seized ? Math.min(1, (f % 90) / 8) : 0;
  return (
    <g transform={`translate(${x},${y + v.bob * 0.6}) scale(${scale})`}>
      <FormGradient id={id} t={t} />
      <ContactShadow cx={0} cy={112} rx={165} opacity={0.36} />
      <rect x={-165} y={-96} width={330} height={208} rx={10} fill={`url(#${id})`} stroke={INK} strokeWidth={4.5} />
      <rect x={-165} y={-96} width={330} height={34} fill={t.shade} stroke={INK} strokeWidth={3} />
      {/* two visible reels */}
      {[-72, 72].map((cx, i) => (
        <g key={cx} transform={`translate(${cx},4) rotate(${spin * (i ? -1 : 1)})`}>
          <circle r={54} fill={t.shade} stroke={INK} strokeWidth={4} />
          <circle r={16 + 34 * (i ? 1 - k : k)} fill={PAPER.ink} opacity={0.72} />
          <circle r={13} fill={PAPER.brass} stroke={INK} strokeWidth={3} />
          {[0, 60, 120, 180, 240, 300].map((a) => (
            <line key={a} x1={0} y1={0} x2={Math.cos((a * Math.PI) / 180) * 50}
                  y2={Math.sin((a * Math.PI) / 180) * 50} stroke={INK} strokeWidth={2.2} opacity={0.5} />
          ))}
        </g>
      ))}
      {/* vents + level lamp */}
      {[-30, -18, -6, 6, 18, 30].map((yy) => (
        <line key={yy} x1={-16} y1={yy} x2={16} y2={yy} stroke={INK} strokeWidth={2.4} opacity={0.55} />
      ))}
      <circle cx={0} cy={-114} r={9} fill={seized ? PAPER.seal : PAPER.stamp} stroke={INK} strokeWidth={3} />
      {/* FULL tag on a spring */}
      {tag > 0 && (
        <g transform={`translate(0,${-150 - tag * 34}) rotate(${Math.sin(f / 3) * 4 * tag})`} opacity={tag}>
          <rect x={-58} y={-26} width={116} height={44} fill={PAPER.front} stroke={INK} strokeWidth={4} />
          <text x={0} y={7} textAnchor="middle" fontFamily="Archivo, Inter, sans-serif"
                fontWeight={900} fontSize={28} fill={INK}>FULL</text>
        </g>
      )}
      <RimLight d="M-165,-96 L165,-96" />
    </g>
  );
};
