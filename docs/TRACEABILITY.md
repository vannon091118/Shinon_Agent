# Traceability — Shinon Agent

> Stand: 2026-10-14 · Ausgangsstand `e78ca1a`
> Verknüpft Anforderungs-IDs ([`SCOPE.md`](SCOPE.md)) mit Implementierungsort,
> Nachweis und Gate. `Status` ist die Bewertung aus Sicht des Codes.

## 1. Anforderung → Code → Nachweis

| ID | Implementierungsort | Nachweis | Gate | Status |
|---|---|---|---|---|
| AND-BUILD-001 | `app/build.gradle.kts`, `settings.gradle.kts`, `gradlew` | `:app:assembleDebug` → `BUILD SUCCESSFUL`, APK `b83615ae…cd6f` | 1, 2 | **IMPLEMENTED** |
| AND-BUILD-002 | `app/build.gradle.kts` (`signingConfigs.release`), `.github/workflows/build.yml` | `:app:validateSigningRelease` → Exit 1 ohne Keystore | 5 | **PARTIAL** |
| AND-SETUP-001 | `SetupActivity.onCreate`, `installRuntime` | Code-Review; Rückgabewert wird ignoriert | 3 | **PARTIAL** |
| AND-SETUP-002 | `SetupActivity.installRuntime` (Platzhalter) | Marker wird nie erzeugt | 3 | **PLANNED** |
| AND-SETUP-003 | `SetupActivity.onCreate` (nur `Log.w`) | fehlender Dialog | 4 | **PLANNED** |
| RT-NODE-001 | — (keine Prüfung im Code) | — | 3 | **PLANNED** |
| RT-PROC-001 | `ShinonService.startEngine` | Code vorhanden, nie ausgeführt | 3 | **UNVERIFIED** |
| RT-PROF-001 | `ShinonService.startEngine` (`--profile mobile`) | Profil fehlt in `shinon-forge` main | 3 | **BLOCKED** |
| RT-READY-001 | `ShinonService.parseReadyUrl` (`Regex("dsh web: (http://\\S+)")`) | Regex vorhanden, nie gegen echtes DSH | 3 | **UNVERIFIED** |
| SEC-KEY-001 | `ShinonApp.ShinonKeystore` | keine `storeSecret`-Methode | 4 | **PLANNED** |
| SEC-KEY-002 | `ShinonService.startEngine` (`env`-Map) | Schlüssel wird nicht eingetragen | 4 | **PLANNED** |
| SEC-LOG-001 | `ShinonService.maskSecrets` | nur `token`/`apikey`/`AGNES_API_KEY` | 3/4 | **PARTIAL** |
| SEC-HOST-001 | `MainActivity.shouldOverrideUrlLoading`, `loadUrl` | doppelte Prüfung, statisch geprüft | Gerät | **IMPLEMENTED** (Code) |
| SEC-SIGN-001 | `.gitignore`, CI-Steps 4/10 | Ignore-Regeln + fail-closed belegt | 0, 5 | **IMPLEMENTED** |
| SVC-FGS-001 | `ShinonService.onStartCommand`, `stopEngine`, `stopNodeProcess` | Code vorhanden, nie ausgeführt | 3 | **UNVERIFIED** |
| SVC-NOTIF-001 | `Manifest` (`POST_NOTIFICATIONS`), `MainActivity.requestNotificationPermissionIfNeeded`, `ShinonService.createNotificationChannel` | Laufzeitabfrage vorhanden; Sichtbarkeit auf einem Gerät nicht geprüft | Gerät | **PARTIAL** |
| WEB-RCV-001 | `MainActivity.onCreate` (`Context.RECEIVER_NOT_EXPORTED`) | keine Weiche für API < 33 | Gerät | **PARTIAL** |
| APP-RESTART-001 | `SetupActivity` (`setup_done`), `START_STICKY` | nur ein Flag persistiert | Gerät | **PARTIAL** |
| RT-BIONIC-001 | — | `koffi`, `node-pty`, `sharp`, `node-addon-require-builtin` per `npm view` belegt | 3 | **BLOCKED** |
| RT-PIN-001 | — | kein Pin, kein Archiv | 3, 5 | **PLANNED** |
| CI-DEBUG-001 | `.github/workflows/build.yml` (nur `assembleRelease`) | kein Debug-Job | CI | **PLANNED** |
| CI-CONTENT-001 | `build.yml` Schritt „APK-Content-Gate" | lokal am echten APK nachgefahren, kein Treffer | 2 | **IMPLEMENTED** |
| CI-RELEASE-001 | `build.yml` Schritte 4, 8, 9 | fail-closed im Workflow verdrahtet; Läufe alle rot (Oberflächen-Beobachtung) | 5 | **PARTIAL** |
| DOC-001 | `README.md`, `docs/*` | Verweise in sich stimmig; alte Bestandsaufnahme archiviert | — | **IMPLEMENTED** |

