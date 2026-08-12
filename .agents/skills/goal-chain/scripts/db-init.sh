#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# db-init.sh — Initialize the TID state database
#
# DB location (priority order):
#   1. $SHINON_GOALCHAIN_DB  (install.py sets this to the CENTRAL
#      $SHINON_HOME/data/goal-chain/tid-state.db so all data lives
#      in one place instead of scattered across the repo)
#   2. fallback: .agents/skills/goal-chain/db/tid-state.db (standalone)
#
# IDEMPOTENT: schema.sql only uses CREATE TABLE IF NOT EXISTS, so this
# script NEVER deletes an existing DB. Re-running it preserves all TIDs.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOAL_CHAIN_DIR="$(dirname "$SCRIPT_DIR")"
SCHEMA="${GOAL_CHAIN_DIR}/db/schema.sql"

if [[ -n "${SHINON_GOALCHAIN_DB:-}" ]]; then
    DB_PATH="${SHINON_GOALCHAIN_DB}"
else
    DB_PATH="${GOAL_CHAIN_DIR}/db/tid-state.db"
fi

mkdir -p "$(dirname "$DB_PATH")"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  TID State Database — Initialisierung                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

if [[ -f "$DB_PATH" ]]; then
    echo "ℹ️  Datenbank existiert bereits: $DB_PATH"
    echo "   Schema wird idempotent angewendet (kein Löschen)."
else
    echo "ℹ️  Erstelle neue Datenbank: $DB_PATH"
fi

# Apply schema idempotently (schema.sql uses CREATE TABLE IF NOT EXISTS).
# Use sqlite3 CLI if present, else python3 stdlib.
if command -v sqlite3 &>/dev/null; then
    sqlite3 "$DB_PATH" < "$SCHEMA"
else
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
with open('$SCHEMA') as f:
    conn.executescript(f.read())
conn.commit()
conn.close()
"
fi

echo "✅ Datenbank bereit: $DB_PATH"

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
