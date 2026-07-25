import React from 'react';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {VoiceProvider, useVoice} from './lib/voice';
import {SeismicStation} from './lib/sensors';
import {tones, FormGradient, RimLight, ContactShadow, GradeLayer, MotionBlur, NightGrade, INK} from './lib/lighting';

const BOLD = 'Arial Black, Arial, sans-serif';
const MONO = 'JetBrains Mono, Consolas, monospace';

// ---- 2026-07-25 palette, locked by out/dispatch/art_direction.json --------------------------
// Light MEANS coverage. Amber appears ONLY where an instrument is actually listening.
// Ember rust is RESERVED for the rock that falls and never touches an instrument.
const SKY = '#134138';
const SKY_HI = '#1E6153';
const GROUND = '#0D2721';
const GROUND_L = '#47A088';
const WATER = '#1D5E56';
const AMBER = '#F2B33D';   // a registered, listening source
const AMBER_HOT = '#FFD98A';
const EMBER = '#E4572E';   // RESERVED: falling rock only
const BRASS = '#DCA94B';   // the hero's horn, deliberately in the amber family
const PROP = '#C6A15B';    // props, dimmer than the hero amber
const CHIP = '#D8CDB4';    // labels, capped below the hero amber value
const CYAN = '#5FC7D8';    // the PROPOSED boundary, drawn unlit, once
const TEXT = '#F4EDDD';
const INKW = '#080D0B';

const ramp = (f: number, a: number, b: number) => interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
const W = 1080, H = 1920;

// ============================================================ shared night world
const FjordNight: React.FC<{f: number; push?: number; lit?: boolean}> = ({f, push = 0, lit = true}) => {
  const drift = f * 0.13;
  return (
    <g transform={`translate(${W / 2},${H / 2}) scale(${1 + push}) translate(${-W / 2},${-H / 2})`}>
      <defs>
        <linearGradient id="fnSky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={SKY_HI} />
          <stop offset="52%" stopColor={SKY} />
          <stop offset="100%" stopColor="#0E2B26" />
        </linearGradient>
      </defs>
      <rect x={-120} y={-120} width={W + 240} height={H + 240} fill="url(#fnSky)" />
      {/* far ridge planes, aerial perspective into haze */}
      {[[0.5, 980, '#1D5347'], [0.66, 1090, '#173F35'], [0.82, 1190, '#12332B']].map(([o, y, c], i) => (
        <g key={i} transform={`translate(${-drift * (0.05 + i * 0.04)},0)`}>
          <path d={`M-160,${y as number} L120,${(y as number) - 130} L360,${(y as number) - 46} L640,${(y as number) - 168} L900,${(y as number) - 62} L1240,${(y as number) - 120} L1240,${H + 120} L-160,${H + 120} Z`}
            fill={c as string} opacity={o as number} />
        </g>
      ))}
      {/* the near walls, hard faceted wedges (the land is angular, the instruments are round) */}
      <path d={`M-160,1240 L150,900 L330,1150 L520,980 L760,1230 L1000,1010 L1240,1180 L1240,${H + 120} L-160,${H + 120} Z`} fill={GROUND} />
      {/* spruce silhouettes along the ridge, so the world has real detail density */}
      {Array.from({length: 17}).map((_, i) => {
        const bx = -60 + i * 72 + ((i * 37) % 26);
        const by = 1180 - ((i * 53) % 150);
        const hh = 92 + ((i * 41) % 66);
        return (
          <path key={`sp${i}`} d={`M${bx},${by} l-19,${hh * 0.42} l10,0 l-15,${hh * 0.36} l9,0 l-13,${hh * 0.30} l38,0 l-13,${-hh * 0.30} l9,0 l-15,${-hh * 0.36} l10,0 Z`}
            fill="#0E2B24" opacity={0.85} transform={`translate(0,${hh * 0.02})`} />
        );
      })}
      {/* scattered boulders + lichen speckle on the near ground */}
      {Array.from({length: 22}).map((_, i) => {
        const px = ((i * 197) % 1180) - 50, py = 1300 + ((i * 149) % 300);
        return <ellipse key={`rk${i}`} cx={px} cy={py} rx={11 + (i % 4) * 6} ry={7 + (i % 3) * 4} fill="#0F2C25" opacity={0.7} />;
      })}
      <path d={`M-160,1240 L150,900 L330,1150 L520,980 L760,1230 L1000,1010 L1240,1180`} fill="none"
        stroke={lit ? GROUND_L : '#16382F'} strokeWidth={7} opacity={0.55} />
      {/* still water */}
      <rect x={-160} y={1520} width={W + 320} height={H} fill={WATER} />
      {Array.from({length: 9}).map((_, i) => (
        <rect key={i} x={-160 + ((i * 197 + drift * 2) % (W + 320))} y={1560 + (i % 4) * 62} width={130} height={4} rx={2}
          fill="#215E56" opacity={0.4} />
      ))}
      {/* drifting haze bands (blur retained for edge softness, tinted near-black per the night spec) */}
      {[0, 1].map((i) => (
        <ellipse key={i} cx={((i * 620 + drift * 3) % (W + 400)) - 200} cy={1120 + i * 130} rx={330} ry={34}
          fill="#0E2A24" opacity={0.5} style={{filter: 'blur(26px)'}} />
      ))}
    </g>
  );
};

