import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Sourdough, Cell, BoxLabel, StatBurst} from './lib/kit';
import {Character} from './lib/Character';
import {NightGrade, GradeLayer, tones, FormGradient, RimLight, ContactShadow} from './lib/lighting';
import {entrance, vitals} from './lib/motion';
import {PaperFiber} from './lib/paper';

// =============================================================================
// DISPATCH 2026-07-29 — "Alaska got written into America's AI moonshot"
//
// Storyboard: out/dispatch/storyboard.json   Art direction: out/dispatch/art_direction.json
//
// THE BINDING PALETTE RULE (art_direction.json craft_advance): light is EMITTED, never
// received. AMBER means an Alaskan generator is running. TEAL means a machine is reading
// in real time. Every amber pool in this film is a REGISTERED NightGrade source, so a lit
// window always means a generator. Nothing is lit decoratively.
// =============================================================================

const INK = '#080D18';
const SKY = '#101A2E';
const GROUND = '#1B2740';
const AMBER = '#F2B33D';
const AMBER_D = '#B87A18';
const TEAL = '#4FD6C8';
const GREY_ROW = '#39424F';
const BOLD = 'Fraunces, Georgia, serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

/** the 4:5 LinkedIn crop is the deliverable — every load-bearing element lives inside this box */
const SAFE_TOP = 285;
const SAFE_BOT = 1635;

const Stage: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{backgroundColor: SKY}}>
    <svg viewBox="0 0 1080 1920" width="1080" height="1920">
      <defs><PaperFiber id="fib" /></defs>
      {children}
    </svg>
  </AbsoluteFill>
);

