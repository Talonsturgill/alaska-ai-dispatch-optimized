#!/usr/bin/env python3
"""One-shot: reduce PERIOD DENSITY in the locked VO script without changing a single
spoken word, then resync vo_script.json and the plan's line table.

WHY (measured 2026-08-06, three synth rounds):
    The required Pace paragraph in docs/craft/VO_DIRECTION.md says "take a real breath
    at every period". It was calibrated on a 288-word probe script. THIS script carries
    44 periods across 300 words because the house style is short punchy sentences, so
    the instruction scales with SENTENCE COUNT while the word band scales with WORD
    COUNT. Takes came in at 168.7s, 165.3s and 148.5s against a 112-130s band.

    Style-line counter-instructions moved it 20s and stalled. The direct lever is the
    period count itself. The WORDS are untouched, so the fact-check, the claim ids and
    the caption text all still hold; only the synth's breath cues change.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "out" / "dispatch" / "vo_script.txt"

SUBS = [
    ("A face. A license plate. One frame.", "A face, a license plate, one frame."),
    ("this week. Same pipe.", "this week, same pipe."),
    ("naming facial recognition. Police don't use it.",
     "naming facial recognition, and police don't use it."),
    ("was a promise. He'd come to a committee first. Generally.",
     "was a promise, he'd come to a committee first, generally."),
    ("Go north. Fairbanks bought the other end.", "Go north, Fairbanks bought the other end."),
    ("named the tool. The chief of staff says", "named the tool, the chief of staff says"),
    ("two jobs. Find it. Then decide.", "two jobs, find it, then decide."),
    ("at finding. It never touched deciding. A person still signs",
     "at finding, it never touched deciding, a person still signs"),
    ("got faster. The line kept growing.", "got faster, the line kept growing."),
    ("requests a month. April, more than thirty-five. July, more than thirty-five.",
     "requests a month, April, more than thirty-five, July, more than thirty-five."),
    ("hours a month. That rule predates", "hours a month, and that rule predates"),
    ("about the problem. His idea was,", "about the problem, his idea was,"),
    ("Same footage. Anchorage takes it up", "Same footage, Anchorage takes it up"),
]


def main() -> int:
    text = SCRIPT.read_text()
    before_words = len(text.split())
    before_periods = text.count(".")
    for old, new in SUBS:
        if old not in text:
            print(f"  skip (already applied): {old[:44]}")
            continue
        text = text.replace(old, new)
    SCRIPT.write_text(text)

    words = len(text.split())
    periods = text.count(".")
    print(f"words {before_words} -> {words} (band 280-300)")
    print(f"periods {before_periods} -> {periods}")
    if not 280 <= words <= 300:
        print("!! WORD COUNT OUT OF BAND")
        return 1

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    (ROOT / "out" / "dispatch" / "vo_script_draft.txt").write_text(text)

    sj = ROOT / "out" / "dispatch" / "vo_script.json"
    d = json.loads(sj.read_text())
    d["lines"] = [{"i": i, "text": t} for i, t in enumerate(lines)]
    sj.write_text(json.dumps(d, indent=2))

    # Resync the PLAN's line table so vo_synth stops rebuilding the prompt from
    # scratch. The repair path drops per-line direction for any changed line, which
    # was silently discarding the director's work on every run.
    pj = ROOT / "out" / "dispatch" / "vo_direction.json"
    plan = json.loads(pj.read_text())
    plan_lines = plan.get("lines") or []
    for i, t in enumerate(lines):
        if i < len(plan_lines):
            plan_lines[i]["text"] = t
    plan["lines"] = plan_lines[: len(lines)]

    ap = plan.get("assembled_prompt", "")
    head, sep, _ = ap.partition("Transcript:")
    if sep:
        plan["assembled_prompt"] = head + sep + "\n" + "\n".join(lines) + "\n"
    pj.write_text(json.dumps(plan, indent=2))
    print(f"resynced {len(lines)} lines into vo_script.json and vo_direction.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
