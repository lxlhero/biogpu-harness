# BioGPU-Harness 迁移方案

## 背景

原始 GPU 加速 agent team 分散在：
- `/Users/huron/code/ai_lab/.claude/commands/gpu-*.md`（18 个命令）
- `/Users/huron/code/ai_lab/.claude/knowledge/`（方法论和踩坑）
- `/Users/huron/code/ai_lab/huron_skills/skills/claude/bioinformatics-tool-gpu-ification/`（skill）

迁移目标：整合为独立项目 `biogpu-harness`，统一入口为 `/bio-gpu-team`。

## 主要变更

### 命名迁移

| 旧入口 | 新入口 |
|--------|--------|
| `/gpu-team` | `/bio-gpu-team`（主入口，废弃旧的） |
| `/gpu-project-init`（无） | `/bio-gpu-project-init`（新增） |

### Command → Agent 迁移

| 旧 command | 新 agent |
|-----------|---------|
| gpu-benchmark.md | bio-gpu-benchmark-agent.md |
| gpu-image-builder.md | bio-gpu-image-builder-agent.md |
| gpu-profiling.md | bio-gpu-profiling-agent.md |
| gpu-feasibility.md | bio-gpu-feasibility-agent.md |
| gpu-e2e-test-planner.md + gpu-user-benchmark-planner.md | bio-gpu-test-planner-agent.md（合并） |
| gpu-e2e-tester.md + gpu-user-benchmark-tester.md | bio-gpu-test-runner-agent.md（合并） |
| gpu-code-planner.md | bio-gpu-code-planner-agent.md |
| gpu-dev.md | bio-gpu-dev-agent.md |
| gpu-code-reviewer.md | bio-gpu-code-reviewer-agent.md |
| gpu-module-tester.md | bio-gpu-module-tester-agent.md |
| gpu-problem-analyst.md | bio-gpu-problem-analyst-agent.md |
| gpu-doc-writer.md | bio-gpu-doc-writer-agent.md |
| （无）| bio-gpu-existing-project-planner-agent.md（新增） |
| gpu-logging.md | 暂不 agent 化（后续改为 scripts/hooks） |
| gpu-rjob.md | 暂不 agent 化（后续改为 scripts/hooks） |

### 测试体系合并

原来 4 个测试 roles：
- gpu-e2e-test-planner.md
- gpu-e2e-tester.md
- gpu-user-benchmark-planner.md
- gpu-user-benchmark-tester.md

合并为 2 个 agents：
- bio-gpu-test-planner-agent（`test_suite` 参数区分）
- bio-gpu-test-runner-agent（`test_suite` + `run_stage` 参数区分）

### task_state.json 字段变更

旧字段（废弃）：
- `e2e_test_plan`
- `user_benchmark`

新字段：
- `tests.primary_e2e`
- `tests.double_check_e2e`

## 第二阶段（后续）

- Completed Gate hooks
- JSON/YAML schema validator
- rjob_submit.py / log_event.py 标准化脚本
- CI
- Python package 化
- dashboard
