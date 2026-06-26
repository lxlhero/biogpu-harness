═══════════════════════════════════════════════════════════════════
  BioGPU-Harness Workflow
═══════════════════════════════════════════════════════════════════

本文描述系统控制流、数据流与所有 agent 职责。
详细角色定义见 `gpu_agent_team.md`，当前状态见 `current_state_analysis.md`。


═══ 一、系统层次 ═══

```
用户
  │  /bio-gpu-team <tool> A|B "<需求>"
  ▼
orchestrator（单主控，读 biogpu_project.yaml + task_state.json）
  │  按 next_action 加载 agent 指令，在同一 LLM 实例内执行
  ▼
bio-gpu-* agents（专职角色）
  │
  ▼
rjob / docker（异步，提交后停下）
  │
  ▼
集群 / registry（外部资源）
```

orchestrator 是唯一执行主体。"角色切换"仅意味着加载不同指令集，不创建新 LLM 实例。


═══ 二、Agent 一览 ═══

── 2.1 orchestrator ──────────────────────────────────────────────

**entrypoint：** `/bio-gpu-team`

读取 `biogpu_project.yaml` 和 `task_state.json`，按 `next_action` 字段路由到对应 agent，执行完毕后更新状态并决定下一步。全程不依赖对话记忆，每次醒来独立读 state。

── 2.2 bio-gpu-benchmark ─────────────────────────────────────────

**描述：** 分析私有/公开数据并构建 `profiling` 和 `primary_e2e` 两类 benchmark。

**触发时机：** Step 1，与 logging 并行启动。

**输入：** 用户数据路径（来自 `biogpu_project.yaml`）。

**输出：** `benchmarks/profiling/`、`benchmarks/e2e/`、数据分析报告。

**约束：** profiling 数据集与 E2E 数据集必须独立；仅有一份数据时 8:2 划分并在报告中注明。

── 2.3 bio-gpu-profiling ─────────────────────────────────────────

**描述：** 运行 profiling 找热点模块，用 Amdahl's Law 判断是否值得 GPU 化。

**触发时机：** Step 3。

**输入：** `benchmarks/profiling/`、工具源码。

**输出：** `reports/profiling_report.md`（热点模块列表 + Amdahl 判断）。

**约束：** E2E 占比 < 10% 的模块直接过滤；预期 E2E speedup < 1.15× 时终止整个流程。

── 2.4 bio-gpu-feasibility ───────────────────────────────────────

**描述：** 评估热点模块的 GPU 化方案和预估加速倍数。

**触发时机：** Step 3，由 profiling 调用。

**输入：** 热点模块代码列表、`profiling_report.md`。

**输出：** `reports/feasibility_report.md`（结构化表格：模块 / 方案 / 预估加速 / 精度风险 / 优先级）。

**约束：** 纯分析，不写可运行代码，不做 Yes/No 可行性判断。

── 2.5 bio-gpu-test-planner ──────────────────────────────────────

**描述：** 生成 E2E 测试计划（`primary_e2e` 或 `double_check_e2e`），产出可审计的测试规格文档。

**触发时机：** Step 4.0（CPU baseline 前）；Step 7.5.2（用户 benchmark 前）。

**输入：** `benchmarks/e2e/`、`profiling_report.md`、`feasibility_report.md`、`precision_config.yaml`。

**输出：** `reports/test_plans/<suite>_test_plan.md`（benchmark 信息 / CPU 命令 / GPU 命令 / 精度指标 / 输出路径全部写明）、`benchmarks/e2e/input_manifest.yaml`。

**约束：** 只负责规划，不执行测试；禁止提交 rjob、修改源码、修改精度阈值、覆盖 baseline。

── 2.6 bio-gpu-test-runner ───────────────────────────────────────

**描述：** 按已批准的测试计划跑 CPU/GPU E2E 测试并输出机器可读结果。

**触发时机：** Step 4.2（CPU baseline）；Step 7（GPU E2E 对比）；Step 7.5.4–7.5.6（用户 benchmark）。

**输入：** `test_plans/<suite>_test_plan.md`（必须存在且 `approved=true`）、对应镜像。

**输出：** `baseline/cpu_e2e_result/`（Step 4）；精度速度对比结果（Step 7）；`user_benchmarks/benchmark_001/`（Step 7.5）。

