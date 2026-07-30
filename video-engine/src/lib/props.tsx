import React from 'react';
import {INK, ICE, SNOW, RED} from './kit';
import {tones, paleTones, FormGradient, RimLight, ContactShadow, BrushedMetal} from './lighting';

// =============================================================================
// PROPS — the generalized physical-prop kit (asset-library session #2,
// 2026-07-20d). These began as episode-locals (07-18 land giveaway, 07-19
// turbine) with story copy hardcoded; promoted here with every label/line a
// param so any run can cast them. Same conventions as fauna/vehicles: local
// coords, base near y=0, caller passes frame f where the prop animates.
// Text-bearing props take their copy as props — a prop with baked-in story
// text is an episode-local, not a library asset.
// =============================================================================

const BOLD = 'Arial Black, Arial, sans-serif';
const WOOD = '#8a6239';
const WOOD_D = '#5c4326';
const BIRCH = '#efe6d0';
const MOSS = '#6b7a4a';
const CRIMSON = '#c0392b';
const GRAPHITE_D = '#232c34';

// A big loud stat chip: one number/phrase, optional sub line.
// FORM-SHADING IS NOW THE DEFAULT (2026-07-30). It was added 2026-07-21 as an OPT-IN
// `formShaded` flag defaulting to FALSE, which is exactly why "HUD chips render as flat
// fills over the lit world" kept getting re-flagged by the scorer panel on 07-18, 07-26
// AND 07-29: the capability existed, but every new scene that simply called <StatCard/>
// still got the flat chip unless its author remembered a flag. A default-off fix is a
// doctrine reminder wearing a code costume. The default is now SHADED, and a caller that
// genuinely wants the old look must ask for it with `flat`. `formShaded` is retained so
// older explicit callers keep compiling.
export const StatCard: React.FC<{x: number; y: number; big: string; sub?: string; op?: number; scale?: number; color?: string; formShaded?: boolean; flat?: boolean}> = ({x, y, big, sub, op = 1, scale = 1, color = CRIMSON, formShaded, flat = false}) => {
  const shaded = formShaded ?? !flat;
  const cardTones = tones(color);
  const gid = `statcard_${x}_${y}`;
  const h = sub ? 128 : 96;
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`} opacity={op}>
      {shaded && <ContactShadow cx={0} cy={h / 2 + 14} rx={280} ry={20} opacity={0.3} />}
      {shaded && <defs><FormGradient id={gid} t={cardTones} softness={0.8} /></defs>}
      <rect x={-260} y={-64} width={520} height={h} rx={16} fill={shaded ? `url(#${gid})` : color} stroke={INK} strokeWidth={8} />
      {shaded && <RimLight d={`M-260,-56 L-252,${h / 2 - 8}`} w={5} opacity={0.4} />}
      <text x={0} y={sub ? -12 : big.length > 10 ? 10 : 16} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={sub ? 58 : 46} fill={SNOW} letterSpacing={1} stroke={INK} strokeWidth={2.5} paintOrder="stroke">{big}</text>
      {sub && <text x={0} y={38} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={26} fill={SNOW} opacity={0.9}>{sub}</text>}
    </g>
  );
};

// A small identity plate (institution, place, person).
// SHADED BY DEFAULT 2026-07-30, same repeat-offender fix as StatCard above. This prop had
// NO dimensional path at all, so every nameplate in every episode was a flat ICE rectangle
// sitting on top of the lit world. It now carries the same contract as the rest of the kit
// (FormGradient body + ContactShadow + a rim on the light-side edge); pass `flat` to opt out.
export const Nameplate: React.FC<{x: number; y: number; text: string; sub?: string; op?: number; subColor?: string; flat?: boolean}> = ({x, y, text, sub, op = 1, subColor = '#e0921a', flat = false}) => {
  const plateTones = paleTones(ICE);
  const gid = `nameplate_${Math.round(x)}_${Math.round(y)}`;
  const h = sub ? 88 : 60;
  return (
    <g transform={`translate(${x},${y})`} opacity={op}>
      {!flat && <ContactShadow cx={0} cy={h - 34} rx={160} ry={14} opacity={0.26} />}
      {!flat && <defs><FormGradient id={gid} t={plateTones} softness={0.75} /></defs>}
      <rect x={-150} y={-40} width={300} height={h} rx={10} fill={flat ? ICE : `url(#${gid})`} stroke={INK} strokeWidth={6} />
      {!flat && <RimLight d={`M-146,-34 L-146,${h - 46}`} w={4} opacity={0.38} />}
      <text x={0} y={sub ? -8 : 10} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={36} fill={INK} letterSpacing={1.5} stroke={ICE} strokeWidth={3} paintOrder="stroke">{text}</text>
      {sub && <text x={0} y={30} textAnchor="middle" fontFamily={BOLD} fontWeight={700} fontSize={20} fill={subColor}>{sub}</text>}
    </g>
  );
};

