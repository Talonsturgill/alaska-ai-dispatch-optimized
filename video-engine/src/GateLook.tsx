import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Gate, ThresholdGate} from './lib/civics';
import {DayGrade} from './lib/lighting';

// =============================================================================
// GateLook — look-dev for lib/civics.tsx (2026-07-31).
//
// THIS HARNESS EXISTS TO RUN ONE TEST BEFORE ANY SCENE IS AUTHORED: can a viewer
// tell, in under a second at phone size, that one scale plate has gradations and
// another does not, and that one clock has hands and another does not? That
// difference IS the film's argument, and the shelf has failed exactly this class
// of legibility three times (the 07-25 SeismicStation horn that read as a
// lollipop, the 07-26 TaperedCone that read as a satellite dish, the 07-30 ice
// keels that read as bunting). Catching it here costs a still. Catching it at the
// turn costs a redesign.
//
// The two ThresholdGates below are the film's turn frame verbatim, so this
// look-dev IS the shot test.
// =============================================================================

export const GateLook: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: '#c3d3de'}}>
      <svg viewBox="0 0 1080 1920" width="1080" height="1920">
        {/* ---- the three CONDITIONAL gates, each carrying its own printed test ---- */}
        <Gate f={f} x={300} y={300} condition="DO YOU HAVE GAS" source="CHUGACH ELECTRIC"
          verdict="block" phase={0} scale={0.62} />
        <Gate f={f} x={780} y={300} condition="IS THERE POWER HERE" source="AIR FORCE SOLICITATION"
          verdict="asking" phase={0.31} scale={0.62} />
        <Gate f={f} x={540} y={620} condition="SHOW UTILITY CAPACITY" source="AO 2026-27"
          verdict="pass" phase={0.68} scale={0.62} />

        {/* ---- THE TURN FRAME: one rig, two configurations ---- */}
        {/* NEW YORK: gradations present, clock has hands, a threshold actually fired */}
        <ThresholdGate f={f} x={300} y={1180} label="NEW YORK"
          boom={1} cut={1} cutW={120} cutLabel="BIGGEST SITES ONLY" hands={1} lamp={1}
          scale={0.6} phase={0.12} />

        {/* ALASKA: same rig, blank plate, handless clock, lamp dark */}
        <ThresholdGate f={f} x={780} y={1180} label="ALASKA"
          boom={1} cut={0} cutW={120} hands={0} lamp={0} scale={0.6} phase={0.44} />

        {/* ---- thumbnail legibility strip: the same pair at feed size ---- */}
        <ThresholdGate f={f} x={330} y={1660} boom={1} cut={1} cutW={120} hands={1} lamp={1}
          scale={0.28} phase={0.7} />
        <ThresholdGate f={f} x={720} y={1660} boom={1} cut={0} cutW={120} hands={0} lamp={0}
          scale={0.28} phase={0.9} />
        <text x={540} y={1810} textAnchor="middle" fontFamily="'JetBrains Mono', monospace"
          fontSize={26} fontWeight={700} fill="#16202a">
          same rig at 0.28 scale. can you still tell them apart
        </text>
      </svg>
      <DayGrade f={f} amount={0.85} floor={0.55} haze={0.3} sunX={840} sunY={210} sunIntensity={0.5} />
    </AbsoluteFill>
  );
};
