# Gemini 4 Carbon 官方基准与安全防线评测：历史事实整理（增补报告 6）

**来源性质：** `anonymized_reported`，中英文双语归档，未独立复现（`independently_reproduced=false`）。
基于 Google DeepMind 于 `2026-10-28` 公开发布的 Gemini 4 Carbon 技术博客与官方评测卡（16 项核心能力基准 + 4 项网络安全与提示注入专项排行榜 + 对齐与反作弊指标）。
英文版见 [gemini-4-carbon.en.md](gemini-4-carbon.en.md)；
结构化数据见 [JSON](../../data/reported/gemini-4-carbon/report.json)、
[16 项能力基准 CSV](../../data/reported/gemini-4-carbon/benchmark_matrix.csv)、
[网络安全与红队专项 CSV](../../data/reported/gemini-4-carbon/cybersecurity_leaderboards.csv)、
[对齐与反作弊指标 CSV](../../data/reported/gemini-4-carbon/alignment_metrics.csv) 与
[可离线预览的 7 页 4:5 视觉卡片 HTML](../../examples/gemini-4-carbon-card-report/index.html)。

## 方法与发布边界

- **发布与获取限制（Fairwind Program）**：Gemini 4 Carbon 为 Gemini 4 系列面向复杂软件工程、代理长程执行与网络安全防御的前沿模型。由于其在自动化漏洞利用与长链攻防上的能力跨入关键能力阈值，Google DeepMind 采用通过 **Fairwind Program** 向安全防御者分阶段开放的受控发布策略。
- **定价口径**：延续与 Gemini 4 Argon 完全一致的首发定价：**输入 `$2.00 / 1M tokens`、输出 `$10.00 / 1M tokens`、缓存输入立减 `95%`（`$0.10 / 1M tokens`）**。
- **本地 Copilot CLI `A1–C4` 编码基准状态（零伪造原则）**：截至本归档日期，Gemini 4 Carbon 处于 Fairwind 受控预览阶段，尚未在公开 GitHub Copilot CLI CAPI `/models` 目录中开放调用。因此，十九模型编码基准（`A1–C4`，11 题 1,310 项隐藏断言）中的 Carbon 对应槽位显式记为 **`null`（`fairwind_preview_pending_cli`）**，严禁将任何估计值或 0 分填入对比分母。

## 16 项核心能力与长程 Agent 基准对比（5 大前沿模型）

下表汇总官方评测卡披露的 `Gemini 4 Carbon`、`Gemini 4 Argon`、`GPT-6 Astra`、`Claude Opus 5.5` 与 `Claude Fable 5.1` 横向结果（缺失/未披露项保留为 `null` / `—`）：

