import React from 'react';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {VoiceProvider, useVoice} from './lib/voice';
import {tones, FormGradient, RimLight, ContactShadow, GradeLayer, MotionBlur, INK} from './lib/lighting';
import {Character} from './lib/Character';
import {PAPER, PaperOfficeBG, PaperFiber, Sheet, StateLetter, FullTapeMachine, TaperedCone} from './lib/paper';
import {RecordsMachine, ThreePipeCutaway} from './lib/records';
import {vitals, EASE, anticipate} from './lib/motion';

// ============================================================================
// THE FIELD THAT STOPPED IN 2019 — Dispatch 2026-07-26
//
// Alaska's Division of Elections asked the DMV to check about fifteen thousand
// license holders at once. That flagged 3,500 Alaskans, mailed them letters
// saying they may not be citizens, and moved 3,048 to inactive. Nobody was
// removed and nobody lost the vote. The cause is that a DMV record stores
// citizenship as of the day you apply and naturalization never travels back.
//
// Board: out/dispatch/storyboard.json. Binding look: out/dispatch/art_direction.json.
// NO SKY, NO LANDSCAPE, NO NATURAL LIGHT anywhere, including the button.
// ============================================================================

const BOLD = 'Archivo, Arial Black, Arial, sans-serif';
const MONO = 'JetBrains Mono, Consolas, monospace';
const W = 1080, H = 1920;

const ramp = (f: number, a: number, b: number) =>
  interpolate(f, [a, b], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

// ---------------------------------------------------------------- shared chrome
/** Boxed label. Form-shaded (this run's secondary craft advance) so chips sit IN the lit world. */
const Label: React.FC<{x: number; y: number; text: string; tint?: string; size?: number; delay?: number}> = ({
  x, y, text, tint = PAPER.front, size = 40, delay = 0,
}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: f - delay, fps, config: {damping: 12, stiffness: 150}});
  if (f < delay) return null;
  const w = text.length * size * 0.62 + 44;
  return (
    <g transform={`translate(${x},${y}) scale(${interpolate(p, [0, 1], [0.86, 1])})`} opacity={p}>
      <rect x={-w / 2 + 5} y={-size * 0.82 + 7} width={w} height={size * 1.62} fill={INK} opacity={0.26} />
      <rect x={-w / 2} y={-size * 0.82} width={w} height={size * 1.62} fill={tint} stroke={INK} strokeWidth={4} />
      <rect x={-w / 2} y={-size * 0.82} width={w} height={size * 0.34} fill="#fff" opacity={0.24} />
      <text x={0} y={size * 0.34} textAnchor="middle" fontFamily={BOLD} fontWeight={900}
            fontSize={size} fill={INK} letterSpacing={0.6}>{text}</text>
    </g>
  );
};

const Stat: React.FC<{x: number; y: number; big: string; small: string; delay?: number; tint?: string}> = ({
  x, y, big, small, delay = 0, tint = PAPER.stamp,
}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame: f - delay, fps, config: {damping: 11, stiffness: 140}});
  if (f < delay) return null;
  return (
    <g transform={`translate(${x},${y}) scale(${interpolate(p, [0, 1], [0.7, 1])})`} opacity={p}>
      <rect x={-186} y={-84} width={372} height={168} fill={INK} opacity={0.24} transform="translate(6,8)" />
      <rect x={-186} y={-84} width={372} height={168} fill={PAPER.front} stroke={INK} strokeWidth={5} />
      <rect x={-186} y={-84} width={372} height={16} fill={tint} />
      <text x={0} y={26} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={82} fill={INK}>{big}</text>
      <text x={0} y={64} textAnchor="middle" fontFamily={MONO} fontSize={24} fill={INK} opacity={0.78}>{small}</text>
    </g>
  );
};

const Stage: React.FC<{children: React.ReactNode; push?: number; drift?: number}> = ({children, push = 0, drift = 1}) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <g transform={`translate(${W / 2},${H / 2}) scale(${1 + push}) translate(${-W / 2},${-H / 2})`}>
          <PaperOfficeBG f={f} parallax={push * 900} drift={drift} />
          {children}
        </g>
      </svg>
    </AbsoluteFill>
  );
};

