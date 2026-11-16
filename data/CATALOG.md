# Katalog danych: analiza kakao

Pobrane 22.10.2026 skryptem `src/pobierz.py` do `data/raw/`; pliki surowe nie są nadpisywane.

| Zbiór | Źródło i URL | Okres | Częstotliwość | Licencja | Znane problemy |
|---|---|---|---|---|---|
| CC=F | Yahoo Finance, `query1.finance.yahoo.com/v8/finance/chart/CC=F` | 2000-01 – 2026-10 | dzienna | warunki Yahoo, użytek własny | ciągły kontrakt najbliższy bez korekty rolowania; 94 dni bez ceny zamknięcia; brak historii wygasłych kontraktów |
| COCO.L | Yahoo Finance, WisdomTree Cocoa (LSE, USD) | 2009-11 – 2026-10 | dzienna | jw. | [ZAŁOŻENIE] odwzorowuje rolowany indeks futures kakao ICE NY; zawiera opłaty ETC |
| BARN.SW, LISP.SW, HSY, MDLZ, ^SSMI, ^GSPC | Yahoo Finance | od 1970–2001 do 2026-10 | dzienna | jw. | ^SSMI to indeks cenowy (bez dywidend), spółki z ceną skorygowaną |
| Pink Sheet | Bank Światowy, `thedocs.worldbank.org/.../CMO-Historical-Data-Monthly.xlsx` (wydanie 2.10.2026) | 1960-01 – 2026-09 | miesięczna | CC BY 4.0 | cena kakao to średnia z miesiąca; starsze wydanie (3.01.2025) zachowane pod inną nazwą |
| NASA POWER dzienne | `power.larc.nasa.gov/api/temporal/daily/point`, 10 punktów pasa kakaowego (PRECTOTCORR, T2M_MAX, GWETROOT) | 1981-01-01 – 2026-10-19 | dzienna | dane publiczne NASA | długie zapytanie zwraca opad ×24 (etykieta mm/day); dzielone przez 24 i sprawdzane z sumami miesięcznymi; reanaliza MERRA-2, słaba dla opadów w tropikach |
| NASA POWER miesięczne | `power.larc.nasa.gov/api/temporal/monthly/point`, PRECTOTCORR_SUM | 1981 – 2025 | miesięczna | jw. | tylko do kontroli skali opadu |
| Niño3.4 | NOAA CPC, `cpc.ncep.noaa.gov/data/indices/sstoi.indices` | 1982-01 – 2026-09 | miesięczna | domena publiczna | anomalia względem bieżącej klimatologii CPC (wersja dzisiejsza, nie z czasu rzeczywistego) |
| ONI | NOAA CPC, `cpc.ncep.noaa.gov/data/indices/oni.ascii.txt` | 1950 – 2026 | sezony 3-mies. | domena publiczna | wartości rewidowane |
| Dyskusje ENSO | NOAA CPC, `cpc.ncep.noaa.gov/products/analysis_monitoring/enso_disc_<mies><rok>/ensodisc.shtml` | 2016-07 – 2026-10 | miesięczna | domena publiczna | brak stron 2016-06, 2016-08, 2017-09 (404); 2020-02, 2020-03, 2020-05 to puste przekierowania; część stron z HTML zapisanym jako encje |
| Produkcja kakao | FAOSTAT, `bulks-faostat.fao.org/production/Production_Crops_Livestock_E_All_Data_(Normalized).zip` (aktualizacja 31.12.2025) | 1961 – 2024 | roczna | [DO WERYFIKACJI] | API FAOSTAT niedostępne (HTTP 521); rok FAO a sezon [DO WERYFIKACJI]; część wartości szacunkowa |

