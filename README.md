# Anything Copy

<p>
  <img src="assets/app-icon/hicolor/256x256/apps/ai.storyteller.craft-anything.png" width="112" height="112" alt="Anything Copy icon">
</p>

> **Anything Copy** 是一个桌面工具：喂它一个网址或软件，它先**研究**（截图、读布局、看交互），再指挥你本机的 AI 编程代理**造出你自己的版本**，最后**逐项验收**。
>
> 本仓库是 [Craft Anything](https://github.com/storytold/craft-anything)（ArtCraft 团队，MIT OR Apache-2.0）的 fork，保留原许可，换用自有名称与图标。ArtCraft 与 Craft Anything 的名称权利归其所有者。

<p>
  <img alt="license" src="https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-2ea44f">
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-0078d4">
  <img alt="version" src="https://img.shields.io/badge/version-v0.1-8957e5">
  <img alt="fork" src="https://img.shields.io/badge/upstream-Craft%20Anything-6e7781">
</p>

---

## 这个 fork 修了什么

上游很好用，但遇到挫折会犯傻。v0.1 只做一件事：**治它的挫折反应**——全部来自真实事故复盘，每一处都有测试压着（`craft-anything-ai` 566 项、`craft-anything-ui-egui` 220 项全绿）。

| # | 病症（上游真实事故） | 处方 |
|---|---|---|
| 1 | 限流（HTTP 429）被报成"余额耗尽"，逼人去充值 | 以服务商原文措辞判类：限流→等一分钟自动续跑；真欠费→报欠费并给出重置时间 |
| 2 | 界面"装死"、暂停后留下僵尸施工队、审批卡片找不到 | 与 Hermes 改走 ACP 对讲机：进度实时流出、协作式取消、审批递到人手上 |
| 3 | 两个构建同时抢同一个项目 | 跨进程磁盘租约（`craft-lease.json`），第二次开工被挡在门外 |
| 4 | 构建失败后一夜自动重试几十轮，烧光整月额度 | 每轮构建 40 次对话预算熔断；停下来问人，你说继续才续 |
| 5 | 超长任务书触发 Windows 命令行长度上限，报 os error 206 | 发起前量长度，超限说人话 |

外加**全量换牌**：名称、窗口标题、图标（12 个尺寸自制）、15 国语言文案 789 处、README 归属声明。LICENSE 三件一字未动。

## 下载与安装

前往 [Releases](../../releases) 下载 `Anything-Copy-v0.1-win64.zip`：

1. 解压到任意文件夹
2. 双击 **启动 Anything Copy.bat**（或直接运行 `craft-anything.exe`）
3. Windows SmartScreen 蓝色提示 →「更多信息」→「仍要运行」（未购买代码签名证书，属正常现象）
4. 首次运行在 **设置 → AI** 里添加你的编码代理（如 Hermes Agent）和模型服务商

> ⚠️ 若你装过旧版 Craft Anything：凭据库服务名已更换，需要重新填入一次 API key。

## 命令行（无头模式）

`craft-anything-cli` 把引擎的全部能力做成子命令，整个"研究→构建→检查"流程可以无界面跑：

```bash
# 发现并注册可用的编码代理
craft-anything-cli ai detect
craft-anything-cli ai add "Hermes Agent" --kind agent_cli --model hermes --acp

# 从网址建一个新项目（--unattended：自动答问、拒绝越权审批）
craft-anything-cli rebuild https://example.com "做一个能离线运行的复刻版" \
  --backend "Hermes Agent" --unattended --rounds 1

# 续跑中断的项目
craft-anything-cli rebuild https://example.com --continue-in <项目文件夹>
```

每条工具同时是子命令：`craft-anything-cli commands` 列全部，`craft-anything-cli <工具> --help` 看参数。

## 仓库导览

| 目录 | 内容 |
|---|---|
| `apps/craft-anything` | 桌面应用（egui 原生窗口） |
| `apps/craft-anything-cli` | 命令行：全部工具 + MCP 服务 + 无头构建 |
| `apps/craft-anything-web` | WASM 网页版查看器 |
| `crates/engine` | 工具注册表、工作区、证据与反馈协议（27 个领域） |
| `crates/ai` | 构建环、适配器（claude/codex/opencode/hermes…）、失败分型、租约 |
| `crates/ui-egui` | 界面与 15 国语言 |
| `crates/mcp` | MCP 服务端 |
| `docs/` | 上游文档（格式、契约、扩展） |
| `docs/upstream-readme.md` | 上游原版 README（留存备查） |
| **`docs/audit/`** | **本 fork 的逐行审计报告、修复台账、交接书** |
| **`companion/anything-copy-mcp/`** | **MCP 观察哨：让任何 agent 远程查看/应答 Craft 项目** |
| **`companion/release-assets/`** | **打包辅助文件（启动 bat、中文说明）** |
| `assets/icons`, `assets/app-icon` | 界面图标与本 fork 自制应用图标 |

## 从源码构建

需要 Rust stable（MSVC 工具链）与 VS Build Tools：

```bash
cargo build --release -p craft-anything      # 桌面应用
cargo build --release -p craft-anything-cli  # 命令行
cargo test -p craft-anything-ai              # 构建环测试（566 项）
```

## 审计与改动记录

- 逐行审计（带文件:行号锚点）：[`batch1a-adapters-core.md`](docs/audit/batch1a-adapters-core.md)、[`batch1b-rebuild-core.md`](docs/audit/batch1b-rebuild-core.md)、[`batch1c-platform.md`](docs/audit/batch1c-platform.md)
- 修复台账 11 项（P0/P1/P2 分级）：[`FIX-PLAN-v1.md`](docs/audit/FIX-PLAN-v1.md)
- 交接书（版本状态、验证矩阵、续跑方法）：[`HANDOFF-2026-11-13.md`](docs/audit/HANDOFF-2026-11-13.md)
- 换牌记录：[`rebrand-v01.md`](docs/audit/rebrand-v01.md)
- 审计索引：[`docs/audit/README.md`](docs/audit/README.md)

与上游基线 `adeddc9`（2026-11-11）相比：本 fork 8 个自研 commit，净改动约 +1019/−609 行（全仓 34.6 万行文本的 0.47%）。

## 许可与商标

- 代码：[MIT](LICENSE) 或 [Apache-2.0](LICENSE-APACHE) 双许可，与上游一致；`NOTICE` 保留
- 名称与视觉：ArtCraft 名称、wordmark 与标志不在代码许可范围内，归其所有者。本 fork 已移除上游品牌资产，使用自有名称、图标与视觉；边界见 [`docs/brand-note.md`](docs/brand-note.md)
- 上游致谢：Craft Anything 由 [the ArtCraft team](https://github.com/storytold/craft-anything) 开发

## v0.2 路线（挂账中）

崩溃时孤儿进程兜底、包内机器名深改（crate 名 / exe 文件名）、P2 安全强化（DLL 劫持面、目录 fsync、崩溃一致性）、可回馈上游的通用修复（#1/#2/#4/#5）。
