#!/usr/bin/env python3
"""Run every mechanical gate BEFORE a panel is ever convened. Exit nonzero if any fail.

WHY THIS EXISTS (2026-08-05, owner: "I'm frustrated at ur pre-panel performance").

The mechanical gates in this repo are good and they were being run inconsistently, after
the fact, one at a time, by a run that remembered to. So cuts reached the panel carrying
defects that a script could have named in four seconds: a string wider than its plate, a
stale deliverable, an evidence pack describing a file that no longer existed. Three judges
then spent twenty minutes each rediscovering them, and a fix round went on something
arithmetic.

A checklist in a document is a suggestion. This is the checklist as a program. The routine
runs it before convening a panel, and a failure here means the panel does not get convened,
because a judge's attention is the most expensive thing in the loop and it should never be
spent on something a regex can find.

It deliberately does NOT judge quality. Everything here is a fact check: does the string
fit, do the bytes match, is the report measured rather than typed. Taste is the panel's
job and this file has no opinion about it.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from strict_json import StrictJSONError, load_path

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RECEIPT_REL = "out/dispatch/preflight_receipt.json"
RECEIPT_SCHEMA_VERSION = 1


class PreflightContractError(RuntimeError):
    pass

# (label, argv, required). A non-required check that fails is reported and does not block,
# because it is advisory rather than a fact about correctness.
CHECKS = [
    ("canonical objective delivery/evidence/audio lineage gate",
     [sys.executable, ".claude/skills/alaska-dispatch/quality_gate.py"], True),
    ("typecheck the engine",
     ["npx", "tsc", "--noEmit", "-p", "video-engine/tsconfig.json"], True),
    ("plated strings fit their plates",
     [sys.executable, "scripts/text_fit_check.py"], True),
    # Belt and braces. Its real home is Gate 0A', BEFORE the render, where catching a
    # collision costs nothing instead of seven minutes. It is repeated here because the
    # defect it catches is invisible at every other stage: the source reads fine, tsc is
    # clean, the render succeeds, and two annotations are stacked in the same pixels.
    ("nothing informational sits in the caption band",
     [sys.executable, "scripts/caption_band_check.py"], True),
    # A phonetic respelling reaching the screen is a hard blocker every time a panel has
    # seen one, and the fix for it is a build-time TRANSFORM with no audit trail. This
    # asks the built artifact the question afterwards, which is the only way an ordering
    # change gets caught. 2026-08-08: "A I" on screen under a plate reading "AI".
    ("no phonetic respelling survived into the built props",
     [sys.executable, "scripts/caption_spelling_check.py"], True),
    # Every other caption check in this list asks what the captions SAY or where they SIT.
    # None of them asked whether they are on screen at all, so on 2026-08-12 a {start,end}
    # cue met a {t,d} reader, matched no frame, and the film shipped 4602 frames of empty
    # caption band with a clean preflight. Three judges found it. This reads the delivered
    # bytes and asks the direct question.
    ("the captions are actually on screen in the delivered cut",
     [sys.executable, "scripts/caption_render_check.py"], True),
    # Two elements in the same pixels cost score in three separate panel rounds on
    # 2026-08-06 and were invisible to every other check, because each element is
    # individually fine and the defect lives only in the relationship.
    ("no two text plates share pixels",
     [sys.executable, "scripts/plate_overlap_check.py"], True),
    # A plate can fit its own box perfectly and still be cut in half by the frame edge,
    # because the scene's content zoom pushes everything off-centre outward. On 2026-08-09
    # that clipped five elements including the film's central NSF quotation, which read on
    # screen as "FORCEMENT-LEARNING CONTROLLERS ... GRATED WITH MICR". No existing check
    # could see it: text_fit measures string against plate, caption_band models the VERTICAL
    # crop, plate_overlap compares boxes to each other. This one projects each box through
    # the zoom and compares it to the frame.
    ("no plate leaves the frame under the content zoom",
     [sys.executable, "scripts/zoom_clip_check.py"], True),
    # The fact-checker's instructions are obligations, not suggestions. Seven were
    # silently declined in one run and judges found all seven.
    ("every claim obligation the fact-checker wrote is honoured",
     [sys.executable, "scripts/claims_contract_check.py"], True),
    # The credits ride in the picture (2026-08-09, owner's request). The music is CC BY 4.0
    # and the licence needs attribution on every surface the file reaches, not just the one
    # comment box somebody remembers. Blocking, because a run that cannot credit its music
    # has nothing to ship.
    ("the film credits its music and shows its sources",
     [sys.executable, "scripts/credits_check.py"], True),
    # THE NARRATION obeys the claim set too. Added 2026-08-08, after a false line
    # ("five rural clinics that didn't have one") passed Gate 0E and the soundcheck
    # and reached a synth, because Gate 0E asks whether a stranger can FOLLOW the
    # script and the soundcheck asks whether the ASR heard it, and nothing asked
    # whether it was TRUE. Verified in both directions on the real defect.
    ("the narration obeys the fact-check-safe set",
     [sys.executable, "scripts/vo_claims_check.py"], True),
    # ...AND SO DOES THE AUDIO WE ACTUALLY SHIP. The check above gates the SCRIPT before TTS
    # is spent, which is the cheap place to catch a false line. It is not the LAST place one
    # can exist. On 2026-08-08 a surgical re-cut left a corrected script beside audio that
    # had not all been re-cut, and a words.json written 17 minutes before the patched vo.wav
    # then misrepresented the mix to a panel judge in the OTHER direction. Both failures are
    # the same gap: nothing had listened to the delivered file. Now something does.
    # Advisory, because a missing ASR backend must never be the thing that halts a run.
    ("the delivered mix obeys the fact-check-safe set",
     [sys.executable, "scripts/vo_audio_check.py"], False),
    # ADVISORY ON PURPOSE, same reasoning as the block below: it has never gone green.
    # On the film that prompted it (2026-08-06) it fails 6 of 8 figures, which is the
    # honest state of the craft rather than a broken checker. Promote it to required once
    # a run has actually staged its cast instead of parking them.
    ("every figure on screen is doing something",
     [sys.executable, "scripts/staging_check.py"], False),
    # ADVISORY ON PURPOSE, FOR NOW. It is new and it has never been observed passing, and
    # arming a hard gate that has never gone green is how a run dies at 3am for a reason
    # nobody has seen (see the beat-delivery note in prompts/dispatch_routine.md). Promote
    # it to required once one run has read it and cleared it.
    ("the evidence pack actually shows the film",
     [sys.executable, "scripts/evidence_coverage_check.py"], False),
    ("the square crop cuts nothing built",
     [sys.executable, "scripts/crop_safety.py"], False),
    # THE STORY REGION, WITH THE FURNITURE TAKEN OUT. The whole-frame dead-window gate went
    # blind the moment a near-field foreground was added to fix the previous round's dead
    # lower third: the foreground bobs continuously, so every frame contains motion whatever
    # the story is doing. A judge then measured two windows over the gate's own 5s rule that
    # it could not see. Advisory: the timecodes are the point, not the exit code.
    ("the story region never stops moving",
     [sys.executable, "scripts/content_sag_check.py"], False),
    ("dead space within ceilings",
     [sys.executable, "scripts/dead_space_check.py", "--every", "30"], False),
]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _check_id(argv):
    if argv and argv[0] == "npx":
        return "typescript_engine"
    if argv:
        stem = Path(argv[1] if argv[0] == sys.executable and len(argv) > 1 else argv[0]).stem
        return stem.replace("-", "_")
    raise PreflightContractError("required check has no executable")


def required_check_specs():
    core = [
        {"id": "git_identity", "label": "git identity is the owner's", "argv": []},
        {"id": "deliverables_manifest", "label": "deliverables are fresh", "argv": []},
        {"id": "evidence_manifest", "label": "terminal evidence is current", "argv": []},
    ]
    return core + [
        {"id": _check_id(argv), "label": label, "argv": list(argv)}
        for label, argv, required in CHECKS if required
    ]


def _safe_file_facts(base: Path, relative: str) -> dict:
    if (
        not isinstance(relative, str) or not relative or not relative.isascii()
        or "\\" in relative or relative.startswith("/")
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise PreflightContractError(f"preflight input path is not canonical: {relative!r}")
    logical = base.joinpath(*relative.split("/"))
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise PreflightContractError(f"preflight input path may not contain symlinks: {relative}")
    try:
        logical.resolve(strict=True).relative_to(base)
    except (OSError, ValueError) as exc:
        raise PreflightContractError(f"preflight input is missing or unsafe: {relative}: {exc}") from None
    if not logical.is_file():
        raise PreflightContractError(f"preflight input is not a file: {relative}")
    return {"path": relative, "bytes": logical.stat().st_size, "sha256": _sha256_file(logical)}


def _current_contract_state(root=REPO):
    from deliverable_contract import contract_digest, require_manifest
    from evidence_contract import evidence_manifest_sha, require_evidence_manifest
    from run_guard import load_stamp, stamp_digest

    base = Path(root).resolve()
    delivery = require_manifest(root=base)
    evidence = require_evidence_manifest(root=base, delivery_manifest=delivery)
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        raise PreflightContractError("run stamp is missing or unreadable")
    evidence_path = base / "out" / "evidence" / "evidence_manifest.json"
    quality_path = base / "out" / "dispatch" / "quality_report.json"
    try:
        quality = load_path(quality_path, label="quality report")
    except (StrictJSONError, OSError) as exc:
        raise PreflightContractError(str(exc)) from None
    expected_quality_checks = [
        {"id": "delivery_manifest_v4", "exit_code": 0, "result": "pass"},
        {"id": "mastering_audio_lineage_v1", "exit_code": 0, "result": "pass"},
        {"id": "evidence_manifest_v3", "exit_code": 0, "result": "pass"},
        {"id": "sole_sfx_ledger_v3", "exit_code": 0, "result": "pass"},
    ]
    quality_delivery = quality.get("delivery") if isinstance(quality, dict) else None
    quality_evidence = quality.get("evidence") if isinstance(quality, dict) else None
    quality_sfx = quality.get("sfx") if isinstance(quality, dict) else None
    mastering_sfx = delivery.get("mastering", {}).get("sfx")
    if (
        not isinstance(quality, dict)
        or not isinstance(quality_delivery, dict)
        or not isinstance(quality_evidence, dict)
        or not isinstance(quality_sfx, dict)
        or not isinstance(mastering_sfx, dict)
        or quality.get("schema_version") != 2
        or quality.get("status") != "pass"
        or quality_delivery.get("digest") != contract_digest(delivery)
        or quality.get("mastering") != delivery.get("mastering")
        or quality_evidence.get("sha256") != evidence_manifest_sha(root=base)
        or quality_sfx.get("sha256") != mastering_sfx.get("sha256")
        or quality.get("checks") != expected_quality_checks
    ):
        raise PreflightContractError("quality report is not canonical or bound to current contracts")
    input_paths = {
        "out/dispatch/.run_stamp.json",
        "out/dispatch/render/render_receipt.json",
        "out/dispatch/mastering_receipt.json",
        "out/dispatch/deliverables_manifest.json",
        "out/evidence/evidence_manifest.json",
        "out/dispatch/sfx_events.json",
        "out/dispatch/episode_props.json",
        "config/compositions.json",
        "config/deliverables.json",
        "config/dispatch_rubric.yaml",
        ".claude/skills/alaska-dispatch/quality_gate.py",
        "out/dispatch/quality_report.json",
    }
    for entry in delivery["artifacts"].values():
        input_paths.add(entry["path"])
    for relative in evidence["artifacts"]:
        input_paths.add(relative)
    for producer in evidence["producers"].values():
        input_paths.add(producer["path"])
        for relative in producer["inputs"]:
            input_paths.add(relative)
    for field in ("registry_path", "root_source_path", "source_path", "props_path"):
        relative = stamp.get(field)
        if isinstance(relative, str) and relative:
            input_paths.add(relative)
    for field in ("source_dependencies", "render_inputs"):
        values = stamp.get(field)
        if isinstance(values, dict):
            input_paths.update(path for path in values if isinstance(path, str))
    engine_root = base / "video-engine" / "src"
    if not engine_root.is_dir() or engine_root.is_symlink():
        raise PreflightContractError("video-engine/src is missing or unsafe")
    for candidate in engine_root.rglob("*"):
        if candidate.is_file() and candidate.suffix in {".ts", ".tsx"}:
            input_paths.add(candidate.resolve().relative_to(base).as_posix())
    inputs = {relative: _safe_file_facts(base, relative) for relative in sorted(input_paths)}

    tool_paths = {
        "scripts/preflight.py",
        "scripts/deliverable_contract.py",
        "scripts/evidence_contract.py",
        "scripts/mastering_contract.py",
        "scripts/render_contract.py",
        "scripts/run_guard.py",
        "scripts/sfx_contract.py",
        "scripts/strict_json.py",
        ".claude/skills/alaska-dispatch/quality_gate.py",
    }
    for _label, argv, required in CHECKS:
        if not required:
            continue
        for value in argv:
            if isinstance(value, str) and value.endswith(".py") and not Path(value).is_absolute():
                tool_paths.add(value.replace("\\", "/"))
    tools = {relative: _safe_file_facts(base, relative) for relative in sorted(tool_paths)}
    binding = {
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "stamp_sha256": stamp_digest(base),
        "render_binding_sha256": delivery["render"]["render_binding_sha256"],
        "delivery_manifest_digest": contract_digest(delivery),
        "evidence_manifest_digest": evidence["delivery_manifest_digest"],
        "evidence_manifest_bytes": evidence_path.stat().st_size,
        "evidence_manifest_sha256": evidence_manifest_sha(root=base),
    }
    return binding, inputs, tools


def record_preflight_receipt(results, *, root=REPO):
    expected = required_check_specs()
    if not isinstance(results, list) or len(results) != len(expected):
        raise PreflightContractError("preflight did not return the exact required check list")
    normalized = []
    for spec, result in zip(expected, results):
        if not isinstance(result, dict):
            raise PreflightContractError(f"preflight result for {spec['id']} is invalid")
        canonical = {
            "id": spec["id"], "label": spec["label"], "argv": spec["argv"],
            "result": "pass" if result.get("exit_code") == 0 else "fail",
            "exit_code": result.get("exit_code"),
            "stdout_sha256": result.get("stdout_sha256"),
            "stderr_sha256": result.get("stderr_sha256"),
        }
        if result.get("id") != spec["id"] or result.get("label") != spec["label"]:
            raise PreflightContractError(f"preflight result order/identity changed at {spec['id']}")
        if canonical["exit_code"] != 0:
            raise PreflightContractError(f"required preflight check failed: {spec['label']}")
        for key in ("stdout_sha256", "stderr_sha256"):
            if not isinstance(canonical[key], str) or len(canonical[key]) != 64:
                raise PreflightContractError(f"preflight result {spec['id']}.{key} is invalid")
        normalized.append(canonical)
    try:
        binding, inputs, tools = _current_contract_state(root)
    except PreflightContractError:
        raise
    except Exception as exc:
        raise PreflightContractError(f"preflight contract state cannot be recorded: {exc}") from None
    receipt = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "binding": binding,
        "required_checks": normalized,
        "inputs": inputs,
        "tool_sources": tools,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    target = Path(root).resolve().joinpath(*RECEIPT_REL.split("/"))
    _atomic_json(target, receipt)
    return receipt


def validate_preflight_receipt(*, root=REPO):
    base = Path(root).resolve()
    target = base.joinpath(*RECEIPT_REL.split("/"))
    try:
        receipt = load_path(target, label="preflight receipt")
    except (StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(receipt, dict):
        return None, ["preflight receipt must be a JSON object"]
    problems = []
    fields = {"schema_version", "binding", "required_checks", "inputs", "tool_sources", "recorded_at"}
    if set(receipt) != fields or receipt.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        problems.append("preflight receipt fields/schema are not canonical")
    try:
        binding, inputs, tools = _current_contract_state(base)
    except Exception as exc:
        return receipt, problems + [f"preflight current contract state is invalid: {exc}"]
    if receipt.get("binding") != binding:
        problems.append("preflight receipt run/render/delivery/evidence binding changed")
    if receipt.get("inputs") != inputs:
        problems.append("preflight input bytes or hashes changed after checks")
    if receipt.get("tool_sources") != tools:
        problems.append("preflight tool source bytes or hashes changed after checks")
    checks = receipt.get("required_checks")
    expected_specs = required_check_specs()
    if not isinstance(checks, list) or len(checks) != len(expected_specs):
        problems.append("preflight receipt does not contain the exact required check list")
    else:
        for index, (spec, result) in enumerate(zip(expected_specs, checks)):
            wanted = {"id": spec["id"], "label": spec["label"], "argv": spec["argv"]}
            if not isinstance(result, dict) or set(result) != set(wanted) | {
                "result", "exit_code", "stdout_sha256", "stderr_sha256",
            }:
                problems.append(f"preflight check {index} result fields are not canonical")
                continue
            if any(result.get(key) != value for key, value in wanted.items()):
                problems.append(f"preflight required check identity changed at {index}")
            if result.get("exit_code") != 0:
                problems.append(f"preflight required check did not pass: {spec['label']}")
            if result.get("result") != "pass":
                problems.append(f"preflight required check result is not pass: {spec['label']}")
            for key in ("stdout_sha256", "stderr_sha256"):
                value = result.get(key)
                if not isinstance(value, str) or len(value) != 64:
                    problems.append(f"preflight check {spec['id']}.{key} is invalid")
    if not isinstance(receipt.get("recorded_at"), str) or not receipt["recorded_at"]:
        problems.append("preflight receipt recorded_at is missing")
    return receipt, problems


def require_preflight_receipt(*, root=REPO):
    receipt, problems = validate_preflight_receipt(root=root)
    if receipt is None or problems:
        raise PreflightContractError("; ".join(problems or ["preflight receipt is unavailable"]))
    target = Path(root).resolve().joinpath(*RECEIPT_REL.split("/"))
    return {
        "path": RECEIPT_REL,
        "bytes": target.stat().st_size,
        "sha256": _sha256_file(target),
        "binding": receipt["binding"],
        "required_checks": receipt["required_checks"],
        "tool_sources": receipt["tool_sources"],
    }


def deliverables_are_fresh():
    """Re-probe and hash-check all five files against the exact run inputs."""
    from deliverable_contract import contract_digest, validate_manifest

    manifest, problems = validate_manifest(root=REPO)
    if problems or manifest is None:
        return False, "; ".join(problems or ["deliverables manifest is unavailable"])
    return True, f"five exact artifacts match manifest {contract_digest(manifest)[:16]}"


def evidence_is_current():
    """Require the exact producer-bound terminal evidence pack before any judge runs."""
    from deliverable_contract import DeliverableContractError, require_manifest
    from evidence_contract import EvidenceContractError, require_evidence_manifest

    try:
        delivery = require_manifest(root=REPO)
        evidence = require_evidence_manifest(root=REPO, delivery_manifest=delivery)
    except (DeliverableContractError, EvidenceContractError) as exc:
        return False, str(exc)
    return True, (
        f"{len(evidence['artifacts'])} exact artifacts match producer-bound manifest "
        f"for {evidence['identity']['run_id']}"
    )


def git_identity_is_the_owners():
    """The PERMANENT media host is a git push, so git identity is a DELIVERY prerequisite.

    WHY THIS EXISTS (2026-08-12, and it cost a run its download links). upload_video.py
    refuses to author a media commit as Claude/Anthropic, which is correct and is CLAUDE.md's
    rule. But git user.email was unset, so the permanent GitHub host declined, the script fell
    back to a temporary host, that host served an HTML error page, verification failed, and the
    run reached the Gmail draft with NO DOWNLOAD LINKS AT ALL.

    Every one of those steps behaved correctly. The failure was that a prerequisite for
    delivery was only discovered AT delivery, which is the most expensive moment available and
    the one place a run is most tempted to shrug and ship without it. One `git config` would
    have prevented the whole chain, and preflight is where that belongs.

    A check that runs before the first frame costs nothing. The same check at the delivery step
    costs the deliverable.
    """
    import subprocess
    r = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True)
    email = (r.stdout or "").strip()
    if not email:
        return False, ("git config user.email is UNSET. upload_video.py's permanent host is a "
                       "git push and will decline, so the run will reach the Gmail draft with no "
                       "download links. Set it to the owner's address.")
    if "anthropic.com" in email.lower() or "noreply@" in email.lower():
        return False, (f"git config user.email is {email!r}, which upload_video.py refuses "
                       f"(CLAUDE.md forbids authoring this repo's commits as Claude/Anthropic). "
                       f"Set it to the owner's address or media upload falls back and fails.")
    return True, f"git identity is {email}, so the permanent media host will accept a push"


def main():
    os.chdir(REPO)
    failures, advisories = [], []
    required_results = []
    receipt_target = Path(REPO).joinpath(*RECEIPT_REL.split("/"))
    try:
        receipt_target.unlink()
    except FileNotFoundError:
        pass

    def capture(identifier, label, exit_code, stdout="", stderr=""):
        required_results.append({
            "id": identifier,
            "label": label,
            "exit_code": int(exit_code),
            "stdout_sha256": _sha256_text(stdout),
            "stderr_sha256": _sha256_text(stderr),
        })

    ok, msg = git_identity_is_the_owners()
    if ok is False:
        failures.append(("git identity is the owner's", msg))
        print(f"  FAIL  git identity is the owner's: {msg}")
        capture("git_identity", "git identity is the owner's", 1, stderr=msg)
    elif ok:
        print(f"  OK    git identity is the owner's: {msg}")
        capture("git_identity", "git identity is the owner's", 0, stdout=msg)

    ok, msg = deliverables_are_fresh()
    if ok is False:
        failures.append(("deliverables are fresh", msg))
        print(f"  FAIL  deliverables are fresh: {msg}")
        capture("deliverables_manifest", "deliverables are fresh", 1, stderr=msg)
    else:
        print(f"  OK    deliverables are fresh: {msg}")
        capture("deliverables_manifest", "deliverables are fresh", 0, stdout=msg)

    ok, msg = evidence_is_current()
    if ok is False:
        failures.append(("terminal evidence is current", msg))
        print(f"  FAIL  terminal evidence is current: {msg}")
        capture("evidence_manifest", "terminal evidence is current", 1, stderr=msg)
    else:
        print(f"  OK    terminal evidence is current: {msg}")
        capture("evidence_manifest", "terminal evidence is current", 0, stdout=msg)

    for label, argv, required in CHECKS:
        p = subprocess.run(argv, capture_output=True, text=True)
        tail = (p.stdout or p.stderr).strip().splitlines()
        tail = tail[-1] if tail else "(no output)"
        if p.returncode == 0:
            print(f"  OK    {label}: {tail}")
        elif required:
            failures.append((label, tail))
            print(f"  FAIL  {label}: {tail}")
        else:
            advisories.append((label, tail))
            print(f"  NOTE  {label}: {tail}")
        if required:
            required_results.append({
                "id": _check_id(argv),
                "label": label,
                "exit_code": p.returncode,
                "stdout_sha256": _sha256_text(p.stdout or ""),
                "stderr_sha256": _sha256_text(p.stderr or ""),
            })

    print()
    if advisories:
        print(f"preflight: {len(advisories)} advisory check(s) reported something. They do "
              f"not block, but read them before spending a panel:")
        for label, tail in advisories:
            print(f"  - {label}: {tail}")
    if failures:
        print(f"preflight: BLOCKED on {len(failures)} check(s). Do NOT convene a panel.")
        print("  Every one of these is a fact a script found in seconds. A judge's "
              "attention is the most expensive thing in this loop and must not be spent "
              "on arithmetic.")
        return 1
    try:
        receipt = record_preflight_receipt(required_results)
    except PreflightContractError as exc:
        print(f"preflight: BLOCKED: receipt could not be recorded: {exc}")
        return 1
    print("preflight: clear. The mechanical checks have nothing left to say; "
          "what remains is taste, which is what the panel is for.")
    print(
        "preflight: receipt bound to "
        f"{receipt['binding']['delivery_manifest_digest'][:16]} -> {RECEIPT_REL}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
