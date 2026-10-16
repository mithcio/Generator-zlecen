"""Wystawianie zlecenia bez kreatora (UI) - ta sama droga co kroki 2-5, ale
z gotowego słownika danych. Używane przez serwer MCP (app/mcp_server.py), żeby
Claude mógł wystawić zlecenie z maila/xlsx; nie zależy od pakietu mcp, więc da
się to testować zwykłym pytestem.

Dwie operacje: podglad() - walidacja i podsumowanie, nic nie zapisuje i nie
pobiera numeru; wystaw() - rezerwuje numer w Numery_zlecen_2026.xlsx, generuje
pliki (Zlecenie xlsx+PDF, opcjonalnie Dane Traffic i plik wydawcy) i zwraca
wiersze do wklejenia do pliku kampanii.
"""
from datetime import date, datetime

from app.models.dane_traffic import DaneTraffic
from app.models.okres import Okres
from app.services import cennik, generator_wydawcy, lookup_podmiotu as lp, numeracja, ustawienia
from app.services.eksport_nazwy import folder_zlecenia, nazwa_pliku_dane_traffic, nazwa_pliku_zlecenie
from app.services.eksport_wiersza import zbuduj_wiersze_do_wklejenia_per_okres
from app.services.generator_dane_traffic import generuj_dane_traffic
from app.services.generator_pdf import generuj_pdf
from app.services.generator_xlsx import generuj_xlsx
from app.services.kalkulacje import auto_podziel_budzet
from app.templates.zlecenie_layout import format_na_zleceniu
# shortcut: konwersja danych -> Zlecenie i dane pomocnicze (podmiot, spółka,
# kontakt) żyją w kroku 4 kreatora - importujemy je stamtąd zamiast kopiować
# (ciągnie flet, co w procesie MCP jest tylko nieco wolniejszym startem).
from app.ui.krok4_podglad import dane_pomocnicze, zbuduj_zlecenie
from app.ui.stan import StanKreatora

NR_TYMCZASOWY = "(zostanie nadany przy wystawieniu)"
PODMIOTY_REALIZUJACE = ["Sp. k.", "Sp. z o.o."]
WYDAWCY = ["brak", "KIDOZ", "ODEEO", "ADVERTY", "CRAZYGAMES", "POKI"]


