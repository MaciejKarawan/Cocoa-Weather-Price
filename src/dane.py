"""Przygotowanie danych do analizy kakao: szeregi dzienne, miesięczne i kalendarz komunikatów CPC.

Wszystko czyta `data/raw/` (zob. `pobierz.py`); nic nie zapisuje poza `data/processed/`.
"""

from __future__ import annotations

import html
import json
import re
import zipfile
from functools import cache
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd

KATALOG = Path(__file__).resolve().parents[1]
SUROWE = KATALOG / "data" / "raw"
PRZETWORZONE = KATALOG / "data" / "processed"
# [ZAŁOŻENIE] wagi krajów w indeksie pogody pasa kakaowego ≈ udziały w produkcji WKS:Ghana.
WAGI_KRAJOW = {"CIV": 0.7, "GHA": 0.3}
MIN_LAT_KLIMATOLOGII = 10


@cache
def yahoo(ticker: str) -> pd.DataFrame:
    """Notowania dzienne z datą sesji w strefie giełdy; wiersze bez ceny zamknięcia usunięte."""
    wynik = json.loads((SUROWE / "yahoo" / f"{ticker}.json").read_text())["chart"]["result"][0]
    strefa = wynik["meta"]["exchangeTimezoneName"]
    daty = pd.to_datetime(wynik["timestamp"], unit="s", utc=True).tz_convert(strefa).normalize()
    tabela = pd.DataFrame(
        {
            "close": wynik["indicators"]["quote"][0]["close"],
            "adj": wynik["indicators"]["adjclose"][0]["adjclose"],
            "volume": wynik["indicators"]["quote"][0]["volume"],
        },
        index=pd.DatetimeIndex(daty.tz_localize(None), name="data"),
    ).astype(float)
    tabela = tabela.loc[tabela["close"].notna() & (tabela["close"] > 0)]
    return tabela.loc[~tabela.index.duplicated(keep="last")]


def zwroty_dzienne(ticker: str, kolumna: str = "adj") -> pd.Series:
    return np.log(yahoo(ticker)[kolumna]).diff().dropna().rename(ticker)


def zwroty_miesieczne(ticker: str, kolumna: str = "adj") -> pd.Series:
    """Log-zwrot z ostatniego notowania miesiąca do ostatniego notowania kolejnego miesiąca."""
    cena = yahoo(ticker)[kolumna]
    koniec = cena.groupby(cena.index.to_period("M")).last()
    return np.log(koniec).diff().dropna().rename(ticker)


