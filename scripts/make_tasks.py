import json
from pathlib import Path

groups = {
    "overview": ["识别字段类型并报告行列数", "找出缺失率最高的列", "统计每个类别的频数", "检查并报告重复行", "报告数值列的基本统计量"],
    "cleaning": ["删除重复行并报告前后行数", "统一日期格式", "识别并处理异常值", "用中位数填补数值缺失", "归一化类别拼写"],
    "aggregation": ["按月份统计收入总额", "按地区统计平均收入", "找出收入最高的Top 5客户", "计算各类别收入占比", "生成月份乘地区透视表"],
    "statistics": ["比较两组均值和中位数", "计算均值的置信区间", "计算两个数值列的相关系数", "完成一个A/B差异检验", "评估异常点对均值的影响"],
    "time_series": ["绘制月度趋势", "计算同比和环比", "计算三个月移动平均", "找出峰值月份", "用简单基线预测下一期"],
    "visualization": ["为任务选择合适图表", "绘制数值分布", "绘制时间趋势", "绘制分组比较", "标注可疑异常点"],
    "features": ["从日期生成时间特征", "构造业务比率特征", "标准化数值特征", "编码类别特征", "检查并避免目标泄漏"],
    "modeling": ["训练线性回归基线", "训练逻辑回归基线", "训练树模型", "完成交叉验证", "比较模型与多数类基线"],
    "decision": ["解释重要特征", "提出有证据的业务建议", "按成本收益排序建议", "生成结构化分析报告", "回答一个基于结果的追问"],
    "robustness": ["适应列名轻微变化", "处理数据文件不存在", "工具报错后重试", "发现矛盾结果并复核", "在调用预算受限时完成分析"],
}

contracts = {
    "overview": ["schema_profile", "missingness_profile", "category_count", "deduplication", "numeric_summary"],
    "cleaning": ["deduplication", "date_cleaning", "outlier_cleaning", "missing_value_cleaning", "category_normalization"],
    "aggregation": ["monthly_aggregation", "general_analysis", "general_analysis", "general_analysis", "general_analysis"],
    "statistics": ["general_analysis"] * 5,
    "time_series": ["general_analysis"] * 5,
    "visualization": ["general_analysis"] * 5,
    "features": ["general_analysis"] * 5,
    "modeling": ["general_analysis"] * 5,
    "decision": ["general_analysis"] * 5,
    "robustness": ["general_analysis"] * 5,
}
out = Path(__file__).parents[1] / "tasks" / "tasks.jsonl"
out.parent.mkdir(exist_ok=True)
rows=[]
for gi,(group, prompts) in enumerate(groups.items()):
    for j,prompt in enumerate(prompts):
        n=gi*5+j+1; difficulty="easy" if n<=15 else "medium" if n<=35 else "hard"
        dataset = "data/sample.csv" if gi < 3 else "data/churn.csv" if gi < 6 else "data/students.csv"
        rows.append({"task_id":f"T{n:02d}","dataset":{"uri":dataset,"format":"csv"},"prompt":prompt,"difficulty":difficulty,"allowed_tools":["load_table","aggregate","profile_missingness","count_categories","deduplicate","describe_numeric","normalize_dates","clip_outliers","fill_missing","normalize_categories","task_analysis","python_exec"],"contract":{"required_capabilities":[contracts[group][j]]},"gold":{"answer_type":"structured"},"constraints":{"max_steps":8 if difficulty=="easy" else 12,"max_tool_calls":4 if difficulty=="easy" else 8,"max_seconds":60 if difficulty!="hard" else 120}})
out.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")
print(f"wrote {len(rows)} tasks to {out}")

