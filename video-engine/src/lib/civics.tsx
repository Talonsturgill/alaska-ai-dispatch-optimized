import React from 'react';
import {INK, tones, paleTones, FormGradient, RimLight, ContactShadow, BrushedMetal} from './lighting';
import {vitals} from './motion';

// =============================================================================
// CIVICS — the RULES kit. NET-NEW 2026-07-31 for "the line that isn't drawn".
//
// The shelf could draw machines, animals, biomes, instruments and paperwork, but it
// had nothing for the thing this channel actually covers most often: A RULE, and the
// moment a rule meets a thing it is supposed to act on. Four prior Dispatches wanted
// this and improvised around it (07-18 the land conveyance, 07-22 the enhanced-use
// lease, 07-26 the records match, 07-29 the award list). props.tsx has
// CheckpointGateLever, but that is a faceless barrier ARM with no condition on it and
// no verdict, so it can show a road closed and nothing else. It cannot show WHY.
//
// THE SHAPE-LANGUAGE DECISION THAT DRIVES THE WHOLE FILE, and it is the thesis:
//   A CONDITIONAL rule and an UNCONDITIONAL rule are drawn as opposite silhouettes.
//   - `Gate` is ROUNDED and ARTICULATED and MANY-PARTED and it has a FACE. It carries
//     a printed condition, it inspects, and it can answer either way. A thing that can
//     say "it depends" must visibly have parts that could move differently.
//   - `ThresholdGate` is the SAME rig built twice. With `marks` and `hands` at 1 it is a
//     bounded instrument that can discriminate. With both at 0 it is unbounded, and the
//     blank dial and handless clock are the two missing numbers the film is about.
//   A viewer should be able to tell which kind of rule they are looking at from the
//   silhouette alone at thumbnail size, before reading a single label.
//
// Every string is a param. A prop with baked-in story copy is an episode-local, not a
// library asset (the props.tsx rule, kept).
// =============================================================================

const BOLD = 'Arial Black, Arial, sans-serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

/** verdicts a conditional gate can reach. `asking` is the resting state. */
export type Verdict = 'asking' | 'pass' | 'block';

const LAMP = {
  asking: '#e8b23a',
  pass: '#3fb46e',
  block: '#e0362c',
};

/**
 * A CONDITIONAL GATE: a rule that carries a printed test and can answer either way.
 *
 * `condition`  the test it applies, in plain words, printed on its board.
 * `source`     the authority line under it (who wrote this rule).
 * `verdict`    asking | pass | block. Drives the lamp, the face, and the arm.
 * `swing`      0..1 overrides the arm angle; by default the verdict drives it, so a
 *              PASS visibly opens the road and a BLOCK visibly closes it.
 * `accent`     0..1 VO-emphasis reactivity (a small brow/tilt kick on emphasised words).
 * `phase`      decorrelates the idle so two gates on screen never bob in lockstep.
 */
