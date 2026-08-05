"""Build the Gmail draft payload for a finished Alaska.Ai video Dispatch (story-agnostic).

Media is NEVER base64'd through the model. The routine uploads the cuts (and ideally the poster)
with scripts/upload_video.py and passes their direct-download URLs here. This prints the draft
payload JSON {subject,to,html_body} on the LAST stdout line for the orchestrator to hand to the
Gmail create_draft connector (use --poster-url, not --poster, to keep that payload small).

Usage:
  python scripts/dispatch_email.py \
    --post out/dispatch/post.txt \
    --video-url-vertical "<9:16 url>" --video-url-square "<1:1 square url>" \
    --poster-url "<poster url>" \
    --voice "Kokoro af_heart" --music '"Title" Composer (source) - CC BY 4.0' \
    --sources out/dispatch/sources.json --score "9.2/10" \
    --note "On-screen numbers are illustrative unless drawn from a live feed." \
    --temporary --date 2026-06-27 --title "Cook Inlet belugas" --out-html out/dispatch/email.html
"""
import argparse, base64, json, datetime as dt, re, sys
from pathlib import Path

# THE MAILBOX IS docket@alaskaaihq.com AND IT IS THE SAME ONE EVERY TIME (owner, 2026-07-31).
# It used to say "me", an account-relative alias, on the theory that a repoint should be a
# connector change and not a code change. In practice the Gmail connector rejects "me" outright
# ("Invalid email address. Please provide a raw email address"), so every run hit the error,
# went and looked the address up, and typed it into the tool call by hand. A constant that every
# caller has to rediscover is not a constant, it is a gap. It lives here now.
DRAFT_TO = "docket@alaskaaihq.com"
# Run-freshness guard: refuse to email a PREVIOUS run's scratch (see run_guard.py
# for the 07-18/07-19 stale-artifact incidents this prevents). Import from the
# sibling scripts/ dir regardless of the caller's cwd.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_guard import fresh, StaleArtifactError  # noqa: E402

CSS = """
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#13202b;background:#eef1f3;margin:0;padding:24px;}
.wrap{max-width:720px;margin:0 auto;background:#fff;border:1px solid #e3e6e8;border-radius:14px;padding:28px;}
h1{font-size:22px;margin:0 0 2px;} .sub{color:#6a7782;font-size:13px;margin-bottom:22px;}
h2{font-size:15px;letter-spacing:.02em;text-transform:uppercase;color:#516170;margin-top:26px;border-bottom:1px solid #eef0f2;padding-bottom:6px;}
pre.post{white-space:pre-wrap;background:#f6f8f9;padding:16px;border-radius:10px;font:14px/1.55 ui-monospace,Menlo,monospace;}
.dl{display:inline-block;background:#FFC72C;color:#13202b;font-weight:700;text-decoration:none;padding:13px 20px;border-radius:10px;font-size:15px;margin:4px 8px 4px 0;}
.dl.alt{background:#13202b;color:#fff;} .dl small{display:block;font-weight:500;font-size:12px;margin-top:2px;opacity:.8;}
.poster{margin:16px 0;text-align:center;} .poster img{max-width:300px;width:100%;border-radius:10px;border:1px solid #e3e6e8;}
ul{padding-left:20px;} li{margin:4px 0;font-size:13.5px;} a{color:#0b6;}
.warn{background:#fff6e0;border:1px solid #f0d68a;color:#7a5a10;font-size:12.5px;padding:8px 12px;border-radius:8px;margin:10px 0;}
ul.upg{background:#eefaf1;border:1px solid #bfe6cd;border-radius:10px;padding:12px 12px 12px 32px;}
ul.upg li{color:#1c5f38;}
.foot{color:#97a2ab;font-size:11px;margin-top:24px;}
"""

def _label_for(url):
    """Readable label for a bare source URL: the registrable domain, uppercased outlet-style."""
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return (m.group(1) if m else url or "source")


def parse_sources(data):
    """Extract EVERY source from the run's sources.json regardless of which schema the
    fact-check phase emitted. Accepts: a `sources` list of {title/outlet/url/note} dicts,
    a `primary_urls` list of URL strings, or (fallback) any http(s) URLs found anywhere in
    the document. Returns (items, sourcing_note) where items is a list of {url,label,note}.

    WHY THIS IS PARANOID (2026-07-21 owner catch): the old code read ONLY `.get("sources")`
    and silently fell back to a 'See DISPATCH.md on GitHub' pointer when the key was absent —
    which shipped a draft that made the owner go fetch their own sources. The email IS the
    deliverable; every source must be IN it. There is no pointer fallback anymore: the
    caller hard-fails if this returns no sources."""
    items, seen = [], set()

    def add(url, label=None, note=""):
        u = (url or "").strip()
        if u.startswith("http") and u not in seen:
            seen.add(u)
            items.append({"url": u, "label": label or _label_for(u), "note": note})

    for s in data.get("sources") or []:
        if isinstance(s, dict):
            add(s.get("url"), s.get("outlet") or s.get("title"), s.get("note", ""))
        elif isinstance(s, str):
            add(s)
    for u in data.get("primary_urls") or []:
        if isinstance(u, str):
            add(u)
    if not items:  # last resort: harvest any URL anywhere in the doc, never silently none
        def walk(v):
            if isinstance(v, str):
                for u in re.findall(r"https?://[^\s\"'<>\\]+", v):
                    add(u)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
            elif isinstance(v, dict):
                for x in v.values():
                    walk(x)
        walk(data)
    return items, (data.get("sourcing_note") or "").strip()