def _data(tekst) -> date:
    if isinstance(tekst, date):
        return tekst
    tekst = str(tekst).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(tekst, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Niepoprawna data „{tekst}” (oczekiwano RRRR-MM-DD albo DD.MM.RRRR).")


def _okresy(lista) -> tuple[list[Okres], list[str]]:
    """Każdy wpis: {start, koniec, budzet}. Jeden wpis rozciągnięty na kilka
    miesięcy jest dzielony automatycznie (jak „Rozbij automatycznie na
    miesiące” w kroku 3) - kampania przejściowa to jeden okres na miesiąc."""
    wynik, bledy = [], []
    for i, wpis in enumerate(lista or [], start=1):
        try:
            start, koniec = _data(wpis["start"]), _data(wpis["koniec"])
            budzet = float(str(wpis["budzet"]).replace(",", ".").replace(" ", ""))
        except (KeyError, ValueError) as err:
            bledy.append(f"Okres {i}: {err}")
            continue
        if (start.year, start.month) != (koniec.year, koniec.month) and koniec >= start and budzet > 0:
            wynik.extend(auto_podziel_budzet(budzet, start, koniec))
        else:
            wynik.append(Okres(start, koniec, budzet))
    return wynik, bledy


def _stan(dane: dict) -> tuple[StanKreatora, list[str]]:
    bledy: list[str] = []
    st = StanKreatora()
    st.account_manager = dane.get("account_manager") or ustawienia.wczytaj().get("domyslny_account_manager") or ""
    st.podmiot_realizujacy = dane.get("podmiot_realizujacy") or ""
    klient = dane.get("klient") or ""
    dom = dane.get("dom_mediowy") or ""
    if st.podmiot_realizujacy == "Sp. z o.o.":
        # Klient bezpośredni: ta sama nazwa w obu polach (jak w kroku 2).
        dom = klient = dom or klient
    st.dom_mediowy, st.klient = dom, klient
    for pole in ("nazwa_kampanii", "brand", "zlecajacy", "target", "format_reklamowy",
                 "model_sprzedazy", "uwagi", "uwagi_traffic", "link_spot", "link_kody"):
        setattr(st, pole, dane.get(pole) or "")
    capping = dane.get("capping")
    st.capping = "brak" if capping in (None, "", "brak") else str(int(capping))
    st.koszt_jednostkowy = "" if dane.get("koszt_jednostkowy") is None else str(dane["koszt_jednostkowy"])
    st.nr_zlecenia = dane.get("nr_zlecenia") or NR_TYMCZASOWY
    st.wydawca_zewnetrzny = dane.get("wydawca_zewnetrzny") or "brak"
    st.poki_placement = dane.get("poki_placement") or ""
    st.okresy, bledy_okresow = _okresy(dane.get("okresy"))
    bledy.extend(bledy_okresow)

    slowniki = lp.slowniki()
    dozwolone = {
        "podmiot_realizujacy": PODMIOTY_REALIZUJACE,
        "target": slowniki.get("target", []),
        "format_reklamowy": slowniki.get("format_reklamowy", []),
        "model_sprzedazy": slowniki.get("model_sprzedazy", []),
        "wydawca_zewnetrzny": WYDAWCY,
    }
    for pole, lista in dozwolone.items():
        wartosc = getattr(st, pole)
        if wartosc and lista and wartosc not in lista:
            bledy.append(f"Niedozwolona wartość pola {pole}: „{wartosc}”. Dozwolone: {', '.join(lista)}.")
    if st.account_manager and st.account_manager not in lp.lista_accountow():
        bledy.append(f"Nieznany account manager „{st.account_manager}”. Dozwolone: {', '.join(lp.lista_accountow())}.")
    return st, bledy


def slowniki_i_podmioty(fraza: str = "", account_manager: str = "") -> dict:
    """Dozwolone wartości pól + (gdy podano frazę) pasujące domy mediowe /
    klienci z bazy podmiotów danego accounta - żeby wpisać nazwy dokładnie
    tak, jak są w bazie (po nich działa lookup danych fakturowych)."""
    slowniki = lp.slowniki()
    domyslny = ustawienia.wczytaj().get("domyslny_account_manager")
    account = account_manager or domyslny or ""
    wynik = {
        "accounty": lp.lista_accountow(),
        "domyslny_account_manager": domyslny,
        "podmioty_realizujace": PODMIOTY_REALIZUJACE,
        "formaty_reklamowe": slowniki.get("format_reklamowy", []),
        "targety": slowniki.get("target", []),
        "modele_sprzedazy": slowniki.get("model_sprzedazy", []),
        "wydawcy_zewnetrzni": WYDAWCY,
        "placementy_poki": generator_wydawcy.PLACEMENTY_POKI,
    }
    if fraza and account:
        f = fraza.casefold()
        trafienia = []
        for nazwa, podmiot in lp.podmioty_dla_accounta(account).items():
            klienci = lp.klienci_dla_agencji(account, nazwa)
            pasujacy = [k for k in klienci if f in k.casefold()]
            if f in nazwa.casefold() or pasujacy:
                trafienia.append({
                    "dom_mediowy_lub_klient_bezposredni": nazwa,
                    "domyslny_podmiot": podmiot.domyslny_podmiot,
                    "termin_platnosci": podmiot.termin_platnosci,
                    "klienci": klienci if f in nazwa.casefold() else pasujacy,
                })
        wynik["trafienia"] = trafienia[:20]
        wynik["account_manager_przeszukany"] = account
    return wynik


def _ostrzezenia(stan: StanKreatora, ostrzezenie_podmiotu: str | None) -> list[str]:
    ost = [ostrzezenie_podmiotu] if ostrzezenie_podmiotu else []
    if stan.wydawca_zewnetrzny != "brak" and not generator_wydawcy.czy_format_pasuje(
        stan.wydawca_zewnetrzny, stan.format_reklamowy
    ):
        ost.append(
            f"Format „{stan.format_reklamowy}” zwykle nie pasuje do wydawcy {stan.wydawca_zewnetrzny}."
        )
    return ost


def podglad(dane: dict) -> dict:
    stan, bledy = _stan(dane)
    zlecenie, bledy_zlecenia = zbuduj_zlecenie(stan)
    bledy += bledy_zlecenia
    if bledy or zlecenie is None:
        return {"ok": False, "bledy": bledy}
    try:
        podmiot, _, _, ostrzezenie = dane_pomocnicze(stan)
    except lp.BrakDanychMediafarm as err:
        return {"ok": False, "bledy": [str(err)]}
    return {
        "ok": True,
        "nr_zlecenia": stan.nr_zlecenia if stan.nr_zlecenia != NR_TYMCZASOWY else NR_TYMCZASOWY,
        "ostrzezenia": _ostrzezenia(stan, ostrzezenie),
        "podsumowanie": {
            "account_manager": stan.account_manager,
            "podmiot_realizujacy": stan.podmiot_realizujacy,
            "nazwa_kampanii": stan.nazwa_kampanii,
            "dom_mediowy": stan.dom_mediowy,
            "klient": stan.klient,
            "target": stan.target,
            "format_reklamowy": stan.format_reklamowy,
            "format_na_zleceniu": format_na_zleceniu(zlecenie.pola),
            "model_sprzedazy": stan.model_sprzedazy,
            "koszt_jednostkowy": zlecenie.pola.koszt_jednostkowy,
            "budzet_total": round(zlecenie.budzet_total, 2),
            "liczba_total": round(zlecenie.liczba_total),
            "data_startu": zlecenie.data_startu.isoformat(),
            "data_konca": zlecenie.data_konca.isoformat(),
            "okresy": [
                {"start": o.data_startu.isoformat(), "koniec": o.data_konca.isoformat(), "budzet": round(o.budzet, 2)}
                for o in sorted(zlecenie.okresy, key=lambda o: o.data_startu)
            ],
            "termin_platnosci": podmiot.termin_platnosci,
        },
    }


def wystaw(dane: dict) -> dict:
    stan, bledy = _stan(dane)
    zlecenie, bledy_zlecenia = zbuduj_zlecenie(stan)
    bledy += bledy_zlecenia
    if bledy or zlecenie is None:
        return {"ok": False, "bledy": bledy}

    zarezerwowano = False
    if stan.nr_zlecenia == NR_TYMCZASOWY:
        try:
            stan.nr_zlecenia = numeracja.zarezerwuj_numer(stan.podmiot_realizujacy, stan.account_manager)
        except numeracja.BladNumeracji as err:
            return {"ok": False, "bledy": [str(err)]}
        zarezerwowano = True
        zlecenie, _ = zbuduj_zlecenie(stan)

    try:
        podmiot, spolka, kontakt, ostrzezenie = dane_pomocnicze(stan)
        folder = folder_zlecenia(stan.nr_zlecenia)
        nazwa = nazwa_pliku_zlecenie(stan.nr_zlecenia, stan.nazwa_kampanii)
        pliki = [
            generuj_xlsx(zlecenie, podmiot, spolka, kontakt, folder / f"{nazwa}.xlsx",
                         nadpisania=stan.zlecenie_nadpisania),
            generuj_pdf(zlecenie, podmiot, spolka, kontakt, folder / f"{nazwa}.pdf",
                        nadpisania=stan.zlecenie_nadpisania),
        ]
    except Exception as err:  # numer wzięty, a zlecenia nie ma - oddajemy numer
        zwolniono = False
        if zarezerwowano:
            try:
                numeracja.zwolnij_numer(stan.nr_zlecenia, stan.podmiot_realizujacy)
                zwolniono = True
            except Exception:
                pass
        return {
            "ok": False,
            "bledy": [f"Nie udało się wygenerować zlecenia: {err}"],
            "numer_zwolniony": zwolniono,
        }

    ostrzezenia = _ostrzezenia(stan, ostrzezenie)
    if dane.get("dane_traffic", True):
        try:
            dane_traffic = DaneTraffic(
                uwagi_traffic=stan.uwagi_traffic, link_spot=stan.link_spot, link_kody=stan.link_kody
            )
            pliki.append(generuj_dane_traffic(
                zlecenie, dane_traffic,
                folder / f"{nazwa_pliku_dane_traffic(stan.klient, stan.brand, stan.nr_zlecenia)}.xlsx",
            ))
            if stan.wydawca_zewnetrzny == "POKI":
                pliki.append(generator_wydawcy.generuj_poki(zlecenie, spolka, kontakt, folder, stan.poki_placement))
            elif stan.wydawca_zewnetrzny != "brak":
                pliki.append(generator_wydawcy.GENERATORY[stan.wydawca_zewnetrzny](zlecenie, spolka, kontakt, folder))
        except (OSError, generator_wydawcy.BladSzablonuWydawcy, cennik.BladCennika) as err:
            ostrzezenia.append(f"Zlecenie wystawione, ale Dane Traffic / plik wydawcy się nie wygenerowały: {err}")

    return {
        "ok": True,
        "nr_zlecenia": stan.nr_zlecenia,
        "numer_nadany_automatycznie": zarezerwowano,
        "folder": str(folder),
        "pliki": [str(p) for p in pliki],
        "ostrzezenia": ostrzezenia,
        "wiersze_do_pliku_kampanii": [
            {"okres": f"{o.data_startu:%d.%m.%Y}-{o.data_konca:%d.%m.%Y}", "wiersz": w}
            for o, w in zbuduj_wiersze_do_wklejenia_per_okres(zlecenie)
        ],
    }