**约束：** 前置检查 plan 存在且已批准，否则立即 FAIL（`plan_missing` / `plan_not_approved`）。

── 2.7 bio-gpu-code-planner ──────────────────────────────────────

**描述：** 将可行性方案翻译为可执行的实现规格，输出 bio-gpu-dev 必须遵循的 implementation_plan。

**触发时机：** Step 4.5，每个候选模块执行一次。

**输入：** `feasibility_report.md`、热点模块完整 CPU 源码、`precision_config.yaml`。

**输出：** `reports/implementation_plan_<module>.md`（数值路径映射表 / 默认参数审计 / R↔Python 桥接接口 / 实现骨架 pseudocode）；更新 `task_state.planner_precision_risk`。

**约束：** 不写可运行代码；`precision_risk=high` 时触发 Human Approval Gate；禁止提交 rjob。

── 2.8 bio-gpu-dev ───────────────────────────────────────────────

**描述：** 按 `implementation_plan` 编写 GPU kernel 代码并 debug。

**触发时机：** Step 5 开发循环，每次 `next_action=write_kernel` 时。

**输入：** `task_state`（`current_module` / `attempt` / `last_result`）、`implementation_plan_<module>.md`（必须先读）、`precision_config.yaml`。

**输出：** `src/<module>_gpu.py`，同步到 GPFS（调试期不重建镜像）。

**约束：** 不提交 rjob、不构建镜像、不修改 CPU baseline；如发现规格有误，先更新 implementation_plan 再实现。

── 2.9 bio-gpu-code-reviewer ────────────────────────────────────

**描述：** 静态审查 bio-gpu-dev 生成的 GPU kernel 代码，拦截明显 bug 再进集群测试。

**触发时机：** Step 5，kernel 写完后、提交集群前。

**输入：** kernel 文件、`.claude/knowledge/pitfalls/`。

**审核分级：**

| 级别 | 检查项 | 方式 |
|------|--------|------|
| P0 | 语法正确 | `ast.parse()` |
| P1 | 数值路径与 CPU 原版一致 | 参考 pitfalls/common.md |
| P2 | GPU 常见陷阱（diagonal / squeeze / sparse.mv） | 静态规则匹配 |
| P3 | `TOOL_DEVICE` 环境变量切换实现 | 代码检查 |
| P4 | 性能建议 | 非阻塞，仅供参考 |

**输出：** PASS → `next_action=submit_rjob`；FAIL → 打回 gpu-dev。

── 2.10 bio-gpu-module-tester ───────────────────────────────────

**描述：** 在集群上验证 GPU kernel 与原版输出的精度和速度对比。

**触发时机：** Step 5，code-reviewer PASS 后。

**输入：** kernel、`precision_config.yaml`（精度阈值，必须从文件读取）、benchmark 数据。

**输出：** `runs/step5/<module>/attempt_N/<rjob_id>/result.json`（PASS/FAIL + 精度值 + 耗时）。

**约束：** 使用 L1 base 镜像 + GPFS mount kernel（不重建镜像）；PASS 通知 profiling 取下一模块；FAIL 更新 `last_result.failure_type`。

── 2.11 bio-gpu-image-builder ───────────────────────────────────

**描述：** 构建 L1 base 镜像和 L2 GPU 镜像并推送到 registry。

**触发时机：** Step 2（L1）；Step 6（L2）；Step 7 PASS 后（tag v1.0）。

**输入：** `task_state`、`image_config.yaml`。

| 阶段 | 镜像内容 | 验证 |
|------|---------|------|
| L1 | 原工具 + CUDA/PyTorch 依赖 | smoke test |
| L2 | COPY 已验证 kernel（不 runtime patch） | 双模式 TOOL_DEVICE smoke |
| v1.0 | L2 正式 tag | Human Approval Gate |

── 2.12 bio-gpu-problem-analyst ─────────────────────────────────

**描述：** 根据失败信息追溯日志链，输出根因诊断和修复建议。

**触发时机：** 任意 agent 失败时由 orchestrator 自动路由。

**输入：** `last_result.failure_type`、`logs/events.jsonl`（决策链）、`.claude/knowledge/pitfalls/`、`$WORKSPACE/pitfalls/<tool>.md`。

**输出：** `reports/last_failure.json`（根因 + 证据 + 修复建议 + 分配给哪个 agent）。

