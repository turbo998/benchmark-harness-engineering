# Edge Decision Model (Kev-0.8B / 4B) Counterfactual SFT, Temperature Calibration & 8-bit GGUF Deployment: Historical Fact Archive (Supplement 7)

**Provenance:** `anonymized_reported`, bilingual archive (`zh-CN` / `en`), not independently reproduced (`independently_reproduced=false`).
Compiled from empirical validation of `jaredpalmer/kev-0.8b@v1.0` (`Qwen/Qwen3.5-0.8B-Base`, commit `dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68`) and `kev-4b@v1.0` (`Qwen/Qwen3.5-4B`) across enterprise support ticket triage (`Support`) and internal policy gating (`Assistant`), covering counterfactual supervised fine-tuning (SFT), post-hoc temperature calibration, and `llama.cpp b11935` 8-bit `Q8_0` / custom `Q4_K_M` GGUF execution on Qualcomm Snapdragon X Elite AIPC and Azure x86-64 CPUs.
Chinese version: [routing-aipc-kev-sft.md](routing-aipc-kev-sft.md);
structured data: [JSON](../../data/reported/routing-aipc-kev-sft/report.json),
[SFT Accuracy Progression CSV](../../data/reported/routing-aipc-kev-sft/sft_accuracy_progression.csv),
[Edge Quantization & Memory Matrix CSV](../../data/reported/routing-aipc-kev-sft/edge_quantization_matrix.csv),
[x86-64 Concurrency Scaling CSV](../../data/reported/routing-aipc-kev-sft/concurrency_scaling_x64.csv), and
[Self-Contained 7-Card 4:5 Visual Report HTML](../../examples/aipc-kev-sft-card-report/index.html).

---

## 1. Executive Summary

1. **Counterfactual SFT Delivers `+31.5` to `+51.6` Points Accuracy Gain**:
   - The unadapted release checkpoint `B0` (`0.8B`) lacks enterprise policy rules, scoring only **`44.7%`** on Support ID (510 questions) and **`43.0%`** on Support OOD (1,011 questions), and **`67.1%` / `65.7%`** on Assistant ID (477 q) / OOD (951 q).
   - Stuffing enterprise policy rules into the prompt without weight training (`B0-policy`, expanding prompts from `~950` to `~4,600` chars) only reaches **`60.8%`** on Support ID while slowing laptop CPU inference **6.5x** (`666 ms -> 4,353 ms`) and raising peak working set RAM to `3,446 MiB`.
   - The delivered Round 2 recipe **`R2-C`** (`4,038` counterfactual enterprise rows + `1,000` `decision-v7` replay rows, trained for 4 epochs in `22m 42s` on 1× NVIDIA H100 NVL at `7,475 MiB` peak VRAM) lifts the `0.8B` model in PyTorch to:
     - **Support ID**: **`96.3%`** (**`+51.6 pts`** vs `B0`)
     - **Support OOD**: **`88.4%`** (**`+45.4 pts`** vs `B0`)
     - **Assistant ID**: **`100.0%`** (**`+32.9 pts`** vs `B0`)
     - **Assistant OOD**: **`97.3%`** (**`+31.5 pts`** vs `B0`)
     - **OOD Single-Field Flip (312 pairs)**: **`48.4% -> 76.9%`** (**`+28.5 pts`**, with days-window flips jumping `37.4% -> 78.6%` and region flips `35.7% -> 69.0%`)
     - **Public General Benchmark (`transfer-v4`, 656 q)**: **`64.8% -> 65.2%`** (**`+0.4 pts`**, zero catastrophic forgetting).
2. **Post-Hoc Temperature Scaling ($T = 2.83$) Restores Probability Calibration**:
   - Multi-epoch SFT sharpens raw logits; fitting a scalar temperature $T = 2.83$ on the validation split preserves argmax accuracy while cutting Support ID Brier score from `0.641` to **`0.063`** (ECE **`0.025`**) and Assistant ID ECE from `0.168` to **`0.009`** (Brier `0.003`), achieving **`100.0%` automation coverage** at $\le 5\%$ error on ID splits.
