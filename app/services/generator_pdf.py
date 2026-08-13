"""Generuje PDF Zlecenia niezależnie od xlsx (reportlab), na podstawie
wspólnego układu z app/templates/zlecenie_layout.py.

Jedna tabela na całą stronę (jak w oryginalnym arkuszu Zlecenie): nagłówki
sekcji na granatowym tle, etykiety na szarym, ramki, logo Mediafarm u góry —
wizualnie spójne z generator_xlsx.py.

Polskie znaki diakrytyczne (ą, ć, ę, ł, ń, ó, ś, ź, ż) wymagają fontu TTF z
pełnym kodowaniem Unicode — wbudowane fonty bazowe reportlab (Helvetica) ich
nie obsługują poprawnie. Zamiast dołączać do repo plik fontu (Arial to font
własnościowy Microsoftu/Monotype — nie wolno go redystrybuować), szukamy w
runtime fontu już zainstalowanego w systemie użytkownika (Windows/macOS/
Linux mają go domyślnie) i rejestrujemy go w reportlab pod jego ścieżką.
"""
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.podmiot import DanePodmiotu, SpolkaMediafarm
from app.models.zlecenie import Zlecenie
from app.templates.zlecenie_layout import (
    LiniaPodpisu,
    Naglowek,
    NaglowekZIdentyfikatorem,
    Pozycja,
    Tekst,
    zbuduj_layout,
)

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo_mediafarm.png"

KOLOR_NAGLOWEK = colors.HexColor("#000080")
KOLOR_ETYKIETA = colors.HexColor("#D9D9D9")
KOLOR_RAMKI = colors.HexColor("#000000")

