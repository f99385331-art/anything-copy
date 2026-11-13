# batch1b · rebuild 状态机与失败处理审计

> 仓：`C:\Users\Murphy\projects\craft-anything-src`（上游 adeddca）。范围：`crates/ai/src/rebuild/` 全部文件 + `crates/ai/src/failure.rs` + `model.rs` 取消语义段。旁证最小外扩：`engine/src/feed.rs`（版本/load/save 是 Q3 必答对象）、`engine/src/tools/interaction_tools.rs`（Q4 许可链）、`platform/src/cancel.rs`、`ui-egui/src/project.rs`（Q1 入口），均为定点核对。
> 残卷 salvaged-rebuild.md 仅有覆盖度清单，无正文结论，本报告从零重建。
> 行号均为工作区文件实测行号。

## 文件清单（先 dir 后定序）

rebuild/：mod.rs 1604 · feed.rs 293 · activity.rs 551 · brief.rs 425 · check.rs 510 · kept_check.rs 80 · locate.rs 149 · notes.rs 213 · note_progress_tests.rs 287 · output.rs 4 · project.rs 108 · question.rs 510 · runs.rs 457 · self_check.rs 304 · stacks.rs 298 · stall_tests.rs 178 · stand_in.rs 102 · study.rs 376 · tests.rs 4428 · tools.rs 839 · kinds/（website/game/app 等）。顶层：failure.rs 178 · model.rs 275。

---

## ① 取消/暂停的完整路径

### 置位链（谁按下第一颗旗）

1. **UI 暂停键** → `ui-egui/src/project.rs:266 pause()` → `RunSet::stop(&root)`（project.rs:268）。
2. **RunSet::stop**（`rebuild/runs.rs:196-208`）：排队中 → 从 queue 移除、返回 `Stopped::Unqueued`（UI 侧立即本地贴 Paused 卡，project.rs:269）；运行中 → `run.stop()`、返回 `Stopped::Stopping`（UI 记入 `pausing` 集合等事件，project.rs:271）。
3. **RebuildRun::stop**（`rebuild/mod.rs:465-467`）→ `CancelToken::cancel()`（`platform/src/cancel.rs:13-15`，`Arc<AtomicBool>` 电平置位，**无 reset，单向闩锁**）。`RebuildRun` 被 drop 时同样 cancel（mod.rs:508-512），关窗即隐式暂停。
4. 取消是**协作式**的：worker 线程只在固定检查点看到它——`step()`（mod.rs:648）、`call()`（655）、重试等待 `wait_for`（1233-1239，逐秒 check）、`progress_fingerprint`（1133）、`converse_turn` 的 TurnDone 出口（1368）、`run_outcome`。model.rs 侧对称物证：`Stop{stopped: Arc<AtomicBool>, tool: Option<CancelToken>}`（model.rs:239-242），`is_stopped = 会话旗 ∨ 工具旗`（261-263），`check()` 抛 `ToolError::cancelled()`（265-267）；`ChatModel::turn` 拿 `&Stop` 自行轮询（272）。**HTTP 请求不被抢占中断，只在轮询点断**（API 后端一次调用最长可跑满其自身超时才响应暂停）。

### builder turn 如何收尾

- 泵循环 `converse_turn`（mod.rs:1318-1385）：每 120ms 一圈；圈首 `if self.stop.is_cancelled() { agent.stop(); }`（1327-1329）——**每圈重复调 stop()**，直至 agent 报出 `TurnDone`。
- 对 CLI agent：`agent.stop()` 杀的是 Craft 亲手 spawn 的进程树（Job Object kill-on-drop 只覆盖 Craft 的子进程，见 batch1a `platform/process.rs:306`）；进程死亡→适配器的 poll 读到 EOF→吐 TurnDone/Error→泵循环 1368 处 `stop.check()?` 抛 Cancelled。
- 出错收尾路径 `run()`（mod.rs:970-986）：`agent.stop(); drop(agent);` 保留原始错误返回。
- 终局 `run_outcome`（**mod.rs:1447-1465**）：`Err(Cancelled)` → **`ws.set_status(Status::Stopped, "Paused. Send a message to continue.")`（mod.rs:1451）** 落 craft.json；返回 `(false, "Paused.", paused=true)` → 线程尾 `ctx.emit(Finished{paused:true})`（365）→ **feed.rs:91 `FeedItem::Paused`** 入 feed.json（`save(true)` 立即写盘，feed.rs:142/159-176）；同时把 Plan 卡上 Doing 步骤改 Stopped（feed.rs:81-87，#504）。

