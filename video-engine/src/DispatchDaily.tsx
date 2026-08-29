import React from 'react';
import fixture0812 from '../fixtures/dispatch-2026-08-12.json';
import fixture0813 from '../fixtures/dispatch-2026-08-13.json';
import fixture0828 from '../fixtures/dispatch-2026-08-28.json';
import {DispatchDailyComposition} from './DispatchDailyComposition';
import {
  dispatchDailyMetadata,
  dispatchDailyInputSchema,
  dispatchDailySchema,
  type DispatchDailyProps,
  validateDispatchDailyProps,
} from './DispatchDailySchema';

/**
 * Fixed parametric Dispatch engine.
 *
 * Daily work changes only episode_props.json. All accepted story, timing,
 * source, credit, palette and visual choices are declared in that JSON and
 * parsed again inside this component. Unknown or inconsistent data throws
 * before a frame can render.
 */
export const DISPATCH_DAILY_FIXTURES = {
  '2026-08-12': validateDispatchDailyProps(fixture0812),
  '2026-08-13': validateDispatchDailyProps(fixture0813),
  '2026-08-28': validateDispatchDailyProps(fixture0828),
} as const;

export const dispatchDailyDefaultProps: DispatchDailyProps = DISPATCH_DAILY_FIXTURES['2026-08-13'];

export {dispatchDailyInputSchema, dispatchDailyMetadata, dispatchDailySchema};
export type {DispatchDailyProps};

export const DispatchDaily: React.FC<DispatchDailyProps> = (rawProps) => {
  const props = validateDispatchDailyProps(rawProps);
  return <DispatchDailyComposition {...props}/>;
};
