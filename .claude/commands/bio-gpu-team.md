---
description: BioGPU-Harness 唯一正式入口 — 根据项目配置调度 bio-gpu-* agents 完成 GPU 加速全流程
argument-hint: "[workspace_path 或 biogpu_project.yaml 路径]"
---

# /bio-gpu-team — BioGPU-Harness 主 Orchestrator

> 本命令是 BioGPU-Harness 的唯一正式入口。
> 所有 GPU 加速任务均从此命令启动。旧 `/gpu-team` 已废弃。

## 启动序列

每次启动必须按序执行：

1. 读取 `biogpu-harness/CLAUDE.md`（路径规则、架构约束）
2. 读取 `.claude/knowledge/methodology.md`（GPU 化方法论）
3. 读取 `.claude/knowledge/pitfalls/common.md`（通用踩坑）

## 项目配置检测

启动后立即检查用户是否提供 `workspace_path` 或 `biogpu_project.yaml` 路径：

**如果没有项目配置：**
```
调用 /bio-gpu-project-init
```

**如果有项目配置：**
```
读取 biogpu_project.yaml
读取 state/task_state.json
进入路由逻辑
```

所有路径必须从 `biogpu_project.yaml` 获取，禁止假设当前目录是工具工作区。

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
A1  benchmark 准备 → bio-gpu-benchmark-agent
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
B0  读取 workspace_path，检查 biogpu_project.yaml
    不存在 → /bio-gpu-project-init (mode=B)
B1  扫描现状 → bio-gpu-existing-project-planner-agent
B2  生成 execution_plan.md
B3  Human Approval Gate（用户确认 execution_plan.md）
B4  按 execution_plan 路由到对应 agent
```

## double_check_e2e 询问规则

`primary_e2e` PASS 后，必须先展示以下信息再询问：

```
primary_e2e.benchmark_name:    <值>
primary_e2e.benchmark_path:    <值>
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
