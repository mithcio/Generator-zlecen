import openpyxl
import pytest

from app.services import eksport_nazwy, numeracja, ustawienia, wystawianie


@pytest.fixture(autouse=True)
def _izolacja(tmp_path, monkeypatch):
    monkeypatch.setattr(ustawienia, "DATA_PLIK", tmp_path / "ustawienia.json")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Numery zleceń"
    ws.append(["SP. K.", "status", "data", "użytkownik", None, "SP. Z O.O.", "status", "data", "użytkownik"])
    for i in range(1, 6):
        ws.append([f"K/2026/{i:03d}", None, None, None, None, f"S/2026/{i:03d}", None, None, None])
    plik = tmp_path / "Numery_zlecen_2026.xlsx"
    wb.save(plik)
    ustawienia.zapisz(
        sciezka_numery_zlecen=str(plik),
        folder_eksportu=str(tmp_path / "zlecenia"),
        domyslny_account_manager="Igor Samul",
    )
    return plik


def _dane(**nadpisania):
    dane = {
        "podmiot_realizujacy": "Sp. k.",
        "nazwa_kampanii": "Initiative_Colian_Hellena_Lody",
        "dom_mediowy": "Initiative Media Warszawa sp. z o.o.",
        "klient": "Colian",
        "brand": "Hellena",
        "zlecajacy": "Paulina Kowalik",
        "target": "KIDS",
        "format_reklamowy": "In-game audio KIDS",
        "model_sprzedazy": "CPM",
        "koszt_jednostkowy": 26,
        "capping": 3,
        "uwagi": "Linia 1\nLinia 2",
        "okresy": [{"start": "2026-11-02", "koniec": "2026-11-30", "budzet": 5200}],
    }
    dane.update(nadpisania)
    return dane


def test_podglad_nic_nie_rezerwuje(tmp_path):
    wynik = wystawianie.podglad(_dane())
    assert wynik["ok"] is True
    assert wynik["podsumowanie"]["budzet_total"] == 5200
    assert wynik["podsumowanie"]["liczba_total"] == 200000  # 5200 / 26 * 1000
    assert wynik["podsumowanie"]["account_manager"] == "Igor Samul"  # domyślny z Ustawień
    # numer nadal wolny
    assert numeracja.zarezerwuj_numer("Sp. k.") == "K/2026/001"


def test_podglad_zbiera_bledy_zamiast_wybuchac():
    wynik = wystawianie.podglad(_dane(target="DOROSLI", okresy=[{"start": "2026-11-02", "koniec": "zly", "budzet": 1}]))
    assert wynik["ok"] is False
    tekst = " ".join(wynik["bledy"])
    assert "target" in tekst and "Niepoprawna data" in tekst


def test_okres_na_wiele_miesiecy_dzieli_sie_automatycznie():
    wynik = wystawianie.podglad(_dane(okresy=[{"start": "2026-11-02", "koniec": "2026-12-31", "budzet": 10000}]))
    assert wynik["ok"] is True
    assert len(wynik["podsumowanie"]["okresy"]) == 2


def test_wystaw_nadaje_numer_i_generuje_pliki(tmp_path):
    wynik = wystawianie.wystaw(_dane(uwagi_traffic="Linia A\nLinia B"))
    assert wynik["ok"] is True, wynik
    assert wynik["nr_zlecenia"] == "K/2026/001"
    assert wynik["numer_nadany_automatycznie"] is True
    rozszerzenia = sorted(p.rsplit(".", 1)[-1] for p in wynik["pliki"])
    assert rozszerzenia == ["pdf", "xlsx", "xlsx"]  # Zlecenie xlsx+pdf, Dane Traffic
    assert all(p.startswith(str(eksport_nazwy.folder_zlecenia("K/2026/001"))) for p in wynik["pliki"])
    assert len(wynik["wiersze_do_pliku_kampanii"]) == 1
    # numer faktycznie zajęty w pliku
    assert numeracja.zarezerwuj_numer("Sp. k.") == "K/2026/002"


def test_wystaw_z_bledami_nie_zajmuje_numeru():
    wynik = wystawianie.wystaw(_dane(klient=""))
    assert wynik["ok"] is False
    assert numeracja.zarezerwuj_numer("Sp. k.") == "K/2026/001"


def test_wystaw_zwalnia_numer_gdy_generowanie_sie_nie_uda(monkeypatch):
    def pada(*a, **k):
        raise OSError("dysk pelny")

    monkeypatch.setattr(wystawianie, "generuj_xlsx", pada)
    wynik = wystawianie.wystaw(_dane())
    assert wynik["ok"] is False and wynik["numer_zwolniony"] is True
    assert numeracja.zarezerwuj_numer("Sp. k.") == "K/2026/001"


def test_wystaw_z_podanym_numerem_nie_rezerwuje():
    wynik = wystawianie.wystaw(_dane(nr_zlecenia="K/2026/077", dane_traffic=False))
    assert wynik["ok"] is True and wynik["numer_nadany_automatycznie"] is False
    assert len(wynik["pliki"]) == 2
    assert numeracja.zarezerwuj_numer("Sp. k.") == "K/2026/001"


def test_slowniki_i_szukanie_podmiotu():
    wynik = wystawianie.slowniki_i_podmioty("initiative")
    assert "Igor Samul" in wynik["accounty"]
    assert "Rewarded KIDS" in wynik["formaty_reklamowe"]
    assert any("Initiative" in t["dom_mediowy_lub_klient_bezposredni"] for t in wynik["trafienia"])
