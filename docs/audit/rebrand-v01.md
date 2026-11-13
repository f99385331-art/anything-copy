# Rebrand v0.1 施工报告 — Anything Copy 换牌批

- **日期**: 2026-11-12（中国标准时间）
- **仓/分支**: `C:\\Users\\Murphy\\projects\\craft-anything-src` @ `anything-copy`
- **基点 → 结果**: `9ec0ad8` → **`93916ae2582e5365dbf06835f53b960201684289`**（一次 commit，87 files changed, 552 insertions(+), 603 deletions(-)，工作树干净）
- **施工脚本**: `C:\\Users\\Murphy\\AppData\\Local\\hermes\\cache\\scratch\\build_rebrand.py`（机械替换 + 守卫表 + 断言式锚点；日志 `rebrand_build_report.json`）

## 一、蓝图执行对照

| 步骤 | 状态 | 实测结果 |
|---|---|---|
| 1a 窗口与版本信息 | ✅ | `build.rs` ProductName/FileDescription/LegalCopyright 按蓝图原文替换（Copyright 行保留 "Craft Anything contributors" 归属、追加 `; fork (c) Murphy.`）；`main.rs:82` with_title、`:83` with_app_id → `dev.murphy.anything-copy`；行 1/63 注释同改 |
| 1b 身份常量 | ✅ | `keys.rs:13` SERVICE → `dev.murphy.anything-copy`（全仓 grep 确认无测试锁死旧串）；`FLATPAK_SIGN_IN`（mod.rs:495/500）与 1634-1636 锁定断言**未动** |
| 1c 图标重画覆盖 | ✅ | Pillow 画圆角方块（半径 22%）#101c3d 底 + 白几何 A（等宽笔画：斜腿垂直厚 ≈0.115、横杠同厚，2048px 母图 LANCZOS 降采样）。覆盖：hicolor 8 尺寸 png（16/24/32/48/64/128/256/512，文件名与路径不变）、`craft-anything-1024.png`、`craft-anything.ico`（PIL 从 256 生成，含 16/32/48/256）、`craft-anything.svg` 与 `hicolor/scalable/apps/….svg`（同设计矢量）。**`.icns` 跳过（v0.2）**。视觉复检通过（无错位/缺口/锯齿） |
| 1d 品牌资产与 README | ✅ | `git rm -r docs/brand/`（5 文件）；README 顶部 ArtCraft `<picture>` 块整体删除；图标段 alt → "Anything Copy icon"；banner（蓝图原文 3 行）+ 迁移说明（老用户重登 API key）紧随 h1 之后；商标段 4 处 docs/brand 死链改指 `docs/brand-note.md`；尾部 ArtCraft mark `<p>` 换成自有图标+如实 fork 归属句；`docs/brand-note.md` 新建（6 行边界说明）。**LICENSE / LICENSE-APACHE / NOTICE 一字未动**（diffstat 可证） |
| 1e 用户可见源串 | ✅ | 逐行替换 + 守卫表：`crates/ui-egui/src`(17 rs)+`tests/smoke.rs`、`crates/ai/src`(含 inline tests)、`apps/craft-anything{,-cli,-web}` 共 **51 个 rs 文件 124 处**；16 个 TSV 共 **789 处**（key 列+译文中拉丁 token；译名未动；改名后 key 集无重复断言通过；TSV 与 Rust 源串同 commit ✅） |

**守卫命中（刻意保留 5 处，均验证为机器路径/上游事实引用）**：
- `demo.rs:220` `/demo/Craft Anything/` 演示假路径
- `dsh.rs:170` 测试 fixture `C:\\Program Files\\Craft Anything\\craft-anything-cli.exe`
- `cli_agents/mod.rs:2431` 测试 fixture `/home/someone/Craft Anything/notes.app`
- `build.rs:18` 版权行内 "Craft Anything contributors"（上游归属，蓝图指定保留）
- `main.rs:245` "Craft Anything issue #742"（指向上游 repo 的事实引用）

## 二、超出蓝图清单的改动（披露）

1. `apps/craft-anything/src/main.rs` 行 128（eframe::run_native 标题）、176（错误对话框标题）、318（子进程 label）——同为用户可见窗口文案，不改会造成半换牌；行 245 上游 issue 引用保留。
2. README.md：h1 换名、商标段/尾注改造（蓝图说 "README 是主要引用者……链接改指 brand-note"，尾部 `<img src=docs/brand/…>` 属死链一并处理）。
3. `hicolor/scalable` 的 svg 与 `craft-anything.svg` 同内容（蓝图说"逐个重画"覆盖 png，svg 取同一设计双落点）。
4. ui-egui/cli/web 文件内 doc 注释顺手改（蓝图允许"注释可顺手改"）。

## 三、门禁结果（全绿，未触发断言修复）

