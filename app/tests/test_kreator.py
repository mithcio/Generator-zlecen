import types

import flet as ft

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
