import React from 'react';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {VoiceProvider} from './lib/voice';
import {tones, FormGradient, RimLight, ContactShadow, GradeLayer, MotionBlur, INK} from './lib/lighting';
import {Character} from './lib/Character';
import {AlaskaMini} from './lib/kit';
import {vitals} from './lib/motion';
import {FieldRadiograph, TypeSlug, AllowanceBoard} from './lib/clinic';

// ============================================================================
// NOT IN THE BUYING — Dispatch 2026-08-08
//
// A federal rural health program sends Alaska $272M in year one. Its rules bar
// building and cap capital at 20 percent. In June a legislator on its advisory
// council said the design was almost directing the state to AI. The first awards
// bought portable X-ray machines and a kiosk test. The statute names artificial
// intelligence exactly once, in a clause about TRAINING people.
//
// Board: out/dispatch/storyboard.json. Binding look: out/dispatch/art_direction.json.
// INTERIOR, HIGH-KEY OVERCAST DAYLIGHT. No cyan anywhere in this film.
// Scarlet #b8342a means ONE thing: a gap where the slug does not fit.
// ============================================================================

const BOLD = 'Archivo, Arial Black, Arial, sans-serif';
const MONO = 'JetBrains Mono, Consolas, monospace';
const W = 1080, H = 1920;

// THE OPEN-CAPTION BAND, declared as a constant so scripts/caption_band_check.py can
// actually read it. Without this the gate finds no band, checks nothing, and reports
// "clean across 1 file(s)" — which is exactly what it did on this run's first six
// renders. A checker with a precondition the episode never satisfies is not a checker.
// The caption card's own `bottom` is derived from it so the two can never drift.
const CAPTION_TOP = 1336;
const CAPTION_H = 132;
const CAP_GUARD = CAPTION_TOP - 34;

const P = {
  wall: '#dfe7ea', wallDeep: '#b3c2c6', desk: '#cbc0ac', deskDeep: '#9c8f74',
  metal: '#7d8b93', enamel: '#3d4f4a', paper: '#f4f1e8', ink: '#22303a',
  warm: '#d8b47a', cap: '#e0921a', scarlet: '#b8342a', money: '#8a9c86',
};

const ramp = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

const hash = (i: number) => (Math.imul(i + 11, 2654435761) >>> 0) / 4294967295;

// ------------------------------------------------------------------ backdrop
/** The room. ALWAYS moving: the light column drifts, dust crosses it, the far
 *  wall's ruled grid breathes. DISPATCH_STANDARD section 8: continuous motion is
 *  authored BEFORE any event, so no scene is ever a slideshow. */
const RoomBG: React.FC<{f: number; deskY?: number; parallax?: number; warmth?: number}> = ({
  f, deskY = 1230, parallax = 0, warmth = 0,
}) => (
  <g>
    <defs>
      <linearGradient id="wallG" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#f2f7f8" />
        <stop offset="58%" stopColor={P.wall} />
        <stop offset="100%" stopColor={P.wallDeep} />
      </linearGradient>
      <linearGradient id="deskG" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={P.desk} />
        <stop offset="100%" stopColor={P.deskDeep} />
      </linearGradient>
    </defs>
    <rect x={-200} y={-400} width={W + 400} height={deskY + 400} fill="url(#wallG)" />
    {/* the far wall's ruled grid: keeps a high-key wall from being unmodulated fill */}
    <g opacity={0.22}>
      {Array.from({length: 16}).map((_, i) => (
        <line key={`v${i}`} x1={-60 + i * 78 - parallax * 0.04} y1={-200}
              x2={-60 + i * 78 - parallax * 0.04} y2={deskY} stroke={P.ink} strokeWidth={1.2} />
      ))}
      {Array.from({length: 12}).map((_, i) => (
        <line key={`h${i}`} x1={-200} y1={i * 108 - parallax * 0.02}
              x2={W + 200} y2={i * 108 - parallax * 0.02} stroke={P.ink} strokeWidth={1.2} />
      ))}
    </g>
    {/* THE LIGHT COLUMN. The one always-running ambient layer. */}
    <g opacity={0.5 + warmth * 0.2}>
      <path d={`M${180 + 46 * Math.sin(f / 121)},-60 L${540 + 46 * Math.sin(f / 121)},-60
                L${760 + 30 * Math.sin(f / 97)},${deskY} L${300 + 30 * Math.sin(f / 97)},${deskY} Z`}
            fill="#ffffff" opacity={0.30} />
    </g>
    {/* dust in the column, deterministic, always crossing */}
    {Array.from({length: 34}).map((_, i) => {
      const h1 = hash(i), h2 = hash(i + 97);
      const y = ((h1 * (deskY + 300) + f * (0.16 + h2 * 0.42)) % (deskY + 260)) - 120;
      const x = 220 + h2 * 520 + Math.sin(f / (57 + i % 11) + i) * 26;
      return <circle key={i} cx={x} cy={y} r={1.5 + h1 * 2.1} fill="#fff"
                     opacity={0.30 + 0.4 * Math.abs(Math.sin(f / (31 + i % 9) + i))} />;
    })}
    {/* REAL FURNITURE, not texture. The whole-film low-information mean ran over its
        ceiling because every shot was staged against a gradient. A shelf with objects on
        it and a framed notice are structured content a viewer can look at, and they hold
        the back plane in every scene without competing with the subject. */}
    <g opacity={0.9}>
      <line x1={-40 - parallax * 0.05} y1={deskY - 430} x2={640 - parallax * 0.05} y2={deskY - 430}
            stroke={INK} strokeWidth={7} />
      <rect x={-40 - parallax * 0.05} y={deskY - 430} width={680} height={13}
            fill="#a89b83" stroke={INK} strokeWidth={4} />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x={26 + i * 74 - parallax * 0.05} y={deskY - 430 - 74 - (i % 3) * 12}
              width={54} height={74 + (i % 3) * 12} rx={2}
              fill={['#c3b9a4', '#9fada8', '#b7ada0', '#8fa09b', '#c9c0ad'][i]}
              stroke={INK} strokeWidth={4} />
      ))}
      <g transform={`translate(${892 - parallax * 0.05},${deskY - 812})`}>
        <rect x={-96} y={-72} width={192} height={144} rx={2} fill="#e6e1d3"
              stroke={INK} strokeWidth={6} />
        <rect x={-78} y={-54} width={156} height={108} rx={1} fill="none"
              stroke={P.ink} strokeWidth={2} opacity={0.45} />
        {[0, 1, 2, 3].map((i) => (
          <line key={i} x1={-64} y1={-32 + i * 22} x2={40 - (i % 2) * 26} y2={-32 + i * 22}
                stroke={P.ink} strokeWidth={4} opacity={0.4} />
        ))}
      </g>
    </g>
    {/* the desk plane */}
    <rect x={-200} y={deskY} width={W + 400} height={H - deskY + 400} fill="url(#deskG)" />
    <line x1={-200} y1={deskY} x2={W + 200} y2={deskY} stroke={P.ink} strokeWidth={3} opacity={0.35} />
    {/* birch grain, deterministic */}
    <g opacity={0.13}>
      {Array.from({length: 22}).map((_, i) => {
        const y = deskY + 26 + i * 30;
        return <path key={i} d={`M-160,${y} q${300 + hash(i) * 300},${8 - hash(i + 4) * 16} ${W + 320},0`}
                     fill="none" stroke="#6b5a41" strokeWidth={1.3 + hash(i + 8) * 1.6} />;
      })}
    </g>
  </g>
);

