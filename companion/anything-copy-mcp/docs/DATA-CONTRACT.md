# The Craft Anything workspace data contract (observed, 0.5.0)

Everything below was learned by reading a real project directory and its
companion application behaviour; it is a clean-room description of file shapes
only, written for interop. Files live under `<Documents>/Craft Anything/<project>/`.

## General rules observed
- Every JSON carries a `version` integer. The app migrates older files forward and refuses to downgrade newer ones — external readers should treat unknown versions as "newest known" and every missing key as optional.
- Writes are atomic (temp + rename). `feed.json` is rewritten wholesale at most about every 2 seconds during a run, plus immediately at finish. **Do not append to these files.**

## craft.json — project manifest
Key fields (type): `name`,`request` (str), `target` ({kind: website|local|none, url? path?}),
`stack` (str), `status` (`new|inspecting|building|checking|needs_you|ready|stopped`),
`note` (str), `created_ms`/`updated_ms` (epoch ms), `checks` (array of CheckResult),
`agent_session`/`agent_session_by` (builder CLI session handle + which agent),
`allowed_actions` (str[], e.g. `bash:npm`), `last_reply` (str — the builder's plain-words
summary), `asset_budget_usd`, `generate_assets`, `questions` (`ask|decide`),
`approvals` (map of action-kind → `allow|ask|refuse`).
The installed 0.5.0 app writes manifest version 2; the upstream repo's current schema is v5
(added `approvals`, session-deep flags). Read with defaults; edit only person-owned fields
between runs: `request`, `questions`, `approvals`, `allowed_actions`, budget flags.

## feed.json — the live event stream (the important one)
`{"version": 5, "items": [...] }`. Each item is one of:
- `{"Step": {"step": "study|build|check|done", "text": …}}`
- `{"Plan": [{"text":…,"doing":…,"status":"todo|doing|done|stopped"}]}` — the builder's checklist, replaced in place
- `{"Agent": {"text":…,"streaming": bool}}` — streamed builder words (may be absent in one-shot CLI mode)
- `{"Work": {"tools": [["name", true|false|null]], "notes": [...]}}` — collapsed tool-call runs; `false` = that call errored
- `{"Check": CheckResult}` — `CheckResult` ≈ `{round, check, passed, similarity (0-100), note, artifacts, pages:[{name,dir,similarity}], claims:[{title,passed}]}`
- `{"Ask": {"request": …, "answer": null|…}}` — unanswered = pending question
- `{"Error": {"message","remediation","log"}}`
- `{"User": …}` — what the person typed
- bare strings `"Paused"` and `"PlanDismissed"`

`feed_age_seconds` (now − feed.json mtime) is the most reliable liveness signal:
a fresh file means events are flowing even when the app UI looks frozen.

## usage.json
`{version, work_ms, input_tokens, output_tokens, cost_usd, api_billed_usd, priced}` — run-owned, read-only for us.

## inbox/ — the cross-process question channel
- `<id>.request.json`: `{id, kind: "question"|"approval", title, detail, choices:[str], allow_text, action, created_ms}` — written when the builder asks.
- `<id>.answer.json`: `{choice, text, allow, always}` — this is the one external write that is safe; the app picks answers up.
- `build-progress.json`: fingerprint bookkeeping, **never touch** — a corrupted record halts builds.

## investigation.cany/ — the evidence store
- `evidence/<2-hex-shard>/<id>.json`: records whose `id` is a SHA-256 of the canonical (key-sorted) JSON of the record itself; reads re-verify. Forged edits fail loudly — treat as read-only audit.
- `unknowns/<id>.json`: `{id, revision, question, severity: low|medium|high|critical, domain, status: open|investigating|blocked|contradicted|resolved, probes[], evidence_for[], evidence_against[], resolution}` — parsed leniently; new well-formed files are accepted.
- `journal/<date>.jsonl`: append-only tool-call audit trail.

## capture/ and checks/
`capture/` holds the study evidence (README digest, capture.json design/layout tokens,
screenshots per width, per-route copies) and `checks/round-N/` per-round comparisons.
Both are treated as immutable evidence by the builder; read freely, write never.
