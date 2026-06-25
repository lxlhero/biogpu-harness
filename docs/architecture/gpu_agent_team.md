═══════════════════════════════════════════════════════════════════
  生信工具 GPU 加速 Agent Team — 使用手册与架构设计
═══════════════════════════════════════════════════════════════════

方法论源文件
  huron_skills/skills/claude/bioinformatics-tool-gpu-ification/references/  （方法论、benchmark 设计、失败模式）

运行时知识库（gpu-team 启动时强制读取）
  .claude/knowledge/methodology.md
  .claude/knowledge/pitfalls/common.md
  .claude/knowledge/pitfalls/docker_r_bioconductor.md
  .claude/knowledge/pitfalls/r_reticulate.md

本文档分两部分：
  第一部分  用户使用手册 — 如何启动、推进、审批任务
  第二部分  架构设计 — 状态机、配置、角色定义、失败路由


═══════════════════════════════════════════════════════════════════
  第一部分  用户使用手册
═══════════════════════════════════════════════════════════════════


═══ 一、快速开始 ═══

两条命令覆盖全部使用场景：

| 命令                                | 用途                                                        |
| ---                                 | ---                                                         |
| /gpu-team 工具名 A "用户要求"         | 从头开始 GPU 化（Step 1→8，新工具）                            |
| /gpu-team 工具名 B "用户需求"         | 已有项目的修复、优化、验证、benchmark 测试或文档更新             |

示例：

```bash
# 新工具全流程
/gpu-team susieR A "从头做 GPU 化，精度优先，最终需要飞书文档和速度报告"

# 修复精度问题
/gpu-team susieR B "Jaccard 只有 0.72，帮我修到 0.95 以上"

# 用额外 benchmark 做端到端验收
/gpu-team susieR B "已有 GPU 版本，帮我用另一个开源 benchmark 做端到端验收"

# 速度优化
/gpu-team scavenge B "速度只有 1.08x，分析瓶颈并继续优化"
```

B 模式内部子类型（orchestrator 根据用户描述自动判断）：

| 子类型                      | 适用场景                          |
| ---                         | ---                               |
| B.rerun_existing_image      | 用已有镜像重跑验证                 |
| B.fix_known_issue           | 定点修复已知精度/速度问题           |
| B.user_benchmark_validation | 额外 benchmark 验收（含开源数据）   |

自动推进（推荐）：

```bash
/loop 3m /gpu-team susieR A "从头做 GPU 化"
```

每 3 分钟自动检查 task_state.json 并推进。仅在 Human Approval Gate 和 Step 7.5 用户确认处停下，其余步骤全程无人值守。


═══ 二、角色一览 ═══

系统包含 17 个角色化执行单元，由单一 orchestrator 调度：

| Slash Command                 | 角色                   | 触发时机                                   |
| ---                           | ---                    | ---                                        |
| /gpu-team                     | orchestrator（主控）    | 用户发起任务，读 task_state 后路由            |
| /gpu-benchmark                | 数据扫描                | 任务启动时并行运行                           |
| /gpu-image-builder            | 镜像构建                | Step 2（L1） / Step 6（L2）                 |
| /gpu-profiling                | 热点分析 + 循环控制      | Step 3；驱动 Step 5 迭代                    |
| /gpu-feasibility              | GPU 可行性评估           | Step 4，由 profiling 调用                   |
| /gpu-code-planner             | 实现规格规划             | Step 4.5，feasibility 完成后、gpu-dev 前    |
| /gpu-dev                      | GPU kernel 开发         | Step 5，按 implementation_plan 实现 kernel  |
| /gpu-code-reviewer            | 代码审核                | Step 5，kernel 完成后、集群验证前             |
| /gpu-module-tester            | 模块精度验证             | Step 5，审核通过后提交集群                   |
| /gpu-e2e-tester               | 端到端测试              | Step 4（CPU baseline）/ Step 7（GPU 对比）   |
| /gpu-e2e-test-planner         | E2E 测试计划            | Step 4.0，CPU baseline 之前                 |
| /gpu-user-benchmark-planner   | 用户 benchmark 测试计划  | Step 7.5.2，用户 benchmark 执行之前          |
| /gpu-user-benchmark-tester    | 用户指定 benchmark 执行  | Step 7.5.4-7.5.6，按已批准 test plan 执行   |
| /gpu-problem-analyst          | 问题诊断                | 任意步骤出错时自动触发                       |
| /gpu-logging                  | 审计日志（异步）         | 全程运行                                   |
| /gpu-doc-writer               | 文档生成                | Step 8                                     |
| /gpu-rjob                     | 集群任务提交工具         | 各步骤按需调用（tools/rjob_submit.py）       |


═══ 三、任务推进机制 ═══

── 3.1 同步推进 ──

写代码、审核、分析等步骤不依赖外部资源，orchestrator 在一次调用内连续推进，无需停下：

```
orchestrator 读 task_state
    → 加载 gpu-dev 指令 → 写 kernel → 更新 next_action=review_kernel
    → 加载 gpu-code-reviewer 指令 → 审核 → 更新 next_action=submit_rjob
    → 调 tools/rjob_submit.py → 提交集群 → 更新 next_action=wait_for_rjob:xxx
    → 停下（异步等待）
```

── 3.2 异步等待 ──