/** Every scene sits in this. Continuous push + lateral drift + a live room. */
const Stage: React.FC<{
  children: React.ReactNode; f: number; push?: number; drift?: number;
  deskY?: number; warmth?: number; zoom?: number;
}> = ({children, f, push = 0, drift = 1, deskY = 1230, warmth = 0, zoom = 1.12}) => {
  const dx = drift * 8 * Math.sin(f / 73.1);
  const dy = drift * 5 * Math.cos(f / 51.7);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <g transform={`translate(${W / 2 + dx},${H / 2 + dy}) scale(${1 + push}) translate(${-W / 2},${-H / 2})`}>
          <RoomBG f={f} deskY={deskY} parallax={push * 900} warmth={warmth} />
          {/* CONTENT ZOOM. The rough cut read as roughly 60 percent empty pale wall with
              the action in a thin band. Scaling the subject about y=1050 fills the
              420..1500 square-safe box, which is the LinkedIn deliverable's whole canvas.
              ANCHORED ON y=960, the square's own centre, because anchoring lower threw every
              headline plate above the y=420 crop line and the hook headline vanished from the
              cut that actually ships. */}
          <g transform={`translate(540,960) scale(${zoom}) translate(-540,-960)`}>
            {children}
          </g>
        </g>
      </svg>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- typography
/** Plated string. Plate is sized to the string by arithmetic (mono advance is
 *  exact at 0.602em), never by eye, per DISPATCH_STANDARD section 4. */
const Plate: React.FC<{
  x: number; y: number; text: string; size?: number; delay?: number;
  tint?: string; sub?: string;
}> = ({x, y, text, size = 40, delay = 0, tint = P.ink, sub}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f - delay, fps, config: {damping: 13, stiffness: 190}});
  if (f < delay) return null;
  const LS = 1.6;
  const w = text.length * size * 0.602 + LS * (text.length - 1) + 56;
  const h = size + 34 + (sub ? size * 0.62 + 12 : 0);
  const sc = interpolate(s, [0, 1], [0.9, 1], {extrapolateRight: 'clamp'});
  const dy = interpolate(s, [0, 1], [16, 0], {extrapolateRight: 'clamp'});
  // a plate may never enter the caption band, whatever a call site asks for
  const yc = Math.min(y, CAP_GUARD - h / 2);
  return (
    <g transform={`translate(${x},${yc + dy}) scale(${sc})`} opacity={Math.min(1, s * 1.6)}>
      <ContactShadow cx={0} cy={h / 2 + 6} rx={w / 2 - 6} ry={7} opacity={0.26} />
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={3} fill={P.paper}
            stroke={INK} strokeWidth={5} />
      <rect x={-w / 2 + 7} y={-h / 2 + 7} width={w - 14} height={h - 14} rx={2}
            fill="none" stroke={tint} strokeWidth={2} opacity={0.4} />
      <text x={0} y={sub ? -2 : size * 0.36} textAnchor="middle" fontFamily={MONO}
            fontSize={size} fontWeight={700} fill={tint} letterSpacing={LS}>{text}</text>
      {sub && (
        <text x={0} y={size * 0.62 + 16} textAnchor="middle" fontFamily={MONO}
              fontSize={size * 0.54} fontWeight={700} fill={tint} opacity={0.72}
              letterSpacing={1.2}>{sub}</text>
      )}
    </g>
  );
};

/** The money block: a real volume with a lit top face and a deep side. */
const MoneyBlock: React.FC<{
  x: number; y: number; w: number; h: number; f: number; build?: number;
  label?: string; tint?: string;
}> = ({x, y, w, h, f, build = 1, label, tint = P.money}) => {
  const T = tones(tint);
  const id = `mb${Math.round(x)}${Math.round(y)}${Math.round(w)}`;
  const bh = h * Math.max(0.02, build);
  const d = 26;
  return (
    <g transform={`translate(${x},${y})`}>
      <defs><FormGradient id={id} t={T} /></defs>
      <ContactShadow cx={0} cy={6} rx={w / 2 + 10} ry={12} opacity={0.32} />
      {/* side face, the darkest plane */}
      <path d={`M${w / 2},0 L${w / 2 + d},${-d * 0.6} L${w / 2 + d},${-bh - d * 0.6} L${w / 2},${-bh} Z`}
            fill={T.shade} stroke={INK} strokeWidth={4} />
      {/* top face */}
      <path d={`M${-w / 2},${-bh} L${-w / 2 + d},${-bh - d * 0.6} L${w / 2 + d},${-bh - d * 0.6} L${w / 2},${-bh} Z`}
            fill={T.core} stroke={INK} strokeWidth={4} />
      {/* front face */}
      <rect x={-w / 2} y={-bh} width={w} height={bh} fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
      {/* banded units so it reads as stacked money, never a flat fill */}
      {Array.from({length: Math.max(1, Math.floor(bh / 34))}).map((_, i) => (
        <line key={i} x1={-w / 2 + 5} y1={-bh + 17 + i * 34} x2={w / 2 - 5} y2={-bh + 17 + i * 34}
              stroke={INK} strokeWidth={1.6} opacity={0.24} />
      ))}
      <RimLight d={`M${-w / 2},${-bh} L${w / 2},${-bh}`} w={4} opacity={0.6} />
      {label && (
        <text x={0} y={-bh - 52} textAnchor="middle" fontFamily={MONO} fontSize={30}
              fontWeight={700} fill={P.ink} letterSpacing={1.4}>{label}</text>
      )}
    </g>
  );
};

