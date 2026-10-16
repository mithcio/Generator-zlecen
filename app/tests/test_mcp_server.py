import asyncio

import pytest

pytest.importorskip("mcp")

from app import mcp_server  # noqa: E402


def test_serwer_wystawia_trzy_narzedzia():
    nazwy = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert nazwy == {"slowniki_i_podmioty", "podglad_zlecenia", "wystaw_zlecenie"}
