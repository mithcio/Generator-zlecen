import json

import pytest

from app.services import mcp_konfiguracja as mk


def test_wlacz_dopisuje_wpis_i_zachowuje_reszte_konfiguracji(tmp_path):
    plik = tmp_path / "claude_desktop_config.json"
    plik.write_text(json.dumps({"theme": "dark", "mcpServers": {"inny": {"command": "x"}}}), encoding="utf-8")

    mk.ustaw(True, plik)

    dane = json.loads(plik.read_text(encoding="utf-8"))
    assert dane["theme"] == "dark"
    assert dane["mcpServers"]["inny"] == {"command": "x"}
    assert dane["mcpServers"][mk.NAZWA_WPISU]["command"]
    assert mk.czy_wlaczony(plik) is True


def test_wylacz_usuwa_tylko_nasz_wpis(tmp_path):
    plik = tmp_path / "claude_desktop_config.json"
    plik.write_text(json.dumps({"mcpServers": {"inny": {"command": "x"}}}), encoding="utf-8")
    mk.ustaw(True, plik)

    mk.ustaw(False, plik)

    assert json.loads(plik.read_text(encoding="utf-8")) == {"mcpServers": {"inny": {"command": "x"}}}
    assert mk.czy_wlaczony(plik) is False


def test_wylaczenie_ostatniego_wpisu_usuwa_pusty_mcpservers(tmp_path):
    plik = tmp_path / "claude_desktop_config.json"
    mk.ustaw(True, plik)
    mk.ustaw(False, plik)
    assert json.loads(plik.read_text(encoding="utf-8")) == {}


def test_uszkodzony_json_nie_jest_nadpisywany(tmp_path):
    plik = tmp_path / "claude_desktop_config.json"
    plik.write_text("{to nie jest json", encoding="utf-8")
    with pytest.raises(mk.BladKonfiguracjiClaude):
        mk.ustaw(True, plik)
    assert plik.read_text(encoding="utf-8") == "{to nie jest json"


def test_brak_claude_desktop_to_czytelny_blad(tmp_path):
    with pytest.raises(mk.BladKonfiguracjiClaude):
        mk.ustaw(True, tmp_path / "nie_ma_takiego_folderu" / "claude_desktop_config.json")


def test_odswiez_sciezke_poprawia_przestarzaly_wpis_tylko_gdy_wlaczony(tmp_path):
    plik = tmp_path / "claude_desktop_config.json"
    mk.odswiez_sciezke(plik)  # wyłączony - nic nie tworzy
    assert not plik.exists()

    plik.write_text(json.dumps({"mcpServers": {mk.NAZWA_WPISU: {"command": "C:/stary/GeneratorZlecen.exe"}}}), encoding="utf-8")
    mk.odswiez_sciezke(plik)
    assert json.loads(plik.read_text(encoding="utf-8"))["mcpServers"][mk.NAZWA_WPISU] == mk._wpis()


def test_sciezka_preferuje_claude_desktop_ze_store(tmp_path, monkeypatch):
    store = tmp_path / "Packages" / "Claude_abc123" / "LocalCache" / "Roaming" / "Claude"
    store.mkdir(parents=True)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert mk.sciezka_konfiguracji() == store / "claude_desktop_config.json"


def test_sciezka_bez_store_to_klasyczny_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert mk.sciezka_konfiguracji() == tmp_path / "Roaming" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_dziala_false_gdy_powershell_nie_zwraca_procesow(monkeypatch):
    import subprocess

    def fake_run(*a, **k):
        return subprocess.CompletedProcess(a, 0, stdout="0\n", stderr="")

    monkeypatch.setattr(mk.subprocess, "run", fake_run)
    monkeypatch.setattr(mk.sys, "platform", "win32")
    assert mk.claude_desktop_dziala() is False


def test_claude_desktop_dziala_true_gdy_jest_proces_desktopowy(monkeypatch):
    import subprocess

    monkeypatch.setattr(
        mk.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="3\n", stderr="")
    )
    monkeypatch.setattr(mk.sys, "platform", "win32")
    assert mk.claude_desktop_dziala() is True
