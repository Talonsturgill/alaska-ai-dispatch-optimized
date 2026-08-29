#!/usr/bin/env python3
"""
SHIP GATE — the last thing that runs before anything leaves the building.

WHY THIS EXISTS (2026-07-31, owner directive after the run shipped a failing cut).

That run did three things wrong and every one of them was possible because nothing
in the pipeline checked:

  1. The 3-judge panel returned a 6.98 median against an 8.6 bar and the run shipped
     anyway, using a clause in the routine that let it "deliver with the full scorecard
     disclosed" when it judged the remaining complaints to be style-register. The run
     graded its own remaining defects as cosmetic. They were not: five boring stretches
     with timestamps and a 15.3 second static ending are concrete named defects. THAT
     CLAUSE IS DELETED and this gate is what replaces it.

  2. The panel graded ONE render. The run then fixed things and re-rendered TWICE more.
     THE CUT THAT SHIPPED WAS NEVER GRADED BY ANYONE. The reported 6.98 described a
     file that no longer existed. Nothing caught that, because the verdict was a number
     in a transcript rather than a claim bound to bytes.

  3. The evidence the panel looked at (contact sheets, motion filmstrips) was likewise
     generated from the FIRST render. Re-rendering silently invalidated every frame the
     judges had seen, and the pipeline had no idea.

So the invariant this gate enforces is one sentence:

    THE PANEL MUST HAVE GRADED THE EXACT BYTES THAT ARE ABOUT TO SHIP, USING EVIDENCE
    DERIVED FROM THOSE EXACT BYTES, AND IT MUST HAVE PASSED.

It is enforced by sha256, not by anyone remembering. Re-render anything and the hashes
stop matching, the gate fails, and the run has to re-cut the evidence and re-grade.

THERE IS NO OVERRIDE FLAG, AND ADDING ONE IS A REGRESSION. The whole failure mode was a
run granting itself permission. A gate with an escape hatch is a suggestion.

OWNER RELEASE (added 2026-07-31, and it is NOT an override flag — read this before you
touch it). The owner, who set the 8.6 bar, can lower it for one specific run. The run
cannot. The difference is the whole point, so the mechanism is built to make it
impossible for a run to grant itself one:

  - It lives in config/owner_release.json, not in an argv flag. A flag is something a
    process types to itself; a file with the owner's own words in it is a decision.
  - It is bound to a single run date and refuses to apply on any other day, so it can
    never sit in the repo quietly authorising future runs.
  - It carries the verbatim instruction and the floor the owner accepted. Both are
    printed by the gate and both go into the dated email, so the release is always
    visible to the person who granted it, in the same place the score is.
  - It does not disable any other check. The bytes still have to be the graded bytes,
    the evidence still has to come from those bytes, and there still have to be three
    judges. A release lowers the bar for one run; it never lets an ungraded or stale
    cut through.

If you are a future run reading this and thinking about writing that file yourself:
don't. That is the exact thing the 2026-07-31 directive forbade.

Usage
-----
  # after the FINAL render, rebuild evidence from it, then have the panel grade THAT
  python3 scripts/ship_gate.py record --median 8.7 --judges 8.5,8.7,8.9 \
      --notes "what the panel said"

  # before upload / email / merge. exit 0 = you may ship. exit 1 = you may not.
  python3 scripts/ship_gate.py check
"""
import argparse, hashlib, json, math, os, re, subprocess, sys, tempfile, time
from pathlib import Path

from deliverable_contract import (
    DeliverableContractError,
    contract_digest,
    require_manifest,
)
from run_guard import ACTIVE_COMPOSITION, check_identity, load_stamp
from strict_json import StrictJSONError, load_path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "dispatch"
# THE GATE WAS POINTING AT A DIRECTORY AND A NAMING SCHEME THE PIPELINE STOPPED USING
# (fixed 2026-08-05). It expected out/dispatch/render/{master_9x16,master_4x5,
# master_9x16_720}.mp4 while encode_deliverables.sh has been writing
# out/dispatch/{dispatch_master,dispatch_square,dispatch_master_720}.mp4. So the gate
# could never pass, on any cut, for any score: it failed on missing deliverables before
# it ever looked at a verdict, and the failure message said "go back into the loop",
# which reads as a quality problem and sent every run back to editing.
#
# Worse, one of the three files it demanded was master_4x5.mp4. This repo documents
# 1080x1350 as the WRONG LinkedIn cut in two places, because a taller-than-square video
# routes into the swipe-only Video tab instead of the main feed. The gate was requiring
# the one deliverable the routine forbids.
RENDER = OUT
# Same staleness as DELIVERABLES above: the evidence pack the panel actually reads is
# built by scripts/build_evidence.py into out/evidence (contact sheet, 14 stills, 5
# filmstrips, audio_report.json). The gate was looking in out/dispatch/review, which
# nothing has written to in this pipeline's lifetime.
REVIEW = ROOT / "out" / "evidence"
VERDICT = OUT / "panel_verdict.json"
ATTEMPTS = OUT / "gate_attempts.json"
RUBRIC = ROOT / "config" / "dispatch_rubric.yaml"