// A hanging sign swinging on its post. 1-3 lines; last line can be dimmed as a
// date/attribution via `dimLast`.
export const SwingSign: React.FC<{x: number; y: number; f: number; lines: string[]; op?: number; dimLast?: boolean}> = ({x, y, f, lines, op = 1, dimLast = false}) => {
  const swing = 6 * Math.sin(f / 18);
  const hh = 28 + lines.length * 30;
  return (
    <g transform={`translate(${x},${y})`} opacity={op}>
      <line x1={0} y1={-60} x2={0} y2={-10} stroke={INK} strokeWidth={5} />
      {/* pivot at the post tip (the episode version set a CSS transformOrigin in
          page px inside a translated group, which double-offset the pivot) */}
      <g transform={`rotate(${swing} 0 -60)`}>
        <rect x={-190} y={-10} width={380} height={hh} rx={10} fill={BIRCH} stroke={INK} strokeWidth={6} />
        {lines.map((ln, i) => (
          <text key={i} x={0} y={20 + i * 30} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={24}
            fill={dimLast && i === lines.length - 1 ? '#8a8274' : GRAPHITE_D}
            textLength={ln.length > 23 ? 360 : undefined} lengthAdjust="spacingAndGlyphs">{ln}</text>
        ))}
      </g>
    </g>
  );
};

// An industrial lever on a panel; `pulled` 0..1 throws it, optional denial
// badge (X + label) fades in as it lands.
export const GearLever: React.FC<{x: number; y: number; pulled: number; deniedLabel?: string}> = ({x, y, pulled, deniedLabel}) => (
  <g transform={`translate(${x},${y})`}>
    <rect x={-80} y={-12} width={160} height={50} rx={12} fill="#8b93a0" stroke={INK} strokeWidth={6} />
    <circle cx={-46} cy={14} r={11} fill={GRAPHITE_D} stroke={INK} strokeWidth={4} />
    <g transform={`rotate(${-40 + 40 * pulled} -46 14)`}>
      <rect x={-53} y={-4} width={13} height={78} rx={6.5} fill="#c9cfd8" stroke={INK} strokeWidth={5} />
      <circle cx={-46} cy={-6} r={14} fill={RED} stroke={INK} strokeWidth={5} />
    </g>
    {deniedLabel && (
      <g transform="translate(56,-52)" opacity={pulled}>
        <circle r={26} fill={ICE} stroke={INK} strokeWidth={6} />
        <line x1={-14} y1={-14} x2={14} y2={14} stroke={CRIMSON} strokeWidth={6} strokeLinecap="round" />
        <line x1={14} y1={-14} x2={-14} y2={14} stroke={CRIMSON} strokeWidth={6} strokeLinecap="round" />
        <text x={0} y={44} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={26} fill={INK} stroke={ICE} strokeWidth={4} paintOrder="stroke">{deniedLabel}</text>
      </g>
    )}
  </g>
);

