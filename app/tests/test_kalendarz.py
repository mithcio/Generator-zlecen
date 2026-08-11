from datetime import date

import flet as ft

from app.ui.kalendarz import widok_kalendarza


def _znajdz_komorki_dni(control) -> dict[str, ft.Container]:
    """Mapuje tekst dnia ('1', '2', ...) na jego Container w siatce."""
    wynik: dict[str, ft.Container] = {}

    def _idz(c):
        if isinstance(c, ft.Container) and isinstance(c.content, ft.Text):
            tekst = c.content.value
            if tekst and tekst.isdigit():
                wynik[tekst] = c
        for dziecko in getattr(c, "controls", []) or []:
            _idz(dziecko)
        content = getattr(c, "content", None)
        if isinstance(content, ft.Control):
            _idz(content)

    _idz(control)
    return wynik


def test_buduje_sie_bez_bledow():
    widok = widok_kalendarza(
        2026, 7, None, None,
        on_wybierz_dzien=lambda d: None, on_zmien_miesiac=lambda delta: None, on_anuluj=lambda: None,
    )
    assert isinstance(widok, ft.Control)


def test_lipiec_2026_ma_31_dni():
    widok = widok_kalendarza(
        2026, 7, None, None,
        on_wybierz_dzien=lambda d: None, on_zmien_miesiac=lambda delta: None, on_anuluj=lambda: None,
    )
    komorki = _znajdz_komorki_dni(widok)
    assert set(komorki.keys()) == {str(n) for n in range(1, 32)}


def test_dni_przed_data_min_sa_zablokowane():
    """Regresja dla pkt 8 z uwag: kalendarz daty końca ma blokować dni
    wcześniejsze niż wybrana data startu."""
    widok = widok_kalendarza(
        2026, 7, None, data_min=date(2026, 7, 15),
        on_wybierz_dzien=lambda d: None, on_zmien_miesiac=lambda delta: None, on_anuluj=lambda: None,
    )
    komorki = _znajdz_komorki_dni(widok)
    assert komorki["14"].on_click is None
    assert komorki["1"].on_click is None
    assert komorki["15"].on_click is not None
    assert komorki["31"].on_click is not None


def test_klik_dnia_od_razu_wybiera_i_nie_wymaga_ok():
    """Regresja dla pkt 7 z uwag: klik dnia sam w sobie wybiera datę —
    kalendarz nie ma osobnego przycisku 'OK'."""
    wybrane = []
    widok = widok_kalendarza(
        2026, 7, None, None,
        on_wybierz_dzien=lambda d: wybrane.append(d), on_zmien_miesiac=lambda delta: None, on_anuluj=lambda: None,
    )
    komorki = _znajdz_komorki_dni(widok)
    komorki["17"].on_click(None)
    assert wybrane == [date(2026, 7, 17)]

    # nie ma przycisku "OK" w ogóle
    def _ma_ok(c):
        if isinstance(c, (ft.TextButton, ft.FilledButton, ft.OutlinedButton)) and c.content == "OK":
            return True
        return any(_ma_ok(d) for d in (getattr(c, "controls", []) or []))

    assert not _ma_ok(widok)


def test_nawigacja_miesiaca_wywoluje_callback():
    wywolania = []
    widok = widok_kalendarza(
        2026, 7, None, None,
        on_wybierz_dzien=lambda d: None, on_zmien_miesiac=lambda delta: wywolania.append(delta), on_anuluj=lambda: None,
    )

    def _znajdz_ikony(c):
        if isinstance(c, ft.IconButton):
            yield c
        for dziecko in getattr(c, "controls", []) or []:
            yield from _znajdz_ikony(dziecko)
        content = getattr(c, "content", None)
        if isinstance(content, ft.Control):
            yield from _znajdz_ikony(content)

    ikony = list(_znajdz_ikony(widok))
    assert len(ikony) == 2
    ikony[0].on_click(None)
    ikony[1].on_click(None)
    assert wywolania == [-1, 1]
