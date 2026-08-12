#!/usr/bin/env python3
"""
dumpy.py — Kompakter Voll-Dump des .promtset/ State.

Zweck:
  Vermeidet Context-Muell durch 10+ read_files-Calls mit Truncation.
  Ein einziger Aufruf liefert ALLE relevanten Informationen:

    - projects.json         (aktive Projekte)
    - task-index.json       (alle Tasks mit Status-Verteilung)
    - context-log.jsonl     (Anzahl, Schemas, malformed-data Warnungen)
    - decision-journal.jsonl (Anzahl, Confidence-Verteilung, Source-Verteilung)
    - handoffs.jsonl        (alle Uebergaben)
    - out/                  (Liste aller Dateien mit Groessen)
    - .promtset/*.md        (Rule-Docs mit Groessen)
    - schemas/*.json        (Required-Felder pro Schema)
    - constraints.json      (alle Constraints)

Nutzung:
    python3 .promtset/tools/dumpy.py
    python3 .promtset/tools/dumpy.py --verbose
    python3 .promtset/tools/dumpy.py --section context-log
"""
import argparse
import json
from collections import Counter
from pathlib import Path


# ---------------------------------------------------------------------------
# Pfade / Konstanten
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]          # .promtset/
PROJECT_ROOT = ROOT.parent                            # Projekt-Wurzel
STATE = ROOT / "state"
OUT = ROOT / "out"
SCHEMAS = ROOT / "schemas"
AGENT_TEMPLATES = ROOT / "agent-templates"
CLAIM_LOG = STATE / "claim-log.jsonl"                # R13 — Claims


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_jsonl(path: Path):
    """Robust JSONL-Reader — ueberspringt kaputte Zeilen."""
    if not path.exists():
        return []
    out = []
    for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"  [WARN] {path.name}:{ln} kaputte JSONL-Zeile uebersprungen", flush=True)
    return out


def safe_load_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as e:
        print(f"  [WARN] {path.name}: JSON-Fehler {e}", flush=True)
        return default


# ---------------------------------------------------------------------------
# Section-Dumps (jeder ist eine eigenstaendige Funktion, kann einzeln gerufen werden)
# ---------------------------------------------------------------------------

def dump_projects(verbose=False):
    data = safe_load_json(STATE / "projects.json")
    if not data:
        return "  (kein projects.json oder leer)"
    lines = [f"  {len(data)} Projekt(e) registriert:"]
    for prefix, p in data.items():
        active = "\u2605 AKTIV" if p.get("active") else "  inaktiv"
        line = f"    {active} [{prefix}] {p.get('name','?')} ({p.get('language','?')}/{p.get('build_system','?')})"
        if verbose:
            line += f"\n      framework={p.get('framework','?')} test={p.get('test_command','?')}"
            line += f"\n      created={p.get('created','?')}"
        lines.append(line)
    return "\n".join(lines)


def dump_task_index(verbose=False):
    idx = safe_load_json(STATE / "task-index.json")
    if not idx:
        return "  (kein task-index.json oder leer)"
    by_status = Counter()
    by_type = Counter()
    by_agent = Counter()
    for tid, meta in idx.items():
        by_status[meta.get("status", "?")] += 1
        by_type[meta.get("type", "?")] += 1
        if "target_agent" in meta:
            by_agent[meta["target_agent"]] += 1
    lines = [f"  {len(idx)} Task(s) im Index:"]
    lines.append(f"    by status: {dict(by_status)}")
    lines.append(f"    by type:   {dict(by_type)}")
    if by_agent:
        lines.append(f"    by agent:  {dict(by_agent)}")
    if verbose:
        # Liste alle Tasks mit ihren wichtigsten Feldern
        lines.append("    --- Detail ---")
        for tid, meta in sorted(idx.items()):
            parts = [tid, meta.get("status", "?"), meta.get("type", "?")]
            if "target_agent" in meta:
                parts.append(f"-> {meta['target_agent']}")
            if "source_research_task" in meta:
                parts.append(f"from {meta['source_research_task']}")
            lines.append(f"    {' | '.join(parts)}")
    return "\n".join(lines)


def dump_context_log(verbose=False):
    tokens = read_jsonl(STATE / "context-log.jsonl")
    if not tokens:
        return "  (kein context-log.jsonl oder leer)"
    # Stats
    schemas = Counter()
    statuses = Counter()
    malformed = 0
    code_refs_with_strings = 0
    for t in tokens:
        if not isinstance(t, dict):
            malformed += 1
            continue
        schemas[t.get("schema", "context-token")] += 1
        statuses[t.get("status", "?")] += 1
        # Crash-Sentinel: String in code_refs
        refs = t.get("code_refs", [])
        if isinstance(refs, list):
            for r in refs:
                if isinstance(r, str):
                    code_refs_with_strings += 1
                    break
    lines = [f"  {len(tokens)} Context-Token:"]
    lines.append(f"    by schema: {dict(schemas)}")
    lines.append(f"    by status: {dict(statuses)}")
    if malformed:
        lines.append(f"    [WARN] {malformed} non-dict Token (sollte nie vorkommen)")
    if code_refs_with_strings:
        lines.append(f"    [WARN] {code_refs_with_strings} Token mit String-code_refs (Legacy-Format)")
    if verbose:
        # Letzte 5 Token
        lines.append("    --- Letzte 5 Token (ID + Status + Quell-Task) ---")
        for t in tokens[-5:]:
            if isinstance(t, dict):
                lines.append(f"    {t.get('id','?')} ({t.get('status','?')}) < {t.get('source_task_id','?')}")
    return "\n".join(lines)


