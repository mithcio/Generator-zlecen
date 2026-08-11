"""Wspólne reguły nazewnictwa plików eksportu (folder docelowy, oczyszczanie
znaków niedozwolonych w nazwie) — używane przez krok 4 (Zlecenie) i krok 5
(Dane Traffic + plik wydawcy zewnętrznego), żeby wszystkie trafiały do tego
samego folderu, niezależnie od tego, w którym kroku wygenerowano dany
plik."""
import re
from pathlib import Path

from app.services import ustawienia

FOLDER_EKSPORTU_DOMYSLNY = Path.home() / "Zlecenia_Mediafarm"

_NIEDOZWOLONE = re.compile(r'[\\/:*?"<>|]')


def oczysc_nazwe(s: str) -> str:
    s = _NIEDOZWOLONE.sub("-", s.strip())
    s = re.sub(r"\s+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")


def folder_bazowy() -> Path:
    """Folder nadrzędny zapisu zleceń — z Ustawień, jeśli użytkownik go tam
    wskazał, w przeciwnym razie domyślny katalog w profilu użytkownika."""
    sciezka = ustawienia.wczytaj().get("folder_eksportu")
    return Path(sciezka) if sciezka else FOLDER_EKSPORTU_DOMYSLNY


def folder_zlecenia(nr_zlecenia: str) -> Path:
    # Folder = sam numer zlecenia (krótko) — nazwy kampanii bywają bardzo
    # długie, a doklejone do nazwy folderu potrafią przekroczyć limit
    # długości ścieżki w niektórych programach.
    return folder_bazowy() / oczysc_nazwe(nr_zlecenia)


def nazwa_pliku_zlecenie(nr_zlecenia: str, nazwa_kampanii: str) -> str:
    return oczysc_nazwe(f"Zlecenie_{nr_zlecenia}_{nazwa_kampanii}")


def nazwa_pliku_dane_traffic(klient: str, brand: str, nr_zlecenia: str) -> str:
    return oczysc_nazwe(f"DANE_{klient}_{brand}_{nr_zlecenia}")


# Nazwy plików dla wydawców zewnętrznych (KIDOZ/Adverty/Odeeo/Crazygames/
# POKI) - różnią się wzorcem per wydawca, patrz app/services/generator_wydawcy.py
# (_nazwa_pliku_purchase / _nazwa_pliku_crazygames / _nazwa_pliku_poki).
