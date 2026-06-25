---
description: BioGPU-Harness 项目初始化向导 — 创建工作区结构和 biogpu_project.yaml
---

# /bio-gpu-project-init — 项目初始化向导

> 本命令由 `/bio-gpu-team` 在向导阶段调用。
> 负责创建或补全工作区结构，不重复向用户询问 `/bio-gpu-team` 已采集的信息。

## A 模式初始化

### 接收来自 /bio-gpu-team 的信息

```
tool_name:             <工具名称>
mode:                  A
acceleration_goal:     <用户描述的加速目标>
user_source:           <用户指定来源，如有>
user_benchmark:        <用户指定 benchmark，如有>
workspace_path:        <用户确认的工作区路径>
```

### A 模式禁止询问

- 生信工具源码路径
- 是否已有 CPU baseline
- 精度要求
- 是否使用 rjob / Docker / 集群
- 加速目标倍数

### A 模式询问顺序

仅在 /bio-gpu-team 未采集的信息缺失时补问，**每步等待用户回答再继续**。

通常 /bio-gpu-team 已采集所有必要信息，本命令直接进入确认和创建。

### 确认前展示

```
即将创建 BioGPU project：

tool_name:        <值>
mode:             A
workspace_path:   <值>
bio_tool_path:    <workspace_path>/bio_tool
source:           <用户指定来源 或 "auto（由 agent 自动查找）">
benchmark:        <用户指定 或 "auto（由 agent 自动选择）">
precision_policy: auto（由 bio-gpu-test-planner-agent 判断）
entrypoint:       /bio-gpu-team

是否确认创建？（yes 继续 / no 重新配置）
```

## B 模式初始化

B 模式只在 `biogpu_project.yaml` 或 `task_state.json` 缺失时补建，**不覆盖已有 reports/runs/baseline**。

### B 模式询问顺序

仅在配置文件缺失时补问：

```
1. 工作区路径是否正确？（/bio-gpu-team 传入）
2. 缺少 biogpu_project.yaml 时，补问 tool_name（如未知）
```

## 确认后创建工作区

确认后创建以下目录结构（已存在的目录跳过）：

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

## biogpu_project.yaml 内容（A 模式）

```yaml
project_id: <tool_name>_<YYYYMMDD>
tool_name: <tool_name>
mode: A

harness:
  root: /Users/huron/code/ai_lab/biogpu-harness
  entrypoint: /bio-gpu-team
  version: 0.1.0

paths:
  workspace_path: <workspace_path>
  bio_tool_path: <workspace_path>/bio_tool
  state_path: <workspace_path>/state/task_state.json
  reports_path: <workspace_path>/reports
  runs_path: <workspace_path>/runs
  benchmarks_path: <workspace_path>/benchmarks
  baseline_path: <workspace_path>/baseline
  logs_path: <workspace_path>/logs
  pitfalls_path: <workspace_path>/pitfalls
  artifacts_path: <workspace_path>/artifacts

source:
  status: pending
  user_specified_source: <true 如果用户提供了来源，否则 false>
  source_url: <用户提供的 URL 或 null>
  version: <用户提供的版本或 null>
  install_method: auto

user_request:
  summary: "<用户描述的 GPU 加速目标>"
  priority: auto
  speedup_target: auto
  notes: ""

benchmarks:
  primary_e2e:
    status: not_ready
    source: <user_provided 如果用户提供，否则 harness_selected>
    name: null
    path: <用户提供的路径或 null>
    input_manifest_path: null
  double_check_e2e:
    status: not_requested
    source: user_provided
    name: null
    path: null
    input_manifest_path: null

precision:
  policy: auto
  decided_by: bio-gpu-test-planner-agent
  plan_path: null

configs:
  rjob_config: configs/rjob_config.yaml
  resource_budget: configs/resource_budget.yaml
  image_config: configs/image_config.yaml
  precision_config: configs/precision_config.yaml
```

## task_state.json 初始内容（A 模式）

```json
{
  "task_id": "<tool_name>_<YYYYMMDD>",
  "tool_name": "<tool_name>",
  "mode": "A",

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

B 模式时还需写入 `session_request`（由 /bio-gpu-team 传入）：

```json
{
  "session_request": {
    "tool_name": "<tool_name>",
    "mode": "B",
    "request_type": "<类型>",
    "summary": "<用户描述>",
    "user_notes": "",
    "allow_code_changes": true,
    "requires_execution_plan_approval": true
  }
}
```

## 创建完成后

创建完成后输出：

```
BioGPU project 创建完成：

workspace_path:      <路径>
biogpu_project.yaml: <路径>
task_state.json:     <路径>

source.status:       pending（bio-gpu-benchmark-agent 将自动初始化工具源码）
precision.policy:    auto（bio-gpu-test-planner-agent 将自动判断精度指标）

下一步：返回 /bio-gpu-team 继续执行流程。
```

然后将控制权交回 `/bio-gpu-team`。

## Resource Layer Policy

This command does not load long-form skill references.

It reads only:
- `CLAUDE.md`
- `biogpu_project.yaml`（如已存在）
- `state/task_state.json`（如已存在）

Long-form references under `skills/bioinformatics-tool-gpu-skills/` are read by specialist agents on demand.

Do not use deprecated path: `skills/bioinformatics-tool-gpu-ification`.