// ====================================================================== S1 HOOK
// The letter opens by PHYSICS against the dark slate wall. No face anywhere.
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const open = ramp(f, 6, 26);
  const push = ramp(f, 0, 90) * 0.06;
  return (
    <Stage push={push} drift={0.6}>
      <StateLetter f={f} x={540} y={1010} scale={1.16} open={open} line="YOU MAY NOT BE A CITIZEN" />
      <Label x={540} y={470} text="3,500 LETTERS" size={72} delay={4} />
      <Label x={540} y={600} text="NOBODY LOST THE VOTE" size={54} tint={PAPER.seal} delay={12} />
    </Stage>
  );
};

// =================================================== S2 THE ROUTINE + THE DEFENSE
const S2: React.FC = () => {
  const f = useCurrentFrame();
  const count = Math.round(interpolate(ramp(f, 4, 46), [0, 1], [0, 200]));
  const mc = ramp(f, 62, 78);
  const v = vitals(f, 2.0, 1);
  return (
    <Stage drift={0.5}>
      {/* the tally clicker, dull brass, clicking calmly to 200 */}
      <g transform={`translate(330,${1010 + v.bob}) rotate(${v.tilt * 0.4})`}>
        <ContactShadow cx={0} cy={120} rx={130} opacity={0.34} />
        <circle r={118} fill={PAPER.brass} stroke={INK} strokeWidth={6} />
        <circle r={96} fill={PAPER.front} stroke={INK} strokeWidth={4} />
        {Array.from({length: 24}).map((_, i) => (
          <line key={i} x1={Math.cos(i * 15 * Math.PI / 180) * 82} y1={Math.sin(i * 15 * Math.PI / 180) * 82}
                x2={Math.cos(i * 15 * Math.PI / 180) * 94} y2={Math.sin(i * 15 * Math.PI / 180) * 94}
                stroke={INK} strokeWidth={3} opacity={0.6} />
        ))}
        <text x={0} y={16} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={54} fill={INK}>{count}</text>
        <line x1={0} y1={0} x2={Math.cos((count / 200 * 300 - 90) * Math.PI / 180) * 70}
              y2={Math.sin((count / 200 * 300 - 90) * Math.PI / 180) * 70}
              stroke={PAPER.stamp} strokeWidth={7} strokeLinecap="round" />
      </g>
      <Label x={330} y={1230} text="MORE LIKE 200 NAMES" size={36} delay={8} />

      {/* the fair defense, drawn straight. no sneer, no dark lighting. */}
      <g opacity={mc} transform={`translate(0,${interpolate(mc, [0, 1], [40, 0])})`}>
        <Character frame={f} x={790} y={1080} scale={0.92} pose="point" emotion="neutral"
                   outfit="referee" headgear="bare" facing={-1} />
        <Label x={790} y={1330} text="REP. KEVIN McCABE" size={30} delay={64} />
        <Label x={620} y={620} text="THIS IS ACTUALLY" size={50} delay={70} />
        <Label x={620} y={718} text="THEIR JOB" size={50} delay={76} />
      </g>
    </Stage>
  );
};

// ================================================ S3 THE MOUTH, THE ASK, THE BURST
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const openM = ramp(f, 4, 58);
  const pour = ramp(f, 40, 100);
  const burst = ramp(f, 150, 175);
  const sheets = Array.from({length: 26}, (_, i) => {
    const h = Math.imul(i + 13, 2654435761) >>> 0;
    const ph = ((f / 26) + (h % 100) / 100) % 1;
    return {x: 300 + (h % 480), y: 120 + ph * 560, rot: (h >>> 5) % 90 - 45, o: pour};
  });
  return (
    <Stage drift={0.8}>
      <RecordsMachine f={f} x={540} y={820} scale={1.05} mouthOpen={openM} strain={burst * 0.4} />
      {/* forms pouring DOWN into the widened mouth */}
      <g opacity={pour}>
        {sheets.map((s, i) => (
          <g key={i} transform={`translate(${s.x},${s.y}) rotate(${s.rot})`} opacity={0.9}>
            <rect width={54} height={70} fill={PAPER.front} stroke={INK} strokeWidth={2.4} />
            <line x1={8} y1={18} x2={44} y2={18} stroke={INK} strokeWidth={2} opacity={0.4} />
            <line x1={8} y1={32} x2={44} y2={32} stroke={INK} strokeWidth={2} opacity={0.4} />
          </g>
        ))}
      </g>
      <Stat x={540} y={330} big="15,200" small="SENT TO THE D M V" delay={46} />
      {/* the burst out of the unchanged stem */}
      {burst > 0 && (
        <g opacity={burst}>
          {Array.from({length: 14}).map((_, i) => {
            const a = -60 + i * 9;
            const d = burst * (200 + (i % 4) * 40);
            return (
              <g key={i} transform={`translate(${540 + Math.cos(a * Math.PI / 180) * d},${1420 + Math.sin(a * Math.PI / 180) * d * 0.5}) rotate(${a})`}>
                <rect x={-24} y={-16} width={48} height={32} fill={PAPER.front} stroke={INK} strokeWidth={2.6} />
              </g>
            );
          })}
          <Stat x={540} y={1620} big="3,500" small="FLAGGED" delay={152} tint={PAPER.seal} />
        </g>
      )}
    </Stage>
  );
};

