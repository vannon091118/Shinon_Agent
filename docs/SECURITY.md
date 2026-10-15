# Sicherheit — Shinon Agent

> Stand: 2026-10-14 · Ausgangsstand `e78ca1a`
> Jede Aussage ist aus dem Code abgeleitet. Verhalten auf einem Gerät ist
> ausschließlich dort als verifiziert markiert, wo es belegt ist.

## 1. Bedrohungsmodell

| Nr. | Bedrohung | Betroffene Grenze | Aktueller Stand |
|---|---|---|---|
| T-1 | Provider-Schlüssel gelangt in Repo, Build, Log oder URL | Build / Log / UI | Log-Maskierung vorhanden; Schlüssel wird **noch nicht** gespeichert (SEC-KEY-001) |
| T-2 | Fremde Seite lädt in der WebView und erhält JS/DOM-Zugriff | `MainActivity` | Prüfung auf `http` + `127.0.0.1` im Code vorhanden (`SEC-HOST-001`) |
| T-3 | Token der lokalen DSH-URL landet im Gerätelog | `ShinonService.parseReadyUrl` | URL wird nicht geloggt, nur der Port |
| T-4 | Signaturschlüssel im Repo | CI / `.gitignore` | `*.jks` und `keystore/` ignoriert (verifiziert) |
| T-5 | Mitgelieferte Runtime ist manipuliert | Runtime-Paket | **kein** SHA256-Check implementiert (RT-PIN-001) |
| T-6 | Zweite App/Prozess greift die lokale DSH-URL ab | Loopback-Schnittstelle | Port `0` (OS-gewählt), Token in der URL; kein Bind auf eine externe Adresse |
| T-7 | Receiver werden von fremden Apps getriggert | Broadcast | `Context.RECEIVER_NOT_EXPORTED` an beiden Registrierungen |
| T-8 | Native Addons (koffi/node-pty/sharp) mit Speicherfehlern in der Sandbox | Engine | nicht untersucht (`RT-BIONIC-001`) |

## 2. Provider-Schlüssel — Lebenszyklus

**Soll:** Eingabe im Setup-Dialog → verschlüsselt im Android Keystore →
nur im Speicher entschlüsselt → ausschließlich als **Environment-Variable** an
den Kindprozess, nie in `argv`, nie in Logs, nie in die URL.

**Ist:**

