import React from 'react';
import {INK, tones, FormGradient, RimLight, ContactShadow} from './lighting';
import {vitals} from './motion';
import {PAPER, TaperedCone, PaperFiber} from './paper';

// ============================================================================
// RECORDS MACHINE — the hero of "The Field That Stopped in 2019" (2026-07-26).
//
// ONE MACHINE, not two. Gate 0B caught the first board running two separate
// brass cutaway plumbing heroes making two different arguments twenty seconds
// apart, plus a reference to "the stem of the mechanism" fourteen seconds before
// the viewer had ever seen a mechanism. So the intake mouth, the output stem,
// the three-pipe interior and the one desk beneath it are all parts of a single
// object the viewer meets whole and then sees opened.
//
// The argument the object makes, with no words: the MOUTH widens and the STEM
// does not. `mouthOpen` and `stemW` are deliberately independent parameters.
// ============================================================================

/**
 * RecordsMachine — closed view. The intake mouth cranks wider tooth by tooth via
 * `mouthOpen` while the output stem stays exactly `stemW` wide, forever.
 * `strain` 0..1 pops rivets and pins the pressure gauge (Gate 0C: the stem's
 * refusal must be STAGED AS MOTION, not declared as an absence).
 */
export const RecordsMachine: React.FC<{
  f: number; x: number; y: number; scale?: number;
  mouthOpen?: number; strain?: number; stemW?: number;
}> = ({f, x, y, scale = 1, mouthOpen = 0, strain = 0, stemW = 84}) => {
  const t = tones(PAPER.hero);
  const v = vitals(f, 4.0, 0.5);
  const o = Math.max(0, Math.min(1, mouthOpen));
  const s = Math.max(0, Math.min(1, strain));
  // the mouth ratchets in discrete teeth, with a small overshoot on each
  const teeth = 7;
  const step = Math.floor(o * teeth) / teeth;
  const frac = o * teeth - Math.floor(o * teeth);
  const over = frac > 0 && frac < 0.3 ? Math.sin(frac / 0.3 * Math.PI) * 0.035 : 0;
  const mouthW = 300 + (step + over) * 560;
  const id = `rm${Math.round(x)}`;
  const shudder = s > 0 ? Math.sin(f / 2.1) * 3.2 * s : 0;
  const gauge = -50 + s * 100;
  return (
    <g transform={`translate(${x},${y + v.bob * 0.5}) scale(${scale})`}>
      <FormGradient id={id} t={t} />
      <ContactShadow cx={0} cy={560} rx={260} opacity={0.34} />

      {/* THE MOUTH — a true tapered cone, never a face-on ellipse */}
      <TaperedCone x={0} y={-210} mouthW={mouthW} stemW={190} len={300} />

      {/* housing body */}
      <rect x={-160} y={70} width={320} height={300} rx={12}
            fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
      {/* rivets — they POP OUT one at a time under load */}
      {[0, 1, 2, 3, 4, 5].map((i) => {
        const popped = s > (i + 1) / 7;
        const dy = popped ? -6 - (i % 3) * 3 : 0;
        return (
          <circle key={i} cx={-132 + i * 53} cy={92 + dy} r={7}
                  fill={popped ? PAPER.brass : t.key} stroke={INK} strokeWidth={2.6}
                  opacity={popped ? 1 : 0.9} />
        );
      })}
      {/* vents */}
      {[150, 172, 194, 216].map((yy) => (
        <line key={yy} x1={-120} y1={yy} x2={120} y2={yy} stroke={INK} strokeWidth={3} opacity={0.45} />
      ))}
      {/* pressure gauge — needles into the red and PINS */}
      <g transform="translate(0,282)">
        <circle r={44} fill={PAPER.front} stroke={INK} strokeWidth={4} />
        <path d="M-38,0 A38,38 0 0,1 38,0" fill="none" stroke={PAPER.seal} strokeWidth={7} opacity={0.85}
              strokeDasharray="18 60" strokeDashoffset={-40} />
        <line x1={0} y1={0} x2={Math.cos((gauge - 90) * Math.PI / 180) * 32}
              y2={Math.sin((gauge - 90) * Math.PI / 180) * 32}
              stroke={INK} strokeWidth={5} strokeLinecap="round" />
        <circle r={6} fill={INK} />
      </g>

      {/* THE STEM — narrow, unchanging, shuddering under load */}
      <g transform={`translate(${shudder},0)`}>
        <TaperedCone x={0} y={370} mouthW={stemW} stemW={stemW} len={170} rings={2} />
      </g>
      <RimLight d="M-160,70 L160,70" />
    </g>
  );
};

