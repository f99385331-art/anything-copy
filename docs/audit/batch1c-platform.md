# batch1c — platform 层审计（craft-anything-src @ adeddca）

> 状态：完成（2026-11-12）。审计范围：Windows 进程树终止、挂载点 API 缺口、which.rs PATH 安全、fs 原子写 fsync 缺口。
> 只读仓内文件；唯一写入=本 reports 目录。

## 待填清单（已全部完成）
- [x] 0. 参考料复读确认（salvaged-platform*.md 覆盖=读了但零结论，故 grep 定位+窗口精读策略）
- [x] 1. 四问①：Windows 进程树终止覆盖矩阵（§1；含前批结论校正）
- [x] 2. 四问②a：磁盘租约+静默探针 API 缺口（§2）
- [x] 3. 四问②b：capture.rs 树扫描可复用件（§3）
- [x] 4. 四问③：which.rs PATH 搜索安全（§4）
- [x] 5. 四问④：fs 原子写缺 fsync save 路径（§5）
- [x] 6. Top5 修复表（§6）
- [x] 7. 值得保留的好设计清单（§7）

## 1. 四问① Windows 进程树终止覆盖矩阵

### 1.0 事实校正（推翻前批一条已证结论）
前批认定"Job Object kill-on-drop 只覆盖 Craft 自 spawn 后代"。**不精确**：本仓 pin 的 process-wrap 10.0.1 的 std::JobObject 显式 `make_job_object(handle, /* kill_on_drop = */ false)`（registry `process-wrap-10.0.1/src/std/job_object.rs:106`），`windows.rs:155` 仅当 kill_on_drop=true 才设 `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`。std 版 JobObject **没有** close-即-杀语义。真实终止机制是**显式 TerminateJobObject**：`JobObjectChild::start_kill`（`job_object.rs:166-168`）。由此逐路径：

### 1.1 覆盖矩阵

| 机制 | 触发点 | 覆盖 | 漏 |
|---|---|---|---|
| Job Object（TerminateJobObject） | spawn 挂 job：platform/process.rs:329；start_watched 挂 job：process.rs:1087。杀链：RunningProcess::drop→kill 标志 process.rs:706 → supervisor watch 返回 process.rs:891-899 → `end()` process.rs:843/936-953 → `start_kill`→TerminateJobObject | **运行期**由 Craft 发起的 timeout(wall process.rs:902)/idle(:905-908)/cancel(:891)/drop(:706)：job 内**任意深度**出生继承的成员全杀（含再孙）。hands_off 交接型 launcher 也在 drop 时等 5s 收族（process.rs:709-711, 883-885） | ①**Craft 崩溃/被杀**：job 句柄关闭但无 KILL_ON_JOB_CLOSE → 全族存活；②`Launched` 句柄 drop 不 stop → 按设计存活（process.rs:1056-1057 文档 + 无 kill-on-close 属实）；③job 外进程不可达 |
| Launched::stop() | process.rs:1238-1253：`child.kill()` = start_kill+wait（PW `std/core.rs:137-141`） | Windows 上 stop 即 TerminateJobObject，杀全族——尽管注释 1236-1237 保守写"what it started on its own may stay" | 崩溃路径同上；stop 仅在有活着的 Craft 调用时有效 |
| R5.2 watched-launch 测试 | `stopping_a_watched_program_stops_its_descendant` process.rs:1515-1533；`a_descendant_startup_timeout_stops_the_watched_launch` :1552-1567；替身 `watched_parent_stand_in` :1585-1615（子进程刻意用裸 std Command 生成以**继承**父 job/group，注释 :1598-1599）；锁探针：子持 `descendant-alive` 排他锁（`alive.lock()` :1629-1630），stop 后 `try_lock` 轮询即退出证明（:1523-1531）——无计时猜测 | 证明 job/group **继承链**上的后代随 stop 死亡（文件锁=OS 释放，等价静默探针原型） | **Windows 执行未验证**：docs/STATUS.md:50 "Windows execution of this replacement remains pending; the prior shell fixture failed there"；任务台账 docs/ROADMAP.md:171-190（R5.2，分支 bugfix/r5.2-watched-launch-tests / test/r5.2-watched-launch-windows-check） |
| taskkill /T | **全仓未使用**——唯一出现是反面论证注释 capture.rs:334-336（父死后 Windows 保留 PID 于子并复用号 → /T 会杀陌生进程） | —（被替代） | — |
| END_TREE（替代者） | capture.rs:338-344：PowerShell `Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,CreationDate` 做 PPID-BFS，**CreationDate≥父**守卫防 PID 复用，`Stop-Process -Force` 后再枚举 survivors 非零退出；调用点 console_text 超时/取消/失败后 capture.rs:401-415（10s 预算，失败仅 log::warn :412-413） | 无 job 的 PTY console 树：cmd→start /b 脱管孙也被杀——回归测试 `nothing_it_started_outlives_the_deadline` capture.rs:484-501 用 start /b 心跳文件字节数不变来证明 | ①console_text 全程**没有 Job Object**（portable-pty 不交句柄 + 工作区禁 unsafe FFI，ponytail 注释 capture.rs:434-435）："a program that leaves this console for one of its own survives"；②经服务/计划任务/COM 重生的 daemon PPID 链断裂，BFS 不可达；③powershell 启动 ~秒级、超时只 warn 不重试 |
| end_with_this_process（崩溃兜底 watcher） | lib.rs:82-112：/bin/sh 循环 `kill -0` 父、父死则 TERM/KILL 组并删 craft-* 残留目录（脚本 :95-103） | 仅 Unix（`if !cfg!(unix) return None` :89-91）。注释 :80 "a Job Object holds Windows children"——**按 1.0 该保证是假的**（崩溃时 job 关闭不杀） | Windows 崩溃后**无任何**平台内兜底：daemon 型后代全漏 |

