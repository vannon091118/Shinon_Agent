#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# install.sh — Shinon Control Plane · Vollständige Installation
#
# Richtet ALLE Komponenten ein:
#   1. Abhängigkeiten prüfen (Python, Node, SQLite, bash)
#   2. Python venv erstellen + Pakete installieren
#   3. LIMEN-Datenbank initialisieren
#   4. Shinon-Frontend (npm install)
#   5. Config-Dateien aus Templates erzeugen
#   6. Erster Start + Onboarding-Erkennung
#
# Usage:
#   bash install.sh              Interaktive Installation
#   bash install.sh --quick      Schnell-Installation (Defaults)
#   bash install.sh --repair     Config reparieren (Secrets bleiben erhalten)
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ─── Farben ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()    { echo -e "  ${GREEN}✅${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
fail()  { echo -e "  ${RED}❌${NC} $1"; }
info()  { echo -e "  ${CYAN}ℹ${NC}  $1"; }
step()  { echo -e "\n${BOLD}═══ $1 ═══${NC}\n"; }
title() { echo -e "\n${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"; echo -e "${BOLD}║${NC}  $1"; echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}\n"; }

MODE="${1:-install}"

# ─── Schritt 1: Willkommen ──────────────────────────────────────────
title "Shinon Control Plane · Installation"

echo "  Dieses Skript richtet alle Komponenten ein:"
echo "    • Shinon (Persönlichkeit + Chat)"
echo "    • LIMEN (API-Gateway + Key-Management)"
echo "    • KARMA (FalsificationGate + Audit-Trail)"
echo "    • Promtguard (Claim-Extraktion)"
echo "    • goal-chain (Autonome Entwicklungskaskade)"
echo "    • Dashboard (Live-Monitoring)"
echo ""

if [[ "$MODE" == "--repair" ]]; then
    step "REPARATUR-MODUS"
    info "Config-Dateien werden repariert. API-Keys und Secrets bleiben erhalten."
elif [[ "$MODE" == "--quick" ]]; then
    info "Schnell-Installation mit Standard-Einstellungen."
else
    read -rp "  Weiter mit Enter (oder Ctrl+C zum Abbrechen)..." _
fi

# ─── Schritt 2: Abhängigkeiten prüfen ───────────────────────────────
step "Schritt 1/6: Abhängigkeiten prüfen"

MISSING=()

check_cmd() {
    local name="$1"; local cmd="${2:-$1}"
    if command -v "$cmd" &>/dev/null; then
        local ver; ver=$("$cmd" --version 2>&1 | head -1 || echo "ok")
        ok "$name: ${ver:0:60}"
    else
        fail "$name — NICHT installiert"
        MISSING+=("$name")
    fi
}

check_cmd "Python 3" python3
check_cmd "Node.js" node
check_cmd "npm" npm
check_cmd "Bash" bash
check_cmd "SQLite3" sqlite3

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo ""
    fail "Fehlende Abhängigkeiten: ${MISSING[*]}"
    echo "  Bitte installieren:"
    for m in "${MISSING[@]}"; do
        case "$m" in
            "Python 3") echo "    sudo apt install python3 python3-pip python3-venv" ;;
            "Node.js")  echo "    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install nodejs" ;;
            *)          echo "    sudo apt install $m" ;;
        esac
    done
    exit 1
fi

# ─── Schritt 3: Python-Umgebung ─────────────────────────────────────
step "Schritt 2/6: Python-Umgebung einrichten"

VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    info "Erstelle virtuelle Umgebung..."
    python3 -m venv "$VENV_DIR"
    ok "venv erstellt: $VENV_DIR"
else
    ok "venv bereits vorhanden"
fi

source "$VENV_DIR/bin/activate"

info "Installiere Python-Pakete..."
pip install --quiet --upgrade pip 2>&1 | tail -1

# Kern-Abhängigkeiten
pip install --quiet \
    fastapi uvicorn \
    httpx aiohttp \
    pydantic \
    2>&1 | tail -1

ok "Python-Pakete installiert"

# ─── Schritt 4: Shinon-Frontend ──────────────────────────────────────
step "Schritt 3/6: Shinon-Frontend einrichten"

