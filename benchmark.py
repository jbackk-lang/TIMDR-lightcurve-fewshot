"""Paired low-label benchmark. Fixed settings, resumable predictions, no tuning."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='1'
from pathlib import Path
import argparse, json, warnings, platform, hashlib
import numpy as np
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import f1_score, recall_score
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits
import joblib, sklearn, scipy

ROOT=Path(__file__).resolve().parent
BUDGETS=[4,8,16,32,64,128,160]
ARMS={'period_lda':'period','classical_rf':'classical','classical_lda':'classical',
      'phase_lda':'phase','timdr_lda':'timdr','phase_mlp':'phase','filtered_lda':'filtered'}

def model(arm,seed):
    if arm=='classical_rf': return RandomForestClassifier(n_estimators=200,min_samples_leaf=2,class_weight='balanced',random_state=seed,n_jobs=1)
    if arm=='phase_mlp': clf=MLPClassifier(hidden_layer_sizes=(64,),activation='tanh',alpha=1,solver='lbfgs',max_iter=400,random_state=seed)
    else: clf=LinearDiscriminantAnalysis(solver='lsqr',shrinkage=.2)
    return make_pipeline(StandardScaler(),clf)

def split(manifest,n,rep):
    y=np.array([r['y'] for r in manifest]); support=np.array([r['split']=='support' for r in manifest])
    rng=np.random.default_rng(10000+rep)
    train=np.concatenate([rng.permutation(np.flatnonzero(support & (y==c)))[:n] for c in range(4)])
    return train,np.flatnonzero(~support),y

def run():
    out=ROOT/'results'; out.mkdir(exist_ok=True)
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    X=np.load(ROOT/'data/features.npz'); bad=np.load(ROOT/'data/features_period_plus1pct.npz')
    predictions=out/'predictions'; predictions.mkdir(exist_ok=True)
    records=[]
    for condition,ns,reps,arms in [('main',BUDGETS,30,list(ARMS)),('period_plus1pct',[4,32,160],5,list(ARMS)),('shuffled_labels',[32],30,['timdr_lda'])]:
        for n in ns:
            for rep in range(reps):
                train,test,y=split(manifest,n,rep); yy=y[train].copy()
                if condition=='shuffled_labels': np.random.default_rng(30000+rep).shuffle(yy)
                for arm in arms:
                    path=predictions/f'{condition}_{n}_{rep}_{arm}.npz'
                    if path.exists():
                        z=np.load(path); pred=z['pred']; converged=bool(z['converged'])
                    else:
                        features=(bad if condition=='period_plus1pct' else X)[ARMS[arm]]
                        clf=model(arm,10000+rep)
                        with warnings.catch_warnings(record=True) as caught, threadpool_limits(limits=1):
                            warnings.simplefilter('always',ConvergenceWarning)
                            clf.fit(features[train],yy); pred=clf.predict(features[test])
                        converged=not any(issubclass(w.category,ConvergenceWarning) for w in caught)
                        np.savez_compressed(path,pred=pred,truth=y[test],test_indices=test,train_indices=train,converged=converged)
                    records.append(dict(condition=condition,n=n,rep=rep,arm=arm,
                                        macro_f1=f1_score(y[test],pred,average='macro'),
                                        recall=recall_score(y[test],pred,average=None).tolist(),converged=converged))
                print(condition,'n=',n,'draw=',rep+1,flush=True)
                (out/'scores.json').write_text(json.dumps(records,indent=2))
    versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__,
                  protocol_sha256=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest())
    (out/'versions.json').write_text(json.dumps(versions,indent=2))
    # Fixed model: first paired support draw, 160/class; not selected on test performance.
    train,test,y=split(manifest,160,0)
    (ROOT/'models').mkdir(exist_ok=True)
    for arm in ['timdr_lda','classical_rf']:
        clf=model(arm,10000)
        with threadpool_limits(limits=1): clf.fit(X[ARMS[arm]][train],y[train])
        joblib.dump(dict(model=clf,arm=arm,classes=['RRab','RRc','CEP-F','CEP-1O'],
                         training_ids=[manifest[i]['id'] for i in train],versions=versions),ROOT/'models'/f'{arm}.joblib')
    summarize()

def summarize():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=ROOT/'results'; records=json.loads((out/'scores.json').read_text())
    main=[r for r in records if r['condition']=='main']; summary={}
    fig,ax=plt.subplots(figsize=(10,6))
    for arm in ARMS:
        vals=np.array([[r['macro_f1'] for r in main if r['n']==n and r['arm']==arm] for n in BUDGETS])
        mean=vals.mean(1); lo,hi=np.percentile(vals,[2.5,97.5],axis=1)
        summary[arm]={str(n):dict(mean=float(mean[i]),p025=float(lo[i]),p975=float(hi[i]),
                     recall=np.mean([r['recall'] for r in main if r['n']==n and r['arm']==arm],axis=0).tolist()) for i,n in enumerate(BUDGETS)}
        ax.plot(BUDGETS,mean,'o-',label=arm); ax.fill_between(BUDGETS,lo,hi,alpha=.08)
    ax.set(xscale='log',xlabel='Labeled stars per class',ylabel='Macro-F1',title='OGLE LMC: fixed 800-star test; 30 paired support draws',ylim=(0,1.02))
    ax.set_xticks(BUDGETS,labels=BUDGETS);ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'learning_curves.png',dpi=180);plt.close(fig)
    rng=np.random.default_rng(99); delta={}
    lookup={(r['n'],r['rep'],r['arm']):r['macro_f1'] for r in main}
    for base in ['classical_rf','phase_lda','classical_lda','filtered_lda']:
        d=np.array([np.mean([lookup[n,r,'timdr_lda']-lookup[n,r,base] for n in [4,8,16,32]]) for r in range(30)])
        boot=d[rng.integers(0,30,(10000,30))].mean(1)
        delta[base]=dict(mean=float(d.mean()),ci95=np.percentile(boot,[2.5,97.5]).tolist())
    # Paired, class-stratified star bootstrap at n=4: support draws held fixed.
    preds={a:np.array([np.load(out/'predictions'/f'main_4_{r}_{a}.npz')['pred'] for r in range(30)]) for a in ['timdr_lda','classical_rf','phase_lda']}
    truth=np.load(out/'predictions/main_4_0_timdr_lda.npz')['truth']; star_delta={}
    def vector_f1(p,t):
        scores=[]
        for c in range(4):
            tp=((p==c)&(t==c)).sum(1); den=(p==c).sum(1)+(t==c).sum()
            scores.append(2*tp/np.maximum(den,1))
        return np.mean(scores,axis=0).mean()
    boot={a:[] for a in ['classical_rf','phase_lda']}
    for _ in range(2000):
        ix=np.concatenate([rng.choice(np.flatnonzero(truth==c),200,replace=True) for c in range(4)])
        t=truth[ix]; score=vector_f1(preds['timdr_lda'][:,ix],t)
        for a in boot: boot[a].append(score-vector_f1(preds[a][:,ix],t))
    for a,v in boot.items(): star_delta[a]=np.percentile(v,[2.5,97.5]).tolist()
    diagnostic={}
    for condition in ['period_plus1pct','shuffled_labels']:
        diagnostic[condition]={a:{str(n):float(np.mean([r['macro_f1'] for r in records if r['condition']==condition and r['arm']==a and r['n']==n])) for n in sorted({r['n'] for r in records if r['condition']==condition})} for a in sorted({r['arm'] for r in records if r['condition']==condition})}
    report=dict(main=summary,primary_deltas=delta,test_star_bootstrap_n4_ci95=star_delta,diagnostics=diagnostic,
                nonconverged_runs=sum(not r['converged'] for r in records),n_runs=len(records),astromer='not_run')
    (out/'summary.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(primary_deltas=delta,nonconverged_runs=report['nonconverged_runs']),indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--summarize',action='store_true');args=p.parse_args()
    summarize() if args.summarize else run()
