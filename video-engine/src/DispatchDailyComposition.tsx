import React from 'react';
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {EndCredits} from './lib/EndCredits';
import type {DispatchAsset, DispatchDailyProps, DispatchScene} from './DispatchDailySchema';

const BOLD = 'Archivo, Arial Black, Arial, sans-serif';
const MONO = 'JetBrains Mono, Consolas, monospace';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const fitSize = (text: string, width: number, ideal: number, floor: number) =>
  Math.max(floor, Math.min(ideal, width / Math.max(1, text.length * 0.57)));

const hashUnit = (value: string, index: number) => {
  let hash = 2166136261 ^ index;
  for (let i = 0; i < value.length; i++) {
    hash ^= value.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 0xffffffff;
};

const Symbol: React.FC<{asset?: DispatchAsset; accent: string; ink: string}> = ({asset, accent, ink}) => {
  const glyph = asset?.glyph ?? 'spark';
  if (glyph === 'document') {
    return <><rect x={420} y={735} width={240} height={300} rx={18} fill="#F7F0E3" stroke={ink} strokeWidth={8}/>{[0, 1, 2, 3].map((i) => <rect key={i} x={458} y={800 + i * 48} width={164 - i * 12} height={10} rx={5} fill={i === 0 ? accent : ink} opacity={i === 0 ? 1 : 0.32}/>)}</>;
  }
  if (glyph === 'battery') {
    return <><rect x={390} y={790} width={300} height={190} rx={28} fill="#F7F0E3" stroke={ink} strokeWidth={9}/><rect x={690} y={850} width={24} height={70} rx={6} fill={ink}/><rect x={430} y={830} width={180} height={110} rx={12} fill={accent}/><path d="M535 842l-42 58h40l-18 44 66-70h-44l18-32z" fill="#fff"/></>;
  }
  if (glyph === 'generator') {
    return <><rect x={350} y={780} width={380} height={220} rx={26} fill="#F7F0E3" stroke={ink} strokeWidth={9}/><circle cx={470} cy={890} r={68} fill={accent} stroke={ink} strokeWidth={8}/><circle cx={470} cy={890} r={20} fill="#fff"/><rect x={575} y={825} width={110} height={42} rx={8} fill={ink}/><rect x={575} y={886} width={86} height={18} rx={9} fill={accent}/><path d="M390 1000v42M690 1000v42" stroke={ink} strokeWidth={16} strokeLinecap="round"/></>;
  }
  if (glyph === 'pin') {
    return <><path d="M540 1038s-142-137-142-243c0-89 64-153 142-153s142 64 142 153c0 106-142 243-142 243z" fill={accent} stroke={ink} strokeWidth={9}/><circle cx={540} cy={795} r={48} fill="#fff" stroke={ink} strokeWidth={8}/></>;
  }
  if (glyph === 'people') {
    return <>{[-130, 0, 130].map((x, i) => <g key={i} transform={`translate(${x} ${i === 1 ? -34 : 0})`}><circle cx={540} cy={790} r={54} fill={i === 1 ? accent : '#F7F0E3'} stroke={ink} strokeWidth={8}/><path d="M445 1030c8-116 53-174 95-174s87 58 95 174" fill={i === 1 ? accent : '#F7F0E3'} stroke={ink} strokeWidth={8}/></g>)}</>;
  }
  if (glyph === 'network') {
    const nodes = [[390, 820], [540, 720], [690, 820], [450, 1000], [630, 1000]];
    return <><path d="M390 820L540 720l150 100-60 180H450zM390 820l240 180M690 820L450 1000" fill="none" stroke={ink} strokeWidth={8} opacity={0.42}/>{nodes.map(([x, y], i) => <circle key={i} cx={x} cy={y} r={i === 1 ? 34 : 26} fill={i === 1 ? accent : '#F7F0E3'} stroke={ink} strokeWidth={7}/>)}</>;
  }
  if (glyph === 'clock') {
    return <><circle cx={540} cy={860} r={170} fill="#F7F0E3" stroke={ink} strokeWidth={10}/><path d="M540 860V746M540 860l94 62" stroke={accent} strokeWidth={18} strokeLinecap="round"/><circle cx={540} cy={860} r={16} fill={ink}/></>;
  }
  return <><circle cx={540} cy={860} r={178} fill={accent} opacity={0.16}/><path d="M540 664l38 135 130-56-87 111 124 66-142-6 14 142-77-120-77 120 14-142-142 6 124-66-87-111 130 56z" fill={accent} stroke={ink} strokeWidth={7}/></>;
};

const MetricVisual: React.FC<{scene: DispatchScene; progress: number; accent: string; ink: string}> = ({scene, progress, accent, ink}) => (
  <g>
    <text x={540} y={904} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={fitSize(scene.primaryValue ?? '—', 760, 164, 70)} fill={ink}>{scene.primaryValue ?? '—'}</text>
    <rect x={220} y={980} width={640} height={30} rx={15} fill={ink} opacity={0.12}/>
    <rect x={220} y={980} width={640 * progress} height={30} rx={15} fill={accent}/>
    {scene.secondaryValue && <text x={540} y={1074} textAnchor="middle" fontFamily={MONO} fontSize={28} fill={ink} opacity={0.72}>{scene.secondaryValue}</text>}
  </g>
);

const ComparisonVisual: React.FC<{scene: DispatchScene; progress: number; accent: string; ink: string}> = ({scene, progress, accent, ink}) => (
  <g>
    {[0, 1].map((i) => {
      const x = i === 0 ? 160 : 555;
      const label = scene.labels[i] ?? `SIDE ${i + 1}`;
      return <g key={i} transform={`translate(0 ${(1 - progress) * (i === 0 ? 50 : -50)})`}>
        <rect x={x} y={760} width={365} height={310} rx={28} fill={i === 0 ? '#F7F0E3' : accent} stroke={ink} strokeWidth={7}/>
        <text x={x + 182.5} y={856} textAnchor="middle" fontFamily={MONO} fontWeight={800} fontSize={fitSize(label, 300, 30, 18)} fill={ink}>{label.toUpperCase()}</text>
        <text x={x + 182.5} y={976} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={fitSize(i === 0 ? scene.primaryValue ?? 'A' : scene.secondaryValue ?? 'B', 300, 76, 34)} fill={ink}>{i === 0 ? scene.primaryValue ?? 'A' : scene.secondaryValue ?? 'B'}</text>
      </g>;
    })}
  </g>
);

const TimelineVisual: React.FC<{scene: DispatchScene; progress: number; accent: string; ink: string}> = ({scene, progress, accent, ink}) => {
  const labels = scene.labels.slice(0, 4);
  return <g><rect x={190} y={884} width={700} height={12} rx={6} fill={ink} opacity={0.18}/><rect x={190} y={884} width={700 * progress} height={12} rx={6} fill={accent}/>{labels.map((label, index) => {const x = labels.length === 1 ? 540 : 190 + index * (700 / (labels.length - 1)); const active = progress >= index / Math.max(1, labels.length - 1); return <g key={label}><circle cx={x} cy={890} r={active ? 26 : 18} fill={active ? accent : '#F7F0E3'} stroke={ink} strokeWidth={6}/><text x={x} y={968 + (index % 2) * 46} textAnchor="middle" fontFamily={MONO} fontWeight={800} fontSize={fitSize(label, 210, 24, 16)} fill={ink}>{label.toUpperCase()}</text></g>;})}</g>;
};

const ProcessVisual: React.FC<{scene: DispatchScene; progress: number; accent: string; ink: string}> = ({scene, progress, accent, ink}) => (
  <g>{scene.labels.slice(0, 4).map((label, index, labels) => {const width = 700 / labels.length; const x = 190 + index * width; const active = progress >= (index + 0.35) / labels.length; return <g key={label}><rect x={x + 8} y={790 + (index % 2) * 70} width={width - 16} height={180} rx={24} fill={active ? accent : '#F7F0E3'} stroke={ink} strokeWidth={6}/><text x={x + width / 2} y={888 + (index % 2) * 70} textAnchor="middle" fontFamily={MONO} fontWeight={900} fontSize={fitSize(label, width - 40, 24, 15)} fill={ink}>{label.toUpperCase()}</text>{index < labels.length - 1 && <path d={`M${x + width - 2} ${880 + (index % 2) * 70}l30 ${index % 2 === 0 ? 70 : -70}`} stroke={ink} strokeWidth={6} fill="none"/>}</g>;})}</g>
);

const DocumentVisual: React.FC<{scene: DispatchScene; progress: number; accent: string; ink: string}> = ({scene, progress, accent, ink}) => (
  <g transform={`rotate(${(1 - progress) * -3} 540 900)`}><rect x={260} y={690} width={560} height={430} rx={18} fill="#F7F0E3" stroke={ink} strokeWidth={8}/><rect x={306} y={748} width={280 * progress} height={18} rx={9} fill={accent}/>{scene.labels.slice(0, 4).map((label, i) => <g key={label}><text x={310} y={834 + i * 66} fontFamily={MONO} fontWeight={800} fontSize={fitSize(label, 420, 27, 18)} fill={ink}>{label.toUpperCase()}</text><circle cx={760} cy={824 + i * 66} r={13} fill={i < Math.ceil(progress * scene.labels.length) ? accent : 'none'} stroke={ink} strokeWidth={4}/></g>)}</g>
);

const QuoteVisual: React.FC<{scene: DispatchScene; progress: number; accent: string; ink: string}> = ({scene, progress, accent, ink}) => (
  <g opacity={progress}><text x={170} y={780} fontFamily={BOLD} fontWeight={900} fontSize={190} fill={accent}>“</text><text x={540} y={880} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={fitSize(scene.primaryValue ?? scene.labels[0], 680, 68, 34)} fill={ink}>{scene.primaryValue ?? scene.labels[0]}</text><path d="M300 968H780" stroke={accent} strokeWidth={10} strokeLinecap="round"/><text x={540} y={1042} textAnchor="middle" fontFamily={MONO} fontWeight={800} fontSize={fitSize(scene.secondaryValue ?? scene.labels[scene.labels.length - 1] ?? '', 700, 28, 18)} fill={ink}>{(scene.secondaryValue ?? scene.labels[scene.labels.length - 1] ?? '').toUpperCase()}</text></g>
);

const SceneVisual: React.FC<{scene: DispatchScene; asset?: DispatchAsset; motion: 'full' | 'reduced'; palette: DispatchDailyProps['palette']}> = ({scene, asset, motion, palette}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const enter = motion === 'reduced' ? 1 : spring({frame, fps, config: {damping: 18, stiffness: 125, mass: 0.8}});
  const travel = motion === 'reduced' ? 1 : interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], clamp);
  const accent = scene.accent ?? palette.accent;
  const source = scene.sourceIds.length ? `SOURCE ${scene.sourceIds.join(' · ')}` : 'SYNTHETIC CANARY · NO FACTUAL CLAIMS';
  let visual: React.ReactNode;
  if (scene.primitive === 'metric') visual = <MetricVisual scene={scene} progress={travel} accent={accent} ink={palette.ink}/>;
  else if (scene.primitive === 'comparison') visual = <ComparisonVisual scene={scene} progress={enter} accent={accent} ink={palette.ink}/>;
  else if (scene.primitive === 'timeline') visual = <TimelineVisual scene={scene} progress={travel} accent={accent} ink={palette.ink}/>;
  else if (scene.primitive === 'process') visual = <ProcessVisual scene={scene} progress={travel} accent={accent} ink={palette.ink}/>;
  else if (scene.primitive === 'document') visual = <DocumentVisual scene={scene} progress={enter} accent={accent} ink={palette.ink}/>;
  else if (scene.primitive === 'quote') visual = <QuoteVisual scene={scene} progress={enter} accent={accent} ink={palette.ink}/>;
  else visual = <Symbol asset={asset} accent={accent} ink={palette.ink}/>;
  return <AbsoluteFill role="img" aria-label={`${scene.eyebrow}. ${scene.title}. ${scene.body}`}>
    <svg width="1080" height="1920" viewBox="0 0 1080 1920">
      <g transform={`translate(0 ${(1 - enter) * 32})`} opacity={enter}>
        <text x={540} y={520} textAnchor="middle" fontFamily={MONO} fontWeight={900} fontSize={25} letterSpacing={3} fill={accent}>{scene.eyebrow.toUpperCase()}</text>
        <text x={540} y={608} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={fitSize(scene.title, 880, 66, 36)} fill={palette.ink}>{scene.title}</text>
        <foreignObject x={150} y={632} width={780} height={108}>
          <div style={{fontFamily: BOLD, fontWeight: 700, color: palette.ink, fontSize: 28, lineHeight: 1.25, textAlign: 'center'}}>{scene.body}</div>
        </foreignObject>
        {visual}
        <rect x={150} y={1228} width={780} height={62} rx={31} fill={palette.ink} opacity={0.08}/>
        <text x={540} y={1269} textAnchor="middle" fontFamily={MONO} fontWeight={800} fontSize={fitSize(source, 700, 21, 14)} fill={palette.ink} opacity={0.72}>{source}</text>
      </g>
    </svg>
  </AbsoluteFill>;
};

