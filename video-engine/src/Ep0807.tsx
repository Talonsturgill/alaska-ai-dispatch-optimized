import React from 'react';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {VoiceProvider, useVoice} from './lib/voice';
import {tones, FormGradient, RimLight, ContactShadow, GradeLayer, MotionBlur, INK} from './lib/lighting';
import {Character} from './lib/Character';
import {Salmon} from './lib/fauna';
import {FishingBoat} from './lib/vehicles';
import {vitals, EASE, anticipate} from './lib/motion';
import {SearchReticle, PendingMark, CandidateField, ConfidenceBloom, VisionGrid, ClaimChip, CYAN} from './lib/vision';

// ============================================================================
// THE BOAT, NOT THE BRAIN — Dispatch 2026-08-07
//
// A machine learning model finds the brain of each individual salmon, because
// that spot sits in a different place in every fish. That is real and was
// independently reported twice. The arrival of any of it in Alaska is one
// trade write-up against more than 1,300 Cook Inlet permits.
//
// Board: out/dispatch/storyboard.json. Binding look: out/dispatch/art_direction.json.
// EXTERIOR, DAWN, ON WATER. The reticle cyan appears nowhere else in the film.
// ============================================================================

const BOLD = 'Archivo, Arial Black, Arial, sans-serif';
const MONO = 'JetBrains Mono, Consolas, monospace';
const W = 1080, H = 1920;

const P = {
  skyHi: '#e68a4f', sky: '#f2c77a', haze: '#dcae7e',
  water: '#2e5d57', waterDeep: '#16302e', foam: '#bfd3cb',
  deck: '#8fa9a2', alu: '#c9d3d6', steel: '#7d8b93',
  carmine: '#b4372f', brass: '#a9793c', wood: '#8a5f36',
  paper: '#f2ece0', shadow: '#16211f',
};

const ramp = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

// ------------------------------------------------------------------ backdrop
/** Dawn sky + sea. ALWAYS moving: haze bands drift, glints crawl, swell breathes. */
const SeaBG: React.FC<{f: number; horizon?: number; parallax?: number; sun?: number}> = ({
  f, horizon = 1180, parallax = 0, sun = 1,
}) => (
  <g>
    <defs>
      <linearGradient id="skyG" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#7fa6b8" />
        <stop offset="52%" stopColor={P.sky} />
        <stop offset="100%" stopColor={P.skyHi} />
      </linearGradient>
      <linearGradient id="seaG" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#4a7d74" />
        <stop offset="60%" stopColor={P.water} />
        <stop offset="100%" stopColor={P.waterDeep} />
      </linearGradient>
    </defs>
    <rect x={-200} y={-400} width={W + 400} height={horizon + 400} fill="url(#skyG)" />
    {sun > 0 && (
      <g opacity={sun}>
        <circle cx={880} cy={horizon - 96} r={150} fill="#ffd9a0" opacity={0.22} />
        <circle cx={880} cy={horizon - 96} r={54} fill="#ffe7bd" />
      </g>
    )}
    {/* haze bands, irrational drift */}
    {[0, 1, 2, 3].map((i) => (
      <rect key={i} x={-300 + ((f * (0.32 + i * 0.14) + i * 260) % 1700) - 300}
            y={horizon - 320 + i * 62 - parallax * 0.1}
            width={1000} height={26 + i * 7} rx={13}
            fill="#ffffff" opacity={0.10 - i * 0.017} />
    ))}
    <rect x={-200} y={horizon} width={W + 400} height={H - horizon + 500} fill="url(#seaG)" />
    {/* sun glare column on the water */}
    <path d={`M840,${horizon} q60,${(H - horizon) * 0.5} -10,${H - horizon} l120,0 q60,${-(H - horizon) * 0.5} 10,${-(H - horizon)} Z`}
          fill="#ffd9a0" opacity={0.13} />
    {/* swell lines, always crawling */}
    {Array.from({length: 16}).map((_, i) => {
      const y = horizon + 16 + i * (i * 2.4 + 16);
      if (y > H + 120) return null;
      const ph = (f / (22 + i * 1.7)) + i;
      return (
        <path key={i}
              d={`M-160,${y + Math.sin(ph) * 3} q${240 + i * 12},${8 + Math.sin(ph * 1.3) * 5} ${520 + i * 20},0 t${520 + i * 20},0`}
              fill="none" stroke={P.foam} strokeWidth={1.6 + i * 0.16}
              opacity={0.09 + i * 0.012} />
      );
    })}
    {/* glints: deterministic, crawling */}
    {Array.from({length: 26}).map((_, i) => {
      const h = (Math.imul(i + 5, 2654435761) >>> 0) / 4294967295;
      const y = horizon + 30 + h * (H - horizon - 40);
      const x = ((h * 1400 + f * (0.5 + h)) % 1300) - 110;
      const tw = 0.35 + 0.65 * Math.abs(Math.sin(f / (9 + i % 7) + i));
      return <ellipse key={i} cx={x} cy={y} rx={9 + h * 13} ry={1.7} fill="#fff" opacity={0.30 * tw} />;
    })}
  </g>
);

/** Every scene sits in this. Continuous push + lateral drift + a live sea. */
const Stage: React.FC<{
  children: React.ReactNode; f: number; push?: number; drift?: number;
  horizon?: number; sun?: number;
}> = ({children, f, push = 0, drift = 1, horizon = 1180, sun = 1}) => {
  const dx = drift * 9 * Math.sin(f / 71.3);
  const dy = drift * 5 * Math.cos(f / 53.7);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <g transform={`translate(${W / 2 + dx},${H / 2 + dy}) scale(${1 + push}) translate(${-W / 2},${-H / 2})`}>
          <SeaBG f={f} horizon={horizon} parallax={push * 900} sun={sun} />
          {children}
        </g>
      </svg>
    </AbsoluteFill>
  );
};

// --------------------------------------------------------------- shared parts
const Plate: React.FC<{x: number; y: number; text: string; size?: number; delay?: number; tint?: string; op?: number}> = ({
  x, y, text, size = 44, delay = 0, tint = P.paper, op = 1,
}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: f - delay, fps, config: {damping: 13, stiffness: 160}});
  if (f < delay) return null;
  const w = text.length * size * 0.665 + 60;   // Archivo Black advance, not the mono 0.605
  return (
    <g transform={`translate(${x},${y}) scale(${interpolate(p, [0, 1], [0.88, 1])})`} opacity={p * op}>
      <rect x={-w / 2 + 5} y={-size * 0.8 + 7} width={w} height={size * 1.6} fill={INK} opacity={0.30} />
      <rect x={-w / 2} y={-size * 0.8} width={w} height={size * 1.6} fill={tint} stroke={INK} strokeWidth={4} />
      <rect x={-w / 2} y={-size * 0.8} width={w} height={size * 0.30} fill="#fff" opacity={0.26} />
      <text x={0} y={size * 0.34} textAnchor="middle" fontFamily={BOLD} fontWeight={900}
            fontSize={size} fill={INK} letterSpacing={0.6}>{text}</text>
    </g>
  );
};

