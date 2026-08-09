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

### Grown 2026-08-02 ("The Copy In The Mud", the run that actually built the film)
- `LayeredLand` — the FOUND half of the grammar as a reusable hillside — bench.tsx — a torn layered
  sediment stack whose every layer is its own jittered polyline, so no two edges are parallel.
  `erased` 0..1 wipes the texture out from screen left and leaves a FLAT BLANK behind, which is what
  the ice takes rather than a scar it leaves. Clip-path driven, so the erasure is exact — ACTIVE
- `ErasingBlade` — the glacier as the most RECTILINEAR object in the film — bench.tsx — fills the
  manifest gap that `GlacierBG` could not: that asset is a torn serac WALL with no tint param, and
  this story needed ice as a hard straight-edged PLANE THAT ACTS. Internal strata are parallel and
  regular, the deliberate opposite of the torn land it eats. Exposes no easing hook ON PURPOSE, so
  callers cannot ease it: the one unaeased motion in a film of eased ones is what reads as
  inhuman — ACTIVE
- `CoringTube` — the TURNED answer to the torn seafloor — bench.tsx — machined barrel with
  fabrication rings and a hardened cutting shoe, `drive` punches it in and `lift` pulls it back with
  a banded plug visible through the barrel window. Head weight so the punch reads as MASS — ACTIVE
- `BrassPlate` — naming an actor as a PHYSICAL OBJECT rather than a HUD chip — bench.tsx — a
  countersunk machined plate that SETS into the light with weight, for the §4.2 name-actors-before-
  you-use-them law. Multi-line, scales, and carries its own contact shadow — ACTIVE
- `CoreColumn` gains `bands[].side` ('left' | 'right', default 'right') — the name plate used to
  always hang right, which is correct on a left-hand column and broken on a right-hand one: at the
  signature pull-back's label scale the right-hand plates ran past x=1080 and the POSTER FRAME read
  "MA", "ER", "ONS". A named band whose name is cut off is worse than an unnamed one, because that
  frame's entire claim is that these three could be NAMED.
- `DistanceCalipers` UPGRADED to the bar — the 08-01 look-dev flagged it as a flat V and it was: two
  thin strokes off a stick. Now a real instrument with a shaded beam, a knurled thumb wheel, jaws
  with hardened measuring tips, and the span called out between the tips with arrowheads at both
  ends, so the DISTANCE is the focal object rather than the tool holding it.
- KNOWN NEXT ADVANCE for this family: `AshReader`'s head still reads as a box on a column at small
  scale. It survives because the film stages it large, but a run that needs it in a wide shot should
  give the housing a silhouette that is legible at 0.28 before leaning on it there.

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

## Insects (the library's FIRST ARTHROPOD YOU CAN LOOK AT) — lib/bugs.tsx
NET-NEW 2026-08-05 ("The Net Comes First"). REAL GAP, checked against this file in full
first: the 21-species bestiary is every one a vertebrate except KingCrab, and the only
other arthropod is `Mosquito`, which is explicitly a gag asset with a whiny wing blur and
a divebomb. There was no insect that could be looked at seriously, and this story is
entirely about Alaska's insect fauna with a headline result specifically on ground beetles.
- `GroundBeetle` — THE RUN'S HERO, and a deliberate variety break: the last five heroes were
  machines and instruments (BurnWindowEngine, AshReader, ThresholdGate, IceGlider,
  RecordsMachine) and this one is an animal — bugs.tsx — SHAPE-LANGUAGE DECISION: the beetle
  is the ORGANIC-IRREGULAR half of a film whose other half is a rectilinear cabinet, so
  NOTHING on it is parallel to anything. Six legs at six different angles with three segments
  each, a pronotum that matches neither head nor body, crossed asymmetric mandibles. A beetle
  with mirrored legs reads as clip art. THE ONE-CHANNEL LESSON APPLIED (07-25 horn, 07-26
  cone, 07-30 glider): state is carried by THREE things, the ANTENNAE (forward and searching
  or folded back), the LEG SET (planted, walking, drawn in), and the ELYTRA SHEEN (dull when
  unnamed, a hard specular band when named). `state` still/walking/caught/named, `sheen`,
  `accentColor` (supplied by the caller so the accent licence stays at the call site),
  `label`, `pinned` (a real entomological pin through the RIGHT elytron, which is where
  entomology puts it, with a contact tick where it enters). Alternating-tripod gait, which is
  the gait a beetle actually has. Deterministic imul-hashed elytral punctures and six striae.
  tones/FormGradient/RimLight/ContactShadow, routed through vitals() — ACTIVE
