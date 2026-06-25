# BioGPU-Harness 快速入门

## 安装与启动

```bash
cd /Users/huron/code/ai_lab/biogpu-harness
claude
/bio-gpu-team
```

## A 模式：从头开始 GPU 加速

适用于未做过 GPU 加速的新工具。

1. 启动 `/bio-gpu-team`，无需任何参数
2. `/bio-gpu-team` 检测到无项目配置，自动调用 `/bio-gpu-project-init`
3. 按向导填写工具信息
4. 确认后系统开始全自动流程

## B 模式：继续优化/修复已有项目

适用于已有 GPU 加速代码但需要修复或优化。

```bash
cd /Users/huron/code/ai_lab/biogpu-harness
claude
/bio-gpu-team /Users/huron/code/ai_lab/transfer2gpu/<tool_name>/biogpu_project.yaml
```

或者直接启动 `/bio-gpu-team`，告知 workspace_path：

```bash
/bio-gpu-team
> workspace_path: /Users/huron/code/ai_lab/transfer2gpu/scavenge
```

## 不要再使用

```bash
# 旧方式（已废弃）
cd /Users/huron/code/ai_lab/transfer2gpu
claude
/gpu-team scavenge A "..."
```

请改用：

```bash
cd /Users/huron/code/ai_lab/biogpu-harness
claude
/bio-gpu-team
```
