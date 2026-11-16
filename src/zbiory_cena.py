"""Zbiory → cena kakao na sezonach (X s – IX s+1), rewizja korelacji z wersji 1 (post-hoc).

Wersja 1 liczyła sumę FAO „WKS + Ghana” (rok FAO) wobec średniej ceny w roku kalendarzowym Y+1;
rok FAO oznacza różne sezony w różnych latach i krajach (`data/CATALOG.md`). Tu: Ghana ze skupu
COCOBOD; WKS z FAO w obu możliwych przypisaniach sezonu, bo przed 2015/16 brak darmowej serii.

Uruchomienie z korzenia repozytorium:
    python src/zbiory_cena.py
"""

from __future__ import annotations

import json

import dane
import numpy as np
import pandas as pd
import statsmodels.api as sm
from analiza import liczba, ols_hac
from scipy import stats

OKRES = (1961, 2023)
PRZESUNIECIA_CENY = {"sezon s−1": -1, "sezon s": 0, "sezon s+1": 1}
WYNIK = dane.KATALOG / "wyniki" / "zbiory_cena.json"


def cena_sezonowa() -> pd.Series:
    """log średniej ceny Pink Sheet w sezonie X s – IX s+1; tylko pełne sezony."""
    cena = dane.pink_sheet()
    sezon = pd.Series(
        [m.year if m.month >= 10 else m.year - 1 for m in cena.index], index=cena.index
    )
    grupy = cena.groupby(sezon.to_numpy())
    srednia = grupy.mean().where(grupy.size() == 12)
    return np.log(srednia).dropna().rename("cena")


def wks(przypisanie: str) -> pd.Series:
    """Produkcja WKS z FAO (tys. t) indeksowana sezonem; `Y/Y+1` lub `Y−1/Y`."""
    szereg = dane.produkcja_fao()["CIV"] / 1000
    szereg.index = szereg.index - (1 if przypisanie == "Y−1/Y" else 0)
    return szereg


def serie_produkcji() -> dict[str, pd.Series]:
    gha = dane.produkcja_ghany()
    return {
        "Ghana (COCOBOD)": gha,
        "WKS Y/Y+1 + Ghana": (wks("Y/Y+1") + gha).dropna(),
        "WKS Y−1/Y + Ghana": (wks("Y−1/Y") + gha).dropna(),
    }


def korelacja(x: pd.Series, y: pd.Series) -> dict:
    d = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    rho, p = stats.spearmanr(d["x"], d["y"])
    model = ols_hac(d["y"].to_numpy(), sm.add_constant(d["x"].to_numpy()), 1)
    return {
        "n": len(d),
        "spearman": liczba(rho, 3),
        "p": liczba(p, 4),
        "elastycznosc": liczba(model.params[1], 3),
        "t_hac": liczba(model.tvalues[1], 2),
    }


def replikacja_v1() -> dict:
    """Wersja 1: Δlog FAO „razem” (rok Y) wobec Δlog średniej ceny w roku kalendarzowym Y+1."""
    cena = dane.pink_sheet()
    roczna = np.log(cena.groupby(cena.index.year).mean()).diff()
    wzrost = np.log(dane.produkcja_fao()["razem"]).diff()
    wynik = korelacja(wzrost, roczna.shift(-1))
    return wynik


def main() -> None:
    dcena = cena_sezonowa().diff()
    wynik = {"okres": f"{OKRES[0]}/{OKRES[0] + 1}–{OKRES[1]}/{OKRES[1] + 1}", "wiersze": []}
    for nazwa, prod in serie_produkcji().items():
        dprod = np.log(prod.loc[OKRES[0] - 1 : OKRES[1]]).diff().loc[OKRES[0] :]
        for opis, k in PRZESUNIECIA_CENY.items():
            wynik["wiersze"].append(
                {"produkcja": nazwa, "cena": opis} | korelacja(dprod, dcena.shift(-k))
            )
    wynik["replikacja_v1"] = replikacja_v1()
    WYNIK.write_text(json.dumps(wynik, indent=1, ensure_ascii=False), encoding="utf-8")
    for w in wynik["wiersze"]:
        print(w)
    print("v1:", wynik["replikacja_v1"])


if __name__ == "__main__":
    main()
