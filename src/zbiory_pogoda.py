"""Pogoda → zbiory kakao, wersja 2: specyfikacja z `wynik.md` (zapisana przed przebiegiem).

K: kontrola pozytywna (replikacja Albright i in. 2026 na krajowej serii Ghany 2000/01–2023/24).
G: test Ghany 1983/84–2023/24 na przyrostach z oceną poza próbą. CHIRPS liczony tą samą ścieżką
wyłącznie jako kontrola produktu opadowego.

Uruchomienie z korzenia repozytorium:
    python src/zbiory_pogoda.py
"""

from __future__ import annotations

import json

import dane
import numpy as np
import pandas as pd
import statsmodels.api as sm
from analiza import Z_MDE, liczba, ols_hac
from scipy import stats

GHANA = {"szerokosc": (5.0, 7.0), "dlugosc": (-3.5, -0.5)}
OKRES_K = (2000, 2023)
OKRES_G = (1983, 2023)
MIN_TRENING = 15
PROG_OOS_R2 = 0.4
WYNIK = dane.KATALOG / "wyniki" / "zbiory_pogoda.json"


def p_jednostronne(t: float, oczekiwany_znak: int, df: float | None = None) -> float:
    """p dla hipotezy kierunkowej; rozkład t przy podanym df, inaczej normalny."""
    rozklad = stats.t(df) if df else stats.norm
    return float(1 - rozklad.cdf(oczekiwany_znak * t))


def kontrola_pozytywna(w: pd.DataFrame, prod: pd.Series) -> dict:
    """Produkcja / trend liniowy na standaryzowanych `R_w`, `R_d`; OLS jak w Albright i in."""
    lata = range(OKRES_K[0], OKRES_K[1] + 1)
    d = pd.concat([prod.loc[lata], w.loc[lata]], axis=1).dropna()
    t = np.arange(len(d))
    trend = np.polyval(np.polyfit(t, d[prod.name], 1), t)
    y = d[prod.name].to_numpy() / trend
    X = sm.add_constant((d[["R_w", "R_d"]] - d[["R_w", "R_d"]].mean()) / d[["R_w", "R_d"]].std())
    model = sm.OLS(y, X.to_numpy()).fit()
    # LOOCV jak w artykule (bez zachowania porządku czasu).
    bledy, bledy_sr = [], []
    for i in range(len(d)):
        maska = np.arange(len(d)) != i
        b = np.linalg.lstsq(X.to_numpy()[maska], y[maska], rcond=None)[0]
        bledy.append(y[i] - X.to_numpy()[i] @ b)
        bledy_sr.append(y[i] - y[maska].mean())
    loocv = 1 - np.sum(np.square(bledy)) / np.sum(np.square(bledy_sr))
    p_w = p_jednostronne(model.tvalues[1], -1, model.df_resid)
    p_d = p_jednostronne(model.tvalues[2], +1, model.df_resid)
    return {
        "sezony": f"{d.index.min()}/{d.index.min() + 1}–{d.index.max()}/{d.index.max() + 1}",
        "n": len(d),
        "alfa_w": liczba(model.params[1], 4),
        "p_w": liczba(p_w, 4),
        "alfa_d": liczba(model.params[2], 4),
        "p_d": liczba(p_d, 4),
        "r2": liczba(model.rsquared, 3),
        "r2_loocv": liczba(loocv, 3),
        "zaliczona": bool(model.params[1] < 0 < model.params[2] and max(p_w, p_d) < 0.05),
        "szereg": [
            {"sezon": int(s), "frakcja": liczba(v, 4), "R_w": liczba(rw, 3), "R_d": liczba(rd, 3)}
            for s, v, rw, rd in zip(d.index, y, d["R_w"], d["R_d"], strict=True)
        ],
    }


def przyrosty(w: pd.DataFrame, prod: pd.Series, okres: tuple[int, int]) -> pd.DataFrame:
    """Δlog produkcji (`y`) i Δ`R_w`, Δ`R_d`; indeks = późniejszy sezon pary."""
    lata = range(okres[0], okres[1] + 1)
    poziomy = pd.concat([np.log(prod.loc[lata]).rename("y"), w.loc[lata]], axis=1).dropna()
    return poziomy.diff().dropna()


