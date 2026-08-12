#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# ctl — Control Plane CLI Entry Point
#
# SyxBridge-Launcher-Pattern port: PID management, port cleanup,
# lock files, dependency checking, component lifecycle.
#
# Usage:
#   ./ctl start [component]     Start one or all components
#   ./ctl stop [component]      Stop one or all components
#   ./ctl status                Show running components
#   ./ctl kill                  Kill ALL old processes (port scan)
#   ./ctl deps                  Check dependencies
#   ./ctl ports                 Show port assignments
#
# Components: shinon, limen, dashboard, all
# ═══════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$SCRIPT_DIR/.ctl/pids"
LOG_DIR="$SCRIPT_DIR/.ctl/logs"
LOCK_DIR="$SCRIPT_DIR/.ctl/locks"
mkdir -p "$PID_DIR" "$LOG_DIR" "$LOCK_DIR"

# ─── Port Assignments ──────────────────────────────────────────────
declare -A COMPONENT_PORTS=(
    ["limen"]="8000"
    ["shinon-backend"]="3100"
    ["shinon-frontend"]="5173"
    ["dashboard"]="4200"
    ["leitstand"]="44519"
)

declare -A COMPONENT_PIDFILES=(
    ["limen"]="$PID_DIR/limen.pid"
    ["shinon-backend"]="$PID_DIR/shinon-backend.pid"
    ["shinon-frontend"]="$PID_DIR/shinon-frontend.pid"
    ["dashboard"]="$PID_DIR/dashboard.pid"
    ["leitstand"]="$PID_DIR/leitstand.pid"
)

declare -A COMPONENT_LOCKFILES=(
    ["limen"]="$LOCK_DIR/limen.lock"
    ["shinon-backend"]="$LOCK_DIR/shinon-backend.lock"
    ["shinon-frontend"]="$LOCK_DIR/shinon-frontend.lock"
    ["dashboard"]="$LOCK_DIR/dashboard.lock"
    ["leitstand"]="$LOCK_DIR/leitstand.lock"
)

# ─── Colors ─────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'; BOLD='\033[1m'

ok()    { echo -e "  ${GREEN}✅${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠️${NC}  $1"; }
fail()  { echo -e "  ${RED}❌${NC} $1"; }
info()  { echo -e "  ${CYAN}ℹ${NC}  $1"; }
header(){ echo -e "\n${BOLD}─── $1 ───${NC}"; }

# ─── PID Helpers ────────────────────────────────────────────────────
is_running() {
    local component="$1"
    local pidfile="${COMPONENT_PIDFILES[$component]:-}"
    if [[ -z "$pidfile" || ! -f "$pidfile" ]]; then
        return 1
    fi
    local pid; pid=$(cat "$pidfile" 2>/dev/null || true)
    if [[ -z "$pid" ]]; then return 1; fi
    kill -0 "$pid" 2>/dev/null
}

get_pid() {
    local component="$1"
    local pidfile="${COMPONENT_PIDFILES[$component]:-}"
    if [[ -f "$pidfile" ]]; then
        cat "$pidfile" 2>/dev/null || echo "unknown"
    else
        echo "—"
    fi
}

get_port() {
    local component="$1"
    echo "${COMPONENT_PORTS[$component]:-unknown}"
}

# ─── Port Cleanup (SyxBridge-pattern) ───────────────────────────────
kill_port_range() {
    local start_port="$1"
    local end_port="$2"
    local label="${3:-port range}"
    local killed=0

    for port in $(seq "$start_port" "$end_port"); do
        local pids
        pids=$(lsof -ti ":$port" 2>/dev/null || true)
        if [[ -n "$pids" ]]; then
            for pid in $pids; do
                if [[ "$pid" != "$$" ]]; then  # don't kill self
                    kill "$pid" 2>/dev/null || true
                    ((killed++)) || true
                fi
            done
        fi
    done
    if [[ $killed -gt 0 ]]; then
        echo "  🧹 $label: $killed process(es) auf Ports $start_port–$end_port beendet"
    fi
}

