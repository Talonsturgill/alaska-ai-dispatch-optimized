import React from 'react';
import {INK, tones, FormGradient, RimLight, ContactShadow} from './lighting';
// vitals(): shared living-idle primitive — see motion.tsx (2026-07-26 repeat-offender fix).
import {vitals} from './motion';

// Net-new sensor assets for the 2026-07-21c beluga Dispatch: the robot EYE (SatelliteEye /
// GAIA) and the robot EAR (ListeningMooring / passive-acoustic node). Flat-vector IGS 2.5D
// house style: thick ink outlines, form-shaded fills, the sensors are the only sharp
// synthetic light in a soft natural world. Reusable for any future remote-sensing / PAM story.

const uid = (s: string) => 'sx' + Math.abs([...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 7)).toString(36);
const MINT = '#31e0b6';
const GOLD = '#ffd24a';

// ---- the ORBITAL EYE: angular bus, twin solar wings, comms dish, down-looking lens ----
export const SatelliteEye: React.FC<{
  x: number; y: number; scale?: number; f: number; facing?: 1 | -1;
  scanCone?: number; lensGlow?: number;
}> = ({x, y, scale = 1, f, facing = 1, scanCone = 0, lensGlow = 0.3}) => {
  const id = uid(`sat${x}${y}`);
  const hull = tones('#6b7683');
  const gold = tones('#ffd24a');
  const cone = Math.max(0, Math.min(1, scanCone));
  const glow = Math.max(0, Math.min(1, lensGlow));
  const yaw = Math.sin(f / 42) * 6;                 // orbital drift (visible idle)
  const bob = vitals(f, 6.0, 2.6).bob;              // living idle (vitals) — was a single sine
  const dish = (f * 2.6) % 360;
  const blink = (Math.sin(f / 8) > 0.6) ? 1 : 0.25;
  const wing = Math.sin(f / 40) * 2.4;
  return (
    <g transform={`translate(${x},${y + bob}) scale(${scale * facing},${scale}) rotate(${yaw})`}>
      <FormGradient id={id} t={hull} />
      <FormGradient id={`${id}_g`} t={gold} />
      {/* the scan cone driving down (the eye looking at the inlet) */}
      {cone > 0.02 && (
        <g opacity={cone} style={{mixBlendMode: 'screen'}}>
          <path d={`M-28,58 L${-56 - 130 * cone},520 L${56 + 130 * cone},520 L28,58 Z`} fill={GOLD} opacity={0.16} />
          <line x1={0} y1={58} x2={0} y2={520} stroke={GOLD} strokeWidth={3} opacity={0.4} />
        </g>
      )}
      {/* solar wings on struts */}
      <line x1={-54} y1={0} x2={-30} y2={0} stroke={hull.shade} strokeWidth={6} />
      <line x1={54} y1={0} x2={30} y2={0} stroke={hull.shade} strokeWidth={6} />
      <g transform={`translate(-102,0) rotate(${wing})`}>
        <rect x={-48} y={-34} width={96} height={68} rx={4} fill="#26303a" stroke={INK} strokeWidth={4} />
        {[0, 1, 2].map((i) => <line key={i} x1={-48 + (i + 1) * 24} y1={-34} x2={-48 + (i + 1) * 24} y2={34} stroke="#3d4a57" strokeWidth={2} />)}
        <line x1={-48} y1={0} x2={48} y2={0} stroke="#3d4a57" strokeWidth={2} />
      </g>
      <g transform={`translate(102,0) rotate(${-wing})`}>
        <rect x={-48} y={-34} width={96} height={68} rx={4} fill="#26303a" stroke={INK} strokeWidth={4} />
        {[0, 1, 2].map((i) => <line key={i} x1={-48 + (i + 1) * 24} y1={-34} x2={-48 + (i + 1) * 24} y2={34} stroke="#3d4a57" strokeWidth={2} />)}
        <line x1={-48} y1={0} x2={48} y2={0} stroke="#3d4a57" strokeWidth={2} />
      </g>
      {/* comms dish */}
      <g transform={`translate(0,-56) rotate(${Math.sin(dish * Math.PI / 180) * 6})`}>
        <ellipse cx={0} cy={0} rx={22} ry={10} fill={`url(#${id}_g)`} stroke={INK} strokeWidth={3} />
        <line x1={0} y1={2} x2={0} y2={20} stroke={hull.shade} strokeWidth={4} />
      </g>
      {/* the bus body */}
      <rect x={-34} y={-40} width={68} height={80} rx={6} fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
      <RimLight d="M-34,-38 L34,-38" w={4} opacity={0.6} />
      <rect x={-24} y={-26} width={18} height={14} rx={3} fill="#26303a" stroke={INK} strokeWidth={2.5} />
      {/* down-looking lens barrel */}
      <rect x={-14} y={38} width={28} height={28} rx={4} fill={hull.core} stroke={INK} strokeWidth={4} />
      <circle cx={0} cy={70} r={16} fill={GOLD} stroke={INK} strokeWidth={4} opacity={0.45 + 0.55 * glow} />
      <circle cx={-4} cy={66} r={6} fill="#fff" opacity={0.55 * glow} style={{mixBlendMode: 'screen'}} />
      {/* telemetry light */}
      <circle cx={22} cy={-30} r={5} fill="#ff6a4a" opacity={blink} />
    </g>
  );
};

