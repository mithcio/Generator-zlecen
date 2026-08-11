"""Fixtury wspólne dla całego zestawu testów."""
import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEDIAFARM_PLIK = DATA_DIR / "mediafarm.json"
PODMIOTY_PLIK = DATA_DIR / "podmioty.json"

# mediafarm.json/podmioty.json zawierają prawdziwe dane firmy i klientów
# (numery kont bankowych, NIP/KRS, telefony pracowników) - są w .gitignore,
# więc świeży checkout (CI) ich nie ma. Testy integracyjne (generator_xlsx,
# ui_kreator) wołają lp.spolka_mediafarm()/kontakt_accounta()/znajdz_podmiot()
# i część wybuchałaby bez nich - fikcyjne dane, tylko żeby kod miał co
# przeczytać (dokładnie account_manager/dom_mediowy/podmiot_realizujacy z
# PELNY_STAN w test_generator_xlsx.py i test_ui_kreator.py). Jeśli developer
# ma już prawdziwe pliki lokalnie (zwykły przypadek), fixture ich nie rusza.
FIKCYJNE_PODMIOTY = {
    "Igor Samul": {
        "Initiative Media Warszawa sp. z o.o.": {
            "adres_fakturowy": "ul. Testowa 2, 00-000 Warszawa",
            "numery_rejestrowe": "KRS: 0000000002 NIP: 000-000-00-02; REGON: 000000002;",
            "termin_platnosci": "30 dni",
            "domyslny_podmiot": "Sp. k.",
        }
    }
}

FIKCYJNE_DANE = {
    "spolki": {
        "Sp. k.": {
            "nazwa": "Testowa sp. k.",
            "numery_rejestrowe": "KRS: 0000000000 NIP: 000-000-00-00; REGON: 000000000;",
            "konto_bankowe": "Testbank 00 0000 0000 0000 0000 0000 0000",
        },
        "Sp. z o.o.": {
            "nazwa": "Testowa sp. z o.o.",
            "numery_rejestrowe": "KRS: 0000000001 NIP: 000-000-00-01; REGON: 000000001;",
            "konto_bankowe": "Testbank 00 0000 0000 0000 0000 0000 0001",
        },
        "adres": "ul. Testowa 1, 00-000 Warszawa",
    },
    "accounts": {
        "Igor Samul": {"email": "test@example.com", "telefon": "500000000"},
        "Marta Urbańska": {"email": "test2@example.com", "telefon": "500000001"},
        "Agnieszka Kraińska": {"email": "test3@example.com", "telefon": "500000002"},
    },
}


@pytest.fixture(scope="session", autouse=True)
def zapewnij_mediafarm_json():
    if MEDIAFARM_PLIK.exists():
        yield
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIAFARM_PLIK.write_text(
        json.dumps(FIKCYJNE_DANE, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        yield
    finally:
        MEDIAFARM_PLIK.unlink(missing_ok=True)


@pytest.fixture(scope="session", autouse=True)
def zapewnij_podmioty_json():
    if PODMIOTY_PLIK.exists():
        yield
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PODMIOTY_PLIK.write_text(
        json.dumps(FIKCYJNE_PODMIOTY, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    try:
        yield
    finally:
        PODMIOTY_PLIK.unlink(missing_ok=True)
