import React from 'react';
import {tones, FormGradient, RimLight, ContactShadow, INK} from './lighting';
import {vitals} from './motion';

// ============================================================================
// THE SYSTEM IDENTIFICATION GRAMMAR — lib/identify.tsx
// NET-NEW 2026-08-13 ("The Machine Nobody Wrote Down", NSF award 2626692).
//
// REAL GAP, checked against ASSET_MANIFEST.md in full first. The shelf can draw a thing
// that PERCEIVES (vision.tsx), a thing that LISTENS (sensors.tsx), a thing that CONTROLS
// (bioprocess.tsx LoopGovernor), a thing that IS NOT THERE (absence.tsx) and a thing MADE
// OF ARITHMETIC (simulation.tsx). Nothing on it draws MEASURING AN UNKNOWN SYSTEM.
//
// The distinction from absence.tsx is exact, and it is the same kind of distinction
// simulation.tsx was built on:
//     ABSENCE says   this should be here and is not.
//     SIMULATION says this is here, it is exact, and it is made of arithmetic.
//     IDENTIFY says  this is here, it plainly works, and nobody knows what it will do.
//
// THE RESERVED HUE. Violet appears ONLY on a measurement: a probe going out, a response
// coming back, and the writing those two produce. It is exported as VIOLET so a scene
// parks its readouts on the same token, and the episode registers it through
// lighting.tsx AccentRegistry so a leak throws at paint time instead of reaching a judge.
// The rule carries meaning: a violet mark is a fact the machine established for itself,
// and a blank field is blank precisely because no violet ever reached it.
// ============================================================================

export const VIOLET = '#7B4BFF';
export const VIOLET_DEEP = '#4A22B8';

export const ID = {
  green: '#3F5D4A',      // accreted service enamel, the genset's factory colour, aged
  greenLit: '#557A5F',
  oxblood: '#7A3B2E',    // rust and heat scale, the visible record of decades of service
  bone: '#E8E4DA',       // the battery cabinet, factory-new, no patina
  graphite: '#2B2F33',
  concrete: '#B9BFC0',
  glare: '#DCE6EC',      // snow-glare daylight through the open door
  shadow: '#8A9296',     // LIFTED. At high albedo a shadow fills with skylight.
} as const;

/** deterministic hash in [-1,1]; never Math.random */
export const ihash = (a: number, b: number): number => {
  let h = Math.imul(a + 0x6d2b, 0x2545f491) ^ Math.imul(b + 0x1f13, 0x27d4eb2d);
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b);
  return (((h ^ (h >>> 13)) >>> 0) / 4294967295) * 2 - 1;
};

/* ------------------------------------------------------------------ Unknown
 * A thing that is PRESENT and whose inside will not resolve.
 *
 * The contract is four clauses and each is a defect somebody already paid for:
 *  (1) a SOLID confident outline, never dashed, because the object really is there and a
 *      dashed edge would say the opposite (that is absence.tsx's job and its grammar).
 *  (2) an interior that never settles: overlapping bands slide against each other on
 *      irrational periods, so it reads as unresolved rather than as unfinished.
 *  (3) NO form gradient inside, because a form-shaded interior asserts knowledge of the
 *      shape and the whole point is that nobody has it.
 *  (4) a REQUIRED `label`, not optional, because an unlabelled unknown is indistinguishable
 *      from a rendering bug, and a caller who must type the label has to decide what the
 *      unknown thing IS. Same reasoning absence.tsx landed on for the same reason.
 */
export const Unknown: React.FC<{
  d: string; f: number; label: string; seed?: number; opacity?: number; stroke?: number;
}> = ({d, f, label, seed = 3, opacity = 1, stroke = 3}) => {
  const uid = `unk${seed}`;
  const bands = Array.from({length: 7}, (_, i) => {
    const ph = ihash(seed, i) * 40;
    return {y: -400 + i * 130, dx: Math.sin(f / (23.7 + i * 4.3) + ph) * 26, o: 0.10 + (i % 3) * 0.05};
  });
  return (
    <g opacity={opacity}>
      <defs>
        <clipPath id={`${uid}c`}><path d={d} /></clipPath>
      </defs>
      <path d={d} fill="#20262B" />
      <g clipPath={`url(#${uid}c)`}>
        {bands.map((b, i) => (
          <rect key={i} x={-600 + b.dx} y={b.y} width={2400} height={64}
                fill="#39424A" opacity={b.o} />
        ))}
      </g>
      <path d={d} fill="none" stroke={INK} strokeWidth={stroke} strokeLinejoin="round" />
      <title>{label}</title>
    </g>
  );
};

