# 测试体系说明

## 两类测试

### primary_e2e

- **来源**：bio-gpu-benchmark-agent 或 harness 选定
- **用途**：主 CPU baseline 和 GPU E2E 对比，是主流程必须项
- **状态流**：`not_ready → benchmark_ready → plan_drafted → approved → cpu_done → gpu_compared → pass/fail`

### double_check_e2e

- **来源**：用户额外提供
- **用途**：primary_e2e PASS 后的二次验证
- **规则**：
  - 用户可跳过（`status: skipped`）
  - 一旦用户选择执行，必须 PASS 才能进入最终报告
  - benchmark 必须与 primary_e2e 不同

## 测试 Agents

| Agent | 职责 |
|-------|------|
| bio-gpu-test-planner-agent | 生成测试计划（只规划，不执行）|
| bio-gpu-test-runner-agent | 按已批准计划执行测试 |

## 执行时序

```
test-planner 生成 test_plan.md
    ↓
Human Approval Gate（用户确认计划）
    ↓
test-runner 执行（cpu_baseline / gpu_compare / cpu_and_gpu_compare）
    ↓
输出结果 JSON + compare_report.md
    ↓
/bio-gpu-team 判断 PASS/FAIL
```

## 精度指标自动判断

精度指标**不由用户在入口阶段定义**，而是由 bio-gpu-test-planner-agent 自动判断：

- 分析工具输出类型（连续值 / 集合 / 排序 / 统计参数等）
- 选择对应精度指标（Pearson r / Jaccard / F1 / exact match 等）
- 在 test_plan.md 中写明选择理由
- 交用户在 Human Approval Gate 确认

bio-gpu-test-runner-agent 只执行 test_plan 中确定的指标，不重新设计。

## 禁止事项

- test-planner 不得执行任何测试
- test-runner 不得在无 approved plan 的情况下运行
- test-runner 不得自行更换 benchmark 或修改精度指标
- test-runner 遇到 test_plan 缺少 precision_metrics 时，返回 blocked，不自行补充
- 不得覆盖已有 CPU baseline
