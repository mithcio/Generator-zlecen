import flet as ft

from app.services import lookup_podmiotu as lp
from app.services import ustawienia
from app.ui.pola_pomocnicze import naglowek_kroku
from app.ui.stan import LICZBA_KROKOW


def buduj(kreator) -> ft.Control:
    stan = kreator.stan

    # Domyślny account manager z Ustawień (ikona koła zębatego) - jeśli
    # ustawiony, wymusza wartość i blokuje dropdown, żeby nie dało się go
    # przez pomyłkę zmienić na innego accounta.
    domyslny_account = ustawienia.wczytaj().get("domyslny_account_manager")
    if domyslny_account:
        stan.account_manager = domyslny_account

    def wybierz_account(e: ft.Event) -> None:
        stan.account_manager = e.control.value or ""
        kreator.odswiez()

    def wybierz_podmiot(e: ft.Event) -> None:
        stan.podmiot_realizujacy = e.control.value or ""
        kreator.odswiez()

    dd_account = ft.Dropdown(
        label="Account manager",
        value=stan.account_manager or None,
        options=[ft.DropdownOption(key=a, text=a) for a in lp.lista_accountow()],
        on_select=wybierz_account,
        disabled=bool(domyslny_account),
        expand=True,
    )
    dd_podmiot = ft.Dropdown(
        label="Podmiot realizujący",
        value=stan.podmiot_realizujacy or None,
        options=[ft.DropdownOption(key=p, text=p) for p in ["Sp. k.", "Sp. z o.o."]],
        on_select=wybierz_podmiot,
        expand=True,
    )

    def dalej(e: ft.Event) -> None:
        bledy = []
        if not stan.account_manager:
            bledy.append("Wybierz accounta.")
        if not stan.podmiot_realizujacy:
            bledy.append("Wybierz podmiot realizujący.")
        if bledy:
            kreator.pokaz_blad(bledy)
            return
        stan.krok = 2
        kreator.odswiez()

    return ft.Column(
        [
            naglowek_kroku(1, LICZBA_KROKOW, "Kto realizuje zlecenie"),
            ft.Text(
                "Account manager decyduje, którzy klienci będą dostępni do wyboru w "
                "kolejnym kroku. Podmiot realizujący decyduje, która spółka Mediafarm "
                "figuruje na zleceniu i jaki prefiks dostanie numer zlecenia (K/…, S/…).",
                color=ft.Colors.GREY_700,
                size=12,
            ),
            dd_account,
            *(
                [
                    ft.Text(
                        "Ustawiony domyślnie w Ustawieniach (ikona koła zębatego) — "
                        "zmień go tam, jeśli trzeba.",
                        color=ft.Colors.GREY_700,
                        size=11,
                    )
                ]
                if domyslny_account
                else []
            ),
            dd_podmiot,
            ft.Row([ft.FilledButton("Dalej", on_click=dalej)], alignment=ft.MainAxisAlignment.END),
        ],
        spacing=16,
    )
