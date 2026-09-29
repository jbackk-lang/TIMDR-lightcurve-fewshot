"""Explicit, auditable import of photometry; never guess flux as magnitude."""
import csv, io, re
from datetime import datetime, timezone
import numpy as np

ALIASES = {
    'time': ['time','czas','jd','hjd','bjd','mjd','date','datetime','timestamp','juliandate'],
    'magnitude': ['magnitude','mag','magnitudo','vmag','imag'],
    'error': ['error','err','merr','magerr','magerror','uncertainty','sigma','blad'],
    'band': ['filter','filt','band','pasmo'],
    'object': ['name','star','object','objectid','target','nazwa'],
}

def norm(s): return re.sub(r'[^a-z0-9]', '',s.lower())

def number(s):
    s=str(s).strip()
    if s.startswith(('<','>')): raise ValueError('upper/lower limit')
    return float(s.replace(',','.'))

def inspect_text(text):
    if not isinstance(text,str) or len(text.encode('utf-8'))>5_000_000:
        raise ValueError('Plik musi być tekstem o wielkości do 5 MB.')
    lines=[]; metadata={}
    for line in text.lstrip('\ufeff').splitlines():
        line=line.strip()
        if not line: continue
        if line.startswith('#'):
            bare=line[1:].strip()
            if '=' in bare:
                k,v=bare.split('=',1); metadata[k.upper()]=v.strip();continue
            if re.match(r'(?i)NAME[,;\t]',bare) or re.match(r'(?i)(time|jd|hjd|mjd)[,;\t ]',bare):
                lines.append(bare)
            continue
        lines.append(line)
    if not lines:raise ValueError('Plik nie zawiera danych. Wgraj tabelę pomiarów, nie zdjęcie.')
    first=lines[0]
    delim=';' if ';' in first else '\t' if '\t' in first else ',' if ',' in first else None
    rows=list(csv.reader(lines,delimiter=delim)) if delim else [line.split() for line in lines]
    if len(rows)>20001:raise ValueError('Maksymalnie 20 000 wierszy. Wybierz jeden obiekt i jedno pasmo.')
    first=[v.strip() for v in rows[0]]
    known={a for arr in ALIASES.values() for a in arr}
    header=any(norm(v) in known for v in first)
    if header:headers=first; rows=rows[1:]
    else:headers=[f'Kolumna {i+1}' for i in range(len(first))]
    if len(headers)<2:raise ValueError('Nie rozpoznano tabeli. Użyj CSV z przecinkiem, średnikiem, tabulatorem albo DAT z odstępami.')
    if len(headers)>80:raise ValueError('Za dużo kolumn (maksymalnie 80).')
    rows=[[v.strip() for v in row] for row in rows]
    suggest={}
    for field,names in ALIASES.items():
        suggest[field]=next((i for i,v in enumerate(headers) if norm(v) in names),None)
    if not header and len(headers)==3:suggest.update(time=0,magnitude=1,error=2)
    values={str(i):sorted({r[i] for r in rows if len(r)>i and r[i]})[:101] for i in range(len(headers))}
    return dict(headers=headers,rows=rows,suggest=suggest,preview=rows[:6],values=values,metadata=metadata,
                delimiter=delim or 'whitespace')

def time_value(value,unit):
    if unit=='iso':
        date=datetime.fromisoformat(value.replace('Z','+00:00'))
        if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
        return date.timestamp()/86400
    return number(value)/{'days':1,'hours':24,'seconds':86400}[unit]

def parse_table(text,mapping,unit='days',band='',object_name=''):
    table=inspect_text(text);rows=table['rows'];headers=table['headers']
    if unit not in ('days','hours','seconds','iso'):raise ValueError('Nieznana jednostka czasu.')
    indexes={}
    for k in ALIASES:
        v=mapping.get(k)
        if v is None or v=='':indexes[k]=None;continue
        i=int(v)
        if i<0 or i>=len(headers):raise ValueError('Wybrana kolumna nie istnieje.')
        indexes[k]=i
    if indexes['time'] is None or indexes['magnitude'] is None:raise ValueError('Wskaż kolumnę czasu i magnitudo.')
    fields=[indexes[k] for k in ('time','magnitude','error') if indexes[k] is not None]
    if len(set(fields))!=len(fields):raise ValueError('Czas, magnitudo i błąd muszą być różnymi kolumnami.')
    for k,selection in [('band',band),('object',object_name)]:
        i=indexes[k]
        if i is not None:
            choices=table['values'][str(i)]
            if len(choices)>1 and not selection:raise ValueError('Wybierz jedno pasmo i jeden obiekt. Nie łącz różnych krzywych.')
            if selection and selection not in choices:raise ValueError('Wybrana wartość filtra nie występuje w pliku.')
    used=[];stats=dict(input_rows=len(rows),filtered_rows=0,bad_time=0,bad_magnitude=0,bad_error=0,limits=0)
    for row in rows:
        if any(indexes[k] is not None and sel and (len(row)<=indexes[k] or row[indexes[k]]!=sel)
               for k,sel in [('band',band),('object',object_name)]):
            stats['filtered_rows']+=1;continue
        try:
            t=time_value(row[indexes['time']],unit)
            if not np.isfinite(t):raise ValueError()
        except (ValueError,IndexError,OverflowError):stats['bad_time']+=1;continue
        try:
            val=row[indexes['magnitude']]
            if val.startswith(('<','>')):stats['limits']+=1;continue
            y=number(val)
            if not np.isfinite(y):raise ValueError()
        except (ValueError,IndexError):stats['bad_magnitude']+=1;continue
        try:
            e=number(row[indexes['error']]) if indexes['error'] is not None else float('nan')
            if not np.isfinite(e) or e<=0:raise ValueError()
        except (ValueError,IndexError):e=float('nan');stats['bad_error']+=1
        used.append((t,y,e))
    if len(used)<2:raise ValueError('Mniej niż dwa poprawne pomiary czasu i magnitudo. Sprawdź kolumny i format czasu.')
    a=np.array(used);stats['unsorted_steps']=int(np.sum(np.diff(a[:,0])<0))
    stats['duplicates']=len(a)-len(np.unique(a[:,0]))
    a=a[np.argsort(a[:,0],kind='stable')]
    # Missing uncertainties remain visible and block classification, not silently invented.
    if stats['duplicates']:
        merged=[]
        for t in np.unique(a[:,0]):
            group=a[a[:,0]==t];good=np.isfinite(group[:,2])
            if good.all():
                w=1/group[:,2]**2;merged.append([t,float(np.average(group[:,1],weights=w)),float(1/np.sqrt(w.sum()))])
            else:merged.append([t,float(np.mean(group[:,1])),float('nan')])
        a=np.array(merged)
    stats['usable_points']=len(a)
    detected_band=band
    if not detected_band and indexes['band'] is not None:
        choices=table['values'][str(indexes['band'])]
        if len(choices)==1:detected_band=choices[0]
    return a,stats,dict(metadata=table['metadata'],band=detected_band,unit=unit)
