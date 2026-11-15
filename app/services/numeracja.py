"""Rezerwacja numeru zlecenia bezpośrednio w pliku Numery_zlecen_2026.xlsx
(ścieżka ustawiana w panelu Ustawienia — ikona koła zębatego).

Plik jest współdzielony (żyje w folderze zsynchronizowanym z chmurą, żeby
kilku akantów mogło z niego korzystać naraz), więc żeby zminimalizować okno
na konflikt, rezerwacja to jedna szybka sekwencja: otwórz -> znajdź pierwszy
wolny numer -> zapisz status/datę/akanta -> zapisz i zamknij od razu. Numer
trafia do pamięci programu i od tej chwili plik jest znów wolny dla innych.
To nie jest twarda blokada (nie ma serwera plików pilnującego dostępu) -
przy dosłownie jednoczesnym kliknięciu dwóch osób nadal jest teoretyczne
ryzyko wyścigu, ale krótkie okno otwarcia/zapisu/zamknięcia drastycznie je
ogranicza względem trzymania pliku otwartego przez cały czas pracy w
kreatorze.

Arkusz "Numery zleceń": kolumny A-D = SP. K. (numer/status/data/użytkownik),
kolumny F-I = SP. Z O.O. (to samo przesunięte o kolumnę E jako separator).
"""
import os
from datetime import date, datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment
from openpyxl.worksheet.worksheet import Worksheet

from app.services import ustawienia

ARKUSZ = "Numery zleceń"

PREFIKSY = {"Sp. k.": "K", "Sp. z o.o.": "S"}

KOLUMNY = {
    "Sp. k.": {"numer": "A", "status": "B", "data": "C", "akant": "D"},
    "Sp. z o.o.": {"numer": "F", "status": "G", "data": "H", "akant": "I"},
}

WYROWNANIE_SRODEK = Alignment(horizontal="center")


class BladNumeracji(Exception):
    """Ścieżka do pliku nieustawiona/nieprawidłowa, brak zakładki, brak
    wolnych numerów, plik zajęty przez inny program — wszystko, co
    użytkownik musi sam poprawić (w Ustawieniach albo w samym pliku), a nie
    błąd programu."""


def _sprawdz_podmiot(podmiot_realizujacy: str) -> None:
    if podmiot_realizujacy not in KOLUMNY:
        raise ValueError(
            f"Nieznany podmiot realizujący: {podmiot_realizujacy!r} "
            f"(oczekiwano: {', '.join(KOLUMNY)})"
        )


def _otworz_workbook(sciezka: str) -> openpyxl.Workbook:
    try:
        return openpyxl.load_workbook(sciezka)
    except OSError as err:
        # Najczęstsza przyczyna: plik otwarty w tej chwili w Excelu (albo
        # jeszcze w trakcie synchronizacji z chmurą) - blokuje odczyt/zapis.
        raise BladNumeracji(
            f"Nie udało się otworzyć pliku {sciezka} — prawdopodobnie jest otwarty "
            "w Excelu (albo w trakcie synchronizacji z chmurą). Zamknij go i spróbuj "
            f"ponownie. Szczegóły: {err}"
        ) from err


def _zapisz_workbook(wb: openpyxl.Workbook, sciezka: str) -> None:
    try:
        wb.save(sciezka)
    except OSError as err:
        raise BladNumeracji(
            f"Nie udało się zapisać pliku {sciezka} — prawdopodobnie jest otwarty "
            f"w Excelu. Zamknij go i spróbuj ponownie. Szczegóły: {err}"
        ) from err


def _sciezka_pliku() -> str:
    sciezka = ustawienia.wczytaj().get("sciezka_numery_zlecen")
    if not sciezka or not Path(sciezka).exists():
        raise BladNumeracji(
            "Nie ustawiono ścieżki do pliku Numery_zlecen_2026.xlsx (albo plik pod "
            "wskazaną ścieżką nie istnieje) — ustaw ją w Ustawieniach (ikona koła "
            "zębatego w prawym górnym rogu)."
        )
    return sciezka


def _arkusz(wb: openpyxl.Workbook, sciezka: str) -> Worksheet:
    if ARKUSZ not in wb.sheetnames:
        raise BladNumeracji(f"Plik {sciezka} nie ma zakładki „{ARKUSZ}”.")
    return wb[ARKUSZ]


def _znajdz_wiersz_numeru(ws: Worksheet, kol_numeru: str, numer: str) -> int | None:
    for r in range(2, ws.max_row + 1):
        if str(ws[f"{kol_numeru}{r}"].value or "").strip() == numer:
            return r
    return None