SHINON_FRONTEND="$SCRIPT_DIR/ShinonLLM-main/frontend"
if [[ -d "$SHINON_FRONTEND" ]]; then
    cd "$SHINON_FRONTEND"
    if [[ ! -d "node_modules" ]]; then
        info "Installiere Frontend-Abhängigkeiten (npm)..."
        npm install --no-audit --no-fund --loglevel error 2>&1 | tail -3
        ok "Frontend-Abhängigkeiten installiert"
    else
        ok "Frontend bereits installiert"
    fi
    cd "$SCRIPT_DIR"
else
    warn "Shinon-Frontend nicht gefunden (optional)"
fi

# ─── Schritt 5: Datenbanken initialisieren ───────────────────────────
step "Schritt 4/6: Datenbanken initialisieren"

# LIMEN DB
LIMEN_DB="$SCRIPT_DIR/limen-main/data/limen.db"
if [[ ! -f "$LIMEN_DB" ]]; then
    info "Initialisiere LIMEN-Datenbank..."
    mkdir -p "$(dirname "$LIMEN_DB")"
    python3 -c "
import sqlite3
conn = sqlite3.connect('$LIMEN_DB')
conn.executescript('''
CREATE TABLE IF NOT EXISTS providers (
    key_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    deployment TEXT NOT NULL DEFAULT 'default',
    value TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    priority INTEGER DEFAULT 0,
    cooldown_until REAL,
    observed_rpm REAL DEFAULT 0,
    itpm REAL DEFAULT 0,
    otpm REAL DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    health_score REAL DEFAULT 100.0,
    avg_latency_ms REAL DEFAULT 0,
    meta_json TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS model_registry (
    model_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    deployment TEXT NOT NULL DEFAULT 'default',
    capabilities TEXT DEFAULT '{}',
    cost_tier TEXT DEFAULT 'standard',
    PRIMARY KEY (model_id, provider, deployment)
);
''')
conn.commit()
conn.close()
print('LIMEN DB initialisiert')
"
    ok "LIMEN-Datenbank erstellt"
else
    ok "LIMEN-Datenbank bereits vorhanden"
fi

# goal-chain DB
GC_DB="$SCRIPT_DIR/.agents/skills/goal-chain/db/tid-state.db"
if [[ ! -f "$GC_DB" ]]; then
    info "Initialisiere goal-chain-Datenbank..."
    if [[ -x ".agents/skills/goal-chain/scripts/db-init.sh" ]]; then
        bash .agents/skills/goal-chain/scripts/db-init.sh 2>&1 | tail -1
    fi
    ok "goal-chain-Datenbank erstellt"
else
    ok "goal-chain-Datenbank bereits vorhanden"
fi

# KARMA DB
KARMA_DB="$HOME/.karma/karma.db"
if [[ ! -f "$KARMA_DB" ]]; then
    info "Initialisiere KARMA-Datenbank..."
    mkdir -p "$(dirname "$KARMA_DB")"
    python3 -c "
import sqlite3
conn = sqlite3.connect('$KARMA_DB')
conn.executescript('''
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    project TEXT,
    payload TEXT NOT NULL,
    correlation_id TEXT,
    prev_hash TEXT,
    event_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS experience (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,
    action_type TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    state_hash TEXT NOT NULL,
    result TEXT NOT NULL,
    feedback_score REAL,
    created_at TEXT DEFAULT (datetime('now'))
);
''')
conn.commit()
conn.close()
"
    ok "KARMA-Datenbank erstellt"
else
    ok "KARMA-Datenbank bereits vorhanden"
fi

# Shinon Memory DB
SHINON_MEM="$HOME/.shinon/memory.db"
if [[ ! -f "$SHINON_MEM" ]]; then
    info "Initialisiere Shinon-Memory-Datenbank..."
    mkdir -p "$(dirname "$SHINON_MEM")"
    python3 -c "
import sqlite3
conn = sqlite3.connect('$SHINON_MEM')
conn.executescript('''
CREATE TABLE IF NOT EXISTS personal_facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    source TEXT DEFAULT 'user',
    evidence TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,
    pattern_text TEXT NOT NULL,
    confidence REAL DEFAULT 0.5,
    occurrences INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS attitudes (
    dimension TEXT PRIMARY KEY,
    value REAL NOT NULL DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO attitudes (dimension, value) VALUES
    ('skepticism', 5.0),
    ('helpfulness', 3.0),
    ('directness', 7.0),
    ('patience', 4.0),
    ('curiosity', 6.0);
''')
conn.commit()
conn.close()
"
    ok "Shinon-Memory-Datenbank erstellt"
