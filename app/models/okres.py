from dataclasses import dataclass
from datetime import date


@dataclass
class Okres:
    """Jeden okres rozliczeniowy kampanii (zwykle miesiąc): budżet + daty.

    Kilka okresów pod jedną kampanią = kampania przejściowa.
    """

    data_startu: date
    data_konca: date
    budzet: float
    # Liczba wyświetleń/klików/odtworzeń ze źródłowego pliku kampanii (jeśli
    # wklejony wiersz ją zawierał) — trzymana tylko do porównania z liczbą
    # przeliczoną przez aplikację z budżetu i modelu sprzedaży, nigdy nie jest
    # używana do żadnych obliczeń w generatorze.
    liczba_zrodlowa: float | None = None

    def liczba_dni(self) -> int:
        return (self.data_konca - self.data_startu).days + 1
