# RL LLM 数据分析 Agent 开工包

## 1 项目目标

我准备研究：强化学习能否利用可验证的数据分析反馈，提高 LLM Agent 在多步数据分析中的工具选择、计划调整和错误恢复能力，同时降低工具调用次数与计算成本。第一阶段先用规则路由和 Contextual Bandit 建立可复现实验，再积累轨迹进入 Offline RL，最后视资源情况加入 LoRA 与 GRPO/PPO。

## 2 首批 50 个实验任务

任务统一使用公开或自建的小型 CSV/Parquet 数据集；每个任务都要求 Agent 输出结论、关键中间产物和可执行代码。建议先固定 5 个随机种子，并按 easy/medium/hard 分层。

|组别|任务编号|任务设计|期望验证点|
|---|---:|---|---|
|读取与概览|T01-T05|识别字段类型；统计行列数；找出缺失率最高列；按类别计数；检查重复行|schema、计数、缺失率、重复率|
|清洗|T06-T10|去重；日期格式统一；异常值截尾；缺失值填补；类别拼写归一|清洗前后行数、规则与审计日志|
|聚合|T11-T15|按月求和；按地区求均值；Top-K 客户；分组占比；透视表|聚合结果与分母正确性|
|统计|T16-T20|均值/中位数比较；置信区间；相关系数；A/B 差异；异常点影响|公式、样本量、方向与数值|
|时间序列|T21-T25|月度趋势；同比环比；移动平均；峰值月份；简单预测|时间排序、窗口、预测区间|
|可视化|T26-T30|选择合适图表；绘制分布；绘制趋势；绘制分组比较；标注异常点|图表类型、轴标签、数据映射|
|特征工程|T31-T35|日期衍生；比率特征；标准化；类别编码；防止目标泄漏|特征定义、训练边界、泄漏检查|
|建模|T36-T40|线性回归；逻辑回归；树模型；交叉验证；基线比较|切分、指标、随机种子、基线|
|解释与决策|T41-T45|解释重要特征；给出业务建议；成本收益排序；生成报告；回答追问|证据引用、结论可追溯、建议约束|
|鲁棒性与恢复|T46-T50|列名变化；缺失文件；工具报错重试；矛盾结果复核；预算受限分析|错误识别、恢复动作、停止条件、成本|

## 3 任务 JSON 格式

```json
{
  "task_id": "T11",
  "dataset": {"uri": "data/sales.csv", "format": "csv", "target": null},
  "prompt": "按月份统计收入总额，并指出收入最高月份。",
  "difficulty": "easy",
  "allowed_tools": ["load_table", "python_exec"],
  "gold": {"answer_type": "table_and_text", "tolerance": 1e-6},
  "constraints": {"max_steps": 8, "max_tool_calls": 4, "max_seconds": 60},
  "reward_weights": {"correctness": 0.6, "traceability": 0.2, "efficiency": 0.2}
}
```

每个任务至少保存 `task.json`、`trajectory.jsonl`、`answer.json` 和 `verification.json`。不要把参考答案直接放进 Agent 可见上下文。

## 4 Verifier 设计

Verifier 分为四层：结构验证（输出字段完整）、数值验证（绝对/相对误差）、语义验证（结论与证据一致）、轨迹验证（工具调用合法且可复现）。总奖励可写为：

`R = 0.60 correctness + 0.20 traceability + 0.20 efficiency - 0.10 invalid_action`

```python
def verify(result, gold, trace, budget):
    structure = has_required_fields(result)
    numeric = compare_tables(result.get("table"), gold.get("table"), tol=gold.get("tolerance", 1e-6))
    evidence = claims_supported(result.get("claims", []), result.get("evidence", []))
    legal = all(step["tool"] in budget["allowed_tools"] for step in trace)
    cost = 1 - min(len(trace) / budget["max_tool_calls"], 1.0)
    score = 0.60 * (0.5 * structure + 0.5 * numeric) + 0.20 * evidence + 0.20 * cost
    return {"passed": bool(structure and numeric and evidence and legal), "score": score,
            "checks": {"structure": structure, "numeric": numeric, "evidence": evidence, "legal": legal}}
```

关键原则：数值任务优先采用程序化核验；开放式建议只核验其证据链、约束满足和是否出现不可支持的断言；所有失败都要记录 `failure_type`，用于后续奖励建模。

## 5 ReAct 与 Rule Router

ReAct 负责在每一步产生 `thought -> action -> observation`，但只允许从白名单工具中选动作；Rule Router 先根据任务特征做低成本初始决策。

