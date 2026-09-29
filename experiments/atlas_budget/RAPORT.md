# ATLAS — wynik taniego pilota

Nie jest to bezpośrednia replikacja wykresu ASTROMER 2. Publiczne archiwum i sposób podania krzywych różnią się od końcowego protokołu pracy.

20 etykiet na klasę, 3 oficjalne podziały archiwum, 4 klasy: CB, DB, Mira, Pulse. Bez trenowania sieci i płatnych usług. Okres oszacowany z tych samych maksymalnie 200 pomiarów dla wszystkich metod.

| Metoda | Macro-F1 (średnia ± SD) |
|---|---:|
| Sam okres + LDA | 65.34% ± 4.19 pp |
| Faza bez sita + LDA | 85.78% ± 3.41 pp |
| TIMDR + LDA | 84.82% ± 2.81 pp |
| Cechy klasyczne + RF | 91.35% ± 1.86 pp |
| TIMDR: losowe etykiety | 24.82% ± 12.35 pp |

Różnica TIMDR względem fazy bez sita: -0.96 punktu procentowego; względem lasu losowego: -6.53 pp. To mały pilot, nie dowód statystyczny przewagi.
Aktualna adaptacja TIMDR nie poprawiła wyniku względem obu tych punktów odniesienia. Najwyższa średnia wśród badanych właściwych modeli należy do classical_rf.

## Zakres i ograniczenia

Czas obliczeń po importach: 855.1 s. Unikalnych krzywych poddanych ekstrakcji: 1426. Pobranie wybranego podzbioru: około 5 MB zamiast 1 GB.

Liczby obiektów testowych według klas, po deduplikacji:

- Podział 0: {'CB': 100, 'DB': 100, 'Mira': 100, 'Pulse': 100}; usunięte powtórzenia testowe: 1200.
- Podział 1: {'CB': 100, 'DB': 100, 'Mira': 100, 'Pulse': 100}; usunięte powtórzenia testowe: 1200.
- Podział 2: {'CB': 100, 'DB': 100, 'Mira': 100, 'Pulse': 100}; usunięte powtórzenia testowe: 1200.

Zbiory train i val połączono bez strojenia parametrów (16+4 etykiety na klasę). Etykiety odczytano z rekordów, nie z nazw folderów. Sprawdzono rozłączność identyfikatorów i identycznych krzywych między treningiem a testem. Powtórzenia między podziałami oznaczają, że nie są to trzy niezależne przeglądy nieba.

Estymator okresu ma ograniczoną siatkę i nie rozstrzyga aliasów ani podwojenia okresu układów podwójnych. Ten wynik ocenia aktualny model razem z tym uproszczonym zegarem. Brak strojenia po wyniku; słaby wynik nie dowodzi nieskuteczności wszystkich adaptacji TIMDR.

## ASTROMER 2 — wyłącznie zewnętrzne odniesienie

Na dostarczonym wykresie A2 + Skip Conn ma F1 70,5% przy 20, 74,6% przy 100 i 78,9% przy 500 etykietach na klasę. Te wartości nie zostały tu ponownie obliczone. Nie odejmujemy ich od wyniku pilota jako miary przewagi: wymagane jest potwierdzenie tych samych obiektów, okien i podziałów. W tym pilocie nie wykonano wariantów 100/500 ani treningu A2, aby ograniczyć koszt.

Źródła: [kod ASTROMER 2](https://github.com/astromer-science/main-code), [praca](https://arxiv.org/abs/2502.02717), [odnośnik do danych](https://github.com/astromer-science/main-code/blob/main/data/get_data.sh).

Predykcje wszystkich 12 właściwych klasyfikatorów sprawdzono przez ponowne obliczenie F1. Protokół, sumy kontrolne danych, identyfikatory, oszacowane okresy i kod znajdują się obok raportu.