def sciezka_rejestru() -> str:
    """Plik, w którym ten proces faktycznie rezerwuje numery (diagnostyka:
    serwer MCP i okno aplikacji mogą mieć różne ustawienia)."""
    return _sciezka_pliku()


def _normalizuj_numer(numer: str) -> str:
    """Rejestr trzyma numery jako K/2026/001, a w nazwach plików i folderów
    ten sam numer występuje jako K-2026-001 - przy szukaniu w rejestrze oba
    zapisy oznaczają to samo."""
    return str(numer).strip().replace("-", "/")


def _potwierdz_zapis(sciezka: str, podmiot_realizujacy: str, numer: str, account_manager: str | None) -> None:
    """Otwiera plik z dysku od nowa (nie obiekt z pamięci) i sprawdza, że numer
    ma status „zajete” i właściwego account managera. Bez tego zapis, który
    nie dotarł na dysk, wyglądał jak udana rezerwacja."""
    kol = KOLUMNY[podmiot_realizujacy]
    wb = _otworz_workbook(sciezka)
    try:
        ws = _arkusz(wb, sciezka)
        wiersz = _znajdz_wiersz_numeru(ws, kol["numer"], _normalizuj_numer(numer))
        zapisano = (
            wiersz is not None
            and str(ws[f"{kol['status']}{wiersz}"].value or "").strip() == "zajete"
            and str(ws[f"{kol['akant']}{wiersz}"].value or "").strip() == (account_manager or "").strip()
        )
    finally:
        wb.close()
    if not zapisano:
        raise BladNumeracji(
            f"Rezerwacja numeru {numer} nie została potwierdzona odczytem pliku {sciezka} "
            "(zapis nie dotarł na dysk albo plik zmienił inny program). Numer NIE jest zarezerwowany."
        )


def stan_rejestru() -> dict:
    """Odczyt (bez zapisu): który plik jest używany, kiedy był zmieniony oraz
    ostatni zajęty i pierwszy wolny numer dla każdego podmiotu."""
    sciezka = _sciezka_pliku()
    wb = _otworz_workbook(sciezka)
    try:
        ws = _arkusz(wb, sciezka)
        wynik = {
            "plik": sciezka,
            "plik_zmieniony": datetime.fromtimestamp(os.stat(sciezka).st_mtime).isoformat(timespec="seconds"),
        }
        for podmiot, kol in KOLUMNY.items():
            zajete, wolny = 0, None
            ostatni = None
            for r in range(2, ws.max_row + 1):
                if str(ws[f"{kol['status']}{r}"].value or "").strip():
                    zajete += 1
                    ostatni = {
                        "numer": ws[f"{kol['numer']}{r}"].value,
                        "data": str(ws[f"{kol['data']}{r}"].value or ""),
                        "account": str(ws[f"{kol['akant']}{r}"].value or ""),
                    }
                elif wolny is None:
                    wolny = ws[f"{kol['numer']}{r}"].value
            wynik[PREFIKSY[podmiot]] = {"zajetych": zajete, "ostatni_zajety": ostatni, "nastepny_wolny": wolny}
        return wynik
    finally:
        wb.close()


