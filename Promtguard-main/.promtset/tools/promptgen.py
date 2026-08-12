#!/usr/bin/env python3
"""
promptgen.py — Promtset-Automatisierung (R00-R12 konform)

Zweck:
  Wandelt rohe Aussagen ("baue mal auth ein") in projekt-spezifische,
  atomare Task-Prompts (R03/R09/R11) um -- aber NICHT direkt. Vorher
  wird IMMER ein read-only Research-Auftrag erzeugt, der den aktuellen
  Kontext aktualisiert (R01/R02), damit der finale Task-Prompt nicht auf
  veralteten Annahmen basiert.

Pipeline:
  1. `research`   Roh-Prompt -> read-only Research-Prompt (Datei)
                  -> das lässt du von einem Research-Agenten ausführen
                  -> der Agent liefert researcher-context/v1 JSON zurück
  2. `ingest`     JSON-Output des Research-Agenten einlesen, gegen
                  .promtset/schemas/researcher-context-v1.json validieren,
                  als Context-Token persistieren (R01), Entscheidungen ins
                  Journal schreiben (R05)
  3. `build`      Aus dem persistierten Context-Token + Roh-Prompt den
                  finalen atomaren Task-Prompt erzeugen (R03/R08/R09/R11)
  4. `resume`     INIT-Block aus dem State bauen, um einen NEUEN Agenten
                  (nach Provider-/Agenten-Wechsel) mit dem vollen
                  persistenten Kontext zu starten (R00/R01/R02)
  5. `handoff`    R04-Handoff manuell anlegen (für Wechsel außerhalb der
                  research/build-Pipeline)
  6. `context`    State inspizieren (show/list)

State liegt unter .promtset/state/ (JSONL, append-only -- R01 "Keine
Löschung"). Alle Kommandos sind reine Text-/Dateioperationen -- keine
Netzwerkzugriffe, kein Ausführen von LLM-Agenten. Das eigentliche
"Denken" (Recherche, Task-Ausführung) macht weiterhin der jeweilige
Agent; dieses Skript sorgt nur für Struktur + Persistenz zwischen den
Schritten.

Nutzung:
  python3 promptgen.py research  "roher prompt text"  [--agent NAME]
  python3 promptgen.py ingest    out/research-RES-001.json
  python3 promptgen.py build     RES-001
  python3 promptgen.py task-done TASK-001 --agent coder-1 --status completed --summary "..." [--decisions '...'] [--handoff-to promter]
  python3 promptgen.py resume    [-n 5]
  python3 promptgen.py handoff   --from implementer-1 --to tester-1 --note "..."
  python3 promptgen.py context   show [-n 10]
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Pfade / Konstanten
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]          # .promtset/
PROJECT_ROOT = ROOT.parent                            # Projektwurzel
STATE_DIR = ROOT / "state"
OUT_DIR = ROOT / "out"
SCHEMA_FILE = ROOT / "schemas" / "researcher-context-v2.json"
SCHEMA_FILE_V1 = ROOT / "schemas" / "researcher-context-v1.json"
RESEARCHER_TEMPLATE = ROOT / "agent-templates" / "code-researcher-prompt.md"

CONTEXT_LOG = STATE_DIR / "context-log.jsonl"
DECISION_JOURNAL = STATE_DIR / "decision-journal.jsonl"
CLAIM_LOG = STATE_DIR / "claim-log.jsonl"              # R13 — Claims (Verifikations-Atome)
HANDOFF_LOG = STATE_DIR / "handoffs.jsonl"
TASK_INDEX = STATE_DIR / "task-index.json"
CONSTRAINTS_FILE = PROJECT_ROOT / "constraints.json"  # Fix High #4: Statt .promtset/state/ nun Projekt-Root
PROJECTS_FILE = STATE_DIR / "projects.json"
PROMPTSET_VERSION = "2.0.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_state():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in (CONTEXT_LOG, DECISION_JOURNAL, HANDOFF_LOG):
        f.touch(exist_ok=True)
    if not TASK_INDEX.exists():
        TASK_INDEX.write_text(json.dumps({}, indent=2))
    if not CONSTRAINTS_FILE.exists():
        CONSTRAINTS_FILE.write_text(json.dumps({}, indent=2))


def read_jsonl(path: Path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            # Toleranz gegen einzelne kaputte Zeilen (Fix Medium #7)
            print(f"[warn] JSONL-Zeile übersprungen ({path.name}:{len(out) + 1}): {e}", file=sys.stderr)
    return out


def append_jsonl(path: Path, obj: dict):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_index() -> dict:
    ensure_state()
    return json.loads(TASK_INDEX.read_text(encoding="utf-8") or "{}")


def save_index(idx: dict):
    TASK_INDEX.write_text(json.dumps(idx, indent=2, ensure_ascii=False))


def next_task_id(prefix: str, idx: dict) -> str:
    n = 1
    existing = {k for k in idx.keys() if k.startswith(prefix + "-")}
    while f"{prefix}-{n:03d}" in existing:
        n += 1
    return f"{prefix}-{n:03d}"


def load_required_schema_fields(schema_file: Path = None) -> list:
    """Lade required-Felder aus dem passenden Schema.
    
    Fallback-Kette: v2 → v1 → []
    Fix Critical #3: vorher nur v2, ohne Fallback auf v1.
    """
    candidate = schema_file or SCHEMA_FILE
    if candidate.exists():
        schema = json.loads(candidate.read_text(encoding="utf-8"))
        return schema.get("required", [])
    # Fallback v1
    if candidate == SCHEMA_FILE and SCHEMA_FILE_V1.exists():
        schema = json.loads(SCHEMA_FILE_V1.read_text(encoding="utf-8"))
        return schema.get("required", [])
    return []


def load_projects() -> dict:
    ensure_state()
    if not PROJECTS_FILE.exists():
        PROJECTS_FILE.write_text(json.dumps({}, indent=2))
    return json.loads(PROJECTS_FILE.read_text(encoding="utf-8") or "{}")


def save_projects(proj: dict):
    PROJECTS_FILE.write_text(json.dumps(proj, indent=2, ensure_ascii=False))


def get_project_prefix() -> str:
    """Ermittelt den aktuellen Projekt-Prefix (3-5 chars) aus projects.json."""
    projects = load_projects()
    active = [k for k, v in projects.items() if v.get("active", False)]
    return active[0] if active else "GEN"  # GEN = GENERIC fallback


# ---------------------------------------------------------------------------
# R13 — Claims (Verifikations-Atome)
# ---------------------------------------------------------------------------
# Jede Research-Aussage IST ein Claim bis verifiziert. Eigene JSONL mit
# Latest-Wins-Semantik pro ID. ID-Format: CLAIM-{PREFIX}-{SEQ:03d}.

CLAIM_ID_PATTERN = re.compile(r"^CLAIM-([A-Z]{3,5})-(\d{3})$")


def _next_claim_max_seq(prefix: str) -> int:
    """Liest aktuellen max SEQ fuer CLAIM-{PREFIX}- aus dem Log (0 wenn leer).

    WICHTIG: Fuer BATCHES von Claims einmal lesen und dann SELBST im Loop
    inkrementieren. Mehrfach-Aufrufe von next_claim_id(prefix) ohne intervening
    Writes lesen DEN GLEICHEN Log-Stand und vergaben dieselbe SEQ.
    """
    raw = read_jsonl(CLAIM_LOG)
    pattern = re.compile(rf"^CLAIM-{prefix}-(\d{{3}})$")
    max_seq = 0
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        m = pattern.match(_safe_str(entry.get("id", "")))
        if m:
            try:
                max_seq = max(max_seq, int(m.group(1)))
            except (ValueError, TypeError):
                continue
    return max_seq


def _reserve_claim_seqs(prefix: str, count: int) -> list:
    """Reserviert `count` aufeinanderfolgende CLAIM-{PREFIX}-{SEQ:03d} IDs.

    EINMAL-Lesen + in-memory Inkrement. Garantiert unique IDs in der
    zurueckgegebenen Liste, auch wenn claim-log.jsonl sich zwischen den
    Aufrufen nicht aendert. Default-Wert fuer count<=0: leere Liste.
    """
    if count <= 0:
        return []
    start = _next_claim_max_seq(prefix)
    return [f"CLAIM-{prefix}-{start + i + 1:03d}" for i in range(count)]


def next_claim_id(prefix: str) -> str:
    """Convenience-Wrapper: einzelne CLAIM-{PREFIX}-{SEQ:03d} reservieren.

    Praktisch gleichwertig mit _reserve_claim_seqs(prefix, 1)[0]. Fuer alle
    BATCH-Operationen siehe _reserve_claim_seqs (atomar, single-Read + in-memory).
    """
    return _reserve_claim_seqs(prefix, 1)[0]  # count=1 garantiert nicht-leer


# ---------------------------------------------------------------------------
# R13 Idempotenz (sha256-Fingerprint gegen semantische Re-Ingest-Duplikate)
# ---------------------------------------------------------------------------
# Verhindert dass Re-Validation-Runden (z.B. RES-033 zweimal ingesTIERT) neue
# semantische Duplikat-IDs erzeugen. Bei Match: idempotent-merge via Trace
# ohne neue SEQ-Vergabe.

CLAIM_FP_SCHEMA = re.compile(r"^[a-f0-9]{64}$")  # sha256-hex


def _compute_idempotency_fingerprint(source_res: str, claim_text: str, evidence: str) -> str:
    """sha256 ueber normalisiertes (source_res, claim_text, evidence).

    Normalisierung: lowercase + strip. Verteidigt gegen harmlose Whitespace-/
    Case-Variationen zwischen Ingest-Episoden.
    """
    norm_text = (claim_text or "").strip().lower()
    norm_evidence = _safe_str(evidence, "").strip().lower()
    raw = f"{source_res}|{norm_text}|{norm_evidence}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _scan_existing_fingerprints() -> dict:
    """Liest EINMAL claim-log.jsonl und liefert fingerprint -> latest_claim_id.

    Latest-wins: bei mehreren Einträgen pro Fingerprint (z.B. nach Updates)
    wird der juengste behalten. Aufgerufen einmal pro cmd_ingest-Submit.
    """
    fps = {}
    for entry in read_jsonl(CLAIM_LOG):
        if not isinstance(entry, dict):
            continue
        fp = entry.get("idempotency_fingerprint")
        cid = entry.get("id")
        if isinstance(fp, str) and CLAIM_FP_SCHEMA.match(fp) and isinstance(cid, str):
            fps[fp] = cid  # latest-wins durch for-loop Order
    return fps


def append_claim(entry: dict, parent: dict = None):
    """Schreibt einen Claim-Eintrag in claim-log.jsonl (append-only).

    parent (optional): bestehender Eintrag mit identischer ID — aus diesem
    erbt der neue Eintrag created_at, promtset_version und origin.
    So bleibt die Origin-Geschichte erhalten, wenn ein Claim verifiziert wird.

    Ohne parent wird created_at = timestamp gesetzt (frischer Claim).
    """
    if parent:
        entry.setdefault("created_at", _safe_str(parent.get("created_at", entry.get("created_at", now_iso()))))
        entry.setdefault("claim_origin", _safe_str(parent.get("claim_origin", entry.get("claim_origin", "decision-extraction"))))
        entry.setdefault("promtset_version", _safe_str(parent.get("promtset_version", PROMPTSET_VERSION)))
    entry.setdefault("timestamp", now_iso())
    entry.setdefault("promtset_version", PROMPTSET_VERSION)
    # Fallback: frischer Claim OHNE parent -> created_at = timestamp
    if "created_at" not in entry:
        entry["created_at"] = entry["timestamp"]
    with CLAIM_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def resolve_claims(prefix: str = None, status: str = None) -> list:
    """Liest claim-log.jsonl und gibt latest-wins pro Claim-ID zurueck.

    Optional-Filter: prefix (CLAIM-{PREFIX}-...) und status (latest Status).
    """
    raw = read_jsonl(CLAIM_LOG)
    by_id = {}  # id -> letzter Eintrag (latest-wins)
    order = []  # Erstauftretens-Reihenfolge
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        cid = _safe_str(entry.get("id", ""))
        if not CLAIM_ID_PATTERN.match(cid):
            continue
        if cid not in by_id:
            order.append(cid)
        by_id[cid] = entry  # latest wins (Append-Only: letzte Zeile gewinnt)
    out = [by_id[cid] for cid in order]
    if prefix:
        out = [c for c in out if _safe_str(c.get("id", "")).startswith(f"CLAIM-{prefix}-")]
    if status:
        out = [c for c in out if _safe_str(c.get("status", "")) == status]
    return out


def get_claim_history(claim_id: str) -> list:
    """Alle Eintraege zu einer Claim-ID (chronologisch), inkl. Updates."""
    raw = read_jsonl(CLAIM_LOG)
    return [e for e in raw if isinstance(e, dict) and _safe_str(e.get("id", "")) == claim_id]


def extract_claims_from_decisions(decisions: list, source_res: str, prefix: str, existing_fps: dict = None) -> tuple:
    """Erzeugt Claims aus decisions[] (eine Decision mit evidence = ein Claim).

    Nutzt _reserve_claim_seqs fuer atomare Batch-ID-Vergabe (kein Duplicate-Bug).
    Returns (count, claim_index_map) fuer cmd_ingest/Mapping.

    Idempotenz (2026-07-28): Wenn existing_fps dict uebergeben wird, Kandidaten mit
    bereits existierendem fingerprint werden als idempotent_re_ingest Updates
    geschrieben (kein Capture-Failure weil R13 append-only). Verhindert Re-Ingest
    Duplikate (CLAIM-SYX-006..010 vs 011..015 Bug, RES-033 Cleanup).
    """
    # Phase 1: Filtere kandidierende Decisions + fingerprints
    candidates = []  # [(idx, claim_text, evidence, confidence, alternatives, fp), ...]
    idempotent_updates = []  # [(existing_id, fp)]
    use_idempotency = isinstance(existing_fps, dict) and len(existing_fps) > 0
    for idx, dec in enumerate(decisions or []):
        if not isinstance(dec, dict):
            continue
        evidence = _safe_str(dec.get("evidence", "")) or None
        if not evidence or evidence == "?":
            continue
        claim_text = _safe_str(dec.get("what", "")).strip()
        if not claim_text:
            continue
        fp = _compute_idempotency_fingerprint(source_res, claim_text, evidence)
        if use_idempotency and fp in existing_fps:
            idempotent_updates.append((existing_fps[fp], fp))
            continue
        candidates.append((
            idx, claim_text, evidence,
            _safe_str(dec.get("confidence", "medium")),
            _coerce_str_list(dec.get("alternatives_rejected", [])),
            fp,
        ))
    # Phase 2: Reserviere alle neuen IDs atomar (single-Read + in-memory counter)
    claim_index_map = {}
    if candidates:
        new_ids = _reserve_claim_seqs(prefix, len(candidates))
        for i, candidate in enumerate(candidates):
            claim_index_map[candidate[0]] = new_ids[i]
    # Phase 3a: Schreibe frische Claims mit festen IDs
    for idx, claim_text, evidence, confidence, alternatives, fp in candidates:
        append_claim({
            "id": claim_index_map[idx],
            "claim": claim_text,
            "evidence": evidence,
            "confidence": confidence,
            "source_res": source_res,
            "source_decision_index": idx,
            "claim_origin": "decision-extraction",
            "idempotency_fingerprint": fp,
            "status": "unverified",
            "alternatives_rejected": alternatives,
        })
    # Phase 3b: Idempotent-Merge Updates (append-only, latest-wins per ID).
    # status wird BEWUSST NICHT geschrieben — latest-wins erbt sonst unverified und
    # koennte zuvor erreichten verified/refuted Status ueberschreiben (2026-07-28 Code-Review).
    for existing_id, fp in idempotent_updates:
        append_claim({
            "id": existing_id,
            "claim_origin": "idempotent_re_ingest",
            "source_res": source_res,
            "idempotency_fingerprint": fp,
        })
    return (len(candidates), claim_index_map)


def next_ctx_id(phase: str, task_id: str = "") -> str:
    """Deterministische CTX-ID: CTX-{PREFIX}-{PHASE}-{SEQ}
    
    Phasen: INIT, RES, TASK, FIX, REVIEW
    SEQ: fortlaufende 3-stellige Nummer pro Phase
    
    Zählt aus context-log.jsonl, NICHT aus task-index.json
    (Fix Critical #1: vorher wurde fälschlich task-index durchsucht)
    """
    prefix = get_project_prefix()
    tokens = read_jsonl(CONTEXT_LOG)
    existing = [t for t in tokens if t.get("id", "").startswith(f"CTX-{prefix}-{phase}-")]
    seq = len(existing) + 1
    return f"CTX-{prefix}-{phase}-{seq:03d}"


# ---------------------------------------------------------------------------
# Kontext-Snapshot: liest den persistierten State und fasst ihn kompakt
# zusammen (für TEIL 1 / INIT-Blöcke)
# ---------------------------------------------------------------------------

def context_snapshot(n: int = 5) -> dict:
    tokens = read_jsonl(CONTEXT_LOG)[-n:]
    decisions = read_jsonl(DECISION_JOURNAL)[-n:]
    handoffs = read_jsonl(HANDOFF_LOG)[-n:]
    return {"tokens": tokens, "decisions": decisions, "handoffs": handoffs}


# ---------------------------------------------------------------------------
# Defensive Helpers (Fix Bug-Cluster: format_context_tokens_md Zeile 226)
# ---------------------------------------------------------------------------
# Vorher (Bug): `r.get('file','?')` schlug fehl wenn ein code_refs-Item ein
# String statt ein Dict war ('str' object has no attribute 'get').
# Fix: Helper _safe_get prüft isinstance(entry, dict) ZUERST und vermeidet
# damit den Crash bei legacy / malformed Einträgen in context-log.jsonl.

def _safe_str(value, default="?"):
    """Robuste String-Konvertierung — akzeptiert beliebige Typen."""
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _safe_get(entry, key, default="?"):
    """Safe .get() — wirkt NUR auf dict-Instanzen, sonst default."""
    if not isinstance(entry, dict):
        return default
    return entry.get(key, default)


def _coerce_str_list(value):
    """Konvertiert eine Liste beliebiger Elemente in eine reine String-Liste."""
    if not isinstance(value, list):
        return []
    return [str(item) if not isinstance(item, str) else item for item in value]


def format_context_tokens_md(tokens: list) -> str:
    if not tokens:
        return "(noch keine persistierten Context-Token -- erster Lauf)"
    lines = []
    for t in tokens:
        if not isinstance(t, dict):
            continue  # Defensive: malformed Token überspringen
        cid = _safe_get(t, "id")
        src = _safe_get(t, "source_task_id")
        rp = _safe_get(t, "roadmap_phase", "unbekannt")
        cc = t.get("collected_context", [])
        parts = []
        # Handle both v1 (list) and v2 (dict) formats
        if isinstance(cc, dict):
            for key, entries in cc.items():
                if isinstance(entries, list):
                    for e in entries[:2]:
                        if isinstance(e, dict):
                            parts.append(f"{key}.{_safe_get(e, 'method')}")
                        else:
                            parts.append(f"{key}")
                elif isinstance(entries, dict):
                    if len(parts) < 6:
                        parts.append(f"{key}={_safe_get(entries, 'value')}")
                else:
                    if len(parts) < 6:
                        parts.append(str(key))
        elif isinstance(cc, list):
            for c in cc[:6]:
                if isinstance(c, dict):
                    parts.append(f"{_safe_get(c, 'category')}.{_safe_get(c, 'key')}={_safe_get(c, 'value')}")
                else:
                    parts.append(str(c))
        cc_str = "; ".join(parts)
        # 🔴 HIGH: code_refs + diff_stats
        refs = t.get("code_refs", [])
        ref_str = ""
        if isinstance(refs, list) and refs:
            ref_parts = []
            for r in refs[:3]:
                if isinstance(r, dict):
                    ref_parts.append(f"{_safe_get(r, 'file')}:{_safe_get(r, 'line')}")
                elif isinstance(r, str):
                    ref_parts.append(r)  # String-Eintrag direkt übernehmen
                else:
                    ref_parts.append(str(r))
            if ref_parts:
                ref_str = f" [REFs: {', '.join(ref_parts)}]"
        diff = t.get("diff_stats", "")
        diff_str = f" ({diff})" if isinstance(diff, str) and diff else ""
        # 🟡 MEDIUM: remaining_tasks
        rem = t.get("remaining_tasks", [])
        rem_str = ""
        if isinstance(rem, list) and rem:
            rem_items = _coerce_str_list(rem)
            if rem_items:
                rem_str = f" ⏳{','.join(rem_items)}"
        lines.append(f"- [{cid}] (aus {src}, Roadmap-Phase: {rp}): {cc_str}{ref_str}{diff_str}{rem_str}")
    return "\n".join(lines)


def format_decisions_md(decisions: list) -> str:
    if not decisions:
        return "(noch keine Einträge im Entscheidungs-Journal)"
    lines = []
    for d in decisions:
        if not isinstance(d, dict):
            continue
        lines.append(
            f"- {_safe_get(d, 'what')} -- {_safe_get(d, 'why', '')} "
            f"(Confidence: {_safe_get(d, 'confidence')}, Quelle: {_safe_get(d, 'source_task_id')})"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Kommando: research
# ---------------------------------------------------------------------------

RESEARCH_PROMPT_TMPL = """\
## ANWEISUNG

Projekt: {project_name}
Sprache: {language} | Build: {build_system}
Task-ID: {task_id}

Auftrag:
> "{raw_prompt}"

### REGELN (JEDE Regelverletzung = ungültiges Ergebnis)

1. **NUR lesen** — kein Schreiben, kein Bauen, kein Testen
2. **Jede Code-Referenz** MUSS Format `datei.java:42:methodenName` — Zeile = INTEGER (42), niemals String ("42")
3. **`method` NIE null** — bei Felddeklaration stattdessen "field-declaration", bei Klassen-Level "class-level", bei Interface "interface-def"
4. **`context`-Feld PFLICHT** bei jedem collected_context-Eintrag — erkläre WARUM die Zeile relevant ist
5. **NUR JSON ausgeben** — null Fließtext, null Markdown, null Erklärungen
6. **Bei Unsicherheit:** `{{"error": {{"type": "unsicher", "reason": "...", "needs_clarification": true}}}}`
7. **Bei nichts gefunden:** `{{"collected_context": {{}}, "summary": "keine relevante Information gefunden"}}`

### Ausführung (IN DIESER REIHENFOLGE)

1. Projektstruktur erkunden (NUR lesen)
2. `collected_context` sammeln — JEDER Eintrag MUSS enthalten: file, line (int), method (nicht null), content, context
3. `evidence`-Liste füllen — mindestens 1 Eintrag PRO KATEGORIE im Format `datei.java:42:relevanter code-ausschnitt`
4. GENAU EINEN `atomic_task_prompt` formulieren (was, scope_in, scope_out, abgrenzung, target_agent)
   - `abgrenzung` MUSS existierende RES-IDs referenzieren (z.B. "Abgrenzung zu RES-002: ...")
5. `decisions` dokumentieren — JEDE decision MUSS `evidence` mit `file:line`-Referenz enthalten
6. **AUSSCHLIESSLICH JSON ausgeben**

## STRIKTE OUTPUT-ANWEISUNG

Du MUSST exakt dieses JSON ausgeben. KEINE zusätzlichen Felder. KEIN Text außerhalb.

```json
{{
  "schema": "researcher-context/v2",
  "agent": "<dein-name>",
  "task_id": "{task_id}",
  "roadmap_found": true,
  "roadmap_phase": "<phase-oder-null>",
  "collected_context": {{
    "kategorie_1": [
      {{"file": "src/...", "line": 42, "method": "methodenName", "content": "code-ausschnitt", "context": "WARUM diese Zeile wichtig ist"}}
    ],
    "kategorie_2": [
      {{"file": "src/...", "line": 99, "method": "andereMethode", "content": "code-ausschnitt", "context": "Erklärung"}}
    ]
  }},
  "live_testing_threshold": {{
    "reasoning": "<begruendung>",
    "testing_boundary": "<grenze>",
    "needs_live_testing": false
  }},
  "atomic_task_prompt": {{
    "was": "<GENAU EINE Aufgabe>",
    "scope_in": "<was ist im scope>",
    "scope_out": ["<was ist NICHT im scope>"],
    "abgrenzung": "<abgrenzung zu RES-XXX: ...>",
    "live_testing_required": false,
    "target_agent": "implementer-1"
  }},
  "decisions": [
    {{
      "what": "<entscheidung>",
      "why": "<begruendung>",
      "evidence": "datei.java:42:relevanter code",
      "alternatives_rejected": ["<alternative>: <grund>"],
      "confidence": "high|medium|low"
    }}
  ],
  "evidence": [
    "datei.java:42:code-ausschnitt"
  ],
  "summary": "<1-3 Saetze Zusammenfassung>",
  "original_prompt": "<originaler user-auftrag>"
}}
```
"""


def cmd_research(args):
    ensure_state()
    idx = load_index()
    task_id = args.task_id or next_task_id("RES", idx)
    snap = context_snapshot(n=args.context_window)

    # Projekt-Metadaten laden (sprachagnostisch)
    projects = load_projects()
    active = [p for p in projects.values() if p.get("active")]
    proj = active[0] if active else {}

    prompt = RESEARCH_PROMPT_TMPL.format(
        project_name=args.project or proj.get("name", PROJECT_ROOT.name),
        language=proj.get("language", "?"),
        build_system=proj.get("build_system", "?"),
        task_id=task_id,
        raw_prompt=args.raw_prompt.strip(),
    )  # KEINE toten Parameter mehr (Fix Medium #6)

    out_file = OUT_DIR / f"{task_id}-research-prompt.md"
    out_file.write_text(prompt, encoding="utf-8")

    idx[task_id] = {
        "type": "research",
        "status": "prompt_generated",
        "raw_prompt": args.raw_prompt.strip(),
        "created": now_iso(),
        "prompt_file": str(out_file.relative_to(PROJECT_ROOT)),
    }
    if args.agent:
        idx[task_id]["target_agent"] = args.agent
    save_index(idx)

    print(f"[research] Task-ID: {task_id}")
    print(f"[research] Read-only Research-Prompt geschrieben nach: {out_file}")
    print("[research] Nächster Schritt: Prompt an einen Research-Agenten geben "
          "(read-only Tools/Session), Antwort als JSON speichern, dann:")
    print(f"           python3 {Path(__file__).name} ingest <pfad-zur-json> --task-id {task_id}")
    if not args.quiet:
        print("\n" + "=" * 70)
        print(prompt)


# ---------------------------------------------------------------------------
# Kommando: ingest
# ---------------------------------------------------------------------------

def cmd_ingest(args):
    ensure_state()
    src = Path(args.json_file)
    if not src.exists():
        sys.exit(f"[ingest] Datei nicht gefunden: {src}")

    raw = src.read_text(encoding="utf-8")
    # Tolerant gegen führenden/nachgestellten Freitext um das JSON herum
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            sys.exit("[ingest] Kein valides JSON gefunden.")
        data = json.loads(match.group(0))

    schema_val = data.get("schema")
    # Akzeptiere v1, v2, und command-result/v1
    valid_schemas = ["researcher-context/v1", "researcher-context/v2", "command-result/v1"]
    if schema_val not in valid_schemas:
        sys.exit(f"[ingest] FEHLGESCHLAGEN -- schema-Feld ist "
                  f"'{schema_val}', erwartet eines von {valid_schemas}")
    
    # Wähle Schema-Version basierend auf JSON-Deklaration
    schema_file = SCHEMA_FILE if schema_val == "researcher-context/v2" else SCHEMA_FILE_V1
    required = load_required_schema_fields(schema_file)
    missing = [f for f in required if f not in data]
    if missing:
        sys.exit(f"[ingest] FEHLGESCHLAGEN -- Schema-Verstoß (Schema: {schema_val}), "
                  f"fehlende Pflichtfelder: {missing}")

    idx = load_index()
    task_id = args.task_id or data.get("task_id") or next_task_id("RES", idx)

    ctx_id = next_ctx_id("RES", task_id)
    token = {
        "id": ctx_id,
        "timestamp": now_iso(),
        "source_task_id": task_id,
        "agent": data.get("agent"),
        "roadmap_found": data.get("roadmap_found"),
        "roadmap_phase": data.get("roadmap_phase"),
        "collected_context": data.get("collected_context", []),
        "live_testing_threshold": data.get("live_testing_threshold", {}),
        "atomic_task_prompt": data.get("atomic_task_prompt", {}),
        "original_prompt": data.get("original_prompt"),
    }
    append_jsonl(CONTEXT_LOG, token)

    decisions = data.get("decisions", []) or []
    for d in decisions:
        if not isinstance(d, dict):
            continue
        dd = dict(d)
        dd.setdefault("source_task_id", task_id)
        dd.setdefault("timestamp", now_iso())
        append_jsonl(DECISION_JOURNAL, dd)    # R13 — Claims: automatische Extraktion + Deklarationen + Verifikation
    prefix = get_project_prefix()
    claims_created = 0
    # Idempotenz-Cache: Einmal lesen, an alle 3 Quellen weitergeben (claims[],
    # extract_claims_from_decisions, verified_claims). Verhindert dass Re-Ingests
    # neue semantische Duplikat-SEQs erzeugen (siehe RES-033 Cleanup 2026-07-28).
    existing_fps = _scan_existing_fingerprints()
    # 1) claims[] -> explizite Claim-Deklarationen.
    # 3-Phasen-Pattern + Idempotenz (siehe historische Notiz unten).
    candidates_explicit = []
    idempotent_updates_explicit = []  # [(existing_id, fp), ...]
    for idx_c, claim_entry in enumerate(data.get("claims", []) or []):
        if not isinstance(claim_entry, dict):
            continue
        claim_text = _safe_str(claim_entry.get("claim", "")).strip()
        evidence = _safe_str(claim_entry.get("evidence", ""))
        if not claim_text or not evidence:
            continue
        confidence = _safe_str(claim_entry.get("confidence", "medium"))
        fp = _compute_idempotency_fingerprint(task_id, claim_text, evidence)
        if fp in existing_fps:
            idempotent_updates_explicit.append((existing_fps[fp], fp))
        else:
            candidates_explicit.append((claim_text, evidence, confidence, fp))
    explicit_ids = _reserve_claim_seqs(prefix, len(candidates_explicit))
    explicit_index_map = {}
    for i, (claim_text, evidence, confidence, fp) in enumerate(candidates_explicit):
        cid = explicit_ids[i]
        explicit_index_map[i] = cid
        append_claim({
            "id": cid,
            "claim": claim_text,
            "evidence": evidence,
            "confidence": confidence,
            "source_res": task_id,
            "claim_origin": "explicit-declaration",
            "idempotency_fingerprint": fp,
            "status": "unverified",
        })
    for existing_id, fp in idempotent_updates_explicit:
        append_claim({
            "id": existing_id,
            "claim_origin": "idempotent_re_ingest",
            "source_res": task_id,
            "idempotency_fingerprint": fp,
            "status": "unverified",
        })
    claims_created += len(candidates_explicit)
    # 2) decisions[] -> auto-extract Claims (1 Claim pro Decision mit evidence)
    extracted_count, claim_index_map = extract_claims_from_decisions(
        decisions, task_id, prefix, existing_fps=existing_fps
    )
    claims_created += extracted_count
    # Idempotente Updates in die cross-Batch Map einfliessen lassen
    for existing_id, fp in idempotent_updates_explicit:
        claim_index_map[len(claim_index_map)] = existing_id

    # 3) verified_claims[] -> Status-Updates bestehender Claims (append, latest-wins)
    verified_updates = 0
    # Merge: claim_index_map (aktueller Ingest, atomare ID-Vergabe via
    # _reserve_claim_seqs) + Fallback via Log-Read fuer Cross-Batch-Refs.
    recent = read_jsonl(CLAIM_LOG)
    full_index = {}
    index_to_id = dict(claim_index_map)  # current-ingest Map zuerst (overwrite-safe)
    for entry in recent:
        if not isinstance(entry, dict) or not CLAIM_ID_PATTERN.match(_safe_str(entry.get("id", ""))):
            continue
        cid = entry["id"]
        full_index[cid] = entry  # latest-wins innerhalb dieses Reads
        if entry.get("source_res") == task_id:
            sdi = entry.get("source_decision_index")
            if isinstance(sdi, int) and sdi not in index_to_id:
                index_to_id[sdi] = cid
    for vc in data.get("verified_claims", []) or []:
        if not isinstance(vc, dict):
            continue
        status = _safe_str(vc.get("status", "")).strip()
        if status not in ("verified", "refuted", "refined"):
            continue
        target_id = _safe_str(vc.get("claim_id", "")).strip()
        if not target_id:
            ci = vc.get("claim_index", -1)
            if isinstance(ci, int) and ci in index_to_id:
                target_id = index_to_id[ci]
            else:
                sys.exit(f"[ingest] verified_claim ohne claim_id und ohne mapbaren claim_index "
                          f"({ci}); bitte claim_id explizit angeben.")
        existing = full_index.get(target_id)
        new_entry = {
            "id": target_id,
            "claim": _safe_str(vc.get("claim", (existing or {}).get("claim", ""))).strip() or (existing or {}).get("claim", ""),
            "status": status,
            "source_res": _safe_str((existing or {}).get("source_res", task_id)),
            "verified_by_res": task_id,
            "verified_at": now_iso(),
            "verified_evidence": _safe_str(vc.get("evidence", "")),
            "confidence": _safe_str((existing or {}).get("confidence", "medium")),
            "alternatives_rejected": _coerce_str_list(vc.get("alternatives_rejected", (existing or {}).get("alternatives_rejected", []))),
        }
        # claim_origin wird via parent=existing in append_claim geerbt (kein doppeltes Setzen)
        append_claim(new_entry, parent=existing)
        # full_index auf aktuellen Stand bringen -> Multi-Verify im selben Ingest
        # referenziert den jeweils letzten Eintrag als parent
        full_index[target_id] = dict(new_entry)
        verified_updates += 1

    idx.setdefault(task_id, {})
    idx[task_id].update({
        "type": "research",
        "status": "ingested",
        "context_token_id": ctx_id,
        "ingested_at": now_iso(),
        "research_json": str(src),
        "claims_created": claims_created,
        "verified_claim_updates": verified_updates,
    })
    save_index(idx)

    print(f"[ingest] OK -- Context-Token {ctx_id} persistiert (Quelle: {task_id})")
    print(f"[ingest] {len(decisions)} Entscheidung(en) ins Journal geschrieben")
    print(f"[ingest] {claims_created} Claim(s) neu angelegt (davon {len(data.get('claims', []) or [])} explizit, {extracted_count} aus decisions[] extrahiert)")
    print(f"[ingest] {verified_updates} Verifikations-Update(s) verarbeitet")
    print(f"[ingest] Nächster Schritt: python3 {Path(__file__).name} build {task_id}")


# ---------------------------------------------------------------------------
# Kommando: build  (Roh-Prompt + Research-Kontext -> finaler Task-Prompt)
# ---------------------------------------------------------------------------

TASK_PROMPT_TMPL = """\
## ANWEISUNG

Projekt: {project_name}

### Scope

IN SCOPE:
{scope_in}

NICHT IN SCOPE:
{scope_out}

### Ausführung

{instruction}

### Regeln

- **GENAU DAS** umsetzen, was in Scope steht — nichts darüber hinaus
- **Jede Änderung** dokumentieren: datei, zeile, methode
- **NUR das JSON ausgeben** (siehe Output-Anweisung)

## STRIKTE OUTPUT-ANWEISUNG

Nach Abschluss MUSS exakt dieses JSON ausgegeben werden:

```json
{{
  "id": "CTX-{ctx_id_placeholder}",
  "timestamp": "<ISO-8601>",
  "task": "<task-beschreibung>",
  "status": "completed",
  "summary": "<1-3 Saetze was gemacht wurde>",
  "code_refs": [
    {{"file": "<dateipfad>", "line": 42, "method": "<methodenname>"}}
  ],
  "diff_stats": "+N -M"
}}
```

Pflichtfelder: id, timestamp, task, status, summary
code_refs MUSS array von {{file, line (int), method}} sein
diff_stats MUSS format "+N -M" sein
"""


def cmd_build(args):
    ensure_state()
    idx = load_index()
    # LATEST-Alias 2026-07-28: neuesten ingested Research-Context wählen statt task-id abtippen
    if args.task_id == "latest":
        res_keys = [k for k in idx if k.startswith("RES-") and "context_token_id" in idx[k]]
        if not res_keys:
            sys.exit("[build] 'latest' hat keine ingested Research-Contexts im Index")
        args.task_id = sorted(res_keys)[-1]
    entry = idx.get(args.task_id)
    if not entry or "context_token_id" not in entry:
        sys.exit(f"[build] Kein ingested Research-Context für Task-ID '{args.task_id}' "
                  f"gefunden. Erst `ingest` ausführen.")

    tokens = read_jsonl(CONTEXT_LOG)
    token = next((t for t in tokens if t["id"] == entry["context_token_id"]), None)
    if token is None:
        sys.exit(f"[build] Context-Token {entry['context_token_id']} nicht im Log gefunden.")

    decisions = [d for d in read_jsonl(DECISION_JOURNAL) if isinstance(d, dict) and d.get("source_task_id") == args.task_id]
    atp = token.get("atomic_task_prompt", {}) or {}

    cc = token.get("collected_context", [])
    cc_parts = []
    if isinstance(cc, dict):
        # v2 dict-Format: {"gruppe": [{file,line,method,content,context}, ...]}
        for group, entries in cc.items():
            for e in entries if isinstance(entries, list) else [entries]:
                if isinstance(e, dict):
                    loc = f"{e.get('file','?')}:{e.get('line','?')}:{e.get('method','?')}"
                    snippet = (e.get('content','') or '')[:80]
                    cc_parts.append(f"- [{group}] {loc} -- {snippet}")
                else:
                    cc_parts.append(f"- [{group}] {e}")
    else:
        # v1 list-Format: [{category, key, value, source, confidence}]
        for c in cc:
            if isinstance(c, dict):
                cc_parts.append(
                    f"- [{c.get('category','?')}] {c.get('key','?')} = {c.get('value','?')} "
                    f"(Quelle: {c.get('source','?')}, Confidence: {c.get('confidence','?')})"
                )
            else:
                cc_parts.append(f"- {c}")
    cc_str = "\n".join(cc_parts) or "(keine gesammelten Einträge -- ggf. research erneut ausführen)"

    dec_str = "\n".join(
        f"- {d.get('what','?')} -- {d.get('why','')} (Confidence: {d.get('confidence','?')})"
        for d in decisions
    ) or "(keine)"

    lt = token.get("live_testing_threshold", {}) or {}
    lt_str = lt.get("reasoning") or lt.get("testing_boundary") or "nicht bewertet"

    raw_prompt = args.raw_prompt or token.get("original_prompt") or ""
    target_agent = args.target_agent or atp.get("target_agent") or "implementer-1"
    instruction = args.instruction or atp.get("was") or (
        f"[MANUELL AUSFÜLLEN -- kein atomic_task_prompt im Research-Output gefunden]\n"
        f"Roh-Auftrag: {raw_prompt}"
    )
    scope_out = args.scope_out or atp.get("abgrenzung") or "[MANUELL ERGÄNZEN]"
    scope_in = args.scope_in or instruction

    task_id = next_task_id("TASK", idx)
    prompt = TASK_PROMPT_TMPL.format(
        project_name=args.project or PROJECT_ROOT.name,
        version=PROMPTSET_VERSION,
        source_task_id=args.task_id,
        ctx_id=token["id"],            ctx_id_placeholder=f"CTX-{get_project_prefix()}-TASK-XXX",
        task_id_output=task_id,
        roadmap_phase=token.get("roadmap_phase") or "unbekannt",
        collected_context=cc_str,
        decisions=dec_str,
        raw_prompt=raw_prompt.strip(),
        scope_in=scope_in,
        scope_out=scope_out,
        live_testing=lt_str,
        target_agent=target_agent,
        instruction=instruction,
    )

    out_file = OUT_DIR / f"{task_id}-task-prompt.md"
    out_file.write_text(prompt, encoding="utf-8")

    idx[task_id] = {
        "type": "task",
        "status": "prompt_generated",
        "source_research_task": args.task_id,
        "target_agent": target_agent,
        "created": now_iso(),
        "prompt_file": str(out_file.relative_to(PROJECT_ROOT)),
    }
    save_index(idx)

    print(f"[build] Task-ID: {task_id} (Ziel-Agent: {target_agent})")
    print(f"[build] Finaler Task-Prompt geschrieben nach: {out_file}")
    if not args.quiet:
        print("\n" + "=" * 70)
        print(prompt)


# ---------------------------------------------------------------------------
# Kommando: resume  (persistenter Kontext nach Agenten-/Provider-Wechsel)
# ---------------------------------------------------------------------------

RESUME_TMPL = """\
## KONTEXT-WIEDERHERSTELLUNG

Projekt: {project_prefix}
{project_info}

### Letzte Context-Token ({n} von {total})
{tokens}

### Letzte Entscheidungen
{decisions}

### Letzte Handoffs
{handoffs}

### Constraints
{constraints}

Letzter Context-Token: {last_ctx_id}
—
"""


def cmd_resume(args):
    ensure_state()
    snap = context_snapshot(n=args.n)
    tokens = snap["tokens"]
    # Defensive: falls handoffs.jsonl komplett korrupt ist, snap["handoffs"] könnte fehlen
    raw_handoffs = snap.get("handoffs") or []
    handoffs_list = raw_handoffs if isinstance(raw_handoffs, list) else []
    handoffs_str = "\n".join(
        f"- {_safe_get(h, 'timestamp')}: {_safe_get(h, 'from')} -> {_safe_get(h, 'to')} :: {_safe_get(h, 'note', '')}"
        for h in handoffs_list if isinstance(h, dict)
    ) or "(keine)"

    constraints = json.loads(CONSTRAINTS_FILE.read_text(encoding="utf-8") or "{}")
    constraints_str = "\n".join(
        f"- {k}: {v.get('value','?')} (von {v.get('updated_by','?')}, {v.get('updated_at','?')})"
        for k, v in constraints.items()
    ) or "(keine Constraints persistiert — promptgen.py constraints init ausführen)"

    # Projekt-Metadaten
    projects = load_projects()
    active = [p for p in projects.values() if p.get("active")]
    proj = active[0] if active else {}
    prefix = proj.get("prefix", "?")
    proj_str = f"{proj.get('name','?')} ({proj.get('language','?')}, {proj.get('build_system','?')}, test: {proj.get('test_command','?')})" if proj else "(kein Projekt registriert — promptgen.py project init ...)"

    text = RESUME_TMPL.format(
        version=PROMPTSET_VERSION,
        project_prefix=prefix,
        project_info=proj_str,
        n=len(tokens),
        total=len(read_jsonl(CONTEXT_LOG)),
        tokens=format_context_tokens_md(tokens),
        decisions=format_decisions_md(snap["decisions"]),
        handoffs=handoffs_str,
        constraints=constraints_str,
        last_ctx_id=tokens[-1]["id"] if tokens else "(keiner -- Erststart)",
    )
    print(text)


# ---------------------------------------------------------------------------
# Kommando: project init  (INIT: Projekt-Metadaten für sprachagnostischen Betrieb)
# ---------------------------------------------------------------------------

def cmd_project_init(args):
    ensure_state()
    projects = load_projects()

    # Deaktiviere alle bestehenden Projekte
    for k in projects:
        projects[k]["active"] = False

    # Neues Projekt anlegen
    prefix = (args.prefix or args.name[:3]).upper()[:5]
    projects[prefix] = {
        "name": args.name,
        "prefix": prefix,
        "active": True,
        "language": args.language or "unknown",
        "build_system": args.build or "unknown",
        "test_command": args.test or "unknown",
        "framework": args.framework or "none",
        "created": now_iso(),
    }
    save_projects(projects)

    print(f"[project] INIT: {args.name}")
    print(f"  Prefix:     {prefix}")
    print(f"  Sprache:    {args.language or '?'}")
    print(f"  Build:      {args.build or '?'}")
    print(f"  Test:       {args.test or '?'}")
    print(f"  Framework:  {args.framework or '?'}")
    print(f"[project] CTX-IDs jetzt: CTX-{prefix}-{{PHASE}}-{{SEQ}}")


def cmd_project_show(args):
    projects = load_projects()
    if not projects:
        print("(keine Projekte registriert — promptgen.py project init ...)")
        return
    print("### Registrierte Projekte ###")
    for prefix, p in projects.items():
        active = "★ AKTIV" if p.get("active") else "  inaktiv"
        print(f"- [{prefix}] {p.get('name','?')} ({p.get('language','?')}, {p.get('build_system','?')}) {active}")


# ---------------------------------------------------------------------------
# Kommando: self-improve (R07 — Gentische Prompt-Verbesserung)
# ---------------------------------------------------------------------------

IMPROVE_TMPL = """\
# Self-Improvement Report ({version}) — {timestamp}

## Analyse ({total_tokens} Context-Token, {total_decisions} Entscheidungen)

### Erfolgreiche Patterns
{good_patterns}

### Fehlermuster
{bad_patterns}

### Verbesserte Prompt-Regeln
{improvements}

---
*Generiert durch promptgen.py self-improve. Review und merge in PROMPTSET.md.*
"""


def cmd_self_improve(args):
    ensure_state()
    tokens = read_jsonl(CONTEXT_LOG)
    decisions = read_jsonl(DECISION_JOURNAL)

    if not tokens:
        print("[self-improve] Keine Context-Token vorhanden. Nichts zu analysieren.")
        return

    # Analysiere erfolgreiche Outputs (nur Task-Tokens, nicht Research)
    # Filter non-dict entries upfront (defensive gegen malformed JSONL)
    good = []
    bad = []
    for t in tokens:
        if not isinstance(t, dict):
            continue
        src = t.get("source_task_id", "")
        if not src.startswith("TASK-") and not src.startswith("FINAL-"):
            continue  # Research/Init tokens haben keine code_refs
        has_refs = bool(t.get("code_refs"))
        status = t.get("status", "?")
        if status == "completed" and has_refs:
            good.append(t)
        elif status == "failed" or (status == "completed" and not has_refs):
            bad.append(t)

    # Muster erkennen
    good_patterns = []
    if good:
        good_patterns.append(f"- {len(good)}/{len(tokens)} Tasks mit code_refs abgeschlossen")
        ref_counts = [len(t.get("code_refs", [])) for t in good]
        if ref_counts:
            good_patterns.append(f"- Durchschnittlich {sum(ref_counts)/len(ref_counts):.1f} code_refs pro Task")
        has_remaining = sum(1 for t in good if t.get("remaining_tasks"))
        if has_remaining:
            good_patterns.append(f"- {has_remaining} Tasks mit remaining_tasks (gute Nachverfolgbarkeit)")

    bad_patterns = []
    if bad:
        bad_patterns.append(f"- {len(bad)} Tasks OHNE code_refs (blinde Flecken)")
    task_tokens = [t for t in tokens if t.get("source_task_id","").startswith(("TASK-","FINAL-"))]
    missing_evidence = sum(1 for t in task_tokens if not t.get("code_refs") and t.get("status") == "completed")
    if missing_evidence:
        bad_patterns.append(f"- {missing_evidence} completed Tasks ohne file:line:method Referenzen")

    # Verbesserungen ableiten — NUR datengetrieben, kein Template-Text (Fix High #5)
    improvements = []
    if missing_evidence > len(tokens) * 0.3:
        improvements.append("- REGEL: Jeder Task-Done MUSS --code-refs enthalten. Ohne Ref = partial, nicht completed.")
    if not any(t.get("commit_sha") for t in tokens):
        improvements.append("- EMPFEHLUNG: --commit-sha in task-done verwenden für Git-Nachverfolgbarkeit")

    report = IMPROVE_TMPL.format(
        version=PROMPTSET_VERSION,
        timestamp=now_iso(),
        total_tokens=len(tokens),
        total_decisions=len(decisions),
        good_patterns="\n".join(good_patterns) or "(keine)",
        bad_patterns="\n".join(bad_patterns) or "(keine)",
        improvements="\n".join(improvements),
    )

    out_file = OUT_DIR / f"self-improve-{now_iso().replace(':', '-')[:19]}.md"
    out_file.write_text(report, encoding="utf-8")
    print(f"[self-improve] Report: {out_file}")
    print(f"[self-improve] {len(good)}/{len(tokens)} Tasks mit code_refs")
    print(f"[self-improve] {len(improvements)} Verbesserungen abgeleitet")

    if not args.quiet:
        print("\n" + report)


# ---------------------------------------------------------------------------
# Kommando: constraints  (🟢 LOW — Projekt-Constraints persistieren)
# ---------------------------------------------------------------------------

def cmd_constraints(args):
    ensure_state()
    action = args.action

    if action == "set":
        if not args.key or not args.value:
            sys.exit("[constraints] set benötigt KEY und VALUE. Beispiel: promptgen.py constraints set max_files_per_task 3")
        constraints = json.loads(CONSTRAINTS_FILE.read_text(encoding="utf-8") or "{}")
        constraints[args.key] = {
            "value": args.value,
            "updated_at": now_iso(),
            "updated_by": args.agent or "promter",
        }
        CONSTRAINTS_FILE.write_text(json.dumps(constraints, indent=2, ensure_ascii=False))
        print(f"[constraints] {args.key} = {args.value}")

    elif action == "show":
        constraints = json.loads(CONSTRAINTS_FILE.read_text(encoding="utf-8") or "{}")
        if not constraints:
            print("(keine Constraints persistiert)")
        else:
            print("### Persistierte Constraints ###")
            for k, v in constraints.items():
                print(f"- {k}: {v.get('value')} (von {v.get('updated_by')}, {v.get('updated_at')})")

    elif action == "init":
        # Standard-Constraints aus PROMPTSET.md ableiten
        defaults = {
            "max_files_per_task": {"value": "3", "updated_at": now_iso(), "updated_by": "promter"},
            "atomic_tasks": {"value": "R03 — Jede Aufgabe = genau EINE Sache", "updated_at": now_iso(), "updated_by": "promter"},
            "promter_no_code_access": {"value": "true — Promter hat KEINEN Code-Zugriff", "updated_at": now_iso(), "updated_by": "promter"},
            "append_only_state": {"value": "true — JSONL ist append-only (R01)", "updated_at": now_iso(), "updated_by": "promter"},
            "language_agnostic": {"value": "true — Keine Sprach-/Framework-Annahmen", "updated_at": now_iso(), "updated_by": "promter"},
        }
        CONSTRAINTS_FILE.write_text(json.dumps(defaults, indent=2, ensure_ascii=False))
        print(f"[constraints] {len(defaults)} Standard-Constraints initialisiert")


# ---------------------------------------------------------------------------
# Kommando: task-done  (Context-Token + Task-Index + Decisions + Handoff in EINEM Befehl)
# ---------------------------------------------------------------------------

def cmd_task_done(args):
    ensure_state()
    idx = load_index()
    task_id = args.task_id
    # LATEST-Alias 2026-07-28: neueste OFFENE TASK-ID wählen (filter completed)
    if task_id == "latest":
        task_keys = [k for k in idx if k.startswith("TASK-") and idx[k].get("status") != "completed"]
        if not task_keys:
            sys.exit("[task-done] 'latest' hat keine offenen TASK-IDs im Index")
        task_id = max(task_keys)

    if task_id not in idx:
        sys.exit(f"[task-done] Task-ID '{task_id}' nicht im Index gefunden.")

    # 1. Context-Token (R01) — deterministische CTX-ID
    phase = "FIX" if args.status == "partial" else ("TASK" if args.status == "completed" else "FIX")
    ctx_id = next_ctx_id(phase, task_id)
    token = {
        "id": ctx_id,
        "timestamp": now_iso(),
        "source_task_id": task_id,
        "agent": args.agent,
        "task": idx[task_id].get("description", args.summary),
        "status": args.status,
        "summary": args.summary or "Keine Zusammenfassung",
        "promtset_version": PROMPTSET_VERSION,
    }
    # code_refs — {file, line, method} pro geänderter Datei
    if args.code_refs:
        try:
            token["code_refs"] = json.loads(args.code_refs)
        except json.JSONDecodeError as e:
            sys.exit(f"[task-done] --code-refs ist kein valides JSON: {e}")
    # 🔴 HIGH: diff_stats — "+15 -40" pro Datei
    if args.diff_stats:
        token["diff_stats"] = args.diff_stats
    # 🟡 MEDIUM: commit_sha — Git Commit
    if args.commit_sha:
        token["commit_sha"] = args.commit_sha
    # 🟡 MEDIUM: remaining_tasks — Was ist noch offen?
    if args.remaining:
        try:
            token["remaining_tasks"] = json.loads(args.remaining)
        except json.JSONDecodeError as e:
            sys.exit(f"[task-done] --remaining ist kein valides JSON: {e}")
    append_jsonl(CONTEXT_LOG, token)
    print(f"[task-done] Context-Token: {ctx_id}")

    # 2. Task-Index updaten
    idx[task_id]["status"] = args.status
    idx[task_id]["context_token_id"] = ctx_id
    idx[task_id]["completed_at"] = now_iso()
    save_index(idx)
    print(f"[task-done] Task-Index: {task_id} -> {args.status}")

    # 3. Entscheidungen (R05, optional)
    if args.decisions:
        try:
            decisions = json.loads(args.decisions)
            if isinstance(decisions, dict):
                decisions = [decisions]
            for d in decisions:
                d.setdefault("source_task_id", task_id)
                d.setdefault("timestamp", now_iso())
                append_jsonl(DECISION_JOURNAL, d)
            print(f"[task-done] Entscheidungen: {len(decisions)} ins Journal")
        except json.JSONDecodeError as e:
            sys.exit(f"[task-done] --decisions ist kein valides JSON: {e}")

    # 4. Handoff (R04, optional)
    if args.handoff_to:
        entry = {
            "handoff_version": "1.0",
            "from": args.agent,
            "to": args.handoff_to,
            "timestamp": now_iso(),
            "note": args.handoff_note or "",
            "promtset_version": PROMPTSET_VERSION,
        }
        append_jsonl(HANDOFF_LOG, entry)
        print(f"[task-done] Handoff: {args.agent} -> {args.handoff_to}")

    print(f"[task-done] ALLE 3-4 Schritte in EINEM Befehl abgeschlossen.")


# ---------------------------------------------------------------------------
# Kommando: handoff  (R04, manuell)
# ---------------------------------------------------------------------------

def cmd_handoff(args):
    ensure_state()
    entry = {
        "handoff_version": "1.0",
        "from": args.from_agent,
        "to": args.to_agent,
        "timestamp": now_iso(),
        "note": args.note or "",
        "promtset_version": PROMPTSET_VERSION,
    }
    append_jsonl(HANDOFF_LOG, entry)
    print(f"[handoff] {args.from_agent} -> {args.to_agent} persistiert ({entry['timestamp']})")


# ---------------------------------------------------------------------------
# Kommando: claim  (R13 — Claims: list / show / verify / migrate)
# ---------------------------------------------------------------------------

def cmd_claim_list(args):
    ensure_state()
    prefix = get_project_prefix()
    claims = resolve_claims(prefix)
    status_filter = args.status
    if status_filter:
        claims = [c for c in claims if _safe_str(c.get("status", "")) == status_filter]
    if not claims:
        print(f"(keine Claims fuer Prefix {prefix}" + (f" mit status={status_filter}" if status_filter else "") + ")")
        return
    # Status-Verteilung
    from collections import Counter
    by_status = Counter(_safe_str(c.get("status", "?")) for c in claims)
    print(f"### Claims ({len(claims)} insgesamt fuer {prefix}) ###")
    print(f"  by status: {dict(by_status)}")
    print()
    for c in claims:
        cid = _safe_get(c, "id", "?")
        status = _safe_get(c, "status", "?")
        confidence = _safe_get(c, "confidence", "?")
        source = _safe_get(c, "source_res", "?")
        claim_text = _safe_get(c, "claim", "")
        verified_by = _safe_get(c, "verified_by_res", "")
        suffix = f" -> {verified_by}" if verified_by else ""
        truncated = claim_text if len(claim_text) <= 90 else claim_text[:87] + "..."
        print(f"- {cid:18s} [{status:11s} | conf={confidence:6s}] (src={source}{suffix})")
        print(f"    {truncated}")


def cmd_claim_show(args):
    ensure_state()
    cid = args.claim_id
    if not CLAIM_ID_PATTERN.match(cid):
        sys.exit(f"[claim show] Ungueltige Claim-ID: '{cid}' (Format: CLAIM-PREFIX-NNN)")
    history = get_claim_history(cid)
    if not history:
        print(f"(kein Claim mit ID {cid} im Log)")
        return
    print(f"### Claim-Trail: {cid} ({len(history)} Eintrag/Eintraege) ###")
    print()
    for i, entry in enumerate(history, 1):
        ts = _safe_get(entry, "timestamp", "?")
        status = _safe_get(entry, "status", "?")
        claim = _safe_get(entry, "claim", "")
        ev = _safe_get(entry, "evidence", "")
        vby = _safe_get(entry, "verified_by_res", "")
        vev = _safe_get(entry, "verified_evidence", "")
        origin = _safe_get(entry, "claim_origin", "?")
        print(f"#{i}  {ts}  [{status}]  origin={origin}")
        print(f"     Claim:   {claim}")
        if ev:
            print(f"     Evidence: {ev}")
        if vby:
            print(f"     Verified by: {vby}")
        if vev:
            print(f"     Verified evidence: {vev}")
        print()


def cmd_claim_verify(args):
    ensure_state()
    cid = args.claim_id
    if not CLAIM_ID_PATTERN.match(cid):
        sys.exit(f"[claim verify] Ungueltige Claim-ID: '{cid}' (Format: CLAIM-PREFIX-NNN)")
    status = args.status
    if status not in ("verified", "refuted", "refined"):
        sys.exit(f"[claim verify] status muss verified|refuted|refined sein, nicht '{status}'")
    evidence = args.evidence
    if not evidence or (":" not in evidence and not evidence.startswith("duplicate-of-")):
        sys.exit("[claim verify] --evidence MUSS file:line:code enthalten oder mit 'duplicate-of-CLAIM-ID' starten")
    # Bestehender Claim?
    existing_resolved = resolve_claims()
    existing = next((c for c in existing_resolved if _safe_str(c.get("id", "")) == cid), None)
    if not existing:
        # Neuer Claim (manuell angelegt)
        prefix = get_project_prefix()
        append_claim({
            "id": cid,
            "claim": args.claim_text or "(manuell verifiziert)",
            "evidence": evidence if status == "verified" else args.evidence,
            "status": status,
            "source_res": args.source_res or "manual",
            "claim_origin": "manual",
            "verified_by_res": args.verified_by_res or "manual",
            "verified_at": now_iso(),
            "verified_evidence": evidence,
        })
        print(f"[claim verify] Neuer Claim manuell angelegt + verifiziert: {cid} [{status}]")
    else:
        append_claim({
            "id": cid,
            "claim": _safe_str(args.claim_text or existing.get("claim", "")),
            "status": status,
            "source_res": _safe_str(existing.get("source_res", "unknown")),
            "verified_by_res": args.verified_by_res or "manual",
            "verified_at": now_iso(),
            "verified_evidence": evidence,
            "confidence": _safe_str(existing.get("confidence", "medium")),
            "claim_origin": _safe_str(existing.get("claim_origin", "decision-extraction")),
            "evidence": _safe_str(existing.get("evidence", "")),
        })
        print(f"[claim verify] {cid} -> {status} (latest-wins)")


def cmd_claim_migrate(args):
    """Backfill: Bestehende decisions[] (aus decision-journal.jsonl) -> Claims.

    EINMAL-Befehl. Pro Decision mit evidence wird ein Claim angelegt.
    Idempotent: ueberspringt Decisions, deren (source_res, source_decision_index)
    bereits im claim-log.jsonl existieren (-> Backfill-sicher).
    """
    ensure_state()
    prefix = get_project_prefix()
    decisions = read_jsonl(DECISION_JOURNAL)
    if not decisions:
        print("(keine Decisions im Journal)")
        return
    # Idempotenz-Index: existierende (source_res, source_decision_index) Tupel
    existing_claims = read_jsonl(CLAIM_LOG)
    seen = set()
    for c in existing_claims:
        if not isinstance(c, dict):
            continue
        sdi = c.get("source_decision_index")
        if isinstance(sdi, int):
            seen.add((c.get("source_res"), sdi))
    # Filter nach min-id (optional)
    if args.min_res:
        try:
            min_n = int(args.min_res.split("-")[1])
        except (IndexError, ValueError):
            sys.exit(f"[claim migrate-from-decisions] Kann min-res '{args.min_res}' nicht parsen (Format: RES-NNN)")
        decisions = [d for d in decisions if d.get("source_task_id", "").startswith("RES-")
                     and int(d.get("source_task_id", "RES-000").split("-")[1]) >= min_n]
    by_res = {}  # Quell-RES -> Liste Decisions
    skipped = 0
    for d in decisions:
        if not isinstance(d, dict):
            continue
        evid = _safe_str(d.get("evidence", ""))
        if not evid or evid == "?":
            continue
        res = _safe_str(d.get("source_task_id", "unknown"))
        sdi = d.get("source_decision_index")
        # source_decision_index wurde nicht durchgaengig gesetzt -> wir nutzen den Index in der By-RES-Liste als Pseudo-Index
        # Wenn der Eintrag kein source_decision_index hat, verwenden wir die Position in `by_res[res]`.
        if not isinstance(sdi, int):
            sdi = len(by_res.get(res, []))
        if (res, sdi) in seen:
            skipped += 1
            continue
        by_res.setdefault(res, []).append((d, sdi))
    if not by_res:
        print(f"(keine neuen Decisions mit evidence im Journal migrierbar; uebersprungen: {skipped})")
        return
    if args.dry_run:
        print("### DRY-RUN: keine Schreiboperationen ###")
        print(f"Wuerde {sum(len(v) for v in by_res.values())} neue Claims anlegen, ueber {len(by_res)} RES-IDs verteilt.")
        print(f"Bereits vorhanden (uebersprungen): {skipped}")
        for res, ds in sorted(by_res.items()):
            print(f"  {res}: {len(ds)} Claims")
        return
    created = 0
    # ROOT-CAUSE-FIX via _reserve_claim_seqs(): einmal max lesen + in-memory
    # inkrementieren. Mehrfach next_claim_id(prefix) ohne intervening Writes
    # wuerde dieselbe SEQ vergeben. Bei migrate koennen das >100 Claims sein.
    # Sammle erst alle (res, dec, sdi, claim_text, evidence, confidence, alt)
    # Tupel, dann atomare ID-Reservierung, dann schreiben.
    flat = []  # [(res, dec, sdi, claim_text, evidence, confidence, alt), ...]
    for res, ds in sorted(by_res.items()):
        for dec, sdi in ds:
            flat.append((
                res, dec, sdi,
                _safe_str(dec.get("what", "")).strip(),
                _safe_str(dec.get("evidence", "")),
                _safe_str(dec.get("confidence", "medium")),
                _coerce_str_list(dec.get("alternatives_rejected", [])),
            ))
    new_ids = _reserve_claim_seqs(prefix, len(flat))
    for i, (res, _dec, sdi, claim_text, evidence, confidence, alt) in enumerate(flat):
        append_claim({
            "id": new_ids[i],
            "claim": claim_text,
            "evidence": evidence,
            "confidence": confidence,
            "source_res": res,
            "source_decision_index": sdi,
            "claim_origin": "decision-extraction",
            "status": "unverified",
            "alternatives_rejected": alt,
        })
        created += 1
    print(f"[claim migrate-from-decisions] {created} neue Claims angelegt aus {len(by_res)} RES-Quellen")
    print(f"[claim migrate-from-decisions] {skipped} bereits vorhandene Decisions uebersprungen (idempotent).")
    print(f"Hinweis: History-Lookup per RES-ID war nicht moeglich (journal enthaelt keine Index-Map).")
    print(f"         Wenn RES-Korrekturen noetig sind: promptgen.py claim-verify <ID> --status ... --evidence ...")


# ---------------------------------------------------------------------------
# Kommando: context
# ---------------------------------------------------------------------------

def cmd_context(args):
    ensure_state()
    if args.action == "show":
        snap = context_snapshot(n=args.n)
        print("### Context-Token ###")
        print(format_context_tokens_md(snap["tokens"]))
        print("\n### Entscheidungen ###")
        print(format_decisions_md(snap["decisions"]))
        print("\n### Handoffs ###")
        for h in snap["handoffs"]:
            print(f"- {h.get('timestamp')}: {h.get('from')} -> {h.get('to')} :: {h.get('note','')}")
    elif args.action == "list-tasks":
        idx = load_index()
        for tid, meta in idx.items():
            print(f"{tid:10s} {meta.get('type','?'):9s} {meta.get('status','?'):18s} "
                  f"{meta.get('prompt_file','')}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        description="Promtset-Automatisierung: Roh-Prompt -> Research (read-only) -> Task-Prompt, "
                    "mit persistentem Kontext über Agenten-Wechsel hinweg.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("research", help="Roh-Prompt -> read-only Research-Prompt")
    pr.add_argument("raw_prompt")
    pr.add_argument("--task-id", dest="task_id", default=None, help="Override auto-increment ID (z.B. RES-036)")
    pr.add_argument("--project", default=None)
    pr.add_argument("--agent", default=None, help="Agent-Name der den Research ausführt (optional)")
    pr.add_argument("--context-window", type=int, default=5, dest="context_window")
    pr.add_argument("--quiet", action="store_true", help="Nur Dateipfad ausgeben, kein Volltext")
    pr.set_defaults(func=cmd_research)

    pi = sub.add_parser("ingest", help="Research-JSON einlesen + persistieren")
    pi.add_argument("json_file")
    pi.add_argument("--task-id", dest="task_id", default=None)
    pi.set_defaults(func=cmd_ingest)

    pb = sub.add_parser("build", help="Finalen Task-Prompt aus Research-Kontext bauen")
    pb.add_argument("task_id", help="Research-Task-ID (z.B. RES-001)")
    pb.add_argument("--raw-prompt", dest="raw_prompt", default=None)
    pb.add_argument("--target-agent", dest="target_agent", default=None)
    pb.add_argument("--instruction", default=None)
    pb.add_argument("--scope-in", dest="scope_in", default=None)
    pb.add_argument("--scope-out", dest="scope_out", default=None)
    pb.add_argument("--project", default=None)
    pb.add_argument("--quiet", action="store_true")
    pb.set_defaults(func=cmd_build)

    pres = sub.add_parser("resume", help="INIT-Block für neuen Agenten/Provider aus State bauen")
    pres.add_argument("-n", type=int, default=5)
    pres.set_defaults(func=cmd_resume)

    ph = sub.add_parser("handoff", help="R04-Handoff manuell persistieren")
    ph.add_argument("--from", dest="from_agent", required=True)
    ph.add_argument("--to", dest="to_agent", required=True)
    ph.add_argument("--note", default="")
    ph.set_defaults(func=cmd_handoff)

    ptd = sub.add_parser("task-done", help="Context-Token + Task-Index + Decisions + Handoff in EINEM Befehl")
    ptd.add_argument("task_id", help="Task-ID (z.B. TASK-001)")
    ptd.add_argument("--agent", required=True, help="Agent der den Task ausgeführt hat")
    ptd.add_argument("--status", default="completed", choices=["completed", "partial", "failed"], help="Task-Status")
    ptd.add_argument("--summary", required=True, help="Zusammenfassung (1-3 Sätze)")
    ptd.add_argument("--decisions", default=None, help="JSON-Array von Entscheidungen (R05)")
    ptd.add_argument("--handoff-to", dest="handoff_to", default=None, help="Nächster Agent für Übergabe (R04)")
    ptd.add_argument("--handoff-note", dest="handoff_note", default="", help="Notiz für Handoff")
    # 🔴 HIGH: code_refs + diff_stats
    ptd.add_argument("--code-refs", dest="code_refs", default=None, help="JSON-Array: [{\"file\":\"...\",\"line\":42,\"method\":\"foo\"}]")
    ptd.add_argument("--diff-stats", dest="diff_stats", default=None, help="Diff-Statistik: '+15 -40'")
    # 🟡 MEDIUM: commit_sha + remaining_tasks
    ptd.add_argument("--commit-sha", dest="commit_sha", default=None, help="Git Commit SHA")
    ptd.add_argument("--remaining", default=None, help="JSON-Array offener Task-IDs: [\"TASK-002\",\"TASK-003\"]")
    ptd.set_defaults(func=cmd_task_done)

    pc = sub.add_parser("context", help="State inspizieren")
    pc.add_argument("action", choices=["show", "list-tasks"])
    pc.add_argument("-n", type=int, default=10)
    pc.set_defaults(func=cmd_context)

    pp = sub.add_parser("project", help="Projekt-Metadaten (sprachagnostisch)")
    pps = pp.add_subparsers(dest="project_action", required=True)
    pp_init = pps.add_parser("init", help="Neues Projekt registrieren")
    pp_init.add_argument("--name", required=True, help="Projektname")
    pp_init.add_argument("--prefix", default=None, help="3-5 Zeichen Prefix für CTX-IDs (default: erste 3 Buchstaben vom Namen)")
    pp_init.add_argument("--language", default=None, help="Programmiersprache (z.B. python, javascript, rust)")
    pp_init.add_argument("--build", default=None, help="Build-System (z.B. pip, npm, cargo, make)")
    pp_init.add_argument("--test", default=None, help="Test-Befehl (z.B. 'pytest', 'npm test', 'cargo test')")
    pp_init.add_argument("--framework", default=None, help="Framework (z.B. react, fastapi, actix)")
    pp_init.set_defaults(func=cmd_project_init)
    pp_show = pps.add_parser("show", help="Alle Projekte anzeigen")
    pp_show.set_defaults(func=cmd_project_show)

    psi = sub.add_parser("self-improve", help="R07: Gentische Prompt-Verbesserung aus State analysieren")
    psi.add_argument("--quiet", action="store_true", help="Nur Dateipfad ausgeben")
    psi.set_defaults(func=cmd_self_improve)

    pcon = sub.add_parser("constraints", help="🟢 LOW: Projekt-Constraints persistieren/inspizieren")
    pcon.add_argument("action", choices=["set", "show", "init"], help="set KEY VALUE | show | init (Standardwerte)")
    pcon.add_argument("key", nargs="?", default=None, help="Constraint-Name (für set)")
    pcon.add_argument("value", nargs="?", default=None, help="Constraint-Wert (für set)")
    pcon.add_argument("--agent", default=None, help="Agent der das Constraint setzt")
    pcon.set_defaults(func=cmd_constraints)

    # R13 — Claims Subcommand-Tree
    pcl = sub.add_parser(
        "claim",
        help="R13: Claims inspizieren / verifizieren / migrieren",
        description="Claims sind atomare Forschungs-Aussagen mit eigenem ID-System "
                    "und latest-wins Semantik pro CLAIM-{PREFIX}-{SEQ}.",
    )
    pcl_subs = pcl.add_subparsers(dest="claim_action", required=True)

    pcll = pcl_subs.add_parser("list", help="Alle Claims (latest-wins) gruppiert nach Status")
    pcll.add_argument("--status", choices=["unverified", "verified", "refuted", "refined"], default=None)
    pcll.set_defaults(func=cmd_claim_list)

    pcls = pcl_subs.add_parser("show", help="Vollstaendiger Trail einer Claim-ID")
    pcls.add_argument("claim_id", help="z.B. CLAIM-SYX-001")
    pcls.set_defaults(func=cmd_claim_show)

    pclv = pcl_subs.add_parser("verify", help="Manuell verifizieren/widerlegen/refine")
    pclv.add_argument("claim_id", help="z.B. CLAIM-SYX-001")
    pclv.add_argument("--status", required=True, choices=["verified", "refuted", "refined"])
    pclv.add_argument("--evidence", required=True, help="file:line:code als Beleg/Widerlegung")
    pclv.add_argument("--claim-text", dest="claim_text", default=None, help="Bei 'refined': neue Formulierung")
    pclv.add_argument("--source-res", dest="source_res", default=None)
    pclv.add_argument("--verified-by-res", dest="verified_by_res", default=None)
    pclv.set_defaults(func=cmd_claim_verify)

    pclm = pcl_subs.add_parser("migrate-from-decisions", help="Einmal-Backfill: decisions -> claims")
    pclm.add_argument("--min-res", dest="min_res", default=None, help="Nur RES >= dieser Nummer")
    pclm.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht schreiben")
    pclm.set_defaults(func=cmd_claim_migrate)

    return p


def main():
    parser = build_parser()
    try:
        args = parser.parse_args()
        args.func(args)
    except Exception as e:
        # Kein raw Traceback an den User, aber stderr-Trace für Debug (Fix Medium #8)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(f"[error] {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