# The permanent tail of every sources section: the owner's public decision/update log.
# Hardcoded in the template ON PURPOSE so no run can forget it.
ALASKAIHQ_LI = ('<li><b>Every Alaska + AI decision and update we track, in one place</b> '
                '<a href="https://alaskaaihq.com">alaskaaihq.com</a></li>')


def render(post, poster_html, vids, voice, music, sources, score, note, temporary, date_str, title, upgrades,
           sourcing_note=""):
    def esc(x):
        return (x or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    src = "\n".join(
        f'<li><a href="{s["url"]}">{s["label"]}</a>'
        f'{(" &middot; " + s["note"]) if s.get("note") else ""}'
        f'<br><span style="color:#6a7782;font-size:12px;">{s["url"]}</span></li>'
        for s in sources
    )
    if sourcing_note:
        src += f'\n<li style="color:#6a7782;"><i>Sourcing note: {sourcing_note}</i></li>'
    src += "\n" + ALASKAIHQ_LI
    # THE COMMENT BLOCK (2026-07-21 owner ask): sources + music + voice must land in ONE plain-text,
    # selectable block the owner pastes into the LinkedIn FIRST COMMENT (never the post). Real URLs
    # on their own line under each title so they survive the paste. No colons (brand voice), so
    # labels use a comma. This is the canonical home for sources/credits; the post body has none.
    cl = ["Sources", ""]
    for s in sources:
        cl.append(esc(s["label"]))
        cl.append(esc(s["url"]))
        cl.append("")
    cl.append("More Alaska and AI updates, alaskaaihq.com")
    cl.append("")
    if music: cl.append(f"Music, {esc(music)}")
    if voice: cl.append(f"Voice, {esc(voice)}")
    comment_text = "\n".join(cl)
    buttons = ""
    # LinkedIn is PRIMARY, so the SQUARE leads. CORRECTED 2026-08-03 on owner evidence: LinkedIn
    # routes ANY video taller than square into the swipe-only Video tab, and 1080x1350 is taller
    # than square, so the old 4:5 label was sending every dispatch to the wrong feed. 1080x1080
    # lands in the MAIN HOME FEED beside the post copy. The 9:16 is the TikTok cut.
    if vids.get("square"):
        buttons += (f'<a class="dl" href="{vids["square"]}">&#9660;&nbsp; Post to LinkedIn &middot; 1:1 square (main feed)'
                    f'<small>1080&times;1080 &middot; ~84s &middot; H.264 MP4 &middot; square stays in the home feed</small></a>')
    if vids.get("vertical"):
        buttons += (f'<a class="dl alt" href="{vids["vertical"]}">&#9660;&nbsp; TikTok &middot; 9:16 (full-screen)'
                    f'<small>1080&times;1920 &middot; on LinkedIn this goes to the vertical Video tab, not the feed</small></a>')
    feed_guide = ('<div class="warn" style="background:#eaf4ff;border-color:#b6d8f5;color:#245c8a;">'
                  'For LinkedIn use the <b>1:1 square</b> cut (top button) so the video lands in the <b>main feed</b> '
                  'next to your caption. The 9:16 is TikTok-native, and uploaded to LinkedIn it gets pulled into the '
                  'swipe-only Video tab instead of the feed.</div>') if vids.get("square") else ''
    warn = '<div class="warn">Heads up: these download links are temporary (~1 hour). Save the file before it expires, or configure a permanent host.</div>' if temporary else ""
    score_html = f"<h2>Grade</h2><ul><li>{score}</li></ul>" if score else ""
    # "Upgrades shipped this run" — Phase 8 makes fixes on the spot and reports what it DID here
    # (one bullet per line of --upgrades). A run that self-improved should say so.
    up_items = "\n".join(f"<li>{ln.strip().lstrip('-').strip()}</li>"
                         for ln in (upgrades or "").splitlines() if ln.strip())
    upgrades_html = (f'<h2>Upgrades shipped this run</h2><ul class="upg">{up_items}</ul>'
                     if up_items else "")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="wrap">
  <h1>ALASKA.AI &middot; Dispatch ready{(' &middot; ' + title) if title else ''}</h1>
  <div class="sub">{date_str} &middot; LinkedIn (primary) + TikTok &middot; review, then post</div>

  <h2>The video</h2>
  {buttons}
  {feed_guide}
  {warn}
  {poster_html}

  <h2>Post text (copy/paste)</h2>
  <div class="sub" style="margin-bottom:8px;">The post body only. Sources and credits are NOT in here on purpose, they go in the first comment (next block).</div>
  <pre class="post">{post}</pre>

  <h2>First comment (copy/paste)</h2>
  <div class="sub" style="margin-bottom:8px;">Paste this as the FIRST COMMENT on the post, not in the post itself. Plain text with the real URLs so the links survive the paste.</div>
  <pre class="post">{comment_text}</pre>

  {score_html}
  {upgrades_html}
  <h2>Sources (clickable reference)</h2>
  <ul>{src}</ul>

  <div class="foot">Generated {dt.datetime.utcnow().isoformat()}Z by the Alaska.Ai Dispatch routine. {note}</div>
</div></body></html>"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", required=True)
    ap.add_argument("--video-url-vertical", required=True, help="9:16 1080x1920 TikTok cut (dispatch_master.mp4)")
    ap.add_argument("--video-url-square", default="",
                    help="1:1 1080x1080 LinkedIn MAIN FEED cut (dispatch_square.mp4). ALWAYS pass this — it is the primary LinkedIn deliverable; without it the draft only offers the 9:16, which LinkedIn routes to the swipe-only Video tab. CORRECTED 2026-08-05: this help string still said 4:5 1080x1350 long after the 08-03 correction, and prompts/dispatch_routine.md names exactly this as the reason the error survived one fix: the claim lives in three places that each read as authoritative alone, and only encode_deliverables.sh fails loudly. This was the third place."
                         "primary LinkedIn deliverable; without it the draft only offers the 9:16, which LinkedIn "
                         "routes to the Video tab instead of the main feed.")
    ap.add_argument("--poster-url", default="", help="hosted poster (preferred, keeps payload small)")
    ap.add_argument("--poster", default="", help="poster file to inline as base64 (heavier)")
    ap.add_argument("--voice", default=""); ap.add_argument("--music", default="")
    ap.add_argument("--sources", default=""); ap.add_argument("--score", default="")
    ap.add_argument("--note", default="On-screen counters/charts are illustrative unless drawn from a live data feed.")
    ap.add_argument("--upgrades", default="",
                    help="what Phase 8 actually FIXED/upgraded this run, one item per line (not "
                         "suggestions -- changes committed this run). Rendered as the 'Upgrades "
                         "shipped this run' section so the owner sees what self-improved.")
    ap.add_argument("--temporary", action="store_true", help="flag download links as temporary (~1h)")
    ap.add_argument("--date", default=dt.date.today().isoformat()); ap.add_argument("--title", default="")
    ap.add_argument("--to", default=DRAFT_TO); ap.add_argument("--out-html", default="")
    ap.add_argument("--no-freshness-check", action="store_true",
                    help="bypass the run-freshness guard (deliberate manual/standalone use only; "
                         "the routine must NEVER pass this -- it is how a previous run's scratch ships)")
    a = ap.parse_args()
    chk = not a.no_freshness_check
    try:
        post = Path(fresh(a.post, check=chk)).read_text().strip()
    except StaleArtifactError as e:
        sys.exit(f"REFUSING TO BUILD DRAFT: --post is not from this run.\n  {e}")
    if a.poster_url:
        poster_html = f'<div class="poster"><img src="{a.poster_url}" alt="poster"/></div>'
    elif a.poster and Path(a.poster).exists():
        b64 = base64.b64encode(Path(a.poster).read_bytes()).decode()
        poster_html = f'<div class="poster"><img src="data:image/png;base64,{b64}" alt="poster"/></div>'
    else:
        poster_html = ""
    # SOURCES ARE MANDATORY AND INLINE (2026-07-21 owner rule): the email is the whole
    # deliverable — the owner must never have to fetch their own sources from GitHub.
    # No pointer fallback exists; zero parseable sources = no draft.
    if not a.sources or not Path(a.sources).exists():
        sys.exit("REFUSING TO BUILD DRAFT: --sources is required and must point at this run's "
                 "sources.json (the email must carry every source inline).")
    try:
        src_data = json.loads(Path(fresh(a.sources, check=chk)).read_text())
    except StaleArtifactError as e:
        sys.exit(f"REFUSING TO BUILD DRAFT: --sources is not from this run.\n  {e}")
    sources, sourcing_note = parse_sources(src_data)
    if not sources:
        sys.exit("REFUSING TO BUILD DRAFT: no sources could be parsed from --sources — the email "
                 "must list every source inline (no 'see the repo' pointers). Fix sources.json.")
    html = render(post, poster_html, {"vertical": a.video_url_vertical, "square": a.video_url_square},
                  a.voice or "(unset)", a.music or "(unset)", sources, a.score, a.note, a.temporary, a.date, a.title,
                  a.upgrades, sourcing_note)
    if a.out_html:
        Path(a.out_html).write_text(html); print("wrote", a.out_html)
    payload = {"subject": f"ALASKA.AI · Dispatch ready · {a.date}", "to": a.to, "html_body": html}
    print(json.dumps(payload))   # LAST line = the draft payload for Gmail create_draft

if __name__ == "__main__":
    main()