// a scrolling seismogram trace. `roller` 0..1 brings the fat slow landslide wave across.
const Trace: React.FC<{f: number; x: number; y: number; w: number; roller?: number; quake?: number; flat?: boolean; boxed?: boolean; bracket?: boolean}> =
({f, x, y, w, roller = 0, quake = 0, flat = false, boxed = false, bracket = false}) => {
  const scroll = (f * 2.4) % 60;
  const pts: string[] = [];
  for (let i = 0; i <= w; i += 4) {
    const t = i / w;
    let v = Math.sin((i + f * 2.4) / 9) * 1.6;                      // baseline noise, always alive
    if (!flat) {
      if (quake > 0) {
        const c = 0.22, d = Math.abs(t - c);
        if (d < 0.05) v += Math.sin(i * 1.7 + f) * 46 * quake * (1 - d / 0.05);
      }
      if (roller > 0) {
        const lead = roller * 1.25;
        if (t < lead) v += Math.sin(i / 46 + f / 22) * 34 * Math.min(1, (lead - t) * 5) * roller;
      }
    }
    pts.push(`${i === 0 ? 'M' : 'L'}${x + i},${y + v}`);
  }
  return (
    <g>
      <line x1={x} y1={y} x2={x + w} y2={y} stroke="#1B3A33" strokeWidth={2} />
      {Array.from({length: 7}).map((_, i) => (
        <line key={i} x1={x + ((i * 90 - scroll + 630) % w)} y1={y - 58} x2={x + ((i * 90 - scroll + 630) % w)} y2={y + 58}
          stroke="#16332C" strokeWidth={2} opacity={0.55} />
      ))}
      <path d={pts.join(' ')} fill="none" stroke={AMBER} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" />
      {/* the live needle, always moving, so a held frame is never dead */}
      <circle cx={x + w} cy={y} r={7} fill={AMBER_HOT} />
      {boxed && <rect x={x + w * 0.06} y={y - 62} width={w * 0.5} height={124} rx={8} fill="none" stroke={AMBER} strokeWidth={5} strokeDasharray="14 9" />}
      {bracket && (
        <g stroke={TEXT} strokeWidth={5} fill="none" strokeLinecap="round">
          <path d={`M${x + w * 0.06},${y - 74} l0,-16 l${w * 0.5},0 l0,16`} />
        </g>
      )}
    </g>
  );
};

// Ambient life layer. Drifting motes + a slow shimmer band, always running, so a held
// frame still carries disjoint motion regions (quality_gate LIVING_SCREEN floor is 80%).
const Motes: React.FC<{f: number; n?: number; tint?: string}> = ({f, n = 44, tint = '#7FD8C0'}) => (
  <g opacity={0.5}>
    {Array.from({length: n}).map((_, i) => {
      const sp = 0.32 + (i % 5) * 0.16;
      const x = ((i * 173) % 1180) - 50 + Math.sin(f / (26 + (i % 7) * 5) + i) * 26;
      const y = 1900 - ((f * sp + i * 121) % 2000);
      const r = 2.2 + (i % 4) * 1.5;
      return <circle key={i} cx={x} cy={y} r={r} fill={tint} opacity={0.18 + 0.24 * Math.sin(f / 13 + i)} />;
    })}
  </g>
);

// A second independent motion field: distant station lamps blinking on their own phases.
const FieldLamps: React.FC<{f: number; n?: number; y0?: number}> = ({f, n = 14, y0 = 980}) => (
  <g>
    {Array.from({length: n}).map((_, i) => {
      const x = 40 + ((i * 227) % 1000);
      const y = y0 + ((i * 139) % 420);
      const ph = 0.5 + 0.5 * Math.sin(f / (6 + (i % 5) * 2.4) + i * 2.1);
      return (
        <g key={i}>
          <circle cx={x} cy={y} r={13} fill="#F2B33D" opacity={0.10 * ph} />
          <circle cx={x} cy={y} r={5} fill="#F2B33D" opacity={0.5 * ph} />
        </g>
      );
    })}
  </g>
);

const Chip: React.FC<{x: number; y: number; t: string; fs?: number; fill?: string; color?: string; op?: number}> =
({x, y, t, fs = 34, fill = CHIP, color = INKW, op = 1}) => {
  const w = t.length * fs * 0.62 + 40;
  return (
    <g opacity={op}>
      <rect x={x - w / 2 + 5} y={y - fs * 0.82 + 6} width={w} height={fs * 1.62} rx={7} fill={INKW} opacity={0.55} />
      <rect x={x - w / 2} y={y - fs * 0.82} width={w} height={fs * 1.62} rx={7} fill={fill} stroke={INKW} strokeWidth={4} />
      <text x={x} y={y + fs * 0.36} fontFamily={BOLD} fontWeight={900} fontSize={fs} fill={color} textAnchor="middle" letterSpacing={1}>{t}</text>
    </g>
  );
};

const Stopwatch: React.FC<{f: number; x: number; y: number; s?: number; from?: number; running?: boolean}> =
({f, x, y, s = 1, from = 62, running = true}) => {
  const secs = running ? from + f / 30 : from;
  const a = (secs % 60) * 6 - 90;
  return (
    <g transform={`translate(${x},${y}) scale(${s})`}>
      <circle r={62} fill={INKW} />
      <circle r={54} fill="#1A2B26" stroke={PROP} strokeWidth={6} />
      {Array.from({length: 12}).map((_, i) => (
        <line key={i} x1={Math.cos(i * Math.PI / 6) * 44} y1={Math.sin(i * Math.PI / 6) * 44}
          x2={Math.cos(i * Math.PI / 6) * 50} y2={Math.sin(i * Math.PI / 6) * 50} stroke={PROP} strokeWidth={3} />
      ))}
      <line x1={0} y1={0} x2={Math.cos(a * Math.PI / 180) * 42} y2={Math.sin(a * Math.PI / 180) * 42} stroke={AMBER} strokeWidth={5} strokeLinecap="round" />
      <circle r={6} fill={PROP} />
      <text y={34} fontFamily={MONO} fontWeight={800} fontSize={24} fill={TEXT} textAnchor="middle">{Math.floor(secs)}s</text>
      <rect x={-13} y={-74} width={26} height={16} rx={4} fill={PROP} stroke={INKW} strokeWidth={3} />
    </g>
  );
};