export const Gate: React.FC<{
  f: number;
  x: number;
  y: number;
  condition: string;
  source?: string;
  verdict?: Verdict;
  swing?: number;
  scale?: number;
  accent?: number;
  phase?: number;
  tint?: string;
}> = ({f, x, y, condition, source, verdict = 'asking', swing, scale = 1, accent = 0, phase = 0, tint = '#8d9aa8'}) => {
  const body = tones(tint);
  const board = paleTones('#eef3f7');
  const uid = `gate_${Math.round(x)}_${Math.round(y)}`;
  const v = vitals(f, phase, 1);

  // The arm follows the verdict unless the caller overrides. Open is UP (road clear).
  const open = swing ?? (verdict === 'pass' ? 1 : verdict === 'block' ? 0 : 0.18);
  const armAngle = -4 - open * 74;

  // the face: a brow bar that reads the verdict even when the lamp is small
  const brow = verdict === 'block' ? -7 : verdict === 'pass' ? 5 : 0;
  const blink = ((f + Math.round(phase * 37)) % 104) < 5;
  const lamp = LAMP[verdict];
  // an inspecting gate sweeps its look; a decided one locks forward
  const look = verdict === 'asking' ? Math.sin(f / 26 + phase) * 3.4 : 0;
  const kick = accent * 3;

  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <ContactShadow cx={0} cy={18} rx={132} ry={24} opacity={0.32} blur={10} />
      <defs>
        <FormGradient id={`${uid}_post`} t={body} softness={0.9} />
        <FormGradient id={`${uid}_board`} t={board} softness={0.75} />
        <FormGradient id={`${uid}_arm`} t={body} softness={0.85} />
      </defs>

      {/* --- the housing: rounded, with visible separate parts (it is articulated) --- */}
      <g transform={`translate(0,${v.bob * 0.5}) rotate(${v.tilt * 0.5 + kick * 0.3})`}>
        {/* base plinth */}
        <rect x={-58} y={-40} width={116} height={58} rx={16} fill={body.base} stroke={INK} strokeWidth={6} />
        <rect x={-58} y={-40} width={116} height={58} rx={16} fill={`url(#${uid}_post)`} opacity={0.55} />
        <BrushedMetal x={-58} y={-40} w={116} h={58} opacity={0.14} />

        {/* the head, a separate rounded part sitting on the plinth */}
        <g transform={`translate(0,${-104 + v.breath * 1.4})`}>
          <rect x={-52} y={-52} width={104} height={94} rx={26} fill={body.base} stroke={INK} strokeWidth={6} />
          <rect x={-52} y={-52} width={104} height={94} rx={26} fill={`url(#${uid}_post)`} opacity={0.5} />
          <RimLight d="M-48,-46 L-48,34" w={4.5} opacity={0.5} />

          {/* THE FACE. A gate that asks a question has to look like it is asking one. */}
          <g transform={`translate(${look},0)`}>
            {/* brow bar carries the verdict at any size */}
            <rect x={-30} y={-26 + brow * 0.6} width={60} height={9} rx={4.5}
              fill={INK} transform={`rotate(${brow} 0 -22)`} />
            {[-15, 15].map((ex, i) => (
              <g key={i} transform={`translate(${ex},-6)`}>
                <circle cx={0} cy={0} r={10} fill="#f4f7fa" stroke={INK} strokeWidth={3.5} />
                {!blink && <circle cx={look * 0.5} cy={0} r={4.6} fill={INK} />}
                {blink && <rect x={-9} y={-2} width={18} height={4} rx={2} fill={INK} />}
              </g>
            ))}
          </g>

          {/* the verdict lamp, a real housing on the crown */}
          <g transform="translate(0,-62)">
            <rect x={-15} y={-16} width={30} height={26} rx={7} fill="#232c34" stroke={INK} strokeWidth={5} />
            <circle cx={0} cy={-3} r={8} fill="#2a2f36" />
            <circle cx={0} cy={-3} r={8} fill={lamp} opacity={0.95} style={{mixBlendMode: 'screen'}} />
            <circle cx={0} cy={-3} r={13} fill="none" stroke={lamp} strokeWidth={2.5}
              opacity={verdict === 'asking' ? 0.28 + 0.22 * Math.sin(f / 7 + phase) : 0.5} />
          </g>
        </g>

        {/* --- THE CONDITION BOARD: the rule is printed ON the object that applies it --- */}
        <g transform={`translate(0,${44 + v.bob * 0.3})`}>
          <ContactShadow cx={0} cy={46} rx={150} ry={13} opacity={0.22} />
          <rect x={-168} y={-2} width={336} height={78} rx={12}
            fill={`url(#${uid}_board)`} stroke={INK} strokeWidth={6} />
          <RimLight d="M-164,4 L-164,70" w={4} opacity={0.42} />
          <text x={0} y={source ? 30 : 42} textAnchor="middle" fontFamily={BOLD} fontWeight={900}
            fontSize={26} fill={INK} letterSpacing={0.4}>{condition}</text>
          {source && (
            <text x={0} y={60} textAnchor="middle" fontFamily={MONO} fontWeight={600}
              fontSize={17} fill="#5c6b78" letterSpacing={0.8}>{source}</text>
          )}
        </g>

        {/* --- the barrier arm, hinged on a visible pivot (the articulation, made obvious) --- */}
        <g transform="translate(52,-96)">
          <circle cx={0} cy={0} r={12} fill="#232c34" stroke={INK} strokeWidth={5} />
          <circle cx={0} cy={0} r={3.6} fill="#c9cfd8" />
          <g transform={`rotate(${armAngle} 0 0)`}>
            <rect x={0} y={-11} width={216} height={22} rx={9} fill={body.core} stroke={INK} strokeWidth={5.5} />
            <rect x={0} y={-11} width={216} height={22} rx={9} fill={`url(#${uid}_arm)`} opacity={0.5} />
            {Array.from({length: 4}).map((_, i) => (
              <rect key={i} x={16 + i * 48} y={-11} width={24} height={22}
                fill={i % 2 === 0 ? '#1a1d24' : '#f0f3f6'} opacity={0.82} />
            ))}
            <RimLight d="M4,-9 L212,-9" w={3} opacity={0.5} />
          </g>
        </g>
      </g>
    </g>
  );
};

