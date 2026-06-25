---
description: BioGPU-Harness 项目初始化向导 — 逐步询问用户并生成 biogpu_project.yaml 和工作区目录结构
---

# /bio-gpu-project-init — 项目初始化向导

> 本命令由 `/bio-gpu-team` 在检测到无项目配置时调用，或用户直接调用。
> 它像配置向导一样逐步询问用户，然后创建标准工作区结构。

## 询问顺序

逐步询问以下问题（每步等待用户回答再继续）：

```
1. 需要 GPU 加速的生信工具叫什么名称？

2. 这是从头开始，还是继续优化/修复已有项目？
   A = 从头开始 GPU 加速
   B = 优化/修复已有 GPU 加速项目

3. 生信工具源码在哪里？（请提供完整路径）

4. 工具工作区放在哪里？
   默认：/Users/huron/code/ai_lab/transfer2gpu/<tool_name>

5. 当前用户需求是什么？（可多选）
   - 端到端加速
   - 修复精度问题
   - 修复速度不达标
   - 修复 Docker/rjob
   - 继续做下一个模块
   - 重新跑 benchmark
   - 生成最终报告

6. 是否已有 benchmark 数据？（有/无，如有请提供路径）

7. 是否已有 CPU baseline 结果？（有/无）

8. 是否已有 GPU 实现？（有/无）

9. 精度要求是什么？（默认：accuracy_first）

10. E2E 加速目标是多少倍？（默认：1.15）

11. 是否使用集群 / rjob / Docker？（是/否）
```

## 确认前展示

收集完所有信息后，展示确认摘要：

```
即将创建 BioGPU project：

tool_name:        <值>
mode:             A / B
bio_tool_path:    <值>
workspace_path:   <值>
benchmark_source: harness_selected / user_provided
precision_policy: accuracy_first / speed_first
speedup_target:   <值>
cluster_mode:     yes / no
entrypoint:       /bio-gpu-team

是否确认创建？（yes 继续 / no 重新配置）
```

## 确认后创建工作区

确认后创建以下目录结构：

```
<workspace_path>/
├── biogpu_project.yaml
├── state/
│   └── task_state.json
├── configs/
│   ├── rjob_config.yaml
│   ├── resource_budget.yaml
│   ├── image_config.yaml
│   └── precision_config.yaml
├── benchmarks/
│   ├── profiling/
│   ├── primary_e2e/
│   └── double_check_e2e/
├── baseline/
├── runs/
├── reports/
│   ├── test_plans/
│   └── test_results/
├── logs/
├── pitfalls/
└── artifacts/
```

## biogpu_project.yaml 内容

```yaml
project_id: <tool_name>_<YYYYMMDD>
tool_name: <tool_name>
mode: <A 或 B>

harness:
  root: /Users/huron/code/ai_lab/biogpu-harness
  entrypoint: /bio-gpu-team
  version: 0.1.0

paths:
  workspace_path: <workspace_path>
  bio_tool_path: <bio_tool_path>
  state_path: <workspace_path>/state/task_state.json
  reports_path: <workspace_path>/reports
  runs_path: <workspace_path>/runs
  benchmarks_path: <workspace_path>/benchmarks
  baseline_path: <workspace_path>/baseline
  logs_path: <workspace_path>/logs
  pitfalls_path: <workspace_path>/pitfalls
  artifacts_path: <workspace_path>/artifacts

user_request:
  summary: "<用户需求描述>"
  priority: <accuracy_first 或 speed_first>
  speedup_target: <加速倍数>
  notes: ""

benchmarks:
  primary_e2e:
    status: not_ready
    source: harness_selected
    name: null
    path: null
    input_manifest_path: null
  double_check_e2e:
    status: not_requested
    source: user_provided
    name: null
    path: null
    input_manifest_path: null

configs:
  rjob_config: configs/rjob_config.yaml
  resource_budget: configs/resource_budget.yaml
  image_config: configs/image_config.yaml
  precision_config: configs/precision_config.yaml
```

## task_state.json 初始内容

```json
{
  "task_id": "<tool_name>_<YYYYMMDD>",
  "tool_name": "<tool_name>",
  "mode": "<A 或 B>",

  "current_step": "project_initialized",
  "current_role": "bio-gpu-team",
  "current_module": null,

  "module_queue": [],
  "attempt": 0,
  "max_attempts_per_module": 3,

  "next_action": "run_benchmark",
  "last_result": null,

  "human_approval_required": false,
  "approval_reason": null,
  "approved": false,

  "tests": {
    "primary_e2e": {
      "status": "not_started",
      "benchmark_source": "harness_selected",
      "benchmark_name": null,
      "benchmark_path": null,
      "plan_path": null,
      "input_manifest_path": null,
      "cpu_result_path": null,
      "gpu_result_path": null,
      "compare_report_path": null,
      "approved": false,
      "pass": null
    },
    "double_check_e2e": {
      "status": "not_requested",
      "benchmark_source": "user_provided",
      "benchmark_name": null,
      "benchmark_path": null,
      "plan_path": null,
      "input_manifest_path": null,
      "cpu_result_path": null,
      "gpu_result_path": null,
      "compare_report_path": null,
      "approved": false,
      "user_confirmed": false,
      "pass": null
    }
  },

  "execution_plan": {
    "required": false,
    "status": "not_started",
    "path": null,
    "user_approved": false
  }
}
```

B 模式时 `execution_plan.required = true`，`next_action = "plan_existing_project"`。

## 创建完成后

创建完成后输出：

```
BioGPU project 创建完成：

workspace_path: <路径>
biogpu_project.yaml: <路径>
task_state.json: <路径>

下一步：
返回 /bio-gpu-team 继续执行流程。
```

然后将控制权交回 `/bio-gpu-team`。
