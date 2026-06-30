# 镜像构建 + rjob 提交踩坑

## 坑1 — 开发机有两个，GPFS 数据和 docker 登录状态不在同一台

**现象：**
- `ailab-ma4agismall` 开发机：有 gsMap GPFS 数据，但 docker 未登录 registry
- `ailab-sdpdev` 开发机：docker 已登录，但 GPFS 挂载的是不同用户目录（没有 gsMap 数据）

**规则：**
- docker build 必须在 **docker 已登录** 的机器上执行（sdpdev）
- build context 文件通过 `scp` 上传到 `/tmp/` 本地目录，不依赖 GPFS
- rjob submit 需要在有 kubebrain 环境的机器上执行，需先 `source /etc/profile.d/ssh-init.sh`

**两台机器 SSH 地址：**
```
# sdpdev — docker 已登录，用于 image build/push
ssh -CAXY huron-dev-1.liangxiuliang+root.ailab-sdpdev.ws@h.pjlab.org.cn

# ma4agismall — gsMap GPFS 数据在此，用于读取数据、提交 rjob
ssh -CAXY huron-dev-1.liangxiuliang+root.ailab-ma4agismall.ws@h.pjlab.org.cn
```

**How to apply:**
build 时：scp 文件到 sdpdev /tmp/ → 在 sdpdev docker build + push
rjob 时：ssh 到 ma4agismall → source ssh-init.sh → rjob submit


## 坑2 — Dockerfile 里不能用多行 python3 -c "..."

**现象：** Docker parser 把多行 `RUN python3 -c "import xxx` 的第二行 `import` 识别为未知指令，报错 `unknown instruction: import`

**修复：** 把 Python 脚本写成独立 `.py` 文件，`COPY` 进镜像后 `RUN python3 /tmp/script.py`

```dockerfile
# 错误写法
RUN python3 -c "
import gsMap
print(gsMap.__file__)
"

# 正确写法
COPY scripts/check.py /tmp/check.py
RUN python3 /tmp/check.py && rm /tmp/check.py
```


## 坑3 — docker login 在非 TTY ssh session 里不生效

**现象：** `docker login registry.h.pjlab.org.cn` 在非交互 ssh 里报 `Cannot perform an interactive login from a non TTY device`，即使你在终端手动登录过，通过 ssh 管道执行的 build 仍然报 401 Unauthorized

**原因：** docker 凭证存在 `/root/.docker/config.json`，非 TTY session 下 `docker login` 不写入，导致 build 时拉取 base image 失败

**修复：**
- 确保在**交互终端**（直接 ssh 进去后手动执行）或
- 用已有凭证的机器（sdpdev docker 已登录）
- 检查：`cat /root/.docker/config.json | python3 -c 'import json,sys; print(list(json.load(sys.stdin).get("auths",{}).keys()))'`


## 坑4 — FROM 本地 tag（如 gsmap-base:20250603）在新机器上不可用

**现象：** `FROM gsmap-base:20250603` — Docker 去 docker.io 找不到，超时 i/o timeout

**原因：** 这是通过 rlaunch 或 `docker save/load` 产生的本地 tag，没有推到任何 registry，换一台机器就消失了

**修复：** 必须用 registry 全路径作为 base，或先确认该 tag 在目标机器的 `docker images` 里存在
```
# 错误
FROM gsmap-base:20250603

# 正确
FROM registry.h.pjlab.org.cn/ailab-sdpdev-sdpdev_gpu/gsmap-gpu:v1.8
```


## 坑5 — 历史 GPU 镜像（v1.x）含旧 GPU 代码，harness A 模式必须清除

**现象：** v1.1+ 镜像里有 `latent_to_gene_gpu.py`、`ldscore_gpu.py`、`spatial_ldsc_gpu.py`、`generate_ldscore_gpu.py` 等历史 GPU 实现，以及修改了原版 `latent_to_gene.py` / `generate_ldscore.py` 的内容

**规则：** harness A 模式从头开始，必须彻底清除所有历史 GPU 代码：
```dockerfile
RUN pip3 uninstall -y gsmap 2>/dev/null || true \
 && rm -rf /opt/gsMap \
 && find /usr /opt -name '*gpu*.py' 2>/dev/null | xargs rm -f
RUN pip3 install --no-cache-dir gsmap==<version>
```
然后只加入本次 harness 的 patch 文件。


## 坑6 — rjob submit 在 ma4agismall 开发机上需要 source ssh-init.sh

**现象：** `rjob submit` 报 `RuntimeError: brainpp only work in kubebrain environment`

**修复：**
```bash
source /etc/profile.d/ssh-init.sh
# 然后再执行 rjob submit
```


## 坑8 — profiling rjob 失败必须修复镜像，不得跳过

**现象：** profiling Step1+2 成功，Step3 失败，直接用 Step1+2 的数据做 feasibility 分析。

**错误做法：** 认为"已经看到热点（Step2 = 587s），继续推进"。

**正确做法：**
1. profiling 失败 = L1 镜像未通过验收，必须修复
2. 查清失败原因，修复镜像，重新 build + push + 重提 rjob
3. 等完整 profiling 成功后才能进入 feasibility

**为什么：** profiling 是 L1 镜像的全流程验收测试。Step3 失败意味着 generate_ldscore 在这个镜像里无法运行，后续的 CPU baseline 和 GPU compare 也会在同样位置失败。


## 坑9 — bitarray 版本不兼容导致 generate_ldscore 失败

**现象：** `TypeError: float() argument must be a string or a real number, not 'bitarray.decodeiterator'`

**根因：** gsMap 要求 `bitarray>=2.9.2,<3.0.0`，但镜像里通过 `pip install bitarray`（无版本锁定）安装了 3.8.1，3.x 的 `decode()` API 返回 `decodeiterator` 而不是 list。

**修复：**
```dockerfile
RUN pip3 install --no-cache-dir \
    -i http://mirrors.i.h.pjlab.org.cn/repository/pypi-proxy/simple/ \
    --trusted-host mirrors.i.h.pjlab.org.cn \
    "bitarray==2.9.3"
```

**预防：** 构建 L1 镜像时，对所有有版本上限的依赖（`<3.0.0`、`<2.0.0` 等）必须显式锁定版本，不能裸 `pip install package`。


## 坑7 — rjob 名称不能含大写字母或下划线

**现象：** rjob 提交时报名称校验失败

**修复：** `--name` 只用小写字母、数字、`-`
```bash
# 错误
--name=gsMap_harness_CPU_baseline

# 正确  
--name=gsmap-harness-cpu-baseline
```