- `BEETLE_PATH` — the elytra outline alone, for filled use.
- `BEETLE_SIL` — THE FULL SILHOUETTE, body plus head, pronotum, six legs and two antennae, as
  a compound path. HARD-WON, and found by looking at the rough cut rather than by reasoning:
  the absence grammar strokes a path with no fill, and BEETLE_PATH unfilled is AN EGG. The
  hook and the signature shot are both built entirely on the dashed form, so the film's two
  most important frames were showing a stranger an oval and calling it an insect. A filled
  beetle gets its legs from separate drawn elements; an unfilled one has only its outline, so
  the outline has to carry the whole animal. Any future asset intended for `Unnamed` needs the
  same treatment.

## THE ABSENCE GRAMMAR — lib/absence.tsx (CRAFT ADVANCE 2026-08-05)
The shelf had paid for this lesson twice and solved it once, inline, for one animal.
07-26 records.tsx `ThreePipeCutaway` drew a capped pipe meaning "no record comes back" and TWO
panel judges found it did not read as an absence, which this file still carried as an open
known weakness. 07-30 underice.tsx `RingedSealGhost` solved it properly (dashed contour, true
void interior, caller-supplied label) and welded the solution to a seal, so every later film
needing to draw a thing that is not there had to re-improvise it.
- `Unnamed` — renders ANY silhouette as A STATED ABSENCE — absence.tsx — the contract is four
  clauses and each one is a defect somebody already found: (1) DASHED, never solid, and the
  dash phase CRAWLS, because a solid outline reads as a style choice; (2) a TRUE VOID interior,
  no hatch, because a hatched absence reads as a material; (3) a slow sparse DRIFT inside the
  void, which is THE FOURTH THING this run added and the one that stops an absence reading as
  UNFINISHED rather than unfilled, since a static dashed outline in a world of form-shaded
  solids looks like an asset that failed to render; (4) a REQUIRED `label` prop, not optional,
  because an unlabelled absence is indistinguishable from an oversight and a caller who has to
  type the label has to decide what the missing thing IS. `solid` 0..1 animates the SAME path
  from an absence into a filled outline without swapping components mid-shot — ACTIVE
- `UnnamedField` — a POPULATION of absences — absence.tsx — deterministic hash scatter, never
  Math.random, with `resolved` 0..1 filling them in from the left. Dash length scales up as
  instance size drops so the dashes never alias to grey noise under H.264 — ACTIVE

## THE NAME ENGINE — lib/nameengine.tsx (net-new 2026-08-05)
- `NameEngine` — the 2008 classifier as a physical object — nameengine.tsx — REDESIGNED AT GATE
  0D AND THE CRITIC WAS RIGHT. The first design was a brass bench instrument with an intake that
  reads a sample and prints an answer, staged in macro-closeup under a lamp, which is bench.tsx's
  `AshReader` staged in `AshReader`'s own treatment two runs earlier. The stated differences were
  BEHAVIOURAL and a viewer cannot see behaviour in a silhouette. So the SHAPE moved instead, and
  moving it made the film better: this machine is RECTILINEAR AND STACKED, drawer-proportioned,
  machined panel lines and recessed corner screws, and it belongs to the CABINET's ordering
  grammar rather than to the bench. THE ONE ROUND ELEMENT IN A SQUARE MACHINE IS THE INTAKE IRIS,
  six overlapping leaves that open, hold and close on visible empty air. AshReader has no iris, it
  is legible at feed size because it is the only circle among right angles, and it IS the film's
  thesis: the machine works and there is nothing to put in it. Three state channels: the IRIS, the
  FEED BAY (`feed` 0 leaves it visibly empty, which is the point of the asset), and the LAMP,
  which lights ONLY when `plate` is non-null, the SeismicStation discipline. `cut` 0..1 opens the
  housing along its length so the empty bay can be seen from inside — ACTIVE
- LESSON WORTH KEEPING: when a gate says a net-new asset duplicates the shelf, the cheapest real
  fix is usually to move its SHAPE LANGUAGE onto the other side of the film's own grammar, not to
  argue that its behaviour differs.

