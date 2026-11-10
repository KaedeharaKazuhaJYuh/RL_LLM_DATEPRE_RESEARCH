import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import tables
from datetime import date
parser=argparse.ArgumentParser()
parser.add_argument('archive', type=Path)
p=parser.parse_args().archive
h=hashlib.sha256()
with p.open('rb') as f:
 while block := f.read(8*1024*1024): h.update(block)
if h.hexdigest() != '340f84491dc9c5eb8173718bea15cd7fe80abf8e945adf26859a34aaa66e7816': raise ValueError('archive hash mismatch')
groups={14:[],15:[]}
with tables.open_file(p) as h:
 for t in h.list_nodes('/flows',classname='Table'):
  d=date.fromisoformat(f'{t.name[1:5]}-{t.name[5:7]}-{t.name[7:9]}')
  iso=d.isocalendar()
  if iso.year==2022 and iso.week in groups:
   groups[iso.week].append(t.read(field='SRC_IP'))
sets={w:set(np.concatenate(arrays).tolist()) for w,arrays in groups.items()}
intersection=sets[14]&sets[15]
result={'archive_sha256':'340f84491dc9c5eb8173718bea15cd7fe80abf8e945adf26859a34aaa66e7816','weeks':[14,15], 'flows':{str(w):sum(len(a) for a in groups[w]) for w in groups}, 'unique_src_ip':{str(w):len(s) for w,s in sets.items()},'shared_src_ip':len(intersection),'fraction_w15_unique_seen_w14':len(intersection)/len(sets[15]),'scope':'Exact string equality in two adjacent weeks; identifiers excluded from output. Does not establish identity stability or duplicate sessions.'}
out=Path('research/reliability_reset/experiments/communication_telemetry/CESNET_XS_SOURCE_OVERLAP_W14_W15_2026_11_10.json')
out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
