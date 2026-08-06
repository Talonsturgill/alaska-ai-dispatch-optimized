import React from 'react';

// =============================================================================
// SCREENLIGHT — the PRACTICAL-SOURCE KEY. Craft advance, 2026-08-06.
//
// WHY THIS EXISTS. NightGrade (2026-07-25) gives a night AMBIENT with registered
// source BLOOM. DayGrade (2026-07-31) gives a daylight ambient. Neither can make a
// source actually KEY a subject, because both emit DIVS and sit OUTSIDE the svg, so
// they can only wash over finished art. Every screen-lit scene this engine has
// attempted has faked the key by hand-pinning a fill at the call site.
//
// THE COMPOSITION CONTRACT, stated before code (Gate 0D required this):
//   SCREENLIGHT emits SVG-SPACE GEOMETRY. It composes INTO tones/FormGradient/
//   RimLight rather than sitting over them, so it reaches asset shading.
//   It is ON BY DEFAULT for anything drawn inside a <ScreenLit> scope, with an
//   explicit `unlit` opt-out. A default-off fix is a doctrine reminder wearing a
//   code costume — that is the flat-HUD-chip lesson from 2026-07-30 and this file
//   does not repeat it.
//
// THE PHYSICS IT MODELS, and each one is a thing a monitor actually does:
//   1. FALLOFF BY DISTANCE from the emitting plane (inverse-square, clamped).
//   2. AN UPWARD-BIASED TERMINATOR. Screen light comes from BELOW the eye line, so
//      the lit band sits under a form's midline and the shadow rides on top. That
//      is the single tell that separates a screen key from a studio key, and it is
//      the opposite of every other light in this engine.
//   3. A CONTACT BOUNCE on the surface the screen sits on.
// =============================================================================

export type ScreenSource = {
  /** frame-space rect of the EMITTING SURFACE */
  x: number; y: number; w: number; h: number;
  /** the light it throws */
  color: string;
  /** 0..1 overall strength */
  intensity?: number;
  /** how far the light reaches, in frame units */
  reach?: number;
};

type Ctx = {sources: ScreenSource[]};
const ScreenCtx = React.createContext<Ctx>({sources: []});

export const useScreenSources = () => React.useContext(ScreenCtx).sources;

/** distance from a point to the nearest edge of a source rect (0 inside it) */
const distToRect = (px: number, py: number, s: ScreenSource) => {
  const dx = Math.max(s.x - px, 0, px - (s.x + s.w));
  const dy = Math.max(s.y - py, 0, py - (s.y + s.h));
  return Math.hypot(dx, dy);
};

/**
 * How strongly a screen source keys a point. 0..1.
 * Pure function, exported as a TEST SEAM (the accentAllowedAt precedent).
 */
export const keyAt = (px: number, py: number, sources: ScreenSource[]): number => {
  let k = 0;
  for (const s of sources) {
    const reach = s.reach ?? 900;
    const d = distToRect(px, py, s);
    const f = Math.max(0, 1 - (d / reach) ** 1.6);
    k = Math.max(k, f * (s.intensity ?? 1));
  }
  return Math.min(1, k);
};

/** the dominant source keying a point, for direction */
export const keySourceAt = (px: number, py: number, sources: ScreenSource[]): ScreenSource | null => {
  let best: ScreenSource | null = null, bk = 0;
  for (const s of sources) {
    const reach = s.reach ?? 900;
    const f = Math.max(0, 1 - (distToRect(px, py, s) / reach) ** 1.6) * (s.intensity ?? 1);
    if (f > bk) {bk = f; best = s;}
  }
  return bk > 0.02 ? best : null;
};

/** Register the screens in a scene. Everything inside is screen-lit by default. */
export const ScreenLit: React.FC<{sources: ScreenSource[]; children: React.ReactNode}> = ({sources, children}) => (
  <ScreenCtx.Provider value={{sources}}>{children}</ScreenCtx.Provider>
);

/**
 * THE KEY ITSELF. Wrap a form's bbox and it receives a real screen key:
 * an upward-biased terminator plus a falloff wash, in svg space, clipped to the form.
 *
 * `unlit` is the explicit opt-out. It exists so a deliberate silhouette can refuse
 * the key, NOT so a careless call site can default out of it.
 */
export const ScreenKey: React.FC<{
  id: string;
  x: number; y: number; w: number; h: number;
  unlit?: boolean;
  /** shape to clip the key to; omit for the bbox */
  d?: string;
  gain?: number;
}> = ({id, x, y, w, h, unlit = false, d, gain = 1}) => {
  const sources = useScreenSources();
  if (unlit || sources.length === 0) return null;
  const cx = x + w / 2, cy = y + h / 2;
  const k = keyAt(cx, cy, sources) * gain;
  if (k < 0.02) return null;
  const src = keySourceAt(cx, cy, sources);
  const col = src?.color ?? '#9FD8E8';
  // THE UPWARD BIAS. The source is almost always BELOW the form's centre in this
  // film (a person at a monitor), so the lit band sits low and the shade rides high.
  const srcY = src ? src.y + src.h / 2 : cy + h;
  const fromBelow = srcY > cy;
  const gid = `sk-${id}`;
  return (
    <>
      <defs>
        <linearGradient id={gid} x1="0" y1={fromBelow ? '1' : '0'} x2="0" y2={fromBelow ? '0' : '1'}>
          <stop offset="0%" stopColor={col} stopOpacity={0.62 * k} />
          <stop offset="38%" stopColor={col} stopOpacity={0.26 * k} />
          <stop offset="78%" stopColor={col} stopOpacity={0.04 * k} />
          <stop offset="100%" stopColor={col} stopOpacity={0} />
        </linearGradient>
        {d ? <clipPath id={`${gid}-c`}><path d={d} /></clipPath> : null}
      </defs>
      <g clipPath={d ? `url(#${gid}-c)` : undefined} style={{mixBlendMode: 'screen'}}>
        <rect x={x} y={y} width={w} height={h} fill={`url(#${gid})`} />
      </g>
    </>
  );
};

/**
 * THE CONTACT BOUNCE. A screen sitting on a surface throws a pool of its own colour
 * onto that surface. Without this a monitor reads as pasted onto a desk.
 */
export const ScreenBounce: React.FC<{id: string; s: ScreenSource; surfaceY: number; spread?: number}> = ({
  id, s, surfaceY, spread = 1.5,
}) => {
  const cx = s.x + s.w / 2;
  const rx = (s.w / 2) * spread;
  const ry = Math.max(14, (surfaceY - (s.y + s.h)) * 0.9 + 18);
  const gid = `sb-${id}`;
  return (
    <>
      <defs>
        <radialGradient id={gid}>
          <stop offset="0%" stopColor={s.color} stopOpacity={0.34 * (s.intensity ?? 1)} />
          <stop offset="60%" stopColor={s.color} stopOpacity={0.12 * (s.intensity ?? 1)} />
          <stop offset="100%" stopColor={s.color} stopOpacity={0} />
        </radialGradient>
      </defs>
      <ellipse cx={cx} cy={surfaceY} rx={rx} ry={ry} fill={`url(#${gid})`} style={{mixBlendMode: 'screen'}} />
    </>
  );
};