| TAMSAT v3.1 | Uniwersytet w Reading, `gws-access.jasmin.ac.uk/public/tamsat/rfe/data_degraded/v3.1/daily/0.25/rfe1983-present_daily_0.25.v3.1.nc` (stan 21.10.2026; SHA-256 w `opad/*.json`) | 1983-01-01 – 2026-10-20 | dzienna, 0,25° | CC BY 4.0 | w `data/raw/opad/` tylko wycinek 3,5–9,5°N, 9°W–1,5°E (`rfe_filled`); w Ghanie dni uzupełnione z CHIRPS < 5% rocznie poza 1988 (14%) |
| CHIRPS v2.0 | UCSB CHC, `data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p25/` | 1983 – 2025 | dzienna, 0,25° | domena publiczna | tylko kontrola produktu; ścięty górny ogon opadu dziennego (Albright i in. 2026) |
| ICCO QBCS, tabela produkcji | `icco.org/wp-content/uploads/Production_QBCS-*.pdf`, 26 wydań (XLIV-3 – LI-2) | sezony 2015/16 – 2024/25 | sezonowa | warunki ICCO | XLVI–XLVIII to skany (odczyt z obrazu); wcześniejsze wydania płatne |
| COCOBOD, raporty roczne | `cocobod.gh/resource_files/{201213,201314,201516,201617}.pdf` | sezony 2011/12 – 2016/17 | sezonowa (skup deklarowany) | [DO WERYFIKACJI] | pozostałe roczniki zwracają 404 |
| COCOBOD, tabela skupu | `cocobod.gh/cocoa-purchases?page={1,2}` (stan 23.10.2026), HTML | sezony 1947/48 – 2019/20 | sezonowa, regiony i suma | [DO WERYFIKACJI] | brak 1976/77; 1956/57 dwukrotnie; 1997/98: Central = Eastern (29 468 t), możliwa literówka; skup, nie produkcja (przemyt) |
| ICCO EX/146/7 „The World Cocoa Economy: Past and Present” | `icco.org/wp-content/uploads/2019/07/EX-146-7-World-Cocoa-Economy-2012-edited-1.pdf` | sezony 2007/08 – 2011/12 | sezonowa | warunki ICCO | tylko kontrola przypisania roku FAO; Ghana wg ICCO różni się od skupu COCOBOD (2007/08: 729,0 wobec 680,8) |
| ICCO, raporty roczne 2004/05 i 2006/07 | `icco.org/wp-content/uploads/2019/07/anrep{0405,0607}english-1.pdf` | sezony 2000/01 – 2006/07 | sezonowa | warunki ICCO | tabela produkcji, WKS i Ghana; 2006/07 zrewidowane w EX/146/7 (1292 → 1229,2); raporty 2007/08–2014/15 pod tym wzorcem zwracają 404 |
| ICCO, studium giełdy kakao, aneks WKS | `icco.org/wp-content/uploads/2-FEASIBILITY-STUDY-ON-AFRICA-COCOA-EXCHANGE_Annex_COTE-DIVOIRE.pdf` | sezony 2012/13 – 2021/22 | sezonowa (zakup „brousse”, CCC) | warunki ICCO | nagłówek „private and confidential”, plik publiczny na icco.org; w tabeli 4 sezon 2015/16 powiela 2014/15, wykres podaje 1 580 611 t (= QBCS 1581) |
| USDA FAS, Foreign Agriculture Circular: Cocoa (X 1988) | `archive.org/download/foreignagricultu288unit/` (OCR djvu) | sezony 1983/84 – 1988/89 | sezonowa | domena publiczna | tylko kontrola przypisania roku FAO; OCR z błędami |

**FAO a sezon (sprawdzone 23.10.2026 z tabelą COCOBOD).** Ghana: rok FAO = sezon s/s+1 do 1995
(różnica ≤ 0,1 tys. t w 1987, 1989, 1990, 1992, 1993 i 1995), s−1/s od 1996 (sezon 1995/96 jako 1995 i 1996); błędne
poziomy: 1988, 2005, 2011, 2014–2016. FAO dla Ghany nieużywane od rewizji. WKS (sprawdzone z ICCO
i CCC 23.10.2026): s/s+1 w 1983–1986 (USDA FAS); s−1/s w 2001–2015, zgodność do 1 tys. t poza
2010 (+4,7%) i 2014 (−6,2%); od 2016 FAO odbiega od ICCO o 1–8% i nie pasuje do żadnego
przypisania; 1987–2000 [DO WERYFIKACJI]. Suma FAO „WKS + Ghana” miesza sezony.

Mapa upraw CROPGRIDS v1.08 (figshare 22491997, CC BY 4.0) pobrana poza repozytorium; użyta raz,
do wyznaczenia obszaru WKS w `wynik.md` (udział pola kakao).

Niepobrane: Copernicus CDS (decyzja użytkownika), CFTC COT, zapasy ICE, ICCO, przemiał i przyjazdy do portów (płatne lub bez rzetelnej historii).
