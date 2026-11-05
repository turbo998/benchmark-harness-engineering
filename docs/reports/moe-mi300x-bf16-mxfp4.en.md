# Azure AMD MI300X Large MoE Models (Muse Spark Open / Nemotron 3 Ultra / Inkling) BF16 & MXFP4 Precision and Deployment Guide: Historical Fact Archive (Supplement 8)

**Provenance:** `anonymized_reported`, bilingual archive (`zh-CN` / `en`), not independently reproduced (`independently_reproduced=false`).
Compiled from real-hardware validation on Azure **`Standard_ND96isr_MI300X_v5`** (8× AMD Instinct MI300X 192 GB HBM3 per node = `1,536 GB` HBM3/node, Ubuntu 24.04.5 LTS, kernel `6.8.0-1067-azure`, ROCm host `6.4.4-129`) across three frontier open-weights MoE architectures—**`Muse Spark Open (816B-A42B)`**, **`NVIDIA Nemotron 3 Ultra (550B-A55B)`**, and **`Thinking Machines Lab Inkling (975B-A41B)`**—evaluating native **BF16** vs **OCP-MXFP4**, HBM3 memory budgets, operator backend routing, multi-node RCCL failure resolution, and streaming throughput (`C=1` and `C=8`).
Chinese version: [moe-mi300x-bf16-mxfp4.md](moe-mi300x-bf16-mxfp4.md);
structured data: [JSON](../../data/reported/moe-mi300x-bf16-mxfp4/report.json),
[Model Census CSV](../../data/reported/moe-mi300x-bf16-mxfp4/mi300x_model_census.csv),
[BF16 / MXFP4 Validation Matrix CSV](../../data/reported/moe-mi300x-bf16-mxfp4/mi300x_bf16_mxfp4_runs.csv),
[Throughput & Latency Probe CSV](../../data/reported/moe-mi300x-bf16-mxfp4/mi300x_perf_probe.csv), and
[Self-Contained 7-Card 4:5 Visual Report HTML](../../examples/moe-mi300x-card-report/index.html).

---

## 1. Executive Summary

1. **All Three 550B–975B MoE Models Pass Native BF16 on Azure MI300X with High Throughput**:
   - Leveraging **192 GB HBM3 per GPU** (`1,536 GB` per 8-GPU node), `Nemotron 3 Ultra (550B-A55B)` (`1,044.06 GiB` BF16 weights) fits entirely on a **single `Standard_ND96isr_MI300X_v5` node (`TP8 + EP8`)**, delivering **`60.7 tok/s`** single-stream decode (`170 ms` TTFT) and **`317.4 tok/s`** aggregate throughput at `C=8`.
   - `Muse Spark Open (816B-A42B)` (`1,531.41 GiB` BF16) and `Inkling (975B-A41B)` (`1,773.94 GiB` BF16) run in native BF16 across **2 nodes (16× MI300X, Ray `TP8 × PP2`)**:
     - `Muse Spark Open`: **`84.6 tok/s`** decode at `C=1` (`205 ms` TTFT), **`348.6 tok/s`** aggregate at `C=8`, with **`72.02 GiB`/GPU free KV cache** (`8,130,184` tokens).
     - `Inkling`: **`68.9 tok/s`** decode at `C=1` (**`45 ms`** TTFT), **`335.8 tok/s`** aggregate at `C=8` (`97 ms` TTFT), with **`51.02–57.39 GiB`/GPU free KV cache**.
2. **OCP-MXFP4 on MI300X (`gfx942`) Is a Memory-Density & Node-Consolidation Mode**:
   - **Nemotron 3 Ultra Online MoE MXFP4 (1 Node `TP8 + EP8`)**: Compresses per-GPU model weights by **`68.3%`** (`136.51 -> 43.21 GiB/GPU`) and expands available KV cache by **`3.94x`** (`23.07 -> 111.86 GiB/GPU`, `13,758,836` tokens).
   - **Inkling 975B Quark MXFP4 (1 Node `TP8`, Halving Hardware from 16 to 8 GPUs)**: Using `lightseekorg/Inkling-MXFP4`, the 975B model fits on a **single 8-GPU MI300X node** at **`66.74 GiB/GPU`** weights with **`94.79 GiB/GPU`** free KV cache.
   - **Why MXFP4 Decode Is `5.8–7.5x` Slower Than BF16 on MI300X**: AMD Instinct MI300X (`CDNA3 / gfx942`) provides native matrix cores for FP16/BF16/FP8/INT8, while hardware FP4 matrix instructions arrive in `CDNA4 / gfx950` (MI355X) and NVIDIA Blackwell. Consequently, MI300X executes MXFP4 via `OCP_MXQuantizationEmulationTritonExperts` software dequantization (`54.9 tok/s` @ `C=8` on Nemotron; `44.6 tok/s` @ `C=8` on Inkling).
   - **Muse Spark Open MXFP4 Status**: `MuseSpark1x` in vLLM enforces a hard check requiring `AITER_MXFP4_MXFP4` (`gfx950`) and explicitly rejects `EMULATION` on `gfx942`.

