"""Parsowanie wklejonego wiersza/wierszy (np. skopiowanych z pliku kampanii
Igora) do pól wspólnych kampanii + listy okresów.

Kolejność kolumn odpowiada arkuszom miesięcznym pliku kampanii: Nazwa
Kampanii, DOM Mediowy, Klient, Zlecający, Target, Przejściowa, Format
reklamowy, Podmiot realizujący, Uwagi, Model sprzedaży, Koszt jednostkowy,
Nr_zlecenia, Budżet, Data startu, Data końca.

Wklejenie wielu linii = wiele okresów pod jedną kampanią. "Przejściowa" jest
tu tylko historycznym znacznikiem z Excela — w nowym modelu jest wyliczana
(len(okresy) > 1), więc kolumna jest parsowana, ale odrzucana.
"""
import re
from dataclasses import dataclass
from datetime import date, datetime

from app.models.okres import Okres

KOLUMNY = [
    "nazwa_kampanii",
    "dom_mediowy",
    "klient",
    "zlecajacy",
    "target",
    "przejsciowa",  # parsowana, ale odrzucana - wyliczamy to sami
    "format_reklamowy",
    "podmiot_realizujacy",
    "uwagi",
    "model_sprzedazy",
    "koszt_jednostkowy",
    "nr_zlecenia",
    "budzet",
    "data_startu",
    "data_konca",
]

POLA_WSPOLNE_KLUCZE = [
    "nazwa_kampanii",
    "dom_mediowy",
    "klient",
    "zlecajacy",
    "target",
    "format_reklamowy",
    "podmiot_realizujacy",
    # "uwagi" celowo pominięte - kolumna Uwagi w pliku kampanii to co innego
    # niż Zlecenie.pola.uwagi (uwagi na dokumencie dla klienta, wpisywane
    # ręcznie w kroku 2) - patrz ustalenia z użytkownikiem. Kolumna jest
    # nadal parsowana (KOLUMNY niżej), żeby nie zepsuć pozycji kolejnych
    # kolumn, ale jej wartość jest odrzucana, nie trafia do stanu kreatora.
    "model_sprzedazy",
    "koszt_jednostkowy",
    "nr_zlecenia",
]

_PREFIKS_NAZWY = re.compile(r"^\d{2}\.\d{4}_")
_FORMATY_DAT = ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%y")
_WALUTA_RE = re.compile(r"\s*(zł|zl|pln)\s*$", re.IGNORECASE)

# Kolumna 16 (indeks 15, zaraz po Data końca) w pliku kampanii to "Liczba
# wyświetleń/klików/pełnych odtworzeń" - nie jest wymagana do zbudowania
# zlecenia (aplikacja liczy ją sama z budżetu i modelu sprzedaży), ale
# zachowujemy ją do porównania. Dalsze kolumny (wydawca do fakturowania,
# kwota zlecona, statystyki) są ignorowane.
_INDEKS_LICZBY_ZRODLOWEJ = 15


class BladParsowaniaWiersza(Exception):
    """Błąd wklejonego wiersza z czytelnym komunikatem po polsku, do pokazania w UI."""


@dataclass
class KonfliktPola:
    pole: str
    wartosci: list[str]


def _parsuj_liczbe(s: str, nazwa_pola: str) -> float:
    """Rozumie zarówno polski format (spacja=tysiące, przecinek=dziesiętny:
    "1 234,56"), jak i format wklejany z pliku kampanii (przecinek=tysiące,
    kropka=dziesiętna, sufiks waluty: "24,667.00 zł"). Gdy oba separatory są
    obecne, decyduje ten, który występuje bliżej końca liczby - to on jest
    dziesiętny. Przy jednym przecinku i braku kropki, dokładnie trzy cyfry po
    przecinku oznaczają grupowanie tysięcy (np. "649,132"), inaczej to
    polski separator dziesiętny (np. "26,5")."""
    original = s
    s = s.strip().replace("\xa0", " ")
    s = _WALUTA_RE.sub("", s).strip()
    liczba_przecinkow = s.count(",")
    ma_kropke = "." in s

    if liczba_przecinkow and ma_kropke:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif liczba_przecinkow >= 2:
        s = s.replace(",", "")
    elif liczba_przecinkow == 1:
        cyfry_po_przecinku = s.split(",")[-1]
        if len(cyfry_po_przecinku) == 3:
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")

    s = s.replace(" ", "")
    try:
        return float(s)
    except ValueError:
        raise BladParsowaniaWiersza(
            f"Nie rozumiem wartości liczbowej w polu „{nazwa_pola}”: {original!r}. "
            "Sprawdź, czy to liczba (np. 1234.56 albo 24,667.00 zł)."
        )


