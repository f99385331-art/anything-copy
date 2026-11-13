#!/usr/bin/env python3
"""Self-test for anything-copy: exercises all six tools against
examples/sample-project (a sanitized real project). Leaves the fixture clean."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import server  # noqa: E402

FIXTURE = HERE / "examples" / "sample-project"


def main():
    tmp = Path(tempfile.mkdtemp(prefix="cc-selftest-"))
    shutil.copytree(FIXTURE, tmp / "sample-project")
    server.projects_root = lambda: tmp  # monkeypatch root
    try:
        r1 = server.tool_projects_list({})
        assert any(p["name"] == "sample-project" for p in r1["projects"]), r1
        print("[1/6] projects_list          OK", [p["status"] for p in r1["projects"]])

        r2 = server.tool_project_status({"project": "sample-project"})
        f = r2["feed"]
        assert f["item_count"] > 0 and r2["app_files"] > 0 and "feed_age_seconds" in r2
        print(f"[2/6] project_status         OK  steps={f['current_step'] and f['current_step']['step']}"
              f" plan={len(f['plan'])} worktools={len(f['work_tools'])} checks={r2['checks_total']}")

        r3 = server.tool_pending_questions({"project": "sample-project"})
        pend = r3["pending"]
        assert len(pend) >= 1, pend
        print(f"[3/6] pending_questions      OK  {len(pend)} pending:",
              [p["request"].get("title", "")[:24] for p in pend])

        req = next(p["request"] for p in pend if p["channel"] == "inbox")
        r4 = server.tool_answer_question({"project": "sample-project",
                                          "request_id": req["id"],
                                          "choice": (req.get("choices") or ["yes"])[0],
                                          "allow": True})
        assert r4.get("answered"), r4
        ans = tmp / "sample-project" / "inbox" / f"{req['id']}.answer.json"
        assert ans.exists(), "answer file not written"
        json.loads(ans.read_text(encoding="utf-8"))
        print("[4/6] answer_question        OK  wrote", ans.name)

        r5 = server.tool_unknowns_list({"project": "sample-project"})
        print("[5/6] unknowns_list          OK", len(r5["unknowns"]), "unknowns")

        r6 = server.tool_render_dashboard({"project": "sample-project",
                                           "out": str(tmp / "dash.html")})
        html = Path(r6["wrote"]).read_text(encoding="utf-8")
        assert html.startswith("<!doctype html>") and "sample-project" in html
        print("[6/6] render_dashboard       OK", len(html), "bytes")

        print("\nALL TOOLS PASS")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