// ---- the SEAFLOOR EAR: anchor base, ribbed cylinder, mint hydrophone dome, tether float ----
export const ListeningMooring: React.FC<{
  x: number; y: number; scale?: number; f: number; detect?: number;
}> = ({x, y, scale = 1, f, detect = 0}) => {
  const id = uid(`moor${x}${y}`);
  const metal = tones('#5b6672');
  const d = Math.max(0, Math.min(1, detect));
  const floatBob = Math.sin(f / 20) * 7;
  const throb = 0.6 + 0.4 * Math.sin(f / 6);
  const DOME_Y = -150;
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <FormGradient id={id} t={metal} />
      {/* sonar rings blooming from the dome when it detects a call */}
      {d > 0.04 && [0, 1, 2, 3].map((i) => {
        const phase = ((f / 26) + i / 4) % 1;
        const r = 16 + phase * 260 * d;
        return <circle key={i} cx={0} cy={DOME_Y} r={r} fill="none" stroke={MINT} strokeWidth={6 * (1 - phase) + 1} opacity={(1 - phase) * 0.6 * d} />;
      })}
      {/* tether up to a small surface float */}
      <line x1={0} y1={DOME_Y} x2={0} y2={DOME_Y - 190} stroke={metal.shade} strokeWidth={3} opacity={0.5} strokeDasharray="4 7" />
      <g transform={`translate(0,${DOME_Y - 200 + floatBob})`}>
        <circle cx={0} cy={0} r={15} fill={GOLD} stroke={INK} strokeWidth={4} />
        <circle cx={-4} cy={-4} r={4} fill="#fff" opacity={0.5} style={{mixBlendMode: 'screen'}} />
      </g>
      {/* anchor base sitting on the seabed */}
      <path d="M-70,0 L70,0 L46,-40 L-46,-40 Z" fill={metal.core} stroke={INK} strokeWidth={5} strokeLinejoin="round" />
      <ellipse cx={0} cy={2} rx={78} ry={12} fill={INK} opacity={0.28} />
      {/* ribbed cylinder body */}
      <rect x={-26} y={-150} width={52} height={112} rx={10} fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
      {[0, 1, 2].map((i) => <line key={i} x1={-26} y1={-120 + i * 34} x2={26} y2={-120 + i * 34} stroke={metal.shade} strokeWidth={3} opacity={0.6} />)}
      <RimLight d="M-24,-148 L24,-148" w={3.5} opacity={0.55} />
      {/* the mint hydrophone dome (the ear) */}
      <circle cx={0} cy={DOME_Y} r={22} fill="#0f1c1a" stroke={INK} strokeWidth={5} />
      <circle cx={0} cy={DOME_Y} r={13} fill={MINT} opacity={0.35 + 0.5 * throb} />
      <circle cx={0} cy={DOME_Y} r={6} fill="#eafff8" opacity={0.6 * throb} style={{mixBlendMode: 'screen'}} />
    </g>
  );
};