3. **8-bit `Q8_0` GGUF Runs Losslessly in 2–3 GB CPU Memory**:
   - The exported `Contoso-Kev-0.8B-FTcf-R2C-Q8_0.gguf` artifact weighs **`775 MiB`** (`774.8 MiB`, `8.52 BPW`).
   - On **Qualcomm Snapdragon X Elite (`X1E80100`)** CPU in single-question mode (2,949 requests, concurrency 1), `Q8_0` achieves **`97.06%`** Support ID accuracy (**`386.34 ms`** median latency, ECE `0.034`), **`99.58%`** Assistant ID (**`409.32 ms`**, ECE `0.007`), **`88.72%`** Support OOD (**`635.37 ms`**), and **`96.95%`** Assistant OOD (**`448.31 ms`**), with a peak working set of **`2,585 MiB` (`~2.52 GiB`)**.
   - In 3-questions-per-request batched mode, tightening `llama-server` flags from `-c 8192 -b 2048 -ub 2048` to compact **`-c 2048 -b 512 -ub 512`** cuts Windows Commit Memory from `5,014 MiB` to **`2,119 MiB`** (Peak Working Set **`2,196 MiB`**) with **987/987 bitwise-identical** output probabilities.

---

## 2. Under the Hood: Pointer Decision Head & LoRA-All Recipe

Unlike generative LLMs that decode JSON tokens autoregressively, `Kev` attaches a **256-dimensional Pointer Decision Head** to the `Qwen3.5` backbone:

1. **Single-Prefill Pointer Scoring (Zero Decode Loop)**:
   - Candidate options are embedded directly in the prompt with special option markers ($h_{\text{opt}_i}$) followed by a decision query marker ($h_{\text{decide}}$).
   - Linear projections $q(\cdot), k(\cdot) \in \mathbb{R}^{d \times 256}$ score each candidate option via scaled dot-product in a single prefill pass:
     $$z_i = \frac{k(h_{\text{opt}_i})^\top q(h_{\text{decide}})}{16}, \qquad p_i = \text{softmax}\!\left(\frac{z}{T}\right)_i$$
   - Because no autoregressive token generation occurs, a single forward pass can score multiple decisions on the same ticket while keeping KV buffer requirements minimal.
2. **LoRA-All + Trainable Decision Head**:
   - `Qwen3.5` interleaves standard Attention, FFN, and **Gated DeltaNet** linear-attention blocks. LoRA (`rank=16, alpha=32`) is applied across **all** projection matrices (`q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`, and DeltaNet projections) alongside trainable `decision_q` and `decision_k` matrices (`11.3M` trainable parameters = `1.4%` for `0.8B`; `33.8M` = `0.8%` for `4B`).
3. **Counterfactual Boundary Pairs + General Replay**:
   - Standard domain SFT (`FT`, 2,147 rows) learns surface correlations (`64.9%` OOD flip in Round 1). Pairing base tickets with single-field boundary flips (modifying only SLA days, claim amount, region, or photo evidence so the ground-truth label flips) plus `1,000` replay rows from `evals/v7/decision-v7` forces the pointer head to attend to exact threshold boundaries without degrading general benchmark accuracy (`64.8% -> 65.2%`).

---

## 3. SFT Progression & Calibration Matrix (PyTorch / 1× H100 NVL)

