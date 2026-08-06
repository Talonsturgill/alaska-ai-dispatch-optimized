import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, Easing, Sequence, interpolate, useCurrentFrame} from 'remotion';
import {tones, FormGradient, RimLight, ContactShadow, NightGrade, AccentRegistry} from './lib/lighting';
import {vitals, EASE, entrance} from './lib/motion';
import {MaterialDefs} from './lib/materials';
import {ScanReticle} from './lib/FX';
import {Character} from './lib/Character';
import {StatCard} from './lib/props';
import {BrassPlate} from './lib/bench';
import {Sheet} from './lib/paper';
import {Unnamed} from './lib/absence';
import {FrameOfEvidence, FrameStack, REDACTION} from './lib/evidence';
import {ScreenLit, ScreenKey, ScreenBounce} from './lib/screenlight';

// =============================================================================
// DISPATCH 2026-08-06 — "THE SAME FACE, THE SAME PLATE"
//
// Board: out/dispatch/storyboard.json   Look: out/dispatch/art_direction.json (v2)
// Facts: out/dispatch/claims.json (the ONLY source of anything on screen)
//
// THESIS: Fairbanks bought AI to make releasing police video affordable. It made the
// mechanical half of redaction fast and never touched the half where a person has to
// decide, so the queue grew anyway. Anchorage is weighing more of the capture end of
// that same pipe. The rule Anchorage DID write names facial recognition, and the
// object recognition its plate readers run is not the thing that rule named.
//
// THE THREE GRAMMARS:
//   RECTILINEAR-GRID   the socket wall, the console, the ordinance plate. Institutions.
//   ORGANIC-IRREGULAR  the face in the frame, the hand, the technician. Nothing parallel.
//   THE GREY BOX       REDACTION and nothing else. Belongs to the grid, lands on the
//                      organic. Axis-aligned, matte, no bevel, no rim, NO OVERSHOOT.
//
// THE ACCENT LAW (Gate 0D rewrote this): #FF6B35 means A MACHINE IS ATTENDING.
// Licensed ONLY at the plate lock, the two detection boxes, and the FIND segment.
// THE PROGRESS RAIL IS HERO WHITE, because it measures the half no machine touched.
// Orange is ABSENT from Act 4, and that absence is the argument.
// #F0A24B warm tungsten means A PERSON IS DECIDING HERE.
//
// FACTUAL GUARDS, both caught at Gate 0D and both would have been wrong on screen:
//   1. 750 is a CAPACITY CEILING on volunteered feeds (c2), so the wall is drawn as
//      mostly EMPTY DARK SOCKETS with a counter climbing. Never a wall of live feeds.
//   2. Object recognition is PLATE READERS ONLY (c6). The wall NEVER brackets anything.
//      Every bracket in this film fires in the plate-reader lane, on one plate.
// =============================================================================

const FPS = 30;
const NIGHT = '#152437';
const SLATE = '#16283C';
const FAR = '#2E4560';
const HERO = '#E8EEF3';
const ORANGE = '#FF6B35';
const TUNGSTEN = '#F0A24B';
const SHADOW = '#101E2E';
const RIM = '#5FD2E0';
const BOLD = 'Arial Black, Arial, sans-serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

const E_OUT = Easing.bezier(...EASE.enter);
const E_MOVE = Easing.bezier(...EASE.move);

const SAFE_TOP = 420;
const SAFE_BOT = 1500;
const CAPTION_TOP = 1310;
const CAP_W = 884;
const CAP_K = 0.482;

const capRows = (s: string): string[] => {
  if (s.length * CAP_K * 40 <= CAP_W) return [s];
  const w = s.split(' ');
  if (w.length < 2) return [s];
  let cut = 1, best = Infinity;
  for (let k = 1; k < w.length; k++) {
    const dd = Math.abs(w.slice(0, k).join(' ').length - w.slice(k).join(' ').length);
    if (dd < best) {best = dd; cut = k;}
  }
  return [w.slice(0, cut).join(' '), w.slice(cut).join(' ')];
};

/** mono width is exact arithmetic: len * size * 0.602 + tracking * (len-1) */
const monoW = (s: string, size: number, track = 0.5) => s.length * size * 0.602 + track * (s.length - 1);

type SceneProps = {from: number; total: number; L: (i: number) => number};

// ---------------------------------------------------------------------------
// SHARED FURNITURE
// ---------------------------------------------------------------------------

/**
 * THE WORLD WRAPPER, and the push is NOT decoration.
 * DISPATCH_STANDARD section 8: a scene built only out of finished interpolate()
 * events is a slideshow. The 2026-08-05 delivered cut measured 76.6 percent of
 * frames at 99 percent identical to the frame before. EVERY scene here rides a
 * continuous push plus a lateral drift on an irrational period, authored BEFORE
 * any event, so no frame in this film is ever identical to the one before it.
 */
const World: React.FC<{f: number; children: React.ReactNode; bg?: string; dur?: number; push?: number}> = ({
  f, children, bg = NIGHT, dur = 320, push = 1,
}) => {
  const k = 1 + 0.062 * push * Math.min(1, f / Math.max(1, dur));
  const dx = (Math.sin(f / 89) * 13 + Math.sin(f / 17) * 5) * push;
  const dy = (Math.cos(f / 127) * 10 + Math.cos(f / 21) * 4) * push;
  return (
    <AbsoluteFill style={{background: bg}}>
      <svg viewBox="0 0 1080 1920" width="100%" height="100%">
        <MaterialDefs />
        <g transform={`translate(${540 + dx},${960 + dy}) scale(${k}) translate(-540,-960)`}>
          {/* THE ROOM. Added after dead_space_check measured the whole film at 55.8%
              low-information area against a 42% ceiling, with seven shots over the
              per-shot ceiling. These are dark rooms full of equipment, and drawing
              them as gradient fields was both a measured defect and a lie about the
              place. Every scene now sits inside a real room with wall panels, a rack
              wall in the far plane and a floor, all of it modulated and none of it
              competing with the subject. */}
          <Room f={f} />
          {children}
        </g>
      </svg>
    </AbsoluteFill>
  );
};

/**
 * THE ROOM. Rebuilt after dead_space_check measured the film at 55.5% low-information
 * area against a 42% ceiling with seven shots over the per-shot ceiling. The first
 * pass added flat panels, which the meter correctly scored as empty: it measures
 * TEXTURE-FREE AREA, and a flat rect has none.
 *
 * The fix is the thing the style grammar asks for anyway (INFOGRAPHIC_2_5D: detail
 * density, interiors drawn, vents and rivets and LEDs, 20+ shapes per object). These
 * are equipment rooms, so they get drawn as equipment rooms: vented panels, rack
 * units with per-unit LEDs on their own phases, cable runs, conduit, floor grating.
 * Every element is dim and low-contrast so none of it competes with a subject.
 */
