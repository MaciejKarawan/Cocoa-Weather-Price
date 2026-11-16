"""Pogoda → zbiory WKS: replikacja Albright i in. 2026 (specyfikacja w `wynik.md`, 23.10.2026).

K_WKS: ścieżka kontroli pozytywnej z `zbiory_pogoda.py` na produkcji WKS i obszarze pasa
kakaowego WKS. Opisowo: postać Δlog jak G dla 2000/01–2023/24.

Uruchomienie z korzenia repozytorium:
    python src/zbiory_wks.py
"""

from __future__ import annotations

import json

import dane
import pandas as pd
import statsmodels.api as sm
from analiza import liczba, ols_hac
from scipy import stats
from zbiory_pogoda import (
    GHANA,
    OKRES_K,
    kontrola_pozytywna,
    p_jednostronne,
    przyrosty,
    test_przyrostow,
)

WKS = {"szerokosc": (5.0, 8.0), "dlugosc": (-8.5, -3.5)}
MIN_TRENING_DELTA = 10
WYNIK = dane.KATALOG / "wyniki" / "zbiory_wks.json"


def zgodnosc_wskaznikow(produkt: str) -> dict:
    """Korelacja Pearsona `R_w`, `R_d` obszarów WKS i Ghany w okresie K (poziomy i Δ)."""
    lata = range(OKRES_K[0], OKRES_K[1] + 1)
    wks = dane.wskazniki_opadu(dane.opad_obszaru(produkt, **WKS)).loc[lata]
    gha = dane.wskazniki_opadu(dane.opad_obszaru(produkt, **GHANA)).loc[lata]
    return {
        f"{miara}_{postac}": liczba(stats.pearsonr(a, b)[0], 3)
        for miara in ("R_w", "R_d")
        for postac, (a, b) in {
            "poziom": (wks[miara], gha[miara]),
            "delta": (wks[miara].diff().dropna(), gha[miara].diff().dropna()),
        }.items()
    }


def bez_sezonow(w: pd.DataFrame, prod: pd.Series) -> dict:
    """Post-hoc: postać Δlog 2001/02–2023/24 bez sezonów kryzysu (2010/11) i spadku (2023/24)."""
    d = przyrosty(w, prod, OKRES_K)
    wiersze = {}
    for opis, pominiete in {
        "bez 2010/11": [2010],
        "bez 2023/24": [2023],
        "bez obu": [2010, 2023],
    }.items():
        c = d.loc[~d.index.isin(pominiete)]
        model = ols_hac(c["y"].to_numpy(), sm.add_constant(c[["R_w", "R_d"]].to_numpy()), 1)
        sd = c[["R_w", "R_d"]].std()
        wiersze[opis] = {
            "n": len(c),
            "b_w_na_sd": liczba(model.params[1] * sd["R_w"], 4),
            "b_d_na_sd": liczba(model.params[2] * sd["R_d"], 4),
            "p_d": liczba(p_jednostronne(model.tvalues[2], +1), 4),
            "r2": liczba(model.rsquared, 3),
        }
    return wiersze


def main() -> None:
    prod = dane.produkcja_wks()
    w = dane.wskazniki_opadu(dane.opad_obszaru("tamsat", **WKS))
    wynik = {
        "specyfikacja": "wynik.md, sekcja „Pogoda → zbiory WKS”",
        "K_WKS": kontrola_pozytywna(w, prod),
        "delta_2000": test_przyrostow(w, prod, OKRES_K, MIN_TRENING_DELTA),
        "delta_post_hoc": bez_sezonow(w, prod),
        "zgodnosc_z_ghana": zgodnosc_wskaznikow("tamsat"),
        "produkcja_wks": {int(s): v for s, v in prod.items()},
    }
    WYNIK.write_text(json.dumps(wynik, indent=1, ensure_ascii=False), encoding="utf-8")
    k, g = wynik["K_WKS"], wynik["delta_2000"]
    print("K_WKS:", {x: k[x] for x in k if x != "szereg"})
    print("Δlog od 2000:", {x: g[x] for x in g if x != "prognozy"})
    print("Δlog post-hoc:", wynik["delta_post_hoc"])
    print("zgodność z Ghaną:", wynik["zgodnosc_z_ghana"])
    print(pd.DataFrame(k["szereg"]).set_index("sezon").round(3).to_string())


if __name__ == "__main__":
    main()
