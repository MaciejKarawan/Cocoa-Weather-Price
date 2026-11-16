# Kakao: czy pogoda daje przewagę (przebieg post-hoc, 22.10.2026)

Rynek: ICE NY (kakao, USD), Afryka Zachodnia (pogoda), spółki z SIX i NYSE. Przebieg eksploracyjny
poza pipeline'em BONASUS; bez karty hipotezy, nie prowadzi do statusu kandydata.

Dashboard (pierwszy przebieg): https://maciejkarawan.github.io/cocoa/. Źródła: `data/CATALOG.md`.

## Wynik

| Ogniwo | Wynik |
|---|---|
| Sezonowość ceny i zmienności | nie widzę (Pink Sheet 66 lat, COCO.L, CC=F; strategia kalendarzowa traci poza próbą) |
| Pogoda i ENSO → zwrot 1–6 mies. | nic nie przechodzi BH; opad i Tmax wbrew hipotezie, ENSO zgodnie, słabo |
| Pogoda → cena w tym samym oknie | R² 0–1% |
| Zbiory → cena | silne: ρ −0,50, elastyczność −1,07 (cena w roku Y+1, 1961–2024) |
| Pogoda → zbiory | nie widzę (MDE \|ρ\| 0,43); ENSO q 0,14 |
| Kakao → spółki | beta w tym samym miesiącu −0,11…−0,15 (HSY, MDLZ, BARN); opóźnionej reakcji brak |
| Komunikaty ENSO (CPC) | brak reakcji, n = 27 zmian statusu |

Rekomendacja: nie budować sygnału z obserwowanej pogody z reanalizy; najpierw ogniwo pogoda →
zbiory na CHIRPS z maską upraw. Jeśli wyjaśni produkcję, dopiero wtedy prognozy sezonowe.

## Pogoda → zbiory, wersja 2: specyfikacja zapisana przed przebiegiem (22.10.2026)

Podstawa: Albright, Berkoh-Oforiwaa, Huybers, PNAS 2026 (Ghana, 66 dystryktów, R² 0,68). Reguła
decyzji uzgodniona z użytkownikiem 22.10.2026. Wersja 1 (tabela wyżej) różniła się od literatury
oknami, miarą opadu, zmienną objaśnianą i produktem opadowym.

| Element | Ustalenie |
|---|---|
| Opad | TAMSAT v3.1, dzienny, 0,25°, `rfe_filled`; CHIRPS v2.0 0,25° wyłącznie jako kontrola produktu |
| Ulewy `R_w` | średnia z IV, V, VI miesięcznego 95. percentyla dziennego opadu uśrednionego po obszarze; sezon s |
| Pora sucha `R_d` | średni dzienny opad XI s – II s+1 |
| Obszar Ghany | 5–7°N, 3,5–0,5°W (Albright) |
| Sezon s/s+1 | X s – IX s+1; rok FAO Y = sezon Y−1/Y dla Ghany |
| Produkcja Ghany | COCOBOD (raport roczny) > ICCO (najnowszy QBCS) > FAO; FAO 2011 i 2014–2016 błędne |
| K: kontrola pozytywna | Ghana 2000/01–2023/24; produkcja / trend liniowy; OLS na `R_w`, `R_d`; zaliczona, gdy `α_w` < 0 i `α_d` > 0, oba p < 0,05 jednostronnie |
| G: test Ghany | 1983/84–2023/24; Δlog produkcji na Δ`R_w`, Δ`R_d`; HAC, opóźnienie 1; okno rozszerzające od 15 sezonów; benchmark: średnia Δlog; Clark–West |
| Reguła | oba znaki istotne (5%, jednostronnie) i R² poza próbą ≥ 0,4 → ogniwo cenowe; istotne poniżej 0,4 → wiedza o podaży; brak istotności → „nie widzę” |
| WKS | wstrzymane: brak darmowej serii sezonowej sprzed 2015/16; rok FAO niepewny [DO WERYFIKACJI] |

Δlog zamiast odchylenia od trendu liniowego: w 41 sezonach trend Ghany nie jest liniowy. Przy
niezależnych w czasie anomaliach R² obu postaci jest w oczekiwaniu równe; korelacja produkcja →
cena (−0,50) też jest liczona na przyrostach.

### Wynik wersji 2 (TAMSAT; `src/zbiory_pogoda.py`, `wyniki/zbiory_pogoda.json`)