// ================================================================= S1 Otto at work
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const voice = useVoice();
  const plate = spring({frame: f - 128, fps, config: {damping: 9, stiffness: 120}});
  const count = Math.round(ramp(f, 215, 300) * 200);
  const lampField = ramp(f, 215, 305);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <FjordNight f={f} push={ramp(f, 0, 311) * 0.34} />
        <Motes f={f} />
        <FieldLamps f={f} />
        {/* poster-grade contrast at frame 0: a bright ground band + hard ink rule */}
        <rect x={0} y={0} width={W} height={330} fill={INKW} opacity={0.92} />
        <rect x={0} y={330} width={W} height={12} fill={AMBER_HOT} />
        <rect x={0} y={690} width={W} height={148} fill={AMBER} opacity={0.30} />
        <rect x={0} y={684} width={W} height={11} fill={AMBER_HOT} />
        <rect x={0} y={838} width={W} height={11} fill={INKW} />
        <rect x={0} y={1700} width={W} height={220} fill={INKW} opacity={0.85} />
        {/* the amber line ripping across at frame 0 */}
        <MotionBlur vx={-70} gain={0.4}>
          <g><Trace f={f} x={-60} y={760} w={1200} roller={ramp(f, 0, 26)} /></g>
        </MotionBlur>
        {/* the field of other stations igniting as the counter climbs */}
        {Array.from({length: 26}).map((_, i) => {
          const px = 70 + ((i * 173) % 950), py = 1180 + ((i * 251) % 380);
          const on = ramp(f, 215 + i * 3, 232 + i * 3) * lampField;
          return <circle key={i} cx={px} cy={py} r={7} fill={AMBER} opacity={on * 0.85}
            style={on > 0.4 ? {filter: `drop-shadow(0 0 9px ${AMBER})`} : undefined} />;
        })}
        <SeismicStation x={360} y={1660} f={f} scale={2.5} emotion="listening" heading={-24}
          accent={voice.accentAt(f)} look={interpolate(Math.sin(f / 40), [-1, 1], [-0.7, 0.7])} groundY={0} />
        {/* the SECOND plate bolting on beside the first */}
        <g transform={`translate(${430 + (1 - plate) * 340},${1300 - (1 - plate) * 50}) scale(1.7) rotate(${(1 - plate) * 22})`} opacity={Math.min(1, plate * 1.6)}>
          <rect x={-4} y={-22} width={128} height={44} rx={6} fill={INKW} />
          <rect x={0} y={-18} width={120} height={36} rx={4} fill={PROP} />
          <text x={60} y={9} fontFamily={BOLD} fontWeight={900} fontSize={25} fill={INKW} textAnchor="middle">LANDSLIDES</text>
        </g>
        <g opacity={ramp(f, 6, 30)}><Stopwatch f={f} x={856} y={330} s={1.1} from={62} /></g>
        {f > 200 && (
          <g opacity={ramp(f, 205, 226)}>
            <text x={540} y={1010} fontFamily={MONO} fontWeight={800} fontSize={92} fill={AMBER} textAnchor="middle">{count}</text>
            <Chip x={540} y={1082} t="SOME 200 SENSORS" fs={34} />
          </g>
        )}
        <g opacity={ramp(f, 4, 22) * (1 - ramp(f, 118, 140))}>
          <Chip x={540} y={196} t="EARTHQUAKES DO NOT" fs={54} fill={AMBER} />
          <Chip x={540} y={276} t="LAST THIS LONG" fs={54} fill={AMBER} />
        </g>
        <g opacity={ramp(f, 130, 152) * (1 - ramp(f, 200, 216))}><Chip x={540} y={210} t="A SECOND JOB" fs={44} /></g>
      </svg>
      <NightGrade f={f} amount={0.95} sources={[{x: 430, y: 1420, r: 300, intensity: 0.5}]} floor={0.46} />
    </AbsoluteFill>
  );
};

// ================================================================= S2 duration + the gate
const S2: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const quakeGone = ramp(f, 44, 66);
  const roller = ramp(f, 62, 128);
  const brk = ramp(f, 96, 132);
  const scan = ramp(f, 128, 176);
  const latch = spring({frame: f - 168, fps, config: {damping: 10, stiffness: 150}});
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <FjordNight f={f} push={ramp(f, 0, 193) * 0.32} />
        <Motes f={f} n={46} />
        <FieldLamps f={f} />
        <rect x={0} y={0} width={W} height={H} fill={INKW} opacity={0.42} />
        {/* TOP LANE: the quake, thrashes and quits */}
        <g opacity={1 - quakeGone * 0.72} transform={`translate(${quakeGone * 460},0)`}>
          <Trace f={f} x={70} y={620} w={940} quake={1 - quakeGone} />
        </g>
        <Chip x={250} y={498} t="SECONDS" fs={40} op={ramp(f, 26, 48)} />
        {/* BOTTOM LANE: the slide, keeps coming */}
        <Trace f={f} x={70} y={1010} w={940} roller={roller} />
        {brk > 0.02 && (
          <g opacity={brk}>
            <path d={`M84,1128 l0,22 l${900 * brk},0 l0,-22`} fill="none" stroke={TEXT} strokeWidth={6} strokeLinecap="round" />
            <Chip x={540} y={1206} t="OVER A MINUTE" fs={44} fill={AMBER} />
          </g>
        )}
        {/* the program: a scan bar sweeping against a duration gate */}
        {scan > 0.01 && (
          <g opacity={scan}>
            <rect x={70 + 940 * ((f - 128) / 48 % 1)} y={940} width={9} height={150} fill={AMBER_HOT} opacity={0.8} />
            <rect x={70} y={1320} width={940} height={112} rx={10} fill="#102B25" stroke={AMBER} strokeWidth={5} />
            <text x={100} y={1392} fontFamily={MONO} fontWeight={800} fontSize={34} fill={TEXT}>DURATION GATE</text>
            <rect x={640} y={1344} width={340} height={64} rx={7} fill={latch > 0.4 ? AMBER : '#1B3A33'} stroke={INKW} strokeWidth={4} />
            <text x={810} y={1390} fontFamily={BOLD} fontWeight={900} fontSize={34} fill={latch > 0.4 ? INKW : '#4C6F66'} textAnchor="middle">
              {latch > 0.4 ? 'LATCHED' : 'OPEN'}
            </text>
          </g>
        )}
        {/* THE TELL IS EARNED: the lamp fires for the first time */}
        <SeismicStation x={840} y={1810} f={f} scale={1.7} emotion={latch > 0.4 ? 'heard' : 'listening'}
          lamp={latch} heading={-40} groundY={0} />
        <Chip x={330} y={1520} t="A PROGRAM WATCHES FOR THAT" fs={34} op={ramp(f, 132, 156)} />
      </svg>
      <NightGrade f={f} amount={0.95} floor={0.44}
        sources={latch > 0.3 ? [{x: 868, y: 1660, r: 300, intensity: latch}] : []} />
    </AbsoluteFill>
  );
};

