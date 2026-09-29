"""Low-cost exploratory ATLAS pilot; see PROTOCOL.md before interpretation."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
os.environ['TF_CPP_MIN_LOG_LEVEL']='3'
import argparse, hashlib, json, struct, sys, time
from pathlib import Path
import numpy as np
from astropy.timeseries import LombScargle
from scipy.optimize import minimize_scalar
from sklearn.metrics import f1_score, confusion_matrix
from threadpoolctl import threadpool_limits

def fields(data):
    """Decode protobuf wire fields used in the public SequenceExample archive."""
    p=0
    def varint():
        nonlocal p
        v=0;shift=0
        while True:
            b=data[p];p+=1;v|=(b&127)<<shift
            if b<128:return v
            shift+=7
    out={}
    while p<len(data):
        tag=varint();wire=tag&7
        if wire==0:value=varint()
        elif wire==2:
            n=varint();value=data[p:p+n];p+=n
        elif wire in (1,5):
            n=8 if wire==1 else 4;value=data[p:p+n];p+=n
        else:raise ValueError(f'Unsupported protobuf wire type {wire}')
        out.setdefault(tag>>3,[]).append(value)
    return out

def mapping(data):
    return {fields(entry)[1][0].decode():fields(entry)[2][0] for entry in fields(data)[1]}

def read(path):
    data=path.read_bytes(); pos=0
    while pos<len(data):
        n=struct.unpack('<Q',data[pos:pos+8])[0]
        ex=fields(data[pos+12:pos+12+n]); pos+=16+n
        c=mapping(ex[1][0]);seq=mapping(ex[2][0])
        curve=np.column_stack([np.frombuffer(fields(fields(fields(seq[f'dim_{k}'])[1][0])[2][0])[1][0],dtype='<f4') for k in range(3)]).astype(float)
        oid=fields(fields(c['id'])[1][0])[1][0].decode()
        label=fields(fields(c['label'])[3][0])[1][0]
        if isinstance(label,bytes):label=int.from_bytes(label,'little')
        yield oid,label,curve
    assert pos==len(data)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repo',required=True);parser.add_argument('--data',required=True)
    args=parser.parse_args();sys.path.insert(0,args.repo)
    print('Imports finished; starting pilot',flush=True)
    from features import extract
    from benchmark import model
    root=Path(__file__).resolve().parent; start=time.perf_counter()
    labels=[0,1,2,4]; names=['CB','DB','Mira','Pulse']; cache={}; records=[]; audits=[]
    arms={'timdr_lda':'timdr','phase_lda':'phase','classical_rf':'classical','period_lda':'period'}
    for fold in range(3):
        groups={}; hashes={}; audit={'fold':fold,'files':{},'duplicates':{}}
        for split in ('train','val','test'):
            group={}; total=0
            for path in sorted((Path(args.data)/f'fold_{fold}'/'atlas_20'/split).glob('*/*.record')):
                audit['files'][str(path.relative_to(args.data))]=hashlib.sha256(path.read_bytes()).hexdigest()
                for oid,label,curve in read(path):
                    if label not in labels:continue
                    total+=1; digest=hashlib.sha256(curve.tobytes()).hexdigest()
                    if oid in group:assert group[oid][0]==label and group[oid][2]==digest
                    group[oid]=(label,curve,digest)
            groups[split]=group;audit['duplicates'][split]=total-len(group)
        train={**groups['train'],**groups['val']}; test=groups['test']
        assert not set(groups['train'])&set(groups['val'])
        assert not set(train)&set(test),'ID leakage'
        assert not {v[2] for v in train.values()} & {v[2] for v in test.values()},'curve leakage'
        audit['train_counts']={name:sum(v[0]==label for v in train.values()) for name,label in zip(names,labels)}
        audit['test_counts']={name:sum(v[0]==label for v in test.values()) for name,label in zip(names,labels)}
        assert set(audit['train_counts'].values())=={20},audit
        assert all(audit['test_counts'].values()),audit
        matrices={}; targets={}; ids={}
        for split,group in [('train',train),('test',test)]:
            ids[split]=sorted(group); targets[split]=np.array([labels.index(group[i][0]) for i in ids[split]])
            features=[]
            for oid in ids[split]:
                _,curve,digest=group[oid]
                if digest not in cache:
                    curve=curve[np.isfinite(curve).all(1)&(curve[:,2]>0)]
                    curve=curve[np.argsort(curve[:,0],kind='stable')][:200]
                    assert len(curve)>=20,(oid,'insufficient observations')
                    t,y,e=curve.T;t=t-t[0];assert np.ptp(t)>0
                    ls=LombScargle(t,y,e)
                    frequency=np.linspace(.001,20.,65536)
                    power=ls.power(frequency,method='fast',assume_regular_frequency=True)
                    j=int(np.nanargmax(power));lo=frequency[max(j-1,0)];hi=frequency[min(j+1,len(frequency)-1)]
                    opt=minimize_scalar(lambda f:-float(ls.power(f,method='cython')),bounds=(lo,hi),method='bounded',options={'xatol':1e-10})
                    period=1/opt.x
                    vals=extract(curve,period)
                    assert all(np.isfinite(v).all() for v in vals.values())
                    cache[digest]=(vals,period,len(curve))
                features.append(cache[digest][0])
                if len(features)%100==0:print('progress',fold,split,len(features),flush=True)
            matrices[split]={key:np.stack([f[key] for f in features]) for key in arms.values()}
        audit['train_ids']=ids['train'];audit['test_ids']=ids['test'];audits.append(audit)
        for arm,key in arms.items():
            t0=time.perf_counter();clf=model(arm,10000+fold)
            with threadpool_limits(limits=1):
                clf.fit(matrices['train'][key],targets['train']); pred=clf.predict(matrices['test'][key])
            row=dict(fold=fold,arm=arm,macro_f1=f1_score(targets['test'],pred,average='macro'),confusion=confusion_matrix(targets['test'],pred,labels=range(4)).tolist(),seconds=time.perf_counter()-t0)
            records.append(row);np.savez_compressed(root/f'predictions_{fold}_{arm}.npz',ids=ids['test'],true=targets['test'],pred=pred)
        clf=model('timdr_lda',10000+fold)
        with threadpool_limits(limits=1):
            clf.fit(matrices['train']['timdr'],np.random.default_rng(32000+fold).permutation(targets['train']))
            pred=clf.predict(matrices['test']['timdr'])
        records.append(dict(fold=fold,arm='shuffled_timdr',macro_f1=f1_score(targets['test'],pred,average='macro')))
        print('completed fold',fold,{r['arm']:round(r['macro_f1'],4) for r in records if r['fold']==fold},flush=True)
        (root/'audit.json').write_text(json.dumps(audits,indent=2))
        (root/'scores.json').write_text(json.dumps(records,indent=2))
    summary={arm:dict(mean=float(np.mean([r['macro_f1'] for r in records if r['arm']==arm])),std=float(np.std([r['macro_f1'] for r in records if r['arm']==arm],ddof=1))) for arm in [*arms,'shuffled_timdr']}
    summary['seconds']=time.perf_counter()-start;summary['unique_curves']=len(cache)
    summary['protocol_sha256']=hashlib.sha256((root/'PROTOCOL.md').read_bytes()).hexdigest()
    summary['feature_code_sha256']=hashlib.sha256((Path(args.repo)/'features.py').read_bytes()).hexdigest()
    (root/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
    (root/'estimated_periods.json').write_text(json.dumps({k:dict(period=v[1],points=v[2]) for k,v in cache.items()}))

if __name__=='__main__':main()
