# CESNET ANN/SNN CUDA 单批次烟测

在本机 NVIDIA GeForce RTX 5070 Ti Laptop GPU 上，用隔离环境的 PyTorch `2.8.0+cu128`、CUDA runtime 12.8，从初始化期 2022-03-14 读取同一批 128 条真实流的 PPI、mask 和标签。归档及初始化类别 census 先核验哈希。两种原型分别执行一次前向、交叉熵反向和 SGD 更新；均检查 logits/梯度有限、事件编码层存在非零梯度且编码参数确实变化。[结果](CESNET_CUDA_MODEL_SMOKE_2026_11_12.json) · [复算脚本](smoke_cesnet_cuda_models.py)

| 原型 | 参数量 | 步数 | 编码层非零梯度和更新 |
|---|---:|---:|---|
| ANN：GRU + 线性分类头 | 9,588 | 1 | 是 |
| SNN：LIF 近似脉冲 + surrogate gradient + 线性分类头 | 6,100 | 1 | 是 |

两者使用同一 PPI 批次及标签；有效序列 mask 相同。为烟测采用固定 `sign(x)*log1p(abs(x))/10` 输入变换，尚未按开发集选择参数。模型参数量不同，未匹配计算量、记忆或优化预算；没有评估集、持续学习、无标签更新或性能对照，也没有能耗测量。一次更新只证明该设备与代码路径可以执行，不证明模型效果或 SNN 优势。初始化类别词表使用 W11–W14 的全量类别支持，故本烟测不代表少标签训练。

CUDA 版 PyTorch 按 [PyTorch 官方版本说明](https://pytorch.org/get-started/previous-versions/) 安装在仓库外的独立环境，未改变项目必需依赖。复算需要 Python、NumPy、PyTables 和支持设备的 PyTorch CUDA 构建：

```sh
python -m research.reliability_reset.experiments.communication_telemetry.smoke_cesnet_cuda_models <XS-HDF5> --output <summary.json>
```

下一步须在 W15–W18 固定标签抽样和训练配置，开展预算匹配的多批次 ANN/SNN 开发实验；科学状态仍为 HOLD。
