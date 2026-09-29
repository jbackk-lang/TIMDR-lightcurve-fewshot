"""Observable diagnostics and cautious explanations; frozen trained features unchanged."""
from pathlib import Path
import json
import numpy as np
import joblib
from functools import lru_cache
from features import fit,extract
from ui_import import parse_table

ROOT=Path(__file__).resolve().parent

@lru_cache(maxsize=2)
def load_model(arm):return joblib.load(ROOT/'models'/f'{arm}.joblib')

def noise_for_diagnostics(a):
    e=a[:,2].copy();good=np.isfinite(e)&(e>0)
    fallback=float(np.median(e[good])) if good.any() else max(np.std(a[:,1])*.1,1e-4)
    e[~good]=fallback
    return e

def signal_view(a,p):
    t,y,_=a.T;e=noise_for_diagnostics(a)
    amp=max(float(np.percentile(y,95)-np.percentile(y,5)),1e-8)
    z=(y-np.median(y))/amp;phi=((t-t[0])/p)%1
    coef,res=fit(phi,z,e/amp);h=np.arange(1,9);origin=np.angle(coef[0])
    aligned=coef*np.exp(-1j*h*origin)
    parts=np.array([fit(phi[ix],z[ix],e[ix]/amp)[0] for ix in np.array_split(np.arange(len(t)),4)])
    coherence=np.clip(abs(parts.mean(0))/np.maximum(np.sqrt(np.mean(abs(parts)**2,axis=0)),1e-10),0,1)
    grid=np.linspace(0,1,257);basis=np.exp(2j*np.pi*grid[:,None]*h)
    raw=(basis@aligned).real;filtered=(basis@(aligned*coherence**2)).real
    offset=float(np.mean(z-res-(np.exp(2j*np.pi*phi[:,None]*h)@coef).real))
    segment_fit=np.array([(basis@(c*np.exp(-1j*h*origin))).real for c in parts])
    agreement=np.clip(np.cos(np.angle(parts*np.conj(coef)[None,:])),0,1)
    energy=float(np.sum(abs(coef)**2));after=float(np.sum(abs(coef*coherence**2)**2))
    bright=int(np.argmin(raw[:-1]));faint=int(np.argmax(raw[:-1]));rise=((bright-faint)%256)/256
    counts=np.bincount(np.minimum((phi*32).astype(int),31),minlength=32)
    return dict(phase=phi,aligned_phase=(phi+origin/(2*np.pi))%1,grid=grid,raw=raw,filtered=filtered,
                normalized=z,amplitude=amp,median=float(np.median(y)),baseline=float(np.median(y)+amp*offset),coherence=coherence,
                harmonic_amplitude=abs(coef)*amp,harmonic_after=abs(coef)*amp*coherence**2,
                segment_templates=segment_fit,segment_agreement=agreement,counts=counts,
                attenuated_energy_pct=100*(1-after/max(energy,1e-15)),rise_fraction=rise,
                residual_ratio=float(np.sqrt(np.mean(res**2))),cycles=float(np.ptp(t)/p))

def search_period(a,pmin,pmax):
    from astropy.timeseries import LombScargle
    from scipy.optimize import minimize_scalar
    pmin=float(pmin);pmax=float(pmax);span=float(np.ptp(a[:,0]))
    if len(a)<20 or span<=0:raise ValueError('Do szukania okresu potrzeba co najmniej 20 punktów z różnych chwil.')
    if not 0<pmin<pmax or not np.isfinite([pmin,pmax]).all():raise ValueError('Zakres okresu musi być dodatni i rosnący.')
    n=int(np.ceil(5*span*(1/pmin-1/pmax)))+1
    if n>200000:raise ValueError('Zakres wymaga zbyt gęstej siatki. Zawęź zakres okresu; nie będziemy pomijać wąskich pików.')
    if np.std(a[:,1])<1e-8:raise ValueError('Stała jasność: nie ma sygnału do wyznaczenia okresu.')
    ls=LombScargle(a[:,0]-a[0,0],a[:,1],noise_for_diagnostics(a))
    freq=np.linspace(1/pmax,1/pmin,max(n,1000));power=ls.power(freq,method='fast')
    power=np.nan_to_num(power,nan=0,posinf=0,neginf=0)
    candidates=[]
    for i in np.argsort(power)[::-1]:
        if not any(abs(freq[i]-c['frequency'])<1/span for c in candidates):
            candidates.append(dict(period=float(1/freq[i]),power=float(power[i]),frequency=float(freq[i])))
        if len(candidates)==5:break
    step=freq[1]-freq[0]
    for c in candidates:
        optimum=minimize_scalar(lambda f:-float(ls.power(f,method='cython')),
                                bounds=(max(freq[0],c['frequency']-step),min(freq[-1],c['frequency']+step)),
                                method='bounded',options={'xatol':1e-12})
        if optimum.success:c.update(frequency=float(optimum.x),period=float(1/optimum.x),power=float(-optimum.fun))
    candidates.sort(key=lambda c:c['power'],reverse=True)
    try:
        fap=float(ls.false_alarm_probability(min(candidates[0]['power'],.999999),minimum_frequency=freq[0],maximum_frequency=freq[-1]))
        if not np.isfinite(fap):fap=None
    except (ValueError,ZeroDivisionError):fap=None
    # Peak-preserving overview: max within each block, not uniform decimation.
    blocks=np.array_split(np.arange(len(freq)),min(1800,len(freq)))
    ix=np.array([b[np.argmax(power[b])] for b in blocks])
    return dict(candidates=candidates,frequency=freq[ix].tolist(),power=power[ix].tolist(),fap=fap,
                grid_points=len(freq),span_days=span,
                note='Kandydaci Lomb–Scargle, nie potwierdzone okresy. Aliasy dobowe oraz P/2 i 2P mogą dawać podobne piki. FAP dotyczy modelu szumu Gaussa, nie prawdopodobieństwa poprawności okresu.')

