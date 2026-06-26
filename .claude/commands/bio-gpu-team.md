---
description: BioGPU-Harness 唯一正式入口 — 根据项目配置调度 bio-gpu-* agents 完成 GPU 加速全流程
argument-hint: ""
---

# /bio-gpu-team — BioGPU-Harness 主 Orchestrator

> 本命令是 BioGPU-Harness 的唯一正式入口。
> 所有 GPU 加速任务均从此命令启动。旧 `/gpu-team` 已废弃。

## 启动序列

每次启动必须按序执行：

1. 读取 `biogpu-harness/CLAUDE.md`（路径规则、架构约束）
2. 读取 `.claude/knowledge/methodology.md`（GPU 化方法论）
3. 读取 `.claude/knowledge/pitfalls/common.md`（通用踩坑）

## 启动向导

启动后**不要直接问 A/B 模式**，按以下顺序询问：

### 第一问：工具名称

```text
请先告诉我这次要处理的生信工具名称。

例如：
- gsMap
- scavenge
- susieR
- 自定义工具名
```

### 第二问：任务模式

用户输入工具名后，再问：

```text
请选择这个工具的任务模式：

A. 从头开始 GPU 加速这个工具
B. 修复 / 优化 / 继续这个工具的已有 GPU 加速工程
```

### A 模式：只问少量业务问题

```text
1. 本次 GPU 加速目标是什么？
   可自由描述，例如：
   - 做端到端 GPU 加速
   - 先自动分析瓶颈，优先加速最值得做的模块
   - 希望整体速度至少提升 2x
   - 只加速某个指定模块

2. 是否指定工具版本或下载来源？（可选）
   - 没有：由 agent 自动查找、下载、初始化
   - 有：请提供 GitHub / GitCode / pip / conda / release 信息

3. 是否有希望优先使用的数据集或 benchmark？（可选）
   - 没有：由 agent 自动选择或构造
   - 有：请提供路径或说明

4. 工作区是否使用默认路径？
   默认：/Users/huron/code/ai_lab/transfer2gpu/<tool_name>
   （回车确认 / 或提供自定义路径）
```

**A 模式禁止问：** 源码路径、是否已有 CPU baseline、精度要求、是否使用 rjob/Docker/集群。

### B 模式：采集工作区和需求

```text
1. 这个工具的已有工程工作区在哪里？
   默认尝试：/Users/huron/code/ai_lab/transfer2gpu/<tool_name>
   （回车确认 / 或提供自定义路径）

2. 这次具体要做什么？
   请选择或自由描述：
   a. 修复精度不达标
   b. 修复 E2E 测试失败
   c. 修复 module test 失败
   d. 修复运行错误 / rjob 错误 / Docker 错误
   e. 优化速度，当前能跑但速度不满意
   f. 继续做下一个 GPU 加速模块
   g. 重新设计或补跑 benchmark
   h. 补做用户 double-check benchmark
   i. 生成或更新最终报告
   j. 其他，自由描述

3. 是否允许 agent 修改已有 GPU 代码？（默认：允许，但须先确认 execution_plan.md）

4. 是否需要在执行前确认 execution_plan.md？（默认：需要）
```

**B 模式禁止在向导阶段问：** 是否沿用已有 benchmark、是否沿用已有 baseline、是否沿用已有 GPU 实现、是否允许重新 profiling。这些由 bio-gpu-existing-project-planner-agent 扫描后判断。

## 启动后路由逻辑

```
/bio-gpu-team
→ ask tool_name
→ ask mode A/B

if mode = A:
  → ask acceleration_goal
  → ask optional source/version
  → ask optional benchmark/dataset
  → ask workspace default yes/no
  → call /bio-gpu-project-init (mode=A)
  → run: python scripts/validate_biogpu_project.py --workspace <workspace>
  → run: python scripts/validate_task_state.py --workspace <workspace>
  → if validator fail: stop, report errors, do not proceed
  → next_action = run_benchmark

if mode = B:
  → ask existing workspace_path
  → ask session_request (need, allow_code_changes, requires_plan_approval)
  → ensure biogpu_project.yaml / task_state.json exists
  → write task_state.session_request
  → run: python scripts/validate_task_state.py --workspace <workspace>
  → if validator fail: fix task_state.json first, do not enter existing-project-planner
  → next_action = plan_existing_project
  → call bio-gpu-existing-project-planner-agent
```

## 路由表

根据 `task_state.json` 中的 `next_action` 调用对应 agent：

| next_action | 调用 |
|---|---|
| initialize_project | /bio-gpu-project-init |
| run_benchmark | bio-gpu-benchmark-agent |
| build_l1_image | bio-gpu-image-builder-agent |
| run_profiling | bio-gpu-profiling-agent |
| assess_feasibility | bio-gpu-feasibility-agent |
| plan_primary_e2e | bio-gpu-test-planner-agent (test_suite=primary_e2e) |
| run_primary_cpu_baseline | bio-gpu-test-runner-agent (test_suite=primary_e2e, run_stage=cpu_baseline) |
| plan_gpu_implementation | bio-gpu-code-planner-agent |
| implement_gpu_module | bio-gpu-dev-agent |
| review_gpu_code | bio-gpu-code-reviewer-agent |
| run_module_test | bio-gpu-module-tester-agent |
| diagnose_failure | bio-gpu-problem-analyst-agent |
| build_l2_image | bio-gpu-image-builder-agent |
| run_primary_gpu_compare | bio-gpu-test-runner-agent (test_suite=primary_e2e, run_stage=gpu_compare) |
| ask_double_check | /bio-gpu-team 直接询问用户（见下方规则） |
| plan_double_check_e2e | bio-gpu-test-planner-agent (test_suite=double_check_e2e) |
| run_double_check_e2e | bio-gpu-test-runner-agent (test_suite=double_check_e2e, run_stage=cpu_and_gpu_compare) |
| plan_existing_project | bio-gpu-existing-project-planner-agent |
| write_final_report | bio-gpu-doc-writer-agent |

