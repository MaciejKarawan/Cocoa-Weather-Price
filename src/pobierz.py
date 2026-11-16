"""Pobranie surowych danych do analizy kakao; istniejące pliki nie są nadpisywane.

Uruchomienie z korzenia repozytorium:
    python src/pobierz.py

Źródła i zastrzeżenia: `data/CATALOG.md`.
"""

from __future__ import annotations

import time
from datetime import UTC, date, datetime
from pathlib import Path

import requests

KATALOG = Path(__file__).resolve().parents[1]
SUROWE = KATALOG / "data" / "raw"
NAGLOWKI = {"User-Agent": "Mozilla/5.0 (badanie kakao; github.com/MaciejKarawan/Cocoa-Weather-Price)"}

# Kontrakt kakao ICE NY (ciągły najbliższy), ETC z rolowanym indeksem kakao, spółki i indeksy.
YAHOO = ("CC=F", "COCO.L", "BARN.SW", "LISP.SW", "HSY", "MDLZ", "^SSMI", "^GSPC")
# [ZAŁOŻENIE] punkty w głównych regionach kakaowych WKS i Ghany (bez mapy upraw).
PUNKTY = {
    "CIV_Soubre": (5.79, -6.61),
    "CIV_Daloa": (6.88, -6.45),
    "CIV_SanPedro": (4.75, -6.64),
    "CIV_Gagnoa": (6.13, -5.95),
    "CIV_Divo": (5.84, -5.36),
    "CIV_Abengourou": (6.73, -3.50),
    "GHA_Kumasi": (6.69, -1.62),
    "GHA_Goaso": (6.80, -2.52),
    "GHA_SefwiWiawso": (6.21, -2.49),
    "GHA_Dunkwa": (5.97, -1.78),
}
PARAMETRY_POWER = "PRECTOTCORR,T2M_MAX,GWETROOT"
PROSTE = {
    "enso/oni.ascii.txt": "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt",
    "enso/sstoi.indices": "https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices",
    "worldbank/CMO-Historical-Data-Monthly.xlsx": (
        "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
        "related/CMO-Historical-Data-Monthly.xlsx"
    ),
    "fao/Production_Crops_Livestock_E_All_Data_(Normalized).zip": (
        "https://bulks-faostat.fao.org/production/"
        "Production_Crops_Livestock_E_All_Data_(Normalized).zip"
    ),
}
MIESIACE = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")


def pobierz(url: str, cel: Path, *, proby: int = 4, pauza: float = 1.0) -> bool:
    """Zapisz odpowiedź 200 do pliku; zwraca False przy 404 lub wyczerpaniu prób."""
    if cel.is_file():
        return True
    cel.parent.mkdir(parents=True, exist_ok=True)
    for proba in range(proby):
        try:
            odp = requests.get(url, headers=NAGLOWKI, timeout=120)
        except requests.RequestException as blad:
            print(f"  błąd sieci ({blad.__class__.__name__}), próba {proba + 1}")
            time.sleep(5 * (proba + 1))
            continue
        if odp.status_code == 200:
            cel.write_bytes(odp.content)
            time.sleep(pauza)
            return True
        if odp.status_code == 404:
            return False
        print(f"  HTTP {odp.status_code}, próba {proba + 1}: {url}")
        time.sleep(10 * (proba + 1))
    return False


def main() -> None:
    teraz = int(datetime.now(UTC).timestamp())
    for ticker in YAHOO:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1=0&period2={teraz}"
            "&interval=1d&events=div%7Csplit&includeAdjustedClose=true"
        )
        print("yahoo", ticker, pobierz(url, SUROWE / "yahoo" / f"{ticker}.json", pauza=2.0))
    koniec = date.today().strftime("%Y%m%d")
    for nazwa, (szer, dl) in PUNKTY.items():
        url = (
            "https://power.larc.nasa.gov/api/temporal/daily/point"
            f"?parameters={PARAMETRY_POWER}&community=AG&latitude={szer}&longitude={dl}"
            f"&start=19810101&end={koniec}&format=JSON"
        )
        print("power", nazwa, pobierz(url, SUROWE / "power" / f"{nazwa}.json", pauza=2.0))
        # Długie zapytanie dzienne zwraca opad ×24 względem sum miesięcznych (CATALOG.md);
        # oficjalne sumy miesięczne służą do kontroli skali.
        url = (
            "https://power.larc.nasa.gov/api/temporal/monthly/point"
            f"?parameters=PRECTOTCORR_SUM&community=AG&latitude={szer}&longitude={dl}"
            f"&start=1981&end={date.today().year - 1}&format=JSON"
        )
        print("power mies.", nazwa, pobierz(url, SUROWE / "power_miesieczne" / f"{nazwa}.json"))
    for sciezka, url in PROSTE.items():
        print(sciezka, pobierz(url, SUROWE / sciezka))
    rok, mies = 2016, 6
    while (rok, mies) <= (date.today().year, date.today().month):
        nazwa = f"{MIESIACE[mies - 1]}{rok}"
        url = (
            "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/"
            f"enso_disc_{nazwa}/ensodisc.shtml"
        )
        ok = pobierz(url, SUROWE / "cpc_enso_disc" / f"{rok}-{mies:02d}.html", pauza=0.5)
        print("cpc", nazwa, ok)
        rok, mies = (rok + 1, 1) if mies == 12 else (rok, mies + 1)


if __name__ == "__main__":
    main()
