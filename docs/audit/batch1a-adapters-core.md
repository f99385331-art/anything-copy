1|# batch1a：cli_agents 适配层 P0 审计
2|
3|> 仓库：craft-anything-src @ adeddca。审计范围（精确）：adapters/hermes.rs、grants.rs、adapters.rs（AgentAdapter trait + claude/codex args()）；回答三问所引用的最小外围：acp.rs（ACP 表/model_args）、mod.rs（transport 选择/run_cli/build_args/check_builder_tools）、platform/process.rs（spawn 链）、ssh.rs（远端二次打包）、prompt.rs（preamble 实测 ~2,560 字符）、config.rs（acp 字段）、models.rs（requires_acp 分支）、docs/ROADMAP.md（grants 定位）。
4|
5|
6|---
7|
8|## 文件 1：crates/ai/src/cli_agents/adapters/hermes.rs（全文 57 行）
9|
10|| # | 位置 | 发现 | 影响 |
11||---|------|------|------|
12|| 1 | hermes.rs:15-23 | `args()` 把 `-m <model>`（17-19）、用户 `options.args`（20）、`-z "<preamble><prompt>"`（21）拼成 argv；**preamble+prompt 合并为单个 argv 元素** | 长消息直接撞 Windows 命令行上限（见问题②）；claude/codex 已用 stdin 规避，hermes 没有 |
13|| 2 | hermes.rs:16-22 | `args()` **完全不使用 `cx.mcp`**——无 `--mcp-config`、无 `-c mcp_servers.*`、无 notes hook | 构建器拿不到 Craft Anything 工具服务器；与 grants.rs:79 `tool_server: No` 申报一致 |
14|| 3 | hermes.rs:25-27 | `required_flags() = (["--help"], ["--oneshot"])`；运行前 `verify_flags` 检查（mod.rs:958-978 消费） | 检查失败时因 `plain_fallback=false`（30-32）不换 Plain，而是"trying it anyway" |
15|| 4 | hermes.rs:30-32 | `plain_fallback() = false`：裸 `hermes <prompt>` 是交互会话 | 与 grants.rs:79 path=Argv 并存：per-message 走 `-z`，失败不退化 |
16|| 5 | hermes.rs:34-36 | `streams_json() = false`：输出按纯文本流解析 | 无结构化事件/usage；成本统计缺失（对比 claude adapters.rs:487+、codex 864+） |
17|| 6 | hermes.rs:10-37 | **trait 默认值缺口**：未覆盖 `requires_acp`（默认 false，adapters.rs:83-85）、`prompt_on_stdin`（默认 false，adapters.rs:172-174）、`mcp_env`（默认 None，adapters.rs:206-208）、`check_tool_server`（默认 Ok，adapters.rs:201-203）、全部 `acp_*` 钩子（adapters.rs:88-116）、`resumes`/`answers_questions`（adapters.rs:162-169） | 升级 ACP 所需的适配层钩子全部走默认；`answers_questions=false` 使 question 运行被拒（mod.rs:988-995） |
18|| 7 | hermes.rs:48-56 | 测试锁定 argv 形状 `["-m", model, …args…, "-z", "PRE make a game"]` 与注册（`for_agent("hermes")` 非 Plain） | 改 `args()` 会红；改 ACP 则 `args()` 成为 run_cli 拒绝后的死路径（mod.rs:934-942），可不删 |
19|
20|## 文件 2：crates/ai/src/cli_agents/grants.rs（全文 260 行）
21|
22|| # | 位置 | 发现 | 影响 |
23||---|------|------|------|
24|| 1 | grants.rs:11-9 头部注释 | 表的定位："what a builder gets is stated in one place… An adapter without a row fails them"——**申报-测试门**，非运行时开关 | 与代码检索结果吻合（见问题③：无运行时消费者） |
25|| 2 | grants.rs:16-27, 31-43 | `Given{Yes,No,NotYet(why)}`；`Grants{tool_server, approvals, resume, mid_turn_notes, long_message}` 五列 | `NotYet` 必须带文字说明（测试 176-180 强制） |
26|| 3 | grants.rs:47-53, 56-62 | `Path{Argv,Acp}` 枚举 + `Declared` 行结构（id/path/tool_server/approvals/mid_turn_notes；resume、long_message 由 adapter 自答） | path 是测试断言的分支开关 |
27|| 4 | grants.rs:66-105 | DECLARED 表：claude-code=Argv/Yes/Yes/Yes(67)、codex=Argv/Yes/No/No(70)、**hermes=Argv/No/No/No(79)**、copilot/grok=Acp/Yes/Yes/No(83-84)、maki/devin=ACP_AGENTS 里有 ACP 启动词但表仍 Argv/No(81,87) | "ACP-capable 但默认 Argv"是既有模式（hermes/maki/devin/gemini-cli/opencode 五行皆如此） |
28|| 5 | grants.rs:107-126 | `grants()`：`long_message = prompt_on_stdin || path==Acp`（124）；无行→`NotYet("this adapter states nothing here yet")`（117） | hermes `prompt_on_stdin=false` → long_message=No，如实反映 argv 风险 |
29|| 6 | grants.rs:130-134 | `table()`：遍历注册适配器 + 末尾 plain 行 | **全仓无生产调用方**（检索见问题③） |
30|| 7 | grants.rs:186-211 | 测试 `a_tool_server_is_declared_exactly_when_a_run_carries_one`：Argv 行要求 `carries_server(argv, mcp_env, "craft-anything-cli")` 与申报严格相等（192-200）+ `!requires_acp`（201）；Acp 行要求 `requires_acp` + tool_server/approvals=Yes + notes=No（203-207） | 这是"改 hermes 行"唯一会被激活/打红的东西（问题③） |
31|| 8 | grants.rs:160-163 | `carries_server`：argv 含 MCP_NAME/命令名、或 env、或 argv 命名的文件内容 | 覆盖三种真交付方式（claude `--mcp-config`、codex `-c`、dsh patch 文件） |
32|| 9 | grants.rs:213-233 | 测试 3：mid_turn_notes 申报 ⇔ argv 含 "builder-notes"；approvals=Yes ⇔ argv 含 APPROVAL_TOOL 或 ACP（228-231） | hermes 若翻 approvals=Yes 同样打红 |
33|
34|## 文件 3：crates/ai/src/cli_agents/adapters.rs（审计范围：trait 定义 46-260 + ClaudeCode::args 441-482 + Codex::args 819-852）
35|
36|| # | 位置 | 发现 | 影响 |
37||---|------|------|------|
38|| 1 | adapters.rs:28-43 | `ArgsCx{options, prompt(已防读成 flag), preamble, mcp, resume, builder, reads_checked, question}` | prompt 防 dash 在调用方 build_args（mod.rs:361），不在 trait 层 |
39|| 2 | adapters.rs:46-116 | trait 核心：`args()`(50) 必选；ACP 全套钩子均有默认——`requires_acp`(83-85, 注释：显式 `acp=false` 或 SSH 必须**失败**而非打开无审批通道的交互会话)、`acp_options`(88-90 默认透传 options.args)、`acp_mcp_options`(93-95)、`acp_mcp_stdio_type`(99-101)、`acp_mode_options`(105-107)、`acp_trailing`(109-111)、`acp_session_config`(114-116 `session/set_config_option`) | 升级 ACP 是"加 override"级改动，无结构性缺口 |
40|| 3 | adapters.rs:142-183 | `required_flags`(144)、`plain_fallback`(150-152, #199)、`streams_json`(154)、`prompt_on_stdin`(172-174 **注释原文**："a long one passes Windows' command-line limit (\"The filename or extension is too long\", os error 206, #402)")、`stdin_text`(177-179)、`process`(181-183) | 仓内对问题②上限的自证（#402） |
41|| 4 | adapters.rs:198-218 | `check_tool_server`(201-203 默认 Ok)、`mcp_env`(206-208 默认 None)、`check_remote_tool_server`(211-213)、`remote_tool_server`(216-218 默认 None) | hermes 全默认 → 原生路径无工具服务器、无环境注入 |
42|| 5 | adapters.rs:282-299 | `built_in()` 注册 12 适配器（Hermes 在 290）；`for_agent` 未知 id → Plain(313-315) | 注册链完好 |
43|| 6 | adapters.rs:332-336 | `Plain::args`：prompt 作为最后 argv（334 preamble+prompt 合并） | Plain 同样受 argv 上限 |
44|| 7 | adapters.rs:421-423, 441-482 | **ClaudeCode**：`prompt_on_stdin=true`（421-423，prompt 不进 argv）；`args()` 交付：`--mcp-config <mcp_json>`(446,470 工具服务器)、`--permission-prompt-tool mcp__{MCP_NAME}__{APPROVAL_TOOL}`(464 审批)、`--settings notes_hook`(466-469+345-349 中途笔记)、`--model`(450)、`--strict-mcp-config`(470) | claude 行 Argv/Yes/Yes/Yes 与 argv 内容严格对应（grants 测试的样板） |
45|| 8 | adapters.rs:801-810, 819-852 | **Codex**：`prompt_on_stdin=true`（803-805，注释 "#528"）+ `stdin_text`(807-809)；`args()`：`exec --json`(820)、`-c mcp_servers.{MCP_NAME}.command/args`(830-838 工具服务器)、`tools.*.approval_mode="approve"`(842-844 预批表)、`-m`(845-847)、结尾 `-`(850 stdin 读消息) | codex 行 Argv/Yes/No/No 对应：有 server、无审批通道（`codex exec` 不能停下来问人，grants.rs:68-69 注释） |
46|| 9 | adapters.rs:362-384 | `question_args`：question 路由复用 claude 适配器，`--fork-session --no-session-persistence --disallowedTools` | 对比 hermes：`answers_questions=false`，question 直接被 mod.rs:988-995 拒 |
47|
48|---
49|
50|## 问题①：把 hermes 升级到 ACP 路径，现有代码还缺哪几块？
51|
52|**结论：四块里有一块（ACP_AGENTS 表）已经存在且无需改；真正缺的是 requires_acp 声明、grants 行改写、模型 flag 三处，外加一处需实测的启动词顺序/尾参。**
53|
54|| 检查项 | 现状 | 证据 | 缺什么 |
55||--------|------|------|--------|
56|| ACP_AGENTS 表 | **不缺**。`("hermes", &["acp"])` 已在表中；`acp_args("hermes")` 返回 `Some(["acp"])` | acp.rs:26-37（hermes 在 31）、acp.rs:73-75 | 无 |
57|| transport 选择 | **机制完好，agent 无声明**。`selected_acp_args` = `acp_args(agent).filter(\|_\| options.acp.unwrap_or_else(\|.\| adapter.requires_acp()))`——hermes 因 requires_acp=false，只有用户手动 `acp=Some(true)`（config.rs:123）才走 ACP；`acp_for()` 组装启动参数并在 SSH/question 不兼容时返回 None 回退 run_cli，run_cli 对 requires_acp 者直接报错拒跑 | mod.rs:315-320、mod.rs:697-734、mod.rs:934-942、adapters.rs:81-82 | 缺 hermes 的 `requires_acp()=true` override（默认 false：adapters.rs:83-85；hermes.rs:10-37 未覆盖） |
58|| requires_acp | **缺**。同上；连带效果：preflight `check_builder_tools` 走不到 ACP 分支（mod.rs:305-311），模型选择走不到 ACP 清理（models.rs:192-198） | hermes.rs（全文件无该 fn）、adapters.rs:83-85 | hermes.rs 加一行 override |
59|| 模型 flag | **缺**。`ACP_MODEL_FLAGS` 只有 maki/grok/devin，无 hermes → `model_args("hermes", _)` 恒空 → mod.rs:711 拼不进模型参数；`acp_session_config` 默认空（adapters.rs:114-116）→ mod.rs:721/729 也不发 `session/set_config_option`。结果：`cli_model` 在 ACP 路径**静默丢失** | acp.rs:41、acp.rs:61-67、mod.rs:711、mod.rs:721+729 | 二选一：acp.rs:41 加 `("hermes", "-m")`（前提实测 `hermes acp` 接受启动期模型 flag）；或 hermes.rs 实现 `acp_session_config()` 用会话配置项设模型 |
60|| （附带）grants 行 | **必须同步改，否则测试打红**：DECLARED 的 hermes 行 path=Argv，而 Argv 行断言 `!requires_acp`（grants.rs:201）；改成 Acp 后又被 203-207 强制 tool_server=Yes、approvals=Yes、mid_turn_notes=No | grants.rs:79、grants.rs:201-207 | 行改写（见下清单 2） |
61|
62|**最小改动清单（文件 + 函数 + 改法）**
63|
64|1. `crates/ai/src/cli_agents/adapters/hermes.rs` :: `impl AgentAdapter for Hermes`（10-37）——加 `fn requires_acp(&self) -> bool { true }`。效果链：`selected_acp_args` 默认选中 ACP（mod.rs:319）→ `acp_for` 用 `["acp"]` 起会话（mod.rs:710 + acp.rs:31）→ run_cli 拒绝 native/SSH/acp=false（mod.rs:934-942，正是 adapters.rs:81-82 注释要求的失败语义）。
65|2. `crates/ai/src/cli_agents/grants.rs` :: `DECLARED`（79）——hermes 行改 `{ path: Path::Acp, tool_server: Given::Yes, approvals: Given::Yes, mid_turn_notes: Given::No }`（对齐 copilot/grok 行 83-84），否则问题③所述测试全红。
66|3. `crates/ai/src/cli_agents/acp.rs` :: `ACP_MODEL_FLAGS`（41）——加 `("hermes", "-m")`；若 `hermes acp` 不接受启动期模型 flag，则改为在 hermes.rs 实现 `acp_session_config()`（adapters.rs:114-116 默认）返回 `Vec<(String,String)>` 的模型配置项。**两处改动互斥，以真机 `hermes acp --help`/initialize 的 configOptions 为准**（上游能力仓内无法验证）。
67|4. （实测门）`crates/ai/src/cli_agents/acp.rs` :: `ACP_AGENTS`（31）+ hermes.rs :: `acp_trailing`/`acp_options`——确认 `hermes acp` 就是 ACP stdio 服务端、无需尾参；若需要 `stdio` 尾词按 grok 先例（acp.rs:34-35 注释、adapters.rs:109-111）实现 `acp_trailing`。同时确认拼参顺序：mod.rs:709-719 是 `options.args → ["acp"] → 模型flag → acp_mode_options → acp_mcp_options → acp_trailing`，而现 argv 适配器顺序是 `-m → args → -z`（hermes.rs:17-21）；若 hermes 要求模型 flag 在 `acp` 之前，需覆盖 `acp_options`（adapters.rs:88-90）。
68|5. （无需改，记录行为差异）hermes 的 `args()`/`required_flags()`/`streams_json()` 保留即可——requires_acp 后 run_cli 在调 `build_args` 前就返回（mod.rs:934-942 先于 997），argv 路径成为死代码；`answers_questions` 仍默认 false（adapters.rs:167-169），question 在 ACP 路径也被 `acp_for` 拒（mod.rs:700-702），与现在等价。
69|
70|## 问题②：prompt 经 argv 在 Windows 上的风险函数链与触界字符数
71|
72|**风险链（谁拼 args → 谁 spawn → 谁到 CreateProcessW）：**
73|
74|```
75|hermes.rs:21        Hermes::args() 把 preamble+prompt 合并成 "-z" 的单值
76|  ↑ preamble: mod.rs:979 → prompt.rs:50-55 cli_preamble()（实测约 2,560 字符：METHOD 1270 + MEMORY 877 + EXPERIENCED 103 + 固定尾注）
77|mod.rs:351-365      build_args()（mod.rs:361 只对 leading '-' 加空格防护，不查长度）
78|mod.rs:997          run_cli() 取得 args: Vec<String>
79|mod.rs:1023-1026    本机: (program, args)；SSH: ssh_line_args(host, remote_command(...)) —— 远端整条命令行被拼成【单个】本地 ssh 参数（ssh.rs:10-21，shell_quote 逐词加单引号）
80|mod.rs:1054-1055    Process::new(&prog).args(&argv)（adapter.process()：adapters.rs:181-183 → platform process.rs:165-177 只 push 进 Vec）
81|process.rs:298-330  Process::spawn() → process_wrap::std::CommandWrap（process.rs:25）包裹 std::process::Command → Windows CreateProcessW
82|```
83|
84|**触界**：`CreateProcessW` 的 `lpCommandLine` 上限 **32,767 个 UTF-16 字符（含程序名、空格、引号；BMP 内一字符计一，CJK 不翻倍）**。Rust std 把 Vec<String> 序列化成一条命令行并按引号规则加转义（含空格参数加外层 `"`）。超限即 `ERROR 206`——本仓两处以注释自证踩过大坑：adapters.rs:170-174（#402，"The filename or extension is too long"）与 adapters.rs:801-805（#528，codex 因此改 stdin）。claude/codex/gemini 已用 `prompt_on_stdin`（adapters.rs:421-423、803-805）规避；**hermes 未实现 → prompt+preamble 全额进 argv**。
85|
86|**具体多少字符会触界（hermes 本机路径估算）**：固定开销 ≈ preamble ~2.6K + 程序路径 0.03-0.12K + `-z`/`-m`/用户 args ~0.1-0.5K + 引号/空格若干 ⇒ **prompt 约 29,500 字符开始进入危险区，约 30,000+ 字符必然 os error 206**。走 SSH 时更糟：整个远端命令行（含引号化的 prompt）是本地一条命令，prompt 里的空格/引号被 `shell_quote` 放大（每对嵌入单引号 +4 字符，ssh.rs:25-30），**有效上限再降 ~2-5%**。注意失败形态不是优雅报错而是 spawn 返回 os error 206 → `TurnFailure::from_process`（mod.rs:1128），对用户表现为进程起不来。
87|
88|**ACP 路径天然免疫**：`session/prompt` 经进程 stdin 的 JSON-RPC 行传输（acp.rs:1-8 头注、grants.rs:5-6/123-124 "ACP carries the message in a session rather than in argv"），升级 ACP 同时消解本风险——这也是问题①清单 1 的隐藏收益。
89|
90|## 问题③：grants.rs 被谁消费？把 hermes 行改成 tool_server=Yes 会激活什么？
91|
92|**消费者（全仓检索 `grants`，*.rs）：**
93|
94|| 引用点 | 性质 |
95||--------|------|
96|| mod.rs:14 `pub mod grants;` | 模块声明（导出本身） |
97|| grants.rs:130-134 `table()`、grants.rs:113-126 `grants()` | 定义 |
98|| grants.rs:171/186/213/236/247 五个 `#[test]` | **唯一实际调用方** |
99|| docs/ROADMAP.md:912-923 | 规划叙述（"a test that fails when one is left out"） |
100|
101|**没有任何运行时/生产代码读取这张表**。运行时行为完全由 trait 的 override 决定：`check_builder_tools`（mod.rs:305-311）只看 `selected_acp_args` 与 adapter 自身的 `check_native_options`/`check_tool_server`；`mcp_for`/`build_args` 只看 args() 内容。表是"申报 + 回归门"（grants.rs:8-9 设计意图）。
102|
103|**把 hermes 行（grants.rs:79）改成 `tool_server: Given::Yes` 而其它不动，会激活的代码路径 = 测试红，仅此而已：**
104|
105|1. `a_tool_server_is_declared_exactly_when_a_run_carries_one`（grants.rs:186-211）：行仍 path=Argv → 走 191-200 分支，用 `builder_run()`（149-155）实跑 `Hermes.args()` + `mcp_env()`，`carries_server`（160-163）检 `MCP_NAME`/"craft-anything-cli"——**Hermes::args 根本不含 mcp（hermes.rs:16-22），mcp_env 默认 None（adapters.rs:206-208）→ carried=false，断言 `row.tool_server.given()==carried` 即 `true==false` 打红**，报错文案正是设计好的 `"hermes: declared Yes, but its run hands over none"`（196-200）。
106|2. 若连 `path: Path::Acp` 一起改：203-207 转而断言 `requires_acp()==true`（grants.rs:204）——hermes 没实现 → 同样打红。即**表改不动、绕不开：翻 Yes 必须先把代码链（问题①清单 1）做齐**。
107|3. 运行时零变化：`long_message` 仍 No（grants.rs:124 由 prompt_on_stdin 推得）；preflight（mod.rs:305-311）对 hermes 仍默认 Ok——工具服务器**不会**因为表里写 Yes 就被递给构建器。这正是上游申报 grants.rs:79 `tool_server=No` 的如实之处。
108|
109|---
110|
111|## Top 5 修复清单
112|
113|| 优先级 | 修复 | 位置 | 做法与验收 |
114||--------|------|------|-----------|
115|| P0 | **hermes 长 prompt 的 os error 206 防护**（升级 ACP 前先止血） | hermes.rs:15-23；对照 adapters.rs:172-179 | 若 `hermes -z -`/stdin 可行：覆盖 `prompt_on_stdin=true` + `stdin_text`（codex 先例 adapters.rs:803-809），grants.rs:124 的 long_message 自动翻 Yes 且被 236-244 测试守住；若不可行：run_cli 前加 argv 总长预检（>~30K 字符给显式错误，而非 spawn 206）。验收：>32K 字符消息要么正常送达要么清晰报错 |
116|| P1 | **hermes 切 ACP 三件套**（requires_acp + grants 行 + 模型 flag） | hermes.rs（加 override）；grants.rs:79（行改 Acp/Yes/Yes/No）；acp.rs:41（加 `("hermes","-m")` 或 hermes.rs 实现 acp_session_config） | 照问题①清单 1-3。验收：`cargo test -p ai cli_agents` 全绿（grants.rs:186-211 是硬门），`hermes acp` 起会话、审批经 `session/request_permission`（acp.rs:5） |
117|| P1 | **ACP 启动词/参数顺序真机核验** | acp.rs:31（`["acp"]` 申报）；mod.rs:709-719（拼参顺序） | `hermes acp --help` + initialize 回包核对：是否 stdio、模型 flag 位置、是否需 trailing。上游申报（path=Argv, tool_server=No, approvals=No, mid_turn_notes=No）与切 ACP 后的申报差值逐项落 grants 注释。验收：清单 4 的实测门有记录 |
118|| P2 | **grants 表维持"代码先行"**：禁止先翻 Yes 后补代码 | grants.rs:79 | 表无运行时消费者（问题③），翻 Yes 只打测试——保持 DECLARED 行与 args()/mcp_env() 实态同步；如需对外展示能力矩阵，应在消费侧（设置页）调用 `grants::table()` 并标注其申报属性，避免被误当 feature flag |
119|| P2 | **SSH+argv 二次打包的长度放大**（hermes 及其他 Argv 适配器共用风险） | mod.rs:1023-1026；ssh.rs:10-21 | 远端整条命令行作为本地单参数（shell_quote 放大嵌入引号）；同 P0 预检应覆盖 SSH 分支总长。hermes 切 ACP 后此路径被 mod.rs:934-942 自然封死，但 Plain/Gemini 等仍暴露——预检放 `build_args` 之后、`Process` 之前一处即可全局受益 |
120|
121|## 收尾备注
122|
123|- 本次审计范围严格限定于任务三文件 + 回答三问所需的最小引用（acp.rs 表与 model_args、mod.rs 传输/spawn/preflight、platform/process.rs spawn 链、ssh.rs 引号、prompt.rs preamble 实测 ~2,560 字符）。
124|- 未验证的外部事实（需真机）：`hermes acp` 模式是否存在及其 flag 集（acp.rs:31 是上游申报，本次仅确认代码链接受该申报）；`hermes -z` 是否可读 stdin。
125|- 关键不变式（供后续批次引用）：`requires_acp=true` ⇒ run_cli 在 `build_args` 前拒绝（mod.rs:934 先于 997）⇒ hermes.rs `args()` 变死代码，无需删除；grants 测试 grants.rs:201 与 204 构成 Argv⇄Acp 行的互斥锁。

---

## 真机核验（2026-11-11 23:5x，本机 Hermes，补问题①清单4与P0）

| 申报 | 真机结果 | 判定 |
|---|---|---|
| `hermes acp` 存在（acp.rs:31） | ✅ `hermes acp --help` 正常；usage 仅 `--accept-hooks/--version/--check/--setup/--setup-browser/--yes`；**无启动期 `-m`** | ACP 路径通；`ACP_MODEL_FLAGS` 加 `("hermes","-m")` 的方案**作废**，模型必须走 `acp_session_config()`（待查 initialize 的 configOptions） |
| ACP 依赖健康 | ✅ `hermes acp --check` → "Hermes ACP check OK" | 清单4实测门已过 |
| `hermes -z -` 读 stdin | ❌ 空 stdin 与 echo 中文 prompt 两次都返回同一句通用问候 → `-` 被当字面 prompt，**stdin 未被消费** | P0 的 prompt_on_stdin 不能直接翻——两条正解：A) 在 Hermes 上游给 `-z` 加 stdin/@file 支持（我们自己就是那个上游，可提 PR/自带 fork）；B) 主线走 ACP（session/prompt 经 JSON-RPC，天然免疫 32K 上限）|
| 副作用 | 两次探测各触发一次真实 one-shot 会话（无害小消耗） | — |

**修正后的 Top 修复序**：P0=argv 总长预检（Craft 侧 >30K 报清晰错误而非 os 206）→ P1=ACP 三件套（requires_acp + grants 行 Acp/Yes/Yes/No + hermes.rs 实现 acp_session_config 模型项）→ P1=initialize/configOptions 实测 → P2=SSH 路径全局预检 → P2=grants 代码先行纪律。
