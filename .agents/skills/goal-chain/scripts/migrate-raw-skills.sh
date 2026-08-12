#!/bin/bash
# migrate-raw-skills.sh — Generate chain-*.sh scripts for all raw skills
# Reads SKILL.md frontmatter to extract stack, then assembles boilerplate.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_ROOT=".agents/skills"

# ─── Skill Catalog ─────────────────────────────────────────────────
# Format: path:stack:special_instruction_template
declare -a SKILLS=(
    # ── agents/ ──
    "agents/clerk-webhooks:AUTONOM:Webhook-Integration mit Clerk (Auth-Provider). Analysiere Clerk-Webhook-Events, baue sichere Endpoints mit Signature-Verification. Self-Check: Idempotenz + Replay-Schutz."
    "agents/delivery-tracking:AUTONOM:Delivery-Tracking-Pipeline. State-Machine fuer Sendungs-Status (pending→in_transit→delivered). Self-Check: Eventual Consistency + Audit-Trail."
    "agents/sub-agent-prompts:AUTONOM:Sub-Agent-Prompt-Library. Erstelle robuste Prompt-Templates (Code-Reviewer, Playwright-Debugger, Repo-Hygiene-Mapper). Self-Check: Rolle+Ziel+Pflichtchecks+Ausgabeformat."

    # ── claude-tools/ ──
    "claude-tools/docx:MEMORY:Word-Datei-Operationen. .docx lesen/schreiben/erstellen via python-docx. Self-Check: Formatierung erhalten (Tabellen, Listen, Styles)."
    "claude-tools/pdf:MEMORY:PDF-Operationen. Lesen/Extrahieren/Verbinden/Teilen/OCR via pypdf + pdfplumber. Self-Check: Output-Validierung (Pages, Text-Länge)."
    "claude-tools/pptx:MEMORY:PowerPoint-Operationen. .pptx lesen/schreiben via python-pptx. Self-Check: Slides + Layouts erhalten."
    "claude-tools/xlsx:MEMORY:Excel-Operationen. .xlsx lesen/schreiben via openpyxl/pandas. Self-Check: Formeln + Sheets erhalten."
    "claude-tools/schedule:MEMORY:Aufgaben-Planung und Zeitfenster. Baue Schedule-Tabelle mit Moeglichkeits-/Deadline-Tracking. Self-Check: keine Konflikte + Realistic-Buffer."
    "claude-tools/morning:MEMORY:Morning-Routine / Tagesplaner. Lade ToDos, Calendar, priorisiere. Self-Check: 3 wichtigste Tasks identifiziert."
    "claude-tools/explain-usage:MEMORY:Erklaere Tool-Nutzung detailliert. Wann nutzen, wie nutzen, Fallstricke. Self-Check: 1 Beispiel + 1 Anti-Pattern."
    "claude-tools/setup-cowork:MEMORY:Cowork Setup-Wizard. Rolle erkennen, Plugins vorschlagen, Connectors, Skill-Tryout. Self-Check: 5-Step-TODOs vollstaendig."

    # ── documents/ ──
    "documents/document-tools:MEMORY:Generisches Dokument-Tool. Markdown/MD/RST lesen+schreiben. Self-Check: Encoding + Line-Endings korrekt."
    "documents/pdf-tools:MEMORY:PDF Convenience-Wrapper. Higher-Level Operationen als 'pdf'-Skill. Self-Check: Kommandozeilen-Pattern idempotent."
    "documents/presentation-tools:MEMORY:Presentation-Tool. Beamer/Keynote/PPT-Logic. Self-Check: Folien-Anzahl + Speaker-Notes."
    "documents/spreadsheet-tools:MEMORY:Spreadsheet-Tool. CSV/TSV/XLSX lesen+schreiben. Self-Check: Schema-Validierung."

    # ── design/standalone ──
    "design/canvas:KREATIV:HTML5 Canvas Rendering. Animationen + Drawing-Logic. Self-Check: FPS + Memory-Leaks."
    "design/performance:KREATIV:Web-Performance-Optimierung. LCP/FID/CLS + Critical-Path. Self-Check: Lighthouse-Score >= 90."
    "design/tailwind-design-system:KREATIV:Tailwind Component-Library. Tokens + Variants + Patterns. Self-Check: alle Components responsive."

    # ── development/standalone ──
    "development/python-performance-optimization:LOGISCH:Python Performance-Tuning. Profiling, Caching, Algorithmic-Improvements. Self-Check: Benchmark vor/nach mit harten Zahlen."
    "development/typescript-expert:LOGISCH:TypeScript Best-Practices. Type-Safety + Utility-Types + Generic-Constraints. Self-Check: Zero 'any'-Type."
    "development/upgrade-react-native:LOGISCH:React-Native Upgrade-Pfad. Breaking-Changes dokumentieren + Migration-Codmods. Self-Check: alle deprecated APIs ersetzt."

    # ── media/ ──
    "media/audio-transcription:LOGISCH:Audio zu Text. Whisper-API + Post-Processing. Self-Check: Word-Timestamps + Speaker-Diarization."
    "media/desktop-automation:LOGISCH:Desktop-Automatisierung. PyAutoGUI/RobotJS. Self-Check: Idempotenz + Screenshots vor/nach."
    "media/screenshot-tools:MEMORY:Screenshot-Capture + Annotation. ImageMagick/Pillow. Self-Check: Output-Format + DPI."

    # ── games/ ──
    "games/lua-game-systems:KREATIV:Lua Game-Systems. ECS-Architecture + Component-Composition. Self-Check: Performance-Budget eingehalten."
    "games/playcanvas-engine:KREATIV:Playcanvas Engine-Integration. Asset-Pipeline + Scene-Graph. Self-Check: Engine-Init + Frame-Budget."

    # ── evil-twin-protocol standalone (separate from phase-*-evil-twin) ──
    "evil-twin-protocol:GOVERNANCE:Standalone Evil-Twin-Engine. Spiegel-Thinker mit identischer Datenlage. FUNDAMENTAL widersprechen — nicht an Kleinigkeiten aufhalten. Synthese erzeugen."
)

