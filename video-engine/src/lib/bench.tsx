import React from 'react';
import {INK, tones, FormGradient, RimLight, ContactShadow} from './lighting';
import {vitals} from './motion';

// =============================================================================
// THE BENCH FAMILY — net-new 2026-08-01, "The Copy In The Mud"
// -----------------------------------------------------------------------------
// THE MANIFEST GAP THIS FILLS (checked against ASSET_MANIFEST.md in full before
// building, per the library mandate §4.3a). The shelf already had an orbital eye
// (SatelliteEye), a seafloor ear (ListeningMooring), a ground ear (SeismicStation),
// two aerial machines (Vale, Petrel), a swimmer (IceGlider), records machinery
// (RecordsMachine, ThreePipeCutaway) and the civics rules kit (Gate, ThresholdGate).
// It had NOTHING that reads a SAMPLE, and no vocabulary at all for bench science or
// material evidence. Every instrument on the shelf observes a WORLD. This story is
// about a piece of the world brought INDOORS and put under a lamp, which is a
// different verb and needed different hardware.
//
// SHAPE LANGUAGE, and it is the whole art-direction plan in one rule: TORN AGAINST
// TURNED. Everything found (mud, ash, ice, land) is drawn with torn irregular
// silhouettes and no two parallel edges. Everything built (this file) is TURNED,
// machined, radially symmetric, with visible fabrication marks. In silhouette alone
// the viewer can tell which half of the film is evidence and which half is instrument.
//
// THE EMOTIONAL TELL IS THE CARD, NOT A FACE. The 07-25 SeismicStation, the 07-26
// TaperedCone and the 07-30 IceGlider all taught the same lesson three times: ONE
// channel is never enough to read at frame size. So AshReader carries its state on
// three channels at once, and the loudest of them is a physical object it prints.
// The number of names on the shortlist card sets the card's WIDTH, so ambiguity is a
// SIZE ON SCREEN rather than a label a viewer has to read. That is the entire reason
// this asset exists rather than a HUD chip: a chip would report the ambiguity, the
// card IS the ambiguity.
// =============================================================================

const uid = (s: string) => 'bn' + Math.abs([...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 11)).toString(36);

/** LICENSED ACCENT. Rhyolite magenta means A CHEMICAL MATCH and nothing else in this film.
 *  Enforced at paint time by the DayGrade AccentRegistry (lighting.tsx, this run's craft
 *  advance): useAccent() throws if it is painted outside a licensed rect. */
export const RHYOLITE = '#d94f8a';
const BRASS = '#c9a24a';
const ENAMEL = '#31424a';
const BONE = '#e8e2d2';
const GLASS = '#8fb3bd';

