"""Odpowiednik HLOOKUP z Zlecenie!C9/C11/C27: dane rozliczeniowe zlecającego
(agencji lub klienta bezpośredniego) po (account_manager, dom_mediowy), oraz
dane spółek Mediafarm / kontaktów accountów.
"""
import json
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import Optional

from app.models.podmiot import DanePodmiotu, SpolkaMediafarm
from app.services.lokalizacje import katalog_danych_uzytkownika

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# mediafarm.json i podmioty.json zawierają dane, które nigdy nie trafiają do
# repo ani do zbudowanej appki (numery kont bankowych Mediafarm, telefony
# accountów, dane rozliczeniowe klientów - patrz .gitignore). W spakowanej
# wersji jedyne miejsce, gdzie appka może je znaleźć, to ten sam trwały
# folder co ustawienia.json (patrz lokalizacje.py) - trzeba je tam ręcznie
# skopiować raz po instalacji. W wersji z kodu źródłowego (dev) zostaje jak
# dotąd: app/data/ - stąd funkcja (nie stała), żeby testy mogły
# monkeypatchować DATA_DIR i nadal trafiać w to samo miejsce.
def _katalog_uzytkownika() -> Path:
    if getattr(sys, "frozen", False):
        return katalog_danych_uzytkownika()
    return DATA_DIR


def formatuj_telefon(numer: Optional[str]) -> str:
    """Numery w mediafarm.json są trzymane jako same cyfry (bez spacji/
    prefiksu) - formatowanie "+48 XXX XXX XXX" dopiero tutaj, w jednym
    miejscu, żeby dokument Zlecenie i pliki dla wydawców zewnętrznych
    zawsze pokazywały numer tak samo."""
    if not numer:
        return ""
    cyfry = re.sub(r"\D", "", numer)
    if len(cyfry) == 9:
        return f"+48 {cyfry[0:3]} {cyfry[3:6]} {cyfry[6:9]}"
    return numer


def _wczytaj(nazwa: str) -> dict:
    """Puste {} gdy pliku jeszcze nie ma (świeża instalacja, mediafarm.json/
    podmioty.json jeszcze nie skopiowane do %APPDATA%) zamiast wywalać całą
    appkę - UI ma wtedy po prostu puste listy zamiast danych, nie crash."""
    for katalog in (_katalog_uzytkownika(), DATA_DIR):
        sciezka = katalog / nazwa
        if sciezka.exists():
            with open(sciezka, encoding="utf-8") as f:
                return json.load(f)
    return {}


def podmioty_dla_accounta(account_manager: str) -> dict[str, DanePodmiotu]:
    """Wszystkie zlecające (agencje/klienci) obsługiwane przez danego accounta
    — do listy rozwijanej "Dom Mediowy" filtrowanej po accouncie."""
    dane = _wczytaj("podmioty.json").get(account_manager, {})
    return {
        nazwa: DanePodmiotu(
            nazwa=nazwa,
            adres_fakturowy=wpis.get("adres_fakturowy"),
            numery_rejestrowe=wpis.get("numery_rejestrowe"),
            termin_platnosci=wpis.get("termin_platnosci"),
            domyslny_podmiot=wpis.get("domyslny_podmiot"),
        )
        for nazwa, wpis in dane.items()
    }


def termin_platnosci_klienta(account_manager: str, klient: str) -> Optional[str]:
    """Termin płatności nadpisany wprost dla klienta (rzadki wyjątek, patrz
    app/data/terminy_platnosci_klientow.json) - None jeśli klient nie ma
    takiego nadpisania, czyli obowiązuje zwykły termin domu mediowego."""
    mapa = _wczytaj("terminy_platnosci_klientow.json").get(account_manager, {})
    return mapa.get(klient)


def znajdz_podmiot(account_manager: str, dom_mediowy: str, klient: Optional[str] = None) -> Optional[DanePodmiotu]:
    """None jeśli dom_mediowy nie występuje w bazie pod danym accountem —
    UI powinno wtedy pozwolić wpisać dane fakturowe ręcznie, nie wybuchać.

    Jeśli podano klienta i ma on własny nadpisany termin płatności, ma on
    pierwszeństwo przed terminem przypisanym do domu mediowego/agencji —
    patrz termin_platnosci_klienta()."""
    podmiot = podmioty_dla_accounta(account_manager).get(dom_mediowy)
    if podmiot is None:
        return None
    if klient:
        nadpisany_termin = termin_platnosci_klienta(account_manager, klient)
        if nadpisany_termin:
            podmiot = replace(podmiot, termin_platnosci=nadpisany_termin)
    return podmiot


def podmioty_dla_accounta_i_typu(account_manager: str, podmiot_typ: str) -> dict[str, DanePodmiotu]:
    """Podzbiór podmiotów accounta przefiltrowany po domyslny_podmiot:
    "Sp. k." -> agencje (do listy "Dom Mediowy"), "Sp. z o.o." -> klienci
    bezpośredni (do listy "Klient" gdy nie ma agencji-pośrednika)."""
    return {
        nazwa: dane
        for nazwa, dane in podmioty_dla_accounta(account_manager).items()
        if dane.domyslny_podmiot == podmiot_typ
    }


def klienci_dla_agencji(account_manager: str, agencja: str) -> list[str]:
    """Lista klientów (marek) obsługiwanych przez daną agencję pod danym
    accountem, z app/data/klienci_agencyjni.json. Puste jeśli agencja jeszcze
    nie ma przypisanych klientów w tym pliku (mapowanie budowane ręcznie,
    stopniowo) — nie jest to błąd."""
    mapa = _wczytaj("klienci_agencyjni.json").get(account_manager, {})
    return sorted(klient for klient, ag in mapa.items() if ag == agencja)


def lista_accountow() -> list[str]:
    return list(_wczytaj("mediafarm.json").get("accounts", {}).keys())


def slowniki() -> dict:
    """Listy rozwijane (Format reklamowy, Target, Model sprzedaży, Podmiot)."""
    return _wczytaj("slowniki.json")


class BrakDanychMediafarm(Exception):
    """mediafarm.json nie jest jeszcze skopiowany do %APPDATA%\\
    GeneratorZlecenMediafarm na tej maszynie (dane nie trafiają do repo ani
    do instalki - patrz _katalog_uzytkownika()) - do poprawienia przez
    użytkownika/wdrożenie, nie błąd programu."""


def spolka_mediafarm(podmiot_realizujacy: str) -> SpolkaMediafarm:
    spolki = _wczytaj("mediafarm.json").get("spolki", {})
    wpis = spolki.get(podmiot_realizujacy)
    if wpis is None:
        raise BrakDanychMediafarm(
            f"Brak danych Mediafarm dla „{podmiot_realizujacy}” — skopiuj "
            f"mediafarm.json do {_katalog_uzytkownika()}."
        )
    return SpolkaMediafarm(
        nazwa=wpis["nazwa"],
        numery_rejestrowe=wpis["numery_rejestrowe"],
        konto_bankowe=wpis["konto_bankowe"],
        adres=spolki["adres"],
    )


def kontakt_accounta(account_manager: str) -> dict:
    accounts = _wczytaj("mediafarm.json").get("accounts", {})
    kontakt = accounts.get(account_manager)
    if kontakt is None:
        raise BrakDanychMediafarm(
            f"Brak danych Mediafarm dla accounta „{account_manager}” — skopiuj "
            f"mediafarm.json do {_katalog_uzytkownika()}."
        )
    return kontakt