SFX_PATH = OUT / "sfx_events.json"


class GateInputError(RuntimeError):
    pass


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ship_threshold() -> float:
    """Read the bar from the rubric. Never hardcode it here, so raising the bar in the
    rubric raises it everywhere."""
    try:
        import yaml
        cfg = yaml.safe_load(RUBRIC.read_text())
        for key in ("ship_threshold", "threshold"):
            if key in cfg:
                return float(cfg[key])
            for v in cfg.values():
                if isinstance(v, dict) and key in v:
                    return float(v[key])
    except Exception:
        pass
    return 8.6


RELEASE = ROOT / "config" / "owner_release.json"


def owner_release(run_date: str):
    """The owner's decision to accept a lower bar for ONE run, or None.

    Requires, in config/owner_release.json: run_date matching this run, the verbatim
    instruction, and the floor being accepted. Anything missing means no release, because
    a release nobody can read afterwards is indistinguishable from a run helping itself.
    """
    if not RELEASE.exists():
        return None
    try:
        d = load_path(RELEASE, label="owner release")
        if not isinstance(d, dict):
            raise StrictJSONError("owner release must be a JSON object")
    except (StrictJSONError, OSError) as e:
        print(f"ship_gate: owner_release.json is unreadable ({e}); ignoring it.")
        return None
    for k in ("run_date", "instruction", "floor"):
        if not d.get(k):
            print(f"ship_gate: owner_release.json has no {k}; ignoring it.")
            return None
    if str(d["run_date"]) != run_date:
        print(f"ship_gate: owner release is for {d['run_date']}, this run is {run_date}; "
              f"it does not apply.")
        return None
    return d


def run_date() -> str:
    """The date this run is shipping under, from the run stamp, never from the clock."""
    stamp = load_stamp(ROOT)
    if not isinstance(stamp, dict) or not isinstance(stamp.get("date"), str):
        raise GateInputError("run stamp has no canonical date")
    return stamp["date"]


def check_render_is_current():
    """Validate hash-bound run inputs and all five manifested files."""
    ok, reason = check_identity(
        root=ROOT, expected_composition=ACTIVE_COMPOSITION, require_props=True
    )
    if not ok:
        fail([f"run identity is invalid: {reason}"])
    try:
        require_manifest(root=ROOT)
    except DeliverableContractError as exc:
        fail([f"deliverable manifest is invalid: {exc}"])


def artifact_state():
    """sha256 of every deliverable plus every piece of review evidence."""
    try:
        manifest = require_manifest(root=ROOT)
    except DeliverableContractError as exc:
        fail([f"deliverable manifest is invalid: {exc}"])
    arts = {role: entry["sha256"] for role, entry in manifest["artifacts"].items()}
    evidence_hashes = {}
    if REVIEW.exists():
        # build_evidence.py writes the contact sheet, the stills and the filmstrips as
        # JPEG. Globbing only *.png found nothing, so the gate reported that the panel
        # "cannot have looked at anything" while a full evidence pack sat beside it.
        # Third instance of the same drift in this file: the gate was written against an
        # older pipeline and never re-pointed when the pipeline changed.
        evidence_files = (
            list(REVIEW.glob("*.png")) + list(REVIEW.glob("*.jpg"))
            + list(REVIEW.glob("*.json"))
        )
        for p in sorted(evidence_files):
            if p.is_symlink():
                fail([f"review evidence may not be a symlink: {p.name}"])
            evidence_hashes[p.name] = sha(p)
    return arts, evidence_hashes, manifest


