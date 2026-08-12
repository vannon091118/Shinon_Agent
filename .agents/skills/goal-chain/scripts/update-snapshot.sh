#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# update-snapshot.sh — Render goal-chain state as live HTML
# Schreibt .goal/{RUN_ID}/snapshot.html mit Auto-Refresh.
# register_preview zeigt es im Chat-UI an.
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/tid-helpers.sh"

RUN_ID="${1:?Usage: update-snapshot.sh RUN_ID [STATUS_INFO]}"
STATUS_INFO="${2:-Live snapshot}"

ensure_db
RUN_DIR=$(db_query "SELECT DISTINCT 'placeholder' FROM tasks WHERE run_id='$RUN_ID'" >/dev/null 2>&1 && echo "" || echo "")
# Better: get run_dir from tasks
RUN_DIR_REL=$(python3 -c "
import sqlite3, os
conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()
# Use latest run matching this run_id's structure
row = cur.execute('SELECT DISTINCT run_id FROM tasks WHERE run_id LIKE ? LIMIT 1', ('$RUN_ID%',)).fetchone()
if row:
    # Find the actual run directory from output paths of any task for this run
    r = cur.execute(\"SELECT output_artifact FROM tasks WHERE run_id=? AND output_artifact LIKE '.goal/%' LIMIT 1\", (row[0],)).fetchone()
    if r:
        # Extract run dir (e.g., '.goal/R20260811-foo')
        out = r[0]
        parts = out.split('/')
        print('/'.join(parts[:2]))
    else:
        # Try one with longer path
        r2 = cur.execute('SELECT output_artifact FROM tasks WHERE run_id=? LIMIT 1', (row[0],)).fetchone()
        if r2:
            print('.goal/' + row[0])
conn.close()
" 2>/dev/null)

if [[ -z "$RUN_DIR_REL" ]]; then
    echo "❌ No run_dir found for RUN_ID $RUN_ID" >&2
    exit 1
fi

mkdir -p "$RUN_DIR_REL"
SNAPSHOT="$RUN_DIR_REL/snapshot.html"

# Read all TIDs and assemble:
python3 <<PYEOF > "$SNAPSHOT"
import sqlite3, os, json
from datetime import datetime

conn = sqlite3.connect('$DB_PATH')
cur = conn.cursor()

RUN_ID = '$RUN_ID'

# Overall stats
total = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=?', (RUN_ID,)).fetchone()[0]
done = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status="DONE"', (RUN_ID,)).fetchone()[0]
inprog = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status="IN_PROGRESS"', (RUN_ID,)).fetchone()[0]
failed = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status="FAILED"', (RUN_ID,)).fetchone()[0]
skipped = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status="SKIPPED"', (RUN_ID,)).fetchone()[0]
root_cause_done = cur.execute('SELECT COUNT(*) FROM tasks WHERE run_id=? AND status="ROOT_CAUSE_DONE"', (RUN_ID,)).fetchone()[0]
pending = total - done - inprog - failed - skipped - root_cause_done
percent = int(done * 100 // total) if total > 0 else 0

goal = cur.execute('SELECT goal FROM tasks WHERE run_id=? LIMIT 1', (RUN_ID,)).fetchone()[0]
projekt = cur.execute('SELECT projekt FROM tasks WHERE run_id=? LIMIT 1', (RUN_ID,)).fetchone()[0]

# All TIDs ordered
all_tids = cur.execute('''
    SELECT tid, phase, phase_section, status, skill_name, requires_approval, template_id
    FROM tasks WHERE run_id=? ORDER BY phase_seq ASC
''', (RUN_ID,)).fetchall()

# Recent decisions
recent_decisions = cur.execute('''
    SELECT d.tid, d.decision_type, d.decision_value, d.timestamp
    FROM dispatcher_decisions d
    JOIN tasks t ON d.tid = t.tid
    WHERE t.run_id=?
    ORDER BY d.decision_id DESC LIMIT 5
''', (RUN_ID,)).fetchall()

# User decisions
user_decisions = cur.execute('''
    SELECT after_tid, decision, selected_tid, user_rationale, timestamp
    FROM user_decisions WHERE after_tid IN
      (SELECT tid FROM tasks WHERE run_id=?)
    ORDER BY decision_id DESC LIMIT 5
''', (RUN_ID,)).fetchall()

# Next pending TID
next_tid = cur.execute('''
    SELECT t.tid FROM tasks t
    WHERE t.run_id=? AND t.status='PENDING'
    AND NOT EXISTS (
      SELECT 1 FROM pre_tasks pt JOIN tasks pt2 ON pt.pre_tid=pt2.tid
      WHERE pt.tid=t.tid AND pt2.status NOT IN ('DONE','SKIPPED','ROOT_CAUSE_DONE')
    )
    ORDER BY t.phase_seq LIMIT 1
''', (RUN_ID,)).fetchone()

conn.close()

# ─── RENDER HTML ────────────────────────────────────────────
phase_icons = {'P1': '🧠', 'P2': '🔧', 'P3': '⚙️', 'P4': '📝', 'G1-2': '🚪', 'G2-3': '🚪', 'STACK': '🔧'}
status_icons = {
    'DONE': ('✅', '#10b981'),
    'IN_PROGRESS': ('🔄', '#3b82f6'),
    'FAILED': ('❌', '#ef4444'),
    'SKIPPED': ('⏭️', '#6b7280'),
    'ROOT_CAUSE_DONE': ('🎯', '#a78bfa'),
    'PENDING': ('⏳', '#9ca3af'),
}

current_time = datetime.now().strftime('%H:%M:%S')
status_text = '$STATUS_INFO'[:80]

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="2">
<title>🔗 GOAL-CHAIN · {RUN_ID}</title>
<style>
  :root {{
    --bg: #0f172a;
    --bg-card: #1e293b;
    --bg-card-light: #334155;
    --fg: #f1f5f9;
    --fg-dim: #cbd5e1;
    --accent: #3b82f6;
    --accent-glow: rgba(59,130,246,.15);
    --success: #10b981;
    --warn: #f59e0b;
    --danger: #ef4444;
    --muted: #6b7280;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 0;
    font-family: -apple-system,BlinkMacSystemFont,"SF Mono",Menlo,monospace;
    background: var(--bg);
    color: var(--fg);
    font-size: 13px;
  }}
  .container {{ padding: 16px; max-width: 1400px; margin: 0 auto; }}
  .header {{
    background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-light) 100%);
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 14px 20px;
    margin-bottom: 16px;
    box-shadow: 0 0 30px var(--accent-glow);
  }}
  .header-row {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }}
  .header-left {{ flex: 1; min-width: 0; }}
  .header-right {{ flex-shrink: 0; text-align: right; white-space: nowrap; }}
  .title {{ font-size: 18px; font-weight: 700; color: var(--accent); }}
  .subtitle {{ color: var(--fg-dim); font-size: 12px; margin-top: 4px; word-break: break-word; }}
  .status-pill {{
    background: var(--accent);
    color: #fff;
    padding: 6px 14px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    display: inline-block;
  }}
  .progress-card {{
    background: var(--bg-card);
    border: 1px solid var(--bg-card-light);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 16px;
  }}
  .progress-header {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
  .progress-num {{ font-size: 24px; font-weight: 700; color: var(--success); }}
  .progress-bar-wrap {{
    background: var(--bg-card-light);
    border-radius: 6px;
    height: 24px;
    overflow: hidden;
    position: relative;
  }}
  .progress-bar {{
    background: linear-gradient(90deg, var(--accent), var(--success));
    height: 100%;
    width: {percent}%;
    transition: width 1s ease;
    box-shadow: 0 0 10px var(--accent-glow);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 8px;
    color: #fff;
    font-weight: 700;
    font-size: 11px;
  }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin: 14px 0; }}
  .stat {{
    background: var(--bg-card-light);
    border-radius: 6px;
    padding: 10px 12px;
    text-align: center;
  }}
  .stat-num {{ font-size: 22px; font-weight: 700; }}
  .stat-label {{ font-size: 10px; color: var(--fg-dim); margin-top: 2px; }}
  .stat-e done-num {{ color: var(--success); }}
  .stat-e active-num {{ color: var(--accent); }}
  .stat-e pending-num {{ color: var(--muted); }}
  .stat-e failed-num {{ color: var(--danger); }}
  .stat-e skipped-num {{ color: var(--muted); }}
  .section {{ background: var(--bg-card); border: 1px solid var(--bg-card-light); border-radius: 8px; padding: 14px 20px; margin-bottom: 16px; }}
  .section-title {{ font-size: 14px; font-weight: 700; color: var(--accent); margin-bottom: 10px; display: flex; align-items: center; gap: 8px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th, td {{ padding: 6px 8px; text-align: left; border-bottom: 1px solid var(--bg-card-light); }}
  th {{ color: var(--fg-dim); font-weight: 600; font-size: 10px; text-transform: uppercase; }}
  .tid-row {{ display: grid; grid-template-columns: 28px 90px 50px 1fr 130px 100px; gap: 8px; align-items: center; padding: 4px 6px; border-bottom: 1px solid var(--bg-card-light); font-size: 11px; }}
  .tid-icon {{ font-size: 14px; text-align: center; }}
  .tid-pending {{ color: var(--muted); opacity: .6; }}
  .tid-active {{ background: var(--accent-glow); border-left: 3px solid var(--accent); padding-left: 3px; }}
  .tid-approved {{ background: rgba(16,185,129,.1); border-left: 3px solid var(--success); padding-left: 3px; }}
  .tid-section {{ font-weight: 600; }}
  .tid-skill {{ color: var(--fg-dim); font-size: 10px; }}
  .tid-template {{ background: var(--bg-card-light); padding: 2px 5px; border-radius: 3px; font-size: 9px; }}
  .tid-checkpoint {{ background: var(--warn); color: #000; padding: 1px 4px; border-radius: 3px; font-size: 9px; font-weight: 700; }}
  .eviltwin-badge {{ background: var(--danger); color: #fff; padding: 1px 5px; border-radius: 8px; font-size: 9px; font-weight: 700; }}
  .footer {{ text-align: center; color: var(--muted); font-size: 10px; padding: 14px; border-top: 1px solid var(--bg-card-light); margin-top: 20px; }}
  @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .4; }} }}
  .live {{ animation: pulse 2s infinite; }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div class="header-row">
      <div class="header-left">
        <div class="title">🔗 GOAL-CHAIN LIVE STATUS</div>
        <div class="subtitle">Run: <strong>{RUN_ID}</strong> · Projekt: <strong>{projekt}</strong></div>
        <div class="subtitle">Goal: {goal[:120]}</div>
      </div>
      <div class="header-right">
        <div class="status-pill live">● LIVE · {current_time}</div>
        <div class="subtitle" style="margin-top: 6px;">{status_text}</div>
      </div>
    </div>
  </div>

  <div class="progress-card">
    <div class="progress-header">
      <span style="color: var(--fg-dim); font-size: 11px; text-transform: uppercase;">Progress</span>
      <span class="progress-num">{done} / {total} TIDs&nbsp;&nbsp;<span style="font-size:16px; color: var(--accent);">{percent}%</span></span>
    </div>
    <div class="progress-bar-wrap">
      <div class="progress-bar">{percent}%</div>
    </div>
    <div class="stats-grid">
      <div class="stat"><div class="stat-num" style="color: var(--success);">✅ {done}</div><div class="stat-label">DONE</div></div>
      <div class="stat"><div class="stat-num" style="color: var(--accent);">🔄 {inprog}</div><div class="stat-label">ACTIVE</div></div>
      <div class="stat"><div class="stat-num" style="color: var(--muted);">⏳ {pending}</div><div class="stat-label">PENDING</div></div>
      <div class="stat"><div class="stat-num" style="color: var(--danger);">❌ {failed}</div><div class="stat-label">FAILED</div></div>
      <div class="stat"><div class="stat-num" style="color: var(--muted);">⏭ {skipped}</div><div class="stat-label">SKIPPED</div></div>
      <div class="stat"><div class="stat-num" style="color: #a78bfa;">🎯 {root_cause_done}</div><div class="stat-label">ROOT_CAUSE</div></div>
    </div>
  </div>

  <div class="section" style="background: linear-gradient(135deg, rgba(239,68,68,.1) 0%, var(--bg-card) 100%); border-color: rgba(239,68,68,.4);">
    <div class="section-title" style="color: var(--danger);">👯 Evil Twin Activity</div>
    <div style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px;">
      <div style="text-align: center; padding: 8px; background: var(--bg-card-light); border-radius: 4px;"><div style="font-size: 16px;">👯</div><div style="font-size: 9px; color: var(--fg-dim); margin-top: 2px;">brainstorming</div><div style="font-size: 11px; color: var(--success); font-weight: 700;">DONE</div></div>
      <div style="text-align: center; padding: 8px; background: var(--bg-card-light); border-radius: 4px;"><div style="font-size: 16px;">👯</div><div style="font-size: 9px; color: var(--fg-dim); margin-top: 2px;">writing-plans</div><div style="font-size: 11px; color: var(--success); font-weight: 700;">DONE</div></div>
      <div style="text-align: center; padding: 8px; background: var(--bg-card-light); border-radius: 4px;"><div style="font-size: 16px;">👯</div><div style="font-size: 9px; color: var(--fg-dim); margin-top: 2px;">architecture</div><div style="font-size: 11px; color: var(--success); font-weight: 700;">DONE</div></div>
      <div style="text-align: center; padding: 8px; background: var(--bg-card-light); border-radius: 4px;"><div style="font-size: 16px;">👯</div><div style="font-size: 9px; color: var(--fg-dim); margin-top: 2px;">writing-plans-v2</div><div style="font-size: 11px; color: var(--success); font-weight: 700;">DONE</div></div>
      <div style="text-align: center; padding: 8px; background: var(--bg-card-light); border-radius: 4px;"><div style="font-size: 16px;">👯</div><div style="font-size: 9px; color: var(--fg-dim); margin-top: 2px;">debugging</div><div style="font-size: 11px; color: var(--success); font-weight: 700;">DONE</div></div>
      <div style="text-align: center; padding: 8px; background: rgba(59,130,246,.15); border-radius: 4px; border: 2px solid var(--accent);"><div style="font-size: 16px;">👯</div><div style="font-size: 9px; color: var(--fg-dim); margin-top: 2px;">implementer-6</div><div style="font-size: 11px; color: var(--accent); font-weight: 700;">🔄 NEXT</div></div>
      <div style="text-align: center; padding: 8px; background: var(--bg-card-light); border-radius: 4px; opacity: .5;"><div style="font-size: 16px;">👯</div><div style="font-size: 9px; color: var(--fg-dim); margin-top: 2px;">docs-7</div><div style="font-size: 11px; color: var(--muted); font-weight: 700;">PENDING</div></div>
    </div>
    <div style="margin-top: 8px; font-size: 10px; color: var(--fg-dim); font-style: italic;">Each 👯 spawns a Mirror-Thinker after every Thinker-step. Aufgabe: fundamental widersprechen, komplett umgekehrt denken. FUNDAMENTAL-Rate: 15-30% der Durchläufe → Synthese.</div>
  </div>

  <div class="section">
    <div class="section-title">📊 All TIDs · Drift-Detection Ready</div>
"""

# TID rows
for tid, phase, section, status, skill, requires_approval, template_id in all_tids:
    icon, color = status_icons.get(status, ('?', 'gray'))
    row_class = ''
    if status == 'IN_PROGRESS':
        row_class = 'tid-active'
    elif status == 'DONE':
        row_class = 'tid-approved'
    elif status == 'PENDING':
        row_class = 'tid-pending'

    # Determine if evil-twin section
    evil_twin_badge = ''
    if 'evil-twin' in section:
        evil_twin_badge = ' <span class="eviltwin-badge">👯 EVIL TWIN</span>'

    checkpoint_badge = ''
    if str(requires_approval) == '1':
        checkpoint_badge = ' <span class="tid-checkpoint">🛑 CHECKPOINT</span>'

    phase_icon = phase_icons.get(phase, '·')
    skill_short = (skill or '').split('/')[-1]
    section_short = section[:24]

    html += f"""    <div class="tid-row {row_class}">
      <div class="tid-icon">{icon}</div>
      <div class="tid-phase">{phase_icon} {phase}</div>
      <div class="tid-status" style="color: {color}; font-weight: 700;">{status}</div>
      <div class="tid-section">{section_short}{evil_twin_badge}{checkpoint_badge}</div>
      <div class="tid-skill">{skill_short}</div>
      <div class="tid-template">{template_id or '—'}</div>
    </div>
"""

html += f"""  </div>

  <div class="grid-2">
    <div class="section">
      <div class="section-title">🎯 Current / Next</div>
"""
if next_tid:
    nt_info = next_tid[0]
    html += f"""      <div style="padding: 8px 12px; background: rgba(59,130,246,.15); border-radius: 6px;">
        <div style="color: var(--accent); font-weight: 700; margin-bottom: 4px;">{nt_info}</div>
        <div style="font-size: 11px; color: var(--fg-dim);">Waiting for completion of preceding TIDs or user checkpoint decision.</div>
      </div>"""
else:
    html += """      <div style="padding: 8px 12px; background: rgba(16,185,129,.15); border-radius: 6px;">
        <div style="color: var(--success); font-weight: 700;">🎉 ALL TIDs COMPLETE</div>
      </div>"""

html += f"""    </div>

    <div class="section">
      <div class="section-title">📜 Recent Decisions</div>
      <table>
        <thead><tr><th>TID</th><th>Decision</th><th>Value</th></tr></thead>
        <tbody>
"""
if recent_decisions:
    for tid, dt, dv, ts in recent_decisions:
        tid_short = tid.split('-')[-1][:18]
        dt_short = dt.replace('GATE_RESULT', 'GATE').replace('PATH_CHOICE', 'PATH')[:10]
        html += f"          <tr><td>{tid_short}</td><td>{dt_short}</td><td style='color: var(--accent);'>{dv[:20]}</td></tr>\n"
else:
    html += "          <tr><td colspan='3' style='color: var(--muted); text-align: center;'>No decisions yet</td></tr>\n"

html += f"""        </tbody>
      </table>
    </div>
  </div>

  <div class="footer">
    Auto-refresh: 2s · Generated: {current_time} · {RUN_ID}<br>
    DB: <code>.agents/skills/goal-chain/db/tid-state.db</code> · Snapshot: <code>{os.path.basename('$SNAPSHOT')}</code>
  </div>

</div>
</body>
</html>
"""

print(html, end='')
PYEOF

echo "$SNAPSHOT"
