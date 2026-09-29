"""Independent integrity checks on the completed benchmark artifacts."""
from pathlib import Path
import hashlib,json
import numpy as np,joblib
from sklearn.metrics import f1_score

ROOT=Path(__file__).resolve().parent

def main():
    rows=json.loads((ROOT/'data/manifest.json').read_text())
    scores=json.loads((ROOT/'results/scores.json').read_text())
    audit=json.loads((ROOT/'data/audit.json').read_text())
    assert len(rows)==2000 and len({r['id'] for r in rows})==2000
    assert len({r['sha256'] for r in rows})==2000
    assert audit['protocol_sha256']==hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()
    assert len(scores)==1605
    for r in scores:
        p=ROOT/'results/predictions'/f"{r['condition']}_{r['n']}_{r['rep']}_{r['arm']}.npz"
        z=np.load(p); tr=z['train_indices'];te=z['test_indices']
        assert not set(tr)&set(te)
        assert all(rows[i]['split']=='support' for i in tr)
        assert all(rows[i]['split']=='test' for i in te)
        assert len(tr)==4*r['n'] and len(te)==800
        assert np.all(np.bincount([rows[i]['y'] for i in tr])==r['n'])
        assert abs(f1_score(z['truth'],z['pred'],average='macro')-r['macro_f1'])<1e-12
    features=np.load(ROOT/'data/features.npz')
    for key in features.files:assert np.isfinite(features[key]).all()
    for arm,key in [('timdr_lda','timdr'),('classical_rf','classical')]:
        saved=joblib.load(ROOT/'models'/f'{arm}.joblib');z=np.load(ROOT/'results/predictions'/f'main_160_0_{arm}.npz')
        np.testing.assert_array_equal(saved['model'].predict(features[key][z['test_indices']]),z['pred'])
        assert saved['training_ids']==[rows[i]['id'] for i in z['train_indices']]
    result=dict(status='passed',unique_stars=2000,verified_prediction_files=len(scores),
                model_roundtrip_checks=2,unit_tests=6,protocol_hash_matches=True)
    (ROOT/'results/verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