// A driven survey stake; `settle` 0..1 drops it in. Optional red claim tag.
export const SurveyStake: React.FC<{x: number; y: number; s?: number; settle: number; tag?: boolean}> = ({x, y, s = 1, settle, tag = true}) => (
  <g transform={`translate(${x},${y}) scale(${s})`}>
    <ellipse cx={0} cy={4} rx={48} ry={10} fill={INK} opacity={0.25} />
    <g transform={`translate(0,${-40 * (1 - settle)})`} opacity={Math.min(1, settle * 1.6)}>
      <path d="M-14,0 L-14,-160 L0,-186 L14,-160 L14,0 Z" fill={WOOD} stroke={INK} strokeWidth={6} strokeLinejoin="round" />
      <path d="M4,-160 L14,-160 L14,0 L4,0 Z" fill={WOOD_D} opacity={0.7} />
      {[-40, -80, -120].map((yy, i) => <line key={i} x1={-14} y1={yy} x2={14} y2={yy} stroke={INK} strokeWidth={2.5} opacity={0.35} />)}
      {tag && <rect x={-20} y={-210} width={40} height={40} rx={4} fill={CRIMSON} stroke={INK} strokeWidth={5} />}
    </g>
  </g>
);

// A surveyor's chain paying out between two points; `taut` 0..1 (sags until
// taut), the distance tag flips up past 0.5.
export const MeasuringChain: React.FC<{x1: number; y1: number; x2: number; y2: number; taut: number; label?: string}> = ({x1, y1, x2, y2, taut, label}) => {
  const n = 18;
  const links: React.ReactNode[] = [];
  for (let i = 0; i < n * taut; i++) {
    const t = i / n;
    const sag = (1 - taut) * 30 * Math.sin(t * Math.PI);
    links.push(<circle key={i} cx={x1 + (x2 - x1) * t} cy={y1 + (y2 - y1) * t + sag} r={7} fill="none" stroke="#9aa2ad" strokeWidth={4} />);
  }
  const tagT = Math.min(1, taut * 1.2);
  return (
    <g>
      {links}
      {label && tagT > 0.5 && (
        <g transform={`translate(${x1 + (x2 - x1) * 0.5},${y1 + (y2 - y1) * 0.5 + 6}) rotate(${4 * Math.sin(tagT * 8)})`} opacity={tagT}>
          <path d="M-30,-4 L0,-24 L30,-4 L18,30 L-18,30 Z" fill={CRIMSON} stroke={INK} strokeWidth={5} strokeLinejoin="round" />
          <text x={0} y={14} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={30} fill={SNOW} stroke={INK} strokeWidth={2} paintOrder="stroke">{label}</text>
        </g>
      )}
    </g>
  );
};

// A pen hovering over a document, trembling, never signing — the unsigned-deal
// image. Optional nameplate names the party.
export const PenAndDocument: React.FC<{x: number; y: number; hover: number; f: number; plate?: string}> = ({x, y, hover, f, plate}) => {
  const tremble = 1.4 * Math.sin(f / 3);
  const settle = Math.min(1, hover * 1.4);
  return (
    <g transform={`translate(${x},${y})`}>
      <rect x={-130} y={0} width={260} height={180} rx={8} fill={SNOW} stroke={INK} strokeWidth={6} />
      <path d="M-130,0 h260 v14 h-260 Z" fill="#e7e0cc" opacity={0.6} />
      {[36, 62, 88, 114, 140, 160].map((yy, i) => <line key={i} x1={-100} y1={yy} x2={100} y2={yy} stroke="#c9c2ad" strokeWidth={3} />)}
      <g transform={`translate(${18 + tremble},${-26}) scale(${settle}) rotate(-28)`} opacity={settle}>
        <path d="M-7,0 L-7,-118 L7,-118 L7,0 Z" fill="#2b2f38" stroke={INK} strokeWidth={5} strokeLinejoin="round" />
        <path d="M0,-118 L-9,-138 L9,-138 Z" fill="#c9cfd8" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
        <rect x={-7} y={-30} width={14} height={22} fill={CRIMSON} opacity={0.9} />
        <line x1={0} y1={0} x2={0} y2={26} stroke={INK} strokeWidth={2} strokeDasharray="3 4" opacity={0.35} />
      </g>
      {plate && <Nameplate x={280} y={40} text={plate} op={0.95} />}
    </g>
  );
};

