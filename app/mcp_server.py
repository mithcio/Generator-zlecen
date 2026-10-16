"""Serwer MCP (stdio) dla Claude Desktop: wystawianie zleceń z czatu na
podstawie maila/xlsx. Uruchamiany przez Claude Desktop jako `GeneratorZlecen.exe
--mcp` (patrz app/services/mcp_konfiguracja.py i przełącznik w Ustawieniach) -
nie działa w tle sam z siebie. Cała logika w app/services/wystawianie.py."""
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from app.services import wystawianie

mcp = FastMCP("generator-zlecen")


class OkresIn(BaseModel):
    start: str = Field(description="Data startu okresu, RRRR-MM-DD albo DD.MM.RRRR")
    koniec: str = Field(description="Data końca okresu (ten sam miesiąc co start; dłuższy zakres zostanie podzielony na miesiące)")
    budzet: float = Field(description="Budżet netto okresu w PLN")


class ZlecenieIn(BaseModel):
    podmiot_realizujacy: str = Field(description='"Sp. k." (agencja) albo "Sp. z o.o." (klient bezpośredni)')
    nazwa_kampanii: str
    dom_mediowy: str = Field(description='Pełna nazwa agencji dokładnie jak w bazie (sprawdź słownikiem); dla "Sp. z o.o." można pominąć')
    klient: str
    brand: str = ""
    zlecajacy: str = Field(description="Osoba zlecająca po stronie klienta/agencji")
    target: str = Field(description="KIDS / ADULTS / SILVER")
    format_reklamowy: str
    model_sprzedazy: str = Field(description="CPM / CPC / FF ...")
    koszt_jednostkowy: float | None = Field(default=None, description="Pomiń dla FF")
    capping: int | str | None = Field(default=None, description='Liczba albo "brak"')
    okresy: list[OkresIn]
    account_manager: str = Field(default="", description="Pomiń, by użyć domyślnego z Ustawień")
    uwagi: str = Field(default="", description="Uwagi na zleceniu dla klienta (pole 4.7)")
    nr_zlecenia: str = Field(default="", description="Pomiń, by nadać numer automatycznie (rezerwacja w pliku Numery_zlecen)")
    wydawca_zewnetrzny: str = "brak"
    poki_placement: str = ""
    uwagi_traffic: str = ""
    link_spot: str = ""
    link_kody: str = ""
    dane_traffic: bool = Field(default=True, description="Czy wygenerować też plik Dane Traffic (i plik wydawcy)")


@mcp.tool()
def slowniki_i_podmioty(fraza: str = "", account_manager: str = "") -> dict:
    """Dozwolone wartości pól (account, formaty, targety, modele, wydawcy) oraz,
    gdy podasz frazę (np. "Starcom"), pasujące agencje/klienci z bazy podmiotów.
    Wołaj przed podglądem, żeby wpisać nazwy dokładnie jak w bazie."""
    return wystawianie.slowniki_i_podmioty(fraza, account_manager)


@mcp.tool()
def podglad_zlecenia(zlecenie: ZlecenieIn) -> dict:
    """Waliduje dane i pokazuje podsumowanie (budżet, liczba, daty, format na
    zleceniu, ostrzeżenia). NIC nie zapisuje i nie pobiera numeru - zawsze
    pokaż to użytkownikowi przed wystawieniem."""
    return wystawianie.podglad(zlecenie.model_dump())


@mcp.tool()
def wystaw_zlecenie(zlecenie: ZlecenieIn) -> dict:
    """Wystawia zlecenie: rezerwuje numer w Numery_zlecen_2026.xlsx, generuje
    Zlecenie (xlsx+PDF), opcjonalnie Dane Traffic i plik wydawcy, zwraca ścieżki
    i wiersze do wklejenia do pliku kampanii. Woła się dopiero po akceptacji
    podglądu przez użytkownika."""
    return wystawianie.wystaw(zlecenie.model_dump())


def uruchom() -> None:
    mcp.run()
