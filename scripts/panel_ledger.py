#!/usr/bin/env python3
"""Persist every panel card, so a re-grade can carry the judge's own previous one.

WHY THIS EXISTS (2026-08-09).
-----------------------------
`config/panel_protocol.md` was written after a run in which the panel's numbers drifted
downward across re-grades of a film that was measurably improving. It names three causes and
prescribes a fix for each. The second one is this:

    "A re-grade had no memory of its own previous card. Nothing forced a judge to notice they
     had moved an axis by two points on an unchanged element, so re-calibration happened
     silently and read as a finding about the film.
     FIX: a re-grade prompt MUST carry that judge's own previous axis scores."

That fix was never implemented as a mechanism. It was implemented as an intention: the
orchestrator held the cards in its context and pasted them into the next round's prompt. That
works until the context is compacted, and on a long run the context is ALWAYS compacted. This
run reached round 4 able to recover three axis scores out of thirty-three, from a summary,
because the only copy of round 3 lived in a conversation that no longer existed.

A protocol requirement that depends on the orchestrator remembering is not a requirement, it is
a hope. The cards are small, they are JSON, and there is no reason for them to live anywhere but
on disk.

WHAT IT DOES
    record   store one judge's card for a round, and refuse to overwrite a different card
    previous print the judge's most recent PRIOR card as the block a re-grade prompt needs
    median   print the round's median weighted total and whether every judge cleared the bar,
             reading the threshold from config/dispatch_rubric.yaml rather than restating it

    python3 scripts/panel_ledger.py record   --round 4 --judge 1 --card out/panel/round4/j1.json
    python3 scripts/panel_ledger.py previous --round 4 --judge 1
    python3 scripts/panel_ledger.py median   --round 4
"""
import argparse
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LEDGER = os.path.join(REPO, "out", "panel", "cards.json")
RUBRIC = os.path.join(REPO, "config", "dispatch_rubric.yaml")


def _load():
    if not os.path.exists(LEDGER):
        return {"note": "every panel card this run, keyed 'r<round>j<judge>'. Written by "
                        "scripts/panel_ledger.py so a re-grade can carry the judge's own "
                        "previous card across a context compaction.",
                "cards": {}}
    return json.load(open(LEDGER))


def _save(d):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(d, open(LEDGER, "w"), indent=1)


def threshold() -> float:
    """Read the bar, never restate it. The 2026-08-06 lesson: a number restated in a second
    place will eventually be wrong in one of them, and this is the number that decides whether
    a film ships."""
    for line in open(RUBRIC):
        s = line.strip()
        if s.startswith("ship_threshold:"):
            return float(s.split(":", 1)[1].split("#")[0].strip())
    sys.exit("panel_ledger: no ship_threshold in the rubric, which is not a thing to guess at")


def cmd_record(a) -> int:
    card = json.load(open(a.card))
    for req in ("axes", "weighted_total", "ship"):
        if req not in card:
            sys.exit(f"panel_ledger: card is missing '{req}', so it is not a card")
    d = _load()
    key = f"r{a.round}j{a.judge}"
    if key in d["cards"] and d["cards"][key] != card:
        # A round is a measurement of specific bytes. Silently replacing one loses the trail
        # that makes drift visible at all, which is the entire point of this file.
        sys.exit(f"panel_ledger: {key} is already recorded with a DIFFERENT card. "
                 f"A round grades one cut. Use a new round number for a new cut.")
    card["_round"], card["_judge"] = a.round, a.judge
    d["cards"][key] = card
    _save(d)
    print(f"panel_ledger: recorded {key}  total {card['weighted_total']}  "
          f"ship {card['ship']}  ({len(card['axes'])} axes)")
    return 0


def cmd_previous(a) -> int:
    d = _load()
    prior = [(int(k.split("j")[0][1:]), v) for k, v in d["cards"].items()
             if v.get("_judge") == a.judge and v.get("_round", 0) < a.round]
    if not prior:
        print(f"NO PRIOR CARD for judge {a.judge} before round {a.round}. "
              f"Grade fresh; there is nothing to declare a move against.")
        return 0
    r, card = max(prior, key=lambda t: t[0])
    print(f"YOUR OWN PREVIOUS CARD (judge {a.judge}, round {r}). "
          f"weighted_total {card['weighted_total']}, ship {card['ship']}.")
    for name, sc in card["axes"].items():
        print(f"  {sc:>5}  {name}")
    print("\nAny axis you move by more than 1.0 from the above, you must name the element that\n"
          "changed and say whether the film moved or your standard did. Both are legitimate.\n"
          "Silently doing the second while reporting the first is not.")
    return 0


def cmd_median(a) -> int:
    d = _load()
    cards = sorted((v for v in d["cards"].values() if v.get("_round") == a.round),
                   key=lambda c: c["weighted_total"])
    if not cards:
        sys.exit(f"panel_ledger: no cards recorded for round {a.round}")
    bar = threshold()
    totals = [c["weighted_total"] for c in cards]
    med = totals[len(totals) // 2] if len(totals) % 2 else \
        (totals[len(totals) // 2 - 1] + totals[len(totals) // 2]) / 2
    blockers = [(c["_judge"], b) for c in cards for b in c.get("hard_blockers", []) or []]
    print(f"round {a.round}: {len(cards)} card(s)  totals {totals}  MEDIAN {med:.2f}  bar {bar}")
    for c in cards:
        print(f"  judge {c['_judge']}: {c['weighted_total']:.2f}  ship={c['ship']}")
    for j, b in blockers:
        what = b.get("what", b) if isinstance(b, dict) else b
        print(f"  HARD BLOCKER from judge {j}: {what}")
    if blockers:
        print("\nA hard blocker fails the film at ANY score. Median is not the question yet.")
        return 1
    if med < bar:
        print(f"\nBELOW BAR by {bar - med:.2f}. This is an instruction to re-enter the loop.")
        return 1
    print("\nMedian clears the bar and no judge raised a hard blocker.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("--round", type=int, required=True)
    r.add_argument("--judge", type=int, required=True); r.add_argument("--card", required=True)
    r.set_defaults(fn=cmd_record)
    p = sub.add_parser("previous"); p.add_argument("--round", type=int, required=True)
    p.add_argument("--judge", type=int, required=True); p.set_defaults(fn=cmd_previous)
    m = sub.add_parser("median"); m.add_argument("--round", type=int, required=True)
    m.set_defaults(fn=cmd_median)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
