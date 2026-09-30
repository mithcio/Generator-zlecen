#!/usr/bin/env bash
# Automatyczna synchronizacja z GitHubem, wołana przez hooki w .claude/settings.json:
#   start - git pull przy otwarciu sesji Claude
#   end   - commit wszystkich zmian + push przy zamknięciu sesji
# Działa tylko u właściciela (mithcio) - pozostali użytkownicy publicznego repo
# nie dostają automatycznych commitów/pushy.
#
# Wrażliwe dane (źródła/, Cenniki_traffic/, app/data/*.json z danymi klientów)
# są w osobnym PRYWATNYM repo mithcio/claude-generator-zlecen-claude. Jego git-dir
# to .git-dane/, work-tree to katalog projektu. Do publicznego repo nie trafiają.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0
case "$(git config user.email)" in
  *mithcio*) ;;
  *) [ -n "$CLAUDE_CODE_REMOTE" ] || exit 0 ;;
esac

DANE_URL="https://github.com/mithcio/claude-generator-zlecen-claude.git"
DANE_PATHS=(źródła Cenniki_traffic
  app/data/podmioty.json app/data/mediafarm.json app/data/numeracja.json
  app/data/klienci_agencyjni.json app/data/terminy_platnosci_klientow.json
  app/data/cennik_wydawcow.json)
dane() { git --git-dir=.git-dane --work-tree=. "$@"; }

# Brak lokalnego repo z danymi (np. świeży klon w chmurze) - pobierz je.
if [ ! -d .git-dane ]; then
  if git clone -q --bare "$DANE_URL" .git-dane >/dev/null 2>&1; then
    dane config core.bare false
    dane config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'
    dane config status.showUntrackedFiles no
    dane config core.autocrlf false
    dane config core.longpaths true
    dane fetch -q origin && dane branch -q -u origin/main main
    dane checkout -q -f main -- .
  else
    echo "git-sync: brak dostępu do prywatnego repo z danymi ($DANE_URL) - dane klientów niedostępne w tej sesji."
  fi
fi

case "$1" in
  start)
    if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
      git pull --rebase --autostash -q >/dev/null 2>&1 \
        || echo "git-sync: git pull nie powiódł się - sprawdź 'git status' przed rozpoczęciem pracy."
    fi
    [ -d .git-dane ] && { dane pull --rebase -q >/dev/null 2>&1 \
      || echo "git-sync: pull repo z danymi (.git-dane) nie powiódł się."; }
    ;;
  end)
    if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
      git add -A
      git diff --cached --quiet || git commit -q -m "Auto-commit po sesji Claude ($(date '+%Y-%m-%d %H:%M'))"
      git push -q >/dev/null 2>&1
    fi
    if [ -d .git-dane ]; then
      dane add -A -f -- "${DANE_PATHS[@]}" 2>/dev/null
      dane diff --cached --quiet || dane commit -q -m "Auto-commit danych po sesji Claude ($(date '+%Y-%m-%d %H:%M'))"
      dane push -q >/dev/null 2>&1
    fi
    ;;
esac
exit 0
