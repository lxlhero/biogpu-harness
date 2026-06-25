# A 模式：从头开始 GPU 加速

## 适用场景

- 生信工具没有 GPU 版本
- 需要从分析热点模块开始，完成完整 GPU 化流程

## 流程

```
A0  项目初始化
    /bio-gpu-team → /bio-gpu-project-init
    生成 biogpu_project.yaml + task_state.json + workspace 目录

A1  benchmark 准备
    bio-gpu-benchmark-agent
    输出：benchmarks/profiling/ + benchmarks/primary_e2e/

A2  L1 镜像构建
    bio-gpu-image-builder-agent (L1)

A3  profiling + feasibility
    bio-gpu-profiling-agent → bio-gpu-feasibility-agent
    输出：reports/profiling_report.md + reports/feasibility_report.md
    若 Amdahl < 1.15×：终止，生成不建议报告

A4  primary_e2e 测试计划
    bio-gpu-test-planner-agent (test_suite=primary_e2e)
    输出：reports/test_plans/primary_e2e_test_plan.md

A5  Human Approval Gate
    用户确认 primary_e2e_test_plan.md

A6  CPU baseline
    bio-gpu-test-runner-agent (test_suite=primary_e2e, run_stage=cpu_baseline)

A7  实现规划
    bio-gpu-code-planner-agent（每个模块）

A8  GPU 开发循环（每个模块）
    bio-gpu-dev-agent → bio-gpu-code-reviewer-agent → bio-gpu-module-tester-agent
    PASS → 下一个模块 / 全部通过进入 A9
    FAIL → 回 bio-gpu-dev-agent（超过 max_attempts → bio-gpu-problem-analyst-agent）

A9  L2 镜像构建
    bio-gpu-image-builder-agent (L2)

A10 primary_e2e GPU 对比
    bio-gpu-test-runner-agent (test_suite=primary_e2e, run_stage=gpu_compare)

A11 double_check_e2e（可选）
    /bio-gpu-team 展示 primary_e2e benchmark，询问是否提供额外 benchmark
    用户跳过 → 进入 A12
    用户提供 → bio-gpu-test-planner-agent + Human Approval Gate + bio-gpu-test-runner-agent

A12 最终文档
    bio-gpu-doc-writer-agent → reports/final_report.md
```

## 启动命令

```bash
cd /Users/huron/code/ai_lab/biogpu-harness
claude
/bio-gpu-team
```