// -----------------------------------------------------------------------------
// ShortlistCard — the printed answer, and the film's whole thesis as an object.
// A card with ONE name is narrow and calm. A card with THREE is WIDE, and the extra
// width is the honest report of ambiguity. Deliberately built on paper.tsx's numeric
// shadow contract (2px edge, drop shadow 4 down / 2 right at 22 percent) so it reads
// as real stock under a hard lamp rather than as a floating rectangle.
// -----------------------------------------------------------------------------
export const ShortlistCard: React.FC<{
  x: number; y: number; f: number; scale?: number;
  names: string[];                 // 1..3 names. Width follows length. THIS IS THE TELL.
  out?: number;                    // 0..1 how far the card has emerged from the slot
  matched?: boolean;               // true = the accent hue is licensed on this card
  accentFill?: string;             // pass the resolved accent from useAccent(); never hardcode
  rot?: number;
}> = ({x, y, f, scale = 1, names, out = 1, matched = false, accentFill, rot = 0}) => {
  const id = uid(`card${x}${y}${names.join()}`);
  const stock = tones('#f2ece0');
  const n = Math.max(1, Math.min(3, names.length));

  // TEXT FITTING, and it is not optional (Gate 0D, 2026-08-01, called this a hard blocker on
  // the film's own thesis object). Pass 1 used a fixed 76px bay and a fixed fontSize 17. At
  // that size "FISHER CALDERA" measures about 148px and "EMMONS LAKE" about 115px in Arial
  // Black, so on the three-name card the outer bay's text ran off the stock entirely. The card
  // is the whole performance of this asset; a card whose names overflow is not a subtler bug
  // than a broken render, it is the same bug.
  //
  // Arial Black advances at roughly 0.62em for mixed uppercase, which is close enough to size a
  // bay from and deliberately errs wide. The bay is derived from the LONGEST name, the font
  // shrinks only if that would push the card past MAXW, and the card's width is then derived
  // from the bay rather than assumed. So W still grows with the number of names (the tell) but
  // now it grows to fit real words.
  const ADV = 0.62, PAD = 18, GAP = 16, MAXW = 430, FS_MAX = 19, FS_MIN = 13;
  const longest = Math.max(...names.slice(0, n).map((s) => s.length), 1);
  let fs = FS_MAX;
  let bayW = Math.max(78, longest * fs * ADV + 16);
  let W = PAD * 2 + n * bayW + (n - 1) * GAP;
  if (W > MAXW) {                                   // shrink to fit, never overflow
    const room = (MAXW - PAD * 2 - (n - 1) * GAP) / n - 16;
    fs = Math.max(FS_MIN, room / (longest * ADV));
    bayW = Math.max(78, longest * fs * ADV + 16);
    W = PAD * 2 + n * bayW + (n - 1) * GAP;
  }
  const H = 116;
  const o = Math.max(0, Math.min(1, out));
  const slide = (1 - o) * -H * 0.9;                 // rises out of the slot
  const flutter = Math.sin(f / 13 + x) * 0.8 * o;   // paper is never dead still
  return (
    <g transform={`translate(${x},${y + slide}) rotate(${rot + flutter}) scale(${scale})`} opacity={Math.min(1, o * 1.6)}>
      <FormGradient id={id} t={stock} softness={0.75} />
      {/* the drop shadow that gives paper body under flat hard light */}
      <rect x={-W / 2 + 2} y={-H / 2 + 4} width={W} height={H} rx={5} fill="#000" opacity={0.22} />
      <rect x={-W / 2} y={-H / 2} width={W} height={H} rx={5} fill={`url(#${id})`} stroke={INK} strokeWidth={4} />
      {/* printed-stock tooth so it is never a flat fill */}
      {Array.from({length: 7}).map((_, i) => (
        <line key={i} x1={-W / 2 + 10} y1={-H / 2 + 20 + i * 12} x2={W / 2 - 10} y2={-H / 2 + 20 + i * 12}
              stroke={INK} strokeWidth={1} opacity={0.055} />
      ))}
      {/* the header rule, and a count of how many names this answer needed */}
      <line x1={-W / 2 + 12} y1={-H / 2 + 26} x2={W / 2 - 12} y2={-H / 2 + 26} stroke={INK} strokeWidth={2.5} opacity={0.5} />
      {names.slice(0, n).map((nm, i) => (
        <g key={nm} transform={`translate(${-W / 2 + PAD + i * (bayW + GAP)},0)`}>
          {/* each name gets its own bay, sized from the LONGEST name so nothing overflows */}
          <rect x={0} y={-8} width={bayW} height={44} rx={3}
                fill={matched && accentFill ? accentFill : '#cfd4cc'} opacity={matched ? 0.9 : 0.5}
                stroke={INK} strokeWidth={2.5} />
          <text x={bayW / 2} y={22} textAnchor="middle" fontSize={fs} fontFamily="Arial Black, Arial, sans-serif"
                fill={INK} letterSpacing={0.4}>{nm}</text>
        </g>
      ))}
      <RimLight d={`M${-W / 2 + 4},${-H / 2 + 3} L${W / 2 - 4},${-H / 2 + 3}`} w={3} color="#fffaf0" opacity={0.5} />
    </g>
  );
};

