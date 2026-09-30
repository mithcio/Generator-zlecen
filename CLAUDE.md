# Generator Zleceń — kontekst projektu

## Cel
Zastąpić VBA/Excel workflow do generowania zleceń kampanijnych lokalną
aplikacją z UI, dla sprzedawców bez zaplecza technicznego (Windows i macOS).

## Punkt wyjścia — istniejący plik Generator_zleceń_i_danych.xlsm
Zakładki: Kampania (wejście), Zlecenie (dokument klienta), Dane Traffic,
KIDOZ / Adverty / Odeeo (formatki wydawców zewnętrznych), Podmioty (dane
rozliczeniowe — istniejący dataset, nie projektujemy go od nowa).

## Wejście — interfejs (kluczowa decyzja)
NIE kopiować obecnego rozwiązania "wklej cały wiersz" jako jedynej metody.
Nowy interfejs: każde pole z osobna, do wyboru z listy rozwijanej albo do
wpisania ręcznie. Wklejenie całego wiersza to jedna z dostępnych opcji
(alternatywa dla wypełniania pól), nie jedyna droga.

Pola wg nagłówków wiersza 2 w zakładce Kampania: Nazwa Kampanii, DOM
Mediowy, Klient, Zlecający, Target, Przejściowa, Format reklamowy,
Podmiot realizujący (Sp. k./Sp. z o.o.), Uwagi, Model sprzedaży
(CPM/CPC/FF), Koszt jednostkowy, Nr_zlecenia, Budżet, Data startu,
Data końca, Liczba wyświetleń/klików/pełnych odtworzeń, Wydawca do
fakturowania, Kwota zlecona do wydawcy + kolumny statystyk.

Obsługa kampanii przejściowych: kilka wpisów (kolejne miesiące) sumowanych
w jedną zagregowaną kampanię — tak jak dziś wiersze 5–14 w Kampania
agregowane do wiersza 3.

## Wyjście
- Zlecenie klienckie (xlsx + PDF) — sekcje 1–8, pola pociągnięte formułowo
  z Kampania + lookup z Podmioty
- Dane Traffic — zestawienie pociągnięte z Zlecenie/Kampania
- Formatka wydawcy zewnętrznego — warunkowo: KIDOZ / Adverty / Odeeo

## Kluczowa decyzja projektowa — wybór wydawcy zewnętrznego
Stary plik wybiera formatkę wydawcy wyłącznie na bazie "Format reklamowy" —
to założenie już nie wystarcza, bo formaty zyskują wielu wydawców.
Nowa aplikacja ma jawnie pytać o wydawcę zewnętrznego (wielokrotny wybór:
KIDOZ / Adverty / Odeeo / brak), z podpowiedzią ze starej mapy
format→wydawca jako punktem startowym, zawsze do potwierdzenia przez
użytkownika — to krok "weryfikacja" w kreatorze.

## Podmioty (rozliczenia)
Istniejący dataset — dane per dom mediowy (pełna nazwa, adres, NIP/KRS/
REGON, termin płatności), pogrupowane wg account managera (Agnieszka/
Marta/Igor), plus dane dwóch spółek Mediafarm. Do przeniesienia jako
dataset, nie do zaprojektowania od nowa.

## Plik z kampaniami (osobny plik, dostarczy Igor)
Zawiera m.in. zakładkę Dane, do której odwołują się formuły w Kampania
(kody modelu sprzedaży, progi CPM KIDOZ) — obecnie podpięta jako
zewnętrzny link [1]Dane w Generator_zleceń_i_danych.xlsm. Do analizy po
dostarczeniu.

## Stos technologiczny (decyzja)
Python + Flet — jeden kod, GUI na Windows i macOS. Na razie wersja
lokalna, bez serwera, testowana solo. Bez płatnego podpisywania kodu
na start.

## Do zrobienia na starcie sesji w Claude Code
- Pełna analiza Generator_zleceń_i_danych.xlsm, w tym próba odczytu
  kodu VBA (do ustalenia, czy dostępne narzędzia na to pozwolą)
- Analiza pliku z kampaniami, gdy dostarczony
- MVP: jeden najczęstszy scenariusz (jeden format, bez wydawcy
  zewnętrznego) jako pierwszy krok

## Synchronizacja z GitHubem (automatyczna, tylko u właściciela - mithcio)

- **Przy otwarciu projektu** hook `SessionStart` (`.claude/hooks/git-sync.sh start`) robi `git pull` tego repo oraz repo z danymi. Jeśli hook zgłosi błąd albo nie zadziałał, zrób `git pull` sam, zanim zaczniesz pracę.
- **Przy zamknięciu sesji** hook `SessionEnd` robi commit wszystkich zmian i `git push`. Gdy użytkownik mówi, że kończy pracę, zrób od razu commit z opisowym komunikatem i push, nie czekając na hook.
- To repo (`Generator-zlecen`) jest **publiczne** i korzystają z niego inni pracownicy. Nigdy nie commituj tu danych klientów, sekretów ani plików z `.gitignore`.
- Wrażliwe dane (`źródła/`, `Cenniki_traffic/`, `app/data/*.json` z danymi klientów) są w osobnym **prywatnym** repo `mithcio/claude-generator-zlecen-claude`, które ma git-dir `.git-dane/` i jako work-tree ten sam katalog projektu. Obsługuj je poleceniem `git --git-dir=.git-dane --work-tree=. ...` (pliki dodawaj przez `add -f`, bo są w `.gitignore`). W świeżym klonie (np. w chmurze albo na telefonie) hook sam pobiera to repo. Jeśli brakuje do niego dostępu, poinformuj użytkownika, że trzeba dodać to repo do środowiska Claude.