/** The worn wooden ike jime spike. Grip point is the ORIGIN (DISPATCH_STANDARD §1). */
const Spike: React.FC<{x: number; y: number; rot?: number; s?: number; mark?: number; f?: number}> = ({
  x, y, rot = 0, s = 1, mark = 0, f = 0,
}) => {
  const t = tones(P.wood);
  return (
    <g transform={`translate(${x},${y}) rotate(${rot}) scale(${s})`}>
      <FormGradient id="spikeG" t={t} />
      {/* handle: tapered, worn, no straight machined edge anywhere */}
      <path d="M-14,0 q-5,-58 3,-98 q9,-16 20,-2 q9,40 5,100 q-15,7 -28,0 Z"
            fill="url(#spikeG)" stroke={INK} strokeWidth={5} strokeLinejoin="round" />
      <path d="M-9,-24 q11,5 21,0" stroke={INK} strokeWidth={2.4} opacity={0.34} fill="none" />
      <path d="M-8,-52 q10,4 19,0" stroke={INK} strokeWidth={2.2} opacity={0.28} fill="none" />
      <RimLight d="M-11,-96 q9,-16 20,-2" w={3.4} opacity={0.7} />
      {/* the steel point */}
      <path d="M-7,2 l7,58 l7,-58 Z" fill={P.steel} stroke={INK} strokeWidth={4} strokeLinejoin="round" />
      <path d="M0,6 l4,48" stroke="#fff" strokeWidth={2} opacity={0.5} />
      {mark > 0 && <SearchReticle x={0} y={64} f={f} lock={1} r={34} color="#f2c77a" />}
    </g>
  );
};

/** The gloved hand. Prop parents to THIS anchor, never eyeballed. */
const Glove: React.FC<{x: number; y: number; rot?: number; s?: number}> = ({x, y, rot = 0, s = 1}) => {
  const t = tones('#d8623a');
  return (
    <g transform={`translate(${x},${y}) rotate(${rot}) scale(${s})`}>
      <FormGradient id="glvG" t={t} />
      <path d="M-46,10 q-16,-40 6,-62 q26,-24 62,-14 q30,8 34,36 q4,30 -14,46 q-40,18 -88,-6 Z"
            fill="url(#glvG)" stroke={INK} strokeWidth={5.5} strokeLinejoin="round" />
      <path d="M-30,-30 q22,-14 46,-8" stroke={INK} strokeWidth={2.6} opacity={0.3} fill="none" />
      <path d="M-24,-12 q24,-12 50,-6" stroke={INK} strokeWidth={2.4} opacity={0.26} fill="none" />
      <RimLight d="M-40,-52 q26,-24 62,-14" w={4} opacity={0.65} />
      {/* cuff */}
      <path d="M-52,4 q-12,22 4,34 l40,10 q16,-18 6,-38 Z" fill={t.shade} stroke={INK} strokeWidth={5} />
    </g>
  );
};

/** Wet cutting board. Always has a contact shadow (DISPATCH_STANDARD §1). */
const Board: React.FC<{x: number; y: number; w?: number; h?: number}> = ({x, y, w = 720, h = 150}) => (
  <g transform={`translate(${x},${y})`}>
    <ContactShadow cx={0} cy={h / 2 + 8} rx={w / 2 + 20} ry={22} opacity={0.42} />
    <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={12} fill="#b9c4bd" stroke={INK} strokeWidth={6} />
    <rect x={-w / 2} y={-h / 2} width={w} height={22} rx={9} fill="#fff" opacity={0.22} />
    {Array.from({length: 9}).map((_, i) => (
      <line key={i} x1={-w / 2 + 30 + i * (w - 60) / 8} y1={-h / 2 + 16}
            x2={-w / 2 + 22 + i * (w - 60) / 8} y2={h / 2 - 16}
            stroke={INK} strokeWidth={1.6} opacity={0.13} />
    ))}
  </g>
);

/** The machine. Rectilinear, unlovable, one glass eye, no face. NET-NEW this run. */
const ReticleArm: React.FC<{
  x: number; y: number; s?: number; f: number; drop?: number; spike?: number; look?: number;
}> = ({x, y, s = 1, f, drop = 1, spike = 0, look = 0}) => {
  const t = tones(P.alu);
  const st = tones(P.steel);
  const headY = interpolate(drop, [0, 1], [-210, 0], {extrapolateRight: 'clamp'});
  const sway = 6 * Math.sin(f / 24.3) * (1 - drop * 0.6);
  return (
    <g transform={`translate(${x},${y}) scale(${s})`}>
      <FormGradient id="armG" t={t} />
      <FormGradient id="armS" t={st} />
      <ContactShadow cx={0} cy={196} rx={168} ry={26} opacity={0.4} />
      {/* base + upright rail: parallel, machined, fasteners visible */}
      <rect x={-150} y={150} width={300} height={46} rx={5} fill="url(#armG)" stroke={INK} strokeWidth={6} />
      {[-110, -60, 60, 110].map((cx) => (
        <circle key={cx} cx={cx} cy={173} r={7} fill={P.steel} stroke={INK} strokeWidth={3} />
      ))}
      <rect x={-132} y={-244} width={54} height={398} fill="url(#armS)" stroke={INK} strokeWidth={6} />
      <rect x={-132} y={-244} width={16} height={398} fill="#fff" opacity={0.14} />
      {[-200, -130, -60, 10, 80].map((cy) => (
        <line key={cy} x1={-132} y1={cy} x2={-78} y2={cy} stroke={INK} strokeWidth={2.4} opacity={0.35} />
      ))}
      {/* cross beam + carriage */}
      <g transform={`translate(0,${headY})`}>
        <rect x={-108} y={-232} width={252} height={44} fill="url(#armG)" stroke={INK} strokeWidth={6} />
        <rect x={-108} y={-232} width={252} height={13} fill="#fff" opacity={0.2} />
        {/* the lens head: ONE glass eye, real specular */}
        <g transform={`translate(96,-150) rotate(${look * 8 + sway * 0.2})`}>
          <rect x={-52} y={-56} width={104} height={104} rx={8} fill="url(#armG)" stroke={INK} strokeWidth={6} />
          <circle cx={0} cy={4} r={38} fill="#1d2b30" stroke={INK} strokeWidth={5} />
          <circle cx={0} cy={4} r={26} fill="#0e1a1e" />
          <circle cx={0} cy={4} r={24} fill="none" stroke={CYAN} strokeWidth={2.2} opacity={0.55} />
          <ellipse cx={-12} cy={-9} rx={11} ry={7} fill="#fff" opacity={0.62} transform="rotate(-28)" />
          <rect x={-52} y={-56} width={104} height={12} fill={P.brass} opacity={0.75} />
        </g>
        {/* the spike carriage */}
        <g transform={`translate(-6,${-120 + spike * 92})`}>
          <rect x={-26} y={-46} width={52} height={70} rx={4} fill="url(#armS)" stroke={INK} strokeWidth={5} />
          <path d="M-6,24 l6,54 l6,-54 Z" fill={P.steel} stroke={INK} strokeWidth={4} />
        </g>
        {/* cable loom: secondary motion, swings AFTER the arm */}
        <path d={`M-96,-210 q${40 + sway * 2.2},${74 + sway * 1.4} ${86},${104}`}
              fill="none" stroke={INK} strokeWidth={7} opacity={0.75} strokeLinecap="round" />
        <path d={`M-96,-210 q${34 + sway * 2.6},${80 + sway * 1.7} ${78},${112}`}
              fill="none" stroke={P.brass} strokeWidth={3.4} opacity={0.55} strokeLinecap="round" />
      </g>
    </g>
  );
};

