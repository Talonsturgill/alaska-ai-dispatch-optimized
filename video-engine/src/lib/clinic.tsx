import React from 'react';
import {tones, FormGradient, RimLight, ContactShadow, INK} from './lighting';
import {vitals} from './motion';

// ============================================================================
// CLINIC — the library's FIRST CLINICAL FAMILY (net-new 2026-08-08)
//
// REAL GAP, checked against ASSET_MANIFEST.md in full first. The shelf carries an
// orbital eye, a seafloor ear, a ground ear, two aerial machines, an under-ice
// swimmer, a bench-science family, a records/paper family, a civics rules kit, an
// absence grammar, an arthropod, a piece of media and 13 biomes. NOTHING on it is
// a piece of CLINICAL equipment, and this channel covers Alaska health.
//
// bench.tsx AshReader is the nearest prior art and it is the wrong verb: that
// machine reads a SAMPLE brought indoors under a lamp. This one is CARRIED TO A
// PERSON. evidence.tsx FrameOfEvidence is an emissive screen, which is the right
// instinct on the wrong object: a radiograph is not a screen you watch, it is a
// source and a receiver with a body in between.
//
// SHAPE-LANGUAGE DECISION, and it is the film's thesis in an object: this is the
// WARM ROUNDED PORTABLE half of a film whose other half is a cold orthogonal rules
// board. Everything on it is a radius. It has a HANDLE, which is the single most
// important line on the drawing, because the whole point is that a person picks it
// up and walks into a village clinic with it.
//
// AND IT HAS NO UPLINK. The back panel is deliberately BARE: no antenna, no dish,
// no cable running off frame. That is the IceGlider's missing-propeller trick
// (2026-07-30) applied to a different argument. This machine needs a person and a
// battery and nothing else, which is exactly why it was the thing that could be
// bought and shipped this month.
// ============================================================================

const hash = (i: number) => (Math.imul(i + 17, 2654435761) >>> 0) / 4294967295;

export interface FieldRadiographProps {
  x: number;
  y: number;
  f: number;
  scale?: number;
  /** 0 closed case, 1 fully deployed with the arm up */
  lid?: number;
  /** 0..1 the exposure event: emitter lights, detector plate answers */
  expose?: number;
  /** 0..1 lifts it off the ground by the handle: shadow shrinks, body tilts */
  carried?: number;
  /** VO-emphasis reactivity */
  accent?: number;
  /** decorrelates the idle from every other instance */
  phase?: number;
  /** ground line for the contact shadow */
  groundY?: number;
  /** case body tint, so a night palette re-tints without a re-draw */
  tint?: string;
  /** stencil on the case flank, e.g. a clinic number */
  stencil?: string;
  /** freeze the idle for a deliberate held beat */
  gain?: number;
}

/**
 * The portable X-ray unit, as a characterized object WITHOUT a face.
 *
 * No face is deliberate and it is the AshReader discipline, not an omission: this
 * machine is going to real clinics serving real communities, and giving it eyes
 * would make it a character with feelings about a story that belongs to the people
 * it serves. It gets warmth from its FORM, not from an expression.
 *
 * THREE STATE CHANNELS, per the one-channel lesson (07-25 horn, 07-26 cone, 07-30
 * glider, 08-05 beetle, 08-06 frame):
 *   1. THE ARM     — folded in the case, or raised and reaching over a patient.
 *   2. THE PAIR    — the emitter cone lights and the detector plate answers it.
 *                    Both, always, together. A source with no receiver is a lamp.
 *   3. THE HANDLE  — up and bearing weight when carried, slack when set down.
 */
