import React from 'react';
import {z} from 'zod';
import {Ep0813, ep0813Schema} from './Ep0813';

/**
 * Correctness-canary replay fixture.
 *
 * This is deliberately not presented as a generic story template. Phase B1
 * needs one stable active identity so renders, props and deliverables can be
 * hash-bound while the later template phase is built. Until that replacement
 * lands, DispatchDaily replays the frozen 2026-08-13 authored film and requires
 * an explicit fixtureId in its props/defaults.
 */
export const DISPATCH_DAILY_FIXTURE = '2026-08-13-replay' as const;

export const dispatchDailySchema = ep0813Schema.extend({
  fixtureId: z.literal(DISPATCH_DAILY_FIXTURE),
});

export type DispatchDailyProps = z.infer<typeof dispatchDailySchema>;

export const DispatchDaily: React.FC<DispatchDailyProps> = ({fixtureId: _fixtureId, ...props}) => {
  return <Ep0813 {...props} />;
};
