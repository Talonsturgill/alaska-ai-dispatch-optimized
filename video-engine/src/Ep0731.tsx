import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, Easing, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Gate, ThresholdGate, AperturePlate, CapClock} from './lib/civics';
import {ServerMachine} from './lib/kit';
import {Character} from './lib/Character';
import {TundraBG, OilfieldBG} from './lib/biomes';
import {Sheet, PaperFiber} from './lib/paper';
import {StatCard, Nameplate, SurveyStake, MeasuringChain, BoundaryReveal, TallyCounter} from './lib/props';
import {PaperStorm} from './lib/FX';
import {DayGrade, tones, FormGradient, ContactShadow} from './lib/lighting';
import {MaterialDefs, matFill} from './lib/materials';
import {entrance, vitals, EASE} from './lib/motion';

// =============================================================================
// DISPATCH 2026-07-31 — "THE GATE WITH NO NUMBER"
//
// Storyboard: out/dispatch/storyboard.json   Art direction: out/dispatch/art_direction.json
// Thesis: a freeze with no size threshold adds little where a gas shortage already
// blocks a project, and is decisive only at the wellhead, where nothing else reaches.
//
// THE BINDING PALETTE RULE (art_direction.json): RED IS THE THRESHOLD AND ONLY THE
// THRESHOLD, with exactly TWO licensed uses in the whole film — the red band on New
// York's bounded plate, and the red edge of the slot when it is cut. Every asset whose
// shelf default is red is PINNED to a non-red value at its call site below, because
// Gate 0D was right that a rule with no mechanism is only a convention. Most important:
// THE BOOM STRIPES ARE SLATE ON BONE. A striped barrier boom defaults to red and white
// in every reference, and this boom is frame 0, the last frame, and the loop image.
//
// SEASON IS PINNED TO LATE ARCTIC SUMMER. Cottongrass and dust, never snow. Sun sits
// UPPER SCREEN LEFT and every rim light in all twelve scenes derives from that bearing.
//
// THE SIGNATURE MOTION is THE FALL THAT NEVER VARIES: the freeze's boom falls with
// identical anticipation, identical +3 frame impact and ZERO hold frames over every
// load, however big or small, while the conditional gates HESITATE for different counts
// before ruling. A rule that weighs visibly takes different amounts of time to weigh.
// =============================================================================

const INK = '#1b232b';
const SKY = '#c3d3de';
const GROUND = '#b9a074';
const GRAVEL = '#8c8577';
const STEEL = '#93a0ad';
const BONE = '#eef3f7';
const CITRON = '#b9d24a';
/** LICENSED USE ONLY: the bounded plate's band, and the cut slot's edge. Nowhere else. */
const THRESHOLD_RED = '#c0392b';
const BOLD = 'Arial Black, Arial, sans-serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

/** the 4:5 LinkedIn crop is the deliverable, so every load-bearing element lives here */
const SAFE_TOP = 285;
const SAFE_BOT = 1635;

/**
 * NOTE THE `grade` SLOT. DayGrade emits HTML <div>s, and a <div> created inside an <svg>
 * lands in the SVG namespace and paints NOTHING. That is the silent bug that made the
 * ENTIRE 2026-07-30 night grade a no-op in the shipped film while look-dev looked graded.
 * The slot makes the correct placement the only placement a scene can use.
 */
const Stage: React.FC<{children: React.ReactNode; grade?: React.ReactNode; bg?: string}> = ({
  children, grade, bg = SKY,
}) => (
  <AbsoluteFill style={{backgroundColor: bg}}>
    <svg viewBox="0 0 1080 1920" width="1080" height="1920">
      <MaterialDefs />
      {children}
    </svg>
    {grade}
  </AbsoluteFill>
);

/** the standing daylight grade for this film. One bearing, upper screen left. */
const Day: React.FC<{f: number; amount?: number; haze?: number}> = ({f, amount = 0.9, haze = 0.34}) => (
  <DayGrade f={f} amount={amount} floor={0.55} haze={haze} sunX={210} sunY={250} sunIntensity={0.5} />
);

/** A flat gravel road plane with a receding centre line. The film's ground. */
const Road: React.FC<{f: number; y?: number; drift?: number}> = ({f, y = 1180, drift = 0}) => (
  <g>
    <rect x={0} y={y} width={1080} height={1920 - y} fill={GRAVEL} />
    <rect x={0} y={y} width={1080} height={1920 - y} fill={matFill('tarmac')} opacity={0.5} />
    <path d={`M0,${y} L1080,${y}`} stroke={INK} strokeWidth={5} opacity={0.5} />
    {/* receding centre dashes */}
    {Array.from({length: 7}).map((_, i) => {
      const p = i / 7;
      const yy = y + 40 + p * p * 640;
      const w = 16 + p * 54;
      return <rect key={i} x={540 - w / 2 + drift * (1 - p) * 60} y={yy} width={w} height={9 + p * 16} rx={4} fill={BONE} opacity={0.5} />;
    })}
    {/* low summer dust, never snow */}
    {Array.from({length: 22}).map((_, i) => {
      const s = (i * 71) % 100 / 100;
      const x = ((s * 1400 + f * (1.1 + s)) % 1240) - 80;
      const yy = y + 60 + ((i * 37) % 520);
      return <circle key={i} cx={x} cy={yy} r={2 + s * 3} fill={BONE} opacity={0.14 + s * 0.12} />;
    })}
  </g>
);

