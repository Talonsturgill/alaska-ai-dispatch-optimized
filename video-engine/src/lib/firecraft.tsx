import React from 'react';
import {INK, tones, FormGradient, RimLight, ContactShadow} from './lighting';
import {vitals} from './motion';

// =============================================================================
// THE FIRE FAMILY — net-new 2026-08-03, "The Days You Are Allowed To Burn"
// -----------------------------------------------------------------------------
// THE MANIFEST GAP THIS FILLS (checked against ASSET_MANIFEST.md in full first,
// per the library mandate §4.3a). The shelf already had an orbital eye
// (SatelliteEye), a seafloor ear (ListeningMooring), a ground ear
// (SeismicStation), two aerial machines (Vale, Petrel), an under-ice swimmer
// (IceGlider), records machinery (RecordsMachine), the civics rules kit (Gate,
// ThresholdGate) and the bench instruments (AshReader, CoreColumn).
//
// EVERY ONE OF THEM READS A PLACE OR A THING. NOTHING ON THE SHELF READS TIME.
// This story's verb is finding WINDOWS IN A CALENDAR, so the gap is real and
// load-bearing rather than an excuse to draw something new. Nearest prior art is
// civics.tsx `AperturePlate`, and the distinction is genuine: that plate is a
// filter on MAGNITUDE (which load gets through), this is a filter on TIME (which
// DAY gets through), and the drawn object is a different machine entirely.
//
// The shelf also had NO FIRE VOCABULARY a person could act with. Vale suppresses
// fire and HazeOverlay grades smoke; nothing anywhere deliberately STARTS one.
// A film about prescribed burning could not draw its own subject.
//
// SHAPE LANGUAGE, and it is the whole art-direction plan in one rule: FLOOD
// AGAINST APERTURE. Everything that says NO is a continuous unbounded wash with
// no edge you could point at (FireDangerWash). Everything that says YES is a cut
// rectangle with hard machined edges and a measurable size (the punched window).
// A window has a frame. A flood does not. In silhouette alone a muted viewer can
// tell a prohibition from a permission, which is the film's entire thesis.
//
// PALETTE NOTE: this family is deliberately CHALK ENAMEL and OXIDIZED STEEL, not
// brass. Gate 0A caught the first draft's warm brass as a structural repeat of
// the 2026-08-02 world (brass instruments plus one reserved accent). The cool dry
// pairing also holds its silhouette better in a low-contrast smoke world.
// =============================================================================

const uid = (s: string) => 'fc' + Math.abs([...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 17)).toString(36);

export const ENAMEL = '#e6e2d6';
export const STEELOX = '#7d8f92';
export const EMBER = '#e2571f';
export const DUFF = '#6b4a3a';
export const SPRUCE = '#1f3833';
/** LICENSED ACCENT. In this film #3fbf7f means A DAY YOU MAY BURN and nothing else.
 *  Enforced at paint time by the AccentRegistry, and specifically by this run's
 *  craft advance `useAccentExtent`, because every licensed green here is a window
 *  with a real width and height and a point check would license one by its centre
 *  while its edges spilled outside. */
export const BURNABLE = '#3fbf7f';

/** deterministic hash so texture never uses Math.random (it would re-roll per frame) */
const h = (i: number, s = 1) => {
  const x = Math.imul(i * 2654435761 + s * 40503, 2246822519);
  return ((x >>> 8) & 0xffff) / 0xffff;
};