## EVIDENCE, the library's FIRST PIECE OF MEDIA — lib/evidence.tsx
NET-NEW 2026-08-06 ("The Same Face, The Same Plate"). REAL GAP, checked against this file in
full and confirmed independently by the Gate 0D critic. The shelf had an orbital eye, a
seafloor ear, a ground ear, two aerial machines, an under-ice swimmer, a bench-science family,
a records/paper family, a civics rules kit, an absence grammar, an arthropod and 13 biomes.
NOTHING on it was A PIECE OF MEDIA, and nothing was an EMISSIVE SURFACE that could act as a
light source. records.tsx `RecordsMachine` is a machine that PROCESSES records, not a record
that gets processed. paper.tsx `Sheet` and bench.tsx `ShortlistCard` are printed stock on the
numeric shadow contract, which is the right instinct on the wrong substance.
- `FrameOfEvidence` — THE RUN'S HERO and its THROUGHLINE OBJECT, one frame of police
  body-camera video as a physical held object — evidence.tsx — SHAPE AND MATERIAL DECISION,
  and it is what keeps this off the closed flat-HUD-chip defect: it is a PHYSICAL EMISSIVE
  OBJECT, not a card. Real bezel thickness with a LIT TOP EDGE and a DARK BOTTOM EDGE, a
  screen surface that spills its own light through screenlight.tsx, a contact shadow whenever
  it rests, and a slight off-axis tilt when `held`. The redaction box that lands on it is then
  its exact material opposite: axis-aligned, perfectly matte, no bevel, no rim, casts no light,
  and it lands FLAT WITH NO OVERSHOOT. A dead plane arriving on a lit dimensional object, which
  is the film's central visual event and the reason the two are different KINDS of rectangle
  rather than one inside another. THE ONE-CHANNEL LESSON APPLIED (07-25 horn, 07-26 cone,
  07-30 glider, 08-05 beetle): three state channels, the TWO TARGETS (`faceState`/`plateState`,
  sharp | hidden, independently), the SCANLINE (always crawling on an irrational period so the
  object is never a still photograph of a still photograph), and the PROGRESS RAIL. `dead`
  drops it to an unlit frame in a stack with a `queueTag`. tones/FormGradient/RimLight/
  ContactShadow, routed through vitals() — ACTIVE
- SCOPE, corrected at Gate 0D: this asset does NOT own the brackets. The brackets are FX.tsx
  `ScanReticle`, which has shipped since 2026-07-20 and which the first art-direction draft
  re-invented without noticing it existed. LESSON WORTH KEEPING: before speccing a net-new
  asset's state channels, grep the shelf for the VERB, not just for the noun.
- THE PROGRESS RAIL IS HERO WHITE, NOT THE ACCENT. It measures the queue, which is the half no
  machine touched, so painting it in the machine's reserved colour would have contradicted the
  film's own argument. Gate 0D caught this as a semantic collision, not a taste note.
- `FrameStack` — the queue as a physical pile — evidence.tsx — deterministic jitter, per-frame
  settle, never Math.random — ACTIVE

## SCREENLIGHT — lib/screenlight.tsx (CRAFT ADVANCE 2026-08-06)
NightGrade (07-25) gives a night AMBIENT with registered source BLOOM and DayGrade (07-31)
gives a daylight ambient. NEITHER CAN MAKE A SOURCE ACTUALLY KEY A SUBJECT, because both emit
DIVS and sit OUTSIDE the svg, so they can only wash over finished art. Every screen-lit scene
this engine had attempted faked the key by hand-pinning a fill at the call site.
- `ScreenLit` / `ScreenKey` / `ScreenBounce` / `keyAt` / `keySourceAt` — screenlight.tsx —
  THE COMPOSITION CONTRACT, stated before code because Gate 0D required it: SCREENLIGHT emits
  SVG-SPACE GEOMETRY that composes INTO tones/FormGradient/RimLight rather than sitting over
  them, so it reaches asset shading. It is ON BY DEFAULT inside a `<ScreenLit>` scope with an
  explicit `unlit` opt-out, because a default-off fix is a doctrine reminder wearing a code
  costume (the flat-HUD-chip lesson, 07-30). Three physical behaviours: FALLOFF BY DISTANCE
  from the emitting plane; an UPWARD-BIASED TERMINATOR, since screen light comes from BELOW the
  eye line so the lit band sits under a form's midline and the shadow rides on top, which is the
  one tell that separates a screen key from a studio key and is the opposite of every other
  light in this engine; and a CONTACT BOUNCE on the surface the screen sits on. `keyAt` is a
  pure test seam, the accentAllowedAt precedent — ACTIVE
