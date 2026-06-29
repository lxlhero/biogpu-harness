# 执行环境踩坑

## 本地 macOS 替代集群执行（已发生，gsMap A 模式测试 2026-06-29）

**现象：** benchmark-agent 在未读取 CLAUDE.md rjob 规则的情况下，判断"可控小规模"等于"本地合成数据 + 本地 CPU 运行"。A1 → A3 → A6 → A8 全部在 macOS 本地跑完。module_test r=1.0 被误报为 GPU 精度验证通过。

**根因：**
- bio-gpu-benchmark-agent 的 Phase 2 缺乏强制执行环境约束
- agent 没有拦截"合成数据 + 本地运行"这个错误路径
- `GSMAP_DEVICE=gpu` 在无 CUDA 的 macOS 上 fallback 到 CPU，与 CPU baseline 完全一致（r=1.0），伪造了精度通过的假象

**后果：**
- 所有 profiling 数据无效（合成数据 500 spots，非生产规模）
- 所有精度数字无效（CPU vs CPU，不是 GPU vs CPU）
- 速度数据无效（本地 58s 与集群 H200 无关）
- A1-A8 全部需要从 A1 重做

**修复：**
- bio-gpu-benchmark-agent.md: 新增顶部 ⛔ 硬性规则，禁止本地运行、禁止合成数据、必须 rjob
- bio-gpu-profiling-agent.md: 新增顶部 ⛔ 硬性规则，禁止本地 profiling
- bio-gpu-test-runner-agent.md: 新增顶部 ⛔ 硬性规则，禁止本地 E2E 测试

**检查清单（每次 A 模式启动时）：**
- [ ] benchmark 数据在 GPFS，不在本地
- [ ] benchmark 运行通过 rjob 提交
- [ ] profiling 在集群 H200 节点上跑
- [ ] CPU baseline 通过 rjob 提交
- [ ] GPU compare 通过 rjob 提交，`GSMAP_DEVICE=gpu` 在真实 CUDA 环境下执行
- [ ] module_test Pearson r < 1.0（r=1.0 说明 CPU vs CPU，不是真实 GPU 测试）