// -----------------------------------------------------------------------------
// AshReader — THE RUN'S HERO. A brass and enamel bench instrument that reads one
// grain of ash and prints a shortlist.
//
// Three simultaneous state channels, because one was never enough (see the header):
//   1. THE CARD (loudest)  — how many names the answer needed
//   2. THE LAMP            — lights ONLY when a match is asserted, same discipline as
//                            SeismicStation's lamp, so a lit lamp always means a real
//                            positive rather than "the machine is on"
//   3. THE THROAT + BROW   — the lens throat telescopes on `straining`, and a brow bar
//                            over the two small eyes carries state even when the lamp is dark
//
// The eyes are deliberately SMALL and subordinate. This asset's job is to make an
// OUTPUT legible, not to emote. Cuteness here would undercut a film about restraint.
// -----------------------------------------------------------------------------
export const AshReader: React.FC<{
  x: number; y: number; f: number; scale?: number;
  emotion?: 'reading' | 'settled' | 'straining';
  feed?: number;                   // 0..1 a sample travels the stage left to right
  lamp?: number;                   // 0..1 lights ONLY on an asserted match
  accent?: number;                 // 0..1 VO-emphasis reactivity
  phase?: number;                  // decorrelates the idle between instances
  groundY?: number;
  lampFill?: string;               // resolved accent for the lamp, from useAccent()
}> = ({
  x, y, f, scale = 1, emotion = 'reading', feed = 0, lamp = 0, accent = 0,
  phase = 0, groundY = 96, lampFill,
}) => {
  const id = uid(`ash${x}${y}`);
  const body = tones(ENAMEL);
  const brass = tones(BRASS);
  const v = vitals(f, phase, emotion === 'settled' ? 0.45 : 1);
  const strain = emotion === 'straining' ? 1 : 0;
  const lit = Math.max(0, Math.min(1, lamp));
  const fed = Math.max(0, Math.min(1, feed));
  const kick = accent * 4;                                   // the body flinches on emphasis
  const throat = 1 + strain * 0.26 + Math.sin(f / 23) * 0.02; // telescopes out past comfort
  const brow = strain ? -7 : emotion === 'settled' ? 2 : -2;
  const blink = (Math.sin(f / 31 + phase) > 0.955) ? 0.12 : 1;
  return (
    <g transform={`translate(${x},${y + v.bob - kick}) scale(${scale}) rotate(${v.tilt * 0.5})`}>
      <FormGradient id={id} t={body} softness={0.62} />
      <FormGradient id={`${id}b`} t={brass} softness={0.58} />
      <ContactShadow cx={0} cy={groundY} rx={150} ry={22} opacity={0.5} blur={16} />

      {/* ---- THE PLINTH: heavy, planted, machined. Four feet, not a floating box. ---- */}
      {[-116, 108].map((fx) => (
        <rect key={fx} x={fx} y={groundY - 26} width={22} height={26} rx={3} fill={body.shade} stroke={INK} strokeWidth={4} />
      ))}
      <rect x={-134} y={groundY - 46} width={268} height={26} rx={5} fill={`url(#${id})`} stroke={INK} strokeWidth={5} />

      {/* ---- THE SAMPLE STAGE: a machined channel a grain travels along ---- */}
      <rect x={-134} y={groundY - 92} width={268} height={48} rx={6} fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
      <rect x={-120} y={groundY - 82} width={240} height={20} rx={4} fill={body.shade} stroke={INK} strokeWidth={3} />
      {/* stage graduations, because a machined part shows its fabrication */}
      {Array.from({length: 13}).map((_, i) => (
        <line key={i} x1={-116 + i * 19} y1={groundY - 82} x2={-116 + i * 19} y2={groundY - 74}
              stroke={INK} strokeWidth={1.8} opacity={0.5} />
      ))}
      {/* the grain of ash itself, travelling the stage. Torn silhouette on purpose. */}
      {fed > 0.01 && (
        <g transform={`translate(${-112 + fed * 224},${groundY - 72})`}>
          <path d="M-9,4 L-4,-8 L3,-9 L9,-1 L6,7 L-3,9 Z" fill="#cfd4cc" stroke={INK} strokeWidth={2.5} />
          <path d="M-4,-8 L3,-9 L4,-3 Z" fill="#f2f4f1" opacity={0.85} />
        </g>
      )}

      {/* ---- THE THROAT: the lens column, telescoping ---- */}
      <g transform={`translate(0,${groundY - 92}) scale(1,${throat})`}>
        <rect x={-30} y={-96} width={60} height={96} rx={4} fill={`url(#${id}b)`} stroke={INK} strokeWidth={5} />
        {/* barrel rings, the turned-metal tell */}
        {[-22, -44, -66].map((ry) => (
          <line key={ry} x1={-30} y1={ry} x2={30} y2={ry} stroke={INK} strokeWidth={2.6} opacity={0.65} />
        ))}
        <ellipse cx={0} cy={-96} rx={34} ry={11} fill={brass.key} stroke={INK} strokeWidth={4.5} />
        <ellipse cx={0} cy={-95} rx={20} ry={6} fill={GLASS} opacity={0.9} stroke={INK} strokeWidth={2.5} />
      </g>

      {/* ---- THE HEAD: enamel housing, small subordinate eyes, a brow that carries state ---- */}
      <g transform={`translate(0,${groundY - 214})`}>
        <rect x={-96} y={-64} width={192} height={92} rx={10} fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
        {/* vent slots */}
        {[-70, -56, -42].map((vx) => (
          <line key={vx} x1={vx} y1={-50} x2={vx} y2={-20} stroke={INK} strokeWidth={3} opacity={0.55} />
        ))}
        {/* screws, four, at real corners */}
        {[[-84, -52], [84, -52], [-84, 16], [84, 16]].map(([sx, sy], i) => (
          <g key={i}>
            <circle cx={sx} cy={sy} r={5} fill={brass.base} stroke={INK} strokeWidth={2.5} />
            <line x1={sx - 3} y1={sy} x2={sx + 3} y2={sy} stroke={INK} strokeWidth={1.8} />
          </g>
        ))}
        {/* the brow bar: angle carries state even when the lamp is dark */}
        <rect x={-46} y={-16 + brow} width={92} height={9} rx={4} fill={INK} opacity={0.85} />
        {/* two small eyes, subordinate by design */}
        {[-24, 24].map((ex) => (
          <g key={ex}>
            <circle cx={ex} cy={6} r={11} fill={BONE} stroke={INK} strokeWidth={3.2} />
            <circle cx={ex} cy={6} r={5 * blink} fill={INK} />
          </g>
        ))}
        <RimLight d="M-92,-60 L92,-60" w={4} color="#fffaf0" opacity={0.5} />
      </g>

      {/* ---- THE LAMP: lights ONLY on an asserted match ---- */}
      {lit > 0.02 && (
        <g transform={`translate(0,${groundY - 250})`} style={{mixBlendMode: 'screen'}} opacity={lit}>
          <circle cx={0} cy={0} r={54} fill={lampFill || '#ffffff'} opacity={0.22} />
          <circle cx={0} cy={0} r={20} fill={lampFill || '#ffffff'} opacity={0.75} />
        </g>
      )}
      <circle cx={0} cy={groundY - 250} r={13} fill={lit > 0.02 ? (lampFill || BONE) : '#2a3238'}
              stroke={INK} strokeWidth={4} />

      {/* ---- THE CARD SLOT: where the answer comes out ---- */}
      <rect x={-56} y={groundY - 122} width={112} height={12} rx={3} fill="#0b1013" stroke={INK} strokeWidth={3.5} />
      {/* the wear-polished edge where a hand rests, the detail that says somebody uses this */}
      <path d={`M-134,${groundY - 46} L134,${groundY - 46}`} stroke="#e6d9b4" strokeWidth={3} opacity={0.35} />
    </g>
  );
};

