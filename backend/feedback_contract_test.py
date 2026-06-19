import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.feedback import ERROR_FEEDBACK, SEVERITY_ORDER, feedback_for


REQUIRED_FIELDS = {
    "title",
    "severity",
    "message",
    "fixes",
    "video_url",
    "body_part",
    "instant_cue",
    "practice_drill",
    "why_it_matters",
}


def main():
    for code in ERROR_FEEDBACK:
        payload = feedback_for(code)
        missing = sorted(REQUIRED_FIELDS - set(payload))
        if missing:
            raise SystemExit(f"{code} missing fields: {', '.join(missing)}")
        if payload["severity"] not in SEVERITY_ORDER:
            raise SystemExit(f"{code} has invalid severity: {payload['severity']}")
        if not payload["fixes"]:
            raise SystemExit(f"{code} must include at least one fix")
        if not payload["video_url"].startswith("https://"):
            raise SystemExit(f"{code} must include a safe video URL")

    print("feedback contract ok")
    print(f"issue codes: {len(ERROR_FEEDBACK)}")


if __name__ == "__main__":
    main()
