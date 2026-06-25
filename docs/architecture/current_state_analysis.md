# BioGPU-Harness 当前状态分析

> 最后更新：2026-06-25（覆盖两轮优化后状态）

---

## 一、整体定位

BioGPU-Harness 是生信工具 GPU 加速的**控制面**，分两层：

```
biogpu-harness/          ← 控制面（本仓库）：commands、agents、knowledge、skills、模板
transfer2gpu/<tool>/     ← 工具工作区：runtime artifacts、reports、runs、baseline
```

所有 runtime artifacts（runs/、reports/、baseline/、logs/）写入工具工作区，不写入 biogpu-harness。

---

## 二、完整项目结构（当前实际文件）

```
biogpu-harness/
├── CLAUDE.md                          ← 项目规则（路径、执行、飞书格式）
├── README.md                          ← 用户使用说明 + 资源层宪法摘要
├── harness_config.yaml                ← 控制面配置（版本、agent 列表）
│
├── .claude/
│   ├── commands/                      ← 用户入口（2 个正式 + 1 个废弃）
│   │   ├── bio-gpu-team.md            ← 唯一正式 orchestrator（含新启动向导）
│   │   ├── bio-gpu-project-init.md    ← 项目初始化向导（A 模式不问源码/精度）
│   │   └── gpu-team.md                ← deprecated redirect only
│   │
│   ├── agents/                        ← 13 个内部专职 agents
│   │   ├── bio-gpu-benchmark-agent.md          ← 新增：自动查找/下载/初始化工具源码
│   │   ├── bio-gpu-profiling-agent.md
│   │   ├── bio-gpu-feasibility-agent.md
│   │   ├── bio-gpu-test-planner-agent.md       ← 新增：自动判断精度指标
│   │   ├── bio-gpu-test-runner-agent.md        ← 明确：只执行 test_plan，不重设精度
│   │   ├── bio-gpu-code-planner-agent.md
│   │   ├── bio-gpu-dev-agent.md
│   │   ├── bio-gpu-code-reviewer-agent.md
│   │   ├── bio-gpu-module-tester-agent.md
│   │   ├── bio-gpu-image-builder-agent.md
│   │   ├── bio-gpu-existing-project-planner-agent.md  ← 新增：读 session_request 自动判断
│   │   ├── bio-gpu-problem-analyst-agent.md
│   │   └── bio-gpu-doc-writer-agent.md
│   │   （以上 13 个 agents 全部含 Resource Layer Policy）
│   │
│   └── knowledge/                     ← 运行时短规则（随身短手册）
│       ├── README.md                  ← 新增：知识库定位说明
│       ├── methodology.md             ← Amdahl + profiling + GPU 代码模式摘要
│       └── pitfalls/
│           ├── common.md
│           ├── docker_r_bioconductor.md
│           └── r_reticulate.md
│
├── skills/
│   └── bioinformatics-tool-gpu-skills/   ← 重命名（原 bioinformatics-tool-gpu-ification）
│       ├── SKILL.md                       ← 重写：明确是方法论图书馆，不是 orchestrator
│       ├── references/                    ← 11 个长方法论文档（按需读取）
│       │   ├── README.md                  ← 重写：清除幻影条目，加 Primary Consumers
│       │   ├── benchmark_design.md
│       │   ├── bioinformatics_gpu_patterns.md
│       │   ├── bottleneck_analysis.md
│       │   ├── common_failure_modes.md
│       │   ├── elbo-diagnostic-softmax.md
│       │   ├── gpu-precision-matching.md
│       │   ├── gpu_porting_principles.md
│       │   ├── gpu_suitability.md
│       │   ├── performance_metrics.md
│       │   ├── sigma2-trace-correction.md
│       │   └── validation_metrics.md
│       └── templates/                     ← 7 个报告/脚本模板（格式参考）
│           ├── README.md                  ← 重写：active/candidate 分类，补充 consumer
│           ├── benchmark_report.md
│           ├── e2e_comparison_report.md
│           ├── feasibility_report.md
│           ├── final_optimization_summary.md
│           ├── user_benchmark_report.md
│           ├── benchmark_real_data.py     ← candidate，待 scripts/ 就绪后迁移
│           └── e2e_checkpoint.sh          ← candidate，待 scripts/ 就绪后迁移
│
├── docs/
│   ├── architecture/
│   │   ├── current_state_analysis.md     ← 本文件
│   │   ├── resource_layer_constitution.md ← 新增：七层宪法，边界规则，文件归属判断树
│   │   ├── knowledge_skills_file_audit.md ← 新增：22 个文件审计表
│   │   └── workflow.md                   ← 新增：飞书格式全流程图 + 13 个 agent 介绍
│   │
│   ├── usage/
│   │   ├── quickstart.md                 ← 重写
│   │   ├── mode_a_from_scratch.md        ← 更新
│   │   ├── mode_b_existing_project.md    ← 更新
│   │   └── testing_flow.md               ← 更新
│   │
│   ├── optimize/
│   │   ├── optimize_20260625_1.md        ← 入口体验优化方案（已执行）
│   │   ├── optimize_20260625_2.md        ← 资源层重构优化方案（已执行）
│   │   └── knowledge_skill_analysis_20260625.md ← 问题分析报告
│   │
│   └── examples/
│       └── example_biogpu_project.yaml
│
├── templates/
│   ├── workspace/                        ← 工作区初始化骨架
│   │   ├── biogpu_project.yaml           ← 新增 source、precision 字段
│   │   ├── task_state.json               ← 新增 session_request 字段
│   │   ├── rjob_config.yaml
│   │   ├── resource_budget.yaml
│   │   ├── image_config.yaml
│   │   └── precision_config.yaml
│   └── reports/
│       └── README.md
│
└── scripts/
    └── README.md                         ← 占位，第二阶段实现工具脚本
```