| Test | Wynik | Ocena |
|---|---|---|
| K: Ghana 2000/01–2023/24, n = 24 | `α_w` −0,126 (p 0,0002), `α_d` +0,117 (p 0,0004), R² 0,65, LOOCV 0,58 | zaliczona: dane i ścieżka odtwarzają artykuł (0,68 / 0,57) |
| G: Ghana 1984/85–2023/24, n = 40 | ulewy −0,027/sd (p 0,16), pora sucha +0,064/sd (p 0,08), R² 0,13 (MDE 0,20), poza próbą 0,11 (Clark–West p 0,01) | **„nie widzę”** wg reguły |
| post-hoc: 1983/84–1999/00, n = 16 | R² 0,03, znaki niezgodne | związku brak |
| post-hoc: 2000/01–2023/24, n = 24 | R² 0,58, oba p ≤ 0,001 | postać Δ działa; różnicę robi okres |
| post-hoc: 2000/01–2008/09; 2009/10–2023/24 | R² 0,71; 0,58 | stabilny w obu połowach |
| post-hoc: bez 2010/11 i 2023/24 (przemyt) | R² 0,51 | nie zależy od sezonów przemytu |

CHIRPS (kontrola produktu): K zaliczona słabiej (ulewy p 0,03, R² 0,38, LOOCV 0,28); G „nie widzę”
(R² 0,08, poza próbą −0,05). W postaci Δ ulewy w CHIRPS mają znak przeciwny, pora sucha zgodny i
istotny po 2000 (R² 0,41). Kanał pory suchej nie zależy od produktu, kanał ulew widać tylko w TAMSAT
(jak w artykule).

Sprawdzone ad hoc: przesunięcie roku FAO o sezon przed 2000 nie przywraca związku (R² ≤ 0,06);
dni TAMSAT uzupełnione z CHIRPS w Ghanie < 5% rocznie poza 1988 (14%). Przyczyna braku związku
przed 2000 nieznana: jakość danych FAO sprzed 2000 albo zmiana reżimu upraw [HIPOTEZA].
Wyjaśnione w rewizji niżej: błąd danych FAO.

### Rewizja danych Ghany (23.10.2026, post-hoc)

Seria Ghany: tabela skupu COCOBOD 1947/48–2019/20 (`cocobod.gh/cocoa-purchases`), dalej ICCO.
Kolejność źródeł i specyfikacja G bez zmian; zmienia się tylko seria, na której ją liczono.

- FAO, Ghana: rok FAO = sezon s/s+1 do 1995, s−1/s od 1996 (sezon 1995/96 dwukrotnie). Wersja 2
  przesuwała sezony 1983/84–1994/95 o jeden. Błędne poziomy FAO także w 1988 (−18%) i 2005 (+23%).
- FAO, WKS: rok FAO = s/s+1 w 1983–1986 (USDA FAS 1988), s−1/s w 2007/08–2010/11 (ICCO
  EX/146/7); pozostałe lata [DO WERYFIKACJI].

| Test (TAMSAT) | Wersja 2 (FAO) | Rewizja (COCOBOD) |
|---|---|---|
| K: 2000/01–2023/24 | R² 0,65, LOOCV 0,58 | R² 0,59, LOOCV 0,51; zaliczona |
| G: 1984/85–2023/24 | R² 0,13, poza próbą 0,11 | R² 0,27 (MDE 0,20), poza próbą 0,28 (Clark–West p < 0,001); pora sucha +0,110/sd (p < 0,001), ulewy −0,015/sd (p 0,34); **„nie widzę”**: ulewy nieistotne |
| post-hoc: 1983/84–1999/00 | R² 0,03, znaki niezgodne | R² 0,14; pora sucha +0,081/sd (p 0,04), ulewy +0,044/sd (p 0,71) |
| post-hoc: 2000/01–2023/24 | R² 0,58 | R² 0,55, oba p ≤ 0,002; poza próbą 0,41 (trening 10, 14 prognoz) i 0,51 (trening 15, 9 prognoz); bez 2010/11 i 2023/24 w ocenie 0,13 i 0,46 (G: 0,28) |
| post-hoc: równość nachyleń przed i od 2000 | — | p 0,02; pora sucha 0,067 → 0,180/sd, ulewy +0,043 (se 0,077) → −0,062/sd |

CHIRPS, G: R² 0,34, poza próbą 0,34; pora sucha p < 0,001, ulewy ze znakiem przeciwnym.
Wariancja Δlog produkcji przed i od 2000: 0,040 i 0,055.

Zbiory → cena (`src/zbiory_cena.py`): Spearman Δlog produkcji w sezonie s wobec Δlog średniej
ceny Pink Sheet w sezonie (X–IX), 1961/62–2023/24, elastyczność OLS z HAC(1).

