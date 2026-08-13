import React from 'react';
import {AbsoluteFill, Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';
import {EndCredits} from './lib/EndCredits';
import {VoiceProvider} from './lib/voice';
import {tones, FormGradient, RimLight, ContactShadow, DayGrade, INK} from './lib/lighting';
import {entrance, POP, SNAP, SETTLE} from './lib/motion';
import {
  RatingPlate, FieldGenset, BatteryCabinet, ProbeResponse, CoupledRinging,
  PowerhouseBG, FilingDrawer, Unknown, ShippedCrate, VIOLET, ID, ihash,
} from './lib/identify';

// ============================================================================
// THE MACHINE NOBODY WROTE DOWN — Dispatch 2026-08-13
//
// NSF award 2626692, made on August 10th 2026 to the University of Alaska Fairbanks,
// PI Mariko Shirazi. A village diesel's rating plate carries one number stamped deep,
// the power it can make, and nothing about how it behaves, because nobody wrote that
// down. The proposal is to let the battery's own grid-forming inverter put a question
// into the wire and learn how the diesel answers.
//
// Board: out/dispatch/storyboard.json. Binding look: out/dispatch/art_direction.json.
//
// HIGH-KEY COLD DAYLIGHT, because both natural readings of a powerhouse were spent (warm
// amber engine room 08-09, dark institutional slate 08-12) and because it is the honest
// light: nothing here is hidden, and a bright room where you can see everything and still
// not know the answer is the better picture.
//
// VIOLET IS RESERVED BY CONSTRUCTION for a MEASUREMENT: the probe going out, the response
// coming back, and the writing those produce. It appears nowhere else. A blank field on
// the plate is blank precisely because no violet ever reached it.
//
// NEITHER MACHINE HAS A FACE, deliberately. A face promises the object can tell you how it
// feels, and this film's argument is that it can't tell you anything. Feeling is carried by
// the flywheel, the light, and what the hands do.
// ============================================================================

const BOLD = 'Archivo, Arial Black, Arial, sans-serif';
const MONO = 'JetBrains Mono, Consolas, monospace';
const W = 1080, H = 1920;
const FPS = 30;

// The open-caption band, declared as a constant so scripts/caption_band_check.py and
// scripts/beat_delivery.py can both read it.
const CAPTION_TOP = 1336;
const CAPTION_H = 132;

const SQUARE_TOP = 420, CROP_DY = 14, CONTENT_ZOOM = 1.20;

const P = {
  glare: ID.glare, concrete: ID.concrete, green: ID.green, oxblood: ID.oxblood,
  bone: ID.bone, graphite: ID.graphite, violet: VIOLET, shadow: ID.shadow,
} as const;

const FLOOR = 1180;

export interface SceneProps { t0: number; L: number[]; }
const at = (p: SceneProps, i: number, off = 0): number =>
  Math.round(((p.L[i] ?? p.t0) + off - p.t0) * FPS);

/** Local adapter over entrance(): opacity plus drop offset, which is what scenes want. */
const ent = (f: number, delay: number, preset = POP, drop = 0) => {
  const e = entrance(f, FPS, delay, {preset, drop});
  return {o: Math.max(0, Math.min(1, e.t)), dy: e.dy, scale: e.scale, vy: e.vy};
};

/** Each scene owns its own <svg>. Sequence renders a wrapper div, so nesting it INSIDE an
 *  <svg> silently produces an empty frame. */
const Frame: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill>
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>{children}</svg>
  </AbsoluteFill>
);

/** EVERY scene gets a continuous slow push plus a lateral drift on an irrational period,
 *  authored BEFORE any event, per DISPATCH_STANDARD section 8. */
const Stage: React.FC<{f: number; dur: number; children: React.ReactNode; drift?: number; zoom?: number}> = ({
  f, dur, children, drift = 1, zoom = 1,
}) => {
  const push = interpolate(f, [0, dur], [0, 0.10], {extrapolateRight: 'clamp'});
  const dx = Math.sin(f / 43.7) * 30 * drift;
  const dy = Math.cos(f / 59.3) * 17 * drift;
  return (
    <Frame>
      <g transform={`translate(${540 + dx} ${960 + dy}) scale(${(1 + push) * CONTENT_ZOOM * zoom}) translate(${-540} ${-960})`}>
        {children}
      </g>
    </Frame>
  );
};

/* ---------------------------------------------------------------- plates */
const MONO_ADV = 0.602;   // exact mono advance; a plated string's width is arithmetic
const HEAD_ADV = 0.66;    // Archivo Black mean advance
const USABLE = (W - 150) / (CONTENT_ZOOM * 1.12);

