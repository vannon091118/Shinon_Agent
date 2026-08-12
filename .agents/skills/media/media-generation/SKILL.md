---
name: media-generation
description: "\"Generiere und bearbeite KI-Medien: Bilder, Videos, Audio, 3D-Assets.\" Nutze KI-Bildgenerierung (GPT Image 2), Video-Erstellung und Audio-Generierung. Schätze Kosten vor der Ausführung."
category: media
stack: KREATIV + GOVERNANCE
risk: medium
side_effects: network_calls
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
---

# Media Generation

Generiere und bearbeite Bilder, Videos, Audio und 3D-Assets mit KI.

## Bild-Generierung

- **GPT Image 2** (`openai/gpt-image-2`) — Höchste Qualität, feine Typografie, realistische Szenen
- **GPT Image 2 Edit** (`openai/gpt-image-2/edit`) — Objekte ersetzen, Hintergrund bereinigen, Relighting

### Parameter
```json
{
  "prompt": "Szene, Subjekt, Details, Constraints",
  "image_size": "landscape_4_3",
  "quality": "high",
  "num_images": 1
}
```

## Workflow

1. **Modell wählen** — GPT Image 2 als Default für Bilder
2. **Kosten schätzen** — Vor Ausführung Kostenschätzung einholen
3. **User informieren** — "Das kostet etwa $X"
4. **Ausführen** — Generierung durchführen
5. **Output speichern** — Im Workspace ablegen

## Regeln

- Kein Hard Approval-Gate, aber Kosten transparent machen
- Video/3D/Multi-Output: Balance vorher prüfen
- Outputs standardmäßig lokal speichern