// ============================================== S4 THE LETTER + THE FIXED CAPACITY
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const type = ramp(f, 6, 44);
  const fill = ramp(f, 62, 128);
  const line = 'We have since received information';
  const line2 = 'that you may not be a citizen.';
  const shown = Math.round(type * (line.length + line2.length));
  const tag = ramp(f, 46, 58);
  return (
    <Stage drift={0.4}>
      <PaperFiber id="s4fib" />
      {/* the plain letter. no face, no gag, no character. */}
      <Sheet x={230} y={200} w={620} h={420} fiber="s4fib" curl={0.5}>
        <rect x={40} y={44} width={92} height={58} fill={PAPER.brass} stroke={INK} strokeWidth={3} />
        <line x1={40} y1={128} x2={660} y2={128} stroke={PAPER.stamp} strokeWidth={5} />
        <text x={40} y={210} fontFamily={BOLD} fontWeight={800} fontSize={31} fill={INK}>
          {line.slice(0, shown)}
        </text>
        <text x={40} y={256} fontFamily={BOLD} fontWeight={800} fontSize={31} fill={INK}>
          {line2.slice(0, Math.max(0, shown - line.length))}
        </text>
        {[320, 356, 392].map((y, i) => (
          <line key={y} x1={40} y1={y} x2={i === 2 ? 300 : 660} y2={y} stroke={INK} strokeWidth={3} opacity={0.24} />
        ))}
      </Sheet>
      {tag > 0 && (
        <g transform={`translate(830,${560 + Math.sin(f / 7) * 6 * (1 - tag * 0.4)}) rotate(${Math.sin(f / 6) * 7 * (1 - tag * 0.3)})`} opacity={tag}>
          <line x1={0} y1={-70} x2={0} y2={0} stroke={INK} strokeWidth={3} />
          <rect x={-88} y={0} width={176} height={54} fill={PAPER.front} stroke={INK} strokeWidth={4} />
          <text x={0} y={38} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={30} fill={INK}>INACTIVE</text>
        </g>
      )}
      <FullTapeMachine f={f} x={540} y={900} scale={1.85} fill={fill} />
      {/* the single-file queue arriving */}
      <g opacity={ramp(f, 60, 76)}>
        {Array.from({length: 9}).map((_, i) => {
          const t = ((f / 20) + i / 9) % 1;
          return (
            <rect key={i} x={60 + t * 340} y={880} width={38} height={26}
                  fill={PAPER.front} stroke={INK} strokeWidth={2.2} opacity={1 - t * 0.3} />
          );
        })}
      </g>
      <Stat x={540} y={1560} big="3,048" small="WENT INACTIVE" delay={92} />
    </Stage>
  );
};