kill_all() {
    header "Prozess-Cleanup (alle Control-Plane-Ports)"
    kill_port_range 3100 3110 "Shinon"
    kill_port_range 5173 5180 "Shinon-Frontend"
    kill_port_range 4200 4210 "Dashboard"
    kill_port_range 8000 8010 "LIMEN"
    kill_port_range 44519 44530 "Leitstand"

    # Clean PID files for dead processes
    for comp in "${!COMPONENT_PIDFILES[@]}"; do
        local pf="${COMPONENT_PIDFILES[$comp]}"
        if [[ -f "$pf" ]]; then
            local pid; pid=$(cat "$pf" 2>/dev/null || true)
            if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
                rm -f "$pf"
            fi
        fi
    done

    # Clean stale locks
    for comp in "${!COMPONENT_LOCKFILES[@]}"; do
        local lf="${COMPONENT_LOCKFILES[$comp]}"
        if [[ -f "$lf" ]]; then
            local lockpid; lockpid=$(cat "$lf" 2>/dev/null || true)
            if [[ -z "$lockpid" ]] || ! kill -0 "$lockpid" 2>/dev/null; then
                rm -f "$lf"
            fi
        fi
    done
    echo ""
}

# ─── Dependency Check ───────────────────────────────────────────────
check_deps() {
    header "Dependency-Check"

    local all_ok=true

    # Python
    if command -v python3 &>/dev/null; then
        local pyver; pyver=$(python3 --version 2>&1)
        ok "Python: $pyver"
    else
        fail "Python 3 — NICHT GEFUNDEN"
        all_ok=false
    fi

    # Node.js
    if command -v node &>/dev/null; then
        local nodever; nodever=$(node --version 2>&1)
        ok "Node.js: $nodever"
    else
        fail "Node.js — NICHT GEFUNDEN"
        all_ok=false
    fi

    # npm
    if command -v npm &>/dev/null; then
        local npmver; npmver=$(npm --version 2>&1)
        ok "npm: v$npmver"
    else
        warn "npm — NICHT GEFUNDEN (Shinon-Frontend benötigt npm)"
        all_ok=false
    fi

    # sqlite3
    if command -v sqlite3 &>/dev/null; then
        ok "SQLite3: vorhanden"
    else
        warn "sqlite3 CLI — nicht gefunden (python3 sqlite reicht)"
    fi

    # bash
    if command -v bash &>/dev/null; then
        local bashver; bashver=$(bash --version 2>&1 | head -1)
        ok "Bash: $bashver"
    else
        fail "Bash — NICHT GEFUNDEN"
        all_ok=false
    fi

    # lsof (for port scanning)
    if command -v lsof &>/dev/null; then
        ok "lsof: vorhanden"
    else
        warn "lsof — nicht gefunden (Port-Scan ohne lsof)"
    fi

    # Python packages
    header "Python-Pakete"
    for pkg in fastapi uvicorn sqlite3; do
        if python3 -c "import $pkg" 2>/dev/null; then
            ok "$pkg: importierbar"
        else
            warn "$pkg: nicht importierbar (pip install $pkg?)"
            all_ok=false
        fi
    done

    # Node packages (check if ShinonLLM has node_modules)
    if [[ -d "$SCRIPT_DIR/ShinonLLM-main/frontend/node_modules" ]]; then
        ok "Shinon-Frontend: node_modules vorhanden"
    else
        warn "Shinon-Frontend: node_modules fehlt (cd ShinonLLM-main/frontend && npm install)"
    fi

    # LIMEN venv
    if [[ -d "$SCRIPT_DIR/limen-main/.venv" ]]; then
        ok "LIMEN: venv vorhanden"
    else
        warn "LIMEN: venv fehlt (cd limen-main && python3 -m venv .venv)"
    fi

    echo ""
    if $all_ok; then
        ok "Alle kritischen Abhängigkeiten erfüllt."
    else
        warn "Einige Abhängigkeiten fehlen. Siehe oben."
    fi
    echo ""
}

