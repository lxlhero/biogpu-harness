# BioGPU-Harness

BioGPU-Harness 是一个用于生信工具 GPU 加速的 Claude Code agent harness。

它负责自动完成：

- 工具源码获取和初始化
- benchmark 设计
- CPU baseline 建立
- profiling 和瓶颈分析
- GPU 实现规划
- GPU kernel / 模块开发
- 精度和性能验证
- 用户 double-check benchmark
- 最终报告生成

## 资源层宪法摘要

BioGPU-Harness 按职责分层，任何文件都必须有明确归属，不能跨层混用。

| 目录 | 定位 | 不做什么 |
|------|------|---------|
| `.claude/commands/` | 用户入口和 orchestrator 路由 | 不做专业执行，不读长方法论 |
| `.claude/agents/` | 专业执行角色 | 不做人类入口，不复制长参考文档 |
| `.claude/knowledge/` | 运行时短规则、高频 checklist、pitfall | 不放长篇方法论，不放报告模板 |
| `skills/bioinformatics-tool-gpu-skills/` | 长方法论、深度 references、报告模板资产 | 不放运行时强规则，不放 task_state 或 artifacts |
| `docs/` | 人类阅读文档、架构记录、使用说明 | 不作为 agent 运行时强规则 |
| `templates/` | 工作区初始化骨架 | 不解释完整逻辑，不存运行结果 |
| `scripts/` | 后续可执行工具脚本 | 不写 prompt，不写方法论 |
| `transfer2gpu/<tool>/` | 具体工具工作区和 runtime artifacts | 不存 harness 控制面文件 |

核心规则：

- `commands` 只负责入口和路由。
- `agents` 负责专业执行，按需读取 `knowledge` 或 `skills`。
- `knowledge` 是 agents 的随身短手册（高频、短、硬约束）。
- `skills` 是 agents 的方法论图书馆（长方法论、按需读取）。
- `docs` 给人看，不作为运行时强规则。
- runtime artifacts 只能写入 `transfer2gpu/<tool>/`。

完整宪法见 [`docs/architecture/resource_layer_constitution.md`](docs/architecture/resource_layer_constitution.md)。

## 启动方式

所有任务都统一从 `/bio-gpu-team` 启动：

```bash
cd /Users/huron/code/ai_lab/biogpu-harness
claude
/bio-gpu-team
```

启动后，系统会先询问工具名称，例如：

```text
gsMap
scavenge
susieR
```

然后选择任务模式：

```text
A. 从头开始 GPU 加速这个工具
B. 修复 / 优化 / 继续这个工具的已有 GPU 加速工程
```

## A 模式：从头开始 GPU 加速

适用于未做过 GPU 加速的新工具。

A 模式只需要用户提供：

1. 工具名称
2. 本次 GPU 加速目标
3. 可选：指定工具版本或下载来源
4. 可选：指定 benchmark / 数据集
5. 可选：是否使用默认工作区路径

不需要用户提供源码路径。BioGPU-Harness 会自动查找、下载、初始化工具源码。

不需要用户手动定义精度要求。BioGPU-Harness 会在测试计划阶段自动选择精度指标，并在执行前交给用户确认。

## B 模式：修复 / 优化已有工程

适用于已有 `transfer2gpu/<tool_name>` 工作区的项目。

B 模式只需要用户提供：

1. 工具名称
2. 已有工作区路径（默认 `/Users/huron/code/ai_lab/transfer2gpu/<tool_name>`）
3. 本次要修复或优化的目标

例如：

- 修复精度不达标
- 修复 E2E 测试失败
- 优化速度
- 继续下一个 GPU 加速模块
- 补做用户 double-check benchmark
- 生成最终报告

系统会扫描已有 artifacts，生成 `reports/execution_plan.md`，用户确认后再继续执行。

## 工作区位置

默认每个工具的工作区在：

```text
/Users/huron/code/ai_lab/transfer2gpu/<tool_name>
```

runtime artifacts 会写入工具工作区，不会写入 `biogpu-harness` 仓库本身：

```text
reports/
runs/
baseline/
logs/
benchmarks/
artifacts/
```

## 常见示例

### 示例 1：从头加速 scavenge

```text
使用 /bio-gpu-team A 模式，从头对 <tool_name> 做 GPU 加速。

workspace：
/Users/huron/code/ai_lab/transfer2gpu/<tool_name>

要求：
1. 不覆盖已有目录，如已存在请新建 <tool_name>_harness_a_mode。
2. 先用小规模 benchmark 跑完整闭环。
3. requires_execution_plan_approval=true。
4. 先通过 validators、trace_context、project_init gate 后再继续。
```

### 示例 2：继续优化 gsMap

```text
使用 /bio-gpu-team B 模式，继续处理已有 <tool_name> 项目。

workspace：
/Users/huron/code/ai_lab/transfer2gpu/<tool_name>

本次任务：
<修精度 / 重跑 benchmark / 优化速度 / 写 final report>

要求：
1. 不覆盖已有 artifacts。
2. 先读取现有 biogpu_project.yaml、task_state.json、reports、runs、baseline、logs。
3. 写入 session_request。
4. 运行 validators、trace_context、project_init gate。
```

### 示例 3：给 scavenge 补做 double-check benchmark

```text
/bio-gpu-team
工具名称：scavenge
模式：B
工作区：/Users/huron/code/ai_lab/transfer2gpu/scavenge
目标：primary_e2e 已通过，我想提供一个新的 benchmark 做复核
```


