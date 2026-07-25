import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {SeismicStation} from './lib/sensors';
import {NightGrade, GradeLayer} from './lib/lighting';

// Look-dev audition sheet for the 2026-07-25 net-new hero + the NightGrade craft advance.
// Render a still before the episode uses either. Four emotional states, one frame.
export const StationLook: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: '#0C231F'}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920">
        <rect x={0} y={0} width={1080} height={1920} fill="#123A34" />
        <rect x={0} y={1080} width={1080} height={840} fill="#0C231F" />
        <SeismicStation x={270} y={620} f={f} scale={0.95} emotion="listening" groundY={0} />
        <SeismicStation x={800} y={620} f={f + 40} scale={0.95} emotion="heard" lamp={1} heading={-42} groundY={0} />
        <SeismicStation x={270} y={1400} f={f + 80} scale={0.95} emotion="straining" heading={-58} groundY={0} />
        <SeismicStation x={800} y={1400} f={f + 120} scale={0.95} emotion="missing" groundY={0} />
        <text x={270} y={760} fontFamily="Arial Black" fontSize={34} fill="#F4EDDD" textAnchor="middle">LISTENING</text>
        <text x={800} y={760} fontFamily="Arial Black" fontSize={34} fill="#F4EDDD" textAnchor="middle">HEARD</text>
        <text x={270} y={1540} fontFamily="Arial Black" fontSize={34} fill="#F4EDDD" textAnchor="middle">STRAINING</text>
        <text x={800} y={1540} fontFamily="Arial Black" fontSize={34} fill="#F4EDDD" textAnchor="middle">MISSING</text>
      </svg>
      <NightGrade f={f} sources={[{x: 800, y: 568, r: 260, intensity: 1}]} floor={0.5} />
      <GradeLayer f={f} bloom={0.2} vignette={0.42} grain={0.05} warmth={0.04} />
    </AbsoluteFill>
  );
};