// -----------------------------------------------------------------------------
// DistanceCalipers — the SECOND INSTRUMENT, and the film's Act 3 in one object.
// The narration says that when the model isn't the right tool, they don't force it,
// they measure chemical distance. Nothing on the shelf could stage a deliberate TOOL
// CHANGE. A pair of brass calipers spanning two points is the literal drawing of a
// distance metric, and `handIn` brings it in on a human hand, which is the literal
// drawing of a person choosing. The two halves of that sentence, drawn.
// -----------------------------------------------------------------------------
export const DistanceCalipers: React.FC<{
  x: number; y: number; f: number; scale?: number;
  span?: number;                   // 0..1 how far the jaws open
  tilt?: number;
  handIn?: number;                 // 0..1 the hand carrying it into frame
  label?: string;
}> = ({x, y, f, scale = 1, span = 0.5, tilt = 0, handIn = 1, label}) => {
  const id = uid(`cal${x}${y}`);
  const brass = tones(BRASS);
  const s = Math.max(0, Math.min(1, span));
  const jaw = 42 + s * 128;                          // the measured distance, visibly
  const h = Math.max(0, Math.min(1, handIn));
  const enter = (1 - h) * 220;                       // slides in from screen right
  const settle = Math.sin(f / 17) * 0.6 * h;         // a held tool is never dead still
  return (
    <g transform={`translate(${x + enter},${y}) rotate(${tilt + settle}) scale(${scale})`} opacity={Math.min(1, h * 1.4)}>
      <FormGradient id={id} t={brass} softness={0.55} />
      {/* the beam */}
      <rect x={-14} y={-150} width={28} height={150} rx={5} fill={`url(#${id})`} stroke={INK} strokeWidth={4.5} />
      {/* graduations up the beam, the turned-instrument tell */}
      {Array.from({length: 9}).map((_, i) => (
        <line key={i} x1={-14} y1={-138 + i * 15} x2={i % 3 === 0 ? 8 : 0} y2={-138 + i * 15}
              stroke={INK} strokeWidth={i % 3 === 0 ? 2.6 : 1.6} opacity={0.65} />
      ))}
      {/* the pivot */}
      <circle cx={0} cy={-6} r={13} fill={brass.key} stroke={INK} strokeWidth={4} />
      <circle cx={0} cy={-6} r={4} fill={INK} />
      {/* the two jaws, opening by `span`. THIS is the measurement. */}
      {[-1, 1].map((sgn) => (
        <g key={sgn}>
          <path d={`M0,-6 L${sgn * jaw},74 L${sgn * (jaw - 13)},84 L0,4 Z`}
                fill={`url(#${id})`} stroke={INK} strokeWidth={4.5} strokeLinejoin="round" />
          <path d={`M${sgn * jaw},74 L${sgn * (jaw - 5)},92`} stroke={INK} strokeWidth={4} strokeLinecap="round" />
        </g>
      ))}
      {/* the span read out as a bar between the jaw tips, so the DISTANCE is the focal object */}
      <line x1={-jaw + 8} y1={92} x2={jaw - 8} y2={92} stroke={INK} strokeWidth={3} strokeDasharray="9 7" opacity={0.75} />
      {label && (
        <text x={0} y={122} textAnchor="middle" fontSize={22} fontFamily="Arial Black, Arial, sans-serif"
              fill={INK}>{label}</text>
      )}
      <RimLight d="M-11,-146 L-11,-14" w={3} color="#fff3d0" opacity={0.55} />
    </g>
  );
};

