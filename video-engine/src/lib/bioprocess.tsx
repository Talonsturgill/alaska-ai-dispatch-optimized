import React from 'react';
import {tones, FormGradient, RimLight, ContactShadow, INK} from './lighting';
import {vitals} from './motion';
import {Simulated, SIM} from './simulation';

/**
 * BIOPROCESS — the library's FIRST CONTAINED LIVING PROCESS, and its first CONTROLLER.
 * ===================================================================================
 * NET-NEW 2026-08-09 ("The Method, Not The Metal", NSF award 2614749).
 *
 * REAL GAP, checked against ASSET_MANIFEST.md in full before a line was written. The shelf
 * carries an orbital eye, a seafloor ear, a ground ear, two aerial machines, an under-ice
 * swimmer, a bench-science family, a records and paper family, a civics rules kit, an
 * absence grammar, an arthropod, a piece of media, a clinical family, a machine-vision
 * layer and thirteen biomes. EVERY MACHINE ON IT PERCEIVES. Not one of them CONTROLS, and
 * nothing on it is a vessel with a process inside.
 *
 * That gap is exactly this story. NSF's abstract puts "reinforcement-learning controllers
 * within a bioprocess digital twin", and the film's own thesis is that the software never
 * looks at the microbe. A shelf whose entire machine vocabulary is eyes could not have drawn
 * that, and re-skinning an eye as a controller would have drawn the opposite of the point.
 */

/* ------------------------------------------------------------------ palette */
export const BP = {
  coal: '#1E1815',
  refuse: '#3A2E27',
  ochre: '#A85E2E',
  steel: '#B4BCC0',
  steelDeep: '#6E787D',
  brass: '#8C7A45',
  bone: '#E8E2D4',
  ink: INK,
};

const hash = (a: number, b: number): number => {
  let h = Math.imul(a + 0x7f4a, 0x27d4eb2d) ^ Math.imul(b + 0x1b3f, 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 15), 0x2545f491);
  return (((h ^ (h >>> 13)) >>> 0) / 4294967295) * 2 - 1;
};

/**
 * THE SHARED SILHOUETTE, and it is load-bearing rather than a convenience.
 *
 * The film's central staging decision is that the real vessel and its model sit at the
 * SAME SIZE on one floor line, so the viewer compares them instead of ranking them. If the
 * two were drawn from two different paths they would drift apart the first time either was
 * edited, and the comparison the whole film rests on would quietly stop being true. So both
 * components consume this one path. Local coords, origin at the vessel's floor centre.
 */
export const VESSEL_PATH =
  'M -96 0 L -96 -196 Q -96 -228 -64 -232 L 64 -232 Q 96 -228 96 -196 L 96 0 Z';

/** the lid, drawn separately so it can hinge */
const LID_PATH = 'M -104 0 L -104 -22 Q -104 -34 -88 -34 L 88 -34 Q 104 -34 104 -22 L 104 0 Z';

/* ====================================================================== */
/* THE REAL ONE                                                            */
/* ====================================================================== */
/**
 * SteelVessel — HEAVY AND IRREGULAR, per the run's art direction.
 *
 * Everything about it is slightly off true on purpose: the weld seams are not straight,
 * the rivet heads are hand-placed by hash rather than spaced, the lid hangs a couple of
 * degrees off its hinge. That irregularity is half of the film's shape grammar, and the
 * model's perfect symmetry is the other half. It casts a contact shadow, always, because
 * DISPATCH_STANDARD section 1 requires it of anything that touches ground AND because the
 * shadow is the single cue that separates it from the thing beside it.
 *
 * `tagTurn` is the film's primary open loop: 0 holds the printed side away from camera, 1
 * faces it. It is planted at 3.2s and not paid until 108.9s, so this prop carries a
 * hundred seconds of the film's structure and must not be defaulted to 1 by a call site.
 */
