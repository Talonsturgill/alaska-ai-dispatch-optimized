#!/usr/bin/env python3
"""Refuse a Dispatch whose credits are missing, hand-typed, or out of step with the record.

WHY THIS EXISTS (2026-08-09, owner's request, and a judge's hard blocker before it).
------------------------------------------------------------------------------------
The music is CC BY 4.0. The licence requires attribution wherever the work is distributed,
which is every surface the file reaches and not just the one comment box somebody remembers
to paste into. The sources are what make the film's claims checkable by anyone who did not
watch a routine build them. Both used to live only in a LinkedIn first comment, typed by
hand, run after run.

On 2026-08-09 a judge filed the missing credit as a HARD BLOCKER, correctly: the rubric names
"music inaudible/uncredited" as an automatic fail. Three judges had raised it across six
rounds before that and each time the answer was "the email carries it", which was an answer
about one surface to a question about all of them.

So the credits are now rendered into the film by lib/EndCredits.tsx from data that
build_scenes.py derives from music_credit.json and sources.json. This gate is the half that
makes that stick. It checks four things, and each one is a way the arrangement could rot:

  1. THE BLOCK EXISTS.        A run that loses it ships an unattributed CC BY work.
  2. IT MATCHES THE RECORD.   The rendered music string must equal music_credit.json's
                              `credit` VERBATIM, and the source labels must be derivable from
                              sources.json. Hand-editing either into episode_props.json is
                              exactly the drift this replaces.
  3. THE ENGINE RENDERS IT.   The block can be perfect and the episode can still not draw it.
                              A prop nothing reads is not a credit.
  4. IT FITS.                 A credit nobody can read is not attribution. Every line is
                              measured against the safe width at its rendered size.

Exit 1 on any failure. There is no flag to skip it; a run that cannot credit its music has
nothing to ship.

    python3 scripts/credits_check.py
"""
import importlib
import math
import os
import subprocess
import re
import sys
from pathlib import Path

from strict_json import StrictJSONError, load_path

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
FRAME_W = 1080
SAFE = 72                      # must match EndCredits.tsx
MAXW = FRAME_W - SAFE * 2


def mono_w(s, size, track=0.0):
    return len(s) * size * 0.602 + track * max(0, len(s) - 1)


def fit_size(s, maxw, ideal, floor=13.0):
    return max(floor, min(ideal, maxw / (len(s) * 0.602 + 0.001)))


def registered_episode():
    """Return the active registry's sole story-bearing dependency; never infer by mtime."""
    try:
        from run_guard import ACTIVE_COMPOSITION, check_identity, composition_record

        ok, _reason = check_identity(
            root=REPO, expected_composition=ACTIVE_COMPOSITION, require_props=False
        )
        if not ok:
            return None
        dependencies = composition_record(ACTIVE_COMPOSITION, REPO).get("source_dependencies")
        if not isinstance(dependencies, list) or len(dependencies) != 1:
            return None
        target = os.path.realpath(os.path.join(REPO, *dependencies[0].split("/")))
        if os.path.commonpath([os.path.realpath(REPO), target]) != os.path.realpath(REPO):
            return None
        return target if os.path.isfile(target) else None
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        return None


def _load_credits_contract():
    """Load the one builder/gate contract, or fail closed with a named reason."""
    try:
        contract = importlib.import_module("credits_contract")
    except (ImportError, OSError, UnicodeError) as exc:
        raise RuntimeError(f"credits label contract cannot be imported: {exc}") from None
    required = (
        "CONTRACT_VERSION", "CREDITS_MIN_S", "CREDITS_TAIL_S",
        "derive_source_labels",
    )
    missing = [name for name in required if not hasattr(contract, name)]
    if missing:
        raise RuntimeError(
            "credits label contract is incomplete: missing " + ", ".join(missing)
        )
    if not callable(contract.derive_source_labels):
        raise RuntimeError("credits label contract derive_source_labels is not callable")
    try:
        minimum = float(contract.CREDITS_MIN_S)
        tail = float(contract.CREDITS_TAIL_S)
    except (TypeError, ValueError, OverflowError):
        raise RuntimeError("credits label contract duration constants are invalid") from None
    if not math.isfinite(minimum) or not math.isfinite(tail) or minimum < 10 or tail <= 0:
        raise RuntimeError("credits label contract duration constants are unsafe")
    return contract, minimum, tail


def _probe_duration(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", path], capture_output=True, text=True, timeout=90)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"duration probe could not run: {exc}") from None
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "ffprobe failed").strip().splitlines()
        raise RuntimeError(f"duration probe failed: {detail[-1] if detail else 'unknown error'}")
    try:
        value = float(r.stdout.strip())
    except (TypeError, ValueError, OverflowError):
        raise RuntimeError("duration probe returned an invalid value") from None
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError("duration probe returned a non-finite/non-positive value")
    return value