// A trail marker post with a two-line sign (e.g. a date: "AUG" / "19").
export const TrailPost: React.FC<{x: number; y: number; s?: number; top?: string; bottom?: string}> = ({x, y, s = 1, top, bottom}) => {
  // sign board auto-widens for longer top/bottom words (2026-07-22 fix: the
  // original fixed 68x64 box was sized for a single short icon-word and made
  // two full-length lines like "AS OF TODAY"/"STILL OPEN" overlap illegibly).
  const longest = Math.max(top?.length ?? 0, bottom?.length ?? 0);
  const boardW = Math.max(68, longest * 15 + 20);
  const hasBoth = Boolean(top) && Boolean(bottom);
  const boardH = hasBoth ? 92 : 64;
  return (
    <g transform={`translate(${x},${y}) scale(${s})`}>
      <ellipse cx={0} cy={4} rx={44} ry={9} fill={INK} opacity={0.25} />
      <path d="M-16,0 L-16,-220 L16,-220 L16,0 Z" fill={WOOD} stroke={INK} strokeWidth={6} strokeLinejoin="round" />
      <path d="M4,-220 L16,-220 L16,0 L4,0 Z" fill={WOOD_D} opacity={0.7} />
      <path d="M-16,-40 q16,-10 32,0" stroke={MOSS} strokeWidth={10} fill="none" opacity={0.8} />
      {(top || bottom) && <rect x={-boardW / 2} y={-198 - (hasBoth ? 14 : 0)} width={boardW} height={boardH} rx={6} fill={BIRCH} stroke={INK} strokeWidth={5} />}
      {top && <text x={0} y={hasBoth ? -180 : -174} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={22} fill={GRAPHITE_D} stroke={BIRCH} strokeWidth={3} paintOrder="stroke">{top}</text>}
      {bottom && <text x={0} y={hasBoth ? -140 : -144} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={30} fill={GRAPHITE_D} stroke={BIRCH} strokeWidth={3} paintOrder="stroke">{bottom}</text>}
    </g>
  );
};

// =============================================================================
// TallyCounter — the MECHANICAL count mark (NET-NEW 2026-07-20b, "The Referee
// Arrives"). Deliberately a physical object you could hold (brass housing,
// cream dial, rolling digits, click motion), NOT a HUD reticle/bracket: the
// story's point is who HOLDS the counter. Two variants:
//   variant="clicker"  — the hand-held dial: a circular cream face whose needle
//                        spins with `spin` (0..1 progress) and hard-locks at 1;
//                        `count` prints in the small window.
//   variant="odometer" — the mounted chip: rolling flip digits showing `count`,
//                        `roll` 0..1 animates the ones-digit mid-flip.
// =============================================================================
const BRASS = '#a8763e';
const BRASS_D = '#7c5628';
const DIAL = '#f7f1df';

