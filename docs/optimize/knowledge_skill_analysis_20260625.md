# knowledge/ 与 skills/ 目录现状与问题分析

> 分析日期：2026-06-25
> 分析范围：`.claude/knowledge/` 和 `skills/bioinformatics-tool-gpu-ification/`

---

## 一、目录结构现状

### `.claude/knowledge/`（4 个文件）

```
.claude/knowledge/
├── methodology.md
└── pitfalls/
    ├── common.md
    ├── docker_r_bioconductor.md
    └── r_reticulate.md
```

| 文件 | 内容摘要 |
|------|---------|
| `methodology.md` | Amdahl's Law 公式、profiling 工具（Rprof/cProfile）、3 个 GPU 代码模式 |
| `pitfalls/common.md` | P1 数值路径对齐规则 + P2 GPU 常见 bug（torch.diag / squeeze / sparse.mv）|
| `pitfalls/docker_r_bioconductor.md` | Docker 构建 R/Bioconductor 版本匹配、silent failure 检测 |
| `pitfalls/r_reticulate.md` | reticulate 数据传递、py_run_string 路径规则 |

**agents 引用情况：** 几乎所有 agents 启动时强制读取，是执行时的直接知识来源。

---

### `skills/bioinformatics-tool-gpu-ification/`（SKILL.md + 11 个 references + 7 个 templates）

```
skills/bioinformatics-tool-gpu-ification/
├── SKILL.md
├── SKILL.md.bak_20260624
├── references/
│   ├── README.md                        ← 列出 29 个文件，实际只有 11 个存在
│   ├── benchmark_design.md
│   ├── bioinformatics_gpu_patterns.md
│   ├── bottleneck_analysis.md
│   ├── common_failure_modes.md
│   ├── elbo-diagnostic-softmax.md
│   ├── gpu-precision-matching.md
│   ├── gpu_porting_principles.md
│   ├── gpu_suitability.md
│   ├── performance_metrics.md
│   ├── sigma2-trace-correction.md
│   └── validation_metrics.md
└── templates/
    ├── README.md
    ├── benchmark_real_data.py
    ├── benchmark_report.md
    ├── e2e_checkpoint.sh
    ├── e2e_comparison_report.md
    ├── feasibility_report.md
    ├── final_optimization_summary.md
    └── user_benchmark_report.md
```

**SKILL.md 自述定位：** "methodology and resource layer, not executable agent workflow"

**agents 引用情况：** 仅 `bio-gpu-benchmark-agent` 有一处引用（且路径有误，见问题三）。

---

## 二、问题清单

### 问题一：内容重叠，无明确分层说明

`knowledge/` 与 `skills/references/` 在以下内容上直接重叠：

| knowledge/ | skills/references/ | 重叠内容 |
|---|---|---|
| `methodology.md` | `bottleneck_analysis.md` | Amdahl's Law 框架、profiling 方法 |
| `methodology.md` | `bioinformatics_gpu_patterns.md` | GPU 代码模式（串行→batch、稀疏传播等）|
| `pitfalls/common.md` | `common_failure_modes.md` | 失败模式与诊断方法 |

`knowledge/` 是 `references/` 的精简摘要，但没有任何地方说明这一关系。agents 也不知道何时应该读详版。

---

### 问题二：`skills/` 机制从未被实际利用

Claude Code 的 `skills/` 目录设计为通过 `/skill-name` 触发，提供给用户或 orchestrator 调用。但当前没有任何 agent、command 或用户流程通过技能调用机制使用 `bioinformatics-tool-gpu-ification`。

实际情况：agents 直接用文件路径引用 `references/` 内容，SKILL.md 这层包装没有功能价值，只是目录结构上的形式。

---

### 问题三：bio-gpu-benchmark-agent 引用了不存在的路径（硬错误）

`bio-gpu-benchmark-agent.md` 启动时读取的路径：

```
.claude/knowledge/bioinformatics-tool-gpu-ification/references/benchmark_design.md
```

这个路径**不存在**。正确路径是：

```
skills/bioinformatics-tool-gpu-ification/references/benchmark_design.md
```

这意味着 benchmark-agent 每次启动都会读取失败，benchmark 设计规范无法被加载。

---

### 问题四：`references/README.md` 严重过时

README 列出 29 个文件，实际只有 11 个存在。缺失的 18 个条目：

```
gpu-bug-fix-catalog.md
gpu-chunked-processing.md
h200-cluster-workflow.md
benchmark-data-sources.md
real-data-benchmark-workflow.md
gsmap-case-study.md
scavenge-case-study.md
gsmap-step3-chromosome-parallelism.md
delegate-task-timeout-strategy.md
hotspot-guide.txt
standardize-mismatch-bug.md
（以及其他）
```

任何依赖 README 导航的 agent 或人类读者都会找到幻影文件，降低可信度。

---

### 问题五：`templates/` 使用状态不明，可能是孤立资产

7 个模板文件没有被任何 agent 或 command 引用。不清楚是：

- A：仍在使用，但 agents 靠 hardcode 生成而非引用模板
- B：已被 doc-writer-agent 的内联生成完全取代
- C：遗留资产，已无人维护

如果是 B 或 C，模板内容与实际生成产物可能已经不一致。

---

## 三、当前调用关系图

```
agents（启动时强制读取）
    │
    ├──→ .claude/knowledge/methodology.md          [几乎所有 agents]
    ├──→ .claude/knowledge/pitfalls/common.md       [几乎所有 agents]
    ├──→ .claude/knowledge/pitfalls/r_reticulate.md [code-reviewer, problem-analyst]
    ├──→ .claude/knowledge/pitfalls/docker_r_bioconductor.md [problem-analyst]
    │
    └──→ .claude/knowledge/bioinformatics-tool-gpu-ification/references/benchmark_design.md
         ↑ 路径错误，文件不存在（bio-gpu-benchmark-agent）

skills/bioinformatics-tool-gpu-ification/
    └── references/*.md    [无 agent 正确引用]
    └── templates/*.md     [无 agent 引用]
    └── SKILL.md           [无调用入口]
```

---

## 四、问题优先级

| 优先级 | 问题 | 影响 |
|--------|------|------|
| P0 | benchmark-agent 路径错误（问题三） | benchmark 设计规范每次加载失败 |
| P1 | references/README.md 列出幻影文件（问题四） | 误导导航，降低可信度 |
| P2 | knowledge/ 与 references/ 内容重叠无分层说明（问题一） | agents 不知何时读详版 |
| P3 | SKILL 机制从未被利用（问题二） | skills/ 目录定位模糊 |
| P3 | templates/ 使用状态不明（问题五） | 可能是孤立资产 |
