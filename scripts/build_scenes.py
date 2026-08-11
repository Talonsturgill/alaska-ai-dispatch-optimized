#!/usr/bin/env python3
"""Compute scene frame boundaries from the VO line timings so the timeline stays
in sync with the narration automatically. Scene i begins at the start of a mapped
VO line; S1 covers lines 0-1. Writes episode_props.json {captions, scenes, total}.
"""
import json
import os
import re
from urllib.parse import urlparse

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
FPS = 30
TAIL = 1.5  # hold after the last word

# scene -> index of the VO line that starts it. 2026-07-22 "the checkpoint lever frozen
# at the midpoint" has 7 scenes (S1..S7 in video-engine/src/Episode.tsx, SCENE_COMPONENTS)
# mapped onto 9 VO lines (vo_lines.json has exactly 9 lines this run, some scenes span 2
# lines of VO): S1 line0 (map/counter+offer), S2 line1 (parcels+NOT FOR SALE+"not a sale"
# is still S2's content but starts visually at the parcels line), S3 line3 (EUL
# mechanism), S4 line4 (MachineShadow/Moriarty), S5 line5 (Hollister), S6 line6 (lever
# return, covers "nobody picked"+"still open"), S7 line8 (closing question+hold+loop).
# (keep this list's length equal to SCENE_COMPONENTS.length every run -- an earlier list
# here silently mismatched it once and Episode fell back to hardcoded DEFAULT_BOUNDS.)
# 2026-07-23 "Counting Belugas From Orbit": 7 scenes (S1..S7) onto 11 VO lines.
# S1 L0 (silt/find-the-whale), S2 L1 (331+decline), S3 L2 (from space, SatelliteEye),
# S4 L3-L4 (GAIA+partners, the learning pipeline), S5 L5-L6 (cannot-count-yet, needs a
# clear look), S6 L7-L8 (June 2025 empty, sky booked), S7 L9-L10 (holding on, the question).
# 2026-07-25 "The One It Didn't Hear": 7 scenes (S1..S7) onto 12 VO lines. Shot boundaries
# are anchored to VO LINE STARTS so the picture can never drift from the words (the Gate 0B/0C
# finding that killed the first board: the collapse was spoken at 19.6s and drawn at 33.9s).
# S1 L0-L1 (Otto at work + the second job), S2 L2 (duration lanes + the gate latching),
# S3 L3-L4 (boundary + travel out + THE COLLAPSE), S4 L5 (signature shot + the dark lamp),
# S5 L6-L7 (still heard + by hand + the boulder), S6 L8 (crate + money),
# S7 L9-L11 (wireframe twin + calendar + button).
# 2026-07-26 "The Field That Stopped in 2019": NINE scenes (S1..S9 in Episode.tsx) onto
# 14 VO lines. Shot boundaries are anchored to VO LINE STARTS so the picture can never
# drift from the words. S1 L0 (the letter opens), S2 L1-L2 (the 200 baseline + McCabe's
# fair defense, VOICED not merely posted), S3 L3-L4 (the mouth cranks wide + the intake +
# the burst from the unchanged stem), S4 L5 (the plain letter + 3,048 into one finite
# tape), S5 L6 (three Alaskans reacting three different ways), S6 L7-L8 (the machine opens
# on the capped third pipe + the pawl + the two records), S7 L9-L10 (the arrow on the
# doorless wall + the door swinging free), S8 L11-L12 (NO ALGORITHM + the signature shot),
# S9 L13 (the button, back at the same table, staying interior).
# 2026-08-02 "The Copy In The Mud": TWELVE shots (S1..S12 in video-engine/src/Ep0802.tsx) onto
# 16 VO lines. Shot boundaries are anchored to VO LINE STARTS so the picture can never drift
# from the words. S1 L0 (the lamp arrives + the notches), S2 L1 (the stack + THE BLADE WIPE),
# S3 L2 (the bench lamp match-cut + the USGS AVO plate), S4 L3 (THE DROP through the waterline
# + the coring punch), S5 L4 (eight columns rise + the running count to 70), S6 L5 (the sort
# down to 37), S7 L6-L7 (THE CARD PRINTS WIDE + the shard's machined edge), S8 L8 (the grain
# runs the chain), S9 L9 (the three name plates + the strips stack + MAGENTA FUSES),
# S10 L10-L11 (out of register + THE SIGNATURE PULL-BACK + the set-down), S11 L12-L13 (the dark
# bench + the calipers + COULD and COULDN'T + the crumb lands), S12 L14-L15 (the button + the
# lamp withdrawing onto the unread stripe, which is frame 1 unlit).
# 2026-08-03 "The Days You Are Allowed To Burn": 10 shots onto 17 VO lines, derived FROM the
# beat table rather than written alongside it (the Gate 0C finding that killed the first board:
# beats had been re-timed and re-anchored while the shots kept their old boundaries, so seven
# beats played inside shots that did not contain their subject).
# S1 L0-L1 (the wash + the paired counters), S2 L2 (the award plates + the stamp),
# S3 L3-L4 (the drip torch + the flame line + one treated patch), S4 L5 (the empty cradle),
# S5 L6-L7 (the engine assembles, the intake re-cut, the reject chute, THE PUNCH, the pullback),
# S6 L8-L9 (the sheet handed across + the four fields colliding), S7 L10-L11 (four hands + the
# plates turning), S8 L12-L13 (the 2026-2030 rule + the empty liability box), S9 L14 (the waiting
# crew), S10 L15-L16 (the wash drains, the windows open, the pulaski flips).
# 2026-08-05 "The Net Comes First": EIGHT shots onto 19 VO lines. Shot boundaries are
# anchored to VO LINE STARTS so the picture can never drift from the words.
# NINE shots (S2 was split at L5: 21.6s was past the 16s oner ceiling).
# S1 L0-L2 (the beetle stripped to a contour + the two counters + the gap + the shuttered machine),
# S2 L3-L6 (the collection room, the drawer, the pin, the odometer, born digital, the sequence, no match),
# S3 L7-L8 (the newspaper laid down, the hole in the column, the NameEngine assembling, the gene window),
# S4 L9-L10 (eighty beetles resolve, the two misses, the author plate turns, SIKES lights on his own name),
# S5 L11-L12 (the decade dial's one tooth, THE SIGNATURE PULL-BACK, the 210-year plate),
# S6 L13-L14 (the machine still, the cutaway iris opening on nothing, the chain running backwards),
# S7 L15-L16 (the net sweep in tussock, the ghost of a newer model),
# S8 L17-L18 (the drawer wall rolling closed, the caught beetle named, the question).
# 2026-08-06 "The Same Face, The Same Plate": ELEVEN shots (S1..S11 in
# video-engine/src/Ep0806.tsx) onto 25 VO lines. Boundaries are anchored to VO LINE
# STARTS so the picture can never drift from the words. Rebalanced at Gate 0C, which
# measured the first map demanding 196 to 210 wpm in three shots and under 120 in three
# others: the total was fine and the DISTRIBUTION desynchronised say-it-show-it across
# roughly 40 seconds. S1 L0-1 (the frame, the refused bracket, the two cities, the pipe),
# S2 L2-3 (capacity and price), S3 L4-5 (the rule and the mismatch), S4 L6-7 (the promise,
# then north), S5 L8-9 (the redaction lands, the tool is unnamed), S6 L10-11 (two jobs),
# S7 L12-13 (the mechanism and the growing line), S8 L14-16 (the curve, one technician,
# the spool), S9 L17-18 (the quote, the idea, the attorneys), S10 L19-21 (the concession,
# the denial, the fusion), S11 L22-24 (the date, the wall, the button).
# 2026-08-07 "The Boat, Not The Brain": TWELVE scenes (S1..S12 in video-engine/src/Ep0807.tsx)
# onto 29 VO lines. Boundaries are anchored to VO LINE STARTS so the picture can never drift
# from the words. S1 L0-L1 (the held breath, the spike that does not descend), S2 L2-L3 (ike
# jime's three steps + the trained hand), S3 L4-L5 (the machine arrives + THE SPOT MOVES),
# S4 L6-L7 (the founder quote drawn as three fish with three different true points),
# S5 L8-L9 (the jig comes down straight and misses), S6 L10-L11 (the machine's own view +
# the lock, THE LOOKING), S7 L12 (Cook Inlet + the dotted mark), S8 L13-L14 (the claim ledger
# + the blank price tag), S9 L15-L18 (THE TEST, one boat one bay + the CTO quote),
# S10 L19-L22 (the seam, one write-up, the empty rack, NO BOAT COUNT), S11 L23-L25 (ten
# machines against 1,300+ permits), S12 L26-L28 (THE TURN to a dozen hulls + the button).
# 2026-08-08 "Not In The Buying": FIFTEEN scenes (S1..S15 in video-engine/src/Ep0808.tsx)
# onto 26 VO lines. Boundaries anchored to VO LINE STARTS so the picture cannot drift
# from the words. S1 L0-L1 (the slug drops, the money block builds), S2 L2 (the two rule
# plates bolt on), S3 L3-L4 (the 20% collar clamps, the flow bends away), S4 L5-L6 (Mina,
# dated June, and the quote), S5 L7-L8 (the state list posts, the slug lifts, the question),
# S6 L9-L11 (Aug 7th, 19 cards deal, only the described ones light), S7 L12-L13 (Chugachmiut,
# the case opens, the arm rises, the plate answers), S8 L14 (five doors swing, the kiosk),
# S9 L15 (THE SIGNATURE: the slug against card after card, fitting none), S10 L16-L17 (Act 3,
# the undecided block), S11 L18 (three regions go dark), S12 L19 (the spreadsheet refuses),
# S13 L20-L22 (the statute opens, the slug descends the column), S14 L23 (it seats flush in
# the training clause), S15 L24-L25 (the button, two empty recesses and one filled).
# 2026-08-09 "The Method, Not The Metal": ELEVEN scenes (S1..S11 in video-engine/src/Ep0809.tsx)
# onto 23 VO lines. Boundaries anchored to VO LINE STARTS so the picture cannot drift from the
# words. S1 L0-L1 (the lamp, the empty vessel, the award plate), S2 L2-L3 (coal waste, the cell,
# the atoms that bind and do not go in), S3 L4-L5 (the money splits, NSF's sentence prints),
# S4 L6-L7 (THE REFUSAL, the cable stops short and the twin draws itself), S5 L8-L10 (the tag
# still turned away, four papers, thin material), S6 L11-L12 (ACT 3, the lamp swings cold and
# Wyoming holds zero), S7 L13-L14 (one coal mine, the unlocated waste as an absence, a sentence
# not a supply), S8 L15-L16 (the payroll accusation, then the crack), S9 L17-L18 (THE ANSWER,
# energy constrained seats into the core and the plant runs), S10 L19-L21 (THE SIGNATURE, the
# ring lifts and the tag turns), S11 L22 (the button).
SCENE_START_LINE = [0, 1, 2, 4, 6, 8, 11, 13, 15, 17, 19, 22]