export const FieldRadiograph: React.FC<FieldRadiographProps> = ({
  x, y, f, scale = 1, lid = 0, expose = 0, carried = 0, accent = 0,
  phase = 0, groundY, tint = '#d8b47a', stencil, gain = 1,
}) => {
  const v = vitals(f, phase, gain * (1 - carried * 0.4));
  const T = tones(tint);
  const Tm = tones('#8d97a0');      // the machined arm and hinges
  const Tp = tones('#e8ede9');      // the detector plate
  const id = `fr${Math.round(x)}${Math.round(y)}`;

  // carried: the whole body lifts, tilts and swings a little under its own mass
  const lift = carried * 96;
  const swing = carried * 3.4 * Math.sin(f / 21.7 + phase);
  const s = scale * v.breath;

  // the arm unfolds out of the case, anticipating slightly before it rises
  const armA = -128 * lid + 8 * Math.sin(lid * Math.PI); // overshoot at the top
  const kick = accent * 3;

  return (
    <g transform={`translate(${x + v.swayX * 0.5},${y - lift + v.bob * 0.6}) rotate(${swing + v.tilt * 0.3}) scale(${s})`}>
      <defs>
        <FormGradient id={`${id}-body`} t={T} />
        <FormGradient id={`${id}-arm`} t={Tm} />
        <FormGradient id={`${id}-plate`} t={Tp} softness={0.7} />
        <radialGradient id={`${id}-beam`} cx="50%" cy="0%" r="100%">
          <stop offset="0%" stopColor="#fff6d8" stopOpacity={0.85} />
          <stop offset="100%" stopColor="#fff6d8" stopOpacity={0} />
        </radialGradient>
      </defs>

      {/* ---- contact shadow. It touches ground until it is carried. ---- */}
      {groundY !== undefined && (
        <ContactShadow
          cx={0}
          cy={(groundY - y) / (s || 1)}
          rx={128 - carried * 46}
          ry={17 - carried * 6}
          opacity={0.42 * (1 - carried * 0.55)}
        />
      )}

      {/* ================= THE DETECTOR PLATE, on its own short stand ============
          Drawn FIRST so it sits behind the case. The pair is the point: the plate
          is what the beam is FOR, and it answers every exposure. */}
      <g transform="translate(126,-38)" opacity={lid}>
        <rect x={-6} y={-4} width={12} height={92} fill={Tm.shade} stroke={INK} strokeWidth={4} />
        <g transform={`rotate(${-6 + expose * 2})`}>
          <rect x={-52} y={-104} width={104} height={112} rx={7}
                fill={`url(#${id}-plate)`} stroke={INK} strokeWidth={5} />
          {/* the plate ANSWERS the beam: it brightens from the emitter's side */}
          <rect x={-52} y={-104} width={104} height={112} rx={7}
                fill="#bfe3ea" opacity={0.55 * expose} />
          {/* the image landing on it, drawn as ribs, never as a real radiograph */}
          <g opacity={expose * 0.7}>
            {[0, 1, 2, 3].map((i) => (
              <path key={i} d={`M-34,${-84 + i * 24} q34,${10 + i * 2} 68,0`}
                    fill="none" stroke="#40606b" strokeWidth={3} opacity={0.5 + i * 0.1} />
            ))}
          </g>
          <rect x={-52} y={-104} width={104} height={112} rx={7} fill="none"
                stroke="#ffffff" strokeWidth={2} opacity={0.35} />
          <RimLight d={`M-52,-97 q0,-7 7,-7 l90,0 q7,0 7,7`} w={3} opacity={0.5} />
        </g>
      </g>

      {/* ======================= THE ARM, machined and folding ================== */}
      <g transform={`translate(-8,-92) rotate(${armA + kick})`} opacity={lid > 0.02 ? 1 : 0}>
        {/* lower boom */}
        <rect x={-11} y={-8} width={150} height={22} rx={11}
              fill={`url(#${id}-arm)`} stroke={INK} strokeWidth={5} />
        {/* the elbow, a real pivot with a bolt */}
        <circle cx={139} cy={3} r={17} fill={Tm.base} stroke={INK} strokeWidth={5} />
        <circle cx={139} cy={3} r={6} fill={Tm.shade} stroke={INK} strokeWidth={3} />
        {/* upper boom + the emitter head, which is the ONE cone on the object */}
        <g transform={`translate(139,3) rotate(${58 - lid * 22})`}>
          <rect x={-9} y={-8} width={104} height={19} rx={9}
                fill={`url(#${id}-arm)`} stroke={INK} strokeWidth={5} />
          <g transform="translate(100,2)">
            {/* the collimator: a true tapered cone in three-quarter, straight walls
                and a flat rim, per the 07-25 horn / 07-26 cone lesson. NOT an ellipse. */}
            <path d="M-16,-26 L-16,26 L26,15 L26,-15 Z"
                  fill={Tm.core} stroke={INK} strokeWidth={5} strokeLinejoin="round" />
            <path d="M-16,-26 L-16,26 L4,20 L4,-20 Z" fill={Tm.shade} opacity={0.55} />
            <ellipse cx={26} cy={0} rx={5} ry={15} fill="#2b3440" stroke={INK} strokeWidth={3} />
            {/* it lights, and only when expose is up */}
            {expose > 0.01 && (
              <>
                <ellipse cx={26} cy={0} rx={5} ry={13} fill="#ffeec2" opacity={expose} />
                <path d="M26,-15 L150,-58 L150,58 L26,15 Z"
                      fill={`url(#${id}-beam)`} opacity={expose * 0.5} />
              </>
            )}
            <rect x={-24} y={-19} width={11} height={38} rx={4}
                  fill={Tm.base} stroke={INK} strokeWidth={4} />
          </g>
        </g>
      </g>

      {/* ============================ THE CASE BODY ============================
          Every edge is a radius. This is the warm, rounded, carryable half of the
          film's shape grammar and it is stated in the corner radii. */}
      <g>
        <rect x={-116} y={-96} width={232} height={128} rx={26}
              fill={`url(#${id}-body)`} stroke={INK} strokeWidth={7} />
        {/* the lid seam, and it separates as the case opens */}
        <path d={`M-116,${-52 - lid * 5} L116,${-52 - lid * 5}`}
              stroke={INK} strokeWidth={4} opacity={0.7} />
        {/* two real latches, which pop before the lid moves */}
        {[-72, 72].map((lx, i) => (
          <g key={i} transform={`translate(${lx},-52)`}>
            <rect x={-13} y={-9} width={26} height={18} rx={5}
                  fill={Tm.base} stroke={INK} strokeWidth={4} />
            <rect x={-6} y={-4 - lid * 5} width={12} height={8} rx={2}
                  fill={Tm.core} stroke={INK} strokeWidth={3} />
          </g>
        ))}
        {/* corner bumpers, the detail density that keeps it from reading as a box */}
        {[[-116, -96], [116, -96], [-116, 32], [116, 32]].map(([bx, by], i) => (
          <circle key={i} cx={bx} cy={by} r={15} fill={T.shade} stroke={INK} strokeWidth={5} />
        ))}
        {/* the battery well: this is what it runs on, and it is drawn */}
        <g transform="translate(-64,-8)">
          <rect x={-30} y={-20} width={60} height={40} rx={7}
                fill={T.shade} stroke={INK} strokeWidth={5} />
          {[0, 1, 2].map((i) => (
            <rect key={i} x={-21 + i * 15} y={-11} width={10} height={22} rx={2}
                  fill={i < 2 + Math.round(expose) ? '#7fbf6a' : '#4a5a52'}
                  stroke={INK} strokeWidth={3} />
          ))}
        </g>
        {/* vents, rivets and a stencil: 20+ shapes on the hero */}
        <g opacity={0.85}>
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <rect key={i} x={16 + i * 15} y={-24} width={7} height={30} rx={3.5}
                  fill={T.shade} stroke={INK} strokeWidth={2.5} />
          ))}
          {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => (
            <circle key={i} cx={-104 + (i % 4) * 69} cy={i < 4 ? -78 : 18} r={3.4}
                    fill={INK} opacity={0.42 + hash(i) * 0.2} />
          ))}
        </g>
        {stencil && (
          <text x={64} y={22} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
                fontSize={17} fontWeight={700} fill={INK} opacity={0.62}
                letterSpacing={1.5}>{stencil}</text>
        )}
        {/* THE BARE BACK PANEL. No antenna, no dish, no cable. The absence is the
            argument, so it is a clean unbroken radius with nothing coming off it. */}
        <path d="M-116,-70 q-9,34 0,68" fill="none" stroke={INK} strokeWidth={5} opacity={0.32} />
        <RimLight d="M-116,-70 q0,-26 26,-26 l180,0 q26,0 26,26" w={4} opacity={0.6} />
      </g>

      {/* ====================== THE HANDLE, the most important line ==============
          It bears weight: it straightens and the grip wrap compresses as `carried`
          comes up, and it hangs slack when the case is down. */}
      <g transform="translate(0,-96)">
        <path d={`M-46,0 q0,${-30 - carried * 12} 46,${-30 - carried * 12} q46,0 46,${30 + carried * 12}`}
              fill="none" stroke={INK} strokeWidth={15} strokeLinecap="round" />
        <path d={`M-46,0 q0,${-30 - carried * 12} 46,${-30 - carried * 12} q46,0 46,${30 + carried * 12}`}
              fill="none" stroke={Tm.core} strokeWidth={8} strokeLinecap="round" />
        <rect x={-22} y={-40 - carried * 12} width={44} height={17} rx={8}
              fill={T.core} stroke={INK} strokeWidth={4} />
      </g>
    </g>
  );
};

