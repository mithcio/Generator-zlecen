from dataclasses import dataclass


@dataclass
class DaneTraffic:
    """Adnotacje dla działu traffic, osobne od pól klienckiego Zlecenia
    (Zlecenie.pola.uwagi to co innego — uwagi do dokumentu dla klienta).

    Reszta danych traffic (osoba kontaktowa, model sprzedaży, capping,
    format, spółka, terminy, liczba wyświetleń/klików per miesiąc) już
    istnieje w Zlecenie — nie duplikujemy jej tutaj.
    """

    uwagi_traffic: str = ""
    link_spot: str = ""
    link_kody: str = ""
