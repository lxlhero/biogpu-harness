# 快速上手

## 启动

所有任务统一从 `/bio-gpu-team` 无参数启动：

```bash
cd /Users/huron/code/ai_lab/biogpu-harness
claude
/bio-gpu-team
```

## 向导流程

### 第一步：输入工具名称

```text
请先告诉我这次要处理的生信工具名称。

例如：
- gsMap
- scavenge
- susieR
```

### 第二步：选择模式

```text
A. 从头开始 GPU 加速这个工具
B. 修复 / 优化 / 继续这个工具的已有 GPU 加速工程
```

## A 模式：新工具，从头加速

只需提供：

1. **加速目标**（自由描述）
2. 可选：工具版本或下载来源
3. 可选：指定 benchmark / 数据集
4. 可选：自定义工作区路径（默认 `/Users/huron/code/ai_lab/transfer2gpu/<tool_name>`）

**不需要提供：** 源码路径、精度要求、CPU baseline、rjob/Docker 配置。
系统自动处理工具下载、精度判断和测试计划，执行前交用户确认。

## B 模式：已有工程，修复或优化

只需提供：

1. **已有工作区路径**（默认 `/Users/huron/code/ai_lab/transfer2gpu/<tool_name>`）
2. **本次要做什么**（修复精度 / 优化速度 / 继续模块 / 补做 benchmark 等）

系统扫描已有 artifacts，自动判断方案，生成 `reports/execution_plan.md` 供用户确认后执行。

## 典型用例

```text
# 新工具全流程
工具名称：susieR
模式：A
目标：端到端 GPU 加速，精度优先

# 速度优化
工具名称：scavenge
模式：B
目标：当前 E2E speedup 只有 1.2×，希望继续优化

# 补做 double-check benchmark
工具名称：gsMap
模式：B
目标：primary_e2e 已通过，补做开源 benchmark 验收
```

## 输出位置

所有 runtime artifacts 写入工具工作区，不写入 biogpu-harness 仓库：

```text
transfer2gpu/<tool_name>/
  reports/          ← 分析报告、测试计划、最终文档
  runs/             ← 每次集群任务结果
  baseline/         ← CPU E2E baseline（不可覆盖）
  benchmarks/       ← profiling + E2E 数据
  logs/             ← 审计日志
```
