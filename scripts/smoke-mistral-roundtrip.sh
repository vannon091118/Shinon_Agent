#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# smoke-mistral-roundtrip.sh
# Validiert, dass der Mistral-Provider in der zentralen Shinon/LIMEN
# Key-Store-Pipeline (Provider-Tabelle) sauber round-tripped:
#     insert → read → fingerprints → status → cleanup
#
# Non-interactive — keine API-Calls, keine TTY-Abhängigkeit.
# Exit 0 = OK, Exit 1 = Drift.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── 1. SHINON_HOME + LIMEN_DB bestimmen ─────────────────────────
SHINON_HOME="${SHINON_HOME:-$HOME/.shinon}"
LIMEN_DB="$SHINON_HOME/data/limen/limen.db"

if [[ ! -f "$LIMEN_DB" ]]; then
    echo "  ❌ LIMEN-DB fehlt: $LIMEN_DB"
    echo "     Init:  python3 install.py   (legt Schema an)"
    exit 1
fi

# ─── 2. Test-Daten vorbereiten ──────────────────────────────────
TEST_KEY="MISTRAL_TEST_KEY_$(date +%s%N | sha256sum | cut -c1-32)"
TEST_PROVIDER="mistral"
TEST_KEY_ID="mistral_test_$(echo "$TEST_KEY" | cut -c1-8)"

# Hash-Funktion (muss konsistent mit Database.upsert_key sein)
fingerprint() {
    python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:16])" "$1"
}
FP=$(fingerprint "$TEST_KEY")

echo ""
echo "── MISTRAL ROUND-TRIP SMOKE-TEST ─────────────────────────"
echo "  Provider:        $TEST_PROVIDER"
echo "  Key-ID:          $TEST_KEY_ID"
echo "  Fingerprint:     $FP"
echo "  DB-Path:         $LIMEN_DB"
echo ""

# ─── 3. INSERT via SQLite (simuliert upsert_provider_key) ──────
python3 - <<PY
import sqlite3, hashlib, json
conn = sqlite3.connect("$LIMEN_DB")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Verify schema
cols = [r['name'] for r in cur.execute("PRAGMA table_info(providers)").fetchall()]
required = ['key_id','provider','status','priority','meta_json','api_key_fingerprint']
missing = [c for c in required if c not in cols]
if missing:
    print(f"  ❌ Schema-Defekt: fehlende Spalten {missing}")
    raise SystemExit(1)

# Insert Mistral-key (idempotent: REPLACE on key_id, no created_at — schema uses last_used_at only)
cur.execute("""
    INSERT OR REPLACE INTO providers
        (key_id, provider, deployment, status, priority, limit_scope, meta_json, api_key_fingerprint)
    VALUES (?, ?, '', 'active', 1, 'provider', ?, ?)
""", (f"$TEST_KEY_ID",
      "$TEST_PROVIDER",
      json.dumps({"api_key": "$TEST_KEY", "source": "smoke-test"}),
      "$FP"))
conn.commit()

# ─── 4. READ back via json_extract (matches providers_has_keys) ─
rows = cur.execute("""
    SELECT key_id, provider, status, priority,
           json_extract(meta_json, '\$.api_key') AS api_key,
           api_key_fingerprint
    FROM providers
    WHERE provider = ?
      AND json_extract(meta_json, '\$.api_key') IS NOT NULL
""", ("$TEST_PROVIDER",)).fetchall()

if not rows:
    print("  ❌ Lese-Back lieferte 0 Zeilen")
    raise SystemExit(1)

row = rows[0]
print(f"  ✅ Read-back:")
print(f"     key_id              = {row['key_id']}")
print(f"     provider            = {row['provider']}")
print(f"     status              = {row['status']}")
print(f"     priority            = {row['priority']}")
print(f"     fingerprint match   = {row['api_key_fingerprint'] == '$FP'}")

if row['api_key'] != "$TEST_KEY":
    print(f"  ❌ API-Key mismatch:\n     erwartet: $TEST_KEY\n     gelesen:  {row['api_key']}")
    raise SystemExit(1)

if row['api_key_fingerprint'] != "$FP":
    print(f"  ❌ Fingerprint mismatch")
    raise SystemExit(1)

# Cleanup
cur.execute("DELETE FROM providers WHERE key_id = ?", ("$TEST_KEY_ID",))
conn.commit()
conn.close()
print()
print("  ✅ MISTRAL ROUND-TRIP OK (insert → read → fingerprint → cleanup)")
PY

echo ""
echo "────────────────────────────────────────────────────────"
echo "  ✅ SMOKE-TEST MISTRAL: PASS (exit 0)"