docker build、rjob 执行等耗时步骤提交后停下，next_action 记录断点。恢复时从断点继续，不重跑已完成步骤。

── 3.3 幂等路径 ──

每次 rjob 结果写入唯一路径，历史证据永不覆盖：

```
runs/step5/get_sigcell_simple/attempt_1/rjob_abc123/result.json
runs/step5/get_sigcell_simple/attempt_2/rjob_def456/result.json
runs/step5/compute_prior/attempt_1/rjob_ghi789/result.json
```

── 3.4 断点恢复 ──

orchestrator 每次醒来重新读 task_state.json，不依赖任何上下文记忆。可从任意断点恢复执行。


═══ 四、Human Approval Gate（人工审批门）═══

以下操作前 orchestrator 自动停止，用户确认后继续：

| 操作                             | approval_reason 示例                              |
| ---                              | ---                                               |
| 建立 CPU E2E baseline            | First E2E baseline for susieR                     |
| 构建 / push L2 release 镜像      | L2 image ready for E2E validation                 |
| tag v1.0                         | All E2E checks passed, ready to release           |
| 覆盖已有 benchmark               | Replacing existing CPU baseline                   |
| 接受 speedup < 1.15×             | E2E speedup 1.08×, confirm acceptable             |
| 强制重跑与系统 E2E 重复的 benchmark | Benchmark duplicates system E2E benchmark        |
| 覆盖已有用户 benchmark baseline  | Replacing user benchmark CPU baseline             |
| 用户 benchmark 速度低于预期       | User benchmark speedup 1.08×, confirm acceptable  |
| 用户 benchmark 与系统 E2E 结果冲突 | User benchmark conflicts with system E2E result  |
| B 模式 execution_plan 用户确认   | execution_plan.md ready for review                |
| E2E 测试计划确认                 | e2e_test_plan.md ready for review                 |
| 用户 benchmark 测试计划确认      | user_benchmark_test_plan.md ready for review      |

进入 gate 时 task_state 状态：

```json
{
  "human_approval_required": true,
  "approval_reason": "First E2E baseline for susieR",
  "approved": false
}
```

用户将 approved 改为 true 后，重新调用 /gpu-team 继续。


═══ 五、工具工作区（用户视图）═══

每个工具的 GPU 化工区路径：transfer2gpu/工具名/

| 目录              | 内容                                             |
| ---               | ---                                              |
| state/            | task_state.json（进度一目了然）                    |
| runs/             | 每次 rjob 结果，按模块和尝试次数组织                 |
| reports/          | 热点分析、可行性评估、诊断报告、execution_plan.md     |
| baseline/         | CPU E2E 基准结果（不可覆盖）                        |
| user_benchmarks/  | 用户指定 benchmark 的 CPU/GPU 结果及精度速度报告     |
| src/              | GPU kernel 代码                                   |
| docker/           | 镜像构建产物                                      |


═══════════════════════════════════════════════════════════════════
  第二部分  架构设计
═══════════════════════════════════════════════════════════════════


═══ 六、设计原则 ═══

| 原则             | 说明                                                                                     |
| ---              | ---                                                                                      |
| 单主控执行        | 不创建多个 LLM 实例。orchestrator 读 task_state → 加载角色指令 → 执行。角色切换 = 加载不同指令集 |
| 状态机驱动        | 每步结果写入 artifact 文件，不依赖对话记忆。orchestrator 每次醒来独立读 task_state                   |
| 同步推、异步等     | 写代码/审核等本地步骤连续推进；rjob/docker 提交后停下，/loop 或 rjob 通知触发恢复                       |
| 幂等路径          | runs/步骤/模块/attempt_N/rjob_id/ 唯一标识每次尝试，历史证据不覆盖                                    |
| rjob 工具化        | 集群任务统一通过 tools/rjob_submit.py 提交，参数集中在 configs/rjob_config.yaml                         |
| 部署即交付物       | v1.0 必须支持 TOOL_DEVICE=gpu|cpu 环境变量切换                                                    |


═══ 七、task_state.json（核心状态机）═══

路径：transfer2gpu/工具名/state/task_state.json

── 7.1 字段说明 ──

| 字段                      | 类型    | 说明                                                        |
| ---                       | ---     | ---                                                         |
| task_id                   | string  | 全局唯一，格式 工具名_gpu_YYYYMMDD                           |
| tool_name                 | string  | 小写，与目录名一致                                           |
| mode                      | string  | A（全流程）/ B（已有项目修复/优化/验证）                       |
| workspace_path            | string  | 本地绝对路径                                                 |
| current_step              | string  | step2 ~ step8（含 step7_5）                                  |
| current_role              | string  | 当前角色                                                     |
| current_module            | string  | Step 5 正在处理的热点模块                                    |
| implementation_plan_path  | string  | Step 4.5 产出的规格文档路径（reports/implementation_plan_<module>.md）|
| planner_precision_risk    | string  | code-planner 评估的精度风险：low / medium / high             |
| next_action               | string  | 下次执行的动作（见路由表）                                    |
| attempt                   | int     | 当前模块已重试次数                                           |
| max_attempts_per_module   | int     | 单模块最大重试（默认 5）                                     |
| base_image                | string  | L1 base 镜像                                                |
| dev_image                 | string  | L2 开发版镜像                                               |
| release_image             | string  | v1.0 正式镜像                                               |
| benchmarks.profiling      | string  | profiling 数据路径                                          |
| benchmarks.e2e            | string  | E2E 数据路径                                                |
| last_result               | object  | 上次执行结果（含 failure_type）                               |
| human_approval_required   | bool    | 是否需人工审批                                               |
| approval_reason           | string  | 审批原因                                                    |
| approved                  | bool    | 是否已审批                                                  |
| user_benchmark            | object  | Step 7.5 用户指定 benchmark 状态（见下）                      |
| e2e_test_plan             | object  | E2E 测试计划状态（required/status/path/benchmark_name/approved 等）|
| execution_plan            | object  | B 模式执行计划状态（见下）                                    |