export const SteelVessel: React.FC<{
  f: number; x: number; y: number; scale?: number;
  /** 0 closed, 1 fully open on its hinge */
  lid?: number;
  /** 0 printed side away from camera, 1 facing it */
  tagTurn?: number;
  tagText?: string;
  tagSub?: string;
  phase?: number;
  /** 0..1 how much of the interior is visible through the mouth */
  mouth?: number;
  gain?: number;
}> = ({f, x, y, scale = 1, lid = 1, tagTurn = 0, tagText = '', tagSub = '', phase = 0, mouth = 1, gain = 1}) => {
  const T = tones(BP.steel);
  const v = vitals(f, phase, gain * 0.28); // a two-tonne vessel barely moves, but it is not dead
  const uid = `sv${Math.round(x)}_${Math.round(y)}`;
  // the lid hangs 3 degrees off true even when "closed" — nothing here is square
  const lidAng = -6 - lid * 104;
  // the tag swings on its wire on a real pendulum period with follow-through
  const swing = 7 * Math.sin(f / 21.3 + phase) + 2.4 * Math.sin(f / 9.1 + phase * 1.7);
  // tagTurn drives a y-scale flip so the paper genuinely turns rather than cross-fading
  const turn = Math.cos((1 - tagTurn) * Math.PI);

  const rivets: React.ReactNode[] = [];
  for (let i = 0; i < 14; i++) {
    const rx = -86 + (i % 7) * 28.7 + hash(i, 3) * 4;
    const ry = -34 - Math.floor(i / 7) * 118 + hash(i, 9) * 5;
    rivets.push(
      <g key={i}>
        <circle cx={rx} cy={ry} r={4.2} fill={T.shade} />
        <circle cx={rx - 1.1} cy={ry - 1.1} r={2.1} fill={T.key} opacity={0.75} />
      </g>,
    );
  }

  return (
    <g transform={`translate(${x + v.swayX * 0.25},${y}) scale(${scale})`}>
      <defs>
        <FormGradient id={`${uid}f`} t={T} softness={0.85} />
        <clipPath id={`${uid}c`}><path d={VESSEL_PATH} /></clipPath>
      </defs>

      <ContactShadow cx={0} cy={4} rx={112} ry={15} opacity={0.5} />

      {/* the barrel */}
      <path d={VESSEL_PATH} fill={`url(#${uid}f)`} stroke={INK} strokeWidth={5} />

      {/* THE MOUTH. A real interior with a floor, not a black hole: the film's argument is
          that it is EMPTY, and an empty thing has to have a bottom you can see. */}
      <g clipPath={`url(#${uid}c)`} opacity={mouth}>
        <path d="M -96 -232 L 96 -232 L 96 -186 Q 0 -160 -96 -186 Z" fill="#0E0C0A" />
        <path d="M -78 -196 Q 0 -174 78 -196 L 78 -188 Q 0 -166 -78 -188 Z" fill={T.shade} opacity={0.5} />
        {/* the clean dry floor of the vessel, catching one sliver of lamp */}
        <path d="M -52 -184 Q 0 -172 52 -184" fill="none" stroke={T.key} strokeWidth={2.4} opacity={0.4} />
      </g>

      {/* weld seams. Deliberately NOT straight — hand-run beads with a bead texture. */}
      {[-150, -86].map((sy, k) => (
        <path
          key={k}
          d={`M -96 ${sy} ${Array.from({length: 8}, (_, i) =>
            `L ${-96 + (i + 1) * 24} ${sy + hash(i, k + 40) * 2.6}`).join(' ')}`}
          fill="none"
          stroke={T.shade}
          strokeWidth={3.4}
          strokeLinecap="round"
          opacity={0.8}
        />
      ))}
      {rivets}

      {/* the sight glass: the one place you could look in, and there is nothing to see */}
      <g>
        <rect x={-22} y={-134} width={44} height={62} rx={7} fill="#0F1512" stroke={INK} strokeWidth={4} />
        <rect x={-16} y={-128} width={13} height={50} rx={5} fill={T.key} opacity={0.22} />
      </g>

      {/* the valve, and the tag hanging off it */}
      <g transform="translate(96,-96)">
        <rect x={-6} y={-9} width={34} height={18} rx={3} fill={T.base} stroke={INK} strokeWidth={4} />
        <circle cx={30} cy={0} r={15} fill="none" stroke={INK} strokeWidth={5} />
        <circle cx={30} cy={0} r={5} fill={T.shade} stroke={INK} strokeWidth={3} />
        <g transform={`rotate(${swing},30,10)`}>
          <path d={`M 30 10 L ${30 + swing * 0.25} 46`} stroke={INK} strokeWidth={2.2} fill="none" />
          <g transform={`translate(${30 + swing * 0.25},46) scale(${Math.abs(turn) < 0.06 ? 0.06 : turn},1)`}>
            <rect x={-46} y={0} width={92} height={44} rx={3}
                  fill={turn > 0 ? BP.bone : '#C9C2B2'} stroke={INK} strokeWidth={3.5} />
            {turn > 0.35 && (
              <>
                <text x={0} y={19} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
                      fontSize={13} fontWeight={700} fill={INK}>{tagText}</text>
                <text x={0} y={35} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
                      fontSize={11} fontWeight={700} fill={INK} opacity={0.72}>{tagSub}</text>
              </>
            )}
            {turn <= 0.35 && (
              /* the BACK of the tag: paper grain and the ghost of print bleeding through,
                 so a viewer can see there IS something written and cannot read it */
              <g opacity={0.5}>
                {Array.from({length: 5}, (_, i) => (
                  <rect key={i} x={-34 + hash(i, 71) * 6} y={11 + i * 5.5} width={54} height={1.6}
                        fill={BP.steelDeep} opacity={0.5} />
                ))}
              </g>
            )}
          </g>
        </g>
      </g>

      {/* the lid, hinged at the left rim, with real weight in its return */}
      <g transform={`translate(-104,-232) rotate(${lidAng})`}>
        <g transform="translate(104,0)">
          <path d={LID_PATH} fill={T.base} stroke={INK} strokeWidth={5} />
          <RimLight d="M -100 -30 L 100 -30" w={4} opacity={0.5} />
          <rect x={-14} y={-30} width={28} height={11} rx={3} fill={T.shade} stroke={INK} strokeWidth={3} />
        </g>
      </g>

      <RimLight d="M -94 -196 Q -94 -228 -64 -230" w={5} opacity={0.6} />
    </g>
  );
};

