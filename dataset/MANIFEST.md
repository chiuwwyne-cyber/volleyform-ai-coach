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

## serve (26 clips)

Expanded 19->27 on 2026-08-16 with eight ON-COURT reps (usertut_serve_06..13)
from a user-provided serve tutorial, then reduced to 26 the same day when
`usertut_serve_10` turned out to be a static reach demonstration rather than a
serve (see the contact-selection audit at the end of this file). The video
offered 41 candidate windows and most were deliberately left out:

  * #11..#27 are arm-swing drills against a white wall with the ball still HELD
    in the hand -- a teaching position, not a struck contact
  * all 41 come from ONE demonstrator, and taking them all would leave serve at
    60 clips with two thirds from a single person; a homogeneous sample narrows
    the band, which is how a demo starts flagging correct technique

Convergence 0.80 -> 0.85.

> NOTE, and it is a real limitation: crouch.knee tightened from an accepted floor
> of 80.4 to 108.3 degrees, because these eight are STANDING serves with little
> knee bend. So the serve standard should be read as calibrated for STANDING
> serves, and a deeper jump-serve load is liable to be flagged.
>
> Two corrections to how this was originally written (2026-08-16):
>
>   * The old text said "a jump serve, which loads to roughly 90-105, would now
>     be flagged." That compares incompatible numbers. 90-105 is the SCANNER's
>     figure (2D image-plane angle at the minimum-knee frame over a 1.6s
>     lookback); 108.3 comes from the backend (3D `calculate_angle_3d` at the
>     lowest-hip frame over everything before contact). No complete jump-serve rep
>     has ever been measured through the backend path, so the false positive is a
>     well-motivated EXPECTATION, not a demonstrated fact. Measuring one rep
>     end-to-end is the cheapest way to settle it.
>   * The old text said "phase_reference_test still has no fixed serve case."
>     That is out of date: it now has `test_serve_flags_a_low_arm`,
>     `test_serve_accepts_a_sound_standing_serve`, and a direct guard asserting
>     the crouch-knee floor stays at or below 130. The remaining gap is narrower —
>     there is no JUMP-serve acceptance case, and there cannot be one until a real
>     jump-serve measurement exists to build the fixture from.

| File | Source |
|---|---|
| usertut_serve_06..09, 11..13.mp4 | user-provided serve tutorial, on-court reps only (trimmed) |
| ~~usertut_serve_10.mp4~~ | QUARANTINED to `dataset/_rejected/` — static reach demo, not a serve |

### Earlier serve set (19 clips, 5 tutorial + 14 Pexels; all still active)

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

## Rejected whole: jump-serve tutorial (2026-08-16)

A user-provided jump-serve tutorial (`videoplayback (3).mp4`, 374s, 640x360, not
committed) was scanned specifically to close the standing-serve limitation noted
under `serve` above. **Zero clips were taken.** The video is a teaching
BREAKDOWN, and a breakdown is structurally the wrong shape for this dataset: it
demonstrates the three-step approach, the toss, and the hand shape as separate
drills, and never shows one complete rep of all three.

Measured, not eyeballed — 5600 frames sampled, 5108 with a pose:

  * 1485 frames PASS THE LEG-LANDMARK HEURISTIC (knee+ankle visibility > 0.5,
    ankle inside frame). Read that as an upper bound, not "whole body in frame":
    the heuristic is fooled by hallucinated off-frame legs, as noted below
  * only 13 moments among those have the wrist well above the nose with a
    straight arm
  * of the 13, two are professional broadcast rallies (multi-player, already a
    standing rejection reason), and the rest are toss drills, footwork drills
    with the ball still held, or hand close-ups

**The new failure mode this exposes:** a toss at full extension is
indistinguishable from a contact frame by the rule `serve` actually uses —
`_segment_overhead` takes the highest wrist, and a good toss arm is higher and
straighter than the hitting arm at contact. Feeding a toss drill into `serve`
would not merely add noise, it would teach the contact band the wrong pose. This
is the same trap as the underhand-serve rule recorded above, one step sharper.

So the standing-serve calibration is unchanged by this video. Before hunting for
more footage, note that the limitation itself is not yet established:
`build_reference.py` pools every clip of an action into ONE band (`_trim_outliers`
with 1.5*IQR fences, then p10/p90) — that part is certain, it is what the code does.
IF jump-serve knee angles measured through the BACKEND turn out clearly lower than
the existing standing samples, they would either fall outside the fences and be
discarded as outliers, or survive and drag down the same floor standing serves are
judged against — the loosening this project already refused — and closing the gap
would then need subtype-aware evaluation (a separate action, a multi-modal band, or
classify-then-select).

