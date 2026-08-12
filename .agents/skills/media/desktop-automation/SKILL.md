---
name: desktop-automation
description: >-
category: media
stack: KREATIV + GOVERNANCE
risk: medium
side_effects: network_calls
requires_approval: false
version: 1.0.0
last_verified: 2026-08-11
  Steuere native Desktop-Apps durch Automation (click, type, scroll, drag, screenshots).
  Verwende wenn der User eine Desktop-App bedienen, native Dialoge ausfüllen, 
  Datei-Dialoge steuern oder Browser-Chrome automatisieren möchte.
---

# Desktop Automation

Steuere native Desktop-Anwendungen über Accessibility-APIs und Screenshot-basierte Interaktion.

## Werkzeuge

- `get_app_state({app})` — Screenshot + Element-Tree einer App holen
- `click({app, element_index?, x?, y?})` — Klick auf Element oder Koordinate
- `type_text({app, text})` — Text in fokussiertes Feld eingeben
- `scroll({app, element_index, direction})` — Scrollen
- `press_key({app, key})` — Tastendruck (Return, Tab, Escape, cmd+s etc.)
- `drag({app, from_x, from_y, to_x, to_y})` — Drag & Drop
- `launch_app({app, name?})` — App starten
- `list_apps({})` — Alle offenen Apps auflisten

## Workflow

1. **Observe**: `get_app_state` → Screenshot + Element-Indices
2. **Act**: Element-Index oder Screenshot-Koordinate nutzen
3. **Verify**: Erneut `get_app_state` zur Bestätigung

## Regeln

- Nach jeder UI-Änderung frisches `get_app_state` holen
- Element-Indices sind nur innerhalb desselben States gültig
- Für Web-Inhalte in Electron/Chromium-Apps: Accessibility-Tree nutzen, nicht aufgeben
- Screenshot-Koordinaten nur wenn AX/UIA das Element nicht exponiert