// -----------------------------------------------------------------------------
// FireDangerWash — THE FLOOD HALF OF THE GRAMMAR.
//
// The hard part of this asset is what it must NOT have: an edge. A shape with a
// silhouette reads as an object you could negotiate with, and the film's claim is
// that the prohibition is exactly the thing you can't. So it is drawn as stacked
// blurred lobes with no stroke anywhere, deliberately overrunning whatever bounds
// the caller gives it, and `bleed` pushes it PAST the coastline on purpose.
// -----------------------------------------------------------------------------
export const FireDangerWash: React.FC<{
  f: number; x?: number; y?: number; w?: number; hgt?: number;
  amount?: number;   // 0..1 coverage
  bleed?: number;    // how far past its own bounds it runs (px)
  drain?: number;    // 0..1 runs off the bottom of frame under its own weight
  seed?: number;
}> = ({f, x = 0, y = 0, w = 1080, hgt = 1920, amount = 1, bleed = 90, drain = 0, seed = 3}) => {
  const id = uid(`wash${seed}${w}`);
  const a = Math.max(0, Math.min(1, amount));
  if (a <= 0.001) return null;
  const dy = drain * (hgt + bleed * 2);
  const lobes = Array.from({length: 11}).map((_, i) => {
    const px = x - bleed + h(i, seed) * (w + bleed * 2);
    const py = y - bleed + h(i, seed + 7) * (hgt + bleed * 2);
    const r = (0.13 + h(i, seed + 13) * 0.3) * Math.max(w, hgt);
    // each lobe drains at a slightly different rate so the trailing edge whips
    const lag = 0.75 + h(i, seed + 21) * 0.5;
    return {px, py: py + dy * lag, r, o: 0.3 + h(i, seed + 31) * 0.42};
  });
  return (
    <g opacity={a}>
      <defs>
        <filter id={`${id}b`} x="-45%" y="-45%" width="190%" height="190%">
          <feGaussianBlur stdDeviation={54} />
        </filter>
        <radialGradient id={`${id}g`}>
          <stop offset="0%" stopColor={EMBER} stopOpacity={0.95} />
          <stop offset="62%" stopColor="#c8410f" stopOpacity={0.55} />
          <stop offset="100%" stopColor="#8f2b06" stopOpacity={0} />
        </radialGradient>
      </defs>
      <g filter={`url(#${id}b)`}>
        {lobes.map((l, i) => (
          // NO STROKE. ANYWHERE. A stroke would give the prohibition a silhouette.
          <ellipse key={i} cx={l.px} cy={l.py} rx={l.r} ry={l.r * (0.7 + h(i, seed + 41) * 0.5)}
                   fill={`url(#${id}g)`} opacity={l.o}
                   transform={`rotate(${h(i, seed + 51) * 360} ${l.px} ${l.py})`} />
        ))}
        {/* a slow breathing overlay so the flood is never a still image */}
        <ellipse cx={x + w / 2} cy={y + hgt / 2 + dy}
                 rx={w * (0.62 + 0.04 * Math.sin(f / 63))}
                 ry={hgt * (0.42 + 0.03 * Math.sin(f / 47 + 1.3))}
                 fill={`url(#${id}g)`} opacity={0.34} />
      </g>
    </g>
  );
};