// ===================================================== S5 THREE DIFFERENT PEOPLE
const S5: React.FC = () => {
  const f = useCurrentFrame();
  // S5 is the SHORTEST scene (its VO line is four words), so the three reactions are
  // staggered tight to fit. Gate 0B required each to be legible on its own, so they
  // arrive sequentially rather than as a single snap, just faster than the board's plan.
  const a = ramp(f, 2, 16), b = ramp(f, 22, 36), c = ramp(f, 44, 58);
  return (
    <Stage drift={0.4}>
      <g opacity={a} transform={`translate(0,${interpolate(a, [0, 1], [30, 0])})`}>
        <Character frame={f} x={215} y={900} scale={1.05} pose="arms-crossed" emotion="neutral" outfit="flannel" headgear="beanie" />
        <Sheet x={268} y={800} w={150} h={104} rot={-8} />
      </g>
      <g opacity={b} transform={`translate(0,${interpolate(b, [0, 1], [30, 0])})`}>
        <Character frame={f} x={860} y={900} scale={1.05} pose="stand" emotion="shock" outfit="puffer" headgear="cap" facing={-1} />
        <Sheet x={648} y={800} w={150} h={104} rot={5} />
      </g>
      <g opacity={c} transform={`translate(0,${interpolate(c, [0, 1], [30, 0])})`}>
        <Character frame={f} x={540} y={1720} scale={1.06} pose="raise" emotion="worried" outfit="vest" headgear="bare" />
        {/* the receiver, and the line that does not pick up */}
        <g transform="translate(690,1560)">
          <rect x={-16} y={-40} width={32} height={80} rx={14} fill={PAPER.hero} stroke={INK} strokeWidth={4} />
          <path d={`M20,${-10 + Math.sin(f / 5) * 3} q26,10 26,34`} fill="none" stroke={INK} strokeWidth={3} opacity={0.6} />
        </g>
        <Label x={820} y={1700} text="STILL DIALING" size={34} delay={52} />
      </g>
      <Label x={540} y={330} text="REAL CITIZENS" size={62} tint={PAPER.seal} delay={10} />
    </Stage>
  );
};

// ============================================ S6 THE MACHINE OPENS + THE TWO RECORDS
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const dis = ramp(f, 4, 62);
  const lock = ramp(f, 118, 130);
  const swap = ramp(f, 190, 214);
  return (
    <Stage push={ramp(f, 0, 200) * 0.05} drift={0.5}>
      <g opacity={1 - swap}>
        <ThreePipeCutaway f={f} x={540} y={800} scale={1.12} disclose={dis} lock={lock} year="2019" />
        <Label x={540} y={1560} text="NOTHING RECEIVES IT" size={46} delay={70} />
        <Label x={540} y={1660} text="CITIZENSHIP AT APPLICATION" size={30} delay={110} />
      </g>
      {/* the two records, six years apart */}
      <g opacity={swap}>
        <PaperFiber id="s6fib" />
        <Sheet x={80} y={640} w={430} h={276} fill={PAPER.mid} fiber="s6fib" rot={-3}>
          <text x={26} y={54} fontFamily={MONO} fontSize={26} fill={INK} opacity={0.8}>ALASKA D M V</text>
          <rect x={26} y={90} width={200} height={70} fill={PAPER.brass} stroke={INK} strokeWidth={3} />
          <text x={40} y={140} fontFamily={MONO} fontWeight={700} fontSize={40}
                fill={INK} opacity={interpolate(ramp(f, 216, 262), [0, 1], [1, 0.22])}>2019</text>
          <text x={26} y={210} fontFamily={MONO} fontSize={22} fill={INK}
                opacity={interpolate(ramp(f, 216, 262), [0, 1], [0.85, 0.16])}>CITIZENSHIP FIELD</text>
        </Sheet>
        <Sheet x={560} y={1010} w={430} h={276} fiber="s6fib" rot={2}>
          <text x={26} y={54} fontFamily={MONO} fontSize={24} fill={INK} opacity={0.8}>NATURALIZATION</text>
          <text x={26} y={140} fontFamily={MONO} fontWeight={700} fontSize={40} fill={INK}>2025</text>
          {/* the ONLY soft closed organic curve in the film, and the only one in vermilion */}
          <ellipse cx={300} cy={175} rx={58} ry={44} fill={PAPER.seal} stroke={INK} strokeWidth={4}
                   opacity={interpolate(ramp(f, 216, 262), [0, 1], [0.75, 1])} />
          <ellipse cx={300} cy={175} rx={40} ry={29} fill="none" stroke={PAPER.front} strokeWidth={3} opacity={0.7} />
        </Sheet>
        <Label x={295} y={600} text="LICENSE 2019" size={32} delay={200} />
        <Label x={775} y={1560} text="CITIZEN 2025" size={32} delay={230} tint={PAPER.seal} />
      </g>
    </Stage>
  );
};

