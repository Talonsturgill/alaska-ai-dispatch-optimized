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
import { GateLook } from './GateLook';
import { BenchLook } from './BenchLook';
import { Ep0730, ep0730Schema } from './Ep0730';
import { Ep0731, ep0731Schema } from './Ep0731';
import { Ep0802, ep0802Schema } from './Ep0802';
import { Ep0803, ep0803Schema } from './Ep0803';
import { Ep0805, ep0805Schema } from './Ep0805';
import { Ep0806, ep0806Schema } from './Ep0806';
import { Ep0807, ep0807Schema } from './Ep0807';
import { Ep0808, ep0808Schema } from './Ep0808';
import { Ep0809, ep0809Schema } from './Ep0809';
import { Ep0812, ep0812Schema } from './Ep0812';
import { Ep0813, ep0813Schema } from './Ep0813';
import {
  DispatchDaily,
  dispatchDailyDefaultProps,
  dispatchDailyInputSchema,
  dispatchDailyMetadata,
} from './DispatchDaily';
import compositionRegistry from '../../config/compositions.json';

const standoffSchema = z.object({
  yesCount: z.number(),
  noLabel: z.string(),
});

// DispatchDaily is the sole active 1080x1920 composition. It is a fixed parametric
// engine: story, scene primitives, captions, word timings, sources and credits all
// arrive through strict episode props. Historical authored films remain registered
// under explicit legacy/date IDs; the retired generic "Dispatch" ID stays absent.
export const RemotionRoot: React.FC = () => {
  const daily = compositionRegistry.compositions.DispatchDaily;
  return (
    <>
      <Composition
        id="DispatchDaily"
        component={DispatchDaily}
        durationInFrames={daily.default_duration_in_frames}
        fps={daily.fps}
        width={daily.width}
        height={daily.height}
        schema={dispatchDailyInputSchema}
        defaultProps={dispatchDailyDefaultProps}
        calculateMetadata={({props}) => dispatchDailyMetadata(props)}
      />
      <Composition
        id="Dispatch0812"
        component={Ep0812}
        durationInFrames={3630}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0812Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 3630,
        })}
      />
      <Composition
        id="Dispatch0809"
        component={Ep0809}
        durationInFrames={3681}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0809Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 3681,
        })}
      />
      <Composition
        id="Dispatch0808"
        component={Ep0808}
        durationInFrames={3786}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0808Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 3786,
        })}
      />
      <Composition
        id="Dispatch0807"
        component={Ep0807}
        durationInFrames={4200}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0807Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 4200,
        })}
      />
      <Composition
        id="Dispatch0806"
        component={Ep0806}
        durationInFrames={3690}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0806Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 3690,
        })}
      />
      <Composition
        id="Dispatch0805"
        component={Ep0805}
        durationInFrames={2664}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0805Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 2664,
        })}
      />
      <Composition
        id="Dispatch0803"
        component={Ep0803}
        durationInFrames={2800}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0803Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as { total?: number }).total ?? 2800,
        })}
      />
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
        id="LegacyDispatch0726"
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
        id="BenchLook"
        component={BenchLook}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
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
        id="GateLook"
        component={GateLook}
        durationInFrames={120}
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
      <Composition
        id="Dispatch0731"
        component={Ep0731}
        durationInFrames={2799}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0731Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as {total?: number}).total ?? 2799,
        })}
      />
      <Composition
        id="Dispatch0802"
        component={Ep0802}
        durationInFrames={2964}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0802Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as {total?: number}).total ?? 2964,
        })}
      />
      <Composition
        id="LegacyDispatch0813"
        component={Ep0813}
        durationInFrames={3900}
        fps={30}
        width={1080}
        height={1920}
        schema={ep0813Schema}
        defaultProps={{ captions: [] }}
        calculateMetadata={({ props }) => ({
          durationInFrames: (props as {total?: number}).total ?? 3900,
        })}
      />
    </>
  );
};
