#!/usr/bin/env python3
"""Build the panel evidence pack, with sample times DERIVED FROM THE SHIPPED TAKE.

WHY THIS EXISTS (2026-08-03). The evidence pack for this run's first panel was cut at
STORYBOARD times while the shipped take's line starts differ by up to ~12s. The result
was that two of the three motion filmstrips sampled windows in which nothing was
happening: the punch fires at 38.1s and the strip was cut at 40.0, the drain runs
74.1 to 76.5 and the strip was cut at 74.0 and caught only its first 0.27s. All three
judges then reported, correctly and independently, that the film's signature events
"do not happen on screen", and the panel median came in at 6.43 against a 7.5 bar on
evidence that misrepresented the film.

That is the same class of bug as the 2026-07-15 stale-frame incident: an artifact read
BY PATH that looked plausible and was wrong. The fix is the same shape, a code guard
rather than a doctrine note. Filmstrip centres are now computed from vo_lines.json plus
a named offset INTO the line, so re-synthesising the voice moves the evidence with the
picture exactly as it moves the scenes.

Usage: python3 scripts/build_evidence.py [--video out/dispatch/dispatch_master.mp4]

SAMPLES THE 9:16 MASTER, because that is the cut config/panel_protocol.md convenes the panel
on. It sampled the square until 2026-08-09, when all three judges independently reported they
could not see the frame they had been asked to grade.
"""
import argparse, glob, json, os, subprocess, sys, time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
EV = os.path.join(REPO, "out", "evidence")