// ====================================================================== S1 HOOK
// The held breath. The spike hovers and does NOT descend. Loop 1 plants here.
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const push = ramp(f, 0, 300) * 0.055;
  const markIn = ramp(f, 22, 52);
  // the hand is HOLDING, which is an act, so it must tremble rather than sit
  const hover = Math.sin(f / 17) * 5 + Math.sin(f / 4.3) * 1.6;
  const tremor = Math.sin(f / 5.7) * 0.9 + Math.sin(f / 3.1) * 0.5;
  return (
    <Stage f={f} push={push} drift={0.5} horizon={860} sun={0.22}>
      <Board x={540} y={1258} w={1140} h={210} />
      <g transform={`translate(0,${vitals(f, 1, 1).bob * 0.5}) scale(1,${vitals(f, 1, 1).breath})`}
         style={{transformOrigin: '520px 1198px'}}>
        <Salmon x={520} y={1198} scale={2.5} f={f} spawning={false} swim={0.42} facing={1} />
      </g>
      {/* the human mark, drawn by eye, irregular, behind the eye */}
      <g opacity={markIn}>
        <path d="M742,1094 l52,58 M794,1094 l-52,58" stroke="#22303a" strokeWidth={9}
              strokeLinecap="round" opacity={0.9} />
      </g>
      {/* hand AND spike are ONE rig: the fist grips the handle, fingers close over it */}
      <g transform={`translate(770,${906 + hover}) rotate(${-13 + tremor})`}>
        <Spike x={0} y={44} rot={0} s={1.35} />
        <Glove x={-4} y={-6} rot={0} s={1.15} />
        {/* fingers closing over the handle, in the glove's own tone */}
        <path d="M-30,-8 q26,-16 54,-6 q6,16 -6,24 q-30,6 -48,-6 Z" fill="#c1552f"
              stroke={INK} strokeWidth={4} strokeLinejoin="round" />
        <ellipse cx={6} cy={16} rx={16} ry={5} fill={INK} opacity={0.32} />
      </g>
      <Plate x={540} y={520} text="WHERE DOES A FISH" size={62} delay={3} />
      <Plate x={540} y={628} text="KEEP ITS BRAIN" size={62} delay={9} />
      <Plate x={540} y={1240} text="A SPOT THE SIZE OF A PEA" size={38} delay={40} tint={P.paper} />
    </Stage>
  );
};

// ============================================== S2 IKE JIME, THE THREE STEPS
const S2: React.FC = () => {
  const f = useCurrentFrame();
  const st = [ramp(f, 6, 30), ramp(f, 38, 62), ramp(f, 70, 94)];
  const card = ramp(f, 116, 142);
  const skiff = ramp(f, 150, 176);
  const steps = [
    {t: 'SPIKE THE BRAIN', y: 700},
    {t: 'BLEED IT', y: 900},
    {t: 'THE SPINAL CORD', y: 1100},
  ];
  return (
    <Stage f={f} push={ramp(f, 0, 300) * 0.05} drift={0.7} horizon={430}>
      <Plate x={540} y={490} text="IKE JIME" size={72} delay={2} tint={P.brass} />
      {steps.map((s, i) => (
        <g key={i} opacity={st[i]} transform={`translate(${interpolate(st[i], [0, 1], [-70, 0])},0)`}>
          <rect x={150} y={s.y - 52} width={780} height={104} rx={8} fill={P.paper}
                stroke={INK} strokeWidth={5} />
          <rect x={150} y={s.y - 52} width={780} height={16} fill={P.carmine} opacity={0.8} />
          <circle cx={220} cy={s.y + 6} r={30} fill={P.brass} stroke={INK} strokeWidth={4} />
          <text x={220} y={s.y + 18} textAnchor="middle" fontFamily={BOLD} fontWeight={900}
                fontSize={36} fill={INK}>{i + 1}</text>
          <text x={278} y={s.y + 18} fontFamily={BOLD} fontWeight={900} fontSize={40} fill={INK}>{s.t}</text>
          {/* the bleed channel actually runs on step 2 */}
          {i === 1 && (
            <g opacity={st[1]}>
              <rect x={700} y={s.y - 14} width={200} height={10} rx={5} fill={P.carmine} opacity={0.55} />
              <rect x={700 + ((f * 5) % 190)} y={s.y - 16} width={26} height={14} rx={7}
                    fill={P.carmine} opacity={0.9} />
            </g>
          )}
        </g>
      ))}
      {/* the cost of the skill, hand-lettered, lands crooked */}
      <g opacity={card} transform={`translate(330,1210) rotate(${interpolate(card, [0, 1], [-14, -6])})`}>
        <rect x={-268} y={-62} width={536} height={124} fill="#efe4cd" stroke={INK} strokeWidth={5} />
        <text x={0} y={-8} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={42} fill={INK}>TRAINED HAND</text>
        <text x={0} y={40} textAnchor="middle" fontFamily={MONO} fontSize={30} fill={INK} opacity={0.85}>YEARS</text>
      </g>
      <g opacity={skiff}>
        <FishingBoat x={830} y={1560} scale={0.34} f={f} heave={0.7} hull="#5b6f6a" />
        <Plate x={700} y={1690} text="ALMOST NOBODY ON A SMALL BOAT" size={30} delay={158} />
      </g>
    </Stage>
  );
};

