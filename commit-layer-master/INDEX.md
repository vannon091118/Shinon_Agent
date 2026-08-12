# 📖 INDEX — core/commit-layer/ (16 Dateien)

> **Version:** v0.25.0 | **Stand:** 2026-07-02
> **Zweck:** Referenzbuch für den Narrative Commit Layer (deterministisch via XorShift128)
> **CL-Refs:** Kanonische Quelle ist `../../CHANGELOG.md`.

---

## Root-Dateien

| Datei | LOC | Beschreibung |
|-------|-----|--------------|
| author_system.js | 400 | Unified Narrative Commit Layer — Composite-Derivation, Narrator-Selection, CHANGELOG-Sync |
| verify_commit_msg.js | 431 | Commit-Message Enforcer — 5 Checks (Tokens, Impulse, Storytelling, Composite, Charakter) |
| commit_lore/ | — | Unterverzeichnis mit 14 Dateien (JS + JSON) |

## commit_lore/ Dateien

| Datei | LOC | Beschreibung |
|-------|-----|--------------|
| rng.js | 232 | Deterministischer PRNG — XorShift128+, djb2-Hash, derive() für Composite-Kette |
| utils.js | 233 | Shared Utilities — findRepoRoot, getCommitLorePaths, loadJSON, selectNarrator, validateCommitInput |
| story_generator.js | 170 | LLM Narrative Integration — collectStoryContext(), baut Plot-Kontext für Commit-Narration |
| annotate_plot_lore.js | 131 | PLOT_LORE.md Composite-Annotation — annotiert [pN]-Tags mit [COMPOSITE:...] |
| build_pool.js | 156 | sidejoke_pool.json Builder — dynamisch aus Git-History + PLOT_LORE.md Buffy-Dialoge |

## commit_lore/ JSON-Datenquellen

| Datei | Beschreibung |
|-------|--------------|
| character_sheets.json | 14 Charaktere mit Voice-Templates, Mood, Attitude |
| plotchain.json (live) | Plot-Chain mit p_id, id, timestamp, summary, narrator, model_id, composite, ref_to, prev_narrator + data_changes + recent_commits + causal_chain_summary — wächst mit jedem author_system-Lauf |
| arcs/&lt;arcId&gt;/frozen_plotchain.json | Arc-Snapshot zum Freeze-Zeitpunkt + kompakte Form mit NUR Kern-Feldern (p_id, id, timestamp, summary, narrator, model_id, composite, ref_to, prev_narrator) + KEIN data_changes / recent_commits / causal_chain_summary |
| composite_chain.json | Composite-Hash-Kette für deterministische Selektion |
| narrative_params.json | Narrative Parameter (mood_pool, etc.) |
| sidejoke_pool.json | Side-Joke-Pool (max 40, dedup) |
| lore_arcs.json | Lore-Arcs für跨-Commit-Konsistenz |
| cross_references.json | Cross-Referenzen zwischen Commits |
| writing_rules.json | Schreibregeln für Commit-Narration |

## Plotchain Schema — live vs frozen

`plotchain.json` (auto-managed, im `commit_lore/`-Root) ist die **Live**-Plot-Chain und enthält pro Eintrag die vollen Felder:

- `p_id` (z. B. `p226`), `id` (ISO-timestamp), `timestamp`, `summary`, `narrator`, `model_id`, `composite` (z. B. `c221j77n11a5p13`)
- `ref_to`, `prev_narrator` (Chain-Linking)
- **`data_changes`** (Array mit `file`/`insertions`/`deletions` pro Commit),
- **`recent_commits`** (5 tiefste Causal-Chain Eintraege mit Hash + Subject + `files_touched` + author/date),
- **`causal_chain_summary`** (Subject-Strings der 5 letzten Commits — Pre-LLM Filler für die narrative Wiedergabe)

`arcs/<arcId>/frozen_plotchain.json` ist die **Frozen-Snapshot-Form** zum Arc-Freeze-Time-Point. Sie enthält pro Eintrag **nur die Kern-Felder** (p_id, id, timestamp, summary, narrator, model_id, composite, ref_to, prev_narrator), **ohne** `data_changes`, `recent_commits`, `causal_chain_summary`.

**Schema-Differenz ist by-design:** die Frozen-Form ist eine kompakte historische Momentaufnahme pro Arc — sie muss nicht alle Live-Felder enthalten. Wenn die beiden Dateien beim Sync-Check schematisch divergieren, ist das normal. **KEIN Drift, KEIN Fix nötig.** Die Frozen-Form darf nicht mit `recent_commits` oder `data_changes` "aufgepumpt" werden, weil sie sonst ihre Arc-Freeze-Stand-Funktion verliert.

**Migrationspfad:** `commit_lore/migrate_to_arcs.js` verschiebt Plot-Nodes aus der Live-Datei in die Frozen-Form beim Arc-Freeze. Im Archiv: `commit_lore/freeze_plotchain.js` (Trigger) und `commit_lore/cross_references.json` (Arc-Bridges).

> **Lese-Hinweis:** wer einen Plot-Node nur in `frozen_plotchain.json` ohne die Live-Erweiterung sieht, hat eine Arc-Freeze-Snapshot vor sich und keine "veraltete" oder "unvollständige" Live-Form.

## Verwendung

```bash
# Commit ausführen
node core/commit-layer/author_system.js --impulse="..." --model="..."

# Verifier prüfen
node core/commit-layer/verify_commit_msg.js <commit-msg-file>
```

*📖 Commit-Layer INDEX v0.25.0 — 16 Dateien, ~1.748 LOC.*

