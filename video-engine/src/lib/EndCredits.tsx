import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {INK} from './lighting';

/**
 * END CREDITS — the attribution the owner used to paste by hand, burned into the film.
 *
 * WHY THIS EXISTS (2026-08-09, owner's request).
 * ----------------------------------------------------------------------------------
 * Every Dispatch owes three things to somebody: the music is CC BY 4.0 and the licence
 * requires attribution wherever the work is distributed, the claims are only checkable if
 * the sources travel with them, and the channel wants people to be able to find it. All
 * three were being pasted into a LinkedIn first comment by hand, every single time, which
 * meant they existed on exactly one of the surfaces the video reaches. A file posted to
 * TikTok, embedded on the site, or sent to anyone carried none of it.
 *
 * A judge raised the missing music credit as a HARD BLOCKER on 2026-08-09 and was right.
 * The fix that day was a one-line strap. This is the general version: credits ride in the
 * picture, so they cannot be forgotten and cannot be separated from the film.
 *
 * IT IS DATA, NOT COPY. Everything on this card comes from `episode_props.json.credits`,
 * which `build_scenes.py` derives from `out/dispatch/music_credit.json` and
 * `out/dispatch/sources.json`. Nothing here is typed per run, so it cannot drift from the
 * record the way a hand-pasted comment can, and `scripts/credits_check.py` fails the run if
 * the rendered strings stop matching those files.
 *
 * The card is deliberately plain: high contrast, nothing moving that has to be READ. It is
 * the one moment in a Dispatch that is not trying to hold attention, it is trying to be
 * legible on a phone and screenshot-able.
 *
 * AMENDED 2026-08-13 (round 7). That paragraph used to say "static ... no motion", and it was
 * a design decision the film could not actually afford: content_sag_check fails
 * 123.50s..134.50s continuous at a 0.0 percent floor, which is eleven seconds of frozen JPEG
 * across the entire tail of the film, and the panel separately kept marking the end card as
 * dead. So there is now exactly one moving thing, a slow bloom on the ground plane, under
 * every glyph. The original intent is preserved as written: nothing a reader has to parse
 * moves, contrast is untouched, and any single frame still screenshots clean.
 */

export type CreditsData = {
  /** the verbatim licence string, straight from music_credit.json */
  music: string;
  /** short source labels, derived from sources.json (never hand-typed) */
  sources: string[];
  /** where to send people */
  site: string;
};

const MONO = 'JetBrains Mono, ui-monospace, Menlo, monospace';
const BONE = '#E8E2D4';
const DIM = '#9C9080';

/** Mono advance is exact, so a string's width is arithmetic and never a guess. */
const monoW = (s: string, size: number, track = 0) =>
  s.length * size * 0.602 + track * Math.max(0, s.length - 1);

/** Largest size at which `s` fits `maxW`, so a long source line shrinks instead of clipping. */
const fitSize = (s: string, maxW: number, ideal: number, floor = 13) =>
  Math.max(floor, Math.min(ideal, maxW / (s.length * 0.602 + 0.001)));

