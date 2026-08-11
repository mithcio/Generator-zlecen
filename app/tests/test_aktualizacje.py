import json
import urllib.error
from io import BytesIO

import pytest

from app.services import aktualizacje as akt


@pytest.mark.parametrize(
    "wersja, oczekiwana",
    [
        ("1.0.0", (1, 0, 0)),
        ("v1.2.3", (1, 2, 3)),
        ("V2.0", (2, 0)),
        ("1.0.0-beta", (1, 0, 0)),
    ],
)
def test_do_krotki(wersja, oczekiwana):
    assert akt._do_krotki(wersja) == oczekiwana


def test_sprawdz_nowsza_wersja_dostepna(monkeypatch):
    payload = {
        "tag_name": "v1.1.0",
        "html_url": "https://github.com/mithcio/Generator-zlecen/releases/tag/v1.1.0",
        "assets": [{"name": "GeneratorZlecen.exe", "browser_download_url": "https://example.com/GeneratorZlecen.exe"}],
    }

    def fake_urlopen(req, timeout=10):
        return BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(akt.urllib.request, "urlopen", fake_urlopen)

    wynik = akt.sprawdz()
    assert wynik.dostepna_nowsza is True
    assert wynik.wersja_najnowsza == "v1.1.0"
    assert wynik.url_do_otwarcia == "https://example.com/GeneratorZlecen.exe"


def test_sprawdz_brak_nowszej_wersji(monkeypatch):
    payload = {"tag_name": f"v{akt.WERSJA_APP}", "html_url": "https://example.com", "assets": []}

    def fake_urlopen(req, timeout=10):
        return BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(akt.urllib.request, "urlopen", fake_urlopen)

    wynik = akt.sprawdz()
    assert wynik.dostepna_nowsza is False
    assert wynik.blad is None


def test_sprawdz_brak_wydan(monkeypatch):
    def fake_urlopen(req, timeout=10):
        raise urllib.error.HTTPError(akt.API_URL, 404, "Not Found", None, None)

    monkeypatch.setattr(akt.urllib.request, "urlopen", fake_urlopen)

    wynik = akt.sprawdz()
    assert wynik.dostepna_nowsza is False
    assert wynik.blad is not None


def test_sprawdz_brak_polaczenia(monkeypatch):
    def fake_urlopen(req, timeout=10):
        raise urllib.error.URLError("brak sieci")

    monkeypatch.setattr(akt.urllib.request, "urlopen", fake_urlopen)

    wynik = akt.sprawdz()
    assert wynik.dostepna_nowsza is False
    assert "połączenia" in wynik.blad