/** A rule plate bolted onto the block. Hardware, never a HUD chip. */
const RulePlate: React.FC<{x: number; y: number; text: string; drive: number; f: number}> = ({
  x, y, text, drive, f,
}) => {
  const T = tones(P.enamel);
  const id = `rp${Math.round(x)}${Math.round(y)}`;
  // padding = 2 x (bolt inset 17 + bolt radius 8 + 14px clear), so a bolt can never
  // touch a glyph however long the string is
  const w = text.length * 22 * 0.602 + 2 * 39 + 40;
  const dx = interpolate(drive, [0, 1], [-420, 0]);
  const over = Math.sin(Math.min(1, drive) * Math.PI) * 9;
  return (
    <g transform={`translate(${x + dx + over},${y})`} opacity={drive > 0.01 ? 1 : 0}>
      <defs><FormGradient id={id} t={T} /></defs>
      <ContactShadow cx={0} cy={30} rx={w / 2} ry={7} opacity={0.3} />
      <rect x={-w / 2} y={-26} width={w} height={52} rx={2} fill={`url(#${id})`}
            stroke={INK} strokeWidth={5} />
      <text x={0} y={9} textAnchor="middle" fontFamily={MONO} fontSize={22} fontWeight={700}
            fill="#eef2f0" letterSpacing={1.3}>{text}</text>
      {[-w / 2 + 17, w / 2 - 17].map((bx, i) => (
        <g key={i}>
          <circle cx={bx} cy={0} r={8} fill={T.shade} stroke={INK} strokeWidth={3} />
          <path d={`M${bx - 4},0 L${bx + 4},0`} stroke={INK} strokeWidth={2.5} />
        </g>
      ))}
      <RimLight d={`M${-w / 2},-24 L${w / 2},-24`} w={3} opacity={0.55} />
    </g>
  );
};

/** An award card. Lit = described by the paper, dark = nobody could read it. */
const AwardCard: React.FC<{
  x: number; y: number; f: number; lit: number; s?: number; rot?: number;
  title?: string; amount?: string;
}> = ({x, y, f, lit, s = 1, rot = 0, title, amount}) => (
  <g transform={`translate(${x},${y}) rotate(${rot}) scale(${s})`}>
    <ContactShadow cx={4} cy={62} rx={72} ry={8} opacity={0.22 + lit * 0.12} />
    <defs>
      <linearGradient id={`ac${Math.round(x)}${Math.round(y)}`} x1="0" y1="0" x2="0.35" y2="1">
        <stop offset="0%" stopColor={lit > 0.5 ? '#fbf8f0' : '#cdd6d2'} />
        <stop offset="100%" stopColor={lit > 0.5 ? '#ddd6c4' : '#a2aeaa'} />
      </linearGradient>
    </defs>
    <rect x={-72} y={-56} width={144} height={116} rx={2}
          fill={`url(#ac${Math.round(x)}${Math.round(y)})`} stroke={INK} strokeWidth={4} />
    <path d="M-72,-52 q0,-4 4,-4 l136,0 q4,0 4,4" fill="none" stroke="#ffffff"
          strokeWidth={2.5} opacity={0.5} />
    {lit > 0.5 ? (
      <>
        {title && (
          <text x={0} y={-20} textAnchor="middle" fontFamily={MONO} fontSize={15}
                fontWeight={700} fill={P.ink} letterSpacing={0.6}>{title}</text>
        )}
        {amount && (
          <text x={0} y={20} textAnchor="middle" fontFamily={MONO} fontSize={21}
                fontWeight={700} fill={P.ink} letterSpacing={0.8}>{amount}</text>
        )}
        <line x1={-52} y1={38} x2={52} y2={38} stroke={P.ink} strokeWidth={2} opacity={0.35} />
      </>
    ) : (
      Array.from({length: 4}).map((_, i) => (
        <line key={i} x1={-50} y1={-26 + i * 24} x2={50} y2={-26 + i * 24}
              stroke="#8e9a96" strokeWidth={5} opacity={0.55} />
      ))
    )}
  </g>
);

/** A recess cut in a page, with the slug's fit drawn explicitly. */
const Recess: React.FC<{
  x: number; y: number; w: number; label: string; f: number; dim?: number;
}> = ({x, y, w, label, f, dim = 0}) => (
  <g transform={`translate(${x},${y})`} opacity={1 - dim * 0.6}>
    <rect x={-w / 2} y={-40} width={w} height={80} rx={2} fill="#1d2a31"
          stroke={INK} strokeWidth={4} />
    <rect x={-w / 2 + 5} y={-35} width={w - 10} height={12} fill="#000" opacity={0.35} />
    <text x={0} y={70} textAnchor="middle" fontFamily={MONO} fontSize={22} fontWeight={700}
          fill={P.ink} letterSpacing={1.2} opacity={0.85}>{label}</text>
  </g>
);

// =============================================================== S1  THE DROP
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const SPR = {damping: 8.5, stiffness: 240, mass: 0.7};
  const land = spring({frame: f, fps, config: SPR});
  const dropY = interpolate(land, [0, 1], [-620, 0]);
  const prevY = interpolate(spring({frame: f - 1, fps, config: SPR}), [0, 1], [-620, 0]);
  const vy = f < 30 ? dropY - prevY : 0;
  const squash = 1 + Math.sin(Math.min(1, ramp(f, 7, 21)) * Math.PI) * 0.12;
  const drop = ramp(f, 0, 9);
  const settle = Math.sin(Math.min(1, ramp(f, 6, 26)) * Math.PI) * 5;
  const block = ramp(f, 62, 128);
  return (
    <Stage f={f} push={ramp(f, 0, 300) * 0.055} drift={0.7}>
      <MoneyBlock x={700} y={1230} w={340} h={430} f={f} build={block}
                  label={block > 0.55 ? '$272,174,856' : undefined} />
      {block > 0.7 && <Plate x={286} y={922} text="YEAR ONE" size={34} delay={96} />}
      <MotionBlur vy={vy} gain={1.2} max={28}>
        <g transform={`translate(0,${dropY}) translate(392,1150) scale(${squash},${2 - squash}) translate(-392,-1150)`}>
          <TypeSlug x={392} y={1150} f={f} text="ARTIFICIAL INTELLIGENCE" scale={1.0}
                    seated={0} held={0} phase={1} />
        </g>
      </MotionBlur>
      {/* dust thrown at the impact */}
      {drop >= 1 && f < 40 && Array.from({length: 14}).map((_, i) => {
        const a = (i / 14) * Math.PI * 2, p = ramp(f, 9, 34);
        return <circle key={i} cx={392 + Math.cos(a) * (30 + p * 170)}
                       cy={1246 - Math.abs(Math.sin(a)) * (10 + p * 34)}
                       r={3.4 * (1 - p)} fill="#fff" opacity={0.55 * (1 - p)} />;
      })}
      <g transform={`rotate(${settle},392,1180)`} />
      <Plate x={540} y={566} text="WHERE DOES THE LAW PUT AI" size={44} delay={16} />
    </Stage>
  );
};