def test_przyrostow(
    w: pd.DataFrame,
    prod: pd.Series,
    okres: tuple[int, int] = OKRES_G,
    min_trening: int = MIN_TRENING,
) -> dict:
    """Δlog produkcji na Δ`R_w`, Δ`R_d`; HAC(1), ocena poza próbą w oknie rozszerzającym."""
    d = przyrosty(w, prod, okres)
    X = sm.add_constant(d[["R_w", "R_d"]].to_numpy())
    model = ols_hac(d["y"].to_numpy(), X, 1)
    p_w = p_jednostronne(model.tvalues[1], -1)
    p_d = p_jednostronne(model.tvalues[2], +1)
    wald = model.f_test(np.array([[0, 1, 0], [0, 0, 1]]))
    prognozy, srednie, fakty, sezony = [], [], [], []
    for i in range(min_trening, len(d)):
        b = np.linalg.lstsq(X[:i], d["y"].to_numpy()[:i], rcond=None)[0]
        prognozy.append(X[i] @ b)
        srednie.append(d["y"].to_numpy()[:i].mean())
        fakty.append(d["y"].to_numpy()[i])
        sezony.append(int(d.index[i]))
    prognozy, srednie, fakty = map(np.asarray, (prognozy, srednie, fakty))
    oos_r2 = 1 - np.sum((fakty - prognozy) ** 2) / np.sum((fakty - srednie) ** 2)
    cw = (fakty - srednie) ** 2 - ((fakty - prognozy) ** 2 - (srednie - prognozy) ** 2)
    cw_t = ols_hac(cw, np.ones((len(cw), 1)), 1).tvalues[0]
    istotny = bool(model.params[1] < 0 < model.params[2] and max(p_w, p_d) < 0.05)
    if istotny and oos_r2 >= PROG_OOS_R2:
        werdykt = "ogniwo cenowe"
    elif istotny:
        werdykt = "wiedza o podaży, poniżej progu"
    else:
        werdykt = "nie widzę"
    sd = d[["R_w", "R_d"]].std()
    return {
        "sezony": f"{d.index.min()}/{d.index.min() + 1}–{d.index.max()}/{d.index.max() + 1}",
        "n": len(d),
        "b_w_na_sd": liczba(model.params[1] * sd["R_w"], 4),
        "p_w": liczba(p_w, 4),
        "b_d_na_sd": liczba(model.params[2] * sd["R_d"], 4),
        "p_d": liczba(p_d, 4),
        "p_wald": liczba(float(wald.pvalue), 4),
        "r2": liczba(model.rsquared, 3),
        "mde_r2": liczba(Z_MDE**2 / len(d), 3),
        "oos_r2": liczba(oos_r2, 3),
        "cw_p": liczba(1 - stats.norm.cdf(cw_t), 4),
        "n_oos": len(fakty),
        "werdykt": werdykt,
        "prognozy": [
            {"sezon": s, "fakt": liczba(f, 4), "model": liczba(m, 4), "srednia": liczba(b, 4)}
            for s, f, m, b in zip(sezony, fakty, prognozy, srednie, strict=True)
        ],
    }


def rownosc_okresow(w: pd.DataFrame, prod: pd.Series, granica: int = 2000) -> dict:
    """Post-hoc: Wald (HAC(1)) równości nachyleń przed i od sezonu `granica`."""
    d = przyrosty(w, prod, OKRES_G)
    po = (d.index >= granica).astype(float)
    X = np.column_stack([np.ones(len(d)), d["R_w"], d["R_d"], po, d["R_w"] * po, d["R_d"] * po])
    model = ols_hac(d["y"].to_numpy(), X, 1)
    wald = model.f_test(np.array([[0, 0, 0, 0, 1, 0], [0, 0, 0, 0, 0, 1]]))
    sd = d[["R_w", "R_d"]].std()
    przed = {"b_w_na_sd": model.params[1] * sd["R_w"], "b_d_na_sd": model.params[2] * sd["R_d"]}
    se = {"se_w_na_sd": model.bse[1] * sd["R_w"], "se_d_na_sd": model.bse[2] * sd["R_d"]}
    return {
        "granica": granica,
        "przed": {k: liczba(v, 4) for k, v in (przed | se).items()},
        "od": {
            "b_w_na_sd": liczba((model.params[1] + model.params[4]) * sd["R_w"], 4),
            "b_d_na_sd": liczba((model.params[2] + model.params[5]) * sd["R_d"], 4),
        },
        "p_rownosc": liczba(float(wald.pvalue), 4),
        "wariancja_y": {
            "przed": liczba(d.loc[d.index < granica, "y"].var(), 4),
            "od": liczba(d.loc[d.index >= granica, "y"].var(), 4),
        },
    }


