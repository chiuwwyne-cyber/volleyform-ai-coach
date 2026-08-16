# Reference Dataset Manifest

All clips downloaded from Pexels (https://www.pexels.com/license/; free to use,
attribution not required).
Videos are NOT committed to the repository; only the derived angle statistics
(`backend/reference_standards.json`) are. To rebuild or extend, drop additional
clips into `dataset/<action>/` and rerun `tools/build_reference.py`.

## spike (20 clips)

Expanded 17->20 on 2026-08-16 with three clean single-player net spikes
(usertut_spike_01..03) trimmed from a user-provided video. Convergence 0.75 ->
0.80. Rejected from the same batch: a clip whose only "spike" window was a
close-up of the shoes -- its reach of 6.58 torso-lengths was an artefact of a
cropped body, not an extraordinary jump.

| File | Source |
|---|---|
| usertut_spike_01..03.mp4 | user-provided single-player spike video (trimmed) |

### Earlier spike set (17 clips)

| File | Source |
|---|---|
| pexels_6216962.mp4 | https://www.pexels.com/video/6216962/ |
| pexels_6216852.mp4 | https://www.pexels.com/video/6216852/ |
| pexels_6217335.mp4 | https://www.pexels.com/video/6217335/ |
| pexels_6217330.mp4 | https://www.pexels.com/video/6217330/ |
| pexels_6216851.mp4 | https://www.pexels.com/video/6216851/ |
| pexels_6217334.mp4 | https://www.pexels.com/video/6217334/ |
| pexels_6216865.mp4 | https://www.pexels.com/video/6216865/ |
| pexels_6216863.mp4 | https://www.pexels.com/video/6216863/ |
| pexels_6216963.mp4 | https://www.pexels.com/video/6216963/ |
| pexels_6216861.mp4 | https://www.pexels.com/video/6216861/ |
| pexels_6217189.mp4 | https://www.pexels.com/video/6217189/ |
| pexels_6217187.mp4 | https://www.pexels.com/video/6217187/ |
| pexels_6216849.mp4 | https://www.pexels.com/video/6216849/ |
| pexels_6216850.mp4 | https://www.pexels.com/video/6216850/ |
| pexels_6179970.mp4 | https://www.pexels.com/video/6179970/ |
| pexels_6217269.mp4 | https://www.pexels.com/video/6217269/ |
| pexels_6217338.mp4 | https://www.pexels.com/video/6217338/ |

## serve (27 clips)

Expanded 19->27 on 2026-08-16 with eight ON-COURT reps (usertut_serve_06..13)
from a user-provided serve tutorial. The video offered 41 candidate windows and
most were deliberately left out:

  * #11..#27 are arm-swing drills against a white wall with the ball still HELD
    in the hand -- a teaching position, not a struck contact
  * all 41 come from ONE demonstrator, and taking them all would leave serve at
    60 clips with two thirds from a single person; a homogeneous sample narrows
    the band, which is how a demo starts flagging correct technique

Convergence 0.80 -> 0.85.

> NOTE, and it is a real limitation: crouch.knee tightened from an accepted floor
> of 80.4 to 108.3 degrees, because these eight are STANDING serves with little
> knee bend. A jump serve, which loads to roughly 90-105, would now be flagged.
> The suite cannot catch this -- phase_reference_test still has no fixed serve
> case, and angle_acceptance derives its fixtures from the band itself. So the
> serve standard should be read as calibrated for STANDING serves.

| File | Source |
|---|---|
| usertut_serve_06..13.mp4 | user-provided serve tutorial, on-court reps only (trimmed) |

### Earlier serve set (19 clips)

14 Pexels clips + 5 clips (usertut_serve_01..05) trimmed on 2026-08-14 from a
user-provided single-player serve tutorial (`videoplayback (1).mp4`, Sikana,
111s, not committed). The tutorial teaches BOTH underhand and overhand serves;
only overhand reps were kept, because serve is an OVERHEAD_ACTION whose contact
frame is "highest wrist" -- an underhand rep would sample a follow-through as if
it were contact and corrupt the band. Candidate events were ranked by reach
normalized to torso length (raw image-space reach under-rates wide shots), then
filtered to full-body only (ankle visibility > 0.5, inside frame) so the crouch
knee sample is real; leg-cropped close-ups, a two-person split-screen intro, and
toss/prep frames (elbow 120-149) were rejected. Windows avoid scene cuts.

Convergence rose 0.68->0.80 and the band TIGHTENED rather than loosened:
contact.shoulder accepted-low 59.9->100.7 (p10 79.6->116.9), so "arm not raised
enough" stays detectable. crouch.knee's 180 upper cap is pre-existing, unchanged
by this expansion. All 11 backend + 1 frontend tests pass.

