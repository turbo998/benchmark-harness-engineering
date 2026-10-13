# 作者 benchmark 方法还原

研究快照：2026-10-12。下面是原创证据分析，不是文章转录。三个输入链接去重后只有
两个独立页面，出处见 [归属](../../ATTRIBUTION.md) 和 [evidence.json](evidence.json)。

## 可以证明什么

固定 `satomic/copilot-benchmark` commit 的完整 tree 中有 11 个任务、187 个非 reference
运行证据目录、11 个 reference 目录。这是固定 Copilot scaffold 下更换模型的编码实验，
不是单纯 API 推理榜，也不自动代表不同 agent 的公平排名。

公开证据支持的流水线是：

`任务与约束 → reference/隐藏 verifier → fresh CLI 会话 → agent 交卷 → 证据封存 → 功能/规范/质量评分 → 汇总 → 图表与文字`

| 环节 | 公开证据 | 不能据此推断 |
|---|---|---|
| 题目 | A/M/C 难度、输出契约、reference 与 verifier | 作者出题是否用 AI、原 prompt |
| 执行 | CLI/模型/effort、fresh session、prompt hash、工具轨迹 | 未公开 runner 的失败/重试实现 |
| 交卷 | session 显示 agent 写代码并自测 | 一次通过能保证长期稳定 |
| 判分 | 隐藏测试、facts、分项 rubric、文件行号理由 | JSON 有文风便证明是 AI 裁判 |
| 绘图 | 文章声称 summary 经脚本重建 | 固定 tree 已公开全部绘图实现 |
| 写文章 | 结果可追溯到结构化数据 | 作者写文章所用模型与会话 |

**“AI 生成被测代码”可核验；“AI 生成整套 benchmark 和文章”未证实。**
固定 tree 中未找到文章所称完整 runner、汇总和 `make_charts.py`，不能假装原样复刻。

## 一个计量/评分证据链

以下均为 `third_party_reported`，不是本项目跑分。

A2 的 GPT-6.1 Sol bundle 记录 CLI `1.0.90-5`、`medium`、一个 repeat：
wall 49.79 秒、API 累计 34.39 秒、4 次模型请求、6.201 AI credits；隐藏测试 38/38，
功能 70、规范 15、质量 11，总分 96。使用的是新会话，但 `coldCache=false`。

因此不能把 API 累计时间、wall time、TTFT 或硬件计算时间互换，也不能把 fresh session
当成冷缓存。usage 把普通输入、cache read/write、输出分开，单看输出 token 会漏账。
credits 与 Azure token 账单是不同渠道，换算需要记录当时的政策和日期。

reference 也不等于满分：C3 reference 功能通过，质量 review 仍 pending。把未复核项
填零后当成质量失败，会制造错误结论。

## Jev 的 300 ms 是另一种实验

对应版本是 model-router `v2.1.1`。计时从路由开始到 Choice 决策完成，包含网络调用，
不包括随后模型生成与工具执行。首次连接、warm 请求、规则命中、sticky 命中必须分开。

候选集约束只能限制可输出的名字，不能证明选得最合适；源码仍处理未知选择与 fallback。
少量演示不是冻结数据集、有独立标签和重复采样的路由准确率 benchmark。
Jev 的请求 state 会送到 TypeSafe，因此后端在 Azure 不代表全部输入只留在 Azure。

## 原报告能启发什么，不能照搬什么

70/15/15 可以成为一个有名字的评分 profile，而非所有 API/agent 任务的通用公式。
复杂任务散点的原文口径是复杂层总花费对复杂层平均分，不是单次调用费用。

单任务单采样、CLI/服务模型跨批次变化、头部得分 ceiling 都是混杂因素。新实验应冻结
dataset/scaffold/scorer，随机化匹配任务顺序，重复执行并按任务簇报告不确定性。
repeat 不是新任务；不到一分的均分差不应直接包装成可靠选型。

本项目采用 [原创 recipe](reproduction-recipe.md) 重建生产流程，不复制上游题库、
评分器或图表，也不冒充恢复了作者未公开的创作 prompts。