GENERATED=0
for entry in "${SKILLS[@]}"; do
    IFS=':' read -r relpath stack instruction <<< "$entry"

    skill_name=$(basename "$relpath")
    parent_dir=$(dirname "$relpath")
    script_name="chain-${skill_name}.sh"
    script_path="$SCRIPT_DIR/$script_name"
    skill_md="$SKILLS_ROOT/$relpath/SKILL.md"

    if [[ ! -f "$skill_md" ]]; then
        echo "⚠️  SKILL.md not found: $skill_md — skipping $skill_name"
        continue
    fi

    if [[ -f "$script_path" ]]; then
        echo "↻ Already exists: $script_name"
        continue
    fi

    cat > "$script_path" <<EOF
#!/bin/bash
# chain-${skill_name}.sh — STACK: ${stack}
# Auto-generated wrap of ${relpath}/SKILL.md
set -euo pipefail
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
source "\$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="\${1:?Usage: bash chain-${skill_name}.sh RUN_ID TID}"
TID="\${2:?}"

ensure_db
assert_tid_state "\$TID" "PENDING"
tid_start "\$TID"
notify_dashboard "TID_STARTED" "\$TID" "\$(progress_summary "\$RUN_ID")"

OUTPUT_FILE=\$(task_field "\$TID" "output_artifact")
SKILL=\$(task_field "\$TID" "skill_name")
GOAL=\$(task_field "\$TID" "goal")

agent_header "\$TID" "${stack}: ${skill_name}"
emit_user_input_start "chain-${skill_name}.sh"

cat <<INSTRUCTION

## Goal: \$GOAL
## Skill: \$SKILL
## Source: ${relpath}/SKILL.md

## Aufgabe
${instruction}

## Domain-Kontext
- Original-Skill liegt unter: \`.agents/skills/${relpath}/SKILL.md\`
- Dieser Wrapper fuehrt den Skill als Chain-Tool aus.
- Drift-Detection: Output wird gegen template_markers verifiziert.

## Output nach \$OUTPUT_FILE
- Strukturiert, kein Drift.
- Self-Check gruen, dann: bash \$SCRIPT_DIR/complete.sh \$TID DONE.

## Agent-Regeln
1. Source-Skills (\`.agents/skills/${relpath}/SKILL.md\`) NICHT veraendern.
2. Output-Format einhalten — sonst Re-Dispatch.
3. NEXT_TID nach Self-Check setzen.
INSTRUCTION

agent_footer "\$TID" "\$SCRIPT_DIR/complete.sh" ""
emit_user_input_end "complete.sh \$TID DONE"

notify_dashboard "AWAITING_OUTPUT" "\$TID" "\$OUTPUT_FILE"
echo ""
echo "AGENT: bash \$SCRIPT_DIR/complete.sh \$TID DONE"
EOF

    chmod +x "$script_path"
    echo "✅ Generated: $script_name (stack=$stack)"
    GENERATED=$((GENERATED + 1))
done

echo ""
echo "========================================"
echo "Total scripts generated: $GENERATED"
echo "========================================"