user_benchmark 字段：

| 子字段                       | 说明                                                                                  |
| ---                          | ---                                                                                   |
| enabled                      | 用户是否选择新增 benchmark                                                             |
| status                       | not_requested / requested / running_cpu / running_gpu / comparing / pass / fail / skipped |
| benchmark_id                 | 编号，如 benchmark_001                                                                |
| benchmark_name / path        | 名称与路径                                                                            |
| is_duplicate_with_system_e2e | 是否与系统 E2E benchmark 重复                                                          |
| *_result_path / *_report_path | 各阶段产物路径                                                                       |
| user_confirmed               | 用户是否确认结果可进入最终文档                                                         |

execution_plan 字段（B 模式专用）：

| 子字段       | 说明                                                                  |
| ---          | ---                                                                   |
| required     | B 模式下为 true                                                       |
| status       | not_started / drafted / approved / rejected / executing / completed   |
| path         | reports/execution_plan.md                                             |
| user_approved| 用户是否确认执行计划                                                   |

── 7.2 next_action 路由表 ──

| next_action                      | orchestrator 动作                           |
| ---                              | ---                                         |
| "write_kernel"                   | 加载 /gpu-dev                               |
| "plan_kernel"                    | 加载 /gpu-code-planner                      |
| "review_kernel"                  | 加载 /gpu-code-reviewer                     |
| "submit_rjob"                    | 调用 tools/rjob_submit.py                   |
| "wait_for_rjob:任务名"            | 查询 rjob 状态，完成则推进                    |
| "build_L2_image"                 | 加载 /gpu-image-builder                     |
| "plan_e2e_test"                  | 加载 /gpu-e2e-test-planner                  |
| "approve_e2e_test_plan"          | 进入 Human Approval Gate（E2E 测试计划确认）  |
| "run_e2e_baseline"               | 加载 /gpu-e2e-tester（Step 4 CPU baseline）  |
| "run_e2e_gpu"                    | 加载 /gpu-e2e-tester（Step 7 GPU E2E）       |
| "compare_e2e_result"             | 加载 /gpu-e2e-tester（Step 7 对比）          |
| "ask_user_benchmark"             | 展示系统 E2E 已用 benchmark，询问是否新增      |
| "plan_user_benchmark_test"       | 加载 /gpu-user-benchmark-planner             |
| "approve_user_benchmark_plan"    | 进入 Human Approval Gate（用户 benchmark 计划确认） |
| "run_user_benchmark_cpu"         | 跑用户 benchmark CPU baseline               |
| "run_user_benchmark_gpu"         | 跑用户 benchmark GPU 版本                   |
| "compare_user_benchmark"         | 计算精度和速度对比                           |
| "show_user_benchmark_result"     | 展示结果给用户                               |
| "wait_user_benchmark_confirmation" | 等待用户确认是否接受结果并进入 Step 8        |
| "skip_user_benchmark"            | 跳过 Step 7.5，进入 Step 8                  |
| "human_approval"                 | 停止，等待 approved=true                    |
| "start"                          | 根据 mode 进入对应入口                       |

── 7.3 完整示例 ──

```json
{
  "task_id": "susieR_gpu_20260622",
  "tool_name": "susieR",
  "mode": "A",
  "workspace_path": "/Users/huron/code/ai_lab/transfer2gpu/susieR/",
  "current_step": "step5",
  "current_role": "gpu_dev",
  "current_module": "get_sigcell_simple",
  "implementation_plan_path": "reports/implementation_plan_get_sigcell_simple.md",
  "planner_precision_risk": "medium",
  "next_action": "write_kernel",
  "attempt": 2,
  "base_image": "registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu/susieR-gpu:20260622-base",
  "last_result": {
    "status": "FAIL",
    "failure_type": "precision_mismatch"
  },
  "human_approval_required": false,
  "approval_reason": null,
  "approved": false,
  "e2e_test_plan": {
    "required": true,
    "status": "not_started",
    "path": "reports/e2e_test_plan.md",
    "benchmark_name": null,
    "benchmark_path": null,
    "benchmark_source": null,
    "input_manifest_path": null,
    "cpu_command": null,
    "gpu_command": null,
    "precision_metrics": [],
    "speed_metrics": [],
    "approved": false
  },
  "user_benchmark": {
    "enabled": false,
    "status": "not_requested",
    "benchmark_id": null,
    "benchmark_name": null,
    "benchmark_path": null,
    "is_duplicate_with_system_e2e": false,
    "test_plan": {
      "required": false,
      "status": "not_started",
      "path": null,
      "input_manifest_path": null,
      "approved": false
    },
    "cpu_result_path": null,
    "gpu_result_path": null,
    "compare_result_path": null,
    "precision_report_path": null,
    "speed_report_path": null,
    "summary_path": null,
    "user_confirmed": false
  },
  "execution_plan": {
    "required": false,
    "status": "not_started",
    "path": "reports/execution_plan.md",
    "user_approved": false
  }
}
```