### 若 agent 进程实际没死（外部网关）——continue 会发生什么

**会。两个 turn 并发同一工作区，且 Craft 无任何围栏。**

- "continue" 按钮：`continue_build()`（project.rs:255-264）置 **`continuing: true`**（262），新 run 进同一 `RunSet`。
- `RunSet::start` 防重入只看**本进程内存**：`is_running(root) || position(root)`（runs.rs:97-101）。而上一 run 已发 Finished、`running=false`（mod.rs:366），队列/映射去重瞬间失效——新 run 堂而皇之开跑。
- `BuildingHere`（self_check.rs:36-57）只是**进程内静态 Vec**，不是文件锁，跨进程/跨 run 都不设防。
- 新 run 的续作路径：`is_carrying_on`（mod.rs:220-222）→ 不重做 Study（starts_with_study，245-247）→ `agent_spec.resume = manifest.agent_session_for_mode(...)`（mod.rs:777）→ `restore_session`（1220-1228）→ prompt 走 `continue_prompt`（911）→ 适配器带 **同一 session id** 续会话。hermes 场景：session id 指向网关里的 turn；网关 turn 是僵尸（暂停只杀了 stub 客户端，turn 本体在 gateway 线程继续烧 API——今晚实证），于是**同一 session、同一 app/ 目录、两个并发 turn**：僵尸按旧上下文写文件，新 turn 按 CONTINUE 语义"看 app/ 现状继续"，互相踩、双份烧配额。
- 根因定性：Craft 把"进程树已死"当作"turn 已停"的**代理信号**（converse_turn:1327 的 agent.stop() 即全部分手动作），对外部 host（hermes 网关、`--resume` 到远端 session）没有**执行代次（generation）/租约**概念——代码里没有可传入的 turn 身份，`remember_session`（1243-1247）只存 id 字符串，无 owner/generation 校验。
- 缓解现状：`wait_for_approval`/inbox wait 都用 `stop.is_cancelled()` 轮询（mod.rs:740），**Ask 卡在暂停时会得到 STOPPED_ANSWER**（self_check.rs:176-183），僵尸 builder 若在等检查也会被 answer_self_checks 的 Cancelled 分支喂 "stopped"——但这全部要求僵尸进程回头读 Craft 的 inbox；网关 turn 不回头，就完全失联。

## ② 重试环与预算

### TurnFailure::retryable 的分类边界（failure.rs）

- `retryable() = matches!(Transient | RateLimited)`（**failure.rs:37-39**）；Authentication/Billing/MissingProgram/ToolsUnavailable/Configuration/Unknown 一律不重试。
- API 分类器 `from_api`（41-64）：先看 `context_overflow→Configuration`（44-47，防超长上下文反复送死——正是 23 万 token 场景的护栏）；401/403、`authentication_error/permission_error/invalid_api_key`→Authentication（48）；**402、`billing_error/insufficient_quota`→Billing（49）**；**429、`rate_limit_error/rate_limit_exceeded`→RateLimited（50）**；408/5xx/`overloaded/api_error`→Transient（51）；其余 4xx→Configuration（52）。
- **致命边界（昨晚烧穿的机关）**：`process_exit(code)`（**failure.rs:89-91**）——**任意非零退出、包括退出码 None（连接丢）都定级 Transient→retryable**，测试 169-171 明确锁死 `Some(1)/Some(255)` 必须可重试。429 若是"Allocated quota exceeded"类中文/自定义 body、status 缺失（如 hermes 客户端退出码 2 报 429 字样），走 process_exit → Transient → 盲重试。只有 provider 明确给 402/`insufficient_quota` 才判死为 Billing 不重试。
- 等待时长：typed `retry_after_secs`（clamp 1..=900，failure.rs:62）或消息文本兼容层 `retry_after()`（97-116，"retry in Ns/minutes/hours"，同样封顶 MAX_RETRY_WAIT=900，failure.rs:28）；两者皆无则**线性 30s×tries**（mod.rs:1300）。

### CONTINUE_TURN 重试发几轮