/** open summer tundra: cottongrass, kettle ponds, a flat horizon. Pinned season. */
const Tundra: React.FC<{f: number; y?: number}> = ({f, y = 1120}) => (
  <g>
    <TundraBG f={f} season="summer" wind={0.55} groundY={y} />
  </g>
);

/** a hard boxed plate in the house register */
const Plate: React.FC<{x: number; y: number; text: string; sub?: string; sub2?: string; op?: number; w?: number; size?: number}> = ({
  x, y, text, sub, sub2, op = 1, w = 700, size = 38,
}) => {
  const h = sub2 ? 176 : sub ? 132 : 88;
  return (
    <g transform={`translate(${x},${y})`} opacity={op}>
      <ContactShadow cx={0} cy={h / 2 + 12} rx={w / 2 * 0.9} ry={13} opacity={0.3} />
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={10} fill="#f7fafc" stroke={INK} strokeWidth={6} />
      <rect x={-w / 2 + 5} y={-h / 2 + 5} width={w - 10} height={h * 0.28} rx={7} fill="#ffffff" opacity={0.5} />
      <text x={0} y={sub ? -8 : 13} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={size}
        fill={INK} letterSpacing={0.6}>{text}</text>
      {sub && (
        <text x={0} y={sub2 ? 28 : 38} textAnchor="middle" fontFamily={MONO} fontWeight={600} fontSize={21}
          fill="#5c6b78" letterSpacing={0.9}>{sub}</text>
      )}
      {sub2 && (
        <text x={0} y={62} textAnchor="middle" fontFamily={MONO} fontWeight={600} fontSize={19}
          fill="#5c6b78" letterSpacing={0.6}>{sub2}</text>
      )}
    </g>
  );
};

/** THE FALL THAT NEVER VARIES. Identical anticipation, identical impact, zero hold,
 *  regardless of what is underneath it. Callers pass only the frame it starts on. */
function theFall(f: number, at: number): {angle: number; impact: number} {
  const l = f - at;
  if (l < 0) return {angle: -76, impact: 0};
  // 8 frames of anticipation (it lifts slightly), then 7 frames of fall, then recoil
  const lift = interpolate(l, [0, 8], [0, -6], {extrapolateRight: 'clamp'});
  const drop = interpolate(l, [8, 15], [0, 76], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.enter)});
  const recoil = l > 15 ? Math.sin((l - 15) / 2.4) * Math.max(0, 7 - (l - 15) * 0.55) : 0;
  return {angle: -76 + lift + drop + recoil, impact: l >= 18 && l < 24 ? 1 - (l - 18) / 6 : 0};
}

