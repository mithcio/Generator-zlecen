"""Wspólne budowniczowie kontrolek Flet używane w kilku krokach kreatora."""
from typing import Callable

import flet as ft

# Podpowiedź (hint_text) ma być wyraźnie odróżnialna od realnie wpisanej
# wartości — jaśniejsza i pochylona, żeby od razu było widać, że pole jest
# jeszcze puste, a nie że coś już w nim wpisano.
STYL_PODPOWIEDZI = ft.TextStyle(color=ft.Colors.GREY_400, italic=True, size=12)


def pole_kombo(label: str, opcje: list[str], wartosc: str, on_zmiana: Callable[[str], None]) -> ft.Dropdown:
    """Pole "lista rozwijana albo wpisanie ręczne" — edytowalny dropdown:
    można wybrać z listy albo wpisać własną wartość."""

    def _on_select(e: ft.Event) -> None:
        on_zmiana(e.control.value or "")

    def _on_text_change(e: ft.Event) -> None:
        on_zmiana(e.control.text or "")

    return ft.Dropdown(
        label=label,
        value=wartosc if wartosc in opcje else None,
        text=wartosc,
        editable=True,
        enable_filter=True,
        options=[ft.DropdownOption(key=o, text=o) for o in opcje],
        on_select=_on_select,
        on_text_change=_on_text_change,
        hint_text="wybierz z listy albo wpisz",
        hint_style=STYL_PODPOWIEDZI,
        expand=True,
    )


def pole_dropdown_zamkniety(
    label: str, opcje: list[str], wartosc: str, on_zmiana: Callable[[str], None]
) -> ft.Dropdown:
    """Zwykła (nieedytowalna) lista rozwijana — dla pól o z góry ustalonym,
    zamkniętym zakresie wartości (np. Capping), gdzie dowolny wpisany ręcznie
    tekst nie miałby sensu."""

    def _on_select(e: ft.Event) -> None:
        on_zmiana(e.control.value or "")

    return ft.Dropdown(
        label=label,
        value=wartosc if wartosc in opcje else None,
        options=[ft.DropdownOption(key=o, text=o) for o in opcje],
        on_select=_on_select,
        expand=True,
    )


def pole_tekstowe(
    label: str,
    wartosc: str,
    on_zmiana: Callable[[str], None],
    wieloliniowe: bool = False,
    podpowiedz: str | None = None,
) -> ft.TextField:
    def _on_change(e: ft.Event) -> None:
        on_zmiana(e.control.value or "")

    return ft.TextField(
        label=label,
        value=wartosc,
        on_change=_on_change,
        multiline=wieloliniowe,
        min_lines=3 if wieloliniowe else 1,
        hint_text=podpowiedz,
        hint_style=STYL_PODPOWIEDZI,
        expand=True,
    )


def pole_z_etykieta_na_ramce(etykieta: str, kontrolka: ft.Control, width: int | None = None) -> ft.Control:
    """Podpisuje `kontrolka` etykietą wciętą w górną krawędź obwódki - jak
    wbudowany label= Dropdown-a, zawsze widoczną niezależnie od tego, czy
    pole jest puste. Flet nie ma floating_label_behavior="always": pusty,
    nieostrzony TextField z label= renderuje etykietę na środku pola pełną
    czcionką, wyglądając jak już wpisana wartość (stąd gdzie indziej w
    kodzie osobny Text NAD polem) - to ręcznie odtwarza wygląd Dropdown-a
    zamiast wbudowanego label=, żeby oba typy pól wyglądały tak samo."""
    return ft.Stack(
        [
            kontrolka,
            ft.Container(
                content=ft.Text(etykieta, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                bgcolor=ft.Colors.SURFACE,
                padding=ft.Padding.symmetric(horizontal=4),
                left=8,
                top=-8,
            ),
        ],
        # Stack domyślnie przycina dzieci do własnych granic (clip_behavior
        # HARD_EDGE) - etykieta z top=-8 (celowo nad górną krawędzią pola)
        # byłaby ucięta w połowie bez wyłączenia przycinania.
        clip_behavior=ft.ClipBehavior.NONE,
        width=width,
    )


def naglowek_kroku(numer: int, z: int, tytul: str) -> ft.Text:
    return ft.Text(f"Krok {numer} z {z} — {tytul}", size=18, weight=ft.FontWeight.BOLD)


def lista_bledow(bledy: list[str]) -> ft.Control:
    if not bledy:
        return ft.Container()
    return ft.Container(
        content=ft.Column(
            [ft.Text("Popraw, zanim przejdziesz dalej:", weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700)]
            + [ft.Text(f"• {b}", color=ft.Colors.RED_700) for b in bledy]
        ),
        bgcolor=ft.Colors.RED_50,
        border_radius=8,
        padding=12,
    )
