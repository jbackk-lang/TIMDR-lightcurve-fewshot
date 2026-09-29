import os
os.environ['TF_USE_LEGACY_KERAS']='1'
os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
os.environ['TF_ENABLE_ONEDNN_OPTS']='0'
os.environ['OMP_NUM_THREADS']='2'
from pathlib import Path
import hashlib,json,urllib.request,zipfile,traceback
import numpy as np

ROOT=Path(__file__).resolve().parent

def run():
    import tensorflow as tf
    tf.config.threading.set_intra_op_parallelism_threads(2)
    tf.config.threading.set_inter_op_parallelism_threads(1)
    tf.random.set_seed(120)
    from ASTROMER.models import SingleBandEncoder
    from benchmark import split,model,BUDGETS
    from sklearn.metrics import f1_score,recall_score
    from threadpoolctl import threadpool_limits
    os.chdir(ROOT)
    directory=ROOT/'weights';directory.mkdir(exist_ok=True)
    archive=directory/'macho_a0.zip'
    if not archive.exists():
        url='https://github.com/astromer-science/weights/raw/main/macho_a0.zip'
        with urllib.request.urlopen(url,timeout=120) as src,archive.open('wb') as dst:
            while chunk:=src.read(1024*1024):dst.write(chunk)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            dest=(directory/info.filename).resolve()
            if not dest.is_relative_to(directory.resolve()):raise ValueError('Unsafe archive member')
            if info.is_dir():dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                if not dest.exists():dest.write_bytes(z.read(info))
    encoder=SingleBandEncoder.from_pretraining(None,'macho')
    manifest=json.loads((ROOT/'data/manifest.json').read_text()); curves=np.load(ROOT/'data/curves.npz')
    cache=ROOT/'data/astromer';cache.mkdir(exist_ok=True)
    for start in range(0,len(manifest),16):
        rows=[r for r in manifest[start:start+16] if not (cache/(r['id']+'.npy')).exists()]
        if not rows:continue
        ids=[r['id'] for r in rows]
        # Official encode returns embeddings sorted by ID when concatenate=True.
        encoded=encoder.encode([curves[i] for i in ids],oids_list=ids,batch_size=16,concatenate=True)
        if len(encoded)!=len(ids):raise ValueError('Embedding count mismatch')
        for ident,emb in zip(sorted(ids),encoded):
            a=np.asarray(emb);v=a.mean(0)
            n=len(curves[ident])
            expected=n if n<encoder.maxlen else (n//encoder.maxlen+1)*encoder.maxlen
            if a.ndim!=2 or len(a)!=expected or not np.isfinite(v).all():
                raise ValueError(f'Invalid embedding shape or missing observations: {ident} {a.shape}')
            np.save(cache/(ident+'.npy'),v)
        print('ASTROMER encoded',min(start+16,len(manifest)),flush=True)
    meta=np.load(ROOT/'data/features.npz')['phase'][:,:3]
    X=np.column_stack((meta,np.stack([np.load(cache/(r['id']+'.npy')) for r in manifest])))
    np.save(ROOT/'data/astromer_features.npy',X)
    records=[];pred_dir=ROOT/'results/astromer_predictions';pred_dir.mkdir(exist_ok=True)
    for n in BUDGETS:
        for rep in range(30):
            tr,te,y=split(manifest,n,rep);clf=model('astromer_lda',10000+rep)
            with threadpool_limits(limits=1):clf.fit(X[tr],y[tr]);pred=clf.predict(X[te])
            records.append(dict(n=n,rep=rep,macro_f1=float(f1_score(y[te],pred,average='macro')),
                                recall=recall_score(y[te],pred,average=None).tolist()))
            np.savez_compressed(pred_dir/f'{n}_{rep}.npz',pred=pred,truth=y[te],train_indices=tr,test_indices=te)
        print('ASTROMER scored n=',n,flush=True)
    (ROOT/'results/astromer_scores.json').write_text(json.dumps(records,indent=2))
    summary={str(n):float(np.mean([r['macro_f1'] for r in records if r['n']==n])) for n in BUDGETS}
    status=dict(status='completed',summary=summary,weights_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
      description='Wykonano dodatkowe porównanie z zamrożonym ASTROMER 1 (MACHO, biblioteka 0.1.8), średnią embeddingów i LDA. Te same gwiazdy, etykiety, metadane i losowania. Brak dostrajania na OGLE. Możliwe pokrywanie się fizycznych gwiazd z korpusem MACHO nie zostało wykluczone; to porównanie eksploracyjne, bez dowodu przewagi nad modelami foundation. Wyniki: '+json.dumps(summary))
    (ROOT/'results/astromer_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')

if __name__=='__main__':
    try:run()
    except Exception as e:
        (ROOT/'results').mkdir(exist_ok=True)
        (ROOT/'results/astromer_error.txt').write_text(traceback.format_exc(),encoding='utf-8')
        (ROOT/'results/astromer_status.json').write_text(json.dumps(dict(status='failed',error=str(e),
            description='Próba uruchomienia pretrained ASTROMER nie zakończyła się poprawną oceną: '+str(e)+'. Nie przypisano wyniku. Nie ma podstaw do twierdzenia o przewadze nad modelem wstępnie uczonym.'),indent=2),encoding='utf-8')
        raise
