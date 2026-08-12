"""Ustawienia aplikacji trwałe między sesjami (panel Ustawienia, ikona koła
zębatego w prawym górnym rogu): ścieżka do pliku Numery_zlecen_2026.xlsx,
domyślny account manager, folder zapisu wygenerowanych zleceń.

W przeciwieństwie do app/data/*.json (dane wsadowe generowane
scripts/export_seed_data.py) ten plik jest jedynym, który edytuje
bezpośrednio użytkownik przez UI — stąd nie ma go w .gitignore razem z
resztą wrażliwych danych, ale i tak nie trafia do repo (ścieżki są
specyficzne dla maszyny)."""
import json
import sys
from pathlib import Path

from app.services.lokalizacje import katalog_danych_uzytkownika


def _katalog_ustawien() -> Path:
    """W spakowanej appce (PyInstaller) app/data/ żyje w tymczasowym folderze
    rozpakowywanym na nowo przy każdym starcie — zapis tam zniknąłby przy
    następnym uruchomieniu. Ustawienia (ścieżka do Numery_zlecen_2026.xlsx
    i inne) muszą przetrwać między sesjami, więc w wersji spakowanej trafiają
    do trwałego folderu danych użytkownika (patrz lokalizacje.py); w wersji
    uruchamianej z kodu źródłowego zostają jak dotąd w app/data/, żeby nie
    zaskakiwać podczas developmentu."""
    if getattr(sys, "frozen", False):
        return katalog_danych_uzytkownika()
    return Path(__file__).resolve().parent.parent / "data"


DATA_PLIK = _katalog_ustawien() / "ustawienia.json"

DOMYSLNE = {
    "sciezka_numery_zlecen": None,
    "domyslny_account_manager": None,
    "folder_eksportu": None,
}


def wczytaj() -> dict:
    if not DATA_PLIK.exists():
        return dict(DOMYSLNE)
    with open(DATA_PLIK, encoding="utf-8") as f:
        zapisane = json.load(f)
    return {**DOMYSLNE, **zapisane}


def zapisz(**zmiany) -> dict:
    stan = wczytaj()
    stan.update(zmiany)
    DATA_PLIK.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PLIK, "w", encoding="utf-8") as f:
        json.dump(stan, f, ensure_ascii=False, indent=2)
    return stan
