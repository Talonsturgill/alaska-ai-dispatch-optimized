import React from 'react';
import {Ep0729, ep0729Schema} from './Ep0729';
import { Composition } from 'remotion';
import { Episode, episodeSchema } from './Episode';
import { Standoff } from './Standoff';
import { FaunaShowcase } from './FaunaShowcase';
import { CraftShowcase } from './CraftShowcase';
import { TwentyFiveD, BorealFlat } from './TwentyFiveD';
import { Nenana3D } from './Nenana3D';
import { BiomeShowcase } from './BiomeShowcase';
import { BiomeShowcase2 } from './BiomeShowcase2';
import { BiomeShowcase3 } from './BiomeShowcase3';
import { PropsShowcase } from './PropsShowcase';
import { FaunaShowcase2 } from './FaunaShowcase2';
import { FaunaShowcase3 } from './FaunaShowcase3';
import { FaunaShowcase4 } from './FaunaShowcase4';
import { FaunaShowcase5 } from './FaunaShowcase5';
import { FishShowcase } from './FishShowcase';
import { CityShowcase } from './CityShowcase';
import { StationLook } from './StationLook';
import { MaterialShowcase } from './MaterialShowcase';
import { z } from 'zod';
import { UnderIceLook } from './UnderIceLook';
import { Ep0730, ep0730Schema } from './Ep0730';

const standoffSchema = z.object({
  yesCount: z.number(),
  noLabel: z.string(),
});

// 1080x1920 (9:16), 30fps. "Dispatch" = the full episode timeline (6 scenes wired
// to the VO line anchors, captions overlaid). "Standoff" kept for look-dev.
// 2026-07-18: retimed to the Gemini-narrated VO (out/dispatch/vo_lines.json,
// 67.52s = 2026 frames @ 30fps incl. tail; switched off the cloned voice per
// owner). DEFAULT_BOUNDS below is the fallback; episode_props.json (from
// scripts/build_scenes.py) carries the authoritative per-run scene timing.
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Dispatch0729"
        component={Ep0729}
        durationInFrames={1830}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0729Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as {total?: number}).total ?? 1830,
        })}
      />
      <Composition
        id="Dispatch"
        component={Episode}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1920}
        schema={episodeSchema}
        defaultProps={{ captions: [] }}
        // Duration follows the VO: read `total` (frames) from episode_props.json so the
        // tail (the S6 button) is never truncated when the narration retimes the piece.
        // Prior bug (2026-07-20): hardcoded 1561 cut the last ~4.5s of a 1699f render.
        // 2026-07-22: default bumped to 1800 (60.0s @ 30fps) to match this run's storyboard.
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 1800,
        })}
      />
      <Composition
        id="StationLook"
        component={StationLook}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Standoff"
        component={Standoff}
        durationInFrames={240}
        fps={30}
        width={1080}
        height={1920}
        schema={standoffSchema}
        defaultProps={{ yesCount: 500, noLabel: 'fewer than a dozen in favor' }}
      />
      <Composition
        id="CraftShowcase"
        component={CraftShowcase}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="FaunaShowcase"
        component={FaunaShowcase}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="TwentyFiveD"
        component={TwentyFiveD}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Nenana3D"
        component={Nenana3D}
        durationInFrames={190}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="BiomeShowcase"
        component={BiomeShowcase}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="BiomeShowcase2"
        component={BiomeShowcase2}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="BiomeShowcase3"
        component={BiomeShowcase3}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="PropsShowcase"
        component={PropsShowcase}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="FaunaShowcase2"
        component={FaunaShowcase2}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="FaunaShowcase3"
        component={FaunaShowcase3}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="FaunaShowcase4"
        component={FaunaShowcase4}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="MaterialShowcase"
        component={MaterialShowcase}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="FaunaShowcase5"
        component={FaunaShowcase5}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="FishShowcase"
        component={FishShowcase}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="CityShowcase"
        component={CityShowcase}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="BorealFlat"
        component={BorealFlat}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="UnderIceLook"
        component={UnderIceLook}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
      />
      <Composition
        id="Dispatch0730"
        component={Ep0730}
        durationInFrames={2001}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0730Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as {total?: number}).total ?? 2001,
        })}
      />
    </>
  );
};
