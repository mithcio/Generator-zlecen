"""Cennik placementów wydawców zewnętrznych (KIDOZ/Adverty/Odeeo/Crazygames/
POKI/...) — z zakładki "Traffic cennik" w Numery_zlecen_2026.xlsx, patrz
scripts/export_seed_data.py::export_cennik_wydawcow.

Klucz stawki to (wydawca, format) - "format" nie zawsze jest tym samym, co
Zlecenie.pola.format_reklamowy: dla KIDOZ/Adverty/Odeeo to dokładnie ta
wartość (różne stawki per KIDS/ADULTS), dla Crazygames to zawsze "Rewarded"
(jeden placement, patrz generator_wydawcy._kidoz_typ_kampanii - to ten sam
"kubełek"), dla POKI to nazwa placementu wybranego w kroku 5, z prefiksem
"POKI " (patrz KOLUMNA_FORMAT_POKI w generator_wydawcy.py)."""
import json
from pathlib import Path
from typing import NamedTuple

DATA_PLIK = Path(__file__).resolve().parent.parent / "data" / "cennik_wydawcow.json"

SYMBOLE_WALUT = {"EUR": "€", "USD": "$", "PLN": "zł"}


class Stawka(NamedTuple):
    cena: float
    waluta: str

    def sformatowana(self) -> str:
        symbol = SYMBOLE_WALUT.get(self.waluta, self.waluta)
        tekst_ceny = f"{self.cena:g}"
        return f"{tekst_ceny}{symbol}"


class BladCennika(Exception):
    """Brak aktywnej stawki dla (wydawca, format) w zakładce „Traffic
    cennik” — do uzupełnienia przez dział traffic, nie błąd programu."""


def _wczytaj() -> dict:
    if not DATA_PLIK.exists():
        return {}
    with open(DATA_PLIK, encoding="utf-8") as f:
        return json.load(f)


def stawka(wydawca: str, format_reklamowy: str) -> Stawka:
    dane = _wczytaj().get(wydawca, {}).get(format_reklamowy)
    if dane is None:
        raise BladCennika(
            f"Brak aktywnej stawki dla „{wydawca}” / „{format_reklamowy}” w cenniku "
            "(zakładka „Traffic cennik” w Numery_zlecen_2026.xlsx)."
        )
    return Stawka(cena=dane["cena"], waluta=dane["waluta"])
