"""Fetch and prepare pinned CC BY 4.0 UCI tables for the V3.1 benchmark."""
import argparse, csv, hashlib, io, json, urllib.request, zipfile
from pathlib import Path
from research.io import ROOT, digest, write_json, write_table

SOURCES = {
    "wine": {"url":"https://archive.ics.uci.edu/static/public/186/wine+quality.zip","sha256":"3ed56667f4b828242bd732d7d1dd7f2861e54432239d7fa63877014cbb0304d4","doi":"10.24432/C56S3T","license":"CC BY 4.0"},
    "bank": {"url":"https://archive.ics.uci.edu/static/public/222/bank+marketing.zip","sha256":"e0bf5f5de5b846e2f18e9d90606637267d46dfa260e0f17bb12e605db5efbeb4","doi":"10.24432/C5K306","license":"CC BY 4.0"},
    "abalone": {"url":"https://archive.ics.uci.edu/static/public/1/abalone.zip","sha256":"755a6a67c5b266961a3f149ea13be2cfb6e6c727e48cee3c83bc0b4526210ee4","doi":"10.24432/C55C7W","license":"CC BY 4.0"},
    "seoul_bike": {"url":"https://archive.ics.uci.edu/static/public/560/seoul+bike+sharing+demand.zip","sha256":"139e9908f0a3544bb222386855c9ce107e96467306bb8e4ce936aab59e7baac4","doi":"10.24432/C5F62R","license":"CC BY 4.0"},
    "bike_sharing": {"url":"https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip","sha256":"b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401","doi":"10.24432/C5W894","license":"CC BY 4.0"},
}
CACHE_NAMES={"wine":"wine_quality.zip","bank":"bank_marketing.zip","abalone":"abalone.zip","seoul_bike":"seoul_bike.zip","bike_sharing":"bike_sharing.zip"}
ABALONE_COLUMNS=["Sex","Length","Diameter","Height","Whole_weight","Shucked_weight","Viscera_weight","Shell_weight","Rings"]

def _bytes(name, cache):
    cached=Path(cache)/CACHE_NAMES[name]
    raw=cached.read_bytes() if cached.exists() else urllib.request.urlopen(SOURCES[name]["url"],timeout=60).read()
    if hashlib.sha256(raw).hexdigest()!=SOURCES[name]["sha256"]: raise ValueError(f"{name} archive hash mismatch")
    return raw

def _read(name, raw):
    outer=zipfile.ZipFile(io.BytesIO(raw))
    if name=="wine": payload=outer.read("winequality-red.csv").decode(); delimiter=";"; columns=None
    elif name=="bank":
        inner=zipfile.ZipFile(io.BytesIO(outer.read("bank.zip")));payload=inner.read("bank.csv").decode();delimiter=";";columns=None
    elif name=="abalone": payload=outer.read("abalone.data").decode();delimiter=",";columns=ABALONE_COLUMNS
    elif name=="seoul_bike": payload=outer.read("SeoulBikeData.csv").decode("latin-1");delimiter=",";columns=None
    else: payload=outer.read("day.csv").decode();delimiter=",";columns=None
    reader=csv.DictReader(io.StringIO(payload),fieldnames=columns,delimiter=delimiter)
    return list(reader)

def build(cache="work", out_dir=None, limit=240):
    out=Path(out_dir or ROOT/"tasks/v3_real/data");out.mkdir(parents=True,exist_ok=True);manifest={"version":"3.2","sources":{}}
    specs={"wine":("quality","alcohol","density"),"bank":("job","balance","duration"),"abalone":("Sex","Whole_weight","Shell_weight"),
           "seoul_bike":("Seasons","Rented Bike Count","Temperature(°C)"),"bike_sharing":("season","cnt","temp")}
    for name in SOURCES:
        rows=_read(name,_bytes(name,cache))[:limit]; category,value,metric=specs[name];cols=list(rows[0])
        target=out/f"{name}.csv";write_table(target,cols,rows)
        manifest["sources"][name]={**SOURCES[name],"derived_sha256":digest(target),"rows":len(rows),"columns":cols,
                                     "category":category,"value":value,"metric":metric,"split":"train" if name in {"wine","bank"} else "test"}
    write_json(out.parent/"manifest.json",manifest);return manifest

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--cache",default="../work");a=p.parse_args();print(json.dumps(build(a.cache),indent=2))
