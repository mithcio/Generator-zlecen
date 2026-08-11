import json

import pytest

from app.services import cennik


@pytest.fixture(autouse=True)
def _dane_testowe(tmp_path, monkeypatch):
    monkeypatch.setattr(cennik, "DATA_PLIK", tmp_path / "cennik_wydawcow.json")
    dane = {
        "KIDOZ": {"Interstitial KIDS": {"cena": 2.5, "waluta": "USD"}},
        "POKI": {"POKI ImViTa": {"cena": 3.0, "waluta": "EUR"}},
    }
    (tmp_path / "cennik_wydawcow.json").write_text(json.dumps(dane), encoding="utf-8")


def test_stawka_zwraca_cene_i_walute():
    wynik = cennik.stawka("KIDOZ", "Interstitial KIDS")
    assert wynik.cena == 2.5
    assert wynik.waluta == "USD"


def test_stawka_nieznany_wydawca_podnosi_blad():
    with pytest.raises(cennik.BladCennika):
        cennik.stawka("Nieznany", "Cokolwiek")


def test_stawka_nieznany_format_podnosi_blad():
    with pytest.raises(cennik.BladCennika):
        cennik.stawka("KIDOZ", "Nieznany format")


def test_stawka_brak_pliku_podnosi_blad(tmp_path, monkeypatch):
    monkeypatch.setattr(cennik, "DATA_PLIK", tmp_path / "nieistniejacy.json")
    with pytest.raises(cennik.BladCennika):
        cennik.stawka("KIDOZ", "Interstitial KIDS")


def test_stawka_sformatowana_eur():
    assert cennik.stawka("POKI", "POKI ImViTa").sformatowana() == "3€"


def test_stawka_sformatowana_liczba_niecalkowita():
    s = cennik.Stawka(cena=2.5, waluta="USD")
    assert s.sformatowana() == "2.5$"