---

## 2. Checkpoint Tensor Census & Architecture Comparison

| Model (`repo @ rev`) | Total / Active Params | Layer & Expert Topology | Hybrid Operators & Tensor Dtypes | BF16 Weight Size (GB / GiB) | NVFP4 Weight Size (GB / GiB) | Min MI300X Nodes (BF16) | Min MI300X Nodes (MXFP4) |
|---|---|---|---|---:|---:|---:|---:|
| **`Muse-Spark-Open-816B-A42B`** (`0fb02478`) | **816B / 42B** | 62 layers, 256 routed experts (top-8), no shared experts | Standard Attention + Routed MoE; vendor container ships `gfx950`-only fused kernel | **1,644.33 GB / 1,531.41 GiB** | 533.01 GB / 496.41 GiB | **2 Nodes (16 GPUs)** | 1 Node (Blocked in software on `gfx942`) |
| **`NVIDIA-Nemotron-3-Ultra-550B-A55B`** (`77df655d`) | **550B / 55B** | Hybrid stack, 225 files / 51,023 tensors | **Mamba-2 SSM + Attention + non-gated `relu2` LatentMoE + MTP**; `gate.weight` BF16, `e_score_correction_bias` F32 | **1,121.05 GB / 1,044.06 GiB** | 320.07 GB / 298.09 GiB | **1 Node (8 GPUs)** | **1 Node (8 GPUs)** |
| **`ThinkingMachines-Inkling`** (`828496ee` / `bc3fdef2`) | **975B / 41B** | 66 layers, 256 routed (top-6) + 2 shared experts, 109 files / 1,552 tensors | **Local/Global Attention + 264 ShortConv (`sconv`) kernels + MTP**; SWA requires `tp_size <= num_kv_heads (8)` | **1,904.76 GB / 1,773.94 GiB** | 592.01 GB / 551.35 GiB | **2 Nodes (16 GPUs)** | **1 Node (8 GPUs, Quark MXFP4)** |

---

## 3. Main Validation Matrix & HBM3 Memory Budget on Azure MI300X

| Model | Precision | Status | Nodes / GPUs | Parallelism | Container & Active Operator Backends | Max Context | Weight / GPU (GiB) | Consumed / GPU (GiB) | Free KV / GPU (GiB) | KV Cache Capacity (Tokens) | Max Concurrency @ Context |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| **Muse Spark Open 816B** | **BF16** | **PASS** | 2 Nodes / 16 GPUs | `TP8 × PP2` (Ray) | `vllm-openai-rocm:v0.33.0` · `MuseSparkTritonExperts` + `ROCM_AITER_FA` | 32,768 | **99.10** | 102.70 | **72.02** | **8,130,184** | 248.11x |
| **Muse Spark Open 816B** | **OCP-MXFP4** | **FAIL** | 1 Node / 8 GPUs | `TP8` | `vllm-openai-rocm:v0.33.0` · Rejects `EMULATION` (`Requires AITER_MXFP4_MXFP4`) | 32,768 | — (`null`) | — (`null`) | — (`null`) | — (`null`) | — (`null`) |
| **Nemotron 3 Ultra 550B** | **BF16** | **PASS** | **1 Node / 8 GPUs** | `TP8 + EP8` | `rocm/vllm v0.29.0` · `TritonExperts` (`AITER_MOE=0`) + `ROCM_ATTN` + `triton` Mamba | 65,536 | **136.51** | 146.78 | **23.07** | **3,490,022** | 53.25x |
| **Nemotron 3 Ultra 550B** | **Online MXFP4** | **PASS** | **1 Node / 8 GPUs** | `TP8 + EP8` | `vllm-openai-rocm:v0.33.0` · `OCP_MXQuantizationEmulationTritonExperts` | 32,768 | **43.21** | 53.48 | **111.86** | **13,758,836** | 419.89x |
| **Inkling 975B** | **BF16** | **PASS** | 2 Nodes / 16 GPUs | `TP8 × PP2` (Ray) | `rocm/vllm v0.29.0` · `AiterExperts` + `ROCM_ATTN` + `sconv` (`GDR_LEVEL=0`) | 65,536 | **109.52 / 116.12** | 112.54 / 118.90 | **51.02 / 57.39** | **398,239** | 6.08x |
| **Inkling 975B** | **Quark MXFP4** | **PASS** | **1 Node / 8 GPUs** | `TP8` (Halved Nodes) | `vllm-openai-rocm:v0.33.0` · `AiterUnquantized` + `OCP_MXQuantizationEmulation` | 32,768 | **66.74** | 70.21 | **94.79** | **305,150** | 9.31x |

