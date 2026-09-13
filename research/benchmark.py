"""Deterministic synthetic benchmark, grouped by data source, with private oracle."""
import hashlib,random,shutil
from pathlib import Path
from research.io import ROOT,write_table,write_json,append_jsonl,digest
from research.oracle import expected

SPECS=[
    ('profile_schema','识别字段类型并报告行列数','value'),
    ('profile_missingness','找出缺失率最高的列，返回每列缺失率','value'),
    ('count_categories','统计每个类别的频数','category'),
    ('deduplicate','删除重复行并报告前后行数','value'),
    ('describe_numeric','报告数值列的基本统计量','value'),
    ('normalize_dates','统一日期格式，无效日期置空并保存表格','date'),
    ('clip_outliers','识别并处理异常值，将数值截断到给定上下界','value'),
    ('fill_missing','用中位数填补数值缺失并保存表格','value'),
    ('normalize_categories','归一化类别拼写，去首尾空格并转大写','category'),
    ('aggregate','按月份统计收入总额','value'),
    ('correlate','计算两个数值列的相关系数','value'),
    ('rolling_mean','计算三个月移动平均，按行序且只保留完整窗口','metric'),
]


def build(out_dir=None,sources=30):
    from agent.tools import ACTIONS  # Names only, never candidate calculations.
    out=Path(out_dir or ROOT/'tasks/v2');out.mkdir(parents=True,exist_ok=True)
    rng=random.Random(20260913);tasks=[];oracles={};datasets={}
    for source in range(sources):
        split='train' if source<18 else 'validation' if source<24 else 'test'
        cols=['month','region','revenue','category','metric'] if source%2==0 else ['日期','区域','金额','类型','指标']
        date,region,value,category,metric=cols
        rows=[]
        for j in range(12):
            revenue=round(rng.uniform(10,90),2)
            rows.append(dict(zip(cols,[f'2026-{j%4+1:02d}', ['East','West'][j%2],str(revenue),[' a ','B','a',' b'][j%4],str(round(revenue*.8+rng.uniform(-3,3),2))])))
        rows[1][value]='';rows[7][value]='250';rows[3][date]='invalid';rows[4][date]='2026/02/01';rows.append(dict(rows[0]))
        data=out/'data'/f'source_{source:02d}.csv';write_table(data,cols,rows)
        uri=data.relative_to(ROOT).as_posix() if data.is_relative_to(ROOT) else data.as_posix()
        datasets[uri]={'sha256':digest(data),'columns':cols,'rows':len(rows),'split':split,'source_id':f'source_{source:02d}'}
        for action,prompt,kind in SPECS:
            col={'value':value,'category':category,'date':date,'metric':metric}[kind]
            params={'column':col,'group_by':date,'other_column':metric,'lower':0,'upper':100,'window':3}
            task_id=hashlib.sha256(f'{source}/{action}'.encode()).hexdigest()[:16]
            # Wording styles appear in every split; split is data-source holdout, not paraphrase holdout.
            text=[prompt,'请基于表格完成：'+prompt,'分析需求：'+prompt][source%3]
            task={'schema_version':2,'task_id':task_id,'source_id':f'source_{source:02d}','split':split,'prompt':text,'dataset':{'uri':uri,'sha256':digest(data),'columns':cols},'params':params,'allowed_tools':ACTIONS,'constraints':{'max_tool_calls':1,'max_steps':1,'max_seconds':10}}
            tasks.append(task);oracles[task_id]=expected(data,action,params)
    rng.shuffle(tasks)
    path=out/'tasks.jsonl';path.write_text('',encoding='utf-8')
    for task in tasks:append_jsonl(path,task)
    write_json(out/'oracle.json',oracles)
    write_json(out/'manifest.json',{'version':2,'generator_seed':20260913,'task_sha256':digest(path),'oracle_sha256':digest(out/'oracle.json'),'datasets':datasets,'counts':{s:sum(t['split']==s for t in tasks) for s in ('train','validation','test')},'scope':'synthetic, 12 fixed templates, held-out sources; not external real-world generalization'})
    return tasks,oracles


def repair_legacy_values():
    """Restore real CSVs at both historical paths; legacy scoring remains historical."""
    import csv
    transforms={'sample.csv':{'revenue':lambda x:f'{float(x)*1.15+7:.2f}'},'churn.csv':{'tenure_months':lambda x:str(int(float(x))+1),'monthly_fee':lambda x:f'{float(x)*1.10+3:.2f}'},'students.csv':{'study_hours':lambda x:f'{float(x)+.5:.2f}','score':lambda x:f'{float(x)+2:.2f}'}}
    for name,mapping in transforms.items():
        with (ROOT/'data'/name).open(encoding='utf-8',newline='') as f:
            reader=csv.DictReader(f);cols=reader.fieldnames;rows=list(reader)
        for row in rows:
            for col,transform in mapping.items():row[col]=transform(row[col])
        for folder in ('data/variants/value_v1','tasks/variants/value_v1/data'):write_table(ROOT/folder/name,cols,rows)


if __name__=='__main__':
    repair_legacy_values();tasks,_=build();print(f'generated {len(tasks)} v2 tasks and repaired historical CSVs')