/**
 * THE THRESHOLD GATE: a rule that MEASURES A THING AGAINST A LINE AND DECIDES.
 *
 * The shelf could draw a binary refusal (props.tsx GearLever with its DENIED badge), a
 * traced boundary (BoundaryReveal) and a measurement (MeasuringChain), but nothing that
 * does all three at once, which is the single most common shape in Alaska policy:
 * permitting, quotas, tariffs, licensing, sunsets.
 *
 * ONE RIG, TWO CONFIGURATIONS, AND THE DIFFERENCE IS THE ARGUMENT. Build it once with
 * `marks`/`hands` at 1 and you have a bounded instrument. Build the same rig with both
 * at 0 and you have an unbounded one. Setting them side by side states a scope contrast
 * as a CONSEQUENCE you can see rather than as a comparative-statutes footnote.
 *
 *   `marks`  0..1  the road scale plate's gradations. AT 0 THE NEEDLE HAS NOTHING TO
 *                  POINT AT and rattles against its pin. This is the size threshold.
 *   `hands`  0..1  the post-head clock's hands. At 0 the face is blank and the rule has
 *                  no end condition. This is the time cap.
 *   `lamp`   0..1  lights ONLY when a threshold actually fired, so a lit lamp always
 *                  means the instrument discriminated. A scene can't glow by accident.
 *
 * Shape language: INSTITUTIONAL BUT NOT COLD. A rectilinear striped boom on a stout
 * pivot, but the post head is ROUNDED with a brow bar and two lidded eyes, so it reads
 * as a doorman rather than a monolith. It is not a villain. It is trying to do its job
 * with an instrument nobody finished.
 *
 * LEGIBILITY IS THE KNOWN RISK, and it has bitten this shelf three times (the 07-25
 * SeismicStation horn that read as a lollipop, the 07-26 TaperedCone that read as a
 * satellite dish, the 07-30 ice keels that read as bunting). The whole argument here
 * rests on a viewer seeing, in under a second on a phone, that one dial has tick marks
 * and another does not. So the gradations are drawn DELIBERATELY OVERSIZED past realism,
 * the blank face carries a dashed ghost arc where marks would be (an absence only reads
 * as an absence when it is dashed and labelled), and GateLook.tsx renders both
 * configurations in one frame so the legibility test happens before any scene is authored.
 */