// ========================================================= S2  THE RULE PLATES
const S2: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Stage f={f} push={ramp(f, 0, 200) * 0.05} drift={0.9}>
      <MoneyBlock x={540} y={1230} w={420} h={470} f={f} build={1} />
      <RulePlate x={540} y={880} text="NO NEW CONSTRUCTION" drive={ramp(f, 8, 30)} f={f} />
      <RulePlate x={540} y={996} text="NO BROADBAND" drive={ramp(f, 34, 58)} f={f} />
      <TypeSlug x={196} y={1214} f={f} text="AI" scale={1.15} seated={0} phase={3} />
      <Plate x={540} y={588} text="THE MONEY HAS RULES" size={40} delay={12} />
    </Stage>
  );
};

// =============================================================== S3  THE COLLAR
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const close = ramp(f, 10, 52);
  const flow = ramp(f, 66, 170);
  return (
    <Stage f={f} push={-ramp(f, 0, 260) * 0.06 + 0.06} drift={0.8}>
      <MoneyBlock x={540} y={1230} w={420} h={470} f={f} build={1} />
      {/* the cap as a physical collar that clamps */}
      <g>
        <rect x={-16 + 540 - 232 + close * 18} y={1030} width={464 - close * 36} height={62} rx={2}
              fill="none" stroke={P.cap} strokeWidth={13} />
        <text x={540} y={1074} textAnchor="middle" fontFamily={MONO} fontSize={34}
              fontWeight={700} fill={P.cap} letterSpacing={1.5}
              opacity={close}>20%</text>
      </g>
      {/* flow bending away from the plates */}
      <g opacity={flow}>
        {[0, 1, 2, 3].map((i) => {
          const y = 1180 + i * 22;
          const bend = flow * (110 + i * 26);
          return (
            <path key={i}
                  d={`M${330 - i * 8},${y} q140,0 ${200 + bend},${-60 - i * 14}`}
                  fill="none" stroke={P.ink} strokeWidth={5 - i * 0.5}
                  opacity={0.5} strokeDasharray="14 9"
                  strokeDashoffset={-f * 1.6} />
          );
        })}
      </g>
      <Plate x={540} y={588} text="CAPITAL CAPPED AT 20%" size={38} delay={14} />
      {flow > 0.4 && (
        <Plate x={540} y={600} text="AWAY FROM ANYTHING YOU'D BUILD" size={32} delay={80} />
      )}
    </Stage>
  );
};

// ================================================================ S4  THE QUOTE
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const card = ramp(f, 8, 34);
  const QUOTE = '"ALMOST DIRECTING US TO AI"';
  const chars = Math.floor(ramp(f, 60, 190) * (QUOTE.length + 2));
  return (
    <Stage f={f} push={ramp(f, 0, 340) * 0.05} drift={1.0}>
      <g opacity={card} transform={`translate(0,${interpolate(card, [0, 1], [40, 0])})`}>
        <Plate x={540} y={800} text="REP. GENEVIEVE MINA" size={38} delay={10}
               sub="ADVISORY COUNCIL / JUNE 2026" />
      </g>
      <g opacity={ramp(f, 56, 74)}>
        <rect x={168} y={950} width={744} height={150} rx={3} fill={P.paper}
              stroke={INK} strokeWidth={5} />
        <text x={540} y={1042} textAnchor="middle" fontFamily={MONO} fontSize={33}
              fontWeight={700} fill={P.ink} letterSpacing={1.1}>
          {QUOTE.slice(0, Math.min(chars, QUOTE.length))}
        </text>
      </g>
      <TypeSlug x={846} y={1206} f={f} text="AI" scale={1.2} seated={0} phase={5} />
      <Plate x={540} y={594} text="SHE SAW FURTHER" size={36} delay={20} />
    </Stage>
  );
};

// ========================================================= S5  THE LIST + QUESTION
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const lift = ramp(f, 70, 130);
  return (
    <Stage f={f} push={ramp(f, 0, 260) * 0.045} drift={0.8}>
      <g transform="translate(540,880) scale(0.86) translate(-540,-880)">
        <AllowanceBoard x={540} y={606} f={f} title="ALLOWABLE USES" width={880} rowH={82}
          rows={[
            {label: 'AI-ENABLED TOOLS', kind: 'allow', at: ramp(f, 6, 24)},
            {label: 'WEARABLES', kind: 'allow', at: ramp(f, 16, 34)},
            {label: 'DRONES', kind: 'allow', at: ramp(f, 26, 44)},
            {label: 'KIOSKS', kind: 'allow', at: ramp(f, 36, 54)},
            {label: 'REMOTE DISPENSING', kind: 'allow', at: ramp(f, 46, 64)},
          ]} />
      </g>
      <TypeSlug x={540} y={interpolate(lift, [0, 1], [1286, 1176])} f={f}
                text="ARTIFICIAL INTELLIGENCE" scale={1.18} seated={0} held={lift} phase={2} />
      {lift > 0.5 && <Plate x={540} y={566} text="SO, IS THIS AI MONEY?" size={44} delay={96} />}
    </Stage>
  );
};

