"""Sprawdzanie nowszej wersji na GitHubie (Releases) — tylko na żądanie
(przycisk w nagłówku), nic w tle i nic automatycznie. Otwiera stronę
pobierania w przeglądarce; appka sama się nie podmienia (uruchomiona .exe
nie może nadpisać samej siebie) - użytkownik ściąga i uruchamia instalkę
ręcznie, tak jak przy pierwszej instalacji."""
import json
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass

REPO = "mithcio/Generator-zlecen"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

# Bump przy każdym wydaniu (razem z --product-version w komendzie `flet pack`
# i z tagiem gita) - to jedyne miejsce, które appka odpytuje o samą siebie.
WERSJA_APP = "1.0.0"


@dataclass
class WynikSprawdzenia:
    dostepna_nowsza: bool
    wersja_najnowsza: str | None = None
    url_do_otwarcia: str | None = None
    blad: str | None = None


def _do_krotki(wersja: str) -> tuple[int, ...]:
    czysta = wersja.lstrip("vV")
    czesci = []
    for cz in czysta.split("."):
        cyfry = "".join(ch for ch in cz if ch.isdigit())
        czesci.append(int(cyfry) if cyfry else 0)
    return tuple(czesci)


def sprawdz() -> WynikSprawdzenia:
    try:
        req = urllib.request.Request(
            API_URL, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            dane = json.load(resp)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return WynikSprawdzenia(
                dostepna_nowsza=False,
                blad="Repozytorium nie ma jeszcze żadnego wydania (Release).",
            )
        return WynikSprawdzenia(dostepna_nowsza=False, blad=f"Błąd GitHuba: {err.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        return WynikSprawdzenia(
            dostepna_nowsza=False, blad=f"Brak połączenia z GitHubem: {err}"
        )

    tag = str(dane.get("tag_name") or "").strip()
    if not tag:
        return WynikSprawdzenia(dostepna_nowsza=False, blad="Wydanie bez numeru wersji (tag).")

    if _do_krotki(tag) <= _do_krotki(WERSJA_APP):
        return WynikSprawdzenia(dostepna_nowsza=False, wersja_najnowsza=tag)

    url = dane.get("html_url") or f"https://github.com/{REPO}/releases/latest"
    for asset in dane.get("assets") or []:
        if str(asset.get("name", "")).lower().endswith(".exe"):
            url = asset.get("browser_download_url") or url
            break

    return WynikSprawdzenia(dostepna_nowsza=True, wersja_najnowsza=tag, url_do_otwarcia=url)


def otworz_strone_pobierania(url: str) -> None:
    webbrowser.open(url)
