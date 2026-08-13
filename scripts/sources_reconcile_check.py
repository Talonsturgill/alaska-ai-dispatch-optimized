#!/usr/bin/env python3
"""
DOES THE SHIPPED SOURCE LEDGER ACCOUNT FOR EVERY CLAIM THE RECORD SOURCES?

WHY THIS EXISTS (2026-08-13, round 8). All three panel judges independently docked Accuracy
for the same bookkeeping defect and none of the fourteen gates in this repo could see it:
out/dispatch/sources.json had no `s6`, carried no entry at all for c14 or c21, and disagreed
with claims.json about c17's URL. The ids jumped s5 -> s7, which is the tell that an entry was
pulled without reconciling, and a silent hole in an id sequence is exactly the kind of thing a
human reads past and a checker does not.

The two files jointly constitute the accuracy record. Neither is authoritative alone, so the
only useful question is whether they agree, and nothing was asking it.

NOTE ON SCOPE. This checks the LEDGER, not the end card. They are different obligations: the
ledger must cover every sourced claim so the record is auditable, while the end card may only
cite sources for claims the film actually makes. Entries carry `used_in_film` for that, and
build_scenes.py reads the subset.

Exit 1 on a real divergence. Advisory notes do not fail.
"""
import json, os, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "out", "dispatch")


def main() -> int:
    try:
        claims_doc = json.load(open(os.path.join(OUT, "claims.json")))
        ledger = json.load(open(os.path.join(OUT, "sources.json")))
    except FileNotFoundError as e:
        print(f"sources_reconcile_check: cannot read {e.filename}")
        return 1

    cl = claims_doc.get("claims", claims_doc) if isinstance(claims_doc, dict) else claims_doc
    claims = cl if isinstance(cl, list) else list(cl.values())
    by_id = {str(c["id"]): c for c in claims if c.get("id")}
    entries = ledger.get("sources", [])

    problems, notes = [], []

    covered = set()
    for e in entries:
        covered.update(e.get("claims") or [])
    sourced = {k for k, v in by_id.items() if v.get("source")}

    missing = sorted(sourced - covered, key=lambda x: int(x[1:]))
    if missing:
        problems.append(
            f"{len(missing)} claim(s) carry a source in claims.json and have NO entry in the "
            f"ledger the film ships: {', '.join(missing)}. Add an entry, or drop the claim.")

    orphan = sorted(covered - set(by_id), key=lambda x: str(x))
    if orphan:
        problems.append(f"ledger cites claim(s) that do not exist in claims.json: {', '.join(orphan)}")

    # a hole in the id sequence is how the c14/c21 gap got in and stayed in
    ids = [e.get("id", "") for e in entries]
    want = [f"s{i}" for i in range(1, len(entries) + 1)]
    if ids != want:
        problems.append(f"ledger ids are not contiguous. Got {ids}, expected {want}. A gap means "
                        f"an entry was pulled without reconciling.")

    # the URL each side records for the same claim should agree, or the entry should say why
    for e in entries:
        urls = e.get("urls") or ([e["url"]] if e.get("url") else [])
        for cid in e.get("claims") or []:
            src = (by_id.get(cid) or {}).get("source")
            if src and src not in urls:
                problems.append(
                    f"{cid}: claims.json cites {src} but ledger entry {e.get('id')} carries "
                    f"{urls}. List both on the entry's `urls` if it covers two documents.")

    on_card = [e for e in entries if e.get("used_in_film", True)]
    notes.append(f"{len(entries)} ledger entries covering {len(covered)} claim(s); "
                 f"{len(on_card)} cited on the end card, {len(entries) - len(on_card)} held off it "
                 f"because their claims are not in the cut.")

    for n in notes:
        print(f"  {n}")
    if problems:
        print(f"\nsources_reconcile_check: {len(problems)} divergence(s).")
        for p in problems:
            print(f"  FAIL  {p}")
        print("\nThe two files jointly ARE the accuracy record. A claim the ledger does not")
        print("account for is a claim a reader cannot check, which is the whole point of")
        print("shipping sources with the film.")
        return 1
    print(f"sources_reconcile_check: ledger accounts for all {len(sourced)} sourced claim(s), "
          f"ids contiguous, every URL agrees with claims.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