// ============================================== S7 THE TURN + THE DOOR (locked hold)
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fly = spring({frame: f - 8, fps, config: {damping: 14, stiffness: 90}});
  const anti = anticipate(f, 8, 9);
  const hit = f > 34;
  const door = ramp(f, 108, 140);
  const crumple = hit ? Math.max(0, 1 - (f - 34) / 26) : 0;
  return (
    <Stage drift={0.35}>
      <g opacity={1 - ramp(f, 100, 118)}>
        {/* the certificate, leaning, looking for a way around */}
        <Sheet x={90} y={1000} w={330} h={210} rot={-2 - crumple * 3}>
          <text x={24} y={54} fontFamily={MONO} fontSize={22} fill={INK} opacity={0.8}>NATURALIZATION 2025</text>
          <ellipse cx={250} cy={148} rx={50} ry={38} fill={PAPER.seal} stroke={INK} strokeWidth={4} />
        </Sheet>
        {/* the arrow, with anticipation, then a dead stop */}
        <g transform={`translate(${interpolate(fly, [0, 1], [430, 640]) - anti * 22},1090)`}>
          <MotionBlur vx={hit ? 0 : 40}>
            <path d="M0,-26 L120,-26 L120,-52 L190,0 L120,52 L120,26 L0,26 Z"
                  fill={PAPER.stamp} stroke={INK} strokeWidth={5}
                  transform={hit ? `scale(${1 - crumple * 0.1},${1 + crumple * 0.16})` : ''} />
          </MotionBlur>
        </g>
        {/* the wall. featureless. no handle, no seam, no villain. already infinite. */}
        <rect x={860} y={-200} width={70} height={2400} fill={PAPER.institution} stroke={INK} strokeWidth={5} />
        <rect x={860} y={-200} width={22} height={2400} fill="#fff" opacity={0.10} />
        <Label x={540} y={1620} text="NEITHER RECORD IS WRONG" size={44} delay={44} />
      </g>
      {/* the door swings FREELY open */}
      <g opacity={door}>
        <g transform={`translate(400,780)`}>
          <rect x={0} y={0} width={300} height={560} fill={PAPER.desk} stroke={INK} strokeWidth={5} />
          <g transform={`rotate(${-door * 62},0,0)`}>
            <rect x={0} y={0} width={300} height={560} fill={PAPER.mid} stroke={INK} strokeWidth={5} />
            <circle cx={258} cy={290} r={14} fill={PAPER.brass} stroke={INK} strokeWidth={4} />
            <g transform={`translate(150,${70 + Math.sin(f / 6) * 5}) rotate(${Math.sin(f / 5) * 6})`}>
              <rect x={-70} y={0} width={140} height={46} fill={PAPER.front} stroke={INK} strokeWidth={4} />
              <text x={0} y={33} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={26} fill={INK}>INACTIVE</text>
            </g>
          </g>
        </g>
        <Character frame={f} x={800} y={1240} scale={0.66} pose="stand" emotion="neutral" outfit="parka" headgear="bare" facing={-1} />
        <Label x={540} y={1700} text="INACTIVE IS NOT REMOVED" size={44} delay={116} tint={PAPER.seal} />
      </g>
    </Stage>
  );
};

// ================================== S8 NO ALGORITHM + THE SIGNATURE SHOT (pullback)
const S8: React.FC = () => {
  const f = useCurrentFrame();
  const stamp = ramp(f, 6, 18);
  const pull = ramp(f, 56, 130);
  return (
    <Stage push={interpolate(pull, [0, 1], [0.10, -0.16])} drift={0.9}>
      {/* the honest disclosure: no robot, no chip, no glowing brain. a card and a stamp. */}
      <g opacity={1 - ramp(f, 50, 66)}>
        <Sheet x={250} y={880} w={580} h={280} curl={0.3}>
          <text x={40} y={120} fontFamily={BOLD} fontWeight={900} fontSize={64} fill={INK}>NO ALGORITHM</text>
          <text x={40} y={200} fontFamily={MONO} fontSize={34} fill={INK} opacity={0.85}>A QUERY AND TWO DATABASES</text>
        </Sheet>
        <g transform={`translate(700,1230) rotate(${-12 + stamp * 12}) scale(${interpolate(stamp, [0, 1], [1.7, 1])})`} opacity={stamp}>
          <rect x={-120} y={-52} width={240} height={104} fill="none" stroke={PAPER.stamp} strokeWidth={9} />
          <text x={0} y={22} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={56}
                fill={PAPER.stamp}>NOT AI</text>
        </g>
      </g>
      {/* THE SIGNATURE SHOT: mouth wide, stem unchanged, both in ONE frame */}
      <g opacity={ramp(f, 58, 76)}>
        <RecordsMachine f={f} x={540} y={640} scale={0.78} mouthOpen={1} strain={ramp(f, 76, 130)} />
        {/* overflow spills toward FRAME CENTRE so the 4:5 crop cannot amputate it */}
        {Array.from({length: 20}).map((_, i) => {
          const h = Math.imul(i + 5, 2246822519) >>> 0;
          const t = ((f / 30) + (h % 100) / 100) % 1;
          const side = i % 2 ? 1 : -1;
          return (
            <rect key={i} x={540 + side * (150 - t * 96)} y={640 + t * 760} width={46} height={30}
                  fill={PAPER.front} stroke={INK} strokeWidth={2.4}
                  transform={`rotate(${side * (20 + t * 50)},${540 + side * 150},${640 + t * 760})`}
                  opacity={0.92 - t * 0.25} />
          );
        })}
        <Label x={540} y={1610} text="THE PART THAT CATCHES MISTAKES" size={34} delay={92} />
        {/* one clerk, one lamp, one clipboard umbrella */}
        <Character frame={f} x={540} y={1810} scale={0.72} pose="raise" emotion="worried" outfit="worker" headgear="bare" />
      </g>
    </Stage>
  );
};

