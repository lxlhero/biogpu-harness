# scavenge B 模式真实回归测试方案

进入真实工具回归测试阶段。

本轮只测试已有 scavenge 项目的 B 模式回归，不做新工具 A 模式，不重新开发 GPU 代码，不重新构建镜像。

## 一、已知真实情况

工具工作区：

```text
/Users/huron/code/ai_lab/transfer2gpu/scavenge
```

已有 GPU 镜像：

```text
registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu/scavenge-gpu:v1.1
```

本轮目标不是重新加速 scavenge，而是验证 BioGPU-Harness 是否能正确接管已有真实项目，并完成一次真实工程回归。

---

## 二、任务模式

使用 `/bio-gpu-team` 的 B 模式。

本次 `session_request`：

```json
{
  "tool_name": "scavenge",
  "mode": "B",
  "request_type": "rerun_benchmark",
  "summary": "对已交付的 scavenge GPU 加速项目进行 BioGPU-Harness 真实回归测试，验证已有工作区、已有 GPU 镜像、配置状态、tracing、completion gate、precision evidence、speed evidence 和 final report 是否完整。",
  "user_notes": "已有 GPU 镜像：registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu/scavenge-gpu:v1.1。本轮不重建镜像，不修改 GPU 代码，优先读取已有 artifacts。",
  "allow_code_changes": false,
  "requires_execution_plan_approval": true
}
```

---

## 三、本轮禁止事项

本轮不要做：

```text
1. 不修改 scavenge GPU 代码。
2. 不重新构建 Docker/GPU 镜像。
3. 不重新设计大规模 benchmark。
4. 不删除已有 reports / runs / baseline / logs。
5. 不覆盖已有结果文件。
6. 不直接进入新工具 A 模式。
```

如需新增文件，只能新增 harness 回归相关报告、trace、logs 或 execution_plan。

---

## 四、优先读取已有信息

进入 scavenge workspace 后，先检查：

```text
biogpu_project.yaml
state/task_state.json
state/trace_context.json
logs/events.jsonl
reports/
runs/
baseline/
configs/
```

重点确认：

```text
1. biogpu_project.yaml 是否存在。
2. task_state.json 是否存在。
3. 现有 primary_e2e benchmark 是什么。
4. 现有 CPU baseline 是否存在。
5. 现有 GPU run 输出是否存在。
6. 现有 precision evidence 是否存在。
7. 现有 speed / runtime evidence 是否存在。
8. 现有 final report 是否存在。
9. scavenge GPU 镜像是否已经记录在配置或报告中。
```

如果 `biogpu_project.yaml` 里没有记录 GPU 镜像，可以补充到合适字段或新增 notes/config，但不要破坏 schema。

建议记录：

```yaml
image:
  gpu_image: registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu/scavenge-gpu:v1.1
  rebuild_required: false
```

如果当前 schema 不支持 `image` 字段，不要硬塞进 `biogpu_project.yaml`，可以写入：

```text
reports/scavenge_b_mode_regression_image_note.md
```

或者现有 image_config / rjob_config 中。

---

## 五、执行步骤

### Step 1：运行 validators

```bash
/Users/huron/miniconda3/envs/biogpu-harness/bin/python scripts/validate_biogpu_project.py \
  --workspace /Users/huron/code/ai_lab/transfer2gpu/scavenge

/Users/huron/miniconda3/envs/biogpu-harness/bin/python scripts/validate_task_state.py \
  --workspace /Users/huron/code/ai_lab/transfer2gpu/scavenge
```

如果失败，先不要继续跑 benchmark。
需要输出失败字段，并判断是否交给 `bio-gpu-trace-analyst-agent`。

---

### Step 2：初始化新的 trace_context

```bash
/Users/huron/miniconda3/envs/biogpu-harness/bin/python scripts/init_trace_context.py \
  --workspace /Users/huron/code/ai_lab/transfer2gpu/scavenge \
  --created-by bio-gpu-team
```

---

