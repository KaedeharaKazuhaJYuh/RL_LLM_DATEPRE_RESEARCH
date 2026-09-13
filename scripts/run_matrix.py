"""Explicit file manifest; no wildcard aggregation."""
import argparse
from research.io import resolve,write_json
from experiments.run import experiment
def main():
    p=argparse.ArgumentParser();p.add_argument('--seeds',default='1,2,3,4,5');p.add_argument('--methods',default='rule,supervised,bandit,random,majority');p.add_argument('--out-dir',default='reports/v2');p.add_argument('--epochs',type=int,default=6);a=p.parse_args();entries=[]
    for method in a.methods.split(','):
        for seed in map(int,a.seeds.split(',')):
            out=f'{a.out_dir}/{method}_seed{seed}.jsonl';print(f'running {method} seed {seed}',flush=True)
            summary=experiment(method,seed,a.epochs,out);entries.append({'file':out,'summary':summary})
    write_json(resolve(a.out_dir)/'matrix_manifest.json',{'version':2,'runs':entries})
if __name__=='__main__':main()
