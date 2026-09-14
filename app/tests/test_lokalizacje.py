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


def test_czy_spakowana_appka_wykrywa_sys_frozen(monkeypatch):
    monkeypatch.setattr(lokalizacje.sys, "frozen", True, raising=False)
    assert lokalizacje.czy_spakowana_appka() is True


def test_czy_spakowana_appka_wykrywa_splaszczony_bundle_macos(monkeypatch):
    # `flet build macos` (serious_python) nie ustawia sys.frozen wcale, ale
    # w runtime rozpakowuje app/ do katalogu "serious_python_tempXXXXXXX" -
    # ten sam sygnał, którym się to wykrywa (patrz komentarz w lokalizacje.py).
    monkeypatch.delattr(lokalizacje.sys, "frozen", raising=False)
    monkeypatch.setattr(
        lokalizacje, "__file__", "/private/var/.../serious_python_tempXYZ/services/lokalizacje.py"
    )
    assert lokalizacje.czy_spakowana_appka() is True


def test_czy_spakowana_appka_false_w_devie(monkeypatch):
    monkeypatch.delattr(lokalizacje.sys, "frozen", raising=False)
    assert lokalizacje.czy_spakowana_appka() is False
