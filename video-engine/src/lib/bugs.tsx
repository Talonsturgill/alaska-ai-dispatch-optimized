import React from 'react';
import {tones, FormGradient, RimLight, ContactShadow} from './lighting';
import {vitals} from './motion';

// =============================================================================
// BUGS — the library's FIRST INSECT, net-new 2026-08-05 ("The Net Comes First").
//
// THE GAP, checked against ASSET_MANIFEST.md in full first. The bestiary holds
// 21 species: moose, raven, eagle, four fish, grizzly, caribou, orca, puffin,
// wolf, fox, dall sheep, sea otter, humpback, ptarmigan, king crab, lynx,
// mountain goat, black bear, walrus, beluga, sled dogs. Every one of them is a
// vertebrate except KingCrab, and the only arthropod built for comedy is
// Mosquito, which is explicitly a gag asset with a whiny wing blur and a
// divebomb. There was no insect that could be looked at seriously.
//
// This film is about Alaska's insect fauna and the 2008 paper's headline result
// is specifically on GROUND BEETLES (Carabidae). A story about naming beetles
// that has to improvise a beetle is the same failure the 07-30 run caught when
// it nearly drew an ESA-threatened seal as an ellipse.
//
// THE SHAPE-LANGUAGE DECISION that drives the asset: a ground beetle is the
// ORGANIC-IRREGULAR grammar in a film whose other grammar is a rectilinear
// cabinet. So NOTHING on this animal is parallel to anything else. The elytra
// taper on a curve, the pronotum is a rounded trapezoid that matches neither
// the head nor the body, and the six legs are drawn at six different angles
// with three segments each. A beetle drawn with mirrored legs reads as a
// clip-art bug, which is exactly what a museum film cannot afford.
//
// THE ONE-CHANNEL LESSON, learned three times on this shelf (07-25 horn,
// 07-26 cone, 07-30 glider): one tell is never enough at feed size. State is
// carried by THREE things at once here: the ANTENNAE (forward and searching,
// or folded back), the LEG SET (planted, walking, or drawn in), and the ELYTRA
// SHEEN (dull when unnamed, a hard specular band when named).
// =============================================================================

const hash = (s: string) => Math.abs([...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 13));
const uid = (s: string) => 'bg' + hash(s).toString(36);

export const CARAPACE = '#2E2A24';      // near-black with a warm bias, never pure black
export const CARAPACE_L = '#6E6252';
export const BRASS_PIN = '#C9963F';

/**
 * THE SILHOUETTE, exported so the Unnamed primitive and the UnnamedField can
 * draw the SAME animal as an absence. This matters: the film's whole argument
 * is a filled form and a dashed form of one shape sitting side by side, and
 * that only reads if it is literally one path.
 *
 * Local coordinates, roughly 200 wide by 120 tall, centred on the origin.
 */
export const BEETLE_PATH =
  'M 0 -58 ' +
  'C 14 -58 22 -50 23 -40 ' +
  'C 34 -36 40 -22 41 -2 ' +
  'C 42 22 34 46 18 56 ' +
  'C 12 60 -12 60 -18 56 ' +
  'C -34 46 -42 22 -41 -2 ' +
  'C -40 -22 -34 -36 -23 -40 ' +
  'C -22 -50 -14 -58 0 -58 Z';

/**
 * THE FULL SILHOUETTE: body PLUS head, legs and antennae.
 *
 * WHY THIS EXISTS, and it was found by looking at the rough cut rather than by
 * reasoning about it. The absence grammar draws BEETLE_PATH as a dashed
 * contour, and BEETLE_PATH is the elytra outline alone. Dashed, with no fill
 * and no legs, that is an EGG. The hook and the signature shot are both built
 * entirely on the dashed form, so the two most important frames in the film
 * were showing a stranger an oval and calling it an insect.
 *
 * A filled beetle gets its legs and antennae from separate drawn elements. An
 * unfilled one has nothing but its outline, so the outline has to carry the
 * whole animal. Compound path: the closed body first, then open subpaths for
 * six legs and two antennae, which stroke correctly under a dash array and
 * contribute no area to the fill.
 */
export const BEETLE_SIL = BEETLE_PATH +
  // six legs, six different angles, same asymmetry as the drawn rig
  ' M -22 -26 L -47 -42 L -70 -30' +
  ' M -25 -4  L -55 -8  L -78 6' +
  ' M -23 20  L -50 34  L -70 52' +
  ' M 22 -26  L 47 -42  L 70 -30' +
  ' M 25 -4   L 55 -8   L 78 6' +
  ' M 23 20   L 50 34   L 70 52' +
  // head and pronotum, so the front end is not a blank curve
  ' M -23 -40 L -17 -22 L 17 -22 L 23 -40' +
  ' M 0 -47 m -13 0 a 13 11 0 1 0 26 0 a 13 11 0 1 0 -26 0' +
  // antennae
  ' M -9 -50 L -26 -74 L -38 -92' +
  ' M 9 -50  L 26 -74  L 38 -92';

export type BeetleState = 'still' | 'walking' | 'caught' | 'named';

