# Cast & Asset Manifest — Alaska.Ai Dispatch engine

The living inventory of everything the Dispatch video engine can draw. **Every run
reads this FIRST and CASTS from this shelf by default** — reuse with fresh staging is
the point of the library (see the library mandate, `prompts/dispatch_routine.md` §4.3a,
rebalanced 2026-07-20). Grow it when a story finds a real gap, and register every
addition here in the same commit. Composition freshness comes from the storyboard
fingerprint + camera + staging, not from re-drawing the cast.

When you add or upgrade an asset, update this file in the same commit. Keep entries
one line: `Name — kind — file — params/poses — status`.

## Characters (people)
- `Character` — human rig — Character.tsx — poses: stand/arms-crossed/point/panic/raise (raise NEW 2026-07-20b: one arm thrust high w/ micro-sway, scenes mount a prop at the raised hand); emotions: neutral/angry/worried/shock/smug; outfits: parka/suit/worker/puffer/flannel/vest/referee (referee NEW 2026-07-20b: cream shirt w/ ink official stripes + collar + brass whistle on a lanyard); headgear: bare/beanie/cap/trapper/hood (bands raised off the eyes 2026-07-18b, no more 'burglar mask'); `talking` prop = TalkMouth lip-flap; form-shaded + rim + contact shadow — ACTIVE