export const ThresholdGate: React.FC<{
  f: number;
  x: number;
  y: number;
  boom?: number;          // 0 = raised/clear, 1 = slammed down
  cut?: number;           // 0..1 a real sorting aperture is present in the plate
  hands?: number;         // 0..1 clock hands present
  lamp?: number;          // 0..1 decision lamp, only lights when a threshold fired
  cutW?: number;          // width of that aperture, i.e. how big a load may pass
  cutLabel?: string;      // what the limit is called on the plate
  label?: string;         // the jurisdiction plate
  scale?: number;
  accent?: number;
  phase?: number;
  tint?: string;
}> = ({
  f, x, y, boom = 0, cut = 0, cutW = 120, cutLabel, hands = 0, lamp = 0,
  label, scale = 1, accent = 0, phase = 0, tint = '#93a0ad',
}) => {
  const body = tones(tint);
  const plate = paleTones('#e9eff4');
  const uid = `tg_${Math.round(x)}_${Math.round(y)}`;
  const v = vitals(f, phase, 1);
  const armAngle = -78 + boom * 78;
  const blink = ((f + Math.round(phase * 53)) % 112) < 5;

  const lampColor = lamp > 0.05 ? '#e8b23a' : '#3a4149';

  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <ContactShadow cx={0} cy={16} rx={120} ry={22} opacity={0.32} blur={10} />
      <defs>
        <FormGradient id={`${uid}_p`} t={body} softness={0.9} />
        <FormGradient id={`${uid}_d`} t={plate} softness={0.7} />
      </defs>

      {/* ---- THE SORTING APERTURE. The size threshold lives here.
             DESIGN CHANGE, and the reason is worth keeping. Pass 1 to 3 drew this as a
             SCALE PLATE with a needle and gradations, and it worked. It was dropped anyway
             because the 2026-07-30 Dispatch had already used "a gauge with no scale printed
             behind its needle" as its own thesis image, one run earlier. The composition-axes
             gate compares palette and metaphor tokens and would have caught it, but a viewer
             would have FELT it first, and that run's own retrospective flagged story-shape
             repetition as the thing the gate cannot see.
             An aperture is also the better drawing on the merits: a dial reports that nothing
             is measured, a slot shows WHICH LOAD GETS THROUGH, which is the actual argument.
             `cut` 0..1 opens a real hole sized by `cutW`. At 0 the plate is SOLID, and a solid
             plate stops everything it meets rather than discriminating. ---- */}
      <g transform="translate(-186,-92)">
        <ContactShadow cx={0} cy={188} rx={112} ry={18} opacity={0.3} />
        {/* the plate body, drawn as two halves around the cut so the opening is real geometry */}
        <g>
          <rect x={-104} y={-40} width={208} height={228} rx={8}
            fill={body.base} stroke={INK} strokeWidth={8} />
          <rect x={-104} y={-40} width={208} height={228} rx={8}
            fill={`url(#${uid}_p)`} opacity={0.5} />
          <BrushedMetal x={-104} y={-40} w={208} h={228} opacity={0.16} />
          {/* corner bolts: detail density, so the plate reads as fabricated */}
          {[[-84,-20],[84,-20],[-84,168],[84,168]].map(([bx,by],i)=>(
            <circle key={i} cx={bx} cy={by} r={6} fill="#2b333b" stroke={INK} strokeWidth={3.5} />
          ))}
        </g>

        {cut > 0.05 ? (
          <>
            {/* THE CUT. A real opening, with a lit inner reveal so it reads as a hole
                through a thick plate rather than as a painted rectangle. */}
            <rect x={-cutW / 2} y={30} width={cutW} height={92} rx={6} fill="#cddbe4" />
            <rect x={-cutW / 2} y={30} width={cutW} height={92} rx={6}
              fill="none" stroke={INK} strokeWidth={8} />
            <rect x={-cutW / 2 + 7} y={37} width={cutW - 14} height={12} rx={4}
              fill={INK} opacity={0.22} />
            {/* the threshold edge, in the film's one reserved colour */}
            <line x1={-cutW / 2} y1={30} x2={cutW / 2} y2={30} stroke="#c0392b" strokeWidth={11}
              strokeLinecap="round" />
            <text x={0} y={214} textAnchor="middle" fontFamily={MONO} fontWeight={700}
              fontSize={19} fill={INK} letterSpacing={1.2}>{cutLabel ?? 'SIZE LIMIT'}</text>
          </>
        ) : (
          <>
            {/* THE UNCUT PLATE. A dashed ghost of the opening that was never made, plus a
                printed word, because an absence only reads as an absence when it is dashed
                and labelled (the 07-30 RingedSealGhost lesson). */}
            <rect x={-cutW / 2} y={30} width={cutW} height={92} rx={6} fill="none"
              stroke={INK} strokeWidth={6} strokeDasharray="15 15" opacity={0.42} />
            <text x={0} y={86} textAnchor="middle" fontFamily={MONO} fontWeight={700}
              fontSize={25} fill={INK} opacity={0.6} letterSpacing={1.8}>NO CUT</text>
            <text x={0} y={214} textAnchor="middle" fontFamily={MONO} fontWeight={700}
              fontSize={19} fill={INK} opacity={0.75} letterSpacing={1.2}>NO SIZE LIMIT</text>
          </>
        )}
        <RimLight d="M-100,-34 L-100,182" w={4.5} opacity={0.45} />
      </g>

      {/* ---- the post: rounded head, brow bar, two lidded eyes. A doorman, not a slab. ---- */}
      <g transform={`translate(0,${v.bob * 0.5})`}>
        <rect x={-30} y={-118} width={60} height={134} rx={10} fill={body.base} stroke={INK} strokeWidth={6} />
        <rect x={-30} y={-118} width={60} height={134} rx={10} fill={`url(#${uid}_p)`} opacity={0.55} />
        <BrushedMetal x={-30} y={-118} w={60} h={134} opacity={0.15} />
        <RimLight d="M-30,-118 L-30,16" w={4} opacity={0.5} />

        <g transform={`translate(0,${-176 + v.breath * 1.2})`}>
          <rect x={-52} y={-48} width={104} height={92} rx={26} fill={body.base} stroke={INK} strokeWidth={6} />
          <rect x={-52} y={-48} width={104} height={92} rx={26} fill={`url(#${uid}_p)`} opacity={0.5} />
          {/* panel line + rivets: detail density, so the head is a built thing not a lozenge */}
          <line x1={-44} y1={26} x2={44} y2={26} stroke={INK} strokeWidth={3} opacity={0.35} />
          {[-36, 36].map((rx, i) => <circle key={i} cx={rx} cy={34} r={3.2} fill={INK} opacity={0.4} />)}
          {/* THE BROW IS LIFTED WELL CLEAR OF THE EYES. Pass 1 sat it right on them and the
              result was the 'burglar mask' the Character rig was explicitly fixed for on
              2026-07-18b. A brow has to read as a separate expressive part. */}
          <rect x={-30} y={-34 - accent * 3} width={60} height={9} rx={4.5} fill={INK} />
          {[-16, 16].map((ex, i) => (
            <g key={i} transform="translate(0,0)">
              <circle cx={ex} cy={-6} r={11} fill="#f4f7fa" stroke={INK} strokeWidth={3.4} />
              {!blink && <circle cx={ex} cy={-6} r={5} fill={INK} />}
              {blink && <rect x={ex - 9} y={-8} width={18} height={4} rx={2} fill={INK} />}
            </g>
          ))}
          {/* the decision lamp: dark unless a threshold actually fired */}
          <g transform="translate(-62,-8)">
            <rect x={-14} y={-15} width={28} height={23} rx={6} fill="#232c34" stroke={INK} strokeWidth={4.5} />
            <circle cx={0} cy={-3} r={7.5} fill={lampColor} opacity={lamp > 0.05 ? 0.95 : 1}
              style={lamp > 0.05 ? {mixBlendMode: 'screen'} : undefined} />
          </g>
        </g>

        {/* ---- THE CLOCK. The time cap lives here. Handless = no end condition.
               Pass 2 nearly doubled it and thickened the hands: at pass-1 size the
               hands/no-hands difference was invisible below full scale, and it is one of
               the film's two missing numbers, so it has to survive the feed.
               PASS 3 CROWN-MOUNTED IT ABOVE THE HEAD. On the post body it sat exactly where
               the boom sweeps, so the arm crossed the face in every raised configuration
               and the one detail that carries the time cap was occluded half the time. ---- */}
        <g transform={`translate(0,${-292 + v.breath * 1.2})`}>
          {/* mount stem + collar, so the crown clock reads as BOLTED ON rather than floating */}
          <rect x={-9} y={40} width={18} height={60} fill={body.shade} stroke={INK} strokeWidth={5} />
          <rect x={-22} y={34} width={44} height={16} rx={5} fill={body.base} stroke={INK} strokeWidth={5} />
          <circle cx={0} cy={0} r={52} fill={`url(#${uid}_d)`} stroke={INK} strokeWidth={7} />
          {Array.from({length: 12}).map((_, i) => {
            const a = (i * 30) * Math.PI / 180;
            const long = i % 3 === 0;
            return (
              <line key={i}
                x1={Math.sin(a) * (long ? 30 : 36)} y1={-Math.cos(a) * (long ? 30 : 36)}
                x2={Math.sin(a) * 43} y2={-Math.cos(a) * 43}
                stroke={INK} strokeWidth={long ? 6 : 3} strokeLinecap="round" opacity={0.75} />
            );
          })}
          {hands > 0.05 ? (
            <g opacity={hands}>
              <line x1={0} y1={0} x2={0} y2={-34} stroke={INK} strokeWidth={9} strokeLinecap="round" />
              <line x1={0} y1={0} x2={24} y2={11} stroke={INK} strokeWidth={7} strokeLinecap="round" />
              <circle cx={0} cy={0} r={7} fill={INK} />
            </g>
          ) : (
            <>
              {/* an EMPTY HUB with its two mounting holes, so "no hands" reads as parts
                  removed rather than as a clock drawn badly */}
              <circle cx={0} cy={0} r={11} fill="none" stroke={INK} strokeWidth={5}
                strokeDasharray="7 7" opacity={0.6} />
              <circle cx={0} cy={0} r={3.4} fill={INK} opacity={0.5} />
            </>
          )}
        </g>
      </g>

      {/* ---- the striped boom on a visible pivot ---- */}
      <g transform="translate(26,-108)">
        <circle cx={0} cy={0} r={11} fill="#232c34" stroke={INK} strokeWidth={5} />
        <g transform={`rotate(${armAngle} 0 0)`}>
          <rect x={0} y={-10} width={252} height={20} rx={8} fill={body.core} stroke={INK} strokeWidth={5.5} />
          {Array.from({length: 5}).map((_, i) => (
            <rect key={i} x={12 + i * 46} y={-10} width={23} height={20}
              fill={i % 2 === 0 ? '#1a1d24' : '#f0f3f6'} opacity={0.85} />
          ))}
          <RimLight d="M4,-8 L248,-8" w={3} opacity={0.5} />
        </g>
      </g>

      {label && (
        <g transform="translate(150,168)">
          <rect x={-118} y={-24} width={236} height={48} rx={9}
            fill={`url(#${uid}_d)`} stroke={INK} strokeWidth={5} />
          <text x={0} y={10} textAnchor="middle" fontFamily={BOLD} fontWeight={900}
            fontSize={28} fill={INK} letterSpacing={1.4}>{label}</text>
        </g>
      )}
    </g>
  );
};

