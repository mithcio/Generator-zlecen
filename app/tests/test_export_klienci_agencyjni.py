import json

import openpyxl

from app.services.export_seed_data import AKANCI_ARKUSZE, export_klienci_agencyjni


def test_ten_sam_klient_pod_dwiema_agencjami_trafia_pod_obie(tmp_path):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for akant in AKANCI_ARKUSZE:
        wb.create_sheet(akant)
    ws = wb["Marta Urbańska"]
    ws.append(["baner"])
    ws.append(["Nazwa", "Podmiot", "Adres", "Numery", "Termin", None, "Klient", "Agencja"])
    ws.append([None] * 6 + ["Marka", "Agencja Alfa"])
    ws.append([None] * 6 + ["Marka", "Agencja Beta"])
    ws.append([None] * 6 + ["Marka", "Agencja Beta"])  # duplikat tego samego wiersza
    ws.append([None] * 6 + ["Bez agencji", None])
    plik = tmp_path / "numery.xlsx"
    wb.save(plik)

    export_klienci_agencyjni(plik, tmp_path)

    wynik = json.loads((tmp_path / "klienci_agencyjni.json").read_text(encoding="utf-8"))
    assert wynik["Marta Urbańska"] == {"Marka": ["Agencja Alfa", "Agencja Beta"]}