### 1.2 detach daemon（hermes gateway 情形）定位
hermes gateway 由 agent CLI（Craft 的 job 内子进程）自行 daemon 化。Windows 下 job 成员资格随 CreateProcess 继承且 process-wrap 未开 breakaway 许可（`windows.rs:151-155` LimitFlags=0），普通子 spawn 逃不出 job；但 daemon 惯用逃逸道——计划任务（schtasks）/服务/COM 激活/自己起新 console——都**不经过** Craft 的子进程创建或**断开 PPID 链**，于是：Process::spawn 路径只有运行期 end() 杀得着（崩溃即全漏）；Launched 路径 drop 不杀；console 路径 END_TREE 靠 PPID+生日、对重生者失明。platform 仓内 0 处 "gateway" 引用（crates/+apps/ rg 零命中），确认其为外部进程。⇒ **platform 在 Windows 无法阻止此类进程存活，只能事后探测**——这正是 batch1b 三层缓解（磁盘租约/指纹探针/gateway WS）必须存在的根据。


## 2. 四问②a "磁盘租约+静默探针"所需 platform API：现状与缺口

### 2.1 现有文件锁使用点（全仓 rg `LockFileEx|flock|File::lock|try_lock`）
**platform 内 0 处原生 LockFileEx/flock**——全部经由 Rust std 的 `File::lock/try_lock`（Windows 后端即 LockFileEx 排他锁），且**都长在 platform 之外**：
| 位点 | 用途 | 模式 |
|---|---|---|
| crates/ai/src/cli_agents/unfinished.rs:61-64 | 回合租约记录：create_new 文件→`file.lock()`→写 JSON→`sync_all()`；文件名 pid+纳秒+计数器防 PID 复用（:57-60 注释） | **最完整**的"磁盘租约"实例（崩溃后 OS 自动解锁，`try_lock` :105 判定持有者已死→sweep 删会话 :125-128，重试上限 TRIES=3 :131-136） |
| crates/engine/src/tools/investigation_tools.rs:260-267 | 锁文件 try_lock 轮询+超时+错误上抛 | 阻塞式互斥 |
| crates/platform/src/process.rs:1523-1531, 1629-1630 | R5.2 后代存活探针（见 1.1） | 探针式 try_lock 轮询 |
| crates/engines/src/ghidra/mod.rs:495, 637（tests.rs:451, 466, 487） | Ghidra 项目 lock 文件；失败即释放、他进程读为"分析进行中" | 存在性+锁混合 |

