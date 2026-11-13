# 抢救残卷 · rebuild 状态机

> 来源 transcript：task-1.log。审计子代理被 429 击杀前的残留。

## 叙述性发现

**23:02:43 [assistant]** 终端通道确实故障，改用 Python subprocess。先统计文件规模：
**23:17:31 [assistant]** 读取剩余 rebuild 模块（study/brief/notes/stacks/locate/project/stand_in/output）：
**23:19:54 [assistant]** 读顶层核心：http.rs、context.rs、model.rs：
**23:21:16 [assistant]** 转向定点核查：write_atomic 原子性、ProjectUsage 双写、allowed_actions 旁路、版本迁移：
**23:33:08 [final]** status=failed duration=1874.46s summary: Billing or credits exhausted: HTTP 429: Allocated quota exceeded, please increase your quota limit. For details, see: https://www.alibabacloud.com/help/en/model-studio/error-code#token-limit Alibaba Token Plan Cn reported that billing, credits, or account entitlement is exhausted for qwen3.8-flash. Add credits or update billing with that provider, then retry. You can switch providers temporarily w …(+41 chars)
**23:36:25 [final]** end status=failed exit_reason=error error: HTTP 429: Allocated quota exceeded, please increase your quota limit. For details, see: https://www.alibabacloud.com/help/en/model-studio/error-code#token-limit

## 读过的文件（覆盖度证据）

- `mod.rs`
- `feed.rs`
- `activity.rs`
- `runs.rs`
- `kept_check.rs`
- `failure.rs`
- `check.rs`
- `self_check.rs`
- `tools.rs`
- `question.rs`
- `study.rs`
- `notes.rs`
- `locate.rs`
- `project.rs`
- `brief.rs`
- `stacks.rs`
- `output.rs`
- `http.rs`
- `context.rs`
- `agent.rs`
- `website.rs`
- `screenshot.rs`
- `game.rs`
- `self_test.rs`
- `app.rs`
- `own.rs`
- `mechanics.rs`
- `plugin_check.rs`
- `stand_in.rs`
- `lib.rs`
- `lib.rs L701`
- `model.rs`
- `failure_log.rs`
- `config.rs`
- `keys.rs`
- `openai.rs L255-419`
- `anthropic.rs`
- `pace.rs`
- `price.rs`
- `providers.rs`