═══ 八、配置文件（configs/）═══

── 8.1 rjob_config.yaml（集群参数）──

```yaml
namespace: ailab-ma4agismall
private_machine: group
charged_group: ma4agismall_gpu
gpu: 1
cpu: 8
memory: 60000
mount: gpfs://gpfs2/liangxiuliang-2:/mnt/...
ssh_host: huron-dev-1.liangxiuliang+root.ailab-ma4agismall.ws@h.pjlab.org.cn
starting_timeout_minutes: 30
max_starting_retries: 3
```

── 8.2 resource_budget.yaml（资源预算）──

```yaml
max_rjobs_total: 50
max_rjobs_per_module: 10
max_gpu_hours_total: 20
require_human_approval_after_gpu_hours: 10
```

── 8.3 image_config.yaml（镜像配置）──

```yaml
registry: registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu
date_base_suffix: "<YYYYMMDD>-base"
dev_tag_prefix: "v0."
release_tag: "v1.0"
```

── 8.4 precision_config.yaml（精度阈值）──

```yaml
pearson_r_continuous: 0.99
pearson_r_pvalue: 0.999
variance_ratio_range: [0.99, 1.01]
jaccard_deterministic: 0.95
jaccard_permutation_1000: 0.80
f1_binary: 0.95
```

所有精度判断统一从这个文件读取，不在代码中硬编码阈值。


═══ 九、精度标准 ═══

| 输出类型                              | 指标           | 阈值                      |
| ---                                   | ---            | ---                       |
| 连续评分（PIP / LD score / beta）      | Pearson r      | > 0.99                    |
| p 值                                  | Pearson r      | > 0.999                   |
| 方差参数（sigma² / h²）               | ratio          | ∈ (0.99, 1.01)            |
| 可信集 / 显著集合（确定性算法）          | Jaccard        | > 0.95                    |
| 可信集 / 显著集合（置换检验 ≥1000 perm） | Jaccard        | > 0.80                    |
| 二进制分类                              | F1             | > 0.95                    |

注：100 perm 仅用于调试，CPU-vs-CPU Jaccard ≈ 0.59，不用于精度判断。


═══ 十、工具脚本（tools/）═══

| 脚本                      | 职责                                   |
| ---                       | ---                                    |
| rjob_submit.py            | 提交 rjob，从 rjob_config.yaml 读参数    |
| rjob_status.py            | 查询 rjob 状态                         |
| rjob_collect_logs.py      | 收集 rjob 日志，写入 runs/ 目录          |
| log_event.py              | 写入 logs/events.jsonl 审计日志         |
| precision_check.py        | 读 precision_config.yaml，输出 PASS/FAIL |


═══ 十一、审计日志（logs/events.jsonl）═══

每次角色执行后自动写入一条记录：

```json
{
  "decision_id": "susieR_gpu_20260622/step5/gpu_dev/001",
  "timestamp":   "2026-06-22T14:30:00+08:00",
  "role":        "gpu_dev",
  "step":        "step5",
  "module":      "get_sigcell_simple",
  "event_type":  "action",
  "summary":     "修改 gamma 方向 (1-gamma)*W + gamma*P0",
  "result":      {"jaccard": 0.82, "speedup": 46.4}
}
```

event_type 枚举：

| 值          | 含义             |
| ---         | ---              |
| action      | 角色执行的操作     |
| result      | 操作结果          |
| error       | 执行错误          |
| escalation  | 问题升级          |

decision_id 格式：任务ID/步骤/角色/序号:03d


═══ 十二、角色详细定义 ═══

── 12.1 总览 ──

| 角色                      | 输入                                    | 输出                                          | 约束                      |
| ---                       | ---                                     | ---                                           | ---                       |
| orchestrator              | task_state.json                         | 更新 task_state，路由到下一角色                 | 唯一执行主体               |
| benchmark                 | 用户数据路径                              | benchmarks/ 目录 + 分析报告                    | 与 E2E 数据独立            |
| profiling                 | benchmark + 工具代码                     | profiling_report.md + Amdahl 判断              | 过滤 E2E 占比 <10% 的模块  |
| feasibility               | 热点模块代码列表                           | feasibility_report.md（结构化表格）             | 纯分析，不写代码            |
| code-planner              | feasibility_report + CPU 源码            | implementation_plan_<module>.md               | 不写可运行代码，不做 Yes/No 判断 |
| gpu-dev                   | task_state + precision_config + implementation_plan | src/模块_gpu.py + 同步到 GPFS    | 不提交 rjob、不构建镜像；必须按 implementation_plan 实现 |
| code-reviewer             | kernel 文件 + pitfalls/                  | P0-P4 审核结论（PASS/FAIL）                    | 本地静态检查，不进集群       |
| module-tester             | kernel + precision_config + benchmark   | runs/step5/.../result.json                    | 用 L1 base + GPFS mount   |
| e2e-tester                | L1/L2 镜像 + E2E benchmark              | baseline/（Step 4）/ 精度速度对比（Step 7）     | 触发 Human Approval Gate  |
| user-benchmark-tester     | 用户指定 benchmark + 系统 E2E 结果        | user_benchmarks/benchmark_001/ 精度速度报告    | Step 7.5，可选；先展示已用 benchmark |
| image-builder             | task_state + image_config               | L1/L2 镜像，tag + push                        | L1 smoke test / L2 双模式  |
| problem-analyst           | failure_type + events.jsonl             | reports/last_failure.json                     | 只诊断，不写代码            |
| logging                   | 各角色执行事件                             | logs/events.jsonl                            | fire-and-forget 异步       |
| doc-writer                | reports/ + baseline/ + user_benchmarks/ | 飞书格式文档（四章节）                          | Step 8 触发               |

