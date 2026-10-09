"""Generate a reviewer worksheet; never fill in human approvals automatically."""
import argparse
from pathlib import Path
import json

from ..semantic.oracle import reference
from ..semantic.tasks import REPO
from .tasks import load


def worksheet():
    lines = ['# 跨来源任务独立审阅表', '',
             '状态：待人工审阅。以下由程序生成，不代表有人签字，也不是独立人工验收。', '',
             '审阅者需核对原始行、授权版本、业务键含义、维表重复是否应折叠、输出计算和任务措辞。',
             '参考值仅供审阅者复算，不进入 Agent 观察；若发现定义不唯一，标记修订并冻结新版本，不能直接改旧成绩。', '',
             '| 任务 | 来源 | 数值列 | 版本政策 | 人工结论 | 审阅者/日期 |',
             '| --- | --- | --- | --- | --- | --- |']
    for t in load():
        c = t['contract']
        lines.append(f'| {t["id"]} | {t["source_id"]} | {c["column"]} | {c["version_policy"]} | 待审 | — |')
    for t in load():
        version, totals = reference(t)
        lines += ['', f'## {t["id"]}', '',
                  f'原文件：`{t["source_path"]}`；SHA-256：`{t["source_sha256"]}`。',
                  f'零起始行索引（不含表头）：`{t["selection_indices"]}`。',
                  f'公开契约：`{json.dumps(t["contract"], ensure_ascii=False)}`',
                  f'独立 Decimal 参考（待人工复算）：版本 `{version}`，`{json.dumps({k: str(v) for k, v in totals.items()})}`。',
                  '人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。']
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=REPO / 'work/cross_source_review.md')
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as stream:
        stream.write(worksheet().encode())
