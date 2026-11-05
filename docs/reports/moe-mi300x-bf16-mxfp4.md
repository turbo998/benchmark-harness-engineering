# Azure AMD MI300X 超大 MoE 模型（Muse Spark Open / Nemotron 3 Ultra / Inkling）BF16 与 MXFP4 精度及部署架构：历史事实整理（增补报告 8）

**来源性质：** `anonymized_reported`，中英文双语归档，未独立复现（`independently_reproduced=false`）。
基于在 Azure **`Standard_ND96isr_MI300X_v5`**（单节点 8× AMD Instinct MI300X 192 GB HBM3 = `1,536 GB` HBM3/节点，Ubuntu 24.04.5 LTS，内核 `6.8.0-1067-azure`，宿主机 ROCm `6.4.4-129`）上对三大前沿开源 MoE 模型——**`Muse Spark Open (816B-A42B)`**、**`NVIDIA Nemotron 3 Ultra (550B-A55B)`** 与 **`Thinking Machines Lab Inkling (975B-A41B)`**——分别以原生 **BF16** 与 **OCP-MXFP4** 运行的完整硬件验证、排障路径、显存/KV Cache 预算与并发吞吐探针整理。
英文版见 [moe-mi300x-bf16-mxfp4.en.md](moe-mi300x-bf16-mxfp4.en.md)；
结构化数据见 [JSON](../../data/reported/moe-mi300x-bf16-mxfp4/report.json)、
[模型权重与拓扑普查 CSV](../../data/reported/moe-mi300x-bf16-mxfp4/mi300x_model_census.csv)、
[BF16 / MXFP4 部署验证矩阵 CSV](../../data/reported/moe-mi300x-bf16-mxfp4/mi300x_bf16_mxfp4_runs.csv)、
[性能与吞吐探针 CSV](../../data/reported/moe-mi300x-bf16-mxfp4/mi300x_perf_probe.csv) 与
[可离线预览的 7 页 4:5 视觉卡片 HTML](../../examples/moe-mi300x-card-report/index.html)。

---

## 1. 核心结论摘要（Executive Summary）

1. **三大 550B–975B MoE 模型在 MI300X 上全部跑通原生 BF16 高吞吐服务**：
   - 凭借单卡 **192 GB HBM3**（单机 8 卡共 `1,536 GB`），`Nemotron 3 Ultra (550B-A55B)` 的 `1,044.06 GiB` BF16 权重可直接装入 **单台 `ND96isr_MI300X_v5` 节点（8× MI300X，`TP8 + EP8`）**，无需跨机通信或有损量化，单流（`C=1`）Decode 达 **`60.7 tok/s`**（TTFT `170 ms`），8 并发（`C=8`）总吞吐达 **`317.4 tok/s`**。
   - `Muse Spark Open (816B-A42B)`（BF16 权重 `1,531.41 GiB`）与 `Inkling (975B-A41B)`（BF16 权重 `1,773.94 GiB`）在 **2 台 `ND96isr_MI300X_v5` 节点（16× MI300X，Ray `TP8 × PP2`）** 上完美跑通原生 BF16：
     - `Muse Spark Open`：`C=1` Decode **`84.6 tok/s`**（TTFT `205 ms`），`C=8` 总吞吐 **`348.6 tok/s`**，每卡剩余 **`72.02 GiB` KV Cache**（可容纳 `8,130,184` tokens）。
     - `Inkling`：`C=1` Decode **`68.9 tok/s`**（TTFT 仅 **`45 ms`**），`C=8` 总吞吐 **`335.8 tok/s`**（TTFT `97 ms`），每卡剩余 **`51.02–57.39 GiB` KV Cache**。
2. **OCP-MXFP4 在 MI300X (`gfx942`) 上是“显存密度与降节点利器”，而非算力加速模式**：
   - **Nemotron 3 Ultra 在线 MoE MXFP4（1 节点 `TP8 + EP8`）**：将每卡权重显存从 `136.51 GiB` 压缩至 **`43.21 GiB`（削减 `68.3%`）**，每卡可用 KV Cache 从 `23.07 GiB` 暴涨至 **`111.86 GiB`（`13,758,836` tokens，提升 `3.94 倍`）**。
   - **Inkling 975B Quark MXFP4（1 节点 `TP8` 硬件减半）**：使用预量化 `lightseekorg/Inkling-MXFP4`，将原本必须 2 台节点（16 卡）才能装下的 975B 巨型模型成功收敛至 **1 台节点（8 卡）**，每卡权重仅 **`66.74 GiB`**，剩余 **`94.79 GiB` KV Cache**。
   - **为什么 MI300X 上 MXFP4 的 Decode 速度比 BF16 慢 `5.8–7.5 倍`？** MI300X 基于 CDNA3 (`gfx942`) 架构，硬件矩阵核心原生支持 FP16/BF16/FP8/INT8，**不包含硬件级原生 FP4 指令**（原生硬件 FP4 位于下一代 CDNA4 `gfx950` MI355X 与 NVIDIA Blackwell）。因此 vLLM 在 MI300X 上回退至 `OCP_MXQuantizationEmulationTritonExperts` 软件反量化仿真内核，`C=8` 总吞吐分别为 **`54.9 tok/s`**（Nemotron）与 **`44.6 tok/s`**（Inkling）。
   - **Muse Spark Open MXFP4 状态**：`vLLM` 的 `MuseSpark1x` 算子路由在源码中硬编码要求 `AITER_MXFP4_MXFP4`（`gfx950` 硬件后端），在 `gfx942` 上明确拒绝 `EMULATION` 后端并报错退出。

