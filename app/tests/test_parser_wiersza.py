import pytest

from app.services.parser_wiersza import (
    BladParsowaniaWiersza,
    parsuj_wiersz,
    parsuj_wiersze,
    rozdziel_pola_wspolne_i_okresy,
    wykryj_ostrzezenia,
)

WIERSZ_LIPIEC = "\t".join(
    [
        "07.2026_Initiative_Colian_Hellena_Lody_Cooltowe_Lipiec_Sierpien_Audio",
        "Initiative Media Warszawa sp. z o.o.",
        "Colian",
        "Paulina Kowalik",
        "KIDS",
        "TAK",
        "In-game audio KIDS",
        "Sp. k.",
        "Dzieci, Młodzież, Dorośli",
        "CPM",
        "26",
        "K/2026/077",
        "5714.29",
        "28.07.2026",
        "31.07.2026",
    ]
)
WIERSZ_SIERPIEN = WIERSZ_LIPIEC.replace("TAK", "NIE").replace(
    "5714.29\t28.07.2026\t31.07.2026", "44285.71\t01.08.2026\t31.08.2026"
)


def test_parsuj_wiersz_podstawowe_pola():
    w = parsuj_wiersz(WIERSZ_LIPIEC)
    assert w["klient"] == "Colian"
    assert w["dom_mediowy"] == "Initiative Media Warszawa sp. z o.o."
    assert w["koszt_jednostkowy"] == 26.0
    assert w["budzet"] == 5714.29
    assert w["data_startu"].isoformat() == "2026-07-28"
    assert w["data_konca"].isoformat() == "2026-07-31"


def test_parsuj_wiersz_usuwa_prefiks_daty_z_nazwy_kampanii():
    w = parsuj_wiersz(WIERSZ_LIPIEC)
    assert w["nazwa_kampanii"] == "Initiative_Colian_Hellena_Lody_Cooltowe_Lipiec_Sierpien_Audio"


def test_parsuj_wiersz_zla_liczba_kolumn():
    with pytest.raises(BladParsowaniaWiersza):
        parsuj_wiersz("a\tb\tc")


def test_parsuj_wiersz_zla_data():
    zly = WIERSZ_LIPIEC.replace("28.07.2026", "niedata")
    with pytest.raises(BladParsowaniaWiersza):
        parsuj_wiersz(zly)


def test_parsuj_wiersz_zla_liczba():
    zly = WIERSZ_LIPIEC.replace("\t26\t", "\tXYZ\t")
    with pytest.raises(BladParsowaniaWiersza):
        parsuj_wiersz(zly)


def test_parsuj_wiersze_pusty_tekst():
    with pytest.raises(BladParsowaniaWiersza):
        parsuj_wiersze("   \n  \n")


def test_rozdziel_bez_konfliktow_daje_dwa_okresy():
    wiersze = parsuj_wiersze(WIERSZ_LIPIEC + "\n" + WIERSZ_SIERPIEN)
    wspolne, okresy, konflikty = rozdziel_pola_wspolne_i_okresy(wiersze)
    assert konflikty == []
    assert wspolne["klient"] == "Colian"
    assert wspolne["nr_zlecenia"] == "K/2026/077"
    assert len(okresy) == 2
    assert round(sum(o.budzet for o in okresy), 2) == 50000.0


def test_rozdziel_wykrywa_konflikt_pola_wspolnego():
    zmieniony = WIERSZ_SIERPIEN.replace("In-game audio KIDS", "Rewarded KIDS")
    wiersze = parsuj_wiersze(WIERSZ_LIPIEC + "\n" + zmieniony)
    wspolne, okresy, konflikty = rozdziel_pola_wspolne_i_okresy(wiersze)
    pola_z_konfliktem = {k.pole for k in konflikty}
    assert "format_reklamowy" in pola_z_konfliktem
    assert wspolne["format_reklamowy"] is None


WIERSZ_Z_PLIKU_KAMPANII = "\t".join(
    [
        "08.2026_Starcom_LEGO_Creator_Sierpien_Wrzesien_Preroll",
        "Starcom Sp. z o.o.",
        "LEGO",
        "Wojciech Morawski",
        "KIDS",
        "TAK",
        "Rewarded KIDS",
        "Sp. k.",
        "Kids 6-12",
        "CPM",
        " 38.00 zł ",
        "K/2026/071",
        " 24,667.00 zł ",
        "17-08-26",
        "31-08-26",
        "649,132",
        "",
        "",
        "0.00%",
        "0.00%",
        "14",
        "-46251",
        "",
        "",
        "0",
        " 13.07 zł ",
    ]
)


