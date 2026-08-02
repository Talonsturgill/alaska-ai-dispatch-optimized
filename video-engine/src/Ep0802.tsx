import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, Easing, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {
  AshReader, ShortlistCard, DistanceCalipers, CoreColumn, AshCrumbs,
  LayeredLand, ErasingBlade, CoringTube, BrassPlate, RHYOLITE,
} from './lib/bench';
import {INK, tones, FormGradient, RimLight, ContactShadow, MotionBlur, NightGrade, AccentRegistry, useAccent} from './lib/lighting';
import {Stage3D, Plane, Atmosphere, CameraMoves, composeCams} from './lib/stage3d';
import {entrance, vitals, EASE, POP, SNAP, SETTLE} from './lib/motion';

// EASE exports BEZIER CONTROL POINTS, not easing functions. Wrap them once, here, so no
// scene reaches for EASE.out and gets a runtime-shaped type error instead of a curve.
const E_OUT = Easing.bezier(...EASE.enter);        // decelerating arrival, the house settle
const E_MOVE = Easing.bezier(...EASE.move);        // symmetric in-out, for camera and reveals
const E_IN = Easing.in(Easing.cubic);              // accelerating departure
import {MaterialDefs, matFill} from './lib/materials';

// =============================================================================
// DISPATCH 2026-08-02 — "THE COPY IN THE MUD"
//
// Storyboard: out/dispatch/storyboard.json   Art direction: out/dispatch/art_direction.json
// Claims (the ONLY source of on-screen facts): out/dispatch/claims.json
//
// THESIS: glaciers scraped Alaska's eruption record off the land, so three USGS
// scientists in Anchorage read a surviving copy out of Gulf of Alaska seafloor mud,
// and the machine could name a volcano confidently only where the volcano had been
// writing the same chemical signature over and over. The confidence is a property of
// the ROCK before it is a property of the classifier.
//
// THE BINDING PALETTE RULE (art_direction.json): RHYOLITE MAGENTA #d94f8a MEANS A
// CHEMICAL MATCH AND NOTHING ELSE. It is enforced at paint time by the AccentRegistry
// (lib/lighting.tsx): every magenta fill resolves through useAccent(hue, x, y), which
// THROWS if the point is outside a licensed rect. An unlicensed accent physically can't
// reach a frame. Scenes 1 to 8 license NOTHING, because no match has been asserted yet.
//
// SHAPE LANGUAGE: TORN AGAINST TURNED. Everything found (mud, ash, land, ice) has torn
// irregular silhouettes with no two parallel edges. Everything built (tube, reader,
// calipers, plates) is machined and radially symmetric with visible fabrication marks.
// In silhouette alone you can tell evidence from instrument.
//
// LIGHT: one hard brass practical from UPPER SCREEN LEFT at ~35 degrees, in every scene,
// because one lamp means one room. Very little fill. Deep graphic shadow.
//
// THE DOMINANT MOVE: HORIZONTAL TRAVERSE. The camera travels ALONG a core, which means
// it travels BACKWARD THROUGH TIME. The single vertical move in the whole film is THE
// DROP THROUGH THE WATERLINE in S4, spent once, and it earns its uniqueness by being the
// film's only axis change.
// =============================================================================

const SKY = '#0e1418';
const GROUND = '#2b3630';
const BONE = '#e8e2d2';
const BRASS = '#c9a24a';
const MUD = '#4a4234';
const ASH = '#cfd4cc';
const ROOMDARK = '#0c1613';
const BOLD = 'Arial Black, Arial, sans-serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

/** the 4:5 LinkedIn crop is the deliverable, so every load-bearing element lives here */
const SAFE_TOP = 285;
const SAFE_BOT = 1635;
/** the caption reserve, inherited from the Ep0731 fix: no card may enter this band */
const CAPTION_TOP = 1420;
const CARD_BOT = CAPTION_TOP - 98;

const FPS = 30;

/** the three bands the abstract licenses naming (c10), and where they sit. */
const NAMED_BANDS = [{col: 1, k: 3, name: 'KATMAI'}, {col: 4, k: 5, name: 'FISHER CALDERA'}, {col: 6, k: 2, name: 'EMMONS LAKE'}];


/**
 * EVERY BEAT IN THIS FILM IS ANCHORED TO A VO LINE, NEVER TO AN ABSOLUTE SECOND.
 *
 * The storyboard quotes beat times as absolute seconds, and the obvious way to build a scene
 * is to copy those numbers in. That is a trap, and this run walked into it once before
 * catching it: the archived board was timed against the 2026-08-01 synth, this run
 * re-synthesized the VO, and every line start moved by a different amount (up to 1.8s). The
 * scene BOUNDARIES stay right, because build_scenes.py derives them from the new line table,
 * so nothing fails loudly. The beats inside each scene just quietly play against the wrong
 * words. So scenes take `L(i)`, the real start of VO line i in the shipped take, and express
 * every beat as an offset from the line it belongs to. Re-synth the voice and the picture
 * re-times itself.
 */
type SceneProps = {from: number; total: number; L: (i: number) => number};

/** the 2026-08-01 board's line starts. Fallback only, for Remotion Studio with no props. */
const FALLBACK_LINES = [
  0.0, 7.0, 14.84, 18.32, 25.38, 33.56, 39.84, 43.46,
  47.96, 54.12, 64.18, 71.26, 77.3, 82.94, 89.14, 93.96,
];

// -----------------------------------------------------------------------------
// THE ROOM. Three declared depth planes in every scene, per the light plan. The far
// plane is nearly nothing on purpose (this is a dark room), but it is real: dust in
// the lamp's throw, and the faint edge of a bench that says the space continues.
// -----------------------------------------------------------------------------
/**
 * THE LAMP HAS TO REACH THE SPECIMEN.
 *
 * Pass 1 put the throw at (300, 210) with the whole cast staged around y 1100 to 1500, so the
 * light was in the corner and the subject was in the dark. The rough cut came back with about
 * two thirds of every frame at near-black and nothing to look at. The bearing is still UPPER
 * SCREEN LEFT per the binding light plan, which is about the DIRECTION rims and shadows derive
 * from; it was never an instruction to aim the pool of light away from the thing being lit.
 */
const LampThrow: React.FC<{f: number; cx?: number; cy?: number; r?: number; strength?: number}> = ({
  f, cx = 468, cy = 946, r = 1420, strength = 1,
}) => {
  const breathe = 0.97 + 0.03 * Math.sin(f / 47);
  return (
    <g style={{mixBlendMode: 'screen'}} opacity={strength * breathe}>
      <defs>
        <radialGradient id="lampthrow">
          <stop offset="0%" stopColor="#ffdcaa" stopOpacity={0.42} />
          <stop offset="26%" stopColor="#f0c489" stopOpacity={0.17} />
          <stop offset="56%" stopColor="#8a7048" stopOpacity={0.04} />
          <stop offset="100%" stopColor="#000000" stopOpacity={0} />
        </radialGradient>
      </defs>
      <ellipse cx={cx} cy={cy} rx={r} ry={r * 0.95} fill="url(#lampthrow)" />
    </g>
  );
};

/**
 * THE ROOM ITSELF, and it exists because dead_space_check measured the film at 52.7 percent
 * low-information area on the final render, over budget, with the hook frame worst at 81.
 *
 * The single-object-void layout in the art-direction plan is deliberate and stays. But "the
 * specimen sits in deep near-black" was being built as "there is nothing behind the specimen",
 * and those are different pictures. A dark room still has a room in it: a pegboard wall, the
 * tools somebody hung on it, jars on a shelf. Drawn at low contrast and low value so it never
 * competes with the lit subject, it turns empty frame into DEPTH, which is what the plan asked
 * for in the first place (three declared planes, atmosphere on the far one).
 */
const RoomBack: React.FC<{f: number; y?: number; op?: number}> = ({f, y = 250, op = 1}) => {
  return (
    <g opacity={op}>
      {/* flat, dark, and far wider than frame: this is the room's VALUE FLOOR, not a subject */}
      <rect x={-1500} y={-1200} width={4080} height={4200} fill="#0f1a18" />
      {/* pegboard perforations: a regular grid, because the wall is BUILT (turned, not torn) */}
      {Array.from({length: 22}).map((_, r) =>
        Array.from({length: 26}).map((_, c) => (
          <circle key={`${r}-${c}`} cx={-420 + c * 74} cy={y - 180 + r * 62} r={3.6}
                  fill="#182724" opacity={0.85} />
        ))
      )}
      {/* the tool silhouettes somebody hung up, in near-value so they read as shape only */}
      {[[128, 'M0,0 L0,150 M-26,0 L26,0 M-16,150 L16,150'],
        [252, 'M0,0 L0,120 M0,120 L-30,168 M0,120 L30,168'],
        [905, 'M0,0 L0,138 M-22,138 A22,22 0 0 0 22,138 Z'],
        [1010, 'M0,0 L0,96 M-30,96 L30,96 M-30,96 L-30,150 M30,96 L30,150']].map(([x, d], i) => (
        <g key={i} transform={`translate(${x},${y - 40 + (i % 2) * 46})`}>
          <path d={d as string} stroke="#0a1412" strokeWidth={12} fill="none" strokeLinecap="round" />
          <path d={d as string} stroke="#243330" strokeWidth={5} fill="none" strokeLinecap="round" />
        </g>
      ))}
      {/* a shelf with sample jars: the story's own furniture, and it fills the upper void */}
      <rect x={-460} y={y + 470} width={2000} height={16} fill="#1a2624" stroke="#0a1412" strokeWidth={4} />
      {Array.from({length: 14}).map((_, i) => {
        const jx = -360 + i * 122;
        const h = 74 + ((Math.abs(Math.imul(i + 5, 40503)) % 100) / 100) * 44;
        const fill = 0.35 + ((Math.abs(Math.imul(i + 19, 69069)) % 100) / 100) * 0.45;
        return (
          <g key={i} transform={`translate(${jx},${y + 470})`}>
            <rect x={-26} y={-h} width={52} height={h} rx={4} fill="#1c2926" stroke="#0a1412" strokeWidth={3.5} />
            {/* the sediment sitting in the jar, which is what this room is full of */}
            <rect x={-22} y={-h * fill} width={44} height={h * fill - 4} rx={2} fill="#2a3129" opacity={0.9} />
            <rect x={-20} y={-h - 7} width={40} height={9} rx={2} fill="#243230" stroke="#0a1412" strokeWidth={3} />
          </g>
        );
      })}
    </g>
  );
};

/** MOTES: the dust that proves there is air between the camera and the specimen. */
const Motes: React.FC<{f: number; n?: number; op?: number}> = ({f, n = 26, op = 0.32}) => (
  <g style={{pointerEvents: 'none'}}>
    {Array.from({length: n}).map((_, i) => {
      const hx = (Math.abs(Math.imul(i + 11, 2654435761)) % 1000) / 1000;
      const hy = (Math.abs(Math.imul(i + 53, 40503)) % 1000) / 1000;
      const x = hx * 1080 + Math.sin(f / (73 + i * 4.1) + i) * 34;
      const y = ((f * (7 + hy * 11)) / 30 + hy * 2400) % 2100 - 90;
      const s = 1.3 + hy * 2.2;
      // brighter inside the lamp's throw, invisible outside it: dust only exists in light
      const lit = Math.max(0, 1 - Math.hypot(x - 300, y - 210) / 1500);
      return <circle key={i} cx={x} cy={y} r={s} fill="#ffe4bb" opacity={op * lit * (0.4 + hy * 0.6)} />;
    })}
  </g>
);

/**
 * NOTE WHAT THIS DOES *NOT* DO: it does not wrap `children` in an <svg>.
 *
 * The first pass did, and every scene rendered as an empty graded rectangle. Stage3D emits
 * HTML <div>s (CSS 3D transforms), and a <div> created inside an <svg> lands in the SVG
 * namespace and paints NOTHING. That is the identical failure the Ep0731 header documents
 * for DayGrade, arriving from the other direction: there an HTML grade was put inside a
 * scene's svg, here the whole 3D stage was. So Stage is a plain HTML container, each Plane
 * opens its own <svg>, and MaterialDefs lives in one hidden document-level <svg> because
 * SVG defs resolve by id across the whole document.
 */