- KNOWN NEXT ADVANCE: no look-dev harness was built this run. ScreenLook.tsx at three distances
  plus a 0.28-scale legibility strip was specified at Gate 0D and deferred under time. Build it
  before the next screen-lit story leans on this.

## MACHINE VISION — lib/vision.tsx (CRAFT ADVANCE 2026-08-07)

This channel keeps telling stories about machines that PERCEIVE (the orbital eye 07-23, the
ground ear 07-25, the plate reader 08-06, and now a robot that finds a fish's brain), and every
one of those runs hand-rolled its own reticle inside its own episode file, so nothing compounded.
This makes perception a first-class library layer.

Design rule it encodes: a perception overlay is the ONLY EMISSIVE thing in a frame. It does not
reflect the scene's light, it emits its own, so it is drawn with hairline strokes and a bloom that
never washes the subject, and its color should appear nowhere else in the film.

- `SearchReticle` — the hunting-to-locked mark. `lock` 0..1 drives width, dash, bloom and four
  converging corner ticks with a real overshoot at ~0.8 before settling. While hunting it samples
  ghosted candidate rejects. It NEVER stops moving (`searchDrift` runs on irrational periods), so a
  hold of any length still breathes, which is the DISPATCH_STANDARD section 8 finding applied at the
  component level rather than left to each scene. `label` prints a mono tag under it — ACTIVE
- `PendingMark` — a mark that has NOT landed: dotted, unlit, slowly rotating dash offset. This is how
  an announced-but-unconfirmed thing gets drawn without either asserting or sneering at it — ACTIVE
- `CandidateField` — N targets, each with its TRUE point passed in independently. The whole thesis of
  the 2026-08-07 dispatch as a component: the target is NOT where a template says it is, so the
  offsets are data per target and a ghosted "where a fixed guide would have guessed" ring is drawn
  beside each one — ACTIVE
- `ConfidenceBloom` — a single expanding ring on a lock. Use sparingly — ACTIVE
- `VisionGrid` — hairline scan grid plus a travelling scanline, for a shot that is explicitly the
  machine's own view — ACTIVE
- `ClaimChip` — an ink-outlined chip that LABELS a claim as somebody's assertion rather than as fact,
  with a mono sub-line (used this run as COMPANY SAYS). The sourcing discipline as a drawable object — ACTIVE
- `CYAN` / `searchDrift()` — the palette token and the drift function, exported so a scene can park
  something else on the same irrational motion.

## Characterized objects, added 2026-08-07
- `ReticleArm` — NET-NEW 2026-08-07, hero of "The Boat, Not The Brain". A gantry arm with a rail,
  a cross beam, a lens head and a spike carriage. Deliberate shape language: PURE MACHINED
  ORTHOGONAL against a film whose every other form is an organic taper (a salmon, a gloved hand, a
  worn wooden spike). It has ONE glass eye with a real specular and NO FACE, on purpose: the film
  must not make it sympathetic or sinister, only exact. `drop` 0..1 lowers the carriage, `spike`
  0..1 drives the striker, `look` steers the head. Cable loom carries secondary motion that swings
  AFTER the arm. Form-shaded + rim + contact shadow — Ep0807.tsx — ACTIVE
  (Episode-local for now. Promote to kit.tsx when a second story needs a gantry.)

## CLINIC — the library's FIRST CLINICAL FAMILY — lib/clinic.tsx
NET-NEW 2026-08-08 ("Not In The Buying", Alaska's first Rural Health Transformation awards).
REAL GAP, checked against this file in full first: the shelf carried an orbital eye, a seafloor
ear, a ground ear, two aerial machines, an under-ice swimmer, a bench-science family, a
records/paper family, a civics rules kit, an absence grammar, an arthropod, a piece of media and
13 biomes, and NOTHING on it was a piece of CLINICAL equipment, although this channel covers
Alaska health regularly. bench.tsx `AshReader` is the nearest prior art and it is the wrong verb:
that machine reads a SAMPLE brought indoors under a lamp, this one is CARRIED TO A PERSON.
- `TypeSlug` — THE RUN'S HERO and its throughline — clinic.tsx — a phrase cast as a physical slug
  of set type. The film's whole argument is about WHERE THE WORDS SIT in a statute, and an
  abstraction cannot be somewhere while a cast slug can. THE STATE CHANNEL IS THE FIT: `seated` 0
  is held proud of a surface with a lit gap under it (unmatched), 1 is dropped flush into a recess
  with no light left under it (located). `recess {w, fits}` DRAWS the mismatch as two scarlet
  dashed marks opening on either side, so a semantic claim becomes a measurable gap rather than a
  caption. Bevelled machined body with a lit top face and a dark bottom lip, mono type sized by
  the exact 0.602em advance so the body is derived from the string. `held` lifts and presents it,
  `accent` VO reactivity, routed through vitals() — ACTIVE
- `FieldRadiograph` — the portable X-ray unit, and the film's one plainly warm object —
  clinic.tsx — SHAPE-LANGUAGE DECISION: everything on it is a radius, against a film whose every
  other form is orthogonal, and the single most important line on the drawing is THE HANDLE,
  because the point is that a person picks it up and walks into a village clinic with it. NO FACE,
  deliberately, and that is the AshReader discipline rather than an omission: this equipment
  serves real communities and giving it eyes would make it a character with feelings about a story
  that is not its own. THREE STATE CHANNELS per the one-channel lesson (07-25 horn, 07-26 cone,
  07-30 glider, 08-05 beetle, 08-06 frame): THE ARM (folded in the case or raised over a patient,
  arriving with anticipation and overshoot), THE PAIR (the emitter cone lights and the detector
  plate ANSWERS it, always both, because a source with no receiver is a lamp), and THE HANDLE
  (straightens and bears weight as `carried` rises, slack when set down). AND IT HAS NO UPLINK:
  the back panel is deliberately bare, no antenna and no cable, which is the IceGlider
  missing-propeller trick applied to a different argument, since this machine needs a person and a
  battery and nothing else. `lid`, `expose`, `carried`, `stencil`, `tint`, `groundY`, `gain`.
  tones/FormGradient/RimLight/ContactShadow, routed through vitals() — ACTIVE
- `AllowanceBoard` — a posted list of allowable uses as a physical enamel notice board —
  clinic.tsx — civics.tsx models a rule that DECIDES about a thing arriving at it; this one is a
  posted LIST. Rows are 'allow', 'deny' (struck, and the strike falls on the excluded row only) or
  'cap', where a percentage CAP is drawn as a physical collar clamping the row instead of a
  footnote. Deliberate opposite of FieldRadiograph: no radius above 3, machine-set type, bolted —
  ACTIVE
- LESSON WORTH KEEPING, and it cost this run four rewrites: a gate can kill a FRAME, not just a
  string. Gate 0E rejected four VO drafts, and the fourth rejection was not a wording note, it was
  that a list of ALLOWABLE uses is a menu and a menu cannot be falsified, so "which lines got
  bought" smuggled in a premise the evidence never supplied. `AllowanceBoard` was built to carry
  that dead thesis and survives here in a smaller role. Build the asset the ARGUMENT needs, and
  make sure the argument survives a cold reader first.

## THE SIMULATION GRAMMAR — lib/simulation.tsx (CRAFT ADVANCE 2026-08-09)
The sibling of `absence.tsx`, and it exists for the same reason that file does: the shelf had
paid for this lesson four times and solved it zero times. This channel has drawn a MODELLED
thing on 07-25 (the landslide digital twin), 07-30 (the glider's dead-reckoned position),
08-06 (a capacity ceiling that was a ceiling and not a count) and 08-09 (a Virtual Pilot
Plant), and improvised it every time.
ABSENCE says: this should be here and is not.  SIMULATION says: this is here, it is exact, and
it is made of arithmetic.
- `Simulated` — renders ANY silhouette as A STATED MODEL — simulation.tsx — the contract is
  four clauses and each is a defect somebody already found: (1) HAIRLINE strokes of uniform
  width that IGNORE the scene's light, because a form-shaded model reads as a real object;
  (2) NO CONTACT AND NO SHADOW EVER, enforced by there being no prop for either, because a
  cast shadow is the strongest cue that a thing is physically present; (3) a CONTINUOUS
  RE-SOLVE on an irrational period, because a static wireframe reads as a render that failed
  rather than as a model that is running, which is exactly the lesson absence.tsx paid for
  with its drift layer; (4) a REQUIRED `fidelity` prop, not optional, so a caller has to state
  how well the modelled thing is known and low fidelity visibly loosens the linework. `drawn`
  animates a model into being outline-first. `occupied` tints an interior for a model meant to
  read as running — ACTIVE
- `SimField` — a POPULATION of measurements — simulation.tsx — a grid whose EMPTY cells are
  drawn as empty rather than omitted, because the gap between a grid's size and its fill is
  the only honest way to draw "compressed measurements, and little to compress" — ACTIVE
- `resolveJitter` / `SIM` / `SIM_DEEP` — the hunt function and the reserved hue, exported so a
  scene can park a readout on the same motion as the outline it belongs to.
- HONEST LIMITATION: the reserved-hue rule (this colour appears only on things that are not
  real) is enforced BY CONSTRUCTION, in that the token lives here and Ep0809 paints it only
  through these components. It is NOT enforced by AccentRegistry, which throws at paint time
  and would kill a render. A repo-level lint on reserved-hue literals is still the open item
  from 2026-08-01.

## BIOPROCESS — the shelf's FIRST CONTROLLER and FIRST CONTAINED PROCESS — lib/bioprocess.tsx
NET-NEW 2026-08-09 ("The Method, Not The Metal", NSF award 2614749). REAL GAP, checked against
this file in full first: the shelf carried an orbital eye, a seafloor ear, a ground ear, two
aerial machines, an under-ice swimmer, a bench-science family, a records and paper family, a
civics rules kit, an absence grammar, an arthropod, a piece of media, a clinical family, a
machine-vision layer and thirteen biomes. EVERY MACHINE ON IT PERCEIVES. Nothing on it
CONTROLS, and nothing on it is a vessel with a process inside.
- `LoopGovernor` — THE RUN'S HERO — bioprocess.tsx — SHAPE-LANGUAGE DECISION and a deliberate
  break with this channel's habit: IT HAS NO EYE. Every hero here for a year has been a thing
  that LOOKS, and this film's narration says in as many words that the software never looks at
  the microbe, so an eye would contradict the script in every frame. Its ancestor is the
  mechanical flyball governor, the original controller, which also makes it the ONE ROUND
  THING in a film of dented cylinders and torn heaps. THREE STATE CHANNELS per the
  thrice-learned one-channel lesson: THE SPIN (flyballs rise with load, the only part legible
  at feed size), THE LOOP (a cable that leaves the head and RETURNS, because a viewer cannot
  see that a controller is closed unless the line comes back, and which object it returns from
  is the film's whole argument), and THE THROTTLE (a power lever, NSF's "energy constrained"
  as a drawn part). `spin`, `throttle`, `strain`, `accent`, `phase`. tones/FormGradient/
  RimLight/ContactShadow, routed through vitals() — ACTIVE
- `SteelVessel` — the REAL one, heavy and irregular — bioprocess.tsx — weld seams that are not
  straight, hash-placed rivet heads, a lid hanging off true, a sight glass, a valve, and a
  wire-hung paper tag whose `tagTurn` carries the film's primary open loop for a hundred
  seconds (planted at 3.2s, paid at 108.9s), so it must never be defaulted to 1 by a call
  site. The mouth has a real lit interior FLOOR rather than a black hole, because the argument
  is that it is empty and an empty thing needs a visible bottom — ACTIVE
- `TwinVessel` — the SAME vessel in the simulation grammar — bioprocess.tsx — consumes the
  shared `VESSEL_PATH`, which is load-bearing rather than a convenience: the film stages the
  two at identical size so a viewer compares instead of ranking, and two separate paths would
  drift apart the first time either was edited and the comparison would quietly stop being
  true. `bioFidelity` is separate from `fidelity` ON PURPOSE and is the film's second open
  loop: the body models well and the biology does not — ACTIVE
- `CellSurface` — THE ACCURACY ASSET — bioprocess.tsx — Shewanella oneidensis does not eat,
  digest or breathe rare earths; it respires iron and manganese, and the rare earth
  interaction is BIOSORPTION. So the accuracy is built into the GEOMETRY rather than trusted
  to a caption: bound atoms sit on a radius strictly greater than the membrane's and are drawn
  AFTER it so they can never be occluded, and `reject` drives an atom that presses in, dimples
  the wall and is pushed back out. A scene physically cannot use this component to show
  ingestion — ACTIVE
- `VESSEL_PATH` / `BP` — the shared silhouette and the family palette.
- KNOWN NEXT ADVANCE: no look-dev harness was built. A `BioLook.tsx` with the governor at four
  spin/throttle states, both vessels side by side, and a 0.28-scale legibility strip should
  exist before the next story leans on this family, per the GateLook and BenchLook precedent.