platform 对外导出（lib.rs:19-22）只有 `write_atomic/write_atomic_private/backup_once/Process/Launch/which` ——**没有任何锁/租约 API**。layers 各写各的，lease 语义（token、心跳、staleness 约定、崩溃回收）在 ai 层重复实现。

### 2.2 "静默探针"（判断外部 owner 进程是否还活着）现有件
- keep_awake Windows 助手（lib.rs:60-72）：PowerShell `Get-Process -Id {owner}` **持句柄**循环，注释 :58-59 明确"handle 保住 → PID 复用不会误判"——正是 PID-liveness 探测的正确姿势，但嵌在字符串脚本里不可复用。
- macOS caffeinate `-w`（lib.rs:67-68）系统自带 owner-watch；Unix 版 end_with_owner（lib.rs:88-112）是完整 watcher——**Windows 全缺**（:89-91 直接 None）。
- sync.rs 的持锁超时诊断（:420, :466 Stuck 报告）只覆盖进程内 Mutex，与磁盘租约无关。

### 2.3 platform 需新增的 API（挂载点答案）
1. `pub mod lease`：`Lease::acquire(dir, token) -> Option<HeldLease>`（内部 = std try_lock + create_new + pid|nano|counter 命名，把 unfinished.rs:55-66 与 process.rs:1523-1531 的成熟做法上提）；`HeldLease`：Drop 自动 retire；附 `probe(dir)`（枚举无主租约，即 sweep 通用化）。工程量：小（~150 行 + 迁移 unfinished/ghidra 两处调用点）。
2. `pub fn process_alive_since(pid, created) -> bool`：Windows 用 OpenProcess+WaitForSingleObject(0) 持句柄语义（对齐 lib.rs:58-59 注释教训，可让 keep_awake 与 rebuild 孤儿检测共用）；Unix kill-0。禁 unsafe 约束下走 powershell `Get-Process` 封装或 windows crate safe 绑定（`windows` 已在本仓依赖，process.rs:329 已在用 `windows::Win32::...CREATE_NO_WINDOW` 常量，句柄操作是 safe wrapper 可行）。工程量：中。
3. Windows 崩溃兜底 watcher：`end_with_this_process` 的 NT 等价（PowerShell owner-循环 + `Stop-Process`/taskkill 单 PID，或命名 Job Object——命名 job 需 OpenJobObject/AssignProcessToJobObject 的 unsafe FFI，与工作区禁令冲突，见 lib.rs:46）。现实选择=owner-watch 脚本化。工程量：中。
4. 租约与 2.2 探针的接线约定（lease 里记 pid+生日，probe 端先验锁再验生日）——纯文档+小工具。

## 3. 四问②b capture.rs 树内可复用件（按 CommandLine 扫外部进程）

**现状：没有任何一处在读 CommandLine**（全仓 rg 命中仅 capture.rs:338 与 process_tree.rs:20 的 CIM 查询，未选 CommandLine 属性；antigravity.rs:198 的 "CommandLine" 是 adapter JSON 键，无关）。可复用件按移植成本排序：