- `turn_with_wait`（**mod.rs:1251-1310**）：`tries < 3`（1286）→ **每个逻辑 turn 最多 1+3=4 次尝试**；重试发送用 `retry=true`→`agent.retry(text)`（1319-1320）→ 默认实现（lib.rs:340-343）**有 session 即改发 CONTINUE_TURN**（failure.rs:29-30 "look at what's already in app/..."），无 session 才重发原文。
- session lost 分支（mod.rs:1266-1273, 1273-1282）：换 fresh prompt 重来一次，**不计入 tries**，但 `fresh.take()` 保证每 turn 只一次。
- 外层轮次环 `run()`（mod.rs:948-1085）每轮调用 `turn()` 一次→ **每轮各有独立的全新 3 次重试预算**；检查 `checks_with_a_retry_now`（1184-1197）失败再跑一次 `run_checks`（**每轮检查恰好重试 1 次**）；builder 自调 `rebuild_check` 由 `answer_self_checks` 代跑（self_check.rs:149-193，限时长 SELF_CHECK_LIMIT=30min，self_check.rs:13）。

### 有无跨 run 的累计预算熔断——没有。最坏烧多少

**不存在任何 token/调用数/成本熔断**。usage.json 只记账不闸门：`record_usage`（mod.rs:627-640）累加 `work_ms/tokens/cost` 后**从不读取比较**；全仓 grep 仅有的"budget"是资产生成预算 `asset_budget_usd`（brief.rs:187，写进提示词劝告模型），与 API 调用无关。

现存的三个"类熔断"及其口径：

| 熔断 | 位置 | 口径 | 漏洞 |
|---|---|---|---|
| `not_working_checks` ≥10 | mod.rs:1041/1071/1470（#736） | 跨 run 持久于 craft.json，按"检查轮"计 | **只统计"检查跑完且未全过"**；turn 本身 429 死掉、检查根本没跑到 → 不计数 |
| `BuildProgress.unchanged_turns` ≥2 | mod.rs:953-955/1059-1068；engine workspace/progress.rs:141-142 | 按"turn 前后 app/ 指纹不变"计，跨 run 持久 | **每次带正文的新消息/便条 reset**（mod.rs:809-812, 1021, 1052；`progress_after_notes` 1114-1122）；重试环内的 4 次尝试只算"一个 turn"的指纹对 |
| `max_rounds=6` | mod.rs:165/1074 | 精修轮上限 | 只限精修，不限首轮/便条轮 |

最坏路径估算（单 run，纯 Craft 侧口径）：builder 会话数 ≤ `(1 首轮 + 6 精修 + N 便条轮 + 1 decompile 提醒) × 4 尝试` ≈ **32 个完整 headless 会话**（N 由人手便条驱动不设限，mod.rs:1019-1026 `continue` 不耗 rounds）。每个会话内部是 agent CLI 自己的多轮 API 循环（不受 rebuild 计数）——hermes 网关场景下"进程被杀但 turn 继续"意味着**这 32 个会话的配额上限只是名义值**：僵尸 turn 不计入任何计数器，而每轮 CONTINUE 的旧会话还在继续烧。跨 run：用户每点一次 "Try again"/发一条新消息就**重置全部局部预算**（936-943 只保护 `not_working` 与 `stalled` 两个文件计数），429-RateLimited 重试 3 次×等待≤900s 后仍失败→ run 报 NeedsYou → 用户再点 → 无限循环，唯一止损靠人的耐心。昨晚"新构建 10 秒被 429 弹死"正是：僵尸+4×3=12 次会话挤进同一配额窗口，`from_api` 把 429 判 RateLimited→重试→进一步压垮分钟配额。

---

## ③ feed/craft.json 写入时序与崩溃一致性

### 双文件两套节奏（先摆事实）

| 文件 | 写入者 | 节奏 | 原子性 |
|---|---|---|---|
| craft.json | worker 线程各处 `ws.save()/set_status`（如 step 内每次：mod.rs:649→workspace.rs:872-877；round 后 1008/1042） | **每个检查点即写，无限流** | write_atomic：临时文件+fsync+rename（platform/fs.rs:64-88），Windows 下 rename 被杀软/索引器占用时重试 20×100ms（fs.rs:123-134） |
| feed.json | 仅 `FeedLog::save`（ai/feed.rs:159-176，经 emit 锁内 record，mod.rs:567-573） | **节流 ≤2s**；Finished/push/answered 强制即写（feed.rs:142/151/156） | 同上 write_atomic（engine feed.rs:221 → project::write_atomic，整文件原子重写） |
| build-progress.json | `progress.save`（mod.rs:956/1016/1045 等） | 每 turn 前后 | 版本 2，>本 build 拒写（engine workspace/progress.rs:92-94） |
| usage.json | `ProjectUsage::update`（mod.rs:631） | TurnDone 及 60s 滴灌（USAGE_FLUSH mod.rs:564/1380-1382） | 进程内静态互斥锁 `USAGE_UPDATE`（workspace.rs:598-610）防 turn/question 双写互相覆盖 |