def diagnostyka_okresow(w: pd.DataFrame, prod: pd.Series) -> list[dict]:
    """Post-hoc, poza specyfikacją: specyfikacja G w podokresach; nie zmienia werdyktu."""
    d = przyrosty(w, prod, OKRES_G)
    warianty = {
        "1983/84–1999/00": (d.index <= 1999),
        "2000/01–2023/24": (d.index >= 2000),
        "2000/01–2008/09": (d.index >= 2000) & (d.index <= 2008),
        "2009/10–2023/24": (d.index >= 2009),
        "2000/01–2023/24 bez 2010/11 i 2023/24": (d.index >= 2000) & ~d.index.isin([2010, 2023]),
    }
    wiersze = []
    for opis, maska in warianty.items():
        c = d.loc[maska]
        model = ols_hac(c["y"].to_numpy(), sm.add_constant(c[["R_w", "R_d"]].to_numpy()), 1)
        sd = c[["R_w", "R_d"]].std()
        wiersze.append(
            {
                "okres": opis,
                "n": len(c),
                "b_w_na_sd": liczba(model.params[1] * sd["R_w"], 4),
                "p_w": liczba(p_jednostronne(model.tvalues[1], -1), 4),
                "b_d_na_sd": liczba(model.params[2] * sd["R_d"], 4),
                "p_d": liczba(p_jednostronne(model.tvalues[2], +1), 4),
                "r2": liczba(model.rsquared, 3),
            }
        )
    return wiersze


def main() -> None:
    prod = dane.produkcja_ghany()
    wynik = {"specyfikacja": "wynik.md, sekcja „Pogoda → zbiory, wersja 2”"}
    for produkt in ("tamsat", "chirps"):
        if not (
            dane.SUROWE / "opad" / f"{produkt}_v{'3.1' if produkt == 'tamsat' else '2.0'}"
            f"_0.25_afryka_zach.npz"
        ).exists():
            continue
        w = dane.wskazniki_opadu(dane.opad_obszaru(produkt, **GHANA))
        wynik[produkt] = {
            "K": kontrola_pozytywna(w, prod),
            "G": test_przyrostow(w, prod),
            "diagnostyka_post_hoc": diagnostyka_okresow(w, prod),
            "rownosc_okresow_post_hoc": rownosc_okresow(w, prod),
            "G_od_2000_post_hoc": {
                str(m): test_przyrostow(w, prod, (1999, OKRES_G[1]), m) for m in (10, MIN_TRENING)
            },
        }
    wynik["produkcja_ghany"] = {int(s): liczba(v, 3) for s, v in prod.loc[1982:].items()}
    WYNIK.write_text(json.dumps(wynik, indent=1, ensure_ascii=False), encoding="utf-8")
    for produkt in ("tamsat", "chirps"):
        if produkt in wynik:
            k, g = wynik[produkt]["K"], wynik[produkt]["G"]
            print(produkt, "K:", {x: k[x] for x in k if x != "szereg"})
            print(produkt, "G:", {x: g[x] for x in g if x != "prognozy"})
            for wiersz in wynik[produkt]["diagnostyka_post_hoc"]:
                print(produkt, "D:", wiersz)
            print(produkt, "równość:", wynik[produkt]["rownosc_okresow_post_hoc"])
            for m, g2 in wynik[produkt]["G_od_2000_post_hoc"].items():
                skrot = {x: g2[x] for x in g2 if x != "prognozy"}
                print(produkt, f"G od 2000, trening {m}:", skrot)


if __name__ == "__main__":
    main()
