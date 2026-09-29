# Przykłady do interfejsu

## OGLE · RRab
`RRab.csv`

Rzeczywista gwiazda OGLE-LMC-RRLYR-25683, pasmo I. Okres katalogowy: 0.5651696 dnia.

Oczekiwane zachowanie: Zobacz krzywą fazową, harmoniczne i porównanie modeli. Wynik może różnić się od etykiety katalogowej.

## OGLE · RRc
`RRc.csv`

Rzeczywista gwiazda OGLE-LMC-RRLYR-05127, pasmo I. Okres katalogowy: 0.2791104 dnia.

Oczekiwane zachowanie: Zobacz krzywą fazową, harmoniczne i porównanie modeli. Wynik może różnić się od etykiety katalogowej.

## OGLE · CEP-F
`CEP-F.csv`

Rzeczywista gwiazda OGLE-LMC-CEP-0380, pasmo I. Okres katalogowy: 7.0875846 dnia.

Oczekiwane zachowanie: Zobacz krzywą fazową, harmoniczne i porównanie modeli. Wynik może różnić się od etykiety katalogowej.

## OGLE · CEP-1O
`CEP-1O.csv`

Rzeczywista gwiazda OGLE-LMC-CEP-4204, pasmo I. Okres katalogowy: 2.1012469 dnia.

Oczekiwane zachowanie: Zobacz krzywą fazową, harmoniczne i porównanie modeli. Wynik może różnić się od etykiety katalogowej.

## Za mało punktów
`few-points.csv`

Pierwsze 35 rzeczywistych pomiarów RRab. Celowo skrócony przykład edukacyjny.

Oczekiwane zachowanie: Klasyfikacja zostanie wstrzymana: mniej niż 80 pomiarów.

## Luki w fazie
`phase-gaps.csv`

Krzywa RRab z celowo usuniętymi pomiarami fazy 0,65–1,00.

Oczekiwane zachowanie: Klasyfikacja zostanie wstrzymana: mniej niż 24/32 przedziałów fazy.

## Duże błędy pomiaru
`large-errors.csv`

Oryginalne jasności RRab z celowo zmienionym błędem na 0,4 mag. To test kontroli jakości, nie nowa obserwacja.

Oczekiwane zachowanie: Klasyfikacja zostanie wstrzymana: błąd jest zbyt duży względem amplitudy.

## Okres błędny o 1%
`wrong-period.csv`

Te same pomiary RRab, ale wpisany okres zwiększono o 1%. Jasności nie zmieniono.

Oczekiwane zachowanie: Zobacz rozmycie fazy i spadek spójności harmonicznych. Ocena okresu powinna wymagać sprawdzenia.

## Nie znam okresu
`unknown-period.csv`

Rzeczywiste pomiary RRab bez podanego okresu. Zakres demonstracyjny 0,5–0,65 dnia obejmuje znany okres katalogowy.

Oczekiwane zachowanie: Wybierz „Szukaj okresu”, a potem obejrzyj jednego z kandydatów. Zakres w tym przykładzie jest ułatwieniem.

Pomiary źródłowe: OGLE LMC, pasmo I. Przypadki problemowe są celowymi modyfikacjami edukacyjnymi, nie danymi do oceny skuteczności modelu.
