import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",default="1,2,3,4,5"); ap.add_argument("--methods",default="rule,bandit"); ap.add_argument("--raw-llm",action="store_true"); ap.add_argument("--task-action-mask",action="store_true"); ap.add_argument("--contract-action-mask",action="store_true"); ap.add_argument("--suffix",default=""); ap.add_argument("--tasks",default="tasks/tasks.jsonl"); ap.add_argument("--gold",default="tasks/gold_answers.json"); ap.add_argument("--references",default="tasks/reference_outputs.json"); ap.add_argument("--temperature",type=float,default=None); args=ap.parse_args()
    out=Path("reports/matrix"); out.mkdir(parents=True,exist_ok=True)
    for method in args.methods.split(","):
        for seed in args.seeds.split(","):
            path=out/f"{method}_seed{seed}{args.suffix}.jsonl"
            cmd=[sys.executable,"-m","experiments.run","--mode",method,"--seed",seed,"--out",str(path),"--tasks",args.tasks,"--gold",args.gold,"--references",args.references]
            if args.raw_llm and method == "llm": cmd.append("--no-contract-protection")
            if args.task_action_mask and method == "llm": cmd.append("--task-action-mask")
            if args.contract_action_mask and method == "llm": cmd.append("--contract-action-mask")
            if args.temperature is not None and method == "llm": cmd.extend(["--temperature",str(args.temperature)])
            label="replicate" if method == "llm" else "seed"
            print("running",method,label,seed,flush=True); subprocess.run(cmd,check=True)
    print(f"wrote matrix results to {out}")
if __name__ == "__main__": main()