**约束：** 只诊断，不写代码，不提交 rjob，不修改配置。

── 2.13 bio-gpu-existing-project-planner ────────────────────────

**描述：** 扫描已有 GPU 加速项目现状，生成 `execution_plan.md` 供 orchestrator 路由（B 模式专用）。

**触发时机：** B 模式 Step B0–B1。

**输入：** `biogpu_project.yaml`（`mode=B`）、`task_state.json`、已有 `runs/` / `reports/` / `baseline/` / `logs/`。

**输出：** `reports/execution_plan.md`（目标 / 参与 agent / step 流转 / 预计产物 / 风险 / 回滚）。

**约束：** 必须先生成计划经用户确认（Human Approval Gate），禁止直接修改代码或提交 rjob。

── 2.14 bio-gpu-doc-writer ──────────────────────────────────────

**描述：** 生成飞书格式的用户文档和精度速度分析报告。

**触发时机：** Step 8（所有模块通过后）。

**输入：** `reports/`、`baseline/cpu_e2e_result/`、`user_benchmarks/`（如有）。

**输出：** `reports/final_report.md`，飞书格式四章节：

```
一、工具说明 — 工具名称、版本、用途、GPU 化适用场景
二、使用方式 — 镜像地址、环境要求、TOOL_DEVICE 切换命令、最小示例
三、热点改造说明 — 改前瓶颈（占 E2E %）、改造方案、模块级加速表
四、Benchmark 说明及端到端精度与速度 — 系统 E2E 结果；用户 benchmark（如有）
```

**约束：** 不写 Amdahl 推算过程、失败历史、模块内部实现细节。

── 2.15 bio-gpu-trace-analyst ───────────────────────────────────

**描述：** 用于多 agent workflow 的 trace / evidence / state 诊断。当 validator、gate、agent workflow 出现不一致时，由它读取 `trace_context.json`、`events.jsonl`、`task_state.json` 和 `reports/` 来定位断链点、归因责任 agent，并输出修复方案。

**与 problem-analyst-agent 的区别：**
- problem-analyst-agent 分析"任务为什么失败"（GPU 代码、精度、runtime 错误）
- trace-analyst-agent 分析"谁在什么时候把流程带偏了"（workflow 断链、artifact 缺失、state 异常）

**触发时机：** task_state 与 events 不一致；artifact 缺失但 agent 声称 pass；trace_id/span_id 链路断裂；precision 结果不可追溯来源时。

**输入：** `state/trace_context.json`、`logs/events.jsonl`、`state/task_state.json`、`reports/`。

**输出：** `reports/debug/trace_analysis_<timestamp>.md`（timeline + broken_links + suspect_agent + fix_plan）。


═══ 三、模式 A — 全流程 GPU 化 ═══

── 3.1 总览 ──────────────────────────────────────────────────────

| 步骤 | 主角 | 关键产物 |
|------|------|---------|
| Step 1 | benchmark + logging | `benchmarks/` |
| Step 2 | image-builder | L1 镜像 |
| Step 3 | profiling + feasibility | `profiling_report.md`、`feasibility_report.md` |
| Step 4.0 | test-planner | `primary_e2e_test_plan.md` |
| Step 4.1 | ⚠ Human Gate | — |
| Step 4.2 | test-runner | `baseline/cpu_e2e_result/` |
| Step 4.2 | ⚠ Human Gate | — |
| Step 4.5 | code-planner（逐模块） | `implementation_plan_<module>.md` |
| Step 5 | dev → reviewer → module-tester（循环） | `src/<module>_gpu.py`、`runs/step5/` |
| Step 6 | image-builder | L2 镜像 |
| Step 6 | ⚠ Human Gate | — |
| Step 7 | test-runner | GPU E2E 对比结果 |
| Step 7 | ⚠ Human Gate | v1.0 tag |
| Step 7.5 | test-planner + test-runner（可选） | `user_benchmarks/benchmark_001/` |
| Step 8 | doc-writer | `reports/final_report.md` |

── 3.2 Step 5 开发循环时序 ───────────────────────────────────────

