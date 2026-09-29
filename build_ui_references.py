"""Package the first held-out star of each class; no score-based selection."""
from pathlib import Path
import json,numpy as np
from ui_analysis import signal_view
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/'data/manifest.json').read_text());curves=np.load(ROOT/'data/curves.npz');refs=[]
for c in range(4):
    row=next(r for r in rows if r['y']==c and r['split']=='test');curve=curves[row['id']]
    s=signal_view(curve,row['period']);family='rrlyr' if c<2 else 'cep'
    refs.append(dict(id=row['id'],label=row['label'],period=row['period'],curve=curve.tolist(),grid=s['grid'].tolist(),
                     template=s['raw'].tolist(),source=f"https://www.astrouw.edu.pl/ogle/ogle4/OCVS/lmc/{family}/phot/I/{row['id']}.dat"))
(ROOT/'examples/ogle_references.json').write_text(json.dumps(refs,ensure_ascii=False),encoding='utf-8')
print('Packaged four OGLE reference curves.')

folder=ROOT/'examples/tutorial';folder.mkdir(exist_ok=True)
samples=[]
def add(key,title,description,curve,period,expected,pmin=.2,pmax=30):
    path=folder/(key+'.csv')
    np.savetxt(path,curve,delimiter=',',header='time,magnitude,error',comments='',fmt='%.10f')
    samples.append(dict(key=key,title=title,description=description,text=path.read_text(),period=period,
                        expected=expected,pmin=pmin,pmax=pmax,filename=path.name))
for ref in refs:
    add(ref['label'],f"OGLE · {ref['label']}",f"Rzeczywista gwiazda {ref['id']}, pasmo I. Okres katalogowy: {ref['period']} dnia.",
        np.array(ref['curve']),ref['period'],'Zobacz krzywą fazową, harmoniczne i porównanie modeli. Wynik może różnić się od etykiety katalogowej.')
base=np.array(refs[0]['curve']);p=refs[0]['period'];phase=((base[:,0]-base[0,0])/p)%1
add('few-points','Za mało punktów','Pierwsze 35 rzeczywistych pomiarów RRab. Celowo skrócony przykład edukacyjny.',base[:35],p,'Klasyfikacja zostanie wstrzymana: mniej niż 80 pomiarów.')
add('phase-gaps','Luki w fazie','Krzywa RRab z celowo usuniętymi pomiarami fazy 0,65–1,00.',base[phase<.65],p,'Klasyfikacja zostanie wstrzymana: mniej niż 24/32 przedziałów fazy.')
noisy=base.copy();noisy[:,2]=.4
add('large-errors','Duże błędy pomiaru','Oryginalne jasności RRab z celowo zmienionym błędem na 0,4 mag. To test kontroli jakości, nie nowa obserwacja.',noisy,p,'Klasyfikacja zostanie wstrzymana: błąd jest zbyt duży względem amplitudy.')
add('wrong-period','Okres błędny o 1%','Te same pomiary RRab, ale wpisany okres zwiększono o 1%. Jasności nie zmieniono.',base,p*1.01,'Zobacz rozmycie fazy i spadek spójności harmonicznych. Ocena okresu powinna wymagać sprawdzenia.')
add('unknown-period','Nie znam okresu','Rzeczywiste pomiary RRab bez podanego okresu. Zakres demonstracyjny 0,5–0,65 dnia obejmuje znany okres katalogowy.',base,None,'Wybierz „Szukaj okresu”, a potem obejrzyj jednego z kandydatów. Zakres w tym przykładzie jest ułatwieniem.',.5,.65)
(ROOT/'examples/ui_examples.json').write_text(json.dumps(samples,ensure_ascii=False),encoding='utf-8')
(folder/'README.md').write_text('# Przykłady do interfejsu\n\n'+ '\n\n'.join(f"## {r['title']}\n`{r['filename']}`\n\n{r['description']}\n\nOczekiwane zachowanie: {r['expected']}" for r in samples)+'\n\nPomiary źródłowe: OGLE LMC, pasmo I. Przypadki problemowe są celowymi modyfikacjami edukacyjnymi, nie danymi do oceny skuteczności modelu.\n',encoding='utf-8')
print('Packaged',len(samples),'downloadable tutorial examples.')
