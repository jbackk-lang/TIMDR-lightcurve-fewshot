# ATLAS: tani pilot, protokol przed wynikiem
2026-09-29. Eksploracyjny test CPU. Bez treningu ASTROMER i bez platnych API.
Oficjalne archiwum atlas-record ze skryptu data/get_data.sh ASTROMER main-code.
Trzy foldy, atlas_20, klasy CB/DB/Mira/Pulse. Other pominiete jawnie.
Train i val polaczone (bez strojenia), docelowo 20 unikalnych obiektow na klase.
Audyt ID i identycznych krzywych: brak przecieku train/test; duplikaty testowe liczone raz.
Maksymalnie pierwsze 200 pomiarow po sortowaniu po czasie. Bez katalogowych okresow.
Lomb-Scargle: 0.05-1000 dni, siatka 65536 czestotliwosci, lokalne doprecyzowanie najwyzszego piku; identyczny okres dla wszystkich metod. To przyblizony, tani zegar, nie zwalidowany estymator okresu.
Niezmieniona ekstrakcja features.py: TIMDR+LDA, faza bez sita+LDA, klasyczne+RF oraz okres+LDA. Ustawienia benchmark.py. Kontrola losowych etykiet.
Macro-F1, macierz pomylek, czas, wyniki kazdego foldu. Brak wyboru najlepszych ustawien na tescie.
Jesli archiwum nie spelnia zalozen, zatrzymanie i raport bledu zamiast pozornego porownania.
Wartosci A2 z wykresu uzytkownika (70.5%,74.6%,78.9%) sa tylko zewnetrznym odniesieniem. Bez potwierdzenia tozsamosci danych i protokolu nie mierza przewagi nad A2.
