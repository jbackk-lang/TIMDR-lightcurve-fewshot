from pathlib import Path
import json,hashlib,shutil
import numpy as np

ROOT=Path(__file__).resolve().parent

def main():
    s=json.loads((ROOT/'results/summary.json').read_text());main=s['main']
    names={'period_lda':'Tylko okres + LDA','classical_rf':'Cechy klasyczne + las losowy',
           'classical_lda':'Cechy klasyczne + LDA','phase_lda':'Krzywa fazowa + LDA',
           'timdr_lda':'TIMDR + LDA','phase_mlp':'Krzywa fazowa + mała sieć',
           'filtered_lda':'Samo sito + LDA'}
    budgets=[4,8,16,32,64,128,160]
    table='| Metoda | '+' | '.join(map(str,budgets))+' |\n|---|'+'---:|'*7+'\n'
    for a,label in names.items():table+='| '+label+' | '+' | '.join(f"{main[a][str(n)]['mean']:.3f}" for n in budgets)+' |\n'
    d=s['primary_deltas']['classical_rf'];p=s['primary_deltas']['phase_lda']
    positive=d['mean']>=.02 and d['ci95'][0]>0
    verdict='Pierwotny cel przewagi nad lasem losowym został spełniony w tym pilotażu.' if positive else 'Pierwotny cel przewagi nad lasem losowym nie został spełniony w tym pilotażu.'
    lines=['# Wyniki: TIMDR-lightcurve-fewshot — pilotaż OGLE LMC','',verdict,'',
      'Model działa na rzeczywistych danych i został zapisany. Poniższe wyniki dotyczą znanych okresów katalogowych, czterech znanych klas i jednego przeglądu. Nie rozstrzygają o skuteczności na nowych przeglądach ani przy nieznanym okresie.','',
      '## Zbiór i test','',
      '2000 gwiazd: po 500 RRab, RRc, CEP-F, CEP-1O. Pula ucząca: 300 na klasę; niezależny od niej, stały test: 200 na klasę. 30 identycznych dla metod, zagnieżdżonych losowań przykładów przy każdym budżecie. Łącznie 1470 głównych dopasowań oraz 135 dopasowań kontrolnych. Gwiazda jest jednostką podziału, nie pojedynczy pomiar ani wycinek. Usunięto duplikaty fotometrii i pozycje bliższe niż 2 sekundy łuku. Nie dobierano parametrów na teście.','',
      '## Średnie macro-F1','',
      'Kolumny oznaczają liczbę etykiet na klasę. Macro-F1 nie jest procentem poprawnych wskazań. Wszystkie metody poza kontrolą samego okresu dostają okres, amplitudę oraz względny błąd pomiaru.', '',table,
      '![Krzywe uczenia](results/learning_curves.png)','',
      '## Porównanie zaplanowane przed wynikami','',
      f"Średnia różnica TIMDR − las losowy dla 4, 8, 16 i 32 etykiet: **{d['mean']:+.4f} macro-F1**, 95% przedział bootstrap z losowań uczących [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}]. Cel praktyczny: co najmniej +0.02 i dolna granica powyżej zera.",'',
      f"TIMDR − krzywa fazowa przy tym samym LDA: **{p['mean']:+.4f}**, przedział [{p['ci95'][0]:+.4f}, {p['ci95'][1]:+.4f}]. Wariant „samo sito” oddziela efekt filtrowania od efektu dodania cech koherencji i harmonicznych.",'',
      'Przedziały z 30 losowań opisują zmienność doboru etykiet na jednym teście. Nie są 30 niezależnymi powtórzeniami na populacji gwiazd. Dodatkowy bootstrap gwiazd testowych przy n=4 utrzymuje losowania uczące stałe; też nie mierzy transferu między przeglądami.','']
    for a,ci in s['test_star_bootstrap_n4_ci95'].items():lines.append(f"- Bootstrap gwiazd przy 4 etykietach, TIMDR − {names[a]}: [{ci[0]:+.4f}, {ci[1]:+.4f}].")
    lines+=['','## Kontrole','',f"Pomieszane etykiety, n=32: macro-F1 **{s['diagnostics']['shuffled_labels']['timdr_lda']['32']:.3f}**. Przy czterech zrównoważonych klasach orientacyjny wynik losowy wynosi 0.25; dokładne macro-F1 zależy od rozkładu predykcji.",'',
            '| Metoda | Prawidłowy okres, n=4 (30 prób) | Okres +1%, n=4 (5 prób) |','|---|---:|---:|']
    # Matched five-draw means for sensitivity, rather than mixing different repetitions.
    records=json.loads((ROOT/'results/scores.json').read_text())
    lines[-2]='| Metoda | Prawidłowy okres, n=4 (te same 5 prób) | Okres +1%, n=4 (5 prób) |'
    for a,label in names.items():
        good=np.mean([r['macro_f1'] for r in records if r['condition']=='main' and r['n']==4 and r['rep']<5 and r['arm']==a])
        lines.append(f"| {label} | {good:.3f} | {s['diagnostics']['period_plus1pct'][a]['4']:.3f} |")
    lines+=['','## Granice wniosku','',
      '- Wybrane klasy okresowe z dobrym pokryciem fazy; nie obejmuje to dowolnych ani nowo odkrytych klas.',
      '- Katalogowy okres i etykieta pochodzą z OGLE; to wariant z korzystnym, znanym zegarem. Test +1% mierzy wrażliwość, nie jakość odzyskiwania okresu.',
      '- Nie wykonano transferu na inny przegląd ani podziału przestrzennego. Wykluczenie sąsiadów do 2 sekund łuku nie zastępuje audytu wszystkich fizycznych duplikatów.',
      '- Mała sieć ma stałą architekturę i ustawienia. Jej wynik nie reprezentuje wszystkich sieci ani najlepiej dostrojonego modelu.',
      f"- Liczba dopasowań z ostrzeżeniem zbieżności: {s['nonconverged_runs']}. Ostrzeżenia są zapisane przy każdej predykcji.",
      '- Klasyczne momenty to zwykłe skośność i kurtoza po skalowaniu odpornym amplitudą; sformułowanie „robust skew/kurtosis” w protokole nie oznacza odpornego estymatora tych momentów. Nie obcinano odstających pomiarów.',
      '- Protokół zapisano lokalnie przed wynikami; nie ma zewnętrznej prerejestracji. Wersja ta nie była poprawiana na podstawie punktacji.',
      '- Nie wolno przenosić wcześniejszego wyniku „8 razy mniej etykiet” z łożysk na ten eksperyment.','',
      '## Modele i odtworzenie','',
      'Zapisano `models/timdr_lda.joblib` i `models/classical_rf.joblib`. Każdy korzysta z 640 etykiet (160 na klasę), z pierwszego ustalonego losowania. Modelu nie wybrano według wyniku testowego. Instrukcja wejściowego CSV i uruchomienia: [README.md](README.md). Identyfikatory i sumy kontrolne: [manifest](results/manifest.json), [audyt](results/data_audit.json).','',
      'Kod implementuje eksperymentalną adaptację sygnałowych wskazówek [GIA-TIMDR](https://github.com/jbackk-lang/GIA-TIMDR). Dane: [OGLE RR Lyrae](https://www.astrouw.edu.pl/ogle/ogle4/OCVS/lmc/rrlyr/) i [OGLE cefeidy](https://www.astrouw.edu.pl/ogle/ogle4/OCVS/lmc/cep/). Publikacje źródłowe wymieniono w README.','']
    ast=ROOT/'results/astromer_status.json'
    if ast.exists():
        status=json.loads(ast.read_text())
        lines+=['## ASTROMER','',status['description'],'']
        s['astromer']=status['status']
        (ROOT/'results/summary.json').write_text(json.dumps(s,indent=2))
    else:lines+=['## ASTROMER','', 'Porównanie z pretrained ASTROMER nie zostało wykonane. Nie ma podstaw do twierdzenia o przewadze nad modelem wstępnie uczonym.','']
    (ROOT/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    shutil.copyfile(ROOT/'data/manifest.json',ROOT/'results/manifest.json')
    shutil.copyfile(ROOT/'data/audit.json',ROOT/'results/data_audit.json')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
    hashes['PROTOCOL.md']=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()
    (ROOT/'results/source_hashes.json').write_text(json.dumps(hashes,indent=2))
    m=json.loads((ROOT/'data/manifest.json').read_text()); row=next(r for r in m if r['split']=='test')
    curve=np.load(ROOT/'data/curves.npz')[row['id']]
    (ROOT/'examples').mkdir(exist_ok=True)
    np.savetxt(ROOT/'examples/ogle_test_curve.csv',curve,delimiter=',',header='time,magnitude,error',comments='')
    (ROOT/'examples/metadata.json').write_text(json.dumps(row,indent=2))
    print('Report written:',ROOT/'RESULTS.md')

if __name__=='__main__':main()
