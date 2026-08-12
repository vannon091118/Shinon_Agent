---
name: audio-transcription
description: >-
category: media
stack: KREATIV + GOVERNANCE
risk: medium
side_effects: network_calls
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
  Transkribiere Audio-Dateien lokal ohne Cloud-API-Keys. Nutze lokale
  Whisper-Modelle für schnelle, private Transkription von Sprache aus
  Audio- und Video-Dateien.
---

# Audio Transcription

Transkribiere Audio lokal mit Whisper-Modellen.

## Workflow

1. Audio/Video-Dateipfad sammeln
2. Modell wählen:
   - `tiny.en` — schnell, Englisch
   - `tiny` — schnell, multilingual
   - `small.en` / `small` — bessere Genauigkeit
   - `medium` / `large-v3` — höchste Qualität (langsamer, größerer Download)
3. Transkription durchführen
4. Ergebnis validieren und speichern

## Output

- `output/transcribe/<job-id>/transcript.txt`
- Bei Video: erst Audio extrahieren, dann transkribieren

## Regeln

- Default: `tiny.en` für englische Quick-Transkription
- Kein Cloud-API-Key nötig — alles lokal
- Speaker-Diarization wird nicht unterstützt
