# 模型 Benchmark 视觉卡片报告规范（7-Card Visual Report Format）

本规范提炼自 4:5 竖版高密度技术评测卡片（Carousel Deck）版式，适用于在本仓库及后续模型评测中输出结构统一、结论鲜明、证据可审计的视觉技术测试报告。

---

## 1. 设计原则与核心特征

1. **结论先行（Headline-as-Finding）**：每页大标题直接写出量化的实验结论或机制事实（例如 `One call. Three decisions. ~170 ms.`、`Reverse the options. Same answer.`），不写无信息量的“实验结果（一）”。
2. **一卡一证据（One Evidence Artifact per Card）**：每张卡片聚焦单一证据形态——工作台全景、单样本多维拆解、全场景判定矩阵、双层协议透视、扰动鲁棒性对照表、批量延迟缩放条形图、适用/禁用双栏建议。
3. **置信度与动作分档显式化（Action-Band Gating）**：不把模型输出仅当静态打分，而是将概率/得分映射为工程动作胶囊（如 `>= 0.9 Act automatically`、`0.5–0.9 Confirm`、`< 0.5 Send to a human`），直观暴露边界样本与失误拦截。
4. **严格绑定封存证据（Zero Fabricated Coordinates）**：所有进度条宽度、百分比、延迟条形图长度和汇总分母必须由封存的 `summary.json` 或 `report.json` 计算生成；缺失值显式标注，禁止由生成模型手写虚构坐标。

---

## 2. 全局版面解剖与视觉 Token（Page Shell & Tokens）

### 2.1 画布与栅格
- **画幅比例**：`4:5` 竖版卡片（推荐基准尺寸 `900px × 1125px` 或导出分辨率 `1080px × 1350px`），兼顾桌面长文嵌入、技术分享幻灯片与移动端滑动阅读。
- **页面结构（自上而下五段式）**：
  1. **顶部渐变饰条（Top Accent Bar）**：高度 `10px`，线性渐变 `linear-gradient(90deg, #6366F1 0%, #4F46E5 50%, #3B82F6 100%)`。
  2. **三段式页眉（Header Stack）**：
     - **Eyebrow 眉题**：`13px–14px`，全大写，`letter-spacing: 0.12em`，字重 `700`，颜色 `#4F46E5`。
     - **主标题（Headline）**：`38px–44px`，行高 `1.12`，字重 `800`，颜色 `#0F172A`（首页核心模型名可使用 `#2563EB -> #4F46E5` 渐变字）。
     - **导语副标题（Dek）**：`17px–19px`，行高 `1.45`，颜色 `#475569`，控制在 1–2 行。
  3. **核心证据画布（Evidence Canvas）**：占画布高度约 `55%–62%`，承载表格、分布条、代码块或双栏对比卡。
  4. **底部结论提示框（Takeaway Callout Box）**：圆角 `12px`，背景 `#F1F5F9`，内边距 `18px 22px`；**首句加粗**给出工程解读、分档口径或复现条件。
  5. **页脚栏（Footer Bar）**：顶部分割线 `1px solid #E2E8F0`；左侧显示专题/来源标识（匿名档案使用仓库或专题名，不暴露个人隐私信息），右侧显示等宽或无衬线页码 `N / 7`。

### 2.2 语义色板（Semantic Palette）

| 用途 | Token 名称 | 色值（Hex） | 适用组件 |
|---|---|---|---|
| 画布背景 | `surface-page` | `#F8FAFC` / `#FFFFFF` | 卡片主背景 |
| 容器浅灰 | `surface-callout` | `#F1F5F9` | 输入引文框、底部结论框 |
| 深色代码底 | `surface-code` | `#0F172A` | 协议/Prompt 透视代码块、底部安全警告卡 |
| 品牌主色 | `accent-primary` | `#3B82F6` / `#4F46E5` | 主概率条、批量延迟主条、眉题高亮 |
| 对照灰条 | `bar-baseline` | `#CBD5E1` | 逐条调用对照条、次选概率底槽 |
| 自动通过（绿） | `status-auto` | 文字 `#15803D` / 底 `#DCFCE7` | `Act automatically`、`Auto`、`Good fit` 卡片 |
| 人工确认（琥珀） | `status-confirm` | 文字 `#B45309` / 底 `#FEF3C7` | `Confirm` 分档标记 |
| 升级人工/拒绝（红） | `status-human` | 文字 `#B91C1C` / 底 `#FEE2E2` | `Send to a human`、错误标记 `✕`、`Not for` 卡片 |

---

## 3. 七页标准卡片原型（7-Card Archetypes）