def test_parsuj_wiersz_obcina_nadmiarowe_kolumny_z_calego_zaznaczenia():
    """Zaznaczenie i wklejenie całego wiersza z pliku kampanii daje więcej niż
    15 kolumn (wydawca, kwota zlecona, statystyki CTR itp.) - to nie ma być
    błąd, tylko obcięcie nadmiaru."""
    w = parsuj_wiersz(WIERSZ_Z_PLIKU_KAMPANII)
    assert w["klient"] == "LEGO"
    assert w["nr_zlecenia"] == "K/2026/071"
    assert w["data_konca"].isoformat() == "2026-08-31"


def test_parsuj_wiersz_za_malo_kolumn_nadal_jest_bledem():
    with pytest.raises(BladParsowaniaWiersza):
        parsuj_wiersz("a\tb\tc")


def test_parsuj_wiersz_zachowuje_liczbe_zrodlowa_do_porownania():
    w = parsuj_wiersz(WIERSZ_Z_PLIKU_KAMPANII)
    assert w["liczba_zrodlowa"] == 649132.0

    wspolne, okresy, konflikty = rozdziel_pola_wspolne_i_okresy([w])
    assert okresy[0].liczba_zrodlowa == 649132.0


def test_parsuj_wiersz_bez_nadmiarowych_kolumn_ma_liczbe_zrodlowa_none():
    w = parsuj_wiersz(WIERSZ_LIPIEC)
    assert w["liczba_zrodlowa"] is None


@pytest.mark.parametrize(
    ("tekst", "oczekiwana"),
    [
        ("38.00 zł", 38.0),
        (" 38.00 zł ", 38.0),
        ("24,667.00 zł", 24667.0),
        ("24,667.00", 24667.0),
        ("649,132", 649132.0),
        ("1 234,56", 1234.56),
        ("26,5", 26.5),
        ("1234.56", 1234.56),
        ("26", 26.0),
        ("13.07 zł", 13.07),
        ("1,234,567", 1234567.0),
    ],
)
def test_parsuj_liczbe_rozne_formaty_walutowe(tekst, oczekiwana):
    zmieniony = WIERSZ_LIPIEC.replace("\t26\t", f"\t{tekst}\t")
    w = parsuj_wiersz(zmieniony)
    assert w["koszt_jednostkowy"] == oczekiwana


def test_parsuj_date_format_dd_mm_rr():
    zmieniony = WIERSZ_LIPIEC.replace("28.07.2026", "28-07-26")
    w = parsuj_wiersz(zmieniony)
    assert w["data_startu"].isoformat() == "2026-07-28"


def _wiersz_sp_zoo(klient: str, budzet_i_daty: str) -> str:
    """Wiersz klienta bezpośredniego (Sp. z o.o.) z dowolną wartością w
    kolumnie "Klient" - ma być ignorowana, więc może być śmieciowa."""
    return (
        WIERSZ_LIPIEC
        .replace("\tSp. k.\t", "\tSp. z o.o.\t")
        .replace("\tColian\t", f"\t{klient}\t")
        .replace("5714.29\t28.07.2026\t31.07.2026", budzet_i_daty)
    )


def test_konflikt_klienta_ignorowany_dla_klientow_bezposrednich():
    """Kolumna Klient bywa pusta/"-"/"brak" dla klientów bezpośrednich
    (Sp. z o.o.) - różnice między wierszami w tym polu nie mają być
    zgłaszane jako konflikt do rozstrzygnięcia."""
    wiersz1 = _wiersz_sp_zoo("-", "1000\t01.07.2026\t31.07.2026")
    wiersz2 = _wiersz_sp_zoo("brak", "2000\t01.08.2026\t31.08.2026")
    wiersz3 = _wiersz_sp_zoo("", "3000\t01.09.2026\t30.09.2026")
    wiersze = parsuj_wiersze("\n".join([wiersz1, wiersz2, wiersz3]))
    wspolne, okresy, konflikty = rozdziel_pola_wspolne_i_okresy(wiersze)
    pola_z_konfliktem = {k.pole for k in konflikty}
    assert "klient" not in pola_z_konfliktem
    assert wspolne["klient"] is None
    assert len(okresy) == 3


def test_konflikt_klienta_nadal_wykrywany_dla_agencji():
    """Dla Sp. k. (agencja pośredniczy) różnice w polu Klient MAJĄ być
    zgłaszane jako konflikt - to nie jest ignorowane pole."""
    zmieniony = WIERSZ_SIERPIEN.replace("\tColian\t", "\tInny Klient\t")
    wiersze = parsuj_wiersze(WIERSZ_LIPIEC + "\n" + zmieniony)
    _, _, konflikty = rozdziel_pola_wspolne_i_okresy(wiersze)
    pola_z_konfliktem = {k.pole for k in konflikty}
    assert "klient" in pola_z_konfliktem