// ============================================ S3 THE MACHINE + THE SPOT MOVES
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const drop = ramp(f, 8, 56);
  const look = ramp(f, 120, 156);
  return (
    <Stage f={f} push={ramp(f, 0, 260) * 0.06} drift={0.8} horizon={760}>
      <Board x={540} y={1400} w={860} h={150} />
      <Salmon x={520} y={1372} scale={1.1} f={f} spawning={false} swim={0.1} />
      <ReticleArm x={560} y={1180} s={1.02} f={f} drop={drop} look={look} />
      <Plate x={540} y={470} text="SHINKEI SYSTEMS" size={52} delay={16} />
      <Plate x={540} y={1240} text="THE SPOT MOVES" size={64} delay={118} tint={P.carmine} />
    </Stage>
  );
};

// ======================================= S4 THREE FISH, THREE DIFFERENT POINTS
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const rev = ramp(f, 30, 120);
  const rule = ramp(f, 158, 196);
  const plate = ramp(f, 8, 28);
  // THE THESIS: the true point sits at a different offset on each fish.
  const targets = [
    {x: 470, y: 700, tx: 604, ty: 662},
    {x: 470, y: 1120, tx: 566, ty: 1096},
    {x: 470, y: 1540, tx: 641, ty: 1494},
  ];
  return (
    <Stage f={f} push={ramp(f, 0, 280) * 0.045} drift={0.6} horizon={300} sun={0.35}>
      {/* a wet deck plane, not a flat fill: planking, grain and a wet sheen */}
      <g opacity={plate}>
        <rect x={40} y={520} width={1000} height={1180} rx={14} fill="#9fb0aa" stroke={INK} strokeWidth={6} />
        {Array.from({length: 8}).map((_, i) => (
          <line key={i} x1={40} y1={520 + (i + 1) * 131} x2={1040} y2={520 + (i + 1) * 131}
                stroke={INK} strokeWidth={2.2} opacity={0.16} />
        ))}
        {Array.from({length: 40}).map((_, i) => {
          const h = (Math.imul(i + 11, 2654435761) >>> 0) / 4294967295;
          return <ellipse key={`w${i}`} cx={70 + h * 940} cy={540 + ((h * 7919) % 1150)}
                          rx={5 + h * 13} ry={2.4} fill="#fff" opacity={0.10 + h * 0.10} />;
        })}
        <rect x={40} y={520} width={1000} height={30} fill="#fff" opacity={0.14} />
      </g>
      {[700, 1120, 1540].map((y, i) => (
        <Salmon key={y} x={470} y={y} scale={1.34 + i * 0.09} f={f + i * 40} spawning={false}
                swim={0.08} facing={1} />
      ))}
      <CandidateField targets={targets} f={f} reveal={rev} />
      {/* the ruler that predicts none of them */}
      <g opacity={rule} transform={`translate(${interpolate(rule, [0, 1], [220, 0])},0)`}>
        <rect x={846} y={620} width={58} height={960} fill={P.brass} stroke={INK} strokeWidth={5} />
        {Array.from({length: 19}).map((_, i) => (
          <line key={i} x1={846} y1={640 + i * 50} x2={i % 2 ? 878 : 896} y2={640 + i * 50}
                stroke={INK} strokeWidth={2.6} opacity={0.6} />
        ))}
        <Plate x={540} y={1240} text="OFF BY A LOT" size={34} delay={168} />
      </g>
      <Plate x={540} y={490} text="A DIFFERENT LOCATION" size={50} delay={12} />
    </Stage>
  );
};

// =============================================== S5 THE JIG COMES DOWN STRAIGHT
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const anti = anticipate(f, 44, 10);
  const dropS = spring({frame: f - 44, fps, config: {damping: 20, stiffness: 200}});
  const jigY = interpolate(dropS, [0, 1], [-360, 0]) - anti * 26;
  const hit = f > 46;
  const dent = hit ? Math.min(1, (f - 46) / 12) : 0;
  return (
    <Stage f={f} push={ramp(f, 0, 200) * 0.05} drift={0.4} horizon={520}>
      <Board x={540} y={1310} w={880} h={160} />
      <Salmon x={470} y={1282} scale={1.24} f={f} spawning={false} swim={0.06} />
      {/* the true mark sits where the jig will NOT land */}
      <SearchReticle x={676} y={1226} f={f} lock={1} r={34} />
      {/* the rails: parallel, machined, confident */}
      {[404, 900].map((x) => (
        <rect key={x} x={x} y={300} width={22} height={980} fill={P.steel} stroke={INK} strokeWidth={5} />
      ))}
      <g transform={`translate(0,${jigY})`}>
        <MotionBlur vy={hit ? 0 : 46}>
          <g>
            <rect x={360} y={880} width={600} height={78} fill={P.steel} stroke={INK} strokeWidth={6} />
            <rect x={360} y={880} width={600} height={18} fill="#fff" opacity={0.2} />
            {[430, 560, 690, 820].map((cx) => (
              <circle key={cx} cx={cx} cy={919} r={8} fill={P.alu} stroke={INK} strokeWidth={3} />
            ))}
            {/* the fixed guide: always the same relative spot */}
            <path d="M846,958 l-9,74 l18,0 Z" fill={P.steel} stroke={INK} strokeWidth={5} />
          </g>
        </MotionBlur>
      </g>
      {/* the miss: a real dent and splinter in the board, not a graphic */}
      {dent > 0 && (
        <g opacity={dent}>
          <ellipse cx={846} cy={1262} rx={20} ry={8} fill={INK} opacity={0.55} />
          <path d="M832,1256 l-16,-16 M862,1256 l17,-15" stroke={INK} strokeWidth={4} strokeLinecap="round" opacity={0.6} />
        </g>
      )}
      <Plate x={540} y={490} text="YOU CAN'T BUILD A JIG" size={52} delay={4} tint={P.carmine} />
      <Plate x={540} y={1240} text="IT NEVER MISSES ITS OWN TARGET" size={32} delay={58} />
    </Stage>
  );
};