// ---- the GROUND EAR: SeismicStation (NET-NEW 2026-07-25) --------------------------------
// The shelf had an orbital EYE (SatelliteEye) and a seafloor EAR (ListeningMooring) but
// nothing that listens to the GROUND, which is the entire subject of the landslide-detection
// Dispatch. Deliberate shape language per out/dispatch/art_direction.json: SOFT ROUND
// INSTRUMENT against HARD ANGULAR LAND, so the silhouette states the mismatch between a small
// earnest machine and something enormous and indifferent, before a word is spoken.
//
// THE EMOTIONAL TELL is the copper gramophone horn. It is the whole performance:
//   listening  lazy quarter-turn sweeps, lamp softly pulsing
//   straining  horn telescopes out past what looks comfortable, rim trembles, stress lines
//   missing    horn goes slack and rolls down to point at the dirt, rim dented, lamp DARK
//   heard      horn snaps rigid toward the source, rim flares one notch, lamp hard warm
// `heard` is the ONLY state that lights the lamp. A scene must not light it any other way,
// because in this piece a lit lamp means a detection actually fired.
export const SeismicStation: React.FC<{
  x: number; y: number; f: number; scale?: number;
  emotion?: 'listening' | 'straining' | 'missing' | 'heard';
  heading?: number;      // deg the horn faces, negative rotates it toward screen-left
  lamp?: number;         // 0..1 chest detection lamp. Only lights when emotion === 'heard'
  accent?: number;       // 0..1 VO-emphasis reactivity, kicks the body
  look?: number;         // -1..1 where the eyes track (-1 screen-left, 1 screen-right)
  groundY?: number;      // where the contact shadow and dirt collar land
  tint?: string;         // body base, so a night palette can re-tint without a re-draw
}> = ({
  x, y, f, scale = 1, emotion = 'listening', heading = -20, lamp = 0,
  accent = 0, look = 0, groundY = 0, tint = '#7E8C82',
}) => {
  const id = uid(`seis${x}${y}${tint}${emotion}`);
  const body = tones(tint);
  const copper = tones('#DCA94B');   // BRASS, deliberately in the lantern-amber family. Ember/rust is RESERVED for falling rock and must never touch an instrument.
  const strain = emotion === 'straining' ? 1 : 0;
  const miss = emotion === 'missing' ? 1 : 0;
  const heard = emotion === 'heard' ? 1 : 0;

  const bob = vitals(f, 7.0, 0.9).bob * (1 - miss * 0.6);   // living idle (vitals) — was a single sine
  const kick = accent * 6;
  const sweep = emotion === 'listening' ? Math.sin(f / 30) * 14 : 0;
  const tremble = strain * Math.sin(f / 3.0) * 2.6;
  const hornRot = heading + sweep + tremble + miss * 82;
  const reach = 1 + strain * 0.34;
  const flare = 1 + heard * 0.14;
  const lampOn = heard * Math.max(0, Math.min(1, lamp));
  const lampPulse = 0.55 + 0.45 * Math.sin(f / 7);
  // blink: mostly open, a fast close on an irrational period so paired stations desync
  const blink = (Math.sin(f / 37 + x * 0.013) > 0.965) ? 0.12 : 1;
  const eyeShift = look * 4.4 + (miss ? 0 : Math.sin(f / 44) * 1.2);
  const browDrop = miss * 6 + strain * 4;

  return (
    <g transform={`translate(${x},${y + bob - kick}) scale(${scale})`}>
      <FormGradient id={id} t={body} softness={0.6} />
      <FormGradient id={`${id}c`} t={copper} softness={0.58} />
      <ContactShadow cx={0} cy={groundY} rx={104} ry={19} opacity={0.45} blur={14} />

      {/* ================= THE HORN, the emotional tell =================
          Built as a real CONE in 3/4, not a disc: two straight taper walls opening
          from the throat to an elliptical mouth, with a visibly HOLLOW dark interior,
          a thick rolled rim, and interior throat rings receding to a vanishing point.
          Pass 1 drew the bell as a flat face-on ellipse and it read as a lollipop. */}
      <g transform={`translate(4,-150) rotate(${hornRot})`}>
        {(() => {
          const L = 118 * reach;            // throat -> mouth distance
          const rx = 30 * flare;            // mouth half-width
          const ry = 54 * flare;            // mouth half-height (long axis, seen near-on)
          const tw = 13;                    // throat half-height
          // cone body: throat at origin, opening to the mouth ellipse at x = L
          const cone = `M0,${-tw} L${L},${-ry} L${L},${ry} L0,${tw} Z`;
          return (
            <>
              <path d={cone} fill={INK} stroke={INK} strokeWidth={16} strokeLinejoin="round" />
              <path d={cone} fill={`url(#${id}c)`} />
              {/* the lit upper wall, so the cone reads as a solid with a top and a bottom */}
              <path d={`M0,${-tw} L${L},${-ry} L${L},${-ry * 0.34} L0,${-tw * 0.2} Z`} fill={copper.key} opacity={0.5} />
              {/* the shaded lower wall */}
              <path d={`M0,${tw} L${L},${ry} L${L},${ry * 0.42} L0,${tw * 0.24} Z`} fill={copper.shade} opacity={0.72} />
              {/* THE OPEN MOUTH: dark hollow interior */}
              <ellipse cx={L} cy={0} rx={rx} ry={ry} fill={INK} />
              <ellipse cx={L} cy={0} rx={rx * 0.84} ry={ry * 0.88} fill="#20120A" />
              {/* interior throat rings receding toward the throat (depth cue) */}
              {[0.68, 0.46, 0.28, 0.15].map((k, i) => (
                <ellipse key={i} cx={L - (1 - k) * 26} cy={0} rx={rx * 0.84 * k} ry={ry * 0.88 * k}
                  fill="none" stroke={copper.shade} strokeWidth={2.6} opacity={0.34 + i * 0.08} />
              ))}
              {/* the rolled rim: a thick bright lip on the lit side of the mouth */}
              <path d={`M${L},${-ry} a${rx},${ry} 0 0 0 0,${ry * 2}`} fill="none" stroke={copper.key} strokeWidth={9} strokeLinecap="round" opacity={0.95} />
              <path d={`M${L},${-ry} a${rx},${ry} 0 0 1 0,${ry * 2}`} fill="none" stroke={copper.shade} strokeWidth={7} strokeLinecap="round" opacity={0.85} />
              {/* dent on the rim, only when it missed */}
              {miss > 0 && <path d={`M${L - 4},${-ry * 0.42} q13,12 1,24`} fill="none" stroke={INK} strokeWidth={7} strokeLinecap="round" />}
              {/* support strut from the post collar to the underside of the horn */}
              <path d={`M14,${tw + 2} L${L * 0.52},${ry * 0.52}`} stroke={INK} strokeWidth={11} strokeLinecap="round" />
              <path d={`M14,${tw + 2} L${L * 0.52},${ry * 0.52}`} stroke={body.core} strokeWidth={5} strokeLinecap="round" />
              {/* strain: stress lines snapping off the throat joint */}
              {strain > 0 && [0, 1, 2].map((i) => (
                <path key={i} d={`M${-10 - i * 6},${-14 - i * 10} l-16,-8`} stroke="#F4EDDD" strokeWidth={4}
                  strokeLinecap="round" opacity={0.45 + 0.35 * Math.sin(f / 4 + i)} />
              ))}
              {/* heard: three sound arcs arriving INTO the mouth */}
              {heard > 0 && [0, 1, 2].map((i) => {
                const ph = ((f / 22) + i / 3) % 1;
                return <path key={i} d={`M${L + 26 + ph * 44},${-ry * 0.8} a${34},${ry * 0.8} 0 0 1 0,${ry * 1.6}`}
                  fill="none" stroke="#F2B33D" strokeWidth={6 * (1 - ph) + 1.5} opacity={(1 - ph) * 0.85} strokeLinecap="round" />;
              })}
            </>
          );
        })()}
      </g>

      {/* ================= antenna, with secondary sway ================= */}
      <g transform={`translate(-46,-142) rotate(${-7 + Math.sin(f / 21) * 4})`}>
        <line x1={0} y1={0} x2={0} y2={-66} stroke={INK} strokeWidth={8} strokeLinecap="round" />
        <line x1={0} y1={0} x2={0} y2={-66} stroke={body.key} strokeWidth={3.4} strokeLinecap="round" />
        <circle cx={0} cy={-71} r={8} fill={INK} />
        <circle cx={0} cy={-71} r={4.6} fill="#F2B33D" opacity={0.45 + 0.55 * Math.sin(f / 11)} />
      </g>

      {/* ================= solar panel, canted like a cap brim ================= */}
      <g transform={`translate(-6,-176) rotate(${-16 - strain * 10 + miss * 14})`}>
        <rect x={-56} y={-11} width={112} height={22} rx={5} fill={INK} />
        <rect x={-51} y={-7} width={102} height={14} rx={3} fill="#1B3D4E" />
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line key={i} x1={-51 + (i + 1) * 14.5} y1={-7} x2={-51 + (i + 1) * 14.5} y2={7} stroke="#2F607A" strokeWidth={2.4} />
        ))}
        <RimLight d="M-51,-7 L51,-7" w={3.2} color="#A9DCF2" opacity={0.55} />
      </g>

      {/* ================= the post body ================= */}
      <g>
        <path d={`M-70,-150 q70,-26 140,0 L72,${44} q-72,24 -144,0 Z`} fill={INK} />
        <path d={`M-63,-143 q63,-23 126,0 L64,${37} q-64,21 -128,0 Z`} fill={`url(#${id})`} />
        {[-108, -76, -44, -12, 20].map((yy, i) => (
          <path key={i} d={`M-62,${yy} q62,-16 124,0`} fill="none" stroke={body.shade} strokeWidth={4.4} opacity={0.5} />
        ))}
        {/* collar the horn throat plugs into */}
        <ellipse cx={2} cy={-146} rx={38} ry={13} fill={INK} />
        <ellipse cx={2} cy={-148} rx={31} ry={10} fill={body.core} />

        {/* ---- THE FACE. Pass 1 had none and the hero read inert. ---- */}
        {/* brow bar, drops when straining or missing */}
        <path d={`M-40,${-104 + browDrop} q40,-11 80,0`} fill="none" stroke={INK} strokeWidth={7} strokeLinecap="round" opacity={0.9} />
        {[-22, 22].map((ex, i) => (
          <g key={i} transform={`translate(${ex + eyeShift},-84)`}>
            <ellipse cx={0} cy={0} rx={15} ry={16 * blink} fill="#F4EDDD" stroke={INK} strokeWidth={4.5} />
            {blink > 0.5 && <>
              <circle cx={look * 3.6} cy={miss ? 3.5 : 0} r={7} fill="#12201B" />
              <circle cx={look * 3.6 - 2.4} cy={(miss ? 3.5 : 0) - 2.6} r={2.6} fill="#FFFFFF" opacity={0.85} />
            </>}
          </g>
        ))}
        {/* chest detection lamp, an instrument below the face */}
        <circle cx={0} cy={-28} r={22} fill={INK} />
        <circle cx={0} cy={-28} r={15.5} fill="#241C10" />
        <circle cx={0} cy={-28} r={13} fill="#F2B33D" opacity={lampOn * lampPulse} />
        <circle cx={0} cy={-28} r={6.5} fill="#FFD98A" opacity={lampOn * 0.9}
          style={lampOn > 0.2 ? {filter: 'drop-shadow(0 0 16px #F2B33D)'} : undefined} />
        <circle cx={0} cy={-28} r={22} fill="none" stroke={body.key} strokeWidth={2.8} opacity={0.5} />
        {[0, 1, 2, 3].map((i) => {
          const a = (i * Math.PI) / 2 + Math.PI / 4;
          return <line key={i} x1={Math.cos(a) * 26} y1={-28 + Math.sin(a) * 26} x2={Math.cos(a) * 31} y2={-28 + Math.sin(a) * 31}
            stroke={body.key} strokeWidth={3} strokeLinecap="round" opacity={0.55} />;
        })}
        {/* vent slots + a stencilled plate (detail density) */}
        {[0, 1, 2].map((i) => (
          <rect key={i} x={-30 + i * 22} y={6} width={13} height={5} rx={2.5} fill={INK} opacity={0.65} />
        ))}
        <RimLight d="M-61,-136 q61,-21 122,0" w={4.4} color="#F4EDDD" opacity={0.45} />
        <RimLight d="M-63,-140 L-58,30" w={3.4} color="#F4EDDD" opacity={0.3} />
      </g>

      {/* ================= the hard angular dirt collar ================= */}
      <path d={`M-124,${groundY} l44,-20 l34,11 l32,-15 l40,17 l32,-9 l36,16 Z`} fill={INK} opacity={0.92} />
      <path d={`M-117,${groundY} l42,-16 l32,10 l30,-13 l38,15 l30,-8 l34,12 Z`} fill="#12271F" />
    </g>
  );
};
