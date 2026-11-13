# AGENTS.md — how to operate anything-copy from an agent

This repo is a tool **for agents**. If you are an AI agent reading this:

## Mission
Monitor and steer "Craft Anything" rebuild projects via the MCP tools in `server.py`.
The single most important judgement you can make for a user:

> **Is the build stuck, or just silent?**
> Call `project_status` and look at `feed_age_seconds`:
> - `<= 5`: the builder is actively emitting events. It is NOT stuck, regardless of what the UI says.
> - `5–120`: between writes (writes are throttled to ~2 s, and some steps are long). Usually fine.
> - `> 600`: possibly stuck or the turn ended. Check `feed.recent_errors`, `status`, `paused`.

## Tool call recipes
- Morning check: `projects_list` → for each `status: building`: `project_status`.
- User asks to "continue/answer/approve": `pending_questions` → `answer_question`
  with `request_id` from the pending list; approvals use `allow: true`
  (`always: true` only when the user explicitly says "always allow").
- User wants a report: `render_dashboard` (self-contained HTML, 10 s auto-refresh).

## Data you can rely on
`feed.json` items are an event list: `Step` / `Plan` (updated in place) /
`Agent` (streamed text) / `Work` (tool chips) / `Check` (similarity) / `Ask` /
`Error` / `"Paused"`. `craft.json` carries the manifest (`status`, `note`,
`last_reply`, `checks`). Never append to these files — they are atomically
rewritten by the app; the only safe external write is an inbox answer file.
Full contract: `docs/DATA-CONTRACT.md`.

## Do NOT
- Do not edit `investigation.cany/` evidence records (content-hash verified).
- Do not touch `inbox/build-progress.json` (a broken record stops builds).
- Do not kill processes or edit config files — this tool is file-level only.

## Self-test
`python selftest.py` runs the whole tool surface against `examples/sample-project/`
(sanitized real data) and prints folded status. All six tools must return without error.
