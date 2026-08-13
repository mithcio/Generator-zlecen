from datetime import date

from app.models.kampania import PolaWspolne
from app.models.okres import Okres
from app.models.zlecenie import Zlecenie
from app.services import lookup_podmiotu as lp
from app.services.generator_pdf import _tekst_pdf, generuj_pdf


def test_tekst_pdf_zamienia_nowa_linie_na_br():
    assert _tekst_pdf("Linia 1\nLinia 2") == "Linia 1<br/>Linia 2"


def test_tekst_pdf_normalizuje_crlf():
    assert _tekst_pdf("Linia 1\r\nLinia 2\rLinia 3") == "Linia 1<br/>Linia 2<br/>Linia 3"


def test_tekst_pdf_escapuje_znaki_specjalne_xml():
    # reportlab Paragraph parsuje treść jako mini-XML - & < > bez escape'owania
    # albo wywalają generowanie, albo urywają tekst w tym miejscu.
    assert _tekst_pdf("Procter & Gamble") == "Procter &amp; Gamble"
    assert _tekst_pdf("Cena < 50 zł > rabat") == "Cena &lt; 50 zł &gt; rabat"


def test_tekst_pdf_escape_przed_br_nie_psuje_tagu():
    # Kolejność ma znaczenie: escape najpierw, potem wstawienie <br/> -
    # inaczej sam wstawiony tag zostałby zamieniony na &lt;br/&gt;.
    wynik = _tekst_pdf("A & B\nC < D")
    assert "<br/>" in wynik
    assert "&lt;br/&gt;" not in wynik


def _przykladowe_zlecenie(uwagi):
    pola = PolaWspolne(
        account_manager="Igor Samul",
        podmiot_realizujacy="Sp. k.",
        nr_zlecenia="K/2026/077",
        nazwa_kampanii="Test",
        dom_mediowy="Initiative Media Warszawa sp. z o.o.",
        klient="Colian",
        brand="Hellena",
        zlecajacy="Paulina Kowalik",
        target="KIDS",
        capping=3,
        format_reklamowy="In-game audio KIDS",
        model_sprzedazy="CPM",
        koszt_jednostkowy=26,
        uwagi=uwagi,
    )
    okresy = [Okres(date(2026, 7, 1), date(2026, 7, 31), 1000.0)]
    return Zlecenie(pola=pola, okresy=okresy)


def test_generuj_pdf_z_wieloliniowymi_i_specjalnymi_uwagami_nie_wybucha(tmp_path):
    # Regresja: surowy tekst z & albo \n wysłany prosto do reportlab
    # Paragraph potrafił wywalić generowanie PDF-a.
    zlecenie = _przykladowe_zlecenie("Linia 1\nLinia 2 z & i < znakami")
    podmiot = lp.znajdz_podmiot(zlecenie.pola.account_manager, zlecenie.pola.dom_mediowy)
    spolka = lp.spolka_mediafarm(zlecenie.pola.podmiot_realizujacy)
    kontakt = lp.kontakt_accounta(zlecenie.pola.account_manager)

    sciezka = generuj_pdf(zlecenie, podmiot, spolka, kontakt, tmp_path / "Zlecenie_test.pdf")
    assert sciezka.exists()
    assert sciezka.stat().st_size > 0
