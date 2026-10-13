# Azure profile：模板与执行门禁

首期面向原创合成样例，不是生产多租户服务。Bicep 本地编译不调用模型、不部署资源；
已验证语法不代表账户 quota、容量、权限、网络或模型参数已验证。

## 架构

Linux VM 运行 Docker/Harbor controller，**不绑定 managed identity**；任务不挂 host home、
Docker socket 或云管理凭证。独立 Container Apps broker 持其自己的 identity，
只调用指定 Azure OpenAI deployment，并访问独立 ledger 容器；原始 artifacts 是另一个
私有容器。worker 不拿 storage key，上传使用受信 operator 颁发的短期、受限授权。

Storage 关闭匿名与 Shared Key，启用 HTTPS/TLS1.2。这里的“私有”指非公开 container，
**不是 private endpoint**。仅合成数据允许认证的公网 endpoint；客户/机密数据须另建
private-connectivity profile。user-delegation SAS 不因关闭 Shared Key 而被禁用。

VM NSG 拒绝所有入站，不默认开放 SSH。必须提供已有显式 egress；可选 Standard NIC
public IP 默认关闭，只有另行批准后启用。其非公开管理行为来自 NSG，不是 IP 自身保证。
不依赖 Azure 新 VNet 的默认 outbound。HTTPS egress 也不替代 task sandbox。

broker 单 replica/scale-to-zero、LRS、不默认 Log Analytics/Key Vault/HA 是实验成本与范围
取舍，不是生产可靠性承诺。ledger 和完整 Run Command 日志是必需的持久证据；
TTL tag 不会自动 deallocate VM，必须有独立可信生命周期 watchdog。

## 准备与验证

```powershell
az bicep build --file infra\main.bicep
uv run --frozen --extra azure python -m benchmark_harness.azure preflight --profile environments\azure\profile.example.json
```

示例 profile 刻意留空并默认拒绝 live，第二条会返回 `blocked`，不是配置自动补全。
将批准绑定保存到自己的 `*.local.json`，避免提交 subscription、资源身份和私人路径。
价表用明确 USD、有效日期、来源和 decimal 值；无法确认的成本不能填零。

选定 subscription/region/SKU/image/deployment/version/API/输出硬限额、预算、expires、
egress、owner 与 watchdog 后运行：

```powershell
.\scripts\azure-preflight.ps1 -Profile .azure\run.local.json -LiveChecks
```

该 opt-in 路径只读 account/provider/SKU/区域与 family quota/deployment 信息，不注册
provider、不授角色、不部署、不调用推理。quota 足够不保证实际容量；有效 inference RBAC、
连通性、TPM/RPM、模型限制和 what-if 仍须在选定账户分别确认。

复制 `infra\main.bicepparam.example`，通过环境变量/安全参数输入。不要把签名 secret 写入
文件、命令 trace 或 task 环境。新模型 role assignment 默认关闭；现有 inference
deployment 不被本模板创建或删除。经过 `azure-validate` 和独立授权后才执行 apply。

## 调度与取消

使用 Managed Run Command，不依赖公网 SSH。Guest Agent 至少 2.4.0.2。
检查脚本 `ExecutionState`/`ExitCode`，不能只看 ARM `ProvisioningState`。
InstanceView 只有最后 4 KB stdout/stderr；每个 attempt 使用新 append-blob 日志与
单独 hashed bundle。受信 operator 负责限时、取消和 owned compute deallocation，
同时保留 partial/uncertain 用量；取消不是自动退款。

`azure-bootstrap.ps1` 强制提供不同的 `-OutputBlobUri`/`-ErrorBlobUri`，必须指向本
storage 的 artifacts container 下 `<run_id>/<attempt_id>/`，由 operator 私下提供
短期 append-blob 授权；不能传 ledger 授权。已存在的 attempt command 禁止重放。
脚本仅打印终态、退出码和时间，不打印完整含 script/SAS 的 Run Command 对象。
这些 SAS URI 与完整服务诊断应保留私有，不进入公开报告。完整日志和 bundle 的
实际输送仍须在获批环境验证，语法检查不能替代它。

可信 broker 的配置、预算状态与关闭/封存流程见 [broker 文档](broker.md)。输入预留使用
已核验的 deployment 整个计费 context-window 上界，不能用希望的短 prompt 长度代替。

原生 Copilot BYOK、broker 协议、Docker 内的 credential/metadata 隔离尚未 live 验证，
不能因为存在模板就宣布 cloud agent 跑通。

