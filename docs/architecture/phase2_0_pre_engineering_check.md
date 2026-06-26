# Phase 2.0 Pre-Engineering Check Report

> 生成日期：2026-06-26
> 目的：确认第一阶段控制面重构足够干净，可以进入 Phase 2.1 基础脚本实现。

---

## 一、本阶段修改文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `docs/examples/example_biogpu_project.yaml` | 重写 | 从 scavenge 特定示例替换为通用 example_tool 模板，补齐 `source` / `precision` 字段 |
| `templates/workspace/task_state.json` | 修改 | `session_request` 字段全部改为 null 默认值；`requires_execution_plan_approval` 从 false → true；`task_id`/`tool_name`/`mode` 顶层字段改为 null |
| `docs/architecture/knowledge_skills_file_audit.md` | 修改 | 新增 `knowledge/README.md` 行；`knowledge/methodology.md` 标为 done（已加跨引用）；`SKILL.md.bak` 标为 done（已删除）；决策统计和待处理项更新 |
| `transfer2gpu/_phase2_dryrun_tool/state/task_state.json` | 新建 | B 模式 dry-run session_request 验证文件 |

---

## 二、Step 1 — docs/examples/example_biogpu_project.yaml

**结论：已同步 source / precision**

原文件是 scavenge 特定配置（tool_name: scavenge），缺少 `source` 和 `precision` 字段。
已替换为通用 example_tool 配置，包含全部必须字段：

```text
source:
  status: pending
  user_specified_source: false
  source_url: null
  version: null
  install_method: auto

precision:
  policy: auto
  decided_by: bio-gpu-test-planner-agent
  plan_path: null
```

注：`session_request` 不属于 `biogpu_project.yaml`，未写入。

---

## 三、Step 2 — templates/workspace/biogpu_project.yaml

**结论：已包含所有必须字段，无需修改**

验证通过字段：

```text
✓ source（status: pending, install_method: auto）
✓ precision（policy: auto, decided_by: bio-gpu-test-planner-agent）
✓ benchmarks.primary_e2e
✓ benchmarks.double_check_e2e
✓ paths.workspace_path
✓ paths.bio_tool_path
✓ harness.entrypoint（/bio-gpu-team）
```

---

## 四、Step 2 — templates/workspace/task_state.json

**结论：已包含 session_request，已修复模板值**

修复内容：

```text
session_request.tool_name:   "example_tool" → null
session_request.mode:        "A"            → null
session_request.request_type: "from_scratch" → null
session_request.requires_execution_plan_approval: false → true
task_id:   "example_tool_20260625" → null
tool_name: "example_tool"          → null
mode:      "A"                     → null
```

其余字段（tests.primary_e2e、tests.double_check_e2e、next_action、current_step、current_role）均存在，验证通过。

---

## 五、Step 3 — 旧路径 grep 检查结果

**结论：active 文件中无旧路径引用，仅文档层提及**

```bash
grep -R "bioinformatics-tool-gpu-ification" -n \
  .claude README.md CLAUDE.md harness_config.yaml templates docs/usage docs/architecture skills
```

| 文件 | 类型 | 内容性质 | 是否问题 |
|------|------|----------|----------|
| `CLAUDE.md` 第 127 行 | 规则文档 | 说明"旧路径已废弃"的规则定义 | 无问题 |
| `CLAUDE.md` 第 139 行 | 规则文档 | 说明"此路径无效"的规则定义 | 无问题 |
| `.claude/agents/*.md`（13 个）| 禁止规则 | `- 不使用旧路径 skills/bioinformatics-tool-gpu-ification` | 无问题（约束规则）|
| `.claude/commands/*.md`（2 个）| 禁止规则 | `Do not use deprecated path: ...` | 无问题（约束规则）|
| `docs/architecture/current_state_analysis.md` | 历史文档 | 记录目录重命名历史 | 无问题 |

**判定：active 文件无旧路径引用。旧路径只出现在规则约束文本和历史文档中。**

---

## 六、Step 4 — Resource Layer Policy 检查结果

**结论：全部通过**

```bash
grep -L "Resource Layer Policy" .claude/agents/*.md   # 无结果
grep -L "Always read"           .claude/agents/*.md   # 无结果
grep -L "Read on demand"        .claude/agents/*.md   # 无结果
grep -L "Resource Layer Policy" .claude/commands/bio-gpu-team.md
                                .claude/commands/bio-gpu-project-init.md  # 无结果
```

13 个 agents 全部具备 `Resource Layer Policy` / `Always read` / `Read on demand` 三节。
2 个 commands 均具备 `Resource Layer Policy`。

---

## 七、Step 5 — references/README.md phantom file 检查

**结论：无 phantom files**

实际存在文件（11 个）：

```text
README.md
benchmark_design.md
bioinformatics_gpu_patterns.md
bottleneck_analysis.md
common_failure_modes.md
elbo-diagnostic-softmax.md
gpu-precision-matching.md
gpu_porting_principles.md
gpu_suitability.md
performance_metrics.md
sigma2-trace-correction.md
validation_metrics.md
```

README 中列出 11 个文件，与磁盘完全一致。无已列出但不存在的文件。

---

## 八、Step 6 — knowledge_skills_file_audit.md 覆盖文件数量

**结论：已覆盖所有 knowledge / skills 文件**

