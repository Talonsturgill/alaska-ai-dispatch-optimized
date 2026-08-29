#!/usr/bin/env python3
"""Write the Gmail draft receipt that scripts/no_exit.py's delivery leg requires.

WHY (2026-08-03). no_exit.py used to ask only whether the encoded BYTES existed. That
let a run finish both cuts, look at them, and still stop without the draft that puts the
film in front of the owner, which is exactly the state the 2026-08-03 run stopped in.
The gate now asks for this receipt instead, so "delivered" means a draft exists rather
than a file exists.

Call this IMMEDIATELY after the Gmail connector returns a draft id.

  python3 scripts/record_draft.py --draft-id <id> --to docket@alaskaaihq.com \\
      --subject "<subject>" [--square-url URL] [--vertical-url URL]
"""
import argparse, datetime as dt, json, os, sys

from canary_guard import CanarySafetyError, require_action

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "out", "dispatch")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft-id", required=True)
    ap.add_argument("--to", default="docket@alaskaaihq.com")
    ap.add_argument("--subject", default="")
    ap.add_argument("--square-url", default="")
    ap.add_argument("--vertical-url", default="")
    a = ap.parse_args()

    try:
        require_action("gmail_draft_receipt", a.to)
    except CanarySafetyError as exc:
        print(f"record_draft: {exc}", file=sys.stderr)
        return 42

    if not a.draft_id.strip():
        print("refusing to write a receipt with no draft id", file=sys.stderr)
        return 1

    receipt = {
        "draft_id": a.draft_id,
        "to": a.to,
        "subject": a.subject,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "square_url": a.square_url,
        "vertical_url": a.vertical_url,
        "note": "Written only after the Gmail connector accepted the draft. "
                "no_exit.py's delivery leg reads this.",
    }
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "gmail_draft_receipt.json")
    with open(path, "w") as fh:
        json.dump(receipt, fh, indent=2)
    print(f"wrote {path}  draft={a.draft_id} to={a.to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
