import {z} from 'zod';

const id = z.string().regex(/^[a-z0-9][a-z0-9._-]{0,63}$/);
const hex = z.string().regex(/^#[0-9A-Fa-f]{6}$/);
const httpsUrl = z.string().url().refine((value) => value.startsWith('https://'), {
  message: 'source URLs must use HTTPS',
});
const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/).refine((value) => {
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value;
}, {message: 'date must be a real YYYY-MM-DD calendar date'});

export const dispatchPrimitiveSchema = z.enum([
  'metric',
  'comparison',
  'timeline',
  'process',
  'document',
  'quote',
  'location',
  'closing',
]);

export const dispatchAssetSchema = z.object({
  id,
  kind: z.literal('symbol'),
  glyph: z.enum(['generator', 'battery', 'document', 'pin', 'people', 'network', 'clock', 'spark']),
  alt: z.string().trim().min(4).max(120),
  credit: z.string().trim().min(2).max(120).optional(),
}).strict();

export const dispatchSourceSchema = z.object({
  id,
  label: z.string().trim().min(4).max(110),
  url: httpsUrl,
  claimIds: z.array(id).max(24),
}).strict();

export const dispatchSceneSchema = z.object({
  id,
  from: z.number().int().nonnegative(),
  dur: z.number().int().positive(),
  primitive: dispatchPrimitiveSchema,
  eyebrow: z.string().trim().min(2).max(34),
  title: z.string().trim().min(4).max(68),
  body: z.string().trim().min(8).max(118),
  primaryValue: z.string().trim().min(1).max(32).optional(),
  secondaryValue: z.string().trim().min(1).max(42).optional(),
  labels: z.array(z.string().trim().min(1).max(36)).min(1).max(4),
  sourceIds: z.array(id).max(8),
  assetId: id.optional(),
  accent: hex.optional(),
}).strict();

export const dispatchCaptionSchema = z.object({
  t: z.number().finite().nonnegative(),
  d: z.number().finite().positive().max(8),
  text: z.string().trim().min(1).max(84).refine(
    (value) => value.split(/\s+/).every((word) => word.length <= 26),
    {message: 'caption words must fit the phone-safe line width'},
  ),
}).strict();

export const dispatchWordTimingSchema = z.object({
  word: z.string().trim().min(1).max(48),
  start: z.number().finite().nonnegative(),
  end: z.number().finite().positive(),
  lineId: id,
}).strict();

export const dispatchCreditsSchema = z.object({
  frames: z.number().int().min(360).max(450),
  seconds: z.number().finite().min(12).max(15),
  music: z.string().trim().min(4).max(140),
  sources: z.array(z.string().trim().min(4).max(110)).min(1).max(6),
  sourceIds: z.array(id).max(12),
  site: z.literal('alaskaaihq.com'),
}).strict();

export const dispatchDailyInputSchema = z.object({
  schemaVersion: z.literal(2),
  episode: z.object({
    id,
    date: isoDate,
    title: z.string().trim().min(6).max(72),
    subtitle: z.string().trim().min(8).max(120),
    provenance: z.object({
      kind: z.enum(['historical_reconstruction', 'synthetic_canary']),
      notice: z.string().trim().min(12).max(180),
    }).strict(),
    motion: z.enum(['full', 'reduced']),
  }).strict(),
  fps: z.literal(30),
  total: z.number().int().min(3360).max(3900),
  safeZones: z.object({
    squareTop: z.literal(420),
    squareBottom: z.literal(1500),
    actionLeft: z.literal(72),
    actionRight: z.literal(1008),
    captionTop: z.literal(1328),
    captionBottom: z.literal(1484),
  }).strict(),
  palette: z.object({
    ink: hex,
    paper: hex,
    accent: hex,
    signal: hex,
  }).strict(),
  assets: z.array(dispatchAssetSchema).max(16),
  sources: z.array(dispatchSourceSchema).max(12),
  scenes: z.array(dispatchSceneSchema).min(6).max(16),
  captions: z.array(dispatchCaptionSchema).min(1).max(80),
  wordTimings: z.array(dispatchWordTimingSchema).min(1).max(600),
  credits: dispatchCreditsSchema,
}).strict();