/**
 * THE APERTURE PLATE, ALONE. Extracted 2026-07-31 so a scene can stage the film's
 * argument at full width without the post and boom eating the frame. The turn is a
 * COMPARISON of two plates, and two whole rigs side by side in a 1080-wide frame push
 * both plates off the edges, which is exactly what the first render did.
 */
export const AperturePlate: React.FC<{
  f: number; x: number; y: number; cut?: number; cutW?: number; cutLabel?: string;
  scale?: number; tint?: string;
}> = ({f, x, y, cut = 0, cutW = 120, cutLabel, scale = 1, tint = '#93a0ad'}) => {
  const body = tones(tint);
  const uid = `ap_${Math.round(x)}_${Math.round(y)}`;
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <defs><FormGradient id={`${uid}_p`} t={body} softness={0.9} /></defs>
      <ContactShadow cx={0} cy={196} rx={116} ry={19} opacity={0.3} />
      <rect x={-104} y={-40} width={208} height={228} rx={8} fill={body.base} stroke={INK} strokeWidth={8} />
      <rect x={-104} y={-40} width={208} height={228} rx={8} fill={`url(#${uid}_p)`} opacity={0.5} />
      <BrushedMetal x={-104} y={-40} w={208} h={228} opacity={0.16} />
      {[[-84,-20],[84,-20],[-84,168],[84,168]].map(([bx,by],i)=>(
        <circle key={i} cx={bx} cy={by} r={6} fill="#2b333b" stroke={INK} strokeWidth={3.5} />
      ))}
      {cut > 0.05 ? (
        <>
          <rect x={-cutW / 2} y={30} width={cutW} height={92} rx={6} fill="#cddbe4" />
          <rect x={-cutW / 2} y={30} width={cutW} height={92} rx={6} fill="none" stroke={INK} strokeWidth={8} />
          <rect x={-cutW / 2 + 7} y={37} width={cutW - 14} height={12} rx={4} fill={INK} opacity={0.22} />
          <line x1={-cutW / 2} y1={30} x2={cutW / 2} y2={30} stroke="#c0392b" strokeWidth={11} strokeLinecap="round" />
          {cutLabel && (
            <text x={0} y={214} textAnchor="middle" fontFamily={MONO} fontWeight={700}
              fontSize={19} fill={INK} letterSpacing={1.2}>{cutLabel}</text>
          )}
        </>
      ) : (
        <>
          <rect x={-cutW / 2} y={30} width={cutW} height={92} rx={6} fill="none" stroke={INK}
            strokeWidth={6} strokeDasharray="15 15" opacity={0.42} />
          <text x={0} y={86} textAnchor="middle" fontFamily={MONO} fontWeight={700}
            fontSize={25} fill={INK} opacity={0.6} letterSpacing={1.8}>NO CUT</text>
          <text x={0} y={214} textAnchor="middle" fontFamily={MONO} fontWeight={700}
            fontSize={19} fill={INK} opacity={0.75} letterSpacing={1.2}>NO SIZE LIMIT</text>
        </>
      )}
      <RimLight d="M-100,-34 L-100,182" w={4.5} opacity={0.45} />
    </g>
  );
};