_KANDYDACI_REGULAR = [
    # Calibri pierwsza - to font oryginalnego szablonu Excela (i naszego
    # generator_xlsx.py) - PDF ma wyglądać spójnie z xlsx i ze starymi
    # zleceniami z Generator_zleceń_i_danych.xlsm (potwierdzone: ich PDF-y
    # eksportowane z Excela też używają Calibri, nie Arial).
    r"C:\Windows\Fonts\calibri.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/Library/Fonts/Calibri.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_KANDYDACI_BOLD = [
    r"C:\Windows\Fonts\calibrib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/Library/Fonts/Calibri Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_zarejestrowano = False


def _zarejestruj_fonty() -> None:
    """Rejestruje font systemowy z polskimi znakami, jeśli jeszcze nie
    zarejestrowany. Bez efektu (cichy fallback do Helvetica) gdy żaden z
    kandydatów nie istnieje na dysku — lepiej wygenerować PDF z ewentualnie
    zniekształconymi znakami niż nie wygenerować go wcale."""
    global _FONT_REGULAR, _FONT_BOLD, _zarejestrowano
    if _zarejestrowano:
        return
    _zarejestrowano = True

    regular = next((p for p in _KANDYDACI_REGULAR if Path(p).exists()), None)
    bold = next((p for p in _KANDYDACI_BOLD if Path(p).exists()), None)
    if regular:
        pdfmetrics.registerFont(TTFont("ZlecenieFont", regular))
        _FONT_REGULAR = "ZlecenieFont"
        if bold:
            pdfmetrics.registerFont(TTFont("ZlecenieFont-Bold", bold))
            _FONT_BOLD = "ZlecenieFont-Bold"
        else:
            _FONT_BOLD = "ZlecenieFont"


def _tekst_pdf(tekst: str) -> str:
    """reportlab Paragraph parsuje treść jako mini-XML - wolny tekst (Uwagi,
    nazwa klienta...) może zawierać &, < albo > i albo wywali generowanie,
    albo urwie tekst w miejscu takiego znaku. \n samo w sobie nic nie robi
    w Paragraph - trzeba <br/>. Escape musi być pierwszy, żeby nie zepsuć
    właśnie wstawionego <br/>."""
    znormalizowany = tekst.replace("\r\n", "\n").replace("\r", "\n")
    return _xml_escape(znormalizowany).replace("\n", "<br/>")


def generuj_pdf(
    zlecenie: Zlecenie,
    podmiot: DanePodmiotu,
    spolka: SpolkaMediafarm,
    kontakt_accounta: dict,
    sciezka: Path,
) -> Path:
    _zarejestruj_fonty()
    layout = zbuduj_layout(zlecenie, podmiot, spolka, kontakt_accounta)

    styl_naglowek = ParagraphStyle(
        "Naglowek", fontName=_FONT_BOLD, fontSize=9, leading=10.5, textColor=colors.white,
    )
    styl_identyfikator_wartosc = ParagraphStyle(
        "IdentyfikatorWartosc", fontName=_FONT_BOLD, fontSize=9, leading=10.5, textColor=colors.black,
    )
    styl_etykieta = ParagraphStyle("Etykieta", fontName=_FONT_BOLD, fontSize=8, leading=9.5)
    styl_wartosc = ParagraphStyle("Wartosc", fontName=_FONT_REGULAR, fontSize=8, leading=9.5)
    styl_tekst = ParagraphStyle("Tekst", fontName=_FONT_REGULAR, fontSize=7, leading=8.5)
    styl_podpis = ParagraphStyle(
        "Podpis", fontName=_FONT_BOLD, fontSize=8, leading=9.5, alignment=1,  # 1 = center
    )

    dane_tabeli: list[list] = []
    indeks_pieczeci: int | None = None
    style_cmds: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.5, KOLOR_RAMKI),
        ("BOX", (0, 0), (-1, -1), 1.25, KOLOR_RAMKI),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ]

    # 5 kolumn - odwzorowują dosłownie A,B,C,D,E z generator_xlsx.py (proporcje
    # szerokości kolumn xlsx: 5/35/6.13/15.4/65), żeby wiersz z identyfikatorem
    # zlecenia wyglądał tak samo jak w xlsx: "1. Dane Mediafarm" (A:B, granat),
    # "Identyfikator Zlecenia:" (C:D, granat) i sam numer (E, białe tło, bez
    # granatu) - wcześniej cały wiersz (łącznie z numerem) miał granatowe tło.
    for element in layout:
        i = len(dane_tabeli)
        if isinstance(element, NaglowekZIdentyfikatorem):
            dane_tabeli.append(
                [Paragraph(_tekst_pdf(element.tekst), styl_naglowek), "",
                 Paragraph(_tekst_pdf(element.etykieta_id), styl_naglowek), "",
                 Paragraph(_tekst_pdf(element.wartosc_id), styl_identyfikator_wartosc)]
            )
            style_cmds += [
                ("SPAN", (0, i), (1, i)),
                ("SPAN", (2, i), (3, i)),
                ("BACKGROUND", (0, i), (3, i), KOLOR_NAGLOWEK),
            ]
        elif isinstance(element, Naglowek):
            dane_tabeli.append([Paragraph(_tekst_pdf(element.tekst), styl_naglowek), "", "", "", ""])
            style_cmds += [
                ("SPAN", (0, i), (-1, i)),
                ("BACKGROUND", (0, i), (-1, i), KOLOR_NAGLOWEK),
            ]
        elif isinstance(element, Pozycja):
            etykieta = f"{element.numer} {element.etykieta}".strip()
            dane_tabeli.append(
                [Paragraph(_tekst_pdf(etykieta), styl_etykieta), "",
                 Paragraph(_tekst_pdf(element.wartosc), styl_wartosc), "", ""]
            )
            style_cmds += [
                ("SPAN", (0, i), (1, i)),
                ("SPAN", (2, i), (4, i)),
                ("BACKGROUND", (0, i), (1, i), KOLOR_ETYKIETA),
            ]
        elif isinstance(element, Tekst):
            dane_tabeli.append([Paragraph(_tekst_pdf(element.tresc), styl_tekst), "", "", "", ""])
            style_cmds.append(("SPAN", (0, i), (-1, i)))
        elif isinstance(element, LiniaPodpisu):
            # Etykiety najpierw, a puste, w pełni oprawione w ramkę miejsce na
            # pieczątkę/podpis POD nimi (jak w oryginalnym szablonie) - nie
            # nad nimi. GRID globalny już rysuje ramkę na każdej komórce, więc
            # wystarczy wymusić wysokość tego wiersza (rowHeights niżej) -
            # bez tego pusty wiersz zapada się do prawie zera wysokości.
            dane_tabeli.append(
                [Paragraph(_tekst_pdf(element.lewa), styl_podpis), "",
                 Paragraph(_tekst_pdf(element.prawa), styl_podpis), "", ""]
            )
            style_cmds += [
                ("SPAN", (0, i), (1, i)),
                ("SPAN", (2, i), (4, i)),
            ]
            indeks_pieczeci = i + 1
            dane_tabeli.append(["", "", "", "", ""])
            style_cmds.append(("SPAN", (0, indeks_pieczeci), (-1, indeks_pieczeci)))

    # Kolumny C+D nieco szersze niż czysta proporcja z xlsx (8.2+20.7mm) -
    # w tej szerokości "Identyfikator Zlecenia:" łamał się na dwie linie
    # pogrubioną czcionką 9pt; różnica odjęta z E, która ma sporo zapasu.
    wysokosci_wierszy: list[float | None] = [None] * len(dane_tabeli)
    if indeks_pieczeci is not None:
        wysokosci_wierszy[indeks_pieczeci] = 18 * mm

    tabela = Table(
        dane_tabeli,
        colWidths=[6.7 * mm, 47 * mm, 10 * mm, 30 * mm, 76.3 * mm],
        rowHeights=wysokosci_wierszy,
    )
    tabela.setStyle(TableStyle(style_cmds))

    story = []
    if LOGO_PATH.exists():
        story.append(Image(str(LOGO_PATH), width=18 * mm, height=14.5 * mm))
        story.append(Spacer(1, 1.5 * mm))
    story.append(tabela)

    sciezka.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(sciezka), pagesize=A4,
        leftMargin=14 * mm, rightMargin=14 * mm, topMargin=9 * mm, bottomMargin=9 * mm,
    )
    doc.build(story)
    return sciezka