| File | Source |
|---|---|
| pexels_6217337.mp4 | https://www.pexels.com/video/6217337/ |
| pexels_6217332.mp4 | https://www.pexels.com/video/6217332/ |
| pexels_6217339.mp4 | https://www.pexels.com/video/6217339/ |
| pexels_6217331.mp4 | https://www.pexels.com/video/6217331/ |
| pexels_6216964.mp4 | https://www.pexels.com/video/6216964/ |
| pexels_6217069.mp4 | https://www.pexels.com/video/6217069/ |
| pexels_6217175.mp4 | https://www.pexels.com/video/6217175/ |
| pexels_6217265.mp4 | https://www.pexels.com/video/6217265/ |
| pexels_6216953.mp4 | https://www.pexels.com/video/6216953/ |
| pexels_10350524.mp4 | https://www.pexels.com/video/10350524/ |
| pexels_6217188.mp4 | https://www.pexels.com/video/6217188/ |
| pexels_12169508.mp4 | https://www.pexels.com/video/12169508/ |
| pexels_10350521.mp4 | https://www.pexels.com/video/10350521/ |
| pexels_12169479.mp4 | https://www.pexels.com/video/12169479/ |
| usertut_serve_01..05.mp4 | user-provided single-player serve tutorial (overhand reps only, trimmed) |

## receive (24 clips)

Expanded 16->24 on 2026-08-16 with 8 clips (usertut_dig_05..12) trimmed from
three user-provided single-player passing videos (not committed): a "dig to
yourself" drill, a platform tutorial captioned STRAIGHT ARMS / CONTACT ON
FOREARMS / STEP TO TARGET, and a low-defence drill. Windows were pose-located on
"wrists together + below the shoulders + elbows > 140 + knee < 155", then every
candidate was reviewed in a montage.

Six candidates were rejected there, both for reasons that have burnt this
dataset before:
  * four were close-ups of the hands and forearms with the legs out of frame
    entirely, so their 34-44 degree "knee" readings were artefacts
  * two showed nearly straight legs (153, 154), the exact fault that forced the
    2026-08-07 receive expansion to be reverted -- an upright demonstrator
    widens the knee band until "knee too straight" stops being flagged

The eight kept measure 88-129 degrees at the knee. Convergence rose 0.72 -> 0.82
(elbow 0.89, knee 0.78, shoulder 0.78) and the knee band held: p10 90.7, p90
149.9, accepted upper 171.3, so a straight-legged 180 is still flagged. All 11
backend + 2 frontend tests pass.

| File | Source |
|---|---|
| usertut_dig_05..08.mp4 | user-provided "dig to yourself" drill (trimmed) |
| usertut_dig_09..10.mp4 | user-provided platform tutorial (trimmed) |
| usertut_dig_11..12.mp4 | user-provided low-defence drill (trimmed) |

### Earlier receive set (16 clips)

12 Pexels candidates + 4 clips (usertut_dig_01..04) trimmed on 2026-08-07 from a
user-provided single-player defensive drill (`videoplayback (9).mp4`, not
committed) with clear LOW bent-knee digs. Windows were pose-located (wrists
together + low + knee < 150) so the knee band stays correct (p10 93.5, p90 149.7)
— unlike the earlier straight-knee tutorials that were rejected. Convergence rose
(elbow 0.67->0.75, knee 0.62->0.71, shoulder 0.64->0.69).

| File | Source |
|---|---|
| pexels_12169404.mp4 | https://www.pexels.com/video/12169404/ |
| pexels_12169454.mp4 | https://www.pexels.com/video/12169454/ |
| pexels_6216862.mp4 | https://www.pexels.com/video/6216862/ |
| pexels_6217278.mp4 | https://www.pexels.com/video/6217278/ |
| pexels_6217340.mp4 | https://www.pexels.com/video/6217340/ |
| pexels_6217342.mp4 | https://www.pexels.com/video/6217342/ |
| pexels_6217344.mp4 | https://www.pexels.com/video/6217344/ |
| pexels_12169435.mp4 | https://www.pexels.com/video/12169435/ |
| pexels_12169455.mp4 | https://www.pexels.com/video/12169455/ |
| pexels_12169640.mp4 | https://www.pexels.com/video/12169640/ |
| pexels_6216965.mp4 | https://www.pexels.com/video/6216965/ |
| pexels_6179955.mp4 | https://www.pexels.com/video/6179955/ |
| usertut_dig_01..04.mp4 | user-provided single-player low-dig drill (trimmed) |

## set (24 clips)

