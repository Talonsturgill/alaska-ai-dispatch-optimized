#!/usr/bin/env python3
"""Retired historical mixer; it cannot produce current Dispatch artifacts."""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "dispatch_mix_minerals.py: RETIRED: this historical mixer wrote the forbidden "
        "split audio/sfx_events.json ledger. Use scripts/dispatch_mix.py, which writes "
        "the sole canonical post-resolve out/dispatch/sfx_events.json ledger.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