```python
def rule_router(state):
    if state["missing_rate"] > 0.30: return "profile_missingness"
    if state["needs_plot"]: return "plot"
    if state["has_target"]: return "split_and_model"
    if state["numeric_columns"] >= 2: return "summarize_and_correlate"
    return "profile_schema"

def react_step(llm, state, tools):
    message = build_prompt(state, tools, output_format="json_action")
    action = llm(message)
    validate_action(action, tools)
    observation = tools[action["tool"]](**action.get("args", {}))
    return action, observation
```

实验上至少比较 Direct Prompt、ReAct、Rule Router、Rule Router + Bandit 四个条件；统一模型、数据、预算和随机种子。

## 6 Contextual Bandit 定义

状态 `s` 建议包括：任务难度、数据行列数、缺失率、数值列数、类别列数、目标变量是否存在、当前步骤数、最近一次 verifier 分数、剩余预算、上一步错误类型。

动作 `a` 为工具白名单中的高层动作，而非任意 token：`profile_schema`、`profile_missingness`、`count_categories`、`deduplicate`、`describe_numeric`、`normalize_dates`、`clip_outliers`、`fill_missing`、`normalize_categories`、`aggregate`、`task_analysis`、`stop`。

当前实现会在每个任务开始时保存状态特征，在任务结束后用 Verifier 得分更新 Bandit。`--seed` 控制随机探索；为了观察未经规则保护的真实探索行为，可使用 `--no-contract-protection`。

即时奖励使用 verifier 分数增量减成本：`r_t = score_t - score_{t-1} - 0.02 * tool_calls - 0.01 * seconds`。先用 LinUCB 或 Thompson Sampling；当有足够轨迹后再训练 Offline RL。

```python
class LinUCBBandit:
    def __init__(self, dim, actions, alpha=1.0):
        self.A = {a: np.eye(dim) for a in actions}; self.b = {a: np.zeros(dim) for a in actions}; self.alpha = alpha
    def select(self, x):
        scores = {}
        for a in self.A:
            inv = np.linalg.inv(self.A[a]); theta = inv @ self.b[a]
            scores[a] = theta @ x + self.alpha * np.sqrt(x @ inv @ x)
        return max(scores, key=scores.get)
    def update(self, a, x, r):
        self.A[a] += np.outer(x, x); self.b[a] += r * x
```

## 7 实验结果表

|方法|平均Verifier分|任务通过率|平均工具调用|平均耗时|平均Token|错误恢复率|95%置信区间|
|---|---:|---:|---:|---:|---:|---:|---|
|Direct Prompt| | | | | | | |
|ReAct| | | | | | | |
|Rule Router| | | | | | | |
|Contextual Bandit| | | | | | | |

建议另存逐任务明细：`task_id, seed, method, score, passed, tool_calls, latency_ms, tokens, failure_type, final_action`。主结论至少报告均值、标准差、通过率和成本，不只报告单次最好结果。

## 8 GitHub 项目目录

```text
rl-llm-data-agent/
├─ README.md
├─ pyproject.toml
├─ configs/{baseline.yaml,bandit.yaml}
├─ data/{raw,processed,manifests}
├─ tasks/{tasks.jsonl,schemas/task.schema.json}
├─ agent/{react.py,router.py,bandit.py,tools.py,state.py}
├─ verifier/{structure.py,numeric.py,semantic.py,trace.py,score.py}
├─ experiments/{run.py,aggregate.py,seed.py}
├─ reports/{tables,figures}
├─ tests/{test_tools.py,test_verifier.py,test_router.py}
└─ scripts/{make_tasks.py,run_all.ps1}
```

## 9 第一周落地顺序

先实现 T01、T06、T11、T16、T26、T36、T46 七个代表任务；完成 Direct Prompt 与 Rule Router；写好程序化 Verifier；固定日志格式；再扩展到全部 50 个任务。只有当 Verifier 在人工抽查中达到至少 95% 一致率，才开始比较 Bandit。

## 10 当前实验状态

Verifier 已经补充了 `gold.expected` 精确答案校验，并拒绝没有实际答案的提前停止结果。修正后的本地重跑结果保存在 `reports/rechecked_summary.json`，对比说明见 `reports/RESULTS.md`。当前 Rule Router 为 50/50 通过；首轮真实 Bandit（seed=7、无合同保护）为 19/50，通过率较低，说明还需要更多任务重复、特征设计和奖励塑形，不能把它表述为 RL 已经优于规则。

DeepSeek 的旧结果仅作为过程记录；由于它们是在 Verifier 修正前生成的，正式报告前应使用同一版本重新运行。

## 11 最小验收标准

我会把一次实验视为有效，前提是：任务输入可复现、工具调用有日志、输出可被 Verifier 独立检查、预算没有被偷偷放宽、失败原因可分类、结果能按 seed 重跑，并且所有方法使用相同模型和数据切分。

