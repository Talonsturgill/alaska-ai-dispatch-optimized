#!/usr/bin/env python3
"""Dedupe ledger for the DAILY Alaska.Ai Dispatch routine.
Never repeat a story within the same week (and never an exact repeat). The ledger is
config/state.yaml > dispatch_history; it is read at the start of research and written at
the end of every run.

  python scripts/dedupe.py list  --days 30
      -> the exclusion list of recently-covered topics + key entities (for research).
  python scripts/dedupe.py check --entities "cook inlet,beluga,noaa" [--days 30]
      -> prints FRESH (exit 0) or DUP ... (exit 1) if it overlaps a recent Dispatch.
  python scripts/dedupe.py add --date 2026-06-28 --topic "..." --slug dispatch-... \
      --entities "a,b,c" --archetype "..." --palette "..." --voice "..." \
      --composition '{"pov":"instrument-screen","motion_vector":"vertical-rise", ...}'
      -> appends the run to the ledger. --composition is the storyboard fingerprint (JSON, the 7
         axes from config/composition_axes.yaml); it is what scripts/storyboard_check.py diffs the
         NEXT run against, so always pass it (copy out/dispatch/storyboard.json's "fingerprint").
"""
import sys, argparse, datetime as dt, re, json
from pathlib import Path
import yaml  # installed by scripts/setup_env.sh

STATE = Path(__file__).resolve().parent.parent / "config" / "state.yaml"
# STOPWORDS CARRY NO SUBJECT, SO THEY MAY NOT DECIDE A REPEAT (widened 2026-08-09).
#
# `check` calls DUP on any TWO shared word tokens. That threshold is right, but the
# tokeniser splits multi-word entities into single words, so the words this channel says
# in EVERY dispatch were voting. Measured on this run's honest entity list, three
# consecutive re-tests were refused on ['learning','machine'], then ['ash','learning'],
# then ['alaska','nsf'], then ['alaska','anchorage'] — four DUPs, and not one of them
# named a subject. "Alaska" plus "Anchorage" is a guaranteed pair for an Alaska channel,
# and "machine" plus "learning" is a guaranteed pair for an AI channel, so the gate was
# structurally incapable of returning FRESH and every run had to argue past it. A gate
# that is always red teaches a run to talk its way through, which is precisely the
# entity-list gaming the routine bans (Phase 3, "never game it").
#
# So the fix is at the tokeniser, not at the threshold: geography this channel is named
# after, the technology it is named after, and the funders/institutions that appear in a
# third of all entries are removed BEFORE the count. Everything that identifies a SUBJECT
# still votes, and the pair threshold is untouched.
#
# VERIFIED, not assumed: scripts/dedupe_selftest.py replays the real 30-day history and
# asserts (a) the two genuine repeats still DUP and (b) four measured false positives from
# this run now pass. Add a word here only with that test green.
STOP = {
    # grammar
    "the", "a", "an", "of", "in", "and", "for", "to", "on", "with", "by", "at", "as",
    # the channel's own name, in every entry by construction
    "ai", "artificial", "intelligence", "machine", "learning", "ml", "model", "models",
    "algorithm", "algorithms", "data", "system", "systems", "tech", "technology",
    # the state this channel is about, and the places it keeps happening in
    "alaska", "alaskan", "alaskans", "ak", "arctic", "state", "statewide",
    "anchorage", "fairbanks", "juneau", "interior", "southeast", "slope", "north",
    # the institutions that recur across a third of the archive
    "uaf", "uaa", "uas", "university", "nsf", "noaa", "usgs", "doe", "nih", "federal",
    "award", "awards", "grant", "grants", "project", "program", "research",
    # organisation-shaped nouns that describe a form, never a subject
    "institute", "center", "centre", "department", "division", "office", "agency",
    "association", "corporation", "consortium", "council", "commission", "bureau",
    # citation scaffolding
    "fr", "cfr", "usc", "doc", "no", "vol", "id",
}

