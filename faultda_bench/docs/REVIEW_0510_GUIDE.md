# 0.5.10-dev 人工裁决与设计复审指南

本轮待审为 **12 个原始回执问题对 + 4 个设计问题**。旧 37 组技术签字不覆盖这些新裁决。材料整理和机械校验由项目完成，不等于独立审阅；科学 HOLD，无 API 授权。

先查看 `reports/review510/review_packet.json` 的 prompt_review：仅按原始 system/user 消息判断 contextual/explicit 各自指向哪次回执，填写解释、具体措辞和历史事件位置，再检查 actor 责任范围及 scripted 来源是否清晰。允许 lookup、last_publish、both_plausible、other、unclear，异议不因偏离项目解释而被判错。

随后再看 response_review，复核模型实际回答；保留第一阶段意见及任何改变理由。整包包含旧答案和分数，无法强制盲审；prompt_first_declared 只是审阅者声明，不是程序认证的盲审事实。不要将查看过模型答案后形成的判断冒充事先判断。

四个设计问题分别针对创新增量、独立簇/泄漏控制、指标与分母、下一步决策。请针对文献具体章节、冻结证据或协议条款给出理由；支持、修改、反对和不确定均可返回，不要求给项目正面结论。相关文献的阅读范围仍以 0.5.05 定位文件为准，本版不声称新增全面查新。

将 `review_return_template.json` 另存新文件后填写。只填亲自复核的项，可以部分返回；请提供姓名、参与关系、真人/亲自复核声明和完整所审 Git 提交。程序只校验源摘要、范围和必填证据，不认证身份、提交可访问性或裁决正确性，也不自动登记最终裁决。

```sh
python -m faultda_bench.review510.review --submission /path/to/filled_return.json --output work/review510_return_check.json
```

返回填写文件和校验结果即可；无需 API 密钥或模型调用。接收时另核对真实提交和原件，再按实际覆盖范围登记人审，旧分数继续冻结。完整返回也不代表创新性通过或允许实跑。

包内离线复核（Python 3.11+、NumPy 2.3.5）：

```sh
python -m faultda_bench.review510.audit
python -m unittest discover -s tests -v
```

完整仓库与交接包测试子集分别统计，包根 BUNDLE_VALIDATION.json 记录实际隔离验证结果。原始响应、数据、旧审阅原件和版本化指标均在包内；research 仅包含实际所需运行支持，不代表继承 V5 全部测试已覆盖。
