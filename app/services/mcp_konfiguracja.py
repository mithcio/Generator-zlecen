"""Przełącznik „Uruchom MCP dla Claude” (Ustawienia) = obecność wpisu w
konfiguracji Claude Desktop (claude_desktop_config.json). Claude Desktop sam
uruchamia serwer z tego wpisu przy swoim starcie (`GeneratorZlecen.exe --mcp`),
więc bez wpisu nic nie chodzi w tle - na komputerach, gdzie przełącznik jest
wyłączony (domyślnie), nie dzieje się nic. Zmiana wymaga restartu Claude Desktop."""
import json
import os
import sys
from pathlib import Path

NAZWA_WPISU = "generator-zlecen"


class BladKonfiguracjiClaude(Exception):
    """Brak Claude Desktop albo uszkodzony plik konfiguracji - do poprawienia
    przez użytkownika, nie błąd programu."""


def obslugiwane() -> bool:
    # macOS (`flet build macos`) nie ma wykonywalnego pliku, któremu da się
    # podać --mcp; Android/iOS tym bardziej.
    return sys.platform == "win32"


def sciezka_konfiguracji() -> Path:
    return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"


def _wpis() -> dict:
    if getattr(sys, "frozen", False):
        return {"command": sys.executable, "args": ["--mcp"]}
    korzen = Path(__file__).resolve().parent.parent.parent
    return {"command": sys.executable, "args": ["-m", "app.main", "--mcp"], "env": {"PYTHONPATH": str(korzen)}}


def _wczytaj(sciezka: Path) -> dict:
    if not sciezka.exists():
        if not sciezka.parent.exists():
            raise BladKonfiguracjiClaude(f"Nie znaleziono Claude Desktop (brak folderu {sciezka.parent}).")
        return {}
    try:
        return json.loads(sciezka.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as err:
        raise BladKonfiguracjiClaude(f"Plik {sciezka} nie jest poprawnym JSON-em ({err}) - nie ruszam go.") from err


def czy_wlaczony(sciezka: Path | None = None) -> bool:
    sciezka = sciezka or sciezka_konfiguracji()
    try:
        return NAZWA_WPISU in _wczytaj(sciezka).get("mcpServers", {})
    except BladKonfiguracjiClaude:
        return False


def ustaw(wlaczony: bool, sciezka: Path | None = None) -> None:
    sciezka = sciezka or sciezka_konfiguracji()
    konfiguracja = _wczytaj(sciezka)
    serwery = konfiguracja.setdefault("mcpServers", {})
    if wlaczony:
        serwery[NAZWA_WPISU] = _wpis()
    else:
        serwery.pop(NAZWA_WPISU, None)
        if not serwery:
            konfiguracja.pop("mcpServers")
    tymczasowy = sciezka.with_suffix(".tmp")
    tymczasowy.write_text(json.dumps(konfiguracja, ensure_ascii=False, indent=2), encoding="utf-8")
    tymczasowy.replace(sciezka)


def odswiez_sciezke(sciezka: Path | None = None) -> None:
    """Po przeniesieniu/aktualizacji appki do innego folderu wpis wskazywałby
    stary plik - przy starcie poprawiamy go, ale tylko gdy już jest włączony."""
    sciezka = sciezka or sciezka_konfiguracji()
    if czy_wlaczony(sciezka) and _wczytaj(sciezka)["mcpServers"][NAZWA_WPISU] != _wpis():
        ustaw(True, sciezka)