That IF is not yet settled: no jump serve has been measured through the backend
path, and the familiar 90-105 figure is the scanner's incomparable 2D metric. So
the cheapest next step is not hunting footage — it is running ONE real jump serve
end to end and seeing where its crouch knee actually lands.

What the footage must look like: complete jump-serve REPS (approach, toss, strike,
land, one player, legs in frame), TRIMMED to one rep each. Not "match footage
rather than tutorials" — 13 serve clips originally came from tutorials (12 still
active after the quarantine below), so the
source medium is not the criterion. The rule is complete reps, whatever the source.
(No claim is made here about which source is cleaner: the audit below measures
candidate uniqueness, which says nothing about correctness.)

> Contact-selection audit (2026-08-16), prompted by the toss finding above, since
> `_segment_overhead` takes the GLOBAL highest wrist and a clip holding both a toss
> and a strike could be segmented on the wrong one. Ran the real `segment_action`
> over all 27 serve clips and looked for a second wrist peak >=8 frames from the
> chosen contact:
>
> The audit MUST use the smoothed signal. `_segment_overhead` minimises a 3-frame
> `_smooth()`ed series, not the raw per-frame wrist height. A first pass measured
> gaps on the raw series and produced a completely different — wrong — list of
> ties: it reported `pexels_6216964` at 0.000 when the smoothed gap is 0.0972.
> Reproduce with `tools/dataset_clips/audit_contact_selection.py`.
>
> Smoothed result: 3 of 27 have a second candidate within 0.01 —
> `pexels_6216953` (0.0012), `usertut_serve_10` (0.0052), `pexels_6217332`
> (0.0067). The other 24 range 0.014-0.126.
>
> What this does NOT show:
>
>   * that the other 24 are correct. A clip containing only a toss also has one
>     unique peak — the original failure mode — so a large gap only means "no
>     second candidate", never "the chosen frame is ball contact". Settling that
>     needs frame-by-frame viewing, which has not been done.
>   * that trimming to a single rep prevents ties. `usertut_serve_10` IS a trimmed
>     single-rep tutorial clip and is one of the three.
>   * any ranking of sources by cleanliness. Gap size measures candidate
>     uniqueness, not correctness, so it cannot order tutorial vs match footage.
>
> What it does show: in 3 clips the contact frame is decided by a difference at
> noise level. Those 3 were then viewed frame by frame:
>
>   * `pexels_6216953` — the chosen frame is a full overhead reach; the rival has
>     the ball still on the floor. Correct as chosen.
>   * `pexels_6217332` — the full 16.3s clip is ONE foreground player performing
>     TWO overhand serves (~t=5.4s and ~t=8.1s, ball visible leaving each time);
>     the background figures are others drilling separately, not a rally. The two
>     candidates are exactly those two serves, so either choice samples a genuine
>     serve contact. (An earlier note here called it "a rally with several
>     attacks" — that was a misread of a low-resolution frame pair, now withdrawn.
>     Its appearance in the rejected SET table is not a conflict: rejected as a
>     set, used as a serve.)
>   * `usertut_serve_10` — NOT A SERVE AT ALL. All 31 frames are a player standing
>     with one arm held up: a static reach demonstration. Wrist height varies by
>     0.023 across the whole clip where every other clip spans 0.10-0.96, and
>     `segment_action` returns `crouch: None` because there is no load phase. Its
>     contact sample was an arbitrary frame of a held pose. **Moved to
>     `dataset/_rejected/`, reference rebuilt, all 13 tests pass; serve is 26.**
>     Band impact was near zero: contact.elbow p10 141.9->141.5 (accepted low
>     126.7->126.2), contact.shoulder p10 122.5->122.3 (105.7->105.2), crouch.knee
>     UNCHANGED (it contributed no crouch sample), mean convergence 0.85 either
>     way. A pure correctness fix at essentially no cost.
>
> Note the audit did NOT catch that one — a 0.0052 gap only says "two candidates
> exist". Viewing the frames caught it. That is the concrete demonstration that
> candidate uniqueness cannot substitute for looking.

