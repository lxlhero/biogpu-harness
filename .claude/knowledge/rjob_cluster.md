# rjob 集群提交规范

## 提交方式

rjob 必须在**开发机 shell**中执行（`brainpp` 包安装后，kubebrain 环境）。

SSH 登录开发机：
```bash
ssh -CAXY huron-dev-1.liangxiuliang+root.ailab-ma4agismall.ws@h.pjlab.org.cn
```

登录后如果 rjob 报 `brainpp only work in kubebrain environment`，先执行：
```bash
source /etc/profile.d/ssh-init.sh
# 或
eval $(sudo strings /proc/1/environ | grep -v HOME | grep -v LS_COLORS | grep -v TERM | tr '\n' ' ')
```

安装/升级 rjob（开发机默认已安装）：
```bash
pip3 install -U brainpp
export PATH=$PATH:~/.local/bin/
```

---

## GPFS 挂载路径

| GPFS 源 | 容器内挂载 | 参数格式 |
|--------|---------|--------|
| `gpfs://gpfs2/liangxiuliang-2` | `/mnt/shared-storage-gpfs2/liangxiuliang-2` | `--mount=gpfs://gpfs2/liangxiuliang-2:/mnt/shared-storage-gpfs2/liangxiuliang-2` |

已确认的 GPFS 资源目录（挂载后路径）：

| 内容 | 路径 |
|------|------|
| gsMap 官方 tutorial ST 数据 | `/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/gsMap_example_data/ST/E16.5_E1S1.MOSTA.h5ad` |
| gsMap 官方 GWAS 数据 | `/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/gsMap_example_data/GWAS/IQ_NG_2018.sumstats.gz` |
| gsMap resource（完整 LD panel + baseline）| `/mnt/shared-storage-gpfs2/liangxiuliang-2/gsMap_resource/` |
| gsMap GPU 源码（历史工程）| `/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/gsMap/` |
| 历史 CPU E2E 脚本 | `/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/e2e_cpu_v18.sh` |
| 历史 GPU E2E 脚本（含精度对比）| `/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/e2e_gpu_v18.sh` |

---

## rjob submit 标准格式（单机单 GPU，gsMap 场景）

```bash
rjob submit \
  --name=gsmap-harness-a1 \
  --namespace=ailab-ma4agismall \
  --charged-group=ma4agismall_gpu \
  --private-machine=group \
  --gpu=1 \
  --cpu=16 \
  --memory=102400 \
  --image=<镜像地址> \
  --image-pull-policy=IfNotPresent \
  --mount=gpfs://gpfs2/liangxiuliang-2:/mnt/shared-storage-gpfs2/liangxiuliang-2 \
  -- bash -c '
    set -eo pipefail
    export PATH=/opt/conda/bin:$PATH
    export LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64:/usr/local/cuda/lib64:$LD_LIBRARY_PATH
    # 实际命令
  '
```

注意：
- `--name` 只能含小写字母、数字、`-`，不能含大写字母或下划线
- `--memory` 单位是 MiB（`102400` = 100 GB）
- GPU 任务必须加 `--private-machine=group`
- CUDA 库路径必须手动设置 `LD_LIBRARY_PATH`

---

## gsMap 专用提交示例

### CPU baseline（profiling / cpu_baseline）

```bash
rjob submit \
  --name=gsmap-cpu-baseline \
  --namespace=ailab-ma4agismall \
  --charged-group=ma4agismall_gpu \
  --private-machine=group \
  --gpu=1 \
  --cpu=32 \
  --memory=204800 \
  --image=<gsmap镜像> \
  --image-pull-policy=IfNotPresent \
  --mount=gpfs://gpfs2/liangxiuliang-2:/mnt/shared-storage-gpfs2/liangxiuliang-2 \
  -- bash -c '
    set -eo pipefail
    export PATH=/opt/conda/bin:$PATH
    GPFS=/mnt/shared-storage-gpfs2/liangxiuliang-2
    WORKDIR=$GPFS/gsmap/workdir_harness_cpu_$(date +%Y%m%d_%H%M%S)
    mkdir -p $WORKDIR
    GSMAP_DEVICE=cpu gsmap quick_mode \
      --workdir $WORKDIR \
      --sample_name E16.5_E1S1.MOSTA \
      --gsMap_resource_dir $GPFS/gsMap_resource \
      --hdf5_path $GPFS/gsmap/gsMap_example_data/ST/E16.5_E1S1.MOSTA.h5ad \
      --annotation annotation \
      --data_layer count \
      --sumstats_file $GPFS/gsmap/gsMap_example_data/GWAS/IQ_NG_2018.sumstats.gz \
      --trait_name IQ_NG_2018 \
      --max_processes 16
  '
```

### GPU E2E + CPU 精度对比（参考历史脚本）

```bash
rjob submit \
  --name=gsmap-gpu-e2e \
  --namespace=ailab-ma4agismall \
  --charged-group=ma4agismall_gpu \
  --private-machine=group \
  --gpu=1 \
  --cpu=32 \
  --memory=204800 \
  --image=<gsmap-gpu镜像> \
  --image-pull-policy=IfNotPresent \
  --mount=gpfs://gpfs2/liangxiuliang-2:/mnt/shared-storage-gpfs2/liangxiuliang-2 \
  -- bash -c '
    set -eo pipefail
    export PATH=/opt/conda/bin:$PATH
    export LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64:/usr/local/cuda/lib64:$LD_LIBRARY_PATH
    GPFS=/mnt/shared-storage-gpfs2/liangxiuliang-2
    WORKDIR_SUFFIX=harness_$(date +%Y%m%d_%H%M%S)
    WORKDIR_SUFFIX=$WORKDIR_SUFFIX bash $GPFS/gsmap/e2e_gpu_v18.sh
  '
```

---

## 查看状态和日志

```bash
rjob list --namespace=ailab-ma4agismall
rjob logs job <job_name> --namespace=ailab-ma4agismall -n 100
rjob get <job_name> --namespace=ailab-ma4agismall
rjob stop <job_name>
rjob delete <job_name>
```

---

## 输出目录约定

所有运行输出写到 GPFS（不写容器本地，容器销毁后数据消失）：

```
/mnt/shared-storage-gpfs2/liangxiuliang-2/<tool>/runs/<step>/<timestamp>/
```

例：
```
/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/runs/profiling/20260629_120000/
/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/runs/cpu_baseline/20260629_130000/
/mnt/shared-storage-gpfs2/liangxiuliang-2/gsmap/runs/gpu_compare/20260629_140000/
```