---

## 三、已完成工具

| 工具 | 版本 | 状态 | E2E 精度 | E2E 加速 |
|------|------|------|---------|---------|
| susieR | v1.0 | 交付 | — | 已知局限：L=L_true + 真实 LD 数据下可能落入次优局部解 |
| gsMap | v1.8.3 | 交付 | — | — |
| scavenge | v1.1 | 交付 | Jaccard=0.9606 | E2E speedup=2.1×，模块 speedup=202× |

工具工作区：`/Users/huron/code/ai_lab/transfer2gpu/<tool_name>/`

---

## 四、本次已完成改进（2026-06-25 两轮优化）

### 优化一：入口体验（optimize_20260625_1.md）

| 类别 | 改进内容 |
|------|---------|
| 启动向导 | `/bio-gpu-team` 第一问工具名、第二问 A/B，不再第一步问模式 |
| A 模式 | 删除 5 个不必要问题：源码路径、CPU baseline、精度要求、rjob/Docker、加速倍数 |
| B 模式 | 不再推荐 `/bio-gpu-team /path/yaml` 启动方式；新增 session_request 向导 |
| bio-gpu-benchmark-agent | 新增自动查找/下载/初始化工具源码（A 模式 source.status=pending 时）|
| bio-gpu-test-planner-agent | 新增自动判断精度指标，不要求用户入口提供 precision requirement |
| bio-gpu-test-runner-agent | 明确只执行 test_plan，test_plan 缺 precision_metrics 时返回 blocked |
| bio-gpu-existing-project-planner-agent | 读 session_request 驱动，按 request_type 路由分析，自动判断工程细节 |
| biogpu_project.yaml 模板 | 新增 source（status/source_url/version/install_method）和 precision（policy/decided_by）字段 |
| task_state.json 模板 | 新增 session_request 字段（tool_name/mode/request_type/summary/allow_code_changes）|
| README.md | 改为纯用户使用说明，去掉内部架构细节 |

### 优化二：资源层重构（optimize_20260625_2.md）

| 类别 | 改进内容 |
|------|---------|
| 目录重命名 | `skills/bioinformatics-tool-gpu-ification` → `skills/bioinformatics-tool-gpu-skills` |
| 硬错误修复 | bio-gpu-benchmark-agent 断链路径已修复（`.claude/knowledge/bioinformatics...` → 正确路径）|
| 备份文件清理 | `SKILL.md.bak_20260624` 已删除 |
| 新增宪法文件 | `docs/architecture/resource_layer_constitution.md`（七层定位 + 边界规则）|
| 新增审计表 | `docs/architecture/knowledge_skills_file_audit.md`（22 个文件逐一标注决策）|
| knowledge/README.md | 新增，说明层定位和与 skills 的分工 |
| SKILL.md 重写 | 明确是图书馆不是 orchestrator，加入 Usage Policy（按需读取规则）|
| references/README.md 重写 | 清除 18 个幻影条目，只列实际存在的 11 个，补充 Primary Consumers |
| templates/README.md 重写 | active/candidate 分类，补充每个模板的 consumer |
| 13 agents 全部更新 | 各加 Resource Layer Policy（Always read / Read on demand / Never）|
| 2 commands 全部更新 | 各加 Resource Layer Policy（不读 skills 长方法论）|
| methodology.md 更新 | 顶部加指针，说明详版在 skills/references/|
| README.md 更新 | 新增资源层宪法摘要章节 |
| docs/architecture/workflow.md | 新增，飞书格式全流程图（含 13 个 agent 介绍、两种模式流程）|

---

## 五、与上次分析相比的结构变化

