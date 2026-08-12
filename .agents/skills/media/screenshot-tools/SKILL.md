---
name: screenshot-tools
description: "Erstelle Desktop-Screenshots (Vollbild, bestimmtes Fenster, Pixel-Bereich). Nutze OS-native Capture-Tools für schnelle Bildschirmaufnahmen wenn tool-spezifische Captures nicht verfügbar sind."
category: media
stack: KREATIV + GOVERNANCE
risk: medium
side_effects: network_calls
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
---

# Screenshot Tools

Erstelle Desktop- und Fenster-Screenshots.

## Speicherorte

1. User-Pfad wenn angegeben
2. OS-Default-Screenshot-Pfad
3. Temp-Verzeichnis für Inspektions-Screenshots

## Tool-Priorität

- Tool-spezifische Captures zuerst (Playwright für Browser, Figma-Tools etc.)
- OS-Capture für Desktop-Apps ohne bessere Integration
- Dieser Skill als Fallback

## macOS

```bash
# Screenshot eines bestimmten Fensters
screencapture -w -o screenshot.png

# Interaktiver Bereichs-Screenshot  
screencapture -i -o selection.png
```

## Linux

```bash
# GNOME Screenshot
gnome-screenshot -f screenshot.png

# Vollbild mit import (ImageMagick)
import -window root screenshot.png
```

## Regeln

- Permissions vorher prüfen (macOS: Screen Recording Rechte)
- Nach Capture: Datei-Existenz und Größe verifizieren
