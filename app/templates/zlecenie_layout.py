"""Jedna definicja układu sekcji 1-8 dokumentu Zlecenia (etykieta -> wartość),
odwzorowująca arkusz Zlecenie!A2:D39 ze starego pliku. Używana zarówno przez
generator_xlsx.py (openpyxl), jak i generator_pdf.py (reportlab), żeby oba
wyjścia nigdy się nie rozjechały.
"""
from dataclasses import dataclass
from datetime import date

from app.models.podmiot import DanePodmiotu, SpolkaMediafarm
from app.models.zlecenie import Zlecenie
from app.services.kalkulacje import etykieta_liczby
from app.services.lookup_podmiotu import formatuj_telefon


@dataclass
class Naglowek:
    tekst: str


@dataclass
class NaglowekZIdentyfikatorem:
    """Wiersz 2 oryginału: nagłówek sekcji 1 i pole 'Identyfikator Zlecenia'
    w jednym wierszu (A:B nagłówek, C:D etykieta, E wartość)."""

    tekst: str
    etykieta_id: str
    wartosc_id: str


@dataclass
class Pozycja:
    numer: str
    etykieta: str
    wartosc: str


@dataclass
class Tekst:
    tresc: str


@dataclass
class LiniaPodpisu:
    lewa: str
    prawa: str


Wiersz = Naglowek | NaglowekZIdentyfikatorem | Pozycja | Tekst | LiniaPodpisu


def _fmt_data(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _fmt_kwota(x: float) -> str:
    s = f"{x:,.2f}".replace(",", " ").replace(".", ",")
    return f"{s} PLN"


def zbuduj_layout(
    zlecenie: Zlecenie,
    podmiot: DanePodmiotu,
    spolka: SpolkaMediafarm,
    kontakt_accounta: dict,
) -> list[Wiersz]:
    pola = zlecenie.pola

    pelna_nazwa_zlecajacego = pola.dom_mediowy if pola.dom_mediowy != "-" else pola.klient
    osoba_kontaktowa = (
        f"{pola.account_manager}; {kontakt_accounta.get('email', '')}; "
        f"{formatuj_telefon(kontakt_accounta.get('telefon'))}"
    )

    return [
        NaglowekZIdentyfikatorem("1. Dane Mediafarm", "Identyfikator Zlecenia:", pola.nr_zlecenia),
        Pozycja("1.1", "Adres siedziby do korespondencji", f"{spolka.nazwa}, {spolka.adres}"),
        Pozycja("1.2", "Bank, numer konta bankowego", spolka.konto_bankowe),
        Pozycja("1.3", "Osoba kontaktowa (tel., e-mail)", osoba_kontaktowa),
        Pozycja("1.4", "Numery rejestrowe spółki", spolka.numery_rejestrowe),
        Naglowek("2. Dane Zlecającego"),
        Pozycja("2.1", "Pełna nazwa Zlecającego", pelna_nazwa_zlecajacego),
        Pozycja("2.2", "Adres fakturowy", podmiot.adres_fakturowy or ""),
        Pozycja("2.3", "Osoba zlecająca", pola.zlecajacy),
        Pozycja("2.4", "Numery rejestrowe (NIP, KRS, REGON)", podmiot.numery_rejestrowe or ""),
        Naglowek("3. Specyfikacja Podmiotu Zlecenia"),
        Pozycja("3.1", "Klient", pola.klient),
        Pozycja("3.2", "Brand", pola.brand),
        Naglowek("4. Rodzaj usługi"),
        Pozycja("4.1", "Nazwa kampanii", pola.nazwa_kampanii),
        Pozycja("4.2", "TG", pola.target),
        Pozycja("4.3", "Capping", "brak" if pola.capping is None else str(pola.capping)),
        Pozycja("4.4", "Format reklamowy", pola.format_reklamowy),
        Pozycja(
            "4.5", etykieta_liczby(pola.model_sprzedazy),
            f"{round(zlecenie.liczba_total):,}".replace(",", " "),
        ),
        Pozycja(
            "4.6", pola.model_sprzedazy or "Koszt jednostkowy",
            _fmt_kwota(zlecenie.budzet_total if pola.model_sprzedazy == "FF" else pola.koszt_jednostkowy),
        ),
        Pozycja("4.7", "Uwagi", pola.uwagi or ""),
        Naglowek("5. Termin kampanii"),
        Pozycja("5.1", "Data rozpoczęcia", _fmt_data(zlecenie.data_startu)),
        Pozycja("5.2", "Data zakończenia", _fmt_data(zlecenie.data_konca)),
        Naglowek("6. Termin płatności"),
        Pozycja("6.1", "Dni", podmiot.termin_platnosci or ""),
        Naglowek("7. Model rozliczeń"),
        Pozycja("7.1", "Koszt netto PLN", _fmt_kwota(zlecenie.budzet_total)),
        Pozycja("7.2", "Stawka podatku VAT", "23%"),
        Pozycja("7.3", "Do zapłaty z VAT", _fmt_kwota(zlecenie.budzet_total * 1.23)),
        Tekst("Kwota brutto do zapłaty na rachunek wskazany w pkt. 1.2."),
        Naglowek("8. Akceptacja oraz podpisy zgodnie z reprezentacją podmiotów"),
        Tekst("8.1 Upoważniam Mediafarm do wystawiania faktur VAT bez podpisu odbiorcy."),
        Tekst(
            "8.2 Niniejszym oświadczam, że jestem upoważniony do podpisania niniejszego "
            "Zlecenia w imieniu Zlecającego na przedmiotową kampanię reklamową realizowaną "
            "przez Mediafarm dla Zlecającego i/lub Klienta Zlecającego (Reklamodawcy). "
            "Oświadczam, że zapoznałem/łam się z Regulaminem świadczenia usług reklamowych "
            "Mediafarm znajdującym się na stronie www.mediafarm.pl w wersji z dnia podpisania "
            "Zlecenia i Specyfikacją Techniczną, akceptuję ich postanowienia oraz potwierdzam, "
            "że są one wiążące i stanowią treść umowy zawartej z Mediafarm jako integralna "
            "część Zlecenia."
        ),
        Tekst(
            "8.3 Podpisane i opieczętowane zlecenie należy zeskanować i przesłać na adres "
            "email Account Managera reprezentującego Mediafarm, z którym uzgadniane są "
            f"warunki zlecenia: {kontakt_accounta.get('email', '')}"
        ),
        Tekst(f"Data: ______________ / ___________ / {date.today().year} r."),
        LiniaPodpisu("Podpis i pieczęć Mediafarm", "Podpis i pieczęć Zlecającego"),
    ]