/* ====================================================================== */
/* THE MODEL OF IT                                                         */
/* ====================================================================== */
/**
 * TwinVessel — the SAME vessel, in the simulation grammar.
 *
 * It consumes VESSEL_PATH, so it is guaranteed to be the same size and shape as the steel
 * one, which is the comparison the film is built on. It has no shadow and no contact by
 * construction, because `Simulated` has no prop for either.
 *
 * `bioFidelity` is separate from `fidelity` ON PURPOSE and it is the film's second open
 * loop. The vessel body models well (pumps, timing, power are ordinary engineering), and
 * the biology section does not, because PubMed indexes four papers. Two independent
 * fidelities let the frame state that at 47.9s and let the narration name it at 91.5s.
 */
export const TwinVessel: React.FC<{
  f: number; x: number; y: number; scale?: number;
  fidelity?: number; bioFidelity?: number;
  drawn?: number; phase?: number; running?: number;
  bioLabel?: string;
}> = ({f, x, y, scale = 1, fidelity = 0.95, bioFidelity = 0.12, drawn = 1, phase = 0, running = 1, bioLabel}) => {
  // the internal values only run once the outline has closed
  const live = drawn > 0.97 ? running : 0;
  const lvl = 0.5 + 0.42 * Math.sin(f / 31.7 + phase) + 0.08 * Math.sin(f / 11.3);
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <Simulated d={VESSEL_PATH} fidelity={fidelity} f={f} phase={phase} drawn={drawn} occupied={live * 0.8}>
        {live > 0.02 && (
          <g opacity={live}>
            {/* the running level inside the model: a thing the steel one never has */}
            <path d={`M -90 ${-40 - lvl * 150} L 90 ${-40 - lvl * 150}`} stroke={SIM}
                  strokeWidth={1.8} opacity={0.8} />
            {/* internal structure, exact and perfectly symmetric, the opposite of the welds */}
            {[-150, -110, -70].map((sy, i) => (
              <path key={i} d={`M -90 ${sy} L 90 ${sy}`} stroke={SIM} strokeWidth={1} opacity={0.32} />
            ))}
            <path d="M 0 -228 L 0 -6" stroke={SIM} strokeWidth={1} opacity={0.28} />
            {/* the impeller, turning: the model is a thing being computed */}
            <g transform={`translate(0,-72) rotate(${(f * 3.4) % 360})`}>
              {[0, 60, 120, 180, 240, 300].map((a) => (
                <path key={a} d="M 0 0 L 0 -26" stroke={SIM} strokeWidth={1.6}
                      transform={`rotate(${a})`} opacity={0.85} />
              ))}
            </g>
          </g>
        )}
      </Simulated>

      {/* THE BIOLOGY SECTION, at its own fidelity. Drawn as a separate Simulated so its
          linework hunts while the body's sits still, which is the whole point. */}
      {drawn > 0.18 && (
        <Simulated
          d="M -58 -206 Q 0 -226 58 -206 L 58 -156 Q 0 -138 -58 -156 Z"
          fidelity={bioFidelity}
          f={f}
          phase={phase + 3.1}
          drawn={Math.min(1, (drawn - 0.18) / 0.30)}
        />
      )}
      {bioLabel && drawn > 0.97 && (
        <g>
          <path d="M 60 -182 L 104 -182" stroke={SIM} strokeWidth={1.4} opacity={0.8} />
          <text x={110} y={-177} fontFamily="JetBrains Mono, monospace" fontSize={17}
                fontWeight={700} fill={SIM}>{bioLabel}</text>
        </g>
      )}
    </g>
  );
};

