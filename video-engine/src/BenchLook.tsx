import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {AshReader, ShortlistCard, DistanceCalipers, CoreColumn, AshCrumbs, RHYOLITE} from './lib/bench';
import {MaterialDefs} from './lib/materials';

// =============================================================================
// BenchLook — the look-dev audition sheet for the 2026-08-01 bench family.
//
// House practice since GateLook (2026-07-31), whose 0.28-SCALE LEGIBILITY STRIP caught
// three real defects on its first pass before a single scene was authored. Gate 0D called
// the absence of this harness out, and it was right: the ShortlistCard name overflow is
// exactly the class of defect this strip exists to catch, and it shipped in pass 1 because
// nothing rendered the card at real size with real words in it.
//
// Every state that appears in the film appears here, at full size AND at 0.28, which is
// roughly what a band label survives at once the camera pulls back to all eight columns.
// =============================================================================

const BG = '#0e1418';
const LABEL = '#8fa3ad';

const Cap: React.FC<{x: number; y: number; children: React.ReactNode}> = ({x, y, children}) => (
  <text x={x} y={y} fontSize={17} fontFamily="JetBrains Mono, ui-monospace, monospace"
        fill={LABEL} textAnchor="middle">{children}</text>
);

export const BenchLook: React.FC = () => {
  const f = useCurrentFrame();
  const REAL = ['KATMAI', 'FISHER CALDERA', 'EMMONS LAKE'];   // the film's actual words
  return (
    <AbsoluteFill style={{backgroundColor: BG}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920">
        <MaterialDefs />

        {/* ---- ROW 1: the hero in all three emotions, lamp off then on ---- */}
        <Cap x={180} y={70}>reading / lamp off</Cap>
        <g transform="translate(180,90) scale(0.52)"><AshReader x={0} y={0} f={f} emotion="reading" feed={0.35} lamp={0} phase={0} /></g>
        <Cap x={540} y={70}>straining / lamp off</Cap>
        <g transform="translate(540,90) scale(0.52)"><AshReader x={0} y={0} f={f} emotion="straining" feed={0.7} lamp={0} phase={1.2} /></g>
        <Cap x={900} y={70}>settled / lamp ON (match)</Cap>
        <g transform="translate(900,90) scale(0.52)"><AshReader x={0} y={0} f={f} emotion="settled" feed={1} lamp={1} lampFill={RHYOLITE} phase={2.4} /></g>

        {/* ---- ROW 2: THE CARD, with the film's REAL words. The pass-1 overflow bug. ---- */}
        <Cap x={540} y={470}>ShortlistCard, real words, 1 name then 3 (the width IS the tell)</Cap>
        <g transform="translate(250,540)"><ShortlistCard x={0} y={0} f={f} names={['KATMAI']} out={1} /></g>
        <g transform="translate(720,540)"><ShortlistCard x={0} y={0} f={f} names={REAL} out={1} /></g>
        <Cap x={540} y={640}>same two, MATCHED (accent licensed)</Cap>
        <g transform="translate(250,700)"><ShortlistCard x={0} y={0} f={f} names={['KATMAI']} out={1} matched accentFill={RHYOLITE} /></g>
        <g transform="translate(720,700)"><ShortlistCard x={0} y={0} f={f} names={REAL} out={1} matched accentFill={RHYOLITE} /></g>

        {/* ---- ROW 3: the second instrument ---- */}
        <Cap x={230} y={840}>DistanceCalipers, span 0.15</Cap>
        <g transform="translate(230,900) scale(0.8)"><DistanceCalipers x={0} y={0} f={f} span={0.15} handIn={1} /></g>
        <Cap x={620} y={840}>span 0.85 + label</Cap>
        <g transform="translate(640,900) scale(0.8)"><DistanceCalipers x={0} y={0} f={f} span={0.85} handIn={1} label="NEAREST" /></g>

        {/* ---- ROW 4: CoreColumn — named bands DEAD STILL vs unnamed restless ---- */}
        <Cap x={540} y={1120}>CoreColumn: named bands hold still, unnamed breathe, mark = the open-loop band</Cap>
        {[0, 1, 2].map((i) => (
          <g key={i} transform={`translate(${300 + i * 240},1620) scale(0.62)`}>
            <CoreColumn
              x={0} y={0} f={f} h={700} w={80} phase={i * 1.7} accentFill={RHYOLITE} labelScale={1}
              bands={[
                {at: 0.12, lit: 0.9},
                {at: 0.26, lit: 1, named: i === 0 ? 'KATMAI' : undefined},
                {at: 0.40, lit: 0.7, mark: i === 1},
                {at: 0.55, lit: 1, named: i === 2 ? 'EMMONS LAKE' : undefined},
                {at: 0.68, lit: 0.6},
                {at: 0.82, lit: 0.95, named: i === 1 ? 'FISHER CALDERA' : undefined},
                {at: 0.93, lit: 0.5},
              ]}
            />
          </g>
        ))}

        {/* ---- THE 0.28 LEGIBILITY STRIP: everything at the size it survives a pull-back ---- */}
        <rect x={0} y={1690} width={1080} height={230} fill="#070a0c" />
        <Cap x={540} y={1718}>0.28 SCALE LEGIBILITY STRIP — if a word dies here it dies in the poster frame</Cap>
        <g transform="translate(150,1800) scale(0.28)"><AshReader x={0} y={0} f={f} emotion="settled" lamp={1} lampFill={RHYOLITE} /></g>
        <g transform="translate(430,1790) scale(0.28)"><ShortlistCard x={0} y={0} f={f} names={REAL} out={1} matched accentFill={RHYOLITE} /></g>
        <g transform="translate(700,1880) scale(0.28)">
          <CoreColumn x={0} y={0} f={f} h={620} w={80} accentFill={RHYOLITE} labelScale={1.9}
            bands={[{at: 0.2, lit: 1, named: 'KATMAI'}, {at: 0.5, lit: 0.8}, {at: 0.8, lit: 1, named: 'EMMONS LAKE'}]} />
        </g>
        <g transform="translate(930,1800) scale(0.28)"><DistanceCalipers x={0} y={0} f={f} span={0.6} handIn={1} /></g>

        <AshCrumbs f={f} count={12} opacity={0.22} />
      </svg>
    </AbsoluteFill>
  );
};
