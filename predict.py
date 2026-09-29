"""Classify one I-band light curve, with a supplied period in days."""
from pathlib import Path
import argparse,json
import joblib,numpy as np
from features import extract
from prepare import clean

ROOT=Path(__file__).resolve().parent

def predict(path,period,arm='timdr_lda'):
    if not np.isfinite(period) or period<=0: raise ValueError('Period must be finite and positive, in days.')
    # Accept OGLE whitespace .dat or CSV time,magnitude,error with header.
    if path.suffix.lower()=='.csv':
        table=np.genfromtxt(path,delimiter=',',names=True)
        expected=('time','magnitude','error')
        if not set(expected)<=set(table.dtype.names or []): raise ValueError('CSV requires time,magnitude,error columns.')
        curve=np.column_stack([np.atleast_1d(table[k]) for k in expected])
    else: curve=np.loadtxt(path)
    curve=np.atleast_2d(curve)
    if curve.shape[1]!=3: raise ValueError('Exactly three columns required: time, magnitude, error.')
    curve=clean(curve)
    if len(curve)<80: raise ValueError('At least 80 valid unique observation times required.')
    coverage=len(np.unique(np.floor(((curve[:,0]-curve[0,0])/period%1)*32)))/32
    if coverage<.75: raise ValueError('Insufficient phase coverage: at least 24 of 32 bins required.')
    if np.ptp(curve[:,1])<1e-6: raise ValueError('Constant curve cannot be classified.')
    saved=joblib.load(ROOT/'models'/f'{arm}.joblib')
    f=extract(curve,period)['timdr' if arm=='timdr_lda' else 'classical'][None,:]
    clf=saved['model'];prob=clf.predict_proba(f)[0];c=int(clf.predict(f)[0])
    return dict(predicted_class=saved['classes'][c],period_days=period,n_observations=len(curve),phase_coverage=coverage,
                scores={saved['classes'][int(k)]:float(v) for k,v in zip(clf.classes_,prob)},
                caveat='Uncalibrated closed-set scores, not probabilities of astrophysical truth. LMC OGLE I-band only; unknown classes are not detected.',
                model=arm)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('curve',type=Path)
    p.add_argument('--period',type=float,required=True);p.add_argument('--model',choices=['timdr_lda','classical_rf'],default='timdr_lda')
    p.add_argument('--output',type=Path);a=p.parse_args()
    result=json.dumps(predict(a.curve,a.period,a.model),indent=2)
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(result)
    print(result)