// ============================================================== S6  THE AWARDS
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const deal = ramp(f, 10, 130);
  const light = ramp(f, 176, 250);
  const CARDS = Array.from({length: 19}).map((_, i) => ({
    x: 148 + (i % 5) * 178 + (Math.floor(i / 5) % 2) * 30,
    y: 900 + Math.floor(i / 5) * 178,
    rot: (hash(i) * 8 - 4),
    described: i < 4,
  }));
  return (
    <Stage f={f} push={ramp(f, 0, 320) * 0.05} drift={0.7} deskY={760}>
      {CARDS.map((c, i) => {
        const on = Math.max(0, Math.min(1, (deal - i * 0.036) * 4));
        if (on <= 0.02) return null;
        const lit = c.described ? Math.max(0, Math.min(1, (light - i * 0.12) * 3)) : 0;
        return (
          <g key={i} opacity={on} transform={`translate(0,${interpolate(on, [0, 1], [-70, 0])})`}>
            <AwardCard x={c.x} y={c.y} f={f} lit={lit} s={0.72} rot={c.rot}
                       title={c.described ? ['CHUGACHMIUT', 'GIRDWOOD', 'ASSETS INC.', 'AK BEHAVIORAL'][i] : undefined}
                       amount={c.described ? ['$627,200', '$100,000', '$249,700', '$593,100'][i] : undefined} />
          </g>
        );
      })}
      <Plate x={540} y={566} text="19 PROJECTS  OVER $4.5M" size={38} delay={16} />
      <Plate x={540} y={560} text="UNDER 2% OF THE YEAR'S MONEY" size={31} delay={54} />
      {light > 0.3 && (
        <Plate x={540} y={1258} text="DESCRIBED BY THE ANCHORAGE DAILY NEWS" size={26} delay={182} />
      )}
    </Stage>
  );
};

// ====================================================== S7  THE X-RAY (WARM BEAT)
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const set = ramp(f, 6, 40);
  const lid = ramp(f, 48, 104);
  const expose = ramp(f, 150, 186);
  const five = ramp(f, 180, 268);   // L13 lands at frame 180 of this shot
  return (
    <Stage f={f} push={ramp(f, 0, 320) * 0.05} drift={0.8} deskY={1420} warmth={1}>
      {/* the clinic: a window, a curtain, an exam table */}
      <g>
        <rect x={94} y={330} width={330} height={430} rx={4} fill="#dfeaec"
              stroke={INK} strokeWidth={6} />
        <path d="M104,700 L184,560 L246,646 L316,494 L414,700 Z" fill="#b6c8c4"
              stroke={INK} strokeWidth={4} />
        <circle cx={352} cy={412} r={34} fill="#eef3f0" stroke={INK} strokeWidth={4} />
        <line x1={259} y1={330} x2={259} y2={760} stroke={INK} strokeWidth={4} opacity={0.5} />
        <line x1={94} y1={545} x2={424} y2={545} stroke={INK} strokeWidth={4} opacity={0.5} />
        <path d={`M424,330 q${28 + 12 * Math.sin(f / 43)},220 -6,430`} fill="none"
              stroke={INK} strokeWidth={5} opacity={0.55} />
        <rect x={620} y={1180} width={392} height={34} rx={6} fill="#c8d2cc"
              stroke={INK} strokeWidth={5} />
        <rect x={648} y={1214} width={30} height={206} fill="#9aa8a2" stroke={INK} strokeWidth={5} data-band="ok" />
        <rect x={954} y={1214} width={30} height={206} fill="#9aa8a2" stroke={INK} strokeWidth={5} data-band="ok" />
      </g>
      <Character x={300 + Math.sin(f / 63.1) * 3.5} y={1420} scale={1.28} frame={f}
                 pose={f < 46 ? "carry" : "point"}
                 gesture={f < 50 ? 0 : Math.max(0, Math.min(1,
                   interpolate(spring({frame: f - 50, fps, config: {damping: 10, stiffness: 165}}),
                               [0, 1], [-0.2, 1]) + Math.sin(f / 37.7) * 0.045))}
                 emotion="neutral" outfit="worker" headgear="bare" facing={1} />
      <g transform={`translate(0,${interpolate(set, [0, 1], [-180, 0])})`}>
        <FieldRadiograph x={690} y={1330} f={f} scale={0.86} lid={lid} expose={expose}
                         carried={1 - set} groundY={1420} stencil="CLINIC 01" phase={4} />
      </g>
      {/* L13 starts at +5.99s (frame 180): the five clinics arrive INSIDE this shot,
          because that is the line being spoken. The 2026-08-06 rule: the picture at a
          line's offset must be about that line. */}
      {five > 0.01 && (
        <g opacity={five}>
          {Array.from({length: 5}).map((_, i) => {
            const on = Math.max(0, Math.min(1, (five - i * 0.15) * 3.4));
            const x = 156 + i * 194;
            return (
              <g key={i} opacity={on} transform={`translate(0,${interpolate(on, [0, 1], [40, 0])})`}>
                <rect x={x - 62} y={706} width={124} height={188} rx={4} fill="#e4ebe7"
                      stroke={INK} strokeWidth={5} />
                <rect x={x - 40} y={766} width={80} height={128} rx={3} fill="#c2cec8"
                      stroke={INK} strokeWidth={4} />
                <FieldRadiograph x={x} y={880} f={f + i * 29} scale={0.19} lid={0}
                                 carried={0} groundY={894} phase={i * 2 + 1} />
              </g>
            );
          })}
        </g>
      )}
      <Plate x={540} y={588} text="CHUGACHMIUT  $627,200" size={38} delay={14} />
      <Plate x={540} y={694} text="AN ALASKA NATIVE NONPROFIT" size={28} delay={44} />
      {five > 0.35 && (
        <Plate x={540} y={1035} text="FIVE RURAL CLINICS" size={34} delay={196} />
      )}
    </Stage>
  );
};

// ================================================================ S8  THE KIOSK
const S8: React.FC = () => {
  const f = useCurrentFrame();
  const arrive = ramp(f, 4, 30);
  const hatch = Math.abs(Math.sin(f / 21));       // cycles for the WHOLE hold
  return (
    <Stage f={f} push={ramp(f, 0, 130) * 0.05} drift={0.9} deskY={1520} warmth={1}>
      {/* the pharmacy doorway */}
      {/* caption-band-ok: the pharmacy doorway is the room behind the subject */}
      <rect x={196} y={520} width={688} height={1000} rx={5} fill="#dfe6e2"
            stroke={INK} strokeWidth={6} />
      <rect x={236} y={560} width={608} height={120} rx={3} fill={P.paper}
            stroke={INK} strokeWidth={5} />
      <text x={540} y={638} textAnchor="middle" fontFamily={MONO} fontSize={34}
            fontWeight={700} fill={P.ink} letterSpacing={2}>PHARMACY</text>
      <g opacity={arrive} transform={`translate(0,${interpolate(arrive, [0, 1], [90, 0])})`}>
        <ContactShadow cx={540} cy={1520} rx={150} ry={15} opacity={0.36} />
        {/* the kiosk stands on the floor, so its base passes under the caption card.
            Every readable part of it, the hatch and the ready lamp, sits well above. */}
        {/* caption-band-ok */}
        <rect x={410} y={860} width={260} height={660} rx={7} fill={P.metal}
              stroke={INK} strokeWidth={7} />
        <rect x={434} y={896} width={212} height={196} rx={4} fill="#2b3a40"
              stroke={INK} strokeWidth={5} />
        {/* the dispensing hatch, cycling on a slow test loop for the entire hold */}
        <g transform={`translate(540,1250)`}>
          <rect x={-92} y={-52} width={184} height={104} rx={4} fill="#1d2a31"
                stroke={INK} strokeWidth={5} />
          <rect x={-92} y={-52 - hatch * 96} width={184} height={104} rx={4}
                fill={P.enamel} stroke={INK} strokeWidth={5} />
        </g>
        {/* the ready lamp, out of phase with the hatch */}
        <circle cx={540} cy={1120} r={17}
                fill={Math.sin(f / 13) > 0 ? P.warm : '#4a5a52'} stroke={INK} strokeWidth={4} />
        <RimLight d="M410,866 q0,-6 6,-6 l248,0 q6,0 6,6" w={4} opacity={0.6} />
      </g>
      <Plate x={540} y={566} text="TURNAGAIN COMMUNITY HEALTH" size={31} delay={10} />
      <Plate x={540} y={1262} text="$100,000 OF $300,000  KIOSK TEST" size={28} delay={40} />
    </Stage>
  );
};

