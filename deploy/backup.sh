#!/usr/bin/env bash
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then
  echo "Execute com sudo: sudo bash $0" >&2
  exit 1
fi
DB=/var/lib/nivus-compose/data/nivus.db
if [[ ! -s "$DB" ]]; then
  echo "Banco Nivus não encontrado em $DB" >&2
  exit 2
fi
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST=/var/backups/nivus-compose/$STAMP
install -d -m 700 "$DEST"
python3 - "$DB" "$DEST/nivus.sqlite3" <<'PY'
import sqlite3, sys
source = sqlite3.connect(sys.argv[1], timeout=30)
target = sqlite3.connect(sys.argv[2])
try:
    source.backup(target)
    check = target.execute("PRAGMA quick_check").fetchone()[0]
    if check != "ok":
        raise SystemExit(f"SQLite quick_check falhou: {check}")
finally:
    target.close()
    source.close()
PY
chmod 600 "$DEST/nivus.sqlite3"
cp -a /opt/nivus-compose/current/docker-compose.yml "$DEST/"
cp -a /opt/nivus-compose/current/.env "$DEST/"
chmod 600 "$DEST/.env"
echo "Backup SQLite consistente e configuração salvos em $DEST"
echo "Segredos não foram copiados. Mantenha este backup em armazenamento protegido."
