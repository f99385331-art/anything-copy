#!/usr/bin/env python3
"""anything-copy: an MCP stdio server that lets any agent watch and steer
Craft Anything build projects through their on-disk workspace contract.

Pure Python stdlib. Read-only except answering inbox questions.
Protocol: newline-delimited JSON-RPC 2.0 (Model Context Protocol, stdio).
Works with Craft Anything 0.5.0+ (feed.json v5, craft.json v2-v5 tolerant).
"""
import json
import os
import sys
import time
from pathlib import Path

SERVER_NAME = "anything-copy"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


def projects_root() -> Path:
    env = os.environ.get("CRAFT_PROJECTS_DIR", "").strip()
    if env:
        return Path(env)
    return Path.home() / "Documents" / "Craft Anything"


def resolve_project(name: str) -> Path:
    root = projects_root().resolve()
    p = (root / name).resolve()
    if not str(p).startswith(str(root)):
        raise ValueError("project name escapes the projects root")
    if not (p / "craft.json").exists():
        raise ValueError(f"not a Craft project: {name}")
    return p


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def summarize_feed(feed):
    """Tolerant fold of feed.json v5 items into a live status."""
    out = {"current_step": None, "plan": [], "last_agent": None,
           "agent_streaming": None, "work_tools": {}, "recent_errors": [],
           "last_check": None, "pending_ask": None, "paused": False,
           "item_count": 0}
    if not isinstance(feed, dict):
        return out
    items = feed.get("items") or []
    out["item_count"] = len(items)
    for it in items:
        if isinstance(it, str):
            if it == "Paused":
                out["paused"] = True
            elif it == "PlanDismissed":
                out["plan"] = []
            continue
        if not isinstance(it, dict):
            continue
        for kind, body in it.items():
            if kind == "Step":
                out["current_step"] = body
            elif kind == "Plan" and isinstance(body, list):
                out["plan"] = body
                out["paused"] = False
            elif kind == "Agent" and isinstance(body, dict):
                out["last_agent"] = (body.get("text") or "")[-400:]
                out["agent_streaming"] = body.get("streaming")
                out["paused"] = False
            elif kind == "Work" and isinstance(body, dict):
                for pair in body.get("tools") or []:
                    if isinstance(pair, list) and pair:
                        name = str(pair[0])
                        rec = out["work_tools"].setdefault(name, {"ok": 0, "fail": 0})
                        if len(pair) > 1 and pair[1] is False:
                            rec["fail"] += 1
                        else:
                            rec["ok"] += 1
            elif kind == "Error" and isinstance(body, dict):
                out["recent_errors"].append(
                    {"message": (body.get("message") or "")[:300],
                     "remediation": body.get("remediation")})
                out["recent_errors"] = out["recent_errors"][-3:]
            elif kind == "Check" and isinstance(body, dict):
                out["last_check"] = {
                    "round": body.get("round"), "check": body.get("check"),
                    "passed": body.get("passed"), "similarity": body.get("similarity"),
                    "pages": body.get("pages") or []}
            elif kind == "Ask" and isinstance(body, dict):
                if body.get("answer") in (None, ""):
                    out["pending_ask"] = body.get("request")
                else:
                    out["pending_ask"] = None
    return out


def tool_projects_list(_args):
    root = projects_root()
    rows = []
    if root.is_dir():
        for d in sorted(root.iterdir()):
            m = load_json(d / "craft.json") if d.is_dir() else None
            if m is None:
                continue
            rows.append({"name": d.name, "status": m.get("status"),
                         "note": (m.get("note") or "")[:160],
                         "updated_ms": m.get("updated_ms")})
    return {"projects_root": str(root), "projects": rows}


def tool_project_status(args):
    p = resolve_project(args["project"])
    manifest = load_json(p / "craft.json") or {}
    feed = summarize_feed(load_json(p / "feed.json"))
    usage = load_json(p / "usage.json") or {}
    unknown_open = 0
    udir = p / "investigation.cany" / "unknowns"
    if udir.is_dir():
        for f in udir.glob("*.json"):
            u = load_json(f)
            if isinstance(u, dict) and u.get("status") not in ("resolved",):
                unknown_open += 1
    app_files = 0
    adir = p / "app"
    if adir.is_dir():
        app_files = sum(1 for _ in adir.rglob("*") if _.is_file())
    age = None
    fj = p / "feed.json"
    if fj.exists():
        age = round(time.time() - fj.stat().st_mtime, 1)
    return {"project": p.name, "status": manifest.get("status"),
            "note": manifest.get("note"), "request": (manifest.get("request") or "")[:200],
            "target": manifest.get("target"), "last_reply": (manifest.get("last_reply") or "")[:600],
            "checks_total": len(manifest.get("checks") or []),
            "feed": feed, "feed_age_seconds": age,
            "usage": {"work_ms": usage.get("work_ms"), "priced": usage.get("priced")},
            "unknown_open": unknown_open, "app_files": app_files}