// ============================================ S6 THE MACHINE'S VIEW, THE LOCK
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const lock = ramp(f, 74, 116);
  const bloom = ramp(f, 112, 150);
  return (
    <Stage f={f} push={ramp(f, 0, 240) * 0.07} drift={0.5} horizon={520} sun={0.5}>
      <g opacity={0.9}>
        <rect x={0} y={0} width={W} height={H} fill="#0f1c20" opacity={0.5} />
      </g>
      {/* the machine is IN its own shot, looking down into frame */}
      <g transform="translate(150,600) scale(1.15)">
        <ReticleArm x={420} y={280} s={0.92} f={f} drop={1} look={0.4} />
      </g>
      {/* a deck plane so the gantry stands on something and the frame has a floor */}
      <rect x={-40} y={1340} width={1160} height={26} fill="#6f8a84" stroke={INK} strokeWidth={5} opacity={0.9} />
      <rect x={-40} y={1366} width={1160} height={70} fill="#31504b" opacity={0.75} />
      <Salmon x={430} y={1120} scale={2.2} f={f} spawning={false} swim={0.14} />
      <VisionGrid f={f} op={0.16} />
      {/* the readout column: real structure, not texture */}
      <g opacity={0.92}>
        <rect x={790} y={880} width={244} height={470} rx={8} fill="#0d1a1e" stroke={CYAN}
              strokeWidth={2.4} opacity={0.9} />
        <rect x={790} y={880} width={244} height={40} fill={CYAN} opacity={0.22} />
        <text x={806} y={909} fontFamily={MONO} fontSize={22} fill={CYAN}>TARGET</text>
        {Array.from({length: 9}).map((_, i) => {
          const w = 40 + ((Math.imul(i + 4, 2654435761) >>> 0) % 150);
          const on = ramp(f, 30 + i * 9, 52 + i * 9);
          return (
            <g key={i} opacity={on}>
              <rect x={806} y={944 + i * 42} width={w} height={16} fill={CYAN} opacity={0.5} />
              <rect x={806} y={944 + i * 42} width={212} height={16} fill="none" stroke={CYAN}
                    strokeWidth={1.4} opacity={0.3} />
            </g>
          );
        })}
        <rect x={806} y={1320} width={212} height={4} fill={CYAN} opacity={0.6} />
      </g>
      <SearchReticle x={700} y={1068} f={f} lock={lock} r={104} label="LOCK" />
      <ConfidenceBloom x={700} y={1068} t={bloom} />
      <Plate x={540} y={490} text="LOOK AT EACH FISH" size={50} delay={6} />
      <Plate x={430} y={1300} text="THE LOOKING" size={60} delay={90} tint={P.brass} />
    </Stage>
  );
};

// ================================================= S7 THE INLET, DOTTED MARK
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const coast = ramp(f, 8, 62);
  const stamp = ramp(f, 74, 96);
  const dot = ramp(f, 118, 150);
  // Cook Inlet, simplified honestly: a long NE-SW trending inlet between two shores.
  const d = 'M300,470 L420,760 L470,1010 L520,1250 L610,1470 L700,1620 L640,1660 L520,1500 L430,1290 L370,1030 L318,770 L228,520 Z';
  // the land on either side, so the map is a PLACE and not a ribbon in a void
  const westLand = 'M-60,300 L250,470 L300,760 L360,1030 L420,1290 L510,1500 L620,1690 L560,1920 L-60,1920 Z';
  const eastLand = 'M470,300 L1140,300 L1140,1920 L740,1920 L680,1660 L620,1470 L540,1250 L490,1010 L440,760 Z';
  return (
    <Stage f={f} push={ramp(f, 0, 260) * 0.04} drift={0.6} horizon={260} sun={0.3}>
      <rect x={0} y={0} width={W} height={H} fill="#25423d" opacity={0.55} />
      <g opacity={coast}>
        {/* land masses with ridge structure, so the frame carries a subject edge to edge */}
        <path d={westLand} fill="#546b52" stroke={INK} strokeWidth={7} strokeLinejoin="round" />
        <path d={eastLand} fill="#4d6350" stroke={INK} strokeWidth={7} strokeLinejoin="round" />
        {Array.from({length: 14}).map((_, i) => (
          <path key={`w${i}`} d={`M${-40 + i * 12},${360 + i * 108} l${70 + (i % 4) * 40},${-46} l${64},${52}`}
                fill="none" stroke={INK} strokeWidth={4} opacity={0.45} />
        ))}
        {Array.from({length: 14}).map((_, i) => (
          <path key={`e${i}`} d={`M${760 + (i % 5) * 62},${340 + i * 110} l${58 + (i % 3) * 36},${-40} l${56},${46}`}
                fill="none" stroke={INK} strokeWidth={4} opacity={0.42} />
        ))}
        <path d={d} fill="#2f6a63" stroke={INK} strokeWidth={7} strokeLinejoin="round" />
        <path d={d} fill="none" stroke={P.foam} strokeWidth={2.6} opacity={0.55} />
        {/* current lines inside the inlet */}
        {Array.from({length: 9}).map((_, i) => (
          <path key={`c${i}`} d={`M${300 + i * 22},${540 + i * 118} q40,40 60,110`} fill="none"
                stroke={P.foam} strokeWidth={2} opacity={0.28} />
        ))}
      </g>
      <g opacity={stamp} transform={`translate(760,560) rotate(${interpolate(stamp, [0, 1], [-16, -7])})`}>
        <rect x={-150} y={-46} width={300} height={92} fill="none" stroke={P.carmine} strokeWidth={8} />
        <text x={0} y={16} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={44}
              fill={P.carmine}>JULY 30TH</text>
      </g>
      {/* the fleet that is already out there, drawn as real objects on the water */}
      <g opacity={coast}>
        {[[352,760],[420,900],[386,1030],[470,1140],[440,1270],[520,1360],[492,1470],[566,1560]]
          .map(([bx, by], i) => (
            <g key={i} opacity={Math.max(0, Math.min(1, (coast - i * 0.06) * 3))}>
              <FishingBoat x={bx} y={by} scale={0.13 + (i % 3) * 0.035} f={f + i * 31}
                           heave={0.5 + (i % 2) * 0.2} hull={i % 2 ? '#5d6f5a' : '#4c6f68'} />
            </g>
          ))}
      </g>
      {/* named anchors, a scale bar and a north mark: structure, not texture */}
      <g opacity={ramp(f, 40, 72)}>
        {[['ANCHORAGE', 268, 560], ['KENAI', 640, 1140], ['HOMER', 700, 1610]].map(([t, tx, ty]) => (
          <g key={t as string} transform={`translate(${tx},${ty})`}>
            <circle r={11} fill={P.brass} stroke={INK} strokeWidth={4} />
            <rect x={16} y={-22} width={(t as string).length * 17 + 24} height={44}
                  fill={P.paper} stroke={INK} strokeWidth={3.6} />
            <text x={28} y={10} fontFamily={MONO} fontWeight={700} fontSize={24} fill={INK}>{t}</text>
          </g>
        ))}
        <g transform="translate(120,1740)">
          <rect x={0} y={0} width={240} height={12} fill={P.paper} stroke={INK} strokeWidth={3} />
          <rect x={0} y={0} width={120} height={12} fill={INK} />
          <text x={0} y={44} fontFamily={MONO} fontSize={22} fill={P.paper} opacity={0.9}>50 MILES</text>
        </g>
        <g transform="translate(960,560)">
          <path d="M0,-46 L15,16 L0,4 L-15,16 Z" fill={P.paper} stroke={INK} strokeWidth={4} />
          <text x={0} y={48} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={26}
                fill={P.paper}>N</text>
        </g>
      </g>
      <PendingMark x={470} y={1120} f={f} r={150} op={dot} label="COMPANY SAYS" />
      <Plate x={540} y={490} text="COOK INLET" size={58} delay={4} />
    </Stage>
  );
};