def dump_decision_journal(verbose=False):
    decs = read_jsonl(STATE / "decision-journal.jsonl")
    if not decs:
        return "  (kein decision-journal.jsonl oder leer)"
    confidences = Counter()
    sources = Counter()
    malformed = 0
    for d in decs:
        if not isinstance(d, dict):
            malformed += 1
            continue
        confidences[d.get("confidence", "?")] += 1
        src = d.get("source_task_id", "?")
        sources[src] += 1
    lines = [f"  {len(decs)} Entscheidung(en):"]
    lines.append(f"    by confidence: {dict(confidences)}")
    lines.append(f"    unique sources: {len(sources)}")
    if malformed:
        lines.append(f"    [WARN] {malformed} non-dict Decision (sollte nie vorkommen)")
    if verbose:
        top_sources = sources.most_common(10)
        lines.append(f"    --- Top-10 Quellen ({len(top_sources)} von {len(sources)}) ---")
        for src, count in top_sources:
            lines.append(f"    {count:3d}x {src}")
    return "\n".join(lines)


def dump_claims(verbose=False):
    """R13 — Claims (latest-wins per Claim-ID) Statistik."""
    raw = read_jsonl(CLAIM_LOG)
    if not raw:
        return "  (kein claim-log.jsonl oder leer)"
    # Latest-wins per ID: iteriere von oben nach unten, letzte Zeile gewinnt
    by_id = {}
    order = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        cid = entry.get("id", "")
        if not cid or not isinstance(cid, str) or not cid.startswith("CLAIM-"):
            continue
        if cid not in by_id:
            order.append(cid)
        by_id[cid] = entry
    latest = [by_id[cid] for cid in order]
    by_status = Counter(e.get("status", "?") for e in latest)
    by_origin = Counter(e.get("claim_origin", "?") for e in latest)
    by_confidence = Counter(e.get("confidence", "?") for e in latest)
    # Updates zaehlen (alle Zeilen minus letzte-pro-ID)
    updates = len(raw) - len(latest)
    lines = [f"  {len(latest)} Claim(s) (latest-wins), {len(raw)} Zeilen total, {updates} Update(s):"]
    lines.append(f"    by status:    {dict(by_status)}")
    lines.append(f"    by origin:    {dict(by_origin)}")
    lines.append(f"    by confidence: {dict(by_confidence)}")
    if verbose:
        lines.append(f"    --- Letzte 5 Claims (ID + Status + Source) ---")
        for e in latest[-5:]:
            claim_text = (e.get("claim", "") or "")[:60]
            lines.append(f"    {e.get('id','?')} ({e.get('status','?')}) < {e.get('source_res','?')} | {claim_text}")
    return "\n".join(lines)


def dump_handoffs(verbose=False):
    hs = read_jsonl(STATE / "handoffs.jsonl")
    if not hs:
        return "  (kein handoffs.jsonl oder leer)"
    lines = [f"  {len(hs)} Handoff(s):"]
    for h in hs:
        if not isinstance(h, dict):
            lines.append(f"    [WARN] non-dict Handoff: {type(h).__name__}")
            continue
        lines.append(
            f"    {h.get('timestamp','?')}: "
            f"{h.get('from','?'):15s} -> {h.get('to','?'):15s} | "
            f"{(h.get('note','') or '')[:80]}"
        )
    return "\n".join(lines)


def dump_out_dir(verbose=False):
    files = sorted(OUT.iterdir(), key=lambda x: x.name)
    if not files:
        return "  (out/ ist leer)"
    lines = [f"  {len(files)} Datei(en):"]
    # Gruppieren nach Typ
    json_files = [f for f in files if f.suffix == ".json"]
    md_files = [f for f in files if f.suffix == ".md"]
    lines.append(f"    JSON: {len(json_files)}, Markdown: {len(md_files)}")
    # Top-10 groesste Dateien
    by_size = sorted(files, key=lambda x: x.stat().st_size, reverse=True)
    lines.append(f"    --- Top-10 nach Groesse ---")
    for f in by_size[:10]:
        size = f.stat().st_size
        lines.append(f"    {size:7,d} B  {f.name}")
    return "\n".join(lines)


def dump_rule_docs(verbose=False):
    rules = sorted(ROOT.glob("*.md"))
    if not rules:
        return "  (keine .promtset/*.md)"
    lines = [f"  {len(rules)} Rule-Doc(s):"]
    for r in rules:
        size = r.stat().st_size
        # Erste Zeile lesen als Inhalts-Vorschau
        try:
            first_line = r.read_text(encoding="utf-8").splitlines()[0][:60]
        except (IndexError, OSError):
            first_line = "(nicht lesbar)"
        lines.append(f"    {size:5,d} B  {r.name:30s} | {first_line}")
    return "\n".join(lines)


