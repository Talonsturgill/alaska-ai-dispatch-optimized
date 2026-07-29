# Story selection — Dispatch run 2026-07-29

## Research shape

Round one fanned out six researcher agents (UAF/agency science, energy/grid, fisheries/wildlife,
defense/aviation/UAS, Alaska-Native-led and rural tech, wildcard). Five of the six independently
reported the same thing in their own words: a genuinely slow week for Alaska plus AI inside the
2026-07-19 to 2026-07-29 window, with most credible candidates either already on the exclusion
list or dated weeks outside it.

**Operational finding that colours the whole round:** the six-agent fan-out consumed the entire
session-wide WebSearch budget (200/200). Every follow-up agent launched afterwards could still
WebFetch specific URLs but could not search at all. So round two was run as targeted verification
of leads already in hand rather than as fresh discovery. This is logged as a real constraint on
this run's coverage, not dressed up as a slow news week, and Phase 1 of the routine has been
amended so it cannot recur silently.

## Candidates considered and why each landed where it did

### 1. Anthropic employees funding a gubernatorial candidate — RECUSED, not aired
ADN (2026-07-23) and Alaska Public Media (2026-07-24) reported six Anthropic employees donating a
combined $372,000 to Jonathan Kreiss-Tomkins, who campaigns on an Alaska data-center moratorium.
It is legitimate, well-sourced, in-window, and on-beat. This automation is Anthropic-built, so it
is not the right narrator for a story about Anthropic employees' political spending. Declined for
conflict of interest, recorded here rather than dropped invisibly. Same call the 2026-07-26 run
made on the same story.

### 2. Bristol Bay drone + AI sockeye counting — REJECTED by adversarial fact-check
Surfaced by two independent beats and looked strong until a validator tried to break it. It broke:
- Only ONE of six claimed sources could actually be fetched (KDLG, 2026-07-03). The Undercurrent
  News page that would have put it in-window returned 403 on every attempt including cache and
  archive routes, so its date could not be confirmed at all.
- Three headline statistics attributed to it (256 drone flights, 17,552 salmon images, 117
  orthomosaics) and a "12 to 18 hours faster" claim appear NOWHERE in the one readable source.
- A quote was misattributed. The real line is Ian Chiu, Machine Learning Developer, not the
  project lead, and the wording differed.
- Recency fails outright. Latest verifiable publication date is 2026-07-03, over three weeks stale.
- Distance fails too. This channel shipped "The Referee Arrives" on 2026-07-21, which already
  covered AI counting Alaska salmon, including the Sitka Tribe's AI video weir modernising a
  manual count. Bristol Bay swaps the river, the camera platform and the agency, but the beat is
  the same one eight days later.

### 3. Rocket Lab's $266M Space Force contract at Kodiak — REJECTED for having no AI angle
Real, in-window (announced 2026-07-21, covered 2026-07-27 and 2026-07-28 by SpaceNews, Stars and
Stripes and KMXT), well-sourced, and a genuine Alaska infrastructure win. But the researcher
checked all three articles and none mentions AI, autonomy or machine learning in connection with
this contract. The only autonomy thread available is that Rocket Lab's Electron family flies an
autonomous flight termination system, and no source confirms it flies on these Kodiak HASTE
missions. Running this would mean bolting an AI frame onto a launch-infrastructure story, which
the honesty rule forbids. Held as a strong candidate for a future run if an AI angle is ever
actually reported.

### 4. UAF pre-earthquake signal near Nenana — REJECTED, no AI angle
Published 2026-07-27, comfortably in-window, and genuinely interesting. On fetching the underlying
writeup the detection was done by conventional seismogram analysis. No AI, no ML, no algorithm
claim anywhere in the piece. Rejected on the same honesty ground as the Rocket Lab item, and
additionally adjacent to the 2026-07-25 seismic dispatch.

### 5. Alaska energy and grid beat — genuinely empty
The researcher fetched and confirmed that AIDEA's $175-190M ANWR 3-D seismic programme, Teck's
Red Dog mine-life extension, and the Southcentral Cook Inlet gas shortage all contain zero AI or
ML content, and reported that honestly rather than stretching any of them. One background lead
worth a future check: DeepGreen Holdings' FERC-docketed proposal for an underwater tidal-powered
AI data centre in Upper Cook Inlet, filed 2026-02-11, with no confirmable in-window update.

### 6. DOE Genesis Mission "Alaska Utility Optimization" — the one live lead
See the verdict section below.

## VERDICT on AURORA-AI, and the run's outcome

The dig succeeded and found something genuinely new. From the DOE Office of Science Genesis Mission
Phase I awards list posted 2026-07-22 (announcement DE-FOA-0003612), read directly as a primary
document rather than from a snippet:

    Wies, Richard | AURORA-AI: Alaska Utility Resilience & Optimization using Real-time AI
    | University of Alaska Fairbanks | Fairbanks | AK | 99775-7880

Confirmed a second time on the National Laboratory of the Rockies' own Genesis Mission page. No
Alaska outlet, and not UAF or ACEP themselves, has published a word about it. That is a real scoop.

**And it still does not clear the bar, on two independent grounds.**

**1. It is a title with no body.** Every source was fetched: the press release, its GlobeNewswire
twin, the HPCwire and Yahoo syndications, NLR's Genesis Mission page, energy.gov, and the OSTI PDF.
Not one contains an abstract, a method, a dataset, a named utility partner, a dollar figure, or a
timeline. A 60-second film purporting to explain AURORA-AI would be reading a grant title aloud.
The only material substantial enough to give it a body is Cordova, which leads directly to the
second problem.