const Room: React.FC<{f: number}> = ({f}) => (
  <g>
    <rect x={0} y={0} width={1080} height={1920} fill="#152437" />
    {/* VENTED WALL PANELS, the far plane. Each panel carries its own louvre set. */}
    {Array.from({length: 8}).map((_, r) =>
      Array.from({length: 6}).map((_, c) => {
        const h = Math.imul(r * 13 + c + 3, 2654435761) >>> 0;
        const x = c * 180 + 6, y = r * 172 + 6;
        return (
          <g key={`w${r}-${c}`} opacity={0.62}>
            <rect x={x} y={y} width={168} height={160} rx={3} fill="#1A2B3F" />
            <rect x={x} y={y} width={168} height={2} fill="#2C4560" opacity={0.8} />
            {Array.from({length: 7}).map((_, k) => (
              <rect key={k} x={x + 14} y={y + 22 + k * 18} width={140} height={5} rx={2}
                    fill="#22374E" opacity={0.85} />
            ))}
            {[[10, 10], [158, 10], [10, 150], [158, 150]].map(([sx, sy], k) => (
              <circle key={`s${k}`} cx={x + sx} cy={y + sy} r={2.4} fill="#33506B" opacity={0.9} />
            ))}
            <circle cx={x + 150} cy={y + 140} r={3}
                    fill="#4E86A8" opacity={0.35 + 0.5 * Math.sin(f / (17 + (h % 11)) + (h % 19))} />
          </g>
        );
      })
    )}
    {/* CABLE RUNS across the wall */}
    {Array.from({length: 4}).map((_, i) => (
      <path key={`c${i}`}
        d={`M0,${300 + i * 300} C 300,${312 + i * 300} 780,${288 + i * 300} 1080,${304 + i * 300}`}
        stroke="#1E3247" strokeWidth={7} fill="none" opacity={0.65} />
    ))}
    {/* THE RACK WALL. Real units with per-unit LEDs on their own phases. */}
    {Array.from({length: 15}).map((_, i) => {
      const h = Math.imul(i + 29, 2246822519) >>> 0;
      const x = 18 + i * 71;
      return (
        <g key={`r${i}`} opacity={0.72}>
          <rect x={x} y={1170} width={60} height={244} rx={3} fill="#1D3045" />
          <rect x={x} y={1170} width={60} height={2} fill="#33506B" />
          {Array.from({length: 8}).map((_, k) => (
            <g key={k}>
              <rect x={x + 5} y={1182 + k * 29} width={50} height={20} rx={2} fill="#233B54" />
              <rect x={x + 9} y={1189 + k * 29} width={26} height={3} rx={1} fill="#2E4B69" />
              <circle cx={x + 47} cy={1191 + k * 29} r={2.2}
                      fill="#5FD2E0" opacity={0.25 + 0.55 * Math.sin(f / (9 + (h % 7)) + k * 1.7 + i)} />
            </g>
          ))}
        </g>
      );
    })}
    {/* FLOOR: real grating, not a fill */}
    <rect x={0} y={1414} width={1080} height={506} fill="#12202F" />
    <rect x={0} y={1414} width={1080} height={3} fill="#33506B" opacity={0.75} />
    {Array.from({length: 11}).map((_, r) => (
      <g key={`g${r}`} opacity={0.5}>
        <path d={`M0,${1440 + r * 44} H1080`} stroke="#1B2C3E" strokeWidth={2} />
        {Array.from({length: 13}).map((_, c) => (
          <path key={c} d={`M${c * 84 + 10},${1440 + r * 44} v40`} stroke="#1B2C3E" strokeWidth={2} />
        ))}
      </g>
    ))}
  </g>
);

/** dust in the screen light: the always-running ambient layer for the void shots */
const Motes: React.FC<{f: number; n?: number; cx?: number; cy?: number; r?: number}> = ({
  f, n = 26, cx = 540, cy = 900, r = 520,
}) => (
  <g opacity={0.3}>
    {Array.from({length: n}).map((_, i) => {
      const h = Math.imul(i + 7, 2654435761) >>> 0;
      const a = (h % 628) / 100;
      const rad = r * (0.25 + ((h >> 9) % 100) / 133);
      const sp = 0.11 + ((h >> 17) % 40) / 340;
      const x = cx + Math.cos(a + f * sp * 0.014) * rad;
      const y = cy + Math.sin(a * 1.7 + f * sp * 0.011) * rad * 0.62;
      return <circle key={i} cx={x} cy={y} r={0.9 + ((h >> 5) % 14) / 12} fill={RIM} opacity={0.4} />;
    })}
  </g>
);

/** a plated mono string, sized to its plate by ARITHMETIC (never the reverse) */
const Plate: React.FC<{
  x: number; y: number; text: string; size?: number; op?: number; fill?: string; align?: 'mid' | 'start';
}> = ({x, y, text, size = 26, op = 1, fill = HERO, align = 'mid'}) => {
  const w = monoW(text, size) + 34;
  const h = size + 24;
  // HARD CLAMP. The open-caption card sits at y 1310..1442 and all three panel judges
  // found plated strings bisected by it, buried under it, or pushed below frame. A
  // plate can never enter that band, whatever a call site asks for.
  const CAP_GUARD = CAPTION_TOP - 34;
  const yy = Math.min(y, CAP_GUARD - h / 2);
  const x0 = align === 'mid' ? x - w / 2 : x;
  return (
    <g opacity={op}>
      <rect x={x0} y={yy - h / 2} width={w} height={h} rx={5} fill="#0B141F" opacity={0.94} />
      <rect x={x0} y={yy - h / 2} width={w} height={2} fill="#3E5468" opacity={0.9} />
      <text x={align === 'mid' ? x : x + 17} y={yy + size * 0.36}
            textAnchor={align === 'mid' ? 'middle' : 'start'} fill={fill}
            style={{font: `700 ${size}px ${MONO}`, letterSpacing: 0.5}}>{text}</text>
    </g>
  );
};