| 类别 | 上次（ef52a4f）| 现在 |
|------|-------------|------|
| skill 目录名 | `bioinformatics-tool-gpu-ification` | `bioinformatics-tool-gpu-skills` |
| knowledge 层定位 | 无说明 | 有 README，明确"随身短手册" |
| skills 层定位 | SKILL.md 定位模糊 | SKILL.md 重写，明确"方法论图书馆" |
| agents 读取规则 | 无统一规则 | 13 个全部有 Resource Layer Policy |
| references README | 列 29 个文件，18 个不存在 | 只列实际存在的 11 个 |
| 入口启动向导 | A/B 问题过多，包含工程细节 | 只问 4 个业务问题 |
| B 模式启动 | 需要传 yaml 路径 | 统一无参数启动 + session_request |
| biogpu_project.yaml | 无 source/precision 字段 | 有 source（status/install_method）和 precision（policy/decided_by）|
| 宪法文档 | 无 | resource_layer_constitution.md |
| 审计表 | 无 | knowledge_skills_file_audit.md（22 个文件）|
| 硬错误 | benchmark-agent 断链路径 | 已修复 |

---

## 六、当前已完成 vs 工程化缺口

### 已完成（控制面层面）

| 类别 | 内容 |
|------|------|
| 入口体验 | 向导简化、A/B 模式分工清晰、session_request 机制 |
| 资源层架构 | 七层宪法、knowledge/skills 分工明确、全文件审计 |
| Agent 职责边界 | 13 个 agents 全部有 Resource Layer Policy，读取规则清晰 |
| 精度判断机制 | test-planner 负责自动判断，test-runner 只执行 |
| 源码获取机制 | benchmark-agent 负责自动查找/下载（A 模式）|
| B 模式路由 | existing-project-planner 按 session_request 自动判断，不问用户工程细节 |
| 文档体系 | 宪法、审计表、工作流、用户手册均已建立 |

### 工程化缺口（尚未完成）

| 缺口 | 具体内容 | 影响 |
|------|---------|------|
| **工具脚本未实现** | `scripts/log_event.py`、`scripts/compare_precision.py`、`scripts/rjob_submit.py` | agents 指令中引用了这些脚本，实际运行时会失败；精度判断和日志记录无法自动化 |
| **Schema 校验缺失** | `biogpu_project.yaml` 和 `task_state.json` 无 JSON/YAML schema + validator | 字段写错时 agents 无法提前发现，静默失败风险高 |
| **Hooks 未实现** | 无 PostToolUse 等自动触发 hooks | task_state 更新全靠 agents 手动写，无自动化保障；断点恢复依赖 agent 自觉 |
| **CI 缺失** | 无结构完整性检查、agent 文件 lint、schema 验证 | harness 文件变更后无法自动验证一致性 |
| **session_request 写入未验证** | task_state.json 的 session_request 字段由 orchestrator 手动写入 | 格式不稳定，existing-project-planner 读到格式错误时无 fallback |
| **source 自动查找未实测** | bio-gpu-benchmark-agent 自动查找工具来源是新增职责 | 实际行为未在真实工具上验证，可能需要调整 |
| **templates 使用路径未闭合** | skills/templates/ 中的脚本模板（.py/.sh）无正式迁移到 scripts/ 的时间表 | 模板与实际 agent 生成产物的格式是否一致，无校验机制 |
| **Python package 化** | 无 `pip install biogpu-harness` | 无法作为依赖引入其他项目 |
| **Dashboard** | 无任务状态可视化 | 只能靠手动读 task_state.json 查进度 |
| **docs/examples 过时** | `example_biogpu_project.yaml` 未同步新增的 source/precision 字段 | 新用户参考示例时看到的是旧格式 |

---

## 七、最高优先级（下一步第一步）

按阻塞程度排序：

**P0（影响实际运行）**

1. `scripts/log_event.py` 和 `scripts/compare_precision.py`
   - 所有 agents 引用这两个脚本
   - 未实现则日志记录和精度自动判断均失败
   - 建议路径：`biogpu-harness/scripts/`

2. `session_request` 写入格式验证
   - B 模式核心数据链路
   - orchestrator 写入格式无约束，existing-project-planner 读取可能失败

**P1（影响可靠性）**

3. YAML/JSON Schema 定义 + 校验脚本
   - `biogpu_project.yaml` 和 `task_state.json` 各缺一份 schema
   - 可复用现有 `jsonschema` / `pydantic` 工具

4. `docs/examples/example_biogpu_project.yaml` 同步新字段
   - 低成本，直接更新即可

**P2（影响工程质量）**

5. Hooks（PostToolUse task_state 自动更新）
6. CI（harness 结构完整性检查）
7. scripts/templates/ 迁移（脚本模板移出 skills/templates/）
