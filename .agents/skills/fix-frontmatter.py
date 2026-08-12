#!/usr/bin/env python3
"""
fix-frontmatter.py — Repariert kaputte Skill-Frontmatter (v4)

Ziel: `description:`-Felder, die durch Fold-Marker (`description: >`,
`>-`, `|`, ...) mit Textblock am FRONTMATTER-ENDE (nach anderen Keys)
für strikte UND tolerante Parser leer/verloren sind.

Drei Fälle:
  A) substantieller Textblock am Ende      → Text in description verschieben
  B) nur [codex:vendor]-Marker             → Description aus Router-Tabelle
     (Routing-Tabellen der *-router/SKILL.md) generieren
  C) ganz leer                              → Router-Fallback, sonst erster
     Body-Absatz (Markdown gestrippt)

Reparatur: `description: "<escaped>"` ersetzt den Fold-Marker; der
angehängte Block wird entfernt. Alle anderen Zeilen bleiben byte-genau.

Usage:
  python3 fix-frontmatter.py --dry-run          # nur anzeigen, nichts schreiben
  python3 fix-frontmatter.py --apply            # schreiben
  python3 fix-frontmatter.py --apply --only path/to/SKILL.md
"""

import argparse
import re
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parent
LIVE_DIR = SKILLS_ROOT / "live"

FOLD_RE = re.compile(r"^description:\s*(?:>\s*-?|\|\s*-?)\s*$")
KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:")

MAX_DESC = 900  # < 1024 (Strict-Loader-Limit)


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
    return lines[1:end_idx], lines[end_idx + 1:], end_idx


def parse_router_tables() -> dict:
    """Skill-Name → Trigger-Phrasen aus allen *-router/SKILL.md Routing-Tabellen."""
    mapping = {}
    row_re = re.compile(r"\|\s*\"([^\"]+)\"([^|]*)\|\s*`?([a-z0-9][a-z0-9-]*)`?\s*\|")
    for smd in sorted(SKILLS_ROOT.rglob("SKILL.md")):
        rel = smd.relative_to(SKILLS_ROOT)
        if len(rel.parts) >= 2 and rel.parts[-2].endswith("-router"):
            try:
                text = smd.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in row_re.finditer(text):
                first = m.group(1).strip()
                rest = m.group(2)
                name = m.group(3).strip()
                phrases = [first] + [p.strip().strip('"') for p in re.findall(r'"([^"]+)"', rest)]
                phrases = [p for p in phrases if p]
                if name and phrases:
                    mapping.setdefault(name, []).extend(phrases)
    # dedupe, Reihenfolge erhalten
    return {k: list(dict.fromkeys(v)) for k, v in mapping.items()}


# Instruction-Banner, die kein Beschreibungs-Text sind
_BANNER_HINTS = ("stop", "read this before", "safety", "⚠", "🛑", "\u26a0", "always confirm", "do not send")

# Kuratierte Descriptions für Fälle, deren Body keinen brauchbaren ersten Absatz hat
MANUAL_OVERRIDES = {
    "media/heygen/heygen-avatar": "Create HeyGen digital human avatars: upload source footage, train identity, and manage avatar assets for video generation.",
    "media/heygen/heygen-video": "Generate HeyGen videos with digital humans: script, voice, avatar selection, and video rendering via the HeyGen API.",
    "productivity/catalyst-by-zoho/catalyst-by-zoho": "Build business apps and workflows on the Zoho Catalyst platform: cloud functions, data store, and REST APIs.",
    "productivity/midpage/draft-long-form-memo": "Draft long-form legal memoranda: structure, citations, and arguments suitable for court filings.",
    "productivity/midpage/litigation-update-post": "Write litigation update posts summarizing case status, filings, and next steps for stakeholders.",
    # Zoom-Kurzskills: degenerierte Descriptions ersetzen (Klasse statt Masse)
    "communication-apis/zoom/build-zoom-bot": "Build a Zoom bot: app setup, OAuth, meeting/webinar events, and bot endpoints for automated Zoom agents.",
    "communication-apis/zoom/cobrowse-sdk": "Integrate Zoom Cobrowse SDK: co-browsing sessions, agent handoff, and UI controls for live customer support.",
    "communication-apis/zoom/debug-zoom": "Debug Zoom integrations: OAuth errors, webhook delivery, SDK connection issues, and common API failures.",
    "communication-apis/zoom/phone": "Build Zoom Phone integrations: call control, voicemail, call queues, and PSTN features via the Zoom Phone API.",
    "communication-apis/zoom/probe-sdk": "Use the Zoom Probe SDK: connectivity diagnostics, network quality checks, and pre-meeting health verification.",
    "communication-apis/zoom/rivet-sdk": "Use the Zoom Rivet SDK: lightweight event-driven integrations and streaming data from Zoom meetings.",
    "communication-apis/zoom/rtms": "Use Zoom RTMS: real-time media streaming, transcription, and audio/video processing from live meetings.",
    "communication-apis/zoom/scribe": "Use Zoom Scribe: real-time transcription and intelligent meeting notes for Zoom sessions.",
    "communication-apis/zoom/setup-zoom-oauth": "Set up Zoom OAuth: app registration, scopes, refresh tokens, and secure token storage for Zoom API access.",
    "communication-apis/zoom/video-sdk": "Build custom video apps with the Zoom Video SDK: real-time video sessions, screen share, and platform support.",
    "communication-apis/zoom/zoom-apps-sdk": "Build Zoom Apps with the Zoom Apps SDK: UI toolkit, in-meeting panels, and app lifecycle integration.",
}


