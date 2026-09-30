# Zdjęcia nieba — pierwszy prototyp

W repo TIMDR-lightcurve-fewshot. Inspiracja: [MAGE-IN-IMAGE-DECODER](https://github.com/jbackk-lang/MAGE-IN-IMAGE-DECODER): niezależne wskazania i nakładki obszarów do oględzin. Nie skopiowano detektorów emocji koloru ani nie użyto ich jako cech astronomicznych. Detekcje nie są identyfikacją katalogową ani dowodem nowego obiektu.

## Użycie
1. Uruchom START.cmd, wybierz Zdjęcia nieba. Domyślny adres: http://127.0.0.1:8768/images.
2. Wypróbuj symulowane niebo albo wgraj FITS/PNG/JPEG/TIFF. Limity: 4 mln pikseli/obraz, 24 MB razem, maks. 160 klatek.
3. Wybierz izolowaną gwiazdę badaną i stałą gwiazdę odniesienia z listy. Pozycje są w pikselach, liczone od zera, Y rośnie w dół podglądu.
4. Dla serii FITS podaj gain elektrony/ADU, próg nasycenia ADU i promień apertury. Potwierdź przygotowanie zdjęć.
5. Pobierz względną krzywą CSV lub raport JSON. CSV można wgrać na stronie głównej. Przykład zmiennej gwiazdy obejmuje 96 pomiarów i trzy cykle z okresem 0,56 dnia. Przycisk Przeanalizuj krzywą w głównym oknie przekazuje dane i parametry bez ręcznego importu. Nie oznaczaj nieznanego pasma jako I.

## Warunki pomiaru
FITS 2D w głównym HDU, skończone wartości, liniowe ADU po kalibracji, już wyrównane zdjęcia o wspólnej skali, orientacji i paśmie. Nie obsługuje kostek, wielorozszerzeniowych danych, surowej mozaiki Bayera ani nie wykonuje rejestracji. Drobne doprecyzowanie środka źródła nie zastępuje wyrównania. DATY: DATE-OBS, JD lub MJD-OBS jako początek ekspozycji UTC, EXPTIME sekundy. Do czasu dodaje się połowę ekspozycji; brak korekcji barycentrycznej. Nagłówki należy zweryfikować zgodnie z dokumentacją aparatu.

PNG/JPEG/TIFF są wyłącznie do oględzin, gdyż obróbka i gamma mogą zmieniać pomiary. Podgląd FITS ma rozciągnięty kontrast, lecz fotometria zawsze pracuje na oryginalnych pikselach.

## Metoda i ograniczenia
Klasyczna fotometria aperturowa: suma pikseli w kole minus lokalne tło z pierścienia 1,7–2,5 promienia. Tło oczyszczane z odchyleń ponad 3 MAD; nie zastępuje kontroli sąsiednich gwiazd. Pozycja doprecyzowywana w małym oknie; duże przesunięcia mogą trafić na obcy obiekt, więc wyrównanie pozostaje obowiązkiem przygotowania danych. Odrzucane: brzeg, nasycenie, słaby S/N, nadmierne lokalne przesunięcie. Względne magnitudo: -2,5 log10(strumień badanego / strumień odniesienia).

Błąd uwzględnia szum fotonowy obiektu, wariancję tła i niepewność średniego tła. Nie uwzględnia systematyki flat/dark, korelacji po rejestracji, scyntylacji ani zmienności odniesienia. Nie ma automatycznej weryfikacji stałości odniesienia, astrometrii ani korekcji PSF. Seeing i zatłoczenie mogą powodować pozorną zmienność. Parametr FWHM diagnostyki jest jedynie przybliżeniem momentowym małej łatki, nie pomiarem optyki.

## Co sprawdzono
Testy odzyskania zadanej sinusoidalnej zmienności oraz stałości drugiej gwiazdy na symulacji z szumem Poissona, detekcja źródeł, nasycenie, brzeg, powtórzone czasy, pasmo, Bayer i lokalne API. To walidacja mechaniki na symulacji, nie potwierdzenie dokładności na prawdziwym niebie. Następny etap badawczy: rzeczywista skalibrowana seria i porównanie z niezależną fotometrią.

Żadne sito TIMDR nie zmienia pikseli ani strumieni w tym prototypie. Krzywą można później analizować obecnymi metodami TIMDR; ich przewaga wymaga osobnego testu. Wgrane obrazy nie opuszczają komputera i nie są zapisywane przez serwer.

## Folder i trzy przykłady
Domyślny folder: `images/inbox`. Przycisk **Wczytaj domyślny folder zdjęć** odczytuje ten folder lokalnie; systemowe okno wyboru plików pozostaje alternatywą. Zdjęcia użytkownika nie są dodawane do Git. Gotowe syntetyczne serie: `images/examples/variable`, `constant`, `saturated` — po 96 FITS. Ostatnia seria ma 3 celowo nasycone klatki. Wszystkie strony korzystają z tego samego portu 8768 ; główne okno kieruje zdjęcia na port 8768 także wtedy, gdy zostało otwarte na starym serwerze 8767.
