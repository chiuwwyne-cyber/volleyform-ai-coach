import json
import os
import re

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
NEWLINE = chr(10)


def _read(*parts):
    with open(os.path.join(ROOT_DIR, *parts), "r", encoding="utf-8") as file:
        return file.read()


def test_reference_standards_are_synced_to_frontend():
    backend_reference = json.loads(_read("backend", "reference_standards.json"))
    local_analyzer = _read("frontend", "local-analyzer.js")
    match = re.search(r"const REFERENCE_STANDARDS = (\{.*?\n\});", local_analyzer, re.S)
    if not match:
        raise SystemExit("Frontend local analyzer is missing REFERENCE_STANDARDS")
    frontend_reference = json.loads(match.group(1))
    assert frontend_reference == backend_reference


def test_frontend_build_markers_are_consistent():
    build_info = json.loads(_read("frontend", "build-info.json"))
    index = _read("frontend", "index.html")
    app = _read("frontend", "app.js")
    service_worker = _read("frontend", "service-worker.js")
    build = build_info["buildVersion"]
    cache = build_info["serviceWorkerCache"]
    assert build in index
    assert build in app
    assert cache in service_worker


def test_index_replaces_stale_build_query():
    index = _read("frontend", "index.html")
    assert "requestedBuild !== currentFrontendBuild" in index
    assert "params.set(\"build\", currentFrontendBuild)" in index
    assert "window.history.replaceState" in index


def test_every_issue_code_has_frontend_text():
    """A code the backend can emit but the browser has no words for is a silent bug.

    Nothing guarded this. The feedback tables live twice -- backend/feedback.py and
    the phaseIssueTips / phaseProblemPhrases maps in frontend/app.js -- and
    sync_frontend.py copies the reference standards across but NOT the wording. The
    frontend degrades politely rather than crashing, which is what makes the gap
    invisible: an unmapped code falls through to "這個部位需要再調整", so a user on
    the on-device path gets a real problem described in words that tell them nothing,
    and every test still passes.

    Found while adding a new issue code, which is when the gap became visible: the
    guard caught lobster_receive_risk -- the app's ONLY high-severity code -- with no
    entry in phaseProblemPhrases, so on-device users saw the vaguest possible text
    for the most serious thing the app can report.
    """
    import sys

    if ROOT_DIR not in sys.path:
        sys.path.append(ROOT_DIR)
    from backend.feedback import ERROR_FEEDBACK

    app = _read("frontend", "app.js")

    def _keys(table_name):
        opener = "const " + table_name + " = {"
        start = app.find(opener)
        if start < 0:
            raise SystemExit(f"frontend/app.js is missing {table_name}")
        end = app.find(NEWLINE + "};", start)
        if end < 0:
            raise SystemExit(f"{table_name} in frontend/app.js is not closed")
        body = app[start + len(opener):end]
        return set(re.findall(r"^\s{2}([a-z_]+):", body, re.M))

    def _keys_from(rel_path, table_name):
        text = _read(*rel_path.split("/"))
        opener = "const " + table_name + " = {"
        start = text.find(opener)
        if start < 0:
            raise SystemExit(f"{rel_path} is missing {table_name}")
        end = text.find(NEWLINE + "};", start)
        body = text[start + len(opener):end]
        return set(re.findall(r"^\s{2}([a-z_]+):", body, re.M))

    tips = _keys("phaseIssueTips")
    phrases = _keys("phaseProblemPhrases")

    # Only codes the phase-aware evaluator can actually raise need phase wording;
    # the capture-quality codes (unknown_action, good, ...) never reach that path.
    from backend.reference_evaluation import ACTION_RULES

    band_codes = {code for phases in ACTION_RULES.values()
                  for joints in phases.values()
                  for rule in joints.values()
                  for code in rule.values()}
    extra_codes = {"lobster_receive_risk"}
    required = (band_codes | extra_codes) & set(ERROR_FEEDBACK)

    # Same gap, different table: a code with no ISSUE_JOINT_STATUS entry is reported
    # in words while the 3D figure and the error skeleton stay entirely green, so the
    # user is told something is wrong and shown nothing.
    from backend.analyzer import ISSUE_JOINT_STATUS

    missing_status = sorted(required - set(ISSUE_JOINT_STATUS))
    assert not missing_status, (
        f"ISSUE_JOINT_STATUS in backend/analyzer.py has no entry for: {missing_status}. "
        "The problem would be described but no joint highlighted."
    )

    local_status = _keys_from("frontend/local-analyzer.js", "ISSUE_JOINT_STATUS")
    missing_local = sorted(set(ISSUE_JOINT_STATUS) - local_status)
    assert not missing_local, (
        f"local-analyzer.js ISSUE_JOINT_STATUS is missing: {missing_local}. "
        "Backend results rendered on-device would highlight nothing."
    )

    missing_tips = sorted(required - tips)
    missing_phrases = sorted(required - phrases)
    assert not missing_tips, (
        f"phaseIssueTips in frontend/app.js has no entry for: {missing_tips}. "
        "On-device users would be told to '先放慢動作' instead of what to fix."
    )
    assert not missing_phrases, (
        f"phaseProblemPhrases in frontend/app.js has no entry for: {missing_phrases}. "
        "On-device users would see '這個部位需要再調整' instead of the problem."
    )


def main():
    test_reference_standards_are_synced_to_frontend()
    test_frontend_build_markers_are_consistent()
    test_index_replaces_stale_build_query()
    test_every_issue_code_has_frontend_text()
    print("frontend sync ok")
    print("checked: backend reference sync, build markers, stale build rewrite, "
          "issue-code wording and joint-status parity")


if __name__ == "__main__":
    main()
