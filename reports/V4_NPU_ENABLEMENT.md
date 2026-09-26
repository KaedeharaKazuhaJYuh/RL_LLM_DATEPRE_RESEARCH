# V4 Intel NPU 接入与精度审计（2026-09-20）

## 结论

本机的 NPU 已被真实调用，不再只使用 NVIDIA GPU。设备为 `Intel(R) AI Boost`，PCI 设备 ID `0xAD1D`，OpenVINO 识别为 NPU 3720，驱动版本 `32.0.100.4512`。独立 ReLU 计算图在 NPU 上编译和推理通过；DeepSeek-R1-Distill-Qwen-1.5B 也已转换为 OpenVINO INT4 并在 NPU 上完成文本生成。Intel 官方将 Arrow Lake `0xAD1D`/NPU 3720/Windows 11 列为受支持平台，并要求 NPU LLM 使用 INT4/NF4 等压缩格式（[NPU 插件支持表](https://github.com/openvinotoolkit/openvino/blob/master/src/plugins/intel_npu/README.md)，[OpenVINO NPU LLM 指南](https://docs.openvino.ai/2026/openvino-workflow-generative/inference-with-genai/inference-with-genai-on-npu.html)）。

当前 NPU 版本不能替代 BF16 主评测：全比例 INT4 严重降低规划正确率，混合 INT4/INT8 虽然改善到 15/24，仍低于 GPU BF16 的 21/24。NPU 可以用于后续量化研究和通过精度门槛后的辅助推理；LoRA/SFT/DPO/GRPO 反向训练仍由 CUDA GPU 执行，因为本轮 OpenVINO NPU 路径是冻结推理后端，不提供项目所需的 PyTorch 反向训练。

## 环境与可复现入口

NPU 使用独立环境 `work/.venv-v4-npu`，避免改变 CUDA 训练环境。固定依赖见 `requirements-v4-npu.txt`：OpenVINO 2026.3、OpenVINO GenAI 2026.3、Optimum Intel 2.2、NNCF 3.4 和 Transformers 5.0。Intel 文档对 OpenVINO 2026.3 的 NPU 模型生成推荐 Transformers 5.0；OpenVINO GenAI 官方支持 LLM LoRA safetensors 适配器（[NPU 指南](https://docs.openvino.ai/2026/openvino-workflow-generative/inference-with-genai/inference-with-genai-on-npu.html)，[LoRA 示例](https://github.com/openvinotoolkit/openvino.genai/blob/master/samples/python/text_generation/lora_greedy_causal_lm.py)）。

```powershell
python -m venv work/.venv-v4-npu
work/.venv-v4-npu/Scripts/python.exe -m pip install -r requirements-v4-npu.txt
work/.venv-v4-npu/Scripts/python.exe -m experiments.v4_npu_probe
```

`experiments.v4_npu_probe` 会先编译并执行一个确定性 ReLU 图；传入 OpenVINO 模型后会继续做 LLM 生成。`experiments.v4_llm_eval_npu` 使用同一个 `SequenceEnv`、严格 JSON 解析和开发集切片执行冻结评测。`experiments.v4_merge_adapter` 用于在部署导出前合并 PEFT LoRA。

## 实测结果

基础 NPU 图探测成功：编译约 0.08–0.10 秒，单次小图推理约 0.46–0.47 秒。基座 1.5B INT4 模型首次 NPU 编译约 29.54 秒，16 token 生成约 2.83 秒。DPO LoRA 能由 OpenVINO GenAI 直接加载；一次 48 token 探针首次编译约 21.99 秒，生成约 3.86 秒。

同一个 12 题开发子集、正常/故障各一次、共 24 次执行的比较如下：

| 后端与模型 | 通过 | 解析错误 | 平均单次生成 | 说明 |
| --- | ---: | ---: | ---: | --- |
| CUDA BF16，DPO LoRA | 21/24 | 0 | 未在旧记录计时 | 主基线 |
| CUDA BF16，合并 DPO | 21/24 | 0 | 未在旧记录计时 | 证明 LoRA 合并无损 |
| OpenVINO CPU FP16，合并 DPO | 21/24 | 0 | 0.92 秒 | 证明 OpenVINO/提示路径无损 |
| OpenVINO CPU INT4，动态 DPO LoRA | 7/24 | 0 | 0.54 秒 | 全比例 INT4 精度下降 |
| NPU INT4，动态 DPO LoRA | 8/24 | 0 | 2.61 秒 | 比 CPU INT4 多 1 题，仍不可接受 |
| NPU INT4，先合并 DPO | 3/24 | 0 | 2.23 秒 | 合并后再全量 INT4 更差 |
| NPU 混合 INT4/INT8，合并 DPO | 15/24 | 0 | 2.99 秒 | 当前最佳 NPU 版本 |

混合版本将 106/198 层压为 INT4，92/198 层保留 INT8；模型目录约 1.21 GiB。全比例 INT4 目录约 1.08 GiB，FP16 目录约 3.33 GiB。混合版本相对 BF16 基线没有新增通过题，丢失 6 题，因此不能用于主结果或替代冻结基线。它的 24 次执行共发起 90 次模型生成，首次编译约 62.19 秒，平均生成约 2.99 秒。

本轮没有把 NPU 与 GPU 延迟直接排名：旧 GPU 评测没有逐次计时，且 NPU 记录包含不同数量的多步调用。当前可确认的是本机 CPU INT4 在这个小模型上更快，但准确率同样不足；NPU 的价值需要在精度合格后结合功耗、并发和持续运行测试判断。

## 下一步

下一轮应使用训练来源的实际中文工具规划提示做数据感知量化校准，并在不查看开发答案的条件下选择量化方案。候选包括提高 INT8 保留比例、AWQ/scale estimation 或适合 NPU 3720 的通道量化；每个候选先通过固定的训练侧精度门槛，再进入一次冻结开发评测。只有达到预注册阈值（建议至少不低于 DPO 子集 21/24，且不得出现新增解析错误），NPU 才用于大规模难例筛选或正式开发评测。

GPU 与 NPU 的职责暂定为：GPU 负责 BF16 LoRA 训练、在线 GRPO 和金标准评测；NPU 负责量化模型研究，精度合格后承担冻结推理、难例扫描或并行辅助评测。这样能够实际使用 NPU，同时不因硬件切换改变研究结论。

所有模型转换物和逐次运行记录位于被 Git 忽略的 `work/`，不会把数 GB 权重提交到仓库。关键记录包括 `work/v4_npu_deepseek_probe.json`、`work/v4_llm_npu_dpo_dev12.json`、`work/v4_llm_npu_dpo_merged_ratio08_dev12.json` 和 `work/v4_llm_openvino_cpu_dpo_merged_fp16_dev12.json`。