def _apply_caption_fixups(caps):
    """On-screen captions are force-aligned from Whisper's transcript of the
    PHONETICALLY-respelled audio, so proper-noun respellings ('Ex Prize', 'DRY-ad',
    'Nana' for Nenana) leak onto screen as typos (the 2026-07-20 panel caught all three
    as hard blockers). vo_script.json declares a `caption_fixups` {phonetic: display}
    map; apply it to every cue text (case-insensitive, word-boundary) so the REAL
    spelling always shows. Permanent pipeline fix so no future run leaks a respelling."""
    import re as _re
    sp = os.path.join(OUT, "vo_script.json")
    fixups = json.load(open(sp)).get("caption_fixups", {}) if os.path.exists(sp) else {}
    if not fixups:
        return caps
    # Use alnum lookarounds, NOT \b: \b fails on tokens whose edge char is punctuation
    # (e.g. "A.I." ends in '.', so \b after it never matches and the fixup silently no-ops —
    # the 2026-07-21c panel caught "A.I." leaking on screen while NOAA/GAIA normalized fine).
    # Longest keys first so a key that is a prefix of another can't pre-empt it.
    for c in caps:
        t = c.get("text", "")
        for wrong, right in sorted(fixups.items(), key=lambda kv: -len(kv[0])):
            t = _re.sub(r"(?<![A-Za-z0-9])" + _re.escape(wrong) + r"(?![A-Za-z0-9])", right, t, flags=_re.IGNORECASE)
        c["text"] = t
    return caps


