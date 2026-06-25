# BioGPU-Harness 当前状态分析

## 项目结构

```
biogpu-harness/
├── CLAUDE.md                    ← 项目规则
├── README.md                    ← 项目说明
├── harness_config.yaml          ← 控制面配置
│
├── .claude/
│   ├── commands/
│   │   ├── bio-gpu-team.md      ← 主入口（唯一正式 orchestrator）
│   │   ├── bio-gpu-project-init.md ← 项目初始化向导
│   │   └── gpu-team.md          ← deprecated redirect
│   │
│   ├── agents/                  ← 13 个内部专职 agents
│   │   ├── bio-gpu-benchmark-agent.md
│   │   ├── bio-gpu-image-builder-agent.md
│   │   ├── bio-gpu-profiling-agent.md
│   │   ├── bio-gpu-feasibility-agent.md
│   │   ├── bio-gpu-test-planner-agent.md
│   │   ├── bio-gpu-test-runner-agent.md
│   │   ├── bio-gpu-code-planner-agent.md
│   │   ├── bio-gpu-dev-agent.md
│   │   ├── bio-gpu-code-reviewer-agent.md
│   │   ├── bio-gpu-module-tester-agent.md
│   │   ├── bio-gpu-existing-project-planner-agent.md
│   │   ├── bio-gpu-problem-analyst-agent.md
│   │   └── bio-gpu-doc-writer-agent.md
│   │
│   └── knowledge/               ← 方法论和踩坑知识库
│       ├── methodology.md
│       └── pitfalls/
│           ├── common.md
│           ├── docker_r_bioconductor.md
│           └── r_reticulate.md
│
└── skills/
    └── bioinformatics-tool-gpu-ification/  ← GPU 化方法论 skill
```

## 已完成的工具

| 工具 | 版本 | 状态 | E2E 加速 |
|------|------|------|---------|
| susieR | v1.0 | 交付 | 已知局限：L=L_true 时次优局部解 |
| gsMap | v1.8.3 | 交付 | - |
| scavenge | v1.1 | 交付 | E2E Jaccard=0.9606，speedup=2.1× |

## 工具工作区

各工具工作区在：`/Users/huron/code/ai_lab/transfer2gpu/<tool_name>/`

biogpu-harness 不存放工具的 runtime artifacts。
