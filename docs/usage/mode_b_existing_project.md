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
# 然后提供 workspace_path
```
