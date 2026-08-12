#!/usr/bin/env python3
"""
validate-catalog.py — Reproduzierbarer Skill-Katalog-Prüfer (v4)

Prüft ALLE SKILL.md unter .agents/skills/ gegen zwei Verträge:
  1. STRICT  = PyYAML safe_load (Freebuff skill-Tool / Hersteller-Format)
  2. TOLERANT = zeilenbasierter Parser wie karma-main/karma/skills/registry.py
               (_parse_skill_frontmatter: name/description/version per split(":",1))

Befunde pro Skill: STRICT_PARSE, TOLERANT_LOAD (simuliert), FIELDS, BODY,
DUPES (doppelter name / mehrfaches SKILL.md im selben Baum), CHAIN
(Router-/Chain-Referenz), LIVE (Snapshot in skills/live/).

Usage:
  python3 validate-catalog.py                  # Summary + broken lists
  python3 validate-catalog.py --json out.json  # vollständige Daten
  python3 validate-catalog.py --report AUDIT.md  # Markdown-Report schreiben
  python3 validate-catalog.py --broken         # nur defekte Dateien listen
  python3 validate-catalog.py --allow-yaml-errors  # fail-open für YAML (Bestandsbefund)

Exit-Code: 0 = alle Skill-Pflichtchecks grün, 1 = mindestens ein Befund.
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    import yaml
    HAVE_YAML = True
except ImportError:  # pragma: no cover
    HAVE_YAML = False

# Das Skript liegt direkt in .agents/skills/ — dort liegen auch alle SKILL.md.
SKILLS_ROOT = Path(__file__).resolve().parent
LIVE_DIR = SKILLS_ROOT / "live"

# Projekt-Konventionen laut SKILL-AUDIT P1 (optional, aber empfohlen)
CONVENTION_FIELDS = [
    "category", "stack", "risk", "side_effects",
    "requires_approval", "version", "last_verified",
]
REQUIRED_FIELDS = ["name", "description"]

MIN_BODY_CHARS = 80           # weniger = Platzhalter-Skill
MIN_BODY_LINES = 6
MAX_FRONTMATTER_LINES = 400   # darüber: keine echte Frontmatter

STRICT_TAG_RE = re.compile(r"(?<![:\w])[a-z][a-z0-9_-]*\s*:\s*[a-z][a-z0-9_.-]*")


def extract_frontmatter(content: str):
    """Gibt (frontmatter_text, body) zurück; (None, content) wenn keine Frontmatter."""
    if not content.startswith("---"):
        return None, content
    lines = content.split("\n")
    end_idx = None
    for i in range(1, min(len(lines), MAX_FRONTMATTER_LINES + 1)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None, content
    return "\n".join(lines[1:end_idx]), "\n".join(lines[end_idx + 1:])


def tolerant_parse(frontmatter: str):
    """Simuliert karma-main _parse_skill_frontmatter (zeilenbasiert, tolerant).
    Liefert {name, description, version} mit _only_first_line Flag."""
    info = {"name": "", "description": "", "version": "", "_only_first_line": False}
    for line in frontmatter.split("\n"):
        s = line.strip()
        if s.startswith("name:"):
            info["name"] = s.split(":", 1)[1].strip().strip("\"'")
        elif s.startswith("description:"):
            rest = s[len("description:"):].strip()
            if rest in (">", "|", ">-", "|-", ">+", "|+"):
                info["_only_first_line"] = True  # Fold: toleranter Parser liest nur 1. Zeile
                info["description"] = ""
            else:
                info["description"] = rest.strip("\"'")
        elif s.startswith("version:"):
            info["version"] = s.split(":", 1)[1].strip().strip("\"'")
    return info


def parse_strict(frontmatter: str):
    """PyYAML safe_load; gibt (dict|None, fehler|None)."""
    if not HAVE_YAML:
        return None, "pyyaml nicht installiert (nur TOLERANT geprüft)"
    try:
        data = yaml.safe_load(frontmatter)
        if not isinstance(data, dict):
            return None, "Frontmatter ist kein YAML-Dictionary"
        return data, None
    except yaml.YAMLError as e:
        return None, str(e).split("\n")[0]


def categorize_yaml_error(msg: str) -> str:
    """Fehlerursache grob kategorisieren für Massenbefund."""
    m = msg or ""
    if "found character" in m and "that cannot start any token" in m:
        return "control_character"
    if "mapping values are not allowed" in m:
        return "unquoted_colon"
    if "could not find expected ':'" in m:
        return "malformed_key"
    if "expected <block end>" in m or "while parsing a block mapping" in m:
        return "block_mapping"
    if "found unexpected" in m or "did not find expected" in m:
        return "unexpected_token"
    return "other"


def norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def check_skill(skill_md: Path, all_names: dict, strict_fail_open: bool):
    """Prüft eine SKILL.md. Liefert Befund-Dict."""
    rel = skill_md.relative_to(SKILLS_ROOT)
    parts = rel.parts  # z.B. ('communication-apis','twilio-developer-kit','twilio-send-message','SKILL.md')
    category = parts[0]
    depth = len(parts) - 1  # 1 = Top-Level-Skill, 2 = unter Sub-Familie, ...
    findings = []
    dupes = []
    chain_refs = []

    try:
        content = skill_md.read_text(encoding="utf-8")
    except OSError as e:
        return {"path": str(rel), "category": category, "depth": depth,
                "findings": [f"unreadable: {e}"], "name": parts[-2] if depth else "", "dupes": [], "chain": []}

    # ── FRONTMATTER ──
    fm, body = extract_frontmatter(content)
    name = parts[-2] if depth else ""
    if fm is None:
        findings.append("NO_FRONTMATTER")
    else:
        strict_data, yaml_err = parse_strict(fm)
        if yaml_err and not strict_fail_open:
            findings.append(f"STRICT_PARSE:{categorize_yaml_error(yaml_err)}")
        tol = tolerant_parse(fm)
        if tol["name"]:
            name = tol["name"]
        if tol["_only_first_line"]:
            findings.append("TOLERANT_LOSES_DESC")  # Folded multiline: Karma liest nur 1. Zeile
        if not tol["description"] and not tol["_only_first_line"]:
            findings.append("NO_DESC_TOLERANT")
        # Feld-Check (strikte Daten wenn vorhanden, sonst tolerant)
        data = strict_data if (strict_data is not None) else tol
        for f in REQUIRED_FIELDS:
            if f not in data or not str(data.get(f, "")).strip():
                findings.append(f"MISSING:{f}")
        for f in CONVENTION_FIELDS:
            if f not in data and depth == 1:
                findings.append(f"NO_CONVENTION:{f}")
        if strict_data is not None and isinstance(strict_data.get("description"), str):
            d = strict_data["description"]
            if len(d) < 20:
                findings.append("DESC_TOO_SHORT")
        # Name-Konvention (kebab-case)
        if name and not re.match(r"^[a-z0-9-]+$", name):
            findings.append(f"NAME_NOT_KEBAB:{name}")

    # ── BODY ──
    if fm is None:
        body = content
    body_stripped = (body or "").strip()
    if len(body_stripped) < MIN_BODY_CHARS:
        findings.append("BODY_TOO_SHORT")
    elif len(body_stripped.split("\n")) < MIN_BODY_LINES:
        findings.append("BODY_FEW_LINES")
    first_h1 = re.search(r"^#\s+.+$", body_stripped, re.M)
    if first_h1 is None:
        findings.append("NO_H1")

    # ── DUPES: gleicher Name an anderem Pfad ──
    nkey = norm_name(name)
    if nkey:
        others = all_names.get(nkey, [])
        for o in others:
            if o != str(rel):
                dupes.append(o)

    # ── CHAIN: wird der Skill von einem Router oder skill-chains referenziert?
    # Katalog aus Router-SKILL.md + skill-chains Body aufbauen (einmalig, siehe main)
    # Reachability = eigener Name ODER ein Pfad-Segment (Eltern-Skill) wird
    # referenziert → Kind-Skills unter z.B. meeting-sdk/ sind erreichbar.
    global _CHAIN_TEXT
    if _CHAIN_TEXT:
        candidates = [name] if nkey else []
        # Pfad-Segmente als Kandidaten (Eltern-Skills: a, a/b, ...)
        for seg in parts[:-1]:
            if re.match(r"^[a-z0-9-]+$", seg):
                candidates.append(seg)
        found = False
        for cand in candidates:
            pat = re.compile(r"(?<![a-z0-9-])" + re.escape(cand) + r"(?![a-z0-9-])", re.IGNORECASE)
            if pat.search(_CHAIN_TEXT):
                found = True
                chain_refs.append(cand)
                break
        if not found:
            findings.append("NOT_IN_CHAIN")

    # ── LIVE-Snapshot ──
    live_md = LIVE_DIR / f"{name}.md"
    if name and not live_md.exists() and depth == 1:
        findings.append("NO_LIVE_SNAPSHOT")

    return {"path": str(rel), "category": category, "depth": depth, "name": name,
            "findings": sorted(set(findings)), "dupes": sorted(set(dupes)),
            "chain": chain_refs}


_CHAIN_TEXT = ""


def build_chain_text() -> str:
    """Konkateniert alle Router-SKILL.md + skill-chains Body für Referenzsuche."""
    texts = []
    for smd in sorted(SKILLS_ROOT.rglob("SKILL.md")):
        rel = smd.relative_to(SKILLS_ROOT)
        if len(rel.parts) >= 2 and rel.parts[0] != "live":
            if rel.parts[-2].endswith("-router") or rel.parts[-2] in ("skill-chains",):
                try:
                    texts.append(smd.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    pass
    return "\n".join(texts)


def main():
    ap = argparse.ArgumentParser(description="Skill-Katalog-Prüfer v4")
    ap.add_argument("--json", metavar="OUT", help="vollständige Befunde als JSON schreiben")
    ap.add_argument("--report", metavar="OUT", help="Markdown-Report schreiben")
    ap.add_argument("--broken", action="store_true", help="nur Dateien mit Befunden listen")
    ap.add_argument("--allow-yaml-errors", action="store_true",
                    help="YAML-Parserfehler nur als Bestandsbefund zählen, nicht als Fehler")
    args = ap.parse_args()

    if not SKILLS_ROOT.exists():
        print(f"❌ Kein Skills-Verzeichnis: {SKILLS_ROOT}", file=sys.stderr)
        sys.exit(2)

    global _CHAIN_TEXT
    _CHAIN_TEXT = build_chain_text()

    # Name → Pfade indexieren (für Duplikaterkennung)
    all_names = defaultdict(list)
    for smd in sorted(SKILLS_ROOT.rglob("SKILL.md")):
        rel = smd.relative_to(SKILLS_ROOT)
        if rel.parts[0] == "live":
            continue
        content = smd.read_text(encoding="utf-8", errors="replace")
        fm, _ = extract_frontmatter(content)
        nm = ""
        if fm:
            tol = tolerant_parse(fm)
            nm = tol["name"] or (rel.parts[-2] if len(rel.parts) >= 2 else "")
        else:
            nm = rel.parts[-2] if len(rel.parts) >= 2 else ""
        if nm:
            all_names[norm_name(nm)].append(str(rel))

    skills = []
    for smd in sorted(SKILLS_ROOT.rglob("SKILL.md")):
        rel = smd.relative_to(SKILLS_ROOT)
        if rel.parts[0] == "live":
            continue
        skills.append(check_skill(smd, all_names, args.allow_yaml_errors))

    # ── Aggregation ──
    total = len(skills)
    broken = [s for s in skills if s["findings"]]
    dup_groups = {k: v for k, v in all_names.items() if len(v) > 1}
    cat_counts = Counter(s["category"] for s in skills)
    finding_counts = Counter()
    for s in skills:
        for f in s["findings"]:
            finding_counts[f.split(":")[0]] += 1

    # ── Ausgabe ──
    if args.json:
        Path(args.json).write_text(
            json.dumps({"total": total, "broken": broken, "skills": skills,
                        "duplicate_groups": dup_groups,
                        "categories": dict(cat_counts),
                        "findings_by_type": dict(finding_counts)},
                       indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"✅ JSON geschrieben: {args.json}")

    if args.report:
        lines = [f"# 🔬 SKILL-AUDIT v4 — Reproduzierbarer Katalog-Prüfer",
                 f"\n> Stand: automatisch erzeugt von `validate-catalog.py` · {total} SKILL.md · "
                 f"{len(cat_counts)} Kategorien",
                 f"> Fehlermodus: {'fail-open (YAML = Bestandsbefund)' if args.allow_yaml_errors else 'fail-closed (YAML = Fehler)'}",
                 "\n## Befunde nach Typ",
                 "| Befund | Anzahl | Bedeutung |",
                 "|---|---|---|"]
        meaning = {
            "STRICT_PARSE": "PyYAML kann Frontmatter nicht parsen (unquoted Vendor-Präfix etc.)",
            "TOLERANT_LOSES_DESC": "Folded-Multiline-Description: Karma-Loader liest nur 1. Zeile",
            "NO_DESC_TOLERANT": "Toleranter Loader findet keine Description",
            "NO_FRONTMATTER": "Keine YAML-Frontmatter",
            "MISSING": "Pflichtfeld (name/description) fehlt oder leer",
            "NO_CONVENTION": "Konventionsfeld fehlt (category/stack/risk/…) bei Top-Level-Skill",
            "BODY_TOO_SHORT": "Body zu kurz (< 80 Zeichen) — Platzhalter-Skill",
            "BODY_FEW_LINES": "Body hat zu wenige Zeilen",
            "NO_H1": "Kein H1-Titel im Body",
            "NOT_IN_CHAIN": "Skill wird von keinem Router/skill-chains referenziert",
            "NO_LIVE_SNAPSHOT": "Kein Snapshot in skills/live/",
            "NAME_NOT_KEBAB": "Name verletzt kebab-case",
            "DESC_TOO_SHORT": "Description kürzer als 20 Zeichen",
        }
        for k, v in sorted(finding_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| `{k}` | {v} | {meaning.get(k, '')} |")
        lines.append("")
        if dup_groups:
            lines.append("## Duplikat-Gruppen (gleicher name in mehreren Pfaden)")
            for nkey, paths in sorted(dup_groups.items()):
                if len(paths) > 1:
                    lines.append(f"\n- **{nkey}**:")
                    for p in paths:
                        lines.append(f"  - `{p}`")
        lines.append("")
        lines.append("## Kategorien (SKILL.md je Top-Level)")
        for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
            lines.append(f"- `{c}`: {n}")
        lines.append("")
        lines.append("## Defekte Skills (mit Befunden)")
        for s in broken:
            lines.append(f"- `{s['path']}` → {', '.join(s['findings'])}")
        Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"✅ Report geschrieben: {args.report}")

    # Konsolen-Summary
    print(f"\n📊 SKILL-AUDIT v4 — {total} SKILL.md · {len(cat_counts)} Kategorien")
    print(f"   Fehler-Modus: {'fail-open' if args.allow_yaml_errors else 'fail-closed'}")
    print(f"   ✅ OK:          {total - len(broken)}")
    print(f"   ⚠️  Mit Befund:  {len(broken)}")
    print(f"   🔁 Duplikat-Gruppen: {len([g for g, p in dup_groups.items() if len(p) > 1])}")
    print("\n   Befunde nach Typ:")
    for k, v in sorted(finding_counts.items(), key=lambda x: -x[1]):
        print(f"     {k:24s} {v:4d}")

    if args.broken:
        print("\n   Defekte Skills:")
        for s in broken:
            print(f"     {s['path']}")
            for f in s["findings"]:
                print(f"       - {f}")

    sys.exit(0 if not broken else 1)


if __name__ == "__main__":
    main()
