"""Analizy kakao: sezonowość, pogoda/ENSO → cena, kakao → spółki, event study komunikatów CPC.

Uruchomienie z korzenia repozytorium:
    python src/analiza.py

Wynik: `wyniki/wyniki.json` (dane dashboardu). Rodziny testów są ustalone w kodzie przed
uruchomieniem; kierunek każdego predyktora wynika z hipotezy [HIPOTEZA] „mniejsza podaż → wyższa
cena”: susza, upał, El Niño → wzrost ceny kakao.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import dane
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.signal.windows import dpss
from statsmodels.stats.multitest import multipletests

KATALOG = Path(__file__).resolve().parents[1]
WYJSCIE = KATALOG / "wyniki" / "wyniki.json"
OSTATNI_MIESIAC = pd.Period("2026-09", "M")  # ostatni pełny miesiąc we wszystkich źródłach
HORYZONTY = (1, 3, 6)
SPOLKI = {"BARN.SW": "^SSMI", "LISP.SW": "^SSMI", "HSY": "^GSPC", "MDLZ": "^GSPC"}
KOSZYK_CZEKOLADY = ("LISP.SW", "HSY", "MDLZ")
OKNA_KAKAO = (1, 3, 6, 12)
Z_MDE = 2.8  # 80% mocy, test dwustronny 5%
# Znak zgodny z hipotezą: dodatnia wartość = oczekiwany wzrost ceny kakao.
PREDYKTORY = {
    "R3": ("opad 3 mies. (z, odwrócony)", -1),
    "R6": ("opad 6 mies. (z, odwrócony)", -1),
    "W3": ("wilgotność gleby 3 mies. (z, odwrócona)", -1),
    "T3": ("Tmax 3 mies. (z)", 1),
    "N34": ("Niño3.4 (z)", 1),
    "dN34": ("zmiana Niño3.4 w 3 mies. (z)", 1),
}


# ---------- narzędzia ----------
def liczba(v: float | None, cyfry: int = 6) -> float | None:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return None
    return round(float(v), cyfry)


def ols_hac(y: np.ndarray, X: np.ndarray, lag: int):
    return sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})


def bh(p: list[float]) -> list[float]:
    p = np.asarray(p, dtype=float)
    q = np.full_like(p, np.nan)
    ok = np.isfinite(p)
    if ok.any():
        q[ok] = multipletests(p[ok], method="fdr_bh")[1]
    return q.tolist()


def do_miesiaca(s: pd.Series) -> pd.Series:
    return s.loc[s.index <= OSTATNI_MIESIAC]


def przyszly(r: pd.Series, h: int) -> pd.Series:
    """Suma log-zwrotów z miesięcy t+1..t+h przypisana do t."""
    return r.rolling(h).sum().shift(-h)


def szereg_json(s: pd.Series, cyfry: int = 4) -> dict:
    return {"t": [str(i) for i in s.index], "v": [liczba(v, cyfry) for v in s.to_numpy()]}


def statystyki_strategii(zwroty: pd.Series) -> dict:
    z = zwroty.dropna()
    if len(z) < 12:
        return {}
    model = ols_hac(z.to_numpy(), np.ones((len(z), 1)), 2)
    krzywa = z.cumsum()
    return {
        "n": len(z),
        "srednia_roczna": liczba(z.mean() * 12, 4),
        "zmiennosc_roczna": liczba(z.std() * math.sqrt(12), 4),
        "sharpe": liczba(z.mean() / z.std() * math.sqrt(12), 3),
        "t": liczba(model.tvalues[0], 3),
        "p": liczba(model.pvalues[0], 4),
        "trafnosc": liczba((z > 0).mean(), 3),
        "max_obsuniecie": liczba((krzywa - krzywa.cummax()).min(), 4),
        "krzywa": szereg_json(krzywa),
    }


# ---------- dane miesięczne ----------
def zwroty() -> dict[str, pd.Series]:
    ps = dane.pink_sheet()
    return {
        "pink": do_miesiaca(np.log(ps).diff().dropna().rename("pink")),
        "coco": do_miesiaca(dane.zwroty_miesieczne("COCO.L")),
        "ccf": do_miesiaca(dane.zwroty_miesieczne("CC=F", "close")),
    }


OPISY_SZEREGOW = {
    "pink": "Pink Sheet (Bank Światowy, średnia miesięczna, USD/kg)",
    "coco": "COCO.L (WisdomTree Cocoa, rolowany indeks futures)",
    "ccf": "CC=F (ICE NY, ciągły kontrakt najbliższy, bez korekty rolowania)",
}


def sekcja_danych(r: dict[str, pd.Series]) -> dict:
    ceny = {
        "pink": dane.pink_sheet(),
        "coco": dane.yahoo("COCO.L")["adj"],
        "ccf": dane.yahoo("CC=F")["close"],
    }
    miesieczne = {}
    for k, c in ceny.items():
        if not isinstance(c.index, pd.PeriodIndex):
            c = c.groupby(c.index.to_period("M")).last()
        miesieczne[k] = szereg_json(do_miesiaca(c), 3)
    wspolne = pd.concat([r["ccf"], r["coco"]], axis=1, keys=["ccf", "coco"]).dropna()
    roznica = wspolne["ccf"] - wspolne["coco"]
    pogoda = dane.pogoda_pasa()
    return {
        "ceny": miesieczne,
        "pokrycie": [
            {
                "szereg": OPISY_SZEREGOW[k],
                "od": str(v.index.min()),
                "do": str(v.index.max()),
                "n": len(v),
                "sd_mies": liczba(v.std(), 4),
            }
            for k, v in r.items()
        ],
        "rolowanie": {
            "korelacja": liczba(wspolne.corr().iloc[0, 1], 3),
            "n": len(wspolne),
            "roznica_roczna": liczba(roznica.mean() * 12, 4),
            "roznica_wg_miesiaca": [
                liczba(roznica[roznica.index.month == m].mean(), 4) for m in range(1, 13)
            ],
        },
        "pogoda_od": str(pogoda.index.min()),
        "pogoda_do": str(pogoda.index.max()),
    }


# ---------- sezonowość ----------
def multitaper(x: np.ndarray, nw: float = 4.0, k: int = 7) -> dict:
    x = x - x.mean()
    n = len(x)
    tapery = dpss(n, nw, k)
    widmo_k = np.abs(np.fft.rfft(tapery * x, axis=1)) ** 2
    czest = np.fft.rfftfreq(n)
    psd = widmo_k.mean(axis=0)
    phi = np.corrcoef(x[1:], x[:-1])[0, 1]
    tlo = 1.0 / (1 + phi**2 - 2 * phi * np.cos(2 * np.pi * czest))
    tlo *= psd.mean() / tlo.mean()
    prog = tlo * stats.chi2.ppf(0.95, 2 * k) / (2 * k)
    u0 = tapery.sum(axis=1)
    testy = []
    for okres in (12, 6, 4):
        e = np.exp(-2j * np.pi * np.arange(n) / okres)
        y = tapery @ (x * e)
        mu = (u0 @ y) / (u0 @ u0)
        f_stat = (k - 1) * abs(mu) ** 2 * (u0 @ u0) / np.sum(np.abs(y - mu * u0) ** 2)
        testy.append(
            {
                "okres": okres,
                "F": liczba(f_stat, 3),
                "p": liczba(1 - stats.f.cdf(f_stat, 2, 2 * k - 2), 4),
            }
        )
    return {
        "czestotliwosc": [liczba(f, 5) for f in czest[1:]],
        "psd": [liczba(v, 8) for v in psd[1:]],
        "tlo95": [liczba(v, 8) for v in prog[1:]],
        "phi_ar1": liczba(phi, 3),
        "testy_f": testy,
    }


def sezonowosc(r: pd.Series, lag: int) -> dict:
    m = r.index.month
    y = r.to_numpy()
    dummy = np.column_stack([(m == k).astype(float) for k in range(1, 13)])
    model = ols_hac(y, dummy, lag)
    restrykcje = np.zeros((11, 12))
    for i in range(11):
        restrykcje[i, i], restrykcje[i, 11] = 1, -1
    wald = model.wald_test(restrykcje, scalar=True, use_f=False)
    kat = 2 * np.pi * m / 12
    harm = np.column_stack(
        [np.ones(len(y)), np.cos(kat), np.sin(kat), np.cos(2 * kat), np.sin(2 * kat)]
    )
    model_h = ols_hac(y, harm, lag)
    wald_h = model_h.wald_test(np.eye(5)[1:], scalar=True, use_f=False)
    kw = stats.kruskal(*[y[m == k] for k in range(1, 13)])
    miesiace = []
    for k in range(1, 13):
        w, reszta = y[m == k], y[m != k]
        t = stats.ttest_ind(w, reszta, equal_var=False)
        miesiace.append(
            {
                "miesiac": k,
                "n": int(len(w)),
                "srednia": liczba(w.mean(), 5),
                "se": liczba(w.std(ddof=1) / math.sqrt(len(w)), 5),
                "p": liczba(t.pvalue, 4),
                "mde": liczba(Z_MDE * y.std(ddof=1) / math.sqrt(len(w)), 4),
            }
        )
    for wiersz, q in zip(miesiace, bh([w["p"] for w in miesiace]), strict=True):
        wiersz["q_bh"] = liczba(q, 4)
    return {
        "n": len(y),
        "lat": round(len(y) / 12, 1),
        "od": str(r.index.min()),
        "do": str(r.index.max()),
        "wald_dummy_p": liczba(float(wald.pvalue), 4),
        "wald_harmoniki_p": liczba(float(wald_h.pvalue), 4),
        "kruskal_p": liczba(kw.pvalue, 4),
        "miesiace": miesiace,
        "spektrum": multitaper(y),
    }


def sezonowosc_oos(r: dict[str, pd.Series]) -> dict:
    """Prognoza = średnia tego samego miesiąca z Pink Sheet do roku poprzedniego włącznie."""
    pink = r["pink"]
    prognoza = {}
    for t in r["coco"].index.union(pink.index):
        historia = pink.loc[(pink.index.month == t.month) & (pink.index.year < t.year)]
        if len(historia) >= 20:
            prognoza[t] = historia.mean()
    prognoza = pd.Series(prognoza)
    wynik = {}
    for nazwa in ("coco", "pink"):
        zwrot = r[nazwa]
        if nazwa == "pink":
            zwrot = zwrot.loc[zwrot.index >= pd.Period("1990-01", "M")]
        p = prognoza.reindex(zwrot.index)
        strategia = np.sign(p) * zwrot
        sr_hist = zwrot.expanding().mean().shift(1)
        if nazwa == "pink":
            sr_hist = r["pink"].expanding().mean().shift(1).reindex(zwrot.index)
        ok = p.notna() & sr_hist.notna()
        e_mod, e_bm = zwrot[ok] - p[ok], zwrot[ok] - sr_hist[ok]
        cw = e_bm**2 - (e_mod**2 - (sr_hist[ok] - p[ok]) ** 2)
        cw_t = ols_hac(cw.to_numpy(), np.ones((ok.sum(), 1)), 2).tvalues[0]
        wynik[nazwa] = {
            "strategia": statystyki_strategii(strategia),
            "kupuj_trzymaj": statystyki_strategii(zwrot.loc[strategia.dropna().index]),
            "oos_r2": liczba(1 - (e_mod**2).sum() / (e_bm**2).sum(), 4),
            "cw_t": liczba(cw_t, 3),
            "cw_p": liczba(1 - stats.norm.cdf(cw_t), 4),
        }
    return wynik


def zmiennosc_sezonowa() -> dict:
    wynik = {}
    for nazwa, ticker, kolumna in (("coco", "COCO.L", "adj"), ("ccf", "CC=F", "close")):
        d = dane.zwroty_dzienne(ticker, kolumna)
        d = d.loc[d.index.to_period("M") <= OSTATNI_MIESIAC]
        rv = (d**2).groupby(d.index.to_period("M")).sum()
        rv = rv.loc[d.groupby(d.index.to_period("M")).size() >= 15]
        log_rv = np.log(rv)
        m = log_rv.index.month
        dummy = np.column_stack([(m == k).astype(float) for k in range(1, 13)])
        model = ols_hac(log_rv.to_numpy(), dummy, 6)
        restrykcje = np.zeros((11, 12))
        for i in range(11):
            restrykcje[i, i], restrykcje[i, 11] = 1, -1
        wynik[nazwa] = {
            "n": len(rv),
            "zmiennosc_roczna": [
                liczba(math.sqrt(rv[m == k].mean() * 12), 4) for k in range(1, 13)
            ],
            "wald_p": liczba(
                float(model.wald_test(restrykcje, scalar=True, use_f=False).pvalue), 4
            ),
            "kruskal_p": liczba(stats.kruskal(*[log_rv[m == k] for k in range(1, 13)]).pvalue, 4),
        }
    return wynik


# ---------- pogoda i ENSO ----------
def predyktory() -> pd.DataFrame:
    """Predyktory miesiąca danych m ze znakiem hipotezy; standaryzacja tylko na przeszłości."""
    pas = dane.pogoda_pasa()
    surowe = pd.DataFrame(
        {
            "R3": dane.anomalia_historyczna(pas["opad"].rolling(3).sum()),
            "R6": dane.anomalia_historyczna(pas["opad"].rolling(6).sum()),
            "W3": dane.anomalia_historyczna(pas["wilgotnosc"].rolling(3).mean()),
            "T3": dane.anomalia_historyczna(pas["tmax"].rolling(3).mean()),
        }
    )
    enso = dane.enso()["nino34"]
    for nazwa, s in (("N34", enso), ("dN34", enso - enso.shift(3))):
        sd = s.expanding(min_periods=120).std().shift(1)
        surowe[nazwa] = (s / sd).reindex(surowe.index)
    znakowane = pd.DataFrame({k: surowe[k] * PREDYKTORY[k][1] for k in PREDYKTORY})
    znakowane["C"] = znakowane.mean(axis=1, skipna=False)
    return znakowane


def regresje_predykcyjne(r: pd.Series, x: pd.DataFrame, poczatek_oos: pd.Period) -> list[dict]:
    """y(t→t+h) na sygnale z końca t; sygnał używa danych z miesiąca t−1 (opóźnienie publikacji)."""
    sygnal = x.shift(1)
    wiersze = []
    for nazwa in x.columns:
        for h in HORYZONTY:
            dane_ = pd.concat(
                [przyszly(r, h).rename("y"), sygnal[nazwa].rename("x")], axis=1
            ).dropna()
            if len(dane_) < 60:
                continue
            X = sm.add_constant(dane_["x"].to_numpy())
            model = ols_hac(dane_["y"].to_numpy(), X, h + 2)
            # OOS: współczynniki z próby, której cele są w pełni znane w chwili prognozy.
            prognozy, srednie, fakty = [], [], []
            for t in dane_.index:
                if t < poczatek_oos:
                    continue
                trening = dane_.loc[dane_.index <= t - h]
                if len(trening) < 60:
                    continue
                b = np.linalg.lstsq(
                    sm.add_constant(trening["x"].to_numpy()), trening["y"].to_numpy(), rcond=None
                )[0]
                prognozy.append(b[0] + b[1] * dane_.at[t, "x"])
                srednie.append(trening["y"].mean())
                fakty.append(dane_.at[t, "y"])
            prognozy, srednie, fakty = map(np.asarray, (prognozy, srednie, fakty))
            oos_r2 = cw_p = None
            if len(fakty) >= 36:
                oos_r2 = 1 - np.sum((fakty - prognozy) ** 2) / np.sum((fakty - srednie) ** 2)
                cw = (fakty - srednie) ** 2 - ((fakty - prognozy) ** 2 - (srednie - prognozy) ** 2)
                cw_t = ols_hac(cw, np.ones((len(cw), 1)), max(h - 1, 1)).tvalues[0]
                cw_p = 1 - stats.norm.cdf(cw_t)
            wiersze.append(
                {
                    "predyktor": nazwa,
                    "h": h,
                    "n": len(dane_),
                    "od": str(dane_.index.min()),
                    "do": str(dane_.index.max()),
                    "b_na_sd": liczba(model.params[1] * dane_["x"].std(), 5),
                    "t": liczba(model.tvalues[1], 3),
                    "p": liczba(model.pvalues[1], 4),
                    "r2": liczba(model.rsquared, 4),
                    "mde_r2": liczba(Z_MDE**2 / (len(dane_) / h), 4),
                    "oos_r2": liczba(oos_r2, 4),
                    "cw_p": liczba(cw_p, 4),
                    "n_oos": len(fakty),
                }
            )
    for w, q in zip(wiersze, bh([w["p"] for w in wiersze]), strict=True):
        w["q_bh"] = liczba(q, 4)
    return wiersze


def strategie_znakowe(r: pd.Series, x: pd.DataFrame) -> list[dict]:
    """Pozycja = znak predyktora (kierunek z hipotezy, bez estymacji); zwrot w miesiącu t+1."""
    sygnal = x.shift(1)
    wynik = []
    for nazwa in x.columns:
        pozycja = np.sign(sygnal[nazwa])
        zwrot = (pozycja * przyszly(r, 1)).dropna()
        s = statystyki_strategii(zwrot)
        s["predyktor"] = nazwa
        s["kupuj_trzymaj"] = statystyki_strategii(przyszly(r, 1).loc[zwrot.index]).get("sharpe")
        wynik.append(s)
    for w, q in zip(wynik, bh([w.get("p") for w in wynik]), strict=True):
        w["q_bh"] = liczba(q, 4)
    return wynik


def regresje_rownoczesne(r: pd.Series, x: pd.DataFrame) -> list[dict]:
    """Zwrot w tych samych 3 miesiącach co okno pogody: czy rynek wycenia pogodę na bieżąco."""
    y = r.rolling(3).sum()
    wiersze = []
    for nazwa in ("R3", "W3", "T3", "dN34", "C"):
        d = pd.concat([y.rename("y"), x[nazwa].rename("x")], axis=1).dropna()
        model = ols_hac(d["y"].to_numpy(), sm.add_constant(d["x"].to_numpy()), 4)
        wiersze.append(
            {
                "predyktor": nazwa,
                "n": len(d),
                "b_na_sd": liczba(model.params[1] * d["x"].std(), 5),
                "t": liczba(model.tvalues[1], 3),
                "p": liczba(model.pvalues[1], 4),
                "r2": liczba(model.rsquared, 4),
            }
        )
    for w, q in zip(wiersze, bh([w["p"] for w in wiersze]), strict=True):
        w["q_bh"] = liczba(q, 4)
    return wiersze


def korelacje_sezonowe(r: pd.Series, x: pd.DataFrame) -> list[dict]:
    """[EKSPLORACJA] korelacja opadu 3 mies. kończącego się w miesiącu m z ceną w 3 kolejnych."""
    sygnal = x["R3"].shift(1)
    y = przyszly(r, 3)
    wynik = []
    for m in range(1, 13):
        d = pd.concat([sygnal, y], axis=1, keys=["x", "y"]).dropna()
        d = d.loc[(d.index - 1).month == m]
        rho, p = stats.spearmanr(d["x"], d["y"])
        wynik.append(
            {"miesiac_konca_okna": m, "n": len(d), "rho": liczba(rho, 3), "p": liczba(p, 4)}
        )
    for w, q in zip(wynik, bh([w["p"] for w in wynik]), strict=True):
        w["q_bh"] = liczba(q, 4)
    return wynik


def sekcja_pogody(r: dict[str, pd.Series]) -> dict:
    x = predyktory()
    pas = dane.pogoda_pasa()
    return {
        "predyktory": {k: {"opis": v[0], "znak": v[1]} for k, v in PREDYKTORY.items()}
        | {"C": {"opis": "złożony: średnia sześciu (ze znakiem hipotezy)", "znak": 1}},
        "szeregi": {k: szereg_json(x[k].dropna(), 3) for k in ("R3", "N34", "C")}
        | {"opad_z": szereg_json(-x["R3"].dropna(), 3)},
        "klimatologia_opadu": [
            liczba(pas["opad"][pas.index.month == m].mean(), 1) for m in range(1, 13)
        ],
        "regresje": {
            "pink": regresje_predykcyjne(r["pink"], x, pd.Period("2001-01", "M")),
            "coco": regresje_predykcyjne(r["coco"], x, pd.Period("2016-01", "M")),
            "ccf": regresje_predykcyjne(r["ccf"], x, pd.Period("2008-01", "M")),
        },
        "strategie": {
            "coco": strategie_znakowe(r["coco"], x),
            "ccf": strategie_znakowe(r["ccf"], x),
        },
        "sezonowe_korelacje": korelacje_sezonowe(r["pink"], x),
        "rownoczesne": {k: regresje_rownoczesne(r[k], x) for k in ("pink", "coco", "ccf")},
    }


# ---------- zbiory (FAOSTAT, roczne) ----------
def sekcja_zbiorow() -> dict:
    """Pogoda → produkcja i produkcja → cena na danych rocznych.

    Rok FAO Y przypisany do sezonu Y/Y+1 (główne zbiory X Y – III Y+1) albo Y−1/Y; oba warianty
    [DO WERYFIKACJI]. Okna pogody dla sezonu S/S+1: opad IV–IX S, sucha pora XII S−1 – II S,
    Tmax IV–IX S, średni Niño3.4 VII S−1 – VI S.
    """
    prod = dane.produkcja_fao()
    wzrost = np.log(prod["razem"]).diff().rename("wzrost")
    pas = dane.pogoda_pasa()
    nino = dane.enso()["nino34"]
    lata = range(1982, 2025)

    def suma(s: pd.Series, r0: int, m0: int, r1: int, m1: int, mean: bool = False) -> float:
        od, do = pd.Period(year=r0, month=m0, freq="M"), pd.Period(year=r1, month=m1, freq="M")
        w = s.loc[(s.index >= od) & (s.index <= do)]
        return w.mean() if mean else w.sum()

    okna = pd.DataFrame(
        {
            "opad_IV_IX": [suma(pas["opad"], s, 4, s, 9) for s in lata],
            "pora_sucha_XII_II": [suma(pas["opad"], s - 1, 12, s, 2) for s in lata],
            "tmax_IV_IX": [suma(pas["tmax"], s, 4, s, 9, mean=True) for s in lata],
            "nino34_VII_VI": [suma(nino, s - 1, 7, s, 6, mean=True) for s in lata],
        },
        index=list(lata),
    )
    okna = (okna - okna.mean()) / okna.std()
    wiersze = []
    for wariant, przesuniecie in (("sezon Y/Y+1", 0), ("sezon Y−1/Y", 1)):
        for nazwa in okna.columns:
            x = okna[nazwa].copy()
            x.index = x.index + przesuniecie
            d = pd.concat([wzrost, x.rename("x")], axis=1).dropna()
            rho, p = stats.spearmanr(d["x"], d["wzrost"])
            r_p, p_p = stats.pearsonr(d["x"], d["wzrost"])
            wiersze.append(
                {
                    "wariant": wariant,
                    "okno": nazwa,
                    "n": len(d),
                    "pearson": liczba(r_p, 3),
                    "p_pearson": liczba(p_p, 4),
                    "spearman": liczba(rho, 3),
                    "p": liczba(p, 4),
                    "mde_rho": liczba(Z_MDE / math.sqrt(len(d)), 3),
                }
            )
    for w, q in zip(wiersze, bh([w["p"] for w in wiersze]), strict=True):
        w["q_bh"] = liczba(q, 4)
    # Produkcja → cena: zmiana średniej ceny rocznej Pink Sheet w roku Y i Y+1.
    cena = dane.pink_sheet()
    roczna = np.log(cena.groupby(cena.index.year).mean()).diff()
    punkty = pd.concat([wzrost, roczna.shift(-1).rename("cena_y1")], axis=1).dropna()
    punkty = punkty.loc[punkty.index <= 2024]
    cena_wiersze = []
    for nazwa, przes in (("cena w roku Y", 0), ("cena w roku Y+1", -1)):
        d = pd.concat([wzrost, roczna.shift(przes).rename("cena")], axis=1).dropna()
        d = d.loc[d.index <= 2024]
        rho, p = stats.spearmanr(d["wzrost"], d["cena"])
        model = ols_hac(d["cena"].to_numpy(), sm.add_constant(d["wzrost"].to_numpy()), 1)
        cena_wiersze.append(
            {
                "wariant": nazwa,
                "n": len(d),
                "spearman": liczba(rho, 3),
                "p": liczba(p, 4),
                "elastycznosc": liczba(model.params[1], 3),
                "t": liczba(model.tvalues[1], 3),
            }
        )
    return {
        "produkcja": {k: szereg_json(prod[k].rename(index=str), 0) for k in ("CIV", "GHA")},
        "pogoda_produkcja": wiersze,
        "produkcja_cena": cena_wiersze,
        "punkty": [
            {
                "rok": int(rok),
                "wzrost_produkcji": liczba(w.wzrost, 4),
                "zmiana_ceny_y1": liczba(w.cena_y1, 4),
            }
            for rok, w in punkty.iterrows()
        ],
    }


# ---------- kakao → spółki ----------
def sekcja_spolek(r: dict[str, pd.Series]) -> dict:
    nadwyzki = {
        s: do_miesiaca(dane.zwroty_miesieczne(s) - dane.zwroty_miesieczne(i)).dropna()
        for s, i in SPOLKI.items()
    }
    kakao = r["coco"]
    wspolczesnie = []
    for s, ex in nadwyzki.items():
        d = pd.concat([ex, kakao], axis=1, keys=["y", "x"]).dropna()
        model = ols_hac(d["y"].to_numpy(), sm.add_constant(d["x"].to_numpy()), 2)
        wspolczesnie.append(
            {
                "spolka": s,
                "n": len(d),
                "beta": liczba(model.params[1], 4),
                "t": liczba(model.tvalues[1], 3),
                "p": liczba(model.pvalues[1], 4),
            }
        )
    predykcyjne = []
    for s, ex in nadwyzki.items():
        for k in OKNA_KAKAO:
            for h in (1, 3):
                d = pd.concat(
                    [przyszly(ex, h), kakao.rolling(k).sum()], axis=1, keys=["y", "x"]
                ).dropna()
                model = ols_hac(d["y"].to_numpy(), sm.add_constant(d["x"].to_numpy()), h + 2)
                predykcyjne.append(
                    {
                        "spolka": s,
                        "k": k,
                        "h": h,
                        "n": len(d),
                        "b_na_sd": liczba(model.params[1] * d["x"].std(), 5),
                        "t": liczba(model.tvalues[1], 3),
                        "p": liczba(model.pvalues[1], 4),
                    }
                )
    for w, q in zip(predykcyjne, bh([w["p"] for w in predykcyjne]), strict=True):
        w["q_bh"] = liczba(q, 4)
    koszyk = pd.concat([nadwyzki[s] for s in KOSZYK_CZEKOLADY], axis=1).mean(axis=1, skipna=False)
    pozycja = -np.sign(kakao.rolling(6).sum())
    strategia = (pozycja * przyszly(koszyk, 1)).dropna()
    return {
        "wspolczesnie": wspolczesnie,
        "predykcyjne": predykcyjne,
        "strategia_koszyka": statystyki_strategii(strategia),
        "nadwyzki_skumulowane": {s: szereg_json(ex.cumsum(), 3) for s, ex in nadwyzki.items()},
    }


# ---------- event study: komunikaty CPC ----------
WAGI_STATUSU = {"El Niño": 2, "La Niña": -2, "El Niño watch": 1, "La Niña watch": -1}


def wynik_statusu(status: str) -> float | None:
    if status == "nieznany":
        return None
    return float(sum(WAGI_STATUSU.get(cz.strip(), 0) for cz in status.split("/")))


def sekcja_zdarzen() -> dict:
    kom = dane.komunikaty_cpc().dropna(subset=["data"]).sort_values("data")
    kom["wynik"] = kom["status"].map(wynik_statusu)
    kom = kom.dropna(subset=["wynik"])
    kom["zmiana"] = kom["wynik"].diff()
    zdarzenia = kom.loc[kom["zmiana"].fillna(0) != 0]
    wynik = {
        "komunikaty": len(kom),
        "zdarzenia": [
            {"data": str(z.data.date()), "status": z.status, "kierunek": int(np.sign(z.zmiana))}
            for z in zdarzenia.itertuples()
        ],
    }
    okna = {"[0]": (0, 0), "[0,+1]": (0, 1), "[-5,-1]": (-5, -1), "[+2,+10]": (2, 10)}
    for nazwa, ticker, kolumna in (("ccf", "CC=F", "close"), ("coco", "COCO.L", "adj")):
        r = dane.zwroty_dzienne(ticker, kolumna)
        indeks = r.index

        def dzien_zero(d: pd.Timestamp, indeks: pd.DatetimeIndex = indeks) -> int:
            return int(indeks.searchsorted(d))

        wiersze, sciezki = [], []
        for z in zdarzenia.itertuples():
            i0 = dzien_zero(z.data)
            if i0 - 260 < 0 or i0 + 10 >= len(r):
                continue
            mu = r.iloc[i0 - 260 : i0 - 10].mean()
            ar = r.iloc[i0 - 10 : i0 + 11].to_numpy() - mu
            sciezki.append(np.sign(z.zmiana) * ar)
            wiersze.append(
                {
                    k: float(np.sign(z.zmiana) * ar[10 + a : 10 + b + 1].sum())
                    for k, (a, b) in okna.items()
                }
            )
        tabela = pd.DataFrame(wiersze)
        testy = {}
        for k in okna:
            v = tabela[k].to_numpy()
            testy[k] = {
                "srednia": liczba(v.mean(), 5),
                "t": liczba(stats.ttest_1samp(v, 0).statistic, 3),
                "p": liczba(stats.ttest_1samp(v, 0).pvalue, 4),
                "dodatnich": int((v > 0).sum()),
                "n": len(v),
                "p_znakow": liczba(stats.binomtest(int((v > 0).sum()), len(v)).pvalue, 4),
                "mde": liczba(Z_MDE * v.std(ddof=1) / math.sqrt(len(v)), 4),
            }
        sciezka = np.cumsum(np.mean(sciezki, axis=0))
        # Zmienność w dniu każdego komunikatu vs pozostałe czwartki.
        dni_kom = {indeks[dzien_zero(d)] for d in kom["data"] if dzien_zero(d) < len(indeks)}
        czwartki = r.loc[(r.index.dayofweek == 3) & (r.index >= kom["data"].min())]
        w_dniu = czwartki.loc[czwartki.index.isin(dni_kom)].abs()
        poza = czwartki.loc[~czwartki.index.isin(dni_kom)].abs()
        wynik[nazwa] = {
            "testy": testy,
            "sciezka": {"dni": list(range(-10, 11)), "car": [liczba(v, 5) for v in sciezka]},
            "zmiennosc": {
                "n_kom": len(w_dniu),
                "n_inne": len(poza),
                "srednia_abs_kom": liczba(w_dniu.mean(), 5),
                "srednia_abs_inne": liczba(poza.mean(), 5),
                "p_mw": liczba(stats.mannwhitneyu(w_dniu, poza).pvalue, 4),
            },
        }
    return wynik


def main() -> None:
    r = zwroty()
    wyniki = {
        "dane": sekcja_danych(r),
        "sezonowosc": {
            "pink": sezonowosc(r["pink"], 3),
            "coco": sezonowosc(r["coco"], 2),
            "ccf": sezonowosc(r["ccf"], 2),
            "oos": sezonowosc_oos(r),
            "zmiennosc": zmiennosc_sezonowa(),
        },
        "pogoda": sekcja_pogody(r),
        "zbiory": sekcja_zbiorow(),
        "spolki": sekcja_spolek(r),
        "zdarzenia": sekcja_zdarzen(),
    }
    WYJSCIE.parent.mkdir(exist_ok=True)
    WYJSCIE.write_text(json.dumps(wyniki, ensure_ascii=False), encoding="utf-8")
    print(f"zapisano {WYJSCIE} ({WYJSCIE.stat().st_size / 1e3:.0f} kB)")


if __name__ == "__main__":
    main()
