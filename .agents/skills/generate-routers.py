#!/usr/bin/env python3
"""
generate-routers.py — Erzeugt fehlende Kategorie-Router („Einbinden" v4)

Kategorien OHNE *-router werden zu einem <category>-router/SKILL.md
zusammengefasst: Routing-Tabelle (Trigger-Phrasen aus den reparierten
Descriptions) + Routing-Logik + vollständiges Sub-Skill-Register.

Das ist das „Klasse statt Masse"-Prinzip: 92 flache Skills → 12 Router,
jeder Skill genau EINMAL adressierbar über Intent-Phrasen.

Usage:
  python3 generate-routers.py --dry-run   # zeigt, was erzeugt würde
  python3 generate-routers.py --apply     # schreibt die Router
  python3 generate-routers.py --apply --only productivity
"""

import argparse
import re
import sys
from pathlib import Path
from datetime import date

SKILLS_ROOT = Path(__file__).resolve().parent


def extract_frontmatter(content: str):
    if not content.startswith("---"):
        return None, content
    lines = content.split("\n")
    end_idx = None
    for i in range(1, min(len(lines), 400)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None, content
    return lines[1:end_idx], lines[end_idx + 1:]


def tolerant_value(fm_lines, key: str) -> str:
    for l in fm_lines:
        if l.strip().startswith(key + ":"):
            return l.split(":", 1)[1].strip().strip("\"'")
    return ""


def clean_phrase(p: str) -> str:
    p = p.strip()
    p = re.sub(r"^\[codex:[^\]]+\]\s*", "", p)  # [codex:vendor]-Marker zuerst
    p = p.strip('"')
    p = p.lstrip('\\"').strip()  # \" escaped quotes
    p = re.sub(r"^[#`>*_~\-\s]+", "", p)
    p = re.sub(r"[`>*_~\-\s]+$", "", p)
    p = re.sub(r"[().,:;]+$", "", p)
    return p.strip()


def trigger_phrases(description: str, skill_name: str, max_n: int = 4) -> list:
    """Extrahiert 1..max_n Trigger-Phrasen aus einer Description."""
    d = clean_phrase(description)
    if not d or d.lower() == skill_name.lower():
        return [skill_name]
    # "Use when: X, Y, Z. See path." → Phrasen
    m = re.match(r"(?i)^use when:?\s*(.*)", d)
    if m:
        rest = m.group(1)
        rest = re.split(r"\.\s*(?:See|Use|For) ", rest, maxsplit=1)[0]
        parts = [clean_phrase(p) for p in rest.split(",")]
        parts = [p for p in parts if p]
        return parts[:max_n] or [skill_name]
    # Sonst: erste 1-2 SÄTZE als Trigger (kein Komma-Splitting von Prosa)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", d) if s.strip()]
    out = []
    for s in sents:
        s = clean_phrase(s)
        if len(s) > 140:
            cut = s.rfind(" ", 0, 140)
            s = (s[:cut] + " ..." if cut > 60 else s[:137] + "...")
        if 5 <= len(s) and s.lower() != skill_name.lower() and s not in out:
            out.append(s)
        if len(out) >= 2:
            break
    return out[:max_n] or [skill_name]


def category_skills(category: str):
    """(name, description, relpath) je Skill in der Kategorie (rekursiv, ohne live)."""
    result = []
    base = SKILLS_ROOT / category
    if not base.exists():
        return result
    for smd in sorted(base.rglob("SKILL.md")):
        rel = smd.relative_to(SKILLS_ROOT)
        if rel.parts[0] == "live":
            continue
        try:
            content = smd.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, _ = extract_frontmatter(content)
        name = tolerant_value(fm, "name") if fm else ""
        if not name:
            name = rel.parts[-2]
        desc = tolerant_value(fm, "description") if fm else ""
        result.append((name, desc, rel.parent.as_posix()))
    return result


def router_exists(category: str) -> bool:
    r = SKILLS_ROOT / f"{category}-router"
    return (r / "SKILL.md").exists()


def render_router(category: str, skills: list) -> str:
    n = len(skills)
    vendors = ", ".join(sorted({s[2].split("/")[1] for s in skills if len(s[2].split("/")) > 1}))
    if len(vendors) > 60:
        vendors = vendors[:57] + "..."
    today = date.today().isoformat()

    lines = []
    lines.append("---")
    lines.append(f"name: {category}-router")
    lines.append(f'description: "Router für {n} {category}-Skills{f" ({vendors})" if vendors else ""}. '
                 f"Leitet User-Intents automatisch an den richtigen Sub-Skill weiter. Routing-Tabelle im Body.\"")
    lines.append(f"category: {category}")
    lines.append("stack: AUTONOM + GOVERNANCE")
    lines.append("risk: medium")
    lines.append("side_effects: file_changes")
    lines.append("requires_approval: true")
    lines.append("version: 1.0.0")
    lines.append(f"last_verified: {today}")
    lines.append("")
    lines.append("---")
    lines.append(f"# 🧭 {category.title()} Router — {n} Skills")
    lines.append("")
    lines.append(f"> **Router für `{category}/`** — Wählt automatisch den richtigen Sub-Skill basierend auf User-Intent.")
    lines.append("")
    lines.append("## 🗺️ Routing-Tabelle")
    lines.append("")
    lines.append("| User sagt... | → Skill | Pfad |")
    lines.append("|---|---|---|")
    for name, desc, path in skills:
        phrases = trigger_phrases(desc, name)
        phr = ", ".join(f'"{p}"' for p in phrases)
        lines.append(f"| {phr} | `{name}` | `{path}` |")
    lines.append("")
    lines.append("## 🔀 Routing-Logik")
    lines.append("")
    lines.append("```")
    for name, desc, path in skills:
        lines.append(f"  \"{name.split('-')[0].title()}\" → {name}")
    lines.append('  Unklar? → Nachfrage: Welche Aufgabe, welcher Anbieter?')
    lines.append("```")
    lines.append("")
    lines.append("## 📋 Sub-Skill-Register")
    lines.append("")
    lines.append("| # | Skill | Pfad |")
    lines.append("|---|---|---|")
    for i, (name, desc, path) in enumerate(skills, 1):
        lines.append(f"| {i} | `{name}` | `{path}` |")
    lines.append("")
    lines.append(f"_{n} Skills · {category} · {today}_")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", metavar="CAT", default=None)
    ap.add_argument("--categories", metavar="a,b,c", default=None,
                    help="nur diese Kategorien (Komma-getrennt)")
    ap.add_argument("--force", action="store_true", help="bestehende Router überschreiben")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("--dry-run oder --apply erforderlich")

    if args.categories:
        wanted = {c.strip() for c in args.categories.split(",") if c.strip()}
    else:
        wanted = None
    categories = sorted(
        d.name for d in SKILLS_ROOT.iterdir()
        if d.is_dir() and not d.name.endswith("-router") and d.name != "live"
        and not d.name.startswith(".")
    )
    if wanted:
        categories = [c for c in categories if c in wanted]
    generated = []
    for cat in categories:
        if router_exists(cat) and not args.force:
            continue
        skills = category_skills(cat)
        if not skills:
            continue
        if args.only and args.only != cat:
            continue
        content = render_router(cat, skills)
        out = SKILLS_ROOT / f"{cat}-router" / "SKILL.md"
        generated.append((out, content, len(skills)))
        print(f"[{len(skills):3d} Skills] {cat}-router/SKILL.md")
        if args.apply:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding="utf-8")

    print(f"\n{len(generated)} Router {'erzeugt' if args.apply else 'würden erzeugt (dry-run)'}")


if __name__ == "__main__":
    main()
