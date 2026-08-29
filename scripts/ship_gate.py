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
  python3 scripts/ship_gate.py record --cards \
      out/dispatch/judge_cards/judge-1.json \
      out/dispatch/judge_cards/judge-2.json \
      out/dispatch/judge_cards/judge-3.json \
      --notes "what the panel said"

  # before upload / email / merge. exit 0 = you may ship. exit 1 = you may not.
  python3 scripts/ship_gate.py check
"""
import argparse, hashlib, json, math, os, re, subprocess, sys, tempfile, time
import statistics
from pathlib import Path

from deliverable_contract import (
    DeliverableContractError,
    contract_digest,
    require_manifest,
)
from run_guard import ACTIVE_COMPOSITION, check_identity, load_stamp
from sfx_contract import sidecar_facts as contract_sfx_facts
from evidence_contract import (
    EvidenceContractError,
    evidence_manifest_sha,
    require_evidence_manifest,
)
from strict_json import StrictJSONError, load_path
from preflight import PreflightContractError, require_preflight_receipt
from video_judge_contract import (
    VideoJudgeContractError,
    require_three_cards,
    rubric_contract,
)

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
            json.dump(
                value, handle, indent=2, ensure_ascii=False, sort_keys=True,
                allow_nan=False,
            )
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


def rubric_facts() -> dict:
    """Return the exact immutable rubric bytes and threshold, or fail closed."""
    try:
        return rubric_contract(root=ROOT)
    except VideoJudgeContractError as exc:
        raise GateInputError(str(exc)) from None


RELEASE = ROOT / "config" / "owner_release.json"


def owner_release(run_date: str, run_id: str | None = None):
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
    except (StrictJSONError, OSError) as exc:
        raise GateInputError(f"owner release is unreadable: {exc}") from None
    if d.get("schema_version") != 1 or d.get("status") not in ("inactive", "active"):
        raise GateInputError("owner release must be schema_version 1 with active/inactive status")
    if d["status"] == "inactive":
        return None
    for key in ("run_id", "run_date", "instruction", "floor"):
        if key not in d or d[key] in (None, ""):
            raise GateInputError(f"active owner release is missing {key}")
    if str(d["run_date"]) != run_date or (run_id is not None and str(d["run_id"]) != run_id):
        raise GateInputError(
            "active owner release belongs to a different run; stale releases hard-fail"
        )
    floor = d["floor"]
    if (
        isinstance(floor, bool) or not isinstance(floor, (int, float))
        or not math.isfinite(float(floor)) or not 0 <= float(floor) <= 10
    ):
        raise GateInputError("active owner release floor must be finite in 0..10")
    return {
        "path": "config/owner_release.json",
        "bytes": RELEASE.stat().st_size,
        "sha256": sha(RELEASE),
        "run_id": str(d["run_id"]),
        "run_date": str(d["run_date"]),
        "floor": float(floor),
        "instruction": str(d["instruction"]),
    }


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
    try:
        evidence_manifest = require_evidence_manifest(root=ROOT, delivery_manifest=manifest)
    except EvidenceContractError as exc:
        fail([f"evidence manifest is invalid: {exc}"])
    evidence_hashes = {
        relative: entry["sha256"]
        for relative, entry in evidence_manifest["artifacts"].items()
    }
    return arts, evidence_hashes, manifest


def evidence_binding(manifest):
    evidence_manifest = require_evidence_manifest(root=ROOT, delivery_manifest=manifest)
    return {
        "path": "out/evidence/evidence_manifest.json",
        "sha256": evidence_manifest_sha(root=ROOT),
        "delivery_manifest_digest": evidence_manifest["delivery_manifest_digest"],
        "vertical_hosted": evidence_manifest["vertical_hosted"],
        "producers": evidence_manifest["producers"],
        "expected_artifacts": evidence_manifest["expected_artifacts"],
        "artifacts": evidence_manifest["artifacts"],
    }


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
    """Return the immutable blankness attestation for the current delivered bytes."""
    return blankness_facts(n=n)


def blankness_facts(n=28):
    """Decode exactly `n` samples and fail closed on every probe/decode anomaly."""
    import shutil
    import subprocess as sp
    import tempfile as tempmod

    try:
        manifest = require_manifest(root=ROOT)
    except DeliverableContractError as exc:
        raise GateInputError(f"blankness check cannot validate deliverables: {exc}") from None
    entry = manifest["artifacts"]["vertical_hosted"]
    video = ROOT.joinpath(*entry["path"].split("/"))
    if not video.is_file() or video.is_symlink():
        raise GateInputError("blankness check vertical_hosted is missing or unsafe")
    try:
        probe = sp.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(video)],
            capture_output=True, text=True, timeout=90,
        )
    except (FileNotFoundError, OSError, sp.TimeoutExpired) as exc:
        raise GateInputError(f"blankness ffprobe failed to run: {exc}") from None
    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout).strip().splitlines()
        raise GateInputError(
            f"blankness ffprobe rejected vertical_hosted: {detail[-1] if detail else 'unknown error'}"
        )
    try:
        duration = float(probe.stdout.strip())
    except (TypeError, ValueError, OverflowError):
        raise GateInputError("blankness ffprobe returned an invalid duration") from None
    if not math.isfinite(duration) or duration <= 0:
        raise GateInputError("blankness ffprobe returned a non-finite/non-positive duration")
    expected = float(entry["duration_seconds"])
    if abs(duration - expected) > 0.05:
        raise GateInputError("blankness duration does not match the manifested vertical bytes")
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise GateInputError("blankness sample count must be a positive integer")

    directory = Path(tempmod.mkdtemp(prefix="shipgate_blank_"))
    try:
        for index in range(n):
            at = duration * (index + 0.5) / n
            output = directory / f"f{index:03d}.png"
            try:
                decoded = sp.run(
                    ["ffmpeg", "-v", "error", "-ss", f"{at:.6f}", "-i", str(video),
                     "-frames:v", "1", "-vf", "scale=360:-1", str(output)],
                    capture_output=True, text=True, timeout=90,
                )
            except (FileNotFoundError, OSError, sp.TimeoutExpired) as exc:
                raise GateInputError(f"blankness ffmpeg sample {index} failed to run: {exc}") from None
            if decoded.returncode != 0 or not output.is_file() or output.stat().st_size == 0:
                detail = (decoded.stderr or decoded.stdout).strip().splitlines()
                raise GateInputError(
                    f"blankness ffmpeg sample {index} failed: "
                    f"{detail[-1] if detail else 'no decoded frame'}"
                )
        paths = sorted(directory.glob("f*.png"))
        if len(paths) != n:
            raise GateInputError(f"blankness decoded {len(paths)} samples, expected exactly {n}")
        try:
            import numpy as np
            from PIL import Image
        except (ImportError, OSError) as exc:
            raise GateInputError(f"blankness image-analysis dependency is unavailable: {exc}") from None
        blank: list[tuple[float, float]] = []
        fractions: list[float] = []
        for index, path in enumerate(paths):
            try:
                pixels = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
            except Exception as exc:
                raise GateInputError(f"blankness sample {index} cannot be decoded: {exc}") from None
            kernel = 17

            def box(values, axis):
                pad = [(kernel // 2 + 1, kernel // 2) if dimension == axis else (0, 0)
                       for dimension in (0, 1)]
                cumulative = np.cumsum(np.pad(values, pad), axis=axis)
                return (
                    np.take(cumulative, range(kernel, cumulative.shape[axis]), axis=axis)
                    - np.take(cumulative, range(0, cumulative.shape[axis] - kernel), axis=axis)
                ) / kernel

            mean = box(box(pixels, 0), 1)
            mean2 = box(box(pixels * pixels, 0), 1)
            deviation = np.sqrt(np.maximum(0.0, mean2 - mean * mean))
            fraction = float((deviation < 5.0).mean())
            if not math.isfinite(fraction):
                raise GateInputError(f"blankness sample {index} produced a non-finite metric")
            fractions.append(fraction)
            if fraction > BLANK_LOW_INFO:
                blank.append((duration * (index + 0.5) / n, fraction))
        if blank:
            raise GateInputError(
                f"{len(blank)} of {n} sampled frames are effectively blank; first: "
                + ", ".join(f"{at:.1f}s ({fraction * 100:.0f}%)" for at, fraction in blank[:6])
            )
        return {
            "algorithm": "local-structure-v2",
            "vertical_sha256": entry["sha256"],
            "duration_seconds": duration,
            "sample_count": n,
            "threshold": BLANK_LOW_INFO,
            "maximum_low_information_fraction": max(fractions),
        }
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def sfx_facts(
    path: Path | None = None, *, duration_seconds: float | None = None,
    root: Path = ROOT,
):
    """Return exact hash-bound SFX/audio facts plus actionable validation problems."""
    # duration_seconds is retained only for narrow caller compatibility.  The
    # authority is the current hash-bound episode_props total/fps.
    return contract_sfx_facts(path, root=root)


def cmd_record(a):
    try:
        preflight_receipt = require_preflight_receipt(root=ROOT)
    except PreflightContractError as exc:
        fail([f"current-run objective preflight is missing or stale: {exc}"])
    check_render_is_current()
    blankness = check_not_blank()
    arts, evidence_hashes, manifest = artifact_state()
    if not evidence_hashes:
        fail([f"no review evidence in {REVIEW} — the panel cannot have looked at anything. "
              f"Run scripts/build_evidence.py against THIS delivered cut."])

    try:
        judge_cards = require_three_cards(a.cards, root=ROOT)
    except VideoJudgeContractError as exc:
        fail([f"video judge cards are invalid: {exc}"])
    judge_totals = [float(card["weighted_total"]) for card in judge_cards]
    median = float(statistics.median(judge_totals))
    hard_blockers = [
        {"judge_id": card["judge_id"], "blocker": blocker}
        for card in judge_cards for blocker in card["hard_blockers"]
    ]

    try:
        evidence_manifest_facts = evidence_binding(manifest)
        rubric = rubric_facts()
        stamp = load_stamp(ROOT)
        if not isinstance(stamp, dict):
            raise GateInputError("run stamp is missing or unreadable")
        release = owner_release(stamp["date"], stamp["run_id"])
    except (EvidenceContractError, GateInputError) as exc:
        fail([str(exc)])
    effective_threshold = (
        min(rubric["ship_threshold"], release["floor"])
        if release is not None else rubric["ship_threshold"]
    )
    if hard_blockers:
        fail([
            f"judge {item['judge_id']} raised hard blocker: {item['blocker'].get('what')}"
            for item in hard_blockers
        ], median=median)
    if median < effective_threshold:
        fail([
            f"panel median {median:.6f} is below immutable threshold {effective_threshold:.6f}"
        ], median=median)

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
            "fps": entry["fps"],
            "frame_count": entry["frame_count"],
        }
        for role, entry in manifest["artifacts"].items()
    }
    atomic_json(VERDICT, {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "median": median,
        "judge_totals": judge_totals,
        "judge_cards": judge_cards,
        "rubric": rubric,
        "owner_release": release,
        "effective_threshold": effective_threshold,
        "notes": a.notes or "",
        "artifacts": arts,
        "evidence": evidence_hashes,
        "evidence_manifest": evidence_manifest_facts,
        "manifest_digest": contract_digest(manifest),
        "media_facts": media_facts,
        "sfx": sfx,
        "blankness": blankness,
        "preflight": preflight_receipt,
    })
    print(f"ship_gate: verdict recorded. median={median} judge_totals={judge_totals} "
          f"threshold={effective_threshold}")
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


def validate_ship_verdict(*, verify_blankness=True):
    """Pure current-run verdict validation shared by ship, previews, and no_exit."""
    problems = []
    try:
        current_preflight = require_preflight_receipt(root=ROOT)
    except PreflightContractError as exc:
        current_preflight = None
        problems.append(f"current-run objective preflight is missing or stale: {exc}")
    ok, reason = check_identity(
        root=ROOT, expected_composition=ACTIVE_COMPOSITION, require_props=True
    )
    if not ok:
        problems.append(f"run identity is invalid: {reason}")
    try:
        manifest = require_manifest(root=ROOT)
    except DeliverableContractError as exc:
        return None, problems + [f"deliverable manifest is invalid: {exc}"]
    if not VERDICT.is_file() or VERDICT.is_symlink():
        return None, problems + ["current-run panel verdict is missing or unsafe"]
    try:
        verdict = load_path(VERDICT, label="panel verdict")
    except (StrictJSONError, OSError) as exc:
        return None, problems + [str(exc)]
    if not isinstance(verdict, dict):
        return None, problems + ["panel verdict must be a JSON object"]
    expected_fields = {
        "recorded_at", "run_id", "run_date", "composition", "median", "judge_totals",
        "judge_cards",
        "rubric", "owner_release", "effective_threshold", "notes", "artifacts",
        "evidence", "evidence_manifest", "manifest_digest", "media_facts", "sfx",
        "blankness", "preflight",
    }
    if set(verdict) != expected_fields:
        problems.append("panel verdict fields are not canonical")
    stamp = load_stamp(ROOT)
    if not isinstance(stamp, dict):
        return verdict, problems + ["run stamp is missing or unreadable"]
    for key, wanted in (
        ("run_id", stamp["run_id"]),
        ("run_date", stamp["date"]),
        ("composition", stamp["composition"]),
    ):
        if verdict.get(key) != wanted:
            problems.append(f"verdict {key} does not match the current run")

    judge_totals = verdict.get("judge_totals")
    if (
        not isinstance(judge_totals, list) or len(judge_totals) != 3
        or any(
            isinstance(score, bool) or not isinstance(score, (int, float))
            or not math.isfinite(float(score)) or not 0 <= float(score) <= 10
            for score in (judge_totals if isinstance(judge_totals, list) else [])
        )
    ):
        problems.append("verdict must record exactly 3 finite rubric-derived judge totals in 0..10")
        computed_median = None
    else:
        computed_median = float(statistics.median(float(score) for score in judge_totals))
    recorded_median = verdict.get("median")
    if (
        computed_median is None or isinstance(recorded_median, bool)
        or not isinstance(recorded_median, (int, float))
        or not math.isfinite(float(recorded_median))
        or abs(float(recorded_median) - computed_median) > 1e-9
    ):
        problems.append("verdict median is not the internally computed median of its 3 judges")

    recorded_cards = verdict.get("judge_cards")
    try:
        paths = [card["path"] for card in recorded_cards] if isinstance(recorded_cards, list) else []
        current_cards = require_three_cards(paths, root=ROOT)
        if recorded_cards != current_cards:
            problems.append("judge card bytes, totals, blockers, or bindings changed after grading")
        elif judge_totals != [float(card["weighted_total"]) for card in current_cards]:
            problems.append("verdict judge totals do not match the bound judge cards")
        elif any(card["hard_blockers"] for card in current_cards):
            problems.append("a bound judge card contains a hard blocker")
    except (VideoJudgeContractError, KeyError, TypeError) as exc:
        problems.append(f"bound judge cards are invalid: {exc}")

    try:
        current_rubric = rubric_facts()
        current_release = owner_release(stamp["date"], stamp["run_id"])
    except GateInputError as exc:
        problems.append(str(exc))
        current_rubric = None
        current_release = None
    if verdict.get("rubric") != current_rubric:
        problems.append("verdict rubric hash/threshold changed after grading")
    if verdict.get("owner_release") != current_release:
        problems.append("verdict owner release does not match the immutable current-run decision")
    if current_rubric is not None:
        effective = (
            min(current_rubric["ship_threshold"], current_release["floor"])
            if current_release is not None else current_rubric["ship_threshold"]
        )
        if verdict.get("effective_threshold") != effective:
            problems.append("verdict effective threshold is not the bound rubric/release threshold")
        if computed_median is not None and computed_median < effective:
            problems.append(
                f"panel median {computed_median} is below the immutable {effective} ship threshold"
            )
    else:
        effective = None

    artifacts = {role: entry["sha256"] for role, entry in manifest["artifacts"].items()}
    if verdict.get("artifacts") != artifacts:
        problems.append("deliverable artifact hashes changed after grading")
    if verdict.get("manifest_digest") != contract_digest(manifest):
        problems.append("deliverable manifest changed after grading")
    if verdict.get("preflight") != current_preflight:
        problems.append("objective preflight receipt changed after grading")
    media_facts = {
        role: {
            "sha256": entry["sha256"],
            "bytes": entry["bytes"],
            "duration_seconds": entry["duration_seconds"],
            "streams": entry["streams"],
            "fps": entry["fps"],
            "frame_count": entry["frame_count"],
        }
        for role, entry in manifest["artifacts"].items()
    }
    if verdict.get("media_facts") != media_facts:
        problems.append("delivered media/audio facts changed after grading")
    try:
        bound_evidence = evidence_binding(manifest)
        evidence_hashes = {
            relative: entry["sha256"] for relative, entry in bound_evidence["artifacts"].items()
        }
        if verdict.get("evidence") != evidence_hashes:
            problems.append("review evidence hashes changed after grading")
        if verdict.get("evidence_manifest") != bound_evidence:
            problems.append("evidence manifest changed after grading")
    except EvidenceContractError as exc:
        problems.append(f"evidence manifest is invalid: {exc}")

    current_sfx, sfx_problems = sfx_facts(root=ROOT)
    problems.extend(sfx_problems)
    if current_sfx is None or verdict.get("sfx") != current_sfx:
        problems.append("sfx/audio evidence changed after grading")
    if verify_blankness:
        try:
            current_blankness = blankness_facts()
            if verdict.get("blankness") != current_blankness:
                problems.append("blankness attestation changed after grading")
        except GateInputError as exc:
            problems.append(str(exc))
    else:
        recorded_blankness = verdict.get("blankness")
        vertical_sha = manifest["artifacts"]["vertical_hosted"]["sha256"]
        if not isinstance(recorded_blankness, dict) or recorded_blankness.get("vertical_sha256") != vertical_sha:
            problems.append("blankness attestation is missing or bound to different vertical bytes")

    return {
        "verdict": verdict,
        "manifest": manifest,
        "median": computed_median,
        "threshold": effective,
        "judge_totals": judge_totals,
    }, problems


def require_ship_verdict(*, verify_blankness=True):
    state, problems = validate_ship_verdict(verify_blankness=verify_blankness)
    if state is None or problems:
        raise GateInputError("; ".join(problems or ["ship verdict is unavailable"]))
    return state


def cmd_check(a):
    check_beats_delivered()
    state, strict_problems = validate_ship_verdict(verify_blankness=True)
    if state is None or strict_problems:
        fail(strict_problems or ["ship verdict is unavailable"])
    median = state["median"]
    effective = state["threshold"]
    judge_totals = state["judge_totals"]
    arts = state["verdict"]["artifacts"]
    graded_ev = state["verdict"]["evidence"]
    from ship_marker import record_ship_marker
    record_ship_marker(state, root=ROOT)
    print("=" * 72)
    print("SHIP GATE: PASS  ->  SHIP NOW, DO NOT KEEP EDITING")
    print("=" * 72)
    print(f"  panel median {median} >= {effective}   judge_totals={judge_totals}")
    print(f"  {len(arts)} deliverables hash-match the graded cut")
    print(f"  {len(graded_ev)} evidence artifacts hash-match the evidence manifest")
    return state
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="bind a passing panel verdict to the current bytes")
    r.add_argument(
        "--cards", nargs=3, required=True, metavar=("JUDGE_1", "JUDGE_2", "JUDGE_3"),
        help="exactly three strict rubric-derived video judge card paths",
    )
    r.add_argument("--notes", type=str, default="")
    r.set_defaults(fn=cmd_record)
    c = sub.add_parser("check", help="the hard gate. run before upload/email/merge")
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    try:
        a.fn(a)
    except (
        GateInputError, DeliverableContractError, StrictJSONError,
        VideoJudgeContractError, OSError, ValueError,
    ) as exc:
        fail([str(exc)])


if __name__ == "__main__":
    main()