```
orchestrator 读 task_state: next_action=plan_kernel
    │
    ▼  同一次调用内连续推进
code-planner → implementation_plan_<module>.md → next_action=write_kernel
    │  （precision_risk=high → ⚠ Human Gate → 等待用户确认）
    ▼
gpu-dev → src/<module>_gpu.py 同步 GPFS → next_action=review_kernel
    │
    ▼
code-reviewer → P0-P4 审核 → PASS → next_action=submit_rjob
    │
    ▼
rjob 提交集群 → next_action=wait_for_rjob:xxx
    │
    ▼  停下（异步等待）

── /loop 触发或 rjob 完成通知 ──

    ▼  恢复执行
读 task_state → 查 rjob 状态 → Succeeded
    │
    ▼
读 runs/step5/<module>/attempt_N/<rjob_id>/result.json
    ├── 精度 PASS → 取下一模块 → 循环
    └── 精度 FAIL → 打回 gpu-dev（attempt+1）
                   → retry > max → problem-analyst
```

── 3.3 Step 7.5 用户 benchmark 验收流程 ─────────────────────────

```
Step 7.5.0  orchestrator 展示系统 E2E 已用 benchmark 摘要
Step 7.5.1  询问用户是否提供不同 benchmark
                └── 否 → 直接进入 Step 8
Step 7.5.2  test-planner
                重复检查（与系统 E2E benchmark 对比）
                    └── 重复 → ⚠ Human Approval Gate
                完整性检查 + 生成 user_benchmark_test_plan.md
Step 7.5.3  ⚠ Human Approval Gate（用户 benchmark 测试计划确认）
Step 7.5.4  test-runner → CPU baseline → user_benchmarks/benchmark_001/cpu_result/
Step 7.5.5  test-runner → GPU 版本   → user_benchmarks/benchmark_001/gpu_result/
Step 7.5.6  精度 + 速度对比           → compare_result.json
Step 7.5.7  展示结果 → 用户确认是否纳入最终报告
```


═══ 四、模式 B — 已有项目修复 / 优化 / 验证 ═══

```
Step B0  orchestrator 扫描现状
         读 task_state / runs / reports / baseline / logs

Step B1  existing-project-planner
         生成 reports/execution_plan.md
         （目标 / 参与 agent / step 流转 / 预计产物 / 风险 / 回滚）

Step B2  ⚠ Human Approval Gate
         用户审核 execution_plan.md，approved=true 后继续

Step B3  按计划执行
         按需调用：problem-analyst / gpu-dev / code-reviewer /
         module-tester / test-runner / image-builder / doc-writer

Step B4  doc-writer（按需）
         更新飞书文档 / 修复报告 / benchmark 验收报告
```

**B 模式铁律：禁止在 execution_plan.md 审批前修改代码、提交 rjob 或构建镜像。**


═══ 五、数据流 ═══

```
用户数据路径
    │
    ▼
benchmark ──→ benchmarks/profiling/
           └─→ benchmarks/e2e/
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
    profiling             test-planner
         │                     │
         ▼                     ▼
  feasibility          primary_e2e_test_plan.md
         │                     │
         ▼                     ▼
  code-planner          test-runner (CPU baseline)
         │                     │
         ▼                     ▼
  implementation_plan   baseline/cpu_e2e_result/
         │
         ▼
      gpu-dev ──→ src/<module>_gpu.py
         │
         ▼
  code-reviewer (本地静态)
         │
         ▼
  module-tester ──→ runs/step5/<module>/attempt_N/
         │ 所有模块 PASS
         ▼
  image-builder ──→ L2 镜像 (v0.x)
         │
         ▼
  test-runner (GPU E2E) ──→ GPU vs CPU 对比
         │ PASS
         ▼
   [可选] user benchmark 验收
         │
         ▼
  doc-writer ──→ reports/final_report.md
```


═══ 六、任务推进机制 ═══

| 机制 | 说明 |
|------|------|
| 同步推进 | 写代码 / 审核 / 分析等本地步骤，orchestrator 在单次调用内连续执行 |
| 异步等待 | rjob / docker build 提交后停下，`next_action=wait_for_rjob:xxx` 记录断点 |
| 断点恢复 | orchestrator 每次醒来重读 `task_state.json`，不依赖对话记忆，可从任意断点继续 |
| 幂等路径 | `runs/step/module/attempt_N/rjob_id/` 唯一标识，历史结果不覆盖 |
| /loop 驱动 | rjob 等待期间可用 `/loop 3m /bio-gpu-team` 每 3 分钟自动轮询并推进 |


═══ 七、Human Approval Gate 触发点 ═══

