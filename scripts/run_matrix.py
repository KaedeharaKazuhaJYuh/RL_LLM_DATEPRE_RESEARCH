import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",default="1,2,3,4,5"); ap.add_argument("--methods",default="rule,bandit"); ap.add_argument("--raw-llm",action="store_true"); ap.add_argument("--suffix",default=""); args=ap.parse_args()
    out=Path("reports/matrix"); out.mkdir(parents=True,exist_ok=True)
    for method in args.methods.split(","):
        for seed in args.seeds.split(","):
            path=out/f"{method}_seed{seed}{args.suffix}.jsonl"
            cmd=[sys.executable,"-m","experiments.run","--mode",method,"--seed",seed,"--out",str(path)]
            if args.raw_llm and method == "llm": cmd.append("--no-contract-protection")
            print("running",method,"seed",seed,flush=True); subprocess.run(cmd,check=True)
    print(f"wrote matrix results to {out}")
if __name__ == "__main__": main()