export const TallyCounter: React.FC<{
  x: number; y: number; s?: number; f: number;
  variant?: 'clicker' | 'odometer';
  count?: string; spin?: number; roll?: number; tag?: string;
}> = ({x, y, s = 1, f, variant = 'clicker', count = '0001', spin = 1, roll = 0, tag}) => {
  const tB = tones(BRASS);
  const uid = `tally${Math.round(x)}_${Math.round(y)}_${variant}`;
  if (variant === 'clicker') {
    const k = Math.max(0, Math.min(1, spin));
    // needle whirls fast early, settles hard at the end (eased lock)
    const ang = 360 * 3 * (1 - Math.pow(1 - k, 3));
    const lockKick = k >= 1 ? 0 : 4 * Math.sin(f / 2) * (1 - k);
    return (
      <g transform={`translate(${x},${y}) scale(${s}) rotate(${lockKick})`}>
        <FormGradient id={`${uid}_b`} t={tB} />
        <ContactShadow cx={0} cy={64} rx={44} ry={9} opacity={0.25} blur={8} />
        {/* thumb plunger + grip ring */}
        <rect x={-10} y={-86} width={20} height={26} rx={8} fill={BRASS_D} stroke={INK} strokeWidth={5} />
        <path d="M-6,20 a30,30 0 1 0 12,0" fill="none" stroke={BRASS_D} strokeWidth={12} opacity={0.9} />
        {/* brass housing */}
        <circle r={62} fill={`url(#${uid}_b)`} stroke={INK} strokeWidth={7} />
        <RimLight d="M-58,-20 a62,62 0 0 1 34,-38" w={4} opacity={0.6} />
        {/* cream dial face */}
        <circle r={46} fill={DIAL} stroke={INK} strokeWidth={5} />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((a) => (
          <line key={a} x1={0} y1={-40} x2={0} y2={-33} stroke={INK} strokeWidth={3} transform={`rotate(${a})`} opacity={0.7} />
        ))}
        {/* needle: whirl then hard lock */}
        <g transform={`rotate(${ang})`}>
          <path d="M0,8 L-4,0 L0,-38 L4,0 Z" fill={RED} stroke={INK} strokeWidth={3} />
        </g>
        <circle r={6} fill={INK} />
        {/* count window */}
        <rect x={-30} y={16} width={60} height={22} rx={5} fill="#fff" stroke={INK} strokeWidth={4} />
        <text x={0} y={33} textAnchor="middle" fontFamily="Arial Black, Arial, sans-serif" fontWeight={900} fontSize={17} fill={INK} letterSpacing={2}>{count}</text>
        {tag && (
          <g transform={`translate(54,44) rotate(${8 + 3 * Math.sin(f / 16)})`}>
            <line x1={-8} y1={-14} x2={0} y2={0} stroke={INK} strokeWidth={3} />
            <rect x={-44} y={0} width={88} height={24} rx={5} fill={ICE} stroke={INK} strokeWidth={4} />
            <text x={0} y={17} textAnchor="middle" fontFamily="Arial Black, Arial, sans-serif" fontWeight={900} fontSize={13} fill={RED}>{tag}</text>
          </g>
        )}
      </g>
    );
  }
  // odometer chip: brass housing, rolling cream flip-digits
  const digits = count.split('');
  const r = Math.max(0, Math.min(1, roll));
  const w = digits.length * 34 + 24;
  return (
    <g transform={`translate(${x},${y}) scale(${s})`}>
      <FormGradient id={`${uid}_b`} t={tB} />
      <rect x={-w / 2} y={-34} width={w} height={68} rx={10} fill={`url(#${uid}_b)`} stroke={INK} strokeWidth={6} />
      <RimLight d={`M${-w / 2},-14 a10,10 0 0 1 8,-18`} w={3.5} opacity={0.55} />
      {digits.map((d, i) => {
        const isOnes = i === digits.length - 1;
        const flip = isOnes ? r : 0;
        const prev = isOnes ? String((parseInt(d, 10) + 9) % 10) : d;
        return (
          <g key={i} transform={`translate(${-w / 2 + 12 + 17 + i * 34},0)`}>
            <rect x={-15} y={-26} width={30} height={52} rx={4} fill={DIAL} stroke={INK} strokeWidth={4} />
            <line x1={-15} y1={0} x2={15} y2={0} stroke={INK} strokeWidth={1.5} opacity={0.5} />
            {/* mid-flip: previous digit rolls up and out, new digit rolls in */}
            <g>
              {flip < 0.05 ? (
                <text x={0} y={11} textAnchor="middle" fontFamily="Arial Black, Arial, sans-serif" fontWeight={900} fontSize={30} fill={INK}>{d}</text>
              ) : (
                <g>
                  <text x={0} y={11 - 44 * flip} textAnchor="middle" fontFamily="Arial Black, Arial, sans-serif" fontWeight={900} fontSize={30} fill={INK} opacity={1 - flip * 0.9}>{prev}</text>
                  <text x={0} y={11 + 44 * (1 - flip)} textAnchor="middle" fontFamily="Arial Black, Arial, sans-serif" fontWeight={900} fontSize={30} fill={INK} opacity={flip}>{d}</text>
                </g>
              )}
            </g>
          </g>
        );
      })}
    </g>
  );
};