/**
 * ThreePipeCutaway — the SAME machine, opened. The rehook.
 *
 * The thesis drawn as a physical ABSENCE: pipe one inbound from the DMV counter
 * and pipe two outbound to Elections are fat and working, and pipe three, which
 * would carry a naturalization certificate back in, simply ENDS IN CAPPED OPEN
 * AIR. Nothing was ever built to receive it. Certificates drop out of the open
 * end onto a drift pile on the floor.
 *
 * `disclose` 0..1 staggers the reveal so the capped pipe is the LAST information
 * the viewer receives (Gate 0C: otherwise the whole disclosure is over in 0.8s
 * and the rest of the beat is a held composition riding a spent reveal).
 * `lock` 0..1 slams the pawl down on the date wheel.
 */
export const ThreePipeCutaway: React.FC<{
  f: number; x: number; y: number; scale?: number; disclose?: number;
  lock?: number; year?: string;
}> = ({f, x, y, scale = 1, disclose = 1, lock = 0, year = '2019'}) => {
  const t = tones(PAPER.hero);
  const d = Math.max(0, Math.min(1, disclose));
  const p1 = Math.max(0, Math.min(1, d / 0.28));
  const p2 = Math.max(0, Math.min(1, (d - 0.30) / 0.28));
  const p3 = Math.max(0, Math.min(1, (d - 0.68) / 0.32));
  const lk = Math.max(0, Math.min(1, lock));
  // opening the housing vents pressure, so pipe two's pulse quickens then re-settles
  const vent = d > 0.3 && d < 0.75 ? 1 : 0;
  const pulse = 0.5 + 0.5 * Math.sin(f / (vent ? 3.4 : 7.2));
  const id = `tpc${Math.round(x)}`;
  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <FormGradient id={id} t={t} />
      <PaperFiber id={`${id}fib`} />
      <ContactShadow cx={0} cy={430} rx={310} opacity={0.32} />

      {/* cross-sectioned housing */}
      <rect x={-300} y={-300} width={600} height={730} rx={14}
            fill={`url(#${id})`} stroke={INK} strokeWidth={5} />
      <rect x={-300} y={-300} width={600} height={730} fill={INK} opacity={0.10} />
      {/* cut edge hatching, so it reads as a SECTION and not a box */}
      {Array.from({length: 16}).map((_, i) => (
        <line key={i} x1={-300} y1={-290 + i * 46} x2={-262} y2={-306 + i * 46}
              stroke={INK} strokeWidth={2.4} opacity={0.4} />
      ))}

      {/* PIPE ONE — inbound from the DMV counter, fat and greased */}
      <g opacity={p1}>
        <path d="M-300,-170 L-40,-170 L-40,40" fill="none" stroke={INK} strokeWidth={62} strokeLinecap="round" />
        <path d="M-300,-170 L-40,-170 L-40,40" fill="none" stroke={t.key} strokeWidth={44} strokeLinecap="round" />
        <path d="M-300,-186 L-52,-186" fill="none" stroke="#fff" strokeWidth={7} opacity={0.30} strokeLinecap="round" />
        <text x={-286} y={-196} fontFamily="JetBrains Mono, monospace" fontSize={22} fill={INK}
              opacity={0.85}>D M V</text>
      </g>

      {/* PIPE TWO — outbound to Elections, fat and PULSING */}
      <g opacity={p2}>
        <path d="M40,40 L40,-240 L300,-240" fill="none" stroke={INK} strokeWidth={62} strokeLinecap="round" />
        <path d="M40,40 L40,-240 L300,-240" fill="none" stroke={t.key} strokeWidth={44} strokeLinecap="round" />
        <path d="M28,28 L28,-240" fill="none" stroke="#fff" strokeWidth={7} opacity={0.28} strokeLinecap="round" />
        <circle cx={40} cy={-40 - pulse * 160} r={17} fill={PAPER.stamp} stroke={INK} strokeWidth={3} />
      </g>

      {/* PIPE THREE — from the courthouse, ENDING IN CAPPED OPEN AIR */}
      <g opacity={p3}>
        <path d="M170,-300 L170,-96" fill="none" stroke={INK} strokeWidth={62} strokeLinecap="round" />
        <path d="M170,-300 L170,-96" fill="none" stroke={t.shade} strokeWidth={44} strokeLinecap="round" />
        {/* the cap. no flange, no bolt holes, nothing was built to receive it. */}
        <ellipse cx={170} cy={-92} rx={34} ry={12} fill={INK} opacity={0.95} />
        <line x1={128} y1={-82} x2={212} y2={-82} stroke={INK} strokeWidth={9} strokeLinecap="round" />
        <line x1={128} y1={-82} x2={212} y2={-82} stroke={PAPER.brass} strokeWidth={4} strokeLinecap="round" />
        {/* certificates falling out of the open end onto a drift pile */}
        {[0, 1, 2].map((i) => {
          const ph = ((f / 34) + i * 0.37) % 1;
          return (
            <g key={i} transform={`translate(${170 + Math.sin(ph * 6.2 + i) * 26},${-60 + ph * 400})
                                    rotate(${ph * 160 - 40})`} opacity={p3 * (1 - ph * 0.25)}>
              <rect x={-42} y={-28} width={84} height={56} fill={PAPER.front} stroke={INK} strokeWidth={2.6} />
              <ellipse cx={24} cy={14} rx={12} ry={9} fill={PAPER.seal} stroke={INK} strokeWidth={1.6} />
            </g>
          );
        })}
        {/* the drift pile beneath the open end */}
        <g opacity={p3}>
          {[0, 1, 2, 3, 4].map((i) => (
            <rect key={i} x={110 + (i % 3) * 16} y={396 - i * 7} width={70} height={16}
                  fill={PAPER.front} stroke={INK} strokeWidth={2.2}
                  transform={`rotate(${-8 + i * 4},170,400)`} />
          ))}
        </g>
      </g>

      {/* the date wheel + the PAWL that locks it */}
      <g transform="translate(-150,300)">
        <rect x={-86} y={-46} width={172} height={92} rx={8} fill={PAPER.brass} stroke={INK} strokeWidth={4} />
        <rect x={-70} y={-30} width={140} height={60} fill={PAPER.ink} opacity={0.82} />
        <text x={0} y={16} textAnchor="middle" fontFamily="JetBrains Mono, monospace"
              fontWeight={700} fontSize={40} fill={PAPER.front}>{year}</text>
        {/* pawl: slams down and LOCKS */}
        <g transform={`translate(0,${-92 + lk * 40})`}>
          <path d="M-16,-40 L16,-40 L10,10 L-10,10 Z" fill={PAPER.hero} stroke={INK} strokeWidth={4} />
          <rect x={-22} y={-56} width={44} height={18} rx={5} fill={PAPER.brass} stroke={INK} strokeWidth={3} />
        </g>
      </g>
      <RimLight d="M-300,-300 L300,-300" />
    </g>
  );
};
