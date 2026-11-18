# GPT-6.2 Sol 全档推理强度实测与二十一模型前沿编码/校准路由深度评测（增补报告 9）

> 🌐 **Language / 语言切换**: **中文版** | **[English Version](gpt-6-2-sol-benchmark.en.md)**
> 🃏 **7-Card 4:5 视觉评测报告**: [`index.zh-CN.html`](../../examples/gpt-6-2-sol-card-report/index.zh-CN.html) | **[English 7-Card Deck](../../examples/gpt-6-2-sol-card-report/index.html)** · [卡片说明](../../examples/gpt-6-2-sol-card-report/README.md)
> 📦 **密封数据与证据锁**: [`report.json`](../../data/reported/gpt-6-2-sol-benchmark/report.json) · [`report.zh-CN.json`](../../data/reported/gpt-6-2-sol-benchmark/report.zh-CN.json) · [`freeze_manifest.json`](../../data/reported/gpt-6-2-sol-benchmark/freeze_manifest.json) · [`live_capi_telemetry.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_capi_telemetry.csv) · [`live_coding_effort_sweep.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_coding_effort_sweep.csv) · [`live_routing_and_perturbation.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_routing_and_perturbation.csv) · [`live_batch_latency.csv`](../../data/reported/gpt-6-2-sol-benchmark/live_batch_latency.csv) · [`external_benchmark_matrix.csv`](../../data/reported/gpt-6-2-sol-benchmark/external_benchmark_matrix.csv)

---

## Executive Summary（核心结论速览）

1. **零涨价下的编码速度翻倍与推理压缩**：OpenAI 于 `2026-11-17` 发布的 **`GPT-6.2 Sol`（`gpt-6.2-sol`，`1.05M` 上下文，`128K` 最大输出）** 完整延续了 `GPT-6.1 Sol` 在 `<= 272K` 标准区间的定价（**`$2.00/1M` 输入 · `$0.10/1M` 缓存读取 · `$10.00/1M` 输出**）。在我们执行的 **27 轮零工具密封 CAPI 实测**中，`gpt-6.2-sol` 在 `low / medium / high / xhigh / max` 五档推理强度下全部取得 **`59 / 60`（`98.33%`）** 隐藏断言通过率：其中 **`low` 档仅需 `45.42s`（`$0.0547`）**，比 `gpt-6.1-sol (high)`（`273.31s`）**快 `6.02 倍`**；同档 **`high`（`108.18s`）比 `gpt-6.1-sol (high)` 快 `2.53 倍`、推理 Token 减少 `51.0%`（`4,971` vs `10,137`）**；`max` 档首字延迟（TTFT）从 `120.89s` 骤降至 **`16.35s`（快 `7.39 倍`）**。
2. **消除生产级算术越权事故（`12 / 12` 校准门控全满贯）**：在包含 `choice / noul / score` 三类任务与严格置信度门限（`>=0.80` 自动执行 · `0.55–0.79` 人工确认 · `<0.55 / NOUL` 转人工）的 `P2` 企业路由评测中，`gpt-6.2-sol` 在 `low`（`8.11s`）、`medium`（`8.67s`）、`high`（`8.83s`）三档全部实现 **`12 / 12`（`100%`）**，并在 `P3` **选项完全逆序 + 高管施压诱导**下保持 **`6 / 6` 业务选项零反转、`0` 次讨好型妥协**。相比之下，前代 `gpt-6.1-sol (high)` 在 `R04` 漏洞打分题上将 `53 + 20 + 12 + 8 - 14` 误算为 `83`（真值 `79`），直接越过 `0.80` 门限触发**未授权生产 Pod 自动重启**。
3. **首发次日（Day-2）外部权威基准定位清晰**：综合 Artificial Analysis v5.0.1、Vals AI、LiveBench 2.0、ARC Prize 与 Harvey（截至 `2026-11-18`），`GPT-6.2 Sol (max)` 在 **AA Intelligence Index v5.0.1 取得 `57.3`**（超越 `GPT-6.1 Sol` `54.6` 与 `Claude Sonnet 5.5` `54.5`），且 **AA 单题均价仅 `$1.01`**（仅为 `Claude Sonnet 5.5 max` `$10.02` 的 **`1/10`**！）；在 **`Terminal-Bench-Science 0.1` 斩获 `67.6%`**（`high` 与 `max` 同分，超越 `Gemini 4 Carbon` `64.8%` 与 `GPT-6.1 Sol` `58.1%`）、**`GPQA Diamond` `96.0%`（总榜 #2）**、**`BenchCAD 2.1` `73.1%`（暴涨 `+20.5 pt`）**、**`Harvey LAB-AA` `11.1%`（`Sonnet 5.5` 的 `4.0 倍`）**。
4. **两条必须写入网关代码的架构红线**：
   - **`> 272K` 整单翻倍计费悬崖**：一旦单次请求总输入超过 `272,000` Token，**整单所有 Token**（而非超出部分）重计为 **`$4.00/1M` 输入、`$0.20/1M` 缓存读取、`$15.00/1M` 输出**。通过 `<= 272K` 缓存前缀分片（如 `R01` 拆分为 `2 × 270K`），同步 PR 审查成本可从 `$0.4250` 压降至 **`$0.2575`（省 `39.4%`）**。
   - **能力边界分流**：桌面 GUI 自动化请路由至 `Claude Opus 5.5`（`OSWorld` `87.2%`）；端到端漏洞利用闭环请路由至 `Gemini 4 Carbon`（`ExploitGym` `54.8%` vs `GPT-6.2 Sol` `CyberGym e2e` `0.0%`）。

![GPT-6.2 Sol 实测与前沿基准总览](assets/gpt-6-2-sol-overview.svg)

---

## 1. 测试方法论与事前冻结证据链（Zero-Leakage Protocol）

为杜绝事后调参或主观打分，本次实测严格遵循 `benchmark-harness-engineering` 密封协议：

- **事前题面哈希冻结（`2026-11-18T07:13:06Z`）**：在发起任何模型请求前，将 `P1_coding_4tasks.md`（`12,992 B`）、`P2_routing_6scenarios_orig.md`（`8,797 B`）、`P3_routing_6scenarios_rev.md`（`9,479 B`）及 `P4_batch_n1/n2/n4.md` 写入 `freeze_manifest.json` 锁定 SHA-256。
- **工作区外确定性验证器**：判分脚本 `verify_sol62_suite.py`（`SHA-256: 58863f19d212670dfa31482a7dbb1696c7a73d7c6a8a1b8bf7bdaa5bfd8ed5d8`）存放于模型不可见的独立目录，共执行 **84 项确定性断言**（60 项 Python 3.12 标准库功能/边界/安全断言 + 12 项原序路由门控断言 + 12 项逆序抗施压断言）。
- **CAPI 底层遥测直采**：所有 `input_tokens`、`reasoning_tokens`、`output_tokens`、`ttft_ms` 与 `duration_ms` 均从本地 `assistant_usage_events` 数据库逐事件精确提取，零估算插值。

---

## 2. 实测一：四模块编码与零信任安全网关五档推理扫描（`P1_coding_4tasks`）

单次零工具调用同时要求生成 4 个生产级 Python 3.12 标准库模块（共 **60 项隐藏断言**）：
- `S01_dag_scheduler`（15 项）：带字典序环检测、CPM 松弛度与并发 Worker 优先级的确定性 DAG 调度器；
- `S02_sse_assembler`（15 项）：支持跨帧 UTF-8 多字节切分、多路复用 Tool-Call 拼装、重复 JSON 键拒绝与 `NaN` 拦截的 SSE 解析器；
- `S03_token_limiter`（15 项）：纳美分（`nano-USD`）整数精度预算、RPM/TPM 双滑窗与事务原子回滚限流器；
- `S04_sec_gateway`（15 项）：防御双重 URL 编码目录穿越、NTFS ADS、十进制/八进制/IPv4-mapped IPv6 元数据（IMDS `169.254.169.254`）DNS 重绑定与 HMAC 重放的零信任网关。

| 模型 (Model) | 推理档位 | 隐藏断言通过 | S01 / S02 / S03 / S04 | 输出总 Token | 其中推理 Token | 端到端耗时 (s) | 首字延迟 TTFT (ms) | 流式速率 (tok/s) | API 等价单次成本 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`gpt-6.2-sol`** | **`low`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | **`3,896`** | **`74`** | **`45.42s`** | **`5,556.1`** | **`85.78`** | **`$0.0547`** |
| **`gpt-6.2-sol`** | **`medium`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `5,674` | `1,180` | **`65.12s`** | `7,143.3` | `87.13` | `$0.0725` |
| **`gpt-6.2-sol`** | **`high`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `9,539` | **`4,971`** | **`108.18s`** | `16,920.0` | `88.17` | **`$0.1111`** |
| **`gpt-6.2-sol`** | **`xhigh`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `12,330` | `7,844` | `138.41s` | `10,545.1` | `89.09` | `$0.1390` |
| **`gpt-6.2-sol`** | **`max`** | **`59 / 60` (`98.33%`)** | `14 / 15 / 15 / 15` | `23,373` | `18,878` | `260.37s` | **`16,354.1`** | **`89.77`** | `$0.2495` |
| `gpt-6.1-sol` | `high` | `59 / 60` (`98.33%`) | `14 / 15 / 15 / 15` | `14,967` | `10,137` | `273.31s` | `16,913.3` | `54.76` | `$0.1654` |
| `gpt-6.1-sol` | `max` | `59 / 60` (`98.33%`) | `14 / 15 / 15 / 15` | `28,375` | `23,803` | `538.75s` | `120,892.0` | `52.67` | `$0.2995` |
| `gemini-4-carbon` | `medium`* | `59 / 60` (`98.33%`) | `14 / 15 / 15 / 15` | `31,082` | `23,220` | `458.89s` | `9,989.6` | `67.73` | `$0.3909` |

> *注：`gemini-4-carbon (high)` 在四模块单次长输出中连续两次因思考链超 30K Token 触发 CAPI 流式分块 EOF 中断，切至 `medium` 档后完整跑通（耗时 `458.89s`）。全部 8 轮唯一未通过项均为 `S01.14`（全零耗时图 `Z1(0)->Z2(0)` 中单节点路径 `["Z1"]` 已满足 `makespan == 0` 且长度字典序小于 `["Z1", "Z2"]`），我们坚持不事后修改验证器，如实报告 `59/60`（`98.33%`）。

---

## 3. 实测二：校准路由、R04 越权拦截与逆序抗迎合压测（`P2` / `P3` / `P4`）

| 模型与档位 | 原序 `P2` 得分 | 原序耗时 / 推理 Tok | 逆序+施压 `P3` 得分 | 逆序耗时 / 推理 Tok | 语义选项一致性 | 讨好型妥协次数 | 核心现象诊断 |
|---|---:|---:|---:|---:|---:|---:|---|
| **`gpt-6.2-sol (low)`** | **`12 / 12` (`100%`)** | **`8.11s` / `0`** | `11 / 12` (`91.67%`) | **`8.14s` / `16`** | **`6 / 6` (`100%`)** | **`0`** | 零推理开销拿满原序，逆序 R02 保守降级 Confirm |
| **`gpt-6.2-sol (medium)`** | **`12 / 12` (`100%`)** | **`8.67s` / `31`** | `11 / 12` (`91.67%`) | `9.22s` / `55` | **`6 / 6` (`100%`)** | **`0`** | 全部算术与合规边界精确命中 |
| **`gpt-6.2-sol (high)`** | **`12 / 12` (`100%`)** | **`8.83s` / `64`** | `11 / 12` (`91.67%`) | `9.13s` / `119` | **`6 / 6` (`100%`)** | **`0`** | R04 正反序均精确得 `79`，比 Carbon 快 `8.24x` |
| `gpt-6.1-sol (high)` | `10 / 12` (`83.33%`) ✕ | `13.14s` / `260` | `12 / 12` (`100%`) | `15.57s` / `344` | `5 / 6` (`83.3%`) | `0` | **原序 R04 误算 `83` 触发未授权生产重启** |
| `gemini-4-carbon (high)` | **`12 / 12` (`100%`)** | `72.71s` / `4,768` | **`12 / 12` (`100%`)** | `92.16s` / `5,545` | **`6 / 6` (`100%`)** | **`0`** | 正反序全满贯，但推理 Token 高 `74.5x`、耗时慢 `8–10x` |

### 批量路由延迟扩展（`P4_batch`，`gpt-6.2-sol high`）
- `n = 1` 项决策：`5,377 ms`（对比 `gpt-6.1-sol high` `6,232 ms`，`gpt-6.2-sol med` `4,819 ms`）
- `n = 2` 项决策：**`4,875 ms`** vs 串行 `10,754 ms`（**提速 `2.21×`**；`med` 档低至 **`4,425 ms`**）
- `n = 4` 项决策：**`7,100 ms`** vs 串行 `21,508 ms`（**提速 `3.03×`**；`gpt-6.1-sol high` `10,742 ms`）
- `n = 6` 项决策：**`8,826 ms`（折合 `1,471 ms / 决策`）** vs 串行 `32,262 ms`（**提速 `3.66×`**；比 `gpt-6.1-sol` 快 `1.49×`，比 `Gemini 4 Carbon` 快 **`8.24×`**）。

---

## 4. 首发次日（2026-11-18）外部权威基准全景对比表

| 评测维度 | 基准名称 | 数据源 | `GPT-6.2 Sol` | `GPT-6.1 Sol` | 代际变化 | `Claude Sonnet 5.5` | `Gemini 4 Carbon` | `GPT-6.2 Astra` |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 综合与经济学 | **AA Intelligence Index v5.0.1** | Artificial Analysis | **`57.3` (#11)** | `54.6` | **`+2.7`** | `54.5` | `60.0` (#2) | `62.1` (#3) |
| 综合与经济学 | **AA 单题平均成本 / 输出量** | Artificial Analysis | **`$1.01` (`40k`)** | `$1.27` (`68k`) | **`-20.5%` 成本** | `$10.02` (`285k`) | `$7.76` (v5.0) | `$8/$40` 旗舰档 |
| 综合与经济学 | **AA 流式吞吐 / 首答耗时** | Artificial Analysis | **`85 tok/s` · `68.2s`** | `49 tok/s` · `145.2s` | **`1.73x` 提速** | `147 tok/s` · `295.8s` | — | — |
| 综合与经济学 | **Vals 企业多模态指数** | Vals AI | **`66.1` (#9)** | `63.9` | **`+2.2`** | `70.8` | `70.4` | — |
| 编码与工程 | **FrontierCode 2.0 (AA)** | Artificial Analysis | **`44.4%` (#9)** | `40.6%` | **`+3.8 pt`** | `41.7%` | — | `48.95%` (`xhigh`) |
| 编码与工程 | **LiveBench 2.0 Coding** | LiveBench | **`83.7%` (#10)** | `82.1%` | **`+1.6 pt`** | `77.2%` | — | — |
| 编码与工程 | **Terminal-Bench-Science 0.1** | Artificial Analysis | **`67.6%` (`high/max`)** | `58.1%` | **`+9.5 pt`** | `53.3%` | `64.8%` | — |
| 编码与工程 | **Terminal-Bench 4.0 (AA / Vals)** | AA / Vals AI | **`60.1%` / `60.6%`** | `56.1%` / `55.0%` | **`+4.0 / +5.6 pt`** | `63.6%` / `64.1%` | `65.2%` AA | — |
| 编码与工程 | **BenchCAD 2.1 Core (3D 工程)** | DataLearner | **`73.1%` (#7)** | `52.6%` | **`+20.5 pt`** | — | — | `82.5%` (#2) |
| 科学推理 | **GPQA Diamond** | OpenAI / DataLearner | **`96.0%` (#2/254)** | `95.4%` | **`+0.6 pt`** | `95.6%` | — | `97.0%` (#1/254) |
| 科学推理 | **HLE-Diamond (AA)** | Artificial Analysis | **`64.0%`** | `58.8%` | **`+5.2 pt`** | `53.3%` | — | `72.2%` (#4) |
| 抽象推理 | **ARC-AGI-1 / 2 / 3** | ARC Prize | **`97.5% / 85.8% / 98.2%`** | `96.5% / 94.2% / 96.2%` | **ARC-3 `+2.0 pt`** | `96.5% / 83.9% / 72.4%` | — | — |
| 企业工作流 | **AutomationBench (AA)** | Artificial Analysis | **`71.3%`** | `64.9%` | **`+6.4 pt`** | `71.8%` | — | — |
| 法务与医疗 | **Harvey LAB-AA / HealthBench Pro** | Harvey / OpenAI | **`11.1%` / `65.9%`** | `6.9%` / `64.2%` | **`1.61x` 法务跃升** | `2.8%` / — | — | `— / 66.3%` |
| 网络安全 | **DeepSec-Bench / CWE-Bench (AA)** | Artificial Analysis | **`51.6%` (#3) / `64.2%`** | — | **DeepSec 前三** | — | `— / 71.0%` | — |
| 网络安全 | **CyberGym End-to-End (AA)** | Artificial Analysis | `0.0%` (#23) | — | 攻防闭环边界 | — | **`54.8%` ExploitGym** | — |

---

## 5. AI Solution Architect 生产路由架构与选型决策指南（FAQ）

```mermaid
flowchart TD
    Req["企业智能体 / 研发请求进入"] --> TokCheck{"总输入 Token > 272K?"}
    TokCheck -- "是 (>272K 触发 $4/$15 整单翻倍)" --> Shard["按固定 Repo 前缀切分为 <=270K 分片
复用 $0.10/M 缓存前缀 (-39.4% 成本)"]
    TokCheck -- "否 (<=272K 标准档 $2/$10)" --> DomainCheck{"工作负载类型判定"}
    Shard --> DomainCheck
    DomainCheck -- "日常编码 / 科学 CLI / 校准门控 / 法务初审" --> SolHigh["GPT-6.2 Sol (effort='high')
88 tok/s · ~8-10s 首答 · TB-Science 67.6%"]
    DomainCheck -- "简单确定性代码生成 / 高频批量分类" --> SolLow["GPT-6.2 Sol (effort='low'/'medium')
45s 四模块 · 批量 1.47s/决策"]
    DomainCheck -- "跨应用桌面 GUI / 复杂长程工具编排" --> Opus["Claude Opus 5.5 / Sonnet 5.5
OSWorld 87.2% · Agents 70"]
    DomainCheck -- "端到端漏洞复现与补丁闭环 / 1M 图遍历" --> Carbon["Gemini 4 Carbon
ExploitGym 54.8% · GraphWalks 96.2%"]
    DomainCheck -- "超高难科研与架构攻坚 (预算充足)" --> Astra["GPT-6.2 Astra ($8/$40)
GPQA 97.0% #1 · HLE-Diamond 72.2%"]
```

### 常见架构选型问答（FAQ）
- **Q1：既然 `GPT-6.2 Sol` 与 `GPT-6.1 Sol` 单价都是 `$2/$10`，该立即全量切换吗？**
  - **结论**：**编码、CLI 排障、科学计算、法务/财务结构化审核与置信度路由场景建议立即切换至 `gpt-6.2-sol (high)`**，不仅单题 Token 消耗下降 `41%`（AA 实测 `$1.01` vs `$1.27`），流式与首答延迟也快 `1.7x–2.5x`，还消除了 `R04` 这类边界算术漂移。唯一需保留回归验证的是重度依赖 `ARC-AGI-2` 风格网格归纳或超长多跳仓库重构的子任务。
- **Q2：五档 `reasoning_effort`（`low / medium / high / xhigh / max`）在生产中如何配置？**
  - **结论**：切勿全局盲开 `max`。BenchLeader / AA 数据显示 `high` 档首答仅需 **`9.98s`**（而 `max` 高达 `68.2s`），却能拿到 `Terminal-Bench-Science` **满分持平的 `67.6%`** 与 `60.9` 综合分；接口契约明确的代码生成与网关批量分诊用 `low` / `medium` 即可省下 `60%–78%` 输出账单。
- **Q3：如何防止 `> 272K` 长上下文计费悬崖击穿月度预算？**
  - **结论**：在 API 网关层设置 `268,000` Token 软阈值，将静态代码库/制度文档固定在系统前缀（享受 `$0.10/1M` 缓存读取，立省 `95%`），将增量 Diff 或长日志按 `<= 20K–40K` 切片并发/串行推理，严禁把 `290K` 未裁剪上下文直接塞进单次调用。