## 证据出口与清理

先关闭 run 的后续 dispatch、等待没有 in-flight 请求后封存 ledger、归档已完成/未确定 attempts，使用 operator 的 Entra
身份导出本 run 的完整 artifacts 和 ledger。可信 inventory 由完整对象列表与冻结 manifest
形成，不能接受 task 自己声明“只导出了这些”。inventory 示例结构：

```json
{"run_id":"synthetic-example","resource_group":"example-rg","dispatch_closed":true,"ledger_sealed":true,"in_flight":0,"files":[
  {"path":"ledger.json","kind":"ledger","sha256":"<actual sha256>"},
  {"path":"manifest.json","kind":"manifest","sha256":"<actual sha256>"},
  {"path":"settings.json","kind":"accounting","sha256":"<actual sha256>"},
  {"path":"attempt-1.json","kind":"artifact","sha256":"<actual sha256>"},
  {"path":"attempt-1/stdout.log","kind":"log","sha256":"<actual sha256>"},
  {"path":"attempt-1/stderr.log","kind":"log","sha256":"<actual sha256>"}
]}
```

在实验资源组之外的私有目的地核验完整 inventory：

```powershell
uv run --frozen --extra azure python -m benchmark_harness.azure export-proof --inventory C:\private-export\inventory.json --export-root C:\private-export\bundle --receipt C:\private-export\receipt.json
.\scripts\azure-cleanup.ps1 -Profile .azure\run.local.json -ResourceInventory C:\private-export\resources.json -ExportReceipt C:\private-export\receipt.json
```

cleanup 默认只预览，不删除资源。receipt 绑定 run/资源组、inventory hash 和每个文件 hash；
缺 ledger、导出中断、路径逃逸、证据改写、混入其他 run 的资源都拒绝。无法删除时明确
残留 owner/保留期限和继续计费，不声称 cleanup 成功。实际删除必须再次核对 live
资源与显式 destructive-action approval；绝不先删整个组再找证据。

本地 receipt 只证明所列文件与实际封存 ledger/计费配置一致，**不单独证明云端全量导出**。
需要保存冻结 experiment manifest、完整 settings/价表和全部 attempt/log，而非 ledger-only
清单；实际 ledger 必须 closed/sealed 且没有 reserved/dispatched 条目。

授权删除还要求 profile 的 `destructive_cleanup=true` 和脚本 `-ApprovedDelete`。
执行端再次读取 live group/资源 tags；未标记的自动生成子资源或其他工作负载会阻塞，
需 operator 核实完整 owned-resource 清单，不能批量强行补标签。只有本 run 独占的组才
请求删除；异步请求返回不代表删除完成。既有模型资源组内的 inference role 不随实验组
删除，若曾授权创建，应另行审核清理，不能把模型部署当作 owned 实验资源。

删除端还须核验 worker 已 deallocated、broker revisions 已 inactive，重新使用 operator
Entra 身份读取本次 owned storage 的全部 artifacts 与 ledger，拒绝其他 run 的 prefix。ETag 条件读取拒绝
中途变化，source/export **精确文件集合与每文件 hash 必须一致**；其他 ledger/额外
container、漏掉的 attempt 或日志、错误 source account 都阻塞。profile 的 `evidence`
绑定受信控制端的 `frozen_manifest_sha256`、`required_paths` 与
`trusted_producers_quiesced`，这些不是 task 自报字段。artifact blobs 采用
`<run_id>/<export-relative-path>`，ledger 独立为 `<run_id>.json` 并导出为 `ledger.json`。
如果完整输送、停止 producer、读权限或 source 检查未通过，保留存储并明确残余费用，
不能用本地 receipt 单独授权删除。这条 SDK/ARM live 路径仍未在真实 Azure 执行验证。

## 官方依据

- [Container Apps WAF](https://learn.microsoft.com/azure/well-architected/service-guides/azure-container-apps)
- [VM WAF](https://learn.microsoft.com/azure/well-architected/service-guides/virtual-machines)
- [Blob WAF](https://learn.microsoft.com/azure/well-architected/service-guides/azure-blob-storage)
- [显式 outbound](https://learn.microsoft.com/azure/virtual-network/ip-services/default-outbound-access)
- [Managed Run Command](https://learn.microsoft.com/azure/virtual-machines/linux/run-command-managed)
- [Shared Key 与 user-delegation SAS](https://learn.microsoft.com/azure/storage/common/shared-key-authorization-prevent)
- [VM 身份安全边界](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/managed-identities-faq#limitations)