def _is_bare_number(w: str) -> bool:
    """Citation scaffolding is not a subject.

    Two shapes, both measured on the real ledger. A YEAR: '2026' sits in a third of the
    entity lists, so paired with one generic noun it alone refused a story. A SHORT
    NUMBER: the Federal Register volume '91' matched '91 FR 46055' against '91 FR 47241',
    two unrelated notices whose only common ground is that both were published in 2026.

    LONG numbers are kept deliberately, because a docket or lease id like ADL 422741 is
    the most identifying token a filing story has, and it is what catches a re-pitch of
    a docket the channel already covered.
    """
    if not w.isdigit():
        return False
    return len(w) < 4 or ("1900" <= w <= "2099" and len(w) == 4)

def load():
    d = yaml.safe_load(STATE.read_text()) or {}
    d.setdefault("dispatch_history", [])
    return d

def norm(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower())
            if w not in STOP and len(w) > 1 and not _is_bare_number(w)}

def entity_key(e):
    ents = e.get("key_entities") or []
    s = ",".join(ents) if isinstance(ents, list) else str(ents)
    return norm(s) | norm(e.get("topic", ""))

# ============================================================================
# THE DEDUPE WINDOW (owner directive, 2026-07-30)
# ----------------------------------------------------------------------------
# The window is THIRTY DAYS, for `list` and `check` alike, and a repeat after
# thirty days is EXPLICITLY ALLOWED. The owner's words: "make the dedupe
# function of this automation only 30 days, it's okay to repeat if it's been 30
# days since we talked about something."
#
# This replaces two older rules that no longer apply:
#   - the 7-day check window and the 14-day list window, and
#   - "never an exact repeat ever", which was an unbounded prohibition.
# The slug check already runs through recent(), so an exact-slug repeat is now
# gated by this same window rather than forever.
#
# Why this changed: topics were getting thin. An unbounded no-repeat rule means
# the automation permanently burns every subject it ever touches, and with a
# daily cadence that shrinks the eligible pool every single run. A subject the
# audience last saw a month ago is not a rerun to them, and a genuinely new
# development on it is real news.
# ============================================================================
DEDUPE_WINDOW_DAYS = 30