── 12.2 orchestrator（/gpu-team）──

执行流程：

```text
1. 读 task_state.json
2. 若 human_approval_required=true 且 approved=false → 停止，告知用户
3. 根据 next_action 加载对应角色指令
4. 角色执行完毕 → 更新 task_state → 调用 log_event.py
5. 决定下一个 next_action，循环或停下
```

── 12.3 benchmark（/gpu-benchmark）──

```text
1. 逐个扫描数据路径，判断格式兼容性
2. 多路径互补判断（能否合并成完整工具输入）
3. 输出分析报告，写入 benchmarks/
4. 更新 task_state.benchmarks

profiling 与 E2E 数据必须独立。仅有一份数据时 8:2 划分，报告中注明。
```

── 12.4 profiling（/gpu-profiling）──

```text
Phase 1  编写 profiling 脚本 → rjob 提交集群 → 整理热点模块
         过滤 E2E 占比 < 10% 的模块

Phase 2  调用 /gpu-feasibility 评估各模块
         E2E_speedup = 1 / ((1-P) + P/S)
         < 1.15× → 终止；≥ 1.15× → 继续

Phase 3  维护模块队列，驱动 gpu-dev → code-reviewer → module-tester 循环
```

── 12.5 gpu-feasibility（/gpu-feasibility）──

输出格式（写入 reports/feasibility_report.md）：

| 模块名             | 计算特征               | GPU 化方案     | 预估加速   | 精度风险                    | 推荐 |
| ---                | ---                    | ---            | ---        | ---                         | ---  |
| get_sigcell_simple | sparse.mv + index_select | CSR matmul   | 40-50×     | Jaccard 可能因浮点顺序下降    | P0   |

── 12.6 gpu-code-planner（/gpu-code-planner）──

```text
输入  feasibility_report.md（高层 GPU 策略）
      热点模块完整 CPU 源码
      precision_config.yaml

执行  1. 逐行阅读 CPU 源码，识别所有影响数值输出的操作
      2. 产出数值路径映射表（CPU 操作 → GPU API，标注精度风险）
      3. 审计所有默认参数和隐式 CPU 行为（如 standardize、dtype casting）
      4. 设计 R↔Python 桥接接口（如适用）
      5. 输出 API 级实现骨架（pseudocode，含 CPU/GPU 切换位置）
      6. 评估 precision_risk（low / medium / high）

完成  更新 next_action=write_kernel
      若 precision_risk=high → Human Approval Gate

产物  reports/implementation_plan_<module>.md
      task_state.implementation_plan_path
      task_state.planner_precision_risk

禁止  写可运行代码、做 Yes/No 可行性判断、提交 rjob
```

── 12.7 gpu-dev（/gpu-dev）──

```text
输入  task_state（current_module / attempt / last_result）
      precision_config.yaml
      implementation_plan_<module>.md（必须先读取，规格来源）
      feasibility_report.md（背景参考）

执行  按 implementation_plan 规格编写 GPU kernel → src/模块名_gpu.py
      同步到 GPFS（调试期不重建镜像）
      如发现规格有误，先更新 implementation_plan 再实现

完成  更新 next_action=review_kernel

禁止  提交 rjob、构建镜像、修改 CPU baseline
      自行改变数值路径或 API 选择（须先修改 plan）
```

── 12.8 code-reviewer（/gpu-code-reviewer）──

审核分级：

| 级别 | 检查项                         | 方式                        |
| ---  | ---                            | ---                         |
| P0   | 语法正确                        | ast.parse()                 |
| P1   | 数值路径与 CPU 原版一致          | 参考 .claude/knowledge/pitfalls/common.md   |
| P2   | GPU 常见陷阱（diagonal / squeeze / sparse.mv） | 静态规则匹配    |
| P3   | TOOL_DEVICE 环境变量切换实现     | 代码检查                     |
| P4   | 性能建议                        | 非阻塞，仅供参考              |

PASS → 更新 next_action=submit_rjob
FAIL → 更新 next_action=write_kernel（打回 gpu-dev）

── 12.9 module-tester（/gpu-module-tester）──

```text
方式  L1 base 镜像 + GPFS mount kernel（不重建镜像）
      调用 tools/rjob_submit.py 提交集群

判断  读 precision_config.yaml，不手动写阈值

输出  runs/step5/模块名/attempt_N/rjob_id/result.json

PASS  → 通知 profiling 取下一模块
FAIL  → 更新 last_result.failure_type → orchestrator 路由修复
```