// -----------------------------------------------------------------------------
// DripTorch — the human tool that STARTS a prescribed fire, in a gloved hand.
// The whole point of drawing the hand is that this is a PERSON CHOOSING, not a
// disaster. `tilt` pours, and a bead leaves the spout on its own arc.
// -----------------------------------------------------------------------------
export const DripTorch: React.FC<{
  x: number; y: number; f: number; scale?: number;
  tilt?: number;      // 0..1 pours
  lit?: number;       // 0..1 the wick is burning
  withHand?: boolean;
  phase?: number;
  groundY?: number;
  gripFingers?: string;   // skin tone: draws fingers closing over the loop handle
}> = ({x, y, f, scale = 1, tilt = 0, lit = 0, withHand = true, phase = 0, groundY = 120,
       gripFingers}) => {
  const id = uid(`torch${x}${y}`);
  const body = tones(STEELOX);
  const glove = tones('#c8b48a');
  const v = vitals(f, phase, 0.6);
  const t = Math.max(0, Math.min(1, tilt));
  // THE SPOUT USED TO POUR UPWARD. The spout is on the canister's LEFT (x -34..-104)
  // and the handle on its right, so a POSITIVE (clockwise) rotation swings the spout
  // toward the sky. `tilt` therefore lifted the fuel away from the ground it is meant
  // to be laying fire on. Pouring is negative here.
  const rot = -8 - t * 40;
  const flick = 0.85 + 0.15 * Math.sin(f / 3.1 + phase);
  return (
    <g transform={`translate(${x},${y + v.bob}) scale(${scale})`}>
      <FormGradient id={id} t={body} softness={0.55} />
      <FormGradient id={`${id}g`} t={glove} softness={0.6} />
      <ContactShadow cx={0} cy={groundY} rx={70} ry={12} opacity={0.34} blur={14} />

      {/* THE ORIGIN IS THE GRIP. Everything inside is shifted so that the point a
          hand closes on, the middle of the loop handle at (44,-8), sits on this
          component's own (x,y). Two consequences, both of them the point: a scene
          places the torch by passing the HAND's coordinate and nothing else, and the
          tilt rotation pivots about the fist rather than about the middle of the fuel
          can, which is how a tool actually swings when someone is holding it. */}
      <g transform={`rotate(${rot}) translate(-44,8)`}>
        {/* fuel canister with a real level window, so the tool has consumable state */}
        <rect x={-34} y={-26} width={68} height={78} rx={9} fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
        <rect x={-22} y={-12} width={16} height={50} rx={3} fill="#2c3a3d" stroke={INK} strokeWidth={3} />
        <rect x={-22} y={4} width={16} height={34} rx={3} fill="#b8862f" opacity={0.9} />
        {/* fabrication marks: seam ring + rivets */}
        <line x1={-34} y1={10} x2={34} y2={10} stroke={INK} strokeWidth={2.6} opacity={0.45} />
        {[-24, -8, 8, 24].map((rx) => (
          <circle key={rx} cx={rx} cy={-19} r={2.6} fill={body.shade} stroke={INK} strokeWidth={1.4} />
        ))}
        {/* the loop handle */}
        <path d="M18,-26 q28,-16 30,10 q2,18 -14,20" fill="none" stroke={INK} strokeWidth={6} strokeLinecap="round" />
        <path d="M18,-26 q28,-16 30,10 q2,18 -14,20" fill="none" stroke={body.key} strokeWidth={2.4} strokeLinecap="round" />
        {/* the spout, bent, with a coiled wick at the tip */}
        <path d="M-34,34 L-84,52 L-104,74" fill="none" stroke={INK} strokeWidth={13} strokeLinecap="round" />
        <path d="M-34,34 L-84,52 L-104,74" fill="none" stroke={body.key} strokeWidth={6} strokeLinecap="round" />
        <circle cx={-104} cy={74} r={9} fill={body.shade} stroke={INK} strokeWidth={4} />
        {lit > 0.02 && (
          <g opacity={lit}>
            <path d={`M-104,66 q${5 * flick},-15 0,-27 q${-9 * flick},13 0,27 Z`} fill="#ffc24a" stroke={INK} strokeWidth={2.6} />
            <path d={`M-104,64 q3,-9 0,-16 q-5,8 0,16 Z`} fill="#fff0c2" />
          </g>
        )}
      </g>

      {/* THE BEAD: fuel leaving the spout on its own arc. This is the verb.
          It is emitted from where the spout ACTUALLY IS after the tilt rotation.
          This group sits outside the rotate, so it used to drip from a fixed point in
          space while the spout swung somewhere else entirely. */}
      {t > 0.35 && (() => {
        const rr = (rot * Math.PI) / 180;
        // spout tip in grip-origin coords, then rotated by the same tilt
        const sx = -104 - 44, sy = 74 + 8;
        const tipX = sx * Math.cos(rr) - sy * Math.sin(rr);
        const tipY = sx * Math.sin(rr) + sy * Math.cos(rr);
        return (
        <g opacity={Math.min(1, (t - 0.35) * 3)}>
          {[0, 1, 2].map((i) => {
            const ph = ((f / 9) + i * 0.34) % 1;
            const bx = tipX + 8 - ph * 14;
            const by = tipY + 6 + ph * ph * 150;
            return (
              <g key={i} transform={`translate(${bx},${by})`}>
                <ellipse rx={5.5} ry={8} fill="#ffb03a" stroke={INK} strokeWidth={2.4} />
                <ellipse cx={-1.4} cy={-2.4} rx={2} ry={3} fill="#fff2cd" />
              </g>
            );
          })}
        </g>
        );
      })()}

      {/* FINGERS CLOSING OVER THE HANDLE. The character is drawn first and its fist
          sits behind the loop; without a few finger forms laid over the front of the
          loop the hand reads as resting near the tool rather than gripping it. Skin
          tone is passed in by the scene so the fingers match the figure holding it. */}
      {gripFingers && (
        <g>
          <ellipse cx={-2} cy={-2} rx={17} ry={13} fill={gripFingers} stroke={INK} strokeWidth={4} />
          {[-9, 1, 11].map((fy, i) => (
            <rect key={i} x={-13} y={fy - 4} width={26} height={8} rx={4}
                  fill={gripFingers} stroke={INK} strokeWidth={3} opacity={0.98} />
          ))}
          {/* the contact tick: a hard AO crease where the fist closes on the metal */}
          <path d="M-14,-13 q14,-5 28,0" fill="none" stroke={INK} strokeWidth={2.6} opacity={0.5} />
        </g>
      )}

      {withHand && (
        <g transform={`translate(26,26)`}>
          {/* canvas glove with stitched seams and a knuckle crease */}
          <path d="M-6,-24 q34,-10 52,6 q14,12 6,34 q-10,26 -40,22 q-24,-4 -26,-28 Z"
                fill={`url(#${id}g)`} stroke={INK} strokeWidth={5} />
          <path d="M4,-14 q26,-4 40,10" fill="none" stroke={INK} strokeWidth={2.2} opacity={0.5} />
          <path d="M0,10 q26,6 44,-2" fill="none" stroke={INK} strokeWidth={2.2} opacity={0.45} />
          {/* cuff */}
          <rect x={-20} y={16} width={30} height={26} rx={6} fill={glove.shade} stroke={INK} strokeWidth={4.5} />
          <RimLight d="M-6,-24 q34,-10 52,6" w={2.6} />
        </g>
      )}
    </g>
  );
};