// ===================================================== S8 THE CLAIM LEDGER
const S8: React.FC = () => {
  const f = useCurrentFrame();
  const rows = [ramp(f, 2, 18), ramp(f, 20, 36), ramp(f, 38, 54)];
  const tag = ramp(f, 86, 112);
  const swing = Math.sin(f / 13) * 7 * (1 - tag * 0.3);
  return (
    <Stage f={f} push={ramp(f, 0, 200) * 0.035} drift={0.5} horizon={340} sun={0.4}>
      <rect x={0} y={0} width={W} height={H} fill="#1b2f2c" opacity={0.5} />
      {/* the thing being claimed about, standing behind its own claims */}
      <g opacity={0.55}>
        <ReticleArm x={560} y={1150} s={1.7} f={f} drop={1} look={0} />
      </g>
      {/* a dock plane so the chips sit ON something */}
      <rect x={60} y={470} width={960} height={1000} rx={12} fill="#22403b" stroke={INK}
            strokeWidth={5} opacity={0.85} />
      {Array.from({length: 7}).map((_, i) => (
        <line key={i} x1={60} y1={470 + (i + 1) * 125} x2={1020} y2={470 + (i + 1) * 125}
              stroke={INK} strokeWidth={2} opacity={0.18} />
      ))}
      <ClaimChip x={540} y={640} text="NEARLY 60% SMALLER" sub="COMPANY SAYS" op={rows[0]} w={720} />
      <ClaimChip x={540} y={820} text="THE ROBOT'S FREE" sub="COMPANY SAYS" op={rows[1]} w={720} />
      <ClaimChip x={540} y={1000} text="BOUGHT AT A PREMIUM" sub="COMPANY SAYS" op={rows[2]} w={720} />
      {/* the price tag whose number never prints */}
      <g opacity={tag} transform={`translate(540,1290) rotate(${swing})`}>
        <line x1={0} y1={-120} x2={0} y2={-56} stroke={INK} strokeWidth={4} />
        <path d="M-160,-56 l320,0 l0,180 l-160,44 l-160,-44 Z" fill={P.paper} stroke={INK} strokeWidth={6} />
        <circle cx={0} cy={-30} r={11} fill="none" stroke={INK} strokeWidth={4} />
        <line x1={-108} y1={64} x2={108} y2={64} stroke={INK} strokeWidth={4} opacity={0.45} />
        <text x={0} y={130} textAnchor="middle" fontFamily={MONO} fontSize={24} fill={INK} opacity={0.6}>NO FIGURE</text>
      </g>
      <Plate x={540} y={1240} text="NO NUMBER ANYWHERE" size={46} delay={98} tint={P.carmine} />
    </Stage>
  );
};

// ============================== S9 THE TEST: one boat, one bay. The warmest shot.
const S9: React.FC = () => {
  const f = useCurrentFrame();
  const crate = ramp(f, 30, 58);
  const plate = ramp(f, 132, 160);
  const quote = ramp(f, 196, 232);
  // the rig's own heave is a couple of px, which vanishes at this scale. Drive a real one.
  const lift = Math.sin(f / 19) * 54 + Math.sin(f / 11.7) * 21;
  const roll = Math.sin(f / 23) * 6.4;
  return (
    <Stage f={f} push={ramp(f, 0, 468) * 0.16} drift={2.2} horizon={1080} sun={1}>
      {/* far headland closing the bay */}
      <path d="M-40,1080 L180,930 L360,1010 L520,940 L700,1030 L900,960 L1120,1060 L1120,1090 L-40,1090 Z"
            fill="#3c5a58" stroke={INK} strokeWidth={4} opacity={0.85} />
      {/* the dock */}
      <g>
        <rect x={120} y={1330} width={840} height={26} fill="#7d6647" stroke={INK} strokeWidth={5} />
        {[200, 380, 560, 740, 900].map((x) => (
          <g key={x}>
            <rect x={x} y={1356} width={26} height={210} fill="#6b5539" stroke={INK} strokeWidth={4} />
            <rect x={x} y={1566} width={26} height={120} fill={INK} opacity={0.22} />
          </g>
        ))}
      </g>
      <g transform={`rotate(${roll},430,${1310 + lift})`}>
        <FishingBoat x={430} y={1310 + lift} scale={0.66} f={f} heave={1} hull="#4c6f68" />
      </g>
      {/* the water answers the hull: a wake band that breaks and reforms under it */}
      {Array.from({length: 5}).map((_, i) => (
        <path key={i}
              d={`M${250 + i * 26},${1392 + i * 17 + Math.sin(f / (13 + i * 2)) * 17} q80,${12 + Math.sin(f / 9 + i) * 14} 180,0`}
              fill="none" stroke={P.foam} strokeWidth={4} opacity={0.30 + i * 0.05} />
      ))}
      {/* the setnetter: looks at the crate, then out at the water. The only face in the film,
          placed at its warmest and fairest beat on purpose. */}
      <g opacity={ramp(f, 62, 92)}>
        <g transform={`translate(${884 + Math.sin(f / 31) * 17},${1322 + Math.sin(f / 21) * 11})
                       rotate(${Math.sin(f / 37) * 2.2},884,1322)`}>
          <Character frame={f} x={0} y={0} scale={0.86} pose="stand" emotion="neutral"
                     outfit="vest" headgear="cap" facing={-1} />
          {/* finish parity: the props beside this figure all carry a rim, so it must too */}
          <path d="M-26,-150 q26,-30 54,-4" fill="none" stroke="#ffe7bd" strokeWidth={4}
                opacity={0.55} strokeLinecap="round" />
          <path d="M-34,-96 q10,44 4,86" fill="none" stroke="#ffe7bd" strokeWidth={3.4}
                opacity={0.4} strokeLinecap="round" />
        </g>
        <ContactShadow cx={884} cy={1340} rx={62} ry={14} opacity={0.42} />   {/* stays planted: the shift is above the feet */}
      </g>
      {/* the crate: LANDS on the boards, with a contact shadow */}
      <g opacity={crate} transform={`translate(790,${1300 - (1 - crate) * 120})`}>
        <ContactShadow cx={0} cy={34} rx={72} ry={13} opacity={0.4} />
        <rect x={-64} y={-58} width={128} height={92} fill="#9a8256" stroke={INK} strokeWidth={5} />
        <line x1={-64} y1={-24} x2={64} y2={-24} stroke={INK} strokeWidth={3} opacity={0.5} />
        <text x={0} y={16} textAnchor="middle" fontFamily={MONO} fontSize={20} fill={INK} opacity={0.75}>PSDN-S</text>
      </g>
      <g opacity={plate}>
        <Plate x={540} y={470} text="THE FAIR CASE" size={58} delay={134} />
        <Plate x={540} y={578} text="ONE BOAT, ONE WRITE UP" size={36} delay={146} />
      </g>
      {/* the CTO quote, given the whole frame and a real beat */}
      <g opacity={quote}>
        <text x={540} y={860} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={44}
              fill="#fff" opacity={0.96}>"IF IT WORKS WHERE</text>
        <text x={540} y={920} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={44}
              fill="#fff" opacity={0.96}>PEOPLE ACTUALLY FISH"</text>
        <text x={540} y={978} textAnchor="middle" fontFamily={MONO} fontSize={24}
              fill="#ffe7bd" opacity={0.9} letterSpacing={2}>REED GINSBERG, CO-FOUNDER AND CTO</text>
      </g>
    </Stage>
  );
};