── 12.10 e2e-tester（/gpu-e2e-tester）──

| 阶段    | 操作                                      | Gate              |
| ---     | ---                                       | ---               |
| Step 4  | L1 镜像跑原版工具 → baseline/cpu_e2e_result/ | Human Approval    |
| Step 7  | L2 镜像 TOOL_DEVICE 切换，与 baseline 对比     | Human Approval    |

── 12.10b e2e-test-planner（/gpu-e2e-test-planner）──

在 Step 4 CPU baseline 前触发。只负责规划，不执行。
读取 benchmarks/e2e/ + profiling_report + feasibility_report + precision_config。
输出 reports/e2e_test_plan.md（含 benchmark 信息、CPU/GPU 命令、精度指标、输出路径）
和 benchmarks/e2e/input_manifest.yaml。
更新 next_action=approve_e2e_test_plan。
禁止：提交 rjob、运行测试、修改源码、修改精度阈值、覆盖 baseline。

── 12.10c user-benchmark-planner（/gpu-user-benchmark-planner）──

在 Step 7.5.2 触发。只负责规划，不执行。
必须先展示系统 E2E 已用 benchmark 信息，再判断用户 benchmark 是否重复。
重复时进入 Human Approval Gate。
输出 user_benchmarks/benchmark_001/user_benchmark_test_plan.md 和 input_manifest.yaml。
更新 next_action=approve_user_benchmark_plan。
禁止：运行 CPU/GPU benchmark、提交 rjob、静默替换用户 benchmark、跳过重复检查。

── 12.11 image-builder（/gpu-image-builder）──

| 阶段 | 镜像内容                                  | 验证            |
| ---  | ---                                       | ---             |
| L1   | 原工具 + CUDA/PyTorch 依赖                 | smoke test      |
| L2   | COPY 已验证 kernel（不 runtime patch）     | 两种 DEVICE smoke |
| v1.0 | L2 正式 tag                                | Human Approval  |

── 12.12 problem-analyst（/gpu-problem-analyst）──

```text
触发  任意角色失败 → orchestrator 自动路由

输入  last_result.failure_type + logs/events.jsonl（决策链）

流程  1. 查 .claude/knowledge/pitfalls/ 匹配历史踩坑（common.md、r_reticulate.md、docker_r_bioconductor.md）
            同时检查 $WORKSPACE/pitfalls/<tool>.md（工具专属踩坑）
      2. 输出：根因 + 证据 + 修复建议 + 分配给哪个角色
      3. 写入 reports/last_failure.json

禁止  写代码、提交 rjob、修改配置
```

── 12.13 logging（/gpu-logging）──

全程异步运行，fire-and-forget，不阻塞主流程。

── 12.14 doc-writer（/gpu-doc-writer）──

Step 8 触发，从 reports/、baseline/ 和 user_benchmarks/ 收集数据，生成飞书格式成功交付报告。
可选输入 reports/e2e_test_plan.md（精度指标来源参考）。

报告聚焦四个核心章节：
  一、工具说明 — 工具名称、版本、用途、GPU 化适用场景
  二、使用方式 — 镜像地址、环境要求、CPU/GPU 切换命令、最小示例
  三、热点改造说明 — 改造前瓶颈（占 E2E %）、改造方案（一句话）、模块级加速表
  四、Benchmark 说明及端到端测试精度与速度 — 系统 E2E 精度表+速度表；用户指定 benchmark（如有）

其他内容（Amdahl 推算过程、失败历史、模块内部实现细节）不写入报告正文。


═══ 十三、失败路由表 ═══

| failure_type                      | 路由                                                         |
| ---                               | ---                                                          |
| syntax_error                      | gpu-dev（本地修复，不进集群）                                  |
| precision_mismatch                | gpu-dev；连续 2 次同类 → problem-analyst                       |
| plan_precision_risk_high          | Step 4.5：planner 发现高精度风险 → Human Approval Gate → 批准后继续 gpu-dev |
| gpu_runtime_error                 | problem-analyst → gpu-dev                                    |
| rjob_starting_timeout             | 重提 rjob，不计入模块 retry                                    |
| oom                               | module-tester 调整资源后重跑                                   |
| image_build_failed                | image-builder                                                |
| benchmark_invalid                 | benchmark                                                    |
| speed_regression                  | 检查 Amdahl，必要时回 Step 3                                   |
| E2E speedup < 1.15×               | Human Approval Gate → 用户决定接受或终止                       |
| user_benchmark_duplicate          | Step 7.5：/gpu-user-benchmark-planner → Human Approval Gate |
| user_benchmark_invalid            | Step 7.5：生成 input spec，要求用户补充信息                     |
| user_benchmark_cpu_failed         | Step 7.5：诊断 benchmark 本身问题，不回 Step 5                  |
| user_benchmark_gpu_runtime_error  | Step 7.5：problem-analyst → Step 5                           |
| user_benchmark_precision_mismatch | Step 7.5：problem-analyst → Step 5                           |
| user_benchmark_speed_regression   | Step 7.5：热点变化→ Step 3，实现问题→ Step 5                   |
| user_benchmark_result_conflict    | Step 7.5：problem-analyst 生成冲突分析 → Human Approval Gate   |
| e2e_test_plan_missing             | /gpu-e2e-test-planner                                        |
| e2e_test_plan_not_approved        | Human Approval Gate                                          |
| e2e_benchmark_incomplete          | /gpu-e2e-test-planner                                        |
| user_benchmark_test_plan_missing  | /gpu-user-benchmark-planner                                  |
| user_benchmark_test_plan_not_approved | Human Approval Gate                                      |
| user_benchmark_incomplete         | /gpu-user-benchmark-planner                                  |
| user_benchmark_metric_mismatch    | /gpu-user-benchmark-planner                                  |
| user_benchmark_gpu_precision_fail | Step 7.5：problem-analyst → Step 5                           |
| user_benchmark_gpu_runtime_fail   | Step 7.5：problem-analyst → Step 5                           |