else
    ok "Shinon-Memory-Datenbank bereits vorhanden"
fi

# ─── Schritt 6: Config-Dateien ──────────────────────────────────────
step "Schritt 5/6: Konfiguration"

CONFIG_DIR="$HOME/.config/shinon"
mkdir -p "$CONFIG_DIR"

# Hauptkonfiguration
if [[ ! -f "$CONFIG_DIR/config.toml" || "$MODE" == "--repair" ]]; then
    if [[ "$MODE" == "--repair" ]] && [[ -f "$CONFIG_DIR/config.toml" ]]; then
        info "Sichere bestehende config.toml nach config.toml.bak..."
        cp "$CONFIG_DIR/config.toml" "$CONFIG_DIR/config.toml.bak"
    fi

    cat > "$CONFIG_DIR/config.toml" << 'CONFEOF'
# Shinon Control Plane · Konfiguration
# Erstellt von install.sh

[shinon]
# Persönlichkeit (0-10, Standard: kritisch/skeptisch)
skepticism = 8
directness = 7
helpfulness = 4
patience = 5
curiosity = 6

# Name im Chat
display_name = "Shinon"

[limen]
# LIMEN API-Gateway
url = "http://127.0.0.1:8000"
auto_start = true

[dashboard]
# Live-Dashboard
port = 4200
auto_start = true

[goal_chain]
# Autonome Entwicklungskaskade
db_path = ".agents/skills/goal-chain/db/tid-state.db"
auto_discover_skills = true
CONFEOF
    ok "Konfiguration erstellt: $CONFIG_DIR/config.toml"
else
    ok "Konfiguration bereits vorhanden (überspringe)"
fi

# LIMEN-Konfiguration (separat, weil LIMEN eigenes Config-Format hat)
LIMEN_CONF="$HOME/.config/limen/config.toml"
if [[ ! -f "$LIMEN_CONF" || "$MODE" == "--repair" ]]; then
    mkdir -p "$(dirname "$LIMEN_CONF")"
    cat > "$LIMEN_CONF" << 'LCONF'
[server]
port = 8000
host = "127.0.0.1"

[database]
path = "limen-main/data/limen.db"

[audit]
enabled = true

[routing]
default_provider_chain = ["groq", "openrouter", "nvidia", "github"]
auto_model = true
LCONF
    ok "LIMEN-Konfiguration erstellt"
fi

# ─── Schritt 7: Abschluss ───────────────────────────────────────────
step "Schritt 6/6: Installation abgeschlossen"

echo ""
echo "  ┌─────────────────────────────────────────────────────────┐"
echo "  │  ✅ Shinon Control Plane ist installiert!               │"
echo "  │                                                         │"
echo "  │  Nächste Schritte:                                      │"
echo "  │                                                         │"
echo "  │  1. Onboarding starten:                                 │"
echo "  │     ./shinon --setup                                    │"
echo "  │                                                         │"
echo "  │  2. Oder direkt starten:                                │"
echo "  │     ./shinon start                                      │"
echo "  │                                                         │"
echo "  │  3. Diagnose bei Problemen:                             │"
echo "  │     ./shinon --doc                                      │"
echo "  │                                                         │"
echo "  │  4. Chat öffnen:                                        │"
echo "  │     ./shinon chat                                       │"
echo "  └─────────────────────────────────────────────────────────┘"
echo ""

# Auto-Onboarding-Erkennung
if [[ ! -f "$CONFIG_DIR/.onboarding-done" ]] && [[ "$MODE" != "--quick" ]]; then
    echo ""
    read -rp "  🚀 Onboarding jetzt starten? (j/N): " START_ONBOARD
    if [[ "$START_ONBOARD" =~ ^[jJyY] ]]; then
        exec bash "$SCRIPT_DIR/shinon-setup"
    fi
fi

touch "$CONFIG_DIR/.install-done"
echo "  Installations-Timestamp: $(date)"
