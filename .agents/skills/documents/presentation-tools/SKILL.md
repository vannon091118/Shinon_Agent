---
name: presentation-tools
description: >-
category: documents
stack: LOGISCH + GOVERNANCE
risk: low
side_effects: file_changes
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
  Erstelle und bearbeite PowerPoint-Präsentationen (.pptx). Baue visuell 
  anspruchsvolle Slide-Decks mit python-pptx oder Artifact-Tool. 
  Nutze Charts, Shapes und Layout-Systeme für professionelle Ergebnisse.
---

# Presentation Tools (PowerPoint .pptx)

Erstelle editierbare, visuell ambitionierte PowerPoint-Decks.

## Werkzeug-Wahl

| Werkzeug | Wann |
|---|---|
| `python-pptx` | Universell verfügbar, gute Python-Integration |
| `@oai/artifact-tool` (Node) | Wenn verfügbar: reichhaltigere Charts, native Shapes |

## Slide-Erstellung mit python-pptx

```python
from pptx import Presentation
from pptx.util import Inches, Pt

prs = Presentation()
prs.slide_width = Inches(13.333)   # 16:9
prs.slide_height = Inches(7.5)

slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
# ... shapes, text, images ...
prs.save("output.pptx")
```

## Qualitäts-Regeln

- 16:9 Standard (1280×720)
- Textfreie Art-Direction-Bilder als Hintergrund
- Charts via native Chart-API, nicht von Hand mit Shapes
- Shapes für Cards, Labels, Icons, Dekoration
- Nach Bau: Editierbarkeit prüfen, Layout verifizieren
- Keine Screenshot-Slides — immer editierbare .pptx