/** A plate sized TO its string. Never the reverse. */
const Plate: React.FC<{
  x: number; y: number; text: string; size?: number; fill?: string; bg?: string; ls?: number;
}> = ({x, y, text, size = 30, fill = '#F2EFE7', bg = INK, ls = 1.5}) => {
  const tw = text.length * size * MONO_ADV + ls * Math.max(0, text.length - 1);
  const pw = tw + 44;                                   // 22px clear each side, over the 14 minimum
  const ph = size + 26;
  return (
    <g>
      <ContactShadow cx={x} cy={y + ph / 2 + 5} rx={pw / 2} ry={7} opacity={0.22} />
      <rect x={x - pw / 2} y={y - ph / 2} width={pw} height={ph} rx={4} fill={bg} opacity={0.92}
            stroke={INK} strokeWidth={3} />
      <RimLight d={`M ${x - pw / 2 + 6} ${y - ph / 2} H ${x + pw / 2 - 6}`} w={2.5} opacity={0.35} />
      <text x={x} y={y + size * 0.36} textAnchor="middle" fontSize={size} fontFamily={MONO}
            fill={fill} letterSpacing={ls}>{text}</text>
    </g>
  );
};

/** The hook headline, fitted to the string. */
const Head: React.FC<{x: number; y: number; text: string; size?: number; fill?: string}> = ({
  x, y, text, size = 92, fill = '#F4F1E9',
}) => {
  const fit = Math.min(size, Math.floor(USABLE / Math.max(1, text.length * HEAD_ADV)));
  return (
    <text x={x} y={y} fill={fill} fontSize={fit} fontFamily={BOLD} fontWeight={900}
          letterSpacing={-1} textAnchor="middle" stroke={INK}
          strokeWidth={Math.max(4, fit * 0.09)} paintOrder="stroke">{text}</text>
  );
};

/** The gloved operator hand. Competent, unhurried, never a face, never helpless. */
const Hand: React.FC<{f: number; x: number; y: number; s?: number; tap?: number; rot?: number}> = ({
  f, x, y, s = 1, tap = 0, rot = 0,
}) => {
  const knock = tap > 0 ? Math.abs(Math.sin(tap * Math.PI * 2)) * 26 : 0;
  return (
    <g transform={`translate(${x} ${y - knock}) scale(${s}) rotate(${rot})`}>
      <ContactShadow cx={10} cy={96} rx={72} ry={12} opacity={0.2 + knock * 0.004} />
      <path d="M -70 92 L -58 6 q 6 -34 34 -32 q 22 2 24 30 l 4 40 l 8 -46 q 4 -26 28 -24
               q 22 2 20 28 l -6 52 q -4 44 -44 50 l -40 2 q -26 -2 -28 -26 Z"
            fill="#C9A98C" stroke={INK} strokeWidth={4} strokeLinejoin="round" />
      <path d="M -70 92 L -66 46 l 74 -6 l 6 52 Z" fill="#8E6B52" opacity={0.5} />
      <path d="M -58 6 q 6 -34 34 -32" fill="none" stroke="#F0E2D2" strokeWidth={3} opacity={0.5} />
    </g>
  );
};

/* ================================================================== SHOTS */