/** the socket grid: CAPACITY, not a dragnet. Mostly dark, a small minority lit. */
const SocketGrid: React.FC<{f: number; lit: number; y0?: number; rows?: number; cols?: number; cell?: number}> = ({
  f, lit, y0 = 300, rows = 12, cols = 8, cell = 118,
}) => {
  const w = cols * cell, x0 = 540 - w / 2;
  return (
    <g>
      {Array.from({length: rows * cols}).map((_, i) => {
        const r = Math.floor(i / cols), c = i % cols;
        const h = Math.imul(i + 11, 2246822519) >>> 0;
        const isLit = (h % 1000) / 1000 < lit;
        const fl = 0.72 + 0.28 * Math.sin(f / (7 + (h % 9)) + (h % 31));
        const x = x0 + c * cell, y = y0 + r * cell;
        return (
          <g key={i}>
            <rect x={x + 5} y={y + 5} width={cell - 10} height={cell - 10} rx={3}
                  fill={isLit ? '#2E5175' : '#16283C'} opacity={isLit ? fl : 1} />
            <rect x={x + 5} y={y + 5} width={cell - 10} height={2} fill={isLit ? '#3E6280' : '#1E3247'} />
            {/* every socket carries its own mount detail so an empty one is still drawn */}
            <circle cx={x + 14} cy={y + cell - 16} r={2.6} fill="#24405C" opacity={0.9} />
            <circle cx={x + cell - 14} cy={y + cell - 16} r={2.6} fill="#24405C" opacity={0.9} />
            <rect x={x + 18} y={y + cell - 26} width={cell - 36} height={4} rx={2} fill="#1E3247" opacity={0.85} />
            {isLit && (
              <rect x={x + 12} y={y + 12} width={cell - 24} height={cell - 24} rx={2}
                    fill={RIM} opacity={0.075 * fl} />
            )}
          </g>
        );
      })}
    </g>
  );
};