/* ------------------------------------------------------------- RatingPlate
 * THE THROUGHLINE OBJECT. A machine's plate that states what it can PRODUCE and says
 * nothing about how it BEHAVES.
 *
 * The state channel is THE WRITING, and it has two hands on purpose:
 *   STAMPED  the kilowatt figure, punched into the steel, casting a real cut shadow.
 *   MEASURED the violet column, written in a visibly different hand, because it was not
 *            issued by anybody. It was found.
 * `columns` sets how many operating-point columns exist and `written` how many carry a
 * measured value, so the film's final honest frame (one column measured, the rest blank)
 * is a PARAMETER rather than a redraw. That is deliberate: the 08-02 CoreColumn lesson was
 * that a per-item channel has to exist or the frame that makes the argument is unbuildable.
 */
export const RatingPlate: React.FC<{
  f: number; x: number; y: number; s?: number; kw?: string; columns?: number;
  written?: number; drift?: number; phase?: number; groundY?: number;
}> = ({f, x, y, s = 1, kw = '365 kW', columns = 1, written = 0, drift = 1, phase = 0, groundY}) => {
  const T = tones('#9BA6AC');
  const v = vitals(f, phase, 0.35);
  const W = 640, H = 380;
  const colW = columns > 1 ? (W - 80) / columns : W - 80;
  return (
    <g transform={`translate(${x + v.swayX * 0.4} ${y + v.bob * 0.3}) scale(${s})`}>
      <defs><FormGradient id="platef" t={T} softness={1.1} /></defs>
      {groundY !== undefined && <ContactShadow cx={0} cy={groundY} rx={W * 0.46} ry={16} opacity={0.3} />}

      {/* the plate body, brushed steel, four corner screws on a regular pitch */}
      <rect x={-W / 2} y={-H / 2} width={W} height={H} rx={8} fill="url(#platef)" />
      <rect x={-W / 2} y={-H / 2} width={W} height={H} rx={8} fill="none" stroke={INK} strokeWidth={4} />
      <RimLight d={`M ${-W / 2 + 8} ${-H / 2} H ${W / 2 - 8}`} w={3} opacity={0.5} />
      {[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sy], i) => (
        <g key={i}>
          <circle cx={sx * (W / 2 - 26)} cy={sy * (H / 2 - 26)} r={11} fill="#6E787E" stroke={INK} strokeWidth={2.5} />
          <path d={`M ${sx * (W / 2 - 26) - 6} ${sy * (H / 2 - 26)} h 12`} stroke={INK} strokeWidth={2.5} />
        </g>
      ))}
      {/* deterministic pitting so the steel is never a flat fill */}
      {Array.from({length: 26}, (_, i) => (
        <circle key={i} cx={ihash(7, i) * (W / 2 - 40)} cy={ihash(11, i) * (H / 2 - 40)}
                r={1.4 + Math.abs(ihash(13, i)) * 1.6} fill={INK} opacity={0.16} />
      ))}

      {/* THE STAMPED BAND: the one fact this plate carries, punched in with a cut shadow */}
      <text x={0} y={-H / 2 + 96} textAnchor="middle" fontSize={78} fontWeight={900}
            fontFamily="Archivo, Arial Black, sans-serif" fill="#5C666C">{kw}</text>
      <text x={-3} y={-H / 2 + 93} textAnchor="middle" fontSize={78} fontWeight={900}
            fontFamily="Archivo, Arial Black, sans-serif" fill="#C6CFD4">{kw}</text>
      <path d={`M ${-W / 2 + 40} ${-H / 2 + 122} H ${W / 2 - 40}`} stroke={INK} strokeWidth={3} opacity={0.6} />

      {/* THE BLANK GRID: milled cells that catch no shadow, with a slow interior drift so
          they read as unfilled rather than as unrendered. */}
      {Array.from({length: columns}, (_, c) => {
        const cx = -W / 2 + 40 + c * colW;
        const isWritten = c < written;
        return (
          <g key={c}>
            {Array.from({length: 4}, (_, r) => {
              const cy = -H / 2 + 146 + r * 52;
              return (
                <g key={r}>
                  <rect x={cx + 3} y={cy} width={colW - 6} height={44} rx={3}
                        fill="#7C868C" opacity={0.5} stroke={INK} strokeWidth={2} />
                  {isWritten ? (
                    <text x={cx + colW / 2} y={cy + 32} textAnchor="middle" fontSize={26}
                          fontFamily="JetBrains Mono, monospace" fill={VIOLET}
                          style={{fontStyle: 'italic'}}>
                      {['0.42', '1.18', '0.07', '2.30'][r]}
                    </text>
                  ) : (
                    <g opacity={0.75}>
                      <rect x={cx + 10 + Math.sin(f / 37.1 + r * 1.7 + c) * 5} y={cy + 18}
                            width={colW - 26} height={3} fill="#5E686E" opacity={0.5} />
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        );
      })}
      {drift > 0 && (
        <rect x={-W / 2 + 40} y={-H / 2 + 146} width={W - 80} height={4 * 52}
              fill="none" stroke={INK} strokeWidth={2.5} opacity={0.8} />
      )}
    </g>
  );
};

/* -------------------------------------------------------------- FieldGenset
 * THE RUN'S HERO. A skid-mounted village diesel generator, and its defining property is
 * that it is UNDOCUMENTED, not that it is friendly.
 *
 * SHAPE-LANGUAGE DECISION: ACCRETED. Nothing on it is parallel to anything, because
 * decades of service are drawn as geometry rather than as grime. Mismatched fasteners, a
 * patched exhaust wrap, a replacement panel in a slightly different green, weld beads that
 * are not straight, hose runs added by different hands at different times. It is not
 * shabby, it is MAINTAINED, which is a different and more respectful drawing: this machine
 * works, and the film's whole claim is that nobody wrote it down.
 *
 * IT HAS NO FACE, DELIBERATELY, and that is the AshReader/FieldRadiograph discipline
 * rather than an omission. A face is a promise that the object can tell you how it feels,
 * and this film's entire argument is that it can't tell you anything. Giving it eyes would
 * contradict the narration in every frame. State is carried by THREE non-facial channels
 * per the thrice-learned one-channel lesson: the FLYWHEEL (the only part legible at feed
 * size, and it never stops while the film is running), the EXHAUST (heat shimmer rising
 * when it is burning and gone when it is off), and the PLATE BAY (where the rating plate
 * bolts on, so the hero and the throughline are physically the same object).
 */
export const FieldGenset: React.FC<{
  f: number; x: number; y: number; s?: number; spin?: number; burning?: number;
  phase?: number; groundY?: number; accent?: number;
}> = ({f, x, y, s = 1, spin = 1, burning = 1, phase = 0, groundY = 250, accent = 0}) => {
  const T = tones(ID.green);
  const R = tones(ID.oxblood);
  const v = vitals(f, phase, 0.5 + spin * 0.5);
  const wheel = (f * 4.2 * spin) % 360;
  const kick = 1 + accent * 0.02;
  return (
    <g transform={`translate(${x + v.swayX * 0.5} ${y + v.bob * 0.45}) scale(${s * kick})`}>
      <defs>
        <FormGradient id="gsf" t={T} softness={0.95} />
        <FormGradient id="gsr" t={R} softness={0.8} />
      </defs>
      <ContactShadow cx={0} cy={groundY} rx={320} ry={26} opacity={0.34} />

      {/* skid: not level, because nothing here was installed on a drawing */}
      <path d="M -320 250 L 322 244 L 318 274 L -316 280 Z" fill="#4A5257" stroke={INK} strokeWidth={4} />
      {Array.from({length: 5}, (_, i) => (
        <rect key={i} x={-280 + i * 130} y={228} width={26} height={26} fill="#5A6368" stroke={INK} strokeWidth={2.5} />
      ))}

      {/* engine block: the big accreted mass */}
      <path d="M -262 42 L -246 -104 L 92 -116 L 116 40 L 106 232 L -252 236 Z"
            fill="url(#gsf)" stroke={INK} strokeWidth={4.5} strokeLinejoin="round" />
      <RimLight d="M -246 -104 L 92 -116" w={4} opacity={0.55} />
      {/* weld beads, not straight */}
      {Array.from({length: 4}, (_, i) => {
        const yy = 20 + i * 52;
        const pts = Array.from({length: 8}, (_, k) => `${-250 + k * 50},${yy + ihash(i, k) * 4}`).join(' L ');
        return <path key={i} d={`M ${pts}`} fill="none" stroke={INK} strokeWidth={2} opacity={0.35} />;
      })}
      {/* the replacement panel, in a slightly different green */}
      <path d="M -168 62 L -34 56 L -30 186 L -164 190 Z" fill={ID.greenLit} stroke={INK} strokeWidth={3.5} opacity={0.9} />
      {Array.from({length: 6}, (_, i) => (
        <circle key={i} cx={-158 + (i % 3) * 60} cy={78 + Math.floor(i / 3) * 96}
                r={5} fill="#6E7C72" stroke={INK} strokeWidth={2} />
      ))}

      {/* radiator grille */}
      <path d="M -262 42 L -246 -104 L -170 -108 L -184 40 Z" fill="#33463A" stroke={INK} strokeWidth={3.5} />
      {Array.from({length: 7}, (_, i) => (
        <path key={i} d={`M ${-256 + i * 11} ${34 - i * 1.4} L ${-241 + i * 11} ${-98 - i * 1.2}`}
              stroke={INK} strokeWidth={2} opacity={0.5} />
      ))}

      {/* THE FLYWHEEL, the state channel legible at feed size. It never stops. */}
      <g transform={`translate(180 96)`}>
        <circle r={92} fill="#39424A" stroke={INK} strokeWidth={4.5} />
        <circle r={92} fill="url(#gsr)" opacity={0.28} />
        <g transform={`rotate(${wheel})`}>
          {Array.from({length: 6}, (_, i) => (
            <path key={i} d={`M 0 0 L ${Math.cos((i * 60) * Math.PI / 180) * 80} ${Math.sin((i * 60) * Math.PI / 180) * 80}`}
                  stroke="#7C868C" strokeWidth={11} strokeLinecap="round" />
          ))}
          <circle r={17} fill="#6E787E" stroke={INK} strokeWidth={3} />
        </g>
        <circle r={92} fill="none" stroke={INK} strokeWidth={4.5} />
        <RimLight d="M -66 -64 A 92 92 0 0 1 62 -68" w={3.5} opacity={0.6} />
      </g>

      {/* exhaust stack with a patched wrap, and heat only when it is burning */}
      <path d="M 24 -116 L 26 -280 L 74 -282 L 72 -114 Z" fill="#4C5A52" stroke={INK} strokeWidth={4} />
      {Array.from({length: 3}, (_, i) => (
        <rect key={i} x={22} y={-268 + i * 54} width={54} height={20} fill={ID.oxblood}
              stroke={INK} strokeWidth={2.5} opacity={0.85} transform={`rotate(${ihash(5, i) * 3} 49 ${-258 + i * 54})`} />
      ))}
      {burning > 0.02 && (
        <g opacity={burning * 0.5}>
          {Array.from({length: 4}, (_, i) => (
            <path key={i} d={`M ${34 + i * 10} -286 q ${Math.sin(f / (9.3 + i * 2.1)) * 16} -46 ${Math.sin(f / (13.7 + i)) * 8} -92`}
                  fill="none" stroke="#CFD8DC" strokeWidth={5} strokeLinecap="round" opacity={0.4} />
          ))}
        </g>
      )}

      {/* hose runs added by different hands */}
      <path d={`M -184 -40 q -46 ${44 + Math.sin(f / 51.3) * 5} -8 108`} fill="none" stroke="#2E3A33" strokeWidth={13} strokeLinecap="round" />
      <path d={`M -184 -40 q -46 ${44 + Math.sin(f / 51.3) * 5} -8 108`} fill="none" stroke="#455449" strokeWidth={7} strokeLinecap="round" />

      {/* THE PLATE BAY: the hero and the throughline are the same object */}
      <rect x={-96} y={-92} width={186} height={112} rx={5} fill="#33413A" stroke={INK} strokeWidth={3} />
    </g>
  );
};

/* ----------------------------------------------------------- BatteryCabinet
 * The counterpart, and its shape language is the exact opposite: MACHINED-ORTHOGONAL.
 * Every edge parallel, panel lines exact, corner screws on a regular pitch, one flush
 * display. Factory-new, no history, and therefore nothing to know about it that is not
 * already written down. It also has no face, for the same reason the genset does not.
 */
export const BatteryCabinet: React.FC<{
  f: number; x: number; y: number; s?: number; charge?: number; live?: number;
  phase?: number; groundY?: number;
}> = ({f, x, y, s = 1, charge = 0.8, live = 1, phase = 1.7, groundY = 250}) => {
  const T = tones(ID.bone);
  const v = vitals(f, phase, 0.25);
  return (
    <g transform={`translate(${x + v.swayX * 0.25} ${y + v.bob * 0.2}) scale(${s})`}>
      <defs><FormGradient id="bcf" t={T} softness={1.2} /></defs>
      <ContactShadow cx={0} cy={groundY} rx={210} ry={22} opacity={0.3} />
      <rect x={-190} y={-300} width={380} height={550} rx={6} fill="url(#bcf)" stroke={INK} strokeWidth={4.5} />
      <RimLight d="M -182 -300 H 182" w={4} opacity={0.6} />
      {/* exact panel lines */}
      {[-160, -20, 120].map((yy, i) => (
        <path key={i} d={`M -190 ${yy} H 190`} stroke={INK} strokeWidth={2.5} opacity={0.45} />
      ))}
      {[[-1, -1], [1, -1], [-1, 1], [1, 1]].map(([sx, sy], i) => (
        <circle key={i} cx={sx * 164} cy={-300 + (sy > 0 ? 524 : 26)} r={8}
                fill="#B9BFC0" stroke={INK} strokeWidth={2.5} />
      ))}
      {/* flush display, the only lit thing on it */}
      <rect x={-120} y={-252} width={240} height={96} rx={4} fill="#20262B" stroke={INK} strokeWidth={3} />
      {Array.from({length: 6}, (_, i) => (
        <rect key={i} x={-104 + i * 36} y={-236} width={26} height={64} rx={2}
              fill={i / 6 < charge ? '#8FA9B4' : '#39424A'}
              opacity={i / 6 < charge ? 0.55 + 0.45 * Math.abs(Math.sin(f / 43 + i)) : 1} />
      ))}
      {/* the inverter bay, where the probe comes from */}
      <rect x={-150} y={30} width={300} height={170} rx={4} fill="#CFCABF" stroke={INK} strokeWidth={3.5} />
      <text x={0} y={128} textAnchor="middle" fontSize={30} fontFamily="JetBrains Mono, monospace"
            fill="#5A6368" letterSpacing={2}>INVERTER</text>
      {live > 0 && (
        <circle cx={132} cy={62} r={9} fill={VIOLET} opacity={0.35 + 0.65 * Math.abs(Math.sin(f / 17))} />
      )}
    </g>
  );
};

/* ------------------------------------------------------------ ProbeResponse
 * THE QUESTION AND THE ANSWER, AS ONE COMPONENT.
 *
 * They are one component on purpose. Drawn as two separate elements a viewer reads two
 * unrelated pulses, and the entire idea is that the ANSWER IS THE DIFFERENCE between what
 * went out and what came back. `p` runs 0..1 out and 1..2 back, so a caller drives one
 * value and the round trip is guaranteed to be a round trip.
 */
export const ProbeResponse: React.FC<{
  f: number; x1: number; x2: number; y: number; p: number; amp?: number; w?: number;
}> = ({f, x1, x2, y, p, amp = 26, w = 6}) => {
  if (p <= 0) return null;
  const out = Math.min(1, p);
  const back = Math.max(0, p - 1);
  const seg = (a: number, b: number, wob: number, op: number) => {
    const n = 46;
    const pts = Array.from({length: n}, (_, i) => {
      const t = i / (n - 1);
      const xx = a + (b - a) * t;
      const yy = y + Math.sin(t * 15 + f / 4.1) * amp * wob * Math.sin(Math.PI * t);
      return `${xx.toFixed(1)},${yy.toFixed(1)}`;
    }).join(' L ');
    return <path d={`M ${pts}`} fill="none" stroke={VIOLET} strokeWidth={w} strokeLinecap="round" opacity={op} />;
  };
  return (
    <g>
      {out > 0 && seg(x1, x1 + (x2 - x1) * out, 0.35, 0.95)}
      {back > 0 && (
        <>
          {seg(x2 - (x2 - x1) * back, x2, 1.0, 0.95)}
          <circle cx={x2 - (x2 - x1) * back} cy={y} r={w * 1.6} fill={VIOLET} opacity={0.9} />
        </>
      )}
      {out > 0 && out < 1 && <circle cx={x1 + (x2 - x1) * out} cy={y} r={w * 1.5} fill={VIOLET} opacity={0.9} />}
    </g>
  );
};

/* ----------------------------------------------------------- CoupledRinging
 * Two bodies on a shared line whose corrections overshoot each other, with the amplitude
 * growing on a real spring and then being caught. The shelf had no oscillation primitive
 * and this channel covers grid physics regularly, so it belongs in the library rather
 * than inline in one episode.
 */
export const CoupledRinging: React.FC<{
  f: number; x1: number; x2: number; y: number; grow: number; caught?: number; color?: string;
}> = ({f, x1, x2, y, grow, caught = 0, color = INK}) => {
  const a = grow * 44 * (1 - caught);
  const n = 90;
  const pts = Array.from({length: n}, (_, i) => {
    const t = i / (n - 1);
    const env = Math.sin(Math.PI * t);
    const yy = y + Math.sin(t * 22 - f / 3.2) * a * env;
    return `${(x1 + (x2 - x1) * t).toFixed(1)},${yy.toFixed(1)}`;
  }).join(' L ');
  return (
    <g>
      <path d={`M ${pts}`} fill="none" stroke={color} strokeWidth={7} strokeLinecap="round" />
      {caught > 0.5 && <path d={`M ${x1} ${y} H ${x2}`} fill="none" stroke={color} strokeWidth={7} opacity={caught} />}
    </g>
  );
};

/* --------------------------------------------------------------- Powerhouse
 * The FOURTEENTH biome and the second interior. A small village powerhouse in cold
 * high-key daylight: a back wall of corrugated steel, a hard snow-glare shaft through an
 * open door on the left, a concrete floor with a cable tray running the near foreground.
 * Built against the beige-page trap the same way PaperOfficeBG was, with an ENFORCED value
 * ladder between the three depth planes, because a high-key flat-lit interior is exactly
 * where every plane collapses to one value.
 */
export const PowerhouseBG: React.FC<{f: number; parallax?: number; door?: number}> = ({
  f, parallax = 0, door = 1,
}) => (
  <g>
    <defs>
      <linearGradient id="phwall" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#7E888E" />
        <stop offset="60%" stopColor="#98A2A7" />
        <stop offset="100%" stopColor="#AAB3B7" />
      </linearGradient>
      <linearGradient id="phfloor" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={ID.concrete} />
        <stop offset="100%" stopColor="#8E9698" />
      </linearGradient>
      <linearGradient id="phshaft" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stopColor={ID.glare} stopOpacity={0.55} />
        <stop offset="100%" stopColor={ID.glare} stopOpacity={0} />
      </linearGradient>
    </defs>
    {/* FAR PLANE: corrugated back wall, the darkest value in the room */}
    <rect x={-400} y={-500} width={1900} height={1700} fill="url(#phwall)" data-band="ok" />
    {Array.from({length: 26}, (_, i) => (
      <path key={i} d={`M ${-380 + i * 74 + parallax * 12} -500 V 1200`}
            stroke={INK} strokeWidth={2} opacity={0.13} />
    ))}
    {/* MID PLANE: the floor, one clear value step lighter */}
    <path d="M -400 1180 H 1500 V 2100 H -400 Z" fill="url(#phfloor)" data-band="ok" />
    <path d="M -400 1180 H 1500" stroke={INK} strokeWidth={4} opacity={0.5} />
    {/* the open door and its hard cold shaft, the brightest value */}
    {door > 0 && (
      <g opacity={door}>
        <rect x={-380} y={180} width={300} height={1000} fill={ID.glare} opacity={0.5} />
        <path d="M -80 180 L 700 1180 L 220 1180 L -80 640 Z" fill="url(#phshaft)" />
        {Array.from({length: 22}, (_, i) => {
          const t = (f / 120 + i * 0.045) % 1;
          return (
            <circle key={i} cx={-40 + t * 620 + Math.sin(f / 33 + i) * 14}
                    cy={300 + t * 760 + Math.cos(f / 41 + i * 2) * 20}
                    r={2.4 + Math.abs(ihash(2, i))} fill="#FFFFFF" opacity={0.28} />
          );
        })}
      </g>
    )}
    {/* SET DRESSING. A powerhouse is a WORKED room, and an empty wall is a stretch of film
        where a viewer is given nothing to look at. These are real objects that belong here:
        a breaker panel, conduit runs, a bench with a vise, a coiled cable on a hook. They are
        subjects, not texture, which is the distinction dead_space_check actually measures. */}
    <g>
      {/* breaker panel high on the back wall */}
      <rect x={70} y={300} width={190} height={280} rx={5} fill="#7E888E" stroke={INK} strokeWidth={4} />
      <rect x={86} y={318} width={158} height={244} rx={3} fill="#5F696F" stroke={INK} strokeWidth={2.5} />
      {Array.from({length: 8}, (_, i) => (
        <rect key={i} x={96 + (i % 2) * 76} y={330 + Math.floor(i / 2) * 58} width={62} height={40} rx={2}
              fill="#AEB6BA" stroke={INK} strokeWidth={2} />
      ))}
      {/* conduit runs, bending down the wall */}
      {[0, 1, 2].map((i) => (
        <path key={i} d={`M ${170 + i * 26} 580 V ${760 + i * 40} q 0 40 40 40 H ${900 - i * 30}`}
              fill="none" stroke="#6E787E" strokeWidth={13} strokeLinecap="round" />
      ))}
      {[0, 1, 2].map((i) => (
        <path key={i} d={`M ${170 + i * 26} 580 V ${760 + i * 40} q 0 40 40 40 H ${900 - i * 30}`}
              fill="none" stroke="#8A949A" strokeWidth={7} strokeLinecap="round" />
      ))}
      {/* the bench, with a vise and a tool row */}
      <g>
        <ContactShadow cx={1010} cy={1188} rx={210} ry={16} opacity={0.3} />
        <rect x={800} y={980} width={420} height={40} rx={4} fill="#9A8564" stroke={INK} strokeWidth={4} />
        <rect x={830} y={1020} width={26} height={168} fill="#6E787E" stroke={INK} strokeWidth={3} />
        <rect x={1150} y={1020} width={26} height={168} fill="#6E787E" stroke={INK} strokeWidth={3} />
        <rect x={860} y={922} width={96} height={60} rx={4} fill="#5F696F" stroke={INK} strokeWidth={3.5} />
        <rect x={880} y={900} width={54} height={26} rx={3} fill="#7E888E" stroke={INK} strokeWidth={3} />
        {Array.from({length: 5}, (_, i) => (
          <rect key={i} x={1000 + i * 40} y={{0: 936, 1: 944, 2: 930, 3: 948, 4: 938}[i as 0 | 1 | 2 | 3 | 4]}
                width={12} height={46} rx={3} fill="#8A949A" stroke={INK} strokeWidth={2.5} />
        ))}
      </g>
      {/* coiled cable on a hook */}
      <g transform="translate(700 470)">
        <path d="M 0 -18 v 26" stroke={INK} strokeWidth={5} />
        {[0, 1, 2].map((i) => (
          <ellipse key={i} cx={0} cy={40 + i * 14} rx={52 - i * 4} ry={26}
                   fill="none" stroke="#4A5257" strokeWidth={11} />
        ))}
      </g>
    </g>
    {/* NEAR PLANE: cable tray in the low foreground, below the square crop line */}
    <path d="M -400 1660 H 1500 V 1720 H -400 Z" fill="#6E787E" stroke={INK} strokeWidth={4} />
    {Array.from({length: 16}, (_, i) => (
      <path key={i} d={`M ${-360 + i * 122} 1660 v 60`} stroke={INK} strokeWidth={3} opacity={0.4} />
    ))}
  </g>
);

/* ------------------------------------------------------------- FilingDrawer
 * The running gag, as a component, because a cross-scene continuity requirement
 * re-improvised per scene silently does not happen (the 08-02 AshCrumbs lesson).
 * `open` 0..1 pulls the third drawer, `card` shows the one index card in it, and `shut`
 * closes it again at the payoff, which is the beat where nobody needs it any more.
 */
export const FilingDrawer: React.FC<{
  f: number; x: number; y: number; s?: number; open?: number; card?: number; label?: string;
}> = ({f, x, y, s = 1, open = 0, card = 0, label = 'ACCURATE GENERATOR MODELS'}) => {
  const T = tones('#6C767C');
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <defs><FormGradient id="fdf" t={T} softness={1.0} /></defs>
      <ContactShadow cx={0} cy={330} rx={200} ry={18} opacity={0.28} />
      <rect x={-180} y={-330} width={360} height={660} rx={5} fill="url(#fdf)" stroke={INK} strokeWidth={4} />
      {[0, 1].map((i) => (
        <g key={i}>
          <rect x={-160} y={-300 + i * 200} width={320} height={180} rx={4} fill="#7E888E" stroke={INK} strokeWidth={3} />
          <rect x={-40} y={-230 + i * 200} width={80} height={16} rx={4} fill="#5A6368" stroke={INK} strokeWidth={2} />
          {/* stuffed: paper edges proud of the drawer face */}
          {Array.from({length: 7}, (_, k) => (
            <rect key={k} x={-140 + k * 40} y={-306 + i * 200 + ihash(i, k) * 3} width={30} height={12}
                  fill="#E8E4DA" stroke={INK} strokeWidth={1.5} />
          ))}
        </g>
      ))}
      {/* THE THIRD DRAWER */}
      <g transform={`translate(${open * 210} 0)`}>
        <rect x={-160} y={100} width={320} height={180} rx={4} fill="#8A949A" stroke={INK} strokeWidth={3.5} />
        <rect x={-40} y={170} width={80} height={16} rx={4} fill="#5A6368" stroke={INK} strokeWidth={2} />
        <text x={0} y={140} textAnchor="middle" fontSize={17} fontFamily="JetBrains Mono, monospace"
              fill="#2B2F33" letterSpacing={0.5}>{label}</text>
        {open > 0.35 && (
          <g opacity={Math.min(1, (open - 0.35) * 3)}>
            <rect x={-150} y={118} width={300} height={146} fill="#3A4348" opacity={0.55} />
            {card > 0 && (
              <g transform={`translate(0 ${196 - card * 46})`} opacity={card}>
                <rect x={-96} y={-30} width={192} height={58} rx={3} fill="#F1EDE3" stroke={INK} strokeWidth={2.5} />
                <text x={0} y={6} textAnchor="middle" fontSize={19} fontFamily="JetBrains Mono, monospace" fill="#2B2F33">
                  usually unavailable
                </text>
              </g>
            )}
          </g>
        )}
      </g>
    </g>
  );
};