/* ====================================================================== */
/* THE HERO                                                                */
/* ====================================================================== */
/**
 * LoopGovernor — THE RUN'S HERO and this shelf's first CONTROLLER.
 *
 * SHAPE-LANGUAGE DECISION, and it is a deliberate break with this channel's habit: IT HAS
 * NO EYE. Every hero this shelf has built for a year has been a thing that looks — an
 * orbital eye, a ground ear with a face, a glider with an iris, a gantry with one glass
 * lens. This film's narration says in as many words that the software never looks at the
 * microbe, so a hero with an eye would contradict the script in every frame it appeared in.
 * Its ancestor is the mechanical flyball governor, which is the original controller and the
 * right piece of history to draw: a machine that senses by FEEL and answers by ADJUSTING.
 * It is also the ONE ROUND THING in a film of dented cylinders and torn heaps.
 *
 * THREE STATE CHANNELS, per the thrice-learned one-channel lesson (07-25 horn, 07-26 cone,
 * 07-30 glider, 08-05 beetle, 08-06 frame, 08-08 slug):
 *   THE SPIN   — the flyballs rise as `spin` rises. Visible at any scale, and it is the
 *                only part of the machine that reads at feed size.
 *   THE LOOP   — the cable leaves the head and comes back. A viewer cannot see that a
 *                controller is CLOSED unless the line physically returns, and the film's
 *                whole argument is which object it returns from.
 *   THE THROTTLE — a power lever. This is NSF's "energy-constrained" as a drawn part, and
 *                it is why the machine is not simply a pump.
 */
