#!/usr/bin/env python3
"""Publish this run's Dispatch video into the alaskaaihq.com /videos feed.

The site (Talonsturgill/alaskaaicarousels, GitHub Pages from docs/ on main) has a
TikTok-style vertical feed at /videos driven by docs/videos/videos.json. This script
prepends the new run's entry to that manifest and pushes it to main, so the site
feed updates the same day the video ships. Idempotent: re-running with the same
--id replaces the existing entry in place instead of duplicating it.

Called by the dispatch routine in Phase 7 (after upload_video.py verifies the
permanent 9:16/poster links, since those exact URLs go into the manifest):

  python3 scripts/publish_feed.py \
    --id 2026-07-22-checkpoint-lever \
    --date 2026-07-22 \
    --title "The Checkpoint Lever" \
    --caption "The Air Force offered 4,700 acres ... still open." \
    --video-url  "https://raw.githubusercontent.com/.../dispatch_2026-07-22_9x16.mp4" \
    --poster-url "https://raw.githubusercontent.com/.../dispatch_2026-07-22_poster.png"

Exit 0 = manifest updated AND pushed. Non-zero = NOT live; the routine must surface
the failure in the Gmail draft (owner may need to grant the routine environment
push access to the alaskaaicarousels repo) rather than silently skipping — the feed
staying current is part of the deliverable, but a feed-push failure must NOT roll
back or block the already-shipped video/email.
"""
import argparse, json, re, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.parse import urlparse

REPO = "https://github.com/Talonsturgill/alaskaaicarousels.git"
MANIFEST = "docs/videos/videos.json"


def clean_text(field, s):
    """A display string bound for the /videos feed. The player renders title and
    caption into card.innerHTML, so a value carrying markup is a script on the
    alaskaaihq.com origin. The player now escapes on output, but the feed should
    not carry markup in the first place: reject angle brackets and control
    characters here, at the trust boundary, so a bad value fails the publish
    (surfaced in the draft) instead of shipping. A headline that needs a literal
    < or > can spell it 'under' / 'over'."""
    s = (s or "").strip()
    if re.search(r"[<>]", s) or any(ord(c) < 0x20 and c not in "\t" for c in s):
        sys.exit(f"publish_feed: --{field} carries markup or control characters, "
                 f"rephrase it: {s!r}")
    return s


def clean_url(field, u, required):
    """A URL bound for a poster/src attribute in the feed. It must be a real
    http(s) URL with no quote, space, or angle bracket, the characters that would
    break out of the attribute it is written into. Empty is allowed for the
    optional URLs."""
    u = (u or "").strip()
    if not u:
        if required:
            sys.exit(f"publish_feed: --{field} is required")
        return u
    p = urlparse(u)
    if p.scheme not in ("http", "https") or not p.netloc or re.search(r"[\"'<>\s]", u):
        sys.exit(f"publish_feed: --{field} is not a clean http(s) URL: {u!r}")
    return u


def run(cmd, cwd=None, ok_fail=False):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0 and not ok_fail:
        sys.exit(f"publish_feed: FAILED: {' '.join(cmd)}\n{r.stderr.strip()[:800]}")
    return r