### 崩溃瞬间的不一致窗口

1. **craft.json 比 feed.json 新 ≤2s+**：`ws.save()`(mod.rs:1042) 与下一个节流 feed 写之间掉电/杀进程 → manifest.checks 有本轮结果、feed.json 缺 Check 事件；重启后 `FeedLog::open → load` 读到的是**存在但滞后**的文件——`history()` 回退（engine feed.rs:169-177）只在文件缺失/不可读/版本过新时触发，**不会**用 manifest 补齐已有 feed。表面损失，非致命。
2. **Plan 卡僵尸 Doing**：`Finished` 事件把 Doing→Stopped 的逻辑（feed.rs:81-87，#504）只走事件流；进程被外力杀（无 Finished）则 feed.json 永远留着 "Doing"，直到下一 run 的 TodoWrite 整体接管（feed.rs:27-40）。
3. **status=building 但无人构建**：`run_outcome` 的"不能把状态留在 Checking"防线（mod.rs:1444-1446 注释）只覆盖 panic/Cancelled/Err 正常退出；外部 kill -9 → craft.json 保持 `status: building`，靠 UI 侧 "This build stopped part-way"+Continue 卡识别（ui-egui/project.rs:1539-1549），**没有启动时全项目 status 修复**。
4. **awaiting_check 是刻意的对账旗**：turn 完成置 true（mod.rs:1007）→ 检查完成置 false（1038）；崩溃时 true ⇒ 下次 resume 直接 `only_check=true`（mod.rs:947-949）**跳过 builder 只补检查**——这是全模块唯一成体系的一致性设计。
5. **notes 三态**：`inbox/notes/` 下 pending/read 标记文件（notes.rs:19-23）；builder 钩子 claim 后、`relay_read_notes` 落 feed 前崩溃 → `take_left`（mod.rs:318-321 + notes.rs:75）把无人读过的 note 交给下一 run，`left_notes_are_a_request`（1426-1442）重置两个计数器——note 不丢但**会重放**（已被 hook 取走而未 forget 的会再进 feed 一次）。
6. **craft.json 跨进程并发无锁**：`Workspace::save` 读盘仅合并 person 字段（workspace.rs:840-846 + 739-746：budget/generate_assets/builder/allowed_actions/questions/approvals），**status/checks/agent_session 等机器字段 last-writer-wins**。两个 Craft 进程（app + CLI 双开）同 project 并发 run 时互相覆盖会话 id——正是①僵尸双 turn 的第二处放大。

### 版本不匹配实测（v2 盘 × v5 码，craft.json）

- `MANIFEST_VERSION=5`，迁移步 v0→v5 逐步编译期对齐（workspace.rs:82-87）。read_manifest（133-152）：无 version 字段=当 0 读；**≤5 则内存升级链跑到 5 并把 `version:5` 写回**（147-150）；任何 `ws.save/set_status` 即落盘 v5。测试锁死：v2 盘 open→version==5、save→磁盘 v5（workspace.rs:1709-1715）。
- v4→v5 语义实测（120-129）：**缺 `capture_deep` 一律补 `true`（当 Deep）**。后果：v2/v4 时代的 Clean-room 项目升级后被标记 Deep → `capture_in_mode`（mod.rs:227-229）对 Clean-room run 判不可用 → **强制重做 Study**（多烧一次调研调用），Deep 项目则无缝。
- 盘比码新（v99/6）：字段能认多少读多少、**version 保留**（131-132 注释；测试 1743-1751 若 from_value 失败则整文件拒读并报"made by a newer…"），随后 `is_read_only`（827-829）⇒ write_manifest 拒写（859-866）、feed `save` 见 `version>FEED_VERSION` 拒写（engine feed.rs:211-219）、usage 拒写（workspace.rs:612-614）、build-progress 拒写（progress.rs:92-94）——**读可降级、写全冻结**，无部分损坏路径。

### 外部写 Ask.answer 的合并点