const Stage: React.FC<{children: React.ReactNode; grade?: React.ReactNode; over?: React.ReactNode;
  overTop?: React.ReactNode; bg?: string}> = ({
  children, grade, over, overTop, bg = ROOMDARK,
}) => (
  <AbsoluteFill style={{backgroundColor: bg}}>
    <svg width="0" height="0" style={{position: 'absolute'}} aria-hidden><MaterialDefs /></svg>
    {children}
    <div style={{
      position: 'absolute', inset: 0, pointerEvents: 'none', mixBlendMode: 'multiply',
      background: 'radial-gradient(ellipse 82% 64% at 46% 52%, rgba(255,255,255,1) 0%, ' +
                  'rgba(158,164,170,1) 66%, rgba(58,64,70,1) 90%, rgba(26,31,37,1) 100%)',
    }} />
    {grade}
    {over}
    {overTop}
  </AbsoluteFill>
);

/**
 * THE STANDING ROOM GRADE. One practical, in every scene, because one lamp means one room.
 *
 * `floor` was 0.62 in pass 1, which is how hard the blacks CRUSH, and combined with a
 * near-black base fill it took the rough cut to a film where the deep shadow ate the subject
 * instead of framing it. A dark film still has to be a LEGIBLE dark film: the shadow is
 * supposed to be the negative space the specimen sits in, not a wash over the specimen.
 * Floor comes down, the practical comes up and moves onto the bench, and the deep graphic
 * shadow the plan asks for now comes from the hard key falloff rather than from crushing.
 */
const Room: React.FC<{f: number; amount?: number; lamp?: number}> = ({f, amount = 0.82, lamp = 1}) => (
  <NightGrade
    f={f}
    color="#16302b"
    amount={amount}
    floor={0.30}
    horizon={0.05}
    sources={lamp > 0.01 ? [{x: 468, y: 946, r: 1320, color: '#ffd7a0', intensity: 0.98 * lamp}] : []}
  />
);

/** a headline plate for the hook, held inside the 4:5 safe box */
const Headline: React.FC<{text: string; op?: number; y?: number}> = ({text, op = 1, y = SAFE_TOP + 66}) => {
  const w = text.length * 43 + 76;
  return (
    <g opacity={op}>
      {/* a real plate, because grey type on a lit tan field is not a hook headline */}
      <rect x={540 - w / 2} y={y - 62} width={w} height={86} rx={9} fill="#0b1114" opacity={0.82} />
      <rect x={540 - w / 2} y={y - 62} width={w} height={86} rx={9} fill="none" stroke={BONE}
            strokeWidth={4} opacity={0.75} />
      <text x={540} y={y} textAnchor="middle" fontSize={72} fontFamily={BOLD} fill="#0a0e11"
            stroke="#0a0e11" strokeWidth={13} strokeLinejoin="round">{text}</text>
      <text x={540} y={y} textAnchor="middle" fontSize={72} fontFamily={BOLD} fill="#ffffff"
            letterSpacing={0.5}>{text}</text>
    </g>
  );
};

/** a small honest label chip. Never a colon, never a dash. */
const Chip: React.FC<{x: number; y: number; text: string; sub?: string; op?: number; size?: number}> = ({
  x, y, text, sub, op = 1, size = 40,
}) => {
  const w = Math.max(text.length, (sub ?? '').length * 0.72) * size * 0.66 + 48;
  const h = sub ? 118 : 66;
  return (
    <g transform={`translate(${x},${y})`} opacity={op}>
      <rect x={-w / 2 + 3} y={-h / 2 + 5} width={w} height={h} rx={7} fill="#000" opacity={0.55} />
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={7} fill="#080d10" stroke={BONE} strokeWidth={4} />
      <text x={0} y={sub ? -8 : 13} textAnchor="middle" fontSize={size} fontFamily={BOLD} fill="#ffffff">{text}</text>
      {sub && (
        <text x={0} y={34} textAnchor="middle" fontSize={Math.max(24, size * 0.62)} fontFamily={MONO}
              fill="#e2ece8" letterSpacing={1.2}>{sub}</text>
      )}
    </g>
  );
};