def _parsuj_date(s: str, nazwa_pola: str) -> date:
    s = s.strip()
    for fmt in _FORMATY_DAT:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise BladParsowaniaWiersza(
        f"Nie rozumiem daty w polu „{nazwa_pola}”: {s!r}. "
        "Oczekiwany format: DD.MM.RRRR, RRRR-MM-DD albo DD-MM-RR."
    )


def _oczysc_nazwe_kampanii(nazwa: str) -> str:
    """Odpowiednik starej formuły Zlecenie!C16 (MID/FIND): jeśli nazwa ma
    prefiks "MM.RRRR_" (konwencja z pliku kampanii), usuwa go."""
    return _PREFIKS_NAZWY.sub("", nazwa.strip())


def parsuj_wiersz(linia: str) -> dict:
    """Parsuje jedną linię (kolumny rozdzielone tabulatorem) na słownik pól.

    Zaznaczenie i wklejenie całego wiersza z pliku kampanii daje więcej niż
    15 kolumn (dalej idą wydawca do fakturowania, kwota zlecona, statystyki
    CTR itp.) - nadmiar jest obcinany, nie jest to błąd. Zbyt mało kolumn
    nadal jest błędem, bo wtedy realnie brakuje wymaganych danych.
    """
    komorki = linia.split("\t")
    if len(komorki) < len(KOLUMNY):
        raise BladParsowaniaWiersza(
            f"Wklejony wiersz ma tylko {len(komorki)} kolumn, a potrzeba co "
            f"najmniej {len(KOLUMNY)} (Nazwa Kampanii, DOM Mediowy, Klient, "
            "Zlecający, Target, Przejściowa, Format reklamowy, Podmiot "
            "realizujący, Uwagi, Model sprzedaży, Koszt jednostkowy, "
            "Nr_zlecenia, Budżet, Data startu, Data końca). Sprawdź, czy "
            "wkleiłeś/aś cały wiersz z właściwych kolumn."
        )

    wartosci = dict(zip(KOLUMNY, (c.strip() for c in komorki[: len(KOLUMNY)])))
    wartosci["nazwa_kampanii"] = _oczysc_nazwe_kampanii(wartosci["nazwa_kampanii"])
    wartosci["koszt_jednostkowy"] = _parsuj_liczbe(wartosci["koszt_jednostkowy"], "Koszt jednostkowy")
    wartosci["budzet"] = _parsuj_liczbe(wartosci["budzet"], "Budżet")
    wartosci["data_startu"] = _parsuj_date(wartosci["data_startu"], "Data startu")
    wartosci["data_konca"] = _parsuj_date(wartosci["data_konca"], "Data końca")

    liczba_zrodlowa = None
    if len(komorki) > _INDEKS_LICZBY_ZRODLOWEJ:
        tekst_liczby = komorki[_INDEKS_LICZBY_ZRODLOWEJ].strip()
        if tekst_liczby:
            try:
                liczba_zrodlowa = _parsuj_liczbe(tekst_liczby, "Liczba (źródłowa)")
            except BladParsowaniaWiersza:
                pass  # tylko do porównania - nie blokujemy wklejenia, jeśli nie da się jej odczytać
    wartosci["liczba_zrodlowa"] = liczba_zrodlowa
    return wartosci


def parsuj_wiersze(tekst: str) -> list[dict]:
    linie = [l for l in tekst.splitlines() if l.strip()]
    if not linie:
        raise BladParsowaniaWiersza("Nie wklejono żadnego wiersza.")
    return [parsuj_wiersz(l) for l in linie]


def rozdziel_pola_wspolne_i_okresy(
    wiersze: list[dict],
) -> tuple[dict, list[Okres], list[KonfliktPola]]:
    """Z listy sparsowanych wierszy wydziela: pola wspólne (jeśli spójne
    między wierszami), listę okresów (budżet+daty per wiersz) i listę
    konfliktów — pól, które różnią się między wierszami i wymagają decyzji
    użytkownika zamiast zgadywania.

    Dla klientów bezpośrednich (Sp. z o.o.) kolumna "Klient" w źródle jest
    ignorowana (bywa pusta/"-"/"brak" - dane biorą się z kolumny "Dom
    Mediowy"), więc pomijamy ją przy wykrywaniu konfliktów, żeby nie prosić
    o rozstrzygnięcie różnicy w polu, którego i tak nie używamy."""
    wspolne: dict = {}
    konflikty: list[KonfliktPola] = []

    wszystkie_sp_zoo = all(
        str(w.get("podmiot_realizujacy", "")).strip() == "Sp. z o.o." for w in wiersze
    )

    for klucz in POLA_WSPOLNE_KLUCZE:
        if klucz == "klient" and wszystkie_sp_zoo:
            wspolne[klucz] = None
            continue
        wartosci_unikalne = list(dict.fromkeys(w[klucz] for w in wiersze))
        if len(wartosci_unikalne) == 1:
            wspolne[klucz] = wartosci_unikalne[0]
        else:
            konflikty.append(KonfliktPola(pole=klucz, wartosci=wartosci_unikalne))
            wspolne[klucz] = None

    okresy = [
        Okres(
            data_startu=w["data_startu"],
            data_konca=w["data_konca"],
            budzet=w["budzet"],
            liczba_zrodlowa=w.get("liczba_zrodlowa"),
        )
        for w in wiersze
    ]
    return wspolne, okresy, konflikty


