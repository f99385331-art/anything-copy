# Anything Copy

**Watch and steer [Craft Anything](https://github.com/storytold/craft-anything) build projects from any AI agent — zero dependencies, one Python file.**

Craft Anything runs its builder turns silently: the UI can sit on "Asking Hermes Agent…" for 30+ minutes, a pause button may leave a detached turn burning quota, and 429 quota errors arrive dressed as "billing exhausted". `anything-copy` is an **MCP stdio server** that reads a project's on-disk contract (`craft.json`, `feed.json`, `usage.json`, `inbox/`, `investigation.cany/`) and gives any MCP-speaking agent (Hermes, Claude Code, opencode, Codex, Goose, …) six live-ops tools:

| tool | what it answers |
|---|---|
| `projects_list` | which projects exist, their status and last note |
| `project_status` | current step, the builder's plan checklist, streamed words, per-tool success/fail counts, recent errors, last check similarity, **feed freshness in seconds** |
| `pending_questions` | questions/approvals waiting for a human (inbox + unanswered feed asks) |
| `answer_question` | answer one, writing `<id>.answer.json` exactly like the Craft app does |
| `unknowns_list` | open unknowns recorded during the study phase |
| `render_dashboard` | write a self-contained HTML dashboard that auto-refreshes |

Pure Python 3.9+ stdlib. No pip. Windows / macOS / Linux.

## Quick start

```bash
# sanity check against a real project
python server.py            # speaks MCP on stdio; it will just wait quietly
```

Attach it to your agent:

**Hermes Agent** (`config.yaml`):
```yaml
mcp_servers:
  anything-copy:
    command: python
    args: ["path/to/anything-copy/server.py"]
```

**Claude Code**:
```bash
claude mcp add anything-copy -- python /path/to/anything-copy/server.py
```

**Generic MCP client**: stdio transport, newline-delimited JSON-RPC 2.0.

Then ask your agent: *"what's the status of my havwoods-com build?"* or *"answer the pending approval with allow=true always=true"*.

## Configuration

The projects root defaults to `~/Documents/Craft Anything`. Override with:

```bash
set CRAFT_PROJECTS_DIR=D:\Craft Projects   # Windows
export CRAFT_PROJECTS_DIR=/data/craft      # unix
```

## Safety model

- Read-only filesystem access to your Craft projects **except** `answer_question`, which writes exactly one answer file the way the Craft app does.
- Refuses to escape the projects root (`..` traversal guard).
- Runs fully locally; no network access.

## Compatibility notes

- Validated against Craft Anything **0.5.0** workspaces (feed.json v5, craft.json v2 written by the app while repo HEAD is v5 — the reader is tolerant of missing/new keys).
- Whole-feed rewrites happen ≤ every 2 s while a build runs; a fresh feed file within seconds means the builder is alive. `feed_age_seconds` is the single best "is it stuck or just silent" signal.

## Why not just read the files myself?

You can! The full field-by-field contract lives in [`docs/DATA-CONTRACT.md`](docs/DATA-CONTRACT.md). `anything-copy` just folds the noisy event list into decisions, guards the paths, and speaks MCP so agents can act.

## Roadmap

- [ ] `watch` long-poll tool (push instead of poll)
- [ ] zombie-turn detection heuristics (feed silent + agent.log still calling) surfaced in `project_status`
- [ ] `approve_all_pending` convenience + audit trail
- [ ] a WASM `checks` plugin for Craft's own plugin API (classroom-grade visual checks)

## License & credits

MIT (see `LICENSE`). `anything-copy` is an independent companion tool; it works **with** [Craft Anything](https://github.com/storytold/craft-anything) by the ArtCraft team but is not affiliated with or endorsed by them. Craft Anything and ArtCraft are names of their respective project/team; this repository uses them only to describe compatibility, and ships none of their trademarks, logos, or brand assets.

---

## 中文速览

`anything-copy` 是一个零依赖的单文件 MCP 服务器，把 Craft Anything 构建项目的工作区文件（`feed.json` 等）折成 6 个实时运维工具，供任何支持 MCP 的 agent（Hermes / Claude Code / opencode…）直接调用：查状态、看计划清单、统计工具失败、回答待批准问题、导出自动刷新看板。判断"是真卡住还是在闷头干活"只看一个字段：`feed_age_seconds`。默认项目根目录 `~/Documents/Craft Anything`，可用环境变量 `CRAFT_PROJECTS_DIR` 覆盖。MIT 许可，独立项目，与 ArtCraft 团队无隶属关系。