def zajmij_numer(numer: str, podmiot_realizujacy: str, account_manager: str | None = None) -> bool:
    """Rezerwuje KONKRETNY numer (podany ręcznie, np. przy ponownym wystawieniu
    zlecenia) - ta sama rezerwacja co przy numerze nadawanym automatycznie.

    Zwraca True, gdy numer był wolny i został teraz zarezerwowany, False, gdy
    był już zajęty przez tego samego account managera (powtórne wystawienie
    własnego numeru - nic nie zmieniamy). Numer zajęty przez kogo innego albo
    nieistniejący w pliku to BladNumeracji: zlecenie z takim numerem nie może
    powstać."""
    _sprawdz_podmiot(podmiot_realizujacy)
    kol = KOLUMNY[podmiot_realizujacy]
    numer = _normalizuj_numer(numer)
    prefiks = PREFIKSY[podmiot_realizujacy] + "/"
    if not numer.startswith(prefiks):
        raise BladNumeracji(
            f"Numer {numer} nie pasuje do podmiotu „{podmiot_realizujacy}” (oczekiwano numeru zaczynającego się od {prefiks})."
        )
    sciezka = _sciezka_pliku()

    wb = _otworz_workbook(sciezka)
    try:
        ws = _arkusz(wb, sciezka)
        wiersz = _znajdz_wiersz_numeru(ws, kol["numer"], numer)
        if wiersz is None:
            raise BladNumeracji(f"Numeru {numer} nie ma w pliku {sciezka} - nie mogę go zarezerwować.")

        if str(ws[f"{kol['status']}{wiersz}"].value or "").strip():
            wlasciciel = str(ws[f"{kol['akant']}{wiersz}"].value or "").strip()
            data = str(ws[f"{kol['data']}{wiersz}"].value or "").strip()
            if account_manager and wlasciciel.casefold() == account_manager.casefold():
                return False
            raise BladNumeracji(
                f"Numer {numer} jest już zajęty w pliku {sciezka} (account: {wlasciciel or 'brak'}, "
                f"data: {data or 'brak'}). Wybierz inny numer."
            )

        for klucz, wartosc in (
            ("status", "zajete"),
            ("data", date.today().strftime("%d.%m.%Y")),
            ("akant", account_manager or ""),
        ):
            komorka = ws[f"{kol[klucz]}{wiersz}"]
            komorka.value = wartosc
            komorka.alignment = WYROWNANIE_SRODEK

        _zapisz_workbook(wb, sciezka)
    finally:
        wb.close()

    _potwierdz_zapis(sciezka, podmiot_realizujacy, numer, account_manager)
    return True


def zarezerwuj_numer(podmiot_realizujacy: str, account_manager: str | None = None) -> str:
    """Znajduje pierwszy wolny numer dla danego podmiotu (skan kolumny
    status), zapisuje w tym samym wierszu status "zajete", dzisiejszą datę i
    przekazanego account managera, po czym zwraca numer zlecenia (z kolumny
    numeru w tym samym wierszu)."""
    _sprawdz_podmiot(podmiot_realizujacy)
    kol = KOLUMNY[podmiot_realizujacy]
    sciezka = _sciezka_pliku()

    wb = _otworz_workbook(sciezka)
    try:
        ws = _arkusz(wb, sciezka)

        wiersz_wolny = None
        for r in range(2, ws.max_row + 1):
            status = ws[f"{kol['status']}{r}"].value
            if not status or not str(status).strip():
                wiersz_wolny = r
                break

        if wiersz_wolny is None:
            raise BladNumeracji(
                f"Brak wolnych numerów zleceń dla „{podmiot_realizujacy}” w pliku {sciezka}."
            )

        numer = ws[f"{kol['numer']}{wiersz_wolny}"].value
        if not numer:
            raise BladNumeracji(
                f"Wiersz {wiersz_wolny} w zakładce „{ARKUSZ}” nie ma numeru zlecenia "
                f"w kolumnie {kol['numer']}."
            )

        for klucz, wartosc in (
            ("status", "zajete"),
            ("data", date.today().strftime("%d.%m.%Y")),
            ("akant", account_manager or ""),
        ):
            komorka = ws[f"{kol[klucz]}{wiersz_wolny}"]
            komorka.value = wartosc
            komorka.alignment = WYROWNANIE_SRODEK

        _zapisz_workbook(wb, sciezka)
    finally:
        wb.close()

    _potwierdz_zapis(sciezka, podmiot_realizujacy, str(numer), account_manager)
    return str(numer)


def zwolnij_numer(numer: str, podmiot_realizujacy: str) -> None:
    """Czyści rezerwację (status/data/akant) numeru wcześniej pobranego
    automatycznie — używane, gdy użytkownik na kroku 2 świadomie zachowuje
    numer wpisany ręcznie/wklejony z pliku kampanii zamiast tego pobranego
    automatycznie, żeby nie zostawić w pliku "wiszącej" rezerwacji numeru,
    którego nikt finalnie nie użył."""
    _sprawdz_podmiot(podmiot_realizujacy)
    kol = KOLUMNY[podmiot_realizujacy]
    sciezka = _sciezka_pliku()

    wb = _otworz_workbook(sciezka)
    try:
        ws = _arkusz(wb, sciezka)

        wiersz = _znajdz_wiersz_numeru(ws, kol["numer"], _normalizuj_numer(numer))
        if wiersz is None:
            raise BladNumeracji(
                f"Nie znaleziono numeru {numer} w pliku {sciezka} — rezerwacja nie została zwolniona."
            )

        for klucz in ("status", "data", "akant"):
            ws[f"{kol[klucz]}{wiersz}"] = None

        _zapisz_workbook(wb, sciezka)
    finally:
        wb.close()