═══ 十四、完整流程 ═══

── 14.1 模式 A（全流程 GPU 化）──

```text
Step 1 ─ orchestrator  初始化 task_state，并行启动 benchmark + logging
         benchmark      扫描/准备数据，写入 benchmarks/

Step 2 ─ image-builder  构建 L1 镜像（原工具 + CUDA/PyTorch），smoke test

Step 3 ─ profiling      集群 profiling → 热点分析 → Amdahl 判断
         feasibility    评估各模块 GPU 化方案，输出结构化表格

Step 4.0 ─ e2e-test-planner
           生成 reports/e2e_test_plan.md（benchmark/命令/指标/输出路径全部写明）
Step 4.1 ─ ⚠ Human Approval Gate（E2E 测试计划确认）
Step 4.2 ─ e2e-tester     按 e2e_test_plan.md 跑 CPU baseline → baseline/cpu_e2e_result/
           ⚠ Human Approval Gate（首次建立 baseline）

Step 4.5 ─ code-planner（每个候选模块逐一执行）
           读 CPU 源码 → 数值路径映射表 → 默认参数审计 → 实现骨架
           → 输出 reports/implementation_plan_<module>.md
           precision_risk=high → ⚠ Human Approval Gate

Step 5 ─ 循环（profiling 控制）
           gpu-dev        按 implementation_plan 实现 kernel（GPFS 调试）
           code-reviewer  本地静态检查（P0-P4）
           module-tester  集群精度+速度验证（L1 base + GPFS mount）
           → PASS 取下一模块
           → FAIL 打回 gpu-dev
           → 超 retry 上限 → problem-analyst

Step 6 ─ image-builder  内化已验证 kernel 到 L2 镜像
         ⚠ Human Approval Gate（push L2 镜像）

Step 7 ─ e2e-tester     GPU E2E 对比（L2 + TOOL_DEVICE 切换）
         → PASS + speedup ≥ 1.15× → 进入 Step 7.5
         → FAIL → 回 Step 5
         ⚠ Human Approval Gate（tag v1.0）

Step 7.5 ─ 用户指定 benchmark 验收（可选）
           Step 7.5.0: orchestrator 展示系统 E2E 已用 benchmark 摘要
           Step 7.5.1: orchestrator 询问用户是否提供不同 benchmark；否 → Step 8
           Step 7.5.2: user-benchmark-planner 重复检查 + 完整性检查 + 生成 test plan
           Step 7.5.3: ⚠ Human Approval Gate（用户 benchmark 测试计划确认）
           Step 7.5.4-6: user-benchmark-tester 按 test plan 跑 CPU baseline + GPU + 对比
           Step 7.5.7: orchestrator 展示结果，等待用户确认是否纳入最终报告

Step 8 ─ doc-writer     生成飞书文档（四章节：工具说明/使用方式/热点改造/benchmark精度速度）
```

── 14.2 模式 B（已有项目修复/优化/验证）──

```text
Step B0 ─ orchestrator
          读取已有项目状态：task_state.json / runs / reports / baseline / logs

Step B1 ─ orchestrator
          生成 execution_plan.md（目标/参与角色/step 流转/预计产物/风险/回滚）

Step B2 ─ Human Approval Gate
          ⚠ 用户审核 execution_plan.md，确认后才继续

Step B3 ─ 按 execution_plan 执行
          按需进入 problem-analyst / gpu-dev / code-reviewer /
          module-tester / e2e-tester / user-benchmark-tester /
          image-builder / doc-writer

Step B4 ─ doc-writer（按需）
          更新飞书文档 / 修复报告 / benchmark 验收报告
```

**B 模式铁律：禁止直接修改代码、提交 rjob、构建镜像，必须先生成 execution_plan.md 经用户确认。**


═══ 十五、Step 5 开发循环时序 ═══

```text
orchestrator 读 task_state: current_role=code_planner, next_action=plan_kernel
    │
    ▼  同一次调用内连续推进
加载 gpu-code-planner → 产出 implementation_plan_<module>.md → next_action=write_kernel
    │  （若 precision_risk=high → Human Approval Gate → 等待用户确认）
    ▼
加载 gpu-dev → 按 implementation_plan 实现 kernel → next_action=review_kernel
    │
    ▼
加载 gpu-code-reviewer → P0-P4 审核 → PASS → next_action=submit_rjob
    │
    ▼
调用 tools/rjob_submit.py → 提交集群 → next_action=wait_for_rjob:xxx
    │
    ▼  停下（异步等待集群完成）
    ╳
   ── /loop 触发 或 rjob 完成通知 ──
    │
    ▼  恢复执行
读 task_state: next_action=wait_for_rjob → 查状态 → Succeeded
    │
    ▼
读 runs/step5/模块名/attempt_N/rjob_id/result.json → 精度 PASS
    │
    ▼
更新 current_step=step6, next_action=build_L2_image
    │
    ▼
加载 gpu-image-builder → 进入 Step 6
```