| Produkcja | Cena s−1 | Cena s | Cena s+1 |
|---|---|---|---|
| Ghana (COCOBOD) | +0,21 | −0,35 (p 0,005), elastyczność −0,41 | −0,17 |
| WKS (FAO, Y/Y+1) + Ghana | +0,10 | −0,44 (p < 0,001), elastyczność −0,95 | −0,16 |
| WKS (FAO, Y−1/Y) + Ghana | +0,20 | −0,35 (p 0,005), elastyczność −0,59 | −0,31 (p 0,02) |

Wersja 1 (suma FAO, cena w roku kalendarzowym Y+1): −0,50, elastyczność −1,07.

## Pogoda → zbiory WKS: replikacja artykułu, specyfikacja zapisana przed przebiegiem (23.10.2026)

Prośba użytkownika: powtórzyć Albright i in. 2026 dla WKS przed testem pogoda → cena.

| Element | Ustalenie |
|---|---|
| Produkcja WKS | ICCO: raport roczny 2004/05 (2000/01–2001/02), 2006/07 (2002/03–2005/06), EX/146/7 (2006/07–2010/11), QBCS (2015/16–2023/24); CCC przez aneks ICCO (2012/13–2014/15); 2011/12 z FAO 2012 |
| Obszar WKS | 5–8°N, 8,5–3,5°W: 90% pola kakao na zachód od 3,1°W wg CROPGRIDS (obszar Ghany Albright: 81% pola Ghany); bez wspólnych komórek z obszarem Ghany |
| Opad, miary, sezon | jak wersja 2: TAMSAT v3.1, `R_w`, `R_d`, sezon X–IX |
| K_WKS | 2000/01–2023/24; produkcja / trend liniowy; OLS na standaryzowanych `R_w`, `R_d`; LOOCV; zaliczona, gdy `α_w` < 0 i `α_d` > 0, oba p < 0,05 jednostronnie |
| Opisowo | postać Δlog jak G, 2000/01–2023/24, okno rozszerzające od 10 sezonów |

### Wynik (TAMSAT; `src/zbiory_wks.py`, `wyniki/zbiory_wks.json`)

| Test | WKS | Ghana (ta sama ścieżka) |
|---|---|---|
| K: produkcja / trend, 2000/01–2023/24, n = 24 | `α_w` −0,023 (p 0,15), `α_d` +0,032 (p 0,08), R² 0,14, LOOCV −0,05; **niezaliczona** | `α_w` −0,117, `α_d` +0,115, R² 0,59, LOOCV 0,51 |
| opisowo: Δlog, 2001/02–2023/24, n = 23 | ulewy +0,007/sd (p 0,66), pora sucha +0,081/sd (p < 0,001), R² 0,45 (MDE 0,34), poza próbą 0,38 (13 prognoz, Clark–West p 0,003) | ulewy −0,063/sd (p 0,002), pora sucha +0,158/sd (p < 0,001), R² 0,55 |
| post-hoc: Δlog bez 2010/11, bez 2023/24, bez obu | R² 0,42; 0,44; 0,42; pora sucha p ≤ 0,001 | R² 0,49; 0,53; 0,46 |

Korelacja wskaźników obszarów WKS i Ghany 2000/01–2023/24: `R_d` 0,93 (poziomy i Δ), `R_w` 0,73
(poziomy), 0,69 (Δ).

## Pogoda → cena: specyfikacja zapisana przed przebiegiem (23.10.2026)

Uzgodniona z użytkownikiem 23.10.2026. Wybór pory suchej opiera się na widzianych danych o
zbiorach; cena nie była oglądana w tym zestawieniu.

| Element | Ustalenie |
|---|---|
| Sygnał V1 | `R_d`: średni opad dzienny XI s – II s+1, znany w III s+1 |
| Sygnał V2 | `R_d31`: średni opad dzienny XI–XII s, znany w I s+1 |
| Obszar sygnału | średnia obszarów WKS i Ghany z wagami 0,7 i 0,3 (`WAGI_KRAJOW`); TAMSAT v3.1 |
| Bramka V2 (zbiory) | Δlog produkcji na Δ`R_d31` ze stałą, HAC(1); Ghana 1984/85–2023/24, WKS 2001/02–2023/24; przechodzi, gdy nachylenie > 0 i p < 0,05 jednostronnie w obu krajach; opisowo to samo dla `R_d` |
| Cena | Pink Sheet, średnia miesięczna; V1: log IX s+1 − log III s+1; V2: log IX s+1 − log I s+1 |
| Próba | sezony 1984/85–2025/26, n = 42 |
| Test | OLS stopy zwrotu na standaryzowanej Δ sygnału, HAC(1); oczekiwany znak ujemny, p jednostronne; V1 i V2 każdy przy α 5%, bez poprawki (zmiana użytkownika 23.10.2026, przed obejrzeniem ceny: testy niemal zależne; błąd rodziny ok. 8% przy korelacji statystyk ok. 0,7) |
| Raport | nachylenie (% ceny na sd), 90% przedział ufności, Spearman |
| Reguła | istotny → dalej (dzienne futures, koszty, termin wejścia); brak → „nie widzę”, temat otwarty: moc 47–64% przy oczekiwanym R² 0,055–0,087 |

