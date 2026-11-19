# Terminal-Bench 4.1 七卡视觉评测报告（4:5 竖版卡片组）

**[English](README.en.md)** | **中文说明**

本目录提供 **Terminal-Bench 4.1（`terminal-bench@4.1.0` / Harbor Framework）** 的自包含 7 卡 `4:5` 视觉卡片组，覆盖 65 组榜单运行、52 组唯一 `(Model, Agent)` 组合、66 道容器化真实任务与 21,450 轮密封试验统计：

- **英文标准卡片组（由 `cards.py` 确定性生成）**：[`index.html`](index.html)
- **中文深度本地化卡片组**：[`index.zh-CN.html`](index.zh-CN.html)
- **配套深度研究长文**：[`../../docs/reports/terminal-bench-4-1.md`](../../docs/reports/terminal-bench-4-1.md)（中文） / [`../../docs/reports/terminal-bench-4-1.en.md`](../../docs/reports/terminal-bench-4-1.en.md)（英文）
- **结构化源数据与 CSV**：[`../../data/reported/terminal-bench-4-1/`](../../data/reported/terminal-bench-4-1/)

## 复现实验卡片生成

```bash
uv run --no-sync benchmark-harness cards data/reported/terminal-bench-4-1/report.json --output examples/terminal-bench-4-1-card-report/index.html
```

## 合规与防污染声明

- **数据溯源**：`provenance: "anonymized_reported"`（`independently_reproduced: false`），全部指标归属上游公开权威基准 [TERMINAL-BENCH (`tbench.ai`)](https://www.tbench.ai/) 与 [`harbor-framework/terminal-bench`](https://github.com/harbor-framework/terminal-bench)（Apache-2.0，快照 `2026-11-19`）。
- **零污染红线**：仓库内仅包含聚合评测统计与架构分析，**严禁且未包含任何原始题面、Oracle 答案脚本或 Canary GUID 字符串**。
- **离线安全锁**：内建严格 CSP（`default-src 'none'; style-src 'unsafe-inline'`），零外部脚本与网络请求。
