import React from 'react';
import {tones, FormGradient, RimLight, ContactShadow} from './lighting';
import {vitals} from './motion';
import {ScreenKey} from './screenlight';

// =============================================================================
// EVIDENCE — lib/evidence.tsx. NET-NEW 2026-08-06 ("The Same Face, The Same Plate").
//
// REAL GAP, checked against ASSET_MANIFEST.md in full and confirmed independently by
// the Gate 0D critic. The shelf has an orbital eye, a seafloor ear, a ground ear, two
// aerial machines, an under-ice swimmer, a bench-science family, a records/paper
// family, a civics rules kit, an absence grammar and 13 biomes. NOTHING on it is a
// PIECE OF MEDIA, and nothing is an EMISSIVE SURFACE that can act as a light source.
// records.tsx RecordsMachine is a machine that PROCESSES records, not a record that
// gets processed. paper.tsx Sheet and bench.tsx ShortlistCard are printed stock on the
// numeric shadow contract, which is the right instinct on the wrong substance.
//
// SCOPE, corrected at Gate 0D: this asset owns the EMISSIVE FRAME, the two TARGET
// FIELDS, the SCANLINE and the PROGRESS RAIL. It does NOT own the brackets. The
// brackets are FX.tsx ScanReticle, which has shipped since 2026-07-20 and which the
// first art-direction draft re-invented without noticing. Compose from the shelf.
//
// SHAPE AND MATERIAL, and this is what keeps it off the closed flat-HUD-chip defect:
// it is a PHYSICAL EMISSIVE OBJECT, not a card. Real bezel thickness with a LIT TOP
// EDGE and a DARK BOTTOM EDGE, a screen surface that spills its own light, a contact
// shadow whenever it rests, and a slight off-axis hold. The redaction box that lands
// on it is then its exact material opposite: axis-aligned, perfectly matte, no bevel,
// no rim, casts no light, and lands FLAT WITH NO OVERSHOOT. A dead plane arriving on
// a lit dimensional object. That contrast IS the film's central visual event, and it
// is why the two are different KINDS of rectangle rather than one inside another.
//
// THE THREE STATE CHANNELS (the one-channel lesson, learned on the 07-25 horn, the
// 07-26 cone, the 07-30 glider and the 08-05 beetle):
//   1. THE TWO TARGETS   faceState / plateState, each sharp | hidden, independently.
//   2. THE SCANLINE      always crawling, on an irrational period, so the object is
//                        never a still photograph of a still photograph.
//   3. THE PROGRESS RAIL along the bottom edge. HERO WHITE, never the machine's
//                        orange: it measures the queue, which is the half no machine
//                        touched, so painting it in the machine's colour would have
//                        contradicted the film's own argument (Gate 0D caught this).
// =============================================================================

export const REDACTION = '#6B6560';   // a faintly WARM dead neutral, deliberately OFF the film's blue axis
const SCREEN_BASE = '#20364A';
const BEZEL = '#2A3442';

export type TargetState = 'sharp' | 'hidden';