def pending_items(p: Path):
    out = []
    inbox = p / "inbox"
    if inbox.is_dir():
        for rf in sorted(inbox.glob("*.request.json")):
            req = load_json(rf)
            if isinstance(req, dict):
                out.append({"channel": "inbox", "request": req})
    ask = summarize_feed(load_json(p / "feed.json")).get("pending_ask")
    if ask:
        out.append({"channel": "feed", "request": ask})
    return out


def tool_pending_questions(args):
    p = resolve_project(args["project"])
    return {"project": p.name, "pending": pending_items(p)}


def tool_answer_question(args):
    p = resolve_project(args["project"])
    rid = args.get("request_id")
    inbox = p / "inbox"
    requests = []
    if inbox.is_dir():
        for rf in inbox.glob("*.request.json"):
            req = load_json(rf)
            if isinstance(req, dict):
                requests.append((rf, req))
    if not requests:
        return {"answered": False, "reason": "no inbox requests"}
    if rid:
        chosen = [(rf, req) for rf, req in requests if req.get("id") == rid]
        if not chosen:
            return {"answered": False, "reason": f"request id not found: {rid}"}
    elif len(requests) == 1:
        chosen = requests
    else:
        return {"answered": False, "reason": "multiple pending; pass request_id",
                "requests": [r.get("id") for _, r in requests]}
    rf, req = chosen[0]
    answer = {"choice": args.get("choice"), "text": args.get("text"),
              "allow": args.get("allow"), "always": bool(args.get("always", False))}
    af = rf.with_name(f"{req.get('id')}.answer.json")
    af.write_text(json.dumps(answer, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"answered": True, "wrote": af.name, "request_title": req.get("title")}


def tool_unknowns_list(args):
    p = resolve_project(args["project"])
    rows = []
    udir = p / "investigation.cany" / "unknowns"
    if udir.is_dir():
        for f in sorted(udir.glob("*.json")):
            u = load_json(f)
            if isinstance(u, dict):
                rows.append({"id": u.get("id"), "question": u.get("question"),
                             "severity": u.get("severity"), "status": u.get("status")})
    return {"project": p.name, "unknowns": rows}


def tool_render_dashboard(args):
    p = resolve_project(args["project"])
    status = tool_project_status({"project": p.name})
    html = build_dashboard_html(status)
    out = Path(args["out"]) if args.get("out") else p / "commander-dashboard.html"
    out.write_text(html, encoding="utf-8")
    return {"wrote": str(out)}


TOOL_SPECS = [
    {"name": "projects_list",
     "description": "List all Craft Anything projects with status and last note.",
     "inputSchema": {"type": "object", "properties": {}, "required": []}},
    {"name": "project_status",
     "description": "Live status of one build project: step, plan checklist, streamed agent text, tool-call success/fail, errors, last check similarity, feed freshness.",
     "inputSchema": {"type": "object", "properties": {
         "project": {"type": "string", "description": "project folder name under the Craft projects root"}},
         "required": ["project"]}},
    {"name": "pending_questions",
     "description": "Questions/approvals awaiting a human: inbox/*.request.json plus unanswered Ask items in the feed.",
     "inputSchema": {"type": "object", "properties": {
         "project": {"type": "string"}}, "required": ["project"]}},
    {"name": "answer_question",
     "description": "Answer an inbox request (writes <id>.answer.json exactly like the Craft app does). choice/text/allow mirror the Request schema.",
     "inputSchema": {"type": "object", "properties": {
         "project": {"type": "string"},
         "request_id": {"type": "string"},
         "choice": {"type": "string"},
         "text": {"type": "string"},
         "allow": {"type": "boolean"},
         "always": {"type": "boolean"}}, "required": ["project"]}},
    {"name": "unknowns_list",
     "description": "Open unknowns recorded for a project (investigation.cany/unknowns).",
     "inputSchema": {"type": "object", "properties": {
         "project": {"type": "string"}}, "required": ["project"]}},
    {"name": "render_dashboard",
     "description": "Write a self-contained HTML dashboard for a project's current status.",
     "inputSchema": {"type": "object", "properties": {
         "project": {"type": "string"},
         "out": {"type": "string", "description": "optional absolute output path"}},
         "required": ["project"]}},
]

TOOL_FUNCS = {"projects_list": tool_projects_list,
              "project_status": tool_project_status,
              "pending_questions": tool_pending_questions,
              "answer_question": tool_answer_question,
              "unknowns_list": tool_unknowns_list,
              "render_dashboard": tool_render_dashboard}


def build_dashboard_html(status):
    data = json.dumps(status, ensure_ascii=False).replace("</", "<\\/")
    plan = status["feed"]["plan"]
    plan_html = "".join(
        f"<li class='{'done' if s.get('status')=='done' else ('doing' if s.get('status')=='doing' else 'todo')}'>{esc(s.get('text',''))}</li>"
        for s in plan) or "<li class='todo'>(no plan yet)</li>"
    tools = status["feed"]["work_tools"]
    tools_html = "".join(
        f"<div class='chip'>{esc(k)} <b>{v['ok']}</b><span class='fail'>{v['fail']}</span></div>"
        for k, v in tools.items()) or "<em>none recorded</em>"
    errs = "".join(f"<div class='err'>{esc(e['message'])}</div>" for e in status["feed"]["recent_errors"])
    age = status.get("feed_age_seconds")
    sim = status["feed"].get("last_check") or {}
    return f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8"><meta http-equiv="refresh" content="10">
<title>anything-copy · {esc(status['project'])}</title>
<style>
body{{font-family:system-ui,'Segoe UI',sans-serif;background:#111418;color:#e6edf3;margin:24px}}
h1{{font-size:20px}} .pill{{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;background:#1f6feb;color:#fff}}
.pill.ready{{background:#238636}} .pill.stopped,.pill.paused{{background:#8b802e}}
.card{{background:#1b2026;border:1px solid #2d333b;border-radius:10px;padding:14px;margin:12px 0}}
li{{margin:4px 0}} .done{{color:#3fb950;text-decoration:line-through}} .doing{{color:#d29922}} .todo{{color:#8b949e}}
.chip{{display:inline-block;background:#21262d;border-radius:6px;padding:3px 8px;margin:3px;font-size:13px}}
.chip .fail{{color:#f85149;margin-left:6px}}
.err{{color:#f85149;font-size:13px;margin:4px 0}}
.agent{{white-space:pre-wrap;font-size:13px;color:#c9d1d9}}
.meta{{color:#8b949e;font-size:12px}}
</style></head><body>
<h1>{esc(status['project'])} <span class="pill {esc(status['status'] or '')}">{esc(status['status'] or '?')}</span></h1>
<div class="meta">step: {esc(str(plan and status['feed']['current_step'] or ''))} · feed updated {('%.0f s ago' % age) if age is not None else 'n/a'} · last check similarity {sim.get('similarity','—')} · app files {status['app_files']} · open unknowns {status['unknown_open']} · work {(status['usage'].get('work_ms') or 0)/3600000:.1f} h</div>
<div class="card"><b>计划（构建助手自查清单）</b><ul>{plan_html}</ul></div>
<div class="card"><b>工具调用统计</b><br>{tools_html}</div>
{f'<div class="card"><b>近期错误</b>{errs}</div>' if errs else ''}
<div class="card"><b>builder 最新语句</b><div class="agent">{esc(status['feed'].get('last_agent') or '（无流式文本——AgentCli 模式下属正常）')}</div></div>
<div class="card"><b>最近总结 last_reply</b><div class="agent">{esc(status.get('last_reply') or '')}</div></div>
<script>window.__STATUS__={data};</script>
</body></html>"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- MCP plumbing
def send(msg):
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def reply(rid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": rid}
    if error:
        msg["error"] = error
    else:
        msg["result"] = result
    send(msg)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        method, rid, params = req.get("method"), req.get("id"), req.get("params") or {}
        if method == "initialize":
            reply(rid, {"protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}})
        elif method in ("notifications/initialized", "initialized"):
            continue
        elif method == "tools/list":
            reply(rid, {"tools": TOOL_SPECS})
        elif method == "tools/call":
            name = params.get("name")
            fn = TOOL_FUNCS.get(name)
            if fn is None:
                reply(rid, error={"code": -32601, "message": f"unknown tool {name}"})
                continue
            try:
                out = fn(params.get("arguments") or {})
                reply(rid, {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]})
            except Exception as exc:  # surface as tool error, keep server alive
                reply(rid, {"content": [{"type": "text",
                                         "text": json.dumps({"error": str(exc)})}], "isError": True})
        elif method == "ping":
            reply(rid, {})
        elif rid is not None:
            reply(rid, error={"code": -32601, "message": f"unsupported method {method}"})


if __name__ == "__main__":
    sys.stderr.write(f"{SERVER_NAME} {SERVER_VERSION} — MCP stdio server; projects root: {projects_root()}\n")
    main()
