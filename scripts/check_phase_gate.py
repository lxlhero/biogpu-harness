#!/usr/bin/env python3
"""
A 模式阶段顺序 Gate 检查器。

验证 task_state.json 中的 next_action 是否满足前置条件。
被 validate_task_state.py 调用，也可以作为 PreToolUse hook 使用。

退出码：
  0 = 通过
  1 = 违反顺序约束（FAIL，阻断执行）
"""

import json
import os
import sys

# ── A 模式状态机转换表 ────────────────────────────────────────────────────────
# key:   next_action（想进入的动作）
# value: 前置条件列表，每条是一个 dict，所有条件必须全部满足
#
# 条件字段：
#   current_step_in:  current_step 必须在此集合中
#   file_must_exist:  相对于 workspace 的路径，必须存在
#   state_field:      task_state 中某字段的断言 {field: value}
#   description:      人类可读的前置说明（用于报错信息）

A_MODE_GATES = {
    # A2: L1 镜像构建 — 需要 benchmark 已就绪且数据在 GPFS
    "build_l1_image": [
        {
            "current_step_in": {"benchmark_ready", "project_initialized"},
            "state_field": {"tests.primary_e2e.status": "benchmark_ready"},
            "description": "benchmark 未就绪，无法构建 L1 镜像",
        }
    ],

    # A3: profiling — 需要 L1 镜像已构建
    "run_profiling": [
        {
            "current_step_in": {
                "benchmark_ready", "l1_image_built", "project_initialized"
            },
            "state_field_not_null": "base_image",
            "description": "L1 镜像未构建（base_image 为 null），无法提交 profiling rjob",
        }
    ],

    # feasibility — 需要 profiling 完成
    "assess_feasibility": [
        {
            "current_step_in": {"profiling_done"},
            "file_must_exist": "reports/profiling_report.md",
            "description": "profiling 未完成，无法评估 feasibility",
        }
    ],

    # test_plan — 需要 feasibility 完成
    "plan_primary_e2e": [
        {
            "current_step_in": {"feasibility_done"},
            "file_must_exist": "reports/feasibility_report.md",
            "description": "feasibility 未完成，无法制定 test_plan",
        }
    ],

    # CPU baseline — 需要 test_plan 已批准
    "run_primary_cpu_baseline": [
        {
            "current_step_in": {"test_plan_drafted"},
            "state_field": {"tests.primary_e2e.approved": True},
            "file_must_exist": "reports/test_plans/primary_e2e_test_plan.md",
            "description": "test_plan 未生成或未批准，无法跑 CPU baseline",
        }
    ],

    # GPU 实现规划 — 需要 CPU baseline 完成 AND feasibility 完成
    # 最关键的门：禁止在 profiling 之前写 GPU 代码
    "plan_gpu_implementation": [
        {
            "current_step_in": {"cpu_baseline_done"},
            "file_must_exist": "reports/feasibility_report.md",
            "file_must_exist_2": "baseline/primary_e2e",
            "description": (
                "GPU 实现规划必须在 CPU baseline 完成且 feasibility 分析完成之后。"
                " profiling → feasibility → test_plan → cpu_baseline → plan_gpu_implementation"
            ),
        }
    ],

    # GPU 开发 — 需要 implementation_plan 存在
    "implement_gpu_module": [
        {
            "current_step_in": {"gpu_plan_done"},
            "file_must_exist": "reports/implementation_plan.md",
            "description": "implementation_plan 未生成，无法开始 GPU 开发",
        }
    ],

    # Code review — 需要 GPU 代码已实现
    "review_gpu_code": [
        {
            "current_step_in": {"gpu_implemented"},
            "description": "GPU 代码未实现，无法 review",
        }
    ],

    # Module test — 需要 code review 通过
    "run_module_test": [
        {
            "current_step_in": {"code_reviewed"},
            "description": "code review 未完成，无法做 module test",
        }
    ],

    # L2 镜像构建 — 需要 module test PASS
    "build_l2_image": [
        {
            "current_step_in": {"module_test_passed"},
            "file_must_exist": "artifacts/module_test_report.json",
            "description": "module test 未通过，无法构建 L2 镜像",
        }
    ],

    # primary_e2e GPU compare — 需要 L2 镜像已构建 + CPU baseline 存在
    "run_primary_gpu_compare": [
        {
            "current_step_in": {"l2_image_built", "module_test_passed"},
            "state_field_not_null": "dev_image",
            "file_must_exist": "baseline/primary_e2e",
            "description": "L2 镜像未构建或 CPU baseline 不存在，无法跑 GPU compare",
        }
    ],
}

