# 评测框架比较与首期选择

本页是固定源码研究后的原创选择，不保证研究 commit 是可安装 release。
实际运行版本必须从发行包选择并锁定，不能使用浮动 latest。

| 框架 | 适合承担 | 主要边界 |
|---|---|---|
| promptfoo | API 候选、断言、repeat/resume、结果导出 | 输入合成不保证 oracle；safe mode 不是 sandbox；cost assertion 是事后检查 |
| Harbor | 编码任务、环境、verifier、agent/ATIF 轨迹 | Copilot adapter 未核实；旧版默认同环境不保证隐藏 verifier（`v4.1.0` 已支持 `environment_mode = "separate"` 独立判分容器）；未知用量可能为 null |
| Inspect AI | Python-native 评测、scorer、limits、统计 | 是合理替代，不作为第三个必装 engine 叠加 |
| SWE-bench | issue/patch 与回归测试 pack | 特定任务族，不当通用 harness 数据契约 |

## 选择：promptfoo + Harbor + Python 薄层

复用两个成熟 engine 的执行能力，由自己的数据层统一 experiment/case/attempt ID、
provenance、计量边界、预算与报告。API 和 agent 不混成同一“速度榜”。
没有证据证明 Harbor JSON 可直接无损导入 promptfoo HTML，因此使用自有报告层。

薄层不重写所有 provider、sandbox 和 UI。报告先消费明确 synthetic 的封存数据，
实际 engine 能力、Docker 和 Copilot 兼容性由独立探针确认。未支持时必须显式阻塞，
不能用 mock 输出冒充真实 provider/agent 运行。

## 需要弥补的工程缺口

- 引擎 retry 不能删除先前 attempt；费用与失败留在外部追加归档。
- engine response cache 与 provider prompt cache 是不同层；缓存重放不进入真实延迟分布。
- task 和 verifier 分开，verifier 不联网，隐藏测试不进入 agent filesystem。
- host home、Docker socket、云管理凭证不进入 task；容器不是任意恶意代码的绝对隔离保证。
- 调用前预留预算，失败/生成/grader 也计费；原生 CLI 的 opaque 计量不保证精确美元硬上限。
- 模型 judge 版本和 rubric 冻结，盲化身份并校准；未复核质量保持 pending。

## 固定研究来源

| 项目 | Commit |
|---|---|
| promptfoo | [162c43a4](https://github.com/promptfoo/promptfoo/tree/162c43a4c037b965df9b2f1e4542b96f4f9b8144) |
| Harbor | [dc933be7](https://github.com/harbor-framework/harbor/tree/dc933be707feafbb9efcdf092cb8a0e391332617) |
| Inspect AI | [a1dbea8d](https://github.com/UKGovernmentBEIS/inspect_ai/tree/a1dbea8db3cc85e04ff532760d0eaaeb64df6d3a) |
| SWE-bench | [02e7a74f](https://github.com/SWE-bench/SWE-bench/tree/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e) |
| Legacy Terminal-Bench | [d28711d0](https://github.com/laude-institute/terminal-bench/tree/d28711d0da2675d0bb1d56de45ae5df6082438a3) |
| Terminal-Bench 4.1 (Harbor Suite) | [v4.1.0](https://github.com/harbor-framework/terminal-bench/releases/tag/v4.1.0) |

代码 license 不代表任务数据/镜像许可。发布安装环境前核对对应 release notices；
不直接复制作者 fork 的未许可题库与流水线。

## Terminal-Bench 4.1（`harbor-framework/terminal-bench@v4.1.0`）关键工程演进

在增补报告十（[中文深度版](../reports/terminal-bench-4-1.md) · [English Monograph](../reports/terminal-bench-4-1.en.md) · [7 页卡片报告](../../examples/terminal-bench-4-1-card-report/index.zh-CN.html)）中，我们对基于 Harbor 构建的 **Terminal-Bench 4.1**（65 组运行、66 道容器任务、21,450 轮试验）做了完整数据与机制审计，其中两项上游架构设计直接印证并补齐了本仓库首期提出的隔离缺口：

1. **双容器物理隔离判分（`environment_mode = "separate"` + `artifacts[]`）**：
   - 早期同容器判分模式下，拥有 `root` 权限的 Agent 存在窥探评测夹具、残留后台守护进程或劫持动态库的风险。
   - TB 4.1 在 `task.toml` 中支持声明 `environment_mode = "separate"` 与显式提取路径 `artifacts = [...]`：当 Agent 主动结束或触发 8 小时（`28,800s`）超时后，编排器先将 Agent 容器**停机冻结**，仅将白名单产物拷贝至全新的无网络 `tests/Dockerfile` 验证容器内运行 `tests/test.sh` 并写入 `reward.txt`。
2. **连续基准语义化版本契约（`x.y.z = Rerun . Regrade . Reuse`）**：
   - **`x`（Major = Rerun）**：任务分布或提示语义发生破坏性重构（如 TB 2.1 饱和至 `87.42%` 后，TB 3.0 洗牌回落至 `42.70%`，TB 4.0 重建 66 题 7 领域体系），历史运行需全量重跑；
   - **`y`（Minor = Regrade）**：验证器边界加固或迁移至独立验证容器（如 `4.0 → 4.1`），对已保存的有效产物执行确定性重判或受影响子集补跑，避免全榜重复烧钱；
   - **`z`（Patch = Reuse）**：纯元数据或文档清理，直接复用既有密封得分。
3. **验证器反馈紧密度主导解决率（「编译器神谕定律」）**：
   - 全榜 21,450 轮试验中仅 `0.69%`（147 轮）因 8 小时耗尽超时，高达 `59.92%`（12,852 轮）系 Agent 盲目自信提前退出后判分失败（如 `bun-sourcemap-leak` 出现 `325/325` 零超时全败）。这表明本仓库在 Harness 层强制引入「提交前反向不变量检查门禁」与工作区外独立验证器是决定生产可靠性的关键。