/* ---------------------------------------------------------------------------
   S1 — THE ROAD. The boom slams, the machine skids short, the candidate and the
   money are named and bounded in the same world. VO line 0.
--------------------------------------------------------------------------- */
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  // THE POSTER GRADE: frame 0 must already be mid-fall, so the fall starts BEFORE zero.
  const fall = theFall(f, -9);
  const skid = entrance(f, fps, 0.9, {drop: 0});
  const card = entrance(f, fps, 3.4, {drop: 26});
  const money = entrance(f, fps, 4.9, {drop: 22});
  return (
    <Stage grade={<Day f={f} />}>
      <Tundra f={f} y={780} />
      <Road f={f} y={1010} />
      {/* the freeze, large and centre-left, mid-fall in frame 0 */}
      <g transform="translate(430,1010) scale(1.34)">
        <ThresholdGate f={f} x={0} y={0} boom={interpolate(fall.angle, [-76, 0], [0, 1])}
          cut={0} cutW={130} hands={0} lamp={0} scale={1} phase={0.1} tint={STEEL} />
      </g>
      {/* the applicant, skidding up short and SMALLER than the instrument */}
      <g transform={`translate(${880 - (1 - skid.t) * 150},960) scale(${0.5 + skid.t * 0.03})`}>
        <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={1} facing={-1} tint="steel" />
      </g>
      {fall.impact > 0 && (
        <g opacity={fall.impact}>
          {Array.from({length: 11}).map((_, i) => (
            <circle key={i} cx={520 + i * 26} cy={1016 + ((i * 17) % 26)} r={4 + (i % 3) * 4} fill={BONE} opacity={0.55} />
          ))}
        </g>
      )}
      <g opacity={card.t}>
        <Nameplate x={540} y={SAFE_TOP + 8 + (1 - card.t) * 24} text="KREISS-TOMKINS" sub="candidate for governor" subColor="#5c6b78" />
      </g>
      <g opacity={money.t}>
        <Plate x={540} y={SAFE_TOP + 210 + (1 - money.t) * 20} w={920} size={30}
          text="$372,000 FROM SIX ANTHROPIC EMPLOYEES"
          sub="as individuals. the company gave nothing."
          sub2={'"The views in his op-ed are his alone and do not represent Anthropic."'} />
      </g>
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S2 — BEHIND THE GATE. A new vantage, not a magnification (Gate 0B). The empty
   ghost cut frames the applicant it cannot measure. VO line 1.
--------------------------------------------------------------------------- */
const S2: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const arrive = entrance(f, fps, 0.2, {drop: 0});
  const clockIn = entrance(f, fps, 1.8, {drop: 18});
  const plateT = tones(STEEL);
  return (
    <Stage grade={<Day f={f} haze={0.28} />}>
      <Tundra f={f} y={980} />
      <Road f={f} y={1240} />
      {/* the plate from BEHIND, backlit by the overcast */}
      <g transform={`translate(540,900) scale(${1.5 + arrive.t * 0.12})`}>
        <defs><FormGradient id="s2plate" t={plateT} softness={0.9} /></defs>
        <ContactShadow cx={0} cy={230} rx={150} ry={22} opacity={0.3} />
        <rect x={-150} y={-190} width={300} height={420} rx={10} fill={plateT.shade} stroke={INK} strokeWidth={9} />
        <rect x={-150} y={-190} width={300} height={420} rx={10} fill="url(#s2plate)" opacity={0.4} />
        {/* the opening that was never made, dashed, backlit */}
        <rect x={-92} y={-10} width={184} height={132} rx={7} fill="none" stroke={BONE}
          strokeWidth={7} strokeDasharray="17 16" opacity={0.72} />
        <text x={0} y={196} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={30}
          fill={BONE} opacity={0.8} letterSpacing={2.4}>NO CUT</text>
        {/* the machine, small and soft, seen through where the slot should be */}
        <g opacity={0.5} style={{filter: 'blur(2.4px)'}}>
          <ServerMachine frame={f} emotion="focused" x={0} y={58} scale={0.2} tint="steel" />
        </g>
      </g>
      <g opacity={clockIn.t} transform={`translate(540,${SAFE_TOP + 130 - (1 - clockIn.t) * 20})`}>
        <Plate x={0} y={0} w={640} text="NO END DATE" size={40} />
      </g>
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S3 — THREE GATES STAND UP. The mechanism that already exists, and it is
   physical rather than political. VO line 2.
--------------------------------------------------------------------------- */
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const rise = [0.1, 0.5, 0.95].map((d) => entrance(f, fps, d, {drop: 40}));
  return (
    <Stage grade={<Day f={f} />}>
      <Tundra f={f} y={1000} />
      <Road f={f} y={1190} />
      {[
        {x: 230, cond: 'DO YOU HAVE GAS', src: 'CHUGACH ELECTRIC', v: 'asking' as const, s: 0.62, ph: 0},
        {x: 540, cond: 'IS THERE POWER HERE', src: 'AIR FORCE SOLICITATION', v: 'asking' as const, s: 0.68, ph: 0.33},
        {x: 855, cond: 'SHOW UTILITY CAPACITY', src: 'AO 2026-27', v: 'asking' as const, s: 0.62, ph: 0.71},
      ].map((g, i) => (
        <g key={i} opacity={rise[i].t} transform={`translate(0,${(1 - rise[i].t) * 70})`}>
          <Gate f={f} x={g.x} y={1190} condition={g.cond} source={g.src} verdict={g.v}
            scale={g.s} phase={g.ph} tint={STEEL} />
        </g>
      ))}
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S4 — TWO VERDICTS, THE GAUGE, THE TALLY, AND THE PLATE THAT STOPS BOTH.
   The conditional gates HESITATE for different counts before ruling. The freeze
   does not hesitate at all. VO lines 3 to 4. Open loop plants here.
--------------------------------------------------------------------------- */
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  // gate one holds 9 frames before ruling, gate two holds 14. The difference IS the point.
  const g1 = f > 30 + 9 ? 'block' : 'asking';
  const g2 = f > 150 + 14 ? 'pass' : 'asking';
  const needle = interpolate(f, [40, 62], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.enter)});
  const tally = entrance(f, fps, 5.4, {drop: 20});
  // the plate stops a small machine and then a huge one, identically
  const small = interpolate(f, [212, 230], [1180, 690], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const bigIn = interpolate(f, [248, 268], [1240, 700], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const bounce1 = f >= 230 && f < 244 ? Math.sin((f - 230) / 2.2) * 26 * (1 - (f - 230) / 14) : 0;
  const bounce2 = f >= 268 && f < 284 ? Math.sin((f - 268) / 2.2) * 26 * (1 - (f - 268) / 16) : 0;
  const showPlate = f > 200;
  return (
    <Stage grade={<Day f={f} />}>
      <Tundra f={f} y={1000} />
      <Road f={f} y={1190} />
      {!showPlate && (
        <>
          <Gate f={f} x={330} y={1190} condition="DO YOU HAVE GAS" source="CHUGACH ELECTRIC"
            verdict={g1} scale={0.72} phase={0} tint={STEEL} />
          <Gate f={f} x={790} y={1190} condition="SHOW UTILITY CAPACITY" source="AO 2026-27"
            verdict={g2} scale={0.72} phase={0.4} tint={STEEL} />
          {/* the fuel gauge on gate one's post: the Railbelt constraint made physical */}
          <g transform="translate(330,880)">
            <circle cx={0} cy={0} r={62} fill="#eef3f7" stroke={INK} strokeWidth={7} />
            {Array.from({length: 5}).map((_, i) => {
              const a = (-58 + i * 29) * Math.PI / 180;
              return <line key={i} x1={Math.sin(a) * 34} y1={-Math.cos(a) * 34} x2={Math.sin(a) * 50}
                y2={-Math.cos(a) * 50} stroke={INK} strokeWidth={5} strokeLinecap="round" />;
            })}
            <g transform={`rotate(${-56 + needle * 108} 0 0)`}>
              <path d="M0,-50 L6,0 L-6,0 Z" fill={INK} />
            </g>
            <circle cx={0} cy={0} r={9} fill="#2b333b" stroke={INK} strokeWidth={4} />
            <text x={0} y={92} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={22}
              fill={INK} letterSpacing={1.4}>GAS</text>
          </g>
          <g opacity={tally.t}>
            <Plate x={790} y={840} w={330} size={40} text="10 TO 2" />
          </g>
          <Plate x={540} y={SAFE_BOT - 150} w={900} size={31}
            text="IT HAS THE GENERATORS, NOT THE GAS" sub="Chugach Electric, per ADN, May 2026" />
        </>
      )}
      {showPlate && (
        <>
          {/* THE PLATE STOPS BOTH. Same refusal, two wildly different loads. */}
          <ThresholdGate f={f} x={430} y={1190} boom={1} cut={0} cutW={130} hands={0} lamp={0}
            scale={1.0} phase={0.2} tint={STEEL} />
          <g transform={`translate(${small + bounce1},1090)`}>
            <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={0.34} facing={-1} tint="steel" />
          </g>
          <g transform={`translate(${bigIn + bounce2},1000)`} opacity={f > 244 ? 1 : 0}>
            <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={1.15} facing={-1} tint="steel" />
          </g>
          <Plate x={540} y={SAFE_BOT - 150} w={880} size={33} text="TWO NUMBERS DECIDE WHO THIS CATCHES" />
        </>
      )}
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S5 — THE ROAD ENDS. Travel past the edge of the regime. VO line 5.
--------------------------------------------------------------------------- */
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const push = interpolate(f, [0, 130], [0, 1], {extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  return (
    <Stage grade={<Day f={f} haze={0.42} />}>
      <g transform={`translate(0,${-push * 90}) scale(${1 + push * 0.07})`} style={{transformOrigin: '540px 960px'}}>
        <rect x={-900} y={-900} width={2880} height={3720} fill={SKY} />
        <rect x={-900} y={900} width={2880} height={1840} fill="#7f9463" />
        <Tundra f={f} y={900 + push * 60} />
        {/* the road runs out */}
        <path d={`M${380 - push * 120},1920 L${470},${1180} L${610},${1180} L${700 + push * 120},1920 Z`}
          fill={GRAVEL} />
        <path d={`M${380 - push * 120},1920 L${470},${1180} L${610},${1180} L${700 + push * 120},1920 Z`}
          fill={matFill('tarmac')} opacity={0.45} />
        <path d={`M470,1180 L610,1180`} stroke={INK} strokeWidth={6} opacity={0.55} />
        {/* the last gate post, leaving frame */}
        <g opacity={1 - push * 0.85} transform={`translate(${300 - push * 240},${1240 + push * 200}) scale(${0.62 - push * 0.2})`}>
          <Gate f={f} x={0} y={0} condition="SHOW UTILITY CAPACITY" source="AO 2026-27" verdict="pass" scale={1} tint={STEEL} />
        </g>
      </g>
      <Plate x={540} y={SAFE_BOT - 140} w={780} size={35} text="NEITHER GATE REACHES HERE" op={Math.min(1, push * 2.2)} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S6 — THE PARCEL, AND FIFTY YEARS. Built at eye level and on the ground, in this
   film's own grammar rather than the aerial parcel treatment a prior dispatch used
   on this same lease (Gate 0B). VO line 6. First scale reveal.
--------------------------------------------------------------------------- */
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const chain = interpolate(f, [10, 70], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const bound = interpolate(f, [60, 108], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const years = Math.max(0, Math.min(50, Math.round((f - 112) / 1.5)));
  const pull = interpolate(f, [112, 176], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const stake = (i: number) => entrance(f, fps, 0.6 + i * 0.45, {drop: 30});
  return (
    <Stage grade={<Day f={f} haze={0.38} />}>
      <g transform={`scale(${1 - pull * 0.34})`} style={{transformOrigin: '540px 1100px'}}>
        <rect x={-900} y={-900} width={2880} height={3720} fill={SKY} />
        <rect x={-900} y={980} width={2880} height={1840} fill="#7f9463" />
        <Tundra f={f} y={980} />
        {[210, 470, 730, 950].map((x, i) => (
          <g key={i} opacity={stake(i).t}>
            <SurveyStake x={x} y={1210 + (i % 2) * 30} s={1.05} settle={stake(i).t} tag={false} />
          </g>
        ))}
        <MeasuringChain x1={210} y1={1240} x2={210 + chain * 740} y2={1268} taut={chain} />
        <g opacity={bound}>
          <BoundaryReveal revealT={bound} d="M180,1300 L960,1258 L1000,1520 L215,1560 Z" perim={2600} accent={BONE} />
        </g>
        {/* the lease bar, ratcheting one click per year along the ground plane */}
        <g transform="translate(150,1420)">
          <rect x={0} y={-16} width={780} height={32} rx={6} fill="#6f7a83" stroke={INK} strokeWidth={5} />
          <rect x={0} y={-16} width={780 * (years / 50)} height={32} rx={6} fill={BONE} stroke={INK} strokeWidth={5} />
          {Array.from({length: 11}).map((_, i) => (
            <line key={i} x1={i * 78} y1={-22} x2={i * 78} y2={22} stroke={INK} strokeWidth={3} opacity={0.5} />
          ))}
          <text x={390} y={-52} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={48}
            fill={INK} stroke="#f7fafc" strokeWidth={6} paintOrder="stroke">{years} YEARS</text>
        </g>
      </g>
      <Plate x={540} y={SAFE_TOP + 90} w={860} size={32}
        text="715.4 ACRES OF STATE LAND" sub="preliminary decision, this spring" op={Math.min(1, chain * 1.6)} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S7 — THE BOOK THAT WAS NEVER WRITTEN. The absence is PERFORMED, not displayed
   (Gate 0C killed the zero-motion still life). VO line 7.
--------------------------------------------------------------------------- */
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const drop = entrance(f, fps, 0.4, {drop: 120});
  const riffle = interpolate(f, [34, 116], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const page = Math.floor(riffle * 13);
  return (
    <Stage grade={<Day f={f} amount={0.7} haze={0.2} />} bg="#c9d3d9">
      <rect x={0} y={0} width={1080} height={1920} fill="#b9c3ca" />
      <rect x={0} y={1180} width={1080} height={740} fill="#8d7a5f" />
      <rect x={0} y={1180} width={1080} height={740} fill={matFill('planks')} opacity={0.4} />
      {/* the bound statute book, open on two blank pages */}
      <g transform="translate(540,1010)">
        <ContactShadow cx={0} cy={250} rx={430} ry={40} opacity={0.34} />
        <rect x={-440} y={-40} width={880} height={300} rx={12} fill="#5d6a54" stroke={INK} strokeWidth={8} />
        <Sheet x={-215} y={80} w={410} h={300} fiber="s7f" />
        <Sheet x={215} y={80} w={410} h={300} fiber="s7f" />
        <line x1={0} y1={-70} x2={0} y2={244} stroke={INK} strokeWidth={6} opacity={0.6} />
        {/* every page passes empty */}
        {riffle > 0.02 && riffle < 0.99 && Array.from({length: 4}).map((_, i) => {
          const a = -70 + ((page + i) % 14) * 11;
          return (
            <g key={i} transform={`rotate(${a} 0 100)`} opacity={0.85}>
              <rect x={-8} y={-52} width={412} height={296} rx={6} fill="#f4f0e4" stroke={INK} strokeWidth={4} />
            </g>
          );
        })}
        <defs><PaperFiber id="s7f" /><PaperFiber id="s7g" /></defs>
      </g>
      {/* the lease lands on it */}
      <g transform={`translate(540,${820 + (1 - drop.t) * -260}) rotate(${-6 + drop.t * 6})`} opacity={drop.t}>
        <Sheet x={0} y={0} w={330} h={230} fiber="s7g" curl={0.5} />
        <text x={0} y={10} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={24}
          fill={INK} letterSpacing={1}>50 YEAR LEASE</text>
      </g>
      <Plate x={540} y={SAFE_BOT - 130} w={840} size={34} text="NO STATUTE ON WHO PAYS" op={Math.min(1, riffle * 2)} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S8 — FIVE HUNDRED, AND ELEVEN ON TOP. The public used the only open door.
   VO line 8.
--------------------------------------------------------------------------- */
const S8: React.FC = () => {
  const f = useCurrentFrame();
  const pile = interpolate(f, [8, 120], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const eleven = interpolate(f, [118, 152], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage grade={<Day f={f} amount={0.75} haze={0.24} />} bg="#c6d0d6">
      <rect x={0} y={1330} width={1080} height={590} fill="#8d7a5f" />
      <rect x={0} y={1330} width={1080} height={590} fill={matFill('planks')} opacity={0.4} />
      {/* the stack, climbing past frame */}
      {Array.from({length: 34}).map((_, i) => {
        const p = i / 34;
        if (p > pile) return null;
        const y = 1330 - i * 30;
        const sk = ((i * 53) % 21) - 10;
        return (
          <g key={i} transform={`translate(${540 + sk},${y}) rotate(${sk * 0.35})`}>
            <rect x={-230} y={-26} width={460} height={30} rx={4} fill="#f4f0e4" stroke={INK} strokeWidth={4} />
          </g>
        );
      })}
      <PaperStorm frame={f} count={26} originX={1180} originY={400} targetX={540} targetY={1200} spread={340} />
      {/* eleven, separately countable, on top */}
      <g opacity={eleven}>
        {Array.from({length: 11}).map((_, i) => (
          <rect key={i} x={318 + i * 40} y={1330 - 34 * 30 - 40} width={30} height={26} rx={4}
            fill={CITRON} stroke={INK} strokeWidth={4} />
        ))}
      </g>
      <Plate x={540} y={SAFE_TOP + 120} w={900} size={33}
        text="MORE THAN 500 COMMENTS" sub="fewer than a dozen supportive" op={Math.min(1, pile * 1.8)} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S9 — THE GROUND GIVES WAY, AND OUR OWN LIMIT. The concession is staged NORTH of
   the last gate post, rhyming with S5's crane, because a hole between the working
   gates would contradict the film's own geography (Gate 0B). VO lines 9 to 10.
--------------------------------------------------------------------------- */
const S9: React.FC = () => {
  const f = useCurrentFrame();
  const roll = interpolate(f, [10, 96], [-240, 1200], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const pull = interpolate(f, [130, 250], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  return (
    <Stage grade={<Day f={f} haze={0.4} />}>
      <g transform={`scale(${1 - pull * 0.52})`} style={{transformOrigin: '540px 1150px'}}>
        <rect x={-900} y={-900} width={2880} height={3720} fill={SKY} />
        <rect x={-900} y={1000} width={2880} height={1840} fill="#7f9463" />
        <Tundra f={f} y={1000} />
        {/* the short strip of road, with the three gates clustered on it */}
        <rect x={80} y={1180} width={620} height={120} fill={GRAVEL} />
        <rect x={80} y={1180} width={620} height={120} fill={matFill('tarmac')} opacity={0.45} />
        {[170, 380, 590].map((x, i) => (
          <Gate key={i} f={f} x={x} y={1190} condition={['GAS', 'POWER', 'CAPACITY'][i]}
            source="" verdict="pass" scale={0.32} phase={i * 0.31} tint={STEEL} />
        ))}
        {/* a machine rolls past the last post into open ground, unchallenged */}
        <g transform={`translate(${roll},1120)`}>
          <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={0.42} facing={1} tint="steel" />
        </g>
      </g>
      <Plate x={540} y={SAFE_TOP + 110} w={820} size={35} text="HE IS RIGHT THAT THERE IS A HOLE"
        op={Math.min(1, interpolate(f, [60, 90], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}))} />
      <Plate x={540} y={SAFE_BOT - 140} w={900} size={32} text="ANCHORAGE IS ONE BOROUGH"
        sub="a patchwork, not a process" op={Math.min(1, pull * 2)} />
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S10 — THE COMPARISON. New York's rig arrives, the slot is CUT ON SCREEN and
   throws a bar of daylight through, then a pan to where no light comes through.
   Then the two clocks, where the empty hub is the ONLY absolutely still thing in
   frame. VO lines 11 to 13. Open loop pays here.
--------------------------------------------------------------------------- */
const S10: React.FC = () => {
  const f = useCurrentFrame();
  const arrive = interpolate(f, [0, 26], [0, 1], {extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.overshoot)});
  const cut = interpolate(f, [8, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.enter)});
  const rack = interpolate(f, [156, 190], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const sweep = interpolate(f, [192, 252], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const labels = interpolate(f, [270, 296], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage grade={<Day f={f} haze={0.3} />}>
      <Tundra f={f} y={860} />
      <Road f={f} y={1120} />
      {/* THE TURN, staged on the plates alone so each one fills its half of the frame */}
      <g transform={`translate(0,${-rack * 250})`}>
        {/* the bar of daylight through the cut, drawn UNDER the plate so it reads as light */}
        {cut > 0.9 && (
          <path d={`M228,912 L372,912 L440,1400 L160,1400 Z`} fill="#fff6dd" opacity={0.34 * cut} />
        )}
        <g transform={`translate(${300 - (1 - arrive) * 90},760) scale(1.45)`} opacity={Math.min(1, arrive * 1.4)}>
          <AperturePlate f={f} x={0} y={0} cut={cut} cutW={140} cutLabel="BIGGEST SITES ONLY" tint={STEEL} />
        </g>
        <g transform="translate(780,760) scale(1.45)">
          <AperturePlate f={f} x={0} y={0} cut={0} cutW={140} tint={STEEL} />
        </g>
        {/* the jurisdiction plates are withheld until the slot exists, so no frame ever
            pairs the label NEW YORK with the words NO CUT (panel judge 1 hard fail) */}
        <g opacity={cut > 0.92 ? 1 : 0}>
          <Nameplate x={300} y={1290} text="NEW YORK" subColor="#5c6b78" />
          <Nameplate x={780} y={1290} text="ALASKA" subColor="#5c6b78" />
        </g>
      </g>
      {/* racked up: the two clocks, one sweeping a year, one absolutely still */}
      <g opacity={rack} transform={`translate(0,${(1 - rack) * 220})`}>
        <CapClock f={f} x={300} y={620} hands={1} sweep={sweep} scale={1.7} tint={STEEL} />
        <CapClock f={f} x={780} y={620} hands={0} scale={1.7} tint={STEEL} />
        <Plate x={300} y={800} w={400} size={26} text="ENDS AFTER A YEAR" />
        <Plate x={780} y={800} w={400} size={26} text="NO END DATE" />
      </g>
      <g opacity={labels}>
        <Plate x={540} y={SAFE_BOT - 150} w={900} size={33} text="NO SIZE LIMIT   AND   NO END DATE" />
      </g>
      <g opacity={(1 - labels) * Math.min(1, cut * 2)}>
        <Plate x={540} y={SAFE_BOT - 150} w={900} size={31} text="ONE LETS A SIZE THROUGH" />
      </g>
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S11 — ONE SHADOW, TWO OUTCOMES, then the wellhead. The inversion in ONE FRAME,
   which is the fingerprint's declared fullbleed-split finally delivered at the
   payoff (Gate 0B's headline fix). VO lines 14 to 15.
--------------------------------------------------------------------------- */
const S11: React.FC = () => {
  const f = useCurrentFrame();
  const shadow = interpolate(f, [14, 96], [-460, 1560], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const fall = theFall(f, 74);
  const toWide = interpolate(f, [176, 250], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const pullOut = interpolate(f, [250, 350], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  return (
    <Stage grade={<Day f={f} haze={0.34} />}>
      {toWide < 0.5 ? (
        <>
          {/* LEFT: already stopped. RIGHT: the only thing in the way. One seam. */}
          <g>
            <Tundra f={f} y={1040} />
            <rect x={0} y={1180} width={540} height={740} fill={GRAVEL} />
            <rect x={0} y={1180} width={540} height={740} fill={matFill('tarmac')} opacity={0.45} />
            <g transform="translate(160,1180) scale(0.62)">
              <Gate f={f} x={0} y={0} condition="DO YOU HAVE GAS" source="CHUGACH" verdict="block" scale={1} tint={STEEL} />
            </g>
            <g transform="translate(370,1110)">
              <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={0.4} facing={-1} tint="steel" />
            </g>
          </g>
          <g>
            <rect x={540} y={0} width={540} height={1920} fill="none" />
            <g transform="translate(540,0)">
              <OilfieldBG f={f} season="summer" flare={0.32} />
            </g>
            <g transform="translate(820,1130)">
              <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={0.48} facing={1} tint="copper" />
            </g>
            {/* the freeze's boom, falling with the SAME fall it has used all film */}
            <g transform={`translate(690,980)`}>
              <g transform={`rotate(${fall.angle} 0 0)`}>
                <rect x={0} y={-11} width={240} height={22} rx={8} fill={STEEL} stroke={INK} strokeWidth={6} />
                {Array.from({length: 5}).map((_, i) => (
                  <rect key={i} x={12 + i * 44} y={-11} width={22} height={22}
                    fill={i % 2 === 0 ? INK : BONE} opacity={0.85} />
                ))}
              </g>
              <circle cx={0} cy={0} r={12} fill="#232c34" stroke={INK} strokeWidth={5} />
            </g>
          </g>
          {/* the hard centre seam */}
          <rect x={536} y={0} width={9} height={1920} fill={INK} />
          {/* ONE shadow crossing both panels */}
          <rect x={shadow} y={0} width={300} height={1920} fill="#0d1620" opacity={0.26} />
          <Plate x={280} y={SAFE_BOT - 120} w={470} size={27} text="ALREADY STOPPED" />
          <Plate x={800} y={SAFE_BOT - 120} w={470} size={25} text="THE ONLY THING IN THE WAY" />
        </>
      ) : (
        <>
          {/* the signature shot, read in DEPTH so the 4:5 crop cannot amputate it */}
          <g transform={`scale(${1.9 - pullOut * 1.15})`} style={{transformOrigin: '620px 1320px'}}>
            <rect x={-1200} y={-1200} width={3480} height={4320} fill="#b8c6cf" />
            <OilfieldBG f={f} season="summer" flare={0.3} />
            <g transform="translate(660,1240)">
              <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={0.6} facing={1} tint="copper" />
              {/* its own generator and the umbilical into the gas beneath its feet */}
              <rect x={92} y={-38} width={92} height={78} rx={9} fill="#7d6a52" stroke={INK} strokeWidth={6} />
              <circle cx={138} cy={0} r={19} fill={BONE} stroke={INK} strokeWidth={5} />
              <g transform={`rotate(${f * 7} 138 0)`}>
                <rect x={135} y={-16} width={6} height={32} rx={3} fill={INK} />
              </g>
              <path d="M120,40 C120,110 96,150 96,210" stroke={INK} strokeWidth={13} fill="none" strokeLinecap="round" />
              <path d="M120,40 C120,110 96,150 96,210" stroke="#a08a68" strokeWidth={7} fill="none" strokeLinecap="round" />
            </g>
            {/* the household, small on the FAR plane, and the line that never arrives */}
            <g opacity={pullOut} transform="translate(150,890) scale(0.5)">
              <rect x={-58} y={-52} width={116} height={94} rx={6} fill="#8f9aa3" stroke={INK} strokeWidth={6} />
              <path d="M-70,-52 L0,-104 L70,-52 Z" fill="#6f7a83" stroke={INK} strokeWidth={6} />
              <rect x={-22} y={-24} width={44} height={38} rx={4} fill="#ffe9c8" stroke={INK} strokeWidth={4} />
            </g>
            <g opacity={pullOut}>
              <path d="M212,930 C330,1010 420,1080 470,1150" stroke={INK} strokeWidth={7}
                strokeDasharray="20 18" fill="none" opacity={0.75} />
              <circle cx={470} cy={1150} r={9} fill={INK} opacity={0.75} />
            </g>
          </g>
          <Plate x={540} y={SAFE_BOT - 130} w={900} size={32} text="IT MAKES ITS OWN POWER"
            sub="the line from the household never arrives" op={pullOut} />
        </>
      )}
    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S12 — THE MISSING QUESTION, THE FIELD, AND THE BUTTON. Loops to frame 0.
   VO lines 16 to 18.
--------------------------------------------------------------------------- */
const S12: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seat = entrance(f, fps, 0.5, {drop: 40});
  const slot = interpolate(f, [58, 84], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.enter)});
  const plates = interpolate(f, [150, 210], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const turn = interpolate(f, [232, 262], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const q1 = entrance(f, fps, 10.2, {drop: 34});
  const q2 = entrance(f, fps, 10.9, {drop: 34});
  const rise = interpolate(f, [346, 420], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bezier(...EASE.move)});
  const showField = f > 140 && f < 300;
  return (
    <Stage grade={<Day f={f} />}>
      <Tundra f={f} y={1010} />
      <Road f={f} y={1180} />
      {!showField && (
        <g transform="translate(560,1180)">
          <ThresholdGate f={f} x={0} y={0} boom={interpolate(rise, [0, 1], [1, 0])}
            cut={slot} cutW={140} cutLabel="WHERE THE POWER COMES FROM" hands={0} lamp={slot > 0.6 ? 1 : 0}
            scale={1.05} phase={0.1} tint={STEEL} />
          {slot > 0.5 && (
            <path d="M-248,-22 L-124,-22 L-70,540 L-300,540 Z" fill="#fff6dd" opacity={0.26 * slot} />
          )}
        </g>
      )}
      {!showField && (
        <g opacity={seat.t}>
          <Plate x={540} y={SAFE_TOP + 110} w={900} size={30}
            text="CONDITION IT ON WHERE THE POWER COMES FROM" sub="not on whether the building is new" />
        </g>
      )}
      {showField && (
        <g opacity={plates}>
          {Array.from({length: 17}).map((_, i) => {
            const col = i % 5, row = Math.floor(i / 5);
            const t = Math.max(0, Math.min(1, (plates * 17 - i) / 1.4));
            return (
              <g key={i} transform={`translate(${186 + col * 168},${760 + row * 132}) scale(${0.5 * t})`} opacity={t}>
                <rect x={-150} y={-44} width={300} height={88} rx={9}
                  fill={i === 0 ? BONE : '#aab5be'} stroke={INK} strokeWidth={7} />
                <rect x={-142} y={-38} width={284} height={22} rx={5} fill="#ffffff" opacity={0.35} />
                <text x={0} y={14} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={i === 0 ? 40 : 34}
                  fill={INK}>{i === 0 ? 'PLATFORM' : '?'}</text>
              </g>
            );
          })}
          <g opacity={turn}>
            <Plate x={540} y={SAFE_BOT - 240} w={960} size={28}
              text="17 PEOPLE ARE RUNNING FOR GOVERNOR"
              sub="we could not establish the field's other positions" />
          </g>
        </g>
      )}
      {/* THE BUTTON */}
      <g opacity={q1.t}>
        <Plate x={540} y={SAFE_BOT - 330 + (1 - q1.t) * 24} w={760} size={40} text="WHAT SIZE TRIGGERS IT" />
      </g>
      <g opacity={q2.t}>
        <Plate x={540} y={SAFE_BOT - 190 + (1 - q2.t) * 24} w={760} size={40} text="WHAT ENDS IT" />
      </g>
      {/* the applicant back at the same edge and scale as frame 0, so the loop does not pop */}
      <g transform="translate(740,1120)">
        <ServerMachine frame={f} emotion="focused" x={0} y={0} scale={0.82} facing={-1} tint="steel" />
      </g>
    </Stage>
  );
};

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
      <div style={{background: 'rgba(20,28,36,0.93)', borderRadius: 14, padding: '16px 30px', maxWidth: 940,
        border: `4px solid ${BONE}`, transform: `translateY(${rise}px) scale(${scale})`, transformOrigin: 'center bottom'}}>
        <div style={{fontFamily: BOLD, fontWeight: 900, fontSize: 46, lineHeight: 1.12, color: '#fff', textAlign: 'center',
          letterSpacing: 0.4, textShadow: '2px 3px 0 rgba(0,0,0,0.7)'}}>{cue.text}</div>
      </div>
    </div>
  );
};

export const ep0731Schema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.object({frame: z.number(), word: z.string(), energy: z.number().optional(), lineIdx: z.number().optional()})).optional(),
});
export type Ep0731Props = z.infer<typeof ep0731Schema>;

const SCENES: React.FC[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12];
const DEFAULT_BOUNDS = [
  {from: 0, dur: 193}, {from: 193, dur: 101}, {from: 294, dur: 79}, {from: 373, dur: 295},
  {from: 668, dur: 134}, {from: 802, dur: 179}, {from: 981, dur: 145}, {from: 1126, dur: 177},
  {from: 1303, dur: 274}, {from: 1577, dur: 365}, {from: 1942, dur: 375}, {from: 2317, dur: 482},
];

export const Ep0731: React.FC<Ep0731Props> = ({captions, scenes}) => {
  const bounds = scenes && scenes.length === SCENES.length ? scenes : DEFAULT_BOUNDS;
  return (
    <AbsoluteFill style={{backgroundColor: SKY}}>
      {SCENES.map((C, i) => (
        <Sequence key={i} from={bounds[i].from} durationInFrames={bounds[i].dur} name={`S${i + 1}`}>
          <C />
        </Sequence>
      ))}
      <Captions captions={captions} />
    </AbsoluteFill>
  );
};