# B 模式不做强制顺序检查（由 existing-project-planner 负责）
B_MODE_BYPASS = {
    "plan_existing_project", "load_execution_plan",
    "diagnose_failure", "write_final_report",
    "done", "blocked", "manual_review",
}


def _get_nested(d: dict, dotted_key: str):
    """Get nested dict value via 'a.b.c' notation."""
    parts = dotted_key.split(".")
    cur = d
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
    return cur


def check_gate(state: dict, workspace: str) -> list[str]:
    """
    Return list of violation messages.
    Empty list = pass.
    """
    mode = state.get("mode")
    next_action = state.get("next_action")
    current_step = state.get("current_step") or ""

    if not next_action:
        return []

    # B mode and special actions bypass sequential gate
    if mode == "B" or next_action in B_MODE_BYPASS:
        return []

    # Only enforce A mode gates
    if mode != "A":
        return []

    gates = A_MODE_GATES.get(next_action)
    if not gates:
        return []  # no gate defined for this action

    violations = []
    for gate in gates:
        gate_violations = []

        # current_step check
        allowed_steps = gate.get("current_step_in")
        if allowed_steps and current_step not in allowed_steps:
            gate_violations.append(
                f"current_step='{current_step}' 不在允许集合 {sorted(allowed_steps)} 中"
            )

        # state field equality check
        sf = gate.get("state_field")
        if sf:
            for dotted_key, expected in sf.items():
                actual = _get_nested(state, dotted_key)
                if actual != expected:
                    gate_violations.append(
                        f"task_state.{dotted_key}={actual!r} (期望 {expected!r})"
                    )

        # state field not-null check
        sfnn = gate.get("state_field_not_null")
        if sfnn:
            actual = _get_nested(state, sfnn)
            if actual is None:
                gate_violations.append(
                    f"task_state.{sfnn} 为 null，前置步骤未完成"
                )

        # file existence checks
        for key in ("file_must_exist", "file_must_exist_2"):
            rel_path = gate.get(key)
            if rel_path:
                full_path = os.path.join(workspace, rel_path)
                if not os.path.exists(full_path):
                    gate_violations.append(
                        f"前置文件/目录不存在: {rel_path}"
                    )

        if gate_violations:
            desc = gate.get("description", "")
            violations.append(
                f"⛔ 阶段顺序违反 [{next_action}]: {desc}\n"
                + "\n".join(f"  - {v}" for v in gate_violations)
            )

    return violations


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Check A-mode phase gate")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--workspace", help="Path to workspace directory")
    group.add_argument("--state", help="Path to task_state.json")
    args = parser.parse_args()

    if args.workspace:
        state_path = os.path.join(args.workspace, "state", "task_state.json")
        workspace = args.workspace
    else:
        state_path = args.state
        workspace = os.path.dirname(os.path.dirname(args.state))

    try:
        with open(state_path) as f:
            state = json.load(f)
    except FileNotFoundError:
        out = {"status": "fail", "errors": [f"File not found: {state_path}"]}
        print(json.dumps(out, indent=2))
        sys.exit(1)
    except json.JSONDecodeError as e:
        out = {"status": "error", "errors": [f"Invalid JSON: {e}"]}
        print(json.dumps(out, indent=2))
        sys.exit(2)

    violations = check_gate(state, workspace)
    status = "pass" if not violations else "fail"
    out = {
        "status": status,
        "next_action": state.get("next_action"),
        "current_step": state.get("current_step"),
        "mode": state.get("mode"),
        "violations": violations,
        "errors": violations,
    }
    print(json.dumps(out, indent=2))
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()