// =============================================================================
// VideoWeir — the tribal camera-lane weir set piece (NET-NEW 2026-07-20b).
// Hand-built warm timber (self-determination reads as craftsmanship): angled
// leg pairs driven into the gravel, a plank walkway, the camera housing with a
// lens ring looking into the lane, and a mounted TallyCounter odometer chip.
// `plant` 0..1 drops it in with a settle; the scene drives `roll`/`count` on
// the chip as fish pass. Water is the SCENE's job; the weir sits on it.
// =============================================================================
export const VideoWeir: React.FC<{
  x: number; y: number; s?: number; f: number; plant?: number;
  count?: string; roll?: number;
}> = ({x, y, s = 1, f, plant = 1, count = '0000', roll = 0}) => {
  const p = Math.max(0, Math.min(1, plant));
  const drop = (1 - p) * -60;
  const tW = tones(WOOD);
  const uid = `weir${Math.round(x)}_${Math.round(y)}`;
  return (
    <g transform={`translate(${x},${y + drop}) scale(${s})`} opacity={Math.min(1, p * 1.5)}>
      <FormGradient id={`${uid}_w`} t={tW} />
      <ContactShadow cx={0} cy={8} rx={190} ry={16} opacity={0.28 * p} blur={10} />
      {/* leg pairs (A-frames) into the gravel */}
      {[-150, -50, 50, 150].map((lx, i) => (
        <g key={i} transform={`translate(${lx},0)`}>
          <path d="M-20,0 L-4,-120 L4,-120 L-10,0 Z" fill={`url(#${uid}_w)`} stroke={INK} strokeWidth={5} strokeLinejoin="round" />
          <path d="M20,0 L6,-120 L-2,-120 L12,0 Z" fill={tW.shade} stroke={INK} strokeWidth={5} strokeLinejoin="round" />
          {/* rounded peg */}
          <circle cx={0} cy={-118} r={7} fill={tW.key} stroke={INK} strokeWidth={4} />
        </g>
      ))}
      {/* plank walkway with grain */}
      <rect x={-200} y={-138} width={400} height={26} rx={6} fill={`url(#${uid}_w)`} stroke={INK} strokeWidth={6} />
      {[-170, -120, -70, -20, 30, 80, 130].map((gx, i) => (
        <line key={i} x1={gx} y1={-136} x2={gx + 8} y2={-114} stroke={INK} strokeWidth={2} opacity={0.3} />
      ))}
      <RimLight d="M-200,-132 h400" w={4} opacity={0.5} />
      {/* picket lane guides under water line */}
      {[-180, -140, -100, 100, 140, 180].map((px, i) => (
        <line key={i} x1={px} y1={-4} x2={px} y2={44} stroke={tW.shade} strokeWidth={7} opacity={0.75} />
      ))}
      {/* camera housing looking into the lane */}
      <g transform={`translate(-8,${-176 + 1.5 * Math.sin(f / 22)})`}>
        <rect x={-34} y={-24} width={68} height={48} rx={10} fill="#3c464f" stroke={INK} strokeWidth={6} />
        <circle cx={22} cy={0} r={13} fill="#9fc4d8" stroke={INK} strokeWidth={5} />
        <circle cx={25} cy={-3} r={4} fill="#fff" opacity={0.8} />
        <circle cx={-18} cy={-10} r={4} fill={RED} opacity={0.6 + 0.4 * Math.sin(f / 8)} />
      </g>
      {/* mounted odometer chip */}
      <TallyCounter x={110} y={-176} s={0.72} f={f} variant="odometer" count={count} roll={roll} />
    </g>
  );
};

// A glowing boundary tracing itself in (`revealT` 0..1) around any closed path,
// with an optional labeled town marker inside. `d` MUST be a closed path;
// `perim` is its approximate length (drives the dash reveal).
export const BoundaryReveal: React.FC<{revealT: number; d: string; perim?: number; accent?: string; town?: {x: number; y: number; label: string}}> = ({revealT, d, perim = 2600, accent = '#ffb531', town}) => (
  <g>
    <path d={d} fill="none" stroke={INK} strokeWidth={14} strokeDasharray={perim} strokeDashoffset={perim * (1 - revealT)} strokeLinejoin="round" />
    <path d={d} fill={accent} opacity={0.14 * revealT} />
    <path d={d} fill="none" stroke={accent} strokeWidth={7} strokeDasharray={perim} strokeDashoffset={perim * (1 - revealT)} strokeLinejoin="round" />
    {town && revealT > 0.3 && (
      <g transform={`translate(${town.x},${town.y})`} opacity={Math.min(1, (revealT - 0.3) * 2)}>
        <rect x={-30} y={-18} width={60} height={36} rx={4} fill={BIRCH} stroke={INK} strokeWidth={4} />
        <path d="M-34,-18 L0,-38 L34,-18 Z" fill={CRIMSON} stroke={INK} strokeWidth={4} strokeLinejoin="round" />
        <text x={0} y={54} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={28} fill={INK} stroke={SNOW} strokeWidth={3} paintOrder="stroke">{town.label}</text>
      </g>
    )}
  </g>
);