| 步骤 | 触发原因 | task_state 字段 |
|------|---------|----------------|
| Step 4.1 | E2E 测试计划确认 | `tests.primary_e2e.approved` |
| Step 4.2 | 首次建立 CPU baseline | `human_approval_required=true` |
| Step 4.5 | code-planner 评估 `precision_risk=high` | `human_approval_required=true` |
| Step 6 | push L2 镜像 | `human_approval_required=true` |
| Step 7 | tag v1.0 / E2E speedup < 1.15× | `human_approval_required=true` |
| Step 7.5.3 | 用户 benchmark 测试计划确认 | `tests.double_check_e2e.approved` |
| Step 7.5（重复） | 用户 benchmark 与系统 E2E benchmark 重复 | `human_approval_required=true` |
| Step B2 | execution_plan.md 审批 | `execution_plan.user_approved` |

Gate 状态写入 `task_state.json`：

```json
{
  "human_approval_required": true,
  "approval_reason": "L2 image ready for E2E validation",
  "approved": false
}
```

将 `approved` 改为 `true` 后重新调用 `/bio-gpu-team` 继续。


═══ 八、失败路由 ═══

| failure_type | 路由 |
|-------------|------|
| `syntax_error` | → gpu-dev（本地修复） |
| `precision_mismatch` | → gpu-dev；连续 2 次 → problem-analyst |
| `plan_precision_risk_high` | → ⚠ Human Gate → 批准后继续 gpu-dev |
| `gpu_runtime_error` | → problem-analyst → gpu-dev |
| `rjob_starting_timeout` | 重提 rjob，不计入模块 retry |
| `oom` | module-tester 调整资源后重跑 |
| `image_build_failed` | → image-builder |
| `speed_regression` | 检查 Amdahl；必要时回 Step 3 |
| `E2E speedup < 1.15×` | → ⚠ Human Gate |
| `user_benchmark_duplicate` | → ⚠ Human Gate |
| `user_benchmark_precision_mismatch` | → problem-analyst → Step 5 |
| `user_benchmark_result_conflict` | → problem-analyst → ⚠ Human Gate |
| `plan_missing` / `plan_not_approved` | → test-planner |

完整路由表见 `gpu_agent_team.md` 第十三节。


═══ 九、配置与状态文件索引 ═══

| 文件 | 位置 | 用途 |
|------|------|------|
| `biogpu_project.yaml` | `WORKSPACE_PATH/` | 项目配置，harness 唯一配置来源 |
| `task_state.json` | `WORKSPACE_PATH/state/` | orchestrator 状态机（真相来源） |
| `precision_config.yaml` | `WORKSPACE_PATH/state/` | 精度阈值，所有判断从此读取 |
| `rjob_config.yaml` | `WORKSPACE_PATH/configs/` | 集群参数（namespace / mount / ssh） |
| `resource_budget.yaml` | `WORKSPACE_PATH/configs/` | GPU 小时数 / rjob 次数上限 |
| `image_config.yaml` | `WORKSPACE_PATH/configs/` | registry 前缀 / 镜像 tag 规则 |
| `harness_config.yaml` | `HARNESS_ROOT/` | 控制面版本与 agent 列表 |


═══ 十、铁律速查 ═══

| 编号 | 铁律 |
|------|------|
| 1 | 精度优先 — 先对齐精度，再提升速度 |
| 2 | E2E 必须用真实生物数据，smoke test 才允许合成数据 |
| 3 | profiling 数据集与 E2E 数据集必须独立 |
| 4 | 调试期 L1 base + GPFS mount，不重建镜像；通过后内化进 L2 |
| 5 | E2E speedup < 1.15× 时终止（Amdahl 15% 门槛） |
| 6 | v1.0 必须支持 `TOOL_DEVICE=gpu\|cpu` 切换 |
| 7 | B 模式必须先生成 execution_plan.md 经用户确认再执行 |
| 8 | 询问用户 benchmark 前必须展示系统 E2E 已用 benchmark 摘要 |
| 9 | 测试计划与执行分离：test-planner 先出计划并通过 Gate，test-runner 才执行 |
| 10 | 模块修复循环完成后，orchestrator 将根因写入对应 pitfall 文件 |
| 11 | Step 4 CPU baseline 与 Step 7 GPU E2E 必须使用同一份 `primary_e2e_test_plan.md` |