def _luma(path, t):
    """(mean, max) luma of the frame at t, off ffmpeg signalstats. (None, None) on failure."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", path, "-vframes", "1",
             "-vf", "format=gray,signalstats,metadata=print:file=-", "-f", "null", "-"],
            capture_output=True, text=True, timeout=90)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"credit-frame probe could not run: {exc}") from None
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "ffmpeg failed").strip().splitlines()
        raise RuntimeError(f"credit-frame probe failed: {detail[-1] if detail else 'unknown error'}")
    vals = {}
    for line in (r.stdout + r.stderr).splitlines():
        if "lavfi.signalstats.Y" in line and "=" in line:
            k, _, v = line.strip().partition("=")
            try:
                vals[k.rsplit(".", 1)[-1]] = float(v)
            except ValueError:
                pass
    if "YAVG" not in vals or "YMAX" not in vals:
        return None, None
    return vals["YAVG"], vals["YMAX"]


def main() -> int:
    problems = []
    contract, credits_min_s, credits_tail_s = _load_credits_contract()

    props_p = os.path.join(OUT, "episode_props.json")
    if not os.path.exists(props_p):
        print("credits_check: no episode_props.json. Run scripts/build_scenes.py first.")
        return 1
    props = load_path(props_p, label="episode props")
    if not isinstance(props, dict):
        raise StrictJSONError("episode props must be a JSON object")
    cred = props.get("credits")

    # ---- 1. the block exists ---------------------------------------------------------
    if not isinstance(cred, dict) or not cred:
        print("credits_check: FAIL, episode_props.json carries no `credits` block.")
        print("  The music is CC BY 4.0 and the licence needs attribution on the work itself.")
        print("  build_scenes.py builds this from music_credit.json + sources.json; if it")
        print("  refused, it said why on its own line above.")
        return 1

    # ---- 2. it matches the record ----------------------------------------------------
    mc_p = os.path.join(OUT, "music_credit.json")
    if not os.path.exists(mc_p):
        problems.append("out/dispatch/music_credit.json is missing, so nothing can verify "
                        "the licence string that is on screen.")
    else:
        music_credit = load_path(mc_p, label="music credit")
        if not isinstance(music_credit, dict):
            raise StrictJSONError("music credit must be a JSON object")
        want_raw = music_credit.get("credit")
        got_raw = cred.get("music")
        if not isinstance(want_raw, str):
            raise StrictJSONError("music credit.credit must be a string")
        if not isinstance(got_raw, str):
            raise StrictJSONError("episode props credits.music must be a string")
        want = want_raw.strip()
        got = got_raw.strip()
        if not want:
            problems.append("music_credit.json has no `credit` field.")
        elif got != want:
            problems.append("the on-screen music credit is NOT the one in music_credit.json.\n"
                            f"          record: {want!r}\n"
                            f"          screen: {got!r}\n"
                            "        A credit that drifts from its own record is the failure "
                            "this gate exists for.")
        for token in ("CC BY", "MacLeod" if "MacLeod" in want else ""):
            if token and token.lower() not in got.lower():
                problems.append(f"the on-screen credit is missing {token!r}, which the licence "
                                f"or the composer requires.")

    src_p = os.path.join(OUT, "sources.json")
    labels = cred.get("sources")
    if not isinstance(labels, list) or any(
        not isinstance(label, str) or not label.strip() for label in labels
    ):
        raise StrictJSONError("episode props credits.sources must be a list of non-empty strings")
    if not labels:
        problems.append("the credits carry no source labels at all.")
    elif not os.path.exists(src_p):
        problems.append("out/dispatch/sources.json is missing, so the on-screen source labels cannot be verified.")
    else:
        sources = load_path(src_p, label="sources")
        if not isinstance(sources, dict):
            raise StrictJSONError("sources must be a JSON object")
        try:
            expected_labels = contract.derive_source_labels(sources)
        except Exception as exc:
            # The contract is deliberately a hard dependency.  A broken import,
            # changed callable, malformed source entry, or derivation error cannot
            # turn into an unverified but apparently clean delivered credit.
            raise RuntimeError(f"credits label derivation failed: {exc}") from None
        if labels != expected_labels:
            problems.append(
                "the on-screen source labels are not the exact ordered labels derived from "
                "sources.json.\n"
                f"          record: {expected_labels!r}\n"
                f"          screen: {labels!r}"
            )

    site_raw = cred.get("site")
    if not isinstance(site_raw, str):
        raise StrictJSONError("episode props credits.site must be a string")
    site = site_raw.strip()
    if "alaskaaihq.com" not in site.lower():
        problems.append(f"the credits point at {site!r} rather than alaskaaihq.com.")

    # ---- 3. the engine renders it ----------------------------------------------------
    ep = registered_episode()
    if not ep:
        problems.append("DispatchDaily has no single valid registered source dependency, so "
                        "nothing can be verified as drawing the credits.")
    else:
        src = Path(ep).read_text(encoding="utf-8")
        body = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)      # comments are not renders
        body = re.sub(r"^\s*//.*$", " ", body, flags=re.M)
        # a TAG, not a substring: the first version of this check passed on "XEndCredits",
        # which is exactly the kind of near-miss a rename would produce
        if not re.search(r"<\s*EndCredits[\s/>]", body):
            problems.append(f"{os.path.relpath(ep, REPO)} never renders <EndCredits>. The "
                            f"credits block exists and nothing draws it.")
        elif not re.search(r"<Sequence[^>]*name=\"CREDITS\"", body):
            problems.append("the credits are not in a Sequence named CREDITS, so their "
                            "placement cannot be verified from the timeline.")

    # ---- 4. it fits ------------------------------------------------------------------
    site_line = f"VISIT US AT {site.upper()}"
    checks = [(site_line, fit_size(site_line, MAXW, 40)),
              ((cred.get("music") or "").upper(), fit_size((cred.get("music") or "").upper(),
                                                           MAXW, 19))]
    src_size = min([fit_size(l.upper(), MAXW, 22) for l in labels] or [22])
    checks += [(l.upper(), src_size) for l in labels]
    for text, size in checks:
        w = mono_w(text, size)
        if w > MAXW + 0.5:
            problems.append(f"{text[:44]!r} renders {w:.0f}px wide at size {size:.1f}, over the "
                            f"{MAXW}px safe width.")
        if size < 13.5:
            problems.append(f"{text[:44]!r} has to shrink to {size:.1f}px to fit, which is not "
                            f"readable on a phone. Shorten the label.")

    total, frames = props.get("total"), cred.get("frames")
    if total and frames and frames >= total:
        problems.append(f"the credits ({frames}f) are as long as the whole film ({total}f).")

    if problems:
        for p in problems:
            print(f"FAIL credits_check: {p}")
        print(f"\ncredits_check: {len(problems)} problem(s). A Dispatch that cannot credit its "
              f"music or show its sources has nothing to ship.")
        return 1

    # ---- THE DWELL FLOOR (owner rule, 2026-08-12) -------------------------------
    # "for the final scene that flashes the credits and sources and whatnot, leave that on
    # screen for 10 seconds so ppl can actually read that stuff."
    #
    # Checked in TWO places on purpose. The config number says what was intended; the
    # DELIVERED BYTES say what a viewer actually got, and those came apart on this run when
    # the mux truncated the card off the end of the film entirely. A build gate would have
    # called that clean.
    #
    # The byte-side signature is simple and stable: the sign-off is bright type on a near
    # black field, so its luma histogram is unmistakable against the slate story frames
    # (measured on this film: credits YAVG about 17 with YMAX at ceiling, story frames YAVG
    # 40+). Sample just inside the end and just inside the start of the required window; both
    # must look like the card. If the second one still shows the story, the card is short.
    dwell_problems = []
    secs = float(cred.get("seconds") or 0)
    if secs + 1e-6 < credits_min_s + credits_tail_s:
        dwell_problems.append(
            f"the sign-off is configured for {secs:.1f}s, which leaves under {credits_min_s:.0f}s of "
            f"READABLE body once EndCredits' {credits_tail_s:.1f}s of fades and mark sign-off are "
            f"taken off. "
            f"Raise CREDITS_MIN_S in scripts/credits_contract.py only to make the card LONGER. "
            f"If the film is over its runtime ceiling, take the seconds out of the script.")

    video = os.path.join(OUT, "dispatch_master_hosted.mp4")
    if not os.path.exists(video):
        dwell_problems.append("the canonical hosted video is missing, so delivered credit dwell cannot be verified.")
    else:
        dur = _probe_duration(video)
        body_end = dur - credits_tail_s
        for label, t in (("end of the readable window", body_end - 0.4),
                         ("start of the readable window", body_end - credits_min_s + 0.8)):
            yavg, ymax = _luma(video, t)
            if yavg is None:
                dwell_problems.append(f"could not sample the frame at {t:.1f}s ({label}).")
            elif not (yavg < 30 and ymax > 200):
                dwell_problems.append(
                    f"at {t:.1f}s ({label}) the frame does not look like the sign-off card "
                    f"(luma avg {yavg:.0f}, max {ymax:.0f}; the card measures avg under 30 "
                    f"with max above 200). The card is on screen for less than "
                    f"{credits_min_s:.0f}s in the delivered cut.")

    if dwell_problems:
        for d in dwell_problems:
            print(f"FAIL credits_check: {d}")
        print(f"\ncredits_check: the sign-off does not hold for {credits_min_s:.0f}s. Sources "
              f"and a CC BY 4.0 attribution nobody can finish reading are not delivered.")
        return 1

    print(f"credits_check: clean. {len(labels)} source line(s), licence string matches "
          f"music_credit.json verbatim, {cred.get('seconds')}s sign-off rendered by the engine "
          f"and verified on screen for the full {credits_min_s:.0f}s floor.")
    for l in labels:
        print(f"    {l}")
    print(f"    {site_line}")
    print(f"    {(cred.get('music') or '')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (StrictJSONError, RuntimeError, OSError, TypeError, ValueError, KeyError) as exc:
        raise SystemExit(f"credits_check: FAIL: {exc}") from None