export const dispatchDailySchema = dispatchDailyInputSchema.superRefine((props, context) => {
  const storyFrames = props.total - props.credits.frames;
  if (Math.round(props.credits.seconds * props.fps) !== props.credits.frames) {
    context.addIssue({code: z.ZodIssueCode.custom, path: ['credits'], message: 'credits seconds and frames disagree'});
  }

  const sceneIds = new Set<string>();
  const sourceIds = new Set(props.sources.map((source) => source.id));
  const assetIds = new Set(props.assets.map((asset) => asset.id));
  let nextFrame = 0;
  props.scenes.forEach((scene, index) => {
    if (sceneIds.has(scene.id)) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['scenes', index, 'id'], message: 'scene IDs must be unique'});
    }
    sceneIds.add(scene.id);
    if (scene.from !== nextFrame) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['scenes', index, 'from'], message: `scene must start at contiguous frame ${nextFrame}`});
    }
    nextFrame = scene.from + scene.dur;
    scene.sourceIds.forEach((sourceId) => {
      if (!sourceIds.has(sourceId)) {
        context.addIssue({code: z.ZodIssueCode.custom, path: ['scenes', index, 'sourceIds'], message: `unknown source ${sourceId}`});
      }
    });
    if (scene.assetId && !assetIds.has(scene.assetId)) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['scenes', index, 'assetId'], message: `unknown asset ${scene.assetId}`});
    }
  });
  if (nextFrame !== storyFrames) {
    context.addIssue({code: z.ZodIssueCode.custom, path: ['scenes'], message: `scenes must cover exactly ${storyFrames} story frames`});
  }

  const ids = <T extends {id: string}>(values: T[], path: string) => {
    const seen = new Set<string>();
    values.forEach((value, index) => {
      if (seen.has(value.id)) {
        context.addIssue({code: z.ZodIssueCode.custom, path: [path, index, 'id'], message: `${path} IDs must be unique`});
      }
      seen.add(value.id);
    });
  };
  ids(props.sources, 'sources');
  ids(props.assets, 'assets');

  props.credits.sourceIds.forEach((sourceId, index) => {
    if (!sourceIds.has(sourceId)) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['credits', 'sourceIds', index], message: `unknown source ${sourceId}`});
    }
  });

  const storySeconds = storyFrames / props.fps;
  let captionEnd = 0;
  props.captions.forEach((caption, index) => {
    if (caption.t + caption.d > storySeconds + 1e-6) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['captions', index], message: 'caption extends into credits'});
    }
    if (caption.t + 1e-6 < captionEnd) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['captions', index], message: 'captions must be sorted and non-overlapping'});
    }
    const rows: string[] = [];
    let row = '';
    for (const word of caption.text.split(/\s+/)) {
      const candidate = row ? `${row} ${word}` : word;
      if (candidate.length > 42 && row) {rows.push(row); row = word;} else row = candidate;
    }
    if (row) rows.push(row);
    if (rows.length > 2) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['captions', index, 'text'], message: 'caption must fit no more than two phone-safe rows'});
    }
    captionEnd = caption.t + caption.d;
  });

  let wordEnd = 0;
  props.wordTimings.forEach((word, index) => {
    if (word.end <= word.start) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['wordTimings', index], message: 'word end must be after start'});
    }
    if (word.start + 1e-6 < wordEnd) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['wordTimings', index], message: 'word timings must be sorted and non-overlapping'});
    }
    if (word.end > storySeconds + 1e-6) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['wordTimings', index], message: 'word timing extends into credits'});
    }
    wordEnd = word.end;
  });

  if (props.episode.provenance.kind === 'historical_reconstruction') {
    if (props.sources.length === 0) {
      context.addIssue({code: z.ZodIssueCode.custom, path: ['sources'], message: 'historical reconstructions require sources'});
    }
    props.scenes.forEach((scene, index) => {
      if (scene.sourceIds.length === 0) {
        context.addIssue({code: z.ZodIssueCode.custom, path: ['scenes', index, 'sourceIds'], message: 'historical scenes require source bindings'});
      }
    });
  } else if (props.sources.length !== 0 || props.credits.sourceIds.length !== 0 || props.scenes.some((scene) => scene.sourceIds.length !== 0)) {
    context.addIssue({code: z.ZodIssueCode.custom, path: ['episode', 'provenance'], message: 'synthetic canaries may not masquerade as sourced history'});
  }
});

export type DispatchDailyProps = z.infer<typeof dispatchDailySchema>;
export type DispatchScene = z.infer<typeof dispatchSceneSchema>;
export type DispatchAsset = z.infer<typeof dispatchAssetSchema>;

export const validateDispatchDailyProps = (value: unknown): DispatchDailyProps => {
  return dispatchDailySchema.parse(value);
};

export const dispatchDailyMetadata = (value: unknown) => {
  const props = validateDispatchDailyProps(value);
  return {durationInFrames: props.total, fps: props.fps, width: 1080, height: 1920};
};
