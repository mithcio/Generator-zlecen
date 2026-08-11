from dataclasses import dataclass, field
from datetime import date

from app.models.kampania import PolaWspolne
from app.models.okres import Okres


@dataclass
class Zlecenie:
    """Zlecenie = pola wspólne kampanii + jeden lub więcej okresów.

    >1 okres = kampania przejściowa. Agregaty (budżet, daty, liczba) liczone
    z okresów — logika w app/services/kalkulacje.py, tu tylko delegacja,
    żeby wzór SUM/MIN/MAX/liczba-wg-modelu żył w jednym miejscu.
    """

    pola: PolaWspolne
    okresy: list[Okres] = field(default_factory=list)

    @property
    def przejsciowa(self) -> bool:
        return len(self.okresy) > 1

    @property
    def budzet_total(self) -> float:
        return sum(o.budzet for o in self.okresy)

    @property
    def data_startu(self) -> date:
        return min(o.data_startu for o in self.okresy)

    @property
    def data_konca(self) -> date:
        return max(o.data_konca for o in self.okresy)

    @property
    def liczba_total(self) -> float:
        from app.services.kalkulacje import liczba_dla_okresu

        return sum(
            liczba_dla_okresu(self.pola.model_sprzedazy, self.pola.koszt_jednostkowy, o.budzet)
            for o in self.okresy
        )
