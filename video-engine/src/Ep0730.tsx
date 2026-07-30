import React from 'react';
import {z} from 'zod';
import {AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {IceGlider, UnderIceBG, AcousticSource, RingedSealGhost} from './lib/underice';
import {Beluga} from './lib/fauna';
import {StatCard, Nameplate} from './lib/props';
import {NightGrade, tones, FormGradient, RimLight, ContactShadow} from './lib/lighting';
import {entrance, vitals} from './lib/motion';

// =============================================================================
// DISPATCH 2026-07-30 — "We know where the machine is"
//
// Storyboard: out/dispatch/storyboard.json   Art direction: out/dispatch/art_direction.json
// Source: 91 FR 46055 (NOAA Fisheries proposed IHA, ONR Arctic Research Activities Year 9)
//
// THE BINDING PALETTE RULE (art_direction.json): CYAN IS SOUND AND ONLY SOUND. No
// surface anywhere in this film is cyan. Every cyan pixel is something being heard,
// emitted, or measured, so a viewer learns the colour's meaning in the first ten
// seconds and the turn can then use its ABSENCE. The one warm object is the machine.
// Every glow is a REGISTERED NightGrade source, so light cannot appear where nothing
// emits.
// =============================================================================

const INK = '#081018';
const ABYSS = '#081a2e';
const ICE = '#cfe6f2';
const HULL = '#f2b33d';
const CYAN = '#4fe3ff';
const LEAD_WARM = '#ffe9b8';
const BOLD = 'Fraunces, Georgia, serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

/** the 4:5 LinkedIn crop is the deliverable — every load-bearing element lives inside this box */
const SAFE_TOP = 285;
const SAFE_BOT = 1635;

// NOTE THE `grade` SLOT, added 2026-07-30 after code review. NightGrade emits HTML <div>
// elements, and a <div> created inside an <svg> is placed in the SVG namespace where it
// paints NOTHING. Every scene below originally rendered <NightGrade> as an svg child, so the
// entire night grade (ambient cast, crushed black floor, registered source bloom) was a
// silent no-op in the shipped film. UnderIceLook.tsx had it right, outside the svg, which is
// why look-dev looked graded and the episode did not. The slot makes the correct placement
// the only placement a scene can use.
const Stage: React.FC<{children: React.ReactNode; grade?: React.ReactNode}> = ({children, grade}) => (
  <AbsoluteFill style={{backgroundColor: ABYSS}}>
    <svg viewBox="0 0 1080 1920" width="1080" height="1920">{children}</svg>
    {grade}
  </AbsoluteFill>
);

/** A hard boxed label in the house register. Ink plate, mono type, contact shadow. */
const Plate: React.FC<{x: number; y: number; text: string; sub?: string; op?: number; w?: number; accent?: string}> = ({
  x, y, text, sub, op = 1, w = 640, accent = ICE,
}) => {
  const h = sub ? 128 : 84;
  return (
    <g transform={`translate(${x},${y})`} opacity={op}>
      <ContactShadow cx={0} cy={h / 2 + 12} rx={w / 2 * 0.9} ry={13} opacity={0.34} />
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={10} fill="#0e1d2c" stroke={accent} strokeWidth={5} />
      <rect x={-w / 2 + 5} y={-h / 2 + 5} width={w - 10} height={h * 0.3} rx={7} fill="#ffffff" opacity={0.05} />
      <text x={0} y={sub ? -6 : 14} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={sub ? 40 : 38}
        fill={accent} letterSpacing={1.4}>{text}</text>
      {sub && (
        <text x={0} y={40} textAnchor="middle" fontFamily={MONO} fontWeight={500} fontSize={24}
          fill="#9dc2d6" letterSpacing={1}>{sub}</text>
      )}
    </g>
  );
};

/* ---------------------------------------------------------------------------
   S1 — THE LID. Extreme wide, high, crane down. VO lines 1 to 2.
   Frame 0 must be dead-legible for the poster grade: the dying signal cone plus
   NO SIGNAL. Beats 1 to 4.
--------------------------------------------------------------------------- */
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const iceY = 470;

  // the cone descends and FLATTENS on the ice (beat 1). Compressed by frame 12.
  const hit = interpolate(f, [0, 12], [0, 1], {extrapolateRight: 'clamp'});
  const coneLen = interpolate(hit, [0, 1], [110, 22], {extrapolateRight: 'clamp'});
  const flat = interpolate(f, [10, 20], [0, 1], {extrapolateRight: 'clamp'});

  // the glider revealed far below (beat 2, t=2.4s -> f=72)
  // Gate 0B: the machine must be IN frame 0, not withheld to 2.4s. It is present from
  // the first frame as a rim-lit speck and only GROWS on its beat.
  const gl = entrance(f, fps, 4, {drop: 40});
  // the eye goes wide and searches (beat 3, t=3.9 -> f=117)
  const searching = f > 110;
  // the failed position marker (beat 4, t=6.8 -> f=204)
  const mk = interpolate(f, [204, 216, 240, 252], [0, 1, 1, 0], {extrapolateRight: 'clamp'});
  const mkJit = Math.sin(f / 2.2) * 3 * (mk > 0.4 ? 1 : 0);

  return (
    <Stage grade={<NightGrade f={f} color="#0f3a52" amount={0.34} floor={0.2} horizon={0.12} sources={[{x: 540, y: iceY - 60, r: 300, color: LEAD_WARM, intensity: 0.45}, {x: 430, y: 1180, r: 90, color: CYAN, intensity: 0.3}]} />}>
      <UnderIceBG f={f} iceY={iceY} lead={0.55} parallax={interpolate(f, [0, 300], [0, 0.5])} />

      {/* the satellite and its dying cone, ABOVE the ice */}
      <g opacity={1 - flat * 0.25}>
        <g transform={`translate(540,${SAFE_TOP + 60})`}>
          <rect x={-46} y={-26} width={92} height={52} rx={9} fill="#8b98a6" stroke={INK} strokeWidth={6} />
          <rect x={-70} y={-12} width={22} height={24} rx={4} fill="#3f5c88" stroke={INK} strokeWidth={4} />
          <rect x={48} y={-12} width={22} height={24} rx={4} fill="#3f5c88" stroke={INK} strokeWidth={4} />
        </g>
        {coneLen > 2 && (
          <path d={`M516,${SAFE_TOP + 92} L${540 - 120},${SAFE_TOP + 92 + coneLen} L${540 + 120},${SAFE_TOP + 92 + coneLen} L564,${SAFE_TOP + 92} Z`}
            fill={CYAN} opacity={0.16} />
        )}
        {/* the cone SPLATS flat against the ice underside */}
        {flat > 0.02 && (
          <ellipse cx={540} cy={iceY - 96} rx={150 * flat} ry={9 * flat} fill={CYAN} opacity={0.3 * (1 - flat * 0.5)} />
        )}
      </g>

      <g opacity={interpolate(f, [8, 22], [0, 1], {extrapolateRight: 'clamp'})}>
        {/* offset right: centred at 540 this plate painted over the satellite body
            (x 470-610), hiding the emitter of the dying cone for most of S1 */}
        <Plate x={815} y={SAFE_TOP + 40} text="NO SIGNAL" w={390} accent={CYAN} />
      </g>

      {/* the machine, small in a big dark world */}
      <g opacity={Math.max(0.55, gl.on ? Math.min(1, gl.scale) : 0)} transform={`translate(0,${gl.dy})`}>
        <IceGlider x={430} y={1180} f={f} scale={interpolate(f, [0, 40], [0.34, 0.5], {extrapolateRight: 'clamp'})} emotion={searching ? 'lost' : 'gliding'} />
      </g>

      {/* the failed fix */}
      {mk > 0.02 && (
        <g opacity={mk} transform={`translate(${560 + mkJit},1090)`}>
          <rect x={-54} y={-54} width={108} height={108} rx={8} fill="none" stroke={CYAN} strokeWidth={5}
            strokeDasharray="14 12" />
          <text x={0} y={16} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={62} fill={CYAN}>?</text>
        </g>
      )}

      <g opacity={interpolate(f, [50, 70], [0, 1], {extrapolateRight: 'clamp'})}>
        <Plate x={540} y={SAFE_BOT - 60} text="BEAUFORT SEA" sub="POSITION UNKNOWN" w={560} />
      </g>

    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S2 — THE FIELD SWITCHES ON. Medium, eye, dolly through. VO lines 3 to 4.
   Beats 5 to 8: the nameplate, the first ring, six moorings plant, all six pulse.
--------------------------------------------------------------------------- */
const S2: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const iceY = 300;
  const floorY = 1520;

  const np = entrance(f, fps, 6, {drop: 40});
  // the first ring rises (beat 6, local t~3.4s -> f~102)
  const ring1 = interpolate(f, [86, 140], [0, 1], {extrapolateRight: 'clamp'});
  // six moorings plant in sequence (beat 7, local ~6.0s -> f=180)
  const xs = [150, 310, 460, 620, 780, 940];
  // all six pulse (beat 8, local ~8.8s -> f=264)
  const allOn = f > 92;

  return (
    <Stage grade={<NightGrade f={f} color="#0f3a52" amount={0.3} floor={0.18} horizon={0.1} sources={[{x: 540, y: iceY - 40, r: 260, color: LEAD_WARM, intensity: 0.3}, ...(allOn ? xs.map((x) => ({x, y: floorY - 44, r: 120, color: CYAN, intensity: 0.34})) : [])]} />}>
      <UnderIceBG f={f} iceY={iceY} lead={0.3} parallax={interpolate(f, [0, 320], [0.1, 0.6])} />

      {/* the first ring, travelling up out of the black before anything is explained */}
      {ring1 > 0.02 && ring1 < 1 && (
        <circle cx={540} cy={floorY - 40} r={40 + 420 * ring1} fill="none" stroke={CYAN}
          strokeWidth={9 - 5 * ring1} opacity={(1 - ring1) * 0.9} />
      )}

      {xs.map((x, i) => {
        const t0 = 2 + i * 9;
        const e = entrance(f, fps, t0, {drop: -150});
        const pulse = allOn ? 0.9 : 0;
        return (
          <g key={i} opacity={e.on ? Math.min(1, e.scale) : 0} transform={`translate(0,${e.dy})`}>
            <AcousticSource x={x} y={floorY} f={f + i * 37} scale={0.72} pulse={pulse}
              floorY={floorY - iceY - 30} />
          </g>
        );
      })}

      <g opacity={np.on ? Math.min(1, np.scale) : 0} transform={`translate(0,${np.dy})`}>
        <Plate x={540} y={SAFE_TOP + 30} text="U.S. NAVY" sub="OFFICE OF NAVAL RESEARCH" w={700} />
      </g>

      <g opacity={interpolate(f, [96, 124], [0, 1], {extrapolateRight: 'clamp'})}>
        <StatCard x={540} y={SAFE_BOT - 300} big="6 SOURCES - 900 Hz" sub="IN PLACE 1 YEAR" scale={0.92} color="#1d4b66" />
      </g>

    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S3 — THE SOLVE. Close, low, static (the geometry must be read, not travelled).
   VO lines 5 to 6. Beats 9 to 11, and beat 10 is THE SIGNATURE SHOT.
--------------------------------------------------------------------------- */
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const cx = 540;
  const cy = 960;

  // three arcs arrive (beat 9). Each from a different bearing.
  const bearings = [{a: 205, t0: 4}, {a: 320, t0: 16}, {a: 95, t0: 28}];
  // THE CLAMP (beat 10, local t~3.3s -> f~99)
  const lock = spring({frame: f - 96, fps, config: {damping: 11, stiffness: 150}});
  const locked = f > 96;
  // the bare geometry draws on (beat 11, local ~5.6s -> f=168)
  const geo = interpolate(f, [6, 54], [0, 1], {extrapolateRight: 'clamp'});
  const discl = interpolate(f, [150, 180], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <Stage grade={<NightGrade f={f} color="#0f3a52" amount={0.36} floor={0.24} horizon={0.08} sources={[{x: cx - 66, y: cy, r: locked ? 170 : 110, color: CYAN, intensity: locked ? 0.5 : 0.28}]} />}>
      <UnderIceBG f={f} iceY={180} lead={0.18} parallax={0.7} motes />

      {/* THREE RANGE LINES that visibly TERMINATE on the machine, each from its own
          off-frame source marker. Pass 1 drew huge thin range circles and they read as
          stray outlines instead of three distances converging on one point. */}
      {geo > 0.02 && bearings.map((b, i) => {
        const rad = (b.a * Math.PI) / 180;
        const sx = cx + Math.cos(rad) * 470;
        const sy = cy + Math.sin(rad) * 470;
        const ex = cx + Math.cos(rad) * 96;
        const ey = cy + Math.sin(rad) * 96;
        return (
          <g key={i} opacity={geo}>
            <line x1={sx} y1={sy} x2={ex} y2={ey} stroke={CYAN} strokeWidth={3.5}
              strokeDasharray="12 9" opacity={0.75} />
            <circle cx={sx} cy={sy} r={16} fill="#0e1d2c" stroke={CYAN} strokeWidth={5} />
            <circle cx={sx} cy={sy} r={6} fill={CYAN} />
            <text x={sx} y={sy - 30} textAnchor="middle" fontFamily={MONO} fontWeight={700}
              fontSize={24} fill={CYAN}>900 Hz</text>
          </g>
        );
      })}

      {/* the arcs arriving from three bearings */}
      {bearings.map((b, i) => {
        const on = interpolate(f, [b.t0, b.t0 + 34], [0, 1], {extrapolateRight: 'clamp'});
        const rad = (b.a * Math.PI) / 180;
        const d = interpolate(on, [0, 1], [560, 120], {extrapolateRight: 'clamp'});
        return (
          <g key={i} opacity={on * (locked ? 0.55 : 1)}>
            {[0, 1, 2].map((k) => {
              const ph = ((f / 8) + k * 0.33) % 1;
              const rr = d + ph * 60;
              return (
                <path key={k}
                  d={`M${cx + Math.cos(rad) * rr - 44},${cy + Math.sin(rad) * rr} Q${cx + Math.cos(rad) * (rr - 34)},${cy + Math.sin(rad) * rr} ${cx + Math.cos(rad) * rr + 44},${cy + Math.sin(rad) * rr}`}
                  fill="none" stroke={CYAN} strokeWidth={4} opacity={(1 - ph) * 0.8} strokeLinecap="round" />
              );
            })}
          </g>
        );
      })}

      <IceGlider x={cx} y={cy} f={f} scale={1.12} emotion={locked ? 'fixed' : 'listening'}
        eyeLock={lock} ping={locked ? 0.25 : 0.95} pingFrom={205} gain={locked ? 0.25 : 1} />

      {/* the solved position pin */}
      {locked && (
        <g opacity={Math.min(1, lock * 1.4)}>
          <circle cx={cx - 66} cy={cy} r={10 + 26 * (1 - Math.min(1, lock))} fill="none" stroke={CYAN} strokeWidth={5} />
          <circle cx={cx - 66} cy={cy} r={5} fill={CYAN} />
        </g>
      )}

      <g opacity={interpolate(f, [100, 122], [0, 1], {extrapolateRight: 'clamp'})}>
        <Plate x={540} y={SAFE_TOP + 30} text="POSITION SOLVED" w={560} accent={CYAN} />
      </g>
      <g opacity={discl}>
        <Plate x={540} y={SAFE_BOT - 70} text="NOT MACHINE LEARNING" sub="AUTONOMY AND ACOUSTIC ENGINEERING" w={860} />
      </g>

    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S4 — THE ANIMAL ENTERS. Wide, overhead-ish, truck across. VO lines 7 to 8.
   Beats 12 to 14. Beat 12 is THE REHOOK. The beluga is an UNFILLED OUTLINE, so
   the absence of data is drawn as the absence of fill.
--------------------------------------------------------------------------- */
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const iceY = 340;

  // the ghost crosses at its OWN slower speed (the art-direction ghost-drift move)
  const cross = interpolate(f, [0, 300], [1180, -180], {extrapolateLeft: 'clamp'});
  // the filing rises and the stamp thuds (beat 13, local ~4.5s -> f=135)
  const doc = entrance(f, fps, 132, {drop: 170});
  const stamp = spring({frame: f - 168, fps, config: {damping: 8, stiffness: 190}});
  // the NOAA plate sets (beat 14, local ~8.3s -> f=249)
  const plate = entrance(f, fps, 246, {drop: 90});

  return (
    <Stage grade={<NightGrade f={f} color="#0f3a52" amount={0.32} floor={0.2} horizon={0.1} sources={[{x: 200, y: 1420, r: 200, color: CYAN, intensity: 0.22}, {x: 540, y: iceY - 40, r: 240, color: LEAD_WARM, intensity: 0.26}]} />}>
      <UnderIceBG f={f} iceY={iceY} lead={0.22} parallax={interpolate(f, [0, 300], [0.2, 0.7])} />

      {/* the sound field the animal is swimming through, dimmed under the music duck */}
      {[0, 1, 2].map((i) => {
        const ph = ((f / 26) + i * 0.33) % 1;
        return <circle key={i} cx={200} cy={1420} r={80 + 820 * ph} fill="none" stroke={CYAN}
          strokeWidth={4 - 2 * ph} opacity={(1 - ph) * 0.22} />;
      })}

      {/* THE GHOST: an unfilled outline. Beluga is drawn, then masked to stroke-only. */}
      <g transform={`translate(${cross - 540},0)`} opacity={0.85}>
        <g style={{filter: 'grayscale(1) brightness(3.6) contrast(0.18)'}} opacity={0.9}>
          <Beluga x={540} y={880} f={f} scale={1.25} mode="cruise" swim={0.55} />
        </g>
        {/* the contour that makes the ghost legible AS a ghost */}
        <ellipse cx={540} cy={888} rx={232} ry={78} fill="none" stroke="#bfe4f5" strokeWidth={6}
          strokeDasharray="18 13" opacity={0.95} />
      </g>

      {/* the filing */}
      <g opacity={doc.on ? Math.min(1, doc.scale) : 0} transform={`translate(0,${doc.dy})`}>
        <g transform="translate(540,1290)">
          <ContactShadow cx={0} cy={190} rx={250} ry={22} opacity={0.4} />
          <rect x={-230} y={-180} width={460} height={370} rx={8} fill="#e8e2d2" stroke={INK} strokeWidth={6} />
          {Array.from({length: 9}).map((_, i) => (
            <rect key={i} x={-190} y={-140 + i * 34} width={i % 3 === 2 ? 240 : 380} height={9} rx={4}
              fill="#8f9aa3" opacity={0.7} />
          ))}
          <text x={0} y={162} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={30}
            fill="#33424f">91 FR 46055</text>
          {stamp > 0.02 && (
            <g transform={`rotate(-9) scale(${interpolate(stamp, [0, 1], [1.7, 1], {extrapolateRight: 'clamp'})})`}
              opacity={Math.min(1, stamp * 1.6)}>
              <rect x={-160} y={-52} width={320} height={104} rx={8} fill="none" stroke="#c0392b" strokeWidth={9} />
              <text x={0} y={6} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={50}
                fill="#c0392b" letterSpacing={3}>PROPOSED</text>
              <text x={0} y={42} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={26}
                fill="#c0392b" letterSpacing={2}>NOAA FISHERIES - NOT FINAL</text>
            </g>
          )}
        </g>
      </g>

      {/* Gate 0B killed the second institutional plate here: two stacked rectangles are not a
          visible state change. The NOAA mark and NOT FINAL now ride the stamp itself, and the
          recovered air goes to a real world event, the rings sweeping THROUGH the ghost. */}
      <g opacity={plate.on ? Math.min(1, plate.scale) : 0}>
        <Plate x={540} y={SAFE_BOT - 70} text="FILED JULY 22" sub="91 FR 46055" w={620} />
      </g>
      <g opacity={interpolate(f, [16, 40], [0, 1], {extrapolateRight: 'clamp'})}>
        <Plate x={540} y={SAFE_TOP + 24} text="BELUGA" sub="BEAUFORT SEA AND EASTERN CHUKCHI STOCKS" w={860} />
      </g>

    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S5 — THE FINDING, READ EVEN-HANDEDLY. Medium, eye, static. VO line 9.
   Beats 15 to 16. The fair counter-point gets its own held beat and real air.
--------------------------------------------------------------------------- */
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const card = entrance(f, fps, 4, {drop: 50});
  // the compliance tick draws itself and HOLDS (beat 16, local ~4.0s -> f=120)
  const tick = interpolate(f, [120, 152], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <Stage grade={<NightGrade f={f} color="#0f3a52" amount={0.3} floor={0.18} horizon={0.1} sources={[{x: 540, y: 1010, r: 220, color: '#7fd4ff', intensity: 0.2}]} />}>
      <UnderIceBG f={f} iceY={260} lead={0.2} parallax={0.5} motes={false} />

      {/* the ghost animals held still, named by the card rather than acted upon */}
      <g style={{filter: 'grayscale(1) brightness(3.6) contrast(0.18)'}} opacity={0.85}>
        <Beluga x={330} y={720} f={f} scale={0.9} mode="cruise" swim={0.2} />
      </g>
      <ellipse cx={330} cy={726} rx={168} ry={58} fill="none" stroke="#bfe4f5" strokeWidth={5}
        strokeDasharray="15 11" opacity={0.9} />

      <g opacity={card.on ? Math.min(1, card.scale) : 0} transform={`translate(0,${card.dy})`}>
        <StatCard x={540} y={1010} big="LEVEL B" sub="HARASSMENT ONLY - DISTURBANCE, NOT INJURY" scale={1.05} color="#1d4b66" />
      </g>

      <g opacity={interpolate(f, [40, 66], [0, 1], {extrapolateRight: 'clamp'})}>
        <Plate x={540} y={1190} text="NO SERIOUS INJURY OR MORTALITY EXPECTED" w={940} />
      </g>

      {/* THE FAIR COUNTER-POINT, given its own held frame */}
      {tick > 0.02 && (
        <g transform="translate(540,1400)">
          <circle cx={-250} cy={0} r={44} fill="none" stroke="#5fd39a" strokeWidth={7} opacity={tick} />
          <path d="M-274,2 L-256,22 L-224,-20" fill="none" stroke="#5fd39a" strokeWidth={10}
            strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray={110} strokeDashoffset={110 * (1 - tick)} />
          <text x={-170} y={-6} fontFamily={MONO} fontWeight={700} fontSize={34} fill="#cfe9f5" opacity={tick}>PRIOR YEARS</text>
          <text x={-170} y={32} fontFamily={MONO} fontWeight={500} fontSize={27} fill="#9dc2d6" opacity={tick}>ALL REQUIREMENTS MET</text>
        </g>
      )}

    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S6 — THE TURN. Insert to wide via a real PULLBACK. VO lines 10 to 12.
   Beats 17 to 20. The scale-class reveal: 34 empty years discovered by widening.
--------------------------------------------------------------------------- */
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();

  // GATE 0B REDESIGN. The first pass drew absence as empty canvas, which reads as
  // "nothing designed there" rather than "a number that does not exist", the same
  // failure the 07-26 ThreePipeCutaway capped pipe hit. Two fixes, both the critic's:
  // (1) absence needs a FILLED SIBLING to be measured against, and the film was
  // sitting on 39,258 and never showing it, and (2) the two absences are DIFFERENT
  // IN KIND, one stale and one never taken, which empty canvas flattened.
  const land = spring({frame: f - 8, fps, config: {damping: 9, stiffness: 200}});
  // the expected cadence exists BEFORE the pullback, so the pullback crosses unfilled SLOTS
  const slots = interpolate(f, [4, 48], [0, 1], {extrapolateRight: 'clamp'});
  const pull = interpolate(f, [64, 130], [0, 1], {extrapolateRight: 'clamp'});
  const zoom = interpolate(pull, [0, 1], [2.1, 1], {extrapolateRight: 'clamp'});
  const sealF = interpolate(f, [150, 190], [0, 1], {extrapolateRight: 'clamp'});
  const gauge = interpolate(f, [240, 300], [0, 1], {extrapolateRight: 'clamp'});
  const needle = Math.sin(f / 6.5) * 34 * gauge;   // swings freely, nothing to read it against

  const x0 = 140, x1 = 940, yT = 700;
  const px = x0 + (x1 - x0) * 0.05;

  return (
    <Stage grade={<NightGrade f={f} color="#0f3a52" amount={0.34} floor={0.22} horizon={0.08} sources={[{x: px, y: yT, r: 130, color: HULL, intensity: 0.24}, {x: 300, y: 1120, r: 150, color: HULL, intensity: 0.18}]} />}>
      <UnderIceBG f={f} iceY={200} lead={0.12} parallax={0.4} motes={false} />

      <g transform={`translate(540,${yT}) scale(${zoom}) translate(-540,${-yT})`}>
        <line x1={x0} y1={yT} x2={x1} y2={yT} stroke="#7f97a8" strokeWidth={5} />
        {Array.from({length: 18}).map((_, i) => {
          const x = px + ((x1 - px) * (i + 1)) / 18;
          return (
            <g key={i} opacity={slots * 0.5}>
              <line x1={x} y1={yT - 16} x2={x} y2={yT + 16} stroke="#5d7385" strokeWidth={2} strokeDasharray="4 5" />
              <circle cx={x} cy={yT} r={9} fill="none" stroke="#5d7385" strokeWidth={2} strokeDasharray="4 5" />
            </g>
          );
        })}
        <text x={px} y={yT + 58} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={30} fill="#9dc2d6">1992</text>
        <text x={x1} y={yT + 58} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={30} fill="#9dc2d6">2026</text>
        <g opacity={Math.min(1, land * 1.3)}>
          <circle cx={px} cy={yT} r={interpolate(land, [0, 1], [30, 14], {extrapolateRight: 'clamp'})}
            fill={HULL} stroke={INK} strokeWidth={4} />
        </g>
        <g opacity={pull}>
          <text x={(px + x1) / 2} y={yT - 46} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={34}
            fill="#e08a7f">34 YEARS, NO NEW ESTIMATE</text>
        </g>
      </g>

      <g opacity={slots}>
        <g transform="translate(300,1120)">
          <rect x={-176} y={-84} width={352} height={168} rx={10} fill="#0e1d2c" stroke={HULL} strokeWidth={5} />
          <text x={0} y={-30} textAnchor="middle" fontFamily={MONO} fontWeight={500} fontSize={23} fill="#9dc2d6">BEAUFORT BELUGA</text>
          <text x={0} y={26} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={58} fill={HULL}>39,258</text>
          <text x={0} y={62} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={26} fill="#e08a7f">STAMPED 1992</text>
        </g>
      </g>
      {sealF > 0.02 && (
        <g opacity={sealF}>
          <g transform="translate(780,1120)">
            <rect x={-176} y={-84} width={352} height={168} rx={10} fill="#0e1d2c" stroke="#c0392b" strokeWidth={5}
              strokeDasharray="16 12" />
            <text x={0} y={-30} textAnchor="middle" fontFamily={MONO} fontWeight={500} fontSize={23} fill="#9dc2d6">ARCTIC RINGED SEAL</text>
            <text x={0} y={26} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={44} fill="#e08a7f">NO COUNT</text>
            <text x={0} y={62} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={22} fill="#e08a7f">NEVER TAKEN</text>
          </g>
          <RingedSealGhost x={790} y={1330} f={f} scale={0.6} op={0.9} />
        </g>
      )}

      <g opacity={interpolate(f, [10, 34], [0, 1], {extrapolateRight: 'clamp'})}>
        <Plate x={540} y={SAFE_TOP + 24} text="ESA THREATENED" sub="ABUNDANCE UNDETERMINED" w={720} />
      </g>

      {/* THE THESIS: an instrument that cannot be READ. Gate 0B killed the tipping
          balance, because a scale that TIPS argues UNFAIRNESS, which contradicts this
          film's declared even-handed valence and reads as the machine outweighing the
          whale. The honest picture is not unfair, it is UNMEASURABLE. */}
      {gauge > 0.02 && (
        <g opacity={gauge} transform="translate(540,1520)">
          <circle cx={0} cy={0} r={92} fill="#0e1d2c" stroke="#cfe9f5" strokeWidth={6} />
          <path d="M-66,-52 A 84 84 0 0 1 66,-52" fill="none" stroke="#33586e" strokeWidth={12} strokeDasharray="2 26" opacity={0.55} />
          <g transform={`rotate(${needle})`}>
            <line x1={0} y1={10} x2={0} y2={-70} stroke="#e08a7f" strokeWidth={7} strokeLinecap="round" />
          </g>
          <circle cx={0} cy={0} r={10} fill="#cfe9f5" />
          <text x={0} y={140} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={34} fill="#cfe9f5">NO BASELINE TO READ</text>
        </g>
      )}

    </Stage>
  );
};

/* ---------------------------------------------------------------------------
   S7 — THE DATE, THEN THE BUTTON. Wide, low, dolly through. VO lines 13 to 14.
   Beats 21 to 22. The split frame: the machine pins, the whale stays blank.
--------------------------------------------------------------------------- */
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const date = entrance(f, fps, 4, {drop: 120});
  // the split (beat 22, local ~4.4s -> f=132)
  const split = interpolate(f, [132, 168], [0, 1], {extrapolateRight: 'clamp'});
  const pin = spring({frame: f - 150, fps, config: {damping: 11, stiffness: 170}});

  return (
    <Stage grade={<NightGrade f={f} color="#0f3a52" amount={interpolate(f, [200, 300], [0.32, 0.5])} floor={0.24} horizon={0.08} sources={[{x: 252, y: 1180, r: 150, color: CYAN, intensity: 0.42}]} />}>
      <UnderIceBG f={f} iceY={300} lead={interpolate(f, [200, 300], [0.3, 0.06])} parallax={0.55} />

      <g opacity={date.on ? Math.min(1, date.scale) : 0} transform={`translate(0,${date.dy})`}>
        <StatCard x={540} y={620} big="COMMENTS CLOSE AUG 21" sub="91 FR 46055" scale={0.98} color="#1d4b66" />
      </g>

      {/* the split seam */}
      {split > 0.02 && (
        <line x1={540} y1={860} x2={540} y2={1660} stroke="#cfe9f5" strokeWidth={5} opacity={split * 0.8}
          strokeDasharray={800} strokeDashoffset={800 * (1 - split)} />
      )}

      {/* LEFT: the machine, position pinned exactly */}
      <IceGlider x={300} y={1180} f={f} scale={0.78} emotion="fixed" eyeLock={0.9} gain={0.5} />
      {pin > 0.02 && (
        <g opacity={Math.min(1, pin * 1.4)}>
          <circle cx={252} cy={1180} r={8 + 22 * (1 - Math.min(1, pin))} fill="none" stroke={CYAN} strokeWidth={5} />
          <circle cx={252} cy={1180} r={4.5} fill={CYAN} />
        </g>
      )}
      <g opacity={split}>
        <text x={300} y={1420} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={38} fill={CYAN}>SOLVED</text>
      </g>

      {/* RIGHT: the whale, still an unfilled outline, and it does NOT resolve */}
      <g style={{filter: 'grayscale(1) brightness(3.6) contrast(0.18)'}} opacity={0.85}>
        <Beluga x={790} y={1180} f={f} scale={0.95} mode="cruise" swim={0.35} />
      </g>
      <ellipse cx={790} cy={1186} rx={178} ry={62} fill="none" stroke="#bfe4f5" strokeWidth={5}
        strokeDasharray="15 11" opacity={0.9} />
      <g opacity={split}>
        <text x={790} y={1420} textAnchor="middle" fontFamily={MONO} fontWeight={700} fontSize={38} fill="#e08a7f">UNKNOWN</text>
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
  const scale = interpolate(pop, [0, 1], [0.88, 1], {extrapolateRight: 'clamp'});
  const rise = interpolate(pop, [0, 1], [20, 0], {extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', bottom: 300, left: 0, right: 0, display: 'flex', justifyContent: 'center', padding: '0 60px'}}>
      <div style={{background: 'rgba(8,16,24,0.93)', borderRadius: 14, padding: '16px 30px', maxWidth: 940,
        border: `4px solid ${ICE}`, transform: `translateY(${rise}px) scale(${scale})`, transformOrigin: 'center bottom'}}>
        <div style={{fontFamily: BOLD, fontWeight: 900, fontSize: 46, lineHeight: 1.12, color: '#fff', textAlign: 'center',
          letterSpacing: 0.4, textShadow: '2px 3px 0 rgba(0,0,0,0.75)'}}>{cue.text}</div>
      </div>
    </div>
  );
};

export const ep0730Schema = z.object({
  captions: z.array(z.object({start: z.number(), end: z.number(), text: z.string()})),
  scenes: z.array(z.object({from: z.number(), dur: z.number()})).optional(),
  total: z.number().optional(),
  mouth: z.array(z.number()).optional(),
  accents: z.array(z.object({frame: z.number(), word: z.string(), energy: z.number().optional(), lineIdx: z.number().optional()})).optional(),
});
export type Ep0730Props = z.infer<typeof ep0730Schema>;

const SCENES: React.FC[] = [S1, S2, S3, S4, S5, S6, S7];
const DEFAULT_BOUNDS = [
  {from: 0, dur: 258}, {from: 258, dur: 321}, {from: 579, dur: 216}, {from: 795, dur: 303},
  {from: 1098, dur: 210}, {from: 1308, dur: 348}, {from: 1656, dur: 345},
];

export const Ep0730: React.FC<Ep0730Props> = ({captions, scenes}) => {
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