@cache
def pink_sheet() -> pd.Series:
    """Miesięczna cena kakao z Pink Sheet Banku Światowego (USD/kg, średnia z miesiąca)."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    plik = zipfile.ZipFile(SUROWE / "worldbank" / "CMO-Historical-Data-Monthly.xlsx")
    teksty = [
        "".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t"))
        for si in ET.fromstring(plik.read("xl/sharedStrings.xml")).findall("m:si", ns)
    ]
    wiersze = ET.fromstring(plik.read("xl/worksheets/sheet2.xml")).findall(
        ".//m:sheetData/m:row", ns
    )

    def wartosc(komorka: ET.Element) -> str | None:
        v = komorka.find("m:v", ns)
        if v is None:
            return None
        return teksty[int(v.text)] if komorka.get("t") == "s" else v.text

    kolumna = None
    dane: dict[pd.Period, float] = {}
    for wiersz in wiersze:
        komorki = {re.sub(r"\d", "", k.get("r")): wartosc(k) for k in wiersz.findall("m:c", ns)}
        if kolumna is None:
            kolumna = next((k for k, v in komorki.items() if v == "Cocoa"), None)
            continue
        okres, liczba = komorki.get("A"), komorki.get(kolumna)
        if okres and re.fullmatch(r"\d{4}M\d{2}", okres) and liczba:
            try:
                dane[pd.Period(okres.replace("M", "-"), "M")] = float(liczba)
            except ValueError:
                continue
    return pd.Series(dane, name="pink_sheet").sort_index()


def _sumy_miesieczne_opadu(plik: Path) -> pd.Series:
    parametr = json.loads(plik.read_text())["properties"]["parameter"]["PRECTOTCORR_SUM"]
    return pd.Series(
        {pd.Period(f"{k[:4]}-{k[4:]}", "M"): v for k, v in parametr.items() if not k.endswith("13")}
    ).replace(-999.0, np.nan)


@cache
def pogoda_punkty() -> pd.DataFrame:
    """Miesięczne wartości NASA POWER w punktach: opad (suma, mm), Tmax (średnia), GWETROOT.

    Długie zapytanie dzienne zwraca PRECTOTCORR ×24; dzielimy przez 24 i sprawdzamy zgodność
    z oficjalnymi sumami miesięcznymi PRECTOTCORR_SUM (CATALOG.md).
    """
    czesci = []
    for plik in sorted((SUROWE / "power").glob("*.json")):
        parametry = json.loads(plik.read_text())["properties"]["parameter"]
        dzienne = pd.DataFrame(parametry).replace(-999.0, np.nan)
        dzienne.index = pd.to_datetime(dzienne.index, format="%Y%m%d")
        dzienne["PRECTOTCORR"] = dzienne["PRECTOTCORR"] / 24.0
        okres = dzienne.index.to_period("M")
        pelne = dzienne.groupby(okres).count().min(axis=1) == dzienne.groupby(okres).size()
        miesieczne = pd.DataFrame(
            {
                "opad": dzienne["PRECTOTCORR"].groupby(okres).sum(min_count=1),
                "tmax": dzienne["T2M_MAX"].groupby(okres).mean(),
                "wilgotnosc": dzienne["GWETROOT"].groupby(okres).mean(),
            }
        ).loc[pelne]
        kontrola = _sumy_miesieczne_opadu(SUROWE / "power_miesieczne" / plik.name)
        wspolne = miesieczne.index.intersection(kontrola.index)
        if len(wspolne) < 500 or not np.allclose(
            miesieczne.loc[wspolne, "opad"], kontrola.loc[wspolne], atol=1e-6
        ):
            raise ValueError(f"{plik.stem}: opad dzienny/24 niezgodny z sumami miesięcznymi")
        miesieczne["punkt"] = plik.stem
        czesci.append(miesieczne)
    return pd.concat(czesci).rename_axis("miesiac")


def pogoda_pasa() -> pd.DataFrame:
    """Indeks pasa kakaowego: średnia punktów w kraju, potem wagi krajów `WAGI_KRAJOW`."""
    punkty = pogoda_punkty().reset_index()
    punkty["kraj"] = punkty["punkt"].str[:3]
    kraje = punkty.groupby(["miesiac", "kraj"])[["opad", "tmax", "wilgotnosc"]].mean()
    wagi = kraje.index.get_level_values("kraj").map(WAGI_KRAJOW).to_numpy()[:, None]
    pas = (kraje * wagi).groupby("miesiac").sum()
    return pas.loc[kraje.groupby("miesiac").size() == len(WAGI_KRAJOW)]


def anomalia_historyczna(szereg: pd.Series) -> pd.Series:
    """Z-score względem tych samych miesięcy z wcześniejszych lat (bez bieżącego i przyszłych)."""
    wynik = pd.Series(np.nan, index=szereg.index, name=szereg.name)
    for miesiac in range(1, 13):
        czesc = szereg.loc[szereg.index.month == miesiac]
        srednia = czesc.expanding().mean().shift(1)
        odchylenie = czesc.expanding().std().shift(1)
        liczba = czesc.expanding().count().shift(1)
        z = (czesc - srednia) / odchylenie
        wynik.loc[czesc.index] = z.where(liczba >= MIN_LAT_KLIMATOLOGII)
    return wynik


@cache
def produkcja_fao() -> pd.DataFrame:
    """Roczna produkcja ziarna kakao (t) WKS i Ghany z FAOSTAT; rok FAO, mapowanie na sezon
    [DO WERYFIKACJI]."""
    plik = zipfile.ZipFile(
        SUROWE / "fao" / "Production_Crops_Livestock_E_All_Data_(Normalized).zip"
    )
    czesci = pd.read_csv(
        plik.open("Production_Crops_Livestock_E_All_Data_(Normalized).csv"),
        encoding="utf-8",
        chunksize=500_000,
        usecols=["Area", "Item", "Element", "Year", "Value"],
    )
    wybrane = pd.concat(
        c.loc[
            (c["Item"] == "Cocoa beans")
            & (c["Element"] == "Production")
            & c["Area"].isin(["Côte d'Ivoire", "Ghana"])
        ]
        for c in czesci
    )
    tabela = wybrane.pivot_table(index="Year", columns="Area", values="Value")
    tabela.columns = ["CIV" if "Ivoire" in k else "GHA" for k in tabela.columns]
    tabela["razem"] = tabela["CIV"] + tabela["GHA"]
    return tabela.rename_axis("rok")


# Produkcja Ghany po 2019/20 (tys. t, sezon s/s+1); tabela skupu COCOBOD kończy się na 2019/20.
GHANA_SEZONY = {
    2020: (1047.0, "ICCO QBCS XLVIII-4"),
    2021: (683.0, "ICCO QBCS LI-2"),
    2022: (654.0, "ICCO QBCS LI-2"),
    2023: (449.0, "ICCO QBCS LI-2"),
}


@cache
def skup_cocobod() -> pd.Series:
    """Skup kakao w Ghanie (tys. t) z tabeli `cocobod.gh/cocoa-purchases`; indeks s = sezon s."""
    wiersze = {}
    for plik in sorted((SUROWE / "cocobod").glob("cocoa-purchases_p*.html")):
        tekst = plik.read_text("utf-8")
        tekst = re.sub(r"<script.*?</script>|<style.*?</style>", "", tekst, flags=re.S)
        tekst = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", tekst)))
        for m in re.finditer(r"\d+ (\d{4})/\d{2,4} (?:(?:[\d,]+|N/A) ){7}([\d,]+) ", tekst):
            wiersze[int(m.group(1))] = int(m.group(2).replace(",", "")) / 1000
    return pd.Series(wiersze, name="GHA").sort_index().rename_axis("sezon")


def produkcja_ghany() -> pd.Series:
    """Produkcja Ghany (tys. t), indeks s = sezon s/s+1: skup COCOBOD, od 2020/21 `GHANA_SEZONY`.

    FAO nieużywane: rok FAO to sezon s/s+1 do 1995 i s−1/s od 1996 (1995/96 dwukrotnie); błędne
    2011 i 2014–2016 (sprawdzone z tabelą COCOBOD, 23.10.2026)."""
    szereg = skup_cocobod().copy()
    for sezon, (wartosc, _) in GHANA_SEZONY.items():
        szereg.loc[sezon] = wartosc
    return szereg.sort_index()


# Produkcja WKS (tys. t, sezon s/s+1); najnowsza dostępna rewizja; źródła w `data/CATALOG.md`.
WKS_SEZONY = {
    2000: (1212.0, "ICCO, raport roczny 2004/05"),
    2001: (1265.0, "ICCO, raport roczny 2004/05"),
    2002: (1352.0, "ICCO, raport roczny 2006/07"),
    2003: (1407.0, "ICCO, raport roczny 2006/07"),
    2004: (1286.0, "ICCO, raport roczny 2006/07"),
    2005: (1408.0, "ICCO, raport roczny 2006/07"),
    2006: (1229.2, "ICCO EX/146/7: 1382,4 − 153,2"),
    2007: (1382.4, "ICCO EX/146/7"),
    2008: (1223.2, "ICCO EX/146/7"),
    2009: (1242.3, "ICCO EX/146/7"),
    2010: (1511.3, "ICCO EX/146/7"),
    2011: (1485.9, "FAO 2012 (rok FAO = sezon s−1/s w 2001–2013)"),
    2012: (1449.0, "CCC, aneks ICCO (studium giełdy kakao)"),
    2013: (1746.2, "CCC, aneks ICCO"),
    2014: (1795.9, "CCC, aneks ICCO"),
    2015: (1581.0, "ICCO QBCS XLIV-4"),
    2016: (2020.0, "ICCO QBCS XLV-4"),
    2017: (1964.0, "ICCO QBCS XLV-4"),
    2018: (2154.0, "ICCO QBCS XLVII-4"),
    2019: (2105.0, "ICCO QBCS XLVIII-4"),
    2020: (2248.0, "ICCO QBCS XLVIII-4"),
    2021: (2121.0, "ICCO QBCS L-4"),
    2022: (2241.0, "ICCO QBCS LI-2"),
    2023: (1674.0, "ICCO QBCS LI-2"),
}


def produkcja_wks() -> pd.Series:
    """Produkcja WKS (tys. t), indeks s = sezon s/s+1, z `WKS_SEZONY`."""
    szereg = pd.Series({s: v for s, (v, _) in WKS_SEZONY.items()}, name="CIV")
    return szereg.rename_axis("sezon")


@cache
def opad_obszaru(produkt: str, szerokosc: tuple, dlugosc: tuple) -> pd.Series:
    """Dzienny opad (mm) uśredniony po komórkach 0,25° prostokąta; produkt `tamsat` lub `chirps`."""
    plik = {"tamsat": "tamsat_v3.1_0.25", "chirps": "chirps_v2.0_0.25"}[produkt]
    z = np.load(SUROWE / "opad" / f"{plik}_afryka_zach.npz")
    iy = (z["lat"] >= szerokosc[0]) & (z["lat"] <= szerokosc[1])
    ix = (z["lon"] >= dlugosc[0]) & (z["lon"] <= dlugosc[1])
    srednia = np.nanmean(z["opad"][:, iy][:, :, ix], axis=(1, 2))
    return pd.Series(srednia, index=pd.DatetimeIndex(z["daty"]), name=produkt)


def wskazniki_opadu(opad: pd.Series) -> pd.DataFrame:
    """Albright i in. 2026: `R_w` = średnia z IV–VI miesięcznego 95. percentyla opadu dziennego
    w roku s; `R_d` = średni opad dzienny XI s – II s+1. Indeks s; tylko pełne miesiące."""
    dni = opad.groupby(opad.index.to_period("M"))
    miesiace = pd.DataFrame({"p95": dni.quantile(0.95), "srednia": dni.mean(), "n": dni.size()})
    miesiace = miesiace.loc[miesiace["n"] == miesiace.index.days_in_month]
    lata = sorted({m.year for m in miesiace.index})
    wiersze = {}
    for s in lata:
        mokre = [pd.Period(year=s, month=m, freq="M") for m in (4, 5, 6)]
        suche = [pd.Period(year=s, month=m, freq="M") for m in (11, 12)] + [
            pd.Period(year=s + 1, month=m, freq="M") for m in (1, 2)
        ]
        if all(m in miesiace.index for m in mokre + suche):
            dni_suche = opad.loc[str(suche[0].start_time.date()) : str(suche[-1].end_time.date())]
            wiersze[s] = {
                "R_w": miesiace.loc[mokre, "p95"].mean(),
                "R_d": dni_suche.mean(),
            }
    return pd.DataFrame.from_dict(wiersze, orient="index").rename_axis("sezon")


@cache
def enso() -> pd.DataFrame:
    """Miesięczna anomalia Niño3.4 (OISST, CPC) i ONI przypisany do środkowego miesiąca sezonu."""
    sst = pd.read_csv(SUROWE / "enso" / "sstoi.indices", sep=r"\s+")
    sst.columns = ["rok", "mies", "n12", "a12", "n3", "a3", "n4", "a4", "n34", "nino34"]
    sst.index = pd.PeriodIndex(
        [
            pd.Period(year=r, month=m, freq="M")
            for r, m in zip(sst["rok"], sst["mies"], strict=True)
        ],
        name="miesiac",
    )
    oni = pd.read_csv(SUROWE / "enso" / "oni.ascii.txt", sep=r"\s+")
    srodek = {
        s: i + 1
        for i, s in enumerate(
            ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
        )
    }
    oni.index = pd.PeriodIndex(
        [
            pd.Period(year=r, month=srodek[s], freq="M")
            for s, r in zip(oni["SEAS"], oni["YR"], strict=True)
        ],
        name="miesiac",
    )
    return pd.DataFrame({"nino34": sst["nino34"], "oni": oni["ANOM"]})


STATUSY = (
    ("final el niño advisory", "koniec El Niño"),
    ("final la niña advisory", "koniec La Niña"),
    ("el niño advisory", "El Niño"),
    ("la niña advisory", "La Niña"),
    ("el niño watch", "El Niño watch"),
    ("la niña watch", "La Niña watch"),
    ("not active", "neutralny"),
)


def _status(tekst: str) -> str:
    tekst = tekst.lower()
    znalezione = [nazwa for klucz, nazwa in STATUSY if klucz in tekst]
    if not znalezione:
        return "nieznany"
    # "Final El Niño Advisory" zawiera "el niño advisory"; bierzemy pierwsze dopasowanie z listy.
    return " / ".join(
        dict.fromkeys(
            z
            for z in znalezione
            if not (z in ("El Niño", "La Niña") and f"koniec {z}" in znalezione)
        )
    )


def komunikaty_cpc() -> pd.DataFrame:
    """Daty i status systemu ostrzeżeń ENSO z miesięcznych dyskusji diagnostycznych CPC."""
    wiersze = []
    for plik in sorted((SUROWE / "cpc_enso_disc").glob("*.html")):
        # Część stron archiwum ma HTML zapisany jako encje; odkodowanie przed usunięciem znaczników.
        surowy = html.unescape(plik.read_text(errors="ignore"))
        tekst = html.unescape(re.sub(r"<[^>]+>", " ", surowy))
        tekst = re.sub(r"\s+", " ", tekst)
        miesiace = (
            "January|February|March|April|May|June|July|August|September|October|November|December"
        )
        po_naglowku = tekst[tekst.find("issued by") :]
        data = re.search(rf"(\d{{1,2}} (?:{miesiace}) \d{{4}})", po_naglowku)
        po_statusie = tekst[tekst.find("ENSO Alert System Status:") + 25 :][:400]
        koniec = re.search(r"Synopsis", po_statusie)
        fragment = po_statusie[: koniec.start()] if koniec else po_statusie[:150]
        wiersze.append(
            {
                "plik": plik.stem,
                "data": pd.to_datetime(data.group(1)) if data else pd.NaT,
                "status_tekst": fragment.strip()[:120],
                "status": _status(fragment) if "ENSO Alert System Status:" in tekst else "nieznany",
            }
        )
    return pd.DataFrame(wiersze)
