# 原创 AI 协作与复现实验 recipe

这是我们的工程建议，不是作者原 prompts。目标是降低下一次 benchmark 的重复劳动，
同时防止“AI 出题、AI 自证正确、AI 造表格”形成不可审计的闭环。

## 六个角色

| 角色 | 允许做 | 不能做 |
|---|---|---|
| 实验设计者 | 能力轴、难度、控制变量、预算、分母 | 先写排名，再找理由 |
| 样例生成者 | 输出冻结 schema 的候选题、seed、边界情形 | 给每个被测模型生成不同题 |
| 独立 oracle/critic | reference、断言、错误变体、歧义检查 | 用生成器自己的回答证明 oracle |
| 确定性执行器 | 实验矩阵、停止、attempt、证据、恢复 | 靠对话记忆跳过失败或重试到正确 |
| 盲化复核者 | rubric 分项、文件行号、理由、待人工项 | 将主观判断伪装成隐藏测试 |
| 报告作者 | 读固定结果写解读、引用 evidence | 自造数字、图坐标或缺失费用 |

## Sample 工程

API case 声明输入、允许的输出形状/答案集合、归一化规则、断言和权重；
用独立 accepted/rejected response fixture 检查评分器。自由文本采用校准 rubric，
与确定性正确率分开。无法验证的 case 标 invalid，而不是加入 holdout。

Coding case 配 instruction、环境、visible outputs、reference 与 hidden verifier。
reference 必须通过，针对性的错误变体必须失败；verifier 不给被测 agent 查看。
先 draft generation，再冻结接受集；同一题集用于所有候选。

免费模板模式用于快速搭出结构；AI-assisted generation 需要单独的付费配置。
生成、critic、grader 费用都计入实验，不只统计候选模型。

## Run 工程

冻结 dataset/prompt/scorer/image/CLI/model/version、repeat、预算与缓存策略。
每次 attempt 记录配置 hash、开始/结束与 phase 时间、原始 usage、费用来源、
状态、文件 hash、失败原因。配置变化开新实验，不能伪装为 resume。

failed、timeout、infra/provider/auth/quota error、cancelled 都在报告分母中；
未知费用是 null 并带原因，质量未复核是 pending。response cache replay 不当实测延迟。

本地与 Azure 分 cohort；API、路由、agent wall、verification 分 phase。
同任务匹配候选并随机化顺序；重复次数不当独立任务，置信区间按任务簇计算。
小 starter pack 是 pilot，不是可靠的全场景模型排行榜。

## Environment 工程

本地使用控制器、agent、verifier 分离；不挂 home、Docker socket 或广泛凭证。
Azure worker 不绑定可访问业务资源的 MI；独立 broker 才持推理权限。
broker 只接收限定 deployment 的过期 run token，不接受任意目标 URL。
先原子预留费用再调用，未知 in-flight 费用不能重启后清零。

云参数先绑定并检查 subscription/region/SKU/permissions/quota/TPM/RPM/dated prices，
再批准 apply。Azure budget 告警不能停费；停止 compute 后磁盘/存储仍可能收费。
清理前先导出完整证据、核验 hash 和独立 receipt，失败时禁止删证据容器。

## Report 工程

保留 JSON/CSV，离线生成 HTML、PNG/SVG、成本质量/Pareto 和延迟质量散点、
难度热力图、分布与分项得分。每个点可追溯到 bundle，caption 声明 cohort、
轴单位、分母、缺失值与数据状态。所有数字同源，重新画图不调用模型。

发布时分开原始私有 evidence 与公开脱敏 export。mock=`synthetic`，
上游=`third_party_reported`，只有真正执行过的运行才标本项目实测。