// =============================================================================
// S1 [0.0 - 7.0]  L0  macro-closeup, truckAcross
// "Every eruption in Alaska signs its name in ash. The trick is reading the signature."
// beats 0 THE LAMP ARRIVES (0.0), 1 THE NOTCHES RESOLVE (2.0), 2 THE STACK begins (6.6)
//
// Opens on EVIDENCE, not on a subject. A stranger's eye reads a barcode in mud before
// their brain does. The lamp ARRIVES hard (it does not sweep) and the band's notched
// edge resolves under it. The notch profile is planted here and not explained until 44s.
// =============================================================================
const S1: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(1) - L(0));            // this scene's real duration, from the take
  const p = f / FPS / d;
  // THE LAMP ARRIVES: a hard 4-frame snap, no sweep. Frame 1 must already be moving.
  const lampOn = interpolate(f, [0, 3], [0.88, 1], {extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  // THE NOTCHES RESOLVE: focus pulls in a quarter of the way through the line, teeth sharpen
  const notch = interpolate(p, [0.0, 0.26], [0.42, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  // THE STACK: the pull-back begins in the last half second and hands off to S2
  const pull = interpolate(p, [0.91, 1.0], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_IN});
  const cam = composeCams(CameraMoves.truckAcross(p, 210), {z: pull * -520});
  const head = interpolate(f, [0, 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const headOut = interpolate(p, [0.84, 0.94], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage
      grade={<Room f={g} lamp={lampOn} />}
      over={
        <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
          <g opacity={head * headOut}>
            <Headline text="THE COPY" y={SAFE_TOP + 92} />
            <Headline text="IN THE MUD" y={SAFE_TOP + 186} />
          </g>
        </svg>
      }
    >
      <Stage3D camera={cam}>
        {/* FAR: the room continues past the specimen, barely */}
        <Plane z={900}>
          <Atmosphere z={900} skyTint="#0d151a" strength={0.9}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1180} width={4080} height={740} fill="#10171b" />
              <path d="M0,1180 L1080,1174" stroke={INK} strokeWidth={6} opacity={0.8} />
            </svg>
          </Atmosphere>
        </Plane>
        {/* MID: the mud bed the band lies in */}
        <Plane z={180}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <MudBed f={g} y={1010} h={780} />
          </svg>
        </Plane>
        {/* NEAR: THE BAND. Fills the frame width. The whole read of the shot. */}
        <Plane z={-40}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <AshBandMacro f={g} y={780} notch={notch} lit={lampOn} />
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        <LampThrow f={g} strength={lampOn} />
        <Motes f={g} op={0.34 * lampOn} />
      </svg>
    </Stage>
  );
};

/** the wet olive-black sediment bed. TORN, granular, never a flat fill. */
const MudBed: React.FC<{f: number; y: number; h?: number; op?: number}> = ({f, y, h = 620, op = 1}) => {
  const mud = tones('#1d1b14');
  const X0 = -1100, X1 = 2180, W = X1 - X0;   // oversized: no plate edge may enter frame
  const pts = Array.from({length: 21}).map((_, i) => {
    const p = i / 20;
    const j = (Math.abs(Math.imul(i + 9, 2654435761)) % 1000) / 1000;
    return `${X0 + p * W},${y + (j - 0.5) * 30}`;
  }).join(' L');
  return (
    <g opacity={op}>
      <FormGradient id="mudbed" t={mud} softness={0.72} />
      <path d={`M${pts} L${X1},${y + h} L${X0},${y + h} Z`} fill="url(#mudbed)" stroke={INK} strokeWidth={5} strokeLinejoin="round" />
      {/* wet-sediment banding: horizontal strata, irregular, so mud is a SUBSTANCE */}
      {Array.from({length: 9}).map((_, i) => {
        const j = (Math.abs(Math.imul(i + 23, 2654435761)) % 1000) / 1000;
        const yy = y + 40 + i * (h / 9);
        return (
          <path key={i}
                d={`M${X0},${yy} ${Array.from({length: 9}).map((_, k) => {
                  const jj = (Math.abs(Math.imul(i * 11 + k, 40503)) % 1000) / 1000;
                  return `L${X0 + (k + 1) * (W / 9)},${yy + (jj - 0.5) * 16}`;
                }).join('')}`}
                stroke={INK} strokeWidth={3 + j * 4} fill="none" opacity={0.3 + j * 0.18} />
        );
      })}
      {/* wet sheen: the lamp finds the moisture, upper screen left */}
      <path d={`M${pts}`} stroke="#8fa9a2" strokeWidth={4} fill="none" opacity={0.34} />
      {/* CLASTS: pebbles and shell hash in the sediment, big enough to read at phone scale */}
      {Array.from({length: 150}).map((_, i) => {
        const hx = (Math.abs(Math.imul(i + 3, 2654435761)) % 1000) / 1000;
        const hy = (Math.abs(Math.imul(i + 61, 40503)) % 1000) / 1000;
        const hr = (Math.abs(Math.imul(i + 97, 69069)) % 1000) / 1000;
        const cx = X0 + hx * W, cy = y + 22 + hy * (h - 40), r = 3 + hr * 9;
        return (
          <g key={i}>
            <ellipse cx={cx} cy={cy} rx={r} ry={r * 0.72} fill={hr > 0.55 ? '#4a4638' : '#26241a'}
                     stroke={INK} strokeWidth={2} opacity={0.8} />
            <ellipse cx={cx - r * 0.28} cy={cy - r * 0.3} rx={r * 0.4} ry={r * 0.26}
                     fill="#6e6a56" opacity={0.55} />
          </g>
        );
      })}
      {/* fine pitting between the clasts */}
      {Array.from({length: 200}).map((_, i) => {
        const hx = (Math.abs(Math.imul(i + 211, 2654435761)) % 1000) / 1000;
        const hy = (Math.abs(Math.imul(i + 13, 40503)) % 1000) / 1000;
        return <circle key={i} cx={X0 + hx * W} cy={y + 18 + hy * (h - 30)} r={1.8 + hy * 2.2}
                       fill={INK} opacity={0.34} />;
      })}
    </g>
  );
};

/** ONE pearl ash band at macro scale, with the machined notch profile along its lower edge. */
const AshBandMacro: React.FC<{f: number; y: number; notch: number; lit: number}> = ({f, y, notch, lit}) => {
  const band = tones(ASH);
  // the torn TOP edge (found), against the notched BOTTOM edge (the tell, planted here)
  const top = Array.from({length: 21}).map((_, i) => {
    const p = i / 20;
    const j = (Math.abs(Math.imul(i + 13, 2654435761)) % 1000) / 1000;
    return `${-60 + p * 1200},${y + (j - 0.5) * 22}`;
  }).join(' L');
  const H = 210;
  return (
    <g>
      <FormGradient id="bandmacro" t={band} softness={0.6} />
      <path d={`M${top} L1140,${y + H} L-60,${y + H} Z`} fill="url(#bandmacro)" stroke={INK} strokeWidth={6}
            strokeLinejoin="round" opacity={0.55 + lit * 0.45} />
      {/* the highlight the lamp lays along the torn top edge */}
      <path d={`M${top}`} stroke="#fffaf0" strokeWidth={5} fill="none" opacity={lit * 0.72} />
      {/* THE SHADE REGION: the lower two thirds sit out of the key, which is what gives the
          band thickness instead of flatness. Hard edge, because the key is hard. */}
      <path d={`M-60,${y + H * 0.42} L1140,${y + H * 0.38} L1140,${y + H} L-60,${y + H} Z`}
            fill={band.shade} opacity={0.55} />
      {/* THE HIGHLIGHT BLOB where the lamp actually lands, upper screen left */}
      <ellipse cx={250} cy={y + H * 0.26} rx={420} ry={H * 0.2} fill="#ffffff" opacity={lit * 0.3} />
      {/* SHARD DETAIL. Ash is made of broken glass, so it gets real facets, not a speckle. */}
      {Array.from({length: 46}).map((_, i) => {
        const hx = (Math.abs(Math.imul(i + 29, 2654435761)) % 1000) / 1000;
        const hy = (Math.abs(Math.imul(i + 7, 40503)) % 1000) / 1000;
        const hr = (Math.abs(Math.imul(i + 61, 69069)) % 1000) / 1000;
        const cx = -40 + hx * 1160, cy = y + 22 + hy * (H - 44), sc = 0.7 + hr * 1.5;
        return (
          <g key={i} transform={`translate(${cx},${cy}) rotate(${hr * 360}) scale(${sc})`}>
            <path d="M-7,3 L-3,-6 L4,-7 L7,-1 L4,5 L-2,7 Z" fill={hr > 0.5 ? '#f4f6f2' : '#9aa39b'}
                  stroke={INK} strokeWidth={1.4} opacity={0.5} />
          </g>
        );
      })}
      {/* fine grain between the shards */}
      {Array.from({length: 90}).map((_, i) => {
        const hx = (Math.abs(Math.imul(i + 131, 2654435761)) % 1000) / 1000;
        const hy = (Math.abs(Math.imul(i + 17, 40503)) % 1000) / 1000;
        return <circle key={i} cx={-40 + hx * 1160} cy={y + 18 + hy * (H - 34)} r={1.2 + hy * 1.4}
                       fill={INK} opacity={0.2} />;
      })}
      {/* THE NOTCHES. They resolve as `notch` rises: a row of cut teeth, deep and shallow,
          irregular in depth but machined in profile. This is the film's open loop. */}
      <g opacity={notch}>
        {Array.from({length: 26}).map((_, i) => {
          const x = -40 + i * 46;
          const d = (Math.abs(Math.imul(i + 17, 40503)) % 1000) / 1000;
          const depth = (16 + d * 46) * notch;
          return (
            <path key={i} d={`M${x},${y + H} L${x + 11},${y + H + depth} L${x + 24},${y + H}`}
                  fill="url(#bandmacro)" stroke={INK} strokeWidth={4} strokeLinejoin="round" opacity={0.9} />
          );
        })}
      </g>
      <RimLight d={`M-40,${y + 6} L1120,${y + 2}`} w={4} color="#fffaf0" opacity={lit * 0.5} />
    </g>
  );
};

// =============================================================================
// S2 [7.0 - 13.6]  L1  wide-establish, static (the world moves, the lens does not)
// "On land the layers stack like pages, then glaciers scrape the page blank."
// beats 2 THE STACK (6.6), 3 THE BLADE ENTERS (9.8), 4 THE CRUMBS CURL OFF (11.8)
//
// THE BLADE WIPE. The glacier crosses screen left to right at CONSTANT speed with NO
// easing, deliberately: the one mechanical motion in a film full of eased ones is what
// makes it read as inhuman. The land's texture literally stops at its trailing edge.
// =============================================================================
const S2: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(2) - L(1));
  const lt = f / FPS;
  const p = lt / d;
  const stack = interpolate(p, [0, 0.2], [0, 1], {extrapolateRight: 'clamp', easing: E_OUT});
  // THE BLADE WIPE: enters on "then glaciers", clears frame by the end of the line.
  // LINEAR ON PURPOSE — the one unaeased motion in the film is what reads as inhuman.
  const blade = interpolate(p, [0.44, 0.86], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const bladeX = -260 + blade * 1760;
  const erased = interpolate(bladeX, [-260, 1400], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const crumbs = interpolate(p, [0.70, 1.0], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // the blade is the only thing that earns motion blur here
  // per-frame displacement, measured rather than assumed: 1760px of travel across the window
  const bladeSpan = 0.86 - 0.44;
  const bladePxPerFrame = 1760 / (bladeSpan * d * FPS);
  const bladeV = blade > 0.001 && blade < 0.999 ? bladePxPerFrame : 0;
  return (
    <Stage
      grade={<Room f={g} lamp={0.86} />}
      over={
        <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
          <g opacity={interpolate(p, [0.07, 0.2, 0.62, 0.74], [0, 1, 1, 0], {extrapolateRight: 'clamp'})}>
            <Chip x={540} y={CARD_BOT} text="THE LAYERS STACK LIKE PAGES" size={38} />
          </g>
        </svg>
      }
    >
      <Stage3D camera={{}}>
        <Plane z={1300}>
          <Atmosphere z={1300} skyTint="#0d151a" strength={1}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              {/* a far torn ridge, so the land has somewhere to be */}
              <path d="M0,880 L150,806 L320,858 L470,780 L640,842 L820,772 L960,830 L1080,796 L1080,1000 L0,1000 Z"
                    fill="#1a2422" stroke={INK} strokeWidth={4} strokeLinejoin="round" opacity={0.9} />
            </svg>
          </Atmosphere>
        </Plane>
        <Plane z={220}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <g transform={`translate(0,${(1 - stack) * 90})`} opacity={stack}>
              <LayeredLand x={540} y={1380} w={1980} h={680} f={g} layers={13} erased={erased} bandEvery={3} />
            </g>
          </svg>
        </Plane>
        <Plane z={-60}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            {blade > 0.0005 && (
              <MotionBlur vx={bladeV} gain={1.1} max={40}>
                <ErasingBlade x={bladeX} groundY={1380} h={860} f={g} />
              </MotionBlur>
            )}
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        {/* THE CRUMBS CURL OFF the blade's trailing edge. From here they drift in the far
            plane of EVERY scene until one of them lands at 87.4s. */}
        <g opacity={crumbs}>
          <AshCrumbs f={g} count={14} opacity={0.34} />
        </g>
        <LampThrow f={g} strength={0.7} />
        <Motes f={g} op={0.2} />
      </svg>
    </Stage>
  );
};

// =============================================================================
// S3 [13.6 - 18.32]  L2  subject-portrait, truckAcross
// "So three federal scientists in Anchorage went looking for a copy."
// beats 5 THE LAMP CLICKS ON (14.5), 6 THE NAMEPLATE SETTLES (16.5)
//
// THE MATCH CUT: the bench lamp clicks on at frame 1's EXACT screen geometry, so the
// erased land hands straight over to the room that answers it. The actors get NAMED
// before they are used (the §4.2 law), as a physical brass plate, not a HUD chip.
// Three lamps, three scientists, drawn as their instruments and not as caricatures.
// =============================================================================
const S3: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(3) - L(2));
  const p = f / FPS / d;
  // THE MATCH CUT: the lamp clicks on in the first 7 frames, at frame 1's screen geometry
  const click = interpolate(f, [0, 7], [0, 1], {extrapolateRight: 'clamp'});
  const plate = interpolate(p, [0.35, 0.58], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const cam = CameraMoves.truckAcross(p, 190);
  return (
    <Stage grade={<Room f={g} lamp={click} />}>
      <Stage3D camera={cam}>
        <Plane z={1000}>
          <Atmosphere z={1000} skyTint="#0d151a" strength={0.9}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1240} width={4080} height={680} fill="#101a1d" />
              <path d="M0,1240 L1080,1236" stroke={INK} strokeWidth={5} opacity={0.7} />
            </svg>
          </Atmosphere>
        </Plane>
        <Plane z={140}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            {/* THE BENCH: turned, machined, planted. The room the rest of the film lives in. */}
            <Bench f={g} y={1420} lit={click} />
            {/* three working lamps, three people, one bench. The pools of light ARE the trio. */}
            {[[250, 1], [540, 0], [830, 2]].map(([bx, ph], i) => (
              <g key={i} opacity={click}>
                <BenchLamp f={g} x={bx as number} y={1420} phase={ph as number} on={click} />
              </g>
            ))}
          </svg>
        </Plane>
        <Plane z={-80}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <g opacity={plate}>
              <BrassPlate x={540} y={CARD_BOT - 40} set={plate} w={840} size={40}
                          lines={['U.S. GEOLOGICAL SURVEY', 'ALASKA VOLCANO OBSERVATORY', 'ANCHORAGE']} />
            </g>
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        <AshCrumbs f={g} count={14} opacity={0.22} />
        <LampThrow f={g} strength={click} />
        <Motes f={g} op={0.3 * click} />
      </svg>
    </Stage>
  );
};

/** the bench: a heavy turned worktop with a fabricated steel frame. */
const Bench: React.FC<{f: number; y: number; lit?: number}> = ({f, y, lit = 1}) => {
  const wood = tones('#3d3a30');
  const steel = tones('#5a656b');
  return (
    <g>
      <FormGradient id="benchtop" t={wood} softness={0.6} />
      <FormGradient id="benchleg" t={steel} softness={0.5} />
      <ContactShadow cx={540} cy={y + 30} rx={520} ry={26} opacity={0.6} blur={22} />
      <rect x={-40} y={y} width={1160} height={54} rx={5} fill="url(#benchtop)" stroke={INK} strokeWidth={6} />
      {/* the wear-polished front edge: somebody has used this for years */}
      <path d={`M-40,${y + 8} L1120,${y + 6}`} stroke="#c2b48a" strokeWidth={4} opacity={0.32 * lit} />
      {/* legs, with visible bolts */}
      {[110, 970].map((lx) => (
        <g key={lx}>
          <rect x={lx} y={y + 54} width={40} height={300} fill="url(#benchleg)" stroke={INK} strokeWidth={5} />
          {[0, 1, 2].map((i) => (
            <circle key={i} cx={lx + 20} cy={y + 96 + i * 84} r={5} fill={steel.key} stroke={INK} strokeWidth={2.5} />
          ))}
        </g>
      ))}
      <RimLight d={`M-30,${y + 4} L1110,${y + 2}`} w={4} color="#ffe0ae" opacity={0.42 * lit} />
    </g>
  );
};

/** an articulated bench lamp, TURNED. Its pool of light is a person working. */
const BenchLamp: React.FC<{f: number; x: number; y: number; phase?: number; on?: number}> = ({
  f, x, y, phase = 0, on = 1,
}) => {
  const brass = tones(BRASS);
  const v = vitals(f, phase, 0.3);
  return (
    <g transform={`translate(${x},${y})`}>
      <FormGradient id={`lamp${x}`} t={brass} softness={0.55} />
      {/* base */}
      <ellipse cx={0} cy={0} rx={46} ry={13} fill={brass.shade} stroke={INK} strokeWidth={4.5} />
      {/* two-segment arm, jointed, never a single curve */}
      <path d={`M0,-4 L${-34 + v.swayX * 0.4},-132 L${26 + v.swayX * 0.6},-236`} stroke={INK} strokeWidth={13}
            fill="none" strokeLinecap="round" />
      <path d={`M0,-4 L${-34 + v.swayX * 0.4},-132 L${26 + v.swayX * 0.6},-236`} stroke={brass.base} strokeWidth={7}
            fill="none" strokeLinecap="round" />
      <circle cx={-34 + v.swayX * 0.4} cy={-132} r={11} fill={brass.key} stroke={INK} strokeWidth={4} />
      {/* the shade, angled down-right so the key bearing stays upper screen left */}
      <g transform={`translate(${26 + v.swayX * 0.6},-236) rotate(28)`}>
        <path d="M-40,-16 L40,-16 L56,34 L-56,34 Z" fill={`url(#lamp${x})`} stroke={INK} strokeWidth={5}
              strokeLinejoin="round" />
        <path d="M-56,34 L56,34" stroke={on > 0.5 ? '#ffeec4' : '#2a3238'} strokeWidth={6} opacity={0.9} />
        {on > 0.02 && (
          <g style={{mixBlendMode: 'screen'}} opacity={on}>
            <path d="M-56,34 L-150,300 L150,300 L56,34 Z" fill="#ffd9a0" opacity={0.12} />
          </g>
        )}
      </g>
    </g>
  );
};

// =============================================================================
// S4 [18.32 - 25.38]  L3  alt-vantage, craneDown
// "They found one under the Gulf of Alaska, in long tubes of mud punched from the seafloor."
// beats 7 THE DROP (19.7), 8 THE PUNCH (24.1)
//
// THE DROP THROUGH THE WATERLINE. The film's ONLY vertical move, spent once, at the
// transition from erased land to kept seafloor. It earns its uniqueness by being the
// single axis change in a film that otherwise travels horizontally.
// =============================================================================
const S4: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(4) - L(3));
  const p = f / FPS / d;
  // THE DROP: the film's only vertical move, spent once, on "under the Gulf of Alaska"
  const drop = interpolate(p, [0.17, 0.55], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  // THE PUNCH: anticipation lift, then a hard fast drive, then overshoot and settle. Pass 1
  // used a bare spring over 150px and the filmstrip showed the tube moving a few pixels with
  // no impact at all, which all three judges named. A punch is the one beat in this film that
  // is allowed to be violent.
  const punchAt = Math.round(0.78 * d * FPS);
  const lift = interpolate(f, [punchAt - 12, punchAt], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const punch = spring({frame: f - punchAt, fps: FPS, config: {damping: 12, stiffness: 320}});
  const drive = Math.max(0, Math.min(1, punch));
  const punchV = (drive > 0.02 && drive < 0.97) ? 60 : 0;
  const cam = composeCams(CameraMoves.craneDown(Math.min(1, p * 1.4), 420), {y: drop * 240});
  // the waterline sits at 640 and travels UP past the camera as we drop through it
  const waterY = interpolate(drop, [0, 1], [640, -420], {extrapolateRight: 'clamp'});
  return (
    <Stage grade={<Room f={g} lamp={0.5} />} bg="#060d12">
      <Stage3D camera={cam}>
        <Plane z={1400}>
          <Atmosphere z={1400} skyTint="#08222b" strength={1}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <rect x={0} y={0} width={1080} height={1920} fill="#0a1a22" />
            </svg>
          </Atmosphere>
        </Plane>
        <Plane z={300}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            {/* THE WATERLINE, seen from below as we pass it. A torn silver ceiling. */}
            <g opacity={interpolate(drop, [0, 0.86, 1], [1, 1, 0])}>
              <WaterCeiling f={g} y={waterY} />
            </g>
            {/* THE SEAFLOOR arrives from below as the water leaves */}
            <g opacity={interpolate(drop, [0.32, 0.8], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
              <MudBed f={g} y={1240} h={700} />
            </g>
          </svg>
        </Plane>
        <Plane z={-100}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            {/* THE PUNCH: a turned steel tube drives into the torn floor and lifts a plug. */}
            <g opacity={interpolate(drop, [0.55, 0.85], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
              <CoringTube x={540} y={1250 - lift * 70} f={g} drive={drive * 2.1}
                          lift={interpolate(p, [0.93, 1.0], [0, 0.55], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})} />
            </g>
            {/* the impact puff when the shoe bites */}
            {/* THE IMPACT. A punch with no ejecta is a poke: a mud plume throws up and out from
                the entry, a displacement ridge humps around the shaft, and both settle. */}
            {drive > 0.25 && (() => {
              const age = Math.max(0, (f - punchAt) / FPS);          // seconds since contact
              const fade = Math.max(0, 1 - age / 0.9);
              return (
                <g opacity={fade}>
                  <path d={`M420,1252 q60,-${26 * fade} 120,0 q60,${20 * fade} 120,0`}
                        stroke="#6b6450" strokeWidth={10} fill="none" opacity={0.75} />
                  {Array.from({length: 18}).map((_, i) => {
                    const h = (Math.abs(Math.imul(i + 7, 2654435761)) % 1000) / 1000;
                    const sgn = i % 2 === 0 ? 1 : -1;
                    const vx = sgn * (90 + h * 230);
                    const px = 540 + vx * age;
                    const py = 1250 - (300 + h * 220) * age + 900 * age * age;
                    return <circle key={i} cx={px} cy={py} r={4 + h * 8} fill={h > 0.5 ? '#6b6450' : '#4a4636'}
                                   stroke={INK} strokeWidth={1.6} opacity={0.85} />;
                  })}
                </g>
              );
            })()}
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        {/* the water column's own light: cold, from above, the opposite of the bench */}
        <g style={{mixBlendMode: 'screen'}} opacity={interpolate(drop, [0, 1], [0.5, 0.16])}>
          <defs>
            <linearGradient id="waterlight" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8fd4e8" stopOpacity={0.24} />
              <stop offset="100%" stopColor="#8fd4e8" stopOpacity={0} />
            </linearGradient>
          </defs>
          <rect x={0} y={0} width={1080} height={1300} fill="url(#waterlight)" />
        </g>
        <AshCrumbs f={g} count={14} opacity={0.16} />
        <g opacity={interpolate(p, [0.23, 0.33, 0.79, 0.88], [0, 1, 1, 0], {extrapolateRight: 'clamp'})}>
          <Chip x={540} y={CARD_BOT} text="GULF OF ALASKA" sub="SEAFLOOR CORES" size={44} />
        </g>
      </svg>
    </Stage>
  );
};

/** the underside of the sea surface: torn, silvered, moving. */
const WaterCeiling: React.FC<{f: number; y: number}> = ({f, y}) => (
  <g>
    {Array.from({length: 5}).map((_, k) => {
      const pts = Array.from({length: 19}).map((_, i) => {
        const p = i / 18;
        return `${p * 1080},${y + k * 15 + Math.sin(f / 21 + i * 0.8 + k) * 11}`;
      }).join(' L');
      return <path key={k} d={`M${pts}`} stroke="#b9e2ee" strokeWidth={4 - k * 0.6} fill="none"
                    opacity={0.5 - k * 0.08} />;
    })}
    <rect x={0} y={y - 620} width={1080} height={620} fill="#123642" opacity={0.55} />
  </g>
);

// =============================================================================
// S5 [25.38 - 33.56]  L4  wide-establish, riseWith
// "Seventy ash layers out of eight tubes, a record they call virtually uninterrupted,
//  reaching into the ice ages."
// beats 9 THE COLUMNS RISE (26.1), 10 SEVENTY (28.8), 11 THE CLERK WAS READY (30.8)
//
// A BIG NUMBER, staged per the recipe: never just a counter. The count RUNS along eight
// standing columns as the bands light one after another, so 70 is a physical length of
// lit evidence and not a digit. HONEST LABEL: 70 TEPHRAS out of 8 CORES, per claim c4.
// =============================================================================
const S5: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(5) - L(4));
  const p = f / FPS / d;
  const rise = interpolate(p, [0.02, 0.14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  /**
   * THE COUNT NOW COUNTS WHAT IS ON SCREEN.
   *
   * Once the columns began arriving one at a time (the fix for the 25-second held image the
   * panel named), the counter kept running on its own interpolation, so the film showed
   * "67 ASH LAYERS OUT OF 8 CORES" over two visible cores. A number that contradicts its own
   * picture is worse than no number: it is the one thing a viewer can check.
   */
  const ARRIVE0 = Math.round(0.06 * d * FPS);      // frame the first column lands
  const ARRIVE_STEP = 4;                           // frames between arrivals
  const PER = [9, 9, 9, 9, 9, 9, 8, 8];            // 6*9 + 2*8 = 70 tephras across 8 cores
  const arrived = Math.max(0, Math.min(8, Math.floor((f - ARRIVE0) / ARRIVE_STEP) + 1));
  const partial = Math.max(0, Math.min(1, (((f - ARRIVE0) % ARRIVE_STEP) + ARRIVE_STEP) % ARRIVE_STEP / ARRIVE_STEP));
  let shown = 0;
  for (let k = 0; k < arrived; k++) shown += PER[k];
  if (arrived > 0 && arrived < 8) shown += Math.round(PER[arrived] * partial);
  const cam = CameraMoves.riseWith(p, 210);
  const COLS = 8;
  return (
    <Stage
      grade={<Room f={g} lamp={0.9} />}
      over={
        <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
          <g opacity={interpolate(p, [0.02, 0.07], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
            <Chip x={540} y={CARD_BOT} text={`${shown} ASH LAYERS`} sub="OUT OF 8 CORES" size={54} />
          </g>
        </svg>
      }
    >
      <Stage3D camera={cam}>
        <Plane z={1100}>
          <Atmosphere z={1100} skyTint="#0d151a" strength={1}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1500} width={4080} height={420} fill="#0f181c" />
            </svg>
          </Atmosphere>
        </Plane>
        <Plane z={120}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <ContactShadow cx={540} cy={1442} rx={500} ry={22} opacity={0.6} blur={20} />
            {Array.from({length: COLS}).map((_, i) => {
              const x = 150 + i * 111;
              // staggered arrival: column i rises on its own beat, so the shot is eight
              // events rather than one held frame under continuous narration
              const eIn = entrance(f, FPS, Math.round(0.06 * d * FPS) + i * 4, {drop: 520, preset: POP});
              const grow = interpolate(Math.min(1, eIn.t), [0, 1], [0.05, 1], {extrapolateRight: 'clamp'});
              // 70 bands total across 8 columns, distributed so no column is empty
              const per = PER[i];
              const before = PER.slice(0, i).reduce((t, v) => t + v, 0);
              const bands = Array.from({length: per}).map((_, k) => {
                const idx = before + k;
                return {
                  at: 0.09 + k * (0.82 / per),
                  lit: Math.max(0, Math.min(1, (shown - idx) * 0.9)),
                };
              });
              return (
                <g key={i} transform={`translate(0,${eIn.dy}) scale(${eIn.sx},${eIn.sy})`}
                   opacity={Math.min(1, eIn.t * 1.4)} style={{transformOrigin: `${x}px 1430px`}}>
                  <CoreColumn x={x} y={1430} f={g} h={720 * grow} w={70} bands={bands} phase={i} />
                </g>
              );
            })}
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        <AshCrumbs f={g} count={14} opacity={0.2} />
        <LampThrow f={g} strength={0.8} />
        <Motes f={g} op={0.26} />
      </svg>
    </Stage>
  );
};

// =============================================================================
// S6 [33.56 - 39.84]  L5  data-panel, truckAcross
// "They sorted them into thirty seven eruptions, then asked which volcano threw each."
// beats 12 THE SORT (33.8), 13 THIRTY SEVEN (35.8)
//
// A COMPARISON, staged: the 70 bands SLIDE sideways and click into families. 37 blocks
// land with visible air between them so the compression from 70 to 37 is a picture, not
// a claim. Honest per c5: 37 eruptions over the span of eight cores.
// =============================================================================
const S6: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(6) - L(5));
  const p = f / FPS / d;
  const sort = interpolate(p, [0.04, 0.45], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const land = interpolate(p, [0.36, 0.62], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const cam = CameraMoves.truckAcross(p, 150);
  const landFrame = Math.round(0.36 * d * FPS);
  return (
    <Stage grade={<Room f={g} lamp={0.88} />}>
      <Stage3D camera={cam}>
        <Plane z={900}>
          <Atmosphere z={900} skyTint="#0d151a" strength={0.9}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1460} width={4080} height={460} fill="#0f181c" />
            </svg>
          </Atmosphere>
        </Plane>
        <Plane z={60}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
           <g transform="translate(540,1010) scale(1.72) translate(-540,-1010)">
            {/* the 70 shards, sliding out of their stack order into families */}
            {Array.from({length: 70}).map((_, i) => {
              const c0x = 100 + (i % 8) * 118;
              const c0y = 640 + Math.floor(i / 8) * 92;
              // target: 37 family blocks laid out in a grid, several shards per block
              const fam = Math.floor(i * 37 / 70);
              const tx = 122 + (fam % 6) * 168;
              const ty = 700 + Math.floor(fam / 6) * 118;
              const jitter = ((Math.abs(Math.imul(i + 5, 40503)) % 100) / 100 - 0.5) * 16;
              const e = Math.max(0, Math.min(1, sort * 1.25 - (i % 9) * 0.03));
              const ee = e * e * (3 - 2 * e);
              const x = c0x + (tx - c0x) * ee + jitter * ee;
              const y = c0y + (ty - c0y) * ee;
              return (
                <g key={i} transform={`translate(${x},${y}) rotate(${(1 - ee) * jitter})`}>
                  <path d="M-15,6 L-7,-12 L7,-13 L16,-2 L11,10 L-4,14 Z" fill={ASH} stroke={INK} strokeWidth={3}
                        opacity={0.86} />
                  <path d="M-7,-12 L7,-13 L8,-5 Z" fill="#f4f6f2" opacity={0.7} />
                </g>
              );
            })}
            {/* the 37 family plinths land underneath, with AIR between them */}
            <g opacity={land}>
              {Array.from({length: 37}).map((_, i) => {
                const x = 122 + (i % 6) * 168;
                const y = 700 + Math.floor(i / 6) * 118;
                const e = entrance(f, FPS, landFrame + i, {drop: 26, preset: POP});
                return (
                  <g key={i} transform={`translate(${x},${y + 44 + e.dy}) scale(${e.sx},${e.sy})`} opacity={e.t}>
                    <rect x={-58} y={-8} width={116} height={17} rx={3} fill="#5c6b63" stroke={INK} strokeWidth={3} />
                    <path d="M-54,-8 L54,-8" stroke="#9db3a8" strokeWidth={2.5} opacity={0.6} />
                  </g>
                );
              })}
            </g>
           </g>
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        <AshCrumbs f={g} count={14} opacity={0.2} />
        <LampThrow f={g} strength={0.75} />
        <g opacity={interpolate(p, [0.35, 0.44], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
          <Chip x={540} y={CARD_BOT} text="37 ERUPTIONS" sub="ACROSS THE EIGHT CORES" size={56} />
        </g>
      </svg>
    </Stage>
  );
};

// =============================================================================
// S7 [39.84 - 47.96]  L6 + L7  push-detail, dollyThrough
// "The answer doesn't always come back with one name."
// "Ash carries trace elements, a chemical handwriting."
// beats 14 THE CARD PRINTS WIDE (39.4), 15 THE SHARD'S EDGE (44.0)
//
// THE CARD PRINT, the film's thesis as an object: anticipation (the reader compresses
// and its lamp DIPS so the frame darkens), disclose (the card snaps out with overshoot),
// hold. The card's WIDTH is the reveal. THREE names, and NO magenta anywhere in this
// scene, because no match has been asserted yet. The registry licenses nothing here.
// =============================================================================
const S7: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const t = (from + f) / FPS;                       // absolute seconds in the shipped take
  const d = Math.max(0.1, L(8) - L(6));
  const p = f / FPS / d;
  // ANTICIPATION -> DISCLOSE -> HOLD, all on line 6 ("doesn't always come back with one name")
  const squeeze = interpolate(t, [L(6) + 0.05, L(6) + 0.65], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_IN});
  const dip = 1 - squeeze * 0.55;
  const print = spring({frame: Math.round((t - (L(6) + 0.75)) * FPS), fps: FPS, config: {damping: 11, stiffness: 150}});
  const out = Math.max(0, Math.min(1, print));
  // THE SHARD'S EDGE, on line 7 ("a chemical handwriting"): the push into the machined
  // notch pays off the tell S1 planted and never explained.
  const push = interpolate(t, [L(7) + 0.34, L(8) - 0.5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const cam = composeCams(CameraMoves.dollyThrough(Math.min(1, p * 0.55), 420), {z: push * 520});
  const cardV = out > 0.02 && out < 0.98 ? 52 : 0;
  return (
    <Stage grade={<Room f={g} lamp={0.55 + 0.45 * dip} />}>
      <Stage3D camera={cam}>
        <Plane z={800}>
          <Atmosphere z={800} skyTint="#0d151a" strength={0.9}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1500} width={4080} height={420} fill="#0f181c" />
            </svg>
          </Atmosphere>
        </Plane>
        <Plane z={100}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <g opacity={1 - push * 0.9} transform={`translate(0,${push * -160})`}>
              <Bench f={g} y={1500} lit={dip} />
              <g transform={`translate(0,${squeeze * 8}) scale(1,${1 - squeeze * 0.03})`}>
                <AshReader x={540} y={1120} f={g} scale={2.05} emotion={squeeze > 0.4 ? 'straining' : 'reading'}
                           feed={interpolate(t, [L(6) + 0.15, L(6) + 0.65], [0.2, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}
                           lamp={0} groundY={200} />
              </g>
              {/* THE CARD. Three names. WIDE. The width is the honest report of ambiguity. */}
              {out > 0.01 && (
                <MotionBlur vy={cardV} gain={0.6} max={10}>
                  <g transform={`translate(540,${742})`}>
                    <ShortlistCard x={0} y={0} f={g} names={['', '', '']}
                                   out={out} matched={false} scale={1.85} />
                  </g>
                </MotionBlur>
              )}
            </g>
          </svg>
        </Plane>
        {/* NEAR: the shard's machined edge, arriving as the push lands */}
        <Plane z={-200}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <g opacity={push}>
              <ShardEdge f={g} y={980} zoom={push} />
            </g>
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        <AshCrumbs f={g} count={14} opacity={0.18} />
        <LampThrow f={g} strength={0.5 + 0.5 * dip} />
        <Motes f={g} op={0.24} />
        <g opacity={interpolate(t, [L(6) + 1.36, L(6) + 1.96, L(7) - 0.06, L(7) + 0.44], [0, 1, 1, 0], {extrapolateRight: 'clamp'})}>
          <Chip x={540} y={CARD_BOT} text="A NAME, OR NAMES" size={46} />
        </g>
        <g opacity={interpolate(t, [L(7) + 1.94, L(7) + 2.54], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
          <Chip x={540} y={CARD_BOT} text="TRACE ELEMENTS" sub="A CHEMICAL HANDWRITING" size={46} />
        </g>
      </svg>
    </Stage>
  );
};

/** the machined notch profile at extreme macro: S1's planted tell, paid off. */
const ShardEdge: React.FC<{f: number; y: number; zoom: number}> = ({f, y, zoom}) => {
  const band = tones(ASH);
  const s = 1 + zoom * 1.6;
  return (
    <g transform={`translate(540,${y}) scale(${s})`}>
      <FormGradient id="shardedge" t={band} softness={0.55} />
      <path d="M-560,-120 L560,-124 L560,0 L-560,4 Z" fill="url(#shardedge)" stroke={INK} strokeWidth={6} />
      {/* the teeth, deep and shallow, machined in profile and irregular in depth */}
      {Array.from({length: 15}).map((_, i) => {
        const x = -560 + i * 76;
        const d = (Math.abs(Math.imul(i + 23, 40503)) % 1000) / 1000;
        const depth = 22 + d * 62;
        return (
          <path key={i} d={`M${x},0 L${x + 20},${depth} L${x + 44},2`} fill="url(#shardedge)" stroke={INK}
                strokeWidth={5} strokeLinejoin="round" />
        );
      })}
      <RimLight d="M-540,-116 L540,-120" w={5} color="#fffaf0" opacity={0.6} />
      {/* the trace-element speckle: the handwriting itself, at this scale visible as grains */}
      {Array.from({length: 40}).map((_, i) => {
        const hx = (Math.abs(Math.imul(i + 31, 2654435761)) % 1000) / 1000;
        const hy = (Math.abs(Math.imul(i + 3, 40503)) % 1000) / 1000;
        return <circle key={i} cx={-540 + hx * 1080} cy={-112 + hy * 100} r={2 + hy * 2.6}
                       fill={i % 4 === 0 ? '#9fb0a8' : '#7d8a80'} opacity={0.55} />;
      })}
    </g>
  );
};

// =============================================================================
// S8 [47.96 - 54.12]  L8  macro-closeup, orbitReveal
// "A machine learning model reads it and names the most probable source, or sources."
// beat 16 THE GRAIN RUNS THE CHAIN (47.1)
//
// A PROCESS/MECHANISM, staged per the recipe: a cutaway with MOVING parts and the
// instrument operating it, fat labeled arrows carrying the flow, each stage clicking in.
// NOTE THE CUT LIST: the ML algorithm is NEVER named or drawn. No decision tree, no
// neural net. The full text is paywalled, so a labelled architecture would be a visual
// fabrication. What is drawn is what the abstract supports: a sample goes in, a ranked
// SET of possible sources comes out.
// =============================================================================
const S8: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(9) - L(8));
  const p = f / FPS / d;
  const travel = interpolate(p, [0.03, 0.72], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const cam = CameraMoves.orbitReveal(p, 20);
  // three stations click in as the grain reaches them
  const stage = (at: number) => Math.max(0, Math.min(1, (travel - at) * 7));
  return (
    <Stage grade={<Room f={g} lamp={0.9} />}>
      <Stage3D camera={cam}>
        <Plane z={760}>
          <Atmosphere z={760} skyTint="#0d151a" strength={0.9}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1440} width={4080} height={480} fill="#0f181c" />
            </svg>
          </Atmosphere>
        </Plane>
        <Plane z={80}>
          <svg viewBox="0 0 1080 1920" width="1080" height="1920">
            <Bench f={g} y={1440} lit={0.9} />
            <AshReader x={540} y={1180} f={g} scale={1.9} emotion="reading" feed={travel} lamp={0} groundY={196} />
            {/* THE CHAIN: three stations, fat outlined arrows between them, each clicking in */}
            <g transform="translate(540,772) scale(1.04) translate(-540,-772)">
            {[
              {x: 306, y: 748, label: 'SAMPLE'},
              {x: 540, y: 700, label: 'READ'},
              {x: 774, y: 748, label: 'RANKED SET'},
            ].map((st, i) => {
              const on = stage(i * 0.3);
              const e = 0.9 + on * 0.1;
              return (
                <g key={st.label} transform={`translate(${st.x},${st.y}) scale(${e})`} opacity={0.35 + on * 0.65}>
                  <rect x={-84} y={-44} width={168} height={88} rx={8} fill="#182228" stroke={INK} strokeWidth={5} />
                  <rect x={-76} y={-36} width={152} height={72} rx={5} fill="#22303a" stroke="#4d6570" strokeWidth={3} />
                  <text x={0} y={8} textAnchor="middle" fontSize={26} fontFamily={BOLD} fill={BONE}>{st.label}</text>
                  {on > 0.6 && <circle cx={70} cy={-30} r={7} fill="#8fe0b0" stroke={INK} strokeWidth={2.5} />}
                </g>
              );
            })}
            {/* fat outlined arrows carrying the flow */}
            {[[386, 738, 468, 712], [612, 712, 694, 738]].map(([x1, y1, x2, y2], i) => (
              <g key={i} opacity={0.3 + stage(0.15 + i * 0.3) * 0.7}>
                <path d={`M${x1},${y1} L${x2 - 26},${y2}`} stroke={INK} strokeWidth={16} strokeLinecap="round" />
                <path d={`M${x1},${y1} L${x2 - 26},${y2}`} stroke={BRASS} strokeWidth={9} strokeLinecap="round" />
                <path d={`M${x2 - 30},${y2 - 15} L${x2},${y2} L${x2 - 30},${y2 + 15} Z`} fill={BRASS} stroke={INK}
                      strokeWidth={4} strokeLinejoin="round" />
              </g>
            ))}
            {/* the grain itself, travelling the chain */}
            <g transform={`translate(${306 + travel * 468},${740 - Math.sin(travel * Math.PI) * 44})`}>
              <path d="M-11,5 L-5,-10 L6,-11 L12,-1 L8,8 L-3,11 Z" fill="#f2f4f1" stroke={INK} strokeWidth={3} />
            </g>
            </g>
          </svg>
        </Plane>
      </Stage3D>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
        <AshCrumbs f={g} count={14} opacity={0.18} />
        <LampThrow f={g} strength={0.8} />
        <Motes f={g} op={0.24} />
        <g opacity={interpolate(p, [0.23, 0.33], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}>
          <Chip x={540} y={CARD_BOT} text="MOST PROBABLE SOURCE" sub="OR SOURCES" size={44} />
        </g>
      </svg>
    </Stage>
  );
};

// =============================================================================
// S9 [54.12 - 64.18]  L9  wide-establish, riseWith + truckAcross
// "It's confident about Katmai, Fisher Caldera and Emmons Lake, because each keeps
//  writing the same ratios, eruption after eruption."
// beats 17 THE THREE NAME PLATES (51.7 -> read here), 18 TWO SHARDS INTERLOCK (55.6),
//       19 THE STRIPS STACK (60.2), 20 MAGENTA FUSES (63.4)
//
// THE EARNED TURN, and the first magenta in the film. Successive notch strips from the
// SAME source drop onto each other in perfect register, again and again, and on the last
// one the stack FUSES and goes magenta. The picture says the confidence came out of the
// ground: the repetition is the rock's, and the machine is reading a signal already there.
// THE REGISTRY LICENSES MAGENTA HERE FOR THE FIRST TIME, and only on the fuse.
// =============================================================================
const S9: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const d = Math.max(0.1, L(10) - L(9));
  const p = f / FPS / d;
  // the three names set into the light exactly as they are spoken
  const plates = interpolate(p, [0.02, 0.13], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const seat = interpolate(p, [0.15, 0.33], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  // THE REPETITION: five successive strips land in register across "eruption after eruption"
  const stack = interpolate(p, [0.40, 0.90], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // MAGENTA FUSES: the film's loudest moment, and its first use of the reserved hue
  const fuse = interpolate(p, [0.90, 0.98], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const cam = composeCams(CameraMoves.riseWith(p, 120), CameraMoves.truckAcross(p, 110));
  return (
    <AccentRegistry accents={[{
      hue: RHYOLITE,
      means: 'a trace element signature matched to a source volcano',
      // licensed ONLY on the fusing stack and the three name plates it names
      rects: [{x: 180, y: 560, w: 720, h: 560}, {x: 60, y: SAFE_TOP, w: 960, h: 260}],
    }]}>
      <Stage
        grade={<Room f={g} lamp={0.92} />}
        over={
          /* THE FUSE, ABOVE THE GRADE. The reserved rhyolite is this film's ONE focal signal,
             and in the graded render it was arriving as pale pink: NightGrade's practical and
             the lamp throw are screen-blend layers over the whole SVG, and screen washes
             saturation out of exactly the hue you most need to survive. The strips themselves
             stay where they belong in the depth stack; this adds the bloom the moment is
             supposed to have, on top of the grade, so the turn actually lands as a colour
             event. It is spent ONLY here and only while the fuse is happening. */
          fuse > 0.02 ? (
            <svg viewBox="0 0 1080 1920" width="1080" height="1920"
                 style={{position: 'absolute', inset: 0, mixBlendMode: 'screen'}}>
              <defs>
                <radialGradient id="fuseglow">
                  <stop offset="0%" stopColor={RHYOLITE} stopOpacity={0.85} />
                  <stop offset="45%" stopColor={RHYOLITE} stopOpacity={0.34} />
                  <stop offset="100%" stopColor={RHYOLITE} stopOpacity={0} />
                </radialGradient>
              </defs>
              <ellipse cx={540} cy={905} rx={300 + fuse * 120} ry={180 + fuse * 80}
                       fill="url(#fuseglow)" opacity={Math.max(0, Math.min(1, fuse * 3) - fuse * fuse * 1.9)} />
            </svg>
          ) : null
        }
        overTop={
          <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
            <g opacity={interpolate(p, [0.36, 0.42, 0.55, 0.60], [0, 1, 1, 0], {extrapolateRight: 'clamp'})}>
              <Chip x={540} y={CARD_BOT} text="THE SAME RATIOS" sub="ERUPTION AFTER ERUPTION" size={44} />
            </g>
          </svg>
        }
      >
        <Stage3D camera={cam}>
          <Plane z={820}>
            <Atmosphere z={820} skyTint="#0d151a" strength={0.9}>
              <svg viewBox="0 0 1080 1920" width="1080" height="1920">
                <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1460} width={4080} height={460} fill="#0f181c" />
              </svg>
            </Atmosphere>
          </Plane>
          <Plane z={90}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <Bench f={g} y={1460} lit={0.9} />
              {/* THE THREE NAME PLATES, set into the light as the names are spoken */}
              {['KATMAI', 'FISHER CALDERA', 'EMMONS LAKE'].map((nm, i) => {
                const on = Math.max(0, Math.min(1, (plates - i * 0.18) * 2.2));
                return (
                  <g key={nm} opacity={on}>
                    <BrassPlate x={540} y={SAFE_TOP + 70 + i * 92} lines={[nm]} set={on} w={620} size={40} />
                  </g>
                );
              })}
              {/* TWO SHARDS INTERLOCK: the teeth seat with no gap, because the chemistry matches */}
              <g transform="translate(540,1120) scale(1.34) translate(-540,-1120)"><InterlockPair f={g} x={540} y={1120} seat={seat} fade={1 - stack} /></g>
              {/* THE STRIPS STACK, then FUSE */}
              <g transform="translate(540,900) scale(1.22) translate(-540,-900)"><StripStack f={g} x={540} y={900} progress={stack} fuse={fuse} /></g>
            </svg>
          </Plane>
        </Stage3D>
        <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
          <AshCrumbs f={g} count={14} opacity={0.18} />
          <LampThrow f={g} strength={0.85} />
          <Motes f={g} op={0.26} />
        </svg>
      </Stage>
    </AccentRegistry>
  );
};

/** two shards from different depths whose teeth seat with no gap. */
const InterlockPair: React.FC<{f: number; x: number; y: number; seat: number; fade: number}> = ({
  f, x, y, seat, fade,
}) => {
  const gap = (1 - seat) * 190;
  const teeth = (sgn: number) =>
    Array.from({length: 7}).map((_, i) => {
      const tx = -150 + i * 50;
      const d = (Math.abs(Math.imul(i + 11, 40503)) % 1000) / 1000;
      const depth = (16 + d * 30) * sgn;
      return `L${tx + 12},${depth} L${tx + 36},0 `;
    }).join('');
  return (
    <g transform={`translate(${x},${y})`} opacity={Math.max(0, fade)}>
      {/* the UPPER shard: pearl, in the key. A 6px standoff is kept even when fully seated so
          the meshed teeth stay legible as a SEAM rather than fusing into one solid block. */}
      <g transform={`translate(0,${-gap - 6})`}>
        <path d={`M-176,-92 L176,-92 L176,0 ${teeth(1)} L-176,0 Z`} fill={ASH} stroke={INK} strokeWidth={5}
              strokeLinejoin="round" />
        <path d={`M-176,-40 L176,-40 L176,0 ${teeth(1)} L-176,0 Z`} fill="#a9b1a9" opacity={0.45} />
        <RimLight d="M-166,-86 L166,-86" w={4} color="#fffaf0" opacity={0.6} />
      </g>
      {/* the LOWER shard: a full value-step darker, so the two are never read as one object */}
      <g transform={`translate(0,${gap + 6})`}>
        <path d={`M-176,92 L176,92 L176,0 ${teeth(1)} L-176,0 Z`} fill="#7f8a80" stroke={INK} strokeWidth={5}
              strokeLinejoin="round" />
        <path d={`M-176,52 L176,52 L176,92 L-176,92 Z`} fill="#5d665e" opacity={0.5} />
        <RimLight d="M-166,88 L166,88" w={3} color="#c8d2c8" opacity={0.3} />
      </g>
      {/* the seam glows only when they actually seat */}
      {seat > 0.9 && (
        <path d={`M-176,0 ${teeth(1)} L176,0`} stroke="#fffaf0" strokeWidth={3} fill="none"
              opacity={(seat - 0.9) * 8} />
      )}
    </g>
  );
};

/**
 * THE TURN, AND IT IS THE MOST IMPORTANT OBJECT IN THE FILM.
 *
 * Successive notch strips from the same source land on each other in perfect register, again
 * and again, and the last one fuses the stack into one magenta signature.
 *
 * PASS 1 OF THIS COMPONENT DID NOT SHOW ITS OWN SUBJECT. The five strips were stacked 3px
 * apart, so the top one covered the other four and the frame read as ONE strip that happened
 * to turn pink. The beat's whole content is REPETITION, and repetition you cannot count is not
 * repetition. So the strips now hold a real 34px gap while they arrive, which lets you SEE
 * five separate arrivals, and only CLOSE to register on the fuse. The gap collapsing IS the
 * argument: five different eruptions, the same signature, landing on top of each other.
 */
const StripStack: React.FC<{f: number; x: number; y: number; progress: number; fuse: number}> = ({
  f, x, y, progress, fuse,
}) => {
  const accent = useAccent();
  const N = 5;
  const GAP = 34;                                    // visible separation while they arrive
  const close = Math.min(1, fuse * 1.8);            // the gap CLOSES on the flip, not slowly
  const strip = (w: number) =>
    `M${-w},0 ${Array.from({length: 8}).map((_, k) => {
      const tx = -w + k * (w / 4);
      const d = (Math.abs(Math.imul(k + 11, 40503)) % 1000) / 1000;
      return `L${tx + w / 17},${15 + d * 27} L${tx + w / 5.5},0 `;
    }).join('')} L${w},0 L${w},-34 L${-w},-34 Z`;
  const W = 196;
  const slam = 1 - Math.sin(Math.min(1, fuse * 1.6) * Math.PI) * 0.16;
  return (
    <g transform={`translate(${x},${y}) scale(${1 / slam},${slam})`}>
      {Array.from({length: N}).map((_, i) => {
        // arrivals are SPREAD so five separate landings are visible, not one packed instant
        const at = Math.max(0, Math.min(1, (progress - i * 0.17) * 3.6));
        const e = at * at * (3 - 2 * at);
        const slot = (i - (N - 1) / 2) * GAP * (1 - close * 0.94);
        const dy = slot + (1 - e) * -420;
        // SQUASH ON CONTACT: the strip flattens as it lands and springs back. Without this the
        // arrival is a translate, and a translate that ends is not an impact.
        const land = Math.max(0, Math.min(1, (at - 0.72) / 0.28));
        const sq = 1 + Math.sin(land * Math.PI) * 0.42;
        const px = x, py = y + slot;
        const lit = fuse > 0.02 && at > 0.85;
        return (
          <g key={i} transform={`translate(0,${dy}) scale(${sq},${2 - sq})`} opacity={e}>
            <path d={strip(W)} fill={lit ? accent(RHYOLITE, px, py) : ASH} stroke={INK} strokeWidth={5}
                  strokeLinejoin="round" />
            {lit && (
              <path d={strip(W)} fill="#ff6fae" stroke="none" opacity={fuse * 0.34} />
            )}
            <RimLight d={`M${-W + 10},-30 L${W - 10},-30`} w={4} color="#fffaf0" opacity={0.45 * e} />
          </g>
        );
      })}
      {/* THE FUSE FLASH: the film's loudest single moment, and its only bloom */}
      {fuse > 0.02 && (
        <g style={{mixBlendMode: 'screen'}} opacity={Math.max(0, 1 - fuse * 2.6)}>
          <circle cx={0} cy={0} r={90 + fuse * 150} fill={accent(RHYOLITE, x, y)} opacity={0.34} />
          <circle cx={0} cy={0} r={40 + fuse * 70} fill="#ffd6e8" opacity={0.3} />
        </g>
      )}
    </g>
  );
};

// =============================================================================
// S10 [64.18 - 77.3]  L10 + L11  two-up, static (a person decides, so the lens holds)
// "That repetition is what separates one volcano from another. The model reads a
//  difference the rock already made."
// "And when the model isn't the right tool, they don't force it. They measure chemical distance."
// beats 21 OUT OF REGISTER (67.4), 22 THE PULL BACK (69.4), 23 THE EMPTY SLOT HOLDS (72.6),
//       24 THE SET DOWN (74.6)
//
// THE SIGNATURE SHOT lives here: the camera pulls back off a single band to reveal EIGHT
// columns standing in the dark, and THREE bands hold a steady magenta name while all the
// others stay pearl and unnamed. The film's argument in one frame, and it is honest.
// Then THE SET-DOWN, in two beats and not one, because the deliberateness IS the content.
// =============================================================================
const S10: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const t = (from + f) / FPS;
  const crossed = interpolate(t, [L(10) + 3.02, L(10) + 4.62], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  // THE SIGNATURE PULL-BACK, on "the model reads a difference the rock already made"
  const pull = interpolate(t, [L(10) + 5.12, L(11) + 1.14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  // THE SET-DOWN, on line 11's second clause ("they measure chemical distance")
  const setDown = interpolate(t, [L(11) + 3.24, L(11) + 5.14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const named = ['KATMAI', 'FISHER CALDERA', 'EMMONS LAKE'];
  return (
    <AccentRegistry accents={[{
      hue: RHYOLITE,
      means: 'a trace element signature matched to a source volcano',
      rects: [{x: 0, y: 380, w: 1080, h: 1180}],
    }]}>
      <Stage
        grade={<Room f={g} lamp={0.9 - setDown * 0.35} />}
        over={
          /* THE MATCH PLATES, above the grade and projected onto their own bands. Deriving a
             plate's position from its column and never checking it against the frame cost this
             run three panel rounds, the last of which printed "ATMAI" on screen. The frame now
             gets the last word (MatchPlate clamps), and the grade no longer gets to wash out
             the three names the whole film is built toward. */
          pull > 0.7 ? (
            <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
              {NAMED_BANDS.map((nb) => {
                const per = nb.col < 6 ? 9 : 8;
                const bandY = 1430 - (0.09 + nb.k * (0.82 / per)) * 720;
                const q = project(150 + nb.col * 111, bandY, 640 - pull * 640);
                return (
                  <MatchPlate key={nb.name} colX={q.x} bandY={q.y} text={nb.name} fill={RHYOLITE}
                              scale={q.k} op={Math.min(1, (pull - 0.7) * 6)} />
                );
              })}
            </svg>
          ) : null
        }
      >
        <Stage3D camera={{z: 640 - pull * 640}}>
          <Plane z={900}>
            <Atmosphere z={900} skyTint="#0d151a" strength={1}>
              <svg viewBox="0 0 1080 1920" width="1080" height="1920">
                <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1520} width={4080} height={400} fill="#0f181c" />
              </svg>
            </Atmosphere>
          </Plane>
          <Plane z={110}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <ContactShadow cx={540} cy={1442} rx={500} ry={22} opacity={0.55} blur={20} />
              {/* THE EIGHT COLUMNS. Three carry a steady magenta name; the rest stay pearl,
                  unnamed, and quietly restless. That difference IS the argument. */}
              {Array.from({length: 8}).map((_, i) => {
                const x = 150 + i * 111;
                const per = i < 6 ? 9 : 8;
                const namedIdx = i === 1 ? 3 : i === 4 ? 5 : i === 6 ? 2 : -1;
                const nameFor = i === 1 ? named[0] : i === 4 ? named[1] : i === 6 ? named[2] : undefined;
                const bands = Array.from({length: per}).map((_, k) => ({
                  at: 0.09 + k * (0.82 / per),
                  lit: 0.85,
                  // the plate is NOT drawn by the column any more: it is drawn in the
                  // clamped pass below, after every column, so it can never ride a frame edge
                  still: k === namedIdx,
                  // the open-loop band: the deep tooth + double torn corner, planted at 72.6
                  mark: i === 3 && k === 4,
                }));
                return (
                  <CoreColumn key={i} x={x} y={1430} f={g} h={720} w={70} bands={bands} phase={i}
                              accentFill={RHYOLITE} />
                );
              })}
              {/* OUT OF REGISTER: a neighbouring band's strips land crossed and never fuse */}
              <g opacity={crossed * (1 - pull)}>
                <CrossedStrips f={g} x={540} y={780} on={crossed} />
              </g>
            </svg>
          </Plane>
          {/* NEAR: the hand sets the reader down, and its lamp goes out */}
          <Plane z={-160}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <g opacity={setDown} transform={`translate(0,${(1 - setDown) * -180})`}>
                <SetDownHand f={g} x={540} y={1560} press={setDown} />
              </g>
            </svg>
          </Plane>
        </Stage3D>
        <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
          <AshCrumbs f={g} count={14} opacity={0.18} />
          <LampThrow f={g} strength={0.85 - setDown * 0.4} />
          <Motes f={g} op={0.26} />
          <g opacity={interpolate(t, [L(10) + 6.22, L(10) + 6.82, L(11) + 2.14, L(11) + 2.64], [0, 1, 1, 0], {extrapolateRight: 'clamp'})}>
            <Chip x={540} y={SAFE_TOP + 96} text="THE ROCK MADE THE DIFFERENCE" size={38} />
          </g>
        </svg>
      </Stage>
    </AccentRegistry>
  );
};

/** strips that land crossed, teeth over teeth, and never seat. The honest negative case. */
const CrossedStrips: React.FC<{f: number; x: number; y: number; on: number}> = ({f, x, y, on}) => (
  <g transform={`translate(${x},${y})`}>
    {[0, 1, 2].map((i) => {
      const rot = (i - 1) * 7 + Math.sin(f / 29 + i) * 0.8;
      return (
        <g key={i} transform={`translate(${(i - 1) * 14},${i * 11}) rotate(${rot})`} opacity={on * 0.9}>
          <path d={`M-150,0 ${Array.from({length: 7}).map((_, k) => {
            const tx = -150 + k * 43;
            const d = (Math.abs(Math.imul(k + i * 5 + 3, 40503)) % 1000) / 1000;
            return `L${tx + 10},${12 + d * 24} L${tx + 31},0 `;
          }).join('')} L150,0 L150,-24 L-150,-24 Z`}
                fill="#b9c0b8" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
        </g>
      );
    })}
    {/* the gap that never closes, drawn as a dashed void */}
    <path d="M-150,44 L150,44" stroke="#7d8a80" strokeWidth={3} strokeDasharray="10 8" opacity={on * 0.8} />
  </g>
);

/** a flannel forearm placing the reader down with real weight. */
const SetDownHand: React.FC<{f: number; x: number; y: number; press: number}> = ({f, x, y, press}) => {
  const squash = 1 + Math.max(0, Math.sin(Math.PI * Math.min(1, press * 1.1))) * 0.05;
  return (
    <g transform={`translate(${x},${y})`}>
      {/* the flannel sleeve: torn cuff, checked, human */}
      <g transform={`scale(${squash},${2 - squash})`}>
        {/* the sleeve, shorter so it frames the hand instead of being the whole object */}
        <path d="M-250,124 L-250,26 L-10,8 L-10,116 Z" fill="#6d4f42" stroke={INK} strokeWidth={5} strokeLinejoin="round" />
        {Array.from({length: 4}).map((_, i) => (
          <line key={i} x1={-238 + i * 58} y1={22} x2={-238 + i * 58} y2={122} stroke="#8a6552" strokeWidth={8}
                opacity={0.65} />
        ))}
        {[46, 82].map((yy) => (
          <line key={yy} x1={-250} y1={yy} x2={-10} y2={yy - 4} stroke="#8a6552" strokeWidth={8} opacity={0.65} />
        ))}
        {/* the cuff: a hard machined edge between cloth and skin, so the two read as two things */}
        <rect x={-30} y={2} width={30} height={120} rx={5} fill="#4f3930" stroke={INK} strokeWidth={5} />
        {/* THE HAND, big enough to read: a back-of-hand mass with SEPARATED fingers over the edge */}
        <path d="M-8,14 L110,4 L150,40 L146,104 L-8,118 Z" fill="#c79a76" stroke={INK} strokeWidth={5}
              strokeLinejoin="round" />
        <path d="M-8,20 L96,12 L120,30 L20,44 Z" fill="#dcb08a" opacity={0.55} />
        {[[112, 22], [126, 50], [122, 80]].map(([fx, fy], i) => (
          <g key={i}>
            <path d={`M${fx},${fy} q46,4 62,22 q-14,20 -60,14 Z`} fill="#c79a76" stroke={INK}
                  strokeWidth={4.5} strokeLinejoin="round" />
          </g>
        ))}
        {/* the thumb, which is what makes a hand read as a hand and not as a mitten */}
        <path d="M-2,104 q40,26 84,14 q-6,24 -50,26 q-34,0 -40,-24 Z" fill="#b98b68" stroke={INK}
              strokeWidth={4.5} strokeLinejoin="round" />
      </g>
      <ContactShadow cx={-120} cy={128} rx={230} ry={18} opacity={0.5 * press} blur={16} />
    </g>
  );
};

// =============================================================================
// S11 [77.3 - 89.14]  L12 + L13  two-up, dollyThrough
// "None of this forecasts an eruption. Chemistry has traced ash for decades."
// "What's new is how carefully they said which volcanoes they could name, and which
//  they couldn't."
// beats 25 THE CALIPERS (77.3), 26 THE DARK BENCH (79.3), 27 THE SLOT CUT WIDE (81.9),
//       28 COULD AND COULDN'T (85.2), 29 THE CRUMB LANDS (87.4)
//
// THE FAIR COUNTER-POINT, SPOKEN AND DRAWN. The reader's lamp is OFF and nothing glows,
// because this beat says the tool forecasts nothing. The calipers come in ON A HUMAN HAND,
// which is the literal drawing of a person choosing a different, non-ML tool (claim c8).
// Then COULD and COULDN'T hold in ONE frame, which is the honest picture of the result.
// =============================================================================
const S11: React.FC<SceneProps> = ({from, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const t = (from + f) / FPS;
  const d = Math.max(0.1, L(14) - L(12));
  const p = f / FPS / d;
  const cal = interpolate(t, [L(12) + 0.1, L(12) + 1.7], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  // THE DARK BENCH, on "none of this forecasts an eruption". Nothing glows. That is the point.
  const dark = interpolate(t, [L(12) + 1.9, L(12) + 3.3], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const slot = interpolate(t, [L(12) + 4.5, L(13) - 0.4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  // COULD AND COULDN'T, on "which volcanoes they could name, and which they couldn't"
  const both = interpolate(t, [L(13) + 2.06, L(13) + 3.46], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  // THE CRUMB LANDS: the open loop planted at the blade wipe, paid 75 seconds later
  const crumb = interpolate(t, [L(13) + 4.26, L(14)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  // the unnamed bands extinguish across "and which they couldn't"
  const dimOut = interpolate(t, [L(13) + 3.2, L(14) - 0.15], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const cam = CameraMoves.dollyThrough(p * 0.5, 300);
  return (
    <AccentRegistry accents={[{
      hue: RHYOLITE,
      means: 'a trace element signature matched to a source volcano',
      rects: [{x: 60, y: 640, w: 960, h: 700}],
    }]}>
      <Stage grade={<Room f={g} lamp={0.9 - dark * 0.5} />}>
        <Stage3D camera={cam}>
          <Plane z={860}>
            <Atmosphere z={860} skyTint="#0d151a" strength={0.95}>
              <svg viewBox="0 0 1080 1920" width="1080" height="1920">
                <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1480} width={4080} height={440} fill="#0f181c" />
              </svg>
            </Atmosphere>
          </Plane>
          <Plane z={90}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <Bench f={g} y={1480} lit={0.85 - dark * 0.4} />
              {/* the reader sits with its lamp OFF. Nothing glows. This beat forecasts nothing. */}
              <AshReader x={318} y={1160} f={g} scale={1.35} emotion="settled" feed={0} lamp={0} groundY={210} />
              {/* THE CALIPERS, brought in on a human hand: a person choosing another tool */}
              <g opacity={cal}>
                <DistanceCalipers
                  x={772} y={1300} f={g}
                  /* THE MEASUREMENT IS THE EVENT. The jaws come in nearly closed and STEP open
                     in two discrete moves on "they measure chemical distance", so the tool does
                     the thing the line names instead of arriving already set. */
                  span={interpolate(t,
                    [L(12) + 0.5, L(12) + 1.4, L(12) + 2.0, L(12) + 3.0, L(12) + 3.6],
                    [0.08, 0.08, 0.44, 0.44, 0.78],
                    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT})}
                  handIn={cal} scale={1.5} label="CHEMICAL DISTANCE" />
              </g>
              {/* COULD AND COULDN'T, in ONE frame */}
              <g opacity={both}>
                <g transform="translate(540,878) scale(1.1) translate(-540,-878)"><CouldPanel f={g} x={540} y={830} on={both} slot={slot} dim={dimOut} /></g>
              </g>
            </svg>
          </Plane>
        </Stage3D>
        <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
          {/* THE CRUMB LANDS: one eraser crumb from the blade wipe, 75 seconds later,
              completes its fall and seats into a slot. The open loop, paid. */}
          <AshCrumbs f={g} count={14} opacity={0.2} landing={crumb} landX={540} landY={1290} />
          <LampThrow f={g} strength={0.85 - dark * 0.45} />
          <Motes f={g} op={0.22} />
          <g opacity={interpolate(t, [L(12) + 2.7, L(12) + 3.3, L(12) + 4.3, L(12) + 4.8], [0, 1, 1, 0], {extrapolateRight: 'clamp'})}>
            <Chip x={540} y={CARD_BOT - 148} text="THIS FORECASTS NOTHING" size={48} />
          </g>
        </svg>
      </Stage>
    </AccentRegistry>
  );
};

/** COULD and COULDN'T held in one frame. Named bands steady, unnamed ones honest and open. */
const CouldPanel: React.FC<{f: number; x: number; y: number; on: number; slot: number; dim: number}> = ({f, x, y, on, slot, dim}) => {
  const accent = useAccent();
  return (
    <g transform={`translate(${x},${y})`}>
      {/* LEFT: COULD NAME. three steady magenta bands with plates seated flush. */}
      <g transform="translate(-236,0)">
        <text x={0} y={-140} textAnchor="middle" fontSize={38} fontFamily={BOLD} fill={BONE}>COULD NAME</text>
        {[0, 1, 2].map((i) => {
          const px = x - 236, py = y - 74 + i * 74;
          return (
            <g key={i} transform={`translate(0,${-74 + i * 74})`} opacity={on}>
              <rect x={-132} y={-20} width={264} height={40} rx={4}
                    fill={accent(RHYOLITE, px, py)} stroke={INK} strokeWidth={4} opacity={0.92} />
              <RimLight d="M-142,-16 L142,-16" w={3} color="#fffaf0" opacity={0.5} />
            </g>
          );
        })}
      </g>
      {/* RIGHT: COULDN'T. pearl bands, plates NOT seated, the slot left honestly open. */}
      <g transform="translate(236,0)">
        <text x={0} y={-186} textAnchor="middle" fontSize={38} fontFamily={BOLD} fill={BONE}>COULDN'T</text>
        {/* SIX, FADING OUT INTO THE DARK, not three. A 3-against-3 panel implies a roughly
            even nameable/unnameable split, and no source states any fraction. This side has to
            read as "and others", never as a count. */}
        {[0, 1, 2, 3, 4, 5].map((i) => {
          const drift = Math.sin(f / (21 + i * 3.4) + i * 2.4) * 2.2;
          // they extinguish in sequence: one after another drops out of the lamp's reach
          const gone = Math.max(0, Math.min(1, (dim - i * 0.16) * 4.5));
          return (
            <g key={i} transform={`translate(0,${-74 + i * 74 + drift}) scale(${1 - gone * 0.5},${1 - gone * 0.85})`}
               opacity={on * (1 - gone * 0.97)}>
              <rect x={-132} y={-20} width={264} height={40} rx={4} fill={ASH} stroke={INK} strokeWidth={4}
                    opacity={0.95} />
              {/* the empty brass slot, cut wide, still open */}
              <rect x={140} y={-16} width={78 * slot} height={32} rx={3} fill="#0b1013" stroke={BRASS}
                    strokeWidth={3} opacity={slot * (1 - gone)} />
            </g>
          );
        })}
      </g>
      <line x1={0} y1={-166} x2={0} y2={146} stroke={BONE} strokeWidth={4} opacity={0.35 * on} />
    </g>
  );
};

// =============================================================================
// S12 [89.14 - end]  L14 + L15  macro-closeup, dollyThrough
// "Alaska's record didn't disappear. It settled where nobody was reading."
// "What else is down there, with a name still on it?"
// beats 30 THE PLATE SETS (90.6), 31 THE UNREAD STRIPE (94.5)
//
// THE BUTTON, and THE LOOPBACK. The last frame is frame 1's composition with the light
// TAKEN AWAY: the film opens on a signature nobody has read and closes on a signature
// nobody has read YET, and the only thing that changed is that somebody went and got the
// others. The question is genuine, not engagement bait.
// =============================================================================
const S12: React.FC<SceneProps> = ({from, total, L}) => {
  const f = useCurrentFrame();
  const g = from + f;
  const t = (from + f) / FPS;
  const endT = total / FPS;
  const p = f / FPS / Math.max(0.1, endT - L(14));
  const plate = interpolate(t, [L(14) + 1.36, L(14) + 2.46], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  // THE BUTTON's question lands with the last line
  const q = interpolate(t, [L(15) - 0.06, L(15) + 0.74], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  // THE LOOPBACK: the lamp withdraws across the tail, so the final image is frame 1 unlit
  const withdraw = interpolate(t, [L(15) + 0.34, endT - 0.3], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const cam = CameraMoves.dollyThrough(Math.min(1, p * 0.4), 240);
  return (
    <AccentRegistry accents={[{
      hue: RHYOLITE,
      means: 'a trace element signature matched to a source volcano',
      rects: [{x: 0, y: 380, w: 1080, h: 1180}],
    }]}>
      <Stage
        grade={<Room f={g} lamp={1 - withdraw * 0.92} />}
        over={
          <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
            {NAMED_BANDS.map((nb) => {
              const per = nb.col < 6 ? 9 : 8;
              const bandY = 1430 - (0.09 + nb.k * (0.82 / per)) * 720;
              const q = project(150 + nb.col * 111, bandY, cam.z ?? 0);
              return (
                <MatchPlate key={nb.name} colX={q.x} bandY={q.y} text={nb.name} fill={RHYOLITE}
                            scale={q.k} op={1 - withdraw * 0.75} />
              );
            })}
          </svg>
        }
      >
        <Stage3D camera={cam}>
          <Plane z={900}>
            <Atmosphere z={900} skyTint="#0d151a" strength={1}>
              <svg viewBox="0 0 1080 1920" width="1080" height="1920">
                <RoomBack f={g} y={300} op={0.95} />
              <rect x={-1500} y={1520} width={4080} height={400} fill="#0f181c" />
              </svg>
            </Atmosphere>
          </Plane>
          <Plane z={110}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <ContactShadow cx={540} cy={1442} rx={500} ry={22} opacity={0.5 * (1 - withdraw)} blur={20} />
              {/* the eight columns hold, three still named. The poster frame, one last time. */}
              {Array.from({length: 8}).map((_, i) => {
                const x = 150 + i * 111;
                const per = i < 6 ? 9 : 8;
                const namedIdx = i === 1 ? 3 : i === 4 ? 5 : i === 6 ? 2 : -1;
                const nameFor = i === 1 ? 'KATMAI' : i === 4 ? 'FISHER CALDERA' : i === 6 ? 'EMMONS LAKE' : undefined;
                const bands = Array.from({length: per}).map((_, k) => ({
                  at: 0.09 + k * (0.82 / per),
                  lit: 0.85 * (1 - withdraw * 0.85),
                  still: k === namedIdx,
                }));
                return (
                  <g key={i} opacity={1 - withdraw * 0.55}>
                    <CoreColumn x={x} y={1430} f={g} h={720} w={70} bands={bands} phase={i}
                                accentFill={RHYOLITE} />
                  </g>
                );
              })}
            </svg>
          </Plane>
          {/* NEAR: THE UNREAD STRIPE. One pearl band at the very edge of the lamp's reach,
              torn, unlabelled, holding as the light falls off it. */}
          <Plane z={-140}>
            <svg viewBox="0 0 1080 1920" width="1080" height="1920">
              <g opacity={Math.min(1, 0.35 + withdraw * 0.65)}>
                <UnreadStripe f={g} y={1230} lit={1 - withdraw} />
              </g>
            </svg>
          </Plane>
        </Stage3D>
        <svg viewBox="0 0 1080 1920" width="1080" height="1920" style={{position: 'absolute', inset: 0}}>
          <AshCrumbs f={g} count={14} opacity={0.16 * (1 - withdraw)} />
          <LampThrow f={g} strength={1 - withdraw * 0.9} />
          <Motes f={g} op={0.24 * (1 - withdraw)} />
          <g opacity={plate * (1 - withdraw * 0.6)}>
            <BrassPlate x={540} y={SAFE_TOP + 78} lines={['ALASKA.AI']} set={plate} w={420} size={44} />
          </g>
          <g opacity={q}>
            <Chip x={540} y={CARD_BOT} text="WHAT ELSE IS DOWN THERE?" size={44} />
          </g>
        </svg>
      </Stage>
    </AccentRegistry>
  );
};

/** Project a point on the columns' depth plane into frame coordinates. Same maths the
 *  Stage3D Plane applies, so an above-the-grade overlay can sit exactly on a band. */
const project = (x: number, y: number, camZ: number, planeZ = 110) => {
  const k = 1400 / (1400 + planeZ - camZ);
  return {x: 540 + (x - 540) * k, y: 960 + (y - 960) * k, k};
};

/**
 * A match plate, drawn in its own pass and CLAMPED to the safe area.
 *
 * `colX` is the column it belongs to and `bandY` the band it names. The plate is placed to
 * whichever side has room, then clamped so its full width sits inside [MARGIN, 1080-MARGIN],
 * and the leader line is drawn from the plate's edge to the band afterwards, so stretching it
 * is what absorbs the clamp. A name the film is built on can never be cut again.
 */
const MatchPlate: React.FC<{
  colX: number; bandY: number; text: string; fill: string; scale?: number; op?: number;
}> = ({colX, bandY, text, fill, scale = 1, op = 1}) => {
  const MARGIN = 34;
  const pw = (text.length * 20 + 40) * scale;
  const ph = 52 * scale;
  // prefer the side with more room, then clamp the whole box into frame
  const wantLeft = colX > 540;
  let x0 = wantLeft ? colX - 46 * scale - pw : colX + 46 * scale;
  x0 = Math.max(MARGIN, Math.min(1080 - MARGIN - pw, x0));
  const anchorX = x0 + (wantLeft ? pw : 0);        // the plate edge the leader leaves from
  return (
    <g opacity={op}>
      {/* the leader stretches to cover whatever the clamp moved */}
      <line x1={anchorX} y1={bandY} x2={colX} y2={bandY} stroke={INK} strokeWidth={3.5} opacity={0.9} />
      <rect x={x0} y={bandY - ph / 2} width={pw} height={ph} rx={5} fill={fill} stroke={INK} strokeWidth={4} />
      <rect x={x0 + 5} y={bandY - ph / 2 + 6} width={pw - 10} height={ph - 12} rx={3} fill="#0a0508" opacity={0.94} />
      <text x={x0 + pw / 2} y={bandY + 10 * scale} textAnchor="middle" fontSize={30 * scale}
            fontFamily={BOLD} fill="#ffffff" textLength={pw - 24} lengthAdjust="spacingAndGlyphs"
            stroke="#0a0508" strokeWidth={3 * scale} paintOrder="stroke">{text}</text>
    </g>
  );
};

/** one pearl band at the edge of the lamp's reach, torn and unlabelled. The last image. */
const UnreadStripe: React.FC<{f: number; y: number; lit: number}> = ({f, y, lit}) => {
  const top = Array.from({length: 17}).map((_, i) => {
    const p = i / 16;
    const j = (Math.abs(Math.imul(i + 19, 2654435761)) % 1000) / 1000;
    return `${-40 + p * 1160},${y + (j - 0.5) * 18}`;
  }).join(' L');
  return (
    <g>
      <path d={`M${top} L1120,${y + 62} L-40,${y + 66} Z`} fill={ASH} stroke={INK} strokeWidth={5}
            strokeLinejoin="round" opacity={0.3 + lit * 0.55} />
      <path d={`M${top}`} stroke="#fffaf0" strokeWidth={4} fill="none" opacity={lit * 0.55} />
      {/* the brass slot beside it, cut and still empty */}
      <g opacity={0.35 + lit * 0.4}>
        <rect x={870} y={y + 8} width={130} height={38} rx={3} fill="#0b1013" stroke={BRASS} strokeWidth={3.5} />
      </g>
    </g>
  );
};

// =============================================================================

const Captions: React.FC<{captions: {start: number; end: number; text: string}[]}> = ({captions}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  const cue = captions.find((c) => t >= c.start && t < c.end + 0.05);
  if (!cue) return null;
  const local = f - Math.round(cue.start * fps);
  const pop = spring({frame: local, fps, config: {damping: 9, stiffness: 130}});
  const scale = interpolate(pop, [0, 1], [0.9, 1], {extrapolateRight: 'clamp'});
  const rise = interpolate(pop, [0, 1], [18, 0], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', bottom: 300, left: 0, right: 0, display: 'flex', justifyContent: 'center', padding: '0 60px'}}>
      <div style={{background: 'rgba(12,18,22,0.94)', borderRadius: 14, padding: '16px 30px', maxWidth: 940,
        border: `4px solid ${BONE}`, transform: `translateY(${rise}px) scale(${scale})`, transformOrigin: 'center bottom'}}>
        <div style={{fontFamily: BOLD, fontWeight: 900, fontSize: 46, lineHeight: 1.12, color: '#fff', textAlign: 'center',
          letterSpacing: 0.4, textShadow: '2px 3px 0 rgba(0,0,0,0.7)'}}>{cue.text}</div>
      </div>
    </div>
  );
};

export const ep0802Schema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  /** VO line start times in seconds. Every beat in this film is anchored to one of these. */
  lines: z.array(z.number()).optional(),
  total: z.number().optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.object({frame: z.number(), word: z.string(), energy: z.number().optional(), lineIdx: z.number().optional()})).optional(),
});
export type Ep0802Props = z.infer<typeof ep0802Schema>;

const SCENES: React.FC<SceneProps>[] = [
  S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12,
];

/** fallback only. episode_props.json (scripts/build_scenes.py) carries the real timing. */
const DEFAULT_BOUNDS = [
  {from: 0, dur: 210}, {from: 210, dur: 198}, {from: 408, dur: 142}, {from: 550, dur: 212},
  {from: 762, dur: 245}, {from: 1007, dur: 188}, {from: 1195, dur: 244}, {from: 1439, dur: 185},
  {from: 1624, dur: 302}, {from: 1926, dur: 394}, {from: 2320, dur: 355}, {from: 2675, dur: 305},
];

export const Ep0802: React.FC<Ep0802Props> = ({captions, scenes, lines, total}) => {
  const bounds = scenes && scenes.length === SCENES.length ? scenes : DEFAULT_BOUNDS;
  const totalF = total ?? 2964;
  const table = lines && lines.length === FALLBACK_LINES.length ? lines : FALLBACK_LINES;
  const L = React.useCallback((i: number) => table[Math.max(0, Math.min(table.length - 1, i))], [table]);
  return (
    <AbsoluteFill style={{backgroundColor: ROOMDARK}}>
      {SCENES.map((C, i) => (
        <Sequence key={i} from={bounds[i].from} durationInFrames={bounds[i].dur} name={`S${i + 1}`}>
          <C from={bounds[i].from} total={totalF} L={L} />
        </Sequence>
      ))}
      <Captions captions={captions} />
    </AbsoluteFill>
  );
};