## Characterized objects (heroes with a face / bespoke silhouette)
- `ServerMachine` — the data-center/AI antagonist — kit.tsx — emotions: greedy/focused/nervous/shock/ghost; tints: steel/copper; `talking` prop = lip-flap — ACTIVE
- `MachineShadow` — faceless institutional monolith (no face, deliberately cold) — Episode.tsx (2026-07-18) — form-shaded + brushed metal + rim + contact shadow — ACTIVE
- `Sourdough` — NET-NEW 2026-07-19 — personified regional power plant hero, warm/rounded/blocky (deliberate shape-language OPPOSITE of ServerMachine/MachineShadow's cold rectilinear institutions) — kit.tsx — emotions: proud/confident/faltering/frozen; `glow` 0..1 drives his furnace-window-chest emotional tell (dims at a story's turn); `accent` 0..1 for VO-emphasis reactivity; form-shaded + rim + contact shadow — ACTIVE
- `Cell` — NET-NEW 2026-07-19 — battery-storage sidekick on sled runners, a genuine parallel-bet visual (grid-modernization hedge) — kit.tsx — `chargeLevel` 0/1/2 charge-bar face; form-shaded + rim + contact shadow — ACTIVE
- `SatelliteEye` — NET-NEW 2026-07-23 — the imaging-satellite AI-presence hero for "Counting Belugas From Orbit" (NOAA GAIA machine-vision). Deliberate shape language: a compact, boxy, wide-winged, EARNEST little worker looking down at Earth, the opposite of a cold institutional monolith. A single DOWNWARD camera-EYE is the emotional tell (iris dilates while `searching`, squints under `strain`, CLAMPS small+bright when `found` with lock ticks, cyan scanning to amber found). `emotion` searching/straining/found/waiting; `eyeLock` 0..1; `accent` 0..1 VO-reactivity; `scanCone` 0..1 fades a downward imaging cone; `strain` 0..1 a comic squint + faint sweat bead (satellite only, NEVER the whale). Indigo solar wings w/ cell grid + sun-glint, high-gain dish, blinking lights, thruster nozzles. Built to the depth bar (tones/FormGradient/RimLight/ContactShadow) with idle bob + blink + panel shimmer — kit.tsx — ACTIVE
- `Petrel` — NET-NEW 2026-07-24 — the SAR "drone-in-a-box" hero for "The Box That Waits for You". Deliberate shape language: small, ROUNDED, WARM-cream helper (opposite of a cold institutional monolith), genuinely capable but INCOMPLETE without the pilot. Single teal thermal camera-EYE is the emotional tell. Signature interaction DEFER-TO-THE-HAND: `heading` leans/faces the drone toward a pointed direction; idle-searching drifts to the WRONG side, then SNAPS to `heading`. `emotion` cocky/eager/lost/purposeful/deferential; `eyeDilate` 0..1 (wide search -> clamped lock, with lock ticks); `accent` VO-reactivity; `heading` deg; `groundY` contact shadow. Built to the depth bar (tones/FormGradient/RimLight/ContactShadow, idle bob + blink + rotor spin) — kit.tsx — ACTIVE
- `PetrelDock` — NET-NEW 2026-07-24 — the cold slate "drone-in-a-box" the industry ships (quarantined blue-gray, rectilinear, the deliberate opposite of Petrel's warm roundness); `lidOpen` 0..1 tips the hinged lid, Petrel rises out of it in the hook + button — kit.tsx — ACTIVE
- `Vale` — NET-NEW 2026-07-20 — the GUARDIAN autonomous wildfire-response drone (hero). Deliberate shape language: rounded/symmetric/protective gunmetal machine, the opposite of the fire's chaos AND the ServerMachine's greed. A single expressive camera-EYE is the emotional tell (iris dilates scanning, CLAMPS small+bright on a lock, with lock ticks); quad rotor arms with spinning blur discs, a suppressant-tank belly with a fill gauge, landing skids, blinking running lights. `emotion` vigilant/locked/resolute/calm; `eyeLock` 0..1; `accent` reactive; `groundY` draws a contact shadow when landed; idle hover-bob + blink. Built to the depth bar (tones/FormGradient/RimLight/ContactShadow) — kit.tsx — ACTIVE

## Craft advance this run (2026-07-19): every claim/format/story is a "live, tested run", not a batch script
- Fixed two real infrastructure bugs discovered while producing this run's VO (both would recur on EVERY future dispatch with numbers/dates in the script, not just this one): `scripts/vo_soundcheck.py`'s WER canonicalizer silently dropped `$`/`%` symbols and mis-split comma-grouped numbers (inflated WER on every number-heavy script); `scripts/vo_synth_gemini.py`'s `_align_wholefile` (a) passed the script's own opening words as Whisper's `initial_prompt`, which made Whisper hallucinate-skip the real audio matching it (reproduced: dropped the first ~14.6s of a real take), and (b) collapsed multi-word token expansions to word[0] only, desyncing the alignment arrays. Both fixed; see the scripts' own comments for the reproduction notes.

## Sensors (the instrument family) — lib/sensors.tsx
REGISTERED 2026-07-25 (this file existed since 2026-07-21c but was NEVER registered here, so two
runs of Gate 0D could not find its assets. That is the manifest-drift bug this run fixed.)
- `SatelliteEye` — the ORBITAL EYE — sensors.tsx — NOTE: a second copy also lives in kit.tsx. Prefer the sensors.tsx one; the duplicate is a known hazard (see UPGRADE_BACKLOG).
- `ListeningMooring` — the SEAFLOOR EAR, passive-acoustic node — sensors.tsx — anchor base, ribbed cylinder, mint hydrophone dome, tether float; `detect` 0..1 blooms sonar rings — ACTIVE
- `SeismicStation` — NET-NEW 2026-07-25 — the GROUND EAR, hero of "The One It Didn't Hear". The shelf had an orbital eye and a seafloor ear but nothing that listens to the GROUND. Deliberate shape language: SOFT ROUND INSTRUMENT against HARD ANGULAR LAND. THE TELL IS A BRASS GRAMOPHONE HORN built as a real cone in 3/4 (straight taper walls, hollow dark mouth, rolled rim, receding interior throat rings) — pass 1 drew it as a flat face-on ellipse and it read as a lollipop. `emotion` listening (lazy quarter-turn sweeps) / straining (telescopes out past comfort, rim trembles, stress lines) / missing (horn rolls down to point at the dirt, rim dented, lamp DARK) / heard (snaps rigid, rim flares, lamp fires amber with sound arcs arriving into the mouth). Also has a real FACE (brow bar that drops, two lidded eyes with highlights that TRACK via `look`, desynced blink) — pass 1 had no face and read inert. `lamp` 0..1 lights ONLY when emotion==='heard', so a lit lamp always means a detection actually fired. `heading` deg, `accent` VO-reactivity, `groundY`, `tint` so a night palette re-tints without a re-draw. Solar-panel brim, stub antenna with secondary sway, ribbed half-buried post, vent slots, bezel ticks, hard angular dirt collar. Form-shaded + rim + contact shadow — ACTIVE
- Look-dev: `StationLook` (StationLook.tsx) — the four emotional states plus NightGrade, in one frame.

## Paper & records (the interior family) — lib/paper.tsx + lib/records.tsx
NET-NEW 2026-07-26 ("The Field That Stopped in 2019"). The shelf had ELEVEN biomes and every
one was outdoors, and materials.tsx had eight substance overlays and none was paper. This
dispatch happens entirely inside an office, so both gaps were load-bearing.
- `PaperOfficeBG` — the library's FIRST INTERIOR BIOME — paper.tsx — a fluorescent-lit records
  room: a back wall of filing cabinets in one-point recession (THE DARK ANCHOR, #4A5A66), a lit
  dust column, a desk plane, and a front parallax drift of loose sheets. Params `parallax`,
  `drift`. Built against a HIGH flatness rating with an ENFORCED value ladder (10 to 12 percent L
  per depth plane) because a high-key flat-lit cream interior is the textbook beige-page recipe — ACTIVE
- `PaperFiber` — the paper SUBSTANCE (the materials.tsx gap) — paper.tsx — fiber tooth plus a pale
  ruled grid so a sheet reads as printed stock, deterministic imul hash, never Math.random — ACTIVE
- `Sheet` — a sheet with REAL BODY — paper.tsx — the numeric shadow contract lives in code, not in
  prose: 2px edge, drop shadow offset 4 down / 2 right at 22 percent, optional curled corner with a
  30 percent under-shadow. Under flat light this is what makes paper read as a solid — ACTIVE
- `TaperedCone` — the TRUE THREE-QUARTER CONE — paper.tsx — REBUILT IN PASS 2 after the panel
  raised it as a hard blocker. Pass 1 drew a dark ellipse at FULL mouth width over the body and the
  whole thing read as a black satellite dish, which is the SAME lollipop failure the 2026-07-25
  SeismicStation horn hit. The fix is three things: a much flatter rim ellipse so the camera looks
  ALONG the cone rather than down into a dish, a dark interior INSET and pushed down the throat so a
  lit rim band and both straight taper walls stay visible, and the two walls drawn as SEPARATE lit
  and shaded faces, which is what actually sells a cone when there is no dramatic falloff to help.
  `mouthW` and `stemW` are independent on purpose — ACTIVE
- `StateLetter` — the letter, WITH NO FACE — paper.tsx — a creative gate ruled the first pass a
  violation: a cartoon envelope performing a wince is a gag played BY the object that carried a
  citizenship challenge to thousands of real people. Reluctance now lives entirely in PHYSICS, an
  `open` flap that hesitates against the paper's own stiffness and flips up about its hinge. Params
  `open`, `line`, `faceDown` — ACTIVE
- `FullTapeMachine` — fixed-capacity answering machine — paper.tsx — two visible reels, a finite
  tape loop, a FULL tag on a spring. Exists so a COUNT can be felt against a KNOWN OBJECT WITH FIXED
  CAPACITY instead of as a ratio, which is how this film honoured a ban on dividing two figures that
  were different kinds of object. `fill` 0..1 seizes the reels — ACTIVE
- `RecordsMachine` — the run's HERO — records.tsx — ONE machine, not two, so its output stem has an
  antecedent before the narration references it. The intake mouth cranks wider tooth by tooth via
  `mouthOpen` while the stem never changes width, which is the entire thesis in two independent
  parameters. `strain` pops rivets one at a time and pins a pressure gauge, so the stem's refusal is
  STAGED AS MOTION rather than declared as an absence — ACTIVE
- `ThreePipeCutaway` — the SAME machine, opened — records.tsx — the thesis drawn as a physical
  ABSENCE. Pipe one inbound and pipe two outbound are fat and working; pipe three, which would carry
  a naturalization certificate back in, ENDS IN CAPPED OPEN AIR with certificates dropping onto a
  drift pile. `disclose` staggers the reveal so the capped pipe is the LAST information; `lock`
  slams a pawl onto the date wheel. KNOWN WEAKNESS: two panel judges found the capped pipe still not
  legible enough as an absence at sampled frames. Next pass should scale the pipes up, label the
  capped end, and animate flow in one and two so the dead one reads by contrast — ACTIVE

## Under-ice (the library's FIRST SUBMERGED WORLD) — lib/underice.tsx
NET-NEW 2026-07-30 for the Arctic Mobile Observing System Dispatch (ONR Year 9, 91 FR 46055). Two
real gaps justified this rather than inventing net-new work: the shelf had an orbital eye, a seafloor
ear, a ground ear and two aerial machines but NO MACHINE THAT SWIMS, and NO SUBMERGED BIOME existed, so a story set under a metre of sea ice could not be
staged at all.
- `IceGlider` — the run's HERO, the UNDER-ICE SWIMMER — underice.tsx — Shape-language decision that
  drives the whole asset: a buoyancy-driven glider HAS NO PROPELLER, so its verb cannot be thrust, it
  is PITCH AND SINK. That is drawn literally as a slow sawtooth on an irrational period, and the tail
  is deliberately BARE so the missing propeller reads as a design fact rather than an omission.
  `emotion` gliding / listening / hibernating / lost / fixed, carried by THREE things at once because
  one eye was not enough to read at frame size (the same lesson as the 07-25 SeismicStation horn and
  the 07-26 TaperedCone): the iris (real 8 to 20 range, CLAMPS small and bright on `fixed` meaning the
  machine knows where it is), the body attitude (yaw wanders on `lost`, squares up on `fixed`), and a
  BROW BAR whose angle carries the state even when the eye is dark. `pitch` overrides the sawtooth,
  `ping` + `pingFrom` bloom inbound acoustic arcs ARRIVING from a bearing (this machine receives, it
  does not emit), `eyeLock`, `rime` creeps frost from the tail forward as it sits still, `accent` VO
  reactivity, `gain` freezes vitals for a held beat. Mid-body swept wings drawn as separate lit and
  shaded faces, CTD sensor stack on the spine, pressure-hull seams, payload bay. Routed through
  vitals(). Taste-looped 4 passes — ACTIVE
- `UnderIceBG` — the THIRTEENTH biome and the first submerged one — underice.tsx — inverts every other
  biome in the kit: the bright hard detailed plane is the CEILING and depth falls away below into near
  black, with an enforced value ladder so three depth planes separate inside one hue family (the
  flat-blue trap an underwater scene falls into by default). The jagged underside is ONE CONTINUOUS
  POLYGON of mostly-flat runs punctuated by three irregular pressure-ridge keels. HARD-WON: pass 2
  drew 22 evenly spaced outlined triangles and they read as decorative BUNTING, pass 3 made them a
  uniform sawtooth and it read as a ZIPPER. A rough edge has to be part of the slab silhouette, not a
  row of separate objects under it, and it needs flat runs for the keels to read against. `lead` opens
  a crack of daylight overhead, the only warm colour available down here and therefore the strongest
  focal signal in frame, so spend it once. `iceY`, `parallax`, `motes`, `hue` — ACTIVE
- `AcousticSource` — the moored 900 Hz navigation source the glider listens FOR — underice.tsx —
  deliberately hard and vertical against the glider's soft horizontal drift: seabed anchor, taut
  mooring line, ribbed transducer can, `pulse` emits expanding rings. The emit/receive split is a
  deliberate pair with IceGlider's inbound arcs — ACTIVE
- `RingedSealGhost` — the UNFILLED CONTOUR, net-new 2026-07-30 — underice.tsx — added mid-run after
  the Gate 0D art critic caught that beat 19 needed this animal and the shelf's marine mammals were
  Beluga, Orca, Humpback, Walrus and SeaOtter, so the one ESA-threatened species the film names was
  about to be improvised as an ellipse. THE FOURTH SHAPE GRAMMAR: in a world where every object is
  form-shaded, UNSHADED is itself a grammar and it is this film's whole thesis. Three things make the
  absence read AS absence rather than as an unfinished asset, which is the live known weakness on the
  07-26 ThreePipeCutaway: the contour is DASHED (a solid outline reads as a style choice, a dashed one
  reads as not filled in), the interior is a true void with no hatch, and the caller supplies a label
  so the absence is named rather than inferred. Ringed-seal tells drawn as outline only: pale flank
  rings, roman muzzle, whiskers, an eye that is a hole rather than a dot, splayed rear flippers.
  `dash` can solidify it for any future non-absence use — ACTIVE
- Look-dev: `UnderIceLook` (UnderIceLook.tsx) — all five glider states, the biome, and the source in
  emitting and silent states, in one frame.

## Fauna (the Alaska bestiary) — lib/fauna.tsx
- `Moose` — land — fauna.tsx — emotion: calm/wary; idle head-bob/ear-flick/tail; palmate antlers; form-shaded + rim + AO — NEW 2026-07-18; `bumpKick` 0..1 NEW 2026-07-19: a comic bumped-indignant-recover reaction pose (squash-and-stagger, pinned ears, wide indignant eyes, antler wobble, impact stars); `alert` 0..1 NEW 2026-07-20: ears perk fully UP+forward, head/neck RAISES, nostril-flare sniff, pupil tracks upward — the OPPOSITE motion from bumpKick's lateral recoil (a watching-the-sky pose), used for the drone-watcher gag — existing-asset new-pose growth quota
- `Raven` — air/perch — fauna.tsx — mode: perch/fly; head-tilt, throat hackles, wing-beat cycle — NEW 2026-07-18
- `BaldEagle` — air — fauna.tsx — soaring, fingered primaries, white head/tail, yellow beak — NEW 2026-07-18
- `Salmon` — water — fauna.tsx — SOCKEYE v3, REBUILT 2026-07-21 (fish-mastery session) on the shared lib/fishcraft.tsx realism engine (owner: "salmon are silver and scaly and shiny... master the fish artwork"): ocean phase = CHROME default hero look (countershade ramp, shingle scales, faded spec band + hard glint, iridescence, belly bounce), spawning = scarlet body + olive head + male hump/kype via `kype` 0..1, drab unspotted tail; carangiform traveling-wave swim (`swim` 0..1), gill pulse, rippling fin membranes, `caustics`. Taste-looped 8 rounds — ACTIVE
- `Coho` — water — fauna.tsx — NET-NEW 2026-07-21 (fish-mastery): the silver salmon; ocean = brilliant chrome w/ small black spots on back + UPPER tail lobe only (the coho tell), spawning = dark olive head/back + maroon flanks + modest hump; white gum line detail; fishcraft engine — ACTIVE
- `RainbowTrout` — water — fauna.tsx — NET-NEW 2026-07-21 (fish-mastery): olive back, THE pink lateral stripe + rosy cheek, 46 deterministic small black spots above the line + spotted dorsal/adipose/BOTH tail lobes, squared spotted tail, small mouth ending under the eye; fishcraft engine — ACTIVE
- `Halibut` — water — fauna.tsx — NET-NEW 2026-07-21 (fish-mastery): Pacific halibut, right-eyed flatfish side-on; elongated-diamond camo body w/ deterministic mottle, BOTH eyes stacked on the eyed side, undulating tapered dorsal+anal fin fringes (the swim), broad crescent tail, high-arched lateral line over the pectoral; `swim`, `caustics` — ACTIVE
- `Grizzly` — land — fauna.tsx — NET-NEW 2026-07-20c (asset-library session, UPGRADE #2): purpose-built anatomy PER STANCE (all4: horizontal bulk, hump highest, head slung forward; stand: upright pear-trunk tower, planted hinds, dangling clawed forepaws; fish: head dropped to the waterline + water hint); emotion calm/alert; roar 0..1 head-throw + jaw; breath/sway/ear idles; fur break-up detail; form-shaded + rim + AO. Taste-looped twice (v1 potato-pose redone). fish stance not yet frame-checked — verify before first on-air use — ACTIVE
- `Caribou` — land — fauna.tsx — NET-NEW 2026-07-20c (asset-library session #2): barren-ground caribou, lighter/leggier than the moose; species reads = pale chest mane + tall C-swept beam antlers w/ forward brow shovel (1.55x, sized in taste pass 2) + pale muzzle + dark socks; `trot` 0..1 diagonal-pair trot with head pump over graze idle; emotion calm/wary; form-shaded + rim + AO. Scatter at depth for a herd — ACTIVE
- `Orca` — water — fauna.tsx — NET-NEW 2026-07-20c (asset-library session #2): killer whale; species reads = TALL upright dorsal blade (rebuilt in taste pass 2 from a stub) + bold white eye patch + white belly sweep + gray saddle; `surface` 0..1 arcs a porpoising breach w/ blowhole spray; swim undulation, sculling pectoral, fluke follow-through; form-shaded + rim — ACTIVE
- `Puffin` — air/coastal — fauna.tsx — NET-NEW 2026-07-20c (asset-library session #2): horned puffin, upright tuxedo build (big head, short body = endearing); white face disc + oversized orange/yellow parrot bill + orange feet; `flap` 0..1 fast wing whirr; waddle-shift + head-tilt + blink idles; cleared taste loop first pass — ACTIVE
- `Wolf` — land — fauna.tsx — NET-NEW 2026-07-20c: gray wolf, level topline + deep chest, grizzled saddle BAND (taste pass 2: v1's saddle read as a crater), straight bushy tail (the wolf tell), cream legs/belly, amber eyes; `howl` 0..1 (muzzle skyward, closed eye, open throat, breath puff), `stalk` 0..1 (head below shoulder, crouch, ears pinned), emotion calm/alert; breath/ear-swivel/tail idles — ACTIVE
- `RedFox` — land — fauna.tsx — NET-NEW 2026-07-20c: flame-red coat, black stockings + ear tips, white bib/cheek/tail-tip (diagnostic), huge radar ears, near-body-length lush tail; `pounce` 0..1 arcs the full mouse-jump (crouch -> vault -> nose-down dive); light-bounce/ear-radar/tail-curl idles; cleared taste loop first pass (best first-pass of the session) — ACTIVE
- `DallSheep` — land/alpine — fauna.tsx — NET-NEW 2026-07-20c: snow-white mountain monarch; massive amber curl horns w/ growth ridges (`ewe` swaps to spikes), roman nose, wool scallop texture, dark hooves; `graze` 0..1 drops the head w/ jaw chew; breath/ear/weight-shift idles; cleared first pass — ACTIVE
- `SeaOtter` — water/coastal — fauna.tsx — NET-NEW 2026-07-20c: floats on its back w/ paws cracking a shell on its chest (`withRock`, tick-tock beat + splash), whisker twitch, kicky webbed feet, waterline hint; `mode` float/dive; pale face fur; cleared first pass — ACTIVE
- `Humpback` — water — fauna.tsx — NET-NEW 2026-07-20c: `mode` cruise (surfacing back + V-mist blow) / breach (arcing clear, LONG white pectoral flung, throat grooves, tubercle knobs, spray sheet) / fluke (the classic tail-up dive w/ scalloped white-under flukes + water drip); cleared first pass — ACTIVE
- `Ptarmigan` — land/alpine — fauna.tsx — NET-NEW 2026-07-20c: the state bird; `season` winter (all-white + black tail edge + red eye comb) / summer (mottled brown); feathered snowshoe feet; pecking-bob + head-jerk idles; `flush` 0..1 startle wing-burst w/ snow poof; cleared first pass — ACTIVE
- `KingCrab` — water/comic — fauna.tsx — NET-NEW 2026-07-20c: Bering Sea money crab; spiky carmine carapace, googly eyestalks, one OVERSIZED snapping right claw (`clawSnap`), six wave-phase scuttle legs (`scuttle`); cleared first pass — ACTIVE
- `Mosquito` — air/comic — fauna.tsx — NET-NEW 2026-07-20c: the unofficial state bird, built for comic beats; comically long proboscis, red eye, whiny wing blur, striped abdomen, dangly legs; `divebomb` attack arc, `swat` tumble w/ dizzy stars; cleared first pass — ACTIVE
- `SledDogTeam` — land — fauna.tsx — PROMOTED 2026-07-20d out of Episode.tsx (built 07-18): gallop gait (two-segment folding legs, suspension bound), 180° motion smear via `vx`, form-shaded amber coats, gang line; `dogs` 1-6 sets the string length — ACTIVE
- `Lynx` — land — fauna.tsx — NET-NEW 2026-07-20d: the snow ghost; black EAR TUFTS + wide facial ruff + stub black-tipped tail + snowshoe paws; `stance` sit (seated triangle, rebuilt pass 2) / stalk (belly-low creep w/ folded Z-legs); slow blink, ear-tuft swivel, tail twitch — ACTIVE
- `MountainGoat` — land/alpine — fauna.tsx — NET-NEW 2026-07-20d: chalk-white shag w/ pantaloon fringe, chin BEARD (swaying), short BLACK recurved spike horns (deliberately distinct from DallSheep's amber curls); `stance` stand / climb (24° grade on a drawn cliff ledge); cleared first pass — ACTIVE
- `BlackBear` — land — fauna.tsx — NET-NEW 2026-07-20d: deliberately the anti-Grizzly: NO hump, straight roman face, tall attached ears (pass 2: tucked into the skull), glossy blue-black w/ tan muzzle + small chest blaze; `stance` all4 / stand, `sniff` lifts the nose; stand paws edge-lit + breaking the silhouette (passes 2-3) — ACTIVE
- `Walrus` — coastal — fauna.tsx — NET-NEW 2026-07-20d: hauled-out blubber mound w/ skin folds, long white TUSKS, bristle mustache pad, bloodshot eye; `huff` 0..1 rears chest+head TOGETHER about the tail base (pass-2 rebuild after the body deformed apart from the head) w/ breath puff; rear-flipper flap idle — ACTIVE
- `Beluga` — water — fauna.tsx — NET-NEW 2026-07-20d: white whale w/ bulbous MELON (wobble idle), NO dorsal (ridge line), permanent upcurved smile; `mode` cruise (waterline y=0, undulation, `blow` mist) / spy (near-vertical spyhop emerging THROUGH splash rings); face repositioned onto the nose in pass 2 — ACTIVE

### Bestiary gaps
NONE. The 2026-07-20 library session banked all 14 gap species + SledDogTeam promotion (21 fauna assets total). Future growth is story-driven (new poses on existing cast count).

## Props & set pieces
- `AlaskaMini` — map of Alaska w/ pulsing pin — kit.tsx — ACTIVE
- `TallyCounter` — NET-NEW 2026-07-20b ("The Referee Arrives") — the MECHANICAL count mark: `variant="clicker"` (hand-held brass dial, needle whirls w/ `spin` 0..1 and hard-locks, count window, optional swinging `tag`) / `variant="odometer"` (mounted brass chip, cream flip-digits, `roll` 0..1 animates the ones digit; rest-digit display bug fixed same run) — props.tsx — deliberately a physical object you could HOLD, never a HUD reticle; form-shaded + rim + contact shadow — ACTIVE
- `VideoWeir` — NET-NEW 2026-07-20b — the tribal camera-lane weir set piece: warm timber A-frame legs w/ pegs, plank walkway w/ grain, picket lane guides, camera housing w/ blinking rec light, mounted TallyCounter odometer; `plant` 0..1 drops it in with a settle; fisheries-monitoring stage for any future salmon/counting story — props.tsx — ACTIVE
- SHARED PROPS KIT — lib/props.tsx — NEW 2026-07-20d: the episode-local props generalized with ALL story copy as params (a prop with baked-in text is an episode-local, not a library asset): `StatCard` (big stat chip, tintable), `Nameplate` (identity plate), `SwingSign` (hanging sign, 1-3 lines, pivot bug fixed), `GearLever` (pulled 0..1 + optional DENIED badge), `SurveyStake` (settle drop-in), `MeasuringChain` (pays out + distance tag), `PenAndDocument` (pen hovers trembling, never signs; optional party plate), `TrailPost` (two-line sign), `BoundaryReveal` (glowing boundary traces any closed path `d` + optional town marker) — look-dev in PropsShowcase.tsx — ACTIVE
  - Episode.tsx copies remain episode-local history; new scenes import from lib/props.tsx.
- `BoxLabel` / `StatBurst` / `FatArrow` / `Stamp` — HUD/label kit — kit.tsx — ACTIVE
  - CLOSED 2026-07-30 (the flat-HUD-chip repeat offender, flagged by the scorer panel on
    2026-07-18, again on 07-26, and still listed open on 07-29). The shading itself landed
    on 07-21/07-24, but it landed as OPT-IN flags defaulting to OFF (`StatCard formShaded`,
    `Stamp onPaper`), so a scene that simply called the prop still got a flat chip and the
    panel kept re-finding it. The real fix was the DEFAULT: `props.tsx` `StatCard` and
    `Nameplate` are now form-shaded + contact-shadowed BY DEFAULT with a `flat` opt-out, and
    `Nameplate` gained a dimensional path it never had. `kit.tsx` `BoxLabel` (shaded unless
    `flat`) and `StatBurst` (always shaded) were already correct. Lesson worth keeping: a
    default-off fix is a doctrine reminder wearing a code costume.

## Vehicles (the Alaska machine kit) — lib/vehicles.tsx (NEW 2026-07-20c, asset-library session #2)
- `BushPlane` — air/ground/water — vehicles.tsx — high-wing taildragger (Super Cub silhouette); `mode` ground (tundra tires, slow prop) / fly (prop blur disc, bank bob) / float (pontoons, heave); airfoil wing slab + lift struts, real rudder blade (both from taste pass 2), cabin glass, engine cowl, N-number panel N907AK, rivets; `propSpeed` override; `body` tint — ACTIVE
- `Snowmachine` — land/winter — vehicles.tsx — rural workhorse: track w/ scrolling lugs + front ski, hood + windshield + handlebars + seat, headlight lights at speed; `speed` 0..1 drives vibration + kicked snow spray; `body` tint — ACTIVE
- `FishingBoat` — water — vehicles.tsx — seiner/troller work boat: sheer-bow hull + waterline stripe, wheelhouse w/ windows, mast + boom + rigging lines, aft net drum, rail buoys, blinking masthead nav light; `heave` 0..1 swell rock; masthead is a gull-perch point (pair with Raven/Puffin); `hull` tint — ACTIVE

## Look-dev harnesses
- `CraftShowcase` — motion/voice/SFX-era look-dev comp (entrance, followThrough, TalkMouth ramp, talking cast) — CraftShowcase.tsx — NEW 2026-07-18b
- `FishShowcase` — FishShowcase.tsx — NEW 2026-07-21: the fish-mastery audition sheet (sockeye/coho ocean+spawn, rainbow trout, halibut, chrome hero); render a still before an episode uses a species
- `CityShowcase` — CityShowcase.tsx — NEW 2026-07-21: AnchorageSkylineBG audition (fall + Denali + floatplane + railroad + trail moose)

## Environments
- `DawnForestBG` — boreal birch/spruce dawn, parallax treeline, mist, birds, ground gradient, form-shaded trunks + bark texture + foliage speckle — Episode.tsx (2026-07-18) — ACTIVE
- `FrostYardBG` — NET-NEW 2026-07-19 — interior powerplant-yard/dusk biome: parallax mist/gust bands, flickering skyline windows, drifting snow particles, `parallax` prop for depth-of-field scene layering — Episode.tsx — ACTIVE
- `NenanaRangeBG` — NET-NEW 2026-07-20 — boreal AIRSTRIP biome (distinct from DawnForestBG's full forest and FrostYardBG's utility yard): a flat man-made tarmac foreground with a painted runway centerline + receding blue edge lights to a vanishing point, fronted by a LOW distant black-spruce band (3-4 parallax sub-bands = the supporting aerial-depth refinement), under a boreal midnight-blue -> rose-gold sky. `dawn` 0..1 warms night->sunrise; `parallax` DOF; `showStrip`; dawn-mist drift + fading stars (second disjoint motion region) — Episode.tsx — ACTIVE
- `AuroraNightBG` — NET-NEW 2026-07-20c (asset-library session #2, lib/biomes.tsx — the SHARED biome home; episode-locals stay in Episode.tsx): the night/aurora rig ("known next advance" since 07-18, now built). Deep star-field night (two twinkle layers) + 2-3 ANIMATED aurora curtains (blurred screen-blend ray stacks breathing on slow sine phases, hue-shifting green->teal->violet), aurora-lit snow horizon, low spruce silhouettes, drifting snow sparkle; params `intensity`, `hueShift` (0 green / ~40 teal / ~120 violet), `groundY`, `moon`. 3 disjoint motion regions guaranteed — ACTIVE
- `TundraBG` — NET-NEW 2026-07-20c (lib/biomes.tsx): open North Slope/western tundra under a big sky: banded tundra colors to a FLAT horizon, kettle ponds catching the sky, drifting flat-bottom clouds, wind-shivering cottongrass tufts; params `season` summer/autumn, `wind`, `groundY` — ACTIVE
- `FjordBG` — NET-NEW 2026-07-20d (lib/biomes.tsx): Southeast fjord: steep forested walls dropping to still green water, distant headland ridges closing the throat (aerial perspective), soft BLURRED hanging mist bands hugging the walls (feGaussianBlur, wide filter region), circling gull specks, wall reflections + shimmer; params `mist`, `waterY` — ACTIVE
- `GlacierBG` — NET-NEW 2026-07-20d (lib/biomes.tsx): tidewater glacier face: fissured blue-white ice wall with jagged serac top edge, deep-blue crevasse strokes, `calve` 0..1 tips and drops a slab with impact splash (>0.7), dark water with drifting bergy bits; params `calve`, `waterY`. THE stage for climate/ice stories — ACTIVE
- `RiverBG` — NET-NEW 2026-07-20d (lib/biomes.tsx): Interior braided river built off ONE parametric centerline (channel, gravel margins, flow-aligned braid-bar island, current lines, riffle sparkle all share it — nothing floats or lands off the water), mottled vegetated banks (never flat fills), bank spruces scaling toward the viewer, distant snow-patched range + drifting clouds; params `season` summer/fall (fall adds red dwarf-birch shrubs), `riffle`. THE salmon-story stage (pair with Salmon, Grizzly 'fish', FishingBoat) — ACTIVE
- `MainStreetBG` — NET-NEW 2026-07-20d (lib/biomes.tsx): small-town main street in one-point perspective: false-front storefronts converging both sides (camera-facing lit faces with door/shop window/sign + shadow-side walls), gravel road with center dashes + puddle shimmer, power poles with sagging wires, pennant string fluttering across the street, snow-capped massif closing the view; params `dusk` 0..1 (dusk sky + per-window warm flicker), `banner`. THE community/politics/town-hall stage — ACTIVE
- `OilfieldBG` — NET-NEW 2026-07-20d (lib/biomes.tsx): North Slope oilfield: flat plain to the horizon, low arctic sun in a haze band (kept left of the flare), derrick lattice with blinking beacon, steel modules on a gravel pad, flare stack with living flicker flame + breathing glow, THE pipeline running the foreground on VSM supports, distant rigs; params `season` winter (blowing snow) / summer (melt ponds), `flare` 0..1. THE energy/economy stage — ACTIVE
- `AnchorageSkylineBG` — NET-NEW 2026-07-21 (lib/biomes.tsx, owner directive "bake the Anchorage skyline in as an artifact"): the verified local-recognition postcard, drawn back-to-front per docs/craft/ANCHORAGE_LANDMARKS.md: sky, tiny lone Denali (`denali`), Mt. Susitna "Sleeping Lady" reclining ridge, continuous faceted Chugach wall w/ termination-dust caps + Flattop + foothill treeline, downtown band on the bluff (ConocoPhillips + Atwood slabs, Hotel Captain Cook three stepped mustard towers), Cook Inlet water w/ wobble reflections, coastal-trail foreground (railing, path, alders, fireweed); params `season` summer/fall, `denali`, `floatplane` (animated Lake Hood red/white floatplane), `train` (blue/gold Alaska Railroad consist). Taste-looped 4 rounds. USAGE RULES in ANCHORAGE_LANDMARKS.md: lowkey background cameo, 1-2 landmarks max, Anchorage-set stories only — ACTIVE
  - Environment kit now THIRTEEN biomes: three episode-local, eight shared in lib/biomes.tsx,
    PaperOfficeBG in lib/paper.tsx (the first interior, 07-26), and UnderIceBG in
    lib/underice.tsx (the first submerged one, 07-30). CORRECTED 2026-07-30: the previous
    total said TWELVE by summing 3 + 8 + 1 and silently dropped PaperOfficeBG, a miscount
    that had stood since 07-26. Caught by the Gate 0D art critic, not by any code check. Every biome candidate from the upgrade backlog is now BUILT.
  - Local-flavor reference docs (NEW 2026-07-21): docs/craft/ANCHORAGE_LANDMARKS.md (skyline formula + insider props + usage rules) and docs/craft/ALASKA_NOSTALGIA.md (top-12 local-grin list, bygone businesses, famous Alaskans w/ sensitivity rules, historic eras, trademark homage-not-copy guide). Consult BOTH in the directors room when a story is set in/near Anchorage or wants a nostalgia beat.

## Engine systems (the craft layer — advance these every run, don't just consume them)
- `lib/fishcraft.tsx` — FISHCRAFT (NET-NEW 2026-07-21, fish-mastery session): the shared fish-realism engine every fauna fish composes (doctrine + research sources in docs/craft/FISHCRAFT.md). `makeSpine()` carangiform traveling wave (amplitude grows tailward, head counter-yaw, tail heave+pitch coupling so the figure-8 emerges, gill pulse, buoyancy bob on irrational periods), `bodyGeom()` sampled outline/rails from depth profiles (SINGLE closed subpath — two concatenated subpaths auto-close with chord artifacts), `FishSurface` chrome layer stack (countershade gradient, masked shingle scales, filled form-shadow band, head-to-tail FADED spec band + hard glint, iridescence puddle, belly bounce, caustics), `FinMembrane` translucent rippling ray-lined fins, `CHROME_SKIN` preset. HARD-WON RULES: uid() inputs must include ALL variant props (pure-hash collisions cross-wire gradients); spec layers fade out before the caudal wrist; body profiles keep a wrist FLOOR (~9% body length) — ACTIVE
- `lib/materials.tsx` — MATERIALS (NEW 2026-07-20d, Stage3D backlog item (d)): surfaces read as SUBSTANCES, not flat fills. Eight deterministic SVG-pattern overlays: brushedMetal, corrugated, tarmac, granite, bark, planks, snowpack, ice. Usage: `<MaterialDefs />` once per svg, then re-draw any silhouette with `fill={matFill('bark')}` over its lit base (or the `Surface` helper). Seeded imul-hash speckle (no Math.random). Look-dev: MaterialShowcase.tsx incl. an Extrude+material demo. Pairs with the no-flat-single-tone-fills rule.
- `lib/motion.tsx` — animation principles: entrance() (anticipation/overshoot/squash-stretch + MotionBlur velocity), followThrough() secondary swing, accentKick(), idleSway(), squashStretch(), ChipShadow (HUD chips sit in the scene) — NEW 2026-07-18b
- `lib/motion.tsx` `vitals()` — THE LIVING-IDLE PRIMITIVE, 2026-07-26 (repeat-offender fix: the
  scorer panel flagged thin idle life on held heroes on 2026-07-24 AND 2026-07-25, and both runs
  DEFERRED it, so the third strike gets a code guard instead of a doctrine note). The Character rig
  had already earned a layered weight-shift idle, but every characterized-object hero floated on a
  SINGLE fixed-period sine (`const bob = 5 * Math.sin(f / 17)`) — which is exactly why they read
  mechanical: over any half-second window the figure barely moves, and two heroes on screen bob in
  lockstep. `vitals(frame, phase, gain)` returns `{bob, swayX, breath, tilt, micro}` from three
  desynced layers on deliberately IRRATIONAL period ratios (no common multiple, so the loop never
  re-phases and never reads as a loop); `phase` decorrelates instances by the golden angle, `gain`
  scales or freezes the whole signal (0 = a deliberate held-breath story beat). WIRED THROUGH every
  hero already: kit.tsx `Sourdough` (frozen still holds its breath), `Cell`, `Vale`, `SatelliteEye`,
  `Petrel`; sensors.tsx `SatelliteEye`, `SeismicStation`. Author new heroes against it — a hero
  cannot be given a thin idle without deliberately bypassing the primitive. Verified: tsc --noEmit
  clean + StationLook draft stills render all four emotional states correctly — ACTIVE
- `lib/voice.tsx` — VOICE ACTING: VoiceProvider/useVoice (per-frame mouth envelope + emphasis accents from the VO pipeline), TalkMouth flapping mouth; Character + ServerMachine take `talking` — the cast speaks/reacts in sync with the narration — NEW 2026-07-18b
- `assets/sfx/` designed-foley bank (scripts/build_sfx_library.py, 16 sounds; scripts/sfx_bank.py resolver; drop real CC0 takes in assets/sfx/real/ to upgrade any entry) — NEW 2026-07-18b
- `scripts/render.sh` — draft (half-res ~2-4x faster) vs final render wrapper; the taste loop iterates on drafts — NEW 2026-07-18b
- `lib/lighting.tsx` — tones() ramps, FormGradient, RimLight, ContactShadow, BrushedMetal/BarkTexture/FoliageSpeckle, GradeLayer (bloom+vignette+grain), MotionBlur (180° anisotropic) — NEW 2026-07-18; `HazeOverlay` NEW 2026-07-19 — translucent grid-textured animated air-quality/pollution grading layer (`amount` 0..1 drives wash + tint + grid opacity), for a story's environmental-stakes turn
- `lib/FX.tsx` — SpeedLines, ImpactStar, PaperStorm, ZoomVignette; `SmellRings` NEW 2026-07-20 (radial VOC/smoke detection rings emanating from a sensor node, radial-emanate motion) + `ScanReticle` NEW 2026-07-20 (thermal-lock targeting reticle: rotating corner brackets that SNAP inward and clamp on a target, `lock` 0..1) — ACTIVE
- `lib/lighting.tsx` CRAFT ADVANCE 2026-07-20: `IRVision` — a reusable false-color THERMAL/IR heat-vision look system (magenta->coral->citron heat ramp centered on the hot target + sensor scanlines + refresh sweep + a boxed THERMAL HUD tag), `amount` 0..1 crossfades the drone's-eye view in. Any future sensor/thermal/IR Alaska story inherits it. The run's SINGLE primary craft advance (atmospheric-perspective aerial-depth treeline in NenanaRangeBG is a supporting refinement).
- `lib/stage3d.tsx` — TRUE 2.5D ENGINE (NEW 2026-07-20, UPGRADE_BACKLOG #1 prototype). A real shared
  virtual camera via CSS 3D perspective (`Stage3D`: dolly/truck/boom/orbit/roll), depth layers with
  automatic perspective parallax + overscan (`Plane`), solid extruded dimensional forms (`Extrude`),
  and projected ground cast-shadows (`CastShadow3D`). Proof scenes in `TwentyFiveD.tsx` (comp
  `TwentyFiveD` vs flat `BorealFlat`). NOT yet wired into the Episode pipeline; see UPGRADE_BACKLOG.md
  for the migration plan (per-face Extrude shading + a Character/kit adapter, then migrate one scene).
- `lib/stage3d.tsx` UPGRADES 2026-07-20b: Extrude now has a REAL per-face light model (side wall
  responds to the live camera orbit under the fixed screen-left key, back-slice AO); new `Atmosphere`
  (per-plane aerial perspective: desaturate + contrast-loss + sky veil with depth); new `Solidify` +
  `Card` asset adapter (ANY existing kit hero gains real body thickness with zero re-authoring:
  darkened copies stacked in Z behind the lit front face). Proven in `Nenana3D.tsx` (comp `Nenana3D`),
  the VERTICAL SLICE: Vale on a TRUE 3D runway floor (rotateX'd ground plane, supersampled 2x so the
  perspective-stretched tarmac stays crisp), camera cranes down through the treeline, flies low over
  the runway, rises with the liftoff.
- `lib/lighting.tsx` NIGHTGRADE — 2026-07-25 CRAFT ADVANCE (the run's single primary engine advance).
  Every prior Dispatch was a daylight or dusk world. The engine had AuroraNightBG (one specific night
  BIOME) but no general system for making ANY biome read as night with rationed practical light.
  `NightGrade(f, color, amount, floor, horizon, sources[])` does four things GradeLayer cannot:
  (1) an ambient cold cast so the world sits in one coherent night, (2) a BLACK FLOOR that crushes
  shadows toward true black so "unlit" is a different STATE from "dimly lit", (3) SOURCE BLOOM emitted
  ONLY at declared `sources` {x,y,r,color,intensity} — a scene must REGISTER a light before it can glow,
  which makes a palette rule like "amber never appears on an unmonitored slope" a property of the scene
  graph instead of a convention a renderer can violate silently, and (4) a horizon lift so ridge
  silhouettes still separate at the black floor. Look-dev: StationLook.tsx.
- KNOWN NEXT ADVANCES (2026-07-26 panel, median 6.68 vs a 9.0 bar, worth reading before the next run):
  held figures render FROZEN across full 8-frame strips even though the Character rig has idle built
  in, so scenes are not driving it; the turn's arrow arrives and never crumples; nine shots played at
  ONE camera height on one set with no close-up and no scale change; and the caption_fixups map in
  vo_script.json must be populated EVERY run or TTS spellings like 'D M V' paint onto screen.
- Known next advances: migrate MORE Episode scenes onto stage3d (first landed 2026-07-20b: the
  boom-up crane in "The Referee Arrives"; lesson: overscan non-fill world planes well past the
  frame at max pull-back or they render as cut-out boxes), kinetic typography, per-material
  texture library, night/aurora lighting. PANEL-BACKED BACKLOG (2026-07-20b, first-time
  deferrals with plans in docs/RUN_UPGRADES.md): fauna Salmon spine-follow swim deform;
  Character rig micro-texture pass behind a `detail` prop; word-level kinetic captions driven
  by words.json.

## Civics, the RULES kit — lib/civics.tsx
NET-NEW 2026-07-31 ("The Gate With No Number"). The shelf could draw machines, animals, biomes,
instruments and paperwork, but nothing for the thing this channel covers most often: A RULE, and
the moment a rule meets the thing it is supposed to act on. Four prior Dispatches wanted it and
improvised around it (07-18 land conveyance, 07-22 enhanced-use lease, 07-26 records match, 07-29
award list). props.tsx CheckpointGateLever is a faceless barrier ARM with no condition and no
verdict, so it can show a road closed and nothing else. It cannot show WHY.
- `Gate` — the CONDITIONAL rule — civics.tsx — rounded, articulated, many-parted, WITH A FACE. Carries
  a printed `condition` and a `source` authority line on a board, and reaches a `verdict`
  asking/pass/block that drives the lamp, the brow and the arm together. A thing that can say "it
  depends" must visibly have parts that could move differently. `accent` VO reactivity, `phase`
  decorrelates the idle, routed through vitals() — ACTIVE
- `ThresholdGate` — the SAME RIG BUILT TWICE — civics.tsx — `cut` 0..1 opens a real sorting aperture
  sized by `cutW`, `hands` 0..1 gives the crown clock its hands, `lamp` lights ONLY when a threshold
  actually fired. Build it with both at 1 and it is a bounded instrument that discriminates; with
  both at 0 it stops everything it meets. Setting the two side by side states a SCOPE CONTRAST as a
  consequence you can see rather than as a comparative-statutes footnote — ACTIVE
- `AperturePlate` / `CapClock` — the plate and the clock ALONE — civics.tsx — extracted mid-run when
  the first render of the turn staged two whole rigs side by side and pushed both plates off the
  frame edges. A comparison needs each object at full width, not the whole machine — ACTIVE
- HARD-WON: pass 1 to 3 drew the threshold as a SCALE PLATE with a needle and gradations. It worked
  and was dropped anyway, because the 2026-07-30 Dispatch had already used "a gauge with no scale
  printed behind its needle" as its own thesis image one run earlier. An aperture is also the better
  drawing: a dial reports that nothing is measured, a slot shows WHICH LOAD GETS THROUGH.
- Look-dev: `GateLook` (GateLook.tsx) — both configurations plus a 0.28-SCALE LEGIBILITY STRIP, run
  BEFORE any scene is authored. It caught three real defects on its first pass (the marks vanished
  below full scale, the boom swept across the clock face, the brow sat on the eyes as a burglar mask).

## Engine advance 2026-07-31 — DayGrade, the daylight counterpart
- `lib/lighting.tsx` `DayGrade(f, sky, bounce, amount, floor, haze, sunX, sunY, sunIntensity)` — NightGrade
  landed 07-25 and never got an opposite, so every bright scene since was ungraded flat art or a night
  grade at low amount. That is the MECHANICAL reason four straight dispatches drifted to dusk or dark:
  night was the only lit world the engine could build. Three of its four moves run backwards from
  NightGrade: a WARM/COOL SPLIT (skylight cool from above, ground bounce warm from below, because
  daylight ambient is never one cast), AERIAL PERSPECTIVE instead of registered practical sources, and
  above all a LIFTED FLOOR — at high albedo outdoor shadows fill with skylight and never approach black,
  so `floor` RAISES shadow density toward the sky hue. Crushed blacks in a daylight scene read as a
  studio table top no matter how bright the mids. Same placement contract as NightGrade: it emits divs,
  so it must sit OUTSIDE the svg.
- KNOWN NEXT ADVANCE, deferred with a plan: DayGrade has no ACCENT REGISTRY. NightGrade's `sources[]`
  makes "amber never appears on an unmonitored slope" a property of the scene graph; DayGrade's reserved
  colour is held only by pinned values at call sites, and the 07-31 panel still found three leaks. Add
  `accents[]`, permit the reserved hue only at registered rects, throw on an unregistered one.

## Bench science (the library's FIRST INDOOR INSTRUMENT FAMILY) — lib/bench.tsx
NET-NEW 2026-08-01 ("The Copy In The Mud", USGS AVO tephra attribution). REAL GAP, checked against
this file in full first: the shelf had an orbital eye, a seafloor ear, a ground ear, two aerial
machines, a swimmer, records machinery and the civics kit, and EVERY one of them observes a WORLD.
Nothing read a SAMPLE, and there was no vocabulary for bench science or material evidence. A piece
of the world brought indoors under a lamp is a different verb and needed different hardware.
- `AshReader` — THE RUN'S HERO, a brass and enamel bench instrument that reads one ash grain and
  PRINTS ITS ANSWER — bench.tsx — THE TELL IS THE CARD, NOT A FACE, and that is restraint rather
  than incapacity: it has eyes, a brow bar and a vitals() idle and deliberately does not use them,
  because a face at the print beat would make the machine a character with stakes in its own
  uncertainty and the film's honesty beat depends on it having none. Three state channels, per the
  thrice-learned one-channel lesson (07-25 horn, 07-26 cone, 07-30 glider): the CARD (loudest), the
  LAMP (lights ONLY on an asserted match, the SeismicStation discipline), and the THROAT + BROW
  (telescopes on `straining`, and the brow carries state even when the lamp is dark). `emotion`
  reading/settled/straining, `feed` 0..1 runs a grain along the stage, `lamp`, `lampFill`, `accent`,
  `phase`, `groundY`. tones/FormGradient/RimLight/ContactShadow, routed through vitals() — ACTIVE
- `ShortlistCard` — the printed answer, and the film's thesis AS AN OBJECT — bench.tsx — one name is
  narrow and calm, three names is WIDE, and the extra width is the honest report of ambiguity, so
  ambiguity is a SIZE ON SCREEN rather than a label. Built on paper.tsx's numeric shadow contract.
  HARD-WON: pass 1 used a fixed 76px bay at fontSize 17 and "FISHER CALDERA" (about 148px) ran off
  the stock entirely on the three-name card. Gate 0D called it a hard blocker on the film's own
  thesis object. Now the bay is derived from the LONGEST name, the font shrinks only if the card
  would pass MAXW, and W is derived from the bay. A card whose names overflow is not a subtler bug
  than a broken render, it is the same bug — ACTIVE
- `DistanceCalipers` — THE SECOND INSTRUMENT — bench.tsx — brass jaws spanning two points, brought in
  BY A HUMAN HAND (`handIn`), which is the literal drawing of a distance metric AND of a person
  choosing. Nearest prior art is props.tsx `MeasuringChain`, and the distinction is real: a chain
  pays out along ground over a long span, calipers span two points at bench scale, in hand, and
  read as a tool being PICKED UP. `span`, `tilt`, `handIn`, `label` — ACTIVE
- `CoreColumn` — one long tube of mud, standing, with its ash bands — bench.tsx — TORN, not turned:
  irregular edges and imul-hashed grain, because this is the FOUND half of the shape grammar.
  `bands[]` takes {at, lit, named, still, mark}. PER-BAND MOTION CHANNEL added after Gate 0D: pass 1
  applied ONE sway to the whole group so bands inherited it wholesale, which made the poster frame's
  entire argument (named bands DEAD STILL, unnamed ones quietly restless) literally unbuildable.
  `named` draws a real NAME PLATE on a stem sized by `labelScale`; pass 1 could only tint a band, so
  the frame that promised named bands had no label geometry at all. `mark` gives a band a
  double-torn corner and one conspicuously deep tooth so the open-loop band is re-identifiable
  across a 52-second gap and two shots — ACTIVE
- `AshCrumbs` — THE CROSS-SCENE GAG AS ONE COMPONENT — bench.tsx — pearl shavings that curl off the
  glacier blade, drift in the far atmosphere plane of every later scene on a GLOBAL frame phase, and
  `landing` promotes one out of the drift to seat as a pearl band. Built as one shared deterministic
  component precisely because a cross-scene continuity requirement re-improvised per scene silently
  does not happen. imul hash, never Math.random — ACTIVE
- Look-dev: `BenchLook` (BenchLook.tsx) — every state in the film at full size AND a 0.28-SCALE
  LEGIBILITY STRIP, run BEFORE any scene is authored, per the GateLook precedent.

## Engine advance 2026-08-01 — the ACCENT REGISTRY (closes the 07-31 deferral)
- `lib/lighting.tsx` `AccentRegistry` / `useAccent` / `accentAllowedAt` / `AccentLicense` — the item
  the 2026-07-31 run deferred WITH A PLAN. NightGrade's `sources[]` makes a palette rule a property
  of the scene graph; DayGrade had no counterpart, so its reserved colour was held only by
  hand-pinned values at call sites and that run's panel still found three leaks. A scene declares
  AccentLicense[] (hue, what it MEANS, licensed rects); code painting a reserved hue resolves it
  through useAccent(hue, x, y), which throws outside every licensed rect, and a throw fails the
  render. accentAllowedAt() is a pure test seam.
  HONEST LIMITATIONS, recorded rather than overclaimed (Gate 0D was right to press): it is OPT-IN at
  paint time, so a literal hex painted directly still slips through and only a repo-level lint would
  close that; the check is POINT-based while most accents are extents; and licences are in frame
  coords with no local-to-frame helper for assets nested under stage3d Planes. It NARROWS the hole
  the 07-31 panel found, it does not seal it. The name is also general, not DayGrade-specific.
- KNOWN NEXT ADVANCES: a lint or AST gate failing on a reserved-hue literal outside useAccent; an
  extent/bbox overload; a local-to-frame coordinate helper; a unit test exercising accentAllowedAt.

## Engine fix 2026-08-01 — align_captions.py no longer feeds Whisper the script
- `scripts/align_captions.py` passed `--script` in as Whisper's `initial_prompt`. Whisper treats
  initial_prompt as text that ALREADY happened, so seeding it with the script's opening words made
  the decoder skip forward to audio that did not match. Reproduced twice on this run's take: WITH
  --script it returned 178 words beginning at 17.42s, silently dropping the film's first FOUR
  narration lines while reporting a healthy-looking transcript_match=0.866; WITHOUT it, the same
  audio and model returned 214 words beginning at 0.00s.
  THIS IS THE SECOND TIME THIS EXACT ROOT CAUSE HAS BEEN PAID FOR. This file already records it
  being fixed in vo_synth_gemini.py's `_align_wholefile` on 2026-07-19, and that fix was never
  carried across to align_captions.py, which the routine names as authoritative for caption timing.
  --script is still honoured, but only for the post-hoc transcript_match validation.