6 original Pexels candidates + 8 clips (usertut_set_01..08) trimmed on 2026-08-06
from a single-player setting tutorial the user provided (`videoplayback (1).mp4`,
not committed). The tutorial windows were auto-located by pose (single player,
hands in overhead-set position) then trimmed. This expansion raised convergence
(elbow 0.46->0.67, shoulder 0.50->0.65) AND kept correctness (phase_reference_test
still flags "hands too low"), unlike the rejected setter-search rally clips.

Expanded 14->24 on 2026-08-14 with 10 clips (usertut_set_09..18) trimmed from a
second user-provided single-player setting tutorial (`videoplayback (10).mp4`, ~15
min, not committed). All 34 pose-located "both wrists overhead + hands close"
windows were reviewed in an annotated montage; rejected inserts were broadcast
match footage (multi-player), a shoe close-up, and the "DON'T WANT TO BE TOO
TIGHT" wrong-form demo (elbow 44-71 deg). Only 10 clean overhead-set reps kept.
Convergence rose (shoulder 0.65->0.79, elbow 0.67->0.83; set avg 0.66->0.81) AND
correctness held: set shoulder p10 stayed high (83.9, accepted-low 65.1) so
phase_reference_test still flags shoulder_low -- unlike the rally clips that
pushed p10 down to ~45. All 11 backend + 1 frontend tests pass.

| File | Source |
|---|---|
| pexels_6179974.mp4 | https://www.pexels.com/video/6179974/ |
| pexels_6217115.mp4 | https://www.pexels.com/video/6217115/ |
| pexels_6217116.mp4 | https://www.pexels.com/video/6217116/ |
| pexels_6217125.mp4 | https://www.pexels.com/video/6217125/ |
| pexels_6217341.mp4 | https://www.pexels.com/video/6217341/ |
| pexels_6217182.mp4 | https://www.pexels.com/video/6217182/ |
| usertut_set_01..08.mp4 | user-provided single-player set tutorial (trimmed) |
| usertut_set_09..18.mp4 | 2nd user set tutorial (videoplayback (10), trimmed) |

## block (18 clips, candidate-calibrated, robust outlier-trimmed)

Expanded 6->12 (2026-08-05, Pexels) then 12->18 (2026-08-07) with 6 clips
(usertut_block_01..06) trimmed from a user-provided single-player over-net
blocking drill (`videoplayback (8).mp4`, not committed). tools/build_reference.py
trims IQR (>1.5x) outliers so one bad clip cannot stretch the band. All tests pass
and convergence rose (elbow 0.61->0.86, shoulder ->0.83, crouch.knee ->0.72).

| File | Source |
|---|---|
| pexels_10350518.mp4 | https://www.pexels.com/video/10350518/ |
| pexels_10350520.mp4 | https://www.pexels.com/video/10350520/ |
| pexels_6179961.mp4 | https://www.pexels.com/video/6179961/ |
| pexels_6217270.mp4 | https://www.pexels.com/video/6217270/ |
| pexels_6217349.mp4 | https://www.pexels.com/video/6217349/ |
| pexels_6179836.mp4 | https://www.pexels.com/video/6179836/ |
| pexels_6217064.mp4 | https://www.pexels.com/video/6217064/ |
| pexels_6217113.mp4 | https://www.pexels.com/video/6217113/ |
| pexels_6217333.mp4 | https://www.pexels.com/video/6217333/ |
| pexels_6216855.mp4 | https://www.pexels.com/video/6216855/ |
| pexels_6179826.mp4 | https://www.pexels.com/video/6179826/ |
| pexels_6217180.mp4 | https://www.pexels.com/video/6217180/ |
| usertut_block_01..06.mp4 | user-provided single-player over-net block drill (trimmed) |

## Pending SET candidates (2026-08-05, awaiting a clean single-player clip)

The block candidates above were integrated (the robust calibration handles them).
The setter-search candidates below are NOT usable: they are rally footage where
the "set" is actually low-arm digging/passing, forming a bad cluster (not
outliers), which widens the set shoulder band and makes the app miss real
"hands too low" errors — the test suite rejects them. Set stays at 6 until a
clean single-player 舉球 clip is provided. See the decision doc above.

| Candidate (setter search — REJECTED, needs clean footage) | Source |
|---|---|
| pexels_6217281.mp4 | https://www.pexels.com/video/6217281/ |
| pexels_6217282.mp4 | https://www.pexels.com/video/6217282/ |
| pexels_6217332.mp4 | https://www.pexels.com/video/6217332/ |
| pexels_6179963.mp4 | https://www.pexels.com/video/6179963/ |
| pexels_6217273.mp4 | https://www.pexels.com/video/6217273/ |
| pexels_6217175.mp4 | https://www.pexels.com/video/6217175/ |
