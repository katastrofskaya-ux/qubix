#!/usr/bin/env bash
# Чтение задач YouTrack (team.qubix.capital) через REST API.
# Требует переменную окружения YOUTRACK_TOKEN (permanent token, права на чтение
# проектов MARKETING / CONTENT / SALES). Токен в репозиторий не кладём.
#
#   scripts/youtrack.sh issue MARKETING-83     — одна задача с комментариями
#   scripts/youtrack.sh list CONTENT 30        — последние N задач проекта
#   scripts/youtrack.sh search "листинг"       — поиск по тексту
set -euo pipefail

BASE="${YOUTRACK_URL:-https://team.qubix.capital}"
: "${YOUTRACK_TOKEN:?нужна переменная окружения YOUTRACK_TOKEN — добавь её в секреты окружения}"

ISSUE_FIELDS='idReadable,summary,description,created,updated,project(shortName),reporter(login,fullName),customFields(name,value(name,login,fullName,presentation))'
COMMENT_FIELDS='text,created,author(login,fullName)'

api() { curl -sS --fail-with-body -H "Authorization: Bearer $YOUTRACK_TOKEN" -H 'Accept: application/json' "$@"; }

case "${1:-}" in
  issue)
    id="${2:?укажи id задачи, например MARKETING-83}"
    api "$BASE/api/issues/$id?fields=$ISSUE_FIELDS"; echo
    echo '--- комментарии ---'
    api "$BASE/api/issues/$id/comments?fields=$COMMENT_FIELDS"; echo
    ;;
  list)
    proj="${2:?укажи проект, например CONTENT}"; top="${3:-30}"
    api "$BASE/api/issues?query=$(printf 'project:%s' "$proj" | sed 's/ /%20/g')&\$top=$top&fields=$ISSUE_FIELDS"; echo
    ;;
  search)
    q="${2:?укажи запрос}"; top="${3:-30}"
    api --get --data-urlencode "query=$q" --data-urlencode "\$top=$top" --data-urlencode "fields=$ISSUE_FIELDS" "$BASE/api/issues"; echo
    ;;
  *)
    sed -n '2,10p' "$0"; exit 1;;
esac