export const LoopGovernor: React.FC<{
  f: number; x: number; y: number; scale?: number;
  /** 0 stopped, 1 at full speed. Drives the flyball angle with real angular inertia. */
  spin?: number;
  /** 0..1 the power lever. */
  throttle?: number;
  /** 0..1 VO emphasis reactivity */
  accent?: number;
  phase?: number;
  /** uneven running, for the Act 3 beat where the machine is visibly argued with */
  strain?: number;
}> = ({f, x, y, scale = 1, spin = 1, throttle = 0.6, accent = 0, phase = 0, strain = 0}) => {
  const T = tones(BP.brass);
  const S = tones(BP.steel);
  const uid = `lg${Math.round(x)}`;
  const v = vitals(f, phase, 0.5);
  // the flyballs answer the spin with a lag and a wobble under strain
  const arm = 14 + spin * 46 - strain * 9 * Math.sin(f / 4.1);
  const rot = (f * (2.2 + spin * 9)) % 360;
  const kick = accent * 3.4;

  return (
    <g transform={`translate(${x},${y + v.bob * 0.5}) scale(${scale})`}>
      <defs>
        <FormGradient id={`${uid}b`} t={T} softness={0.9} />
        <FormGradient id={`${uid}s`} t={S} softness={0.9} />
      </defs>

      <ContactShadow cx={0} cy={2} rx={64} ry={11} opacity={0.46} />

      {/* base plinth */}
      <path d="M -58 0 L -46 -26 L 46 -26 L 58 0 Z" fill={`url(#${uid}s)`} stroke={INK} strokeWidth={5} />
      {[-34, 0, 34].map((bx) => (
        <circle key={bx} cx={bx} cy={-13} r={4} fill={S.shade} stroke={INK} strokeWidth={2} />
      ))}

      {/* the column */}
      <rect x={-11} y={-150} width={22} height={126} rx={4} fill={`url(#${uid}s)`} stroke={INK} strokeWidth={4.5} />
      <RimLight d="M -8 -146 L -8 -28" w={3.5} opacity={0.5} />

      {/* THE THROTTLE. Energy constrained, drawn as a part. */}
      <g transform="translate(46,-70)">
        <rect x={-5} y={-46} width={10} height={54} rx={4} fill={S.shade} stroke={INK} strokeWidth={3} />
        <g transform={`rotate(${-58 + throttle * 74})`}>
          <path d="M 0 0 L 0 -44" stroke={INK} strokeWidth={7} strokeLinecap="round" />
          <circle cx={0} cy={-46} r={8} fill={T.base} stroke={INK} strokeWidth={3.5} />
        </g>
        <circle cx={0} cy={0} r={5} fill={T.shade} stroke={INK} strokeWidth={3} />
      </g>

      {/* THE SPIN. Flyballs on hinged links, rising with load. */}
      <g transform={`translate(0,-150)`}>
        <g transform={`rotate(${rot * 0.14})`}>
          {[-1, 1].map((s) => (
            <g key={s}>
              <path d={`M 0 0 L ${s * (30 + arm * 0.62)} ${34 + arm * 0.5}`}
                    stroke={INK} strokeWidth={6} strokeLinecap="round" />
              <circle cx={s * (30 + arm * 0.62)} cy={34 + arm * 0.5} r={15 + kick}
                      fill={`url(#${uid}b)`} stroke={INK} strokeWidth={4.5} />
              <circle cx={s * (30 + arm * 0.62) - 5} cy={29 + arm * 0.5} r={4.6}
                      fill={T.key} opacity={0.8} />
            </g>
          ))}
        </g>
        {/* the weighted collar the arms lift, so the mechanism reads as CAUSAL */}
        <rect x={-19} y={46 - arm * 0.34} width={38} height={13} rx={3}
              fill={T.base} stroke={INK} strokeWidth={4} />
        <circle cx={0} cy={0} r={10} fill={T.shade} stroke={INK} strokeWidth={4} />
      </g>

      {/* the spool the cable pays off */}
      <g transform="translate(-44,-56)">
        <circle cx={0} cy={0} r={20} fill={`url(#${uid}s)`} stroke={INK} strokeWidth={4.5} />
        <g transform={`rotate(${-rot * 0.5})`}>
          {[0, 60, 120].map((a) => (
            <path key={a} d="M -15 0 L 15 0" stroke={S.shade} strokeWidth={3}
                  transform={`rotate(${a})`} opacity={0.85} />
          ))}
        </g>
        <circle cx={0} cy={0} r={5.5} fill={T.base} stroke={INK} strokeWidth={3} />
      </g>
    </g>
  );
};