| Stage | Model Size | Training Recipe & Dataset | Train Time | Peak GPU (MiB) | Temp $T$ | Support ID (510 q) | Assistant ID (477 q) | Support OOD (1,011 q) | Assistant OOD (951 q) | Support ID Brier / ECE | OOD Flip Acc (312 pairs) | Public `transfer-v4` (656 q) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`B0`** | `0.8B` | Release checkpoint (no enterprise rules) | 0 | — | 1.00 | 44.7% | 67.1% | 43.0% | 65.7% | 0.641 / 0.048 | 48.4% | 64.8% |
| **`B0-policy`** | `0.8B` | Zero-training prompt policy injection (`~950 -> ~4,600` chars) | 0 | — | 1.00 | 60.8% | 71.9% | — (`null`) | — (`null`) | 0.562 / 0.150 | — (`null`) | — (`null`) |
| **`FT`** | `0.8B` | Standard SFT: 2,147 vendor rows + 1k replay, 2 ep (`1×8`) | 26.9m | 4,555 | 1.26 | 86.5% | 93.5% | — (`null`) | — (`null`) | 0.197 / 0.030 | — (`null`) | 65.1% |
| **`FT-cf`** | `0.8B` | Round 1 counterfactual SFT: 3,832 rows + 1k replay, 2 ep (`4×2`) | 11.6m | 7,573 | 1.15 | 86.9% | 97.5% | 82.5% | 94.4% | 0.185 / 0.029 | 64.9% | 64.8% |
| **`R2-A`** | `0.8B` | Round 2 targeted counterfactuals: 4,038 rows (+116 region, +90 onsite), 2 ep | 14.25m | 13,589 | 1.20 | 88.0% | 97.5% | 83.3% | 94.7% | 0.172 / 0.032 | 66.8% | 64.5% |
| **`R2-B`** | `0.8B` | Round 2 4-epoch schedule: 3,832 rows, 4 ep (`4×2`) | 21.97m | 7,495 | 2.41 | 92.2% | 99.8% | 84.8% | 97.5% | 0.123 / 0.025 | 71.1% | 64.6% |
| **`R2-C` (Delivered)** | **`0.8B`** | **Targeted counterfactuals + 4 ep: 4,038 rows + 1k replay (`4×2`)** | **22.7m** | **7,475** | **2.83** | **96.3%** | **100.0%** | **88.4%** | **97.3%** | **0.063 / 0.025** | **76.9%** | **65.2%** |
| **`4B-B0`** | `4B` | `4B` release checkpoint (no enterprise rules) | 0 | — | 1.00 | 60.8% | 81.8% | 60.7% | 81.9% | 0.459 / 0.059 | — (`null`) | 74.1% |
| **`4B-FT-cf`** | `4B` | `4B` Round 1 counterfactual SFT: 3,832 rows, 2 ep | 20.1m | 26,215 | 2.35 | 95.9% | 99.8% | 91.4% | 98.8% | 0.068 / 0.025 | — (`null`) | 74.2% |

---

## 4. Edge GGUF Quantization, Memory Footprint & Cross-ISA Matrix (`llama.cpp b11935`)