| 件 | 位置 | 内容 | 可移植性 |
|---|---|---|---|
| CIM 查询+守卫模板 | capture.rs:338-344 `END_TREE` | `Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,CreationDate`；BFS 在脚本内；CreationDate≥父 防 PID 复用；杀后复验 survivors | 加 `-Property ... ,CommandLine` 即得指纹源；PS 5.1 内置/pwsh 7 同；纯扫描不需管理员。缺点：每次 spawn powershell（0.5-2s） |
| powershell 硬启动样板 | window_tools/process_tree.rs:14-22 | `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe` **绝对路径**+`-NoProfile -NonInteractive`（防 PATH 劫持，见 §7） | 直接抄；配 `Process.timeout/idle_timeout/stdout_cap`（:29-32） |
| 跨平台快照 | process_tree.rs:12-38 `snapshot()` | Windows=CIM "pid ppid"；Unix=`/bin/ps -A -o pid= -o ppid=`（每列单独 -o，FreeBSD 兼容注释 :24-25） | CommandLine 版：Win 加属性；Unix 加 `-o command=`。解析仍在 Rust 侧、可测 |
| 纯函数树解析 | process_tree.rs:41-64 `descendants()` | BFS、环安全、32768 行封顶、输入畸形宽容（单测 :176-191） | **完全可移植**，指纹匹配不需要 PPID 树时直接 `lines()`+`splitn(3, ' ')` 取 pid/ppid/cmdline |
| 子树搜索框架 | process_tree.rs:67-89 `capture()` | "root 找不到就扫后代"泛型循环 + 64 候选上限 | 指纹工具可直接套：谓词从"有窗口"换成"CommandLine 匹配" |
| 探测节奏 | process.rs:1523-1531 | try_lock 轮询 20ms/20s deadline | 静默探针事件循环样板 |

**缺口**：原生路径（Toolhelp32Snapshot/QueryFullProcessImageName/WMI 直连）全仓 0 处，且被"禁 unsafe FFI"文化挡死（lib.rs:46）→ 指纹工具只能走 powershell；轮询探测需自设节流（建议与租约联动：租约被持有就跳过扫描，避免每轮 ~1-2s 的 CIM 开销）。

## 4. 四问③ which.rs 的 PATH 搜索安全（DLL 劫持面 / 当前目录优先）

which.rs 全文 791 行：代码止于 :387（is_executable），:389 起全部为测试。核心路径 `which_in :250-278 → candidates :355-371 → is_executable :379-387 → launch_target :55-68`（被 process.rs:300 spawn 前置调用）。

