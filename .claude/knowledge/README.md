# BioGPU Runtime Knowledge

This directory contains short, high-frequency runtime knowledge for BioGPU-Harness agents.

It is intended to be read directly by agents during execution.

## What belongs here

- Runtime rules and hard constraints
- Short methodology digest（公式摘要、判断规则）
- Pitfall checklist（bug 速查）
- Failure quick diagnosis
- Reviewer / tester / problem-analyst 必查规则
- 直接影响 next_action 的判断规则

## What does not belong here

- Long-form methodology（长篇 GPU 化方法论 → skills/references/）
- Report templates（报告模板 → skills/templates/）
- Historical design documents（架构文档 → docs/architecture/）
- User documentation（用户说明 → docs/usage/）
- Runtime artifacts（运行结果 → transfer2gpu/<tool>/）

## Files

| File | Purpose | Consumers |
|------|---------|-----------|
| `methodology.md` | Amdahl's Law、profiling 方法、GPU 代码模式摘要 | 几乎所有 agents |
| `pitfalls/common.md` | GPU kernel 通用 bug checklist（P1 数值路径 / P2 GPU bug）| code-reviewer、dev、module-tester |
| `pitfalls/docker_r_bioconductor.md` | Docker/R/Bioconductor 构建坑 | image-builder、problem-analyst |
| `pitfalls/r_reticulate.md` | R-Python reticulate 桥接坑 | code-reviewer、dev、problem-analyst |

## Relationship to skills/

`knowledge/` 是 `skills/references/` 的摘要提炼版：

- `knowledge/methodology.md` 是 `bottleneck_analysis.md` + `bioinformatics_gpu_patterns.md` 的精简摘要
- `pitfalls/common.md` 是 `common_failure_modes.md` 的速查子集

当 runtime 短规则不够用时，agents 再按需读取对应 skills reference。
