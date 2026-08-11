"""Testy filtrowania podmiotów po typie (Sp. k. = agencje / Sp. z o.o. =
klienci bezpośredni) i mapowania klient->agencja. Dane testowe - nie realne
app/data/*.json - żeby testy nie zależały od tego, co akanci akurat wpiszą."""
import json

import pytest

from app.services import lookup_podmiotu as lp


@pytest.fixture(autouse=True)
def _dane_testowe(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "DATA_DIR", tmp_path)

    podmioty = {
        "Testowy Account": {
            "Agencja Alfa": {
                "adres_fakturowy": "Adres Alfa", "numery_rejestrowe": "NIP Alfa",
                "termin_platnosci": "30 dni", "domyslny_podmiot": "Sp. k.",
            },
            "Agencja Beta": {
                "adres_fakturowy": "Adres Beta", "numery_rejestrowe": "NIP Beta",
                "termin_platnosci": "30 dni", "domyslny_podmiot": "Sp. k.",
            },
            "Klient Bezposredni SA": {
                "adres_fakturowy": "Adres Bezposredni", "numery_rejestrowe": "NIP Bezposredni",
                "termin_platnosci": "30 dni", "domyslny_podmiot": "Sp. z o.o.",
            },
        }
    }
    klienci_agencyjni = {
        "Testowy Account": {
            "Marka Jeden": "Agencja Alfa",
            "Marka Dwa": "Agencja Alfa",
            "Marka Trzy": "Agencja Beta",
        }
    }
    terminy_platnosci_klientow = {
        "Testowy Account": {
            "Marka Jeden": "60 dni",
        }
    }
    (tmp_path / "podmioty.json").write_text(json.dumps(podmioty, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "klienci_agencyjni.json").write_text(
        json.dumps(klienci_agencyjni, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "terminy_platnosci_klientow.json").write_text(
        json.dumps(terminy_platnosci_klientow, ensure_ascii=False), encoding="utf-8"
    )


def test_podmioty_dla_accounta_i_typu_zwraca_tylko_agencje():
    wynik = lp.podmioty_dla_accounta_i_typu("Testowy Account", "Sp. k.")
    assert set(wynik.keys()) == {"Agencja Alfa", "Agencja Beta"}


def test_podmioty_dla_accounta_i_typu_zwraca_tylko_klientow_bezposrednich():
    wynik = lp.podmioty_dla_accounta_i_typu("Testowy Account", "Sp. z o.o.")
    assert set(wynik.keys()) == {"Klient Bezposredni SA"}


def test_podmioty_dla_accounta_i_typu_pusty_dla_nieznanego_accounta():
    assert lp.podmioty_dla_accounta_i_typu("Nikt Taki", "Sp. k.") == {}


def test_klienci_dla_agencji_zwraca_przypisanych():
    wynik = lp.klienci_dla_agencji("Testowy Account", "Agencja Alfa")
    assert wynik == ["Marka Dwa", "Marka Jeden"]  # posortowane alfabetycznie


def test_klienci_dla_agencji_pusta_lista_dla_agencji_bez_klientow():
    assert lp.klienci_dla_agencji("Testowy Account", "Agencja Beta") == ["Marka Trzy"]
    assert lp.klienci_dla_agencji("Testowy Account", "Agencja Nieznana") == []


def test_formatuj_telefon_same_cyfry():
    assert lp.formatuj_telefon("500099699") == "+48 500 099 699"


def test_formatuj_telefon_juz_ze_spacjami():
    assert lp.formatuj_telefon("530 703 740") == "+48 530 703 740"


def test_formatuj_telefon_puste_daje_pusty_string():
    assert lp.formatuj_telefon(None) == ""
    assert lp.formatuj_telefon("") == ""


def test_formatuj_telefon_nietypowa_dlugosc_zostaje_bez_zmian():
    assert lp.formatuj_telefon("123") == "123"


def test_termin_platnosci_klienta_zwraca_nadpisanie():
    assert lp.termin_platnosci_klienta("Testowy Account", "Marka Jeden") == "60 dni"


def test_termin_platnosci_klienta_brak_nadpisania_daje_none():
    assert lp.termin_platnosci_klienta("Testowy Account", "Marka Dwa") is None
    assert lp.termin_platnosci_klienta("Testowy Account", "Nieznany Klient") is None


def test_znajdz_podmiot_z_klientem_ktory_ma_nadpisany_termin():
    # Marka Jeden jest pod Agencją Alfa (termin agencji: 30 dni), ale ma
    # własne nadpisanie na 60 dni - to drugie ma pierwszeństwo.
    podmiot = lp.znajdz_podmiot("Testowy Account", "Agencja Alfa", "Marka Jeden")
    assert podmiot.termin_platnosci == "60 dni"
    assert podmiot.nazwa == "Agencja Alfa"  # reszta danych (adres, numery...) bez zmian


def test_znajdz_podmiot_bez_nadpisania_zostaje_przy_terminie_domu_mediowego():
    podmiot = lp.znajdz_podmiot("Testowy Account", "Agencja Alfa", "Marka Dwa")
    assert podmiot.termin_platnosci == "30 dni"


def test_znajdz_podmiot_bez_klienta_dziala_jak_dawniej():
    podmiot = lp.znajdz_podmiot("Testowy Account", "Agencja Alfa")
    assert podmiot.termin_platnosci == "30 dni"
