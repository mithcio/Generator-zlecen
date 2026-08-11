"""Własna siatka kalendarza (zamiast natywnego ft.DatePicker), żeby:
- kliknięcie dnia od razu wybierało datę, bez osobnego przycisku "OK";
- dla daty końca dało się z góry zablokować/wyszarzyć dni wcześniejsze niż
  wybrana data startu (i domyślnie otworzyć na tym samym miesiącu).
"""
import calendar
from datetime import date

import flet as ft

from app.services.kalkulacje import MIESIACE_PL

DNI_PL = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Nd"]


def widok_kalendarza(
    rok: int,
    miesiac: int,
    data_wybrana: date | None,
    data_min: date | None,
    on_wybierz_dzien,
    on_zmien_miesiac,
    on_anuluj,
) -> ft.Control:
    naglowek = ft.Row(
        [
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=lambda e: on_zmien_miesiac(-1)),
            ft.Text(f"{MIESIACE_PL[miesiac - 1]} {rok}", weight=ft.FontWeight.BOLD, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=lambda e: on_zmien_miesiac(1)),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    naglowki_dni = ft.Row(
        [ft.Container(ft.Text(d, size=11, color=ft.Colors.GREY_600), width=36, alignment=ft.Alignment.CENTER) for d in DNI_PL],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0,
    )

    pierwszy_dzien_tydzien, dni_w_miesiacu = calendar.monthrange(rok, miesiac)

    wiersze = []
    komorki = [None] * pierwszy_dzien_tydzien
    for dzien in range(1, dni_w_miesiacu + 1):
        ta_data = date(rok, miesiac, dzien)
        zablokowany = data_min is not None and ta_data < data_min
        wybrany = data_wybrana == ta_data

        if zablokowany:
            komorka = ft.Container(
                ft.Text(str(dzien), size=13, color=ft.Colors.GREY_300),
                width=36, height=36, alignment=ft.Alignment.CENTER,
            )
        else:
            komorka = ft.Container(
                ft.Text(
                    str(dzien), size=13,
                    color=ft.Colors.WHITE if wybrany else None,
                    weight=ft.FontWeight.BOLD if wybrany else None,
                ),
                width=36, height=36, alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.BLUE_700 if wybrany else None,
                border_radius=18,
                on_click=(lambda e, d=ta_data: on_wybierz_dzien(d)),
                ink=True,
            )
        komorki.append(komorka)

    while len(komorki) % 7 != 0:
        komorki.append(None)

    for i in range(0, len(komorki), 7):
        tydzien = komorki[i : i + 7]
        wiersze.append(
            ft.Row(
                [k if k is not None else ft.Container(width=36, height=36) for k in tydzien],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=0,
            )
        )

    return ft.Container(
        content=ft.Column(
            [naglowek, naglowki_dni, *wiersze, ft.Row([ft.TextButton("Anuluj", on_click=lambda e: on_anuluj())], alignment=ft.MainAxisAlignment.END)],
            spacing=4,
            tight=True,
        ),
        bgcolor=ft.Colors.WHITE,
        border=ft.Border.all(1, ft.Colors.GREY_300),
        border_radius=8,
        padding=12,
        width=290,
    )