---

## 4. Streaming Performance Probe (`max_tokens=256`, `C=1` vs `C=8`)

| Model & Precision | Topology | Concurrency $C$ | TTFT (ms) | Decode Speed (tok/s) | E2E Latency (s) | Aggregate Throughput (tok/s) |
|---|---|---:|---:|---:|---:|---:|
| **Muse Spark Open 816B (BF16)** | 2 Nodes / 16× MI300X (`TP8 × PP2`) | 1 | 205.0 | **84.6** | 3.22 | 79.5 |
| **Muse Spark Open 816B (BF16)** | 2 Nodes / 16× MI300X (`TP8 × PP2`) | 8 | 506.0 | 47.6 | 5.88 | **348.6** |
| **Nemotron 3 Ultra 550B (BF16)** | 1 Node / 8× MI300X (`TP8 + EP8`) | 1 | 170.0 | **60.7** | 4.37 | 58.6 |
| **Nemotron 3 Ultra 550B (BF16)** | 1 Node / 8× MI300X (`TP8 + EP8`) | 8 | 358.0 | 42.0 | 6.45 | **317.4** |
| **Nemotron 3 Ultra 550B (MXFP4 Emulation)** | 1 Node / 8× MI300X (`TP8 + EP8`) | 1 | 178.0 | 7.7 | 33.42 | 7.7 |
| **Nemotron 3 Ultra 550B (MXFP4 Emulation)** | 1 Node / 8× MI300X (`TP8 + EP8`) | 8 | 484.0 | 6.9 | 37.30 | **54.9** |
| **Inkling 975B (BF16)** | 2 Nodes / 16× MI300X (`TP8 × PP2`) | 1 | **45.0** | **68.9** | 3.75 | 68.3 |
| **Inkling 975B (BF16)** | 2 Nodes / 16× MI300X (`TP8 × PP2`) | 8 | **97.0** | 42.5 | 6.10 | **335.8** |
| **Inkling 975B (Quark MXFP4 Emulation)** | 1 Node / 8× MI300X (`TP8`) | 1 | 358.0 | 6.1 | 41.97 | 6.1 |
| **Inkling 975B (Quark MXFP4 Emulation)** | 1 Node / 8× MI300X (`TP8`) | 8 | 726.0 | 5.7 | 45.92 | **44.6** |

---

## 5. Deployment Troubleshooting & Verified Production Recipes

1. **`Muse Spark Open (816B-A42B)`**: Do not use the `muse-spark-open:latest` image on MI300X (`gfx942`); its precompiled `fused_muse_spark_qknorm_rope_kv_insert_kernel.hip` targets `gfx950` only and crashes with `SIGSEGV`. Use `vllm/vllm-openai-rocm:v0.33.0` + `ray==2.55.1` with `--tensor-parallel-size 8 --pipeline-parallel-size 2`.
2. **`NVIDIA Nemotron 3 Ultra (550B-A55B)`**: Export `VLLM_ROCM_USE_AITER_MOE=0` so vLLM routes its non-gated `relu2` `LatentMoE` layers to `TritonExperts` instead of gated AITER MoE, and omit `--enable-mamba-cache-stochastic-rounding` (avoids `PHILOX_ROUNDS` `ld.lld: error: target emulation unknown`).
3. **`Thinking Machines Lab Inkling (975B-A41B)`**:
   - Export **`NCCL_NET_GDR_LEVEL=0`** across both nodes to eliminate the 240-second 16-rank RCCL hang (restoring `52.4 GB/s` bus bandwidth / `2.4 ms` on 64 MiB `all_reduce`).
   - Use **`TP8 × PP2`** (`--tensor-parallel-size 8 --pipeline-parallel-size 2`), never `TP16` (violates `sconv` `tp_size <= num_kv_heads (8)`) or `TP8 × DP2 + EP16` (hangs in remote DP coordinator RPC on the second request).
4. **NVFP4 Single-Expert Numerical Fidelity Probe**: On 1× MI300X, `Nvfp4QuantizationEmulationTritonExperts` matched PyTorch reference outputs with relative L2 error **`0.0`** (`Nemotron-3-Ultra-NVFP4`) and **`3.74e-9`** (`Inkling-NVFP4`), well below the `0.02` acceptance threshold.