## All-action sweep (2026-08-16)

After `usertut_serve_10` was found by eye rather than by the audit, the same two
checks were run over all five actions instead of serve alone — spike and block
share serve's "global highest wrist" contact rule, so the same failures were
possible there and had never been looked for.

**A second static clip exists, and it is NOT being removed.** `usertut_set_01` is
100 frames of a player holding the setting hand position overhead, never
releasing a ball; wrist height moves 0.037 and `contact` lands on frame 2 of 100.
Structurally identical to `usertut_serve_10` — but measuring what it actually
contributes gives the opposite answer: elbow 119.4 against a band whose p50 is
121.7, shoulder 117.2 against a p50 of 106.1. Both sit near the middle of the
distribution, so the sample is benign and removing it would be churn.

The useful generalisation: **a held pose is only harmful when the held pose
differs from the action's key moment.** A held overhead reach is nothing like a
serve strike, so `usertut_serve_10` was poison. A held setting position is close
to the actual release, so `usertut_set_01` is harmless. "Static" alone is not a
rejection reason — compare the pose to the phase being sampled.
(Mild circularity: this clip is one of the 24 that built the band. At n=24 a
single clip barely moves p50, so the comparison is still informative.)

**Five untriaged near-ties in spike and block.** Contact candidates within 0.01
of each other, never inspected: spike `pexels_6217269` (0.0027) and
`pexels_6217335` (0.0026); block `usertut_block_01` (0.0011),
`usertut_block_02` (0.0019), `usertut_block_05` (0.0053). As established above a
tie is not evidence of a wrong pick, and these are recorded as unreviewed rather
than as defects.

**The thin crouch sample base is not serve-specific.** Clips whose segmentation
finds no load phase contribute no crouch sample at all:

| action | crouch.knee samples | clips |
|---|---:|---:|
| spike | 15 | 20 |
| serve | 19 | 26 |
| block | 16 | 18 |

Quote those floors against the sample count, not the clip count.


> Sample-base note, measured the same day across the then-13 usertut clips: 8 return
> `crouch: None`, so the crouch.knee band rests on 19 clips, not 27
> (`raw_count: 19` in reference_standards.json agrees). The "standing serve floor
> of 108.3" therefore has a much smaller sample base than the clip count suggests.
> Not an error, but worth knowing when quoting it.

> Scanner note, found the hard way on this video: ranking candidates by
> `above_nose / torso` is unsafe on its own. On a hand close-up the torso
> collapses to the clamp and the ratio explodes — 5.03 and 7.00 here were both
> wrist-and-ball close-ups, so the WORST frames ranked first.
>
> A landmark-visibility gate does not fix it by itself: MediaPipe happily
> hallucinates off-frame legs and reports them as visible. What works alongside it
> is a cap on the ratio, `MAX_NORM = 1.5`.
>
> That 1.5 is NOT an anatomical bound, and calling it one would be wrong. Pure
> proportion gives ~0.7 (an arm is about one torso, the nose about 0.25 torso above
> the shoulders) — but real full-body serves here measured 0.5–0.95, already past
> it, because the denominator is a PROJECTED shoulder-hip distance that shortens
> when the trunk arches back or the camera is off-axis. The actual justification is
> that the two regimes are an order of magnitude apart (0.5–0.95 normal vs 5–7 with
> a collapsed torso) and 1.5 sits in the gap. It rejects a FAILED DENOMINATOR, not
> a bad pose.
>
> And it is a HARD FILTER, not a ranking guard: frames at or above the cap are
> dropped before events are assembled, so they never reach the montage and no human
> ever sees them. Setting it too low silently discards good clips with no warning —
> if a video with real reps ever scans empty, suspect this first.
> `tools/dataset_clips/serve_scan_events.py` applies both gates (candidates
> 342 → 100, no runaway ratios) and also reports a crouch knee angle.
>
> Treat that crouch number as a TRIAGE HINT only. It is not the quantity the
> backend thresholds: the scanner takes a 2D image-plane angle at the minimum-knee
> frame over a fixed 1.6s lookback, while `_crouch_before` takes the lowest-hip
> frame and `calculate_angle_3d` over everything before contact. Those differences
> have never been error-measured, and the standing (~110–150) and jump (~90–105)
> ranges are only 5 degrees apart at the nearest edge — so a low value is a reason
> to look, not a classification.
