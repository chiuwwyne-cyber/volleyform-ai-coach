"""Put numbers in the loss matrix, using the only ground truth this project has.

The project has no labelled test set: every clip in dataset/ is assumed-correct
footage, collected to BUILD the standard. That rules out a normal confusion
matrix, but it does not rule out measuring anything -- it just means the two
cells have to be measured by different methods, and reported as different kinds
of number. Reporting them as one four-cell table of comparable percentages would
be the dishonest version.

FALSE POSITIVE -- measured, leave-one-out.
  Every dataset clip is assumed correct, so a clip the standard flags is a false
  positive by construction. Scoring a clip against a band it helped build is
  in-sample and optimistic, so each sample is scored against a band rebuilt
  WITHOUT it. That is a real out-of-sample estimate on n~10-25 samples per band.
  The in-sample number is printed beside it: the gap is how much the band is
  fitted to its own samples.

FALSE NEGATIVE -- measured, but as an exposure, not a rate.
  A rate needs known-bad clips, which do not exist here. What can be measured
  exactly is the BLIND ZONE: the interval between the enforced threshold and the
  10th percentile of correct form. An angle inside it is more extreme than 90% of
  correct execution and still passes. Its width in degrees is how wrong a user
  can be before the app says anything.

Neither number is a claim about real users, and the script says so in its output.
Both are claims about the standard, which is what the loss matrix is about.

Usage:
    .venv/Scripts/python.exe tools/loss_matrix.py <calibration_samples.json> [--json out.json]
"""

import json
import os
import sys
from collections import defaultdict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.reference_evaluation import ACTION_RULES, _band_range
from tools.build_reference import _band

# What the user is told, per issue code, and how loud it is. Severity is the
# backend's own SEVERITY_ORDER weighting, not a number invented here.
CODE_TEXT = {
    "elbow_bad": ("手肘太彎、沒有打開", "medium"),
    "elbow_not_straight": ("手臂沒有完全伸直", "medium"),
    "elbow_position_bad": ("手肘位置沒抓好", "medium"),
    "knee_bad": ("膝蓋沒有跟著一起彎、吸震不夠", "medium"),
    "knee_too_bent": ("膝蓋彎得太多", "high"),
    "shoulder_low": ("手臂（肩膀）抬得不夠高", "medium"),
    "hands_not_high": ("手舉得不夠高", "medium"),
}


def _rule_for(action, phase, joint):
    return ACTION_RULES.get(action, {}).get(phase, {}).get(joint, {})


def _enforced(band, rule):
    """The range the evaluator enforces, through its own function.

    Not band["accepted_range"], which is the same numbers rounded to one decimal.
    Rounding a threshold before comparing against it moves the decision boundary,
    and a sample sitting a hundredth of a degree outside would be scored
    differently here than by the app -- a measurement that disagrees with the
    thing it claims to measure.
    """
    return _band_range(band, band["tolerance"], has_high_rule=bool(rule.get("high")))


def _flagged(value, band, rule):
    """Exactly the evaluator's decision (reference_evaluation.py:242-251)."""
    low, high = _enforced(band, rule)
    hits = []
    if rule.get("low") and value < low:
        hits.append(rule["low"])
    elif rule.get("high") and value > high:
        hits.append(rule["high"])
    return hits