### 4.1 已做对的（详见 §7）
- **空 PATH 项不查当前目录**：which_in:267-269 `dir.as_os_str().is_empty() → continue`——POSIX/cmd 语义里空项=隐式 CWD，此处封死；全仓无任何 `set_current_dir`（rg 零命中），GUI 进程 CWD 固定于启动位置，"当前目录优先"在**自研查找器里不存在**。
- **附路目录后置**：search_path 的 USUAL_HOME_DIRS/USUAL_DIRS 追加在 PATH 之后（:40-44 "the person's own order wins"）——安装器目录不能抢在用户 PATH 前（残余面见 F17）。
- **按发现的绝对路径启动**：launch_target:57-59 注释 #152——即使调用方给裸名，spawn 用 which 命中的全路径，CreateProcess 不再走自身搜索序。
- **plain_form 去 `\\?\` 前缀校验**（:330-352）：MAX_PATH、`.`/`..`、尾点/空格、`/?:`、设备名（CON/NUL/CONOUT$/COM⁰⁻⁹/LPT¹²³ :342-345）逐项拒——去前缀换名类攻击被文档化防死；candidates 里 PATHEXT 顺序对齐系统行为（#41）。

**F17 · 附路目录供给面（低危）。** USUAL_HOME_DIRS 含 `~/.cargo/bin`、`AppData\Roaming\npm`、`AppData\Local\hermes\bin` 等（:20-35）：程序**不在 PATH** 而落在这类用户可写目录时会被采纳。能写这些目录者本已等价代码执行，故非升级面；真正的新攻击者是 npm 全局安装链（包名混淆→`~/.local/bin` 幻影），属生态而非本文件缺陷。记录以防"顺手前插"回退。

### 4.2 真实劫持面（两条，均有 file:line）
**F15 · 未命中时的裸名回退 = CWD 幻影依赖劫持。**
launch_target:59 `which_in(...) .next()` 失败 → `return (program.to_owned(), vec![])` **原样把裸名交给 CreateProcess**；CreateProcess 的 exe 搜索序含**调用进程当前目录**（本文件 :357 自己承认 "CreateProcess only adds .exe" 的同一语义面）。场景：用户 cd 进不可信项目目录跑 craft-anything-cli，agent 未安装（PATH 无 codex.exe/hermes.exe），项目里摆一个伪造 `codex.exe` → 直接执行＝任意代码执行。GUI 场景因 CWD≈安装目录较难利用，CLI 场景现实可行。修复方向：未命中即报 ToolError::ProgramFailed（spawn_error :422-429 已有完整"找不到"报告链，只差不把裸名递出去）。

**F16 · 子进程 DLL 搜索面：cwd=不可信工作区 + 零 loader 加固。**
spawn 设 `cmd.current_dir(dir)`（process.rs:314-316），agent CLI 的 dir 是被重建的**不可信源树**（acp.rs:871、mod.rs:1106、models.rs:145 三处传入）。Windows 默认 SafeDllSearchMode 下子 exe 的 DLL 搜索第 5 位仍是 CWD（前 4 位=exe 目录/system32/系统目录/Windows 目录）：凡目标 CLI 运行时在 exe 目录找不到的 DLL（典型：python3xx.dll 一类"伴生运行时库"、插件式 `LoadLibrary(名)` 走搜索序）都会命中项目根里的伪造品。全仓 `SetDefaultDllDirectories|AddDllDirectory|LOAD_WITH_ALTERED` **零命中**；工作区禁 unsafe FFI（lib.rs:46 注释、capture.rs:435 再证）→ 运行时无法调用。可行政策：(a) 子进程 env 与 cwd 隔离——把 cwd 从"源树根"换到受控目录仅当程序非必须；(b) 打包 manifest 层面声明 loader 参数（无需 unsafe）；(c) 评估放行 windows crate 的 safe `SetDefaultDllDirectories`。
附带：is_executable 在 Windows=p.is_file()（:384-387）——显式扩展名查询可命中 .dll 之类的非可执行文件，但 CreateProcess 会拒绝，失败面非执行面，低危。
shim 解析（read_shim :98-106 → parse_npm_shim :119-137 → exe_wrapper_target :146-163）：从 shim 文本提取真实目标并以绝对路径直启 .exe（绕开 cmd 的参数缺陷 #1237），`exe_wrapper_target` 白名单极严（单条+仅 %*、禁 `%`、必须盘符/UNC 全路径），值得保留；npm/pnpm shim 的 target 允许 `..\` 成分（:133 实例），可越出 shim 目录——但可写 shim 目录已等价代码执行，不构成升级。

## 5. 四问④ fs 原子写缺 fsync 的 save 路径清单（掉电损坏面）

基准件 `write_impl`（fs.rs:64-88）：create_temp(:92) → write_all → **f.sync_all()(:80)** → rename_retrying(:82/125)。temp 文件本身有 fsync；**目录级 fsync（rename 持久化）全仓 0 处**——grep `sync_all|FlushFileBuffers|fsync` 全仓仅 6 命中（fs.rs:80/164、unfinished.rs:64、project.rs:215 注释、install.rs:203、fs.rs:1 文档），无一开目录句柄。

| # | 路径 | 现状 | 掉电面 |
|---|---|---|---|
| A（系统性） | write_atomic/write_atomic_private 全体调用者：engine/project.rs:115（project.toml）/ :132 / :176（unknowns/*.json）/ :207（annotations）；failure_log.rs:84；cli_agents/adapters.rs:699；opencode.rs:28；rebuild/mod.rs:1207；apps/craft-anything/renderer.rs:130（settings 落盘）；engine/workspace.rs:1389（png）；engines/install.rs:14,203；platform/sync.rs:503 | temp 已 fsync；rename 后不 fsync 父目录 | **Unix**：rename 条目可丢→文件"回滚到上一版"（不撕裂，文件内容恒一致），且可遗留 `.craft-anything.tmp-pid-n` 孤儿（fs.rs:107 命名，无开机清扫）。**Windows**：NTFS rename 走事务日志、持久，A 实际只咬 Unix |
| B | fs.rs:152-166 backup_once（"first backup 永不覆盖"不变式，:150-151 文档 + 测试 :228-238） | 文件 fsync(:164)，**create_new 的目录条目不 fsync** | Unix：掉电后备份"从未存在"→下次 backup_once 把**改后内容**当第一备份写下去——不变式被掉电静默打破。同 Windows 免罪 |
| C | ai/cli_agents/unfinished.rs:137-138 tries 计数重写：set_len+rewind+write_all，**无 sync**（对照首次记录 :61-64 有 lock+write+sync_all——首次路径是全仓最正确的范例） | 重写不同步 | 掉电后 tries JSON 可撕裂 → sweep :117 解析失败→"leave it as it is" 优雅降级，可接受但应补 sync_all |
| D | 文档谎报 | project.rs:215 注释宣称 "temp file of its own, fsync, then rename"；lib.rs:80 "a Job Object holds Windows children"（见 §1.0 证伪） | 误导续跑审计/修复者，先改注释 |
| E | fs.rs:22 注释 "FIFO cannot block the open" + :24 O_NONBLOCK（read 侧）；create_temp :92-121 含大小写/尾点尾空格别名排除（:108-111，测试 :207-226） | 读侧与命名加固完备 | 无缺口——列此防误删 |

**净结论**：本仓原子写纪律在同规模项目里属上游（sync-then-rename 全覆盖）；真正要修的是 Unix rename 持久化（A/B 补目录 fsync，Windows 无害但应同一实现 `#[cfg(unix)]` 分支）与 C 的一处 sync 缺失。掉电损坏面=回滚/不变式破坏，不含撕裂。

