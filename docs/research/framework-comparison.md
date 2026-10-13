# 评测框架比较与首期选择

本页是固定源码研究后的原创选择，不保证研究 commit 是可安装 release。
实际运行版本必须从发行包选择并锁定，不能使用浮动 latest。

| 框架 | 适合承担 | 主要边界 |
|---|---|---|
| promptfoo | API 候选、断言、repeat/resume、结果导出 | 输入合成不保证 oracle；safe mode 不是 sandbox；cost assertion 是事后检查 |
| Harbor | 编码任务、环境、verifier、agent/ATIF 轨迹 | Copilot adapter 未核实；默认同环境不保证隐藏 verifier；未知用量可能为 null |
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

代码 license 不代表任务数据/镜像许可。发布安装环境前核对对应 release notices；
不直接复制作者 fork 的未许可题库与流水线。