覆盖统计：

| 层 | 文件数 | 说明 |
|----|--------|------|
| `.claude/knowledge/` | 5 | README.md（新增）+ methodology.md + 3 pitfall 文件 |
| `skills/.../SKILL.md` | 1 | SKILL.md（已重写）|
| `skills/.../references/` | 11 | 全部覆盖 |
| `skills/.../templates/` | 7 | 5 md + 2 脚本模板 |
| 旧备份（已删）| 1 | SKILL.md.bak_20260624（status=done）|
| **合计** | **25** | — |

---

## 九、Step 7 — no consumer 文件清单和处理决策

所有无通用 consumer 的文件均有明确处理决策：

| 文件 | 性质 | 处理决策 |
|------|------|----------|
| `elbo-diagnostic-softmax.md` | domain-specific（variational Bayes 类工具专用）| keep，按需读取，标注 domain-specific |
| `sigma2-trace-correction.md` | domain-specific（variational Bayes 类工具专用）| keep，按需读取，标注 domain-specific |
| `templates/benchmark_real_data.py` | 脚本模板 candidate | keep（暂时），scripts/ 就绪后迁移 |
| `templates/e2e_checkpoint.sh` | 脚本模板 candidate | keep（暂时），scripts/ 就绪后迁移 |

无 `Consumers = none + Decision = keep`（无处理理由）的条目。

---

## 十、Step 8 — B 模式 session_request dry-run 结果

**结论：dry-run 成功写出合法 session_request**

临时工作区路径：

```text
/Users/huron/code/ai_lab/transfer2gpu/_phase2_dryrun_tool/
```

写入文件：

```text
/Users/huron/code/ai_lab/transfer2gpu/_phase2_dryrun_tool/state/task_state.json
```

session_request 内容：

```json
{
  "tool_name": "_phase2_dryrun_tool",
  "mode": "B",
  "request_type": "optimize_speed",
  "summary": "Dry-run only: verify B-mode session_request serialization before Phase 2.1.",
  "user_notes": "Do not run real benchmark or modify real tool code.",
  "allow_code_changes": false,
  "requires_execution_plan_approval": true
}
```

7 个必须字段全部存在：tool_name / mode / request_type / summary / user_notes / allow_code_changes / requires_execution_plan_approval。

**execution_plan.md**：B 模式 dry-run 仅验证 session_request 序列化，未调用 existing-project-planner，未生成 execution_plan.md。该文件将在真实 B 模式任务中由 bio-gpu-existing-project-planner-agent 生成。

**dry-run 约束确认：**
- 未运行真实 benchmark ✓
- 未下载真实源码 ✓
- 未提交 rjob ✓
- 未修改 susieR / gsMap / scavenge 工作区 ✓
- 仅在 _phase2_dryrun_tool 临时目录操作 ✓

---

## 十一、Step 9 — runtime artifact 写入规则检查

**结论：无违规写入**

```bash
find . -maxdepth 2 -type d \( \
  -name reports -o -name runs -o -name baseline -o -name logs -o -name artifacts \
\)
```

结果：

```text
./templates/reports   ← 允许（模板目录）
./.git/logs           ← git 内部目录，不计入
```

无 `./reports`、`./runs`、`./baseline`、`./logs`、`./artifacts` 非法目录。Phase 2.0 过程中未向 HARNESS_ROOT 写入 runtime artifacts。

---

## 十二、Phase 2.0 验收结论

| 验收项 | 结果 |
|--------|------|
| 1. active 文件无旧路径 bioinformatics-tool-gpu-ification | ✓ PASS |
| 2. active 文件无错误路径 .claude/knowledge/bioinformatics-tool-gpu | ✓ PASS |
| 3. example_biogpu_project.yaml 已同步 source / precision | ✓ PASS |
| 4. task_state.json 模板已有 session_request（null 默认值）| ✓ PASS |
| 5. 13 个 agents 全部有 Resource Layer Policy | ✓ PASS |
| 6. references/README.md 无 phantom files | ✓ PASS |
| 7. knowledge_skills_file_audit.md 覆盖所有文件 | ✓ PASS |
| 8. no consumer 文件都有处理决策 | ✓ PASS |
| 9. B 模式 dry-run 能写出 session_request | ✓ PASS |
| 10. 没有 runtime artifacts 写进 HARNESS_ROOT | ✓ PASS |

**Phase 2.0 通过。**

---

## 十三、建议 Phase 2.1 第一批任务

按优先级排列：

| 优先级 | 任务 | 说明 |
|--------|------|------|
| P1 | `scripts/validate_task_state.py` | 验证 task_state.json schema 合法性，agent 和 CI 双用 |
| P1 | `scripts/validate_biogpu_project.py` | 验证 biogpu_project.yaml 字段完整性 |
| P2 | `scripts/log_event.py` | 结构化事件日志，为 dashboard 和审计准备 |
| P2 | `scripts/compare_precision.py` | CPU/GPU 输出精度自动对比，支持多输出类型 |
| P3 | `scripts/rjob_submit.py` | rjob 提交封装，统一参数注入 |
| P4 | schema 定义（JSON Schema）| 为 validate_* 脚本提供 schema |
| P5 | CI hooks | 在 git commit 或 PR 时自动跑 validate_* |
