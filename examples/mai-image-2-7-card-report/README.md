# MAI-Image-2.7 与 2.7-Flash 商业图像编辑基准七卡视觉报告（4:5 竖版卡片组）

**[English](README.en.md)** | **中文说明**

本目录提供 **MAI-Image-2.7 与 MAI-Image-2.7-Flash 商业图像编辑基准评测（基于学术界 `ServImage` `arXiv:2604.24023v2` 复现并扩展 Editable 商业修图套件）** 的自包含 7 卡 `4:5` 竖版视觉评测卡片组，基于 `Microsoft Foundry GlobalStandard` 真实执行的 **121 轮 API 实测**（`8 款模型 × 12 个商业场景 = 96 轮主实验` + `9 轮双轮品牌一致性` + `16 轮中英双语提示词扰动`，实测总账单 `$6.041`）：

- **中文深度本地化卡片组**：[`index.zh-CN.html`](index.zh-CN.html)
- **英文标准卡片组**：[`index.html`](index.html)
- **配套中英双语技术深度报告**：[`../../docs/reports/mai-image-2-7-commercial-editing-benchmark.md`](../../docs/reports/mai-image-2-7-commercial-editing-benchmark.md)（中文） / [`../../docs/reports/mai-image-2-7-commercial-editing-benchmark.en.md`](../../docs/reports/mai-image-2-7-commercial-editing-benchmark.en.md)（英文）
- **结构化密封数据与 CSV**：[`../../data/reported/mai-image-2-7-commercial-editing/`](../../data/reported/mai-image-2-7-commercial-editing/)
- **交互式原图逐像素滑块比对工作台**：[中文 Studio](https://turbo998.github.io/workshops/benchmarks/mai-image-2-7-commercial-edit-bench.html) · [English Studio](https://turbo998.github.io/workshops/benchmarks/mai-image-2-7-commercial-edit-bench.en.html) · [配套样张库源码 (`generative-visual-lab`)](https://github.com/turbo998/generative-visual-lab/tree/main/demos/commercial-image-edit-benchmark-studio)

## 七卡结构概览（`#card-1` .. `#card-7`）

1. **`1 / 7` · `HANDS-ON · MULTIMODAL COMMERCIAL IMAGE EDITING`**：指令执行并列 `#1`（`BRF = 4.17/5.00`）与 `MAI-Image-2.7-Flash` 每美元 `41.67` 张零返工商业交付（`Sunburst` 的 `3.8x`、`FLUX.2-flex` 的 `8.7x`）工作台总览。
2. **`2 / 7` · `SCENARIO: S11 NATIVE RGBA TRANSPARENT CUTOUT`**：单次 API 直出真 4 通道 `RGBA` 透明抠图深度剖析（边缘 Alpha 纯净度 `100.0%`，对比 `FLUX.2` 伪棋盘格 RGB 像素与前代 `MAI-Image-2.6` HTTP 400）。
3. **`3 / 7` · `WHAT I TESTED`**：全部 12 个 `1024×1024` 商业场景逐项密封矩阵（延迟、非编辑区 SSIM、三维盲评与 `Act automatically / Confirm / Send to a human` 流转门控）。
4. **`4 / 7` · `UNDER THE HOOD`**：三大 API 方言（MAI multipart、OpenAI Images、BFL FLUX JSON）归一化契约、SHA-256 参考图冻结与盲评 + 像素验证器流水线。
5. **`5 / 7` · `ROBUSTNESS CHECK`**：16 轮简体中文 vs 英文原生提示词扰动检验（MAI 双模型保持 `4/4` `100%` 商用通过；`FLUX.2-pro` 中文人像精修暴跌 `-66.6 pts` 失效）。
6. **`6 / 7` · `LATENCY & TWO-TIER PIPELINE`**：四大商业赛道中位端到端延迟对比（`Flash` `20.69s` 比 OpenAI 快 `2.0x`）与 `Flash ($0.010) -> 2.7 ($0.035)` 双层 `$0.045` 创意管线。
7. **`7 / 7` · `MY TAKE`**：生产级场景选型边界（`✅ Good fit` vs `⛔ Not for` 裸调禁区与前景蒙版回贴建议）及外部盲测交叉印证（Artificial Analysis v2.1 全球 `#1` `1,215 Elo`）。

## 合规、溯源与离线安全锁

- **数据溯源**：主实验 `provenance: "measured"`（`independently_reproduced: true`，121 轮真实 Foundry API 调用 + SHA-256 密封清单）；外部公开盲测引用显式标注 `provenance: "reported"`。
- **隐私脱敏红线**：端点统一脱敏为 `<foundry-resource>`，不包含任何内部资源名、订阅/租户 ID、私有链接或个人署名。
- **严格离线 CSP**：内建 `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">`，零 `<script>`、零外部字体与零网络资源加载，可直接离线打开审阅。