// -----------------------------------------------------------------------------
// BurnWindowEngine — THE RUN'S HERO, and the shelf's first instrument that reads TIME.
//
// THREE STATE CHANNELS AT ONCE, per the lesson this library has now paid for four
// times (07-25 SeismicStation horn, 07-26 TaperedCone, 07-30 IceGlider, 08-01
// AshReader): one channel is never legible at frame size.
//   1. THE PUNCHED RIBBON (loudest). Windows ACCUMULATE along the outbound stock,
//      so the count is a visible OBJECT with a length rather than a number to read.
//      This is the whole reason the hero is a ribbon machine and not a dial: a dial
//      would REPORT the count, the ribbon IS the count.
//   2. THE LAMP, which lights ONLY on an asserted window (the SeismicStation
//      discipline). A lit lamp always means a real day got through.
//   3. THE BROW plus THE FEED RATE, which carry state even when the lamp is dark.
//
// The intake never stops and the outbound stock is mostly solid, on purpose. The
// machine's characteristic experience is REJECTING, and the punch is rare, which
// is what makes it an event when it finally lands.
// -----------------------------------------------------------------------------
export const BurnWindowEngine: React.FC<{
  x: number; y: number; f: number; scale?: number;
  emotion?: 'reading' | 'straining' | 'found';
  feed?: number;        // 0..1 how fast the weather ribbon runs in
  punch?: number;       // 0..1 the punch stroke (0 up, 1 driven home)
  windows?: number;     // how many windows have accumulated on the outbound stock
  lamp?: number;        // 0..1, lights ONLY on an asserted window
  accent?: number;      // VO-emphasis reactivity
  phase?: number;
  groundY?: number;
  windowFill?: string;  // resolved licensed accent, from useAccentExtent()
}> = ({
  x, y, f, scale = 1, emotion = 'reading', feed = 1, punch = 0, windows = 0,
  lamp = 0, accent = 0, phase = 0, groundY = 104, windowFill,
}) => {
  const id = uid(`bwe${x}${y}`);
  const body = tones(ENAMEL);
  const steel = tones(STEELOX);
  const v = vitals(f, phase, emotion === 'found' ? 0.5 : 1);
  const strain = emotion === 'straining' ? 1 : 0;
  const p = Math.max(0, Math.min(1, punch));
  const kick = accent * 4;
  const lit = Math.max(0, Math.min(1, lamp));
  // the feed is the ONE UNEASED MOTION in the film, because data does not care
  const scroll = (f * 2.3 * feed) % 40;
  const brow = strain ? -8 : emotion === 'found' ? 3 : -2;
  const blink = Math.sin(f / 29 + phase) > 0.95 ? 0.14 : 1;
  const shake = p > 0.72 ? (h(Math.floor(f), 5) - 0.5) * 5 : 0;

  return (
    <g transform={`translate(${x + shake},${y + v.bob - kick}) scale(${scale}) rotate(${v.tilt * 0.4})`}>
      <FormGradient id={id} t={body} softness={0.6} />
      <FormGradient id={`${id}s`} t={steel} softness={0.52} />
      <ContactShadow cx={0} cy={groundY} rx={172} ry={24} opacity={0.4} blur={18} />

      {/* ---- THE PLINTH: planted, machined, four feet not a floating box ---- */}
      {[-132, 112].map((fx) => (
        <rect key={fx} x={fx} y={groundY - 28} width={24} height={28} rx={3}
              fill={steel.shade} stroke={INK} strokeWidth={4} />
      ))}
      <rect x={-152} y={groundY - 50} width={304} height={26} rx={5}
            fill={`url(#${id}s)`} stroke={INK} strokeWidth={5} />

      {/* ---- THE INTAKE: the weather ribbon, dense and endless, running in ---- */}
      <g>
        <rect x={-268} y={-26} width={122} height={52} rx={5}
              fill="#3a4a4d" stroke={INK} strokeWidth={4} />
        <g clipPath={`url(#${id}clipIn)`}>
          <defs><clipPath id={`${id}clipIn`}><rect x={-268} y={-26} width={122} height={52} rx={5} /></clipPath></defs>
          {Array.from({length: 22}).map((_, i) => {
            const gx = -272 + ((i * 40 + scroll) % 170);
            return (
              <g key={i}>
                <line x1={gx} y1={-22} x2={gx} y2={22} stroke="#9fb0b3" strokeWidth={2} opacity={0.75} />
                {/* printed weather density, the reason it reads as DATA not tape */}
                {[0, 1, 2, 3].map((k) => (
                  <rect key={k} x={gx + 5} y={-18 + k * 11} width={4 + h(i * 4 + k, 9) * 20} height={5}
                        fill="#c9d6d8" opacity={0.5 + h(i * 4 + k, 3) * 0.4} />
                ))}
              </g>
            );
          })}
        </g>
        <rect x={-268} y={-26} width={122} height={52} rx={5} fill="none" stroke={INK} strokeWidth={4} />
      </g>

      {/* ---- THE HOUSING ---- */}
      <rect x={-150} y={-104} width={300} height={148} rx={12}
            fill={`url(#${id})`} stroke={INK} strokeWidth={6} />
      {/* fabrication rings + vent slots, so it reads MACHINED */}
      <line x1={-150} y1={-58} x2={150} y2={-58} stroke={INK} strokeWidth={2.6} opacity={0.4} />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x={-136 + i * 15} y={20} width={7} height={18} rx={2}
              fill={body.shade} stroke={INK} strokeWidth={1.8} />
      ))}
      {[-140, 140].map((rx) => [-96, 36].map((ry) => (
        <circle key={`${rx}${ry}`} cx={rx} cy={ry} r={3.4} fill={steel.shade} stroke={INK} strokeWidth={1.6} />
      )))}

      {/* THE FACE: a brow bar and two lidded eyes. Restrained, but present. */}
      <rect x={-56} y={-92 + brow} width={112} height={11} rx={4}
            fill={INK} opacity={0.86} />
      {[-28, 28].map((ex) => (
        <g key={ex}>
          <ellipse cx={ex} cy={-66} rx={15} ry={15 * blink} fill="#f7f4ea" stroke={INK} strokeWidth={4} />
          <circle cx={ex + (emotion === 'found' ? 0 : Math.sin(f / 71 + phase) * 4)} cy={-66}
                  r={emotion === 'found' ? 4.5 : 7} fill={INK} opacity={blink > 0.5 ? 1 : 0} />
        </g>
      ))}

      {/* THE LAMP: lights ONLY on an asserted window. A lit lamp always means a real day. */}
      <circle cx={0} cy={-24} r={17} fill={lit > 0.05 ? '#ffd98a' : '#5d6b6d'}
              stroke={INK} strokeWidth={5} opacity={lit > 0.05 ? 0.55 + lit * 0.45 : 1} />
      {lit > 0.05 && <circle cx={0} cy={-24} r={17 + lit * 13} fill="#ffd98a" opacity={0.24 * lit} />}

      {/* ---- THE PUNCH HEAD: anticipation is built in via `punch` easing at the call site ---- */}
      <g transform={`translate(96,${-4 + p * 46})`}>
        <rect x={-26} y={-62} width={52} height={58} rx={5}
              fill={`url(#${id}s)`} stroke={INK} strokeWidth={5} />
        {/* compression spring that visibly loads as the head drops */}
        {[0, 1, 2, 3].map((i) => (
          <line key={i} x1={-18} y1={-58 + i * (13 - p * 4)} x2={18} y2={-52 + i * (13 - p * 4)}
                stroke={INK} strokeWidth={3} opacity={0.6} />
        ))}
        {/* hardened cutting shoe */}
        <path d="M-15,-4 L15,-4 L11,12 L-11,12 Z" fill={steel.key} stroke={INK} strokeWidth={4} />
      </g>

      {/* ---- THE OUTBOUND STOCK: mostly solid. The windows accumulate along it. ---- */}
      <g transform="translate(150,18)">
        <rect x={0} y={-22} width={250} height={44} rx={4}
              fill="#efeade" stroke={INK} strokeWidth={4} />
        {/* date gradations, so it reads as a CALENDAR and not as blank tape */}
        {Array.from({length: 25}).map((_, i) => (
          <line key={i} x1={8 + i * 10} y1={-22} x2={8 + i * 10} y2={-15}
                stroke={INK} strokeWidth={1.6} opacity={0.4} />
        ))}
        {/* THE COUNT AS AN OBJECT: each punched window is a real hole with a bevel */}
        {Array.from({length: Math.max(0, Math.round(windows))}).map((_, i) => {
          const wx = 20 + i * 31;
          if (wx > 226) return null;
          return (
            <g key={i}>
              <rect x={wx} y={-11} width={19} height={22} rx={2}
                    fill={windowFill || BURNABLE} stroke={INK} strokeWidth={3} />
              <path d={`M${wx + 2},${9} L${wx + 2},${-9} L${wx + 17},${-9}`} fill="none"
                    stroke="#c9f5dd" strokeWidth={2.4} opacity={0.8} />
              <path d={`M${wx + 2},${9} L${wx + 17},${9} L${wx + 17},${-9}`} fill="none"
                    stroke="#1d6b46" strokeWidth={2.4} opacity={0.85} />
            </g>
          );
        })}
        <rect x={0} y={-22} width={250} height={44} rx={4} fill="none" stroke={INK} strokeWidth={4} />
      </g>

      <RimLight d="M-150,-104 L150,-104" w={3} />
    </g>
  );
};