## 6. Top5 修复表（工程量按 batch1b 三层缓解在 platform 侧落地口径）

| # | 修复 | 锚点/依据 | 动作 | platform 侧工程量（人日估） | 服务的缓解层 |
|---|---|---|---|---|---|
| 1 | **磁盘租约 API 上提** | unfinished.rs:55-79（模板）；lib.rs:19-22 无导出 | 新增 `platform::lease`（acquire/probe/Drop-retire），迁移 unfinished + ghidra + investigation_tools 三处 | **3-4 天**（含单测 + unfinished.rs 回归 #1115） | 第 1 层（磁盘租约） |
| 2 | **Windows owner-watch/崩溃兜底** | lib.rs:80-91（Unix-only + 假保证注释）；§1.0 无 kill-on-close | `process_alive_since()` 原语（OpenProcess 持句柄语义，对齐 lib.rs:58-59）+ `end_with_this_process` NT 等价（powershell 循环或 safe windows crate）；命名 Job Object 方案需 unsafe FFI——与 lib.rs:46 政策冲突，先走 watcher 脚本 | **4-6 天**（含 STATUS.md:50 挂起的 Windows R5.2 fixture 执行验证） | 第 1 层前置 + 矩阵缺口 ①④ |
| 3 | **指纹探针（CommandLine 扫描）** | capture.rs:338-344、process_tree.rs:12-64 复用件 | CIM 查询加 `CommandLine` 属性（Win）/`-o command=`（Unix），复用 descendants() 纯函数；租约联动节流（持有即跳过，防 powershell 1-2s/轮 开销）；杀后 survivors 复验回灌（END_TREE :343-344 已有同款） | **2-3 天**（解析器有测试样板 :176-191） | 第 2 层（指纹探针） |
| 4 | **launch_target 裸名回退封堵** | which.rs:59；§4.2 F15 | 未命中→返回显式 not-found 错误（复用 spawn_error 链 process.rs:422-429），不再把裸名递给 CreateProcess；顺手把 gateway WS（第 3 层）连接失败与该错误码统一 | **1 天**（改动面小，风险在兼容——回归需过 adapters 全家） | 第 3 层（gateway WS）搭档；独立安全修复 |
| 5 | **Unix rename 持久化** | fs.rs:80-82/152-166（§5 A/B） | write_impl 与 backup_once 在 rename/create 后对父目录 `File::open(dir)?.sync_all()`（`#[cfg(unix)]`）；unfinished.rs:138 补 sync；开机清扫 `.craft-anything.tmp-*` 孤儿 | **1-2 天**（fs.rs 单测 + regression_atomic_temp_creation.rs 扩展） | 掉电面收敛（非三层，但 Top5 内需量最小） |