**`crates/ai/src/rebuild/feed.rs:163-171`（`FeedLog::save` 内部）**：每次（节流放行后）全文件重写前，先 `Workspace::open` + `load` 重读磁盘 feed.json，把磁盘上带答案的 `FeedItem::Ask{answer:Some(a)}` 用 `engine::feed::answered()`（engine feed.rs:150-158，只填 `answer: None` 的第一条同 id 项）回放进内存再整写。除此之外**一切外部 append 都会在下一次 ≤2s 全文件重写中蒸发**（前提成立，代码无任何其他 merge 分支）。run 结束走 `RebuildRun::answer_as`（mod.rs:459-463：inbox.answer+feed.answered+save(true)）；无 run 时 UI 直写 `record_answer`（project.rs:285 → engine feed.rs:227-234）。注意 `answered` 只认内存里存在的同 id 项——外部先 append Ask 再写 answer 的项若不在 run 内存 feed 中（如外部自己 post 的卡），回盘 merge 只补 answer 不补 item，item 本体靠 load 时的 inbox pending 附加（engine feed.rs:184-185）兜底。

## ④ allowed_actions / approvals 的真正强制链

### grants 表确无运行时消费者

`cli_agents/grants.rs:113-132` 只在测试（217/239）里被调；全仓 grep `grants` 无生产调用点——与 hermes 侧核验一致（"申报+回归测试门，先改代码再翻行"）。**真正的许可执行链是三段：**

1. **策略函数**（engine 侧）：`decide(ws, tool, input)`（interaction_tools.rs:365-404）→ Allow/Deny/Ask{kind}。要点：Write/Edit 只有落进 app/∪checks/ 且非 own_record 才 Allow（376-392，链接穿越用 `really_inside`）；Bash 逐段过 `decide_command`（321-348：SAFE_COMMANDS 白名单 150+、`&&` 全段安全才放、含管道/分号/反引号/`$` 一律 Ask、dev-server 直接 Deny 329-333）；Read/Glob/Grep/LS/TodoWrite 无条件 Allow（375）。
2. **决策合成**：`approve_with → outcome()`（421-498）：先 clean-room `off_limits` 一票否决（431-433 + 506-529，跟随链接防软链穿透）；再 `Decision::Ask` 的按 **ActionKind 集合取最严**（477-487；kind→Approval{Allow/Ask/Refuse} 的项目级 `manifest.approvals` 覆盖 auto/manual 默认，workspace.rs:1208-1210）；`allowed_actions` 的**唯一消费者**在此——**interaction_tools.rs:490**：所有涉及 kind 都 `remembers_actions`（按动作记忆，如 `bash:npm`）且未被现行 Refuse 且 `manifest.allowed_actions.contains(action)` 才免卡放行（`cd git` 之前 allow 过不会连坐放行 push，489-491 注释）。写入点：卡片勾"always"时 `set_person` push（895-897）；`tool:<id>` 版在 mcp/lib.rs:583-584。**approvals（按 kind 整类）消费者**：477-479/899-901。
3. **builder 侧挂钩**（ai 侧，本范围）：
   - Claude Code 流：`converse_turn` 收 `ConsentNeeded` → **只有 Toolset==Build 的工具自动批准，其它一律拒**（mod.rs:1344-1347）——Build 工具内部再走 `approve()`（interaction_tools.rs:409-415）。即"builder 的许可 = Craft 引擎工具门"。
   - ACP 流：`Worker::approver`（mod.rs:726-745）把 session_permission 路由进同一个 `approve_with`（用项目 inbox + 本 run 的 stop 旗做 cancel 回调 740）。
   - MCP 工具服务器流（外部 agent 调 Craft 工具）：mcp/lib.rs:563-570 consent 检查。

**链条的洞（今晚实证的上半段）**：上述三段全部只管辖**经过 Craft 进程/工具服务器路由的动作**。AgentCli·hermes 适配器不挂 Craft MCP、也不发 ConsentNeeded（batch1a 锚点 `adapters/hermes.rs:15-23`，prompt 走 argv、`cx.mcp` 被忽略）——hermes 用它自带的 shell 在 app/ 里 `git push` 时，Craft 的 decide()/approvals/allowed_actions **一个字节都不参与**。简报层唯一约束是文案：`PRIVATE_USE_NOTE`（brief.rs:248，含 Original 文件时提示"must not be shared or published"）——纯提示词，无执行体。审批卡（ActionKind::Publish，workspace.rs:1111-1112）形同对哑巴 agent 虚设。

### questions=Decide 对核心问答的影响

