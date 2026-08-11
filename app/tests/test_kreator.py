import asyncio
import types

import flet as ft

from app.services import numeracja
from app.ui.kreator import Kreator
from app.ui.stan import StanKreatora


class _FakeSelf:
    """Minimalny obiekt z .stan i .odswiez(), żeby wywołać metody Kreator
    bez żywego ft.Page (page.clean()/page.add() wymagają realnej sesji)."""

    def __init__(self, stan):
        self.stan = stan
        self.page = None
        self.liczba_odswiezen = 0
        self.idz_do_kroku = types.MethodType(Kreator.idz_do_kroku, self)

    def odswiez(self):
        self.liczba_odswiezen += 1


def _znajdz_kontenery(control):
    if isinstance(control, ft.Row):
        return control.controls
    return []


def test_pasek_postepu_ma_piec_klikalnych_krokow():
    fejk = _FakeSelf(StanKreatora(krok=2))
    pasek = Kreator._pasek_postepu(fejk)
    kontenery = _znajdz_kontenery(pasek)
    assert len(kontenery) == 5
    assert all(isinstance(k, ft.Container) and k.on_click is not None for k in kontenery)


def test_klik_kroku_w_pasku_przenosi_bezposrednio():
    """Regresja dla uwagi: menu na górze ma być klikalne, bez konieczności
    przechodzenia 'wstecz'/'dalej' krok po kroku."""
    fejk = _FakeSelf(StanKreatora(krok=5))
    pasek = Kreator._pasek_postepu(fejk)
    kontenery = _znajdz_kontenery(pasek)

    pierwszy_krok = kontenery[0]
    pierwszy_krok.on_click(None)

    assert fejk.stan.krok == 1
    assert fejk.liczba_odswiezen == 1


def test_idz_do_kroku_ustawia_stan_i_odswieza():
    fejk = _FakeSelf(StanKreatora(krok=1))
    Kreator.idz_do_kroku(fejk, 4)
    assert fejk.stan.krok == 4
    assert fejk.liczba_odswiezen == 1


class _FakeWindow:
    def __init__(self):
        self.destroyed = False

    async def destroy(self):
        self.destroyed = True


class _FakePage:
    def __init__(self):
        self.window = _FakeWindow()
        self.dialog_shown = None

    def show_dialog(self, dlg):
        self.dialog_shown = dlg

    def pop_dialog(self):
        self.dialog_shown = None


class _FakeSelfOkno:
    def __init__(self, stan):
        self.stan = stan
        self.page = _FakePage()


def test_zamkniecie_bez_aktywnej_rezerwacji_zamyka_od_razu():
    fejk = _FakeSelfOkno(StanKreatora(numer_automatyczny_aktywny=False))
    event = types.SimpleNamespace(type=ft.WindowEventType.CLOSE)

    asyncio.run(Kreator.obsluz_zamkniecie_okna(fejk, event))

    assert fejk.page.window.destroyed is True
    assert fejk.page.dialog_shown is None


def test_zamkniecie_z_aktywna_rezerwacja_pokazuje_dialog_zamiast_zamykac():
    stan = StanKreatora(
        numer_automatyczny_aktywny=True,
        nr_zlecenia_automatyczny="K/2026/999",
        podmiot_realizujacy="Sp. k.",
    )
    fejk = _FakeSelfOkno(stan)
    event = types.SimpleNamespace(type=ft.WindowEventType.CLOSE)

    asyncio.run(Kreator.obsluz_zamkniecie_okna(fejk, event))

    assert fejk.page.window.destroyed is False
    assert fejk.page.dialog_shown is not None
    assert "K/2026/999" in fejk.page.dialog_shown.content.value


def test_zamkniecie_ignoruje_zdarzenia_inne_niz_close():
    stan = StanKreatora(numer_automatyczny_aktywny=True, nr_zlecenia_automatyczny="K/2026/999")
    fejk = _FakeSelfOkno(stan)
    event = types.SimpleNamespace(type=ft.WindowEventType.FOCUS)

    asyncio.run(Kreator.obsluz_zamkniecie_okna(fejk, event))

    assert fejk.page.window.destroyed is False
    assert fejk.page.dialog_shown is None


def test_zwolnij_i_zamknij_zwalnia_numer_i_zamyka(monkeypatch):
    wywolania = []
    monkeypatch.setattr(
        numeracja, "zwolnij_numer", lambda numer, podmiot: wywolania.append((numer, podmiot))
    )
    stan = StanKreatora(
        numer_automatyczny_aktywny=True,
        nr_zlecenia_automatyczny="K/2026/999",
        podmiot_realizujacy="Sp. k.",
    )
    fejk = _FakeSelfOkno(stan)
    event = types.SimpleNamespace(type=ft.WindowEventType.CLOSE)
    asyncio.run(Kreator.obsluz_zamkniecie_okna(fejk, event))

    przycisk_zwolnij = fejk.page.dialog_shown.actions[-1]
    asyncio.run(przycisk_zwolnij.on_click(None))

    assert wywolania == [("K/2026/999", "Sp. k.")]
    assert fejk.page.window.destroyed is True


def test_zostaw_zarezerwowany_zamyka_bez_zwalniania(monkeypatch):
    wywolania = []
    monkeypatch.setattr(
        numeracja, "zwolnij_numer", lambda numer, podmiot: wywolania.append((numer, podmiot))
    )
    stan = StanKreatora(
        numer_automatyczny_aktywny=True,
        nr_zlecenia_automatyczny="K/2026/999",
        podmiot_realizujacy="Sp. k.",
    )
    fejk = _FakeSelfOkno(stan)
    event = types.SimpleNamespace(type=ft.WindowEventType.CLOSE)
    asyncio.run(Kreator.obsluz_zamkniecie_okna(fejk, event))

    przycisk_zostaw = fejk.page.dialog_shown.actions[1]
    asyncio.run(przycisk_zostaw.on_click(None))

    assert wywolania == []
    assert fejk.page.window.destroyed is True
