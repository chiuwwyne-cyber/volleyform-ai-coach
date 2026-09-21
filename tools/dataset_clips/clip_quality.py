"""Shared frame-quality checks for the clip scanners.

Every scanner had grown its own copy of "are the legs in frame", and they had
drifted to three different answers for the same question -- block used
visibility >= 0.6 with ankle y <= 0.95, serve used 0.5 and 0.99, set used an
inline vis > 0.5. None of them was the rule the evaluator actually applies, so a
clip could clear the scanner and then have the very same joint refused at
judgement time.

There is now one gate, and it is the evaluator's: angle.angle.landmarks_offscreen.

Two checks here have no equivalent anywhere in the old scanners, and both were
added after measuring a 16-minute match recording (2026-09-21):

  subject continuity -- MediaPipe returned a pose on 12908 of 12908 sampled
      frames. It never says "nobody here"; with twelve players on court it simply
      picks one, and it changed which one 167 times, roughly every 5.8 seconds.
      A video that tracked a bystander for its entire length has already passed
      every check this pipeline had.

  torso floor -- MAX_NORM in serve_scan_events bounds the close-up regime, where
      the torso denominator collapses. Nothing bounded the far regime. That match
      produced torsos down to 0.008 of frame height, where landmark noise is the
      same size as the angles being measured.
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from angle.angle import landmarks_offscreen  # noqa: E402

# Knees and ankles. Both sides, because get_angles takes knee = min(left, right)
# and one invented leg is enough to win that.
LEG_LANDMARKS = (25, 26, 27, 28)

# Shoulder-to-hip distance, as a fraction of frame height, below which the
# detection is treated as degenerate rather than merely small.
#
# Chosen from the data, not picked: across the 209 reference samples that pass
# the off-screen gate, a floor of 0.06 excludes exactly one (0.5%), while 0.10
# would exclude 12 (5.7%) of clips the calibration already accepts. Like
# MAX_NORM, this is not an anatomical bound -- it works because the failure
# regime (0.008) is an order of magnitude away.
TORSO_FLOOR = 0.06

# Hip-centre movement between consecutive sampled frames that cannot be one body
# continuing to move. Clean single-subject footage measures 0.02-0.08 per step;
# a subject switch in that match measured up to 0.73.
SUBJECT_JUMP = 0.15


def legs_offscreen(landmarks):
    """Are the knee/ankle landmarks guessed rather than seen?

    Delegates to the evaluator's gate, so the scanner and the judgement agree
    about which frames are readable. The old per-scanner rule (visibility plus a
    y cutoff) is fooled in both directions: MediaPipe reports invented off-frame
    legs confidently, and it reports genuinely visible but occluded legs at low
    confidence.
    """
    return landmarks_offscreen(landmarks, LEG_LANDMARKS)


def torso_length(landmarks):
    """Shoulder-midpoint to hip-midpoint, in frame heights."""
    shoulder_x = (landmarks[11].x + landmarks[12].x) / 2.0
    shoulder_y = (landmarks[11].y + landmarks[12].y) / 2.0
    hip_x = (landmarks[23].x + landmarks[24].x) / 2.0
    hip_y = (landmarks[23].y + landmarks[24].y) / 2.0
    return ((shoulder_x - hip_x) ** 2 + (shoulder_y - hip_y) ** 2) ** 0.5


def torso_too_small(landmarks, floor=TORSO_FLOOR):
    return torso_length(landmarks) < floor


def hip_centre(landmarks):
    return ((landmarks[23].x + landmarks[24].x) / 2.0,
            (landmarks[23].y + landmarks[24].y) / 2.0)


def subject_runs(frames, jump=SUBJECT_JUMP, key=hip_centre):
    """Split a frame sequence into stretches that plausibly follow ONE person.

    `frames` is any sequence whose entries are landmark lists, or None where no
    pose was returned. Yields lists of (index, frame) pairs.

    This cannot prove the tracked person is the RIGHT person -- a bystander
    standing still tracks perfectly. It only detects the moment tracking moves to
    a different body, which is the failure that produced a whole unusable clip
    the existing checks passed. Treat a long run as necessary, never sufficient:
    the montage still has to show a human that it is the subject performing the
    action.
    """
    runs, current, previous = [], [], None
    for index, frame in enumerate(frames):
        if frame is None:
            if current:
                runs.append(current)
            current, previous = [], None
            continue
        centre = key(frame)
        if previous is not None:
            step = ((previous[0] - centre[0]) ** 2 + (previous[1] - centre[1]) ** 2) ** 0.5
            if step > jump:
                runs.append(current)
                current = []
        current.append((index, frame))
        previous = centre
    if current:
        runs.append(current)
    return [r for r in runs if r]


def frame_is_usable(landmarks):
    """The per-frame half of the gate: legs really seen, and the player not tiny.

    Returns (ok, reason). The reason string is for the scanner's own reporting --
    a scanner that silently drops frames teaches nobody why a video scanned empty.
    """
    if landmarks is None or len(landmarks) < 29:
        return False, "no pose"
    if torso_too_small(landmarks):
        return False, f"torso {torso_length(landmarks):.3f} < {TORSO_FLOOR}"
    if legs_offscreen(landmarks):
        return False, "legs off-screen or unconfident"
    return True, ""