### Bramka V2 (`src/pogoda_cena.py`, `wyniki/pogoda_cena.json`): przechodzi

| Kraj, sezony | `R_d31` (XI–XII) | `R_d` (XI–II), opisowo |
|---|---|---|
| Ghana 1984/85–2023/24, n = 40 | +0,097/sd (p 0,0001), R² 0,19 | +0,114/sd (p < 0,0001), R² 0,26 |
| WKS 2001/02–2023/24, n = 23 | +0,072/sd (p 0,0001), R² 0,35 | +0,081/sd (p < 0,0001), R² 0,44 |

### Test ceny: **„nie widzę”** w obu wariantach

| Wariant, n = 42 | Nachylenie (zwrot na sd Δ sygnału) | 90% przedział | p (znak −) | Spearman | Oczekiwane przy pełnym łańcuchu |
|---|---|---|---|---|---|
| V1: `R_d`, zwrot III → IX | +0,050 | −0,004 … +0,104 | 0,93 | +0,19 (p 0,23) | −0,039 … −0,049 |
| V2: `R_d31`, zwrot I → IX | −0,001 | −0,047 … +0,046 | 0,49 | −0,04 (p 0,79) | −0,039 … −0,052 |

Oczekiwane: −√R² × sd zwrotu przy R² 0,055–0,087 (pogoda → zbiory × zbiory → cena, rynek nie
wycenia sygnału przed oknem); dla V2 pomnożone przez 0,85–0,89 (słabszy związek `R_d31` ze
zbiorami). Sd zwrotu: V1 0,167, V2 0,197; korelacja zwrotów V1 i V2 0,71. V1 wyklucza wartość
oczekiwaną na poziomie 90%; V2 obejmuje jej słabszą połowę.

### Test równoczesny (post-hoc, specyfikacja przed przebiegiem, 23.10.2026)

Pytanie: czy cena reaguje na porę suchą w czasie jej trwania. Diagnoza wyniku V1, nie strategia.

| Element | Ustalenie |
|---|---|
| Sygnał | Δ`R_d` jak w V1 (pas WKS + Ghana, 0,7 / 0,3), standaryzowana |
| Cena | log III s+1 − log X s (Pink Sheet); razem z V1 daje zwrot X s → IX s+1 |
| Test | jak V1: OLS, HAC(1), znak oczekiwany ujemny, 90% przedział; n = 42 |
| Odczyt | istotny ujemny → rynek wycenia porę suchą na bieżąco; brak → pora sucha nie przechodzi na cenę („nie widzę”) |

Wynik: −0,067/sd (90%: −0,131 … −0,002), p 0,045, R² 0,11, Spearman −0,19 (p 0,22); oczekiwane
przy pełnym łańcuchu −0,047 … −0,059 (sd zwrotu 0,201). Wg odczytu: wycena na bieżąco.

Post-hoc, sezony usunięte po różnicowaniu (2025/26: Δ`R_d` +2,3 sd, zwrot X → III −0,61, III → IX
+0,60):

| Test | Bez 2025/26, n = 41 | Bez 2023/24–2025/26, n = 39 |
|---|---|---|
| równoczesny X → III | −0,034 (90%: −0,080 … +0,013), p 0,12 | −0,015 (−0,053 … +0,024), p 0,27 |
| V1: III → IX | +0,018 (−0,012 … +0,048) | +0,015 (−0,014 … +0,044) |
| V2: I → IX | −0,014 (−0,057 … +0,030), p 0,30 | −0,026 (−0,065 … +0,013), p 0,14 |

Reakcja równoczesna stoi na sezonie 2025/26; w 1984/85–2022/23 cena słabo reaguje na porę suchą
także w trakcie jej trwania. V1 wyklucza wartość oczekiwaną także bez tych sezonów.

## Odtworzenie

Z korzenia repozytorium: `python src/pobierz.py`, `python src/analiza.py`, `python src/eksport.py`.
Wyniki: `wyniki/wyniki.json`, zbiory dashboardu: `wyniki/dashboard/`.
Wersja 2: `python src/opad.py tamsat|chirps <źródło>` (wymaga `h5py`), potem `src/zbiory_pogoda.py`,
`src/zbiory_cena.py`, `src/zbiory_wks.py` i `src/pogoda_cena.py`.
