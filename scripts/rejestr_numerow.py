"""Ręczna obsługa rejestru numerów (Numery_zlecen_2026.xlsx) poza oknem
generatora - te same funkcje i te same zabezpieczenia co w app/services/
numeracja.py (zapis potwierdzany odczytem, numer zajęty przez kogoś innego
= błąd). Do użycia, gdy zlecenia wystawia się innym torem niż kreator, np.
z czatu przez MCP: najpierw `zajmij` w prawdziwym rejestrze, dopiero potem
wystawienie z tym numerem.

  python scripts/rejestr_numerow.py status  --rejestr <plik>
  python scripts/rejestr_numerow.py nastepny --rejestr <plik> --podmiot "Sp. z o.o." --account "Igor Samul"
  python scripts/rejestr_numerow.py zajmij  --rejestr <plik> --podmiot "Sp. k." --numer K/2026/106 --account "Igor Samul"

`status` tylko czyta. `nastepny` rezerwuje pierwszy wolny numer, `zajmij`
rezerwuje wskazany. Ustawienia aplikacji nie są ruszane (ścieżka rejestru
trafia do tymczasowego pliku ustawień)."""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import numeracja, ustawienia  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("komenda", choices=["status", "nastepny", "zajmij"])
    ap.add_argument("--rejestr", required=True, help="ścieżka do Numery_zlecen_2026.xlsx")
    ap.add_argument("--podmiot", choices=list(numeracja.KOLUMNY), help="Sp. k. (K/...) albo Sp. z o.o. (S/...)")
    ap.add_argument("--numer", help="numer do zarezerwowania, np. S/2026/084 albo S-2026-084")
    ap.add_argument("--account", default="Igor Samul")
    args = ap.parse_args(argv)

    ustawienia.DATA_PLIK = Path(tempfile.mkdtemp()) / "ustawienia.json"
    ustawienia.zapisz(sciezka_numery_zlecen=args.rejestr)

    try:
        if args.komenda == "status":
            wynik = numeracja.stan_rejestru()
        elif args.komenda == "nastepny":
            if not args.podmiot:
                ap.error("nastepny wymaga --podmiot")
            wynik = {"zarezerwowano": numeracja.zarezerwuj_numer(args.podmiot, args.account), "plik": args.rejestr}
        else:
            if not (args.podmiot and args.numer):
                ap.error("zajmij wymaga --podmiot i --numer")
            nowy = numeracja.zajmij_numer(args.numer, args.podmiot, args.account)
            wynik = {"numer": args.numer, "zarezerwowano_teraz": nowy, "plik": args.rejestr}
    except numeracja.BladNumeracji as err:
        print(f"BLAD: {err}", file=sys.stderr)
        return 1
    print(json.dumps(wynik, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
