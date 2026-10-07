import app.main as main


def test_spakowana_appka_zapisuje_do_folderu_uzytkownika(tmp_path, monkeypatch):
    wywolania = []
    for nazwa in ("export_podmioty", "export_klienci_agencyjni",
                  "export_terminy_platnosci_klientow", "export_cennik_wydawcow"):
        monkeypatch.setattr(main, nazwa, lambda sciezka, katalog, n=nazwa: wywolania.append((n, katalog)))
    monkeypatch.setattr(main, "czy_spakowana_appka", lambda: True)
    monkeypatch.setattr(main, "katalog_danych_uzytkownika", lambda: tmp_path / "dane")

    main.odswiez_baze_klientow()

    assert len(wywolania) == 4
    assert all(katalog == tmp_path / "dane" for _, katalog in wywolania)
    assert (tmp_path / "dane").is_dir()


def test_wersja_z_kodu_zostaje_przy_app_data(monkeypatch):
    wywolania = []
    for nazwa in ("export_podmioty", "export_klienci_agencyjni",
                  "export_terminy_platnosci_klientow", "export_cennik_wydawcow"):
        monkeypatch.setattr(main, nazwa, lambda sciezka, katalog, n=nazwa: wywolania.append(katalog))
    monkeypatch.setattr(main, "czy_spakowana_appka", lambda: False)

    main.odswiez_baze_klientow()

    assert wywolania == [None, None, None, None]