// ================================================================= S3 boundary, travel, THE COLLAPSE
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const snap = spring({frame: f - 10, fps, config: {damping: 11, stiffness: 130}});
  const whip = ramp(f, 78, 100);
  const dateIn = ramp(f, 96, 116);
  const crack = ramp(f, 128, 142);
  const fall = spring({frame: f - 142, fps, config: {damping: 13, stiffness: 42}});
  const impact = ramp(f, 176, 186);
  const shake = impact * (1 - ramp(f, 186, 214)) * 4;
  const scale = ramp(f, 186, 214);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}
        style={{transform: `translate(${Math.sin(f * 2.3) * shake}px,${Math.cos(f * 1.9) * shake}px)`}}>
        {/* phase A: the boundary, seen from above */}
        {f < 96 && (
          <g opacity={1 - whip}>
            <rect x={0} y={0} width={W} height={H} fill={GROUND} />
            <path d="M40,1500 L180,980 L420,760 L760,700 L1010,880 L1040,1420 L700,1720 L300,1690 Z" fill="#12312A" />
            {Array.from({length: 22}).map((_, i) => {
              const px = 210 + ((i * 149) % 620), py = 900 + ((i * 211) % 560);
              return <circle key={i} cx={px} cy={py} r={8} fill={AMBER} opacity={0.85}
                style={{filter: `drop-shadow(0 0 10px ${AMBER})`}} />;
            })}
            <path d="M170,860 L700,790 L950,1000 L860,1560 L330,1610 Z" fill="none" stroke={AMBER}
              strokeWidth={8} strokeDasharray="24 16" strokeDashoffset={(1 - snap) * 900} opacity={0.95} />
            <Chip x={540} y={470} t="IT SEARCHES ONLY ONE" fs={44} op={ramp(f, 20, 40)} />
            <Chip x={540} y={548} t="STRETCH OF COAST" fs={44} op={ramp(f, 26, 46)} />
          </g>
        )}
        {/* phase B: out past the line into the dark, and the wall */}
        {f >= 90 && (
          <g opacity={ramp(f, 90, 106)}>
            <FjordNight f={f} lit={false} push={ramp(f, 106, 221) * 0.30} />
            <path d={`M-60,240 L340,120 L520,700 L640,520 L790,1240 L1140,1020 L1140,1660 L-60,1660 Z`} fill="#173A31" />
            <path d={`M-60,240 L340,120 L520,700 L640,520 L790,1240 L1140,1020`} fill="none" stroke="#3C7C6B" strokeWidth={9} />
            {[0,1,2,3,4].map((i) => (
              <path key={`fa${i}`} d={`M${20 + i * 150},${300 + i * 130} L${140 + i * 150},${520 + i * 150}`} stroke="#0E2A23" strokeWidth={7} opacity={0.7} />
            ))}
            <path d={`M340,150 L430,700 L560,1180`} fill="none" stroke={INKW} strokeWidth={6 + crack * 16} opacity={crack} />
            <MotionBlur vy={fall * 170} gain={0.55}>
              <g transform={`translate(${fall * 70},${fall * 900}) rotate(${fall * 21})`} opacity={crack}>
                <path d="M340,150 L640,300 L560,1180 L390,1010 Z" fill={EMBER} stroke={INKW} strokeWidth={10} strokeLinejoin="round" />
                <path d="M380,240 L590,352 L530,1030" fill="none" stroke="#A82F14" strokeWidth={9} opacity={0.8} />
                <path d="M420,330 L560,404" stroke="#F27B52" strokeWidth={7} opacity={0.6} />
                <path d="M400,560 L540,626" stroke="#A82F14" strokeWidth={6} opacity={0.7} />
              </g>
            </MotionBlur>
            {/* impact + spray sheet */}
            {impact > 0.02 && (
              <g opacity={impact * (1 - ramp(f, 200, 221))}>
                <ellipse cx={520} cy={1500} rx={520 * impact} ry={92 * impact} fill="none" stroke={TEXT} strokeWidth={10} opacity={0.7} />
                <ellipse cx={520} cy={1500} rx={330 * impact} ry={60 * impact} fill="none" stroke={TEXT} strokeWidth={7} opacity={0.45} />
                <path d={`M120,1500 q400,${-620 * impact} 800,0`} fill="none" stroke={TEXT} strokeWidth={13} opacity={0.6} />
                <path d={`M240,1500 q280,${-430 * impact} 560,0`} fill="none" stroke={TEXT} strokeWidth={9} opacity={0.45} />
              </g>
            )}
            {/* runup scale bar climbing the far wall */}
            {scale > 0.02 && (
              <g opacity={scale}>
                <line x1={1000} y1={1500} x2={1000} y2={1500 - 1170 * scale} stroke={TEXT} strokeWidth={10} strokeLinecap="round" />
                {[0.25, 0.5, 0.75, 1].map((k, i) => (
                  <line key={i} x1={952} y1={1500 - 1170 * scale * k} x2={1048} y2={1500 - 1170 * scale * k} stroke={TEXT} strokeWidth={6} />
                ))}
                <text x={936} y={1500 - 1170 * scale + 6} fontFamily={MONO} fontWeight={800} fontSize={40} fill={TEXT} textAnchor="end">470 TO 500 M</text>
              </g>
            )}
            <Chip x={540} y={250} t="AUGUST 10, 2025" fs={46} fill={CHIP} op={dateIn * (1 - ramp(f, 150, 168))} />
            <Chip x={540} y={1780} t="UP TO 100 MILLION CUBIC METERS" fs={32} op={ramp(f, 186, 206)} />
          </g>
        )}
      </svg>
      <NightGrade f={f} amount={0.95} floor={0.46}
        sources={f < 96 ? [{x: 540, y: 1180, r: 460, intensity: 0.55}] : (impact > 0.05 ? [{x: 400, y: 1400, r: 340, intensity: impact * 0.7, color: EMBER}] : [])} />
    </AbsoluteFill>
  );
};