# ─── Component Start/Stop ───────────────────────────────────────────

start_limen() {
    local port="${COMPONENT_PORTS[limen]}"
    local pidfile="${COMPONENT_PIDFILES[limen]}"
    local lockfile="${COMPONENT_LOCKFILES[limen]}"
    local logfile="$LOG_DIR/limen.log"

    if is_running "limen"; then
        warn "LIMEN läuft bereits (PID $(get_pid limen), Port $port)"
        return 0
    fi

    # Check port
    if lsof -ti ":$port" &>/dev/null; then
        warn "Port $port belegt — versuche Cleanup"
        kill_port_range "$port" "$port" "LIMEN-Port"
        sleep 1
    fi

    local limen_dir="$SCRIPT_DIR/limen-main"
    if [[ ! -d "$limen_dir" ]]; then
        fail "LIMEN-Verzeichnis nicht gefunden: $limen_dir"
        return 1
    fi

    # Check for config file
    local config_path="${LIMEN_CONFIG:-$HOME/.config/limen/config.toml}"
    if [[ ! -f "$config_path" ]]; then
        warn "LIMEN-Konfiguration nicht gefunden: $config_path"
        warn "Erstelle Standard-Konfiguration..."
        mkdir -p "$(dirname "$config_path")"
        cat > "$config_path" << 'LIMENCONF'
[server]
port = 8000
host = "127.0.0.1"
max_body_size_kb = 1024

[database]
path = ":memory:"
busy_timeout_ms = 5000
sync_mode = "normal"

[audit]
audit_token_secret = "dev-token-change-in-production"
LIMENCONF
        ok "Standard-Konfiguration erstellt: $config_path"
    fi

    info "Starte LIMEN auf Port $port..."

    cd "$limen_dir"
    if [[ -d ".venv" ]]; then
        source .venv/bin/activate
    fi

    # Use Python one-liner to load config and start uvicorn
    nohup python3 -c "
import sys
sys.path.insert(0, 'src')
from limen.config.loader import load_config
from limen.api.app import create_app
import uvicorn

config = load_config('$config_path')
app = create_app(config)
uvicorn.run(app, host='127.0.0.1', port=$port, log_level='info')
" >> "$logfile" 2>&1 &

    local pid=$!
    echo "$pid" > "$pidfile"
    echo "$pid" > "$lockfile"

    # Wait for startup
    for i in $(seq 1 10); do
        if curl -s "http://127.0.0.1:$port/health" &>/dev/null; then
            ok "LIMEN gestartet (PID $pid, Port $port)"
            return 0
        fi
        sleep 0.5
    done
    ok "LIMEN gestartet (PID $pid, Port $port — health check pending)"
    return 0
}

start_shinon_backend() {
    local port="${COMPONENT_PORTS[shinon-backend]}"
    local pidfile="${COMPONENT_PIDFILES[shinon-backend]}"
    local logfile="$LOG_DIR/shinon-backend.log"

    if is_running "shinon-backend"; then
        warn "Shinon-Backend läuft bereits (PID $(get_pid shinon-backend), Port $port)"
        return 0
    fi

    local backend_dir="$SCRIPT_DIR/ShinonLLM-main/backend"
    if [[ ! -d "$backend_dir" ]]; then
        warn "Shinon-Backend-Verzeichnis nicht gefunden: $backend_dir"
        return 1
    fi

    info "Starte Shinon-Backend auf Port $port..."

    cd "$SCRIPT_DIR/ShinonLLM-main/backend"
    if [[ ! -d "node_modules" ]]; then
        info "Installiere Backend-Abhängigkeiten..."
        npm install --no-audit --no-fund --loglevel error 2>&1 | tail -1
    fi

    nohup node server.js >> "$logfile" 2>&1 &
    local pid=$!
    echo "$pid" > "$pidfile"

    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
        ok "Shinon-Backend gestartet (PID $pid, Port $port)"
    else
        fail "Shinon-Backend konnte nicht gestartet werden — siehe $logfile"
        return 1
    fi
    return 0
}

