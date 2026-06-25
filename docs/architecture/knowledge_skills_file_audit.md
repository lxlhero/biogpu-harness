# Knowledge & Skills 文件审计表

> 审计日期：2026-06-25
> 覆盖范围：`.claude/knowledge/` 和 `skills/bioinformatics-tool-gpu-skills/`
> 宪法依据：`docs/architecture/resource_layer_constitution.md`

---

## 审计字段说明

| 字段 | 说明 |
|------|------|
| File | 文件路径 |
| Summary | 1-2 句话内容摘要 |
| Current Layer | 当前所在层 |
| Target Layer | 按宪法应该在哪里 |
| Consumers | 哪些 agents 或 commands 读取 |
| Problems | 重复、路径错误、无调用者、内容过长等 |
| Decision | keep / move / merge / internalize / delete / archive |
| Action | 具体处理方式 |
| Status | pending / done |

---

## `.claude/knowledge/` 审计

| File | Summary | Current Layer | Target Layer | Consumers | Problems | Decision | Action | Status |
|------|---------|---------------|--------------|-----------|----------|----------|--------|--------|
| `knowledge/methodology.md` | Amdahl's Law 公式、profiling 工具列表（Rprof/cProfile）、3 个 GPU 代码模式摘要 | knowledge | knowledge | 几乎所有 agents（启动时 always read）| 内容与 bottleneck_analysis.md + bioinformatics_gpu_patterns.md 重叠，但分工合理（摘要 vs 详版）；未说明与 skills 的关系 | keep + clarify | 在文件顶部加一句说明："详版见 skills/references/bottleneck_analysis.md 和 bioinformatics_gpu_patterns.md" | pending |
| `knowledge/pitfalls/common.md` | P1 数值路径对齐规则 + P2 GPU 常见 bug（torch.diag / squeeze / sparse.mv）| knowledge | knowledge | code-reviewer、dev-agent、module-tester、problem-analyst | 内容与 common_failure_modes.md 有重叠，但定位清晰（速查 vs 详版）；格式为 code-reviewer P1/P2 checklist，定位合理 | keep | 无需修改，保持现状 | done |
| `knowledge/pitfalls/docker_r_bioconductor.md` | Docker 构建 R/Bioconductor 版本匹配、BiocManager silent failure 检测方法 | knowledge | knowledge | image-builder、problem-analyst | 内容短、专注、有明确调用者；定位正确 | keep | 无需修改 | done |
| `knowledge/pitfalls/r_reticulate.md` | reticulate 数据传递规则、py_run_string 路径规则 | knowledge | knowledge | code-reviewer、dev-agent、problem-analyst | 内容短、专注、有明确调用者；定位正确 | keep | 无需修改 | done |

---

## `skills/bioinformatics-tool-gpu-skills/` 审计

### SKILL.md 和备份文件

| File | Summary | Current Layer | Target Layer | Consumers | Problems | Decision | Action | Status |
|------|---------|---------------|--------------|-----------|----------|----------|--------|--------|
| `SKILL.md` | 定位说明 + 方法论索引 | skills | skills | 人类读者；agents 不直接执行 | 已重写为新版（定位清晰、加入 Usage Policy）| keep | 已在本次优化中重写 | done |
| `SKILL.md.bak_20260624` | 旧版 SKILL.md 备份 | skills | docs/archive 或 delete | 无调用者 | 是过期备份，不应出现在 skills/ 目录下 | archive | 移到 docs/archive/ 或直接删除 | pending |

### references/ 文件

