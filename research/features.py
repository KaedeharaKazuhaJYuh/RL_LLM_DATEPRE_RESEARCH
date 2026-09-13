"""Named dataset profile + fixed, label-free hashed character n-grams."""
import hashlib,math,re
import numpy as np
from research.io import read_table

DIM=106
def profile(uri):
    cols,rows=read_table(uri);numeric=[];vals=[]
    for c in cols:
        try:v=[float(r[c]) for r in rows if r[c]!='']
        except ValueError:continue
        if v and all(math.isfinite(x) for x in v):numeric.append(c);vals.extend(v)
    return {'rows':len(rows),'columns':cols,'numeric_columns':numeric,'missing_rate':sum(v=='' for r in rows for v in r.values())/max(1,len(rows)*len(cols)),'mean_abs_numeric':sum(abs(v) for v in vals)/max(1,len(vals))}

def encode(task,data_profile,data_only=False):
    x=np.zeros(DIM);x[0]=1;x[1]=min(data_profile['rows']/100,1);x[2]=data_profile['missing_rate'];x[3]=len(data_profile['numeric_columns'])/10;x[4]=len(data_profile['columns'])/10;x[5]=math.log1p(data_profile['mean_abs_numeric'])/10
    if not data_only:
        text=re.sub(r'\s+','',task['prompt'].lower())
        for n in (2,3):
            for i in range(max(0,len(text)-n+1)):
                token=text[i:i+n].encode();index=int.from_bytes(hashlib.blake2b(token,digest_size=4).digest(),'little')%100
                x[6+index]+=1
        norm=np.linalg.norm(x[6:])
        if norm:x[6:]/=norm
    return x
