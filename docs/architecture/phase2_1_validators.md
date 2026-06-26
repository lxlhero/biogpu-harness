# Phase 2.1-A：Validators 实现文档

> 实现日期：2026-06-26
> 范围：`scripts/validate_biogpu_project.py` 和 `scripts/validate_task_state.py`

---

## 一、脚本概览

| 脚本 | 校验目标 | 退出码 |
|------|---------|--------|
| `validate_biogpu_project.py` | 工具工作区中的 `biogpu_project.yaml` | 0=pass / 1=fail / 2=error |
| `validate_task_state.py` | 工具工作区中的 `state/task_state.json` | 0=pass / 1=fail / 2=error |

---

## 二、validate_biogpu_project.py

### 接口

```bash
python scripts/validate_biogpu_project.py --workspace <workspace_path>
python scripts/validate_biogpu_project.py --project <yaml_path>
```

### 校验规则

#### 必须字段

```text
tool_name, mode
harness.root, harness.entrypoint, harness.version
paths.workspace_path, paths.bio_tool_path, paths.state_path
paths.reports_path, paths.runs_path, paths.benchmarks_path
paths.baseline_path, paths.logs_path, paths.artifacts_path
source.status, source.user_specified_source, source.source_url, source.version, source.install_method
user_request.summary, user_request.priority, user_request.speedup_target, user_request.notes
benchmarks.primary_e2e.status, benchmarks.double_check_e2e.status
precision.policy, precision.decided_by, precision.plan_path
```

#### 合法值

| 字段 | 合法值 |
|------|--------|
| `mode` | `A`, `B` |
| `harness.entrypoint` | `/bio-gpu-team` |
| `source.status` | `pending`, `ready`, `failed`, `user_provided` |
| `source.install_method` | `auto`, `git`, `github`, `gitcode`, `pip`, `conda`, `local`, `archive`, `unknown` |
| `precision.policy` | `auto`, `planned`, `approved`, `fixed` |

#### 路径规则

```text
workspace_path 不能等于 biogpu-harness 根目录
workspace_path 不能在 biogpu-harness 下面
bio_tool_path, reports_path, runs_path, benchmarks_path, baseline_path, logs_path, artifacts_path
  → 必须在 workspace_path 下
state_path → 必须在 workspace_path/state/ 下
```

### 输出格式

```json
{
  "status": "pass",
  "file": "/path/to/biogpu_project.yaml",
  "errors": [],
  "warnings": []
}
```

---

## 三、validate_task_state.py

### 接口

```bash
python scripts/validate_task_state.py --workspace <workspace_path>
python scripts/validate_task_state.py --state <json_path>
```

### 校验规则

#### 必须字段

```text
task_id, tool_name, mode
current_step, current_role, current_module
module_queue, attempt, max_attempts_per_module
next_action, last_result
human_approval_required, approval_reason, approved
tests.primary_e2e（含 11 个子字段）
tests.double_check_e2e（含 11 个子字段）
session_request
```

#### next_action 合法值

```text
initialize_project, run_benchmark, setup_source, build_l1_image, run_profiling,
assess_feasibility, plan_primary_e2e, run_primary_cpu_baseline, plan_gpu_implementation,
implement_gpu_module, review_gpu_code, run_module_test, diagnose_failure,
build_l2_image, run_primary_gpu_compare, ask_double_check, plan_double_check_e2e,
run_double_check_e2e, plan_existing_project, write_final_report,
done, blocked, manual_review, load_execution_plan
```

未知值直接 fail（exit 1）。

#### session_request 规则

| 条件 | 规则 |
|------|------|
| mode = A | session_request 可为 null |
| mode = B | session_request 不能为 null |
| mode = B | session_request.tool_name 不能为空 |
| mode = B | session_request.mode 必须是 "B" |
| mode = B | session_request.request_type 必须是合法值 |
| mode = B | session_request.summary 为空时输出 warning |

#### request_type 合法值

```text
from_scratch, fix_accuracy, fix_e2e_failure, fix_module_test_failure,
fix_runtime_error, fix_docker_or_rjob, optimize_speed, continue_next_module,
rerun_benchmark, run_double_check, write_final_report, other
```

### 输出格式

```json
{
  "status": "pass",
  "file": "/path/to/state/task_state.json",
  "errors": [],
  "warnings": []
}
```

---

## 四、Smoke Test 命令和结果

使用 dry-run workspace：`/Users/huron/code/ai_lab/transfer2gpu/_phase2_dryrun_tool`

### 正常用例（期望 PASS，exit 0）

```bash
python scripts/validate_biogpu_project.py --workspace /Users/huron/code/ai_lab/transfer2gpu/_phase2_dryrun_tool
python scripts/validate_task_state.py --workspace /Users/huron/code/ai_lab/transfer2gpu/_phase2_dryrun_tool
```

**validate_biogpu_project.py 结果：**

```json
{
  "status": "pass",
  "file": ".../_phase2_dryrun_tool/biogpu_project.yaml",
  "errors": [],
  "warnings": []
}
```

exit: 0

**validate_task_state.py 结果：**

```json
{
  "status": "pass",
  "file": ".../_phase2_dryrun_tool/state/task_state.json",
  "errors": [],
  "warnings": []
}
```

exit: 0

---

## 五、错误样例测试结果

### 样例 1：mode = C（biogpu_project.yaml）

```json
{
  "status": "fail",
  "errors": ["mode must be one of {'B', 'A'}, got: 'C'"],
  "warnings": []
}
```

exit: 1 ✓

### 样例 2：next_action = invalid_action（task_state.json）

```json
{
  "status": "fail",
  "errors": ["next_action 'invalid_action' is not a valid value; must be one of [...]"],
  "warnings": []
}
```

exit: 1 ✓

---

## 六、依赖

`validate_biogpu_project.py` 依赖 `PyYAML`：

```bash
pip install pyyaml
```

`validate_task_state.py` 仅使用标准库，无额外依赖。