# (name, vo_line, seconds INTO that line where the move actually peaks)
MOVES = [
    # RE-ANCHORED 2026-08-13 for "The Machine Nobody Wrote Down". Every name above this line
    # belonged to a previous film and NONE of those beats exist here. Anchor names and offsets
    # are PER-RUN DATA and a run that changes the film changes them in the same commit, because
    # a strip pointed at the wrong moment produces a judge finding that is true about the
    # EVIDENCE and false about the FILM, which is the most expensive kind.
    # Each strip CENTRES on its own storyboard beat, and the board was remapped onto the
    # delivered vo_lines.json first, so board and strips are finally on one clock. One strip
    # per beat, thirty-seven of them, across all fourteen shots.
    ("land",  0,  0.00),  # opens on the object the film returns to
    ("tap",  0,  2.15),  # plants loop 1 before anyone knows what it is
    # 2.66 -> 2.15: the knuckle taps run f58-74, i.e. 1.93-2.47s, so a window centred
    # at 2.66 opened AFTER the move ended and three judges reported the hand frozen
    # across all 8 frames. They were right about the strip and wrong about the film.
    ("stamp",  1,  0.00),  # the one fact the plate does carry
    ("blanks",  1,  3.73),  # the contrast the whole film rests on
    ("form",  2,  0.00),  # names the absence as an absence
    ("record",  2,  4.52),  # the reason nobody can look it up
    ("drums",  3,  0.00),  # the news peg, dated
    ("nameplate",  3,  3.86),  # draws the two-award obligation instead of captioning it
    ("pair",  3,  7.03),  # names the actor before the film uses her
    ("ring",  4,  0.00),  # the two machines as equals
    ("note",  4,  3.59),  # the failure mode, drawn
    ("switchoff",  4,  6.11),  # keeps the operators competent and the room lit
    ("fuelstop",  5,  0.00),  # why the battery is there at all
    ("contactor",  5,  2.81),  # the saving made physical
    ("hold",  6,  0.00),  # the stake, and it plants loop 2
    ("unroll",  6,  3.75),  # the cost of not knowing, with nothing broken in frame
    ("collapse",  7,  0.00),  # why the standard fix does not fit
    ("drawer",  7,  3.86),  # the scale contrast that kills the method
    ("probeout",  7,  6.80),  # the running gag lands and the bottleneck is named
    ("probeback",  8,  0.00),  # the proposal, in the record's own words
    ("shutter",  8,  3.63),  # the answer read off the difference
    ("pinned",  9,  0.00),  # the fair objection opens
    ("change",  9,  3.39),  # THE TEST, held and not rescued
    ("strip",  9,  6.24),  # what changed while the photograph stayed the same
    ("seat", 10,  0.00),  # the rebuttal, inside the same picture
    ("crate", 10,  3.11),  # the shape of the answer
    ("panel", 11,  0.00),  # the operators' half, and it is theirs
    ("sandia", 11,  3.65),  # the utilities are ahead of the paperwork
    ("boundary", 11,  5.75),  # the operators' competence is shown, not asserted
    ("pullback", 12,  0.00),  # the honest size, said out loud
    ("sheet", 12,  2.80),  # THE SIGNATURE SHOT
    ("search", 13,  0.00),  # the film's one beat about its own name
    ("stencil", 13,  2.91),  # the checked absence, drawn as an absence
    ("breath", 14,  0.00),  # the tense discipline as a picture
    ("button", 14,  2.60),  # the held breath before the button
    ("pulse", 15,  0.00),  # the button, and loop 1 pays
    ("loopback", 15,  3.09),  # the last image, and the loopback
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(OUT, "dispatch_master.mp4"))
    ap.add_argument("--frames", type=int, default=14)
    a = ap.parse_args()

    lines = json.load(open(os.path.join(OUT, "vo_lines.json")))["lines"]
    start = {L["idx"]: L["start"] for L in lines}
    # THE FILM, NOT THE NARRATION. `end` was the last VO line's end (122.84s), so the
    # contact sheet stopped there and never photographed the final 2.6 seconds — which is
    # exactly where the sign-off plate and the music credit live. Five judges across three
    # rounds wrote "no composer credit is verifiable / the sign-off falls outside the
    # sampled stills" and every one of them was right about the pack. Sample the whole film.
    import json as _j
    _props = _j.load(open(os.path.join(OUT, "episode_props.json")))
    end = max(max(L["end"] for L in lines), _props["total"] / 30.0)

    os.makedirs(EV, exist_ok=True)
    for f in glob.glob(os.path.join(EV, "*.jpg")):
        os.remove(f)

    # ---- FRESHNESS GATE (added 2026-08-07, after it cost a whole panel round) ----
    # The 2026-08-07 run rendered a fix pass, built the pack while the encode was still
    # running, and graded the PREVIOUS cut. motion.json came back byte-identical to the
    # prior round, three judges wrote "the claimed fix did not land", and the run nearly
    # spent a fourth render chasing a defect that was already fixed. Nothing objected,
    # because every artifact existed and only their ORDER was wrong.
    # A pack is evidence about a FILM. If the file it samples is older than the engine that
    # drew it, it is evidence about a different film, so refuse rather than mislead a panel.
    _eng = os.path.join(REPO, "video-engine", "src")
    _newest_src, _newest_p = 0.0, ""
    for _root, _dirs, _files in os.walk(_eng):
        for _f in _files:
            if _f.endswith((".tsx", ".ts")):
                _fp = os.path.join(_root, _f)
                _m = os.path.getmtime(_fp)
                if _m > _newest_src:
                    _newest_src, _newest_p = _m, _fp
    if not os.path.exists(a.video):
        sys.exit(f"build_evidence: {a.video} does not exist. Encode before building a pack.")
    _vid_m = os.path.getmtime(a.video)
    if _newest_src and _vid_m < _newest_src:
        sys.exit(
            "build_evidence: REFUSING TO BUILD A STALE PACK.\n"
            f"  video : {a.video}\n          modified {time.strftime('%H:%M:%S', time.localtime(_vid_m))}\n"
            f"  engine: {os.path.relpath(_newest_p, REPO)}\n          modified "
            f"{time.strftime('%H:%M:%S', time.localtime(_newest_src))}\n"
            "  The cut is OLDER than the engine that draws it, so this pack would describe a\n"
            "  film that no longer exists. Judges would report fixes as not landing and the\n"
            "  run would re-fix things that are already fixed. Re-render and re-encode first.\n"
            "  (Waiting on encode_deliverables.sh to FINISH is usually the missing step.)")

    from PIL import Image, ImageChops, ImageDraw

    # ---- contact sheet: an even sweep, PLUS every scene photographed once it has settled ----
    # An even sweep alone samples a 125s film every 9.3s, and on 2026-08-09 that stride landed
    # inside the NSF quote's typewriter reveal. All three judges read a half-typed line as a
    # truncated string, one of them raised it as a hard blocker, and the pack had no frame
    # between 41.8s and 51.0s to settle it with. The film was correct. The evidence was not.
    #
    # A stride can always straddle a reveal, so the fix is not a smaller stride, it is a sample
    # taken WHERE NOTHING IS STILL ANIMATING: near the end of each scene, after every type-on,
    # slide and spring in it has finished. That is the state the shot actually holds, and it is
    # the state a judge should be grading.
    _sweep = [round(end * (i + 0.5) / a.frames, 2) for i in range(a.frames)]
    _settle = []
    for _sc in _props.get("scenes", []):
        _s_end = (_sc["from"] + _sc["dur"]) / 30.0
        _t = round(min(end - 0.1, _s_end - 0.5), 2)      # half a second before the cut
        if _t > 0.2:
            _settle.append(_t)
    # dedupe against the sweep, since a sweep sample that already sits in a settled tail is fine
    times = sorted(set(_sweep) | {t for t in _settle if all(abs(t - s) > 0.6 for s in _sweep)})
    print(f"contact sampling: {len(_sweep)} even + "
          f"{len(times) - len(_sweep)} scene-settle = {len(times)} frames")
    paths = []
    for t in times:
        p = os.path.join(EV, f"f{t:05.1f}.jpg")
        subprocess.run(["ffmpeg", "-y", "-ss", str(t), "-i", a.video, "-frames:v", "1",
                        "-q:v", "3", p, "-v", "error"], check=True)
        paths.append((t, p))
    ims = [(t, Image.open(p).convert("RGB")) for t, p in paths]
    w, h = ims[0][1].size
    tw, th = int(w * 0.32), int(h * 0.32)
    cols = 5
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 18)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (t, im) in enumerate(ims):
        x, y = (i % cols) * tw, (i // cols) * (th + 18)
        sheet.paste(im.resize((tw, th)), (x, y))
        d.text((x + 4, y + th + 3), f"t={t:.1f}s", fill="black")
    sheet.save(os.path.join(EV, "contact_square.jpg"), quality=90)
    print(f"contact sheet: {len(ims)} frames across {end:.1f}s ->", sheet.size)

    # ---- the caption cue list, so caption claims are gradeable at all ----
    # A judge wrote "the pack carries no caption cue or word-timing file... I do not credit
    # a fix I cannot see", about a caption defect that WAS fixed. Stills sample 14 moments
    # out of ~125 seconds, so a caption defect between two samples is unfalsifiable in
    # either direction. The cue list is 6KB and makes every caption in the film checkable.
    # episode_props.json now carries cues in the ENGINE's shape, {t, d, text}, because
    # build_scenes converts at the boundary (2026-08-12: the props used to hand the engine
    # {start, end}, which its reader compares against undefined, and the film shipped with an
    # empty caption band for all 4602 frames). This reader still spoke the old shape and
    # died on KeyError. Accept either, and emit start/end here because that is what a human
    # grading a cue list wants to read.
    def _se(c):
        if "t" in c and "d" in c:
            return round(c["t"], 2), round(c["t"] + c["d"], 2)
        return round(c["start"], 2), round(c["end"], 2)

    _cues = [{"start": s, "end": e, "text": c["text"]}
             for c in _props.get("captions", []) for s, e in [_se(c)]]
    _j.dump({"note": "every open-caption cue in the delivered cut, in order, as built into "
                     "episode_props.json and rendered by the episode. Times are seconds from "
                     "the first frame. Grade caption text against THIS, not against the 14 "
                     "contact stills, which sample only a fraction of the runtime.",
             "count": len(_cues), "cues": _cues},
            open(os.path.join(EV, "caption_cues.json"), "w"), indent=1)
    print(f"caption cues: {len(_cues)} written to evidence")

    # ---- motion filmstrips, CENTRED ON THE REAL MOVE ----
    #
    # A STRIP THAT STRADDLES A CUT MEASURES THE CUT (2026-08-13). Two judges independently
    # worked this out from the pack and one put it plainly: "every strip reporting 42-67%
    # sits exactly on a storyboard shot boundary, so those numbers measure cuts and not
    # animation." They were right, and it is the worst kind of wrong, because motion.json's
    # own note tells a judge to read these figures BEFORE recording a beat as frozen. The
    # instrument was handing out 66.7% for a hard cut between two frozen tableaux and a judge
    # who trusted it would have scored motion that does not exist.
    #
    # The cause is arithmetic: many MOVES carry off=0.0, so the centre IS the line start, and
    # a line start is a shot boundary. An 8-frame window centred there is 4 frames of the
    # outgoing shot and 4 of the incoming one.
    #
    # So the window is now slid off the boundary into whichever shot the centre belongs to,
    # and every entry records whether it had to move. changed_pct now means WITHIN-SHOT
    # motion in every row, which is the only thing it was ever supposed to mean.
    bounds = []
    try:
        _sc = json.load(open(os.path.join(OUT, "episode_props.json"))).get("scenes") or []
        bounds = sorted({round(s["from"] / 30.0, 3) for s in _sc if s.get("from")})
    except Exception as _e:
        print(f"  (no scene boundaries available, strips not de-straddled: {_e})")

    WIN = 8 / 30.0
    motion = {}
    for name, line, off in MOVES:
        if line not in start:
            print(f"  SKIP {name}: vo line {line} missing")
            continue
        centre = start[line] + off
        t0 = max(0.0, centre - 0.13)          # 8 frames at 30fps spans ~0.27s
        straddled = next((b for b in bounds if t0 < b < t0 + WIN), None)
        if straddled is None:
            # A CUT IS NOT ALWAYS A SHOT BOUNDARY (2026-08-13, round 4). All three judges
            # caught the same row: filmstrip_pulse visibly cuts between frames 4 and 5 while
            # this file marked it straddled_cut false, because that cut is a BEAT change
            # inside S14 (the threshold card giving way to the plate) and the scene table
            # knows nothing about it. So the boundary list is not the authority any more --
            # the PIXELS are. Cut a cheap probe pair either side of each interior frame and
            # slide off whichever gap is a cut. Empirical beats declarative here, because the
            # thing being measured is exactly "did the picture change wholesale".
            probe = os.path.join(EV, f"_p_{name}_%d.jpg")
            subprocess.run(["ffmpeg", "-y", "-ss", f"{t0:.3f}", "-i", a.video, "-frames:v", "8",
                            "-vsync", "0", "-q:v", "6", "-vf", "scale=120:-1", probe,
                            "-v", "error"], check=False)
            pg = sorted(glob.glob(os.path.join(EV, f"_p_{name}_*.jpg")),
                        key=lambda q: int(q.rsplit("_", 1)[1].split(".")[0]))
            ims = [Image.open(q).convert("L") for q in pg]
            for k in range(len(ims) - 1):
                d = ImageChops.difference(ims[k], ims[k + 1]).histogram()
                px = ims[k].size[0] * ims[k].size[1]
                if 100.0 * sum(d[40:]) / px > 22.0:          # a wholesale picture change
                    straddled = t0 + (k + 1) / 30.0
                    break
            for q in pg:
                os.remove(q)
        if straddled is not None:
            # keep the shot the CENTRE belongs to, and sit clear of the cut by one frame
            # EPSILON, and it is not a nicety (2026-08-13, round 5). A beat whose centre IS the
            # cut -- every strip with off=0.0 -- compares equal, and float representation decided
            # which way it fell. On this run centre and cut were both 115.76 and it slid BACKWARD,
            # so the button strip showed only the OUTGOING shot and a judge correctly reported
            # "the plate has not returned" for a beat where the plate returns exactly on its line.
            # A tie must resolve FORWARD, into the shot the beat is about.
            t0 = (straddled + 1 / 30.0 if centre >= straddled - 1e-6
                  else max(0.0, straddled - WIN - 1 / 30.0))
            print(f"  filmstrip {name}: window straddled the cut at {straddled:.2f}s, "
                  f"slid to {t0:.2f}s so the measurement is within-shot")
        subprocess.run(["ffmpeg", "-y", "-ss", f"{t0:.3f}", "-i", a.video, "-frames:v", "8",
                        "-vsync", "0", "-q:v", "3",
                        os.path.join(EV, f"s_{name}_%d.jpg"), "-v", "error"], check=True)
        g = sorted(glob.glob(os.path.join(EV, f"s_{name}_*.jpg")),
                   key=lambda q: int(q.rsplit("_", 1)[1].split(".")[0]))
        xs = [Image.open(q).convert("RGB") for q in g]

        # ------------------------------------------------------------------
        # MEASURE THE MOTION AND PRINT IT ON THE STRIP.
        #
        # Added 2026-08-05 after this cost FOUR panel rounds. Judges kept
        # reporting a beat as frozen while a pixel diff of the very frames the
        # strip is cut from showed 13.9 percent of the frame changing by more
        # than 12/255, with a max delta of 221. Two judges saw the motion and
        # two did not, on the same JPEG.
        #
        # Both readings were honest. The strip downscaled each 1080x1920 frame
        # to 22 percent, and a soft shadow raking across cream stock simply does
        # not survive that. The film was fine and the EVIDENCE was lying, which
        # is the same class as the stale-frame and wrong-anchor bugs above: an
        # artifact that looked plausible and misrepresented the film.
        #
        # So the panel now gets the number alongside their eyes. "I cannot see
        # it" and "it is not there" are different findings and a judge should
        # not have to guess which one they are making.
        # ------------------------------------------------------------------
        d = ImageChops.difference(xs[0].convert("L"), xs[-1].convert("L"))
        hist = d.histogram()
        px = xs[0].size[0] * xs[0].size[1]
        changed = 100.0 * sum(hist[12:]) / px
        peak = max((i for i, c in enumerate(hist) if c), default=0)
        motion[name] = {"centre_s": round(centre, 2), "changed_pct": round(changed, 1),
                        "peak_delta": peak, "window_start_s": round(t0, 2),
                        "straddled_cut": straddled is not None,
                        "within_shot": True}

        t2, h2 = int(w * 0.34), int(h * 0.34)
        st = Image.new("RGB", (len(xs) * t2, h2 + 34), "white")
        for i, im in enumerate(xs):
            st.paste(im.resize((t2, h2)), (i * t2, 34))
        dr = ImageDraw.Draw(st)
        dr.text((8, 9), f"{name}  centred {centre:.2f}s   "
                        f"frame 1 vs frame 8: {changed:.1f}% of pixels changed "
                        f"(peak delta {peak}/255)  <- MEASURED, not asserted",
                fill="black")
        st.save(os.path.join(EV, f"filmstrip_{name}.jpg"), quality=92)
        for q in g:
            os.remove(q)
        print(f"  filmstrip {name}: vo line {line} +{off}s -> centred {centre:.2f}s, "
              f"strip starts {t0:.2f}s, motion {changed:.1f}% peak {peak}")

    json.dump({"note": "frame 1 vs frame 8 of each filmstrip window, measured on the "
                       "delivered cut. changed_pct is the share of pixels differing by "
                       "more than 12/255. A judge who cannot SEE motion in a strip should "
                       "read this before recording that the beat is frozen. EVERY WINDOW "
                       "HERE IS WITHIN A SINGLE SHOT: any window that straddled a cut has "
                       "been slid clear of it and is marked straddled_cut, because a strip "
                       "spanning a cut measures the cut and reports it as animation. Before "
                       "2026-08-13 it did not do this, and the large figures in older packs "
                       "are shot changes, not motion. Cross-check against "
                       "motion_registered.json, which solves the camera out per shot.",
               "strips": motion},
              open(os.path.join(EV, "motion.json"), "w"), indent=2)
    print("  motion.json written:", {k: v["changed_pct"] for k, v in motion.items()})

    import subprocess as _sp
    # SAMPLE THE CREDITS CARD (2026-08-12, panel round 6). The still sampler walks the VO's
    # named moves, and the credits sit AFTER the last word, so it never sampled them. Three
    # judges in one round reported the CC BY 4.0 music credit as unverifiable or absent and
    # docked Sound for it; the card was on screen the whole time, at 127.5s, and the pack
    # simply stopped at 125.0. Attribution is a licence condition, so "the evidence cannot
    # show it" is not an acceptable resting place. Grab a frame from the last two seconds.
    try:
        _dur = float(_sp.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", a.video], capture_output=True,
                             text=True).stdout.strip())
        _t = max(0.0, _dur - 2.0)
        _sp.run(["ffmpeg", "-v", "error", "-ss", f"{_t:.2f}", "-i", a.video, "-vframes", "1",
                 "-q:v", "3", "-y", os.path.join(EV, f"f{_t:05.1f}.jpg")],
                capture_output=True, text=True)
        print(f"  credits card sampled at {_t:.1f}s")
    except Exception as _e:
        print(f"  !! could not sample the credits card: {_e}")

    # THE AUDIO REPORT IS PART OF THE PACK, SO THIS BUILDS IT (2026-08-12).
    # It used to be whatever audio_report.py last happened to write, whenever that was. On
    # this run the pack shipped a report describing a 153.5s cut to a panel grading a 119.57s
    # one: last_word_ends_s 150.94 and gap entries at 129.52s and 134.98s, both past the end
    # of the film, with loudness figures a full 0.65 LU off the delivered master. All three
    # judges spotted it and one filed it as an evidence-hygiene flag, which is a judge's
    # attention spent on our filing rather than on the film.
    #
    # Every other artifact in this directory is rebuilt from the delivered bytes each time.
    # This one was the exception purely because it lived in a different script, so run that
    # script here. A stale number in an evidence pack is worse than a missing one: a missing
    # file is obviously missing, and a stale file is quietly believed.
    _ar = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio_report.py")
    _r = _sp.run([sys.executable, _ar], capture_output=True, text=True)
    if _r.returncode == 0:
        print("  audio_report.json rebuilt from the delivered cut")
    else:
        # Loud, and not fatal: the rest of the pack is still worth having, but nobody should
        # be able to read past this and assume the report describes this film.
        print("  !! audio_report.json COULD NOT BE REBUILT and may describe a different cut:")
        print("     " + (_r.stderr or _r.stdout).strip()[-300:])


if __name__ == "__main__":
    main()