def test_wykryj_ostrzezenia_brak_gdy_wszystko_spojne():
    """Lipiec (pierwszy miesiąc) TAK - przechodzi na sierpień. Sierpień
    (ostatni miesiąc) NIE - nic po nim się nie ciągnie. To typowy poprawny
    przypadek (domyślne oznaczenia WIERSZ_LIPIEC/WIERSZ_SIERPIEN), bez
    żadnych ostrzeżeń."""
    wiersze = parsuj_wiersze(WIERSZ_LIPIEC + "\n" + WIERSZ_SIERPIEN)
    _, okresy, _ = rozdziel_pola_wspolne_i_okresy(wiersze)
    assert wykryj_ostrzezenia(wiersze, okresy) == []


def test_wykryj_ostrzezenia_wykrywa_nie_przejsciowy_wiersz_w_laczonej_kampanii():
    """Lipiec (nie ostatni miesiąc) oznaczony w źródle jako NIE przejściowy,
    a mimo to łączony z sierpniem - to niespójność warta ostrzeżenia.
    Sierpień zostaje przy domyślnym NIE (poprawne dla ostatniego miesiąca),
    żeby w ostrzeżeniach był tylko ten jeden problem."""
    wiersz_nie = WIERSZ_LIPIEC.replace("\tTAK\t", "\tNIE\t")
    wiersze = parsuj_wiersze(wiersz_nie + "\n" + WIERSZ_SIERPIEN)
    _, okresy, _ = rozdziel_pola_wspolne_i_okresy(wiersze)
    ostrzezenia = wykryj_ostrzezenia(wiersze, okresy)
    assert len(ostrzezenia) == 1
    assert "NIE przejściowy" in ostrzezenia[0]


def test_wykryj_ostrzezenia_wykrywa_ostatni_wiersz_oznaczony_tak():
    """Ostatni (chronologicznie) wiersz oznaczony TAK sugeruje, że powinien
    się dalej przechodzić, a jednak jest ostatnim wklejonym miesiącem -
    warte ostrzeżenia (brakujący kolejny wiersz)."""
    wiersze = parsuj_wiersze(WIERSZ_LIPIEC + "\n" + WIERSZ_SIERPIEN.replace("NIE", "TAK"))
    _, okresy, _ = rozdziel_pola_wspolne_i_okresy(wiersze)
    ostrzezenia = wykryj_ostrzezenia(wiersze, okresy)
    assert len(ostrzezenia) == 1
    assert "Ostatni wiersz" in ostrzezenia[0]


def test_wykryj_ostrzezenia_pojedynczy_wiersz_tak_bez_kontynuacji():
    """Jeden samotnie wklejony wiersz oznaczony TAK sugeruje brakujący
    kolejny miesiąc."""
    wiersze = parsuj_wiersze(WIERSZ_LIPIEC)  # WIERSZ_LIPIEC ma "TAK"
    _, okresy, _ = rozdziel_pola_wspolne_i_okresy(wiersze)
    ostrzezenia = wykryj_ostrzezenia(wiersze, okresy)
    assert len(ostrzezenia) == 1
    assert "tylko jeden miesiąc" in ostrzezenia[0]


def test_wykryj_ostrzezenia_pojedynczy_wiersz_nie_bez_ostrzezenia():
    """Jeden wiersz oznaczony NIE, wklejony samotnie - spójne, brak ostrzeżeń."""
    wiersz_nie = WIERSZ_LIPIEC.replace("\tTAK\t", "\tNIE\t")
    wiersze = parsuj_wiersze(wiersz_nie)
    _, okresy, _ = rozdziel_pola_wspolne_i_okresy(wiersze)
    assert wykryj_ostrzezenia(wiersze, okresy) == []


def test_wykryj_ostrzezenia_wykrywa_przerwe_miedzy_okresami():
    wiersz_1 = WIERSZ_LIPIEC.replace("5714.29\t28.07.2026\t31.07.2026", "1000\t01.09.2026\t11.09.2026")
    wiersz_2 = WIERSZ_LIPIEC.replace("5714.29\t28.07.2026\t31.07.2026", "1000\t17.09.2026\t13.10.2026")
    wiersze = parsuj_wiersze(wiersz_1 + "\n" + wiersz_2)
    _, okresy, _ = rozdziel_pola_wspolne_i_okresy(wiersze)
    ostrzezenia = wykryj_ostrzezenia(wiersze, okresy)
    assert any("Przerwa" in o for o in ostrzezenia)


def test_wykryj_ostrzezenia_brak_dla_ciaglych_okresow():
    """Lipiec kończy się 31.07, sierpień zaczyna 01.08 - to ciągłość, nie przerwa."""
    wiersze = parsuj_wiersze(WIERSZ_LIPIEC + "\n" + WIERSZ_SIERPIEN.replace("NIE", "TAK"))
    _, okresy, _ = rozdziel_pola_wspolne_i_okresy(wiersze)
    ostrzezenia = wykryj_ostrzezenia(wiersze, okresy)
    assert not any("Przerwa" in o for o in ostrzezenia)