| 基准测试（Benchmark） | 评测口径与工具设置 | Gemini 4 Carbon | Gemini 4 Argon | GPT-6 Astra | Claude Opus 5.5 | Claude Fable 5.1 | Carbon 相对 Argon 提升 |
|---|---|---:|---:|---:|---:|---:|---:|
| **AA Index v5.0** | Artificial Analysis 综合指数（含工具） | **59 (#1)** | 50 | 57 | 58 | 49 | **+9 pts** |
| **Vals Index v2.2** | 企业级综合多模态基准 | **70.4% (#1)** | 69.2% | 65.0% | 70.2% | — (`null`) | **+1.2 pts** |
| **SWE-sweep** | mini-swe-agent 子任务奖励率 | **9.6% (#1)** | 4.3% | 9.5% | 3.6% | 2.9% | **+5.3 pts (2.23x)** |
| **FrontierSWE 2** | Proximal 公开排行榜 | 61.2% (#3) | 55.0% | **65.5% (#1)** | 62.3% (#2) | 56.3% | **+6.2 pts** |
| **Terminal-Bench 4.0 (AA)** | 终端命令行工程任务 | **65.2% (#1)** | 57.1% | 59.1% | 59.6% | 52.0% | **+8.1 pts** |
| **Agents' Last Exam v1.1** | 122 题，ALE-Claw，5 小时窗口 | **77.4% (#1)** | 69.0% | 73.1% | 71.6% | — (`null`) | **+8.4 pts** |
| **OSWorld-2.1** | 82 题离线子集，max@3 | 81.5% (#2) | 74.7% | 80.9% | **87.2% (#1)** | 76.8% | **+6.8 pts** |
| **AutomationBench** | Zapier 私有工作流评测集 | **53.9% (#1)** | 51.3% | 41.4% | 42.5% | 31.4% | **+2.6 pts** |
| **Vending-Bench 2** | Andon Labs 期末银行账户余额 ($) | **$16,484 (#1)** | $13,718 | $15,515 | $9,235 | $5,422 | **+$2,766 (+20.2%)** |
| **Chartography** | Surge 复杂图表解析（无工具） | **72.5% (#1)** | 71.6% | 71.0% | 66.3% | 46.2% | **+0.9 pts** |
| **Blueprint-Bench 2** | Andon Labs 工程蓝图相似度 | **58.6% (#1)** | 54.4% | 49.7% | 51.2% | 41.9% | **+4.2 pts** |
| **GraphWalks** | 256k–1M 上下文，200 题 BFS F1 | **96.2% (#1)** | 84.2% | 71.8% | 66.8% | 65.0% | **+12.0 pts** |
| **RiemannBench** | Surge 高等数学与证明 | **80.0% (#1)** | 76.0% | 72.0% | 69.6% | 65.6% | **+4.0 pts** |
| **Terminal-Bench-Science 0.1** | AA 科学计算终端任务 | **64.8% (#1)** | 52.9% | 63.3% | 59.0% | 43.3% | **+11.9 pts** |
| **CWE-bench** | Collinear Pass@1（平局按 Pass@4） | **71.0% (#1)** | 68.0% | 68.0% | 67.0% | 58.0% | **+3.0 pts** |
| **ExploitGym** | Antigravity 因果通过率（10h / 6h） | **54.8% / 53.5% (#1)** | 42.0% / 39.5% | 42.4% (无时限) | 34.5% (6h) | — (`null`) | **+12.8 pts / +14.0 pts** |
| **SEC-bench Pro** | 183 个 JS 引擎任务，Pass@1 三次均值 | **88.2% (#1)** | 83.4% | 85.4% | — (`null`) | — (`null`) | **+4.8 pts** |
| **WebDev Arena** | 盲测 Elo 评分 | **1768 (#4)** | 1679 | — (`null`) | — (`null`) | — (`null`) | **+89 Elo** |

**汇总事实：** 在上述 16 项主基准矩阵（外加 ExploitGym 与 WebDev Arena 扩展项）中，`Gemini 4 Carbon` 夺得 **14 项第一**；仅在 `FrontierSWE 2`（`61.2%`，位列 `GPT-6 Astra` `65.5%` 与 `Claude Opus 5.5` `62.3%` 之后居 #3）和 `OSWorld-2.1`（`81.5%`，位列 `Claude Opus 5.5` `87.2%` 之后居 #2）上未居榜首。

## 网络安全、漏洞修复与提示注入专项排行榜

### 1. `SEC-bench Pro`（183 个 JavaScript 引擎真实漏洞任务，Pass@1 三次运行均值，Antigravity 框架）

| 排名 | 模型 | Pass@1 均值 (%) |
|---:|---|---:|
| 1 | **Gemini 4 Carbon** | **88.2%** |
| 2 | GPT-6 Astra | 85.4% |
| 3 | Gemini 4 Argon | 83.4% |
| 4 | GPT-6.1 Terra | 83.3% |
| 5 | GPT-6.1 Sol | 78.8% |
| 6 | MiMo-V2.6-Pro | 66.3% |
| 7 | DeepSeek-V4.1-Flash | 62.8% |
| 8 | DeepSeek-V4-Pro | 56.4% |

### 2. `ExploitGym`（Causal Pass Rate 因果通过率，区分时间上限）

| 排名 | 模型与时间预算配置 | 因果通过率 (%) |
|---:|---|---:|
| 1 | **Gemini 4 Carbon (10h)** | **54.8%** |
| 2 | **Gemini 4 Carbon (6h)** | **53.5%** |
| 3 | GPT-6 Astra (No time cap / 无时间上限) | 42.4% |
| 4 | Gemini 4 Argon (10h) | 42.0% |
| 5 | Gemini 4 Argon (6h) | 39.5% |
| 6 | GPT-6.1 Sol (No time cap / 无时间上限) | 35.1% |
| 7 | Claude Opus 5.5 (6h) | 34.5% |
| 8 | Claude Mythos 5.1 (6h) | 30.4% |
| 9 | MiMo-V2.6-Pro (Unknown time cap) | 17.8% |
| 10 | GLM-5.3 (6h) | 15.0% |

### 3. `CWE-bench`（Collinear Pass@1，平局按 Pass@4 决胜，标注 Agent 框架）

| 排名 | 模型 | Agent 框架 | Pass@1 (%) |
|---:|---|---|---:|
| 1 | **Gemini 4 Carbon** | Antigravity | **71.0%** |
| 2 | Grok 4.7 | opencode | 68.0% |
| 2 | Gemini 4 Argon | Antigravity | 68.0% |
| 2 | GPT-6 Astra | Codex | 68.0% |
| 5 | Claude Opus 5.5 | Claude Code | 67.0% |
| 6 | Claude Fable 5.1 | Claude Code | 58.0% |
| 7 | Grok 4.6 | opencode | 57.0% |
| 8 | DeepSeek-V4-1-Flash | opencode | 55.0% |
| 8 | Muse Spark 1.3 | opencode | 55.0% |
| 10 | Hy4 Preview | opencode | 53.0% |
| 11 | GPT-6 Sol | Codex | 52.0% |

### 4. `Gray Swan IPI`（间接提示注入攻击成功率，`k=15` 次尝试，**越低越好**）

| 排名 | 模型 | `k=15` 攻击成功率 (%) | 防御表现 |
|---:|---|---:|---|
| 1 | **Gemini 4 Carbon** | **0.0%** | **15 次红队尝试零失守** |
| 2 | Gemini 4 Argon | 0.7% | 亚百分位鲁棒 |
| 3 | Claude Opus 5.5 | 1.0% | 强防御 |
| 3 | Claude Fable 5.1 | 1.0% | 强防御 |
| 5 | Claude Opus 5 | 4.6% | 中高防御 |
| 6 | Gemini 3.8 Flash | 5.5% | 中高防御 |
| 7 | Gemini 3.8 Flash Cyber | 6.0% | 中高防御 |
| 8 | GPT-6 Astra | 8.5% | 存在注入风险 |
| 9 | GPT-6.1 Sol | 8.6% | 存在注入风险 |
| 10 | Muse Spark 1.3 | 15.9% | 中度脆弱 |
| 11 | GLM 5.3 | 31.5% | 高度脆弱 |
| 12 | Grok 4.6 | 51.8% | 过半攻击得手 |
| 13 | Kimi K3 | 52.7% | 过半攻击得手 |

## 对齐、诚实度与反奖励黑客（Anti-Cheating）指标

官方技术报告同时披露了针对 Agent 环境作弊、越界执行与虚构声明的专项对齐审计：

| 评估维度 | Gemini 4 Carbon 报告值 | 相对参照系变化 |
|---|---|---|
| **Terminal-Bench 4.0 作弊成功率** | **0.0%**（尝试率仅 **0.4%**） | 彻底阻断测试集硬编码与验证器篡改 |
| **内部真实编码高危失调告警（High-severity misalignment alerts）** | **-80%** | 相比前代基线降低 80% |
| **无根据声明率（Unsupported claims）** | **-50%**（`~2x` 削减） | 相比 Gemini 4 Argon 减少约一半 |
| **代理越权操作率（Overreach）** | **-26%** | 相比 Gemini 4 Argon 降低 26% |
| **任务欠服务率（Under-service / 过度拒绝）** | **-29%** | 在提升安全性的同时减少无效拒答 |
| **安全代码生成率（Secure code generation）** | **>2x** | 相比 Gemini 4 Argon 提升逾 2 倍 |
| **Chrome 真实漏洞补丁质量（Chrome patch quality）** | **>10x** | 相比竞品前沿模型高出 10 倍以上 |

## 适用边界与方法限制

- **适用场景（Good fit）**：长上下文代码库跨文件遍历（`256k–1M` `GraphWalks` `96.2%`）、复杂终端与科学计算 Agent（`Terminal-Bench 4.0` `65.2%`、`Agents' Last Exam` `77.4%`）、高对抗环境下的间接提示注入防御（`Gray Swan IPI` `0.0%`）以及获准加入 Fairwind Program 后的自动化漏洞定位与补丁生成（`SEC-bench Pro` `88.2%`）。
- **不适用场景（Not for）**：当前需要立即通过公开自助 API / Copilot CLI 无门槛调用的流水线（需申请 Fairwind 权限）、纯桌面 GUI 视觉点击任务中追求绝对极限单点分数的场景（`OSWorld-2.1` 上 `Claude Opus 5.5` `87.2%` 仍领先 Carbon `81.5%`）。
- **方法限制**：各外部基准使用的 Agent 脚手架不尽相同（例如 `CWE-bench` 中 Carbon/Argon 使用 `Antigravity`、Astra/Sol 使用 `Codex`、Claude 使用 `Claude Code`、开源模型使用 `opencode`；`ExploitGym` 中不同模型的时间上限存在 `6h`、`10h` 与 `No time cap` 差异）。因此跨模型对比反映的是“模型 + 评测脚手架 + 时间预算”的联合系统表现，不能简单等同于裸模型在统一 Harness 下的受控对照实验。
