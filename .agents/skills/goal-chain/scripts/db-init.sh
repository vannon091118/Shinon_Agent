#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# db-init.sh — Initialize the TID state database
# Creates .agents/skills/goal-chain/db/tid-state.db with schema
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOAL_CHAIN_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="${GOAL_CHAIN_DIR}/db/tid-state.db"
SCHEMA="${GOAL_CHAIN_DIR}/db/schema.sql"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  TID State Database — Initialisierung                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ -f "$DB_PATH" ]]; then
    echo "⚠️  Datenbank existiert bereits: $DB_PATH"
    echo "   Überschreiben..."
    rm "$DB_PATH"
    echo "   Alte DB gelöscht."
fi

if command -v sqlite3 &>/dev/null; then
    sqlite3 "$DB_PATH" < "$SCHEMA"
    echo "✅ Datenbank erstellt (sqlite3): $DB_PATH"
else
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
with open('$SCHEMA') as f:
    conn.executescript(f.read())
conn.commit()
conn.close()
print('✅ Datenbank erstellt (python3): $DB_PATH')
"
fi

# Verify
echo ""
echo "Schema-Tabellen:"
if command -v sqlite3 &>/dev/null; then
    sqlite3 "$DB_PATH" ".tables"
else
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()
for t in tables:
    print(' ', t[0])
conn.close()
"
fi

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  DB bereit. Nutze dispatch.sh um einen neuen Run zu starten."
echo "══════════════════════════════════════════════════════════"
