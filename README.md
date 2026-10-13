# Benchmark Harness Engineering

把「生成样例 → 验收与冻结 → 准备环境 → 多模型/agent 跑分 → 评分 → 可视化」
做成可重复、可审计的工程工作流，而不是每次临时让 AI 写一套测试和图表。

## 原创研究

- [作者 benchmark 方法还原](docs/research/author-workflow.md)：公开证据、未知信息、计时与计费口径。
- [框架比较与选择](docs/research/framework-comparison.md)：promptfoo、Harbor、Inspect AI、SWE-bench。
- [原创 AI 协作与复现实验 recipe](docs/research/reproduction-recipe.md)：如何设计、生成、验收、执行和写报告。
- [机器可读来源](docs/research/evidence.json)：固定 commit、文件、来源类型和证据边界。

研究结论：**被测代码由 AI agent 生成有证据；作者制作题库、评分器、图表与文章的创作
prompts 没有公开。** Jev 的约 300 ms 是路由决策耗时，不是编码任务完成时间。
本项目提供原创重建方案，不声称恢复了未公开的作者会话或脚本。

## 工程路线

promptfoo 负责 API 评测，Harbor 负责 coding-agent 任务；Python 薄层负责冻结实验契约、
样例验收、attempt 证据、预算和统一报告。API 与 agent、本地与 Azure 分开比较。

默认使用免费确定性模板与明确标注的 mock 数据。真实模型调用、AI 出题/评分和 Azure
部署需要显式目标、权限、价表、限额与单独批准。缺失成本不是零，未复核质量不是失败。

Azure 模板采用无云身份的临时 VM worker、独立可信推理 broker 和私有证据容器。
broker 不执行被测代码；删除实验存储前必须校验独立导出的证据。

## 当前状态

原创研究已发布；工具正在实施。**尚未验证真实 engine、Docker sandbox、云部署或付费
模型实验。** 上游数字标记为 `third_party_reported`；未来 mock 演示标记为 `synthetic`。
只有实际完成的检查才会提升对应 readiness，模板存在不等于部署成功。

## 许可与出处

原创代码和文档采用 [MIT](LICENSE)。第三方文章、题库、源码、图片和结果不被本项目
重新授权或整库分发；参见 [归属](ATTRIBUTION.md) 与 [第三方说明](THIRD_PARTY_NOTICES.md)。
