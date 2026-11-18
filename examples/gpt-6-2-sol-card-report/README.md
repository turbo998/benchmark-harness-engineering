# GPT-6.2 Sol 7-Card 4:5 视觉评测报告示例（增补报告 9）

> 🌐 **Language / 语言切换**: **中文说明** | **[English README](README.en.md)**

本目录提供 **增补报告 9：GPT-6.2 Sol 全档推理实测、校准路由与二十一模型前沿基准（`2026-11-18`）** 的自包含 7 页 `4:5` 竖版视觉卡片报告（`900px × 1125px`，`provenance="measured"`，`independently_reproduced=true`）。

## 文件说明

- [`index.zh-CN.html`](index.zh-CN.html)：中文版 7-Card `4:5` 视觉卡片报告（含顶部相对导航栏与完整内嵌 `report.zh-CN.json` 数据）。
- [`index.html`](index.html)：英文版 7-Card `4:5` 视觉卡片报告，由 `benchmark_harness.cards` 从密封数据源字节级确定性渲染生成。
- 关联完整技术评测报告：
  - 中文版：[`../../docs/reports/gpt-6-2-sol-benchmark.md`](../../docs/reports/gpt-6-2-sol-benchmark.md)
  - English Version：[`../../docs/reports/gpt-6-2-sol-benchmark.en.md`](../../docs/reports/gpt-6-2-sol-benchmark.en.md)
- 密封数据源与遥测目录：[`../../data/reported/gpt-6-2-sol-benchmark/`](../../data/reported/gpt-6-2-sol-benchmark/)（含 `report.json`、`report.zh-CN.json`、`freeze_manifest.json` 与 5 份实测/外部矩阵 CSV）。

## 本地离线查看与确定性重新生成

两份 HTML 卡片集均启用严格内容安全策略 `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'`，零外部字体、零网络请求、零 `<script>`，下载后可直接双击离线在浏览器打开。

在仓库根目录重新生成 `index.html`（与 `src/benchmark_harness/cards.py` 逐字节一致）：

```bash
uv run benchmark-harness cards data/reported/gpt-6-2-sol-benchmark/report.json --output examples/gpt-6-2-sol-card-report/index.html
```