def require_ship_gate():
    """Refuse to publish a cut the 3-judge panel has not passed.

    WHY THIS EXISTS (2026-08-06, and it was live on the public site when it was found).

    The routine's Phase 7 has always had the right ORDER on paper: ship_gate.py check, and
    only then encode, upload, publish. On 2026-08-06 the run pushed the media at 07:42,
    added the feed entry at 07:45, and convened the panel at 08:13, which scored the cut
    5.12 against a 9.0 bar and returned "BELOW BAR. THIS CUT DOES NOT SHIP." For the half
    hour in between, and for every hour after it, alaskaaihq.com/videos served a film with
    a raw \\u2019 escape painted on screen inside a quote attributed to a named official.

    Nothing malfunctioned. The run simply did Phase 7 before Phase 6 finished, and every
    guard in the repo was somewhere else: ship_gate refuses SHIPS but only when something
    calls it, and no_exit refuses STOPS. The publish step is the single most outward-facing
    action this machine takes — it is the one that reaches strangers — and it was the one
    step that would run on anything you handed it.

    Prose in the routine cannot fix this, because prose is what failed. The guard goes in
    the publish path, where a run that skips ahead hits it whether or not it remembered to.

    Asymmetric, like the others: this refuses PUBLISHES and can never cause one. If the
    gate is missing or unreadable, that is a refusal too — an unverifiable pass is not one.
    """
    gate = Path(__file__).resolve().parent / "ship_gate.py"
    if not gate.exists():
        sys.exit("publish_feed: scripts/ship_gate.py is missing. Refusing to publish a cut "
                 "whose quality gate cannot be run.")
    p = subprocess.run([sys.executable, str(gate), "check"], capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stdout)
        sys.stderr.write(p.stderr)
        sys.exit(
            "\npublish_feed: REFUSING TO PUBLISH — ship_gate.py check did not pass.\n"
            "  The feed is the public site. A cut the panel has not passed does not go on it,\n"
            "  and reaching Phase 7 is not evidence that Phase 6 finished. Go back to the\n"
            "  editing loop, fix the panel's named defects, re-render, re-grade, and publish\n"
            "  when the median clears the bar.\n"
            "  There is no override flag and one must not be added.")
    print("  ship_gate passed; publishing is permitted")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True, help="unique slug, e.g. 2026-07-22-checkpoint-lever")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD air date")
    ap.add_argument("--title", required=True, help="display title (short, Fraunces headline on the feed)")
    ap.add_argument("--caption", required=True, help="1-2 sentence verified summary shown under the title")
    ap.add_argument("--video-url", required=True, help="permanent 9:16 mp4 URL (upload_video.py output, verified live)")
    ap.add_argument("--poster-url", default="", help="permanent poster PNG URL (optional but strongly preferred)")
    ap.add_argument("--video-mobile-url", default="",
                    help="permanent 720x1280 mobile rendition URL -- the feed page serves THIS to "
                         "phones (the 1080p master is 15MB+; the rendition ~3-6MB). Omitting it "
                         "makes the page fall back to the heavy master on mobile, so pass it "
                         "whenever the rendition was produced (Phase 7 step 1 produces it).")
    ap.add_argument("--poster-thumb-url", default="",
                    help="permanent 540x960 JPEG poster thumb URL (~<80KB vs the 300-600KB PNG)")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--branch", default="main")
    a = ap.parse_args()

    # BEFORE anything is written or pushed anywhere. See require_ship_gate.
    require_ship_gate()

    # Validate every value that reaches the feed manifest before it is written,
    # so videos.json cannot carry an XSS payload into the /videos player.
    a.title = clean_text("title", a.title)
    a.caption = clean_text("caption", a.caption)
    a.video_url = clean_url("video-url", a.video_url, required=True)
    a.poster_url = clean_url("poster-url", a.poster_url, required=False)
    a.video_mobile_url = clean_url("video-mobile-url", a.video_mobile_url, required=False)
    a.poster_thumb_url = clean_url("poster-thumb-url", a.poster_thumb_url, required=False)

    with tempfile.TemporaryDirectory(prefix="feedpub_") as td:
        # shallow, blob-less clone: we only need the manifest, not site history/media
        run(["git", "clone", "--depth", "1", "--filter=blob:none", "--branch", a.branch, a.repo, td])
        mpath = Path(td) / MANIFEST
        if not mpath.exists():
            sys.exit(f"publish_feed: {MANIFEST} missing in {a.repo}@{a.branch} -- has the /videos page shipped there?")
        m = json.loads(mpath.read_text())
        vids = m.get("videos") or []

        entry = {
            "id": a.id,
            "date": a.date,
            "title": a.title,
            "caption": a.caption,
            # store absolute URLs: the page treats http(s) entries as absolute, and the
            # routine's uploader already returns full verified raw.githubusercontent URLs
            "video": a.video_url,
            "poster": a.poster_url,
        }
        # optional mobile-optimized fields: the feed page prefers these on phones and
        # falls back to video/poster when absent, so only include them when real
        if a.video_mobile_url:
            entry["video_mobile"] = a.video_mobile_url
        if a.poster_thumb_url:
            entry["poster_thumb"] = a.poster_thumb_url
        vids = [v for v in vids if v.get("id") != a.id]  # idempotent replace
        vids.insert(0, entry)                             # newest first
        m["videos"] = vids
        mpath.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n")

        run(["git", "-C", td, "add", MANIFEST])
        run(["git", "-C", td, "commit", "-m", f"feed: add {a.id} ({a.title})"])
        # network retries with backoff, per repo git policy
        for i, wait in enumerate([0, 2, 4, 8, 16]):
            if wait:
                time.sleep(wait)
            r = run(["git", "-C", td, "push", "origin", a.branch], ok_fail=True)
            if r.returncode == 0:
                print(f"publish_feed: OK -- {a.id} is live in {MANIFEST} on {a.branch}")
                return
            if "403" in (r.stderr or "") or "denied" in (r.stderr or "").lower():
                sys.exit("publish_feed: PUSH DENIED (403) -- the routine environment lacks write "
                         "access to Talonsturgill/alaskaaicarousels. Add that repo to the routine's "
                         "repo scope at claude.ai/code (environment settings), then re-run. The video "
                         "itself already shipped; only the site feed update is pending.")
        sys.exit(f"publish_feed: push failed after retries:\n{r.stderr.strip()[:800]}")


if __name__ == "__main__":
    main()