### Step 3：运行 project_init gate

```bash
/Users/huron/miniconda3/envs/biogpu-harness/bin/python scripts/check_completion_gate.py \
  --workspace /Users/huron/code/ai_lab/transfer2gpu/scavenge \
  --gate project_init
```

如果 fail，按 `recommended_next_agent` 路由。

---

### Step 4：检查已有 scavenge evidence

不要先重跑。先扫描已有结果：

```text
reports/test_plans/
reports/test_results/
reports/
runs/
baseline/
logs/events.jsonl
```

重点找：

```text
1. primary_e2e test plan
2. precision_config
3. CPU baseline 输出
4. GPU 输出
5. precision.json / precision.md
6. runtime / speedup report
7. final report
```

已知历史结果可作为参考：

```text
Jaccard = 0.9606
E2E speedup = 2.1x
module speedup = 202x
```

但必须以实际 workspace artifacts 为准，不要只凭记忆写入结论。

---

### Step 5：运行 primary_e2e gate

根据实际 test_suite 名称运行。
如果已有 test_suite 叫 `primary_e2e`：

```bash
/Users/huron/miniconda3/envs/biogpu-harness/bin/python scripts/check_completion_gate.py \
  --workspace /Users/huron/code/ai_lab/transfer2gpu/scavenge \
  --gate primary_e2e \
  --test-suite primary_e2e
```

如果 test_suite 名称不同，先从 `reports/test_plans/` 中识别实际名称。

---

### Step 6：必要时只做轻量 rerun

如果 artifacts 不完整，才考虑轻量 rerun。

轻量 rerun 原则：

```text
1. 使用已有 GPU 镜像：
   registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu/scavenge-gpu:v1.1

2. 不重建镜像。

3. 不改 GPU 代码。

4. 只补缺失 evidence，例如：
   - 缺 precision.json：重新调用 compare_precision.py
   - 缺 event log：补 log_event
   - 缺 test_plan precision_config：让 test-planner-agent 修 test_plan
   - 缺 speed evidence：只补已有 benchmark 的 runtime summary
```

---

### Step 7：如果 gate fail，调用 trace analyst

如果出现：

```text
artifact 缺失
event 和 artifact 不一致
task_state.next_action 不合理
precision evidence 缺失
final report 引用错误 evidence
```

则调用：

```text
bio-gpu-trace-analyst-agent
```

输出：

```text
reports/debug/trace_analysis_<timestamp>.md
```

---

## 六、最终输出报告

新增报告：

```text
reports/scavenge_b_mode_regression_report.md
```

报告包含：

```text
1. scavenge workspace 路径
2. 使用的 GPU 镜像
3. validators 结果
4. trace_context 结果
5. project_init gate 结果
6. primary_e2e gate 结果
7. precision evidence 是否完整
8. speed evidence 是否完整
9. 是否需要轻量 rerun
10. 是否调用 trace-analyst
11. 是否可作为真实工具回归样例
12. 修改文件列表
```

---

## 七、验收标准

本轮通过条件：

```text
1. 不修改 scavenge GPU 代码。
2. 不重建 GPU 镜像。
3. validators 至少能明确 pass 或给出可修复错误。
4. trace_context 能初始化。
5. project_init gate 能运行。
6. primary_e2e gate 能运行。
7. 能明确判断已有 precision / speed evidence 是否完整。
8. 如果 evidence 不完整，能正确路由到 trace-analyst 或对应 agent。
9. 输出 scavenge B 模式回归报告。
```

---

## 八、完成后输出

完成后请输出：

```text
1. 修改文件列表
2. scavenge biogpu_project.yaml 是否存在
3. task_state.json 是否存在
4. GPU 镜像是否已记录
5. validators 结果
6. trace_context 结果
7. project_init gate 结果
8. primary_e2e gate 结果
9. precision evidence 路径和结果
10. speed evidence 路径和结果
11. 是否需要 trace-analyst
12. scavenge 是否通过 B 模式真实回归
13. commit hash
```