// ================================ S10 THE RECORD: one write-up, an empty rack
const S10: React.FC = () => {
  const f = useCurrentFrame();
  const seam = ramp(f, 6, 30);
  const page = ramp(f, 44, 74);
  const rack = ramp(f, 92, 124);
  const stamp = ramp(f, 168, 190);
  return (
    <Stage f={f} push={ramp(f, 0, 380) * 0.045} drift={0.5} horizon={420} sun={0.45}>
      <rect x={0} y={0} width={W} height={H} fill="#16302e" opacity={0.5} />
      {/* the hard seam */}
      <rect x={534} y={interpolate(seam, [0, 1], [-1920, 0])} width={12} height={1920} fill={P.brass} />
      {/* lit side: one printed write-up */}
      <g opacity={page} transform={`translate(270,${1000 - (1 - page) * 60}) rotate(-3)`}>
        <ContactShadow cx={0} cy={230} rx={150} ry={20} opacity={0.35} />
        <rect x={-160} y={-220} width={320} height={440} fill={P.paper} stroke={INK} strokeWidth={6} />
        <rect x={-130} y={-186} width={260} height={30} fill={INK} opacity={0.8} />
        {Array.from({length: 11}).map((_, i) => (
          <line key={i} x1={-130} y1={-130 + i * 30} x2={i % 3 === 2 ? 60 : 130} y2={-130 + i * 30}
                stroke={INK} strokeWidth={3} opacity={0.28} />
        ))}
        <text x={0} y={-96} textAnchor="middle" fontFamily={MONO} fontSize={19} fill={INK} opacity={0.8}>ONE WRITE UP</text>
      </g>
      {/* dark side: an empty masthead rack */}
      <g opacity={rack}>
        {[0, 1, 2, 3].map((i) => (
          <g key={i}>
            <rect x={620} y={700 + i * 250} width={380} height={200} fill="#0e1a1e"
                  stroke={INK} strokeWidth={5} />
            <rect x={620} y={700 + i * 250} width={380} height={14} fill={P.steel} opacity={0.4} />
            <line x1={620} y1={880 + i * 250} x2={1000} y2={880 + i * 250}
                  stroke={P.steel} strokeWidth={4} opacity={0.35} />
          </g>
        ))}
        <Plate x={810} y={620} text="NO ALASKA OUTLET" size={34} delay={110} />
      </g>
      <g opacity={stamp} transform={`translate(540,1190) rotate(-7)`}>
        <rect x={-232} y={-46} width={464} height={92} fill="none" stroke={P.carmine} strokeWidth={9} />
        <text x={0} y={16} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={44}
              fill={P.carmine}>NO BOAT COUNT</text>
      </g>
      <Plate x={540} y={490} text="WHAT'S ON THE WATER" size={48} delay={10} />
    </Stage>
  );
};

// ================================== S11 TEN AGAINST THIRTEEN HUNDRED (reveal)
const S11: React.FC = () => {
  const f = useCurrentFrame();
  const ten = ramp(f, 10, 50);
  const field = ramp(f, 76, 210);
  const slice = ramp(f, 214, 240);
  const count = Math.round(interpolate(field, [0, 1], [0, 1300]));
  const COLS = 34, ROWS = 40;
  return (
    <Stage f={f} push={ramp(f, 0, 320) * 0.05} drift={0.4} horizon={300} sun={0.3}>
      <rect x={0} y={0} width={W} height={H} fill="#122a27" opacity={0.62} />
      {/* the permit field builds outward around the ten */}
      <g opacity={0.95}>
        {Array.from({length: ROWS}).map((_, r) =>
          Array.from({length: COLS}).map((_, c) => {
            const i = r * COLS + c;
            const dcx = Math.abs(c - COLS / 2) / (COLS / 2);
            const dcy = Math.abs(r - ROWS / 2) / (ROWS / 2);
            const dist = Math.sqrt(dcx * dcx + dcy * dcy);
            const on = Math.max(0, Math.min(1, (field - dist * 0.85) * 3.2));
            if (on <= 0.02) return null;
            const rot = ((Math.imul(i + 3, 2654435761) >>> 0) % 100) / 100 * 8 - 4;
            return (
              <rect key={i} x={40 + c * 29} y={430 + r * 25} width={20} height={15} rx={2}
                    transform={`rotate(${rot},${50 + c * 29},${437 + r * 25})`}
                    fill="#4a6f68" stroke={INK} strokeWidth={1.4} opacity={0.30 + 0.5 * on} />
            );
          }),
        )}
      </g>
      {/* the ten, lit, staying lit and shrinking against the field */}
      <g opacity={ten}>
        {Array.from({length: 10}).map((_, i) => (
          <circle key={i} cx={392 + (i % 5) * 74} cy={1030 + Math.floor(i / 5) * 74} r={13}
                  fill={CYAN} opacity={0.95} />
        ))}
        <rect x={352} y={984} width={378} height={166} rx={8} fill="none" stroke={CYAN}
              strokeWidth={3} opacity={0.7} />
      </g>
      <Plate x={540} y={490} text="2024 GOAL: 10 MACHINES" size={38} delay={16} />
      <Plate x={540} y={596} text="COMPANY WIDE" size={32} delay={26} />
      <g opacity={field}>
        <Plate x={540} y={1240} text={`${count.toLocaleString()}+ PERMITS`} size={56} delay={80} tint={P.brass} />
      </g>
      <g opacity={slice}>
        <Plate x={540} y={1330} text="ABOUT 10% OF ALASKA" size={34} delay={244} />
      </g>
    </Stage>
  );
};

