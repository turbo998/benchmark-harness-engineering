# Strands Decider 2B 决策模型评测：历史事实整理

**来源性质：** `anonymized_reported`，单份 7 页视觉评测卡片，未独立复现。
模型标识为 `strands-decider-2B-qwen3.5-v1-2610`（Apache-2.0），运行于本地 Apple M5 Pro（MPS 后端）。
结构化数据见 [JSON](../../data/reported/routing-strands-decider/report.json)、
[12 项决策明细 CSV](../../data/reported/routing-strands-decider/scenarios.csv)、
[选项逆序鲁棒性 CSV](../../data/reported/routing-strands-decider/robustness_reversal.csv)、
[批量延迟对比 CSV](../../data/reported/routing-strands-decider/batch_latency.csv) 与
[可离线预览的 7 页卡片 HTML](../../examples/card-report/index.html)（版式规范见
[视觉卡片报告规范](../research/visual-report-card-format.md)）。

## 方法与执行机制

被测对象为 2B 参数规模的 System One 决策模型：服务端将结构化 JSON（共享的 `state`
与多个 `questions`）渲染为带 `<state>`、`<question>`、`<options>`、`<answer>` 标签的纯文本，
不使用聊天模板。模型在 `<answer>` 位置**不生成任何输出 token**，而是通过单次前向传播
（single forward pass）计算各编号选项行末尾 token 的隐藏状态匹配度并经 softmax 输出概率或分数。

评测包含 7 个 Agent 场景（共 12 个决策问题），覆盖三种问题类型：
- `choice`：多选一分类（输出各选项概率与最高项置信度）；
- `noul`：二元是非判定（输出 `true` / `false` 概率，置信度取 `max(p, 1-p)`）；
- `score`：有序等级打分（如 `0–3` 级紧急度，输出加权期望分值与置信度）。

报告采用三档动作阈值（作者亦声明生产环境需按自有流量重新校准）：
- `Auto`（自动执行）：`confidence >= 0.9`
- `Confirm`（人工确认）：`0.5 <= confidence < 0.9`
- `Human`（转交人工）：`confidence < 0.5`

## 单样本深度拆解（Complaint Triage）

针对一条客户投诉文本（连续三次被多收 30 美元、48 小时承诺未兑现并威胁向监管投诉及销户，
输入 `335 tokens`），单次请求同时提问 3 个决策问题（端到端单次调用约 `170 ms`；工作台界面单次记录为推理 `217 ms`、往返 `219 ms`）：

| 决策字段 | 类型 | 模型输出 | 置信度 / 概率 | 动作分档 | 候选分布明细 |
|---|---|---|---:|---|---|
| `intent` | `choice` | `billing_dispute` | 0.919（93.9%） | `Act automatically` | `billing_dispute` 93.9%, `close_account` 3.9%, `tech_issue` 1.4%, `inquiry` 0.9% |
| `escalate` | `noul` | `Yes` | P(true) = 0.947 | `Act automatically` | `true` 94.7%, `false` 5.3% |
| `urgency` | `score` | `1.71 / 3` | 0.377 | `Send to a human` | `0 Low` 16.6%, `1 Medium` 24.2%, `2 High` 30.5%, `3 Critical` 28.7% |

该样本展示了置信度门控的作用：前两项超过 `0.9` 可自动流转，而紧急度分布在 `1–3` 级之间较分散（置信度仅 `0.377`），系统自动将其拦截并转交人工。

## 7 场景 12 决策报告值

| 场景 | 决策问题 | 模型回答（报告百分比） | 方向是否正确 | 动作分档 |
|---|---|---|---:|---|
| Support ticket routing | Which team? | Billing (98%) | 是 | `Auto` |
| Complaint triage | Main request? | Billing dispute (94%) | 是 | `Auto` |
| Complaint triage | Escalate? | Yes (95%) | 是 | `Auto` |
| Agent tool-call gate | Arguments grounded? | Yes (53%) | 否 | `Confirm` |
| Agent tool-call gate | Ask the user first? | Yes (67%) | 是 | `Confirm` |
| GenBI question routing | Which data domain? | Finance (95%) | 是 | `Auto` |
| GenBI question routing | Needs clarification? | No (85%) | 是 | `Confirm` |
| Collections call intent | Repayment intent? | Negotiate a plan (96%) | 是 | `Auto` |
| Collections call intent | Complaint risk? | Yes (78%) | 是 | `Confirm` |
| Prompt-injection screening | Contains an injection? | Yes (78%) | 是 | `Confirm` |
| Prompt-injection screening | Main risk? | Data exfiltration (85%) | 是 | `Confirm` |
| Model routing | Which model tier? | Frontier model (90%) | 是 | `Confirm` |

**汇总事实：** 12 个决策中 **11 个方向正确**，**5 个达到 `>= 0.9` 自动执行分档**。
唯一方向失误出现在 `Agent tool-call gate` 的参数 grounding 检查：Agent 编造了用户未提及的城市，模型仍以 `53%` 微弱倾向判为 `Yes`，但因远低于 `0.9` 自动放行线，仍停留在 `Confirm` 分档等待确认。

## 选项逆序鲁棒性与批量延迟

对全部 6 个 `choice` 问题进行选项顺序反转（Reversed Order）复测，**6/6 的首选答案保持不变**：

| 场景 | 首选答案 | 原始顺序概率 % | 逆序概率 % | 变化（百分点） |
|---|---|---:|---:|---:|
| Support ticket routing | `billing` | 97.8 | 97.8 | 0.0 |
| Complaint triage | `billing_dispute` | 93.9 | 96.4 | +2.5 |
| GenBI question routing | `finance` | 95.1 | 96.2 | +1.2 |
| Collections call intent | `negotiate` | 96.3 | 96.5 | +0.1 |
| Prompt-injection screening | `data_exfiltration` | 84.7 | 90.2 | +5.5 |
| Model routing | `frontier` | 90.1 | 86.9 | -3.2 |

由于同一请求内的所有问题共享一次 `<state>` 前缀计算，在 Apple M5 Pro（MPS）上运行 7 次取中位数的批量耗时显著低于逐条调用折算值（`One by one* = 问题数 × 71 ms`）：

| 单次请求问题数 | 批量调用中位数 ms | 逐条调用折算 ms | 批量相对耗时比 |
|---:|---:|---:|---:|
| 1 | 71 | 71 | 1.00x |
| 3 | 152 | 213 | 0.71x |
| 6 | 233 | 426 | 0.55x |
| 10 | 365 | 710 | 0.51x |

## 适用边界与限制

- **适用场景（Good fit）**：意图路由、工单分诊与升级判定、工具调用前预检、GenBI 数据域路由、选择下游调用的 LLM 层级。
- **不适用场景（Not for）**：长链多步推理、需要生成自然语言文本的任务、以及安全的最终 Allow/Deny 裁决（安全放行必须保留在确定性策略引擎中）。
- **方法限制**：本报告为 7 个场景的动手压力测试（hands-on stress test），不是大规模盲化基准；`0.9 / 0.5` 阈值为演示建议值而非校准保证；随附服务端尚无鉴权机制，不建议直接用于生产。
