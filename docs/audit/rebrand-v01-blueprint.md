# Anything Copy 换牌施工蓝图 v0.1（代理照此执行，勿自行探索）

仓：C:\Users\Murphy\projects\craft-anything-src 分支 anything-copy HEAD 9ec0ad8。
cargo 绝对路径 C:\Users\Murphy\.cargo\bin\cargo.exe；长命令一律 subprocess+重定向日志。
原则：只做用户可见身份；机器名（crate 包名、craft-anything-cli、文件格式名）本批不动。

## 步骤 1：写并跑一个施工脚本（scratch 目录），机械替换清单如下

### 1a. 窗口与版本信息
- apps/craft-anything/build.rs:16-18
  - ProductName "Craft Anything" → "Anything Copy"
  - FileDescription → "Anything Copy: find out how any software works"
  - LegalCopyright → "Copyright (c) the ArtCraft Team and the Craft Anything contributors; fork (c) Murphy. MIT OR Apache-2.0."
- apps/craft-anything/src/main.rs:82 `.with_title("Craft Anything")` → `.with_title("Anything Copy")`
- apps/craft-anything/src/main.rs:83 `.with_app_id("ai.storyteller.craft-anything")` → `.with_app_id("dev.murphy.anything-copy")`
- main.rs:1 文档注释与 main.rs:63 注释里的 "Craft Anything" → "Anything Copy"（仅注释文案）

### 1b. 身份常量（README 迁移说明里写清：老用户需重登 API key）
- crates/ai/src/keys.rs:13 SERVICE = "ai.storyteller.craft-anything" → "dev.murphy.anything-copy"
  - 注意：该 SERVICE 是系统凭据库的服务名；改了以后旧存 key 读不到属预期。跑该 crate 相关测试，若有测试锁死旧字符串，按测试语义更新（先 grep "ai.storyteller" crates/ai/src/keys.rs 附近与 tests）。
- crates/ai/src/cli_agents/mod.rs:495,500 FLATPAK_SIGN_IN 里 `ai.storyteller.craft-anything` 与路径 `$XDG_DATA_HOME/craft-anything/claude`：**不改**（flatpak 机器名，v0.2 随包名统一改；改了会破测试 1634-1636 的锁定断言）。

### 1c. 图标内容替换（保持文件名与路径不动！）
- 用 Pillow（host python 3.14，已装）画新图标：圆角方块、深海军蓝 #101c3d 底、白色粗字母 "A"（几何无衬线，笔画等宽），输出：
  - assets/app-icon/hicolor/256x256/apps/ai.storyteller.craft-anything.png（覆盖，256x256）
  - assets/app-icon/ 下同 app-icon 目录里其他尺寸 png 一并覆盖（先 ls hicolor 全尺寸列表，逐个重画同图不同尺寸）
  - assets/craft-anything.ico（覆盖；用 PIL 从 256 PNG 生成含 16/32/48/256 的 ico）
  - assets/craft-anything-1024.png（覆盖 1024 版）
  - assets/craft-anything.svg（重写为同设计的矢量圆角方块+A）
  - craft-anything.icns：跳过（mac 用不到；v0.2）
- crates/ui-egui/src/lib.rs:2085 include_bytes! 路径不动（文件已换新图）。

### 1d. 品牌资产与 README
- git rm -r docs/brand/（README 是主要引用者；删后 cargo check 若报引用再处理）
- README.md 顶部两个 <p align=center> 品牌块（ArtCraft logo 段 + raven 图标段 alt 文案）替换为：
  - 保留图标 <p>，alt 改 "Anything Copy icon"，srcset/logo 的 ArtCraft <picture> 块整体删除
  - 紧随其后加一段 fork banner：
    ```
    > **Anything Copy** is a fork of [Craft Anything](https://github.com/storytold/craft-anything) by the ArtCraft team.
    > ArtCraft and Craft Anything are names of their respective project — all rights belong to their owners.
    > Code stays MIT OR Apache-2.0; this fork ships its own icon and name. See docs/brand-note.md for the trademark boundary.
    ```
- docs/brand-note.md 新建（3-5 行，写上面这个边界 + docs/brand 已删）；README 里原指向 docs/brand/ 的链接（grep 一下）改指 brand-note.md。
- LICENSE / LICENSE-APACHE / NOTICE：**一字不动**。

### 1e. UI 用户可见英文源串（32 处，逐文件）
规则：只改**面向用户的字符串字面量**里的产品名 "Craft Anything"→"Anything Copy"；
注释可顺手改（无害）；标识符/路径/凭据键/craft.json 一律不动；动词短语 "craft" 不动；
"Craft Anything contributors"（版权行）、测试里锁定上游文案的断言，先跑测试红了再看语义。
文件清单（grep -c 已数）：
builders.rs:1 chat.rs:1 demo.rs:1 engine_ui.rs:5 first_run.rs:1 folders.rs:3 glossary.rs:2 home.rs:1 lib.rs:2 make.rs:3 manage.rs:1 menu.rs:7（共 17 rs，含未列全的——以 `grep -rl "Craft Anything" crates/ui-egui/src --include=*.rs` 全列表为准）+ crates/ai/src 15 处（同样以 grep 全列表为准）+ apps/craft-anything-cli、apps/craft-anything-web 若有 --help/usage 文案也改。
i18n TSV（14 个文件）：
- 第一列（English key）里的 "Craft Anything" → "Anything Copy"（脚本处理，14 文件同步，key 集一致性由现有测试把关）
- 第二列译文：仅把其中**西文产品名 token** "Craft Anything" 换成 "Anything Copy"；译名（如 zh-hans 若有"手造万物"类）不动；zh-hans.tsv 有 25 处含 "Craft Anything"，多为英文原文夹带。
- **key 与文件同改**：先改 TSV 第一列，再改 Rust 源串——两边必须同一 commit。

## 步骤 2：门禁（全绿才许 commit）
1. cargo check --workspace（日志重定向）
2. cargo test -p craft-anything-ui-egui
3. cargo test -p craft-anything-ai
4. xtask i18n-coverage 不存在（tools/xtask/src/codegen.rs 只有 check_tools）——改跑 ui-egui 测试里的 keyset 一致性测试（第 2 步已覆盖；报告写明）
测试若红：读断言，属于"锁旧产品名"的按新名更新断言；属于行为回归的停下别 commit，报告卡点。

## 步骤 3：一次 commit
git -c user.name="f99385331-art" commit -m "Rebrand for distribution: Anything Copy carries its own name and mark

Distributing a fork under the upstream name and raven mark would present it as
ArtCraft's product, which the brand license does not allow. The window title,
version-info, saved-keys service and icons now say Anything Copy; docs/brand
and the README logo block are replaced by an attribution banner. Machine names
(crates, craft.json, the CLI) keep upstream spellings until v0.2 — renaming
those is a mechanical follow-up, this commit is the legal boundary.

Existing installs: API keys stored under the old service name need one re-login."

## 步骤 4：报告 ~/projects/anything-copy-audit/reports/rebrand-v01.md
改动清单（脚本 diffstat 粘贴）、刻意不改清单（机器名 backlog：crate 包名、craft-anything-cli、FLATPAK_SIGN_IN、assets 文件名、.icns）、测试结果、commit hash、遗留风险（.icns 旧图仍在、ico 需真机看、SERVICE 改名要重登）。