start_shinon_frontend() {
    local port="${COMPONENT_PORTS[shinon-frontend]}"
    local pidfile="${COMPONENT_PIDFILES[shinon-frontend]}"
    local logfile="$LOG_DIR/shinon-frontend.log"

    if is_running "shinon-frontend"; then
        warn "Shinon-Frontend läuft bereits (PID $(get_pid shinon-frontend), Port $port)"
        return 0
    fi

    local frontend_dir="$SCRIPT_DIR/ShinonLLM-main/frontend"
    if [[ ! -d "$frontend_dir" ]]; then
        warn "Shinon-Frontend-Verzeichnis nicht gefunden: $frontend_dir"
        return 1
    fi

    info "Starte Shinon-Frontend (Vite dev server)..."

    cd "$SCRIPT_DIR/ShinonLLM-main/frontend"
    if [[ ! -d "node_modules" ]]; then
        info "Installiere Frontend-Abhängigkeiten..."
        npm install --no-audit --no-fund --loglevel error 2>&1 | tail -1
    fi

    nohup npx vite --port "$port" --host 127.0.0.1 >> "$logfile" 2>&1 &
    local pid=$!
    echo "$pid" > "$pidfile"

    sleep 2
    if kill -0 "$pid" 2>/dev/null; then
        ok "Shinon-Frontend gestartet (PID $pid, Port $port)"
    else
        fail "Shinon-Frontend konnte nicht gestartet werden — siehe $logfile"
        return 1
    fi
    return 0
}

start_dashboard() {
    local port="${COMPONENT_PORTS[dashboard]}"
    local pidfile="${COMPONENT_PIDFILES[dashboard]}"
    local logfile="$LOG_DIR/dashboard.log"

    if is_running "dashboard"; then
        warn "Dashboard läuft bereits (PID $(get_pid dashboard), Port $port)"
        return 0
    fi

    local server_py="$SCRIPT_DIR/.agents/skills/goal-chain/scripts/live-dashboard-server.py"
    if [[ ! -f "$server_py" ]]; then
        warn "Dashboard-Server nicht gefunden: $server_py"
        return 1
    fi

    info "Starte Live-Dashboard auf Port $port..."
    nohup python3 "$server_py" --port "$port" >> "$logfile" 2>&1 &
    local pid=$!
    echo "$pid" > "$pidfile"

    sleep 1
    if kill -0 "$pid" 2>/dev/null; then
        ok "Dashboard gestartet (PID $pid, Port $port)"
    else
        fail "Dashboard konnte nicht gestartet werden — siehe $logfile"
        return 1
    fi
    return 0
}

stop_component() {
    local component="$1"

    # Handle 'all' specially
    if [[ "$component" == "all" ]]; then
        for comp in limen shinon-backend shinon-frontend dashboard leitstand; do
            stop_component "$comp"
        done
        return 0
    fi

    local pidfile="${COMPONENT_PIDFILES[$component]:-}"
    local lockfile="${COMPONENT_LOCKFILES[$component]:-}"

    if [[ -z "$pidfile" ]]; then
        fail "Unbekannte Komponente: $component"
        return 1
    fi

    if ! is_running "$component"; then
        info "$component: bereits gestoppt"
        rm -f "$pidfile" "$lockfile"
        return 0
    fi

    local pid; pid=$(get_pid "$component")
    info "Stoppe $component (PID $pid)..."

    kill "$pid" 2>/dev/null || true
    sleep 0.5

    # Force kill if still running
    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
        sleep 0.5
    fi

    rm -f "$pidfile" "$lockfile"

    if ! kill -0 "$pid" 2>/dev/null; then
        ok "$component gestoppt"
    else
        fail "$component: konnte nicht gestoppt werden"
        return 1
    fi
    return 0
}

