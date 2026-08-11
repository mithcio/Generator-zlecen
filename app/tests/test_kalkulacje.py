from datetime import date

import pytest

from app.services.kalkulacje import auto_podziel_budzet, etykieta_liczby, liczba_dla_okresu


def test_etykieta_liczby_zalezna_od_modelu():
    assert etykieta_liczby("CPM") == "Liczba wyświetleń"
    assert etykieta_liczby("CPC") == "Liczba klików"
    assert etykieta_liczby("CPV") == "Liczba pełnych odtworzeń"
    assert etykieta_liczby("Liczba wyświetleń") == "Liczba wyświetleń"
    assert etykieta_liczby("") == "Liczba"


def test_liczba_cpm():
    assert liczba_dla_okresu("CPM", 26, 5714.29) == pytest.approx(219780.3846, rel=1e-4)


def test_liczba_cpc():
    assert liczba_dla_okresu("CPC", 2, 100) == pytest.approx(50)


def test_liczba_ff():
    assert liczba_dla_okresu("FF", 999, 12345) == 1.0


def test_liczba_fallback_dla_innych_modeli():
    assert liczba_dla_okresu("CPV", 5, 100) == pytest.approx(20)


def test_liczba_zero_kosztu_nie_wybucha():
    assert liczba_dla_okresu("CPM", 0, 100) == 0.0


def test_auto_podzial_budzetu_zgodny_z_oryginalnym_przykladem():
    """Colian Hellena Lipiec/Sierpień: 50000 PLN na 28.07-31.08.2026 ->
    5714.29 (lipiec, 4 dni) / 44285.71 (sierpień, 31 dni) w oryginalnym pliku."""
    okresy = auto_podziel_budzet(50000.0, date(2026, 7, 28), date(2026, 8, 31))
    assert len(okresy) == 2
    assert okresy[0].data_startu == date(2026, 7, 28)
    assert okresy[0].data_konca == date(2026, 7, 31)
    assert okresy[0].budzet == 5714.29
    assert okresy[1].data_startu == date(2026, 8, 1)
    assert okresy[1].data_konca == date(2026, 8, 31)
    assert okresy[1].budzet == 44285.71


def test_auto_podzial_suma_zawsze_rowna_calosci():
    for start, koniec, budzet in [
        (date(2026, 1, 5), date(2026, 4, 17), 123456.78),
        (date(2026, 3, 1), date(2026, 3, 31), 1000.0),
        (date(2025, 12, 20), date(2026, 2, 3), 9999.99),
    ]:
        okresy = auto_podziel_budzet(budzet, start, koniec)
        assert round(sum(o.budzet for o in okresy), 2) == round(budzet, 2)
        assert okresy[0].data_startu == start
        assert okresy[-1].data_konca == koniec


def test_auto_podzial_jeden_miesiac_daje_jeden_okres():
    okresy = auto_podziel_budzet(1000.0, date(2026, 3, 1), date(2026, 3, 31))
    assert len(okresy) == 1
    assert okresy[0].budzet == 1000.0


def test_auto_podzial_konczy_sie_przed_startem_rzuca_blad():
    with pytest.raises(ValueError):
        auto_podziel_budzet(1000.0, date(2026, 3, 31), date(2026, 3, 1))