// -----------------------------------------------------------------------------
// PunchedWindow — one window, standalone, for the shots that stage it large.
// Carries the hard-edged beam that falls THROUGH it, which is the film's only
// hard light. Kept separate from the engine so a scene can hero one window
// without drawing the whole machine (the 07-31 lesson: a comparison needs each
// object at full width, not the whole rig).
// -----------------------------------------------------------------------------
export const PunchedWindow: React.FC<{
  x: number; y: number; f: number; w?: number; hgt?: number;
  beam?: number;     // 0..1 the hard light through the hole
  fill?: string;     // resolved licensed accent
  label?: string;
}> = ({x, y, f, w = 120, hgt = 150, beam = 0, fill, label}) => {
  const id = uid(`pw${x}${y}${w}`);
  const b = Math.max(0, Math.min(1, beam));
  return (
    <g transform={`translate(${x},${y})`}>
      {b > 0.02 && (
        <g opacity={b * 0.8}>
          <defs>
            <linearGradient id={`${id}beam`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#fff6dd" stopOpacity={0.72} />
              <stop offset="100%" stopColor="#fff6dd" stopOpacity={0} />
            </linearGradient>
          </defs>
          {/* HARD EDGES. This is the one place in the film light has a boundary. */}
          <path d={`M${-w / 2},${hgt / 2} L${w / 2},${hgt / 2} L${w * 1.5},${hgt * 4.2} L${-w * 1.5},${hgt * 4.2} Z`}
                fill={`url(#${id}beam)`} />
        </g>
      )}
      <defs>
        <linearGradient id={`${id}f`} x1="0" y1="0" x2="0.7" y2="1">
          <stop offset="0%" stopColor="#7ee0ab" />
          <stop offset="52%" stopColor={fill || BURNABLE} />
          <stop offset="100%" stopColor="#2a8f5e" />
        </linearGradient>
      </defs>
      <rect x={-w / 2} y={-hgt / 2} width={w} height={hgt} rx={3}
            fill={`url(#${id}f)`} stroke={INK} strokeWidth={6} />
      <path d={`M${-w / 2 + 5},${hgt / 2 - 5} L${-w / 2 + 5},${-hgt / 2 + 5} L${w / 2 - 5},${-hgt / 2 + 5}`}
            fill="none" stroke="#c9f5dd" strokeWidth={4} opacity={0.8} />
      <path d={`M${-w / 2 + 5},${hgt / 2 - 5} L${w / 2 - 5},${hgt / 2 - 5} L${w / 2 - 5},${-hgt / 2 + 5}`}
            fill="none" stroke="#1d6b46" strokeWidth={4} opacity={0.85} />
      {label && (
        <text x={0} y={hgt / 2 + 34} textAnchor="middle" fill={INK}
              style={{font: `700 ${Math.round(w * 0.2)}px "JetBrains Mono", ui-monospace, monospace`}}>
          {label}
        </text>
      )}
    </g>
  );
};