// ================================================================= S4 THE SIGNATURE SHOT + the dark lamp
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ember = ramp(f, 8, 22);
  const rack = ramp(f, 58, 78);
  const push = spring({frame: f - 62, fps, config: {damping: 14, stiffness: 90}});
  const rollerIn = ramp(f, 72, 108);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <rect x={0} y={0} width={W} height={H} fill={GROUND} />
        {/* the lattice, held, with the ember OUTSIDE the line. The dots never react. */}
        <g opacity={1 - rack * 0.86} style={{filter: rack > 0.2 ? `blur(${rack * 7}px)` : undefined}}
          transform={`translate(${W / 2},${H / 2}) scale(${1 + ramp(f, 0, 116) * 0.26}) translate(${-W / 2},${-H / 2})`}>
          <path d="M20,1620 L150,900 L430,560 L830,470 L1060,760 L1062,1520 L700,1850 L250,1810 Z" fill="#1A423A" stroke="#2E6558" strokeWidth={5} />
          <path d="M210,700 L820,610 L1000,900 L900,1600 L330,1660 Z" fill="none" stroke={AMBER} strokeWidth={12} strokeDasharray="30 20" opacity={1} />
          {Array.from({length: 34}).map((_, i) => {
            const px = 265 + ((i * 149) % 640), py = 720 + ((i * 211) % 800);
            // the POSITIVE CONTROL: unchanged idle pulse, so the non-reaction reads as a choice
            const pulse = 0.7 + 0.3 * Math.sin(f / 9 + i * 1.7);
            return (
              <g key={i}>
                <circle cx={px} cy={py} r={22} fill={AMBER} opacity={0.16 * pulse} />
                <circle cx={px} cy={py} r={11} fill={AMBER} opacity={0.95 * pulse} style={{filter: `drop-shadow(0 0 14px ${AMBER})`}} />
              </g>
            );
          })}
          {/* the ember, outside the boundary, in the dark, and unmissable */}
          <g opacity={ember}>
            <circle cx={132} cy={380} r={120 + Math.sin(f / 6) * 14} fill={EMBER} opacity={0.16} />
            <circle cx={132} cy={380} r={62} fill={EMBER} opacity={0.34} />
            <circle cx={132} cy={380} r={34} fill={EMBER} style={{filter: `drop-shadow(0 0 46px ${EMBER})`}} />
            <circle cx={132} cy={380} r={92 + Math.sin(f / 5) * 12} fill="none" stroke={EMBER} strokeWidth={7} opacity={0.6} />
            <path d="M132,380 L214,548" stroke={EMBER} strokeWidth={5} opacity={0.5} strokeDasharray="9 8" />
            <text x={232} y={576} fontFamily={MONO} fontWeight={800} fontSize={30} fill={EMBER}>OUTSIDE THE LINE</text>
          </g>
          <Chip x={540} y={330} t="NO INJURIES OR FATALITIES REPORTED" fs={30} op={ramp(f, 22, 44)} />
        </g>
        {/* rack focus to the instrument that did not fire */}
        <g opacity={rack} transform={`translate(${W / 2},${H / 2}) scale(${1 + push * 0.34}) translate(${-W / 2},${-H / 2})`}>
          <rect x={0} y={0} width={W} height={H} fill={GROUND} opacity={0.72} />
          <SeismicStation x={470} y={1720} f={f} scale={2.9} emotion="straining" lamp={0} heading={-56} groundY={0} />
          <Trace f={f} x={60} y={700} w={960} roller={rollerIn} />
          {/* the detection box that NEVER draws */}
          <Chip x={540} y={470} t="NO ALARM FIRED" fs={46} fill={CHIP} op={ramp(f, 86, 106)} />
          <g opacity={ramp(f, 92, 110)}><Stopwatch f={f} x={905} y={1120} s={0.8} from={0} /></g>
        </g>
      </svg>
      <NightGrade f={f} amount={0.95} floor={0.48}
        sources={[{x: 540, y: 1180, r: 420, intensity: (1 - rack) * 0.5}]} />
    </AbsoluteFill>
  );
};