def body_fallback(body_lines: list) -> str:
    """Erster brauchbarer Absatz des Bodys, Markdown gestrippt."""
    for ln in body_lines:
        s = ln.strip()
        if not s:
            continue
        low = s.lower()
        if any(h in low for h in _BANNER_HINTS):
            continue
        s = re.sub(r"^#+\s*", "", s)
        s = re.sub(r"[`>*_~]", "", s)
        s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
        if len(s) >= 20:
            return s.strip()
    return ""


def yaml_quote(text: str) -> str:
    """Korrektes Double-Quote-Escaping für YAML-Skalare."""
    t = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{t}"'


def clean_desc(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("\\'", "'")  # \' → ' (YAML-escaped Quotes im Quelltext)
    return text[:MAX_DESC]


INDENTED_KEY_RE = re.compile(r"^\s+[A-Za-z_][A-Za-z0-9_-]*\s*:")
MARKER_ONLY_RE = re.compile(r"^\s*\[[^\]\n]+\]\s*$")


def _collect_continuation(fm_lines: list, fold_idx: int):
    """Sammelt eingerückte Continuation-Zeilen direkt unter dem Fold-Marker
    (überspringt Leerzeilen, stoppt am ersten nicht-eingerückten Inhalt).
    Liefert (indices, text)."""
    idxs = []
    j = fold_idx + 1
    while j < len(fm_lines):
        l = fm_lines[j]
        if l.strip() == "":
            j += 1
            continue
        if l.startswith(" ") or l.startswith("\t"):
            idxs.append(j)
            j += 1
        else:
            break
    text = " ".join(fm_lines[i].strip() for i in idxs).strip()
    return idxs, text


def _last_top_level_key(fm_lines: list) -> int:
    """Index des letzten UNINDENTED Keys (Indented-Sub-Keys zählen nie als Key)."""
    last = 0
    for i, l in enumerate(fm_lines):
        if l.startswith((" ", "\t")):
            continue
        if KEY_RE.match(l):
            last = i
    return last


def _delete_marker_trailing(new_lines: list, fold_idx: int):
    """Entfernt NUR [vendor]-Marker-Zeilen nach dem letzten Key (nie Struktur)."""
    last_key = _last_top_level_key(new_lines)
    for i in range(len(new_lines) - 1, last_key, -1):
        if new_lines[i].strip() and MARKER_ONLY_RE.match(new_lines[i]):
            del new_lines[i]


def _fallback_desc(name: str, router: dict, rel: Path, smd: Path) -> tuple:
    """(desc, grund) aus Router-Tabelle / Body / Platzhalter."""
    phrases = router.get(name, [])
    if phrases:
        return (clean_desc(f"Use when: {', '.join(phrases)}. See {rel.parent.as_posix()}."), "ROUTER")
    content = smd.read_text(encoding="utf-8")
    _, body, _ = extract_frontmatter(content)
    fb = body_fallback(body)
    if fb:
        return clean_desc(fb), "BODY"
    return clean_desc(f"Use when working with {name} ({rel.parent.as_posix()})."), "FALLBACK"


def _frontmatter_name(fm_lines: list) -> str:
    for l in fm_lines:
        if l.strip().startswith("name:"):
            return l.split(":", 1)[1].strip().strip("\"'")
    return ""


def fix_one(fm_lines: list, router: dict, rel: Path, smd: Path) -> tuple:
    """Liefert (neue_fm_lines, alte_desc, neue_desc|None, grund).
    Sicherheitsregeln:
    - Nie strukturierte Indented-Keys (Metadata) löschen.
    - Nie Continuation-Zeilen im File zurücklassen (sonst ungültiges YAML).
    - Bei unklarer Struktur: Datei unverändert lassen (grund None)."""
    override = MANUAL_OVERRIDES.get(rel.parent.as_posix())
    name = _frontmatter_name(fm_lines) or rel.parts[-2]

    fold_idx = None
    for i, l in enumerate(fm_lines):
        if FOLD_RE.match(l.strip()):
            fold_idx = i
            break
    cont_idxs, cont_txt = _collect_continuation(fm_lines, fold_idx) if fold_idx is not None else ([], "")

    # ── MANUAL-Override: schlägt alles, räumt aber Fold-Reste sicher weg ──
    if override:
        new_lines = list(fm_lines)
        for i, l in enumerate(new_lines):
            if l.strip().startswith("description:"):
                new_lines[i] = f"description: {yaml_quote(clean_desc(override))}"
                for k in sorted(cont_idxs, reverse=True):
                    del new_lines[k]
                _delete_marker_trailing(new_lines, fold_idx if fold_idx is not None else i)
                return new_lines, cont_txt or None, clean_desc(override), "MANUAL"
        return fm_lines, None, None, None

    if fold_idx is None:
        return fm_lines, None, None, None

    # ── VALIDER Fold: Continuation unter dem Marker IST die Description ──
    if cont_idxs:
        cont_txt = re.sub(r"^\[[^\]]+\]\s*(.+)$", r"\1", cont_txt)
        if len(cont_txt) >= 5:
            new_desc = clean_desc(cont_txt)
            grund = "FOLD_TEXT"
        else:
            new_desc, grund = _fallback_desc(name, router, rel, smd)
            grund = "FOLD_" + grund
        new_lines = list(fm_lines)
        new_lines[fold_idx] = f"description: {yaml_quote(new_desc)}"
        for k in sorted(cont_idxs, reverse=True):
            del new_lines[k]
        _delete_marker_trailing(new_lines, fold_idx)
        return new_lines, cont_txt, new_desc, grund

    # ── Broken Pattern: leerer Fold + Textblock am Ende ──
    last_key = _last_top_level_key(fm_lines)
    trailing = [l for l in fm_lines[last_key + 1:] if l.strip()]
    if any(INDENTED_KEY_RE.match(l) for l in trailing):
        # strukturierte Indented-Keys (z.B. metadata:) → NICHT anfassen
        return fm_lines, None, None, None

    txt = " ".join(l.strip() for l in trailing).strip()
    marker = re.match(r"^\[[^\]]+\]\s*(.+)$", txt, re.DOTALL)
    if marker and len(marker.group(1).strip()) >= 40:
        txt = marker.group(1).strip()
    old_desc = txt

    if len(txt) >= 40:
        new_desc = clean_desc(txt)
        grund = "TRAILING_TEXT"
    else:
        new_desc, grund = _fallback_desc(name, router, rel, smd)

    new_lines = list(fm_lines)
    new_lines[fold_idx] = f"description: {yaml_quote(new_desc)}"
    trailing_indices = [i for i in range(last_key + 1, len(new_lines))
                        if new_lines[i].strip()]
    for i in sorted(trailing_indices, reverse=True):
        del new_lines[i]
    return new_lines, old_desc, new_desc, grund


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--only", metavar="PATH", default=None)
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        ap.error("--dry-run oder --apply erforderlich")

    router = parse_router_tables()
    changed = 0
    skipped = 0
    for smd in sorted(SKILLS_ROOT.rglob("SKILL.md")):
        rel = smd.relative_to(SKILLS_ROOT)
        if rel.parts[0] == "live":
            continue
        if args.only and args.only not in str(rel):
            continue
        content = smd.read_text(encoding="utf-8")
        fm_lines, body_lines, end_idx = extract_frontmatter(content)
        if fm_lines is None:
            continue
        new_fm, old_desc, new_desc, grund = fix_one(fm_lines, router, rel, smd)
        if grund is None:
            continue
        if new_fm == fm_lines:
            skipped += 1
            continue
        print(f"[{grund:11s}] {rel}")
        print(f"    alt: {repr(old_desc[:70]) if old_desc else ''}")
        print(f"    neu: {new_desc[:90]}")
        if args.apply:
            out = "---\n" + "\n".join(new_fm) + "\n---\n" + "\n".join(body_lines)
            smd.write_text(out, encoding="utf-8")
        changed += 1

    print(f"\n{changed} Datei(en) {'repariert' if args.apply else 'zu reparieren (dry-run)'}, {skipped} übersprungen")
    sys.exit(0 if not (changed and args.dry_run) else 0)


if __name__ == "__main__":
    main()