---

## 2. 三大模型权重普查与架构特征对比（Checkpoint Census）

| 模型名称与版本 (`repo @ rev`) | 总参数 / 激活参数 | 层数与专家路由结构 | 特殊混合算子与张量特征 | BF16 权重体积 (GB / GiB) | NVFP4 权重体积 (GB / GiB) | BF16 最小 MI300X 节点数 | MXFP4 最小 MI300X 节点数 |
|---|---|---|---|---:|---:|---:|---:|
| **`Muse-Spark-Open-816B-A42B`** (`0fb02478`) | **816B / 42B** | 62 层，256 路由专家（Top-8），无共享专家 | 标准 Attention + Routed MoE；官方镜像含 `gfx950` 专用融合算子 | **1,644.33 GB / 1,531.41 GiB** | 533.01 GB / 496.41 GiB | **2 节点 (16 卡)** | 1 节点（`gfx942` 软件栈拦截） |
| **`NVIDIA-Nemotron-3-Ultra-550B-A55B`** (`77df655d`) | **550B / 55B** | 混合层结构，225 文件 / 51,023 张量 | **Mamba-2 SSM + Attention + 非门控 `relu2` LatentMoE + MTP**；`gate.weight` 为 BF16，`e_score_correction_bias` 为 F32 | **1,121.05 GB / 1,044.06 GiB** | 320.07 GB / 298.09 GiB | **1 节点 (8 卡)** | **1 节点 (8 卡)** |
| **`ThinkingMachines-Inkling`** (`828496ee` / `bc3fdef2`) | **975B / 41B** | 66 层，256 路由专家（Top-6）+ 2 共享专家，109 文件 / 1,552 张量 | **Local/Global Attention + 264 个 `sconv` 短卷积核 + MTP**；滑动窗口要求 `tp_size <= num_kv_heads (8)` | **1,904.76 GB / 1,773.94 GiB** | 592.01 GB / 551.35 GiB | **2 节点 (16 卡)** | **1 节点 (8 卡，Quark MXFP4)** |

---

## 3. Azure MI300X 6 大主实验单元验证矩阵与显存预算

| 模型 | 精度模式 | 状态 | 节点 / GPU 数 | 并行拓扑 | 容器镜像与核心算子后端 | 最大上下文 | 每卡权重显存 (GiB) | 每卡总消耗 (GiB) | 每卡可用 KV Cache (GiB) | KV Cache 总容量 (Tokens) | 满长并发上限 |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|
| **Muse Spark Open 816B** | **BF16** | **PASS** | 2 节点 / 16 卡 | `TP8 × PP2` (Ray) | `vllm-openai-rocm:v0.33.0` · `MuseSparkTritonExperts` + `ROCM_AITER_FA` | 32,768 | **99.10** | 102.70 | **72.02** | **8,130,184** | 248.11x |
| **Muse Spark Open 816B** | **OCP-MXFP4** | **FAIL** | 1 节点 / 8 卡 | `TP8` | `vllm-openai-rocm:v0.33.0` · 拒绝 `EMULATION`，强制要求 `AITER_MXFP4_MXFP4` | 32,768 | — (`null`) | — (`null`) | — (`null`) | — (`null`) | — (`null`) |
| **Nemotron 3 Ultra 550B** | **BF16** | **PASS** | **1 节点 / 8 卡** | `TP8 + EP8` | `rocm/vllm v0.29.0` · `TritonExperts` (`AITER_MOE=0`) + `ROCM_ATTN` + `triton` Mamba | 65,536 | **136.51** | 146.78 | **23.07** | **3,490,022** | 53.25x |
| **Nemotron 3 Ultra 550B** | **Online MXFP4** | **PASS** | **1 节点 / 8 卡** | `TP8 + EP8` | `vllm-openai-rocm:v0.33.0` · `OCP_MXQuantizationEmulationTritonExperts` | 32,768 | **43.21** | 53.48 | **111.86** | **13,758,836** | 419.89x |
| **Inkling 975B** | **BF16** | **PASS** | 2 节点 / 16 卡 | `TP8 × PP2` (Ray) | `rocm/vllm v0.29.0` · `AiterExperts` + `ROCM_ATTN` + `sconv` (`GDR_LEVEL=0`) | 65,536 | **109.52 / 116.12** | 112.54 / 118.90 | **51.02 / 57.39** | **398,239** | 6.08x |
| **Inkling 975B** | **Quark MXFP4** | **PASS** | **1 节点 / 8 卡** | `TP8` (减半硬件) | `vllm-openai-rocm:v0.33.0` · `AiterUnquantized` + `OCP_MXQuantizationEmulation` | 32,768 | **66.74** | 70.21 | **94.79** | **305,150** | 9.31x |