def log_attempt(reasons, median=None):
    """Every blocked attempt is appended, so the editing loop is auditable and a run
    cannot quietly stall in it. This is a LEDGER, not a budget: there is no attempt
    count at which stopping becomes allowed."""
    hist = []
    if ATTEMPTS.exists():
        try:
            value = load_path(ATTEMPTS, label="gate attempts")
            hist = value if isinstance(value, list) else []
        except (StrictJSONError, OSError):
            hist = []
    hist.append({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "attempt": len(hist) + 1, "median": median, "reasons": reasons})
    try:
        atomic_json(ATTEMPTS, hist)
    except OSError:
        pass
    return len(hist)


def fail(lines, median=None):
    n = log_attempt(lines, median)
    print("=" * 72)
    print(f"SHIP GATE: BLOCKED  (editing round {n})")
    print("=" * 72)
    for l in lines:
        print(f"  FAIL  {l}")
    print()
    print("  THIS IS NOT AN OUTCOME. IT IS AN INSTRUCTION TO GO BACK INTO THE LOOP.")
    print("  Return to Phase 6. Take the panel's named defects, fix them, re-render,")
    print("  rebuild the evidence FROM the new render, re-grade, re-record, run this again.")
    print()
    print("  There is no override flag and there is no round count at which stopping")
    print("  becomes acceptable. A below-bar film is unfinished, not failed. The only")
    print("  exit from this loop is a passing median. Quality is never a blocker;")
    print("  the only thing that legitimately halts a run is a tool that will not run.")
    sys.exit(1)


BLANK_LOW_INFO = 0.85   # a frame this featureless is not a shot, it is an absence