export const EndCredits: React.FC<{data: CreditsData; durationInFrames: number}> = ({
  data, durationInFrames,
}) => {
  const f = useCurrentFrame();
  // TWO FADES, because the mark is a SIGN-OFF and not a header (owner, 2026-08-09).
  // The body (site, sources, licence) clears first and the mark holds alone, then fades out
  // last, so the film ends on the logo the way a sign-off should. One fade for everything
  // would have the brand disappear in the middle of a wall of type.
  const bodyOut = durationInFrames - 46;
  const body = interpolate(f, [0, 9, bodyOut - 12, bodyOut],
    [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const mark = interpolate(f, [0, 9, durationInFrames - 16, durationInFrames],
    [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  // once the body is gone the mark eases to optical centre and settles, so the last frames
  // are the logo alone rather than a logo sitting where a paragraph used to be
  const rise = interpolate(f, [bodyOut - 12, bodyOut + 16], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const W = 1080;
  const SAFE = 72;              // 6.7 percent, comfortably outside every platform's chrome
  const MAXW = W - SAFE * 2;

  const siteLine = `VISIT US AT ${data.site.toUpperCase()}`;
  const siteSize = fitSize(siteLine, MAXW, 40);
  // A LICENCE CONDITION SET IN 19px IS NOT "UNMISSABLE" (2026-08-13, round 7). The comment
  // below this block says the credit is drawn last and unmissable, and then it fit a 74
  // character string to one line, which caps it at 19px in DIM -- the smallest, faintest type
  // in the whole film, on the one line CC BY 4.0 actually obliges us to make readable. Split
  // at the licence clause it doubles, because each half fits on its own line.
  const musicRaw = data.music.toUpperCase();
  const mSplit = musicRaw.lastIndexOf(', LICENSED');
  const musicLines = mSplit > 0
    ? [musicRaw.slice(0, mSplit), musicRaw.slice(mSplit + 2)]
    : [musicRaw];
  const musicSize = musicLines.reduce((acc, l) => Math.min(acc, fitSize(l, MAXW, 32)), 32);

  // sources are laid one per line, each shrunk to fit rather than truncated: a source you
  // cannot read is the same as a source you did not cite
  const srcSize = data.sources.reduce(
    (acc, s) => Math.min(acc, fitSize(s.toUpperCase(), MAXW, 22)), 22);

  // 620, not 470: at 470 the block sat in the upper half and left a third of a 1920 frame
  // empty under it, which is the single most repeated composition note this film has had.
  const top = 620;
  const srcTop = top + 250;
  const lineH = srcSize * 1.9;

  // the mark eases to TRUE frame centre, derived rather than offset, so moving the block
  // above never drags the sign-off off-centre with it
  const markY = top + rise * (940 - top);

  return (
    <AbsoluteFill>
      <svg width={W} height={1920} viewBox={`0 0 ${W} 1920`}>
        {/* the ground, so the credits never inherit whatever the last shot left on screen */}
        <rect x={0} y={0} width={W} height={1920} fill="#100D0B" />

        {/* ELEVEN SECONDS OF ABSOLUTE STILLNESS (2026-08-13, round 7). content_sag_check fails
            123.50s..134.50s continuous at a 0.0 percent floor: once the block finishes easing
            in, this card is a frozen JPEG for the whole tail of the film, which is where a
            viewer decides whether to follow. The room the film just left is lit by a hunting
            generator, so the credits are lit by the same bus: one slow bloom crossing the
            ground, under everything, changing nothing that has to be read. */}
        <ellipse cx={W / 2 + Math.sin(f / 74) * 300} cy={640 + Math.cos(f / 96) * 260}
                 rx={640} ry={430} fill="#3A2F22"
                 opacity={0.16 + 0.06 * Math.sin(f / 41)} />

        {/* THE SIGN-OFF. Drawn last in the file so it is on top, and it outlives the body. */}
        <g transform={`translate(${W / 2},${markY})`} opacity={mark}>
          <rect x={-monoW('ALASKA.AI', 46, 2) / 2 - 28} y={-46} rx={5}
                width={monoW('ALASKA.AI', 46, 2) + 56} height={86}
                fill="#8C7A45" stroke={INK} strokeWidth={5} />
          <text x={0} y={16} textAnchor="middle" fontFamily={MONO} fontSize={46}
                fontWeight={700} fill="#241F13" letterSpacing={2}>ALASKA.AI</text>
        </g>

        <g opacity={body}>
        <text x={W / 2} y={top + 120} textAnchor="middle" fontFamily={MONO} fontSize={siteSize}
              fontWeight={700} fill={BONE} letterSpacing={1.4}>{siteLine}</text>

        {/* sources, so the film's claims travel with the file that makes them */}
        <text x={W / 2} y={srcTop} textAnchor="middle" fontFamily={MONO} fontSize={srcSize * 0.86}
              fontWeight={700} fill={DIM} letterSpacing={2.4}>SOURCES</text>
        {data.sources.map((s, i) => (
          <text key={i} x={W / 2} y={srcTop + 44 + i * lineH} textAnchor="middle"
                fontFamily={MONO} fontSize={srcSize} fontWeight={700} fill={BONE}
                letterSpacing={0.8}>{s.toUpperCase()}</text>
        ))}

        {/* the licence condition, last and unmissable */}
        {musicLines.map((l, i) => (
          <text key={i} x={W / 2} y={srcTop + 96 + data.sources.length * lineH + i * (musicSize * 1.5)}
                textAnchor="middle" fontFamily={MONO} fontSize={musicSize} fontWeight={700}
                fill={BONE} letterSpacing={0.6}>{l}</text>
        ))}
        </g>
      </svg>
    </AbsoluteFill>
  );
};