| Schritt | Ort | Zustand |
|---|---|---|
| Schlüssel erzeugen | `ShinonApp.ShinonKeystore.ensureKey` | **IMPLEMENTED** (AES-256, `AndroidKeyStore`, GCM, nicht exportierbar) |
| Schlüsselwert speichern | — | **fehlt** (kein `storeSecret`, keine Verschlüsselung des Werts) |
| Eingabe abfragen | `SetupActivity.onCreate` | **fehlt** (nur `Log.w`, Kommentar beschreibt den geplanten Dialog) |
| Wert lesen/entschlüsseln | — | **fehlt** |
| An Prozess übergeben | `ShinonService.startEngine` | Struktur vorhanden, die `env`-Map bleibt jedoch **ohne den Schlüssel** (Kommentar: „In v1: nur die Existenz") |

Konsequenz: **SEC-KEY-001 und SEC-KEY-002 sind PLANNED**, nicht implementiert.
Ein Provider-Aufruf kann heute nicht authentifiziert werden (Gate 4 BLOCKED).

Der Alias-Schema `shinon_<provider>` (`getKeyAliasForProvider("agnes")` →
`shinon_agnes`) ist implementiert und konsistent zwischen Setup und Service.

## 3. Keystore-Konfiguration (geändert)

`ensureKey()` erzeugte den Schlüssel zuvor mit
`setEncryptionPaddings(KeyProperties.PADDING_RSA_OAEP)` und
`setUnwrapAlgorithm("AES")`. Beide Aufrufe existieren in der Android-API
**nicht** (Compiler-Fehler). Die Korrektur setzt
`KeyProperties.ENCRYPTION_PADDING_NONE`, was für AES-GCM fachlich korrekt ist
(AES-GCM arbeitet ohne Padding; RSA-OAEP gehört zu RSA-Schlüsseln).
Siehe [`DECISIONS.md`](DECISIONS.md) DEC-004.

## 4. WebView-Grenzen

| Einstellung | Wert | Ort |
|---|---|---|
| `javaScriptEnabled` | `true` | `MainActivity.configureWebView` |
| `domStorageEnabled` | `true` | dito |
| `allowFileAccess` | `false` | dito |
| `javaScriptCanOpenWindowsAutomatically` | `false` | dito |
| Navigation | nur `http://127.0.0.1` bleibt in der WebView | `shouldOverrideUrlLoading` |
| Externe URL | `ACTION_VIEW` → Systembrowser | dito |
| Zweite Prüfung | `loadUrl` verwirft alles ohne `http://127.0.0.1`-Präfix | `MainActivity.loadUrl` |

Die doppelte Prüfung (Navigation + `loadUrl`) ist bewusst: selbst ein
kompromittierter Receiver-Pfad kann keine Fremd-URL laden. Ob ein
`https`-Aufruf auf Loopback in der Praxis ein Risiko darstellt, ist
**UNVERIFIED** — die frühere Risikobewertung dazu steht in der archivierten
Bestandsaufnahme.

## 5. Logging

`ShinonService.maskSecrets()` ersetzt `[?&](token|apikey|api_key|key)=…` und
`AGNES_API_KEY…` durch `***`. Die READY-Zeile wird getrennt behandelt: geloggt
wird nur `Port <n>`, nicht die tokenisierte URL.

**Offen (`SEC-LOG-001`):** Weitere Muster (Bearer-Header, Session-IDs,
Request-IDs) werden **nicht** maskiert. Solange DSH keine solchen Werte auf
stdout ausgibt, ist das Risiko klein; es ist aber nicht geprüft, weil DSH hier
nie gestartet wurde.

## 6. Berechtigungen (Manifest)

| Permission | Zweck | Bewertung |
|---|---|---|
| `INTERNET` | Provider-Aufrufe der Engine | erforderlich |
| `FOREGROUND_SERVICE` | Dienst | erforderlich |
| `FOREGROUND_SERVICE_DATA_SYNC` | `foregroundServiceType="dataSync"` | erforderlich ab API 34 |
| `POST_NOTIFICATIONS` | Dienst-Sichtbarkeit ab API 33 | deklariert **und** zur Laufzeit angefragt (`MainActivity.requestNotificationPermissionIfNeeded`) |
| `…DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` | von AGP automatisch ergänzt | erwartet |

`WAKE_LOCK` ist **entfernt**: kein Code hält einen Wakelock, die Deklaration war
wirkungslos. Dadurch sind die angeforderten Rechte auf das für Netz, Dienst und
Benachrichtigung nötige Minimum begrenzt.

Bewusst **nicht** angefordert: externer Speicher, Boot-Receiver, Standort —
entsprechend dem Nicht-Ziel-Katalog in [`EXTENSIONS-PLAN.md`](EXTENSIONS-PLAN.md).

**Prüfauftrag aus der alten Bestandsaufnahme:** Die Behauptung, ein fehlendes
`FOREGROUND_SERVICE_DATA_SYNC` lasse den Dienst auf API 28–33 abstürzen, ist
**nicht belegt**. Das `foregroundServiceType`-Attribut wird erst ab API 29
ausgewertet, die Permission ab API 34 erzwungen. Der Befund ist deshalb als
`UNVERIFIED` geführt, nicht als geschlossen.

## 7. Umgang mit Geheimnissen im Prozess

Der Release-Keystore liegt **nie** im Repo. Die CI dekodiert ihn flüchtig in
die Runner-Umgebung und löscht ihn im Schritt „Clean up Keystore“ wieder
(`if: always()`). Fehlt `SHINON_KEYSTORE_B64`, bricht der Lauf absichtlich ab —
kein ungesigniertes Artefakt. Verifiziert: siehe [`TESTING.md`](TESTING.md) Gate 5.
