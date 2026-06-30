# BioGPU-Harness Project Rules

This repository is the control plane for BioGPU-Harness.

The official entrypoint is:

```text
/bio-gpu-team
```

Do not treat this repository as a specific bioinformatics tool workspace.

Specific tool workspaces live under:

```text
/Users/huron/code/ai_lab/transfer2gpu/<tool_name>
```

---

## 1. Repository Role

`biogpu-harness` is the control plane.

It contains:

```text
.claude/commands/
.claude/agents/
.claude/knowledge/
skills/
docs/
templates/
scripts/
harness_config.yaml
```

It must not contain runtime outputs from a specific GPU acceleration project.

Runtime outputs must go to:

```text
/Users/huron/code/ai_lab/transfer2gpu/<tool_name>/
```

---

## 2. Resource Layer Constitution

BioGPU-Harness uses strict directory roles.

| Directory                                | Role                                                             | Must Not Do                                                   |
| ---------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------- |
| `.claude/commands/`                      | User-facing entrypoints and orchestration                        | Do not perform specialist execution or store long methodology |
| `.claude/agents/`                        | Specialist execution roles                                       | Do not act as user entrypoints or duplicate long references   |
| `.claude/knowledge/`                     | Short runtime rules, checklists, and pitfalls                    | Do not store long methodology or report templates             |
| `skills/bioinformatics-tool-gpu-skills/` | Long-form methodology, references, and report templates          | Do not store runtime state, task_state, or hard per-run rules |
| `docs/`                                  | Human-facing documentation, architecture notes, and usage guides | Do not serve as mandatory runtime rules                       |
| `templates/`                             | Workspace initialization skeletons                               | Do not store actual project outputs                           |
| `scripts/`                               | Executable utilities and future validation helpers               | Do not store prompts or methodology                           |
| `transfer2gpu/<tool>/`                   | Specific tool workspace and runtime artifacts                    | Do not store harness control-plane files                      |

Core rules:

1. Commands only handle entrypoint, user interaction, mode selection, and routing.
2. Agents perform specialist execution.
3. Knowledge is the agents’ short runtime handbook.
4. Skills are the agents’ long-form methodology library.
5. Docs are for humans and must not be treated as runtime hard rules.
6. Runtime artifacts must be written only under `transfer2gpu/<tool>/`.
7. Any file without a clear role or consumer must be merged, internalized, moved, archived, or deleted.

Full resource-layer constitution:

```text
docs/architecture/resource_layer_constitution.md
```

---

## 3. Path Rules

1. `HARNESS_ROOT` is this repository:

```text
/Users/huron/code/ai_lab/biogpu-harness
```

2. `WORKSPACE_PATH` must come from `biogpu_project.yaml`.

3. `BIO_TOOL_PATH` must come from `biogpu_project.yaml`.

4. The following runtime directories must be under `WORKSPACE_PATH`:

```text
reports/
runs/
baseline/
logs/
benchmarks/
artifacts/
pitfalls/
state/
configs/
```

5. Do not write runtime artifacts into `HARNESS_ROOT`.

6. Only modify `HARNESS_ROOT` when updating:

```text
commands
agents
knowledge
skills
docs
templates
scripts
harness_config.yaml
CLAUDE.md
README.md
```

7. The old skill path is deprecated and must not be used:

```text
skills/bioinformatics-tool-gpu-ification/
```

8. The active skill path is:

```text
skills/bioinformatics-tool-gpu-skills/
```

9. The following path is invalid and must never be referenced:

```text
.claude/knowledge/bioinformatics-tool-gpu-ification/
```

---

## 4. Execution Rules

1. `/bio-gpu-team` is the only official orchestrator.
2. `/bio-gpu-project-init` is the project setup wizard.
3. `/gpu-team` is deprecated and must only redirect to `/bio-gpu-team` if kept.
4. A mode means from-scratch GPU acceleration.
5. B mode means continuing, repairing, or optimizing an existing GPU acceleration project.
6. `/bio-gpu-team` must first ask for the tool name.
7. `/bio-gpu-team` must then ask whether the task is A mode or B mode.
8. A mode must not ask the user for source code path by default.
9. A mode must not ask the user to define precision requirements at entry time.
10. B mode must ask for the existing workspace path and the current repair/optimization goal.
11. All agents must read `biogpu_project.yaml` and `state/task_state.json` before acting.
12. All test PASS claims require artifact evidence.
13. Detailed logs and reports must be written to files, not dumped into chat.
14. Long-form skill references must be read by specialist agents only on demand.
15. Commands must not directly load long-form methodology from `skills/`.