def recent(d, days):
    today = dt.date.today(); out = []
    for e in d["dispatch_history"]:
        try: ed = dt.date.fromisoformat(str(e.get("date")))
        except Exception: ed = None
        if ed is None or (today - ed).days <= days:
            out.append(e)
    return out

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("list");  pl.add_argument("--days", type=int, default=DEDUPE_WINDOW_DAYS)
    pc = sub.add_parser("check"); pc.add_argument("--entities", required=True); pc.add_argument("--days", type=int, default=DEDUPE_WINDOW_DAYS)
    pc.add_argument("--hero", default="",
                    help="the library asset cast as this run's HERO / AI-embodiment (e.g. ServerMachine, "
                         "Vale, Sourdough). HARD GATE (2026-07-21 owner rule): the same hero asset in "
                         "either of the last TWO dispatches = HERO RERUN, exit 1 — recast from the "
                         "manifest (5 characterized objects, 21 fauna, vehicles, props).")
    pa = sub.add_parser("add")
    for f in ["date","topic","slug","entities","archetype","palette","voice","stance","angle"]:
        pa.add_argument("--"+f, default="",
                        help="stance = celebratory|cautionary|curious|mixed (for register rotation); "
                             "angle = one-sentence thesis" if f in ("stance","angle") else None)
    pa.add_argument("--composition", default="", help="storyboard fingerprint as JSON (the 7 axes)")
    pa.add_argument("--hero", default="", help="library asset cast as the HERO/AI-embodiment this run (required for the rotation gate)")
    pa.add_argument("--cast", default="", help="comma list of featured library assets this run (for roster pressure in `list`)")
    a = ap.parse_args(); d = load()

    if a.cmd == "list":
        rs = recent(d, a.days)
        if not rs: print("(ledger empty — anything is fresh)"); return
        print(f"# Covered in the last {a.days} days — DO NOT repeat (and rotate STANCE, don't stack one):")
        for e in rs:
            ents = e.get("key_entities") or []
            st = e.get("stance") or "?"
            print(f"- {e.get('date')} | stance={st} | {e.get('topic')} | entities: {', '.join(ents) if isinstance(ents,list) else ents}")
        stances = [e.get("stance") for e in rs if e.get("stance")]
        if stances:
            print(f"# recent stances (oldest→newest): {', '.join(stances)}  — if these skew one way, look hard for the other.")
        heroes = [f"{e.get('date')}:{e.get('hero')}" for e in rs if e.get("hero")]
        if heroes:
            print(f"# recent HERO assets (oldest→newest): {', '.join(heroes)}  — the next hero must differ "
                  f"from the last TWO (dedupe.py check --hero <Asset> enforces this).")

    elif a.cmd == "check":
        cand = norm(a.entities)
        for e in recent(d, a.days):
            if e.get("slug") and e.get("slug") in a.entities:
                print(f"DUP: slug {e.get('slug')} ({e.get('date')})"); sys.exit(1)
            shared = cand & entity_key(e)
            if len(shared) >= 2:
                print(f"DUP: overlaps {e.get('date')} \"{e.get('topic')}\" on {sorted(shared)}"); sys.exit(1)
        # HERO-ASSET ROTATION GATE (2026-07-21 owner rule: "we keep using this little square guy
        # in like every video"). The same library asset must not play the HERO/AI-embodiment in
        # back-to-back dispatches — with a 26-asset shelf, the audience should never see a rerun.
        if a.hero:
            hist = sorted(d["dispatch_history"], key=lambda e: str(e.get("date")))
            last_heroes = [(e.get("date"), e.get("hero")) for e in hist if e.get("hero")][-2:]
            for hd, hh in last_heroes:
                if hh and hh.strip().lower() == a.hero.strip().lower():
                    print(f"HERO RERUN: {a.hero} was the hero on {hd} — recast. The manifest has 5 "
                          f"characterized objects, 21 fauna, 3 vehicles and a props kit; the AI-presence "
                          f"does NOT have to be a server (a drone, a counter, a plant, a phone, a weir-cam "
                          f"...whatever THIS story's tool actually is).")
                    sys.exit(1)
        print("FRESH"); sys.exit(0)

    elif a.cmd == "add":
        ents = [x.strip() for x in a.entities.split(",") if x.strip()]
        entry = {
            "date": a.date or dt.date.today().isoformat(),
            "topic": a.topic, "slug": a.slug, "key_entities": ents,
            "archetype": a.archetype, "palette": a.palette, "voice": a.voice,
            "stance": a.stance, "angle": a.angle}
        if a.hero:
            entry["hero"] = a.hero.strip()
        else:
            print("WARNING: no --hero passed; the next run's hero-rotation gate will be blind to this "
                  "dispatch's casting. Pass the library asset that played the hero/AI-embodiment.",
                  file=sys.stderr)
        if a.cast:
            entry["cast"] = [x.strip() for x in a.cast.split(",") if x.strip()]
        if a.composition:
            try:
                entry["composition"] = json.loads(a.composition)
            except json.JSONDecodeError as e:
                print(f"WARNING: --composition is not valid JSON ({e}); storing nothing. "
                      f"The next run's storyboard_check will have no fingerprint to diff against.", file=sys.stderr)
        else:
            print("WARNING: no --composition fingerprint passed; the next run's divergence gate will be "
                  "blind to this dispatch's composition. Pass out/dispatch/storyboard.json's fingerprint.", file=sys.stderr)
        d["dispatch_history"].append(entry)
        STATE.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
        print("added:", a.slug or a.topic)

if __name__ == "__main__":
    main()
