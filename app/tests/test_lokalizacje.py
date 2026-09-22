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
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    assert lokalizacje.katalog_danych_uzytkownika() == Path.home() / ".generatorzlecenmediafarm"


def test_android_uzywa_katalogu_ze_zmiennej_fleta(monkeypatch):
    # Android (i iOS) nie mają odpowiednika %APPDATA%/Application Support, a
    # Path.home() w piaskownicy appki jest nieprzewidywalna i tak czy inaczej
    # niedostępna z poziomu zwykłego menedżera plików bez roota - Flet sam
    # ustawia tę zmienną w runtime na trwały, zapisywalny katalog appki
    # (patrz flet.controls.services.storage_paths), więc ma pierwszeństwo
    # przed zgadywaniem ścieżki po sys.platform.
    monkeypatch.setattr(lokalizacje.sys, "platform", "linux")
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", "/data/user/0/com.mediafarm.generatorzlecen/app_flutter/data")
    assert lokalizacje.katalog_danych_uzytkownika() == Path(
        "/data/user/0/com.mediafarm.generatorzlecen/app_flutter/data/GeneratorZlecenMediafarm"
    )


def test_czy_spakowana_appka_wykrywa_sys_frozen(monkeypatch):
    monkeypatch.setattr(lokalizacje.sys, "frozen", True, raising=False)
    assert lokalizacje.czy_spakowana_appka() is True


def test_czy_spakowana_appka_wykrywa_bundle_macos(monkeypatch):
    # `flet build macos` (serious_python) nie ustawia sys.frozen wcale - w
    # runtime appka dziala z main.pyc wewnatrz samego .app bundla, sciezka
    # potwierdzona diagnostyka z realnego Maca (patrz komentarz w
    # lokalizacje.py).
    monkeypatch.delattr(lokalizacje.sys, "frozen", raising=False)
    monkeypatch.setattr(
        lokalizacje,
        "__file__",
        "/Applications/Generator Zlecen.app/Contents/Resources/"
        "serious_python_darwin_serious_python_darwin.bundle/Contents/Resources/"
        "app/services/lokalizacje.pyc",
    )
    assert lokalizacje.czy_spakowana_appka() is True


def test_czy_spakowana_appka_wykrywa_tymczasowy_katalog_kompilacji(monkeypatch):
    monkeypatch.delattr(lokalizacje.sys, "frozen", raising=False)
    monkeypatch.setattr(
        lokalizacje, "__file__", "/private/var/.../serious_python_tempXYZ/services/lokalizacje.py"
    )
    assert lokalizacje.czy_spakowana_appka() is True


def test_czy_spakowana_appka_false_w_devie(monkeypatch):
    monkeypatch.delattr(lokalizacje.sys, "frozen", raising=False)
    assert lokalizacje.czy_spakowana_appka() is False
