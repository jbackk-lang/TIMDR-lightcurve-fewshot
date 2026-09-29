import json
from pathlib import Path
import numpy as np
from sklearn.metrics import f1_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=Path(__file__).resolve().parent
s=json.loads((p/'summary.json').read_text());rows=json.loads((p/'scores.json').read_text());audit=json.loads((p/'audit.json').read_text())
for f in p.glob('predictions_*.npz'):
    d=np.load(f);parts=f.stem.split('_');fold=int(parts[1]);arm='_'.join(parts[2:])
    expected=next(r['macro_f1'] for r in rows if r['fold']==fold and r['arm']==arm)
    assert abs(f1_score(d['true'],d['pred'],average='macro')-expected)<1e-12
arms=['period_lda','phase_lda','timdr_lda','classical_rf','shuffled_timdr']
names=['Sam okres + LDA','Faza bez sita + LDA','TIMDR + LDA','Cechy klasyczne + RF','TIMDR: losowe etykiety']
fig,ax=plt.subplots(figsize=(9,5));ax.bar(names,[s[a]['mean'] for a in arms],yerr=[s[a]['std'] for a in arms],color=['gray','#66a5ad','#318d7a','#e4ab46','lightgray'],capsize=5)
ax.set(ylim=(0,1),ylabel='Macro-F1',title='ATLAS: tani pilot, 20 etykiet na klasę, 3 podziały\nOkres oszacowany z obserwacji; słupki błędów = SD podziałów')
ax.tick_params(axis='x',labelrotation=18);fig.tight_layout();fig.savefig(p/'comparison.png',dpi=160)
text='# ATLAS — wynik taniego pilota\n\n'
text+='Nie jest to bezpośrednia replikacja wykresu ASTROMER 2. Publiczne archiwum i sposób podania krzywych różnią się od końcowego protokołu pracy.\n\n'
text+='20 etykiet na klasę, 3 oficjalne podziały archiwum, 4 klasy: CB, DB, Mira, Pulse. Bez trenowania sieci i płatnych usług. Okres oszacowany z tych samych maksymalnie 200 pomiarów dla wszystkich metod.\n\n'
text+='| Metoda | Macro-F1 (średnia ± SD) |\n|---|---:|\n'
for a,n in zip(arms,names):text+=f'| {n} | {100*s[a]["mean"]:.2f}% ± {100*s[a]["std"]:.2f} pp |\n'
delta_phase=100*(s['timdr_lda']['mean']-s['phase_lda']['mean'])
delta_rf=100*(s['timdr_lda']['mean']-s['classical_rf']['mean'])
text+=f'\nRóżnica TIMDR względem fazy bez sita: {delta_phase:+.2f} punktu procentowego; względem lasu losowego: {delta_rf:+.2f} pp. To mały pilot, nie dowód statystyczny przewagi.\n'
if delta_phase<=0 and delta_rf<=0:
    text+='Aktualna adaptacja TIMDR nie poprawiła wyniku względem obu tych punktów odniesienia. Najwyższa średnia wśród badanych właściwych modeli należy do '+max(arms[:-1],key=lambda a:s[a]['mean'])+'.\n'
text+='\n## Zakres i ograniczenia\n\n'
text+=f'Czas obliczeń po importach: {s["seconds"]:.1f} s. Unikalnych krzywych poddanych ekstrakcji: {s["unique_curves"]}. Pobranie wybranego podzbioru: około 5 MB zamiast 1 GB.\n\n'
text+='Liczby obiektów testowych według klas, po deduplikacji:\n\n'
for a in audit:text+=f'- Podział {a["fold"]}: {a["test_counts"]}; usunięte powtórzenia testowe: {a["duplicates"]["test"]}.\n'
text+='\nZbiory train i val połączono bez strojenia parametrów (16+4 etykiety na klasę). Etykiety odczytano z rekordów, nie z nazw folderów. Sprawdzono rozłączność identyfikatorów i identycznych krzywych między treningiem a testem. Powtórzenia między podziałami oznaczają, że nie są to trzy niezależne przeglądy nieba.\n\n'
text+='Estymator okresu ma ograniczoną siatkę i nie rozstrzyga aliasów ani podwojenia okresu układów podwójnych. Ten wynik ocenia aktualny model razem z tym uproszczonym zegarem. Brak strojenia po wyniku; słaby wynik nie dowodzi nieskuteczności wszystkich adaptacji TIMDR.\n\n'
text+='## ASTROMER 2 — wyłącznie zewnętrzne odniesienie\n\nNa dostarczonym wykresie A2 + Skip Conn ma F1 70,5% przy 20, 74,6% przy 100 i 78,9% przy 500 etykietach na klasę. Te wartości nie zostały tu ponownie obliczone. Nie odejmujemy ich od wyniku pilota jako miary przewagi: wymagane jest potwierdzenie tych samych obiektów, okien i podziałów. W tym pilocie nie wykonano wariantów 100/500 ani treningu A2, aby ograniczyć koszt.\n\n'
text+='Źródła: [kod ASTROMER 2](https://github.com/astromer-science/main-code), [praca](https://arxiv.org/abs/2502.02717), [odnośnik do danych](https://github.com/astromer-science/main-code/blob/main/data/get_data.sh).\n\nPredykcje wszystkich 12 właściwych klasyfikatorów sprawdzono przez ponowne obliczenie F1. Protokół, sumy kontrolne danych, identyfikatory, oszacowane okresy i kod znajdują się obok raportu.\n'
(p/'RAPORT.md').write_text(text,encoding='utf-8');print(text[:1600])