def check_not_blank(n=28):
    """Is there actually a FILM in the file?

    Added 2026-07-31 after this run rendered the wrong Remotion composition. Root.tsx keeps
    every past episode registered under its own id, and the generic id "Dispatch" still
    pointed at the July 26 film, so the render produced 93.3 seconds of the WRONG episode:
    correct length, correct dimensions, correct captions burned over the top, and thirty
    seconds of blank grey at the end where that episode had simply run out of scenes.

    Every existing check passed. The hashes matched because the bytes were consistent. The
    freshness check passed because the file was new. The mux verified because there was
    audio. ffprobe passed because the frame size was right. They all answer "is this
    deliverable current and well-formed", and not one of them answers "is this a movie".

    So: sample frames across the whole duration and measure local structure. A frame that is
    almost entirely flat is not a composition choice, it is a missing scene. Named by
    timestamp so the failure points at where to look rather than just asserting badness.
    """
    import glob, shutil, subprocess as sp, tempfile
    import numpy as np
    from PIL import Image

    vid = RENDER / "dispatch_master_hosted.mp4"
    if not vid.exists():
        return
    tmp = tempfile.mkdtemp(prefix="shipgate_blank_")
    try:
        dur = float(sp.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(vid)], capture_output=True, text=True
                           ).stdout.strip() or 0)
        if dur <= 0:
            return
        for i in range(n):
            t = dur * (i + 0.5) / n
            sp.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(vid),
                    "-frames:v", "1", "-vf", "scale=360:-1", f"{tmp}/f{i:03d}.png"],
                   capture_output=True)
        blank = []
        for i, p in enumerate(sorted(glob.glob(f"{tmp}/*.png"))):
            a = np.asarray(Image.open(p).convert("L"), dtype=np.float32)
            k = 17
            def box(x, ax):
                c = np.cumsum(np.pad(x, [(k // 2 + 1, k // 2) if d == ax else (0, 0)
                                         for d in (0, 1)]), axis=ax)
                return (np.take(c, range(k, c.shape[ax]), axis=ax)
                        - np.take(c, range(0, c.shape[ax] - k), axis=ax)) / k
            m = box(box(a, 0), 1)
            m2 = box(box(a * a, 0), 1)
            sd = np.sqrt(np.maximum(0.0, m2 - m * m))
            frac = float((sd < 5.0).mean())
            if frac > BLANK_LOW_INFO:
                blank.append((i * dur / n, frac))
        if blank:
            fail([f"{len(blank)} of {n} sampled frames are effectively BLANK "
                  f"(over {BLANK_LOW_INFO * 100:.0f}% of the frame carries no structure).",
                  "First few: " + ", ".join(f"{t:.1f}s ({f * 100:.0f}%)" for t, f in blank[:6]),
                  "A deliverable of the right length and the right dimensions is not the same "
                  "thing as the right film. Check that render.sh was given THIS run's "
                  "composition id (out/dispatch/.run_stamp.json > composition) and that every "
                  "scene in episode_props.json has a component behind it."])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def sfx_facts(
    path: Path | None = None, *, duration_seconds: float | None = None,
    root: Path = ROOT,
):
    """Return hash-bound SFX facts plus actionable validation problems."""
    path = path or (root / "out" / "dispatch" / "sfx_events.json")
    problems = []
    root = Path(root).resolve()
    stamp = load_stamp(root)
    started_at = None
    if (
        isinstance(stamp, dict) and isinstance(stamp.get("started_at"), (int, float))
        and not isinstance(stamp.get("started_at"), bool)
        and math.isfinite(float(stamp["started_at"]))
    ):
        started_at = float(stamp["started_at"])
    try:
        resolved_path = path.resolve()
        resolved_path.relative_to(root)
    except (OSError, ValueError):
        return None, ["sfx_events.json path escapes the repository"]
    if path.is_symlink():
        return None, ["sfx_events.json may not be a symlink"]
    path = resolved_path
    if not path.is_file():
        return None, ["no out/dispatch/sfx_events.json"]
    if started_at is None:
        problems.append("run stamp is missing a valid started_at")
    elif path.stat().st_mtime <= started_at:
        problems.append("sfx_events.json does not postdate the current run stamp")
    try:
        raw = load_path(path, label="sfx_events.json")
    except (StrictJSONError, OSError) as exc:
        return None, problems + [str(exc)]
    if not isinstance(raw, dict):
        return None, problems + ["sfx_events.json must be an object with an events list"]
    events = raw.get("events")
    if not isinstance(events, list):
        return None, problems + ["sfx_events.json.events must be a list"]
    if len(events) < 6:
        problems.append(f"sfx_events.json carries {len(events)} event(s); at least 6 are required")
    if "count" not in raw:
        problems.append("sfx_events.json count is required")
    elif isinstance(raw["count"], bool) or not isinstance(raw["count"], int) or raw["count"] != len(events):
        problems.append("sfx_events.json count does not match events")
    if "video_seconds" not in raw:
        problems.append("sfx_events.json video_seconds is required")
    else:
        declared = raw["video_seconds"]
        if isinstance(declared, bool) or not isinstance(declared, (int, float)) or not math.isfinite(float(declared)):
            problems.append("sfx_events.json video_seconds must be finite")
        elif duration_seconds is not None and abs(float(declared) - duration_seconds) > 0.25:
            problems.append("sfx_events.json video_seconds does not match the delivered duration")
    normalized = []
    kinds = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            problems.append(f"sfx event {index} must be an object")
            continue
        when = event.get("t")
        kind = event.get("kind")
        if isinstance(when, bool) or not isinstance(when, (int, float)) or not math.isfinite(float(when)):
            problems.append(f"sfx event {index}.t must be a finite number")
        elif float(when) < 0:
            problems.append(f"sfx event {index}.t may not be negative")
        elif duration_seconds is not None and float(when) > duration_seconds:
            problems.append(f"sfx event {index}.t is beyond the delivered duration")
        if not isinstance(kind, str) or not kind.isascii() or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", kind):
            problems.append(f"sfx event {index}.kind must be a lowercase ASCII identifier")
        else:
            kinds.add(kind)
        if isinstance(when, (int, float)) and not isinstance(when, bool) and math.isfinite(float(when)) and isinstance(kind, str):
            normalized.append({"t": float(when), "kind": kind})
    listed_kinds = raw.get("kinds")
    if (
        not isinstance(listed_kinds, list) or any(not isinstance(item, str) for item in listed_kinds)
        or listed_kinds != sorted(kinds)
    ):
        problems.append("sfx_events.json kinds must exactly match the sorted event kinds")

    audio_rel = "out/dispatch/audio/master.wav"
    audio_path = root.joinpath(*audio_rel.split("/"))
    audio_facts = raw.get("audio")
    if not audio_path.is_file() or audio_path.is_symlink():
        problems.append("current audio master is missing or a symlink")
        current_audio = None
    else:
        current_audio = {
            "path": audio_rel,
            "bytes": audio_path.stat().st_size,
            "sha256": sha(audio_path),
        }
        if started_at is not None and audio_path.stat().st_mtime <= started_at:
            problems.append("audio master does not postdate the current run stamp")
        if path.stat().st_mtime <= audio_path.stat().st_mtime:
            problems.append("sfx_events.json does not postdate the audio master it describes")
    if not isinstance(audio_facts, dict) or audio_facts != current_audio:
        problems.append("sfx_events.json audio facts do not match the current audio master")

    facts = {
        "path": "out/dispatch/sfx_events.json",
        "sha256": sha(path),
        "count": len(events),
        "kinds": sorted(kinds),
        "first_seconds": min((item["t"] for item in normalized), default=None),
        "last_seconds": max((item["t"] for item in normalized), default=None),
        "audio": current_audio,
    }
    return facts, problems


def cmd_record(a):
    check_render_is_current()
    check_not_blank()
    arts, evidence_hashes, manifest = artifact_state()
    if not evidence_hashes:
        fail([f"no review evidence in {REVIEW} — the panel cannot have looked at anything. "
              f"Run scripts/make_review_sheets.py on frames extracted from THIS render."])

    try:
        judges = [float(x) for x in a.judges.split(",") if x.strip()] if a.judges else []
    except ValueError:
        fail(["judge scores must be comma-separated finite numbers"])
    if len(judges) != 3 or any(not math.isfinite(score) for score in judges):
        fail([f"a 3-judge panel means THREE judges. Got {len(judges)}: {judges}. "
              f"The panel was skipped on 2026-07-29 and 2026-07-30 and that is exactly "
              f"how a failing cut reaches the owner."])

    median = a.median
    if median is None:
        s = sorted(judges)
        median = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
    if not math.isfinite(median):
        fail(["panel median must be finite"])

    # The frames the judges saw must be NEWER than the render they claim to describe.
    # If a sheet predates the video, it was made from a different cut.
    vertical = ROOT / manifest["artifacts"]["vertical_hosted"]["path"]
    vid_mtime = vertical.stat().st_mtime
    stale = [n for n in evidence_hashes if (REVIEW / n).stat().st_mtime <= vid_mtime]
    if stale:
        fail([f"review evidence is OLDER than the render it is supposed to describe: "
              f"{', '.join(sorted(stale)[:6])}{' ...' if len(stale) > 6 else ''}",
              "This is the 2026-07-31 failure exactly: the panel graded render #1 and the "
              "run shipped render #3. Rebuild the sheets from the current render."])

    duration = float(manifest["artifacts"]["vertical_hosted"]["duration_seconds"])
    sfx, sfx_problems = sfx_facts(duration_seconds=duration)
    if sfx_problems or sfx is None:
        fail(sfx_problems or ["sfx evidence is unavailable"])
    media_facts = {
        role: {
            "sha256": entry["sha256"],
            "bytes": entry["bytes"],
            "duration_seconds": entry["duration_seconds"],
            "streams": entry["streams"],
        }
        for role, entry in manifest["artifacts"].items()
    }
    atomic_json(VERDICT, {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "median": median,
        "judges": judges,
        "threshold": ship_threshold(),
        "notes": a.notes or "",
        "artifacts": arts,
        "evidence": evidence_hashes,
        "manifest_digest": contract_digest(manifest),
        "media_facts": media_facts,
        "sfx": sfx,
    })
    print(f"ship_gate: verdict recorded. median={median} judges={judges} "
          f"threshold={ship_threshold()}")
    print(f"  bound to {len(arts)} deliverables, {len(evidence_hashes)} evidence files and {sfx['count']} SFX events")
    print(f"  -> {VERDICT}")


def check_beats_delivered():
    """Did the build draw the events the board wrote? (scripts/beat_delivery.py)

    Added 2026-07-31. Advisory-to-hard: it PASSES the run it was written for, at 100%, which
    is itself the finding -- that run's beats all moved, and the panel still scored the picture
    as static, so this is not the explanation for that score. It is here as a regression guard
    against a build that quietly stops drawing what the board promised, which is a failure that
    contact sheets hide and that cost a full review cycle to even suspect.

    LIVE, AND ADVISORY ON PURPOSE (2026-08-13). Until this run the body opened with a glob
    of out/dispatch/frames/frame_*.png, a directory the pipeline has never produced -- it
    renders straight to mp4 -- so this returned silently on every run since it was written
    and never once looked at a frame. It was dead code wearing the costume of a gate.

    It now samples the DELIVERED CUT (beat_delivery.analyze_cut) with the EPISODE'S OWN
    CAPTION_TOP rather than beat_delivery's stale 1420, which on a film using 1336 was
    counting burned captions as beat motion and made the check too lenient.

    It does NOT fail the run yet, and that is the whole point of this step. The check ends
    in fail(problems), so making it blocking in the same change that makes it live would arm
    a hard gate nobody has ever seen pass, on the critical path, mid-delivery. Promote it to
    a hard fail only after it has been observed passing a good film. Anything it reports here
    is a note for the fix loop, not a refusal.
    """
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import beat_delivery as _bd
        r = _bd.analyze_cut(str(OUT / "dispatch_master_hosted.mp4"),
                            str(OUT / "storyboard.json"))
        print(f"  beat delivery (ADVISORY): {r['delivered']}/{r['beats']} beats draw a "
              f"visible event ({r['share']*100:.0f}%), caption band from "
              f"y={_bd.episode_caption_top()}")
        for p in r["problems"]:
            print(f"    advisory: {p}")
    except SystemExit as e:
        print(f"  beat delivery (ADVISORY): could not run ({e}); beats not delivery-checked")
    except Exception as e:
        print(f"  beat delivery (ADVISORY): could not run ({e}); beats not delivery-checked")


def cmd_check(a):
    check_render_is_current()
    check_not_blank()
    check_beats_delivered()
    problems = []
    if not VERDICT.exists():
        fail([f"no {VERDICT.name}. The 3-judge panel has not graded this cut. "
              f"A Dispatch may not ship ungraded."])

    try:
        v = load_path(VERDICT, label="panel verdict")
    except (StrictJSONError, OSError) as exc:
        fail([str(exc)])
    if not isinstance(v, dict):
        fail(["panel verdict must be a JSON object"])
    arts, evidence_hashes, manifest = artifact_state()
    thr = ship_threshold()

    # ---- 1. DID IT PASS? No self-granted exceptions, no 'style-register' carve-out. ----
    try:
        median = float(v.get("median"))
        if not math.isfinite(median):
            raise ValueError
    except (TypeError, ValueError):
        median = 0.0
        problems.append("verdict median must be a finite number")
    try:
        rel = owner_release(run_date())
    except GateInputError as exc:
        rel = None
        problems.append(str(exc))
    effective = thr
    if rel and float(rel["floor"]) < thr:
        effective = float(rel["floor"])
    if median < effective:
        problems.append(
            f"PANEL MEDIAN {median} IS BELOW THE {effective} SHIP BAR. This is a hard stop. "
            f"The routine's old 'deliver with the scorecard disclosed' clause was DELETED "
            f"on 2026-07-31 because a run used it to ship a 6.98. Disclosure is not a "
            f"substitute for fixing. Fix the defects, re-render, re-grade.")
    elif effective < thr:
        print("=" * 72)
        print(f"SHIPPING UNDER AN OWNER RELEASE — the rubric bar is {thr}, this cut scored "
              f"{median}.")
        print(f"  released to: {effective}   on: {rel['run_date']}")
        print(f"  owner said: {rel['instruction']}")
        print("  Every other check below still applies and none of them were waived.")
        print("=" * 72)
    judges = v.get("judges")
    if not isinstance(judges, list) or len(judges) != 3 or any(
        isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score))
        for score in (judges if isinstance(judges, list) else [])
    ):
        problems.append("verdict must record exactly 3 finite numeric judge scores")
        judges = judges if isinstance(judges, list) else []

    # ---- 2. DID THEY GRADE WHAT IS ABOUT TO SHIP? ----
    graded_artifacts = v.get("artifacts")
    if not isinstance(graded_artifacts, dict):
        problems.append("verdict artifacts must be an object")
        graded_artifacts = {}
    for name, want in graded_artifacts.items():
        if not isinstance(want, str) or not re.fullmatch(r"[0-9a-f]{64}", want):
            problems.append(f"graded hash for {name} is invalid")
            continue
        got = arts.get(name)
        if got is None:
            problems.append(f"{name} was graded but is no longer present.")
        elif got != want:
            problems.append(
                f"{name} HAS CHANGED SINCE IT WAS GRADED.\n"
                f"          graded: {want[:16]}...\n"
                f"          on disk: {got[:16]}...\n"
                f"        The panel's verdict describes a file that is not the file you are "
                f"about to ship. Re-cut the evidence, re-grade, re-record.")
    for name in arts:
        if name not in graded_artifacts:
            problems.append(f"{name} is a deliverable but was never graded.")

    # The immutable manifest projection and probed audio facts must be the ones recorded.
    if v.get("manifest_digest") != contract_digest(manifest):
        problems.append("deliverable manifest changed after grading")
    current_media_facts = {
        role: {
            "sha256": entry["sha256"],
            "bytes": entry["bytes"],
            "duration_seconds": entry["duration_seconds"],
            "streams": entry["streams"],
        }
        for role, entry in manifest["artifacts"].items()
    }
    if v.get("media_facts") != current_media_facts:
        problems.append("delivered media/audio facts changed after grading")

    duration = float(manifest["artifacts"]["vertical_hosted"]["duration_seconds"])
    current_sfx, sfx_problems = sfx_facts(duration_seconds=duration)
    problems.extend(sfx_problems)
    if current_sfx is not None and v.get("sfx") != current_sfx:
        problems.append("sfx_events.json changed after grading")

    # ---- 3. WAS THE EVIDENCE DERIVED FROM THOSE BYTES? ----
    graded_ev = v.get("evidence")
    if not isinstance(graded_ev, dict):
        problems.append("verdict evidence must be an object")
        graded_ev = {}
    if not graded_ev:
        problems.append("the verdict records no review evidence — nobody looked at a frame.")
    for name, want in graded_ev.items():
        got = evidence_hashes.get(name)
        if got is None:
            problems.append(f"review evidence {name} is gone.")
        elif got != want:
            problems.append(f"review evidence {name} changed after grading.")
    for name in evidence_hashes:
        if name not in graded_ev:
            problems.append(f"review evidence {name} was added after grading")

    if problems:
        fail(problems, median=median)

    # A PASS IS A STOP ORDER, NOT A CHECKPOINT (2026-08-09, owner's instruction after this
    # routine passed at 7.61, kept editing, and never cleared the bar again in five further
    # rounds costing nine hours). The run that day had a shippable cut, found a real defect,
    # fixed it, and destroyed the passing verdict to do so, because any source edit forces a
    # re-render and a re-grade. The defect was genuine; fixing it THEN was the error.
    #
    # So the pass now leaves a lock on disk and render_parallel.sh refuses to start while it
    # exists. Continuing to polish after a pass is no longer a judgement call a run gets to
    # make on its own: it has to delete a file whose name says what it is doing.
    SHIP_NOW = RENDER / "SHIP_NOW"
    SHIP_NOW.write_text(
        f"median {median} cleared {effective} at {time.strftime('%H:%M:%S')}.\n"
        "SHIP THESE BYTES. Do not edit, do not re-render, do not improve.\n"
        "Every further fix is next run's work. Delete this file only if you are deliberately\n"
        "abandoning a passing cut, and say so out loud when you do.\n")
    print("=" * 72)
    print("SHIP GATE: PASS  ->  SHIP NOW, DO NOT KEEP EDITING")
    print("=" * 72)
    # print the EFFECTIVE bar, not the rubric one. The first version of this line printed
    # "7.2 >= 7.5" under a release, which is a false statement in the pass banner of the gate
    # whose entire job is to not let false statements through.
    print(f"  panel median {median} >= {effective} (rubric bar {thr})   judges={judges}"
          if effective != thr else
          f"  panel median {median} >= {thr}   judges={judges}")
    print(f"  {len(arts)} deliverables hash-match the graded cut")
    print(f"  {len(graded_ev)} pieces of review evidence hash-match")
    if ATTEMPTS.exists():
        try:
            n = len(json.loads(ATTEMPTS.read_text()))
            print(f"  cleared after {n} blocked round(s) in the editing loop")
        except Exception:
            pass
    print("  these bytes may be retained locally or published only to the canary media branch.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="bind a passing panel verdict to the current bytes")
    r.add_argument("--median", type=float, default=None)
    r.add_argument("--judges", type=str, default="", help="comma-separated, need 3")
    r.add_argument("--notes", type=str, default="")
    r.set_defaults(fn=cmd_record)
    c = sub.add_parser("check", help="the hard gate. run before upload/email/merge")
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    try:
        a.fn(a)
    except (GateInputError, DeliverableContractError, StrictJSONError, OSError, ValueError) as exc:
        fail([str(exc)])


if __name__ == "__main__":
    main()