- 开关：`manifest.questions: Option<Questions>`（workspace.rs:453-456；Ask/Decide 枚举 1090-1097），`Settings::questions_in(manifest)` 合成（项目覆盖全局默认）。
- 生效点唯一：**`core_person_ask`（interaction_tools.rs:104-105）**——Decide 时**卡都不发**，立刻返回 `{"answered":false, note:DECIDE_ANSWER}`；DECIDE_ANSWER（第 28 行）要求模型"下一条消息以 'I decided:' 开头自述选择与理由"。等待路径（111-119：post→wait 10min→超时 best judgement）整体旁路。
- **注意正交性**：`Questions::Decide` 不影响 `core_action_approve`/审批卡（那是 `manifest.approvals`/`allowed_actions` 的域）；也不影响便条、Just-ask。它与"审批链管不到 hermes"叠加才构成事故完整路径：builder 自决一切问题 + 它执行的命令本来就没有 Craft 门。
- Just-ask 问答（rebuild/question.rs:73-179）独立于 builder turn：fork 构建者 session（`resume: session`，104-117）或从文件回答（TheFiles，123-133）；claude-code 用 `kept_total` 差值法剥离 fork 成本（141-177，防 fork 报全会话总额虚账，实测 $22.67 教训写在 164-166 注释）；session lost 自动降级 TheFiles 重问一次（151-162）并 `forget_lost_session`（154）。**fork 与在跑的 build 共享同一 CLI session 是有意的并发面**（139-141 注释承认"build turn 可能同时推进同一 session"）——又一处双 turn 同会话，但仅限 claude-code 系（其 fork 语义安全），对 hermes 式网关无此保障。

---

## ⑤ 逐文件审计记录（发现编号 F-01…F-14）

