#!/usr/bin/env python3
"""Persist and revalidate strict rubric-derived video judge cards.

The ledger never trusts a judge-supplied total, axis list, weight, threshold, or
ship boolean. ``video_judge_contract`` recomputes all of those from the current
rubric and current run bytes before a card enters or leaves the ledger.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import tempfile
from pathlib import Path

from strict_json import StrictJSONError, load_path
from video_judge_contract import (
    VideoJudgeContractError,
    require_three_cards,
    rubric_contract,
    sha256_file,
    validate_card,
)

ROOT = Path(__file__).resolve().parent.parent
LEDGER_REL = "out/dispatch/panel_cards.json"
LEDGER_SCHEMA_VERSION = 1


class PanelLedgerError(RuntimeError):
    pass


def _target(root: Path) -> Path:
    return root.joinpath(*LEDGER_REL.split("/"))


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


def _load(root: Path) -> dict:
    path = _target(root)
    if not path.exists():
        return {"schema_version": LEDGER_SCHEMA_VERSION, "cards": {}}
    try:
        value = load_path(path, label="panel card ledger")
    except (StrictJSONError, OSError) as exc:
        raise PanelLedgerError(str(exc)) from None
    if (
        not isinstance(value, dict) or set(value) != {"schema_version", "cards"}
        or value.get("schema_version") != LEDGER_SCHEMA_VERSION
        or not isinstance(value.get("cards"), dict)
    ):
        raise PanelLedgerError("panel card ledger fields/schema are not canonical")
    return value


def record_card(card_path: str | Path, *, round_number: int, root: str | Path = ROOT) -> dict:
    base = Path(root).resolve()
    if isinstance(round_number, bool) or not isinstance(round_number, int) or round_number < 1:
        raise PanelLedgerError("panel round must be a positive integer")
    card = validate_card(card_path, root=base)
    path = Path(card_path)
    if not path.is_absolute():
        path = base / path
    path = path.resolve(strict=True)
    fact = {
        "path": path.relative_to(base).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "judge_id": card["judge_id"],
        "weighted_total": card["weighted_total"],
    }
    ledger = _load(base)
    key = f"r{round_number}:{card['judge_id']}"
    existing = ledger["cards"].get(key)
    if existing is not None and existing != fact:
        raise PanelLedgerError(
            f"{key} already records different bytes; a changed cut/card requires a new round"
        )
    ledger["cards"][key] = fact
    _atomic_json(_target(base), ledger)
    return fact


def round_cards(round_number: int, *, root: str | Path = ROOT) -> list[dict]:
    base = Path(root).resolve()
    ledger = _load(base)
    prefix = f"r{round_number}:"
    facts = [fact for key, fact in ledger["cards"].items() if key.startswith(prefix)]
    if len(facts) != 3:
        raise PanelLedgerError(
            f"round {round_number} requires exactly three unique cards; found {len(facts)}"
        )
    paths = []
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != {
            "path", "bytes", "sha256", "judge_id", "weighted_total",
        }:
            raise PanelLedgerError("panel card ledger entry fields are not canonical")
        path = base.joinpath(*str(fact.get("path", "")).split("/"))
        if not path.is_file() or path.is_symlink():
            raise PanelLedgerError(f"recorded panel card is missing or unsafe: {fact.get('path')}")
        if path.stat().st_size != fact.get("bytes") or sha256_file(path) != fact.get("sha256"):
            raise PanelLedgerError(f"recorded panel card bytes changed: {fact.get('path')}")
        paths.append(fact["path"])
    return require_three_cards(paths, root=base)


def round_result(round_number: int, *, root: str | Path = ROOT) -> dict:
    cards = round_cards(round_number, root=root)
    totals = [float(card["weighted_total"]) for card in cards]
    blockers = [
        {"judge_id": card["judge_id"], "blocker": blocker}
        for card in cards for blocker in card["hard_blockers"]
    ]
    threshold = rubric_contract(root=root)["ship_threshold"]
    median = float(statistics.median(totals))
    return {
        "round": round_number,
        "cards": cards,
        "totals": totals,
        "median": median,
        "threshold": threshold,
        "hard_blockers": blockers,
        "pass": not blockers and median >= threshold,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--round", type=int, required=True)
    record.add_argument("--card", required=True)
    median = sub.add_parser("median")
    median.add_argument("--round", type=int, required=True)
    args = parser.parse_args()
    try:
        if args.command == "record":
            fact = record_card(args.card, round_number=args.round)
            print(
                f"panel_ledger: recorded r{args.round}:{fact['judge_id']} "
                f"{fact['sha256'][:16]} total={fact['weighted_total']:.3f}"
            )
            return 0
        result = round_result(args.round)
        print(
            f"panel_ledger: round {args.round} totals={result['totals']} "
            f"median={result['median']:.3f} threshold={result['threshold']:.3f} "
            f"blockers={len(result['hard_blockers'])}"
        )
        return 0 if result["pass"] else 1
    except (PanelLedgerError, VideoJudgeContractError, OSError, ValueError) as exc:
        print(f"panel_ledger: FAIL: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