## A 模式流程（从头 GPU 加速）

```
A0  项目初始化 → /bio-gpu-project-init
A1  benchmark 准备 + 工具源码初始化 → bio-gpu-benchmark-agent
A2  L1 镜像构建 → bio-gpu-image-builder-agent
A3  profiling + feasibility
    → bio-gpu-profiling-agent → bio-gpu-feasibility-agent
A4  primary_e2e 测试计划 → bio-gpu-test-planner-agent(test_suite=primary_e2e)
A5  Human Approval Gate（用户确认 primary_e2e_test_plan.md）
A6  CPU baseline → bio-gpu-test-runner-agent(test_suite=primary_e2e, run_stage=cpu_baseline)
A7  实现规划 → bio-gpu-code-planner-agent
A8  GPU 开发循环
    bio-gpu-dev-agent → bio-gpu-code-reviewer-agent → bio-gpu-module-tester-agent
    PASS → 下一个 module
    FAIL → 回 bio-gpu-dev-agent
    超过 max_attempts → bio-gpu-problem-analyst-agent
A9  L2 镜像构建 → bio-gpu-image-builder-agent
A10 primary_e2e GPU 对比 → bio-gpu-test-runner-agent(test_suite=primary_e2e, run_stage=gpu_compare)
A11 double_check_e2e 可选复核（见下方规则）
A12 最终文档 → bio-gpu-doc-writer-agent
```

## B 模式流程（已有项目继续优化/修复）

```
B0  读取 workspace_path，写入 session_request 到 task_state
    biogpu_project.yaml 不存在 → /bio-gpu-project-init (mode=B)
B1  扫描现状 → bio-gpu-existing-project-planner-agent
    （agent 根据 session_request + 已有 artifacts 自动判断方向）
B2  生成 execution_plan.md
B3  Human Approval Gate（用户确认 execution_plan.md）
B4  按 execution_plan 路由到对应 agent
```

## double_check_e2e 询问规则

`primary_e2e` PASS 后，必须先展示以下信息再询问：

```
primary_e2e.benchmark_name:      <值>
primary_e2e.benchmark_path:      <值>
primary_e2e.input_manifest_path: <值>
primary_e2e.compare_report_path: <值>
```

然后询问：

```
primary_e2e 已通过。是否提供不同的额外 benchmark 做 double-check 验收？
（必须与上方 primary_e2e benchmark 不同）
```

用户跳过：

```json
{"tests": {"double_check_e2e": {"status": "skipped"}}}
```

用户提供：

```
→ bio-gpu-test-planner-agent(test_suite=double_check_e2e)
→ Human Approval Gate
→ bio-gpu-test-runner-agent(test_suite=double_check_e2e, run_stage=cpu_and_gpu_compare)
```

double_check_e2e 一旦用户选择执行，必须 PASS 才能继续。

## Human Approval Gate

以下操作前必须停止并请求用户确认：

- primary_e2e_test_plan.md 生成后 → 执行 CPU baseline 前
- execution_plan.md 生成后 → B 模式执行前
- double_check_e2e_test_plan.md 生成后
- 构建 L2 release 镜像 / push
- tag 或 push v1.0
- 覆盖已有 benchmark 数据
- 删除或重建 CPU baseline
- 接受 E2E speedup < 1.15× 的边界结果

进入 gate 时更新 task_state：

```json
{"human_approval_required": true, "approval_reason": "<原因>", "approved": false}
```

## Agent 返回格式要求

调用每个 bio-gpu-* agent 后，期望返回：

```
status: pass | fail | blocked
evidence: <artifact 路径或简短说明>
artifact_paths: [<path1>, ...]
next_action: <下一步 action>
blockers: <问题描述（如有）>
```

不接受空口宣布 PASS；PASS 必须有 artifact 证据。

## 异常路由

| failure_type | 处理 |
|---|---|
| precision_mismatch | → bio-gpu-dev-agent，连续 2 次同类失败后 → bio-gpu-problem-analyst-agent |
| rjob_runtime_error | → bio-gpu-problem-analyst-agent → bio-gpu-dev-agent |
| speed_regression | → bio-gpu-profiling-agent → bio-gpu-code-planner-agent |
| image_build_failed | → bio-gpu-image-builder-agent |
| benchmark_invalid | → bio-gpu-benchmark-agent |
| 未分类错误 | → bio-gpu-problem-analyst-agent |

## 知识沉淀

任意失败修复循环完成后，检查根因是否已记录在 `.claude/knowledge/pitfalls/`。
未覆盖则写入对应文件（不使用 `pitfall #N` 编号）。

## Resource Layer Policy

This command does not load long-form skill references.

It may read:
- `CLAUDE.md`
- `.claude/knowledge/README.md`
- `biogpu_project.yaml`
- `state/task_state.json`

Long-form references under `skills/bioinformatics-tool-gpu-skills/` are read by specialist agents on demand.

Do not use deprecated path: `skills/bioinformatics-tool-gpu-ification`.