def analyze(payload):
    a,stats,meta=parse_table(payload.get('text',''),payload.get('mapping',{}),payload.get('time_unit','days'),
                             payload.get('band',''),payload.get('object',''))
    period=payload.get('period');p=None if period in (None,'') else float(period)
    if p is not None and (not np.isfinite(p) or p<=0):raise ValueError('Okres musi być dodatnią, skończoną liczbą dni.')
    warnings=[];blockers=[];tips=[]
    def issue(message,tip=None,block=False):
        (blockers if block else warnings).append(message)
        if tip and tip not in tips:tips.append(tip)
    n=len(a);t,y,e=a.T;span=float(np.ptp(t));amp=float(np.percentile(y,95)-np.percentile(y,5))
    if n<80:issue(f'Za mało punktów: {n}/80.', 'Zbierz co najmniej 80 pomiarów, najlepiej ponad 120 rozłożonych w całym cyklu.',True)
    if stats['bad_error']:issue(f"Brak dodatniego błędu magnitudo w {stats['bad_error']} wierszach.",'Wyeksportuj niepewności pomiarów z programu fotometrycznego. Nie wpisuj zera ani wymyślonego błędu.',True)
    if stats['bad_time']:issue(f"Pominięto {stats['bad_time']} wierszy z błędnym czasem.",'Sprawdź format daty i wybraną jednostkę czasu.')
    if stats['bad_magnitude'] or stats['limits']:issue(f"Pominięto nieprawidłowe magnitudo: {stats['bad_magnitude']}; granice jasności: {stats['limits']}.",'Użyj pomiarów magnitudo; strumień i granice jasności wymagają osobnej analizy.')
    if stats['duplicates']:issue(f"Połączono {stats['duplicates']} powtórzeń czasu. Nie są dodatkowymi niezależnymi obserwacjami.")
    if stats['unsorted_steps']:issue('Wiersze nie były chronologiczne; uporządkowano je po czasie.')
    if meta['unit']=='iso':issue('Daty ISO bez strefy potraktowano jako UTC; nie wykonano korekty heliocentrycznej ani barycentrycznej.')
    gaps=np.diff(t);cad=float(np.median(gaps[gaps>0])) if np.any(gaps>0) else 0
    ix=np.flatnonzero(gaps>max(5*cad,1e-12))
    gap_rows=[dict(start=float(t[i]),end=float(t[i+1]),days=float(gaps[i])) for i in ix[np.argsort(gaps[ix])[::-1]][:12]]
    if len(ix):issue(f'Wykryto {len(ix)} przerw dłuższych niż 5× mediana odstępu między pomiarami.','Zaplanuj kolejne noce tak, aby uzupełnić puste przedziały fazy.')
    if span>100000:issue('Bardzo duży zakres czasu: możliwe połączenie JD/MJD albo pomylenie sekund i dni.','Ujednolić format i jednostkę czasu przed klasyfikacją.',True)
    if amp<1e-6:issue('Krzywa jest stała lub ma znikomą amplitudę.','Sprawdź kolumnę magnitudo oraz kalibrację fotometrii.',True)
    finite=e[np.isfinite(e)&(e>0)];median_error=float(np.median(finite)) if len(finite) else None
    relative_error=median_error/max(amp,1e-8) if median_error is not None else None
    if relative_error is not None and relative_error>.25:issue('Błąd pomiaru jest duży względem amplitudy (ponad 25%).','Popraw ostrość, dobierz ekspozycję bez nasycenia i sprawdź gwiazdy porównania.',True)
    mad=float(np.median(abs(y-np.median(y))));outliers=int(np.sum(abs(y-np.median(y))>8*max(mad,1e-8)))
    if outliers:issue(f'{outliers} punktów odstaje od mediany o ponad 8 MAD. Nie usunięto ich automatycznie.','Sprawdź nasycenie, chmury, ślady satelitów i poprawność apertury dla odstających punktów.')
    band=(meta['band'] or payload.get('declared_band','unknown')).strip()
    if band.upper() not in ('I','IC','I_C'):
        issue(f'Pasmo „{band}”: modele sprawdzono na OGLE I. Wynik poza tym pasmem jest eksperymentalny.',
              'Użyj pojedynczego pasma; porównanie z modelem OGLE I wymaga osobnej walidacji dla DSLR, V i innych filtrów.',not bool(payload.get('allow_experimental',False)))
    view=None;classification=None;explanations=[];period_info=None;sensitivity=[]
    if p is None:issue('Okres nie został podany — dostępna jest diagnostyka, bez klasyfikacji.','Uruchom szukanie okresu i sprawdź kandydatów na wykresie fazowym.',True)
    elif n>=20 and span>0 and amp>=1e-6:
        view=signal_view(a,p);occupied=int(np.count_nonzero(view['counts']))
        if occupied<24:issue(f'Niepełne pokrycie fazy: {occupied}/32 (minimum 24).','Dookreśl okres i obserwuj w pustych przedziałach fazy zaznaczonych na pasku.',True)
        if view['cycles']<2:issue('Obserwacje obejmują mniej niż dwa cykle.','Wydłuż obserwacje do co najmniej 2–3 cykli; nie potwierdzaj okresu na jednym fragmencie.',True)
        quality='wymaga sprawdzenia'
        if view['coherence'][0]>=.8 and view['residual_ratio']<.2 and view['cycles']>=3:quality='zgodny z danymi — nadal możliwe aliasy'
        else:issue('Okres lub powtarzalność kształtu budzą wątpliwości.','Porównaj inne piki okresogramu oraz P/2 i 2P. Sprawdź wspólną skalę czasu i synchronizację aparatu.')
        for factor in [.99,1,1.01]:
            sv=signal_view(a,p*factor)
            sensitivity.append(dict(factor=factor,period=p*factor,residual=sv['residual_ratio'],coherence=float(sv['coherence'][0])))
        base=sensitivity[1]['residual'];best=min(sensitivity,key=lambda r:r['residual'])
        if best['factor']!=1 and best['residual']<.85*base:
            issue('Zmiana okresu o 1% poprawia dopasowanie. Podany okres może być błędny.','Sprawdź dokładniejszy okres; test ±1% nie jest estymacją niepewności.')
            quality='podejrzenie błędnego okresu'
        period_info=dict(status=quality,cycles=view['cycles'],sensitivity=sensitivity)
        stable=[i+1 for i,c in enumerate(view['coherence']) if c>=.8]
        explanations=[f"Rozjaśnianie w dopasowanym cyklu zajmuje około {100*view['rise_fraction']:.0f}% okresu. To opis asymetrii, nie samodzielny dowód klasy.",
                      'Składowe o zgodności co najmniej 0,8: '+(', '.join(map(str,stable)) if stable else 'brak')+'. Próg jest diagnostyczny, nie oznacza pewności klasyfikacji.',
                      f"Sito osłabiło {view['attenuated_energy_pct']:.1f}% energii dopasowanych harmonicznych. Nie odrzucało punktów ani fragmentów obserwacji."]
        if not blockers:
            x=extract(a,p);classification={}
            for arm,key in [('timdr_lda','timdr'),('classical_rf','classical')]:
                saved=load_model(arm);model=saved['model'];xx=x[key][None,:]
                label=saved['classes'][int(model.predict(xx)[0])];scores=model.predict_proba(xx)[0]
                classification[arm]=dict(label=label,scores={saved['classes'][int(c)]:float(s) for c,s in zip(model.classes_,scores)})
            if classification['timdr_lda']['label']!=classification['classical_rf']['label']:
                issue('Modele wskazują różne klasy — wynik jest niejednoznaczny.','Porównaj krzywą z przykładami OGLE i zbierz dodatkowe obserwacje.')
    elif p is not None:issue('Za mało danych lub brak zmienności do analizy harmonicznych.',block=True)
    points=np.linspace(0,n-1,min(n,2500),dtype=int)
    result=dict(stats=stats,band=band,quality=dict(blockers=blockers,warnings=warnings,tips=tips,ready=classification is not None),
                raw=dict(time=t[points].tolist(),magnitude=y[points].tolist(),error=[float(v) if np.isfinite(v) else None for v in e[points]],displayed=len(points),total=n),
                metrics=dict(span_days=span,amplitude=amp,median_error=median_error,relative_error=relative_error,outliers=outliers,cadence_days=cad),
                gaps=gap_rows,gap_count=len(ix),classification=classification,explanations=explanations,period=p,period_info=period_info,
                error_values=finite[np.linspace(0,len(finite)-1,min(len(finite),2500),dtype=int)].tolist() if len(finite) else [])
    if view:
        result['signal']={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in view.items() if k not in ('phase','aligned_phase','normalized')}
        result['signal'].update(phase=view['aligned_phase'][points].tolist(),normalized=view['normalized'][points].tolist(),
                                time_phase=view['phase'][points].tolist())
    return result

def json_safe(obj):
    if isinstance(obj,float) and not np.isfinite(obj):return None
    if isinstance(obj,dict):return {k:json_safe(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [json_safe(v) for v in obj]
    return obj