// -----------------------------------------------------------------------------
// CoreColumn — one long tube of mud, standing, with its ash bands.
// TORN, not turned: the mud's edges are irregular and the bands have ragged tops,
// because this is the FOUND half of the film's shape grammar. Bands are supplied by
// the caller as fractions down the column so a scene can light them one at a time.
// -----------------------------------------------------------------------------
export const CoreColumn: React.FC<{
  x: number; y: number; f: number; h?: number; w?: number;
  /**
   * at    0..1 down the column
   * lit   0..1 how strongly the lamp has found it
   * named a recurring NAME-CLASS on this band. It is a class, never a specimen count: the
   *       same name recurs at many depths, because c10 says these centers keep producing
   *       nearly invariant magmas. Never stage a countable "N of 37".
   * still PER-BAND MOTION CHANNEL (added 2026-08-01 after Gate 0D). The signature shot needs
   *       three bands DEAD STILL while the rest are quietly restless, and pass 1 applied ONE
   *       sway to the whole group so bands inherited it wholesale and the contrast, which IS
   *       the poster frame's argument, was literally unbuildable.
   * mark  a re-identifiable tell (a double-torn corner plus one conspicuously deep tooth) so
   *       the open-loop band can be recognised 52 seconds and two shots later.
   */
  bands: {at: number; lit?: number; named?: string; still?: boolean; mark?: boolean}[];
  accentFill?: string;                                     // resolved accent, from useAccent()
  phase?: number;
  labelScale?: number;                                     // name plates scale with the pull-back
}> = ({x, y, f, h = 620, w = 74, bands, accentFill, phase = 0, labelScale = 1}) => {
  const id = uid(`core${x}${y}`);
  const mud = tones('#4a4234');
  const sway = Math.sin(f / 61 + phase) * 0.35;
  return (
    <g transform={`translate(${x},${y}) rotate(${sway})`}>
      <FormGradient id={id} t={mud} softness={0.7} />
      {/* the column body, with a TORN left edge so it never reads as a machined tube */}
      <path
        d={`M${-w / 2},0 L${-w / 2 - 3},${-h * 0.28} L${-w / 2 + 2},${-h * 0.55}
            L${-w / 2 - 4},${-h * 0.79} L${-w / 2},${-h} L${w / 2},${-h} L${w / 2},0 Z`}
        fill={`url(#${id})`} stroke={INK} strokeWidth={4.5} strokeLinejoin="round"
      />
      {/* grain speckle so mud is a SUBSTANCE, never a flat fill */}
      {Array.from({length: 26}).map((_, i) => {
        const hh = Math.abs(Math.imul(i + 7, 2654435761)) % 1000 / 1000;
        const ww = Math.abs(Math.imul(i + 31, 40503)) % 1000 / 1000;
        return <circle key={i} cx={-w / 2 + 8 + ww * (w - 16)} cy={-hh * h} r={1.7} fill={INK} opacity={0.16} />;
      })}
      {bands.map((b, i) => {
        const by = -b.at * h;
        const lit = Math.max(0, Math.min(1, b.lit ?? 0));
        const fill = b.named && accentFill ? accentFill : '#cfd4cc';
        // PER-BAND UNREST. A named band holds DEAD STILL (that steadiness is the argument);
        // an unnamed one breathes on its own irrational period so a field of them never
        // re-phases into a visible pulse.
        const restless = b.still || b.named ? 0 : 1;
        const jy = restless * Math.sin(f / (19 + (i % 7) * 2.3) + i * 2.399) * 1.6;
        const jo = restless * Math.sin(f / (23 + (i % 5) * 3.1) + i) * 0.10;
        const corner = b.mark ? 9 : 0;                  // the double-torn corner tell
        return (
          <g key={i} transform={`translate(0,${jy})`}>
            {/* ragged band top: the ash settled, it was not machined in */}
            <path
              d={`M${-w / 2 - corner},${by} L${-w / 2 + w * 0.3},${by - 3} L${-w / 2 + w * 0.62},${by + 2}
                  L${w / 2},${by - 2} L${w / 2},${by + 13} L${-w / 2 - corner * 0.6},${by + 14} Z`}
              fill={fill} stroke={INK} strokeWidth={3} opacity={Math.max(0, 0.45 + lit * 0.55 + jo)}
            />
            {b.mark && (
              /* one conspicuously deep tooth, so this band is re-identifiable across shots */
              <path d={`M${-w / 2 - corner},${by + 3} L${-w / 2 - corner - 11},${by + 7} L${-w / 2 - corner},${by + 11} Z`}
                    fill={fill} stroke={INK} strokeWidth={2.5} opacity={Math.max(0, 0.5 + lit * 0.5)} />
            )}
            {lit > 0.02 && (
              <path d={`M${-w / 2},${by + 1} L${w / 2},${by - 1}`} stroke="#fffaf0" strokeWidth={2.4}
                    opacity={lit * 0.7} />
            )}
            {/* THE NAME PLATE. Gate 0D: the poster frame promises named bands and pass 1 could
                only TINT one, so the frame's whole point had no geometry. A small machined plate
                on a stem, sized by labelScale so it survives the pull-back. */}
            {b.named && (
              <g transform={`translate(${w / 2 + 10},${by + 6}) scale(${labelScale})`}>
                <line x1={0} y1={0} x2={13} y2={0} stroke={INK} strokeWidth={3} />
                <rect x={13} y={-13} width={b.named.length * 8.4 + 16} height={26} rx={3}
                      fill={accentFill || '#cfd4cc'} stroke={INK} strokeWidth={3} />
                <text x={13 + (b.named.length * 8.4 + 16) / 2} y={6} textAnchor="middle" fontSize={15}
                      fontFamily="Arial Black, Arial, sans-serif" fill={INK}>{b.named}</text>
              </g>
            )}
          </g>
        );
      })}
      <RimLight d={`M${w / 2 - 3},${-h + 6} L${w / 2 - 3},-8`} w={3} color="#d8c79a" opacity={0.4} />
    </g>
  );
};