// ---------------------------------------------------------------------------
// S1  0.0-  THE FRAME. A face, a plate, and a bracket that is refused.
// ---------------------------------------------------------------------------
const S1: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const t = f / FPS;
  // the plate lock: a value SLAMMING to its stop in 4 frames with a 1-frame overshoot
  const lockRaw = interpolate(f, [12, 16, 17], [0, 1.06, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // the face bracket STARTS and is REFUSED: it converges then slides away
  const faceTry = interpolate(f, [78, 92], [0, 0.62], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const faceOff = interpolate(f, [92, 112], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const plates = interpolate(f, [156, 176], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const conduit = interpolate(f, [255, 261, 273], [0, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const SRC = [{x: 280, y: 800, w: 520, h: 300, color: RIM, intensity: 0.95, reach: 780}];
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={420} push={1}>
        <Motes f={f} cy={950} r={560} />
        <rect x={0} y={1440} width={1080} height={480} fill="#0E1B2A" />
        <rect x={0} y={1440} width={1080} height={4} fill="#33506B" opacity={0.85} />
        {Array.from({length: 6}).map((_, i) => (
          <rect key={i} x={40 + i * 178} y={1478} width={140} height={70} rx={4}
                fill="#1C3049" opacity={0.55 + 0.25 * Math.sin(f / (13 + i * 2) + i)} />
        ))}
        <ScreenBounce id="s1b" s={SRC[0]} surfaceY={1180} spread={1.7} />
        <FrameOfEvidence id="hero1" x={540} y={960} f={f} s={1.62}
          faceState="sharp" plateState="sharp" progress={0} accent={0} phase={0} />
        {/* THE PLATE LOCK. ScanReticle is CAST from the shelf, not re-drawn. */}
        <ScanReticle cx={540 + 82} cy={960 + 110} frame={f} lock={lockRaw} color={ORANGE} size={214} />
        {/* THE REFUSED BRACKET: the ban drawn before anyone speaks it */}
        <g opacity={(1 - faceOff) * (faceTry > 0 ? 1 : 0)} transform={`translate(${-190 * faceOff},0)`}>
          <ScanReticle cx={540 - 182} cy={960 - 56} frame={f} lock={faceTry} color={ORANGE} size={222} />
        </g>
        {/* the two cities enter as two lit plates */}
        <g opacity={plates}>
          <BrassPlate x={230} y={1330} lines={["ANCHORAGE"]} set={1} scale={0.7} size={28} w={330} />
          <BrassPlate x={850} y={1330} lines={["FAIRBANKS"]} set={1} scale={0.7} size={28} w={330} />
        </g>
        {/* THE PRIMARY LOOP, planted and refused: the conduit lights and dies */}
        <g opacity={conduit}>
          <path d="M300,1372 H780" stroke={RIM} strokeWidth={7} strokeLinecap="round" opacity={0.8} />
          <text x={540} y={1424} textAnchor="middle" fill={RIM}
                style={{font: `700 26px ${MONO}`, letterSpacing: 3}}>SAME PIPE</text>
        </g>
        <Plate x={540} y={560} text="A FACE AND A PLATE" size={34}
               op={interpolate(f, [4, 20], [0, 1], {extrapolateRight: 'clamp'})} />
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S2  THE SOCKET GRID. Capacity and price. A crane down, NOT a pull-back.
// ---------------------------------------------------------------------------
const S2: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const crane = interpolate(f, [0, 150], [0, 1], {extrapolateRight: 'clamp', easing: E_MOVE});
  const money = interpolate(f, [10, 40], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  // THE FIGURE IS STATIC, DELIBERATELY. A count-up paints a FALSE number on every
  // frame it is sampled at: two encodes of this shot read 'UP TO 21' and 'UP TO 83'
  // on screen at t=14s. The claim (c2) appears whole or not at all. What animates is
  // the SOCKETS filling, which is the capacity idea and carries no number.
  const capCard = interpolate(f, [96, 122], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const SRC = [{x: 120, y: 300, w: 840, h: 900, color: '#7FB6D8', intensity: 0.7, reach: 900}];
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={360} push={0.85} bg={SHADOW}>
        <g transform={`translate(0,${-260 * crane})`}>
          <SocketGrid f={f} lit={0.05 + 0.13 * capCard} y0={250} rows={10} cols={9} cell={112} />
        </g>
        {/* the console lip: the near plane, in shadow, below the square band */}
        <rect x={0} y={1520} width={1080} height={400} fill="#0A121C" />
        <rect x={0} y={1520} width={1080} height={3} fill="#2B3D4F" />
        <ScreenBounce id="s2b" s={SRC[0]} surfaceY={1560} spread={1.2} />
        <g opacity={money}>
          <StatCard x={540} y={560} big="$600,000" sub="REQUESTED" scale={1.5} color={HERO} />
        </g>
        <g opacity={capCard}>
          <Plate x={540} y={1180} text="UP TO 750 VOLUNTEERED FEEDS" size={30} />
        </g>
        <Plate x={540} y={1268} text="CAPACITY, NOT A COUNT" size={22} fill="#7E93A6"
               op={capCard * 0.9} />
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S3  THE CODE. The rule that holds, and the capability that isn't what it named.
// ---------------------------------------------------------------------------
const S3: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const seat = interpolate(f, [6, 30], [0, 1], {extrapolateRight: 'clamp', easing: E_OUT});
  const open = interpolate(f, [26, 58], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  // THE MISMATCH: the orange plate-lock bracket SLAMS at the socket and BOUNCES OFF
  const slamT = interpolate(f, [74, 86, 94, 110], [0, 1, 0.42, 0.5],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const SRC = [{x: 140, y: 1180, w: 800, h: 120, color: '#7FB6D8', intensity: 0.55, reach: 640}];
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={260} push={0.9}>
        <Motes f={f} cy={880} r={430} />
        {/* a second depth plane so the shot is never an unmodulated field */}
        <g opacity={0.5}>
          {Array.from({length: 5}).map((_, i) => (
            <rect key={i} x={90 + i * 200} y={1420 + (i % 2) * 46} width={150} height={92} rx={4}
                  fill="#16283C" opacity={0.5 + 0.2 * Math.sin(f / (11 + i * 3) + i)} />
          ))}
          <rect x={0} y={1650} width={1080} height={270} fill="#0A121C" />
          <rect x={0} y={1650} width={1080} height={3} fill="#2B3D4F" opacity={0.7} />
        </g>
        {/* THE RULE THAT HOLDS, seated with real weight */}
        <g transform={`translate(0,${(1 - seat) * -70})`} opacity={seat}>
          <ContactShadow cx={540} cy={790} rx={300} ry={20} opacity={0.55} blur={11} />
          <rect x={250} y={620} width={580} height={168} rx={8} fill="#1D2E40" />
          <rect x={250} y={620} width={580} height={4} fill="#46607A" />
          <text x={540} y={700} textAnchor="middle" fill={HERO}
                style={{font: `700 30px ${MONO}`, letterSpacing: 1.5}}>FACIAL</text>
          <text x={540} y={748} textAnchor="middle" fill={HERO}
                style={{font: `700 30px ${MONO}`, letterSpacing: 1.5}}>RECOGNITION</text>
        </g>
        <Plate x={540} y={520} text="THE RULE NAMES ONE CATEGORY" size={26} op={seat} />
        {/* THE SOCKET the code cuts, drawn as a stated absence */}
        <g opacity={open}>
          <Unnamed
            d="M300,860 h480 v250 h-480 Z"
            label="THE CATEGORY THE CODE NAMES"
            f={f}
            wide={480}
            tall={250}
          />
        </g>
        {/* THE CAPABILITY IN USE, in the machine's own colour, failing to seat */}
        <g opacity={slamT > 0 ? 1 : 0} transform={`translate(0,${-150 * (1 - Math.min(1, slamT * 1.6))})`}>
          <ScanReticle cx={540} cy={1010 - 96 * (1 - slamT)} frame={f} lock={0.9} color={ORANGE} size={244} />
          <Plate x={540} y={1210} text="OBJECT RECOGNITION" size={30} fill={ORANGE} op={slamT} />
          <Plate x={540} y={1292} text="NOT WHAT THE RULE NAMED" size={28} op={slamT} />
        </g>
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S4  THE WHIP. The room smears; THE FRAME does not move one pixel.
// ---------------------------------------------------------------------------
const S4: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const whip = interpolate(f, [0, 9, 18], [0, 1, 0], {extrapolateRight: 'clamp'});
  const room = interpolate(f, [10, 40], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const travel = interpolate(f, [20, 200], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const conduit = interpolate(f, [60, 70, 86], [0, 0.85, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const SRC = [{x: 300, y: 860, w: 480, h: 280, color: '#8FCBA8', intensity: 0.9, reach: 720}];
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={330} push={0.8} bg="#0B1620">
        {/* the far wall of dim screens, receding, the third depth plane */}
        <g opacity={room}>
          {Array.from({length: 7}).map((_, i) => {
            const k = i / 6;
            const w = 240 - k * 150, h = 150 - k * 96;
            const x = 120 + k * 380 + travel * 60 * (1 - k);
            const y = 700 + k * 130;
            return (
              <g key={i} opacity={0.24 + 0.3 * (1 - k)}>
                <rect x={x} y={y} width={w} height={h} rx={4} fill={FAR} opacity={0.5} />
                <rect x={x} y={y} width={w} height={2} fill="#43607E" />
              </g>
            );
          })}
          <rect x={0} y={1230} width={1080} height={690} fill="#12212F" />
          {Array.from({length: 5}).map((_, i) => (
            <rect key={`d${i}`} x={30 + i * 212} y={1290} width={168} height={96} rx={5}
                  fill="#1B2E42" opacity={0.6 + 0.22 * Math.sin(f / (9 + i * 3) + i * 2)} />
          ))}
          <rect x={0} y={1230} width={1080} height={3} fill="#2A3B4C" opacity={0.8} />
        </g>
        <ScreenBounce id="s4b" s={SRC[0]} surfaceY={1250} spread={1.5} />
        {/* THE CARRIED ELEMENT. The still point through the city change. */}
        <FrameOfEvidence id="hero4" x={540} y={980} f={f} s={1.38}
          faceState="sharp" plateState="sharp" progress={0} phase={0.4} />
        <ScanReticle cx={540 + 70} cy={980 + 94} frame={f} lock={0.92} color={ORANGE} size={182} />
        <g opacity={conduit}>
          <path d="M60,1180 H300" stroke={RIM} strokeWidth={6} strokeLinecap="round" opacity={0.75} />
        </g>
        {/* the whip smear rides OVER the room, never over the frame */}
        <rect x={0} y={0} width={1080} height={1920} fill="#0B1620" opacity={whip * 0.86} />
        <Plate x={540} y={560} text="FAIRBANKS" size={30} op={room} />
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S5  THE TECHNICIAN. The redaction lands, dead flat. The bar appears at zero.
// ---------------------------------------------------------------------------
const S5: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  // THE BOXES LAND FLAT. No overshoot, deliberately: the one dead motion in the film.
  const box = interpolate(f, [8, 14], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const bar = interpolate(f, [16, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const vend = interpolate(f, [48, 58], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // FIVE frames pass through, boxes dead accurate on each: the tool WORKS
  const pass = interpolate(f, [116, 176], [0, 5], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const SRC = [{x: 250, y: 700, w: 580, h: 330, color: '#8FCBA8', intensity: 1, reach: 760}];
  const v = vitals(f, 0.2, 1);
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={260} push={0.85} bg="#0B1620">
        <rect x={0} y={1210} width={1080} height={710} fill="#0A131C" />
        <ScreenBounce id="s5b" s={SRC[0]} surfaceY={1230} spread={1.5} />
        {/* the warm tungsten practical: A PERSON IS DECIDING HERE */}
        <ellipse cx={830} cy={1250} rx={190} ry={70} fill={TUNGSTEN} opacity={0.16} style={{mixBlendMode: 'screen'}} />
        <FrameOfEvidence id="hero5" x={540} y={880} f={f} s={1.34}
          faceState={box > 0.5 ? 'hidden' : 'sharp'} plateState={box > 0.5 ? 'hidden' : 'sharp'}
          progress={bar * 0.012} phase={0.9} />
        {/* the five frames that pass through cleanly */}
        {Array.from({length: 5}).map((_, i) => (
          pass > i + 0.4 ? (
            <g key={i} opacity={Math.max(0, Math.min(1, pass - i - 0.4)) * 0.55}
               transform={`translate(${-330 + i * 165},${1120}) scale(0.22)`}>
              <FrameOfEvidence id={`p${i}`} x={0} y={0} f={f} s={1} dead
                faceState="hidden" plateState="hidden" progress={0} phase={i} />
            </g>
          ) : null
        ))}
        {/* THE VENDOR NAME, REDACTED. c13: neither outlet names the tool. */}
        <g opacity={vend}>
          <rect x={330} y={1300} width={420} height={54} rx={4} fill="#0B141F" opacity={0.94} />
          <rect x={342} y={1310} width={252} height={34} fill={REDACTION} />
          <text x={610} y={1336} fill="#7E93A6" style={{font: `700 22px ${MONO}`}}>NOT NAMED</text>
        </g>
        <g transform="translate(870,1190) scale(1.55)">
          <Character pose="stand" emotion="worried" outfit="vest" headgear="bare" frame={f} />
        </g>
        <Plate x={300} y={640} text="REDACTED" size={26} op={box} />
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S6  THE MECHANISM. One task, two segments. FIND collapses. DECIDE does not move.
// ---------------------------------------------------------------------------
const S6: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const split = interpolate(f, [4, 26], [0, 1], {extrapolateRight: 'clamp', easing: E_OUT});
  // the two lanes measure EQUAL first (proper telegraph), THEN find collapses
  const measure = interpolate(f, [34, 58], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const collapse = interpolate(f, [96, 132], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const rule = interpolate(f, [136, 158], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const X0 = 120, FULL = 400;
  const findW = FULL * (1 - 0.93 * collapse);
  const SRC = [{x: 120, y: 1180, w: 840, h: 90, color: '#7FB6D8', intensity: 0.5, reach: 600}];
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={230} push={0.8}>
        <Motes f={f} cy={950} r={470} />
        <Plate x={540} y={560} text="REDACTING VIDEO IS TWO JOBS" size={28} op={split} />
        {/* FIND: the machine's half, in the machine's colour */}
        <g opacity={split}>
          <rect x={X0} y={880} width={findW} height={168} rx={5} fill={ORANGE} opacity={0.92} />
          <rect x={X0} y={880} width={findW} height={4} fill="#FFB48F" opacity={0.9} />
          <text x={X0 + 16} y={1120} fill={ORANGE} style={{font: `700 26px ${MONO}`, letterSpacing: 2}}>FIND</text>
        </g>
        {/* DECIDE: the human half. Irregular edge, and its surface is a SIGNATURE
            repeated along its whole length. Not 'the expensive half', THE HALF WITH
            SOMEBODY'S NAME ON IT. */}
        <g opacity={split}>
          <path d={`M${X0 + FULL + 20},880 h${FULL} l-5,84 l5,84 h${-FULL} l4,-84 Z`}
                fill="#33485E" />
          <g clipPath="none" opacity={0.55}>
            {Array.from({length: 7}).map((_, i) => (
              <path key={i}
                d={`M${X0 + FULL + 44 + i * 48},986 c8,-16 16,10 24,-4 c6,-10 12,6 16,-2`}
                stroke={TUNGSTEN} strokeWidth={2.6} fill="none" strokeLinecap="round" opacity={0.85} />
            ))}
          </g>
          <text x={X0 + FULL + 36} y={1120} fill={HERO}
                style={{font: `700 26px ${MONO}`, letterSpacing: 2}}>DECIDE</text>
        </g>
        {/* the measure that proves the total barely moved */}
        <g opacity={rule}>
          <path d={`M${X0},1210 H${X0 + FULL * 2 + 20}`} stroke={HERO} strokeWidth={3} />
          <path d={`M${X0},1196 v28 M${X0 + FULL * 2 + 20},1196 v28`} stroke={HERO} strokeWidth={3} />
          <Plate x={540} y={1215} text="THE TOTAL BARELY MOVED" size={28} />
        </g>
        <Plate x={300} y={620} text="A PERSON STILL SIGNS THE ONE IT MISSED" size={22}
               fill="#B9C6D2" op={rule * 0.95} />
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S7  THE LOAD. The curve, and the stack landing on one desk.
// ---------------------------------------------------------------------------
const S7: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const build = interpolate(f, [6, 120], [0, 1], {extrapolateRight: 'clamp'});
  const spike = interpolate(f, [122, 150], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const months = 26;
  const SRC = [{x: 140, y: 560, w: 800, h: 420, color: '#7FB6D8', intensity: 0.55, reach: 700}];
  // one more frame slides onto the stack during the held breath
  const late = interpolate(f, [196, 232], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={300} push={0.75} bg="#0B1620">
        <rect x={0} y={1240} width={1080} height={680} fill="#0A131C" />
        <rect x={0} y={1240} width={1080} height={3} fill="#2A3B4C" opacity={0.85} />
        <ellipse cx={300} cy={1270} rx={200} ry={64} fill={TUNGSTEN} opacity={0.13} style={{mixBlendMode: 'screen'}} />
        {/* the request curve, stepping month by month */}
        <g>
          <path d="M150,1140 H930" stroke="#3A4E62" strokeWidth={2} />
          <path d="M150,900 H930" stroke="#54687C" strokeWidth={1.5} strokeDasharray="8 8" opacity={0.8} />
          <text x={942} y={906} fill="#7E93A6" style={{font: `700 20px ${MONO}`}}>35</text>
          {Array.from({length: months}).map((_, i) => {
            const shown = build * months;
            if (shown < i) return null;
            const isSpike = i === 21 || i === 24;
            const base = 34 + ((Math.imul(i + 3, 2654435761) >>> 0) % 46);
            const hRaw = isSpike ? 300 * spike : base;
            const h = Math.min(hRaw, isSpike ? 300 : base);
            const x = 156 + i * 29;
            return (
              <rect key={i} x={x} y={1140 - h} width={20} height={h} rx={2}
                    fill={isSpike ? HERO : '#46617C'} opacity={isSpike ? 0.96 : 0.85} />
            );
          })}
        </g>
        <Plate x={330} y={1258} text="NEVER ABOVE 20 BEFORE OCT 2025" size={21} op={build} />
        <g opacity={spike}>
          <Plate x={540} y={620} text="APRIL: MORE THAN 35" size={26} />
          <Plate x={540} y={700} text="JULY: MORE THAN 35" size={26} />
        </g>
        {/* the stack, growing UPWARD on a fixed desk. Never a funnel. */}
        <FrameStack x={840} y={1270} f={f} count={Math.round(build * 9 + late * 2)} s={0.44} />
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S8  ONE TECHNICIAN, AND THE SPOOL. The other side's case, drawn.
// ---------------------------------------------------------------------------
const S8: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const hold = interpolate(f, [0, 24], [0, 1], {extrapolateRight: 'clamp'});
  const quote = interpolate(f, [110, 138], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const spool = interpolate(f, [186, 214], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const bury = interpolate(f, [280, 340], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const SRC = [{x: 260, y: 720, w: 520, h: 300, color: '#8FCBA8', intensity: 0.85, reach: 700}];
  const v = vitals(f, 0.55, 1);
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={340} push={0.7} bg="#0A1520">
        <rect x={0} y={1250} width={1080} height={670} fill="#09121B" />
        <ellipse cx={760} cy={1280} rx={210} ry={72} fill={TUNGSTEN} opacity={0.15} style={{mixBlendMode: 'screen'}} />
        <ScreenBounce id="s8b" s={SRC[0]} surfaceY={1270} spread={1.4} />
        <g transform={`translate(790,1200) scale(1.7)`} opacity={hold}>
          <Character pose="stand" emotion="worried" outfit="vest" headgear="bare" frame={f} />
        </g>
        <FrameStack x={250} y={1290} f={f} count={11} s={0.46} />
        <Plate x={300} y={1252} text="ONE EVIDENCE TECHNICIAN" size={24} op={hold} />
        <g opacity={quote}>
          <Plate x={540} y={520} text='"BASICALLY JUST SUBSIDIZING' size={26} />
          <Plate x={540} y={588} text='YOUTUBERS FROM THE LOWER 48"' size={26} />
        </g>
        {/* THE FIVE-HOUR RULE as a finite spool, never a dial with a needle */}
        <g opacity={spool} transform="translate(500,880) scale(1.35)">
          <ContactShadow cx={0} cy={128} rx={190} ry={16} opacity={0.5} blur={9} />
          <rect x={-186} y={-104} width={372} height={228} rx={9} fill="#243748" />
          <rect x={-186} y={-104} width={372} height={3} fill="#476279" />
          {[-92, 92].map((cx, i) => (
            <g key={i}>
              <circle cx={cx} cy={6} r={66} fill="#16232F" stroke="#3D566C" strokeWidth={3} />
              <circle cx={cx} cy={6} r={Math.max(10, 46 - 34 * bury)} fill="#38506A" />
              {Array.from({length: 5}).map((_, k) => (
                <circle key={k} cx={cx} cy={6} r={20 + k * 6} fill="none"
                        stroke={TUNGSTEN} strokeWidth={1.4} opacity={0.5 * (1 - bury)} />
              ))}
            </g>
          ))}
          <rect x={-24} y={-150} width={48} height={44} rx={4} fill={bury > 0.5 ? '#B5432E' : '#3D566C'} />
          <text x={0} y={-118} textAnchor="middle" fill={HERO}
                style={{font: `700 18px ${MONO}`}}>FULL</text>
        </g>
        <Plate x={540} y={1120} text="FREE UNDER 5 STAFF HOURS A MONTH" size={24} op={spool} />
        {/* the burial IS the frames, so the throughline never leaves the film */}
        <g opacity={bury}>
          {Array.from({length: 7}).map((_, i) => {
            const h = Math.imul(i + 5, 2246822519) >>> 0;
            const dx = ((h % 300) - 150);
            const dy = -520 + bury * (620 + (h % 90));
            return (
              <g key={i} transform={`translate(${540 + dx},${880 + dy}) scale(0.2) rotate(${(h % 24) - 12})`}>
                <FrameOfEvidence id={`bur${i}`} x={0} y={0} f={f} s={1} dead
                  faceState="hidden" plateState="hidden" progress={0} phase={i} />
              </g>
            );
          })}
          <Plate x={540} y={1258} text="WRITTEN BEFORE BODY CAMERAS" size={23} op={bury} />
        </g>
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S9  THE TABLE. The idea, the concession, and the city's own attorneys.
// ---------------------------------------------------------------------------
const S9: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const slip = interpolate(f, [6, 30], [0, 1], {extrapolateRight: 'clamp', easing: E_OUT});
  const tick = interpolate(f, [96, 122], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const back = interpolate(f, [168, 206], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const SRC = [{x: 300, y: 1180, w: 480, h: 60, color: '#7FB6D8', intensity: 0.4, reach: 520}];
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={280} push={0.75} bg="#0A1420">
        <rect x={0} y={1180} width={1080} height={740} fill="#101C27" />
        <rect x={0} y={1620} width={1080} height={300} fill="#0A121C" />
        <rect x={0} y={1620} width={1080} height={3} fill="#2B3D4F" opacity={0.7} />
        <rect x={0} y={1180} width={1080} height={3} fill="#33485C" />
        <ellipse cx={540} cy={1215} rx={340} ry={72} fill={TUNGSTEN} opacity={0.16} style={{mixBlendMode: 'screen'}} />
        {/* THE ONLY MULTI-FIGURE FRAME IN THE FILM. It earns the plural in
            "its own attorneys" and escalates in the register the film rationed. */}
        <g opacity={back}>
          {[300, 540, 780].map((x, i) => (
            <g key={i} transform={`translate(${x},1210) scale(1.3)`}>
              <Character pose="stand" emotion="neutral" outfit="suit" headgear="bare" frame={f + i * 19} />
            </g>
          ))}
        </g>
        <g opacity={1 - back * 0.55}>
          <g transform={`translate(${540 + 330 * back},1300) rotate(${-3 + 6 * back})`}>
            <g opacity={slip}>
              <Sheet x={-150} y={-66} w={300} h={132} />
              <text x={0} y={8} textAnchor="middle" fill="#3A4650"
                    style={{font: `700 20px ${MONO}`}}>REQUEST</text>
            </g>
          </g>
        </g>
        <g opacity={slip}>
          <Plate x={540} y={512} text={`"YOU'LL GET IT WHEN YOU GET IT"`} size={25} />
        </g>
        {/* THE CONCESSION, ticked on a THING: the stack and the technician */}
        <g opacity={tick}>
          <FrameStack x={215} y={1230} f={f} count={7} s={0.4} />
          <path d="M180,860 l30,32 l62,-78" stroke={TUNGSTEN} strokeWidth={11} fill="none"
                strokeLinecap="round" strokeLinejoin="round" />
          <Plate x={300} y={700} text="HE'S RIGHT ABOUT THE PROBLEM" size={22} />
        </g>
        <g opacity={back}>
          <Plate x={540} y={606} text="THE CITY'S OWN ATTORNEYS DISAGREED" size={24} />
        </g>
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S10  THE FUSION. Recognize and hide, on the same footage.
// ---------------------------------------------------------------------------
const S10: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const conv = interpolate(f, [14, 96], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_MOVE});
  const fire1 = interpolate(f, [30, 46], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fire2 = interpolate(f, [62, 76], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fuse = interpolate(f, [96, 116], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const stamp = interpolate(f, [160, 182], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const SRC = [{x: 200, y: 800, w: 680, h: 340, color: RIM, intensity: 0.8, reach: 820}];
  return (
    <ScreenLit sources={SRC}>
      <World f={f} dur={300} push={0.85}>
        <Motes f={f} cy={930} r={520} />
        {/* the seam */}
        <path d="M540,520 V1360" stroke="#3E5468" strokeWidth={2} opacity={0.5 * (1 - fuse)} />
        <g transform={`translate(${-300 * (1 - conv)},0)`} opacity={1 - fuse * 0.0}>
          <FrameOfEvidence id="anc" x={fuse > 0.5 ? 540 : 340} y={940} f={f} s={1.0}
            faceState="sharp" plateState={fire1 > 0.5 ? 'sharp' : 'sharp'} progress={0} phase={0.1} />
          <g opacity={fire1}>
            <ScanReticle cx={(fuse > 0.5 ? 540 : 340) + 52} cy={940 + 72} frame={f} lock={fire1} color={ORANGE} size={150} />
          </g>
        </g>
        <g transform={`translate(${300 * (1 - conv)},0)`} opacity={1 - fuse}>
          <FrameOfEvidence id="fbx" x={740} y={940} f={f} s={1.0}
            faceState={fire2 > 0.5 ? 'hidden' : 'sharp'} plateState={fire2 > 0.5 ? 'hidden' : 'sharp'}
            progress={0.012} phase={0.6} />
        </g>
        {/* THE FUSED FRAME: brackets AND boxes, on the same face and the same plate */}
        <g opacity={fuse}>
          <FrameOfEvidence id="fused" x={540} y={940} f={f} s={1.22}
            faceState="hidden" plateState="hidden" progress={0.012} phase={0.3} />
          <ScanReticle cx={540 + 60} cy={940 + 84} frame={f} lock={1} color={ORANGE} size={172} />
          <path d="M180,1180 H900" stroke={RIM} strokeWidth={7} strokeLinecap="round" opacity={0.7 * fuse} />
          <Plate x={540} y={1250} text="SAME FOOTAGE" size={30} op={fuse} />
        </g>
        <Plate x={300} y={600} text="RECOGNIZE" size={26} fill={ORANGE} op={fire1 * (1 - fuse)} />
        <Plate x={780} y={600} text="HIDE" size={26} fill="#9AA6AE" op={fire2 * (1 - fuse)} />
        {/* THE DATE, on an EMPTY calendar square. c3 says POSTPONED, not a vote. */}
        <g opacity={stamp}>
          <rect x={352} y={1330} width={376} height={128} rx={6} fill="#16232F" />
          {Array.from({length: 8}).map((_, i) => (
            <rect key={i} x={368 + (i % 4) * 88} y={1348 + Math.floor(i / 4) * 50} width={76} height={40} rx={3}
                  fill={i === 5 ? '#0B141F' : '#2B4257'} opacity={i === 5 ? 1 : 0.75} />
          ))}
          <Plate x={540} y={1520} text="POSTPONED TO AUGUST 18TH" size={25} op={stamp} />
        </g>
      </World>
    </ScreenLit>
  );
};

// ---------------------------------------------------------------------------
// S11  THE SIGNATURE SHOT. Hundreds get found. One gets released, by a person.
// ---------------------------------------------------------------------------
const S11: React.FC<SceneProps> = ({from}) => {
  const f = useCurrentFrame();
  const out = interpolate(f, [0, 150], [0, 1], {extrapolateRight: 'clamp', easing: E_MOVE});
  const q = interpolate(f, [104, 132], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const sign = interpolate(f, [150, 176], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: E_OUT});
  const scale = 1 - 0.72 * out;
  const cols = 9, rows = 11, cell = 104;
  const gw = cols * cell, gx = 540 - gw / 2, gy = 470;
  return (
    <World f={f} dur={330} push={0.55} bg={SHADOW}>
      {/* EVERY tile bracketed. EXACTLY ONE hidden. The thesis as a picture. */}
      <g opacity={out}>
        {Array.from({length: rows * cols}).map((_, i) => {
          const r = Math.floor(i / cols), c = i % cols;
          const x = gx + c * cell, y = gy + r * cell;
          const isHero = r === 6 && c === 4;
          const behindFigure = r >= 8 && c >= 3 && c <= 5;
          const h = Math.imul(i + 17, 2654435761) >>> 0;
          const fl = 0.7 + 0.3 * Math.sin(f / (9 + (h % 7)) + (h % 29));
          if (behindFigure) {
            return <rect key={i} x={x + 4} y={y + 4} width={cell - 8} height={cell - 8} rx={3} fill="#060C13" />;
          }
          return (
            <g key={i}>
              <rect x={x + 4} y={y + 4} width={cell - 8} height={cell - 8} rx={3}
                    fill={isHero ? '#1A2836' : '#22405C'} opacity={isHero ? 1 : fl} />
              {isHero ? (
                <g>
                  <rect x={x + 4} y={y + 4} width={cell - 8} height={cell - 8} rx={3} fill="#0E1620" />
                  <rect x={x + 14} y={y + 16} width={cell - 28} height={cell - 32} fill={REDACTION} />
                </g>
              ) : (
                <g opacity={0.85 * fl}>
                  {[[8, 8, 1, 1], [cell - 8, 8, -1, 1], [8, cell - 8, 1, -1], [cell - 8, cell - 8, -1, -1]]
                    .map(([bx, by, sx, sy], k) => (
                      <path key={k}
                        d={`M${x + bx},${y + by + sy * 16} V${y + by} H${x + bx + sx * 16}`}
                        stroke={ORANGE} strokeWidth={3} fill="none" strokeLinecap="round" />
                    ))}
                </g>
              )}
            </g>
          );
        })}
      </g>
      {/* the one person, BACKLIT and rim-separated, inside the square band */}
      <g transform={`translate(540,1400) scale(${0.92})`} opacity={out}>
        <ellipse cx={0} cy={62} rx={150} ry={22} fill="#04090F" opacity={0.85} />
        <g transform="scale(1.05)">
          <Character pose="stand" emotion="neutral" outfit="vest" headgear="bare" frame={f} />
        </g>
      </g>
      <Plate x={540} y={840} text="ONE PERSON RELEASES IT" size={23} fill="#B9C6D2" op={out * 0.9} />
      {/* THE BUTTON */}
      <g opacity={q}>
        <Plate x={540} y={640} text="WHAT WOULD YOU WANT" size={32} />
        <Plate x={540} y={716} text="WRITTEN DOWN?" size={32} />
      </g>
      {/* THE SIGN-OFF, seated on the console lip as a real object */}
      <g opacity={sign} transform={`translate(0,${(1 - sign) * 40})`}>
        <BrassPlate x={540} y={1660} lines={["ALASKA.AI"]} set={sign} scale={0.8} size={34} w={420} />
        <text x={540} y={1760} textAnchor="middle" fill="#6E8496"
              style={{font: `700 17px ${MONO}`, letterSpacing: 1}}>
          ALASKA&apos;S NEWS SOURCE · KUAC · ALASKA PUBLIC MEDIA · MUNICIPALITY OF ANCHORAGE
        </text>
      </g>
    </World>
  );
};

const SCENES: React.FC<SceneProps>[] = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11];
const FALLBACK_LINES = [
  0, 2.8, 7.6, 15.2, 20.8, 26.0, 32.0, 37.2, 40.0, 46.0, 51.6, 54.0, 57.6,
  64.8, 68.4, 75.2, 76.8, 82.4, 88.0, 94.8, 97.2, 101.6, 108.8, 111.2, 115.6,
];
const SSL = [0, 2, 4, 6, 8, 11, 13, 15, 18, 21, 23];

export const ep0806Schema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})).optional(),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  lines: z.array(z.number()).optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.any()).optional(),
});

export const Ep0806: React.FC<z.infer<typeof ep0806Schema>> = ({captions = [], scenes, total, lines}) => {
  const f = useCurrentFrame();
  const lineTable = lines && lines.length >= 25 ? lines : FALLBACK_LINES;
  const L = React.useCallback((i: number) => lineTable[Math.min(i, lineTable.length - 1)], [lineTable]);
  const bounds = scenes && scenes.length === SCENES.length
    ? scenes
    : SCENES.map((_, i) => {
        const start = Math.round(FALLBACK_LINES[SSL[i]] * FPS);
        const end = i + 1 < SSL.length
          ? Math.round(FALLBACK_LINES[SSL[i + 1]] * FPS)
          : Math.round((total ?? 3690));
        return {from: start, dur: Math.max(1, end - start)};
      });
  const totalF = total ?? 3690;

  // THE ACCENT LICENCE. #FF6B35 means A MACHINE IS ATTENDING. An unlicensed
  // reserved hue THROWS under AccentRegistry and a throw fails the render, so the
  // licensed rects are declared here and nowhere else. The progress rail is NOT on
  // this list: it is hero white, because it measures the half no machine touched.
  const licences = React.useMemo(() => [{
    hue: ORANGE,
    means: 'a machine is attending to something',
    rects: [
      {x: 300, y: 780, w: 520, h: 400},    // S1 the plate lock and the refused bracket
      {x: 330, y: 850, w: 420, h: 560},    // S3 the capability that fails to seat
      {x: 480, y: 980, w: 220, h: 180},    // S4 the bracket carried through the whip
      {x: 140, y: 840, w: 400, h: 220},    // S6 the FIND segment ONLY
      {x: 300, y: 880, w: 480, h: 200},    // S10 the two firings and the fusion
      {x: 60, y: 440, w: 960, h: 780},     // S11 the wall of bracketed tiles
    ],
  }], []);

  return (
    <AccentRegistry accents={licences}>
      <AbsoluteFill style={{background: NIGHT}}>
        {SCENES.map((S, i) => (
          <Sequence key={i} from={bounds[i].from} durationInFrames={Math.max(1, bounds[i].dur)}>
            <S from={bounds[i].from} total={totalF} L={L} />
          </Sequence>
        ))}
        {/* NIGHTGRADE emits divs, so it sits OUTSIDE the svg, per its contract. */}
        <NightGrade
          f={f}
          color="#0E1B2A"
          amount={0.22}
          floor={0.14}
          horizon={0.2}
          sources={[{x: 540, y: 900, r: 620, color: '#5FD2E0', intensity: 0.5}]}
        />
        {/* OPEN CAPTIONS from the forced alignment. Most plays are muted. */}
        <AbsoluteFill>
          <svg viewBox="0 0 1080 1920" width="100%" height="100%">
            {captions
              .filter((c) => f >= c.start * FPS && f <= c.end * FPS)
              .map((c, i) => {
                const rows = capRows(c.text);
                const longest = rows.reduce((m, r) => Math.max(m, r.length), 0);
                const size = Math.max(24, Math.min(40, Math.floor(CAP_W / (longest * CAP_K))));
                return (
                  <g key={i}>
                    <rect x={70} y={CAPTION_TOP} width={940} height={132} rx={12}
                          fill="#0A121C" opacity={0.96} />
                    {rows.map((r, k) => (
                      <text key={k} x={540}
                            y={CAPTION_TOP + (rows.length === 1 ? 80 : 56 + k * 48)}
                            textAnchor="middle" fill="#F6F1E4"
                            style={{font: `800 ${size}px ${BOLD}`, letterSpacing: 0.5}}>{r}</text>
                    ))}
                  </g>
                );
              })}
          </svg>
        </AbsoluteFill>
      </AbsoluteFill>
    </AccentRegistry>
  );
};