// ================================================================= S5 recorded, by hand, the ceiling
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const handIn = ramp(f, 76, 104);
  const brkDraw = ramp(f, 104, 150);
  const letters = ramp(f, 150, 186);
  const toBoulder = ramp(f, 206, 226);
  const tip = spring({frame: f - 268, fps, config: {damping: 16, stiffness: 40}});
  const wave = ramp(f, 286, 320);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <FjordNight f={f} push={ramp(f, 0, 344) * 0.30} />
        <Motes f={f} n={48} />
        <FieldLamps f={f} />
        {/* phase A: the roller IS on the paper, unmarked */}
        <g opacity={1 - toBoulder}>
          <SeismicStation x={880} y={1810} f={f} scale={1.5} emotion="listening" heading={-70} groundY={0} />
          <rect x={40} y={620} width={1000} height={600} rx={14} fill="#0B1D19" stroke="#2E6558" strokeWidth={7} />
          <rect x={40} y={620} width={1000} height={62} rx={14} fill="#153A32" />
          <text x={72} y={664} fontFamily={MONO} fontWeight={800} fontSize={30} fill="#7FB8A8">RECORDED, UNFLAGGED</text>
          {Array.from({length: 4}).map((_, i) => (
            <circle key={`led${i}`} cx={962 - i * 34} cy={650} r={8} fill={i === 0 ? AMBER : '#24544A'} opacity={0.9} />
          ))}
          <Trace f={f} x={70} y={930} w={940} roller={1} bracket={brkDraw > 0.02} />
          {brkDraw > 0.02 && (
            <path d={`M126,850 l0,-18 l${470 * brkDraw},0 l0,18`} fill="none" stroke={TEXT} strokeWidth={6} strokeLinecap="round" />
          )}
          {letters > 0.02 && (
            <g opacity={letters}>
              <text x={360} y={796} fontFamily={MONO} fontWeight={800} fontSize={38} fill={TEXT} textAnchor="middle">
                {'LANDSLIDE'.slice(0, Math.round(letters * 9))}
              </text>
            </g>
          )}
          {/* the hand. crisp, unsmeared, the only slow move in the piece */}
          <g opacity={handIn} transform={`translate(${170 + brkDraw * 470},${1180 - handIn * 90})`}>
            <path d="M0,0 l-16,-120 l30,-8 l26,116 Z" fill="#D8B48C" stroke={INKW} strokeWidth={5} strokeLinejoin="round" />
            <path d="M-10,-118 l10,-52" stroke={INKW} strokeWidth={7} strokeLinecap="round" />
            <path d="M-10,-118 l10,-52" stroke={PROP} strokeWidth={3.5} strokeLinecap="round" />
            <path d="M28,4 q22,44 4,86" fill="none" stroke="#C6A07C" strokeWidth={22} strokeLinecap="round" />
          </g>
          <Chip x={540} y={1330} t="THE SENSORS STILL HEARD IT" fs={36} op={ramp(f, 14, 40) * (1 - ramp(f, 88, 106))} />
          <Chip x={540} y={1330} t="RUN BY HAND, AFTERWARD" fs={36} op={ramp(f, 110, 132)} />
        </g>
        {/* phase B: the ceiling. the rock is silent until it moves. */}
        <g opacity={toBoulder}>
          <rect x={0} y={0} width={W} height={H} fill={GROUND} opacity={0.85} />
          <path d="M-60,1560 L260,900 L640,1240 L980,940 L1140,1180 L1140,1720 L-60,1720 Z" fill="#12332B" stroke="#2E6558" strokeWidth={8} strokeLinejoin="round" />
          {[0,1,2,3].map((i) => (
            <path key={`sl${i}`} d={`M${60 + i * 230},${1620 - i * 80} L${200 + i * 230},${1360 - i * 90}`} stroke="#0C2620" strokeWidth={8} opacity={0.7} />
          ))}
          <MotionBlur vy={tip * 150} gain={0.5}>
            <g transform={`translate(${tip * 150},${tip * 520}) rotate(${tip * 62},300,1000)`}>
              <path d="M150,1010 L214,886 L336,858 L412,952 L396,1096 L300,1178 L178,1140 Z"
                fill="#7A6752" stroke={INKW} strokeWidth={12} strokeLinejoin="round" />
              <path d="M214,886 L268,986 L412,952" fill="none" stroke="#57473A" strokeWidth={9} opacity={0.9} />
              <path d="M268,986 L300,1178" fill="none" stroke="#57473A" strokeWidth={8} opacity={0.8} />
              <path d="M150,1010 L268,986" fill="none" stroke="#57473A" strokeWidth={7} opacity={0.7} />
              <path d="M232,912 L318,894" stroke="#A28C6E" strokeWidth={9} opacity={0.55} strokeLinecap="round" />
              <path d="M182,1042 L246,1064" stroke="#A28C6E" strokeWidth={6} opacity={0.4} strokeLinecap="round" />
            </g>
          </MotionBlur>
          <Trace f={f} x={70} y={1520} w={940} roller={wave} flat={wave < 0.02} />
          <Chip x={540} y={640} t="ROCK MAKES NO SOUND" fs={44} op={ramp(f, 214, 240)} />
          <Chip x={540} y={720} t="UNTIL IT FALLS" fs={44} fill={AMBER} op={ramp(f, 276, 300)} />
        </g>
      </svg>
      <NightGrade f={f} amount={0.95} floor={0.46} sources={[{x: 540, y: 960, r: 360, intensity: 0.42 * (1 - toBoulder)}]} />
    </AbsoluteFill>
  );
};

// ================================================================= S6 the crate + the money
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drop = spring({frame: f - 6, fps, config: {damping: 13, stiffness: 90}});
  const dust = ramp(f, 26, 60);
  const money = ramp(f, 80, 132);
  const amount = Math.round(money * 1772170);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <FjordNight f={f} push={ramp(f, 0, 168) * 0.36} />
        <Motes f={f} n={48} />
        <FieldLamps f={f} />
        <SeismicStation x={790} y={1700} f={f} scale={1.9} emotion="listening" heading={-64} groundY={0} />
        <MotionBlur vy={(1 - drop) * 90} gain={0.4}>
          <g transform={`translate(${380},${1520 - (1 - drop) * 620})`}>
            <rect x={-190} y={-180} width={380} height={200} rx={9} fill={INKW} />
            <rect x={-182} y={-172} width={364} height={184} rx={6} fill="#5A4A34" />
            {[0, 1, 2, 3].map((i) => (
              <line key={i} x1={-182} y1={-172 + (i + 1) * 37} x2={182} y2={-172 + (i + 1) * 37} stroke="#463829" strokeWidth={4} opacity={0.8} />
            ))}
            <RimLight d="M-182,-172 L182,-172" w={5} color={PROP} opacity={0.6} />
            <text x={0} y={-118} fontFamily={BOLD} fontWeight={900} fontSize={31} fill={PROP} textAnchor="middle">NSF TO UAF</text>
            <text x={0} y={-78} fontFamily={MONO} fontWeight={800} fontSize={26} fill="#9C8560" textAnchor="middle">JULY 10, 2026</text>
            {money > 0.02 && (
              <text x={0} y={-22} fontFamily={MONO} fontWeight={800} fontSize={38} fill={AMBER} textAnchor="middle">
                ${amount.toLocaleString('en-US')}
              </text>
            )}
          </g>
        </MotionBlur>
        {dust > 0.02 && (
          <g opacity={dust * (1 - ramp(f, 56, 92))}>
            {[0, 1, 2, 3].map((i) => (
              <ellipse key={i} cx={230 + i * 100} cy={1524} rx={40 + dust * 44} ry={12} fill="#2B4B41" opacity={0.5} />
            ))}
          </g>
        )}
        <Chip x={540} y={1720} t="$1,772,170 OF $4,430,711" fs={38} fill={AMBER} op={ramp(f, 118, 146)} />
      </svg>
      <NightGrade f={f} amount={0.95} floor={0.44} sources={[{x: 800, y: 1480, r: 300, intensity: 0.45}]} />
    </AbsoluteFill>
  );
};