// -----------------------------------------------------------------------------
// AshCrumbs — THE CROSS-SCENE GAG, as one shared deterministic component.
// Gate 0D, correctly: the eraser-crumb callback requires crumbs to curl off the glacier
// blade, drift in the far atmosphere plane of EVERY scene after the wipe, and one to land
// and seat some seventy seconds later. That is a continuity requirement, and a continuity
// requirement re-improvised per scene silently does not happen. So it is ONE component with
// a global-frame phase, mounted in every scene from the wipe onward at the same seed.
//
// `landing` promotes ONE crumb out of the drift and seats it, which is the payoff beat.
// -----------------------------------------------------------------------------
export const AshCrumbs: React.FC<{
  f: number;                      // GLOBAL frame, so the drift is continuous across cuts
  count?: number;
  opacity?: number;               // far-plane crumbs sit low; the payoff crumb comes forward
  landing?: number;               // 0..1 seats crumb 0 into a slot at (landX, landY)
  landX?: number; landY?: number;
  w?: number; h?: number;
}> = ({f, count = 14, opacity = 0.3, landing = 0, landX = 540, landY = 1500, w = 1080, h = 1920}) => {
  const L = Math.max(0, Math.min(1, landing));
  return (
    <g style={{pointerEvents: 'none'}}>
      {Array.from({length: count}).map((_, i) => {
        // deterministic imul hash, never Math.random, so the drift is identical every render
        const hx = Math.abs(Math.imul(i + 13, 2654435761)) % 1000 / 1000;
        const hs = Math.abs(Math.imul(i + 71, 40503)) % 1000 / 1000;
        const speed = 22 + hs * 26;
        const x = hx * w + Math.sin(f / (61 + i * 3.7) + i) * 26;
        const y = ((f * speed) / 30 + hx * h * 1.7) % (h * 1.25) - h * 0.12;
        const rot = (f * (0.5 + hs)) % 360;
        if (i === 0 && L > 0.01) {
          // THE PAYOFF CRUMB: leaves the drift, arcs to the slot, compresses as it seats
          const e = L * L * (3 - 2 * L);                       // smoothstep, never linear
          const px = x + (landX - x) * e;
          const py = y + (landY - y) * e;
          const squash = 1 + 0.45 * Math.max(0, Math.sin(Math.PI * Math.min(1, L * 1.15)));
          return (
            <g key={i} transform={`translate(${px},${py}) rotate(${rot * (1 - e)}) scale(${squash},${2 - squash})`}
               opacity={0.9}>
              <path d="M-7,3 L-3,-6 L3,-7 L7,-1 L4,5 L-2,7 Z" fill="#cfd4cc" stroke={INK} strokeWidth={2} />
            </g>
          );
        }
        return (
          <g key={i} transform={`translate(${x},${y}) rotate(${rot}) scale(0.62)`} opacity={opacity}>
            <path d="M-7,3 L-3,-6 L3,-7 L7,-1 L4,5 L-2,7 Z" fill="#cfd4cc" stroke={INK} strokeWidth={2} />
          </g>
        );
      })}
    </g>
  );
};
