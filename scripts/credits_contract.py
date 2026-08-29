#!/usr/bin/env python3
"""Authoritative, deterministic source-label and credits-duration contract.

Both the scene author and the delivered-credits gate import this module.  A
label is therefore never accepted merely because one identifier happens to
occur somewhere in ``sources.json``: the complete ordered label list must be
derived from the complete strict source ledger.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

CONTRACT_VERSION = 1
CREDITS_MIN_S = 10.0
CREDITS_TAIL_S = 2.3
CREDITS_S = CREDITS_MIN_S + CREDITS_TAIL_S


class CreditsSourceError(RuntimeError):
    pass


def _source_entries(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise CreditsSourceError("sources ledger must be a JSON object")
    entries = document.get("sources")
    if not isinstance(entries, list) or not entries:
        raise CreditsSourceError("sources.sources must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CreditsSourceError(f"sources.sources[{index}] must be an object")
        source_id = entry.get("id")
        title = entry.get("title")
        url = entry.get("url")
        used = entry.get("used_in_film", True)
        if not isinstance(source_id, str) or not source_id.strip() or source_id != source_id.strip():
            raise CreditsSourceError(f"sources.sources[{index}].id must be a trimmed string")
        if source_id in seen_ids:
            raise CreditsSourceError(f"sources ledger has duplicate source id {source_id!r}")
        seen_ids.add(source_id)
        if not isinstance(title, str) or not title.strip():
            raise CreditsSourceError(f"sources.sources[{index}].title must be a non-empty string")
        if not isinstance(url, str) or not url.strip() or url != url.strip():
            raise CreditsSourceError(f"sources.sources[{index}].url must be a trimmed string")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise CreditsSourceError(f"sources.sources[{index}].url must be an HTTP(S) URL")
        if url in seen_urls:
            raise CreditsSourceError(f"sources ledger has duplicate primary URL {url!r}")
        seen_urls.add(url)
        if not isinstance(used, bool):
            raise CreditsSourceError(f"sources.sources[{index}].used_in_film must be boolean")
        if used:
            normalized.append(entry)
    if not normalized:
        raise CreditsSourceError("sources ledger has no sources used in the film")
    return normalized


def derive_source_labels(document: Any) -> list[str]:
    """Return the exact ordered phone-readable labels rendered on the end card."""
    awards: list[str] = []
    papers: list[str] = []
    other: list[str] = []
    seen_labels: set[str] = set()
    for entry in _source_entries(document):
        url = entry["url"]
        title = entry["title"]
        match = re.search(r"/awards/(\d+)\.json", url) or re.search(r"AWD_ID=(\d+)", url)
        if not match:
            match = re.search(r"\bAwards?\s+(\d{7,})", title)
        if match:
            if match.group(1) not in awards:
                awards.append(match.group(1))
            continue
        match = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url)
        if match:
            if match.group(1) not in papers:
                papers.append(match.group(1))
            continue
        if "eutils.ncbi" in url or "esearch.fcgi" in url:
            label = "PUBMED QUERY"
        elif "awards.json?keyword" in url:
            continue
        elif "dggs.alaska.gov" in url:
            label = "ALASKA DGGS"
        elif "epscor" in url:
            label = "NSF EPSCOR"
        else:
            label = re.sub(r"^www\.", "", urlparse(url).netloc).upper()
        if label and label not in seen_labels:
            seen_labels.add(label)
            other.append(label)

    labels: list[str] = []
    if awards:
        labels.append(("NSF AWARDS " if len(awards) > 1 else "NSF AWARD ") + ", ".join(awards))
    if papers:
        labels.append("PUBMED " + ", ".join(papers))
    labels.extend(other)
    if not labels:
        raise CreditsSourceError("sources ledger derives no end-card source labels")
    if len(labels) > 6:
        labels = labels[:5] + [f"AND {len(labels) - 5} MORE AT ALASKAAIHQ.COM"]
    return labels
