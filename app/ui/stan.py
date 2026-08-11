"""Stan kreatora zlecenia — żyje tylko w trakcie sesji (bez trwałego zapisu
w tym MVP), przekazywany między krokami."""
from dataclasses import dataclass, field
from datetime import date

from app.models.okres import Okres

LICZBA_KROKOW = 5


@dataclass
class StanKreatora:
    krok: int = 1
    tryb_danych: str = "formularz"  # "formularz" | "wklej"
    tryb_okresow: str = "jeden"  # "jeden" | "auto_podzial"

    account_manager: str = ""
    podmiot_realizujacy: str = ""

    nazwa_kampanii: str = ""
    dom_mediowy: str = ""
    klient: str = ""
    brand: str = ""
    zlecajacy: str = ""
    target: str = ""
    capping: str = "3"
    format_reklamowy: str = ""
    model_sprzedazy: str = "CPM"
    koszt_jednostkowy: str = ""
    nr_zlecenia: str = ""
    uwagi: str = ""

    # Numer faktycznie pobrany automatycznie z pliku Numery_zlecen_2026.xlsx
    # (krok 2) — osobne od nr_zlecenia, bo to drugie może zostać nadpisane
    # wklejeniem wiersza albo ręczną edycją. Porównanie tych dwóch pól przy
    # "Dalej" wykrywa taką rozbieżność, żeby zapytać, który numer ma
    # obowiązywać (patrz krok2_dane_kampanii._pokaz_ostrzezenie_numeru).
    nr_zlecenia_automatyczny: str | None = None

    okresy: list[Okres] = field(default_factory=list)

    # Robocze pole formularza "dodaj okres" w kroku 3 — musi żyć w stanie
    # (nie jako zmienna lokalna buduj()), inaczej ginie przy każdym odświeżeniu.
    nowy_okres_start: date | None = None
    nowy_okres_koniec: date | None = None
    nowy_okres_budzet: str = ""

    # Który kalendarz jest aktualnie otwarty ("start" / "koniec" / None) i na
    # jaki miesiąc/rok jest ustawiony — własna siatka kalendarza (app/ui/kalendarz.py)
    # zamiast natywnego DatePickera, żeby klik dnia od razu wybierał datę.
    kalendarz_pole: str | None = None
    kalendarz_rok: int = 0
    kalendarz_miesiac: int = 0

    # Jedno pole = jeden skopiowany wiersz (jeden miesiąc kampanii
    # przejściowej, zwykle z osobnej zakładki pliku kampanii). Zaczyna od
    # jednego pustego pola, "+" dokłada kolejne (limit LIMIT_WIERSZY_WKLEJANIA).
    wiersze_wklejane: list[str] = field(default_factory=lambda: [""])

    # Wynik generowania Zlecenie (xlsx+PDF) w kroku 4 — (folder, xlsx, pdf).
    # Niezależne od kroku 5 (Dane Traffic, plik generowany osobno) - każdy
    # krok generuje tylko swój własny plik/pliki.
    zlecenie_wygenerowane: tuple[str, str, str] | None = None

    # Czy krok 4 (Zlecenie) aktualnie pokazuje wiersze do wklejenia do pliku
    # z kampaniami — dostępne bez generowania zlecenia (xlsx/PDF).
    pokaz_wiersze_kampanii: bool = False

    # Krok 5 (Dane Traffic) — adnotacje dla działu traffic, osobne od
    # Zlecenie.pola.uwagi (to jest uwaga na dokumencie dla klienta, nie do
    # traffic). "Wydawcy zewnętrzni" na razie pojedynczy wybór (jeśli inny niż
    # "brak", generuje się dodatkowo IO/brief tego wydawcy razem z Dane
    # Traffic - patrz app/services/generator_wydawcy.py) -
    # PolaWspolne.wydawcy_zewnetrzni jest już listą, żeby przejście na
    # wielokrotny wybór później nie wymagało zmiany modelu, tylko UI.
    uwagi_traffic: str = ""
    link_spot: str = ""
    link_kody: str = ""
    wydawca_zewnetrzny: str = "brak"

    # Placement POKI (ImViTa/Overlay/HPTO/Rewarded/Video interaktywne) -
    # tylko gdy wydawca_zewnetrzny == "POKI", decyduje o stawce z cennika i
    # trafia na wygenerowany brief (patrz generator_wydawcy.PLACEMENTY_POKI).
    poki_placement: str = ""

    # Ścieżka ostatnio wygenerowanego pliku Dane Traffic (krok 5) —
    # niezależne od zlecenie_wygenerowane (krok 4, Zlecenie xlsx+PDF).
    ostatnia_sciezka_dane_traffic: str | None = None

    # Ścieżka ostatnio wygenerowanego pliku dla wydawcy zewnętrznego (krok 5,
    # generowane razem z Dane Traffic gdy wydawca_zewnetrzny != "brak").
    ostatnia_sciezka_wydawcy: str | None = None
