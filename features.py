"""Experimental TIMDR-inspired phase/coherence sieve; no class labels used."""
import numpy as np

def fit(phi,z,error):
    h=np.arange(1,9)
    a=2*np.pi*phi[:,None]*h
    X=np.column_stack((np.ones(len(phi)),np.cos(a),np.sin(a)))
    w=1/np.maximum(error,1e-10)**2
    w=np.minimum(w,100*np.median(w)); w/=np.mean(w)
    gram=X.T@(w[:,None]*X)
    beta=np.linalg.solve(gram+np.eye(17)*(.01*np.trace(gram)/17),X.T@(w*z))
    return beta[1:9]-1j*beta[9:17], z-X@beta

def extract(curve,period):
    t,y,e=curve.T
    amp=max(np.percentile(y,95)-np.percentile(y,5),1e-8)
    z=(y-np.median(y))/amp
    phase=((t-t[0])/period)%1
    coef,resid=fit(phase,z,e/amp)
    h=np.arange(1,9)
    aligned=coef*np.exp(-1j*h*np.angle(coef[0]))
    grid=np.exp(2j*np.pi*np.arange(64)[:,None]/64*h)
    raw=(grid@aligned).real
    parts=np.array([fit(phase[ix],z[ix],e[ix]/amp)[0] for ix in np.array_split(np.arange(len(t)),4)])
    coherence=np.clip(np.abs(parts.mean(0))/np.maximum(np.sqrt(np.mean(np.abs(parts)**2,axis=0)),1e-10),0,1)
    filtered=(grid@(aligned*coherence**2)).real
    rel=np.abs(coef)/max(abs(coef[0]),1e-5)
    rel=np.clip(rel,0,100)
    meta=np.array([np.log10(period),np.log10(amp),np.log10(max(np.median(e)/amp,1e-8))])
    centered=z-z.mean(); std=max(z.std(),1e-8)
    moments=[np.mean(centered**3)/std**3,np.mean(centered**4)/std**4,
             np.sqrt(np.mean(resid**2)),np.mean(np.diff(z)**2)/std**2]
    angles=np.angle(aligned[1:])
    classical=np.r_[meta,moments,rel,np.sin(angles),np.cos(angles)]
    return dict(period=meta[:1],classical=classical,phase=np.r_[meta,raw],
                timdr=np.r_[meta,filtered,coherence,rel],filtered=np.r_[meta,filtered])
