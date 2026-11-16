"""Wycięcie dziennego opadu Afryki Zachodniej z plików TAMSAT (kontynent) i CHIRPS (glob).

Pliki źródłowe (1,3 GB i 43 × 71 MB) zostają poza repozytorium; do `data/raw/opad/` trafia wycinek
z metadanymi źródła (URL, rozmiar, SHA-256). Wymaga `h5py` (`pip install h5py`).

Uruchomienie z korzenia repozytorium:
    python src/opad.py tamsat <plik .nc>
    python src/opad.py chirps <katalog plików rocznych>
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import h5py
import numpy as np

KATALOG = Path(__file__).resolve().parents[1]
CEL = KATALOG / "data" / "raw" / "opad"
# Pas kakaowy WKS i Ghany z zapasem; środki komórek 0,25° obu produktów leżą na tej samej siatce.
SZEROKOSC = (3.5, 9.5)
DLUGOSC = (-9.0, 1.5)
URL_TAMSAT = (
    "https://gws-access.jasmin.ac.uk/public/tamsat/rfe/data_degraded/v3.1/daily/0.25/"
    "rfe1983-present_daily_0.25.v3.1.nc"
)
URL_CHIRPS = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p25/"
    "chirps-v2.0.{rok}.days_p25.nc"
)


def sha256(plik: Path) -> str:
    """Skrót SHA-256 pliku czytanego blokami."""
    skrot = hashlib.sha256()
    with plik.open("rb") as f:
        for blok in iter(lambda: f.read(1 << 24), b""):
            skrot.update(blok)
    return skrot.hexdigest()


def _indeksy(os: np.ndarray, zakres: tuple[float, float]) -> np.ndarray:
    return np.flatnonzero((os >= zakres[0]) & (os <= zakres[1]))


def _daty(f: h5py.File) -> np.ndarray:
    """Daty z osi czasu CF „days since R-M-D” (także bez zer wiodących, jak w CHIRPS)."""
    jednostka = f["time"].attrs["units"].decode()
    rok, mies, dzien = (int(x) for x in jednostka.split("since")[1].split()[0].split("-"))
    poczatek = date(rok, mies, dzien)
    dni = np.rint(f["time"][:]).astype(int)
    return np.array([(poczatek + timedelta(days=int(d))).isoformat() for d in dni])


def wytnij(f: h5py.File, zmienna: str) -> dict[str, np.ndarray]:
    """Wycinek prostokąta `SZEROKOSC` × `DLUGOSC` z osiami rosnącymi; wartości braku → NaN."""
    nazwy = ("lat", "lon") if "lat" in f else ("latitude", "longitude")
    lat, lon = f[nazwy[0]][:], f[nazwy[1]][:]
    iy, ix = _indeksy(lat, SZEROKOSC), _indeksy(lon, DLUGOSC)
    dane = f[zmienna][:, iy.min() : iy.max() + 1, ix.min() : ix.max() + 1].astype(np.float32)
    brak = f[zmienna].attrs.get("_FillValue")
    if brak is not None and np.isfinite(brak).all():
        dane[dane == brak[0]] = np.nan
    lat_w = lat[iy.min() : iy.max() + 1]
    if lat_w[0] > lat_w[-1]:
        lat_w, dane = lat_w[::-1], dane[:, ::-1, :]
    return {"lat": lat_w, "lon": lon[ix.min() : ix.max() + 1], "dane": dane}


def tamsat(plik: Path) -> None:
    """Wycinek TAMSAT v3.1 (`rfe_filled`, mm/dzień) z metadanymi źródła."""
    with h5py.File(plik, "r") as f:
        w = wytnij(f, "rfe_filled")
        daty = _daty(f)
    _zapisz("tamsat_v3.1_0.25", w, daty, URL_TAMSAT, [plik])


def chirps(katalog: Path) -> None:
    """Wycinek CHIRPS v2.0 (`precip`, mm/dzień) sklejony z plików rocznych."""
    pliki = sorted(katalog.glob("chirps-v2.0.*.days_p25.nc"))
    czesci, daty = [], []
    for plik in pliki:
        with h5py.File(plik, "r") as f:
            czesci.append(wytnij(f, "precip"))
            daty.append(_daty(f))
    w = {
        "lat": czesci[0]["lat"],
        "lon": czesci[0]["lon"],
        "dane": np.concatenate([c["dane"] for c in czesci]),
    }
    _zapisz("chirps_v2.0_0.25", w, np.concatenate(daty), URL_CHIRPS, pliki)


def _zapisz(
    nazwa: str, w: dict[str, np.ndarray], daty: np.ndarray, url: str, pliki: list[Path]
) -> None:
    CEL.mkdir(parents=True, exist_ok=True)
    wynik = CEL / f"{nazwa}_afryka_zach.npz"
    if wynik.exists():
        raise FileExistsError(f"{wynik} istnieje; surowe dane nie są nadpisywane")
    dane = np.where(np.isfinite(w["dane"]), w["dane"], np.nan).astype(np.float32)
    np.savez_compressed(wynik, lat=w["lat"], lon=w["lon"], daty=daty, opad=dane)
    meta = {
        "url": url,
        "zakres": {"szerokosc": SZEROKOSC, "dlugosc": DLUGOSC},
        "okres": [str(daty[0]), str(daty[-1])],
        "zrodla": [{"plik": p.name, "bajty": p.stat().st_size, "sha256": sha256(p)} for p in pliki],
    }
    (CEL / f"{nazwa}_afryka_zach.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print(nazwa, dane.shape, meta["okres"])


if __name__ == "__main__":
    {"tamsat": tamsat, "chirps": chirps}[sys.argv[1]](Path(sys.argv[2]))
