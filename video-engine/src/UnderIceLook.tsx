import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {IceGlider, UnderIceBG, AcousticSource} from './lib/underice';
import {NightGrade} from './lib/lighting';

// Look-dev for the net-new under-ice family (2026-07-30): the five glider
// emotional states, the submerged biome, and the moored acoustic source.
// Render a still of this BEFORE any episode scene uses the assets.
const cap = (x: number, y: number, t: string) => (
  <text x={x} y={y} textAnchor="middle" fontFamily="Arial, sans-serif" fontWeight={800} fontSize={24} fill="#cfe9f5">{t}</text>
);

export const UnderIceLook: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: '#081a2e'}}>
      <svg width={1080} height={1920} viewBox="0 0 1080 1920" style={{position: 'absolute'}}>
        {/* the biome, with a lead of daylight overhead */}
        <UnderIceBG f={f} iceY={210} lead={0.7} parallax={0.3} />

        {/* the five emotional states, top to bottom */}
        <g transform="translate(0,80)">
          <IceGlider x={300} y={470} f={f} scale={0.62} emotion="gliding" />
          {cap(300, 560, 'gliding')}

          <IceGlider x={780} y={470} f={f} scale={0.62} emotion="listening" ping={0.9} pingFrom={205} />
          {cap(780, 560, 'listening + ping')}

          <IceGlider x={300} y={720} f={f} scale={0.62} emotion="hibernating" rime={0.8} />
          {cap(300, 810, 'hibernating + rime')}

          <IceGlider x={780} y={720} f={f} scale={0.62} emotion="lost" />
          {cap(780, 810, 'lost')}

          <IceGlider x={540} y={980} f={f} scale={0.72} emotion="fixed" eyeLock={1} accent={0.6} />
          {cap(540, 1080, 'fixed (eye clamped)')}
        </g>

        {/* the moored source it listens for, standing on the seafloor */}
        <AcousticSource x={250} y={1560} f={f} scale={1.1} pulse={0.9} floorY={1250} />
        {cap(250, 1660, 'AcousticSource (emitting)')}
        <AcousticSource x={620} y={1560} f={f} scale={1.1} pulse={0} floorY={1250} />
        {cap(620, 1660, 'AcousticSource (silent)')}

        {/* hero scale, for the signature-shot read */}
        <IceGlider x={880} y={1500} f={f} scale={1.0} emotion="fixed" eyeLock={0.8} />
        {cap(880, 1660, 'hero scale')}
      </svg>
      <NightGrade
        f={f} color="#0f3a52" amount={0.3} floor={0.16} horizon={0.1}
        sources={[{x: 540, y: 250, r: 320, color: '#ffe9b8', intensity: 0.5}]}
      />

    </AbsoluteFill>
  );
};
