# Reference Dataset Manifest

All clips downloaded from Pexels (https://www.pexels.com/license/; free to use,
attribution not required).
Videos are NOT committed to the repository; only the derived angle statistics
(`backend/reference_standards.json`) are. To rebuild or extend, drop additional
clips into `dataset/<action>/` and rerun `tools/build_reference.py`.

## spike (17 clips)

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

## serve (14 clips)

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

## receive (16 clips)

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

## set (14 clips)

6 original Pexels candidates + 8 clips (usertut_set_01..08) trimmed on 2026-08-06
from a single-player setting tutorial the user provided (`videoplayback (1).mp4`,
not committed). The tutorial windows were auto-located by pose (single player,
hands in overhead-set position) then trimmed. This expansion raised convergence
(elbow 0.46->0.67, shoulder 0.50->0.65) AND kept correctness (phase_reference_test
still flags "hands too low"), unlike the rejected setter-search rally clips.

| File | Source |
|---|---|
| pexels_6179974.mp4 | https://www.pexels.com/video/6179974/ |
| pexels_6217115.mp4 | https://www.pexels.com/video/6217115/ |
| pexels_6217116.mp4 | https://www.pexels.com/video/6217116/ |
| pexels_6217125.mp4 | https://www.pexels.com/video/6217125/ |
| pexels_6217341.mp4 | https://www.pexels.com/video/6217341/ |
| pexels_6217182.mp4 | https://www.pexels.com/video/6217182/ |
| usertut_set_01..08.mp4 | user-provided single-player set tutorial (trimmed) |

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
