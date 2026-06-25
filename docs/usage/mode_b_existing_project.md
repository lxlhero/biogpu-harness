# B 模式：继续优化/修复已有项目

## 适用场景

- 已有 GPU 加速版本，需要修复精度/速度问题
- 需要重新跑 benchmark 验证
- 需要继续做下一个模块
- 需要生成最终报告

## 流程

```
B0  项目识别
    /bio-gpu-team 读取 workspace_path 或 biogpu_project.yaml
    如果不存在 biogpu_project.yaml → 调用 /bio-gpu-project-init (mode=B)

B1  现状扫描
    bio-gpu-existing-project-planner-agent
    读取：biogpu_project.yaml、task_state.json、reports/、runs/、baseline/、logs/

B2  生成 execution_plan.md
    输出：reports/execution_plan.md
    包含：当前状态、失败阶段、缺失 artifacts、推荐恢复点、推荐 next_action

B3  Human Approval Gate
    用户确认 execution_plan.md

B4  按 execution_plan 路由
    缺 benchmark → bio-gpu-benchmark-agent
    缺 CPU baseline → bio-gpu-test-runner-agent (primary_e2e, cpu_baseline)
    primary_e2e fail → bio-gpu-problem-analyst-agent
    module test fail → bio-gpu-problem-analyst-agent → bio-gpu-dev-agent
    速度不达标 → bio-gpu-profiling-agent → bio-gpu-code-planner-agent
    精度不达标 → bio-gpu-problem-analyst-agent → bio-gpu-dev-agent
    primary_e2e passed + double_check not_requested → ask_double_check
    both tests passed → bio-gpu-doc-writer-agent
```

## B 模式铁律

**B 模式禁止：**
- 直接修改代码（未生成 execution_plan 前）
- 提交 rjob（未 Human Approval 前）
- 构建镜像（未 Human Approval 前）

必须先完成 B1-B3 才允许执行任何操作。

## 启动命令

```bash
cd /Users/huron/code/ai_lab/biogpu-harness
claude
/bio-gpu-team
```

启动后：第一问工具名称，第二问选择 B 模式，然后提供工作区路径和本次需求描述。

**不再使用以下方式启动（已废弃）：**

```bash
# 旧方式，不再推荐
/bio-gpu-team /path/to/biogpu_project.yaml
```

## B 模式向导问题

```text
1. 已有工程工作区在哪里？
   默认：/Users/huron/code/ai_lab/transfer2gpu/<tool_name>

2. 这次具体要做什么？
   a. 修复精度不达标
   b. 修复 E2E 测试失败
   c. 修复 module test 失败
   d. 修复运行错误 / rjob / Docker 错误
   e. 优化速度
   f. 继续下一个 GPU 加速模块
   g. 重新设计或补跑 benchmark
   h. 补做用户 double-check benchmark
   i. 生成或更新最终报告
   j. 其他，自由描述

3. 是否允许 agent 修改已有 GPU 代码？（默认：允许）
4. 是否需要在执行前确认 execution_plan.md？（默认：需要）
```

以下工程细节**无需用户回答**，由 bio-gpu-existing-project-planner-agent 自动判断：

- 是否沿用已有 benchmark
- 是否沿用已有 CPU baseline
- 是否沿用已有 GPU 实现
- 是否需要重新 profiling
