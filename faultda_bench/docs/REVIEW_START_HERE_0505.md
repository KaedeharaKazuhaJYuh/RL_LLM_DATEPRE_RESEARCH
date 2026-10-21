# 0.5.05-dev 独立复核包入口

本包是固定 Git 提交的证据子集，附真实 `research/__init__.py`、`research/io.py` 和原始 `pyproject.toml`，修复旧包缺依赖的问题；没有伪造 research 存根。它不包含继承 V5 全部实现或测试。此元数据的 5.0.15b2 是继承代码包版本，当前基准版本为 0.5.05-dev。

Python 3.11+，唯一第三方运行依赖 NumPy 2.3.5。从**解压根目录**运行，不需要密钥、GPU 或可编辑安装：

```sh
python -m pip install numpy==2.3.5
python -m faultda_bench.review505.audit
python -m unittest discover -s tests -v
```

安装依赖可能需要网络；其后的审计/测试只读本地记录，不调用模型 API。不要以完整仓库的测试总数要求本子集；本版实测数见报告，分发时的实际数/退出码见包根 `BUNDLE_VALIDATION.json`。该元数据是工程验证，不是额外人工签字。

`REVIEW_MANIFEST.json` 列出除自身外每个成员的 SHA256；包含固定源提交，以及生成的包验证元数据。本地哈希仅校验一致性，供应商真实性未认证。用 GitHub 同一提交或独立保存的摘要交叉核对，不能把项目自己维护的清单称为独立历史证明。

复核顺序：原始人审 Markdown 与 intake 范围 → 12 对解释及 24 迁移组 → 新证据命题与强规则结果 → 相关工作矩阵和准入草案 → 统一审计与测试。前 37 组已被张雨田技术复核；本版新增设计与包装修复仍待独立复核，最终指代裁决未进行，科学 HOLD。
