# BioGPU-Harness Project Rules

This repository is the control plane for BioGPU-Harness.

The official entrypoint is:

```
/bio-gpu-team
```

Do not treat this repository as a specific bioinformatics tool workspace.

Specific tool workspaces live under:

```
/Users/huron/code/ai_lab/transfer2gpu/<tool_name>
```

## Path Rules

1. HARNESS_ROOT is this repository (`/Users/huron/code/ai_lab/biogpu-harness`).
2. WORKSPACE_PATH must come from `biogpu_project.yaml`.
3. BIO_TOOL_PATH must come from `biogpu_project.yaml`.
4. reports / runs / baseline / logs must be written to WORKSPACE_PATH.
5. Do not write runtime artifacts into HARNESS_ROOT.
6. Only modify HARNESS_ROOT when updating commands, agents, knowledge, docs, templates, or harness config.

## Execution Rules

1. Commands are user-facing entrypoints.
2. Agents are internal specialist roles.
3. `/bio-gpu-team` is the only official orchestrator.
4. `/bio-gpu-project-init` is the project setup wizard.
5. A mode means from-scratch GPU acceleration.
6. B mode means continuing, repairing, or optimizing an existing GPU acceleration project.
7. All agents must read `biogpu_project.yaml` and `task_state.json` before acting.
8. All test PASS claims require artifact evidence.
9. Detailed logs and reports must be written to files, not dumped into chat.
10. `/gpu-team` is deprecated and must only redirect to `/bio-gpu-team` if kept.

## 飞书报告格式规范

所有写入 `reports/final_report.md` 的内容必须遵守以下格式规则：

- bash 命令使用 ` ```bash ` 代码块
- R / Python 代码使用对应语言代码块
- 章节分隔：`═══ 标题 ═══`（全角等号）
- 小节分隔：`── 标题 ──────`（全角破折号）
- 表格：标准 Markdown `| col |` 格式
- 禁止用纯缩进（4 空格）代替代码块
- 禁止在正文中裸写多行 bash 命令

## rjob 铁律

- 所有 rjob 提交一律 bash 内联（`rjob submit -- bash -c '...'`）
- 必带参数：
  ```
  --namespace ailab-ma4agismall
  --private-machine=group
  --charged-group=ma4agismall_gpu
  --mount=gpfs://gpfs2/liangxiuliang-2:/mnt/shared-storage-gpfs2/liangxiuliang-2
  ```
- SSH 地址：`huron-dev-1.liangxiuliang+root.ailab-ma4agismall.ws@h.pjlab.org.cn`
- rjob 输出写入：`runs/<step>/<module>/attempt_<N>/<rjob_id>/`

## 精度阈值

| 输出类型 | 阈值 |
|---------|------|
| 连续评分（PIP、LD score、beta 等）| Pearson r > 0.99 |
| p 值 | Pearson r > 0.999 |
| 方差参数（sigma²、h²）| ratio ∈ (0.99, 1.01) |
| 可信集 / 显著集合（CS、QTL set）| Jaccard > 0.95 |
| 二进制分类结果 | F1 > 0.95 |
