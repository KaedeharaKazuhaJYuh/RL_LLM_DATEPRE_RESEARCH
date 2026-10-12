"""Fail-closed checks of normalized window records; public facts only."""
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

def instant(value):
    d=datetime.fromisoformat(value)
    if d.tzinfo is None or d.utcoffset()!=timedelta(0):
        raise ValueError('explicit zero-offset instant required')
    return d

def number(value):
    if type(value) not in (int,float,str): raise ValueError('number type')
    d=Decimal(str(value))
    if not d.is_finite(): raise ValueError('finite number required')
    return d

def check(record, public=None):
    errors=[]
    try:
        if not isinstance(record,dict) or set(record)!={'version','start_utc','end_utc','rows','total'}: raise ValueError('record schema')
        start,end=instant(record['start_utc']),instant(record['end_utc'])
        if start>=end: raise ValueError('window order')
        if not isinstance(record['version'],str) or not isinstance(record['rows'],list): raise ValueError('record types')
        seen=set(); total=Decimal(0)
        for r in record['rows']:
            if not isinstance(r,dict) or set(r)!={'id','included','value','ge_start','lt_end','time_utc'}: raise ValueError('row schema')
            if not isinstance(r['id'],str) or r['id'] in seen: raise ValueError('duplicate or invalid id')
            seen.add(r['id']); t=instant(r['time_utc'])
            if any(type(r[k]) is not bool for k in ('included','ge_start','lt_end')): raise ValueError('boolean flags')
            v=None if r['value'] is None else number(r['value'])
            if r['ge_start']!=(t>=start) or r['lt_end']!=(t<end): errors.append('comparison:'+r['id'])
            if r['included']!=(r['ge_start'] and r['lt_end']): errors.append('selection:'+r['id'])
            if r['included'] and v is not None: total+=v
        if abs(number(record['total'])-total)>Decimal('1e-9'): errors.append('sum')
        if public is not None:
            if set(public)!={'version','start','end','rows'}: raise ValueError('public schema')
            if record['version']!=public['version']: errors.append('version_binding')
            if start!=datetime.fromisoformat(public['start']) or end!=datetime.fromisoformat(public['end']): errors.append('window_binding')
            source={r['id']:r for r in public['rows']}
            if len(source)!=len(public['rows']): raise ValueError('ambiguous source ids')
            if seen!=set(source): errors.append('coverage_binding')
            for r in record['rows']:
                if r['id'] not in source: continue
                raw=source[r['id']]
                expected=None if raw['value']=='' else number(raw['value'])
                actual=None if r['value'] is None else number(r['value'])
                if actual!=expected: errors.append('value_binding:'+r['id'])
                if instant(r['time_utc'])!=datetime.fromisoformat(raw['time']): errors.append('time_binding:'+r['id'])
    except (KeyError,TypeError,ValueError,InvalidOperation,OverflowError):
        errors.append('malformed_or_unverifiable')
    return {'pass':not errors,'violations':sorted(set(errors)), 'scope':'public_bound' if public is not None else 'internal_only'}
