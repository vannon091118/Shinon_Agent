# Scope — Shinon Agent

> Stand: 2026-10-14 · Ausgangsstand `e78ca1a`
> Statusvokabular: **IMPLEMENTED** · **PARTIAL** · **PLANNED** · **BLOCKED** · **UNVERIFIED**
>
> „IMPLEMENTED" heißt: der Code ist vorhanden. Es heißt **nicht**, dass das
> Verhalten auf einem Gerät nachgewiesen ist — das ist `UNVERIFIED` bzw.
> `BLOCKED`. Kein Gate wird grün genannt, ohne dass das Kommando ausgeführt wurde.

## 1. Zielbild (Soll)

Nach vollständiger Umsetzung soll die App:

1. installierbar sein (APK);
2. beim ersten Start die Runtime kontrolliert installieren oder einen
   nachvollziehbaren Fehler melden;
3. eine kompatible Node.js-Fassung verwenden (`^22.19.0 || >=24.0.0`);
4. DSH und Shinon Forge über definierte, stabile Pfade starten;
5. Provider und API-Key sicher konfigurieren;
6. den Schlüssel bei echten Provider-Aufrufen verwenden, ohne ihn offenzulegen;
7. Runtime-Status, Setup-Fortschritt, Fehler und Logs verständlich darstellen;
8. Zustand und Konfiguration über App-Neustarts hinweg erhalten;
9. Fehler bei Installation, Start, Authentifizierung und Provider-Aufrufen
   sauber unterscheiden;
10. überprüfbar und reproduzierbar gebaut werden.

