from pathlib import Path

import pytest

from app.services import eksport_nazwy, ustawienia


@pytest.fixture(autouse=True)
def _izolacja(tmp_path, monkeypatch):
    monkeypatch.setattr(ustawienia, "DATA_PLIK", tmp_path / "ustawienia.json")


def test_folder_bazowy_bez_ustawien_uzywa_domyslnego():
    assert eksport_nazwy.folder_bazowy() == eksport_nazwy.FOLDER_EKSPORTU_DOMYSLNY


def test_folder_bazowy_respektuje_ustawienia(tmp_path):
    ustawienia.zapisz(folder_eksportu=str(tmp_path))
    assert eksport_nazwy.folder_bazowy() == tmp_path


def test_folder_zlecenia_dokleja_numer_pod_folderem_bazowym(tmp_path):
    ustawienia.zapisz(folder_eksportu=str(tmp_path))
    assert eksport_nazwy.folder_zlecenia("K/2026/078") == tmp_path / "K-2026-078"


def test_nazwa_pliku_zlecenie_uzywa_numeru_i_nazwy_kampanii():
    nazwa = eksport_nazwy.nazwa_pliku_zlecenie("K/2026/078", "LEGO City Sierpień")
    assert nazwa == "Zlecenie_K-2026-078_LEGO_City_Sierpień"