// =============================================================================
// CheckpointGateLever -- NET-NEW 2026-07-22 (Air Force EUL dispatch, "the
// checkpoint lever frozen at the midpoint"). An access-control/decision-gate
// prop the library lacked. Composes GearLever's `pulled` 0..1 mechanic (the
// lever-position value) but owns its own geometry: a striped barrier arm on a
// pivot post, a pivot bolt, and two signal-light housings either side of the
// post. `pulled` 0..1 sets the arm angle (0 = down/closed, 1 = up/open; the
// dispatch holds it at exactly 0.5, neither). `signalPulse` 0..1 drives BOTH
// housing lights brightening together (caution-yellow only, no red/green --
// this asset never renders a red/green pair, keeping the palette locked to
// the run's gunmetal/frost/caution-yellow world). Form-shaded (tones +
// FormGradient), RimLight along the arm's top edge, ContactShadow at the base.
export const CheckpointGateLever: React.FC<{
  x: number; y: number; pulled: number; signalPulse?: number; scale?: number;
}> = ({x, y, pulled, signalPulse = 0, scale = 1}) => {
  const metal = tones('#7c8592');
  const uid = `cgl_${x}_${y}`;
  const angle = -2 + pulled * 47; // 0 = resting just past horizontal, 0.5 = frozen halfway (~21deg), 1 = near-vertical
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <ContactShadow cx={0} cy={14} rx={120} ry={22} opacity={0.34} blur={9} />
      {/* base post */}
      <rect x={-22} y={-96} width={44} height={110} rx={8} fill={metal.base} stroke={INK} strokeWidth={6} />
      <defs><FormGradient id={`${uid}_post`} t={metal} softness={0.9} /></defs>
      <rect x={-22} y={-96} width={44} height={110} rx={8} fill={`url(#${uid}_post)`} opacity={0.55} />
      <BrushedMetal x={-22} y={-96} w={44} h={110} opacity={0.16} />
      <RimLight d="M-22,-96 L-22,14" w={4} opacity={0.5} />
      {/* pivot bolt */}
      <circle cx={0} cy={-70} r={13} fill={GRAPHITE_D} stroke={INK} strokeWidth={5} />
      <circle cx={0} cy={-70} r={4} fill="#c9cfd8" />
      {/* two signal-light housings, either side of the post, caution-yellow only */}
      {[[-46, -18], [46, -18]].map(([hx, hy], i) => (
        <g key={i} transform={`translate(${hx},${hy})`}>
          <rect x={-14} y={-14} width={28} height={28} rx={6} fill={GRAPHITE_D} stroke={INK} strokeWidth={5} />
          <circle cx={0} cy={0} r={8} fill="#4a3f10" />
          <circle cx={0} cy={0} r={8} fill="#ffcf3f" opacity={signalPulse * 0.9} style={{mixBlendMode: 'screen'}} />
          {signalPulse > 0.15 && <circle cx={0} cy={0} r={13} fill="none" stroke="#ffcf3f" strokeWidth={2} opacity={signalPulse * 0.5} />}
        </g>
      ))}
      {/* the striped barrier arm, on the pivot */}
      <g transform={`rotate(${angle} 0 -70)`}>
        <rect x={-14} y={-78} width={28} height={220} rx={10} fill={metal.core} stroke={INK} strokeWidth={6} />
        <defs><FormGradient id={`${uid}_arm`} t={metal} softness={0.85} /></defs>
        <rect x={-14} y={-78} width={28} height={220} rx={10} fill={`url(#${uid}_arm)`} opacity={0.5} />
        {Array.from({length: 5}).map((_, i) => (
          <rect key={i} x={-14} y={-64 + i * 44} width={28} height={22} fill={i % 2 === 0 ? '#1a1d24' : '#ffcf3f'} opacity={0.85} />
        ))}
        <RimLight d="M-14,-78 L-14,142" w={3.5} opacity={0.55} />
        <circle cx={0} cy={142} r={10} fill={metal.shade} stroke={INK} strokeWidth={4} />
      </g>
    </g>
  );
};
