"""Child process used by V3.4 to create genuine timeout and partial-write failures."""
import argparse, json, os, time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=["timeout","partial","success"],required=True);p.add_argument("--output",required=True);p.add_argument("--sleep",type=float,default=2.0);a=p.parse_args()
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    if a.mode=="partial":
        with target.open("wb") as f:f.write(b'{"status":"running","rows":');f.flush();os.fsync(f.fileno())
    if a.mode in {"timeout","partial"}:time.sleep(a.sleep)
    target.write_text(json.dumps({"status":"complete","rows":1})+"\n",encoding="utf-8",newline="\n")

if __name__=="__main__":main()
