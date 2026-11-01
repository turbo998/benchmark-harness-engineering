# 匿名历史测试报告档案

本档案将指定资料库中的历史测试报告与 7 页视觉卡片评测归并为 **10 个主题**：
四个 coding-agent 主题、一个前沿编程/智能体/网络安全综合评测主题（增补报告六：Gemini 4 Carbon）和五个路由/决策模型主题。中英文版本与视觉卡片合并归档，不当成独立实验；
其他私人页面未迁移。内容为重新撰写的方法、事实数据和限制说明，
**不是原文转载，也不是本 harness 新跑出的成绩**。

| 主题 | 来源版本 | 规模与边界 | 整理报告 |
|---|---|---|---|
| 五模型编码基准 | 中 / 英 | 11 个任务，55 次评分运行 | [coding-five](coding-five.md) |
| 十模型编码增补 | 中 / 英 | 新增 55 次，累计 110 次；复用旧模型 | [coding-ten](coding-ten.md) |
| 十七模型编码增补 | 中 / 英 | 新增 22 次，累计 187 次；跨批次且有评分修订 | [coding-seventeen](coding-seventeen.md) |
| 十九模型编码增补 | 中 / 英 | 新增 Haiku 5.5 与 Gemini 4 Argon（22 次），累计 209 次 | [coding-nineteen](coding-nineteen.md) · [EN](coding-nineteen.en.md) |
| Gemini 4 Carbon 前沿与安全评测 | 中 / 英（含 7 页卡片） | 16 项官方基准（14 项第一）、4 项网络安全子榜与对齐指标；本地 CLI A1–C4 待测 (`null`) | [gemini-4-carbon](gemini-4-carbon.md) · [EN](gemini-4-carbon.en.md) · [7 页卡片](../../examples/gemini-4-carbon-card-report/index.html) |
| Jev 路由集成观察 | 中 / 英 | 少量示例，不是准确率基准 | [routing-jev](routing-jev.md) |
| Laya / Jev / LLM 对比 | 中 | 20 个请求，每引擎一轮 | [routing-laya](routing-laya.md) |
| Decision-1 四引擎对比 | 中 / 英 | 40 个请求，三轮，480 次决策 | [routing-decision](routing-decision.md) |
| OpenJev 补充对比 | 中 | 新测 120 次，另四个引擎复用上一报告 | [routing-openjev](routing-openjev.md) |
| Strands Decider 2B 决策评测 | 英（7 页卡片） | 7 个场景 12 次决策、6 题逆序鲁棒性与批量延迟 | [routing-strands-decider](routing-strands-decider.md) |

## 如何读数据

[机器可读目录](../../data/reported/catalog.json)记录主题、版本数量、窗口、口径和限制。
各主题目录提供 `report.json` 与 CSV。编码报告保留逐任务评分、轮次、token、
费用以及存在于原表中的时间；路由报告保留决策结果和计时，不混入编码质量榜。

所有记录标记 `anonymized_reported`、`independently_reproduced=false`。
这是对既有报告的事实整理，而非原始会话、完整审计证据或独立复现。
JSON 中的表格保留源表小数位、单位和缺失值，CSV 是相同单元格的导出；
中文“万”、英文缩写和总量小数不能当作精确逐 token 计量。
价格保留测试当时的报告口径，不是最新报价或已核验账单。

十模型页面标题中的 Luna 版本与正文/表格不一致；十七模型批次还修订了部分历史
隐藏断言和 C3 分数。档案保留各期快照，**不拼成一条未经说明的统一历史榜**。
十二/十五配置增补只出现在已读页面的时间线中，不计入本次七个已迁移主题。

## 脱敏、版权与完整性边界

新增档案移除作者署名、职务、联系信息、内部团队、内部演示链接、私有页面地址及 ID、
实际资源/账号/端点和凭据；没有复制截图、原图、完整题库、实现代码、模型权重、
ZIP 附件或原始会话。全文和这些附件的再分发权限尚未核验，故未迁移。
公开产品名、历史版本、通用硬件/区域和数值保留，以免破坏实验解释。

文字由本项目重新组织，并有 AI 辅助；未将原作者贡献改称本项目原创实测。
去掉身份字段不保证无法通过相同数值重识别来源。既有研究引用与 Git 历史不在本次
新增档案脱敏范围内，也未为了匿名而删除既有合法归属说明。
源 Notion 页面未编辑或删除；这次是可公开的匿名事实档案，不是全量迁移备份。

## 对 harness 的启示

编码评分、路由标签一致率和路由耗时是不同测量对象。
为新实验冻结 dataset、模型版本、CLI、环境与计价表，保留所有 attempt 和证据；
将费用来源、未复核项、跨批次变更、重复/复用样本显式写入 manifest 与报告。
参考 [实验方法](../methodology.md)、[计量口径](../metrics.md)、
[7 页视觉卡片版式规范](../research/visual-report-card-format.md)和
[本地闭环](../quickstart-local.md)。本档案不会自动启用 live 模式。
