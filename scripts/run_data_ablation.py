from experiments.run import experiment
from research.io import ROOT,write_json
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out-dir',default='reports/v2_data_only');args=parser.parse_args()
    runs=[]
    for seed in range(1,6):
        path=f'{args.out_dir}/bandit_seed{seed}.jsonl'
        result=experiment('bandit',seed,6,path,data_only=True);runs.append({'file':path,'summary':result})
        print(f'data-only seed {seed}: {result["passed"]}/{result["tasks"]}',flush=True)
    write_json(ROOT/args.out_dir/'matrix_manifest.json',{'version':2,'runs':runs})