def _rebalance_cues(caps):
    """Never break a caption between a number and its unit, or inside a proper noun.

    ADDED 2026-08-02 after a panel judge caught both failure modes in one film. Forced
    alignment chunks cues by width, which is correct for timing and blind to sense, so it
    produced "70 ash layers out of 8" / "tubes, a record they call virtually" (a number torn
    off its unit) and "It's confident about Katmai, Fisher" / "Caldera and Emmons Lake,
    because" (a two-word proper noun split across cards). Both read as errors to a viewer,
    because the eye finishes the line before the next one arrives.

    The fix is a MERGE, never a re-time: when a cue ends on a dangling token, it absorbs the
    next cue and takes its end time. Timing stays exactly as aligned, so caption sync is
    untouched; only the grouping changes. Merging is capped so a cue can't grow past what
    fits on two lines at phone size.
    """
    DANGLING = ("of", "out of", "the", "a", "an", "to", "in", "on", "and", "or", "for",
                "at", "by", "with", "from", "into", "than", "as", "is", "was", "which",
                "you", "it", "they", "we", "that", "this", "has", "have", "had", "be",
                # NUMBER WORDS, added 2026-08-09. The digit guard below cannot see these, and
                # the VO script spells every number out for the synth, so a panel judge found
                # "obligated about six" / "million dollars" split across two cards. A spelled
                # number is exactly as torn from its unit as a numeral is.
                "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
                "eighty", "ninety", "hundred", "thousand", "million", "billion")
    MAXLEN = 68
    # ORPHAN TAILS, added 2026-08-04. The forward-merge above only fires when the CURRENT
    # cue ends badly, so it never caught a cue whose NEXT cue is a stub. This film shipped
    # "Nobody has mapped the days you" / "can." and "It works, and Alaska barely uses" /
    # "it." -- both of the piece's punchlines alone on a card, which reads as a stutter and
    # throws the line away. A tail of one or two short words is never its own caption.
    ORPHAN_WORDS, ORPHAN_CHARS = 2, 15
    NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                    "ten", "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "sixty",
                    "seventy", "eighty", "ninety", "hundred", "thousand", "million", "billion"}
    out = []
    i = 0
    while i < len(caps):
        cur = dict(caps[i])
        while i + 1 < len(caps):
            t = cur["text"].rstrip()
            last = t.split()[-1] if t.split() else ""
            nxt = caps[i + 1]["text"].strip()
            first = nxt.split()[0] if nxt.split() else ""
            # NEVER merge across a full stop or across a VO line: a caption that spans two
            # sentences reads as one run-on, and one that spans two lines desyncs from the
            # shot boundary, which is anchored to the line start. Widening DANGLING without
            # this guard produced "It works, and Alaska barely uses it. NSF says Alaska lacks"
            # in one pass -- two sentences from two different lines on a single card.
            if cur.get("seg") != caps[i + 1].get("seg") or t.endswith((".", "!", "?")):
                break
            bad = (
                last.lower().strip(",.") in DANGLING            # dangling function word
                or last.rstrip(",.").isdigit()                  # a number torn from its unit
                # a proper noun split across cards: "... Fisher" / "Caldera ..."
                or (last.rstrip(",").istitle() and first.istitle() and not last.endswith("."))
                # the next cue is an orphan tail, e.g. "can." or "it."
                or (len(nxt.split()) <= ORPHAN_WORDS and len(nxt) <= ORPHAN_CHARS)
            )
            # an orphan tail gets a longer leash than a normal merge: a stub alone on a
            # card is a worse defect than a cue the renderer has to set on two lines, and
            # the renderer now wraps and auto-fits rather than overflowing its own bar.
            # A NUMBER AND ITS UNIT GET A LONGER LEASH, same reasoning as the orphan tail:
            # "obligated about six" / "million dollars" reads as an error to a viewer, because
            # the eye finishes the card before the next one arrives, and a slightly wide card
            # is a far smaller defect than a severed figure. The renderer wraps and auto-fits.
            _numtail = last.lower().strip(",.") in NUMBER_WORDS
            if len(nxt.split()) <= ORPHAN_WORDS and len(nxt) <= ORPHAN_CHARS:
                limit = 74
            elif _numtail:
                # 78 rather than higher ON PURPOSE. A number-unit merge is worth a slightly wide
                # card, and it is NOT worth a 97-character one. KNOWN LIMIT, logged rather than
                # papered over: on this run "obligated about six" / "million dollars" still splits,
                # because the VO line is 19 words and every width-based split point in it lands
                # badly. The real fix is chunking by SENSE rather than by width, which is a
                # bigger change than a delivery run should make.
                limit = 78
            else:
                limit = MAXLEN
            if not bad or len(t) + 1 + len(nxt) > limit:
                break
            cur["text"] = t + " " + nxt
            cur["end"] = caps[i + 1]["end"]
            i += 1
        out.append(cur)
        i += 1
    return out