## 2. Gate → ausgeführte Prüfung

| Gate | Kommando/Beleg | Ergebnis |
|---|---|---|
| 0 | `scripts/setup-toolchain.sh`, `./gradlew --version`, `sdkmanager --list_installed` | **PASS** |
| 1 | `scripts/build.sh :app:assembleDebug` | **PASS** (vorher 5 Compile-Fehler) |
| 1b | `scripts/build.sh :app:lintDebug` | **BLOCKED** (OOM, Exit 137) |
| 2 | `unzip -l`, Entkopplungsgate, `apksigner verify`, `aapt2 dump badging` | **PASS** |
| 3 | nicht ausgeführt (kein Gerät, kein KVM, kein Runtime-Paket, kein `mobile`-Profil) | **BLOCKED** |
| 4 | nicht ausgeführt (kein Prozess, keine Zugangsdaten, kein Key-Pfad) | **BLOCKED** |
| 5 | `:app:validateSigningRelease`, `:app:minifyReleaseWithR8` | **PARTIAL** (fail-closed belegt, R8 grün, Signaturlauf offen) |

## 3. Offene Befunde → Dokument

| Befund | Ort |
|---|---|
| Runtime-Platzhalter | [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) B-1 |
| fehlendes `mobile`-Profil | B-2, [`DECISIONS.md`](DECISIONS.md) OPEN-001 |
| fehlender Schlüsselpfad | B-3 |
| native Addons ungeprüft | B-4 |
| fehlendes Runtime-Artefakt | B-5, OPEN-002 |
| kein Gerät/KVM | B-6, OPEN-004 |
| Lint nicht ausführbar | N-1 |
| keine Tests | N-2 |
| grobe Fehlertrennung | N-3, OPEN-003 |
| ungenutzte Deklarationen | N-4 (bereinigt) |
| `RECEIVER_NOT_EXPORTED` ohne Weiche | N-5 |
| Doku-Verweise ins andere Repo | N-6, OPEN-005 |

## 4. Vorschläge für die ersten Tests (heute: keine vorhanden)

| Test | Art | Prüft |
|---|---|---|
| `maskSecrets` gegen eine Reihe von Token-Formen | JVM-Unit-Test | SEC-LOG-001 |
| READY-Regex gegen echte DSH-Zeilen (Erfolg/Fehler/kein Treffer) | JVM-Unit-Test | RT-READY-001 |
| `shouldOverrideUrlLoading`-Entscheidung als reine Funktion | JVM-Unit-Test | SEC-HOST-001 |
| URL-Präfixprüfung in `loadUrl` (positiv/negativ) | JVM-Unit-Test | SEC-HOST-001 |
| `ShinonKeystore` erzeugen/speichern/lesen | instrumentiert | SEC-KEY-001 |
| Receiver-Registrierung auf API 26–34 | instrumentiert | WEB-RCV-001 |
| Dienst-Start/Stop mit Attrappen-Runtime | instrumentiert | SVC-FGS-001 |

Diese Tests existieren **nicht**. Sie sind Vorschläge, keine Umsetzung — die
Reihenfolge richtet sich nach OPEN-001/OPEN-002, weil Tests ohne Runtime nur
die Randlogik abdecken können.