| Model Variant & Batching | Hardware | Quantization (BPW) | File Size (MiB) | `llama-server` Context Flags | Support ID Acc | Assistant ID Acc | Support OOD Acc | Assistant OOD Acc | Support Median (ms) | Assistant Median (ms) | Peak Working Set (MiB) | Commit Memory (MiB) |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`0.8B R2-C Q8_0` (1q/req)** | **Snapdragon X Elite CPU** | **`Q8_0` (8.52)** | **774.8** | `-c 8192 -b 2048 -ub 2048 --cache-ram 0` | **97.06%** | **99.58%** | **88.72%** | **96.95%** | **386.34** | **409.32** | **2,585** | — (`null`) |
| **`0.8B R2-C Q8_0` (3q/req default)** | Snapdragon X Elite CPU | `Q8_0` (8.52) | 774.8 | `-c 8192 -b 2048 -ub 2048` | 96.9% | 99.6% | — (`null`) | — (`null`) | 635.0 | 905.0 | 2,314 | 5,014 |
| **`0.8B R2-C Q8_0` (3q/req compact)** | **Snapdragon X Elite CPU** | **`Q8_0` (8.52)** | **774.8** | **`-c 2048 -b 512 -ub 512`** | **96.9%** | **99.6%** | — (`null`) | — (`null`) | **851.0** | **1023.0** | **2,196** | **2,119** |
| **`0.8B R2-C Q8_0` (3q/req x64 default)** | Azure `D16as_v5` (EPYC 7763) | `Q8_0` (8.52) | 774.8 | `-c 8192 -b 2048 -ub 2048` | 96.5% | 99.8% | — (`null`) | — (`null`) | 1260.0 | 1430.0 | 1,552 | 4,284 |
| **`0.8B R2-C Q8_0` (3q/req x64 compact)** | **Azure `D16as_v5` (EPYC 7763)** | **`Q8_0` (8.52)** | **774.8** | **`-c 2048 -b 512 -ub 512`** | **96.5%** | **99.8%** | — (`null`) | — (`null`) | **1255.0** | **1421.0** | **1,421** | **1,360** |
| `0.8B FT-cf BF16` (3q/req) | Snapdragon X Elite CPU | `BF16` (16.0) | 1,446.6 | `-c 8192 -b 2048 -ub 2048` | 86.9% | 97.5% | 82.5% | 94.4% | 1007.0 | 1207.0 | 3,001 | — (`null`) |
| `0.8B FT-cf Q8_0` (3q/req) | Snapdragon X Elite CPU | `Q8_0` (8.52) | 774.8 | `-c 8192 -b 2048 -ub 2048` | 86.9% | 97.9% | 82.1% | 94.5% | 674.0 | 825.0 | 2,333 | — (`null`) |
| `0.8B FT-cf Custom Q4_K_M` (3q/req) | Snapdragon X Elite CPU | `Q4_K_M` (5.76) | 527.8 | `-c 8192 -b 2048 -ub 2048` | 87.3% | 97.3% | 81.8% | 94.0% | 657.0 | 798.0 | 2,088 | — (`null`) |
| `0.8B FT Q8_0` Adreno GPU (`-ngl 99`) | Snapdragon Adreno X1-85 OpenCL | `Q8_0` (8.52) | 774.8 | `-ngl 99 -c 8192` | 86.5% | 93.7% | — (`null`) | — (`null`) | 1035.0 | 1221.0 | 4,105 | — (`null`) |
| `4B FT-cf Q8_0` (3q/req) | Snapdragon X Elite CPU | `Q8_0` | 4,276.0 | `-c 8192 -b 2048 -ub 2048` | 96.3% | 99.8% | 91.5% | 99.1% | 2368.0 | 2925.0 | 6,122 | — (`null`) |
| `4B FT-cf Custom Q4_K_M` (3q/req) | Snapdragon X Elite CPU | `Q4_K_M` | 2,893.0 | `-c 8192 -b 2048 -ub 2048` | 95.3% | 99.6% | 91.1% | 98.4% | 2033.0 | 2380.0 | 4,743 | — (`null`) |

---

## 5. CPU Concurrency Scaling & Long-History Boundary (`Standard_D16as_v5`)

| Concurrency $N$ | Server Config | Requests | Correct / Acc (%) | Timeouts (>30s) | Median Latency (s) | P95 Latency (s) | Throughput (req/s) | Peak Working Set (MiB) | Commit Memory (MiB) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **1** | `-c 8192 -np 1` | 384 | 360 / **93.75%** | 0 | **0.92** | 1.38 | **0.923** | **1,674** | 4,412 |
| **2** | `-c 16384 -np 2` | 384 | 360 / **93.75%** | 0 | **2.32** | 2.86 | **0.929** | **1,790** | 4,528 |
| **4** | `-c 32768 -np 4` | 384 | 360 / **93.75%** | 0 | **4.21** | 5.39 | **0.930** | **2,238** | 4,976 |
| **8** | `-c 65536 -np 8` | 384 | 360 / **93.75%** | 0 | 8.48 | 10.71 | 0.925 | 3,756 | 6,494 |
| **16** | `-c 131072 -np 16` | 384 | 360 / **93.75%** | 0 | 16.57 | 20.89 | 0.927 | 5,033 | 7,771 |
| **32** | `-c 262144 -np 32` | 384 | 351 / 91.41% | 9 | 26.20 | 30.00 | 0.919 | 6,906 | 9,644 |

- **Long-History Boundary (`3k–8k` tokens)**: On 160 raw multi-turn support transcripts (`3,000–8,000` tokens), 7 requests exceeded `-c 8192` and the remaining 153 cases (459 questions) dropped to **`44.9%`** accuracy at **`26,395 ms`** median latency (`5,060 MiB` peak working set). Always summarize long transcripts into structured state (`< 2,048` tokens) before calling the edge decision model.