# ---------------------------------------------------------------- end credits
# THE ATTRIBUTION RIDES IN THE PICTURE (2026-08-09, owner's request).
#
# The music is CC BY 4.0 and the licence requires attribution wherever the work is
# distributed. The sources are what make the film's claims checkable. Both were being pasted
# into a LinkedIn first comment by hand every run, which put them on exactly one of the
# surfaces the video reaches: a file on TikTok, embedded on the site, or forwarded to anyone
# carried neither. A judge raised the missing credit as a hard blocker and was right.
#
# So the credits are DERIVED HERE, from the same files the rest of the run is checked
# against, and rendered by lib/EndCredits.tsx. Nothing is typed per run, so the card cannot
# drift from the record, and scripts/credits_check.py fails the run if it ever does.
CREDITS_S = 6.5          # long enough to read a URL out loud, short enough not to be a cost

def _source_labels(srcs):
    """Group sources.json into lines a person can read off a phone in six seconds.

    One label per URL produced junk: the aggregate award query rendered as "API.NSF.GOV",
    the human-readable award page duplicated an id already listed, and eight near-identical
    rows pushed real sources off the card behind an "AND 4 MORE". Grouping by KIND is what a
    credit roll actually wants: every NSF award on one line, every indexed paper on the next.
    """
    awards, papers, other, seen = [], [], [], set()
    for e in srcs:
        url = (e.get("url") or "").strip()
        m = re.search(r"/awards/(\d+)\.json", url) or re.search(r"AWD_ID=(\d+)", url)
        if m:
            if m.group(1) not in awards:
                awards.append(m.group(1))
            continue
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url)
        if m:
            if m.group(1) not in papers:
                papers.append(m.group(1))
            continue
        if "eutils.ncbi" in url or "esearch.fcgi" in url:
            lab = "PUBMED QUERY"
        elif "awards.json?keyword" in url:
            continue          # the aggregate query behind the total, already implied by the ids
        elif "dggs.alaska.gov" in url:
            lab = "ALASKA DGGS"
        elif "epscor" in url:
            lab = "NSF EPSCOR"
        else:
            host = re.sub(r"^www\.", "", urlparse(url).netloc)
            lab = host.upper()
        if lab and lab not in seen:
            seen.add(lab)
            other.append(lab)

    labels = []
    if awards:
        labels.append("NSF AWARDS " + ", ".join(awards))
    if papers:
        labels.append("PUBMED " + ", ".join(papers))
    labels.extend(other)
    return labels