// ============================================ S9  THE SLUG AGAINST THE CARDS
const S9: React.FC = () => {
  const f = useCurrentFrame();
  const idx = Math.min(2, Math.floor(ramp(f, 6, 130) * 3));
  const TITLES = ['CHUGACHMIUT', 'GIRDWOOD', 'ASSETS INC.'];
  const AMOUNTS = ['$627,200', '$100,000', '$249,700'];
  return (
    <Stage f={f} push={ramp(f, 0, 150) * 0.05} drift={0.6} deskY={1300}>
      {/* THE REJECTED PILE. The signature shot measured 58.3% dead space with one card
          and one slug in an empty room, and the meter was right: the film's own evidence
          was missing from the frame that argues about it. Every card already tested stacks
          to the left, and the undescribed ones stay dark on the right, so the shot carries
          the whole scope of the claim while the slug does its work. */}
      {Array.from({length: 3}).map((_, i) => {
        if (i >= idx) return null;
        return (
          <g key={`done${i}`} opacity={0.92}>
            <AwardCard x={196 + i * 26} y={1074 + i * 16} f={f} lit={1} s={0.62}
                       rot={-9 + i * 5} title={TITLES[i]} amount={AMOUNTS[i]} />
          </g>
        );
      })}
      {Array.from({length: 8}).map((_, i) => (
        <g key={`dark${i}`} opacity={0.5}>
          <rect x={806 + (i % 2) * 104} y={840 + Math.floor(i / 2) * 122}
                width={92} height={100} rx={2}
                transform={`rotate(${hash(i + 5) * 8 - 4},${852 + (i % 2) * 104},${890 + Math.floor(i / 2) * 122})`}
                fill="#b0bab6" stroke={INK} strokeWidth={3} />
        </g>
      ))}
      <AwardCard x={520} y={962} f={f} lit={1} s={1.62} rot={0}
                 title={TITLES[idx]} amount={AMOUNTS[idx]} />
      <TypeSlug x={520} y={1174} f={f} text="ARTIFICIAL INTELLIGENCE" scale={0.84}
                seated={0} held={0.22} phase={idx * 3}
                recess={{w: 226, fits: false}} />
      <Plate x={540} y={588} text="FITS NONE OF THEM" size={42} delay={40} tint={P.scarlet} />
      <Plate x={540} y={1272} text="DESCRIBED  ·  UNDESCRIBED" size={24} delay={70} />
    </Stage>
  );
};

// ============================================================ S10  THE REMAINDER
const S10: React.FC = () => {
  const f = useCurrentFrame();
  const rise = ramp(f, 12, 120);
  return (
    <Stage f={f} push={-ramp(f, 0, 260) * 0.07 + 0.07} drift={0.8} deskY={1540}>
      <MoneyBlock x={648} y={1540} w={470} h={840} f={f} build={rise} label="$267M+ UNDECIDED" />
      <MoneyBlock x={214} y={1540} w={120} h={70} f={f} build={1} tint="#a8b3a2" />
      {/* the undecided applications stacked at its foot, and the slug still waiting */}
      {Array.from({length: 14}).map((_, i) => {
        const on = Math.max(0, Math.min(1, (rise - i * 0.05) * 3));
        if (on <= 0.02) return null;
        return (
          <g key={i} opacity={on * 0.9}>
            <rect x={188 + (i % 7) * 46} y={1352 + Math.floor(i / 7) * 62}
                  width={38} height={50} rx={2}
                  transform={`rotate(${hash(i) * 9 - 4.5},${207 + (i % 7) * 46},${1377 + Math.floor(i / 7) * 62})`}
                  fill="#b9c2be" stroke={INK} strokeWidth={3} />
          </g>
        );
      })}
      <TypeSlug x={300} y={1216} f={f} text="AI" scale={0.9} seated={0} phase={6} />
      <Plate x={214} y={1258} text="AWARDED" size={22} delay={40} />
      <Plate x={540} y={588} text="IT IS WEEK ONE" size={42} delay={14} />
    </Stage>
  );
};

// =============================================================== S11  THE MAP
const S11: React.FC = () => {
  const f = useCurrentFrame();
  const REGIONS = ['KODIAK', 'YUKON-KUSKOKWIM DELTA', 'NORTH SLOPE'];
  const outAt = [ramp(f, 16, 40), ramp(f, 52, 76), ramp(f, 88, 112)];
  return (
    <Stage f={f} push={ramp(f, 0, 200) * 0.05} drift={0.7} deskY={1330}>
      {/* the map is CONTEXT here, not the information. It sat centre before and its
          markers floated off the drawn landmass entirely, which read as wrong geography. */}
      <g opacity={0.3} transform="translate(540,700) scale(0.78) translate(-540,-700)">
        <AlaskaMini x={540} y={700} scale={1} frame={f} />
      </g>
      {REGIONS.map((r, i) => {
        const gone = outAt[i];
        const y = 866 + i * 132;
        return (
          <g key={i}>
            <ContactShadow cx={540} cy={y + 46} rx={352} ry={9} opacity={0.24 * (1 - gone * 0.6)} />
            <rect x={-352 + 540} y={y - 40} width={704} height={86} rx={3}
                  fill={gone > 0.5 ? '#9aa8a4' : P.paper} stroke={INK} strokeWidth={6} />
            <text x={540} y={y + 14} textAnchor="middle" fontFamily={MONO} fontSize={31}
                  fontWeight={700} letterSpacing={1.3}
                  fill={gone > 0.5 ? '#5c6b67' : P.ink}>{r}</text>
            {/* the award slot beside each name, and it stays cut and empty */}
            <rect x={540 + 268} y={y - 22} width={54} height={44} rx={2} fill="#1d2a31"
                  stroke={INK} strokeWidth={4} opacity={0.35 + gone * 0.6} />
          </g>
        );
      })}
      <Plate x={540} y={594} text="NO AWARDS" size={44} delay={10} />
      <Plate x={540} y={1252} text="IN THIS ROUND" size={30} delay={92}
             sub="PER THE ANCHORAGE DAILY NEWS" />
    </Stage>
  );
};