def dump_agent_templates(verbose=False):
    files = sorted(AGENT_TEMPLATES.glob("*.md"))
    lines = [f"  {len(files)} Agent-Template(s):"]
    for f in files:
        size = f.stat().st_size
        lines.append(f"    {size:5,d} B  {f.name}")
    return "\n".join(lines)


def dump_schemas(verbose=False):
    files = sorted(SCHEMAS.glob("*.json"))
    lines = [f"  {len(files)} Schema(s):"]
    for f in files:
        data = safe_load_json(f, default={})
        schema_id = data.get("$id", "?")
        title = data.get("title", "?")
        req = data.get("required", [])
        lines.append(f"    {f.name:35s} | id={schema_id:30s} | required=[{', '.join(req)}]")
    return "\n".join(lines)


def dump_constraints(verbose=False):
    c_path = PROJECT_ROOT / "constraints.json"
    data = safe_load_json(c_path, default={})
    if not data:
        return "  (constraints.json ist leer)"
    lines = [f"  {len(data)} Constraint(s):"]
    for k, v in sorted(data.items()):
        lines.append(f"    {k}: {v.get('value', '?')} (by {v.get('updated_by','?')}, {v.get('updated_at','?')})")
    return "\n".join(lines)


def dump_promptgen_health(verbose=False):
    """Prueft promptgen.py auf die bekannten Crash-Pattern."""
    tool = ROOT / "tools" / "promptgen.py"
    if not tool.exists():
        return "  (kein promptgen.py)"
    src = tool.read_text(encoding="utf-8")
    lines = [f"  promptgen.py: {len(src):,} Zeichen, {src.count(chr(10))+1:,} Zeilen"]
    # Sentinel-Checks
    sentinels = [
        ("_safe_get", "Defensive helper _safe_get vorhanden"),
        ("_safe_str", "Defensive helper _safe_str vorhanden"),
        ("_coerce_str_list", "Defensive helper _coerce_str_list vorhanden"),
        ("format_context_tokens_md", "format_context_tokens_md vorhanden"),
        ("isinstance(t, dict)", "isinstance(t, dict) Guard in format_context_tokens_md"),
    ]
    for needle, label in sentinels:
        present = needle in src
        lines.append(f"    {'+' if present else '!'} {label}: {'OK' if present else 'FEHLT'}")
    # Anti-Pattern-Checks (rohe .get()-Aufrufe ohne isinstance-Schutz in den format_* Funktionen)
    risky = src.count('.get(') - src.count('_safe_get(') - src.count('entry.get(') - src.count('t.get(') - src.count('h.get(') - src.count('d.get(') - src.count('r.get(')
    lines.append(f"    .get()-Aufrufe total: {src.count('.get(')}, geschuetzt: ~{src.count('.get(') - risky}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section-Registry (fuer --section Filter)
# ---------------------------------------------------------------------------

SECTIONS = {
    "projects":        ("Projekte",                dump_projects),
    "task-index":      ("Task-Index",              dump_task_index),
    "promptgen":       ("promptgen.py Health",     dump_promptgen_health),
    "context-log":     ("Context-Log",             dump_context_log),
    "decisions":       ("Decision-Journal",        dump_decision_journal),
    "claims":          ("Claim-Log (R13)",         dump_claims),
    "handoffs":        ("Handoffs",                dump_handoffs),
    "out":             ("Out-Verzeichnis",         dump_out_dir),
    "rules":           ("Rule-Dokumente",          dump_rule_docs),
    "agent-templates": ("Agent-Templates",         dump_agent_templates),
    "schemas":         ("Schemas",                 dump_schemas),
    "constraints":     ("Constraints",             dump_constraints),
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Promtset Info-Dump — kompakte Voll-Uebersicht ueber .promtset/ State."
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Mehr Details (z.B. letzte 5 Token, Top-10 Sources)")
    parser.add_argument("--section", "-s", choices=list(SECTIONS.keys()),
                        help="Nur EINE Section ausgeben")
    args = parser.parse_args()

    print("=" * 78)
    print(" PROMPTSET DUMPY  ".center(78, "="))
    print("=" * 78)
    print()

    if args.section:
        label, fn = SECTIONS[args.section]
        print(f"### {label} ###")
        print(fn(verbose=args.verbose))
    else:
        # Standard-Reihenfolge: wichtigste zuerst
        order = [
            "projects", "task-index", "promptgen", "context-log",
            "decisions", "claims", "handoffs", "out", "rules",
            "agent-templates", "schemas", "constraints",
        ]

        for key in order:
            label, fn = SECTIONS[key]
            print(f"### {label} ###")
            print(fn(verbose=args.verbose))
            print()

    print("=" * 78)
    print(" DONE ".center(78, "="))
    print("=" * 78)


if __name__ == "__main__":
    main()