// ============================ S12 THE TURN (a dozen different hulls) + BUTTON
const S12: React.FC = () => {
  const f = useCurrentFrame();
  const rise = ramp(f, 10, 190);
  const button = ramp(f, 224, 262);
  const HULLS = [
    {x: 200, y: 1150, s: 0.20, h: '#4c6f68'}, {x: 540, y: 1215, s: 0.30, h: '#5d6f5a'},
    {x: 870, y: 1135, s: 0.18, h: '#3f6a72'}, {x: 320, y: 1390, s: 0.44, h: '#6b6350'},
    {x: 720, y: 1415, s: 0.33, h: '#4a5d6b'}, {x: 960, y: 1345, s: 0.26, h: '#57705f'},
    {x: 140, y: 1610, s: 0.58, h: '#42655e'}, {x: 545, y: 1655, s: 0.40, h: '#6a5f4a'},
    {x: 900, y: 1630, s: 0.52, h: '#3e5f66'}, {x: 285, y: 1835, s: 0.74, h: '#546b62'},
    {x: 745, y: 1865, s: 0.63, h: '#5f6a54'}, {x: 1010, y: 1790, s: 0.34, h: '#476a6a'},
  ];
  const markX = interpolate(rise, [0, 1], [300, 560]) + 46 * Math.sin(f / 41);
  const markY = interpolate(rise, [0, 1], [1210, 1380]) + 22 * Math.cos(f / 33);
  return (
    <Stage f={f} push={interpolate(rise, [0, 1], [0.14, -0.10])} drift={1.1} horizon={640}>
      <g opacity={1 - button}>
        {HULLS.map((b, i) => {
          // beam, freeboard and house are all varied per hull, because the line under this
          // shot is DIFFERENT DECK, DIFFERENT RAIL and one sprite repeated cannot say it
          const beam = 0.74 + ((i * 37) % 11) / 11 * 0.62;   // 0.74..1.36 wide
          const free = 0.82 + ((i * 53) % 7) / 7 * 0.44;     // 0.82..1.26 tall
          const house = i % 3;                                // 0 none, 1 low, 2 tall
          const mast = i % 4 === 1 || i % 4 === 2;
          return (
            <g key={i} opacity={Math.max(0, Math.min(1, (rise - i * 0.045) * 3))}>
              <g transform={`translate(${b.x},${b.y}) scale(${beam},${free}) translate(${-b.x},${-b.y})`}>
                <FishingBoat x={b.x} y={b.y} scale={b.s} f={f + i * 27}
                             heave={0.5 + (i % 4) * 0.14} hull={b.h} />
                {house > 0 && (
                  <rect x={b.x - 44 * b.s} y={b.y - (86 + house * 46) * b.s}
                        width={92 * b.s} height={(52 + house * 40) * b.s}
                        fill={b.h} stroke={INK} strokeWidth={4 * b.s} />
                )}
                {mast && (
                  <line x1={b.x + 58 * b.s} y1={b.y - 40 * b.s} x2={b.x + 58 * b.s}
                        y2={b.y - 196 * b.s} stroke={INK} strokeWidth={5 * b.s} />
                )}
              </g>
            </g>
          );
        })}
        {/* the mark, drifting, finding no seat */}
        <g>
          <SearchReticle x={markX} y={markY} f={f} lock={0.12} r={168} seed={4} />
          <Plate x={markX} y={markY + 232} text="IT FITS NONE OF THEM" size={40} delay={90} tint={P.carmine} />
        </g>
        <Plate x={540} y={470} text="DIFFERENT DECK, DIFFERENT RAIL" size={38} delay={70} />
      </g>
      {/* THE BUTTON: back to the opening frame, the mark now on the spike */}
      <g opacity={button}>
        {/* the SAME board AND the same fish, from frame one. The echo has to be unmistakable,
            so the only thing that changed is what is resting on the spike. */}
        <Board x={540} y={1180} w={1140} h={210} />
        <Salmon x={520} y={1120} scale={2.5} f={f} spawning={false} swim={0.12} facing={1} />
        {/* the human X, still on the board, never struck */}
        <path d="M742,1016 l52,58 M794,1016 l-52,58" stroke="#22303a" strokeWidth={9}
              strokeLinecap="round" opacity={0.85} />
        {/* the spike now LIES on the board, and the mark has come to rest on its tip */}
        <ContactShadow cx={430} cy={1258} rx={150} ry={18} opacity={0.42} />
        <g transform="translate(452,1218) rotate(90)">
          <Spike x={0} y={0} rot={0} s={1.5} mark={1} f={f} />
        </g>
        <Plate x={540} y={500} text="THE BRAIN WAS THE HARD PART" size={40} delay={232} />
        <Plate x={540} y={620} text="THE BOAT IS STILL OUT THERE" size={46} delay={248} tint={P.brass} />
      </g>
    </Stage>
  );
};

// -------------------------------------------------------------------- assembly
const Grade: React.FC = () => {
  const f = useCurrentFrame();
  return <GradeLayer f={f} bloom={0.12} vignette={0.22} grain={0.045} warmth={0.06} />;
};

const Captions: React.FC<{captions: Ep0807Props['captions']}> = ({captions}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  const cue = captions.find((c) => t >= c.start && t < c.end + 0.05);
  if (!cue) return null;
  const local = f - Math.round(cue.start * fps);
  const pop = spring({frame: local, fps, config: {damping: 9, stiffness: 130}});
  const scale = interpolate(pop, [0, 1], [0.86, 1], {extrapolateRight: 'clamp'});
  const rise = interpolate(pop, [0, 1], [22, 0], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', bottom: 452, left: 0, right: 0, display: 'flex',
      justifyContent: 'center', padding: '0 60px'}}>
      <div style={{background: 'rgba(18,28,30,0.90)', borderRadius: 14, padding: '16px 30px', maxWidth: 940,
        border: `4px solid ${P.brass}`, transform: `translateY(${rise}px) scale(${scale})`,
        transformOrigin: 'center bottom'}}>
        <div style={{fontFamily: BOLD, fontWeight: 900, fontSize: 46, lineHeight: 1.12, color: '#fff',
          textAlign: 'center', letterSpacing: 0.5, textShadow: '2px 3px 0 rgba(0,0,0,0.65)'}}>{cue.text}</div>
      </div>
    </div>
  );
};

export const ep0807Schema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.object({frame: z.number(), word: z.string(), energy: z.number().optional(),
    lineIdx: z.number().optional()})).optional(),
});
export type Ep0807Props = z.infer<typeof ep0807Schema>;

const SCENES: React.FC[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12];
const DEFAULT_BOUNDS = [
  {from: 0, dur: 312}, {from: 312, dur: 360}, {from: 672, dur: 240}, {from: 912, dur: 276},
  {from: 1188, dur: 180}, {from: 1368, dur: 228}, {from: 1596, dur: 264}, {from: 1860, dur: 192},
  {from: 2052, dur: 420}, {from: 2472, dur: 432}, {from: 2904, dur: 360}, {from: 3264, dur: 396},
];

export const Ep0807: React.FC<Ep0807Props> = ({captions, scenes, mouth, accents}) => {
  const bounds = scenes && scenes.length === SCENES.length ? scenes : DEFAULT_BOUNDS;
  const voice = mouth && mouth.length ? {fps: 30, mouth, accents: accents ?? []} : null;
  return (
    <AbsoluteFill style={{backgroundColor: P.waterDeep}}>
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
