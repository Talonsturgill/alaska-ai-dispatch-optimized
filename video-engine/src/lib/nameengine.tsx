import React from 'react';
import {tones, FormGradient, RimLight, ContactShadow} from './lighting';
import {vitals} from './motion';

// =============================================================================
// THE NAME ENGINE — the 2008 classifier as a physical object.
// NET-NEW 2026-08-05 ("The Net Comes First").
//
// REDESIGNED AT GATE 0D, AND THE CRITIC WAS RIGHT. The first design was a
// brass bench instrument with an intake and a plate that prints an answer,
// staged in macro-closeup under a practical lamp. That is bench.tsx's
// AshReader, built 2026-08-01 and staged in exactly that treatment two runs
// ago. The stated differences (starved rather than fed, one clean name rather
// than a hedged shortlist) were BEHAVIOURAL, and a viewer cannot see behaviour
// in a silhouette.
//
// So the shape language moved instead, and moving it made the film better.
// AshReader is rounded, organic, warm brass, a thing on a bench. This machine
// is RECTILINEAR AND STACKED: a hard-cornered unit with machined panel lines
// and a face that is the same proportion as a museum drawer, because it
// belongs to the CABINET, to the ordering system, to the side of this film's
// shape grammar that imposes order. The living world is the curved, irregular
// thing it is waiting for and never gets.
//
// THE ONE ROUND ELEMENT IN A SQUARE MACHINE IS THE INTAKE IRIS, and that is
// the asset's whole identity. AshReader has no iris. Six overlapping leaves
// that open, hold, and close on visible empty air is a mechanical grammar this
// shelf does not own yet, it is legible at feed size because it is the only
// circle in a field of right angles, and it is the film's thesis: the machine
// works, and there is nothing to put in it.
//
// STATE, carried by three channels because one is never enough at feed size
// (07-25 horn, 07-26 cone, 07-30 glider, all learned the same way):
//   the IRIS      open and waiting, or clamped shut
//   the FEED BAY  visibly empty, or carrying a specimen
//   the LAMP      lights ONLY on an asserted name, the SeismicStation rule
// =============================================================================

const hash = (s: string) => Math.abs([...s].reduce((a, c) => (a * 31 + c.charCodeAt(0)) | 0, 17));
const uid = (s: string) => 'ne' + hash(s).toString(36);

const CASE = '#8A7A5E';       // machined brass-grey, deliberately duller than AshReader's warm brass
const FACE = '#C9963F';
const ENAMEL = '#EDE7DA';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

export type EngineState = 'ready' | 'reading' | 'named' | 'starved';

/**
 * The classifier. Rectilinear, stacked, drawer-proportioned.
 *
 * `iris`   0 = clamped shut, 1 = fully open. Drive it open-hold-closed on an
 *          irrational period for the starved gag and it never reads as a loop.
 * `feed`   0..1 runs a specimen along the stage and into the iris. At 0 the
 *          bay is VISIBLY EMPTY, which is the point of the whole asset.
 * `plate`  the printed name. Null means nothing has been asserted, and the
 *          lamp stays dark, always.
 * `cut`    0..1 opens the housing along its length for the cutaway beat, so
 *          the empty feed bay can be seen from inside.
 */