def analyse(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["kept"]:
            groups[(row["action"], row["phase"], row["joint"])].append(row)

    results = []
    for (action, phase, joint), samples in sorted(groups.items()):
        rule = _rule_for(action, phase, joint)
        if not rule:
            # No issue code on either side: nothing here can be flagged, so there
            # is no decision to score. receive.contact.shoulder is the live case.
            continue
        has_high = bool(rule.get("high"))
        values = [s["angle"] for s in samples]
        full = _band(values, joint, has_high_rule=has_high)

        in_sample = [s for s in samples if _flagged(s["angle"], full, rule)]

        loo_hits = []
        for index, sample in enumerate(samples):
            others = values[:index] + values[index + 1:]
            if len(others) < 4:
                continue  # a band from <4 samples is not a band
            held_out = _band(others, joint, has_high_rule=has_high)
            codes = _flagged(sample["angle"], held_out, rule)
            if codes:
                loo_hits.append({"clip": sample["clip"], "angle": sample["angle"],
                                 "codes": codes,
                                 "range": held_out["accepted_range"]})

        low, high = full["accepted_range"]
        blind = {}
        if rule.get("low"):
            blind["low"] = {"code": rule["low"], "threshold": low,
                            "p10": full["p10"], "width": round(full["p10"] - low, 1)}
        if rule.get("high"):
            blind["high"] = {"code": rule["high"], "threshold": high,
                             "p90": full["p90"], "width": round(high - full["p90"], 1)}

        results.append({
            "key": f"{action}.{phase}.{joint}",
            "n": len(samples),
            "accepted_range": full["accepted_range"],
            "p10": full["p10"], "p50": full["p50"], "p90": full["p90"],
            "tolerance": full["tolerance"],
            "convergence": full["convergence"],
            "convergence_state": full["convergence_state"],
            "in_sample_fp": len(in_sample),
            "loo_fp": len(loo_hits),
            "loo_n": sum(1 for i in range(len(samples)) if len(samples) - 1 >= 4),
            "loo_detail": loo_hits,
            "blind": blind,
            "rule": rule,
        })
    return results


def report(results, excluded, skipped_clips):
    print("=" * 96)
    print("FALSE POSITIVE  --  leave-one-out over assumed-correct dataset clips")
    print("=" * 96)
    print(f"{'decision point':<28}{'n':>4}{'LOO FP':>9}{'rate':>9}{'in-sample':>11}"
          f"{'accepted range':>18}{'conv':>8}")
    tot_n = tot_fp = tot_in = 0
    for r in results:
        rate = f"{100.0 * r['loo_fp'] / r['loo_n']:.1f}%" if r["loo_n"] else "n/a"
        rng = f"[{r['accepted_range'][0]}, {r['accepted_range'][1]}]"
        print(f"{r['key']:<28}{r['n']:>4}{r['loo_fp']:>9}{rate:>9}{r['in_sample_fp']:>11}"
              f"{rng:>18}{r['convergence']:>8}")
        tot_n += r["loo_n"]; tot_fp += r["loo_fp"]; tot_in += r["in_sample_fp"]
    print("-" * 96)
    overall = f"{100.0 * tot_fp / tot_n:.1f}%" if tot_n else "n/a"
    print(f"{'TOTAL':<28}{tot_n:>4}{tot_fp:>9}{overall:>9}{tot_in:>11}")

    print()
    print("=" * 96)
    print("FALSE NEGATIVE  --  blind zone: how wrong you can be before anything is said")
    print("=" * 96)
    print(f"{'decision point':<28}{'side':>6}{'code':<22}{'threshold':>11}"
          f"{'p10/p90':>10}{'blind':>8}  what the user is told")
    for r in results:
        for side, b in sorted(r["blind"].items()):
            text, severity = CODE_TEXT.get(b["code"], (b["code"], "?"))
            ref = b.get("p10", b.get("p90"))
            print(f"{r['key']:<28}{side:>6}{b['code']:<22}{b['threshold']:>11}"
                  f"{ref:>10}{b['width']:>8}  {text}（{severity}）")

    print()
    print("=" * 96)
    print("WHAT WAS EXCLUDED BEFORE ANY OF THIS")
    print("=" * 96)
    for reason, items in sorted(excluded.items()):
        print(f"{reason:<22}{len(items):>4}  {', '.join(sorted(set(items))[:5])}"
              f"{' ...' if len(set(items)) > 5 else ''}")
    for clip in skipped_clips:
        print(f"{'no segmentation':<22}{'':>4}  {clip['action']}/{clip['clip']} "
              f"({clip['frames']} frames)")

    print()
    print("READ THIS BEFORE QUOTING THE NUMBERS")
    print("  * FP is measured against clips ASSUMED correct, not verified correct by a")
    print("    coach. It is a self-consistency rate, not an accuracy rate.")
    print("  * FN has no rate here at all -- there are no known-bad clips. The blind")
    print("    zone is an exact property of the thresholds, not an error frequency.")
    print("  * Both describe the BACKEND aggregation (knee=min, elbow/shoulder=max).")
    print("    The browser path averages left and right, so it can land elsewhere.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    with open(sys.argv[1], encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload["rows"]

    excluded = defaultdict(list)
    for row in rows:
        if row["scoped_out"]:
            excluded["phase-scoped out"].append(f"{row['action']}/{row['clip']}")
        elif row["offscreen"]:
            excluded["off-screen landmark"].append(f"{row['action']}/{row['clip']}")

    results = analyse(rows)
    report(results, excluded, payload.get("skipped_clips", []))

    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(results, handle, ensure_ascii=False, indent=1)
        print(f"\nwritten: {out}")


if __name__ == "__main__":
    main()