---

## 5. Agent Resource Rules

Every agent must follow this resource policy:

```text
Always read:
- biogpu_project.yaml
- state/task_state.json
- the runtime knowledge files required by the agent role

Read on demand:
- skills/bioinformatics-tool-gpu-skills/references/
- skills/bioinformatics-tool-gpu-skills/templates/
```

Agents must not:

1. Read all skill references by default.
2. Copy long-form reference content into agent prompts.
3. Use deprecated skill paths.
4. Write runtime outputs into `HARNESS_ROOT`.
5. Claim PASS without report artifacts.
6. Invent precision metrics during execution if a test plan already exists.

---

## 6. Precision Policy

Precision requirements are not collected from the user at entry time.

Precision metrics must be selected by:

```text
bio-gpu-test-planner-agent
```

The planner must infer precision metrics from:

```text
tool output type
CPU baseline output
deterministic vs stochastic behavior
numerical vs set/ranking/matrix/statistical output
domain-specific validation needs
```

The selected metrics and thresholds must be written to:

```text
reports/test_plans/<test_suite>_test_plan.md
```

and must include rationale.

The following thresholds are default reference thresholds only.
They are not universal hard rules.
The final threshold must be justified in the test plan.

| Output Type                                   | Default Reference Threshold |
| --------------------------------------------- | --------------------------- |
| Continuous scores, PIP, LD score, beta, etc.  | Pearson r > 0.99            |
| p-values                                      | Pearson r > 0.999           |
| Variance parameters, sigma², h²               | ratio ∈ (0.99, 1.01)        |
| Credible sets / significant sets, CS, QTL set | Jaccard > 0.95              |
| Binary classification results                 | F1 > 0.95                   |

If the output type does not fit this table, the test planner must define an appropriate metric and explain why.

---

## 7. Report Format Rules

All content written to:

```text
reports/final_report.md
```

must follow these formatting rules:

* Bash commands must use fenced code blocks with `bash`.
* R and Python code must use fenced code blocks with the corresponding language.
* Major section separator:

```text
═══ 标题 ═══
```

* Subsection separator:

```text
── 标题 ──────
```

* Tables must use standard Markdown pipe table format.
* Do not use four-space indentation as a replacement for code blocks.
* Do not write multi-line bash commands directly in normal prose.

---

## 8. rjob Rules

**rjob must be submitted from the development machine shell** (not local macOS).

Development machine SSH:

```bash
ssh -CAXY huron-dev-1.liangxiuliang+root.ailab-ma4agismall.ws@h.pjlab.org.cn
```

If rjob reports `brainpp only work in kubebrain environment`, run first:

```bash
source /etc/profile.d/ssh-init.sh
```

**All rjob submissions must use inline bash — never execute a shell script file.**

The command to run must be written directly inside `-- bash -c '...'`, not via `-- bash /path/to/script.sh`. If the command is long, write it inline with line continuations (`\`). Scripts on GPFS cannot be trusted to exist or be up to date; inline commands are the single source of truth.

All rjob submissions must use inline bash:

```bash
rjob submit \
  --namespace=ailab-ma4agismall \
  --private-machine=group \
  --charged-group=ma4agismall_gpu \
  --mount=gpfs://gpfs2/liangxiuliang-2:/mnt/shared-storage-gpfs2/liangxiuliang-2 \
  -- bash -c '...'
```

GPFS mount: `gpfs://gpfs2/liangxiuliang-2` → `/mnt/shared-storage-gpfs2/liangxiuliang-2`

rjob outputs must be written to GPFS (container local storage is lost on job end):

```text
/mnt/shared-storage-gpfs2/liangxiuliang-2/<tool>/runs/<step>/<timestamp>/
```

Full rjob reference: `.claude/knowledge/rjob_cluster.md`

If this repository is made public or shared outside the team, move cluster-specific values into a local, gitignored config file and keep only variable names in `CLAUDE.md`.

---

## 9. Final Safety Rules

1. Do not modify real tool workspaces unless the active `biogpu_project.yaml` points to that workspace.
2. Do not delete existing reports, runs, baselines, or artifacts unless explicitly instructed.
3. Do not overwrite B-mode project history when repairing or optimizing an existing project.
4. Do not silently change precision criteria after a test plan has been approved.
5. Do not claim speedup from module-level timing alone; end-to-end timing must be reported separately.
6. Do not claim success without both precision evidence and runtime evidence.
