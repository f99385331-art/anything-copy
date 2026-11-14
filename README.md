# Anything Copy

<p>
  <img src="assets/app-icon/anything-copy.png" width="112" height="112" alt="Anything Copy icon">
</p>

**Anything Copy 是一个"看懂→复刻"的桌面工具。** 给它一个网址、一款软件或一个游戏，它会先**研究**（截图、读布局、分析交互），再指挥你本机的 AI 编程代理**造出一个属于你自己的版本**，最后**逐项验收**打分。

适合这些人：想把一个网站变成自己能改的版本、想照着某个软件做教具/原型、想学结构而不是抄代码。

<p>
  <img alt="license" src="https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-2ea44f">
  <img alt="platform" src="https://img.shields.io/badge/platform-Windows-0078d4">
  <img alt="version" src="https://img.shields.io/badge/version-v0.1-8957e5">
  <img alt="lang" src="https://img.shields.io/badge/lang-15%20languages-6e7781">
</p>

---

## 它怎么工作

1. **研究**：打开目标，逐页截图，展开菜单与弹窗，读页面行为，把每一屏的证据存进项目文件夹
2. **构建**：把证据装订成任务书，交给本机的 AI 编程代理（Hermes / Claude Code / Codex / OpenCode 等）照单施工
3. **检查**：拿你的版本与目标逐项对比（布局、配色、字体、内容），给出相似度与差距清单
4. **就绪**：反复打磨到达标，交给你一个可以本地运行的完整项目

全程你只在它举手提问（比如"登录后的页面要不要也研究"）时答话。

## 已内置的工程质量

v0.1 修掉了五类真实踩过的坑，每一处都有测试压着（`craft-anything-ai` 566 项、`craft-anything-ui-egui` 220 项全绿）：

| # | 场景 | 现在怎么处理 |
|---|---|---|
| 1 | 模型服务商限流（HTTP 429） | 按服务商原文措辞判类：限流→等一分钟自动续跑；真欠费→报明并给出重置时间 |
| 2 | 构建中界面像"卡死"、暂停后进程残留 | 与代理走 ACP 协议：进度实时流出、暂停真正停下、审批递到人手上 |
| 3 | 两个构建同时抢同一个项目 | 跨进程磁盘租约（`craft-lease.json`），第二次开工被挡在门外 |
| 4 | 失败后一夜自动重试几十轮、额度烧光 | 每轮构建 40 次对话预算熔断；停下来问你，你说继续才续 |
| 5 | 超长任务书触发 Windows 命令行长度上限 | 发起前先量长度，超限用大白话报错 |

## 下载与安装

前往 [Releases](../../releases) 下载 `Anything-Copy-v0.1-win64.zip`：

1. 解压到任意文件夹
2. 双击 **启动 Anything Copy.bat**（或直接运行 `craft-anything.exe`）
3. Windows SmartScreen 蓝色提示 →「更多信息」→「仍要运行」（未购买代码签名证书，属正常现象）
4. 首次运行在 **设置 → AI** 里添加你的编码代理（如 Hermes Agent）和模型服务商

项目文件默认存放在 `文档\Anything Copy\<项目名>\`：`craft.json`（任务书）、`build-activity.log`（施工流水）、`capture/`（证据截图）、`app/`（成品）。

## 命令行（无头模式）

`craft-anything-cli` 把引擎的全部能力做成子命令，"研究→构建→检查"可以完全无界面跑：

```bash
# 发现并注册可用的编码代理
craft-anything-cli ai detect
craft-anything-cli ai add "Hermes Agent" --kind agent_cli --model hermes --acp

# 从网址建一个新项目（--unattended：自动答问、拒绝越权审批）
craft-anything-cli rebuild https://example.com "做一个能离线运行的复刻版" \
  --backend "Hermes Agent" --unattended --rounds 1

# 续跑中断的项目
craft-anything-cli rebuild https://example.com --continue-in <项目文件夹>

# 每个工具都是子命令
craft-anything-cli commands              # 列出全部工具
craft-anything-cli <工具名> --help       # 看参数
```

## 仓库导览

| 目录 | 内容 |
|---|---|
| `apps/craft-anything` | 桌面应用（原生窗口） |
| `apps/craft-anything-cli` | 命令行：全部工具 + MCP 服务 + 无头构建 |
| `apps/craft-anything-web` | WASM 网页版查看器 |
| `crates/engine` | 工具注册表、工作区、证据与反馈协议（27 个领域） |
| `crates/ai` | 构建环、代理适配器、失败分型、租约 |
| `crates/ui-egui` | 界面与 15 国语言文案 |
| `crates/mcp` | MCP 服务端（给外部 agent 用） |
| `docs/` | 数据格式、契约、扩展开发文档 |
| `docs/audit/` | 逐行审计报告、修复台账、交接书（工程记录） |
| `companion/anything-copy-mcp/` | MCP 观察哨：让任何 agent 远程查看/应答构建项目 |
| `companion/release-assets/` | 打包辅助文件（启动 bat、中文说明） |
| `assets/icons`、`assets/app-icon` | 界面图标与应用图标 |

## 从源码构建

需要 Rust stable（MSVC 工具链）与 VS Build Tools：

```bash
cargo build --release -p craft-anything      # 桌面应用
cargo build --release -p craft-anything-cli  # 命令行
cargo test -p craft-anything-ai              # 构建环测试（566 项）
```

构建时带上 `CRAFT_FONTS_DIR=<字体仓库路径>` 可内嵌多语言字体（含中日韩）；不带则中文会显示为方块。

## 许可

代码以 [MIT](LICENSE) 或 [Apache-2.0](LICENSE-APACHE) 双许可发布；版权与许可声明见 `NOTICE` 与 `ATTRIBUTION.md`。

## 路线图

- v0.2：崩溃时进程清理兜底、安全强化（动态库搜索面、目录 fsync、崩溃一致性）
- 新界面（开发中）：iOS/macOS 风格液态玻璃新壳，独立工程，引擎不变
