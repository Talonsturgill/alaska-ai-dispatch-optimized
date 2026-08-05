#!/usr/bin/env python3
"""FORMAT GATE SELF-TEST — prove the gates enforce the runtime format they claim to.

WHY THIS EXISTS (2026-08-05, the 90s -> 120s upgrade). A format change edits numbers in
three config files and rules in two gate scripts, and the failure mode is silent in BOTH
directions:

  - a rule that does not actually bind lets a padded two-minute film pass, and the whole
    point of the upgrade was that the extra thirty seconds must be earned;
  - a rule that binds too hard retroactively fails a legal SHORTER board, which breaks
    the archive and any re-run.

Neither shows up by running the gates on the one board you happen to have. So this
builds three boards from a real shipped one and asserts the gates react correctly:

  CONFORMING  a 120s board that satisfies every two-minute rule            -> must PASS
  PADDED      the 86s story with filler beats out to 120s and nothing else -> must FAIL,
              and must fail with the SPECIFIC two-minute rules, not by accident
  LEGACY      the shipped 86s board, untouched                             -> must PASS

Divergence/ledger failures are ignored throughout: a synthetic board reuses a real
board's composition on purpose, and the ledger is right to say so. This test is about the
RUNTIME rules only.

Usage: python3 scripts/format_gate_selftest.py
Exit 0 if every assertion holds.
"""
import copy, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
BASE = os.path.join(REPO, "archive", "dispatch-2026-08-05-net-comes-first", "storyboard.json")

# problems that are NOT about runtime and are expected on a synthetic board
IGNORE = ("differs on only", "spatial signature", "camera_strategy", "palette",
          "repeats the previous", "too close to")


def _pad(sb, end, target=120.0):
    """Model PADDING the way it actually happens.

    Not by stretching every timestamp: a proportional stretch moves the reveals and the
    loop payoff along with everything else, so the result still has a reveal in its final
    third and still pays its loop late. That is a re-timed film, not a padded one, and it
    would let this test pass while proving nothing.

    Real padding is the 90-second cut with thirty seconds of more-of-the-same on the end.
    The story lands where it always landed and the film keeps going. So: keep every
    original time, append legal filler beats out to the target, and add nothing else.
    Gaps are jittered because a fixed cadence would trip the metronome rule and the point
    is to be caught by the TWO-MINUTE rules, not by an unrelated one.
    """
    out = copy.deepcopy(sb)
    t, i, jitter = end, 0, [3.4, 4.6, 3.1, 4.9, 3.7, 4.3, 2.9, 4.7]
    while t < target - 1.0:
        t = round(t + jitter[i % len(jitter)], 2)
        i += 1
        b = copy.deepcopy(out["beats"][-1])
        b["t"] = t
        b["i"] = len(out["beats"]) + 1
        b["means"] = "more of the same"
        out["beats"].append(b)
    out["total_seconds"] = target
    return out


def _conform(sb):
    """Add exactly what the two-minute format asks for, and nothing else."""
    out = copy.deepcopy(sb)
    # the primary loop must reach into minute two
    out["open_loop"]["pay_t"] = 96.0
    out["open_loop"]["plant_t"] = 10.0
    # a second, staggered loop for the middle
    out["open_loop_2"] = {
        "plant_t": 44.0, "pay_t": 78.0,
        "what": "the counter stalls at a number nobody explains until the field season lands",
    }
    # a rehook inside the third drift window
    for b in out["beats"]:
        t0 = float(str(b["t"]).split("-")[0])
        if 88 <= t0 <= 104:
            b["rehook"] = "the count moves for the first time in the film"
            break
    # a scale-class reveal in the final third
    out["reveals"].append({"t": 104.0, "type": "scale-pullback", "hold_s": 0.6,
                           "what": "the drawer wall opens out to the whole collection"})
    # the throughline object
    out["throughline"] = {
        "object": "the beetle",
        "lands_in_button": "named, filled, and alone in frame",
        "states": [
            {"at_s": 1.0, "state": "fully drawn and form-shaded"},
            {"at_s": 30.0, "state": "stripped to a dashed contour"},
            {"at_s": 62.0, "state": "one contour among nine thousand"},
            {"at_s": 98.0, "state": "the contour closes and fills"},
            {"at_s": 116.0, "state": "named"},
        ],
    }
    return out


def run_gates(sb, tag):
    """Run both runtime gates on a board; return the list of runtime-relevant problems."""
    d = tempfile.mkdtemp(prefix=f"gate_{tag}_")
    p = os.path.join(d, "storyboard.json")
    json.dump(sb, open(p, "w"), indent=1)
    problems = []

    import importlib
    import flow_check
    importlib.reload(flow_check)
    R = flow_check.analyze(d)
    problems += R["problems"]

    r = subprocess.run([sys.executable, os.path.join(HERE, "storyboard_check.py"), p],
                       capture_output=True, text=True, cwd=REPO)
    for line in (r.stdout + r.stderr).splitlines():
        if line.strip().startswith("FAIL") and not any(k in line for k in IGNORE):
            problems.append(line.split("]", 1)[-1].strip())
    return [q for q in problems if not any(k in q for k in IGNORE)]


def main():
    base = json.load(open(BASE))
    beats = [float(str(b["t"]).split("-")[0]) for b in base["beats"]]
    end = max(beats)
    print(f"base board: {len(base['beats'])} beats, ends {end:.1f}s\n")

    fails = []

    # ---- LEGACY: the shipped 86s board must still pass the runtime rules ----
    legacy = run_gates(base, "legacy")
    print(f"LEGACY  ({end:.0f}s, untouched): {len(legacy)} runtime problem(s)")
    for q in legacy:
        print("    ", q[:150])
    if legacy:
        fails.append("LEGACY board must still pass the runtime rules after the format change")

    # ---- PADDED: stretched to 120s, nothing added. Must fail, for the right reasons ----
    padded = _pad(base, end, 120.0)
    pad_problems = run_gates(padded, "padded")
    print(f"\nPADDED  ({len(padded['beats'])} beats, story still ends at {end:.0f}s, "
          f"filler out to 120s): {len(pad_problems)} runtime problem(s)")
    for q in pad_problems:
        print("    ", q[:150])
    expect = {
        "throughline": "throughline",
        "second open loop": "OPEN LOOP 2",
        "third rehook window": "88-104",
        "reveal per third": "ONE PER THIRD",
        "loop payoff depth": "must land no earlier than",
    }
    for name, needle in expect.items():
        if not any(needle in q for q in pad_problems):
            fails.append(f"PADDED board was NOT caught by the {name} rule (no problem mentioning "
                         f"{needle!r})")
        else:
            print(f"    [ok] caught by the {name} rule")

    # ---- CONFORMING: a real two-minute board must pass ----
    good = _conform(padded)
    good_problems = run_gates(good, "conforming")
    print(f"\nCONFORMING (120s, every two-minute rule satisfied): "
          f"{len(good_problems)} runtime problem(s)")
    for q in good_problems:
        print("    ", q[:150])
    if good_problems:
        fails.append("CONFORMING 120s board must PASS the runtime rules")

    print()
    if fails:
        print("SELF-TEST FAILED:")
        for f in fails:
            print("  -", f)
        return 1
    print("SELF-TEST PASSED. The gates bind on a padded two-minute board, stay off a legal "
          "shorter one, and accept a conforming one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