/** S1 0.00-10.08 — the plate lands, the hand taps it, the one stamped fact. */
const S1: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const land = ent(f, 0, SNAP, 90);
  const tap = interpolate(f, [58, 74], [0, 2], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const stamp = ent(f, at(p, 1), SNAP);
  return (
    <Stage f={f} dur={p.dur} drift={0.5} zoom={1.10}>
      <PowerhouseBG f={f} parallax={0.2} />
      {/* the genset behind the plate, so the shot is never pixel-frozen between events */}
      <g opacity={0.9}><FieldGenset f={f} x={210} y={1030} s={0.66} spin={1} burning={0.7} groundY={300} /></g>
      <g transform={`translate(0 ${land.dy})`} opacity={land.o}>
        <RatingPlate f={f} x={540} y={880} s={1.02} kw="365 kW" columns={1} written={0} />
      </g>
      {f > 46 && <Hand f={f} x={760} y={1010} s={1.05} tap={tap} rot={-14} />}
      {stamp.o > 0 && (
        <g opacity={stamp.o}>
          <Plate x={540} y={1180 + stamp.dy} text="RATING PLATE" size={34} />
        </g>
      )}
      {f > at(p, 1) + 26 && (
        <Plate x={540} y={1206} text="kW  ·  STAMPED" size={28} fill="#F2EFE7" />
      )}
      <DayGrade f={f} amount={0.5} floor={0.28} haze={0.16} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/** S2 10.08-16.87 — the blank fields, named as an absence, and the form with nothing to copy. */
const S2: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const open = interpolate(f, [4, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const form = ent(f, at(p, 2, 3.3), SETTLE, 40);
  return (
    <Stage f={f} dur={p.dur} drift={0.4} zoom={1.34}>
      <PowerhouseBG f={f} parallax={0.4} door={0.6} />
      <g opacity={0.85}><FieldGenset f={f} x={190} y={1060} s={0.6} spin={1} burning={0.6} groundY={300} phase={2.1} /></g>
      <RatingPlate f={f} x={540} y={900} s={1.0} kw="365 kW" columns={1} written={0} drift={open} />
      <g opacity={open * 0.9}>
        <Unknown f={f} seed={4} label="how it behaves, not recorded"
                 d="M 260 900 h 560 v 210 h -560 Z" opacity={0.55} />
      </g>
      <Plate x={540} y={1120} text="NOT RECORDED" size={30} />
      {form.o > 0 && (
        <g opacity={form.o} transform={`translate(0 ${form.dy})`}>
          <rect x={702} y={1030} width={230} height={150} rx={4} fill="#F1EDE3" stroke={INK} strokeWidth={3.5}
                transform="rotate(-7 817 1105)" />
          <Hand f={f} x={840} y={1060} s={0.78} rot={22} />
          <Plate x={540} y={1206} text="NOBODY WROTE IT DOWN" size={26} />
        </g>
      )}
      <DayGrade f={f} amount={0.5} floor={0.28} haze={0.14} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/** S3 16.87-25.82 — the award record stamped, the two drums apart, the name plate. */
const S3: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const rec = ent(f, 2, SNAP, 70);
  const dA = ent(f, at(p, 3, 3.5), SETTLE, 60);
  const dB = ent(f, at(p, 3, 3.9), SETTLE, 60);
  const nm = ent(f, at(p, 3, 6.4), SETTLE, 34);
  const T = tones('#C9C3B4');
  return (
    <Stage f={f} dur={p.dur} drift={0.6} zoom={1.04}>
      <PowerhouseBG f={f} parallax={0.1} door={0.85} />
      <defs><FormGradient id="recf" t={T} softness={1.1} /></defs>
      <g opacity={rec.o} transform={`translate(0 ${rec.dy})`}>
        <ContactShadow cx={540} cy={766} rx={260} ry={16} opacity={0.26} />
        <rect x={286} y={470} width={508} height={290} rx={5} fill="url(#recf)" stroke={INK} strokeWidth={4} />
        {Array.from({length: 7}, (_, i) => (
          <path key={i} d={`M 322 ${520 + i * 32} H ${700 - (i % 3) * 60}`} stroke={INK} strokeWidth={3} opacity={0.24} />
        ))}
        <g transform={`rotate(-9 640 706)`} opacity={Math.min(1, Math.max(0, (f - 20) / 8))}>
          <rect x={520} y={660} width={240} height={78} rx={4} fill="none" stroke={P.oxblood} strokeWidth={5} />
          <text x={640} y={712} textAnchor="middle" fontSize={26} fontFamily={MONO} fill={P.oxblood}>AUG 10 2026</text>
        </g>
      </g>
      <Plate x={540} y={900} text="NSF 2626692  ·  AUGUST 10TH 2026" size={26} />
      {/* two drums, apart, never poured into one tank */}
      {[{e: dA, x: 330, t: '$324,995', s: 'UAF'}, {e: dB, x: 750, t: '$225,000', s: 'WISCONSIN'}].map((d, i) => (
        <g key={i} opacity={d.e.o} transform={`translate(0 ${d.e.dy})`}>
          <ContactShadow cx={d.x} cy={1178} rx={92} ry={13} opacity={0.28} />
          <rect x={d.x - 80} y={960} width={160} height={220} rx={10} fill="#8E9AA0" stroke={INK} strokeWidth={4} />
          {[0, 1, 2].map((k) => <path key={k} d={`M ${d.x - 80} ${1000 + k * 62} h 160`} stroke={INK} strokeWidth={3} opacity={0.35} />)}
          <RimLight d={`M ${d.x - 70} 962 H ${d.x + 70}`} w={3} opacity={0.5} />
          <text x={d.x} y={1092} textAnchor="middle" fontSize={25} fontFamily={MONO} fill="#1D2226">{d.t}</text>
          <text x={d.x} y={1128} textAnchor="middle" fontSize={19} fontFamily={MONO} fill="#39424A">{d.s}</text>
        </g>
      ))}
      {nm.o > 0 && (
        <g opacity={nm.o} transform={`translate(0 ${nm.dy})`}>
          <Plate x={540} y={1206} text="MARIKO SHIRAZI" size={28} bg="#5C4A22" />
        </g>
      )}
      <DayGrade f={f} amount={0.52} floor={0.3} haze={0.14} sunX={0.06} sunY={0.2} />
    </Stage>
  );
};

/** S4 25.82-36.07 — both machines at equal height, and the line begins to ring. */
const S4: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const reveal = ent(f, 0, SETTLE);
  const grow = interpolate(f, [at(p, 4, 3.8), at(p, 4, 7.0)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const nod = Math.sin(f / 7.4) * grow * 9;
  const clip = ent(f, at(p, 4, 7.2), SNAP, 50);
  return (
    <Stage f={f} dur={p.dur} drift={0.9} zoom={1.08}>
      <PowerhouseBG f={f} parallax={0.6} door={1} />
      <g transform={`translate(0 ${nod})`}>
        <FieldGenset f={f} x={330} y={860} s={0.82} spin={1} burning={1} groundY={310} />
      </g>
      <g transform={`translate(0 ${-nod})`}>
        <BatteryCabinet f={f} x={790} y={880} s={0.80} charge={0.75} groundY={280} />
      </g>
      {/* the one conductor between them */}
      <CoupledRinging f={f} x1={452} y={1092} x2={676} grow={grow} />
      <g opacity={reveal.o}>
        <Plate x={540} y={1120} text="CO-LOCATED  ·  COMMENSURATE IN SIZE" size={24} />
      </g>
      {grow > 0.35 && (
        <Plate x={540} y={1206} text="SUSTAINED OSCILLATIONS" size={26} bg="#5A2A22" />
      )}
      {clip.o > 0 && (
        <g opacity={clip.o} transform={`translate(0 ${clip.dy})`}>
          <Hand f={f} x={210} y={1218} s={0.72} rot={34} />
        </g>
      )}
      <DayGrade f={f} amount={0.55} floor={0.3} haze={0.18} sunX={0.05} sunY={0.2} />
    </Stage>
  );
};

/** S5 36.07-44.16 — the diesel switches off, and the fuel stops drawing. */
const S5: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const off = interpolate(f, [6, 52], [1, 0.04], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const fuel = interpolate(f, [at(p, 5, 4.1), at(p, 5, 6.0)], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage f={f} dur={p.dur} drift={0.7} zoom={1.00}>
      <PowerhouseBG f={f} parallax={0.35} door={1} />
      <FieldGenset f={f} x={330} y={880} s={0.82} spin={off} burning={off} groundY={300} />
      <BatteryCabinet f={f} x={790} y={900} s={0.80} charge={0.55 + (1 - off) * 0.4} groundY={270} />
      <Plate x={540} y={1120} text="THE DIESEL SWITCHES OFF" size={28} />
      {/* the fuel line stops drawing and the level holds */}
      <g transform="translate(0 0)">
        <rect x={120} y={1060} width={120} height={170} rx={8} fill="#8E9AA0" stroke={INK} strokeWidth={4} />
        <rect x={128} y={1230 - 150 * (0.55 + (1 - fuel) * 0.0)} width={104}
              height={150 * (0.55 + (1 - fuel) * 0.0)} fill={P.oxblood} opacity={0.55} />
        <path d={`M 240 1120 h ${60 * fuel}`} stroke="#4A5257" strokeWidth={9} opacity={fuel} />
      </g>
      {fuel < 0.4 && <Plate x={540} y={1206} text="WHERE THE SAVING COMES FROM" size={24} />}
      <DayGrade f={f} amount={0.55} floor={0.32} haze={0.15} sunX={0.05} sunY={0.2} />
    </Stage>
  );
};

/** S6 44.16-53.11 — MAXIMUM PRESSURE. Nothing broken in the frame, and the money burns. */
const S6: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const back = ent(f, 2, SNAP);
  const watch = Math.sin(f / 11.3) * 5;
  return (
    <Stage f={f} dur={p.dur} drift={1.1} zoom={0.90}>
      <PowerhouseBG f={f} parallax={0.8} door={1} />
      <FieldGenset f={f} x={330} y={880} s={0.82} spin={back.o} burning={back.o} groundY={310} />
      <BatteryCabinet f={f} x={790} y={900} s={0.80} charge={0.8} groundY={280} />
      {/* the packed case by the door that cannot leave */}
      <g transform={`translate(196 1046) scale(1.7) rotate(${watch * 0.4})`}>
        <ContactShadow cx={0} cy={92} rx={82} ry={12} opacity={0.26} />
        <rect x={-74} y={-32} width={148} height={124} rx={9} fill="#7A5A3E" stroke={INK} strokeWidth={4} />
        <path d="M -74 12 H 74" stroke={INK} strokeWidth={3} opacity={0.4} />
        <path d={`M -24 -32 q 24 ${-34 + watch} 48 0`} fill="none" stroke={INK} strokeWidth={6} />
        <rect x={-20} y={28} width={40} height={24} rx={3} fill="#C9A98C" stroke={INK} strokeWidth={2.5} />
      </g>
      <Plate x={540} y={1120} text="IT KEEPS RUNNING" size={30} />
      <Plate x={540} y={1206} text="THE SAVING NEVER ARRIVES" size={26} bg="#5A2A22" />
      <DayGrade f={f} amount={0.58} floor={0.32} haze={0.2} sunX={0.05} sunY={0.18} />
    </Stage>
  );
};

/** S7 53.11-63.37 — the transmission schematic slams open, the scale collapses, the drawer. */
const S7: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const un = ent(f, 2, SNAP);
  const collapse = interpolate(f, [at(p, 7, 4.2), at(p, 7, 6.6)], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const dOpen = interpolate(f, [at(p, 7, 4.6), at(p, 7, 6.4)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const card = interpolate(f, [at(p, 7, 6.2), at(p, 7, 7.6)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const spread = 60 + collapse * 340;
  return (
    <Stage f={f} dur={p.dur} drift={0.8} zoom={0.96}>
      <PowerhouseBG f={f} parallax={0.5} door={0.7} />
      {/* the oversized schematic, hanging off both walls */}
      <g opacity={un.o * (0.25 + collapse * 0.75)}>
        <rect x={-40} y={452} width={1160} height={476} fill="#E4E0D4" stroke={INK} strokeWidth={4} opacity={0.9} />
        {Array.from({length: 9}, (_, i) => (
          <path key={i} d={`M -120 ${470 + i * 56} H 1200`} stroke={INK} strokeWidth={2} opacity={0.18} />
        ))}
        <Plate x={540} y={512} text="STUDY EACH MACHINE ALONE" size={24} />
      </g>
      {/* two towers whose spacing collapses */}
      {[-1, 1].map((sgn, i) => (
        <g key={i} transform={`translate(${540 + sgn * spread} 760)`}>
          <path d="M -34 130 L -12 -96 L 12 -96 L 34 130" fill="none" stroke={INK} strokeWidth={6} />
          <path d="M -22 20 H 22 M -28 74 H 28" stroke={INK} strokeWidth={4} />
        </g>
      ))}
      <Plate x={540} y={1010} text={collapse > 0.5 ? 'A HUNDRED MILES APART' : 'WIRED TOO CLOSE FOR THAT'} size={26} />
      {dOpen > 0 && (
        <g opacity={dOpen}>
          <FilingDrawer f={f} x={742} y={980} s={0.78} open={dOpen} card={card} />
          
        </g>
      )}
      <DayGrade f={f} amount={0.55} floor={0.3} haze={0.16} sunX={0.06} sunY={0.2} />
    </Stage>
  );
};

/** S8 63.37-71.89 — THE CUTAWAY. The probe goes out and comes back changed. */
const S8: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const trip = interpolate(f, [10, 92], [0, 2], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const curve = interpolate(f, [at(p, 8, 4.2), at(p, 8, 7.4)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage f={f} dur={p.dur} drift={0.5} zoom={0.98}>
      <PowerhouseBG f={f} parallax={0.3} door={0.5} />
      <FieldGenset f={f} x={330} y={900} s={0.82} spin={1} burning={0.5} groundY={300} />
      <BatteryCabinet f={f} x={790} y={906} s={0.80} charge={0.85} groundY={276} />
      <path d="M 452 1104 H 676" stroke={INK} strokeWidth={8} />
      <ProbeResponse f={f} x1={666} x2={462} y={1104} p={trip} amp={30} w={7} />
      <Plate x={540} y={1120} text="PROBE THE GRID" size={30} />
      {curve > 0 && (
        <g opacity={curve}>
          {/* the transfer curve drawing itself from out minus back */}
          <rect x={700} y={980} width={280} height={150} rx={4} fill="#20262B" stroke={INK} strokeWidth={3} />
          <path d={Array.from({length: 40}, (_, i) => {
            const t = i / 39;
            if (t > curve) return '';
            return `${720 + t * 240},${1100 - Math.sin(t * 4.2) * 46 * Math.exp(-t * 1.1)}`;
          }).filter(Boolean).map((s, i) => (i === 0 ? `M ${s}` : `L ${s}`)).join(' ')}
                fill="none" stroke={VIOLET} strokeWidth={5} strokeLinecap="round" />
          <Plate x={540} y={1206} text="LEARN HOW IT ANSWERS" size={26} />
        </g>
      )}
      <DayGrade f={f} amount={0.5} floor={0.3} haze={0.14} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/** S9 71.89-83.45 — THE TEST, held. The photograph is sharp and already out of date. */
const S9: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const shot = ent(f, 6, SNAP);
  const pin = ent(f, at(p, 9, 4.5), SETTLE, 26);
  const drift = interpolate(f, [at(p, 9, 5.0), p.dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage f={f} dur={p.dur} drift={0.35} zoom={1.08}>
      <PowerhouseBG f={f} parallax={0.2} door={0.45} />
      {/* the real machine, changing behind the photograph */}
      <g transform={`translate(${drift * 26} ${drift * -12})`}>
        <FieldGenset f={f} x={330} y={940} s={0.82} spin={1} burning={0.35} groundY={300} phase={0.6} />
      </g>
      {/* the pinned photograph: sharp, correct, and frozen */}
      {pin.o > 0 && (
        <g opacity={pin.o} transform={`translate(0 ${pin.dy}) rotate(${-2 + drift * 1.4} 700 880)`}>
          <ContactShadow cx={700} cy={1064} rx={168} ry={12} opacity={0.24} />
          <rect x={528} y={700} width={344} height={364} rx={3} fill="#F1EDE3" stroke={INK} strokeWidth={4} />
          <rect x={548} y={720} width={304} height={272} fill="#8E9AA0" />
          <g opacity={0.85}>
            <FieldGenset f={0} x={700} y={880} s={0.28} spin={0} burning={0} groundY={300} />
          </g>
          <text x={700} y={1032} textAnchor="middle" fontSize={22} fontFamily={MONO} fill="#39424A">08:14</text>
          <circle cx={700} cy={712} r={9} fill="#B44A3A" stroke={INK} strokeWidth={2.5} />
        </g>
      )}
      <Plate x={540} y={1120} text="A MEASUREMENT IS THE MOMENT" size={26} />
      {drift > 0.35 && <Plate x={540} y={1206} text="LOAD SWINGS  ·  FORTY BELOW" size={24} />}
      <DayGrade f={f} amount={0.48} floor={0.3} haze={0.13} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/** S10 83.45-90.66 — the strip accumulates, and the value seats into the inverter. */
const S10: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const n = Math.min(5, Math.floor(interpolate(f, [4, 66], [0, 5.4], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})));
  const seat = ent(f, at(p, 10, 3.8), SNAP, 44);
  const shut = interpolate(f, [at(p, 10, 2.6), at(p, 10, 5.0)], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <Stage f={f} dur={p.dur} drift={0.6} zoom={1.02}>
      <PowerhouseBG f={f} parallax={0.3} door={0.5} />
      {Array.from({length: n}, (_, i) => (
        <g key={i} transform={`translate(${180 + i * 172} ${820 + ihash(9, i) * 14}) rotate(${ihash(3, i) * 3})`}>
          <ContactShadow cx={0} cy={124} rx={72} ry={9} opacity={0.2} />
          <rect x={-70} y={-92} width={140} height={216} rx={3} fill="#F1EDE3" stroke={INK} strokeWidth={3.5} />
          <rect x={-58} y={-80} width={116} height={150} fill="#8E9AA0" />
          <text x={0} y={104} textAnchor="middle" fontSize={19} fontFamily={MONO} fill="#39424A">
            {['08:14', '09:14', '10:14', '11:14', '12:14'][i]}
          </text>
        </g>
      ))}
      <Plate x={540} y={1120} text="A NEW ONE ANY HOUR" size={30} />
      {seat.o > 0 && (
        <g opacity={seat.o} transform={`translate(0 ${seat.dy})`}>
          <Plate x={540} y={1206} text="ALREADY ON THE WALL" size={26} />
        </g>
      )}
      {/* the drawer closes on its own behind them, because nobody needs it any more */}
      <g opacity={0.9}>
        <FilingDrawer f={f} x={872} y={1000} s={0.6} open={shut} card={shut} />
      </g>
      <DayGrade f={f} amount={0.5} floor={0.3} haze={0.14} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/** S11 90.66-100.05 — St. Mary's. The operators got there first. */
const S11: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const land = ent(f, 4, SNAP, 80);
  const panel = interpolate(f, [at(p, 11, 6.8), at(p, 11, 8.6)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const rec = ent(f, at(p, 11, 4.3), SETTLE, 40);
  return (
    <Stage f={f} dur={p.dur} drift={0.8} zoom={0.98}>
      <PowerhouseBG f={f} parallax={0.5} door={1} />
      <g opacity={land.o} transform={`translate(0 ${land.dy})`}>
        <ShippedCrate f={f} x={520} y={940} s={0.94} open={panel} />
        {panel > 0.1 && <Hand f={f} x={742} y={1002} s={0.78} rot={-24} />}
      </g>
      <Plate x={540} y={1120} text="ST. MARY'S  ·  1 MW / 1 MWh  ·  2023" size={24} />
      {rec.o > 0 && (
        <g opacity={rec.o} transform={`translate(0 ${rec.dy})`}>
          <Plate x={540} y={1206} text="SANDIA  ·  DEPLOYMENT" size={25} />
        </g>
      )}
      <DayGrade f={f} amount={0.56} floor={0.32} haze={0.18} sunX={0.05} sunY={0.2} />
    </Stage>
  );
};

/** S12 100.05-107.6 — the lab boundary, the case finally leaves, THE SIGNATURE PULL-BACK. */
const S12: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const bound = interpolate(f, [4, 34], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pull = interpolate(f, [at(p, 12, 3.35), p.dur], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const caseX = interpolate(f, [at(p, 12, 1.6), at(p, 12, 4.4)], [140, -260], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const z = 1.34 - pull * 0.62;
  return (
    <Stage f={f} dur={p.dur} drift={0.4} zoom={z}>
      <PowerhouseBG f={f} parallax={0.3} door={0.9} />
      {/* the dashed laboratory boundary, with the powerhouse floor beyond it, never entered */}
      <g opacity={bound}>
        <rect x={150} y={620} width={790} height={600} rx={8} fill="none" stroke={INK}
              strokeWidth={5} strokeDasharray="26 18" strokeDashoffset={-f * 0.5} opacity={0.75} />
        <Plate x={280} y={620} text="LABORATORY" size={22} />
      </g>
      <g transform={`translate(${caseX} 1246) scale(0.5)`} opacity={caseX < 120 ? 1 : 0.85}>
        <rect x={-74} y={-32} width={148} height={124} rx={9} fill="#7A5A3E" stroke={INK} strokeWidth={4} />
        <path d="M -24 -32 q 24 -30 48 0" fill="none" stroke={INK} strokeWidth={6} />
      </g>
      {/* THE SIGNATURE SHOT: the plate revealed as a grid of operating-point columns */}
      <RatingPlate f={f} x={540} y={912} s={0.78 + pull * 0.12} kw="365 kW"
                   columns={pull > 0.25 ? 6 : 1} written={pull > 0.25 ? 1 : 0} />
      <Plate x={540} y={1120} text="THE FAIRBANKS AWARD  ·  A LAB TEST BED" size={23} />
      {pull > 0.5 && <Plate x={540} y={1206} text="ONE COLUMN MEASURED" size={26} />}
      <DayGrade f={f} amount={0.5} floor={0.3} haze={0.14} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/** S13 107.6-116.0 — the cover sheet slides off an unchanged methods list. */
const S13: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const on = interpolate(f, [4, 26], [-620, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const off = interpolate(f, [at(p, 13, 3.6), at(p, 13, 5.4)], [0, 760], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const tick = Math.floor(interpolate(f, [at(p, 13, 4.6), at(p, 13, 7.2)], [0, 3.4], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  const T = tones('#D8D3C4');
  return (
    <Stage f={f} dur={p.dur} drift={0.3} zoom={1.06}>
      <PowerhouseBG f={f} parallax={0.15} door={0.4} />
      <defs><FormGradient id="mlf" t={T} softness={1.1} /></defs>
      {/* the methods list, which never changes */}
      <g>
        <ContactShadow cx={540} cy={1082} rx={330} ry={14} opacity={0.24} />
        <rect x={252} y={648} width={576} height={404} rx={5} fill="url(#mlf)" stroke={INK} strokeWidth={4} />
        {['TRANSFER FUNCTIONS', 'STABILITY SPECIFICATIONS', 'ACTIVE DAMPING'].map((s, i) => (
          <text key={i} x={288} y={766 + i * 96} fontSize={26} fontFamily={MONO} fill="#242A2E">{s}</text>
        ))}
        {tick > 0 && (
          <g>
            {['artificial intelligence', 'machine learning', 'neural'].slice(0, Math.min(3, tick)).map((s, i) => (
              <g key={i}>
                <text x={252} y={1010 + i * 0} fontSize={0} fill="none">{s}</text>
              </g>
            ))}
          </g>
        )}
      </g>
      {/* the cover sheet with the bigger word, sliding on and then off */}
      <g transform={`translate(${on + off} 0)`} opacity={off > 700 ? 0 : 1}>
        <ContactShadow cx={540} cy={1010} rx={300} ry={16} opacity={0.26} />
        <rect x={286} y={620} width={508} height={360} rx={5} fill="#E9E4D6" stroke={INK} strokeWidth={4.5} />
        <text x={540} y={830} textAnchor="middle" fontSize={62} fontFamily={BOLD} fontWeight={900}
              fill="#242A2E" stroke={INK} strokeWidth={5} paintOrder="stroke">A.I.</text>
      </g>
      <Plate x={540} y={1074} text="NO AI  ·  NO MACHINE LEARNING" size={26} />
      {tick >= 3 && <Plate x={540} y={1206} text="IT SAYS DATA DRIVEN" size={28} bg="#2B2456" />}
      <DayGrade f={f} amount={0.48} floor={0.3} haze={0.12} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/** S14 116.0-end — the date on the threshold, the held breath, the button. */
const S14: React.FC<SceneProps & {dur: number}> = (p) => {
  const f = useCurrentFrame();
  const stencil = ent(f, 4, SNAP);
  const toPlate = at(p, 15);
  const tap = interpolate(f, [toPlate + 18, toPlate + 36], [0, 2], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pulse = interpolate(f, [toPlate + 96, p.dur - 4], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const onPlate = f >= toPlate;
  return (
    <Stage f={f} dur={p.dur} drift={0.35} zoom={onPlate ? 1.06 : 0.92}>
      <PowerhouseBG f={f} parallax={0.25} door={0.8} />
      {!onPlate && (
        <g opacity={stencil.o}>
          <rect x={150} y={1000} width={790} height={6} fill={INK} opacity={0.7} />
          <rect x={150} y={1000} width={790} height={220} fill="none" stroke={INK}
                strokeWidth={5} strokeDasharray="26 18" strokeDashoffset={-f * 0.5} opacity={0.6} />
          <Plate x={540} y={1108} text="STARTS AUGUST 15TH 2026" size={30} />
          <Plate x={540} y={1212} text="NOT YET" size={26} /> {/* plate-overlap-ok: never shares a frame with the button plates */}
        </g>
      )}
      {onPlate && (
        <g>
          <RatingPlate f={f} x={540} y={880} s={1.02} kw="365 kW" columns={1} written={0} />
          <Hand f={f} x={760} y={1010} s={1.05} tap={tap} rot={-14} />
          {pulse > 0 && (
            <ProbeResponse f={f} x1={880} x2={200} y={880} p={Math.min(1, pulse * 1.3)} amp={16} w={6} />
          )}
          <Plate x={540} y={1120} text="THE PLATE STILL WON'T SAY" size={28} /> {/* plate-overlap-ok: the onPlate branch, the stencil plates are gone by here */}
          {pulse > 0.25 && <Plate x={540} y={1206} text="FAIRBANKS IS GOING TO ASK IT" size={25} />}
        </g>
      )}
      <DayGrade f={f} amount={0.5} floor={0.3} haze={0.14} sunX={0.06} sunY={0.22} />
    </Stage>
  );
};

/* ================================================================ captions */
const Captions: React.FC<{cues: {t: number; d: number; text: string}[]}> = ({cues}) => {
  const f = useCurrentFrame();
  const t = f / FPS;
  const cue = cues.find((c) => t >= c.t && t < c.t + c.d);
  if (!cue) return null;
  const SIZE = 42;
  const perLine = Math.max(8, Math.floor((W - 84) / (SIZE * HEAD_ADV)));
  const words = cue.text.split(' ');
  const rows: string[] = [];
  let row = '';
  for (const w of words) {
    if (row && (row + ' ' + w).length > perLine) { rows.push(row); row = w; } else {
      row = row ? row + ' ' + w : w;
    }
    if (rows.length === 2) break;
  }
  if (row && rows.length < 2) rows.push(row);
  const top = CAPTION_TOP + (rows.length > 1 ? 46 : 84);
  return (
    <Frame>
      <rect x={0} y={CAPTION_TOP} width={W} height={CAPTION_H} fill={INK} opacity={0.72} data-band="ok" />
      {rows.map((r, i) => (
        <text key={i} x={W / 2} y={top + i * 52} fill="#F4EEE0" fontSize={SIZE} fontFamily={BOLD}
              fontWeight={800} textAnchor="middle" stroke={INK} strokeWidth={7} paintOrder="stroke">
          {r}
        </text>
      ))}
    </Frame>
  );
};

/* ================================================================= episode */
export const ep0813Schema = z.object({
  captions: z.array(z.object({t: z.number(), d: z.number(), text: z.string()})).optional(),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  lines: z.array(z.number()).optional(),
  credits: z.any().optional(),
  mouth: z.any().optional(),
  accents: z.any().optional(),
});

const SCENES = [S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S11, S12, S13, S14];

// Fallback bounds so the composition renders before build_scenes.py has run.
const DEFAULT_LINES = [0, 4.17, 10.08, 16.87, 25.82, 36.07, 44.16, 53.11, 63.37, 71.89,
                       83.45, 90.66, 100.05, 108.13, 116.65, 121.26];
const DEFAULT_STARTS = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14];

export const Ep0813: React.FC<z.infer<typeof ep0813Schema>> = ({
  captions = [], scenes, total, lines, credits, mouth, accents,
}) => {
  const {fps} = useVideoConfig();
  const L = lines && lines.length >= 16 ? lines : DEFAULT_LINES;
  const totalF = total ?? Math.round(130 * fps);
  const bounds = scenes ?? DEFAULT_STARTS.map((li, i) => {
    const from = Math.round(L[li] * fps);
    const nextLi = DEFAULT_STARTS[i + 1];
    const end = nextLi === undefined ? totalF : Math.round(L[nextLi] * fps);
    return {from, dur: end - from};
  });

  return (
    <VoiceProvider data={(mouth || accents) ? ({mouth, accents} as never) : null}>
      <AbsoluteFill style={{backgroundColor: '#6E787E'}}>
        {SCENES.map((Comp, i) => {
          const b = bounds[i];
          if (!b || b.dur <= 0) return null;
          return (
            <Sequence key={i} from={b.from} durationInFrames={b.dur} name={`S${i + 1}`}>
              <Comp t0={b.from / fps} L={L} dur={b.dur} />
            </Sequence>
          );
        })}
        <Captions cues={captions} />
        {credits ? (
          <Sequence from={totalF - (credits.frames ?? 195)} durationInFrames={credits.frames ?? 195} name="CREDITS">
            <EndCredits data={credits} durationInFrames={credits.frames ?? 195} />
          </Sequence>
        ) : null}
      </AbsoluteFill>
    </VoiceProvider>
  );
};