// ============================================================================
// THE ALLOWANCE BOARD — the rule as a physical object.
//
// civics.tsx already owns RULES (Gate, ThresholdGate, AperturePlate, CapClock) and
// this belongs to that family in spirit, but those assets model a rule that
// DECIDES about a thing arriving at it. This one is different: it is a posted
// LIST, an enamelled menu of what the money may and may not buy, and the drama is
// entirely in which lines carry a strike.
//
// DELIBERATE OPPOSITE of FieldRadiograph: hard orthogonal, no radius over 3, cold
// enamel, machine-set type. The film's two halves never share a corner radius.
// ============================================================================

export interface AllowanceRow {
  label: string;
  /** 'allow' plain, 'deny' struck through, 'cap' with a percentage collar */
  kind: 'allow' | 'deny' | 'cap';
  /** for kind 'cap', the collar text, e.g. '20%' */
  cap?: string;
  /** 0..1 reveals this row */
  at?: number;
}

// ============================================================================
// THE TYPE SLUG — a phrase as a physical object you can hold against things.
//
// The film's throughline is the phrase ARTIFICIAL INTELLIGENCE, and the whole
// argument is about WHERE IT SITS: everyone expects it in an equipment clause and
// it turns out to live in a training clause. An abstraction cannot be somewhere.
// A cast metal slug of set type can.
//
// Shape-language: it belongs to the COLD orthogonal half (machined, bevelled, no
// radius above 2) but it is the one cold object the film treats with affection,
// because it is the thing being looked for rather than the rule doing the looking.
//
// `seated` is the state channel that carries the argument: 0 is held up loose with
// a shadow under it (an expectation), 1 is dropped into a matching recess with a
// hard contact and no gap left (located). A slug held against a card it does not
// match sits proud of the surface, and that gap IS the finding.
// ============================================================================

