"""Cennik placementów wydawców zewnętrznych (KIDOZ/Adverty/Odeeo/Crazygames/
POKI/...) — z zakładki "Traffic cennik" w Numery_zlecen_2026.xlsx, patrz
app/services/export_seed_data.py::export_cennik_wydawcow.

Klucz stawki to (wydawca, format) - "format" nie zawsze jest tym samym, co
Zlecenie.pola.format_reklamowy: dla KIDOZ/Adverty/Odeeo to dokładnie ta
wartość (różne stawki per KIDS/ADULTS), dla Crazygames to zawsze "Rewarded"
(jeden placement, patrz generator_wydawcy._kidoz_typ_kampanii - to ten sam
"kubełek"), dla POKI to nazwa placementu wybranego w kroku 5, z prefiksem
"POKI " (patrz KOLUMNA_FORMAT_POKI w generator_wydawcy.py)."""
import json
from pathlib import Path
from typing import NamedTuple

from app.services.lokalizacje import czy_spakowana_appka, katalog_danych_uzytkownika

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
    # W spakowanej appce odswiez_baze_klientow (main.py) zapisuje cennik do
    # folderu danych uzytkownika, a app/data/ w instalce go nie zawiera
    # (plik jest w .gitignore) - czytanie tylko stamtad dawalo pusty cennik i
    # "Brak aktywnej stawki" dla kazdego wydawcy. Tak samo szuka
    # lookup_podmiotu._wczytaj: najpierw folder uzytkownika, potem app/data.
    kandydaci = [DATA_PLIK]
    if czy_spakowana_appka():
        kandydaci.insert(0, katalog_danych_uzytkownika() / DATA_PLIK.name)
    for plik in kandydaci:
        if plik.exists():
            with open(plik, encoding="utf-8") as f:
                return json.load(f)
    return {}


def stawka(wydawca: str, format_reklamowy: str) -> Stawka:
    dane = _wczytaj().get(wydawca, {}).get(format_reklamowy)
    if dane is None:
        raise BladCennika(
            f"Brak aktywnej stawki dla „{wydawca}” / „{format_reklamowy}” w cenniku "
            "(zakładka „Traffic cennik” w Numery_zlecen_2026.xlsx)."
        )
    return Stawka(cena=dane["cena"], waluta=dane["waluta"])
