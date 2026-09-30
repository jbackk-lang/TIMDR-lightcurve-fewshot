# TIMDR-lightcurve-fewshot

## Interfejs dla obserwatora

**Windows: `SETUP.cmd` przy pierwszej instalacji, potem `START.cmd`.** Lokalna aplikacja: http://127.0.0.1:8768. Import CSV/DAT, kontrola jakości, wykres czasu i fazy, harmoniczne TIMDR, diagnostyka okresu, porównanie z czterema gwiazdami OGLE i raport JSON. Dziewięć przykładów dostępnych jednym kliknięciem oraz jako CSV. Instrukcja: [INTERFEJS.md](INTERFEJS.md). Testy: `python -m unittest test_ui.py test_pipeline.py`.

Eksperymentalny klasyfikator rzeczywistych krzywych blasku OGLE: RRab, RRc, cefeidy F i 1O. Celem jest sprawdzenie, czy struktura sygnału ogranicza liczbę potrzebnych etykiet. Wyniki pilotażu i ograniczenia zawiera `RESULTS.md` po zakończeniu obliczeń.

**Rola [GIA-TIMDR](https://github.com/jbackk-lang/GIA-TIMDR):** rama budowy modelu — wybór zegara procesu, reprezentacja w fazie i sito oparte na powtarzalności składowych. Tutaj zegarem jest okres zmienności gwiazdy. Implementacja to nowa, eksperymentalna adaptacja gałęzi sygnałowej M/S: zgodność harmonicznych w czterech fragmentach obserwacji steruje filtrowaniem. Nie jest kopią sita pasm nośnych z łożysk; nie przypisuje TIMDR autorstwa analizy Fouriera, LDA ani lasu losowego. O korzyści adaptacji rozstrzyga porównanie z reprezentacją bez sita.

## Uruchomienie

Python 3.12. W folderze projektu:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m unittest test_pipeline.py
.venv/Scripts/python.exe prepare.py --cache ../../work/ogle-cache
.venv/Scripts/python.exe benchmark.py
```

Pierwsze przygotowanie pobiera około 220 MB archiwów OGLE. Kolejne używa pamięci podręcznej. Wyniki można wznowić: istniejące predykcje są używane ponownie. Po zmianie definicji eksperymentu należy użyć nowego katalogu wyników; nie mieszać wersji.

Klasyfikacja własnej krzywej (czas i okres w dniach; magnitudo i jego dodatnia niepewność):

```powershell
.venv/Scripts/python.exe predict.py moja_krzywa.csv --period 0.567 --output wynik.json
```

CSV ma nagłówek `time,magnitude,error`. Obsługiwany jest także format OGLE `.dat` z trzema kolumnami rozdzielonymi białymi znakami. Minimalnie 80 różnych chwil obserwacji i pokrycie 24 z 32 przedziałów fazy. Okres podaje użytkownik; automatyczne jego odzyskiwanie nie jest jeszcze zwalidowane. Wynik dotyczy czterech znanych klas. Wartości `scores` nie są skalibrowaną pewnością i nie służą wykrywaniu nieznanych typów obiektów.

## Pliki

- `PROTOCOL.md`: zasady zapisane przed pomiarem wyników, bez strojenia na teście.
- `features.py`: odwzorowanie w fazie i eksperymentalne sito.
- `data/manifest.json`: dokładne identyfikatory 2000 gwiazd, podział i okresy.
- `data/curves.npz`: wybrane rzeczywiste pomiary, bezpieczny format tablic NumPy.
- `data/audit.json`: źródła, sumy kontrolne, wykluczenia.
- `results/scores.json`, `summary.json`, `predictions/`: wszystkie wyniki i predykcje.
- `models/timdr_lda.joblib`, `models/classical_rf.joblib`: dwa modele z ustalonego pierwszego losowania, po 160 etykiet na klasę; wybór nie zależy od testu.
- `results/learning_curves.png`: wykres krzywych uczenia.

Modele joblib wczytuj wyłącznie z zaufanego źródła. Dwa gotowe modele są dołączone do repozytorium. Surowe dane i zewnętrzne wagi ASTROMER są pomijane przez `.gitignore`; kod potrafi je odtworzyć. Pliki wyników i manifest zachowano do audytu.

Gotowy przykład po instalacji zależności: `./run_example.ps1 -PythonPath .venv/Scripts/python.exe`. Skrypt uruchamia oba modele na `examples/ogle_test_curve.csv` i zapisuje wyniki w folderze `examples`. Okres i prawdziwa etykieta przykładu są w `examples/metadata.json`.

Dodatkowe porównanie ASTROMER: zainstaluj `requirements-astromer.txt`, uruchom `astromer_extension.py`, a następnie `make_report.py`. Zasady i ograniczenia opisano w `ASTROMER_EXTENSION.md`.

## Źródła i zakres

- [OGLE Collection of Variable Stars](https://ogle.astrouw.edu.pl/main/collections.html).
- [Krzywe RR Lyrae LMC i opis kolumn](https://www.astrouw.edu.pl/ogle/ogle4/OCVS/lmc/rrlyr/).
- [Krzywe cefeid LMC i opis kolumn](https://www.astrouw.edu.pl/ogle/ogle4/OCVS/lmc/cep/).
- Soszyński i in. 2016, RR Lyrae: [arXiv:1606.02727](https://arxiv.org/abs/1606.02727).
- Soszyński i in. 2015, cefeidy: [arXiv:1601.01318](https://arxiv.org/abs/1601.01318).
- Udalski, Szymański i Szymański 2015, OGLE-IV, Acta Astronomica 65, 1.
- Punkt odniesienia dla uczenia ze wstępnym treningiem: [ASTROMER](https://arxiv.org/abs/2205.01677), [ASTROMER 2](https://arxiv.org/abs/2502.02717).

To klasyfikacja gwiazd, nie model orbit satelitów. Nie modyfikuje TIMDR-orbital-tracker. Rozkład testowy jest sztucznie zrównoważony, okresy katalogowe znane, a przegląd i obszar nieba wspólne. Wyniku nie wolno przedstawiać jako dowodu skuteczności przy dowolnych nowych typach gwiazd lub przewagi nad wszystkimi sieciami neuronowymi.

## Tani pilot ATLAS

[Raport ATLAS](experiments/atlas_budget/RAPORT.md): 20 etykiet na klasę, 3 podziały, okresy wyznaczane z pomiarów. Macro-F1: TIMDR 84,82%, faza bez sita 85,78%, cechy klasyczne + las losowy 91,35%. Obecne sito nie dało przewagi. To eksploracyjny pilot na publicznym archiwum, nie bezpośrednia replikacja wyników ASTROMER 2. Kod, protokół i predykcje są w `experiments/atlas_budget/`.

## Zdjęcia nieba — prototyp

Uruchom `START.cmd` i wybierz **Zdjęcia nieba** lub otwórz `/images`. Wgranie zdjęcia pokazuje kandydatów na gwiazdy i lokalne diagnostyki; seria skalibrowanych i wyrównanych FITS pozwala wyznaczyć względną krzywą blasku oraz pobrać CSV. Przycisk **Wypróbuj symulowane niebo** uruchamia przykład 96 klatek. Szczegóły: [ZDJECIA_NIEBA.md](ZDJECIA_NIEBA.md). Testy: `python -m unittest test_sky_images.py test_ui.py test_pipeline.py`.