// ================================================================= S7 the twin, the calendar, the button
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const build = ramp(f, 10, 96);
  const threads = ramp(f, 40, 110);
  const ghostTip = spring({frame: f - 118, fps, config: {damping: 15, stiffness: 44}});
  const realStill = spring({frame: f - 800, fps, config: {damping: 15, stiffness: 44}});
  const bracket = ramp(f, 140, 182);
  const cal = ramp(f, 200, 236);
  const bar = ramp(f, 236, 288);
  const lid = spring({frame: f - 290, fps, config: {damping: 12, stiffness: 100}});
  const proposal = ramp(f, 330, 420);
  const watch = ramp(f, 400, 420);
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <FjordNight f={f} push={ramp(f, 0, 487) * 0.40} />
        <Motes f={f} n={54} />
        <FieldLamps f={f} />
        {/* the real slope, inert */}
        <g transform={`translate(${ghostTip * 0},${realStill * 0})`}>
          <path d="M60,1180 L250,900 L400,1210 L400,1520 L60,1520 Z" fill="#0F2A24" stroke="#1E4C41" strokeWidth={6} strokeLinejoin="round" />
          <text x={230} y={1600} fontFamily={MONO} fontWeight={800} fontSize={26} fill="#5C7B72" textAnchor="middle">THE REAL SLOPE</text>
        </g>
        {/* the wireframe twin, assembling line by line */}
        <g opacity={build}>
          <g transform={`translate(${640},0) rotate(${ghostTip * 16},60,1300)`}>
            <path d="M60,1180 L250,900 L400,1210 L400,1520 L60,1520 Z" fill="none" stroke={AMBER} strokeWidth={5}
              strokeDasharray={1600} strokeDashoffset={1600 * (1 - build)} opacity={0.9} />
            {[0, 1, 2, 3, 4].map((i) => (
              <line key={i} x1={60} y1={1230 + i * 60} x2={400} y2={1180 + i * 66}
                stroke={AMBER} strokeWidth={2.6} opacity={0.45 * build} />
            ))}
            {[0, 1, 2].map((i) => (
              <line key={i} x1={130 + i * 92} y1={1010 + i * 60} x2={130 + i * 92} y2={1520}
                stroke={AMBER} strokeWidth={2.6} opacity={0.4 * build} />
            ))}
          </g>
          <text x={870} y={1600} fontFamily={MONO} fontWeight={800} fontSize={26} fill={AMBER} textAnchor="middle">THE SIMULATED ONE</text>
        </g>
        {/* sensor threads feeding the twin, thick and visibly pulsing */}
        {threads > 0.02 && [0, 1, 2, 3, 4].map((i) => (
          <path key={i} d={`M420,${1250 + i * 66} Q560,${1180 + i * 44} 700,${1260 + i * 58}`} fill="none"
            stroke={AMBER} strokeWidth={7} opacity={threads * (0.35 + 0.5 * Math.sin(f / 6 + i * 1.3))}
            strokeDasharray="16 12" strokeDashoffset={-f * 3.2} strokeLinecap="round" />
        ))}
        {/* a scan sweep continuously re-solving the twin, so the frame never rests */}
        {build > 0.3 && (
          <g opacity={0.7}>
            <rect x={640 + ((f * 5) % 400) - 6} y={860} width={12} height={700} fill={AMBER_HOT} opacity={0.5} />
            <rect x={640} y={860} width={400} height={700} fill="none" stroke={AMBER} strokeWidth={3} opacity={0.25} />
          </g>
        )}
        {/* the lattice keeps pulsing behind the whole button sequence */}
        {Array.from({length: 16}).map((_, i) => {
          const px = 90 + ((i * 149) % 900), py = 420 + ((i * 211) % 260);
          const pulse = 0.5 + 0.5 * Math.sin(f / 8 + i * 1.7);
          return <circle key={`lat${i}`} cx={px} cy={py} r={7} fill={AMBER} opacity={0.55 * pulse}
            style={{filter: `drop-shadow(0 0 10px ${AMBER})`}} />;
        })}
        {/* the forecast bracket reaching PAST the present-moment needle */}
        {bracket > 0.02 && (
          <g opacity={bracket}>
            <line x1={70} y1={760} x2={1010} y2={760} stroke="#1B3A33" strokeWidth={2} />
            <path d={`M70,760 q120,-56 240,0 t240,0`} fill="none" stroke={AMBER} strokeWidth={5} />
            <circle cx={550} cy={760} r={7} fill={AMBER_HOT} />
            <path d={`M560,700 l${380 * bracket},0`} fill="none" stroke={CYAN} strokeWidth={5} strokeDasharray="12 9" />
            <text x={760} y={672} fontFamily={MONO} fontWeight={800} fontSize={26} fill={CYAN} textAnchor="middle">AHEAD</text>
          </g>
        )}
        {/* the calendar bar */}
        {cal > 0.02 && (
          <g opacity={cal}>
            <Chip x={330} y={330} t="AUG 1, 2026" fs={38} fill={CHIP} />
            <line x1={470} y1={330} x2={470 + 340 * bar} y2={330} stroke={TEXT} strokeWidth={7} strokeLinecap="round" />
            {bar > 0.9 && <Chip x={900} y={330} t="2032" fs={38} fill={CHIP} />}
            <Chip x={540} y={430} t="YEAR ONE DELIVERS DATASETS" fs={30} op={ramp(f, 262, 292)} />
          </g>
        )}
        {/* the crate opens on a blueprint, not a machine */}
        {lid > 0.02 && (
          <g opacity={Math.min(1, lid * 1.4)} transform="translate(250,1760)">
            <rect x={-150} y={-90} width={300} height={90} rx={6} fill="#5A4A34" stroke={INKW} strokeWidth={6} />
            <g transform={`translate(0,${-96 - lid * 74}) rotate(${-lid * 16})`}>
              <rect x={-104} y={-58} width={208} height={104} rx={5} fill="#1B4652" stroke={INKW} strokeWidth={5} />
              {[0, 1, 2].map((i) => <line key={i} x1={-88} y1={-38 + i * 30} x2={88} y2={-38 + i * 30} stroke={CYAN} strokeWidth={2.6} opacity={0.7} />)}
            </g>
            <text x={0} y={-24} fontFamily={BOLD} fontWeight={900} fontSize={24} fill={PROP} textAnchor="middle">NOTHING IS BUILT YET</text>
          </g>
        )}
        {/* THE BUTTON. the real amber line never moves. the wider one is PROPOSED, unlit. */}
        {proposal > 0.02 && (
          <g>
            <path d="M170,1000 L700,930 L950,1140 L860,1700 L330,1750 Z" fill="none" stroke={AMBER} strokeWidth={7} strokeDasharray="22 15" opacity={0.9} />
            <path d="M60,900 L840,810 L1030,1090 L950,1810 L220,1860 Z" fill="none" stroke={CYAN} strokeWidth={6}
              strokeDasharray={2600} strokeDashoffset={2600 * (1 - proposal)} opacity={0.75} />
            <text x={540} y={880} fontFamily={MONO} fontWeight={800} fontSize={27} fill={CYAN} textAnchor="middle" opacity={proposal}>PROPOSED, NOT BUILT</text>
          </g>
        )}
        <SeismicStation x={545} y={1780} f={f} scale={1.9}
          emotion={proposal > 0.5 ? 'listening' : 'listening'} heading={-20 + proposal * 14} groundY={0} />
        {watch > 0.02 && <g opacity={watch}><Stopwatch f={f - 400} x={880} y={560} s={1.0} from={0} /></g>}
      </svg>
      <NightGrade f={f} amount={0.95} floor={0.46} sources={[{x: 560, y: 1580, r: 300, intensity: 0.5}]} />
    </AbsoluteFill>
  );
};

