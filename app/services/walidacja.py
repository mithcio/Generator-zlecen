"""Centralny punkt reguł walidacji z czytelnymi komunikatami po polsku —
używany zarówno przy wypełnianiu formularza, jak i po sparsowaniu wklejonych
wierszy. Zwraca listę czytelnych komunikatów zamiast wybuchać wyjątkiem, żeby
UI mogło pokazać je wszystkie naraz w jednym dialogu.
"""
from app.models.kampania import PolaWspolne
from app.models.okres import Okres
from app.models.zlecenie import Zlecenie

ETYKIETY = {
    "account_manager": "Account manager",
    "podmiot_realizujacy": "Podmiot realizujący",
    "nr_zlecenia": "Numer zlecenia",
    "nazwa_kampanii": "Nazwa kampanii",
    "dom_mediowy": "DOM Mediowy",
    "klient": "Klient",
    "brand": "Brand",
    "zlecajacy": "Zlecający",
    "target": "Target",
    "format_reklamowy": "Format reklamowy",
    "model_sprzedazy": "Model sprzedaży",
    "koszt_jednostkowy": "Koszt jednostkowy",
}

WYMAGANE_POLA_WSPOLNE = [
    "account_manager",
    "podmiot_realizujacy",
    "nr_zlecenia",
    "nazwa_kampanii",
    "dom_mediowy",
    "klient",
    "zlecajacy",
    "target",
    "format_reklamowy",
    "model_sprzedazy",
]


def _brak(pole: str) -> str:
    return f"To pole jest wymagane: {ETYKIETY.get(pole, pole)}."


def waliduj_pola_wspolne(pola: PolaWspolne) -> list[str]:
    bledy = []
    for pole in WYMAGANE_POLA_WSPOLNE:
        if not getattr(pola, pole, None):
            bledy.append(_brak(pole))
    # FF (opłata stała) nie ma kosztu jednostkowego — cały budżet to jedna opłata.
    if pola.model_sprzedazy != "FF" and (pola.koszt_jednostkowy is None or pola.koszt_jednostkowy <= 0):
        bledy.append("Koszt jednostkowy musi być liczbą większą od zera.")
    if pola.capping is not None and pola.capping < 0:
        bledy.append("Capping nie może być liczbą ujemną.")
    return bledy


def waliduj_okres(okres: Okres, etykieta: str | None = None) -> list[str]:
    prefiks = f"{etykieta}: " if etykieta else ""
    bledy = []
    if okres.data_konca < okres.data_startu:
        bledy.append(f"{prefiks}Data końca nie może być wcześniejsza niż data startu.")
    elif (okres.data_startu.year, okres.data_startu.month) != (okres.data_konca.year, okres.data_konca.month):
        # Jeden okres = jeden wiersz w jednej zakładce miesięcznej pliku
        # kampanii (patrz eksport_wiersza.py) - okres rozciągnięty na dwa
        # miesiące nie ma tam gdzie trafić. Kampania na więcej niż miesiąc
        # to kilka okresów (kampania przejściowa), nie jeden szerszy okres.
        bledy.append(
            f"{prefiks}Okres musi mieścić się w jednym miesiącu (start i koniec w tym "
            "samym miesiącu) - kampanię na więcej miesięcy podziel na kilka okresów, "
            "po jednym na miesiąc (użyj „Rozbij automatycznie na miesiące”)."
        )
    if okres.budzet is None or okres.budzet <= 0:
        bledy.append(f"{prefiks}Budżet musi być liczbą większą od zera.")
    return bledy


def waliduj_zlecenie(zlecenie: Zlecenie) -> list[str]:
    bledy = list(waliduj_pola_wspolne(zlecenie.pola))
    if not zlecenie.okresy:
        bledy.append("Dodaj przynajmniej jeden okres (budżet + daty startu/końca).")
    for i, okres in enumerate(zlecenie.okresy, start=1):
        etykieta = f"Okres {i}" if len(zlecenie.okresy) > 1 else None
        bledy.extend(waliduj_okres(okres, etykieta))
    return bledy