export const TypeSlug: React.FC<{
  x: number; y: number; f: number; text: string; scale?: number;
  /** 0 held above a surface, 1 seated into a recess that fits it */
  seated?: number;
  /** 0..1 how much it is lifted and presented rather than resting */
  held?: number;
  /** VO-emphasis reactivity */
  accent?: number;
  phase?: number;
  /** draws the recess it is being tested against, and whether it fits */
  recess?: {w: number; fits: boolean} | null;
}> = ({x, y, f, text, scale = 1, seated = 0, held = 0, accent = 0, phase = 0, recess = null}) => {
  const v = vitals(f, phase, 1 - seated * 0.8);
  const T = tones('#7d8b93');
  const id = `ts${Math.round(x)}${Math.round(y)}`;
  const CH = 0.602;                       // mono advance, exact
  const size = 34;
  const w = text.length * size * CH + 44;
  const h = 74;
  const lift = (1 - seated) * (18 + held * 46);
  return (
    <g transform={`translate(${x + v.swayX * 0.4},${y - lift + v.bob * 0.5}) scale(${scale})`}>
      <defs><FormGradient id={`${id}-b`} t={T} /></defs>

      {/* the recess it is being held against. A slug that does not fit leaves a gap
          on both sides, and the gap is the argument, so it is drawn explicitly. */}
      {recess && (
        <g transform={`translate(0,${lift + 6})`}>
          <rect x={-recess.w / 2} y={-6} width={recess.w} height={h + 12} rx={2}
                fill="#1d2a31" opacity={0.5} stroke={INK} strokeWidth={4} />
          {!recess.fits && (
            <>
              <path d={`M${-recess.w / 2},${h / 2} L${-w / 2 - 6},${h / 2}`}
                    stroke="#c0402f" strokeWidth={4} strokeDasharray="7 6" />
              <path d={`M${recess.w / 2},${h / 2} L${w / 2 + 6},${h / 2}`}
                    stroke="#c0402f" strokeWidth={4} strokeDasharray="7 6" />
            </>
          )}
        </g>
      )}

      <ContactShadow cx={0} cy={h + 16 + lift * 0.5} rx={w / 2 - 4 + lift * 0.25}
                     ry={9} opacity={0.34 * (1 - seated * 0.3)} />

      {/* the slug body: a bevelled machined block, type face up */}
      <g transform={`rotate(${(1 - seated) * (v.tilt * 0.5 + accent * 1.5)})`}>
        <rect x={-w / 2} y={0} width={w} height={h} rx={2}
              fill={`url(#${id}-b)`} stroke={INK} strokeWidth={6} />
        {/* the bevel: a lit top face and a dark bottom lip, so it has real thickness */}
        <path d={`M${-w / 2},6 L${-w / 2 + 11},${h - 10} L${w / 2 - 11},${h - 10} L${w / 2},6 Z`}
              fill={T.core} opacity={0.55} />
        <rect x={-w / 2} y={h - 11} width={w} height={11} fill={T.shade}
              stroke={INK} strokeWidth={4} />
        <text x={0} y={h / 2 + 11} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
              fontSize={size} fontWeight={700} fill="#f2f4f3" letterSpacing={1.4}>{text}</text>
        <RimLight d={`M${-w / 2},4 q0,-4 4,-4 l${w - 8},0 q4,0 4,4`} w={4} opacity={0.62} />
      </g>
    </g>
  );
};

