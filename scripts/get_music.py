#!/usr/bin/env python3
"""Fetch + prepare the Dispatch music bed, and emit the credit for the Gmail draft.

PRIMARY (every run): the routine RESEARCHES a fresh royalty-free track that fits THIS story, then
passes it here to download + validate + credit:
  python scripts/get_music.py --url <direct audio url> --title "T" --composer "C" \
      --license "CC BY 4.0" --source "pixabay.com" --out out/dispatch/music_bed.wav

BACKUP (only if the live search fails): pick a verified track from config/music_sources.yaml:
  python scripts/get_music.py --pool --mood ambient --out out/dispatch/music_bed.wav

It downloads, converts to 44.1k stereo WAV, VALIDATES it is real audio (>=20s, not a 404/HTML page),
and writes the credit to music_credit.json (and prints `CREDIT: ...`). The WAV path is the LAST
stdout line. Exit !=0 on any failure so the caller can fall back to the engine's synth bed.
Then set DISPATCH_MUSIC=<the wav> so audio_v3.py uses it.
"""
import argparse, os, re, sys, json, subprocess, tempfile, random

def sh(c, **k): return subprocess.run(c, capture_output=True, text=True, **k)
def dur(p):
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p])
    try: return float(r.stdout.strip())
    except Exception: return 0.0
def download(url, dst):
    # a browser-like UA + same-origin referer, several free hosts (ccmixter, etc) hotlink-block bare curl
    from urllib.parse import urlparse
    origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}/"
    r = sh(["curl", "-sSL", "--max-time", "240", "-A", "Mozilla/5.0", "-e", origin, "-o", dst, url])
    return r.returncode == 0 and os.path.exists(dst) and os.path.getsize(dst) > 50_000
def to_wav(src, out, cap=180):
    r = sh(["ffmpeg", "-y", "-t", str(cap), "-i", src, "-ac", "2", "-ar", "44100", out])
    return r.returncode == 0 and os.path.exists(out) and dur(out) >= 20.0
# ============================================================================
# THE MUSIC HAS TO ANSWER THE STORY (2026-08-13, owner: "all the last videos just feel like
# down, or intense or kinds of like doomy ... seems like the variety engines needs to swing a
# bit more in a different way or weight a diff style more then u are").
#
# The tonal chain was severed at the join and nobody could see it. Phase 2 writes
# out/dispatch/angle.json with a COMMITTED VALENCE -- the 08-13 run's says "Curious, and
# genuinely hopeful ... Not caution, because no Alaska outage is in the record" -- and this
# picker never read that file. It took a --mood string typed by hand and did random.choice over
# whatever matched. "ambient" is the easiest word to type and the pool's ambient entries are
# cold, vast, glacial and reflective, so a genuinely hopeful story got scored like a requiem,
# every time, and the palette followed the music into the same grey.
#
# Two rules now. First, the bed must not CONTRADICT the valence the writers room already
# committed to in prose. Second, the last few runs are a fact about tone: if the recent stack is
# all cold, this run has to swing, because "swing a bit more" is a property of the SEQUENCE and
# no single run can see it from inside itself.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_HERE, ".."))
_POOL = os.path.join(_REPO, "config", "music_sources.yaml")

DOWN_MOODS = {"cold", "glacial", "somber", "dark", "ominous", "tense", "urgent", "vast",
              "reflective", "pondering", "deep", "ambient"}
UP_MOODS = {"warm", "upbeat", "hopeful", "friendly", "gentle", "celebratory", "uplifting",
            "playful", "bouncy", "light", "wonder", "inspired"}
# "driving" was in UP_MOODS for about four minutes and the first thing it did was pick
# "Volatile Reaction" (driving, urgent, tense, newsy) for a hopeful film -- i.e. it answered the
# owner's "doomy" note with "intense", which was the other half of the same complaint. A track
# is only a warm choice if it carries NO harsh tag at all.
HARSH_MOODS = {"tense", "urgent", "dark", "ominous", "somber", "cold", "glacial", "deep"}


def committed_valence():
    """The stance Phase 2 already argued for, in its own words. Empty if there is no angle."""
    try:
        a = json.load(open(os.path.join(_REPO, "out", "dispatch", "angle.json")))
        return " ".join(str(a.get(k, "")) for k in ("valence", "stance")).lower()
    except Exception:
        return ""


def recent_bed_moods(n=5):
    """Moods of the last n shipped beds, so a run can tell whether the stack is already grey."""
    try:
        import yaml
        st = yaml.safe_load(open(os.path.join(_REPO, "config", "state.yaml"))) or {}
        hist = (st.get("dispatch_history") or [])[-n:]
        pool = {t["title"]: t.get("mood", []) for t in
                yaml.safe_load(open(_POOL))["tracks"]}
        out = []
        for e in hist:
            for title, moods in pool.items():
                if title.lower() in str(e.get("music", "")).lower():
                    out += [m.lower() for m in moods]
        return out
    except Exception:
        return []