# ─── Status ──────────────────────────────────────────────────────────
show_status() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  Control Plane — Komponenten-Status                     ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    printf "  %-20s %-8s %-8s %s\n" "KOMPONENTE" "PORT" "PID" "STATUS"
    printf "  %-20s %-8s %-8s %s\n" "──────────" "────" "───" "──────"

    for comp in limen shinon-backend shinon-frontend dashboard leitstand; do
        local port; port=$(get_port "$comp")
        local pid; pid=$(get_pid "$comp")
        local status="⏹ STOPPED"

        if is_running "$comp"; then
            status="${GREEN}▶ RUNNING${NC}"
        elif [[ "$pid" != "—" ]]; then
            status="${YELLOW}⚡ DEAD (stale PID)${NC}"
        fi

        printf "  %-20s %-8s %-8s " "$comp" "$port" "$pid"
        echo -e "$status"
    done

    echo ""
    echo "  ${CYAN}URLs:${NC}"
    for comp in limen shinon-backend shinon-frontend dashboard leitstand; do
        if is_running "$comp"; then
            local port; port=$(get_port "$comp")
            local label="$comp"
            [[ "$comp" == "shinon-frontend" ]] && label="Shinon UI"
            [[ "$comp" == "shinon-backend" ]] && label="Shinon API"
            [[ "$comp" == "dashboard" ]] && label="Goal Dashboard"
            printf "    http://127.0.0.1:%-5s → %s\n" "$port" "$label"
        fi
    done
    echo ""
}

# ─── Main ────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-status}"
    local target="${2:-all}"

    case "$cmd" in
        start)
            case "$target" in
                limen)          start_limen ;;
                shinon)         start_shinon_backend && start_shinon_frontend ;;
                shinon-backend) start_shinon_backend ;;
                shinon-frontend) start_shinon_frontend ;;
                dashboard)      start_dashboard ;;
                all)
                    echo -e "\n${BOLD}Control Plane — Starte alle Komponenten${NC}\n"
                    start_limen
                    start_shinon_backend
                    start_shinon_frontend
                    start_dashboard
                    echo ""
                    show_status
                    ;;
                *)
                    echo "Unbekannte Komponente: $target"
                    echo "Verfügbar: limen, shinon, shinon-backend, shinon-frontend, dashboard, all"
                    exit 1
                    ;;
            esac
            ;;

        stop)
            case "$target" in
                all)
                    echo -e "\n${BOLD}Control Plane — Stoppe alle Komponenten${NC}\n"
                    for comp in limen shinon-backend shinon-frontend dashboard leitstand; do
                        stop_component "$comp"
                    done
                    echo ""
                    ;;
                *)
                    stop_component "$target"
                    ;;
            esac
            ;;

        restart)
            stop_component "${target}" 2>/dev/null || true
            sleep 1
            main start "$target"
            ;;

        status)
            show_status
            ;;

        kill)
            kill_all
            ;;

        deps)
            check_deps
            ;;

        ports)
            echo ""
            echo -e "${BOLD}Port-Zuweisungen:${NC}"
            echo ""
            for comp in limen shinon-backend shinon-frontend dashboard leitstand; do
                printf "  %-20s → :%s\n" "$comp" "$(get_port "$comp")"
            done
            echo ""
            ;;

        *)
            echo "Usage: ctl {start|stop|restart|status|kill|deps|ports} [component]"
            echo ""
            echo "Commands:"
            echo "  start [comp]   Starte Komponente(n)"
            echo "  stop [comp]    Stoppe Komponente(n)"
            echo "  restart [comp] Neustart Komponente(n)"
            echo "  status         Zeige Status aller Komponenten"
            echo "  kill           Beende ALLE Control-Plane-Prozesse (Port-Scan)"
            echo "  deps           Prüfe Abhängigkeiten"
            echo "  ports          Zeige Port-Zuweisungen"
            echo ""
            echo "Components: limen, shinon, shinon-backend, shinon-frontend, dashboard, all"
            exit 1
            ;;
    esac
}

main "$@"
