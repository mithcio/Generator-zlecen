"""Fixtury wspólne dla całego zestawu testów."""
import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEDIAFARM_PLIK = DATA_DIR / "mediafarm.json"

# mediafarm.json zawiera prawdziwe dane firmy (numery kont bankowych,
# telefony pracowników) - jest w .gitignore, więc świeży checkout (CI) go
# nie ma. Testy integracyjne (generator_xlsx, ui_kreator) wołają
# lp.spolka_mediafarm()/kontakt_accounta() i wybuchałyby bez niego -
# fikcyjne dane, tylko żeby kod miał co przeczytać. Jeśli developer ma już
# prawdziwy plik lokalnie (zwykły przypadek), fixture go nie rusza.
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