| 文件 | 行数 | 深读/略读 | 结论与发现 |
|---|---|---|---|
| **mod.rs** | 1604 | 全量热点+骨架 | 状态机全貌见①②。F-01 重试预算每 turn 独立重置、无 run 级/跨 run 累计（1261-1264 局部 `tries`）。F-02 Cancelled 判定只认 `e.code`（1450），`run_outcome` 对 panic 一律 NeedsYou、不区分暂停竞态（1459-1463）。F-03 泵循环 120ms 忙等（1383），暂停响应最坏滞后 2 秒级但 `wait_for` 逐秒可断（1234-1237）。F-04 `agent.stop()` 在 1327-1329 每圈重复调用（幂等要求被隐式信任）。 |
| **feed.rs (ai)** | 293 | 全量 | F-05 节流窗口内（<2s）事件只进内存；崩溃即丢最后 <2s 事件（159-163），Finished 强制刷盘是唯一硬点（142）。回盘 merge 只回放 Ask.answer（163-171）——外部 append 必丢，实证前提。 |
| **activity.rs** | 551 | 核心全读（155-279）| Activity 纯内存+`last_ms` 原子（160-178）：`quiet_for` 无事件时基于 `began` 计算，**外部僵尸烧 API 不产生任何事件**——"X 分钟无新进展"对僵尸 turn 是假阴性信号，与①互证。日志行过 `journal::scrubbed_line`（199，密钥剥离，测试 496）；`ActivityFile` 追加式 + 超长轮转 `build-activity.old.log`（workspace.rs:591-593，测试 517）；写失败只说一次不杀 run（540）。 |
| **runs.rs** | 457 | 核心全读 | F-06 `RunSet` 去重/`alone` 互斥全在进程内存（37-47、97-101）；`keep_queue_moving` 线程独立拉队列（224-257），与 UI 主 poll 并发靠同一把 `Arc<Mutex<RunSet>>`。F-07 `Started` 失败路径给 `NeedsYou + Finished{paused:false}`（139-143），排队 run 起不来不重试。`stopped` 语义（196-208）已在①。 |
| **kept_check.rs** | 80 | 全量 | 指纹相等则复用上一"全过"轮（60-70）——省 API 也**掩盖文件仍在被僵尸改**的事实：僵尸写入改变指纹反而会触发重检，无害但①的双写竞态在此可见。 |
| **self_check.rs** | 304 | 全量 | `BuildingHere` 进程内 Vec（36-57，F-08：跨进程无围栏）。`answer_self_checks` 的 Cancelled 分支喂 STOPPED_ANSWER（176-183）——暂停时 builder 不悬挂，但同样**只对回头读 inbox 的 agent 有效**。asks/ 目录与 inbox/ 分离（16）。 |
| **question.rs** | 510 | ask() 全读 | Fork 会话回答 Just-ask（73-179），成本差值法 141-177、session-lost 降级 151-162。F-09 与 build 并发共会话是被注释承认的设计，仅对可 fork 的 claude 系安全。WAIT=10min（24）。 |
| **tools.rs** | 839 | 关键函数 | 8 个工具（rebuild_start/status/activity_show/note/note_withdraw/stop/questions_list/check，15-120）。F-10 `rebuild_stop`（474-485）与 UI 同走 `RunSet::stop`——CLI 暂停等价，无更强语义。`rebuild_check` 经 asks 信箱、`building_here` 时直接拒（500-503，防自锁）；等待 `SELF_CHECK_LIMIT+5min`（184-185）。`rebuild_start` 亦入同一 RunSet（319+）——**同进程内 MCP 与 UI 互斥是齐的，缺的只是跨进程**。 |
| **check.rs** | 510 | 骨架+CheckStop | 构建/测试命令行执行器；`CheckStop` 支持暂停与限时双断（364-390 测试：超时步、暂停拒启）。检查子进程同样受 Job Object 管辖——外部网关不在此域。 |
| **kinds/** | mod 444 + website 912 game 332 screenshot 507 等 | mod.rs 读段 | `run_checks_within`（kinds/mod.rs:280-292）：每检查前看暂停与限长，插件 check（WASM world）并入轮次；website/game/app 是 Check 定义——Q2 预算的"检查侧重试 1 次"覆盖此全链。 |
| **brief.rs** | 425 | 常量+骨架 | continue_prompt/follow_up 组装；F-11 发布禁令仅文案级（PRIVATE_USE_NOTE 248），无执行体（接④）。DECOMPILE_FIRST（202）每 run 至多提醒一次（mod.rs:945/1027）。 |
| **study.rs** | 376 | 骨架 | Study 与 reopen_target；`remove_deep_only`（349）——模式切换时的 capture 清洗；`tools_run_remotely`（26）SSH 判定。 |
| **notes.rs** | 213 | 骨架 | pending/read 双标记文件（19-23）；`hand_over`/`take_left`/`take_back`/`claim`（39-130）——③第5条的底层。 |
| **project.rs / locate.rs / stacks.rs / stand_in.rs / output.rs** | 108/149/298/102/4 | 略读 | 建项字段（1-76）；本地目标定位；stacks.toml 表加载（stacks.rs:70-141，含 used_in 探测——mod.rs:1002 的栈改判来源）；测试假 run；输出 re-export。与四问无直接交互。 |
| **tests.rs / stall_tests / note_progress_tests** | 4428/178/287 | 锚点 | F-12 行为锁定审计：975 `a_plain_nonzero_cli_exit_resumes_its_saved_session`（断言非零退出→CONTINUE_TURN、wait=[30]、两次 TurnDone）与 1069 `an_untyped_opencode_exit_keeps_its_error_and_the_three_retry_cap`（三次上限锁死）——**修 F-01/process_exit 属"改行为须翻测试"区**（grants 同款门）。2751 暂停断言、3920 自检查轮暂停即停。 |
| **failure.rs** | 178 | 全量 | F-13 `process_exit` 任意非零/None→Transient（89-91）+ 测试 169-171 = 烧配额主因；分类器本身健全（typed-first，display 只供等待时长 94-116）。F-14 `retry_after` 的 `unit.starts_with('m')` 把 "m…" 一律当分钟（108）：`"retry after 5 months"` 类荒谬串被 clamp 900s 兜底，但 `"retry in 3 min, after load"` 与 "3 m" 歧义只会更保守，无危险面。 |
| **model.rs（取消段）** | 237-268 | 全量 | 见①第4步。`Stop` 双旗合成清晰；唯一软肋：`ChatModel::turn` 内部是否逐 chunk 检查由实现自决（trait 只传 &Stop，272）——暂停响应粒度不可静态保证（本次范围外，agent.rs 侧核实留待 batch2）。 |

## ⑥ Top5 修复表

| # | 修复 | 锚点 | Craft 侧可行性 / 代价 |
|---|---|---|---|
| **1** | **暂停僵尸治理（组合拳，run_session 不可达时的平台层出路）**：(a) 磁盘租约 `inbox/.craft-lease`（write_atomic：pid+session_id+heartbeat+generation 随机数），continue/新 run 前检查——心跳未死或租约超龄未清 ⇒ 拒绝自动续、要求人工确认；(b) 续跑前置**静默探针**：暂停后至少冷却 T（如 120s），期间用现成 `AppFingerprintCache` 对 app/ 连续取指纹，**指纹仍在变 ⇒ 僵尸活着**，feed 直说"上一构建仍在写文件"，禁发 CONTINUE_TURN；(c) hermes 专属 `probe_session`（适配器扩展）：借 `%LOCALAPPDATA%/hermes/tools/python` + gateway WS 做 `session.resume` 读 `execution_generation`（今晚已验证的杀法同源），读到 active turn 就提示先 interrupt。 | mod.rs:220-222 续跑判定；runs.rs:97 内存去重；self_check.rs:36-57 BuildingHere | (a)(b) **零外部依赖**、纯 Craft 代码，各约 100-200 行；(c) 依赖 hermes 网关在跑 + python 侧 websockets（便携 python 自带），失败时退回 (b)。三者叠加即可把"两个 turn 并发同工作区"从默认行为变成显式例外。 |
| **2** | **429 分型止血 + 退出码语义收紧**：quota-exhausted 型 429（provider_error 含 `insufficient_quota`/`Allocated quota exceeded`/中文额度词）判 Billing 而非 RateLimited；`process_exit` 非零退出首次给 Unknown（不盲试），仅当失败前有 TextDelta/工具活动（turn 真跑过）才升 Transient。 | failure.rs:50、89-91；tests.rs:169-171/975/1069 | 改分类 + 翻三处测试（上游 grants 式申报门同理：先改代码再翻行）。直击昨晚烧穿路径，12→1 个会话的量级削减。 |
| **3** | **run 级 + 跨 run 烧钱熔断**：`build-progress.json`（或新 `burn.json`）累计 `turn_attempts_24h` 与连续失败数；`turn_with_wait` 每次 tries+1 都落账，超阈（如 24h ≥12 次尝试或连续 6 次 ProgramFailed）直接 `Err(OverLimit)`→NeedsYou，人工复位。把 `not_working_checks` 从"仅检查轮"扩到"含 turn 级失败"。 | mod.rs:1261/1286、1041；workspace/progress.rs:20-21 | 中：计数器与持久化通道现成，主要是口径设计+2 个测试；不改行为锁不碰 975/1069。 |
| **4** | **feed.json 全文件重写改为 append-safe**：回盘 merge 时除 Ask.answer 外，把"磁盘有而内存无"的尾部项按序并入（或改事件日志+快照双文件）；节流期内 Finished 落盘失败（v99 只读盘、rename 重试耗尽）时把事件暂存重试队列而非 `log::warn` 吞掉（ai/feed.rs:172-174）。 | ai/feed.rs:159-176；engine feed.rs:205-222 | 中偏大；短期最小刀＝只补"外部 append 保全"一叉（约 40 行），伴侣工具（Anything Copy 面板）立刻受益。 |
| **5** | **craft.json 机器字段跨进程互斥**：仿 `USAGE_UPDATE` 但落盘——`inbox/.craft-lock` O_EXCL 创建 + pid 存活校验 + TTL；或 manifest 增 `status_owner`（租约同#1 的 generation），`write_manifest` 拒绝非 owner 覆盖 status/checks/agent_session。person 字段合并逻辑保留。 | workspace.rs:840-868、739-746 | 小中；与 #1(a) 同底座，做完锁把①③④三处竞态一次收口（双进程互相抹掉 agent_session 是当前最隐蔽的数据损毁面）。 |

---

### 汇总

- findings_count: **14**（F-01…F-14，另①—④四问结论若干）
- 四问速答：①置位=UI/CLI→RunSet::stop→CancelToken 电平闩；turn 收尾靠泵循环反复 `agent.stop()`+TurnDone 出口 check；"Paused…"写于 mod.rs:1451（craft.json）+feed.rs:91（feed.json）；外部网关未死时 **会** 双 turn 并发同工作区（Craft 全内存围栏，无 generation 概念）。②retryable=Transient|RateLimited；CONTINUE_TURN 每逻辑 turn 最多 3 次续试；**无任何累计预算熔断**，最坏单 run ≈32 个完整 agent 会话、跨 run 无限（计数器重置口径见②表）。③双文件两套节奏差 ≤2s；awaiting_check 是唯一对账旗；v2 盘升 v5 会被 markDeep 强制重 Study，盘新于码=读降级+写全冻结；Ask.answer 合并点=ai feed.rs:163-171（FeedLog::save）。④唯一消费者 interaction_tools.rs:490（allowed_actions）+477-479（approvals）；Decide 只旁路 core_person_ask（104-105），审批链对"不经 Craft 路由的 agent 自带工具"（hermes 的 shell）零管辖——事故全路径=Decide×无路由门。
