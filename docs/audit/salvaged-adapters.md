# 抢救残卷 · cli_agents 适配层

> 来源 transcript：task-0.log。审计子代理被 429 击杀前的残留。

## 叙述性发现

**23:02:10 [assistant]** I'll start by mapping the target directory and checking its size so I can plan the read passes.
**23:02:19 [assistant]** Terminal channel is behaving oddly, as warned. Switching to Python subprocess for shell work.
**23:02:51 [assistant]** 16 files / 9,782 lines. I'll read them all, taking notes per file so findings are captured incrementally. Starting with the small adapter files.
**23:03:32 [assistant]** Good — several concrete issues already. Next batch of adapter files.
**23:07:15 [assistant]** adapters.rs is the core trait/registry — reading it in full next, plus the trait's argument builder.
**23:11:41 [assistant]** Now the core module (spawn/argv/stream plumbing) plus the remaining adapters.
**23:15:31 [assistant]** Key lead: `run_session` — the #1115 cleanup trigger — appears to be set by only one adapter. Verifying against the platform line-reader and the remaining adapters.
**23:17:47 [assistant]** Let me build the capability matrix programmatically (accuracy for the consistency section), then read acp.rs.
**23:18:35 [assistant]** Production code boundaries are now known. Reading acp.rs (the ACP transport + approval flow) in full.
**23:27:29 [final]** status=failed duration=1535.37s summary: Billing or credits exhausted: HTTP 429: Allocated quota exceeded, please increase your quota limit. For details, see: https://www.alibabacloud.com/help/en/model-studio/error-code#token-limit Alibaba Token Plan Cn reported that billing, credits, or account entitlement is exhausted for qwen3.8-flash. Add credits or update billing with that provider, then retry. You can switch providers temporarily w …(+41 chars)
**23:36:25 [final]** end status=failed exit_reason=error error: HTTP 429: Allocated quota exceeded, please increase your quota limit. For details, see: https://www.alibabacloud.com/help/en/model-studio/error-code#token-limit

## 读过的文件（覆盖度证据）

- `hermes.rs`
- `devin.rs`
- `maki.rs`
- `shared.rs`
- `copilot.rs`
- `dsh.rs`
- `antigravity.rs`
- `unfinished.rs`
- `adapters.rs`
- `adapters.rs L701`
- `mod.rs`
- `mod.rs L801-1600`
- `process.rs L670-699`
- `opencode.rs`
- `grok.rs`
- `aider.rs`
- `acp.rs`
- `acp.rs L531-1035`
- `models.rs`
- `claude_cost.rs`
- `ssh.rs`
- `failure.rs`
- `process.rs L180-399`
- `process.rs L560-739`