| File | Summary | Current Layer | Target Layer | Consumers | Problems | Decision | Action | Status |
|------|---------|---------------|--------------|-----------|----------|----------|--------|--------|
| `references/benchmark_design.md` | Benchmark 分层设计、真实数据要求、用户 benchmark 协议 | skills.references | skills.references | bio-gpu-benchmark-agent（按需）、bio-gpu-test-planner-agent（按需）| 定位正确；之前被 benchmark-agent 用错误路径引用（已修复）| keep | 路径已修复 | done |
| `references/bioinformatics_gpu_patterns.md` | 生信 GPU 代码模式详版（vectorize、sparse batch、BLAS、hybrid）| skills.references | skills.references | bio-gpu-feasibility-agent（按需）、bio-gpu-code-planner-agent（按需）| 定位正确；knowledge/methodology.md 有简版摘要，分工合理 | keep | 无需修改 | done |
| `references/bottleneck_analysis.md` | Amdahl 详版框架、bottleneck 识别方法论 | skills.references | skills.references | bio-gpu-profiling-agent（按需）、bio-gpu-existing-project-planner-agent（按需）| 定位正确；knowledge/methodology.md 有摘要，分工合理 | keep | 无需修改 | done |
| `references/common_failure_modes.md` | 15 种 GPU 化失败模式（症状/根因/缓解），英文长版 | skills.references | skills.references | bio-gpu-problem-analyst-agent（按需）、bio-gpu-code-reviewer-agent（按需）| 定位正确；pitfalls/common.md 是其中文速查子集，分工合理 | keep | 无需修改 | done |
| `references/elbo-diagnostic-softmax.md` | ELBO softmax 浓度异常 vs 数值 bug 的诊断方法 | skills.references | skills.references | 领域专项，按需读取 | 内容高度专项，只在特定工具（variational Bayes 类）需要时有价值；无通用调用者 | keep | 保留，标注 domain-specific | done |
| `references/gpu-precision-matching.md` | CPU/GPU 浮点精度对齐策略（scipy.gmean / torch 差异）| skills.references | skills.references | bio-gpu-test-planner-agent（按需）、bio-gpu-module-tester-agent（按需）| 定位正确 | keep | 无需修改 | done |
| `references/gpu_porting_principles.md` | GPU 移植哲学和决策准则（通用原则）| skills.references | skills.references | bio-gpu-feasibility-agent（按需）、bio-gpu-code-planner-agent（按需）| 定位正确 | keep | 无需修改 | done |
| `references/gpu_suitability.md` | GPU 适合 vs 不适合的操作决策表 | skills.references | skills.references | bio-gpu-feasibility-agent（按需）| 定位正确 | keep | 无需修改 | done |
| `references/performance_metrics.md` | E2E vs kernel speedup 度量方法定义 | skills.references | skills.references | bio-gpu-benchmark-agent（按需）、bio-gpu-test-runner-agent（按需）| 定位正确 | keep | 无需修改 | done |
| `references/sigma2-trace-correction.md` | Variational Bayes sigma² trace 修正方法 | skills.references | skills.references | 领域专项，按需读取 | 内容高度专项，只在特定工具需要时有价值 | keep | 保留，标注 domain-specific | done |
| `references/validation_metrics.md` | 各输出类型精度阈值选择指南 | skills.references | skills.references | bio-gpu-test-planner-agent（按需）| 定位正确 | keep | 无需修改 | done |

### templates/ 文件

| File | Summary | Current Layer | Target Layer | Consumers | Problems | Decision | Action | Status |
|------|---------|---------------|--------------|-----------|----------|----------|--------|--------|
| `templates/feasibility_report.md` | GPU 可行性报告模板（bottleneck evidence / Amdahl / go/no-go）| skills.templates | skills.templates | bio-gpu-feasibility-agent（按需）| 之前无调用者说明；已在 templates/README.md 明确 consumer | keep | 已在 README 补充 consumer 说明 | done |
| `templates/benchmark_report.md` | 模块级 benchmark 报告模板 | skills.templates | skills.templates | bio-gpu-benchmark-agent（按需）| 同上 | keep | 已在 README 补充 | done |
| `templates/e2e_comparison_report.md` | CPU vs GPU E2E 对比报告模板 | skills.templates | skills.templates | bio-gpu-test-runner-agent（按需）| 同上 | keep | 已在 README 补充 | done |
| `templates/user_benchmark_report.md` | 用户指定 benchmark 验收报告模板 | skills.templates | skills.templates | bio-gpu-test-runner-agent（按需）| 同上 | keep | 已在 README 补充 | done |
| `templates/final_optimization_summary.md` | 最终交付总结报告模板 | skills.templates | skills.templates | bio-gpu-doc-writer-agent（按需）| 同上 | keep | 已在 README 补充 | done |
| `templates/benchmark_real_data.py` | 真实数据 benchmark 准备脚本模板 | skills.templates | scripts/templates（待定）| 无明确当前调用者 | 是脚本模板，放在 skills/templates/ 定位略偏；待 scripts/ 目录建立后可迁移 | keep（暂时）| 标注为 candidate，待 scripts/ 目录就绪后迁移 | pending |
| `templates/e2e_checkpoint.sh` | 集群 checkpoint pipeline 脚本模板 | skills.templates | scripts/templates（待定）| 无明确当前调用者 | 同上 | keep（暂时）| 标注为 candidate，待 scripts/ 目录就绪后迁移 | pending |

---

## 决策统计

| Decision | 数量 | 文件 |
|---------|------|------|
| keep | 17 | 所有 knowledge 文件（4）、所有 references（11）、templates（5）、SKILL.md |
| keep（暂时）| 2 | benchmark_real_data.py、e2e_checkpoint.sh |
| archive | 1 | SKILL.md.bak_20260624 |
| delete | 0 | — |
| move | 0 | — |
| merge | 0 | — |

---

## 待处理项

| 优先级 | 文件 | 操作 |
|--------|------|------|
| P1 | `SKILL.md.bak_20260624` | 删除或移到 docs/archive/ |
| P2 | `knowledge/methodology.md` | 顶部加说明指向 skills 详版 |
| P3 | `templates/benchmark_real_data.py`、`e2e_checkpoint.sh` | scripts/ 目录就绪后迁移 |