export const NameEngine: React.FC<{
  x: number; y: number; f: number; scale?: number;
  state?: EngineState;
  iris?: number;
  feed?: number;
  plate?: string | null;
  lamp?: number;
  cut?: number;
  accent?: number;
  accentColor?: string;
  phase?: number;
  gain?: number;
  groundY?: number;
}> = ({
  x, y, f, scale = 1, state = 'ready', iris = 1, feed = 0, plate = null,
  lamp = 0, cut = 0, accent = 0, accentColor = '#35C8C0', phase = 0, gain = 1, groundY,
}) => {
  const id = uid(`ne${x}${y}`);
  const t = tones(CASE);
  const tf = tones(FACE);
  const v = vitals(f, phase, gain);
  // the lamp can only be lit when a name has actually been asserted
  const lit = plate ? lamp : 0;

  const W = 260, H = 168;
  // the cutaway slides the front shell off to the left along the machine's axis
  const shellDX = -cut * 96;

  // six iris leaves. The one circle in a square machine.
  const leaves = Array.from({length: 6}, (_, i) => {
    const a = (i * 60 + f * 0.12) * (Math.PI / 180);
    const R = 27;
    // closed leaves reach past centre and overlap; open ones retract to the ring
    const reach = R * (1 - iris * 0.82);
    const cx = Math.cos(a) * (R - reach * 0.5);
    const cy = Math.sin(a) * (R - reach * 0.5);
    const rot = (i * 60 + 20) + iris * 26;
    return {cx, cy, rot, key: i};
  });

  return (
    <g transform={`translate(${x},${y}) scale(${scale})`}>
      <defs>
        <FormGradient id={`${id}-case`} t={t} />
        <FormGradient id={`${id}-face`} t={tf} />
        <clipPath id={`${id}-throat`}>
          <circle cx={0} cy={0} r={28} />
        </clipPath>
      </defs>

      {groundY !== undefined && (
        <ContactShadow cx={0} cy={groundY} rx={W * 0.52} ry={13} opacity={0.3} />
      )}

      <g transform={`translate(0,${v.bob * 0.35})`}>
        {/* ---- the stacked plinth. This machine sits in the cabinet's language. ---- */}
        <rect x={-W / 2 - 10} y={H / 2 - 4} width={W + 20} height={16} rx={2} fill={t.shade} />
        <rect x={-W / 2 - 4} y={H / 2 - 16} width={W + 8} height={14} rx={2} fill={t.core} />

        {/* ---- THE FEED BAY, drawn BEHIND the shell so the cutaway exposes it ---- */}
        <g>
          <rect x={-W / 2 + 18} y={-16} width={W - 36} height={44} rx={2}
                fill="#0E1512" opacity={0.9} />
          {/* the stage rails the specimen would ride, running into the iris throat */}
          <rect x={-W / 2 + 24} y={2} width={W - 48} height={3} fill={t.core} opacity={0.55} />
          <rect x={-W / 2 + 24} y={12} width={W - 48} height={3} fill={t.core} opacity={0.35} />
          {/* the specimen, only when there IS one. feed=0 leaves the bay empty. */}
          {feed > 0 && (
            <g transform={`translate(${-W / 2 + 30 + feed * (W - 90)},4)`}>
              <ellipse cx={0} cy={0} rx={13} ry={9} fill="#2E2A24" />
              <ellipse cx={0} cy={-1.5} rx={10} ry={6} fill="#6E6252" opacity={0.6} />
            </g>
          )}
        </g>

        {/* ---- THE SHELL. Hard corners, machined panel lines, drawer proportion. ---- */}
        <g transform={`translate(${shellDX},0)`}>
          <rect x={-W / 2} y={-H / 2} width={W} height={H} rx={3} fill={`url(#${id}-case)`} />
          {/* panel lines: parallel, regular, the opposite of the beetle's geometry */}
          {[-52, -34, 40, 58].map((py, i) => (
            <line key={i} x1={-W / 2 + 8} y1={py} x2={W / 2 - 8} y2={py}
                  stroke="#000" strokeWidth={1.4} opacity={0.16} />
          ))}
          {/* recessed screws at the four corners, the cabinet's own hardware */}
          {[[-W / 2 + 12, -H / 2 + 12], [W / 2 - 12, -H / 2 + 12],
            [-W / 2 + 12, H / 2 - 12], [W / 2 - 12, H / 2 - 12]].map(([sx, sy], i) => (
            <g key={i}>
              <circle cx={sx} cy={sy} r={4} fill={t.shade} />
              <line x1={sx - 2.4} y1={sy} x2={sx + 2.4} y2={sy} stroke="#000" strokeWidth={1.2} opacity={0.5} />
            </g>
          ))}

          {/* the brass face plate: the drawer front this machine is pretending to be */}
          <rect x={-W / 2 + 16} y={-H / 2 + 20} width={W - 32} height={H - 52} rx={2}
                fill={`url(#${id}-face)`} opacity={0.22} />

          {/* ---- THE GENE WINDOW. A slot with a bright reading band that travels. ---- */}
          <rect x={-W / 2 + 26} y={-H / 2 + 28} width={W - 52} height={22} rx={2} fill="#141C19" />
          {Array.from({length: 22}, (_, i) => (
            <rect key={i} x={-W / 2 + 30 + i * 8.6} y={-H / 2 + 32} width={4} height={14}
                  fill={ENAMEL} opacity={0.2 + ((hash(`g${i}`) % 5) * 0.13)} />
          ))}
          {state === 'reading' && (
            <rect x={-W / 2 + 26 + ((f * 3.1) % (W - 52))} y={-H / 2 + 28} width={16} height={22}
                  fill={ENAMEL} opacity={0.5} />
          )}

          {/* ---- THE IRIS. The one round thing, and the asset's whole identity. ---- */}
          <g transform={`translate(0,6)`}>
            {/* the throat behind the leaves. Real depth, so a closed iris shuts on something. */}
            <circle cx={0} cy={0} r={28} fill="#0A100E" />
            <g clipPath={`url(#${id}-throat)`}>
              <circle cx={0} cy={6} r={20} fill="#050807" opacity={0.8} />
            </g>
            {leaves.map((L) => (
              <g key={L.key} transform={`translate(${L.cx},${L.cy}) rotate(${L.rot})`}>
                <path d="M -16 -5 L 16 -9 L 15 6 L -15 7 Z" fill={t.core} stroke="#141C19" strokeWidth={1.4} />
                <path d="M -16 -5 L 16 -9 L 16 -5 L -15 0 Z" fill={ENAMEL} opacity={0.16} />
              </g>
            ))}
            <circle cx={0} cy={0} r={29} fill="none" stroke={t.shade} strokeWidth={5} />
            <circle cx={0} cy={0} r={29} fill="none" stroke="#141C19" strokeWidth={2} />
          </g>

          {/* ---- THE LAMP. Lights ONLY when a name has been asserted. ---- */}
          <g transform={`translate(${W / 2 - 34},${H / 2 - 34})`}>
            <circle cx={0} cy={0} r={9} fill={t.shade} />
            <circle cx={0} cy={0} r={6} fill={lit > 0 ? accentColor : '#25302B'}
                    opacity={lit > 0 ? 0.55 + lit * 0.45 : 1} />
            {lit > 0 && <circle cx={0} cy={0} r={13} fill={accentColor} opacity={0.18 * lit} />}
          </g>

          {/* ---- THE NAME PLATE BAY. Empty until something is asserted. ---- */}
          <g transform={`translate(${-W / 2 + 30},${H / 2 - 40})`}>
            <rect x={0} y={0} width={132} height={30} rx={2} fill="#141C19" opacity={0.85} />
            {plate ? (
              <>
                <rect x={3} y={3} width={126} height={24} rx={1} fill={ENAMEL} />
                <text x={66} y={20} textAnchor="middle" fill="#14100C"
                      style={{font: `700 15px ${MONO}`, letterSpacing: 0.5}}>{plate}</text>
              </>
            ) : (
              <line x1={10} y1={15} x2={122} y2={15} stroke={ENAMEL} strokeWidth={1.5} opacity={0.22} />
            )}
          </g>

          <RimLight d={`M ${-W / 2} ${-H / 2} L ${W / 2} ${-H / 2} L ${W / 2} ${H / 2} L ${-W / 2} ${H / 2} Z`}
                    w={2.4} opacity={0.42} />
          <rect x={-W / 2} y={-H / 2} width={W} height={H} rx={3}
                fill="none" stroke="#141C19" strokeWidth={3.4} />
        </g>

        {/* the accent tick, only ever present when a name exists */}
        {plate && accent > 0 && (
          <rect x={-W / 2} y={H / 2 - 3} width={W * accent} height={3} fill={accentColor} opacity={0.7} />
        )}
      </g>
    </g>
  );
};