═══ 十六、铁律 ═══

| 编号 | 铁律                                                                   |
| ---  | ---                                                                    |
| 1    | 精度优先 — 先对齐精度，再提升速度                                         |
| 2    | 真实数据 — E2E 必须用真实生物数据，smoke test 才允许合成数据                |
| 3    | benchmark 独立 — E2E 与 profiling 数据集独立                              |
| 4    | bash 内联 — 所有 rjob 一律 bash 内联，参数从 rjob_config.yaml 读            |
| 5    | 不重建镜像 — 调试期用 L1 base + GPFS mount，通过后内化进 L2                |
| 6    | 15% 门槛 — Amdahl 预期 E2E speedup < 1.15× 时终止                        |
| 7    | 幂等路径 — runs/步骤/模块/attempt_N/ 禁止覆盖                             |
| 8    | 切换是交付物 — v1.0 必须支持 TOOL_DEVICE=gpu｜cpu                         |
| 9    | B 模式先出计划 — B 模式禁止直接改代码/提交 rjob/构建镜像，必须先生成 execution_plan.md 经用户确认 |
| 10   | 用户 benchmark 不等于私有 — 可以是开源/公开/第三方 benchmark，但必须与系统 E2E 已用 benchmark 不重复 |
| 11   | Step 7.5 必须先展示已用 benchmark — 询问用户前必须展示系统 E2E 已用 benchmark 名称/路径/规模/结果，防止重复提供 |
| 12   | 知识沉淀 — 任意模块修复循环完成（修复验证通过）后，orchestrator 将未记录的根因写入对应 pitfall 文件；工具专属写 $WORKSPACE/pitfalls/<tool>.md，跨工具通用写 .claude/knowledge/pitfalls/common.md；禁止使用编号，使用描述性标题 |
| 13   | 测试计划与执行分离 — 所有 E2E 和用户 benchmark 测试必须先由 planner 产出 test_plan 并通过 Human Approval Gate，tester 才能执行 |
| 14   | 系统 E2E 复用同一测试计划 — Step 4 CPU baseline 与 Step 7 GPU E2E 必须使用同一份 e2e_test_plan.md |
| 15   | 用户 benchmark 先规划后执行 — Step 7.5 必须先经 user-benchmark-planner 完整性检查、重复检查和 test_plan 生成，未批准前不允许执行 |


═══ 十七、工作区完整目录结构 ═══

```text
transfer2gpu/工具名/
  state/
    task_state.json              orchestrator 状态机（唯一真相来源）
    precision_config.yaml        精度阈值（工具特定）
  configs/
    rjob_config.yaml             集群参数（统一配置，不手写）
    resource_budget.yaml         GPU 小时数、rjob 次数上限
    image_config.yaml            registry 前缀、base image
  benchmarks/
    profiling/                   profiling 数据集
    e2e/                         E2E 数据集
  runs/
    step5_module_tests/
      模块名/attempt_N/rjob_id/
        stdout.log               集群标准输出
        result.json              PASS/FAIL + 精度值 + 耗时
  reports/
    profiling_report.md          热点分析与 Amdahl 判断
    feasibility_report.md        模块 GPU 化可行性评估
    implementation_plan_<module>.md  Step 4.5 规格文档（数值路径映射、实现骨架）
    failure_report.md            诊断报告
    execution_plan.md            B 模式执行计划（用户确认后才允许执行）
    final_report.md              Step 8 飞书文档
  baseline/
    cpu_e2e_result/              CPU 基准结果（不可覆盖）
  user_benchmarks/
    benchmark_001/
      input_manifest.yaml        用户提供的 benchmark 信息
      cpu_result/                CPU 运行结果
      gpu_result/                GPU 运行结果
      compare_result.json        精度对比
      speed_report.md            速度报告
      precision_report.md        精度报告
      summary.md                 Step 8 doc-writer 汇总使用
  logs/
    events.jsonl                 全程审计日志
  src/
    工具名_gpu.py                GPU kernel（调试期同步到 GPFS）
  docker/
    Dockerfile
```


═══ 十八、参考资料 ═══

| 资源                      | 路径                                                                         |
| ---                       | ---                                                                          |
| 方法论（benchmark 设计、失败模式、精度策略） | huron_skills/skills/claude/bioinformatics-tool-gpu-ification/references/ |
| 运行时踩坑（gpu-team 启动时读取） | .claude/knowledge/pitfalls/                                           |
| 工作区约束（自动加载）      | transfer2gpu/CLAUDE.md                                                       |
| susieR 案例                | transfer2gpu/susieR/report/CLAUDE_HANDOFF.md                                  |
| scavenge 案例              | transfer2gpu/scavenge/report/CLAUDE_HANDOFF.md                                |