| 门 | 命令 | 结果 | 证据 |
|---|---|---|---|
| 1 | `cargo check --workspace` | ✅ rc=0 | 冷缓存全量编译 ~7min（target/ 当时为 23:42 新建）；warm 复检 `Finished in 2.58s`，0 error（`gate1_check.log`/`gate1b_check.log`） |
| 2 | `cargo test -p craft-anything-ui-egui` | ✅ rc=0 | **220 passed / 0 failed / 1 ignored**（8 个 test binary 汇总，`gate2b_test_ui.log`）。smoke.rs 锁旧名断言与源串同改，keyset 一致性测试通过（含蓝图步骤 2.4 说明：xtask i18n-coverage 不存在，由该测试把关） |
| 3 | `cargo test -p craft-anything-ai` | ✅ rc=0 | **566 passed / 0 failed / 1 ignored**（550+16，`gate3_test_ai.log`） |

首两轮经 .bat 重定向的日志为空是 cmd 重定向异常（非编译异常），已改用 Python Popen 直接捕获重跑核实，EXIT 码与 warm-cache 复跑一致。

## 四、commit

```
93916ae  Rebrand for distribution: Anything Copy carries its own name and mark
         (git -c user.name=f99385331-art；信息为蓝图原文)
```

## 五、刻意不改（机器名 backlog，v0.2 处理）

- crate 包名/目录名全部 `craft-anything-*`；`craft-anything-cli` 及 `cargo build -p craft-anything-cli` 文案中的命令名
- `craft.json` / `.cany` 等文件格式名；`CRAFT_ANYTHING_*` 环境变量（含 `NO_KEYCHAIN_ENV`）
- `FLATPAK_SIGN_IN` 两处 + flatpak 数据路径（改了会破 mod.rs:1634-1636 锁定断言，蓝图明令）
- assets 全部文件名（含 `ai.storyteller.craft-anything.png` 目录名，保 Linux 打包链）
- `OriginalFilename`/`InternalName`（build.rs:19-20，仍 craft-anything.exe）
- 本批未触碰 crate：`crates/engine`(87 处)、`setup`(19)、`analysis`、`mcp`(3)、`platform`、`evidence`、`js`、`disasm`、`engines`；`examples/snapshot.rs`(2)；`.github/`(3)、`packaging/`(10)、`vendor/`(4)
- README.md 正文余 21 处（含"Download Craft Anything"按钮、`Documents/Craft Anything` 默认数据目录描述——后者与未改的 engine 路径一致，属机器名侧，随 v0.2 统一）

## 六、diffstat（git show --stat 93916ae）