/**
 * A GROUND BEETLE, drawn to be looked at.
 *
 * `state`
 *   still    planted, antennae sweeping slowly, a breath in the abdomen
 *   walking  a real alternating-tripod gait, the beetle's actual gait
 *   caught   legs drawn in, antennae folded back, body tilted off level
 *   named    planted and lit, a hard specular band across the elytra, and the
 *            label plate below it carries the accent
 *
 * `pinned` puts a real entomological pin through the right elytron with the
 * label stack beneath, which is what a specimen physically IS.
 */
export const GroundBeetle: React.FC<{
  x: number; y: number; f: number; scale?: number;
  state?: BeetleState;
  facing?: 1 | -1;
  /** 0..1 the specular band that arrives WITH a name and never before */
  sheen?: number;
  /** the accent colour, supplied by the caller so the accent licence stays at the call site */
  accentColor?: string;
  label?: string;
  pinned?: boolean;
  accent?: number;
  phase?: number;
  gain?: number;
  groundY?: number;
}> = ({
  x, y, f, scale = 1, state = 'still', facing = 1, sheen = 0,
  accentColor = '#35C8C0', label, pinned = false, accent = 0, phase = 0, gain = 1, groundY,
}) => {
  const id = uid(`b${x}${y}${label ?? ''}`);
  const t = tones(CARAPACE);
  const v = vitals(f, phase, gain);

  const walking = state === 'walking';
  const caught = state === 'caught';
  // the alternating tripod: legs 0,3,4 move together, 1,2,5 oppose. Real beetle gait.
  const gait = (i: number) => {
    if (!walking) return 0;
    const tri = i === 0 || i === 3 || i === 4 ? 0 : Math.PI;
    return Math.sin(f / 4.5 + tri) * 7;
  };

  // six legs, six DIFFERENT angles. Nothing mirrors anything.
  const LEGS = [
    {ax: -22, ay: -26, a1: -142, a2: -104, len1: 26, len2: 30},
    {ax: -25, ay: -4, a1: -172, a2: -142, len1: 30, len2: 34},
    {ax: -23, ay: 20, a1: 158, a2: 122, len1: 29, len2: 33},
    {ax: 22, ay: -26, a1: -38, a2: -74, len1: 25, len2: 29},
    {ax: 25, ay: -4, a1: -8, a2: -40, len1: 31, len2: 35},
    {ax: 23, ay: 20, a1: 22, a2: 58, len1: 28, len2: 32},
  ];

  const leg = (L: typeof LEGS[number], i: number) => {
    const drawIn = caught ? 0.45 : 1;
    const g = gait(i);
    const a1 = ((L.a1 + g) * Math.PI) / 180;
    const kx = L.ax + Math.cos(a1) * L.len1 * drawIn;
    const ky = L.ay + Math.sin(a1) * L.len1 * drawIn;
    const a2 = ((L.a2 + g * 1.6) * Math.PI) / 180;
    const fx = kx + Math.cos(a2) * L.len2 * drawIn;
    const fy = ky + Math.sin(a2) * L.len2 * drawIn;
    return (
      <g key={i}>
        <path d={`M ${L.ax} ${L.ay} L ${kx} ${ky} L ${fx} ${fy}`}
              fill="none" stroke={t.shade} strokeWidth={5.5} strokeLinecap="round" strokeLinejoin="round" />
        <path d={`M ${L.ax} ${L.ay} L ${kx} ${ky}`}
              fill="none" stroke={t.core} strokeWidth={2.4} strokeLinecap="round" opacity={0.7} />
        {/* the tarsus, a small hook so the foot is not a blunt stop */}
        <path d={`M ${fx} ${fy} l ${Math.cos(a2) * 5} ${Math.sin(a2) * 5 + 2}`}
              fill="none" stroke={t.shade} strokeWidth={3} strokeLinecap="round" />
      </g>
    );
  };

  // antennae: forward and searching when alive, folded back when caught
  const antenna = (side: 1 | -1) => {
    const sweep = caught ? -34 * side : Math.sin(f / 21 + (side > 0 ? 0 : 1.3) + phase) * 13;
    const base = {x: 9 * side, y: -50};
    const seg = 5;
    let d = `M ${base.x} ${base.y}`;
    let px = base.x, py = base.y, ang = (-72 + sweep) * side;
    for (let i = 0; i < seg; i++) {
      // followThrough: each segment lags the one before it, so the tip trails
      const a = ((ang + Math.sin(f / 17 - i * 0.6 + phase) * 5 * (i + 1) * 0.4) * Math.PI) / 180;
      const nx = px + Math.cos(a) * 9;
      const ny = py + Math.sin(a) * 9;
      d += ` L ${nx} ${ny}`;
      px = nx; py = ny; ang += 6 * side;
    }
    return <path d={d} fill="none" stroke={t.shade} strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />;
  };

  // deterministic elytral punctures, the surface texture a carabid actually has
  const punctures = Array.from({length: 26}, (_, i) => {
    const h = hash(`p${i}`);
    const col = (h % 5) - 2;
    const row = (Math.floor(h / 5) % 9) - 4;
    return {cx: col * 8 + ((h % 3) - 1), cy: row * 9 + 8, r: 1.1 + (h % 3) * 0.25};
  });

  const bodyTilt = caught ? 13 : v.tilt * 0.6;
  const breath = 1 + v.breath * 0.012;

  return (
    <g transform={`translate(${x},${y}) scale(${scale * facing},${scale})`}>
      <defs>
        <FormGradient id={`${id}-body`} t={t} />
        <clipPath id={`${id}-shell`}>
          <path d={BEETLE_PATH} />
        </clipPath>
        <linearGradient id={`${id}-sheen`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="45%" stopColor="#ffffff" stopOpacity={0.5 * sheen} />
          <stop offset="55%" stopColor="#ffffff" stopOpacity={0.5 * sheen} />
          <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>

      {groundY !== undefined && (
        <ContactShadow cx={0} cy={groundY} rx={46} ry={9} opacity={caught ? 0.16 : 0.24} />
      )}

      <g transform={`translate(0,${v.bob * 0.4}) rotate(${bodyTilt}) scale(${breath})`}>
        {LEGS.map(leg)}
        {antenna(-1)}
        {antenna(1)}

        {/* head */}
        <ellipse cx={0} cy={-49} rx={13} ry={11} fill={t.shade} />
        <ellipse cx={0} cy={-51} rx={11} ry={9} fill={t.core} />
        {/* mandibles, crossed and asymmetric, which is what a carabid has */}
        <path d="M -6 -58 q -5 -6 -2 -10" fill="none" stroke={t.shade} strokeWidth={3} strokeLinecap="round" />
        <path d="M 6 -58 q 6 -5 3 -10" fill="none" stroke={t.shade} strokeWidth={3} strokeLinecap="round" />
        {/* eyes, set on the sides of the head where a beetle's actually are */}
        <circle cx={-10} cy={-52} r={3.4} fill="#0E0C0A" />
        <circle cx={10} cy={-52} r={3.4} fill="#0E0C0A" />
        <circle cx={-11} cy={-53.4} r={1.2} fill="#C9C2B4" opacity={0.85} />

        {/* pronotum, a rounded trapezoid matching neither head nor body */}
        <path d="M -23 -40 C -20 -32 -18 -26 -17 -22 L 17 -22 C 18 -26 20 -32 23 -40 C 14 -46 -14 -46 -23 -40 Z"
              fill={t.shade} />
        <path d="M -19 -38 C -17 -32 -15 -28 -14 -25 L 14 -25 C 15 -28 17 -32 19 -38 C 12 -42 -12 -42 -19 -38 Z"
              fill={t.core} opacity={0.8} />

        {/* the elytra, form-shaded, never a flat fill */}
        <path d={BEETLE_PATH} fill={`url(#${id}-body)`} />
        <g clipPath={`url(#${id}-shell)`}>
          {/* striae: the longitudinal grooves. Six per side, converging slightly. */}
          {[-30, -22, -14, 14, 22, 30].map((sx, i) => (
            <path key={i} d={`M ${sx} -18 C ${sx * 0.92} 10 ${sx * 0.8} 34 ${sx * 0.55} 52`}
                  fill="none" stroke="#000" strokeWidth={1.6} opacity={0.22} />
          ))}
          {punctures.map((p, i) => (
            <circle key={i} cx={p.cx} cy={p.cy} r={p.r} fill="#000" opacity={0.18} />
          ))}
          {/* the seam between the two elytra, the beetle's defining line */}
          <path d="M 0 -20 L 0 56" stroke="#000" strokeWidth={2.4} opacity={0.42} />
          <rect x={-50} y={-60} width={100} height={126} fill={`url(#${id}-sheen)`} />
        </g>
        <RimLight d={BEETLE_PATH} w={2.6} opacity={0.5} />
        <path d={BEETLE_PATH} fill="none" stroke="#14100C" strokeWidth={3} strokeLinejoin="round" />
      </g>

      {pinned && (
        <g>
          {/* a real pin, through the RIGHT elytron, which is where entomology puts it */}
          <line x1={17} y1={-96} x2={17} y2={54} stroke={BRASS_PIN} strokeWidth={3.4} strokeLinecap="round" />
          <circle cx={17} cy={-98} r={4.6} fill={BRASS_PIN} />
          <circle cx={15.6} cy={-99.4} r={1.6} fill="#F4DDAE" />
          {/* the contact tick where the pin enters the shell */}
          <ellipse cx={17} cy={-2} rx={5} ry={2} fill="#000" opacity={0.35} />
        </g>
      )}

      {label && (
        <g transform={`scale(${facing},1)`}>
          <rect x={-58} y={70} width={116} height={30} rx={3} fill="#F2ECDF" stroke="#14100C" strokeWidth={2} />
          <rect x={-58} y={70} width={116} height={30} rx={3} fill={accentColor} opacity={0.14 + accent * 0.1} />
          <text x={0} y={91} textAnchor="middle" fill="#14100C"
                style={{font: '700 17px "JetBrains Mono", ui-monospace, monospace', letterSpacing: 0.5}}>
            {label}
          </text>
        </g>
      )}
    </g>
  );
};