export const FrameOfEvidence: React.FC<{
  x: number; y: number; f: number;
  /** overall scale */
  s?: number;
  faceState?: TargetState;
  plateState?: TargetState;
  /** 0..1 how far the queue has moved. It barely moves. */
  progress?: number;
  /** 0..1 VO emphasis reactivity */
  accent?: number;
  /** decorrelates the idle from other instances */
  phase?: number;
  /** when set, a contact shadow lands on this y */
  groundY?: number;
  /** the frame is HELD by a hand: a slight off-axis tilt */
  held?: boolean;
  /** dead and unlit, one of a stack rather than the live one on a screen */
  dead?: boolean;
  /** queue position stamped on a dead frame */
  queueTag?: string;
  id?: string;
}> = ({
  x, y, f, s = 1, faceState = 'sharp', plateState = 'sharp', progress = 0,
  accent = 0, phase = 0, groundY, held = false, dead = false, queueTag, id = 'foe',
}) => {
  const W = 520, H = 300;
  const v = vitals(f, phase, dead ? 0.25 : 1);
  const tilt = held ? -1.6 + v.tilt * 0.5 : v.tilt * 0.25;
  const bob = dead ? 0 : v.bob * 0.35;
  const t = tones(SCREEN_BASE);
  const bez = tones(BEZEL);

  // THE SCANLINE: an irrational period so the loop never re-phases and the object is
  // never identical to the frame before it. This is the always-running ambient layer
  // DISPATCH_STANDARD section 8 requires before any event is authored.
  const scanY = ((f * 1.7) % (H + 40)) - 20;
  const flick = dead ? 0 : 0.86 + 0.14 * Math.sin(f / 6.3) * Math.sin(f / 11.7);

  const face = {x: 96, y: 74, w: 132, h: 150};
  const plate = {x: 300, y: 176, w: 156, h: 62};

  return (
    <g transform={`translate(${x},${y + bob}) rotate(${tilt}) scale(${s})`}>
      {groundY !== undefined && (
        <ContactShadow cx={0} cy={(groundY - y) / s} rx={W * 0.46} ry={16} opacity={0.5} blur={9} />
      )}
      <defs>
        <FormGradient id={`${id}-bez`} t={bez} />
        <clipPath id={`${id}-screen`}>
          <rect x={-W / 2 + 16} y={-H / 2 + 16} width={W - 32} height={H - 32} rx={4} />
        </clipPath>
      </defs>

      {/* BEZEL WITH REAL THICKNESS. Lit top edge, dark bottom edge. This is what makes
          it an object rather than a card, and it is what the redaction box is not. */}
      <rect x={-W / 2 - 6} y={-H / 2 - 6} width={W + 12} height={H + 12} rx={10} fill="#0A121C" opacity={0.9} />
      <rect x={-W / 2} y={-H / 2} width={W} height={H} rx={8} fill={`url(#${id}-bez)`} />
      <rect x={-W / 2} y={-H / 2} width={W} height={4} fill="#4B5C70" opacity={0.95} />
      <rect x={-W / 2} y={H / 2 - 5} width={W} height={5} fill="#070E17" opacity={0.95} />

      {/* THE EMISSIVE SURFACE */}
      <g clipPath={`url(#${id}-screen)`}>
        <rect x={-W / 2 + 16} y={-H / 2 + 16} width={W - 32} height={H - 32}
              fill={dead ? '#141E29' : t.base} opacity={dead ? 1 : flick} />
        {!dead && (
          <rect x={-W / 2 + 16} y={-H / 2 + 16} width={W - 32} height={H - 32}
                fill={`url(#${id}-bez)`} opacity={0.18} />
        )}

        {/* THE FACE FIELD — organic-irregular, nothing parallel to anything.
            REBUILT after all three judges found the film's hero reading PLAINER than
            the bezel enclosing it, which is this channel's most repeated craft note.
            It is now form-shaded with a real terminator, a core shade, a screen-lit
            highlight from below (the key is a monitor, so the light comes up), hair
            mass, brow, nose and jaw. It is a person, not an emoji on a plate. */}
        <g transform={`translate(${-W / 2 + face.x},${-H / 2 + face.y})`} opacity={dead ? 0.5 : 1}>
          <defs>
            <linearGradient id={`${id}-skin`} x1="0" y1="1" x2="0.25" y2="0">
              <stop offset="0%" stopColor="#8A9CAC" />
              <stop offset="42%" stopColor="#6E8090" />
              <stop offset="100%" stopColor="#4A5A6A" />
            </linearGradient>
          </defs>
          {/* neck and shoulder mass, so the head is attached to a body */}
          <path d="M40,132 C40,152 30,158 18,166 L112,166 C100,158 88,152 88,132 Z" fill="#3E4E5D" />
          <path d="M8,84 C4,44 26,10 62,8 C98,6 122,36 120,78 C118,116 96,142 64,144 C32,146 12,122 8,84 Z"
                fill={`url(#${id}-skin)`} />
          {/* core shade crescent on the far side, not a bbox gradient */}
          <path d="M96,20 C120,44 122,104 88,136 C112,116 114,52 96,20 Z" fill="#3B4A59" opacity={0.75} />
          {/* hair mass, an irregular contour that matches nothing else in frame */}
          <path d="M10,66 C6,26 34,6 64,7 C96,8 122,30 120,68 C112,44 96,30 62,32 C34,34 18,44 10,66 Z"
                fill="#2B3846" />
          <path d="M22,58 C34,48 50,49 60,57" stroke="#2E3B49" strokeWidth={5} fill="none" strokeLinecap="round" />
          <path d="M74,57 C86,48 102,50 110,61" stroke="#2E3B49" strokeWidth={5} fill="none" strokeLinecap="round" />
          <ellipse cx={41} cy={74} rx={7} ry={8} fill="#26313C" />
          <ellipse cx={92} cy={74} rx={7} ry={8} fill="#26313C" />
          <ellipse cx={43} cy={71} rx={2.4} ry={2.4} fill="#C3D2DC" opacity={0.85} />
          <ellipse cx={94} cy={71} rx={2.4} ry={2.4} fill="#C3D2DC" opacity={0.85} />
          <path d="M64,80 C60,94 56,100 62,104" stroke="#3B4A59" strokeWidth={4} fill="none" strokeLinecap="round" />
          <path d="M44,116 C58,126 76,125 88,114" stroke="#2E3B49" strokeWidth={5} fill="none" strokeLinecap="round" />
          {/* the screen key, from BELOW, which is what makes it read as screen-lit */}
          <path d="M18,104 C34,132 96,134 112,102 C100,140 32,142 18,104 Z" fill="#9FD8E8" opacity={0.16} />
        </g>

        {/* THE PLATE FIELD — rectilinear, the grid's own kind of object */}
        <g transform={`translate(${-W / 2 + plate.x},${-H / 2 + plate.y})`} opacity={dead ? 0.5 : 1}>
          <rect x={0} y={0} width={plate.w} height={plate.h} rx={6} fill="#C9D4DE" />
          <rect x={5} y={5} width={plate.w - 10} height={plate.h - 10} rx={3} fill="none" stroke="#57646F" strokeWidth={2} />
          <text x={plate.w / 2} y={plate.h / 2 + 12} textAnchor="middle" fill="#26303A"
                style={{font: '700 32px "JetBrains Mono", ui-monospace, monospace', letterSpacing: 2}}>AK</text>
        </g>

        {/* THE SCANLINE, always crawling */}
        {!dead && (
          <rect x={-W / 2 + 16} y={-H / 2 + 16 + scanY * ((H - 32) / (H + 40))} width={W - 32} height={2}
                fill="#9FD8E8" opacity={0.16} />
        )}

        {/* THE REDACTION BOXES. Axis-aligned, perfectly matte, no bevel, no rim, no
            light. They are the material OPPOSITE of everything above. */}
        {faceState === 'hidden' && (
          <rect x={-W / 2 + face.x - 6} y={-H / 2 + face.y - 6} width={face.w + 12} height={face.h + 12}
                fill={REDACTION} />
        )}
        {plateState === 'hidden' && (
          <rect x={-W / 2 + plate.x - 6} y={-H / 2 + plate.y - 6} width={plate.w + 12} height={plate.h + 12}
                fill={REDACTION} />
        )}

        {/* SCREENLIGHT keys the interior off its own emitting plane */}
        {!dead && (
          <ScreenKey id={`${id}-in`} x={-W / 2 + 16} y={-H / 2 + 16} w={W - 32} h={H - 32} gain={0.5} />
        )}
      </g>

      {/* THE PROGRESS RAIL. HERO WHITE, never the machine's orange. */}
      <rect x={-W / 2 + 16} y={H / 2 - 14} width={W - 32} height={6} rx={3} fill="#0A121C" opacity={0.85} />
      <rect x={-W / 2 + 16} y={H / 2 - 14} width={Math.max(2, (W - 32) * Math.max(0, Math.min(1, progress)))}
            height={6} rx={3} fill="#E8EEF3" opacity={0.92} />

      {queueTag && (
        <text x={W / 2 - 22} y={-H / 2 + 40} textAnchor="end" fill="#7E93A6"
              style={{font: '700 22px "JetBrains Mono", ui-monospace, monospace', letterSpacing: 1}}>{queueTag}</text>
      )}

      {!dead && (
        <RimLight d={`M${-W / 2},${-H / 2} h${W} v${H} h${-W} Z`} w={2} color="#5FD2E0" opacity={0.3 + 0.3 * accent} />
      )}
    </g>
  );
};

/** A STACK of dead redacted frames. The queue, as a physical pile. */
export const FrameStack: React.FC<{
  x: number; y: number; f: number; count: number; s?: number;
}> = ({x, y, f, count, s = 0.34}) => (
  <g transform={`translate(${x},${y}) scale(${s})`}>
    {Array.from({length: Math.max(0, count) }).map((_, i) => {
      const jx = ((i * 37) % 11) - 5;
      const settle = Math.min(1, Math.max(0, (f - i * 2) / 10));
      return (
        <g key={i} transform={`translate(${jx},${-i * 26 * settle})`} opacity={settle}>
          <ContactShadow cx={0} cy={168} rx={250} ry={16} opacity={0.34} blur={9} />
          <FrameOfEvidence
            id={`stk${i}`} x={0} y={0} f={f} s={1} dead
            faceState="hidden" plateState="hidden" progress={0} phase={i * 0.7}
          />
        </g>
      );
    })}
  </g>
);
