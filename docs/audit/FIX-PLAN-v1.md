# Anything Copy · 修复总清单 v1（合成自 batch1a/1b/1c 审计 + 2026-11-10/11 实战事故）

> **进度（2026-11-12 深夜）**：分支 `anything-copy` 上已完成第一刀全部四件——
> #1 argv 预检(524de53) · #2 429 分型止血(219418f) · #4 hermes 切 ACP(edc6731) · #5 磁盘租约(a3931a5)。
> 全绿：548 单测 + 16 集成 + 工作区 check；ACP 的 model/reasoning_effort configOption id 经真机实测。
> 剩余：#3 崩溃兜底 #6 指纹扫尾 #7 预算熔断 + P2(#8-11)。


基线：上游 craft-anything @ adeddca · cargo check 全绿。人日为纯手工估算，AI 辅助可大幅压缩。

## P0 止血（用户必感知）

| # | 修复 | 依据（file:line） | 人日 | 归属 |
|---|---|---|---|---|
| 1 | **argv 总长预检**：build_args 后、spawn 前查 CreateProcessW 32,767 UTF-16 上限（preamble≈2.6K + SSH shell_quote 放大留余量），超限报清晰 TurnFailure 而非 os error 206 | 1a: hermes.rs:15-23→mod.rs:351/997/1023→process.rs:298；#402/#528 自证 | 0.5-1 | Craft |
| 2 | **429 分型止血**：CLI 输出短语分类（codex 先例 adapters.rs:898）→ RateLimited/Billing + retry_after；盲重试环只重 RateLimited，Billing 即停并明示 | 1b: failure.rs:37/89, rebuild/mod.rs:1286 | 1-2 | Craft |
| 3 | **Windows 崩溃兜底**（事实校正产物）：process-wrap std 后端 kill_on_drop=**false**，Craft 崩溃时 job 内全族存活；唯一兜底 end_with_this_process 仅 Unix（lib.rs:89-91，注释是假保证）。补 assign_kill_on_close 或 PID 心跳清单 | 1c: std/job_object.rs:106, process.rs:843/936-953, lib.rs:80 | 4-6 | Craft |

## P1 核心体验（今晚三大痛点的手术刀）

| # | 修复 | 依据 | 人日 | 归属 |
|---|---|---|---|---|
| 4 | **hermes 切 ACP 三件套**：①hermes.rs 加 requires_acp()=true ②grants.rs:79 行改 Acp/Yes/Yes/No ③模型走 acp_session_config()（真机已证 hermes acp 无启动期 -m；ACP_MODEL_FLAGS 方案作废）④initialize/configOptions 实测门已过一半（acp --check OK） | 1a 问题①清单；真机 2026-11-11 | 2-3+1 实测 | Craft + Hermes 侧确认 |
| 5 | **磁盘租约防双 builder**：run 起始按项目指纹+generation 上锁（unfinished.rs:55-79 模式上提为 platform::lease）；"继续"拿不到活体持有即拒——根治 11-10 双施工队事故 | 1b: runs.rs:97（去重仅进程内存）; 1c: 零 LockFileEx 导出 | 3-4 | Craft |
| 6 | **CommandLine 指纹扫尾**：暂停/停止时按项目指纹（`-z <preamble头段>` 匹配）powershell CIM 扫外部会话，复用 END_TREE 模板（capture.rs:338-344，含 CreationDate 防 PID 复用）——覆盖 hermes gateway 类"借住别人家"的 turn | 1c ②b（全仓 0 处读 CommandLine，6 个可复用件） | 2-3 | Craft |
| 7 | **跨 run 预算熔断**：累计 turn/API-call 上限（现状最坏 32 个完整会话；turn 级 429 死亡不进失败计数器=口径漏洞），到限停下来向人请示 | 1b 问题② + failure 口径分析 | 1 | Craft |

## P2 健壮与安全

| # | 修复 | 依据 | 人日 |
|---|---|---|---|
| 8 | **CWD 幻影 exe 劫持封堵**：launch_target 未命中裸名回退交 CreateProcess 的缝隙 + 子进程 cwd=不可信工作区而无 SetDefaultDllDirectories（DLL 搜索第 5 位可命中项目根伪造品）——Deep 模式克隆恶意站点时是真攻击面 | 1c ③（which.rs:59 一带） | 1 |
| 9 | **fsync 补全**：12 处 save 无目录 fsync；backup_once"首备份不可变"可被掉电静默破；unfinished tries 重写缺 sync | 1c ④（fs.rs:152-166 等） | 1-2 |
| 10 | **崩溃一致性**：feed.json append-safe（外部 Ask.answer 回盘窗口）+ craft.json 跨进程锁 + awaiting_check 对账 + v2→v5 迁移不再静默 mark capture_deep（净室旧项目免被迫重 Study） | 1b 问题③（ai/feed.rs:163-171, mod.rs:947） | 2-3 |
| 11 | **grants 纪律**：保持"代码先行再翻行"（表=申报+回归门，零运行时消费者）；能力矩阵如需展示走 grants::table() 并标注申报性质 | 1a 问题③ | 0.5 |

合计 ≈ **19-28 人日**；P0+P1 ≈ 13-18。

## 发行建议（Anything Copy v0.1 给朋友的第一版）

第一刀 = **#1 #2 #4 #5**（全解"假死/429/僵尸/双施工队"四件套，恰好都是朋友必遇到的）→ 换牌（显示名/图标/bundle id/删 brand 目录，一次性批量 commit）→ `cargo build --release` → 便携 zip + 无签名 SmartScreen 提示 → 仓库 anything-copy-app（public，MIT+NOTICE 齐）。
#3 #6 #7 第二刀；P2 按审计余温排后。
上游双线：#1 #2 #7 #8 #9 适合直接 PR 给 ArtCraft（不撞车、他们活跃期）；#4 若先做可抢 R2.2 open lane。

## 遗留待审（体检未完成部分）

engine 61K 行（工具面/审批强制点）、ui-egui 23K、mcp+evidence 2.5K（哈希链已核过一部分）、formats 71K（抽查即可）、js/disasm/analysis 23K、apps/*。1c 报告 141 行/97 锚点，见 reports 目录。
