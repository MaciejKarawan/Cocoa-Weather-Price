"""Zbiory danych dashboardu (JSON, tablice wierszy) z `wyniki/wyniki.json`.

Uruchomienie z korzenia repozytorium:
    python src/eksport.py

Każdy wiersz zbioru o kilku tabelach ma kolumny `tabela` i unikalny `klucz`.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

KATALOG = Path(__file__).resolve().parents[1]
WYNIKI = KATALOG / "wyniki" / "wyniki.json"
CEL = KATALOG / "wyniki" / "dashboard"
NAZWY = {"pink": "Pink Sheet", "coco": "COCO.L", "ccf": "CC=F"}
BAZA_INDEKSU = "2010-01"

# Wnioski autora analizy; liczby stoją w zbiorach niżej, tu tylko ocena słowna.
WERDYKT = [
    (
        "sezonowosc",
        "Sezonowość ceny",
        "Czy cena kakao ma przewidywalny wzorzec kalendarzowy?",
        "Nie widzę: testy łączne i harmoniczne nieistotne na 66 latach, "
        "strategia kalendarzowa traci poza próbą.",
        "brak sygnału",
    ),
    (
        "zmiennosc",
        "Sezonowość ryzyka",
        "Czy zmienność zależy od miesiąca?",
        "Nie widzę: zmienność miesięczna bez istotnego wzorca w obu szeregach.",
        "brak sygnału",
    ),
    (
        "pogoda_cena",
        "Pogoda i ENSO → przyszła cena",
        "Czy obserwowana pogoda w pasie kakaowym i ENSO przewidują zwroty "
        "w horyzoncie 1–6 miesięcy?",
        "Nie po korekcie na wielokrotne testowanie. Opad i temperatura działają wbrew "
        "hipotezie, ENSO zgodnie z nią, ale słabo.",
        "brak sygnału",
    ),
    (
        "pogoda_teraz",
        "Pogoda → cena w tym samym okresie",
        "Czy rynek reaguje na pogodę, gdy ona się dzieje?",
        "Prawie wcale: pogoda tłumaczy ułamek procenta wariancji zwrotów także jednocześnie.",
        "brak sygnału",
    ),
    (
        "zbiory_cena",
        "Zbiory → cena",
        "Czy wielkość zbiorów WKS i Ghany przekłada się na cenę?",
        "Tak, silnie: niższa produkcja to wyższa cena w kolejnym roku.",
        "silny związek",
    ),
    (
        "pogoda_zbiory",
        "Pogoda → zbiory",
        "Czy nasz indeks pogody wyjaśnia zmiany produkcji?",
        "Nie widzę przy tej jakości danych; jedynym śladem jest ENSO, nieistotne po korekcie.",
        "słaby ślad",
    ),
    (
        "spolki",
        "Kakao → spółki czekoladowe",
        "Czy zmiana ceny kakao przewiduje względne zwroty producentów czekolady?",
        "Rynek wycenia koszt natychmiast (ujemna beta w tym samym miesiącu); "
        "opóźnionej reakcji nie widzę.",
        "brak sygnału",
    ),
    (
        "zdarzenia",
        "Komunikaty ENSO (CPC)",
        "Czy zmiana statusu ENSO porusza ceną kakao?",
        "Nie widzę reakcji w dniu komunikatu ani po nim; próba 27 zmian ma małą moc.",
        "brak sygnału",
    ),
]


def wiersze_szeregu(szereg: dict, nazwa: str) -> dict[str, float | None]:
    return dict(zip(szereg["t"], szereg["v"], strict=True)) if szereg else {}


def zapisz(nazwa: str, wiersze: list[dict]) -> None:
    CEL.mkdir(parents=True, exist_ok=True)
    plik = CEL / f"{nazwa}.json"
    plik.write_text(
        json.dumps(wiersze, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"{plik.name}: {len(wiersze)} wierszy, {plik.stat().st_size / 1e3:.0f} kB")


def ceny(w: dict) -> list[dict]:
    serie = {k: wiersze_szeregu(v, k) for k, v in w["dane"]["ceny"].items()}
    miesiace = sorted(set().union(*serie.values()))
    bazy = {k: s.get(BAZA_INDEKSU) for k, s in serie.items()}
    wynik = []
    for m in miesiace:
        wiersz = {"miesiac": m}
        for k, s in serie.items():
            v = s.get(m)
            wiersz[f"{k}_cena"] = v
            wiersz[f"{k}_indeks"] = round(100 * v / bazy[k], 2) if v and bazy[k] else None
        wynik.append(wiersz)
    return wynik


def pokrycie(w: dict) -> list[dict]:
    wynik = [
        {"klucz": k, **wiersz}
        for k, wiersz in zip(("pink", "coco", "ccf"), w["dane"]["pokrycie"], strict=True)
    ]
    rol = w["dane"]["rolowanie"]
    wynik.append(
        {
            "klucz": "rolowanie",
            "szereg": "CC=F względem COCO.L",
            "n": rol["n"],
            "korelacja": rol["korelacja"],
            "roznica_roczna": rol["roznica_roczna"],
        }
    )
    wynik.append(
        {
            "klucz": "pogoda",
            "szereg": "NASA POWER, 10 punktów pasa kakaowego",
            "od": w["dane"]["pogoda_od"],
            "do": w["dane"]["pogoda_do"],
        }
    )
    wynik.append(
        {
            "klucz": "cpc",
            "szereg": "Dyskusje diagnostyczne CPC o ENSO",
            "n": w["zdarzenia"]["komunikaty"],
        }
    )
    return wynik


def sezonowosc(w: dict) -> list[dict]:
    s = w["sezonowosc"]
    wynik = []
    for k in ("pink", "coco", "ccf"):
        for m in s[k]["miesiace"]:
            wynik.append(
                {
                    "tabela": "miesiace",
                    "klucz": f"m|{k}|{m['miesiac']}",
                    "szereg": k,
                    "instrument": NAZWY[k],
                    **m,
                }
            )
        testy_f = {t["okres"]: t["p"] for t in s[k]["spektrum"]["testy_f"]}
        oos = s["oos"].get(k, {})
        zm = s["zmiennosc"].get(k, {})
        wynik.append(
            {
                "tabela": "testy",
                "klucz": f"t|{k}",
                "szereg": k,
                "nazwa": NAZWY[k],
                "n": s[k]["n"],
                "lat": s[k]["lat"],
                "od": s[k]["od"],
                "do": s[k]["do"],
                "wald_dummy_p": s[k]["wald_dummy_p"],
                "wald_harm_p": s[k]["wald_harmoniki_p"],
                "kruskal_p": s[k]["kruskal_p"],
                "f12_p": testy_f.get(12),
                "f6_p": testy_f.get(6),
                "mde_miesiaca": s[k]["miesiace"][0]["mde"],
                "oos_r2": oos.get("oos_r2"),
                "cw_p": oos.get("cw_p"),
                "zm_wald_p": zm.get("wald_p"),
                "zm_kruskal_p": zm.get("kruskal_p"),
            }
        )
        sp = s[k]["spektrum"]
        for f, psd, tlo in zip(sp["czestotliwosc"], sp["psd"], sp["tlo95"], strict=True):
            wynik.append(
                {
                    "tabela": "spektrum",
                    "klucz": f"s|{k}|{f}",
                    "szereg": k,
                    "cykle_na_rok": round(f * 12, 4),
                    "psd": psd,
                    "tlo95": tlo,
                }
            )
    for k, zm in s["zmiennosc"].items():
        for i, v in enumerate(zm["zmiennosc_roczna"], start=1):
            wynik.append(
                {
                    "tabela": "zmiennosc",
                    "klucz": f"z|{k}|{i}",
                    "szereg": k,
                    "miesiac": i,
                    "zmiennosc_roczna": v,
                }
            )
    return wynik


def pogoda(w: dict) -> list[dict]:
    p = w["pogoda"]
    wynik = []
    for k, wiersze in p["regresje"].items():
        for r in wiersze:
            wynik.append(
                {
                    "tabela": "regresje",
                    "klucz": f"r|{k}|{r['predyktor']}|{r['h']}",
                    "szereg": k,
                    "instrument": NAZWY[k],
                    "opis": p["predyktory"][r["predyktor"]]["opis"],
                    **r,
                }
            )
    for k, wiersze in p["rownoczesne"].items():
        for r in wiersze:
            wynik.append(
                {
                    "tabela": "rownoczesne",
                    "klucz": f"w|{k}|{r['predyktor']}",
                    "szereg": k,
                    "instrument": NAZWY[k],
                    "opis": p["predyktory"][r["predyktor"]]["opis"],
                    **r,
                }
            )
    for r in p["sezonowe_korelacje"]:
        wynik.append({"tabela": "sezonowe", "klucz": f"k|{r['miesiac_konca_okna']}", **r})
    return wynik


def pogoda_szeregi(w: dict) -> list[dict]:
    s = {k: wiersze_szeregu(v, k) for k, v in w["pogoda"]["szeregi"].items()}
    miesiace = sorted(set(s["opad_z"]) | set(s["N34"]))
    return [
        {
            "miesiac": m,
            "opad_z": s["opad_z"].get(m),
            "nino34_z": s["N34"].get(m),
            "zlozony": s["C"].get(m),
        }
        for m in miesiace
    ]


def strategie(w: dict) -> tuple[list[dict], list[dict]]:
    pola = (
        "n",
        "srednia_roczna",
        "zmiennosc_roczna",
        "sharpe",
        "t",
        "p",
        "trafnosc",
        "max_obsuniecie",
    )
    wynik, krzywe = [], []

    def dodaj(klucz: str, grupa: str, nazwa: str, instrument: str, s: dict, q=None, bh=None):
        wynik.append(
            {
                "klucz": klucz,
                "grupa": grupa,
                "strategia": nazwa,
                "instrument": instrument,
                **{p: s.get(p) for p in pola},
                "q_bh": q,
                "kupuj_trzymaj_sharpe": bh,
            }
        )

    def krzywa(nazwa: str, s: dict) -> None:
        for t, v in zip(s["krzywa"]["t"], s["krzywa"]["v"], strict=True):
            krzywe.append({"strategia": nazwa, "miesiac": t, "skumulowany_log": v})

    oos = w["sezonowosc"]["oos"]
    for k in ("coco", "pink"):
        dodaj(
            f"sezon|{k}",
            "sezonowa",
            "Znak średniej tego miesiąca (Pink Sheet do roku t−1)",
            NAZWY[k],
            oos[k]["strategia"],
            bh=oos[k]["kupuj_trzymaj"].get("sharpe"),
        )
    opisy = w["pogoda"]["predyktory"]
    for k in ("coco", "ccf"):
        for s in w["pogoda"]["strategie"][k]:
            dodaj(
                f"pogoda|{k}|{s['predyktor']}",
                "pogodowa",
                f"Znak predyktora: {opisy[s['predyktor']]['opis']}",
                NAZWY[k],
                s,
                q=s.get("q_bh"),
                bh=s.get("kupuj_trzymaj"),
            )
    kosz = w["spolki"]["strategia_koszyka"]
    dodaj(
        "koszyk",
        "spolki",
        "Koszyk LISP+HSY+MDLZ względem rynku, pozycja przeciwna do kakao 6 mies.",
        "akcje",
        kosz,
    )
    krzywa("Kupuj i trzymaj COCO.L", oos["coco"]["kupuj_trzymaj"])
    krzywa("Sezonowa (COCO.L)", oos["coco"]["strategia"])
    zlozona = next(s for s in w["pogoda"]["strategie"]["coco"] if s["predyktor"] == "C")
    krzywa("Pogodowa złożona (COCO.L)", zlozona)
    krzywa("Koszyk spółek", kosz)
    return wynik, krzywe


def zbiory(w: dict) -> list[dict]:
    z = w["zbiory"]
    wynik = [
        {"tabela": "pogoda_produkcja", "klucz": f"pp|{r['wariant']}|{r['okno']}", **r}
        for r in z["pogoda_produkcja"]
    ]
    wynik += [
        {"tabela": "produkcja_cena", "klucz": f"pc|{r['wariant']}", **r}
        for r in z["produkcja_cena"]
    ]
    civ, gha = (
        wiersze_szeregu(z["produkcja"]["CIV"], "CIV"),
        wiersze_szeregu(z["produkcja"]["GHA"], "GHA"),
    )
    for rok in sorted(civ, key=int):
        wynik.append(
            {
                "tabela": "produkcja",
                "klucz": f"p|{rok}",
                "rok": int(rok),
                "civ_kt": round(civ[rok] / 1000, 1) if civ[rok] else None,
                "gha_kt": round(gha[rok] / 1000, 1) if gha.get(rok) else None,
            }
        )
    wynik += [{"tabela": "punkty", "klucz": f"pt|{r['rok']}", **r} for r in z["punkty"]]
    return wynik


def spolki(w: dict) -> list[dict]:
    s = w["spolki"]
    wynik = [{"tabela": "beta", "klucz": f"b|{r['spolka']}", **r} for r in s["wspolczesnie"]]
    wynik += [
        {"tabela": "predykcja", "klucz": f"p|{r['spolka']}|{r['k']}|{r['h']}", **r}
        for r in s["predykcyjne"]
    ]
    for spolka, szereg in s["nadwyzki_skumulowane"].items():
        for t, v in zip(szereg["t"], szereg["v"], strict=True):
            wynik.append(
                {
                    "tabela": "krzywe",
                    "klucz": f"c|{spolka}|{t}",
                    "spolka": spolka,
                    "miesiac": t,
                    "skumulowana_nadwyzka_log": v,
                }
            )
    return wynik


def zdarzenia(w: dict) -> list[dict]:
    z = w["zdarzenia"]
    wynik = [{"tabela": "lista", "klucz": f"e|{e['data']}", **e} for e in z["zdarzenia"]]
    for k in ("ccf", "coco"):
        for okno, t in z[k]["testy"].items():
            wynik.append(
                {
                    "tabela": "testy",
                    "klucz": f"t|{k}|{okno}",
                    "instrument": NAZWY[k],
                    "okno": okno,
                    **t,
                }
            )
        for d, v in zip(z[k]["sciezka"]["dni"], z[k]["sciezka"]["car"], strict=True):
            wynik.append(
                {
                    "tabela": "sciezka",
                    "klucz": f"s|{k}|{d}",
                    "instrument": NAZWY[k],
                    "dzien": d,
                    "car": v,
                }
            )
        wynik.append(
            {"tabela": "zmiennosc", "klucz": f"z|{k}", "instrument": NAZWY[k], **z[k]["zmiennosc"]}
        )
    return wynik


def main() -> None:
    w = json.loads(WYNIKI.read_text(encoding="utf-8"))
    zapisz(
        "werdykt",
        [
            dict(zip(("klucz", "obszar", "pytanie", "wynik", "ocena"), r, strict=True))
            for r in WERDYKT
        ],
    )
    zapisz("ceny", ceny(w))
    zapisz("pokrycie", pokrycie(w))
    zapisz("sezonowosc", sezonowosc(w))
    zapisz("pogoda", pogoda(w))
    zapisz("pogoda_szeregi", pogoda_szeregi(w))
    stat, krzywe = strategie(w)
    zapisz("strategie", stat)
    zapisz("krzywe", krzywe)
    zapisz("zbiory", zbiory(w))
    zapisz("spolki", spolki(w))
    zapisz("zdarzenia", zdarzenia(w))
    for plik in CEL.glob("*.json"):
        for wiersz in json.loads(plik.read_text(encoding="utf-8")):
            for v in wiersz.values():
                if isinstance(v, float) and not math.isfinite(v):
                    raise ValueError(f"{plik.name}: wartość nieskończona")


if __name__ == "__main__":
    main()
