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

**0.1.0 是离线验证的工程原型，不是十七模型实测榜或可直接启用的付费 runner。**
原创研究、样例生成/验收、冻结计划、mock 执行/恢复、预算证据和报告重建已实现。
示例包含 9 个原创 API/coding fixtures、2 个 mock candidates、2 次重复：
36 个 trial、41 个保留 attempt；图中的费用/速度明确标为 `synthetic`。

promptfoo 0.124.0 的真实本地无网络 provider smoke 已通过；Harbor 0.24.0 的原生
`copilot-cli` 适配由发布 wheel 源码确认，**Docker/Harbor execution、Copilot BYOK、
Azure 部署与付费模型实验尚未验证**。Azure Bicep 已本地编译，broker 预算、lease、
封存和导出门禁已离线验证；这些都不等于云数据面或 sandbox 已跑通。
上游数字保留 `third_party_reported` 来源，缺失费用/待复核质量不填零。

## 免费闭环

从自己的 clone/隔离 worktree 执行：

```powershell
uv sync --frozen --dev
uv run --frozen benchmark-harness demo --output .runs\demo
```

打开 `.runs\demo\report\index.html`。生成器使用确定性原创模板，不调用 AI 或模型；
报告从保存的 evidence 重建，输出自包含 HTML、JSON/CSV 和 PNG/SVG。
真实模型、AI 生成/评分与云 apply 默认拒绝，不会因运行 demo 产生这些费用。

- [本地命令与 engine readiness](docs/quickstart-local.md)
- [样例生成与独立验收](docs/sample-generation.md)
- [统计与计量口径](docs/metrics.md) · [实验方法](docs/methodology.md)
- [Azure profile 与生命周期](docs/azure.md) · [可信推理 broker](docs/broker.md)
- [保存的合成演示](examples/mock-report/report/index.html)（下载后离线打开）

要跑真实模型，仍需绑定模型/价表/预算并批准付费 smoke；当前 CLI 的 live 路径保持
阻塞，不能把导出的 engine config、源码适配存在或 mock 分数冒充 live readiness。

## 许可与出处

原创代码和文档采用 [MIT](LICENSE)。第三方文章、题库、源码、图片和结果不被本项目
重新授权或整库分发；参见 [归属](ATTRIBUTION.md) 与 [第三方说明](THIRD_PARTY_NOTICES.md)。