export const AllowanceBoard: React.FC<{
  x: number; y: number; f: number; scale?: number;
  title?: string;
  rows: AllowanceRow[];
  /** 0..1 draws the strike across every 'deny' row */
  strike?: number;
  width?: number;
  rowH?: number;
}> = ({x, y, f, scale = 1, title = 'ALLOWABLE USES', rows, strike = 0, width = 720, rowH = 74}) => {
  const T = tones('#31424c');
  const id = `ab${Math.round(x)}${Math.round(y)}`;
  const H = 96 + rows.length * rowH;
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <defs><FormGradient id={`${id}-b`} t={T} softness={1.3} /></defs>
      {/* the board: enamel over steel, hard corners, two real mounting bolts */}
      <rect x={-width / 2} y={0} width={width} height={H} rx={3}
            fill={`url(#${id}-b)`} stroke={INK} strokeWidth={8} />
      <rect x={-width / 2 + 13} y={13} width={width - 26} height={H - 26} rx={2}
            fill="none" stroke="#8fa3ad" strokeWidth={3} opacity={0.45} />
      {[-1, 1].map((sgn) => (
        <circle key={sgn} cx={sgn * (width / 2 - 30)} cy={30} r={9}
                fill="#8fa3ad" stroke={INK} strokeWidth={4} />
      ))}
      <text x={0} y={62} textAnchor="middle" fontFamily="Archivo, Arial Black, sans-serif"
            fontWeight={900} fontSize={38} fill="#f0f4f2" letterSpacing={2}>{title}</text>
      <path d={`M${-width / 2 + 26},80 L${width / 2 - 26},80`} stroke="#8fa3ad" strokeWidth={3} opacity={0.5} />

      {rows.map((r, i) => {
        const ry = 96 + i * rowH;
        const on = r.at === undefined ? 1 : r.at;
        if (on <= 0.01) return null;
        const isDeny = r.kind === 'deny';
        return (
          <g key={i} opacity={on}>
            {/* the row's own bullet: a set square for allow, a blank slot for deny */}
            <rect x={-width / 2 + 34} y={ry + 12} width={22} height={22}
                  fill={isDeny ? 'none' : '#f0f4f2'} stroke={isDeny ? '#8fa3ad' : INK}
                  strokeWidth={4} opacity={isDeny ? 0.7 : 1} />
            <text x={-width / 2 + 74} y={ry + 33} fontFamily="JetBrains Mono, monospace"
                  fontSize={30} fontWeight={700} fill={isDeny ? '#c9d4d8' : '#f0f4f2'}
                  letterSpacing={0.5}>{r.label}</text>
            {/* THE COLLAR: a cap is a physical clamp on the row, not a footnote */}
            {r.kind === 'cap' && r.cap && (
              <g transform={`translate(${width / 2 - 96},${ry + 23})`}>
                <rect x={-46} y={-21} width={92} height={42} rx={2}
                      fill="#1d2a31" stroke="#e0921a" strokeWidth={4} />
                <text x={0} y={11} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
                      fontSize={27} fontWeight={700} fill="#e0921a">{r.cap}</text>
              </g>
            )}
            {/* THE STRIKE. It falls ONLY on a deny row, and it lands on the words
                that name the excluded thing. DISPATCH_STANDARD section 4: a mark
                that negates must negate the right thing. */}
            {isDeny && strike > 0.01 && (
              <path d={`M${-width / 2 + 66},${ry + 24} L${-width / 2 + 66 + (width - 150) * Math.min(1, strike)},${ry + 24}`}
                    stroke="#c0402f" strokeWidth={8} strokeLinecap="round" />
            )}
          </g>
        );
      })}
      <RimLight d={`M${-width / 2},14 q0,-14 14,-14 l${width - 28},0 q14,0 14,14`} w={4} opacity={0.4} />
    </g>
  );
};
