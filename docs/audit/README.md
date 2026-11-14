# 审计与改动记录（docs/audit）

本目录收录 Anything Copy 代码库的完整审计与改动轨迹（基线 commit `adeddc9`，2026-11-11）。

| 文件 | 内容 |
|---|---|
| `batch1a-adapters-core.md` | 适配器层逐行审计：hermes/claude/codex/opencode 的传输、授权、ACP 面 |
| `batch1b-rebuild-core.md` | 构建环审计：重试策略、失败分型、僵尸施工队根因、无进展判定 |
| `batch1c-platform.md` | 平台层审计：进程包裹（Job Object）、取消、文件落盘、DLL 搜索面 |
| `FIX-PLAN-v1.md` | 11 项修复台账（P0/P1/P2），含事故日期、锚点、验收条件 |
| `rebrand-v01-blueprint.md` | 换牌批施工蓝图（供代理照图施工，防探索式浪费与限流） |
| `rebrand-v01.md` | 换牌批执行报告（改动清单、刻意不改的机器名 backlog、风险） |
| `HANDOFF-2026-11-13.md` | 交接书：版本状态、验证矩阵、CLI 用法、环境陷阱、待决事项 |
| `salvaged-*.md` | 中途被限流打断的审计运行的残卷（供追溯） |

已落地的修复对应 commit 见主 README「这个 fork 修了什么」一节；每处修复均有对应测试锁定（`craft-anything-ai` 566 项、`craft-anything-ui-egui` 220 项）。