def _credits():
    """Build the credits block, or return None and say why. Never invents a credit."""
    try:
        music = json.load(open(os.path.join(OUT, "music_credit.json"))).get("credit", "").strip()
    except Exception:
        music = ""
    try:
        srcs = json.load(open(os.path.join(OUT, "sources.json"))).get("sources", [])
    except Exception:
        srcs = []
    labels = _source_labels(srcs)
    if not music:
        print("build_scenes: NO MUSIC CREDIT. out/dispatch/music_credit.json has no `credit`.")
        return None
    if not labels:
        print("build_scenes: NO SOURCE LABELS. out/dispatch/sources.json produced none.")
        return None
    # six lines is what fits above the licence strap at a size a phone can read
    if len(labels) > 6:
        labels = labels[:5] + [f"AND {len(labels) - 5} MORE AT ALASKAAIHQ.COM"]
    return {"music": music, "sources": labels, "site": "alaskaaihq.com",
            "seconds": CREDITS_S, "frames": round(CREDITS_S * FPS)}


def main():
    lines = json.load(open(os.path.join(OUT, "vo_lines.json")))["lines"]
    caps = _rebalance_cues(_apply_caption_fixups(json.load(open(os.path.join(OUT, "captions.json")))))
    start = {L["idx"]: L["start"] for L in lines}
    last_end = max(L["end"] for L in lines)
    total_s = last_end + TAIL
    total_f = round(total_s * FPS)

    bounds = [round(start[si] * FPS) for si in SCENE_START_LINE]
    scenes = []
    for i, b in enumerate(bounds):
        end = bounds[i + 1] if i + 1 < len(bounds) else total_f
        scenes.append({"from": b, "dur": end - b})

    # THE VO LINE START TABLE, and it is not a convenience (2026-08-02).
    # Scenes used to hardcode beat times as ABSOLUTE seconds copied off the storyboard. That
    # silently rots the moment the VO is re-synthesized, because a new take shifts every line
    # start by a different amount (this run: up to 1.8s of drift between the archived board and
    # the re-synth). The picture then plays against words it was not cut to, and no gate catches
    # it because the scene BOUNDARIES are still correct. Shipping the line table lets a scene
    # anchor each beat to the VO LINE IT BELONGS TO, so the film re-times itself with the voice.
    # the credits tail sits AFTER the story, so it lengthens the film without touching the
    # VO seconds band, which governs the spoken read and not the runtime
    cred = _credits()
    if cred:
        total_f += cred["frames"]

    props = {"captions": caps, "scenes": scenes, "total": total_f,
             "lines": [round(L["start"], 3) for L in sorted(lines, key=lambda x: x["idx"])]}
    # voice-acting data (scripts/vo_envelope.py): per-frame mouth envelope + the
    # vo-director's emphasis accents, for lib/voice.tsx. Optional, additive.
    mt = os.path.join(OUT, "mouth_track.json")
    ac = os.path.join(OUT, "accents.json")
    if os.path.exists(mt):
        props["mouth"] = json.load(open(mt))["values"]
    if os.path.exists(ac):
        props["accents"] = json.load(open(ac))
    if cred:
        props["credits"] = cred
        print(f"credits: {len(cred['sources'])} source label(s), {cred['seconds']}s tail "
              f"-> {cred['sources']}")
    json.dump(props, open(os.path.join(OUT, "episode_props.json"), "w"))
    print(f"total={total_f}f ({total_s:.2f}s)  mouth={'y' if 'mouth' in props else 'n'} accents={len(props.get('accents', []))}")
    for i, s in enumerate(scenes):
        print(f"  S{i+1}: from={s['from']} dur={s['dur']} ({s['dur']/FPS:.2f}s)")


if __name__ == "__main__":
    main()