const Captions: React.FC<{cues: DispatchDailyProps['captions']; palette: DispatchDailyProps['palette']; top: number; bottom: number}> = ({cues, palette, top, bottom}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = frame / fps;
  const cue = cues.find((item) => seconds >= item.t && seconds < item.t + item.d);
  if (!cue) return null;
  const words = cue.text.split(/\s+/);
  const rows: string[] = [];
  let row = '';
  for (const word of words) {
    const candidate = row ? `${row} ${word}` : word;
    if (candidate.length > 42 && row) {rows.push(row); row = word;} else row = candidate;
  }
  if (row) rows.push(row);
  const shown = rows.slice(0, 2);
  const center = (top + bottom) / 2;
  return <AbsoluteFill aria-live="off" aria-label={`Caption: ${cue.text}`}>
    <svg width="1080" height="1920" viewBox="0 0 1080 1920">
      <rect x={54} y={top} width={972} height={bottom - top} rx={28} fill={palette.ink} opacity={0.92}/>
      {shown.map((text, index) => <text key={text} x={540} y={center + (index - (shown.length - 1) / 2) * 50 + 14} textAnchor="middle" fontFamily={BOLD} fontWeight={900} fontSize={40} fill={palette.paper}>{text}</text>)}
    </svg>
  </AbsoluteFill>;
};

