import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--seeds",default="1,2,3,4,5"); ap.add_argument("--methods",default="rule,bandit"); args=ap.parse_args()
    out=Path("reports/matrix"); out.mkdir(parents=True,exist_ok=True)
    for method in args.methods.split(","):
        for seed in args.seeds.split(","):
            path=out/f"{method}_seed{seed}.jsonl"
            cmd=[sys.executable,"-m","experiments.run","--mode",method,"--out",str(path)]
            print("running",method,"seed",seed,flush=True); subprocess.run(cmd,check=True)
    print(f"wrote matrix results to {out}")
if __name__ == "__main__": main()