---

## 4. 性能探针实测对比（`max_tokens=256`，并发 `C=1` vs `C=8`）

| 模型与精度配置 | 节点 / 并行方式 | 并发度 $C$ | 首 Token 延迟 TTFT (ms) | 单流生成速度 Decode (tok/s) | 端到端耗时 E2E (s) | 系统聚合吞吐 Aggregate (tok/s) |
|---|---|---:|---:|---:|---:|---:|
| **Muse Spark Open 816B (BF16)** | 2 节点 16× MI300X (`TP8 × PP2`) | 1 | 205.0 | **84.6** | 3.22 | 79.5 |
| **Muse Spark Open 816B (BF16)** | 2 节点 16× MI300X (`TP8 × PP2`) | 8 | 506.0 | 47.6 | 5.88 | **348.6** |
| **Nemotron 3 Ultra 550B (BF16)** | 1 节点 8× MI300X (`TP8 + EP8`) | 1 | 170.0 | **60.7** | 4.37 | 58.6 |
| **Nemotron 3 Ultra 550B (BF16)** | 1 节点 8× MI300X (`TP8 + EP8`) | 8 | 358.0 | 42.0 | 6.45 | **317.4** |
| **Nemotron 3 Ultra 550B (MXFP4 Emulation)** | 1 节点 8× MI300X (`TP8 + EP8`) | 1 | 178.0 | 7.7 | 33.42 | 7.7 |
| **Nemotron 3 Ultra 550B (MXFP4 Emulation)** | 1 节点 8× MI300X (`TP8 + EP8`) | 8 | 484.0 | 6.9 | 37.30 | **54.9** |
| **Inkling 975B (BF16)** | 2 节点 16× MI300X (`TP8 × PP2`) | 1 | **45.0** | **68.9** | 3.75 | 68.3 |
| **Inkling 975B (BF16)** | 2 节点 16× MI300X (`TP8 × PP2`) | 8 | **97.0** | 42.5 | 6.10 | **335.8** |
| **Inkling 975B (Quark MXFP4 Emulation)** | 1 节点 8× MI300X (`TP8`) | 1 | 358.0 | 6.1 | 41.97 | 6.1 |
| **Inkling 975B (Quark MXFP4 Emulation)** | 1 节点 8× MI300X (`TP8`) | 8 | 726.0 | 5.7 | 45.92 | **44.6** |

---

## 5. 部署架构排障手册：三大模型在 MI300X 上的致命陷阱与修复方案

### 5.1 `Muse Spark Open (816B-A42B)`：规避 `gfx950` 专属 HIP 内核段错误

- **失败根因**：
  1. Attempt 1：使用 `muse-spark-open:latest` 官方镜像启动双机 Ray 时因缺少 `ray` 包失败。
  2. Attempt 2：补齐 `ray` 后，加载完权重在首次前向推理时触发 **`SIGSEGV` 段错误**。定位发现该镜像内置的融合算子 `fused_muse_spark_qknorm_rope_kv_insert_kernel.hip` 仅针对 `gfx950`（MI355X）编译，在 `gfx942`（MI300X）上直接非法指令崩溃。
  3. MXFP4 尝试：`--quantization online` 报 `MuseSpark1x on ROCm only supports Quark W8A8 FP8 or OCP-MXFP4 W4A4 quantized checkpoints`；改用 `--moe-backend auto` 后在 MI300X 上被路由至 `EMULATION`，触发断言 `MuseSpark1x MXFP4 on ROCm requires the AITER_MXFP4_MXFP4 backend; got EMULATION`。
- **生产验证启动命令（2 节点 16× MI300X，`vllm/vllm-openai-rocm:v0.33.0` + `ray==2.55.1`）**：
  ```bash
  export NCCL_NET_GDR_LEVEL=0
  export GLOO_SOCKET_IFNAME=eth0
  export NCCL_SOCKET_IFNAME=eth0
  vllm serve /models/Muse-Spark-Open-816B-A42B \
    --tensor-parallel-size 8 \
    --pipeline-parallel-size 2 \
    --distributed-executor-backend ray \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90
  ```