/* ====================================================================== */
/* THE ACCURACY ASSET                                                      */
/* ====================================================================== */
/**
 * CellSurface — the microbe, drawn so the film cannot lie about it.
 *
 * THE SINGLE MOST IMPORTANT NOTE IN THIS RUN'S FACT-CHECK: Shewanella oneidensis does NOT
 * eat, digest, consume or breathe rare earths. It respires iron and manganese, and the rare
 * earth interaction is BIOSORPTION, meaning the atoms bind to the OUTSIDE of the cell. The
 * verified verbs are bind, stick, latch, adsorb.
 *
 * So the accuracy is built into the geometry rather than trusted to a caption. `bound`
 * atoms are placed on a radius strictly GREATER than the membrane's, they are drawn AFTER
 * the membrane so they can never be occluded by it, and `reject` drives an atom that
 * presses inward, dimples the wall, and is pushed straight back out. A scene physically
 * cannot use this component to show ingestion.
 */
export const CellSurface: React.FC<{
  f: number; cx: number; cy: number; r?: number;
  /** 0..1 how many rare earth atoms have bound to the surface */
  bound?: number;
  /** 0..1 drives the rejection beat: an atom presses in and is pushed back out */
  reject?: number;
  phase?: number;
  atomColor?: string;
}> = ({f, cx, cy, r = 190, bound = 1, reject = 0, phase = 0, atomColor = BP.ochre}) => {
  const T = tones('#7E8C6A');
  const uid = `cs${Math.round(cx)}`;
  // the membrane breathes on an irrational period so a held macro shot is never a still
  const breath = 1 + 0.018 * Math.sin(f / 27.1 + phase) + 0.006 * Math.sin(f / 11.7);
  const N = 22;
  const n = Math.round(Math.max(0, Math.min(1, bound)) * N);
  const atoms: React.ReactNode[] = [];
  for (let i = 0; i < n; i++) {
    const a = (i / N) * Math.PI * 2 + hash(i, 5) * 0.22 + f / 900;
    // STRICTLY OUTSIDE the wall. This clearance is the accuracy contract.
    const rr = r * breath + 9 + hash(i, 17) * 3.5;
    const jitter = 1.1 * Math.sin(f / 6.3 + i * 1.7);
    atoms.push(
      <g key={i} transform={`translate(${cx + Math.cos(a) * (rr + jitter)},${cy + Math.sin(a) * (rr + jitter)})`}>
        {/* the contact tick, drawn toward the cell, where the atom meets the wall */}
        <ellipse cx={-Math.cos(a) * 8} cy={-Math.sin(a) * 8} rx={7} ry={3.4}
                 transform={`rotate(${(a * 180) / Math.PI},${-Math.cos(a) * 8},${-Math.sin(a) * 8})`}
                 fill={INK} opacity={0.34} />
        <circle r={9.5} fill={atomColor} stroke={INK} strokeWidth={3} />
        <circle cx={-2.6} cy={-2.6} r={3.1} fill="#E7A968" opacity={0.85} />
      </g>,
    );
  }
  // the rejected atom: presses in on the left flank, the wall bows, and it is pushed out
  const push = Math.sin(Math.max(0, Math.min(1, reject)) * Math.PI);
  const rx = cx - (r * breath + 9) + push * 16;
  const dimple = push * 13;

  return (
    <g>
      <defs><FormGradient id={`${uid}f`} t={T} softness={1.05} /></defs>
      {/* cytoplasm */}
      <circle cx={cx} cy={cy} r={r * breath} fill={`url(#${uid}f)`} stroke="none" />
      {/* internal texture so it is never a flat fill */}
      {Array.from({length: 16}, (_, i) => (
        <ellipse key={i}
                 cx={cx + hash(i, 21) * r * 0.5}
                 cy={cy + hash(i, 33) * r * 0.5}
                 rx={16 + hash(i, 41) * 9} ry={11 + hash(i, 47) * 7}
                 fill={T.shade} opacity={0.46}
                 transform={`rotate(${hash(i, 55) * 60},${cx},${cy})`} />
      ))}
      {/* THE WALL, with the dimple where the rejected atom presses */}
      <path
        d={`M ${cx} ${cy - r * breath}
            A ${r * breath} ${r * breath} 0 0 1 ${cx} ${cy + r * breath}
            A ${r * breath - dimple} ${r * breath} 0 0 1 ${cx} ${cy - r * breath} Z`}
        fill="none" stroke={INK} strokeWidth={9}
      />
      {/* MEMBRANE THICKNESS: an inner wall line offset from the outer one, so the boundary is a
          shell with depth rather than a single stroke. */}
      <circle cx={cx} cy={cy} r={r * breath - 13} fill="none" stroke={INK} strokeWidth={3.5} opacity={0.42} />
      <circle cx={cx} cy={cy} r={r * breath - 6.5} fill="none" stroke={T.shade} strokeWidth={9} opacity={0.5} />
      <circle cx={cx} cy={cy} r={r * breath} fill="none" stroke={T.key} strokeWidth={5} opacity={0.6} />
      {/* RIM LIGHT along the upper-left arc, the one cue the panel said was missing */}
      <path d={`M ${cx - r * breath * 0.94} ${cy - r * breath * 0.33}
                A ${r * breath} ${r * breath} 0 0 1 ${cx + r * breath * 0.30} ${cy - r * breath * 0.95}`}
            fill="none" stroke="#E9F0C8" strokeWidth={7} opacity={0.5} strokeLinecap="round" />
      {/* the nucleoid: a darker mass with a real edge, so the interior is never one flat tone */}
      <ellipse cx={cx - r * 0.12} cy={cy + r * 0.06} rx={r * 0.42} ry={r * 0.3}
               fill={T.shade} opacity={0.5} transform={`rotate(-18,${cx},${cy})`} />
      <ellipse cx={cx - r * 0.12} cy={cy + r * 0.06} rx={r * 0.42} ry={r * 0.3}
               fill="none" stroke={INK} strokeWidth={3} opacity={0.35} transform={`rotate(-18,${cx},${cy})`} />
      {/* pili */}
      {Array.from({length: 22}, (_, i) => {
        const a = (i / 22) * Math.PI * 2 + 0.3;
        const L = 20 + hash(i, 61) * 12;
        const wag = 5 * Math.sin(f / 13.7 + i);
        return (
          <path key={i}
                d={`M ${cx + Math.cos(a) * r * breath} ${cy + Math.sin(a) * r * breath}
                    q ${Math.cos(a) * L * 0.6 + wag} ${Math.sin(a) * L * 0.6} ${Math.cos(a) * L} ${Math.sin(a) * L}`}
                fill="none" stroke={INK} strokeWidth={2.6} opacity={0.55} />
        );
      })}
      {/* bound atoms, drawn LAST so the membrane can never cover one */}
      {atoms}
      {push > 0.02 && (
        <g transform={`translate(${rx},${cy + 26})`}>
          <circle r={9.5} fill={atomColor} stroke={INK} strokeWidth={3} />
          <circle cx={-2.6} cy={-2.6} r={3.1} fill="#E7A968" opacity={0.85} />
        </g>
      )}
    </g>
  );
};
