#!/usr/bin/env python3
"""Bind the canonical operator preview to a fully validated ship verdict."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

from deliverable_contract import (
    DeliverableContractError,
    contract_digest,
    require_publication_url,
    terminal_preview_roles,
)
from run_guard import load_stamp
from strict_json import StrictJSONError, load_path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW_REL = "out/dispatch/dispatch-preview.html"
RECEIPT_REL = "out/dispatch/delivery_preview_receipt.json"
SCHEMA_VERSION = 2


class DeliveryPreviewError(RuntimeError):
    pass


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "a" and isinstance(values.get("href"), str):
            self.hrefs.append(values["href"])
        if tag.lower() in {"img", "video", "source"} and isinstance(values.get("src"), str):
            self.sources.append(values["src"])


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
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


def _paths(root: str | Path):
    base = Path(root).resolve()
    return (
        base,
        base.joinpath(*PREVIEW_REL.split("/")),
        base.joinpath(*RECEIPT_REL.split("/")),
    )


def _publication_state(
    base: Path,
    manifest: dict[str, Any],
    verifier: Callable[[str, str], Any] | None,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    try:
        roles = terminal_preview_roles(root=base)
    except (DeliverableContractError, StrictJSONError, OSError) as exc:
        raise DeliveryPreviewError(f"terminal preview role config is invalid: {exc}") from None
    publications = manifest.get("publications")
    if not isinstance(publications, dict):
        raise DeliveryPreviewError("deliverables manifest publications must be an object")
    facts: dict[str, Any] = {}
    for role in roles:
        receipt = publications.get(role)
        if not isinstance(receipt, dict) or not isinstance(receipt.get("url"), str):
            raise DeliveryPreviewError(f"mandatory publication {role} is missing")
        url = receipt["url"]
        try:
            verified = (
                verifier(role, url) if verifier is not None
                else require_publication_url(role, url, root=base)
            )
        except (DeliverableContractError, OSError, ValueError) as exc:
            raise DeliveryPreviewError(f"mandatory publication {role} failed full-byte verification: {exc}") from None
        if verified is None:
            raise DeliveryPreviewError(f"mandatory publication {role} verifier returned no receipt")
        artifact = manifest.get("artifacts", {}).get(role)
        facts[role] = {
            "url": url,
            "artifact_sha256": artifact.get("sha256") if isinstance(artifact, dict) else None,
            "media_commit_sha": receipt.get("media_commit_sha"),
        }
    return facts, roles


def _html_bindings(path: Path, manifest: dict[str, Any], roles: tuple[str, ...]) -> dict[str, Any]:
    try:
        html = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DeliveryPreviewError(f"terminal preview cannot be read: {exc}") from None
    if not html.strip():
        raise DeliveryPreviewError("terminal preview HTML is empty")
    parser = _LinkParser()
    try:
        parser.feed(html)
        parser.close()
    except (TypeError, ValueError) as exc:
        raise DeliveryPreviewError(f"terminal preview HTML cannot be parsed: {exc}") from None
    bindings: dict[str, Any] = {}
    for role in roles:
        receipt = manifest["publications"][role]
        url = receipt["url"]
        media_type = manifest["artifacts"][role]["media_type"]
        locations = parser.hrefs if media_type == "video" else parser.sources
        count = locations.count(url)
        if count != 1:
            attribute = "a[href]" if media_type == "video" else "img/video/source[src]"
            raise DeliveryPreviewError(
                f"terminal preview must contain the exact {role} URL once in {attribute}; found {count}"
            )
        bindings[role] = {"url": url, "location": "href" if media_type == "video" else "src"}
    return bindings


def record_delivery_preview(
    path: str | Path,
    *,
    ship_state: dict[str, Any],
    root: str | Path = ROOT,
    publication_verifier: Callable[[str, str], Any] | None = None,
) -> dict[str, Any]:
    base, canonical, receipt_path = _paths(root)
    supplied = Path(path).resolve()
    if supplied != canonical:
        raise DeliveryPreviewError(f"terminal preview must use canonical path {PREVIEW_REL}")
    if not canonical.is_file() or canonical.is_symlink():
        raise DeliveryPreviewError("terminal preview is missing or unsafe")
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        raise DeliveryPreviewError("run stamp is missing or unreadable")
    verdict_path = base / "out" / "dispatch" / "panel_verdict.json"
    if not verdict_path.is_file() or verdict_path.is_symlink():
        raise DeliveryPreviewError("ship verdict is missing or unsafe")
    manifest = ship_state["manifest"]
    publication_facts, required_roles = _publication_state(
        base, manifest, publication_verifier,
    )
    html_bindings = _html_bindings(canonical, manifest, required_roles)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "preview": {
            "path": PREVIEW_REL,
            "bytes": canonical.stat().st_size,
            "sha256": _sha(canonical),
        },
        "ship_verdict": {
            "path": "out/dispatch/panel_verdict.json",
            "bytes": verdict_path.stat().st_size,
            "sha256": _sha(verdict_path),
            "median": ship_state["median"],
            "threshold": ship_state["threshold"],
        },
        "manifest_digest": contract_digest(manifest),
        "mandatory_publications": publication_facts,
        "html_bindings": html_bindings,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_json(receipt_path, payload)
    return payload


def validate_delivery_preview(
    *,
    root: str | Path = ROOT,
    ship_state: dict[str, Any] | None = None,
    publication_verifier: Callable[[str, str], Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    base, canonical, receipt_path = _paths(root)
    if ship_state is None:
        try:
            from ship_gate import GateInputError, require_ship_verdict
            ship_state = require_ship_verdict(verify_blankness=True)
        except GateInputError as exc:
            return None, [f"ship verdict is not fully valid: {exc}"]
    try:
        raw = load_path(receipt_path, label="delivery preview receipt")
    except (StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(raw, dict):
        return None, ["delivery preview receipt must be a JSON object"]
    if not canonical.is_file() or canonical.is_symlink():
        return raw, ["canonical delivery preview is missing or unsafe"]
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        return raw, ["run stamp is missing or unreadable"]
    verdict_path = base / "out" / "dispatch" / "panel_verdict.json"
    if not verdict_path.is_file() or verdict_path.is_symlink():
        return raw, ["ship verdict is missing or unsafe"]
    manifest = ship_state["manifest"]
    try:
        publication_facts, required_roles = _publication_state(
            base, manifest, publication_verifier,
        )
        html_bindings = _html_bindings(canonical, manifest, required_roles)
    except DeliveryPreviewError as exc:
        return raw, [str(exc)]
    expected = {
        "schema_version": SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "preview": {"path": PREVIEW_REL, "bytes": canonical.stat().st_size, "sha256": _sha(canonical)},
        "ship_verdict": {
            "path": "out/dispatch/panel_verdict.json",
            "bytes": verdict_path.stat().st_size,
            "sha256": _sha(verdict_path),
            "median": ship_state["median"],
            "threshold": ship_state["threshold"],
        },
        "manifest_digest": contract_digest(manifest),
        "mandatory_publications": publication_facts,
        "html_bindings": html_bindings,
    }
    problems = [
        f"delivery preview receipt {key} does not match current ship state"
        for key, value in expected.items() if raw.get(key) != value
    ]
    if set(raw) != set(expected) | {"recorded_at"}:
        problems.append("delivery preview receipt fields are not canonical")
    return raw, problems


def require_delivery_preview(*, root: str | Path = ROOT, ship_state=None):
    receipt, problems = validate_delivery_preview(root=root, ship_state=ship_state)
    if receipt is None or problems:
        raise DeliveryPreviewError("; ".join(problems or ["delivery preview is unavailable"]))
    return receipt
