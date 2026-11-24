import json

import pytest

from app.services import cennik


def _zapisz(katalog, dane):
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "cennik_wydawcow.json").write_text(json.dumps(dane), encoding="utf-8")


@pytest.fixture
def katalogi(tmp_path, monkeypatch):
    app_data = tmp_path / "app_data"
    uzytkownik = tmp_path / "uzytkownik"
    monkeypatch.setattr(cennik, "DATA_PLIK", app_data / "cennik_wydawcow.json")
    monkeypatch.setattr(cennik, "katalog_danych_uzytkownika", lambda: uzytkownik)
    return app_data, uzytkownik


def test_spakowana_appka_czyta_cennik_z_folderu_uzytkownika(katalogi, monkeypatch):
    # Regresja: odswiezanie zapisuje do folderu uzytkownika, a app/data w
    # instalce jest puste - cennik dawal "Brak aktywnej stawki" dla kazdego wydawcy.
    _, uzytkownik = katalogi
    _zapisz(uzytkownik, {"PRADO": {"Rewarded": {"cena": 2.0, "waluta": "USD"}}})
    monkeypatch.setattr(cennik, "czy_spakowana_appka", lambda: True)

    assert cennik.stawka("PRADO", "Rewarded").cena == 2.0


def test_spakowana_appka_folder_uzytkownika_ma_pierwszenstwo_przed_app_data(katalogi, monkeypatch):
    app_data, uzytkownik = katalogi
    _zapisz(app_data, {"KIDOZ": {"Rewarded": {"cena": 1.0, "waluta": "USD"}}})
    _zapisz(uzytkownik, {"KIDOZ": {"Rewarded": {"cena": 3.5, "waluta": "USD"}}})
    monkeypatch.setattr(cennik, "czy_spakowana_appka", lambda: True)

    assert cennik.stawka("KIDOZ", "Rewarded").cena == 3.5


def test_wersja_z_kodu_czyta_app_data(katalogi, monkeypatch):
    app_data, uzytkownik = katalogi
    _zapisz(app_data, {"KIDOZ": {"Rewarded": {"cena": 1.0, "waluta": "USD"}}})
    _zapisz(uzytkownik, {"KIDOZ": {"Rewarded": {"cena": 9.9, "waluta": "USD"}}})
    monkeypatch.setattr(cennik, "czy_spakowana_appka", lambda: False)

    assert cennik.stawka("KIDOZ", "Rewarded").cena == 1.0


def test_brak_plikow_daje_blad_cennika(katalogi, monkeypatch):
    monkeypatch.setattr(cennik, "czy_spakowana_appka", lambda: True)
    with pytest.raises(cennik.BladCennika):
        cennik.stawka("PRADO", "Rewarded")