**Punkt 1 ist erreicht. Punkte 2–9 sind nicht erreicht.** Siehe
[`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md).

## 2. Scope-Matrix

| ID | Anforderung | Prio | Ist-Zustand | Abhängigkeiten | Abnahmekriterium | Testnachweis | Status |
|---|---|---|---|---|---|---|---|
| AND-BUILD-001 | Debug-APK reproduzierbar bauen | Muss | Build läuft | JDK 17, SDK 34, Gradle 8.7 | `:app:assembleDebug` → Exit 0, APK existiert | Gate 2 | **IMPLEMENTED** (verifiziert) |
| AND-BUILD-002 | Release-APK signiert, fail-closed | Muss | Signing-Config vorhanden, fail-closed belegt | Keystore-Secrets | Ohne Secrets **kein** APK; mit Secrets signiertes APK | Gate 5 | **PARTIAL** (fail-closed verifiziert, Signaturlauf fehlt) |
| AND-SETUP-001 | Setup-Flow beim Erststart | Muss | `SetupActivity` legt Verzeichnis an, setzt Flag | — | Flag erst nach erfolgreicher Runtime-Installation | Gate 3 (Vorlauf) | **PARTIAL** — Flag wird auch bei fehlgeschlagener Installation gesetzt (`SetupActivity.installRuntime()` Rückgabe wird nicht geprüft) |
| AND-SETUP-002 | Runtime wirklich installieren (Download + SHA256) | Muss | Platzhalter, `installRuntime()` setzt nie einen Marker | Runtime-Artefakt + Bezugsquelle | Nach Setup existieren `node` und `node_modules/.bin/dsh` | Gate 3 | **PLANNED** (Code existiert als Platzhalter) |
| AND-SETUP-003 | API-Key erfassen und speichern | Muss | Dialog fehlt, nur Log-Warnung | `ShinonKeystore.storeSecret()` | Key liegt verschlüsselt im Keystore | Gate 4 | **PLANNED** |
| RT-NODE-001 | Kompatible Node-Fassung erzwingen | Muss | **Keine** Prüfung im App-Code | Node-Binary ≥ 22 im Runtime-Paket | Falsche Fassung → klarer Fehler statt Absturz | Gate 3 | **PLANNED** |
| RT-PROC-001 | Prozessstart über `ProcessBuilder` + Env | Muss | Code vorhanden, **nie ausgeführt** | Runtime-Paket | Prozess startet, Exit-Code wird behandelt | Gate 3 | **UNVERIFIED** |
| RT-PROF-001 | DSH lädt das Profil `mobile` | Muss | Profil existiert in `shinon-forge` **nicht** | Profil upstream (dort geplant) | `--dump-config` löst alle Layer auf | Gate 3 | **BLOCKED** |
| RT-READY-001 | READY-Handshake `dsh web: http://…` | Muss | Regex vorhanden, nie gegen echtes DSH gelaufen | RT-PROF-001 | READY-URL mit Port, maschinenlesbar | Gate 3 | **UNVERIFIED** |
| SEC-KEY-001 | Provider-Key im Android Keystore | Muss | Key wird erzeugt, **Wert nie gespeichert** | `storeSecret()`-Implementierung | `hasKey()` nach Speichern wahr | Gate 4 | **PLANNED** |
| SEC-KEY-002 | Key nur per Environment an den Prozess | Muss | Env-Map wird gebaut, Key fehlt darin | SEC-KEY-001 | Key steht in `environment()`, nie in argv | Gate 4 | **PLANNED** |
| SEC-LOG-001 | Keine Secrets in Logs | Soll | `maskSecrets()` vorhanden | Erweiterte Muster | Kein Token in Logausgabe | Gate 3/4 (Logsichtung) | **PARTIAL** (nur `token`/`apikey`/`AGNES_API_KEY`) |
| SEC-HOST-001 | WebView nur `http://127.0.0.1` | Muss | Prüfung im Code vorhanden | — | Externe URL → Systembrowser | Gerätetest | **IMPLEMENTED** (Code) / **UNVERIFIED** (Gerät) |
| SEC-SIGN-001 | Keystore/Secrets nie im Repo | Muss | `.gitignore` deckt `*.jks`, `keystore/` | — | Repo-Scan leer | Gate 0 | **IMPLEMENTED** (verifiziert) |
| SVC-FGS-001 | Foreground-Service startet/stoppt kontrolliert | Muss | Code vorhanden | Runtime | Dienst sichtbar, stoppbar, kein Orphan | Gate 3 | **UNVERIFIED** |
| SVC-NOTIF-001 | Nutzer sieht die Dienst-Benachrichtigung | Soll | deklariert **und** Laufzeitabfrage vorhanden (API 33+) | — | Benachrichtigung sichtbar | Gerätetest | **PARTIAL** (Gerätetest offen) |
| WEB-RCV-001 | Receiver-Registrierung API-34-konform | Muss | `RECEIVER_NOT_EXPORTED` gesetzt, ohne Fallback für API < 33 | Versionsweiche | Kein Crash auf API 26–32 | Gerätetest | **PARTIAL** |
| APP-RESTART-001 | Zustand über App-Neustarts erhalten | Soll | Nur `setup_done`-Flag | — | Neustart zeigt denselben Zustand | Gerätetest | **PARTIAL** |
| RT-BIONIC-001 | Native DSH-Addons laufen auf Bionic | Muss | **Nicht untersucht** | Nachweis auf Gerät | DSH startet ohne `dlopen`-Fehler | Gate 3 | **BLOCKED** (koffi, node-pty, sharp — siehe KNOWN-LIMITATIONS) |
| RT-PIN-001 | Runtime-Pinning reproduzierbar | Muss | Kein Pin, kein Archiv | Runtime-Build | Gleicher Input → gleiche SHA256 | Gate 3/5 | **PLANNED** |
| CI-DEBUG-001 | CI baut die Debug-APK | Muss | Workflow baut nur Release | — | Grüner Debug-Job | CI-Lauf | **PLANNED** |
| CI-CONTENT-001 | APK-Inhaltsgate (Entkopplung) | Muss | Logik vorhanden, am Debug-APK nachgefahren | — | Kein Forge-/Vendor-Fund im APK | Gate 2 | **IMPLEMENTED** (verifiziert am APK) |
| CI-RELEASE-001 | Release nur bei grünen Gates | Muss | Fail-closed verdrahtet | Secrets | Leeres Secret → Build rot | Gate 5 | **PARTIAL** (Verhalten verifiziert, CI-Läufe alle rot) |
| DOC-001 | Doku codebasiert und widerspruchsfrei | Soll | Neu geschrieben, alte Bestandsaufnahme archiviert | — | Keine zwei konkurrierenden Aussagen | Dieser Umbau | **IMPLEMENTED** |

## 3. Muss / Soll / Später / Nicht

**Muss (v1-Abnahme):** AND-BUILD-001/002, AND-SETUP-001/002/003, RT-NODE-001,
RT-PROC-001, RT-PROF-001, RT-READY-001, SEC-KEY-001/002, SEC-HOST-001,
SEC-SIGN-001, SVC-FGS-001, WEB-RCV-001, RT-BIONIC-001, RT-PIN-001,
CI-DEBUG-001, CI-CONTENT-001, CI-RELEASE-001.

**Soll:** SEC-LOG-001, SVC-NOTIF-001, APP-RESTART-001, DOC-001.

**Später (nach dem ersten Live-Test):** Dateimanager, Terminal, Device-Tools —
Entwurf in [`EXTENSIONS-PLAN.md`](EXTENSIONS-PLAN.md). Voraussetzung laut
Plan: required `android-device-smoke`, Update-Mechanismus, Third-Party-Lizenzen.

**Nicht (bewusst ausgeschlossen):**

- Capacitor, React Native, Framework-Overhead.
- DSH-Fork (die Engine bleibt `shinon-forge`).
- Runtime-Artefakte oder `node_modules` in der APK.
- Zugriff auf `/sdcard` (nur App-interner Speicher).
- Behauptung, eine Runtime laufe auf Android, weil sie auf Desktop-Linux läuft.
- Integration nativer Pakete ohne geprüfte Android/Bionic-Kompatibilität.
- Automatischer Setup-Erfolg, solange Runtime-Start nicht nachgewiesen ist.

## 4. Verbindliche Abnahmekriterien

1. **Gate 3 muss auf einem echten Gerät oder Emulator laufen**, mit echter
   Runtime und echtem Profil. Ein erfolgreicher Compiler-Lauf ist kein Ersatz.
2. **Gate 4 muss einen echten Provider-Aufruf zeigen** (Erfolg **und**
   Auth-Fehler) — ein lokaler Start beweist keine Provider-Verbindung.
3. **Gate 3 und Gate 4 sind getrennt.** Grün in einem Gate färbt das andere nicht.
4. **Fehlende Umgebung ist `BLOCKED`, nicht `PASS`.**
5. **Release nur** bei grünen Pflicht-Gates und vorhandenen Secrets.