### 5.2 `NVIDIA Nemotron 3 Ultra (550B-A55B)`：非门控 `relu2` LatentMoE 与 Mamba 缓存修复

- **失败根因**：
  1. ROCm 默认开启的 `AITER` MoE 内核假定专家层为门控激活（SwiGLU / GeGLU），而 Nemotron 3 Ultra 的 `LatentMoE` 采用**非门控 `relu2` MLP**，直接调用会报错或数值异常。
  2. 若开启 `--enable-mamba-cache-stochastic-rounding`，Triton/LLVM 链接器在编译 `PHILOX_ROUNDS` 相关内联汇编时会抛出 `ld.lld: error: target emulation unknown`。
- **生产验证启动命令（1 节点 8× MI300X，BF16 与在线 MoE MXFP4）**：
  ```bash
  # BF16 高吞吐生产模式 (317.4 tok/s @ C=8)
  export VLLM_ROCM_USE_AITER_MOE=0
  vllm serve /models/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16 \
    --tensor-parallel-size 8 \
    --enable-expert-parallel \
    --mamba-ssm-cache-dtype float16 \
    --max-model-len 65536 \
    --gpu-memory-utilization 0.90

  # 在线 MoE OCP-MXFP4 超大 KV 模式 (43.21 GiB/GPU 权重, 111.86 GiB/GPU KV)
  export VLLM_ROCM_USE_AITER_MOE=0
  vllm serve /models/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16 \
    --tensor-parallel-size 8 \
    --enable-expert-parallel \
    --quantization online \
    --quantization-config '{"moe":"mxfp4"}' \
    --moe-backend emulation \
    --mamba-ssm-cache-dtype float16 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90
  ```

### 5.3 `Thinking Machines Lab Inkling (975B-A41B)`：双机 RCCL 死锁修复与 `sconv` 并行度约束

- **失败根因**：
  1. **TP16 约束报错**：尝试在 16 卡上运行 `--tensor-parallel-size 16` 立即抛出 `ValueError`——Inkling 包含 264 个短卷积（`sconv`）与滑动窗口注意力层，其 SWA Cache 分片强制要求 `tp_size <= num_kv_heads (8)`。
  2. **跨机 RCCL GDR 240 秒死锁**：默认 GPU Direct RDMA 设置下，16 卡跨机 `all_reduce` 在初始化阶段卡死 240 秒超时。显式设置 **`NCCL_NET_GDR_LEVEL=0`** 后，16 进程 `64 MiB` `all_reduce` 仅需 **`2.4 ms`（总线带宽 `52.4 GB/s`）**。
  3. **DP2 + EP16 远程协调器死锁**：尝试 `TP8 × DP2 + EP16` 时，首个请求通过，但第二个请求在远程 DP Coordinator RPC `sample_tokens` 处永久挂起；改用 **`TP8 × PP2`** 彻底解决。
- **生产验证启动命令（2 节点 BF16 与 1 节点 Quark MXFP4）**：
  ```bash
  # 2 节点 16× MI300X BF16 生产模式 (335.8 tok/s @ C=8, 45 ms TTFT)
  export NCCL_NET_GDR_LEVEL=0
  export GLOO_SOCKET_IFNAME=eth0
  export NCCL_SOCKET_IFNAME=eth0
  vllm serve /models/Inkling \
    --tensor-parallel-size 8 \
    --pipeline-parallel-size 2 \
    --distributed-executor-backend ray \
    --max-model-len 65536 \
    --gpu-memory-utilization 0.90

  # 1 节点 8× MI300X Quark MXFP4 单机收敛模式 (66.74 GiB/GPU 权重, 94.79 GiB/GPU KV)
  vllm serve /models/Inkling-MXFP4 \
    --tensor-parallel-size 8 \
    --moe-backend emulation \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90
  ```

---

## 6. NVFP4 单专家数值精度探针（1× MI300X）

为验证 NVIDIA ModelOpt `NVFP4` 权重在 MI300X 上的数值还原精度，在单张 MI300X 上使用 `Nvfp4QuantizationEmulationTritonExperts` 对齐 PyTorch 参考实现进行了单专家前向验证（合格阈值：相对 L2 误差 $\le 0.02$）：
- **`nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4`**：相对 L2 误差 **`0.0`**（完全一致）。
- **`lightseekorg/Inkling-NVFP4`**：相对 L2 误差 **`3.74e-9`**（远优于 `0.02` 阈值）。
- **工程注意**：全模型 NVFP4 权重体积高达 `320–592 GB`，在无硬件 FP4 加速器的节点上若执行全量离线反量化转换，需要 `>= 600 GB` 主机 CPU 内存以防 OOM；在 MI300X 上应优先使用 **Quark OCP-MXFP4 预量化权重** 或 **vLLM 在线 MoE MXFP4**。