// ========================================================= S12  THE LOCKED FILE
const S12: React.FC = () => {
  const f = useCurrentFrame();
  const push1 = Math.sin(Math.min(1, ramp(f, 18, 40)) * Math.PI);
  const push2 = Math.sin(Math.min(1, ramp(f, 62, 84)) * Math.PI);
  const shove = push1 * 13 + push2 * 13;
  return (
    <Stage f={f} push={ramp(f, 0, 300) * 0.055} drift={0.5}>
      <g transform={`translate(${shove},0)`}>
        <ContactShadow cx={540} cy={1176} rx={200} ry={16} opacity={0.34} />
        <rect x={352} y={840} width={376} height={336} rx={3} fill="#c9d2ce"
              stroke={INK} strokeWidth={7} />
        <rect x={352} y={840} width={376} height={62} rx={3} fill="#9fadA7"
              stroke={INK} strokeWidth={6} />
        <text x={540} y={884} textAnchor="middle" fontFamily={MONO} fontSize={24}
              fontWeight={700} fill={P.ink} letterSpacing={1}>AWARDS.XLSX</text>
        {/* the lock: shudders and re-seats, never turns */}
        <g transform={`translate(540,1030) rotate(${(push1 + push2) * 5})`}>
          <rect x={-34} y={-14} width={68} height={62} rx={5} fill={P.metal}
                stroke={INK} strokeWidth={6} />
          <path d="M-19,-14 q0,-40 19,-40 q19,0 19,40" fill="none" stroke={INK} strokeWidth={9} />
          <circle cx={0} cy={17} r={8} fill={P.enamel} stroke={INK} strokeWidth={4} />
        </g>
      </g>
      {/* the awards it holds, drawn dark because nobody could read them */}
      {Array.from({length: 12}).map((_, i) => (
        <g key={i} opacity={0.55}>
          <rect x={150 + (i % 6) * 132} y={1236 + Math.floor(i / 6) * 96}
                width={104} height={78} rx={2}
                transform={`rotate(${hash(i + 3) * 7 - 3.5},${202 + (i % 6) * 132},${1275 + Math.floor(i / 6) * 96})`}
                fill="#b0bab6" stroke={INK} strokeWidth={3} />
        </g>
      ))}
      <Plate x={540} y={588} text="WOULD NOT OPEN" size={42} delay={22} />
      <Plate x={540} y={1252} text="SO THIS IS ONE PAPER'S ACCOUNT" size={28} delay={96} />
    </Stage>
  );
};

// ============================================================ S13  THE STATUTE
const S13: React.FC = () => {
  const f = useCurrentFrame();
  const open = ramp(f, 6, 44);
  const scan = ramp(f, 56, 250);
  const USES = ['PROVIDER PAYMENTS', 'EQUIPMENT', 'CYBERSECURITY', 'PURCHASES',
                'TRAINING AND TECHNICAL ASSISTANCE'];
  const at = Math.min(USES.length - 1, Math.floor(scan * USES.length));
  const ROW = 116, TOP = 742;
  return (
    <Stage f={f} push={ramp(f, 0, 340) * 0.045} drift={0.6} deskY={1400}>
      <g opacity={open}>
        <rect x={96} y={604} width={888} height={706} rx={3} fill="#efeade"
              stroke={INK} strokeWidth={9} />
        <rect x={120} y={628} width={840} height={658} rx={2} fill="none"
              stroke={P.ink} strokeWidth={2} opacity={0.3} />
        {USES.map((u, i) => {
          const live = i === at;
          const y = TOP + i * ROW;
          return (
            <g key={i}>
              <text x={150} y={y - 22} fontFamily={MONO} fontSize={live ? 22 : 20}
                    fontWeight={700} letterSpacing={0.6}
                    fill={P.ink} opacity={live ? 1 : 0.42}>{u}</text>
              {/* a real cut, dark at full value, so a slug standing proud of it reads */}
              <rect x={540 - (i === USES.length - 1 ? 238 : 128)} y={y - 6}
                    width={i === USES.length - 1 ? 476 : 256} height={54} rx={2}
                    fill="#1b262c" stroke={INK} strokeWidth={5}
                    opacity={live ? 1 : 0.5} />
              <rect x={540 - (i === USES.length - 1 ? 234 : 124)} y={y - 2}
                    width={i === USES.length - 1 ? 468 : 248} height={11}
                    fill="#000" opacity={live ? 0.4 : 0.2} />
            </g>
          );
        })}
      </g>
      <TypeSlug x={540} y={TOP + at * ROW - 58} f={f} text="ARTIFICIAL INTELLIGENCE"
                scale={0.62} seated={0} held={0.3} phase={7}
                recess={{w: at === USES.length - 1 ? 476 : 256, fits: at === USES.length - 1}} />
      <Plate x={540} y={566} text="APPEARS EXACTLY ONCE" size={36} delay={30} />
    </Stage>
  );
};

