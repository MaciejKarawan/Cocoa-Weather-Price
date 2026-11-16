"""Pogoda → cena kakao: specyfikacja w `wynik.md` (23.10.2026).

Bramka: czy pora sucha liczona do 31 grudnia (`R_d31`) wyjaśnia przyrosty zbiorów Ghany i WKS.
Test ceny: Δ pory suchej w pasie WKS + Ghana wobec zwrotu Pink Sheet w oknie po znanym sygnale.

Uruchomienie z korzenia repozytorium:
    python src/pogoda_cena.py
"""

from __future__ import annotations

import json

import dane
import numpy as np
import pandas as pd
import statsmodels.api as sm
from analiza import liczba, ols_hac
from scipy import stats
from zbiory_pogoda import GHANA, OKRES_G, OKRES_K, p_jednostronne, przyrosty
from zbiory_wks import WKS

OKRES_CENY = (1984, 2025)
Z_90 = stats.norm.ppf(0.95)
WYNIK = dane.KATALOG / "wyniki" / "pogoda_cena.json"


def pora_sucha_do_grudnia(opad: pd.Series) -> pd.Series:
    """`R_d31`: średni opad dzienny XI–XII roku s; indeks s; tylko pełne okna (61 dni)."""
    wartosci = {}
    for s in sorted(set(opad.index.year)):
        okno = opad.loc[f"{s}-11-01" : f"{s}-12-31"]
        if len(okno) == 61:
            wartosci[s] = okno.mean()
    return pd.Series(wartosci, name="R_d31").rename_axis("sezon")


def nachylenie(w: pd.DataFrame, prod: pd.Series, okres: tuple[int, int], miara: str) -> dict:
    """Δlog produkcji na Δ`miara` ze stałą, HAC(1); efekt na sd i p jednostronne (znak +)."""
    d = przyrosty(w[[miara]], prod, okres)
    model = ols_hac(d["y"].to_numpy(), sm.add_constant(d[[miara]].to_numpy()), 1)
    return {
        "sezony": f"{d.index.min()}/{d.index.min() + 1}–{d.index.max()}/{d.index.max() + 1}",
        "n": len(d),
        "b_na_sd": liczba(model.params[1] * d[miara].std(), 4),
        "p": liczba(p_jednostronne(model.tvalues[1], +1), 4),
        "r2": liczba(model.rsquared, 3),
    }


def bramka() -> dict:
    kraje = {
        "Ghana": (dane.produkcja_ghany(), GHANA, OKRES_G),
        "WKS": (dane.produkcja_wks(), WKS, OKRES_K),
    }
    wynik = {}
    for kraj, (prod, obszar, okres) in kraje.items():
        opad = dane.opad_obszaru("tamsat", **obszar)
        w = pd.concat([dane.wskazniki_opadu(opad)["R_d"], pora_sucha_do_grudnia(opad)], axis=1)
        wynik[kraj] = {miara: nachylenie(w, prod, okres, miara) for miara in ("R_d31", "R_d")}
    wynik["przechodzi"] = bool(
        all(wynik[k]["R_d31"]["b_na_sd"] > 0 and wynik[k]["R_d31"]["p"] < 0.05 for k in kraje)
    )
    return wynik


def sygnaly() -> pd.DataFrame:
    """`R_d` i `R_d31` dla średniej obszarów WKS i Ghany z wagami `WAGI_KRAJOW`."""
    opad = dane.WAGI_KRAJOW["CIV"] * dane.opad_obszaru("tamsat", **WKS) + dane.WAGI_KRAJOW[
        "GHA"
    ] * dane.opad_obszaru("tamsat", **GHANA)
    return pd.concat([dane.wskazniki_opadu(opad)["R_d"], pora_sucha_do_grudnia(opad)], axis=1)


