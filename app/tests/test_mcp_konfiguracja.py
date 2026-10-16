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