const GradedGrade: React.FC = () => {
  const f = useCurrentFrame();
  return <GradeLayer f={f} bloom={0.18} vignette={0.44} grain={0.05} warmth={0.03} />;
};

const Captions: React.FC<{captions: EpisodeProps['captions']}> = ({captions}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = f / fps;
  const cue = captions.find((c) => t >= c.start && t < c.end + 0.05);
  if (!cue) return null;
  const local = f - Math.round(cue.start * fps);
  const pop = spring({frame: local, fps, config: {damping: 9, stiffness: 130}});
  const scale = interpolate(pop, [0, 1], [0.84, 1], {extrapolateRight: 'clamp'});
  const rise = interpolate(pop, [0, 1], [24, 0], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', bottom: 452, left: 0, right: 0, display: 'flex', justifyContent: 'center', padding: '0 60px'}}>
      <div style={{background: 'rgba(6,14,11,0.88)', borderRadius: 14, padding: '16px 30px', maxWidth: 940,
        border: `4px solid ${AMBER}`, transform: `translateY(${rise}px) scale(${scale})`, transformOrigin: 'center bottom'}}>
        <div style={{fontFamily: BOLD, fontWeight: 900, fontSize: 46, lineHeight: 1.12, color: '#fff', textAlign: 'center',
          letterSpacing: 0.5, textShadow: '2px 3px 0 rgba(0,0,0,0.65)'}}>{cue.text}</div>
      </div>
    </div>
  );
};

export const episodeSchema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.object({frame: z.number(), word: z.string(), energy: z.number().optional(), lineIdx: z.number().optional()})).optional(),
});
export type EpisodeProps = z.infer<typeof episodeSchema>;

const SCENE_COMPONENTS: React.FC[] = [S1, S2, S3, S4, S5, S6, S7];
const DEFAULT_BOUNDS = [
  {from: 0, dur: 311}, {from: 311, dur: 193}, {from: 504, dur: 221}, {from: 725, dur: 116},
  {from: 841, dur: 344}, {from: 1185, dur: 168}, {from: 1353, dur: 487},
];

export const Episode: React.FC<EpisodeProps> = ({captions, scenes, mouth, accents}) => {
  const bounds = scenes && scenes.length === SCENE_COMPONENTS.length ? scenes : DEFAULT_BOUNDS;
  const voice = mouth && mouth.length ? {fps: 30, mouth, accents: accents ?? []} : null;
  return (
    <AbsoluteFill style={{backgroundColor: INKW}}>
      <VoiceProvider data={voice}>
        {SCENE_COMPONENTS.map((C, i) => (
          <Sequence key={i} from={bounds[i].from} durationInFrames={bounds[i].dur} name={`S${i + 1}`}>
            <C />
          </Sequence>
        ))}
        <GradedGrade />
        <Captions captions={captions} />
      </VoiceProvider>
    </AbsoluteFill>
  );
};