def tone_advice():
    """Print what the story asked for and what the stack has been doing. Never fatal."""
    # NEGATION IS NOT ASSERTION. The valence field is PROSE and the good ones argue by
    # elimination: the 08-13 angle reads "Not celebration, because the award is three days old
    # ... Not caution, because no Alaska outage is in the record". A bare keyword match reads
    # "caution" there and scores a hopeful film as a warning, which inverts the tone on exactly
    # the runs that reasoned most carefully about it. Strip the negated phrases first.
    val = re.sub(r"\bnot\s+[a-z]+", " ", committed_valence())
    wants_up = any(w in val for w in ("hopeful", "celebrat", "warm", "upbeat", "optimis",
                                      "curious", "wonder", "playful"))
    wants_down = any(w in val for w in ("caution", "somber", "grim", "warning", "loss", "danger"))
    rec = recent_bed_moods()
    down_share = (sum(1 for m in rec if m in DOWN_MOODS) / len(rec)) if rec else 0.0
    if val:
        print(f"  angle valence: {'hopeful-leaning' if wants_up and not wants_down else 'cautionary' if wants_down else 'neutral'}")
    if rec:
        print(f"  recent beds: {down_share:.0%} of their mood tags are in the DOWN set")
        if down_share >= 0.6 and not wants_down:
            print("  SWING: the last few films already scored cold and this story is not a "
                  "cautionary one. Pick from the warm/upbeat branch unless the record forbids it.")
    if wants_up and not wants_down:
        print("  NOTE: the writers room committed to a hopeful stance. A cold ambient bed "
              "contradicts the film's own argument, which is how a hopeful story ships doomy.")
    return wants_up and not wants_down, down_share


def pool_pick(mood):
    import yaml
    cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "music_sources.yaml")
    pool = (yaml.safe_load(open(cfg)) or {}).get("pool", [])
    wants_up, down_share = tone_advice()
    # A hopeful story may not be scored from the DOWN branch. This is the actual defect: the
    # mood word is chosen by whoever types the command and nothing checked it against the film.
    if mood and wants_up and mood.lower() in DOWN_MOODS:
        print(f"  REFUSING mood={mood!r}: the committed valence is hopeful and {mood!r} is in the "
              f"DOWN set. Falling back to the warm/upbeat branch. Override only by changing the "
              f"angle, which is the thing that should decide this.")
        mood = ""
    if not mood and wants_up:
        up = [t for t in pool
              if (UP_MOODS & {x.lower() for x in t.get("mood", [])})
              and not (HARSH_MOODS & {x.lower() for x in t.get("mood", [])})]
        if up:
            return random.choice(up)
    if mood:
        m = [t for t in pool if mood.lower() in [x.lower() for x in t.get("mood", [])]]
        pool = m or pool
    return random.choice(pool) if pool else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url"); ap.add_argument("--title", default=""); ap.add_argument("--composer", default="")
    ap.add_argument("--license", default=""); ap.add_argument("--source", default=""); ap.add_argument("--credit", default="")
    ap.add_argument("--pool", action="store_true"); ap.add_argument("--mood", default="")
    ap.add_argument("--out", default="out/dispatch/music_bed.wav")
    a = ap.parse_args(); os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if a.pool or not a.url:
        t = pool_pick(a.mood)
        if not t: print("no pool track available", file=sys.stderr); sys.exit(2)
        track = {k: t.get(k, "") for k in ("url", "title", "composer", "license", "source", "credit")}
        print(f"(pool fallback: {track['title']})", file=sys.stderr)
    else:
        track = dict(url=a.url, title=a.title, composer=a.composer, license=a.license, source=a.source, credit=a.credit)
    tmp = tempfile.mktemp(suffix=os.path.splitext(track["url"])[1] or ".mp3")
    if not download(track["url"], tmp):
        print("download failed: " + track["url"], file=sys.stderr); sys.exit(1)
    if not to_wav(tmp, a.out):
        print("not valid audio / convert failed: " + track["url"], file=sys.stderr); sys.exit(1)
    credit = track["credit"] or " ".join(x for x in [
        f'"{track["title"]}"' if track["title"] else "", track["composer"],
        f'({track["source"]})' if track["source"] else "", f'- {track["license"]}' if track["license"] else ""] if x).strip()
    json.dump({**track, "credit": credit, "wav": a.out, "duration": round(dur(a.out), 1)},
              open(os.path.join(os.path.dirname(os.path.abspath(a.out)), "music_credit.json"), "w"), indent=2)
    print("CREDIT: " + credit)
    print(a.out)   # LAST line = the prepared wav

if __name__ == "__main__":
    main()
