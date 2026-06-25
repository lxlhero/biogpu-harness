# BioGPU-Harness 资源层宪法

> 本文件是 BioGPU-Harness 各目录定位的最高级说明。
> 任何新文件在落地前必须先对照本宪法确定归属。

---

## 一、七层目录定位

### `.claude/commands/` — 用户入口层

**是什么：** 用户通过 `/bio-gpu-team` 触发的入口指令。

**负责：**
- 接收用户调用
- 询问少量业务信息（工具名、A/B 模式、目标描述）
- 判断 A/B 模式
- 创建或读取项目配置（biogpu_project.yaml）
- 路由到对应 agent
- 展示 Human Approval Gate

**不负责：**
- 不做 benchmark 设计
- 不做 profiling
- 不判断 precision metrics
- 不下载工具源码
- 不跑测试
- 不写复杂报告
- 不直接读取 skills 长方法论

**正式文件：**

```
.claude/commands/bio-gpu-team.md      ← 唯一正式 orchestrator
.claude/commands/bio-gpu-project-init.md
.claude/commands/gpu-team.md          ← deprecated redirect only
```

---

### `.claude/agents/` — 专业执行角色层

**是什么：** 由 orchestrator 按 next_action 调度的专职执行单元。

**负责：**
- 读取 biogpu_project.yaml 和 state/task_state.json
- 执行专业任务（benchmark、profiling、开发、测试、诊断等）
- 按需读取 knowledge / skills
- 写入 reports/runs/baseline/logs/artifacts（到 WORKSPACE_PATH）
- 更新 task_state.next_action
- 返回短摘要给 /bio-gpu-team

**不负责：**
- 不做人类总入口
- 不重写总流程
- 不绕过 task_state 自己跳步骤
- 不把长日志贴回主对话
- 不把 runtime artifact 写进 biogpu-harness
- 不复制长方法论正文到 agent 文件里

**每个 agent 必须声明：**

```
Always read:   高频运行时文件
Read on demand: 长方法论 / 模板资产
Never:         不该读取或不该承担的职责
```

---

### `.claude/knowledge/` — 运行时短规则层

**定位一句话：** agents 的随身短手册。

**允许放：**
- 高频必读短规则
- 执行硬约束
- Pitfall checklist
- Failure quick diagnosis
- Reviewer / tester / problem-analyst 必查规则
- 会直接影响 next_action 的判断规则

**不允许放：**
- 长篇 GPU 化方法论
- 完整 benchmark 教程
- 完整 validation metrics 教程
- 报告模板
- 历史迁移记录
- 用户说明
- Runtime artifacts

**当前文件：**

```
methodology.md                        ← Amdahl + profiling + GPU 代码模式摘要
pitfalls/common.md                    ← GPU kernel 通用 bug checklist
pitfalls/docker_r_bioconductor.md     ← Docker/R/Bioconductor 构建坑
pitfalls/r_reticulate.md              ← R-Python reticulate 桥接坑
```

---

### `skills/bioinformatics-tool-gpu-skills/` — 长方法论资产库

**定位一句话：** agents 的方法论图书馆。

**允许放：**
- 完整 GPU 化方法论
- Benchmark 设计方法
- Bottleneck analysis 详细框架
- GPU suitability 判断指南
- Validation metrics 设计
- Performance metrics 设计
- Bioinformatics GPU patterns 详版
- Failure mode 长版 taxonomy
- 报告模板（格式参考，非 runtime artifact）
- 脚本模板

**不允许放：**
- `/bio-gpu-team` 路由规则
- 当前 task_state 运行状态
- 当前工具运行结果
- Runtime artifacts
- 每次 agent 必须遵守的短规则
- 当前项目路径
- 已废弃备份文件（.bak）

**使用规则：**
- agents 不默认加载所有 references
- agents 只在当前决策需要时按需读取对应 reference
- 每个 reference 有明确的 Primary Consumers（见 references/README.md）

---

### `docs/` — 人类阅读文档层

**是什么：** 给人类读者的文档，包括架构记录、使用说明、分析报告。

**负责：**
- 用户使用说明（docs/usage/）
- 架构设计记录（docs/architecture/）
- 优化方案记录（docs/optimize/）
- 示例配置（docs/examples/）

**不负责：**
- 不作为 agent 运行时强规则
- 不存 runtime artifacts

---

### `templates/` — 工作区初始化骨架层

**是什么：** 新工具工作区初始化时使用的配置骨架。

**负责：**
- `templates/workspace/biogpu_project.yaml` — 项目配置模板
- `templates/workspace/task_state.json` — 状态文件模板
- `templates/workspace/` 下的其他配置骨架

**不负责：**
- 不解释完整逻辑
- 不存运行结果

---

### `transfer2gpu/<tool>/` — 工具工作区层

**是什么：** 具体工具的 GPU 化工作区，所有 runtime artifacts 的唯一存放地。

**只允许：**
- reports/、runs/、baseline/、benchmarks/、logs/、artifacts/ 写入此处
- biogpu_project.yaml、task_state.json 在此处读写

**不允许：**
- 不存 harness 控制面文件
- 不存 agent 指令
- 不存方法论文档

---

## 二、层间边界规则

### knowledge vs skills

| 判断标准 | knowledge | skills |
|---------|-----------|--------|
| 内容长度 | 短（checklist / 公式 / 简短规则） | 长（完整方法论 / 详细教程）|
| 读取频率 | 高频，几乎每个 agent 每次都读 | 按需，只有相关 agent 在需要时读 |
| 内容类型 | 硬约束、bug checklist、快速判断规则 | 方法论、设计指南、模板 |
| 变更频率 | 慢（规则稳定） | 可迭代（方法论随工具积累更新）|

### agents vs knowledge

- agent 文件不复制 knowledge 内容，只引用路径
- knowledge 只存 agent 需要在执行决策时直接用的内容
- knowledge 内容过长时，拆出长版放到 skills，knowledge 保留摘要

### commands vs agents

- commands 只做入口、询问、路由、gate；不执行专业任务
- agents 只在被 orchestrator 调用时执行；不主动做入口

### docs vs runtime rules

- docs 给人看，agents 不从 docs/ 读取运行规则
- agent 执行规则写在 agent 文件本身或 knowledge/ 或 skills/

---

## 三、文件去向判断规则

新文件入库前，按以下问题判断落地位置：

```
Q1: 这是用户调用入口吗？
    是 → .claude/commands/

Q2: 这是专职执行角色的指令吗？
    是 → .claude/agents/

Q3: 这是短、硬、高频被 agent 读取的运行时规则吗？
    是 → .claude/knowledge/

Q4: 这是长方法论、设计指南、报告模板吗？
    是 → skills/bioinformatics-tool-gpu-skills/references/ 或 templates/

Q5: 这是给人类读者的说明文档吗？
    是 → docs/

Q6: 这是工作区初始化骨架文件吗？
    是 → templates/workspace/

Q7: 这是 runtime artifact（运行结果）吗？
    是 → transfer2gpu/<tool>/

Q8: 这是已废弃但有历史价值的文件吗？
    是 → docs/archive/ 或直接删除
```

如果某个文件对以上 8 个问题全部回答"否"，则删除。

---

## 四、关键定义速查

```
commands  = user entrypoints and routing
agents    = specialist execution roles
knowledge = runtime short rules（随身短手册）
skills    = long-form methodology assets（方法论图书馆）
docs      = human documentation
templates = initialization/report skeletons
scripts   = executable utilities（待实现）
transfer2gpu/<tool>/ = runtime artifacts only
```
