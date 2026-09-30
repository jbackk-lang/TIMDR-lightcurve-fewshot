# Pracownia krzywych blasku — instrukcja dla obserwatora

## Uruchomienie

Windows: uruchom `SETUP.cmd` jeden raz (Python 3.12 i internet), następnie `START.cmd`. Lokalna strona otworzy się pod adresem http://127.0.0.1:8768. Pozostaw terminal otwarty; Ctrl+C zatrzymuje serwer. Alternatywnie: `.venv/Scripts/python.exe ui_server.py`.

Pomiary są analizowane w pamięci na Twoim komputerze. Wykresy nie korzystają z zewnętrznego serwisu. Raport zapisuje użytkownik przyciskiem pobrania.

## Dziewięć przykładów

Cztery przyciski OGLE wczytują rzeczywiste gwiazdy RRab, RRc, CEP-F i CEP-1O wraz z okresem katalogowym i pasmem I. Gwiazdy wybrano jako pierwsze obiekty testowe każdej klasy, bez selekcji według trafności modelu. Każdy przykład ma identyfikator i link do OGLE.

Pięć przykładów edukacyjnych pokazuje: za mało punktów, luki w fazie, duże niepewności, okres błędny o 1% i nieznany okres. Są celowo zmodyfikowane i opisane; nie stanowią oceny skuteczności modelu. „Pobierz ten przykład CSV” zapisuje wybrany plik. Wszystkie CSV są również w `examples/tutorial/`.

## Własne pomiary

Wgraj CSV, DAT lub TXT. Obsługiwane są przecinki, średniki, tabulatory i odstępy w DAT. Przecinek dziesiętny wymaga separatora innego niż przecinek. Import rozpoznaje m.in. time/JD/HJD/MJD, mag/magnitude, error/MERR. Nietypowe kolumny wybierz ręcznie. Dla pliku AAVSO wybierz jeden obiekt i jeden filtr. Strumień należy wcześniej przeliczyć na magnitudo z poprawną propagacją błędów.

Wybierz jednostkę czasu: dni, godziny, sekundy lub datę ISO. ISO bez strefy oznacza założenie UTC. Program nie wykonuje korekty heliocentrycznej/barycentrycznej ani nie sprawdza zegara aparatu. Nie mieszaj JD z MJD lub różnych skal czasu.

## Jakość i interpretacja

- Minimum klasyfikacji: 80 różnych chwil i 24 zajęte przedziały z 32 fazy.
- Klasyfikacja jest dodatkowo wstrzymywana przy brakujących lub niedodatnich błędach, stałej krzywej, rozpiętości krótszej niż dwa cykle lub medianie błędu przekraczającej 25% amplitudy 5–95%. Dodatkowe progi są heurystyczne.
- Przerwy oznaczają odstępy większe niż pięciokrotność mediany kadencji. Nie muszą dyskwalifikować dobrze pokrytej krzywej fazowej.
- Oś magnitudo jest odwrócona: jaśniejsza gwiazda jest wyżej. Fazę wykresu wyrównano pierwszą harmoniczną; pasek pokrycia używa fazy od pierwszej obserwacji.
- Sito TIMDR tłumi harmoniczne według ich zgodności w czterech kolejnych grupach pomiarów. Procent osłabienia dotyczy energii harmonicznych, nie odrzuconych punktów. Program nie usuwa automatycznie odstających obserwacji.
- Mapa kolorów pokazuje zgodność fazy harmonicznej z pełnym dopasowaniem: zielony ≥0,8; żółty ≥0,5; czerwony <0,5. Przy małej amplitudzie interpretacja fazy jest ograniczona.
- Klasyfikatory wskazują kandydata spośród czterech znanych klas. Wyniki nie są skalibrowaną pewnością; nieznany typ może otrzymać wysoki wynik. Opisy asymetrii i harmonicznych opisują dane, nie dowodzą przyczyn decyzji modelu.
- Modele oceniono na OGLE LMC w paśmie I ze znanymi okresami. Inne pasma wymagają osobnej walidacji. Pilotaż nie wykazał przewagi TIMDR nad klasycznym lasem losowym.

## Nieznany okres

Zaznacz „Nie znam okresu”, podaj zakres i wybierz „Szukaj okresu”. Lomb–Scargle zwraca pięć odseparowanych, lokalnie doprecyzowanych kandydatów. Obejrzyj ich krzywe fazowe. Aliasy dobowe oraz P/2 i 2P mogą być silniejsze od właściwego piku. FAP nie oznacza prawdopodobieństwa poprawności okresu. Limit 200 000 częstotliwości wymusza zawężenie zbyt szerokiego zakresu.

Ocena podanego okresu korzysta z koherencji, reszt i liczby cykli. Test ±1% obrazuje wrażliwość, nie wyznacza niepewności. Diagnostyka okresu jest sprawdzona na sygnale kontrolnym; nie zastępuje walidacji na niezależnym przeglądzie.

## API lokalne

GET `/api/references` i `/api/examples`: przykłady. POST `/api/inspect`: kolumny; `/api/analyze`: analiza; `/api/period`: kandydaci okresu. POST wymaga X-Local-Token z metadanych lokalnej strony. Pola JSON: text, mapping, time_unit, band, object, declared_band, allow_experimental, period; wyszukiwanie dodatkowo pmin/pmax. Limit: 5 MB i 20 000 wierszy. Serwer nasłuchuje tylko na 127.0.0.1, sprawdza Host i Origin. To serwer lokalny, nie gotowa usługa publiczna.

Źródła: [OGLE](https://ogle.astrouw.edu.pl/main/collections.html), [Lomb–Scargle w Astropy](https://docs.astropy.org/en/stable/timeseries/lombscargle.html), [format AAVSO](https://www.aavso.org/aavso-extended-file-format).