def _fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def wykryj_ostrzezenia(wiersze: list[dict], okresy: list[Okres]) -> list[str]:
    """Sygnały, że coś może być nie tak z połączeniem wierszy w jedną
    kampanię — nie blokują (mogą mieć uzasadnienie), tylko proszą o
    potwierdzenie zamiast po cichu przechodzić dalej:

    - Kolumna "Przejściowa" (TAK/NIE) ze źródła nie zgadza się z faktyczną
      liczbą okresów. Flaga jest przypisana do konkretnego miesiąca i mówi,
      czy kampania przechodzi na KOLEJNY miesiąc - więc każdy wiersz poza
      ostatnim (chronologicznie) powinien mieć TAK (skoro łączymy go z
      następnym), a ostatni powinien mieć NIE (nic po nim nie kontynuujemy).
      Odstępstwo w dowolną stronę - wiersz przed ostatnim oznaczony NIE, albo
      ostatni oznaczony TAK (sugerujący brakujący kolejny wiersz) - jest
      warte ostrzeżenia. Osobny przypadek: pojedynczy samotnie wklejony
      wiersz oznaczony TAK.
    - Przerwa dłuższa niż 1 dzień między końcem jednego okresu a początkiem
      kolejnego — zlecenie i tak pokaże cały zakres dat (MIN-MAX), więc
      przerwa byłaby niewidoczna na dokumencie.
    """
    ostrzezenia: list[str] = []

    if len(okresy) > 1:
        posortowane_wiersze = sorted(wiersze, key=lambda w: w["data_startu"])
        ostatni_indeks = len(posortowane_wiersze) - 1
        for i, w in enumerate(posortowane_wiersze):
            oznaczenie = str(w.get("przejsciowa", "")).strip().upper()
            czy_ostatni = i == ostatni_indeks
            if not czy_ostatni and oznaczenie == "NIE":
                ostrzezenia.append(
                    f"Wiersz z okresem {_fmt(w['data_startu'])}–{_fmt(w['data_konca'])} "
                    "jest oznaczony w źródle jako NIE przejściowy, ale łączysz go z "
                    "kolejnym miesiącem tej samej kampanii."
                )
            elif czy_ostatni and oznaczenie == "TAK":
                ostrzezenia.append(
                    f"Ostatni wiersz (okres {_fmt(w['data_startu'])}–{_fmt(w['data_konca'])}) "
                    "jest oznaczony w źródle jako przejściowy (TAK), czyli powinien się "
                    "przechodzić dalej — sprawdź, czy nie brakuje kolejnego wiersza "
                    "(kliknij „+ Dodaj wiersz”)."
                )
    elif len(wiersze) == 1:
        w = wiersze[0]
        if str(w.get("przejsciowa", "")).strip().upper() == "TAK":
            ostrzezenia.append(
                "Ten wiersz jest oznaczony w źródle jako przejściowy (TAK), ale "
                "wkleiłeś/aś tylko jeden miesiąc — sprawdź, czy nie brakuje kolejnego "
                "wiersza (kliknij „+ Dodaj wiersz”)."
            )

    posortowane = sorted(okresy, key=lambda o: o.data_startu)
    for poprzedni, nastepny in zip(posortowane, posortowane[1:]):
        przerwa_dni = (nastepny.data_startu - poprzedni.data_konca).days - 1
        if przerwa_dni > 1:
            ostrzezenia.append(
                f"Przerwa {przerwa_dni} dni między okresami ({_fmt(poprzedni.data_konca)} "
                f"a {_fmt(nastepny.data_startu)}) — zlecenie pokaże cały zakres dat, "
                "przerwa nie będzie na nim widoczna. Sprawdź, czy to zamierzone."
            )

    return ostrzezenia