/* ---------------------------------------------------------------------------
   S1 — THE LINE. Insert, high angle, static camera. All motion is rows stamping
   into the page. Frame 0 must be a dead-legible printed line for the poster grade.
--------------------------------------------------------------------------- */
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ROWS = 11;
  return (
    <Stage>
      <rect x={0} y={0} width={1080} height={1920} fill={INK} />
      {/* the sheet, with real body */}
      <g transform="translate(40,330)">
        <rect x={10} y={14} width={1000} height={1210} fill="#000" opacity={0.55} />
        <rect x={0} y={0} width={1000} height={1210} fill="#E7E1D4" stroke={INK} strokeWidth={4} />
        <rect x={0} y={0} width={1000} height={1210} fill="url(#fib)" opacity={0.5} />
        {/* the lamp pool falls ON the page, so the light is a physical thing */}
        <ellipse cx={500} cy={548} rx={430} ry={330} fill={AMBER} opacity={0.16} />
        <ellipse cx={500} cy={548} rx={300} ry={225} fill={AMBER} opacity={0.13} />
        {/* hairline column rules — the hard orthogonal grid of the record */}
        {[76, 700, 866].map((x) => (
          <line key={x} x1={x} y1={30} x2={x} y2={1180} stroke={GREY_ROW} strokeWidth={2} opacity={0.5} />
        ))}
        {Array.from({length: ROWS}).map((_, i) => {
          const e = entrance(f, fps, 4 + i * 3, {drop: 26, anticipation: false});
          const isHero = i === 5;
          const y = 70 + i * 104;
          const lift = isHero ? -6 - 2 * Math.sin(f / 18) : 0;
          return (
            <g key={i} opacity={e.on ? 1 : 0} transform={`translate(0,${e.dy + lift})`}>
              {isHero && <rect x={30} y={y - 34} width={940} height={78} fill={AMBER} opacity={0.5} rx={5} />}
              {isHero && <rect x={30} y={y + 44} width={940} height={9} fill={INK} opacity={0.3} />}
              <line x1={30} y1={y + 52} x2={970} y2={y + 52} stroke={GREY_ROW} strokeWidth={2} opacity={0.3} />
              <text x={100} y={y + 16} fontFamily={MONO} fontSize={isHero ? 42 : 28} fontWeight={isHero ? 700 : 400}
                fill={isHero ? '#241703' : GREY_ROW} opacity={isHero ? 1 : 0.45}>
                {isHero ? 'AURORA-AI' : `PROJECT ${String(i * 17 + 31).padStart(3, '0')}`}
              </text>
              <text x={720} y={y + 14} fontFamily={MONO} fontSize={isHero ? 30 : 21} fontWeight={isHero ? 700 : 400}
                fill={isHero ? '#241703' : GREY_ROW}
                opacity={isHero ? 1 : 0.35}>{isHero ? 'ALASKA' : ['CO', 'NM', 'IL', 'CA', 'TN', '', 'WA', 'NY', 'TX', 'MA', 'OH'][i]}</text>
            </g>
          );
        })}
      </g>
      {/* the single lamp — a REGISTERED source, so the light means something */}
      <NightGrade f={f} color="#0B1524" amount={0.94} floor={0.72} horizon={0.08}
        sources={[{x: 540, y: 878 + 3 * Math.sin(f / 18), r: 470, color: AMBER, intensity: 0.95}]} />
      <GradeLayer f={f} bloom={0.4} vignette={0.72} grain={0.07} warmth={0.1} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S2 — THE GENESIS MACHINE. Wide, eye level, truck across. The national scale
   that Alaska is one line inside of. Parts fly in and lock together.
--------------------------------------------------------------------------- */
const S2: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const truck = interpolate(f, [0, 300], [40, -40], {extrapolateRight: 'clamp'});
  const t = tones('#243247');
  return (
    <Stage>
      <rect x={0} y={0} width={1080} height={1920} fill={SKY} />
      <defs><FormGradient id="gm" t={t} /></defs>
      <rect x={0} y={1500} width={1080} height={420} fill={GROUND} />
      <g transform={`translate(${540 + truck},1020)`}>
        {/* three racks assembling */}
        {[-250, 0, 250].map((dx, i) => {
          const e = entrance(f, fps, 10 + i * 14, {drop: 260});
          return (
            <g key={dx} transform={`translate(${dx},${e.dy}) scale(${e.sx},${e.sy})`}>
              <ContactShadow cx={0} cy={330} rx={110} ry={20} opacity={0.34} blur={10} />
              <rect x={-96} y={-300} width={192} height={630} fill="url(#gm)" stroke={INK} strokeWidth={7} rx={10} />
              {Array.from({length: 9}).map((_, k) => (
                <g key={k}>
                  <rect x={-74} y={-270 + k * 66} width={148} height={44} fill="#151E2C" stroke={INK} strokeWidth={3} rx={4} />
                  <circle cx={-52} cy={-248 + k * 66} r={6}
                    fill={(f + k * 7 + i * 13) % 40 < 22 ? TEAL : '#1D2836'} />
                  {[0, 1, 2, 3].map((v) => (
                    <line key={v} x1={-16 + v * 16} y1={-262 + k * 66} x2={-16 + v * 16} y2={-236 + k * 66}
                      stroke="#2B3A4E" strokeWidth={3} opacity={0.7} />
                  ))}
                </g>
              ))}
            </g>
          );
        })}
        {/* the quantum bell jar — lights and pulses */}
        <g transform="translate(0,-420)" opacity={entrance(f, fps, 66, {drop: 0}).on ? 1 : 0}>
          <ellipse cx={0} cy={96} rx={92} ry={18} fill={INK} opacity={0.3} />
          <path d="M-84,96 L-84,0 A84,84 0 0 1 84,0 L84,96 Z" fill="#16283A" stroke={INK} strokeWidth={7} opacity={0.92} />
          <circle cx={0} cy={22} r={34 + 5 * Math.sin(f / 9)} fill={TEAL} opacity={0.55} />
          <circle cx={0} cy={22} r={16} fill="#DFFBF6" />
        </g>
      </g>
      <BoxLabel x={540} y={SAFE_TOP + 90} text="GENESIS MISSION" w={620} h={96} fs={54} fill={AMBER} />
      <BoxLabel x={540} y={SAFE_BOT - 120} text="AI · SUPERCOMPUTING · QUANTUM" w={800} h={72} fs={34} fill="#E7E1D4" />
      <NightGrade f={f} color="#0C1A2C" amount={0.86} floor={0.5} horizon={0.3}
        sources={[{x: 540, y: 600, r: 320, color: TEAL, intensity: 0.5}]} />
      <GradeLayer f={f} bloom={0.55} vignette={0.6} grain={0.06} warmth={0.05} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S3 — THE TURN. Medium, LOW angle, static. Sourdough's furnace dims and the
   frame loses its key light with him. The emptiest frame in the film.
--------------------------------------------------------------------------- */
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  // the dim IS the motion of this shot
  const glow = interpolate(f, [26, 96], [1, 0.1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const slots = [0, 1, 2].map((i) => entrance(f, fps, 110 + i * 22, {drop: 30}));
  return (
    <Stage>
      <rect x={0} y={0} width={1080} height={1920} fill={INK} />
      <rect x={0} y={1520} width={1080} height={400} fill="#121B2A" />
      {/* low angle: the hero sits high in frame and we look up past his plinth */}
      <g transform="translate(540,1300) scale(1.95)">
        <Sourdough frame={f} emotion={glow < 0.45 ? 'faltering' : 'proud'} glow={glow} />
      </g>
      {/* three empty label slots — the absence made countable */}
      {slots.map((e, i) => (
        <g key={i} opacity={e.on ? 1 : 0} transform={`translate(0,${e.dy})`}>
          <rect x={190} y={1500 + i * 92} width={700} height={70} rx={8}
            fill="none" stroke={GREY_ROW} strokeWidth={4} strokeDasharray="14 12" />
          <text x={214} y={1548 + i * 92} fontFamily={MONO} fontSize={30} fill={GREY_ROW} opacity={0.8}>
            {['NO ABSTRACT', 'NO BUDGET', 'NO COVERAGE WE COULD FIND'][i]}
          </text>
        </g>
      ))}
      <NightGrade f={f} color="#070C16" amount={1} floor={0.82} horizon={0.06}
        sources={glow > 0.12 ? [{x: 540, y: 1180, r: 300 * glow, color: AMBER, intensity: 0.9 * glow}] : []} />
      <GradeLayer f={f} bloom={0.3} vignette={0.85} grain={0.08} warmth={0.04} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S4 — HUNDREDS OF SEPARATE GRIDS. Extreme wide, overhead, crane down.
   Nodes ignite ONE BY ONE with no lines drawn between them. That absence is the point.
--------------------------------------------------------------------------- */
const NODES: [number, number][] = [
  [300, 980], [372, 1044], [255, 1090], [430, 950], [500, 1030], [568, 962], [640, 1024],
  [352, 1160], [455, 1136], [545, 1188], [618, 1120], [700, 1180], [742, 1078], [806, 1140],
  [270, 1216], [352, 1272], [470, 1266], [596, 1284], [688, 1250], [790, 1230], [860, 1188],
  [318, 890], [402, 856], [498, 900], [590, 866], [676, 920], [760, 986], [836, 1044],
];
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const crane = interpolate(f, [0, 240], [1.1, 1.0], {extrapolateRight: 'clamp'});
  return (
    <Stage>
      <rect x={0} y={0} width={1080} height={1920} fill="#070E1C" />
      <g transform={`translate(540,1120) scale(${crane}) translate(-540,-1120)`}>
        {/* simplified honest Alaska landmass, near-black */}
        <path d="M232,1046 L286,952 L360,900 L452,860 L560,846 L664,872 L742,922 L812,982 L878,1052
                 L900,1130 L862,1214 L790,1272 L690,1308 L580,1326 L470,1316 L372,1292 L292,1250
                 L244,1180 L226,1112 Z"
          fill="#131D2E" stroke="#22314A" strokeWidth={4} />
        {/* the Aleutian tail */}
        <path d="M244,1180 L188,1236 L138,1272 L92,1292" fill="none" stroke="#22314A" strokeWidth={4} strokeLinecap="round" />
        {[188, 138, 92].map((x, i) => <circle key={x} cx={x} cy={[1236, 1272, 1292][i]} r={7} fill="#1B2436" />)}
        {NODES.map(([x, y], i) => {
          const on = f > 12 + i * 6;
          const age = f - (12 + i * 6);
          const pop = on ? Math.min(1, age / 8) : 0;
          return (
            <g key={i}>
              {on && <circle cx={x} cy={y} r={26 * pop} fill={AMBER} opacity={0.16} />}
              {on && <circle cx={x} cy={y} r={9 * pop} fill={AMBER} stroke={AMBER_D} strokeWidth={2} />}
            </g>
          );
        })}
      </g>
      <BoxLabel x={540} y={SAFE_TOP + 100} text="HUNDREDS OF SEPARATE GRIDS" w={880} h={92} fs={46} fill={AMBER} />
      <NightGrade f={f} color="#060B18" amount={0.95} floor={0.7} horizon={0.42}
        sources={NODES.filter((_, i) => f > 12 + i * 6).slice(0, 14)
          .map(([x, y]) => ({x, y, r: 90, color: AMBER, intensity: 0.3}))} />
      <GradeLayer f={f} bloom={0.6} vignette={0.7} grain={0.07} warmth={0.09} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S5 — CORDOVA AND ITS LIVE MODEL. Medium, eye level, two-up, dolly through.
   The real town in amber on the left, its teal wireframe copy on the right,
   moving in lockstep ONE FRAME APART so the twin reads as a copy keeping up.
--------------------------------------------------------------------------- */
const Town: React.FC<{f: number; wire?: boolean}> = ({f, wire = false}) => {
  const stroke = wire ? TEAL : INK;
  const fill = (c: string) => (wire ? 'none' : c);
  const v = vitals(f, 0.6, 1);
  return (
    <g>
      {/* hydro dam with penstock curve */}
      <path d="M-190,120 L-190,-40 Q-120,-96 -30,-96 L-30,120 Z" fill={fill('#26354B')} stroke={stroke} strokeWidth={6} />
      <path d="M-30,-70 Q60,-52 96,26" fill="none" stroke={stroke} strokeWidth={22} opacity={wire ? 0.9 : 1}
        strokeLinecap="round" />
      {!wire && <path d="M-30,-70 Q60,-52 96,26" fill="none" stroke="#3D4E68" strokeWidth={12} strokeLinecap="round" />}
      {/* powerhouse with lit windows */}
      <g transform="translate(120,60)">
        <rect x={-70} y={-46} width={150} height={106} fill={fill('#2B3B52')} stroke={stroke} strokeWidth={6} rx={5} />
        {[0, 1, 2].map((i) => (
          <rect key={i} x={-52 + i * 44} y={-24} width={30} height={30}
            fill={wire ? 'none' : ((f + i * 9) % 70 < 58 ? AMBER : '#3A2C10')} stroke={stroke} strokeWidth={3} />
        ))}
      </g>
      {/* spillway water */}
      {!wire && <path d={`M96,34 q14,${26 + 3 * Math.sin(f / 7)} 4,54`} fill="none" stroke="#4E7FA6" strokeWidth={9}
        strokeLinecap="round" opacity={0.8} />}
      <g transform={`translate(0,${v.bob})`}>
        {wire && NODEDOTS.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={4} fill={TEAL} />)}
      </g>
    </g>
  );
};
const NODEDOTS: [number, number][] = [
  [-190, 120], [-190, -40], [-30, -96], [-30, 120], [96, 26], [50, 14], [190, 60], [190, 120], [50, 120],
];

const S5: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const dolly = interpolate(f, [0, 300], [0.96, 1.05], {extrapolateRight: 'clamp'});
  const build = Math.min(1, Math.max(0, (f - 12) / 54));
  const plate = entrance(f, fps, 60, {drop: 44});
  return (
    <Stage>
      <rect x={0} y={0} width={1080} height={1920} fill={SKY} />
      <rect x={0} y={1400} width={1080} height={520} fill={GROUND} />
      {/* hard centre seam — this is a two-up, not a blend */}
      <line x1={540} y1={640} x2={540} y2={1180} stroke="#2A3550" strokeWidth={5} opacity={0.5} />
      <g transform={`translate(306,1000) scale(${dolly * 1.0})`}>
        <Town f={f} />
        <g transform="translate(150,150) scale(0.5)"><Cell frame={f} chargeLevel={2} /></g>
        <g transform="translate(-150,150) scale(0.42)">
          <Character frame={f} pose="stand" emotion="neutral" outfit="flannel" headgear="beanie" />
        </g>
      </g>
      {/* the twin lags the real town by exactly one frame */}
      <g transform={`translate(774,1000) scale(${dolly * 1.0})`} opacity={build}>
        <g clipPath="none">
          <Town f={f - 1} wire />
        </g>
        {/* scan sweep crawling down the wireframe */}
        <rect x={-215} y={-120 + ((f * 5) % 300)} width={430} height={4} fill={TEAL} opacity={0.6} />
      </g>
      <g opacity={plate.on ? 1 : 0} transform={`translate(0,${plate.dy})`}>
        <BoxLabel x={306} y={1262} text="CORDOVA · 2,600" w={430} h={76} fs={32} fill={AMBER} />
        <BoxLabel x={774} y={1262} text="LIVE MODEL" w={330} h={76} fs={32} fill={TEAL} />
        <BoxLabel x={540} y={SAFE_TOP + 78} text="$6.2M · SEPARATE PROJECT" w={660} h={78} fs={32} fill="#E7E1D4" />
      </g>
      <NightGrade f={f} color="#0A1320" amount={0.88} floor={0.55} horizon={0.3}
        sources={[{x: 300, y: 1180, r: 260, color: AMBER, intensity: 0.75},
          {x: 810, y: 1160, r: 210 * build, color: TEAL, intensity: 0.5 * build}]} />
      <GradeLayer f={f} bloom={0.5} vignette={0.62} grain={0.06} warmth={0.07} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S6 — THE SIGNATURE PULL-BACK. Close to extreme wide, high angle, rise with.
   From the readable AURORA-AI line back to one hairline among 200 rows.
--------------------------------------------------------------------------- */
const S6: React.FC = () => {
  const f = useCurrentFrame();
  // TRUE-SCALE PULL-BACK. Anchored on the hero row so the one legible line stays dead
  // centre while 199 others resolve around it. Ends at 0.9 so the PAGE EDGES are visible
  // and the frame reads as a bounded document rather than as wallpaper (draft-1 defect).
  const z = interpolate(f, [0, 150], [4.6, 0.9], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const ROWS = 200, rowH = 6, PAGE_X = 240, PAGE_W = 600, PAGE_Y = 300, heroIdx = 96;
  const heroY = PAGE_Y + heroIdx * rowH + 3;
  return (
    <Stage>
      <rect x={0} y={0} width={1080} height={1920} fill={INK} />
      <g transform={`translate(540,960) scale(${z}) translate(${-540},${-heroY})`}>
        {/* the sheet, with a real edge and a cast shadow so it sits ON a dark desk */}
        <rect x={PAGE_X + 8} y={PAGE_Y + 10} width={PAGE_W} height={ROWS * rowH + 44} fill="#000" opacity={0.6} />
        <rect x={PAGE_X} y={PAGE_Y} width={PAGE_W} height={ROWS * rowH + 44} fill="#E7E1D4" stroke={INK} strokeWidth={2} />
        <rect x={PAGE_X} y={PAGE_Y} width={PAGE_W} height={ROWS * rowH + 44} fill="url(#fib)" opacity={0.35} />
        <line x1={PAGE_X + 430} y1={PAGE_Y + 12} x2={PAGE_X + 430} y2={PAGE_Y + ROWS * rowH + 32}
          stroke={GREY_ROW} strokeWidth={1} opacity={0.4} />
        {Array.from({length: ROWS}).map((_, i) => {
          const y = PAGE_Y + i * rowH + 22;
          if (i === heroIdx) {
            return (
              <g key={i}>
                <rect x={PAGE_X + 6} y={y - 8} width={PAGE_W - 12} height={rowH + 6} fill={AMBER} opacity={0.85} rx={1.5} />
                <text x={PAGE_X + 16} y={y - 1.6} fontFamily={MONO} fontSize={5.1} fontWeight={700} fill="#241703">
                  AURORA-AI · UNIV. OF ALASKA FAIRBANKS · AK
                </text>
              </g>
            );
          }
          return (
            <g key={i}>
              <rect x={PAGE_X + 16} y={y - 5} width={300 + ((i * 37) % 130)} height={1.9} fill={GREY_ROW} opacity={0.4} />
              <rect x={PAGE_X + 438} y={y - 5} width={26 + ((i * 19) % 34)} height={1.9} fill={GREY_ROW} opacity={0.3} />
            </g>
          );
        })}
      </g>
      <BoxLabel x={540} y={SAFE_TOP + 96} text="1 OF 200" w={420} h={100} fs={58} fill={AMBER} />
      <NightGrade f={f} color="#070C16" amount={0.9} floor={0.62} horizon={0.08}
        sources={[{x: 540, y: 960, r: Math.max(150, 300 * z), color: AMBER, intensity: 0.85}]} />
      <GradeLayer f={f} bloom={0.45} vignette={0.86} grain={0.07} warmth={0.08} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S7 — THE BUTTON. Wide, GROUND level, crane down + dolly through.
   The furnace flares back and the question sets beside him. Loops to the open.
--------------------------------------------------------------------------- */
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const glow = interpolate(f, [0, 34], [0.14, 1], {extrapolateRight: 'clamp'});
  const q = entrance(f, fps, 40, {drop: 40});
  const push = interpolate(f, [0, 200], [1.0, 1.06], {extrapolateRight: 'clamp'});
  return (
    <Stage>
      <rect x={0} y={0} width={1080} height={1920} fill={INK} />
      {/* ground-level camera: horizon sits low, we look slightly up */}
      <rect x={0} y={1580} width={1080} height={340} fill="#0F1826" />
      <g transform={`translate(540,1470) scale(${push * 1.5})`}>
        <Sourdough frame={f} emotion="proud" glow={glow} accent={0.4 + 0.3 * Math.sin(f / 11)} />
      </g>
      {/* embers rising — ambient life in the final held frame */}
      {Array.from({length: 14}).map((_, i) => {
        const p = ((f * 1.6 + i * 37) % 240) / 240;
        return <circle key={i} cx={430 + ((i * 61) % 230)} cy={1470 - p * 420} r={3.2}
          fill={AMBER} opacity={(1 - p) * 0.65} />;
      })}
      <g opacity={q.on ? 1 : 0} transform={`translate(0,${q.dy})`}>
        <StatBurst cx={540} cy={SAFE_TOP + 250} big="1 LINE" lines={['OF PUBLIC RECORD']} big_fs={92} />
        <BoxLabel x={540} y={SAFE_TOP + 470} text="WHAT'S IN IT?" w={640} h={110} fs={60} fill="#E7E1D4" />
      </g>
      <NightGrade f={f} color="#070C16" amount={0.95} floor={0.7} horizon={0.12}
        sources={[{x: 540, y: 1360, r: 360 * glow, color: AMBER, intensity: 0.95 * glow}]} />
      <GradeLayer f={f} bloom={0.55} vignette={0.75} grain={0.07} warmth={0.12} />
    </Stage>
  );
};

/* --------------------------------------------------------------------------- */
const Captions: React.FC<{captions: {start: number; end: number; text: string}[]}> = ({captions}) => {
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
    <div style={{position: 'absolute', bottom: 430, left: 0, right: 0, display: 'flex', justifyContent: 'center', padding: '0 60px'}}>
      <div style={{background: 'rgba(8,13,24,0.92)', borderRadius: 14, padding: '16px 30px', maxWidth: 940,
        border: `4px solid ${AMBER}`, transform: `translateY(${rise}px) scale(${scale})`, transformOrigin: 'center bottom'}}>
        <div style={{fontFamily: BOLD, fontWeight: 900, fontSize: 46, lineHeight: 1.12, color: '#fff', textAlign: 'center',
          letterSpacing: 0.4, textShadow: '2px 3px 0 rgba(0,0,0,0.7)'}}>{cue.text}</div>
      </div>
    </div>
  );
};

export const ep0729Schema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.object({frame: z.number(), word: z.string(), energy: z.number().optional(), lineIdx: z.number().optional()})).optional(),
});
export type Ep0729Props = z.infer<typeof ep0729Schema>;

const SCENES: React.FC[] = [S1, S2, S3, S4, S5, S6, S7];
const DEFAULT_BOUNDS = [
  {from: 0, dur: 258}, {from: 258, dur: 324}, {from: 582, dur: 252}, {from: 834, dur: 246},
  {from: 1080, dur: 306}, {from: 1386, dur: 204}, {from: 1590, dur: 240},
];

export const Ep0729: React.FC<Ep0729Props> = ({captions, scenes}) => {
  const bounds = scenes && scenes.length === SCENES.length ? scenes : DEFAULT_BOUNDS;
  return (
    <AbsoluteFill style={{backgroundColor: INK}}>
      {SCENES.map((C, i) => (
        <Sequence key={i} from={bounds[i].from} durationInFrames={bounds[i].dur} name={`S${i + 1}`}>
          <C />
        </Sequence>
      ))}
      <Captions captions={captions} />
    </AbsoluteFill>
  );
};
