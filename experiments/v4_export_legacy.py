"""Convert earlier trajectories without silently mixing obsolete rewards into training."""
import argparse
import json
from pathlib import Path
from research.io import ROOT,append_jsonl,write_json,load_jsonl


def export(source,out):
    out=Path(out)
    if out.exists():raise FileExistsError('new output directory required')
    out.mkdir(parents=True)
    records=json.loads(Path(source).read_text(encoding='utf-8'))['records']
    tasks={t['task_id']:t for t in load_jsonl('tasks/v3/tasks.jsonl')}
    steps=0
    for record in records:
        task=tasks[record['task_id']];history=[]
        for row in record['trace']:
            obs={'prompt':task['prompt'],'history':list(history)}
            next_history=history+([{'action':row['decision']['action'],'observation':row.get('observation')}] if not row.get('stop') else [])
            append_jsonl(out/'converted.jsonl',{'task_id':record['task_id'],'source_id':task['source_id'],
                'observation':obs,'action':row['decision'],'next_observation':{'prompt':task['prompt'],'history':next_history},
                'terminal_return':record['reward'],'episode_passed':record['passed'],
                'eligible_for_current_training':False,'reason':'old protocol: ambiguous fields and different stop/scoring contract'})
            history=next_history;steps+=1
    result={'episodes':len(records),'converted_steps':steps,'current_training_eligible':0,
            'reason':'retained for audit; fresh current-protocol demonstrations are used for SFT'}
    write_json(out/'audit.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(export(a.source,a.out),indent=2))
