"""Download public OGLE data, freeze a star-level split and extract representations."""
from pathlib import Path
import argparse, hashlib, io, json, tarfile, urllib.request
import numpy as np
from features import extract

ROOT = Path(__file__).resolve().parent
BASE = 'https://www.astrouw.edu.pl/ogle/ogle4/OCVS/lmc/'
CLASSES = [('rrlyr','RRab.dat','RRab'), ('rrlyr','RRc.dat','RRc'),
           ('cep','cepF.dat','CEP-F'), ('cep','cep1O.dat','CEP-1O')]

def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    print('Downloading', url, flush=True)
    with urllib.request.urlopen(url, timeout=120) as src, path.with_suffix('.tmp').open('wb') as dst:
        while chunk := src.read(1024*1024):
            dst.write(chunk)
    path.with_suffix('.tmp').replace(path)

def clean(a):
    a = np.atleast_2d(a)
    a = a[np.isfinite(a).all(1) & (a[:,2]>0)]
    a = a[np.argsort(a[:,0], kind='stable')]
    t, inv = np.unique(a[:,0], return_inverse=True)
    w = 1 / a[:,2]**2
    sw = np.bincount(inv, weights=w)
    return np.column_stack((t, np.bincount(inv, weights=a[:,1]*w)/sw, np.sqrt(1/sw)))

def positions(path):
    result = {}
    for line in path.read_text().splitlines():
        try:
            ra = (float(line[28:30])+float(line[31:33])/60+float(line[34:39])/3600)*15
            dec = (float(line[41:43])+float(line[44:46])/60+float(line[47:51])/3600)
            dec *= -1 if line[40]=='-' else 1
            r,d = np.deg2rad([ra,dec])
            result[line.split()[0]] = np.array([np.cos(d)*np.cos(r),np.cos(d)*np.sin(r),np.sin(d)])
        except (ValueError, IndexError):
            continue
    return result

def main(cache):
    data = ROOT/'data'; data.mkdir(exist_ok=True)
    protocol_hash = hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()
    rng = np.random.default_rng(20260929)
    tables, pos, selected_ids = [], {}, set()
    for family in ('rrlyr','cep'):
        download(BASE+family+'/ident.dat', cache/family/'ident.dat')
        pos.update(positions(cache/family/'ident.dat'))
    for family, table, label in CLASSES:
        p = cache/family/table; download(BASE+family+'/'+table,p)
        rows=[]
        for line in p.read_text().splitlines():
            s=line.split()
            if not s or s[0].startswith('#'): continue
            try: period=float(s[3])
            except (ValueError,IndexError): continue
            if period>0 and s[0] in pos: rows.append((s[0],period))
        rng.shuffle(rows)
        tables.append(rows)
        # All candidates are needed for deterministic eligibility selection.
        selected_ids.update(r[0] for r in rows)
    curves={}
    for family in ('rrlyr','cep'):
        archive=cache/family/'phot.tar.gz'; download(BASE+family+'/phot.tar.gz',archive)
        with tarfile.open(archive,'r:gz') as tar:
            for member in tar:
                name=Path(member.name)
                if member.isfile() and name.parent.name=='I' and name.stem in selected_ids:
                    try: curves[name.stem]=clean(np.loadtxt(io.BytesIO(tar.extractfile(member).read())))
                    except (ValueError,IndexError): pass
        print('Loaded',family,len(curves),'curves',flush=True)
    manifest=[]; excluded={}; seen=set(); coordinates=[]; arrays={}; features={}; perturbed={}
    for c, rows in enumerate(tables):
        count=0
        for ident,period in rows:
            a=curves.get(ident)
            reason=None
            if a is None or len(a)<80: reason='missing_or_short'
            elif len(np.unique(np.floor(((a[:,0]-a[0,0])/period%1)*32)))<24: reason='phase_coverage'
            elif np.percentile(a[:,1],95)-np.percentile(a[:,1],5)<1e-6: reason='constant'
            digest=hashlib.sha256(a.tobytes()).hexdigest() if a is not None else ''
            if digest in seen: reason='duplicate_curve'
            if coordinates and np.max(np.asarray(coordinates)@pos[ident])>np.cos(np.deg2rad(2/3600)): reason='near_duplicate_position'
            if reason:
                excluded[reason]=excluded.get(reason,0)+1; continue
            f=extract(a,period); g=extract(a,period*1.01)
            for k,v in f.items(): features.setdefault(k,[]).append(v)
            for k,v in g.items(): perturbed.setdefault(k,[]).append(v)
            seen.add(digest); coordinates.append(pos[ident]); arrays[ident]=a
            manifest.append(dict(id=ident, label=CLASSES[c][2], y=c, period=period,
                                 split='support' if count<300 else 'test', n_obs=len(a), sha256=digest))
            count+=1
            if count%100==0: print(CLASSES[c][2],count,flush=True)
            if count==500: break
        if count!=500: raise RuntimeError(f'Not enough eligible curves for {CLASSES[c][2]}: {count}')
    np.savez_compressed(data/'curves.npz',**arrays)
    np.savez_compressed(data/'features.npz',**{k:np.array(v) for k,v in features.items()})
    np.savez_compressed(data/'features_period_plus1pct.npz',**{k:np.array(v) for k,v in perturbed.items()})
    (data/'manifest.json').write_text(json.dumps(manifest,indent=2))
    audit=dict(protocol_sha256=protocol_hash,excluded=excluded,classes=[c[2] for c in CLASSES],
               sources=[BASE+f+'/'+t for f,t,_ in CLASSES],
               archives={f:hashlib.sha256((cache/f/'phot.tar.gz').read_bytes()).hexdigest() for f in ('rrlyr','cep')})
    (data/'audit.json').write_text(json.dumps(audit,indent=2))
    print('Prepared',len(manifest),'unique stars at',data,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--cache',type=Path,required=True)
    main(p.parse_args().cache)