```
 README.md                                          |  29 ++++++------
 apps/craft-anything-cli/src/main.rs                |  10 ++---
 apps/craft-anything-cli/src/setup_cmd.rs           |   2 +-
 apps/craft-anything-cli/tests/plugins.rs           |   2 +-
 apps/craft-anything-web/src/main.rs                |   2 +-
 apps/craft-anything-web/src/triage.rs              |   2 +-
 apps/craft-anything-web/src/viewer.rs              |   4 +-
 apps/craft-anything-web/src/web.rs                 |   2 +-
 apps/craft-anything/build.rs                       |   6 +--
 apps/craft-anything/src/main.rs                    |  14 +++---
 assets/app-icon/craft-anything-1024.png            | Bin 229301 -> 54638 bytes
 assets/app-icon/craft-anything.ico                 | Bin 73620 -> 16157 bytes
 assets/app-icon/craft-anything.svg                 |   7 ++-
 .../128x128/apps/ai.storyteller.craft-anything.png | Bin 15744 -> 6029 bytes
 .../16x16/apps/ai.storyteller.craft-anything.png   | Bin 754 -> 712 bytes
 .../24x24/apps/ai.storyteller.craft-anything.png   | Bin 1251 -> 1082 bytes
 .../256x256/apps/ai.storyteller.craft-anything.png | Bin 41035 -> 11565 bytes
 .../32x32/apps/ai.storyteller.craft-anything.png   | Bin 1943 -> 1511 bytes
 .../48x48/apps/ai.storyteller.craft-anything.png   | Bin 3517 -> 2300 bytes
 .../512x512/apps/ai.storyteller.craft-anything.png | Bin 99595 -> 27222 bytes
 .../64x64/apps/ai.storyteller.craft-anything.png   | Bin 5466 -> 3001 bytes
 .../apps/ai.storyteller.craft-anything.svg         |   7 ++-
 crates/ai/src/cli_agents/acp.rs                    |   2 +-
 crates/ai/src/cli_agents/adapters.rs               |  12 ++---
 crates/ai/src/cli_agents/adapters/aider.rs         |   2 +-
 crates/ai/src/cli_agents/adapters/copilot.rs       |   8 ++--
 crates/ai/src/cli_agents/adapters/dsh.rs           |   2 +-
 crates/ai/src/cli_agents/adapters/grok.rs          |   8 ++--
 crates/ai/src/cli_agents/grants.rs                 |   2 +-
 crates/ai/src/cli_agents/mod.rs                    |  14 +++---
 crates/ai/src/cli_agents/unfinished.rs             |   4 +-
 crates/ai/src/failure_log.rs                       |   2 +-
 crates/ai/src/keys.rs                              |   6 +--
 crates/ai/src/openai.rs                            |   2 +-
 crates/ai/src/prompt.rs                            |   2 +-
 crates/ai/src/rebuild/activity.rs                  |   2 +-
 crates/ai/src/rebuild/brief.rs                     |  24 +++++-----
 crates/ai/src/rebuild/check.rs                     |   4 +-
 crates/ai/src/rebuild/kinds/app.rs                 |   2 +-
 crates/ai/src/rebuild/kinds/mechanics.rs           |   4 +-
 crates/ai/src/rebuild/kinds/mod.rs                 |   2 +-
 crates/ai/src/rebuild/kinds/screenshot.rs          |   2 +-
 crates/ai/src/rebuild/kinds/self_test.rs           |   4 +-
 crates/ai/src/rebuild/mod.rs                       |   4 +-
 crates/ai/src/rebuild/question.rs                  |   2 +-
 crates/ai/src/rebuild/tests.rs                     |   4 +-
 crates/ai/src/rebuild/tools.rs                     |   6 +--
 crates/ai/src/ssh.rs                               |   2 +-
 crates/ui-egui/src/builders.rs                     |   2 +-
 crates/ui-egui/src/chat.rs                         |   2 +-
 crates/ui-egui/src/engine_ui.rs                    |  10 ++---
 crates/ui-egui/src/first_run.rs                    |   2 +-
 crates/ui-egui/src/folders.rs                      |   6 +--
 crates/ui-egui/src/fr.tsv                          |  50 ++++++++++-----------
 crates/ui-egui/src/glossary.rs                     |   4 +-
 crates/ui-egui/src/home.rs                         |   2 +-
 crates/ui-egui/src/i18n/cs.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/de.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/es.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/et.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/it.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/ka.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/ko.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/pt-br.tsv                  |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/ru.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/th.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/tr.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/vi.tsv                     |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/zh-hans.tsv                |  50 ++++++++++-----------
 crates/ui-egui/src/i18n/zh-hant.tsv                |  50 ++++++++++-----------
 crates/ui-egui/src/ja.tsv                          |  42 ++++++++---------
 crates/ui-egui/src/lib.rs                          |   4 +-
 crates/ui-egui/src/make.rs                         |   6 +--
 crates/ui-egui/src/manage.rs                       |   2 +-
 crates/ui-egui/src/menu.rs                         |  14 +++---
 crates/ui-egui/src/project.rs                      |   2 +-
 crates/ui-egui/src/report.rs                       |   2 +-
 crates/ui-egui/src/settings_ui.rs                  |   6 +--
 crates/ui-egui/src/titlebar.rs                     |   4 +-
 crates/ui-egui/src/usage.rs                        |   2 +-
 crates/ui-egui/tests/smoke.rs                      |   8 ++--
 docs/brand-note.md                                 |   6 +++
 docs/brand/LICENSE-brand.txt                       |  42 -----------------
 docs/brand/artcraft-logo-white.svg                 |   7 ---
 docs/brand/artcraft-logo.svg                       |   7 ---
 docs/brand/artcraft-mark-black.svg                 |   4 --
 docs/brand/artcraft-mark.svg                       |   4 --
 87 files changed, 552 insertions(+), 603 deletions(-)
```

## 七、遗留风险

1. **`craft-anything.icns` 仍是旧渡鸦图**（mac 分发前必须重制，v0.2 首项）。
2. **ico 真机核验**：任务栏/资源管理器小尺寸渲染需在 Windows 实机看一眼（PIL 生成合规，但未经 winres 嵌入后目检）。
3. **SERVICE 改名 = 老用户需重登一次 API key**（README banner 与 commit message 均已写明；OS 凭据库中旧 `ai.storyteller.craft-anything` 条目不会自动清理，用户可手动删除）。
4. **翻译版 README（10 个，185 处）** 与 **docs/ 其余 68 处** 仍带 ArtCraft logo 块与 docs/brand 死链——不影响代码/打包，属文档半换牌状态，v0.2 清扫；`NOTICE`/`ATTRIBUTION.md`/`assets/app-icon/LICENSE.txt` 中指向已删 `docs/brand/` 的文字性引用同样悬空（NOTICE 按蓝图一字不动）。
5. 提交尚未推送远端（本批只做本地 commit）。
