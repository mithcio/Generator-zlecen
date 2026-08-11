from dataclasses import dataclass
from typing import Optional


@dataclass
class DanePodmiotu:
    """Dane rozliczeniowe zlecającego (agencji lub klienta bezpośredniego),
    odczytane z app/data/podmioty.json — jeden wpis pod danym accountem.
    """

    nazwa: str
    adres_fakturowy: Optional[str]
    numery_rejestrowe: Optional[str]
    termin_platnosci: Optional[str]
    domyslny_podmiot: Optional[str] = None  # podpowiedź "Sp. k." / "Sp. z o.o.", nie wiążąca


@dataclass
class SpolkaMediafarm:
    """Dane jednej spółki Mediafarm (Sp. k. albo Sp. z o.o.)."""

    nazwa: str
    numery_rejestrowe: str
    konto_bankowe: str
    adres: str  # wspólny adres korespondencyjny obu spółek
