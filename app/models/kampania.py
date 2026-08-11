from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PolaWspolne:
    """Pola kampanii wspólne dla wszystkich okresów (miesięcy) danego zlecenia.

    Odpowiednik nagłówków z arkusza Kampania (wiersz 2), pomniejszony o pola,
    które w kampanii przejściowej różnią się per okres (budżet, daty) — te
    żyją w Okres, nie tutaj.
    """

    account_manager: str
    podmiot_realizujacy: str  # "Sp. k." / "Sp. z o.o." — determinuje spółkę Mediafarm i prefiks numeru
    nr_zlecenia: str

    nazwa_kampanii: str
    dom_mediowy: str  # pełna nazwa agencji — klucz lookupu w Podmioty; "-" jeśli klient zleca bezpośrednio
    klient: str
    brand: str
    zlecajacy: str  # osoba kontaktowa po stronie zlecającego

    target: str
    capping: Optional[int]  # None = "brak"
    format_reklamowy: str
    model_sprzedazy: str
    koszt_jednostkowy: float

    uwagi: str = ""
    wydawcy_zewnetrzni: list = field(default_factory=list)  # placeholder — nie budowane w tym kroku