def stopy_zwrotu() -> pd.DataFrame:
    """log IX s+1 − log III s+1 (V1), log IX s+1 − log I s+1 (V2), log III s+1 − log X s
    (równoczesny) z Pink Sheet; indeks s."""
    cena = np.log(dane.pink_sheet())
    wiersze = {}
    for s in range(OKRES_CENY[0], OKRES_CENY[1] + 1):
        okresy = {m: pd.Period(year=s + 1, month=m, freq="M") for m in (1, 3, 9)}
        okresy[10] = pd.Period(year=s, month=10, freq="M")
        if all(o in cena.index for o in okresy.values()):
            wiersze[s] = {
                "V1": cena[okresy[9]] - cena[okresy[3]],
                "V2": cena[okresy[9]] - cena[okresy[1]],
                "rownoczesny": cena[okresy[3]] - cena[okresy[10]],
            }
    return pd.DataFrame.from_dict(wiersze, orient="index").rename_axis("sezon")


def test_ceny(sygnal: pd.Series, zwrot: pd.Series, pomin: tuple[int, ...] = ()) -> dict:
    """Zwrot na standaryzowanej Δ sygnału, HAC(1); znak oczekiwany ujemny; 90% przedział.

    `pomin`: sezony usuwane po różnicowaniu (kontrola post-hoc)."""
    d = pd.concat([sygnal.diff().rename("x"), zwrot.rename("y")], axis=1).dropna()
    d = d.drop(list(pomin), errors="ignore")
    z = (d["x"] - d["x"].mean()) / d["x"].std()
    model = ols_hac(d["y"].to_numpy(), sm.add_constant(z.to_numpy()), 1)
    b, se = model.params[1], model.bse[1]
    rho, p_rho = stats.spearmanr(d["x"], d["y"])
    p = p_jednostronne(model.tvalues[1], -1)
    return {
        "sezony": f"{d.index.min()}/{d.index.min() + 1}–{d.index.max()}/{d.index.max() + 1}",
        "n": len(d),
        "b_na_sd": liczba(b, 4),
        "przedzial_90": [liczba(b - Z_90 * se, 4), liczba(b + Z_90 * se, 4)],
        "p": liczba(p, 4),
        "r2": liczba(model.rsquared, 3),
        "spearman": liczba(rho, 3),
        "p_spearman_dwustronne": liczba(p_rho, 4),
        "istotny": bool(b < 0 and p < 0.05),
    }


def main() -> None:
    wynik = {"specyfikacja": "wynik.md, sekcja „Pogoda → cena”", "bramka_V2": bramka()}
    for kraj in ("Ghana", "WKS"):
        for miara, wiersz in wynik["bramka_V2"][kraj].items():
            print(kraj, miara, wiersz)
    print("bramka V2 przechodzi:", wynik["bramka_V2"]["przechodzi"])
    s, r = sygnaly(), stopy_zwrotu()
    wynik["cena"] = {"V1": test_ceny(s["R_d"], r["V1"])}
    if wynik["bramka_V2"]["przechodzi"]:
        wynik["cena"]["V2"] = test_ceny(s["R_d31"], r["V2"])
    wynik["cena"]["rownoczesny_post_hoc"] = test_ceny(s["R_d"], r["rownoczesny"])
    wynik["sd_zwrotu"] = {k: liczba(v, 4) for k, v in r.std().items()}
    pary = {"rownoczesny": ("R_d", "rownoczesny"), "V1": ("R_d", "V1"), "V2": ("R_d31", "V2")}
    wynik["bez_sezonow_post_hoc"] = {
        f"{nazwa} bez {'+'.join(map(str, pomin))}": test_ceny(s[x], r[y], pomin)
        for pomin in ((2025,), (2023, 2024, 2025))
        for nazwa, (x, y) in pary.items()
    }
    WYNIK.write_text(json.dumps(wynik, indent=1, ensure_ascii=False), encoding="utf-8")
    for wariant, wiersz in wynik["cena"].items():
        print("cena", wariant, wiersz)
    print("sd zwrotu:", wynik["sd_zwrotu"])
    for opis, wiersz in wynik["bez_sezonow_post_hoc"].items():
        print(opis, {k: wiersz[k] for k in ("n", "b_na_sd", "przedzial_90", "p", "spearman")})


if __name__ == "__main__":
    main()