// ======================================================= S9 BUTTON (stays interior)
const S9: React.FC = () => {
  const f = useCurrentFrame();
  const road = ramp(f, 14, 76);
  return (
    <Stage push={ramp(f, 0, 100) * 0.05} drift={0.5}>
      <PaperFiber id="s9fib" />
      {/* the EXACT table from frame one. the letter now face down. */}
      <StateLetter f={f} x={400} y={1040} scale={0.9} open={0} faceDown />
      <Sheet x={560} y={1150} w={330} h={210} fiber="s9fib" rot={3}>
        <text x={24} y={50} fontFamily={MONO} fontSize={22} fill={INK} opacity={0.8}>NATURALIZATION 2025</text>
        <ellipse cx={250} cy={148} rx={50} ry={38} fill={PAPER.seal} stroke={INK} strokeWidth={4} />
      </Sheet>
      {/* the connection that does not exist yet, drawn as an intention */}
      <path d={`M540,1120 C620,900 700,760 760,620`} fill="none" stroke={PAPER.stamp} strokeWidth={7}
            strokeDasharray="18 20" strokeDashoffset={-f * 1.5}
            opacity={road} strokeLinecap="round" pathLength={1}
            style={{strokeDasharray: `${road * 0.5} 0.5`} as React.CSSProperties} />
      {/* the capped pipe, still capped, still visible */}
      <g opacity={ramp(f, 10, 40)}>
        <TaperedCone x={790} y={560} mouthW={110} stemW={110} len={150} rings={2} />
        <ellipse cx={790} cy={556} rx={56} ry={17} fill={INK} opacity={0.9} />
        <line x1={720} y1={566} x2={860} y2={566} stroke={INK} strokeWidth={6} />
      </g>
      <Label x={540} y={380} text="STILL REGISTERED" size={54} tint={PAPER.seal} delay={20} />
    </Stage>
  );
};

// -------------------------------------------------------------------- assembly
const GradedGrade: React.FC = () => {
  const f = useCurrentFrame();
  return <GradeLayer f={f} bloom={0.10} vignette={0.24} grain={0.05} />;
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
      <div style={{background: 'rgba(24,30,36,0.90)', borderRadius: 14, padding: '16px 30px', maxWidth: 940,
        border: `4px solid ${PAPER.stamp}`, transform: `translateY(${rise}px) scale(${scale})`, transformOrigin: 'center bottom'}}>
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

const SCENE_COMPONENTS: React.FC[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9];
const DEFAULT_BOUNDS = [
  {from: 0, dur: 90}, {from: 90, dur: 210}, {from: 300, dur: 234}, {from: 534, dur: 153},
  {from: 687, dur: 183}, {from: 870, dur: 288}, {from: 1158, dur: 189}, {from: 1347, dur: 183},
  {from: 1530, dur: 180},
];

export const Episode: React.FC<EpisodeProps> = ({captions, scenes, mouth, accents}) => {
  const bounds = scenes && scenes.length === SCENE_COMPONENTS.length ? scenes : DEFAULT_BOUNDS;
  const voice = mouth && mouth.length ? {fps: 30, mouth, accents: accents ?? []} : null;
  return (
    <AbsoluteFill style={{backgroundColor: PAPER.institution}}>
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
