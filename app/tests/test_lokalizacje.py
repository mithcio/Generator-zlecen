from pathlib import Path

from app.services import lokalizacje


def test_windows(monkeypatch):
    monkeypatch.setattr(lokalizacje.sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    assert lokalizacje.katalog_danych_uzytkownika() == Path(
        r"C:\Users\test\AppData\Roaming\GeneratorZlecenMediafarm"
    )


def test_macos(monkeypatch):
    monkeypatch.setattr(lokalizacje.sys, "platform", "darwin")
    assert lokalizacje.katalog_danych_uzytkownika() == (
        Path.home() / "Library" / "Application Support" / "GeneratorZlecenMediafarm"
    )


def test_inna_platforma_ma_fallback(monkeypatch):
    monkeypatch.setattr(lokalizacje.sys, "platform", "linux")
    assert lokalizacje.katalog_danych_uzytkownika() == Path.home() / ".generatorzlecenmediafarm"