const Background: React.FC<{props: DispatchDailyProps}> = ({props}) => {
  const frame = useCurrentFrame();
  const reduced = props.episode.motion === 'reduced';
  const shift = reduced ? 0 : Math.sin(frame / 80) * 28;
  return <AbsoluteFill>
    <svg width="1080" height="1920" viewBox="0 0 1080 1920">
      <defs><linearGradient id="dispatch-paper" x1="0" y1="0" x2="1" y2="1"><stop stopColor={props.palette.paper}/><stop offset="1" stopColor="#D8D2C4"/></linearGradient></defs>
      <rect width={1080} height={1920} fill="url(#dispatch-paper)"/>
      {[0, 1, 2, 3, 4].map((index) => {const x = 90 + hashUnit(props.episode.id, index) * 900 + shift * (index % 2 ? 1 : -1); const y = 260 + hashUnit(props.episode.date, index) * 1300; return <circle key={index} cx={x} cy={y} r={90 + index * 34} fill={index % 2 ? props.palette.accent : props.palette.signal} opacity={0.035}/>;})}
      <rect x={24} y={420} width={8} height={1080} rx={4} fill={props.palette.ink} opacity={0.14}/>
      <rect x={24} y={420} width={8} height={1080 * (frame / Math.max(1, props.total))} rx={4} fill={props.palette.accent}/>
      <text x={72} y={120} fontFamily={MONO} fontWeight={900} fontSize={29} letterSpacing={3} fill={props.palette.ink}>ALASKA.AI · DISPATCH</text>
      <text x={1008} y={120} textAnchor="end" fontFamily={MONO} fontWeight={800} fontSize={24} fill={props.palette.ink} opacity={0.64}>{props.episode.date}</text>
      <text x={540} y={330} textAnchor="middle" fontFamily={MONO} fontWeight={800} fontSize={fitSize(props.episode.provenance.notice, 850, 20, 13)} fill={props.palette.ink} opacity={0.56}>{props.episode.provenance.notice.toUpperCase()}</text>
    </svg>
  </AbsoluteFill>;
};

export const DispatchDailyComposition: React.FC<DispatchDailyProps> = (props) => {
  const assets = new Map(props.assets.map((asset) => [asset.id, asset]));
  const storyFrames = props.total - props.credits.frames;
  return <AbsoluteFill style={{backgroundColor: props.palette.paper}}>
    <Background props={props}/>
    {props.scenes.map((scene) => <Sequence key={scene.id} name={scene.id} from={scene.from} durationInFrames={scene.dur}><SceneVisual scene={scene} asset={scene.assetId ? assets.get(scene.assetId) : undefined} motion={props.episode.motion} palette={props.palette}/></Sequence>)}
    <Sequence from={0} durationInFrames={storyFrames} name="ACCESSIBLE_CAPTIONS"><Captions cues={props.captions} palette={props.palette} top={props.safeZones.captionTop} bottom={props.safeZones.captionBottom}/></Sequence>
    <Sequence from={storyFrames} durationInFrames={props.credits.frames} name="CREDITS">
      <EndCredits data={props.credits} durationInFrames={props.credits.frames}/>
    </Sequence>
  </AbsoluteFill>;
};