/**
 * THE CAP CLOCK, ALONE. Same reason as AperturePlate. `sweep` 0..1 runs the hands a
 * full turn so a bounded rule can visibly END, while an unbounded one holds an empty
 * hub that is ABSOLUTELY STILL, which is the film's declared stillness-as-absence beat.
 */
export const CapClock: React.FC<{
  f: number; x: number; y: number; hands?: number; sweep?: number; scale?: number; tint?: string;
}> = ({f, x, y, hands = 0, sweep = 0, scale = 1, tint = '#93a0ad'}) => {
  const plate = paleTones('#e9eff4');
  const uid = `cc_${Math.round(x)}_${Math.round(y)}`;
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <defs><FormGradient id={`${uid}_d`} t={plate} softness={0.7} /></defs>
      <ContactShadow cx={0} cy={72} rx={54} ry={12} opacity={0.24} />
      <circle cx={0} cy={0} r={52} fill={`url(#${uid}_d)`} stroke={INK} strokeWidth={7} />
      {Array.from({length: 12}).map((_, i) => {
        const a = (i * 30) * Math.PI / 180;
        const long = i % 3 === 0;
        return (
          <line key={i} x1={Math.sin(a) * (long ? 30 : 36)} y1={-Math.cos(a) * (long ? 30 : 36)}
            x2={Math.sin(a) * 43} y2={-Math.cos(a) * 43}
            stroke={INK} strokeWidth={long ? 6 : 3} strokeLinecap="round" opacity={0.75} />
        );
      })}
      {hands > 0.05 ? (
        <g opacity={hands}>
          <g transform={`rotate(${sweep * 360} 0 0)`}>
            <line x1={0} y1={0} x2={0} y2={-34} stroke={INK} strokeWidth={9} strokeLinecap="round" />
          </g>
          <g transform={`rotate(${sweep * 30} 0 0)`}>
            <line x1={0} y1={0} x2={0} y2={-22} stroke={INK} strokeWidth={7} strokeLinecap="round" />
          </g>
          <circle cx={0} cy={0} r={7} fill={INK} />
        </g>
      ) : (
        <>
          <circle cx={0} cy={0} r={11} fill="none" stroke={INK} strokeWidth={5} strokeDasharray="7 7" opacity={0.6} />
          <circle cx={0} cy={0} r={3.4} fill={INK} opacity={0.5} />
        </>
      )}
    </g>
  );
};
