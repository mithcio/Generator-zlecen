"""Wzory przeniesione z arkusza Kampania: liczba wg modelu sprzedaży
i podział/agregacja budżetu kampanii przejściowej.
"""
from calendar import monthrange
from datetime import date

from app.models.okres import Okres

MIESIACE_PL = [
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
]

MODELE_CPM = {"CPM"}
MODELE_CPC = {"CPC"}
MODELE_FF = {"FF"}

# Etykieta pola "liczba" zależna od modelu sprzedaży — ten sam podział co w
# liczba_dla_okresu, żeby podgląd (krok 3) zawsze pasował do wzoru.
ETYKIETY_LICZBY = {
    "CPM": "Liczba wyświetleń",
    "CPC": "Liczba klików",
    "CPV": "Liczba pełnych odtworzeń",
    "FF": "Liczba (opłata stała)",
}


def etykieta_liczby(model_sprzedazy: str) -> str:
    """Etykieta dla wyliczonej liczby — dla modeli, które same nazywają się
    liczbą czegoś ("Liczba wyświetleń" itp.), etykieta to po prostu ten model."""
    return ETYKIETY_LICZBY.get(model_sprzedazy, model_sprzedazy or "Liczba")


def liczba_dla_okresu(model_sprzedazy: str, koszt_jednostkowy: float, budzet: float) -> float:
    """Odpowiednik formuły Kampania!P: liczba wyświetleń/klików/odtworzeń dla okresu.

    CPM -> budżet/koszt*1000, CPC -> budżet/koszt, FF -> 1 (opłata stała),
    pozostałe modele (CPV, Liczba wyświetleń/klików/odtworzeń) -> fallback
    budżet/koszt, tak jak w oryginalnym pliku (w praktyce niemal wszystko to CPM).
    """
    if model_sprzedazy in MODELE_FF:
        return 1.0
    if not koszt_jednostkowy:
        return 0.0
    if model_sprzedazy in MODELE_CPM:
        return budzet / koszt_jednostkowy * 1000
    return budzet / koszt_jednostkowy


def _miesiace_w_zakresie(start: date, koniec: date) -> list[tuple[date, date]]:
    """Zwraca (początek, koniec) części kampanii przypadającej na każdy
    miesiąc kalendarzowy nachodzący na [start, koniec]."""
    wyniki: list[tuple[date, date]] = []
    rok, mies = start.year, start.month
    while (rok, mies) <= (koniec.year, koniec.month):
        pierwszy = date(rok, mies, 1)
        ostatni = date(rok, mies, monthrange(rok, mies)[1])
        wyniki.append((max(start, pierwszy), min(koniec, ostatni)))
        rok, mies = (rok + 1, 1) if mies == 12 else (rok, mies + 1)
    return wyniki


def auto_podziel_budzet(budzet_total: float, data_startu: date, data_konca: date) -> list[Okres]:
    """Dzieli budżet całkowity na okresy miesięczne proporcjonalnie do liczby
    dni kampanii przypadających na dany miesiąc. Ostatni okres dorównuje sumę
    do budżetu całkowitego co do grosza (bez błędów zaokrągleń).
    """
    if data_konca < data_startu:
        raise ValueError("Data końca nie może być wcześniejsza niż data startu")

    zakresy = _miesiace_w_zakresie(data_startu, data_konca)
    total_dni = (data_konca - data_startu).days + 1

    okresy: list[Okres] = []
    suma_dotychczas = 0.0
    for i, (s, e) in enumerate(zakresy):
        dni = (e - s).days + 1
        if i == len(zakresy) - 1:
            budzet = round(budzet_total - suma_dotychczas, 2)
        else:
            budzet = round(budzet_total * dni / total_dni, 2)
            suma_dotychczas += budzet
        okresy.append(Okres(data_startu=s, data_konca=e, budzet=budzet))
    return okresy