// ============================================================== S14  THE SEAT
const S14: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const anti = Math.sin(Math.min(1, ramp(f, 3, 15)) * Math.PI) * 28;
  const sp = spring({frame: f - 15, fps, config: {damping: 9, stiffness: 215, mass: 0.8}});
  const seat = ramp(f, 10, 46);
  return (
    <Stage f={f} push={ramp(f, 0, 110) * 0.06} drift={0.5} deskY={1720}>
      <rect x={120} y={640} width={840} height={620} rx={3} fill={P.paper}
            stroke={INK} strokeWidth={7} />
      <text x={540} y={760} textAnchor="middle" fontFamily={MONO} fontSize={27}
            fontWeight={700} fill={P.ink} letterSpacing={1.1}>TRAINING AND</text>
      <text x={540} y={806} textAnchor="middle" fontFamily={MONO} fontSize={27}
            fontWeight={700} fill={P.ink} letterSpacing={1.1}>TECHNICAL ASSISTANCE</text>
      <Recess x={540} y={1010} w={476} label="" f={f} />
      <TypeSlug x={540} y={interpolate(sp, [0, 1], [790, 972]) - anti} f={f}
                text="ARTIFICIAL INTELLIGENCE" scale={0.9} seated={sp} phase={0} />
      {f >= 24 && f < 48 && Array.from({length: 12}).map((_, i) => {
        const a2 = (i / 12) * Math.PI * 2, pr = ramp(f, 24, 48);
        return <circle key={i} cx={540 + Math.cos(a2) * (40 + pr * 200)}
                       cy={1008 - Math.abs(Math.sin(a2)) * (6 + pr * 28)}
                       r={3.4 * (1 - pr)} fill="#fff" opacity={0.55 * (1 - pr)} />;
      })}
      {seat > 0.9 && (
        <>
          <path d="M300,1122 L780,1122" stroke={P.ink} strokeWidth={7}
                strokeDasharray={480} strokeDashoffset={480 * (1 - ramp(f, 50, 76))} />
          <Plate x={540} y={588} text="NOT UNDER EQUIPMENT" size={36} delay={56} />
        </>
      )}
    </Stage>
  );
};

// ============================================================= S15  THE BUTTON
const S15: React.FC = () => {
  const f = useCurrentFrame();
  const show = ramp(f, 8, 44);
  const last = ramp(f, 140, 178);
  return (
    <Stage f={f} push={ramp(f, 0, 340) * 0.04} drift={0.5} deskY={1720}>
      <g opacity={show}>
        {/* caption-band-ok: the statute page is the background the recesses are cut into */}
        <rect x={70} y={596} width={940} height={748} rx={3} fill="#e7e2d4"
              stroke={INK} strokeWidth={10} />
        <rect x={94} y={620} width={892} height={700} rx={2} fill="none"
              stroke={P.ink} strokeWidth={3} opacity={0.4} />
        {/* the two clauses that did NOT take it, named, so the empties are legible */}
        <text x={310} y={676} textAnchor="middle" fontFamily={MONO} fontSize={21}
              fontWeight={700} fill={P.ink} opacity={0.75} letterSpacing={1}>APPROVED USE</text>
        <text x={770} y={676} textAnchor="middle" fontFamily={MONO} fontSize={21}
              fontWeight={700} fill={P.ink} opacity={0.75} letterSpacing={1}>APPROVED USE</text>
        <Recess x={310} y={840} w={244} label="EQUIPMENT" f={f} />
        <Recess x={770} y={840} w={244} label="PURCHASES" f={f} />
        <Recess x={540} y={1140} w={476} label="TRAINING" f={f} />
        <TypeSlug x={540} y={1102} f={f} text="ARTIFICIAL INTELLIGENCE" scale={0.9}
                  seated={1} phase={0} />
      </g>
      <Plate x={540} y={566} text="NOT IN THE BUYING" size={46} delay={18} />
      {last > 0.2 && <Plate x={540} y={1246} text="IN THE TEACHING" size={40} delay={144} />}
    </Stage>
  );
};

// -------------------------------------------------------------------- assembly
const Grade: React.FC = () => {
  const f = useCurrentFrame();
  return <GradeLayer f={f} bloom={0.08} vignette={0.16} grain={0.04} warmth={0.02} />;
};

const Captions: React.FC<{captions: Ep0808Props['captions']}> = ({captions}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  const cue = captions.find((c) => t >= c.start && t < c.end + 0.05);
  if (!cue) return null;
  const local = f - Math.round(cue.start * fps);
  const pop = spring({frame: local, fps, config: {damping: 9, stiffness: 130}});
  const scale = interpolate(pop, [0, 1], [0.88, 1], {extrapolateRight: 'clamp'});
  const rise = interpolate(pop, [0, 1], [20, 0], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', bottom: H - CAPTION_TOP - CAPTION_H, left: 0, right: 0, display: 'flex',
      justifyContent: 'center', padding: '0 60px'}}>
      <div style={{background: 'rgba(26,38,42,0.92)', borderRadius: 12, padding: '16px 30px',
        maxWidth: 940, border: `4px solid ${P.warm}`,
        transform: `translateY(${rise}px) scale(${scale})`, transformOrigin: 'center bottom'}}>
        <div style={{fontFamily: BOLD, fontWeight: 900, fontSize: 46, lineHeight: 1.12,
          color: '#fff', textAlign: 'center', letterSpacing: 0.5,
          textShadow: '2px 3px 0 rgba(0,0,0,0.65)'}}>{cue.text}</div>
      </div>
    </div>
  );
};

export const ep0808Schema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.object({frame: z.number(), word: z.string(), energy: z.number().optional(),
    lineIdx: z.number().optional()})).optional(),
});
export type Ep0808Props = z.infer<typeof ep0808Schema>;

const SCENES: React.FC[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14, S15];
// Fallback only. episode_props.json from scripts/build_scenes.py carries the
// authoritative per-run timing, retimed from the real vo_lines.json.
const DEFAULT_BOUNDS = [
  {from: 0, dur: 303}, {from: 303, dur: 183}, {from: 486, dur: 265}, {from: 751, dur: 366},
  {from: 1117, dur: 265}, {from: 1382, dur: 423}, {from: 1805, dur: 315}, {from: 2120, dur: 145},
  {from: 2265, dur: 145}, {from: 2410, dur: 265}, {from: 2675, dur: 183}, {from: 2858, dur: 170},
  {from: 3028, dur: 309}, {from: 3337, dur: 107}, {from: 3444, dur: 342},
];

export const Ep0808: React.FC<Ep0808Props> = ({captions, scenes, mouth, accents}) => {
  const bounds = scenes && scenes.length === SCENES.length ? scenes : DEFAULT_BOUNDS;
  const voice = mouth && mouth.length ? {fps: 30, mouth, accents: accents ?? []} : null;
  return (
    <AbsoluteFill style={{backgroundColor: P.wallDeep}}>
      <VoiceProvider data={voice}>
        {SCENES.map((C, i) => (
          <Sequence key={i} from={bounds[i].from} durationInFrames={bounds[i].dur} name={`S${i + 1}`}>
            <C />
          </Sequence>
        ))}
        <Grade />
        <Captions captions={captions} />
      </VoiceProvider>
    </AbsoluteFill>
  );
};