**2. It structurally repeats the 2026-07-25 dispatch.** `dedupe.py` flagged the overlap on
[alaska, digital, twin, uaf] and the flag is correct on inspection, not a generic-token collision.
"The One It Didn't Hear" already told this audience that UAF had won an unreported federal award,
surfaced from a federal award database, to build real-time digital twins, with no press release in
existence. AURORA-AI is an unreported federal award, to UAF, surfaced from a federal awards
document, for real-time AI modelling, with no description in existence. Different agency, same news
to a viewer, four days apart. And the only way to give the story a body is the Cordova digital twin,
which is precisely the material that creates the overlap. The two problems are not independent:
fixing the thinness deepens the repeat.

Gaming the entity list to get a FRESH result would have cleared the gate and produced exactly the
cookie-cutter the gate exists to prevent.

## Outcome: an explicit no-story-clears-the-bar stop

No video Dispatch ships today. Six candidates were examined and every one failed an honest test:
two had no AI angle at all, one was broken by adversarial fact-check and repeated the 07-21 beat,
one was recused for conflict of interest, one beat was empty, and the best find is a title with no
body that repeats 07-25.

Forcing any of them would have meant either inventing an AI angle where the sources have none, or
shipping the same story twice in one week. The routine's own instruction is to say so and stop
rather than force a weak story, so that is what this run does.

## Leads carried forward (worth real money next time)

1. **AURORA-AI is a live, unclaimed scoop.** Nobody has it. It becomes a strong Dispatch the moment
   any of these lands: DOE publishes an abstract or dollar figure, UAF or ACEP announces it, or
   Richard Wies answers a direct request for comment. Direct outreach would beat every outlet in
   the state to it. Re-check `science.osti.gov` awards lists and the NLR Genesis Mission page.
2. **Rocket Lab at Kodiak** ($266M, up to 18 suborbital launches, new dedicated pad, ~140 acres
   added at Narrow Cape). A genuine Alaska win, in-window, three-source verified. It needs a real
   AI or autonomy angle before this channel can carry it. Worth watching for one.
3. **DeepGreen Holdings' underwater tidal-powered AI data centre** for Upper Cook Inlet, FERC
   preliminary permit filed 2026-02-11. Check the FERC eLibrary docket directly for movement.
4. **Alaska's $272M Rural Health Transformation Program**, including a Tanana Chiefs Conference
   drone-delivery proposal. Award notifications were expected mid-July and had not been published
   as of this run.
5. **Cordova's data centre inside the Humpback Creek hydro plant** (170 kW, 2026-03-05) sitting on
   top of the RADIANCE digital twin. Out of window now, but it is the most visually rich and best
   documented Alaska AI-energy story in the record, and it would make an excellent Dispatch on any
   fresh development.

---

# REVERSAL (2026-07-29, after owner review)

The owner's ruling on the stop above: **there is always news, and an empty run is a failed run.**
That ruling is correct and the reasoning above was wrong in three specific, identifiable ways.

1. **Circular.** Six researchers consumed the entire session-wide WebSearch budget in round one.
   The run then cited its own resulting blindness as evidence there was no news.
2. **Wrong window.** A fixed 10-day window was applied although the automation had skipped 07-27
   and 07-28. A skipped day means the audience has seen NOTHING, so the backlog is unspent
   inventory. The window should have widened, not narrowed.
3. **Dedupe misapplied.** AURORA-AI was killed on a generic-token overlap
   [alaska, digital, twin, uaf] when its actual SUBJECT, the electrical grid, has nothing to do
   with 07-25's landslide seismology. A viewer would not feel shown the same story twice.

And beneath all three: WebFetch was never capped. Alaska outlet front pages could have been swept
for free at any moment and were not. Stopping was cheap, so the run stopped.

## What the escalation ladder actually produced

- **Rung 2, outlet index sweep** (the rung originally skipped): 19 of 21 Alaska outlet indexes
  fetched and read. Two candidates, both correctly set aside. The Anchorage Claude Impact Lab is
  Anthropic-branded, so it draws the same conflict-of-interest recusal as the donation story.
  Bethel's Dirt Busters FIRST Lego League team is a lovely story and is classical robotics, not AI.
  The thin week is now a MEASURED finding rather than an assumption.
- **Rung 4, carried leads**: the 07-29 lead list's own item #1 is AURORA-AI.
- **Rung 7, pegged explainer**: available regardless, because the Genesis Mission has real body.

## STORY LOCKED

**Alaska got written into America's AI moonshot and nobody noticed.**

The DOE Office of Science Genesis Mission Phase I awards list, posted 2026-07-22, carries
`AURORA-AI: Alaska Utility Resilience & Optimization using Real-time AI`, University of Alaska
Fairbanks, PI Richard Wies. No Alaska outlet has it. Neither has UAF.

The earlier objection that it is "a title with no body" was solved the wrong way round. The film's
subject is not the grant abstract. It is that a national AI initiative, launched 2025-11-24 with
$293M in March 2026 and more than $800M in partner commitments by July 2026, reached down and put
Alaska's electrical grid on its list, and the reason it did is knowable even though the abstract is
not: Alaska's grid is islanded, and DOE has already proved the pattern in Cordova, where a
2,600-person microgrid became a real-time digital twin with 1,200 smart meters, 6 phasor measurement
units and a 1 MW battery, and where a 170 kW data centre now sits inside the Humpback Creek hydro
plant. Cordova is a SEPARATE, EARLIER project and must be labelled as such on screen.

The honest turn stays honest: the public record on AURORA-AI is one line long. That is a real open
question the audience should weigh, and the routine explicitly allows an open question as a dramatic
shape. It is not a reason to ship nothing.

Stance curious. Hero Sourdough with Cell, which differs from the last two heroes (SeismicStation,
RecordsMachine). Dedupe FRESH on the honest distinctive entity set.