**gateway WS（第 3 层）本体不在 platform**：仓内 0 处 gateway 代码（§1.2），platform 侧只承担 #2/#3/#4 的接口面。

## 7. 值得保留的好设计清单

1. **文件锁=OS 生命周期探针**：R5.2 测试用排他锁替代计时猜测（process.rs:1510-1514, 1629-1630）——租约/静默探针的现成正典。
2. **PID 复用双防线**：租约文件名嵌 pid+纳秒+计数（unfinished.rs:58-60）；END_TREE 用 CreationDate≥父守卫（capture.rs:336, 341）；keep_awake 持 OpenProcess 句柄（lib.rs:58-59）。三处同一教训的独立实现——应合并为 `process_alive_since` 而非删减。
3. **taskkill /T 弃用有实证**：capture.rs:334-336 把"为什么不用它"写进注释，且 END_TREE 杀后复验、非零退出上报（:343-344）——终止要有证据，不要 fire-and-forget。
4. **hands_off 交接语义**：launcher 成功退出≠族消亡，drop 时等 5s 收族（process.rs:709-711, 880-885）——`go run`/npm 类包装器的正确姿势。
5. **STARTING rwlock + spawn_retrying**：并发开 console 与 spawn 的句柄继承竞态、ETXTBSY 退避，均有注释锚定（process.rs:389-412）。
6. **which 加固全套**：空 PATH 项跳过、绝对路径直启、附路目录后置、plain_form 设备名/MAX_PATH 校验、npm/pnpm/cmd 三类 shim 白名单解析（§4.1）。
7. **process_tree.rs 的防御姿态**：32768 行封顶、环安全 BFS、64 候选上限、快照输出截断即弃（:9, :34-35, :78-79）+ powershell 绝对路径启动（:15-16）。
8. **fs.rs 原子写纪律**：temp fsync-先于-rename（:80）、AV/索引器占用重试（:123-136）、大小写/尾点尾空格别名排除（:108-111）、备份首写不可变（:150-151）。
9. **日志切割 append-only 契约**：子进程只 append、切割方 set_len(0)，互不踩踏（process.rs:1132-1157）。
10. **失败报告走原子私有写**：failure_log.rs:84 write_atomic_private——自诊断文件本身遵守 durability 纪律。

## 附：审计口径
- 文件覆盖：platform 全部 11 src + 6 tests 目录清点；精读 process.rs（:290-360, :600-713, :836-960, :1065-1179, :1215-1289, :1500-1644）、capture.rs（:300-501, :505-656）、which.rs（:1-388）、fs.rs 全文、lib.rs 全文；跨层 unfinished.rs:1-140、process_tree.rs 全文、project.rs/failure_log/sync/ghidra/investigation_tools 锚点行；外部 process-wrap-10.0.1 std/job_object.rs 全文 + windows.rs 关键段。
- 与残卷冲突声明：salvaged-platform.md/run2.md 的"Job Object kill-on-drop"前提已被 §1.0 校正（registry 源码为准）；其余已读范围未重读。
- 发现计数：**28 条**带 file:line 的结论（四问分布 ①9 ②a5 ②b3 ③6 ④5 + 交叉 0；其中正向保留/复用结论 6 条，问题与缺口 22 条）。
- files_done：platform 深读 5/11（process.rs, capture.rs, which.rs, fs.rs, lib.rs；其余 6 个文件属四问外或残批已覆盖：serve/standin_server/window/display/cancel/sync 仅锚点行引用）；跨层与外部 14（unfinished.rs, process_tree.rs, project.rs, failure_log.rs, ghidra mod+tests, investigation_tools.rs, adapters.rs, opencode.rs, rebuild/mod.rs, renderer.rs, install.rs, STATUS.md, ROADMAP.md, process-wrap 源码 3 处合并计 1）。