| 页序 | 标准眉题模板 | 卡片原型 | 必备元素与数据绑定规则 |
|---|---|---|---|
| **1 / 7** | `HANDS-ON · <TRACK>` | **封面与测试工作台** | 1. 评测对象与核心问题副标题；<br>2. 居中展示工作台/架构预览卡（左：场景列表与阈值规则；中：结构化输入；右：实时输出与耗时胶囊）；<br>3. 底部框注明运行硬件、推理后端、是否需要 API Key 及数据来源属性（`measured` / `synthetic` / `anonymized_reported`）。 |
| **2 / 7** | `SCENARIO: <CASE_NAME>` | **单样本深度拆解** | 1. 标题点明单次调用完成的子任务数与端到端耗时；<br>2. 顶部浅灰框展示原始输入文本/请求摘要；<br>3. 纵向堆叠 2–3 张子决策卡：每张含字段名、任务类型胶囊（如 `choice` / `noul` / `score`）、问题说明、主结果大字、置信度、右侧动作胶囊及各候选水平概率条；<br>4. 底部框解释高置信自动放行与低置信人工兜底的协同机制。 |
| **3 / 7** | `WHAT I TESTED` | **全场景评测矩阵** | 1. 标题给出 `<N> scenarios, <M> decisions/tasks`；<br>2. 四列表格（`SCENARIO \| QUESTION/TASK \| MODEL ANSWER \| ACTION/STATUS`），主答案加粗并附百分比/得分，错误判例紧跟红色 `✕`；<br>3. 底部双提示框：第一框交代动作分档阈值与总体命中率/自动率，第二框专门复盘 `✕` 失误案例及其是否被安全阈值拦截。 |
| **4 / 7** | `UNDER THE HOOD` | **底层协议与渲染透视** | 1. 上方深色代码块展示调用方传入的结构化 JSON / 实验契约；<br>2. 中间蓝色向下箭头说明转换机制（如 `↓ the server renders it into plain text` 或独立 Verifier 校验流）；<br>3. 下方深色代码块展示模型实际看到的渲染 Prompt / 隐藏状态打分位置（如高亮 `<answer>`）；<br>4. 底部框说明为何该机制能省去生成 token 或避免评分器污染。 |
| **5 / 7** | `ROBUSTNESS CHECK` | **鲁棒性与扰动检验** | 1. 针对位置偏置、提示词扰动或多轮重复进行对照；<br>2. 四列表格（`QUESTION / ANSWER` 双行单元格 \| `ORIGINAL` \| `PERTURBED/REVERSED` \| `CHANGE (PTS)`）；<br>3. 底部框汇总保持一致的题数比例、最小/最大偏移百分点及计算定义。 |
| **6 / 7** | `LATENCY` | **延迟与吞吐缩放对比** | 1. 标题揭示批处理、缓存或并发带来的延迟规律（如 `Ask in batches, not one by one`）；<br>2. 按负载规模（如 1 / 3 / 6 / 10 问或 Atomic / Medium / Complex）分组绘制水平双条形图：主色条为优化路径（如 `Batched`），浅灰条为基线路径（如 `One by one*`），条末直接标注加粗毫秒/秒数；<br>3. 底部框写明重复运行次数、统计量（中位数/P95）、硬件环境及基线折算公式。 |
| **7 / 7** | `MY TAKE` | **工程选型边界与就绪度** | 1. 左右等高双栏圆角卡：左栏绿底 `✅ Good fit`（列出 4–5 类高契合场景），右栏浅红底 `⛔ Not for`（列出不适用场景与必须保留确定性策略引擎的边界）；<br>2. 底部深色信息卡：坦诚说明当前生产就绪度限制（如鉴权、沙箱、单样本局限）、开源许可证与代码/数据路径。 |

---

## 4. 三类 Model Benchmark 轨道映射指南

本仓库涵盖 **路由/决策模型（Routing & Decision）**、**通用 API 模型（API Evaluation）**、**编码智能体（Coding Agent）** 三类评测。使用本版式时按以下规则映射各页内容：

| 页序 | 路由 / 决策模型（Routing & Decision） | 通用 API 模型（API Benchmark） | 编码智能体（Coding Agent Benchmark） |
|---|---|---|---|
| **Card 1** | 决策/路由模型定位、候选池规模、本地/远端拓扑 | 参评模型队列、任务维度、评分 Profile 与成本口径 | 参评 Agent/模型队列、CLI/Harbor 版本、任务难度分层 |
| **Card 2** | 单条请求的多维路由/分诊决策与概率分布条 | 典型 Case 的结构化输出断言、分项得分与耗时拆解 | 单个复杂任务（如 `C3`）的功能/规范/质量得分拆解与轮次消耗 |
| **Card 3** | 全场景路由/门控命中矩阵 + 阈值拦截复盘 | 全任务 × 模型得分/通过率矩阵 + 典型失败断言复盘 | 11 任务（`A1–C4`）或模型总榜矩阵（均分、隐藏断言通过、费用、轮次） |
| **Card 4** | JSON 状态转纯文本 Prompt 与单次前向打分机制 | Promptfoo 契约、归一化规则与确定性断言执行流 | 任务隔离目录、Reference 验收与隐藏测试（Hidden Verifier）封存校验流 |
| **Card 5** | 候选顺序逆序（Option Reversal）与多轮一致性对比 | 提示词同义扰动、温度/Seed 变化或格式约束稳定性对比 | 跨批次评分修订对照、单任务复跑极差（得分波动 vs 成本波动） |
| **Card 6** | 前缀共享批量提问 vs 逐条提问中位数延迟条形图 | 各候选模型平均延迟 / TTFT 与单次调用成本水平条形图 | 各模型 Wall Time vs 纯模型推理时间（Inference Time）双条形对比 |
| **Card 7** | `Good fit`（意图路由/门控预检）vs `Not for`（长链推理/最终安全放行） | 高性价比主力模型 vs 高精度兜底模型的分层选型建议 | 不同预算与复杂度下的 Agent 模型选型建议 + 沙箱与样本局限声明 |

---

## 5. 自动化渲染与合规护栏

1. **代码工具支持**：仓库提供 `src/benchmark_harness/cards.py` 与 CLI 子命令 `benchmark-harness cards`，可将结构化 7 页卡片 JSON 或评测 `run` 目录直接渲染为自包含、零外部依赖、支持打印导出的 `cards.html`。
2. **禁止篡改或冒充实测**：
   - 合成演示生成的卡片必须在顶栏/页脚与第 1、7 页显著标明 `SYNTHETIC DEMO`；
   - 外部或历史报告整理的卡片必须标明 `ANONYMIZED REPORTED (independently_reproduced=false)`；
   - 严禁在未核验版权与隐私授权前将含个人署名或内部信息的原始截图直接入库。
