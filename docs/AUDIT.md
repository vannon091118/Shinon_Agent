# Audit — Ist-Zustand, Prüfpunkte und Blocker

> Stand: 2026-10-15 · Basis: Ausgangsstand `e78ca1a`, Arbeitsstand `347d958` + DSH_HOME-Fix
>
> Dieses Dokument ist die **Belegschicht**: jeder Befund nennt Fundstelle,
> beobachtetes Verhalten, Auswirkung, Reproduktionsschritt und Korrektur.
> Die Blocker-Zusammenfassung liegt in [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md),
> der Anforderungsbezug in [`TRACEABILITY.md`](TRACEABILITY.md).
>
> **Regel:** Was hier nicht als ausgeführtes Kommando steht, ist nicht verifiziert.
> Externe Beobachtungen (GitHub-Oberfläche) sind als solche gekennzeichnet.

## 1. Phase A — Ist-Bericht

### 1.1 Shinon_Agent

| Punkt | Wert |
|---|---|
| Remote | `origin` = `https://github.com/vannon091118/Shinon_Agent.git` |
| Ausgangsstand | Branch `freebuff/26b468caadd46c8f77ba61d9` @ `e78ca1af9f624f3ae1a204861af479942d0a226c` (== `origin/main`) |
| Arbeitsstand | Feature-Branch `feat/scope-audit-and-docs` (remote vorhanden) |
| `git status --short` | leer — Arbeitsbaum sauber |
| Stashes | **keine** (`git stash list` leer) |
| Lokale Branches | `freebuff-base` (`be96f2b` „Initial cloud project"), Arbeitsbranch |
| Remote-Branches (`git ls-remote`) | `main` `e78ca1a`, `feat/notion-session-runner-scaffold` `8595b93`, `feat/scope-audit-and-docs` |
| Tags | **keine** |
| CI | `.github/workflows/build.yml` (Release-Build, Signing, Inhaltsgate); in der Actions-Übersicht zusätzlich Läufe eines nicht mehr vorhandenen Workflows `ci-install` |
| Tests | **keine** — `app/src/test` und `app/src/androidTest` existieren nicht |
| Build-Kommandos | `./gradlew …`, `scripts/build.sh …`, `scripts/setup-toolchain.sh` |
| Dokumentation | `README.md`, `docs/{AUDIT,SCOPE,ARCHITECTURE,SETUP-AND-RUNTIME,SECURITY,TESTING,CI-AND-RELEASE,KNOWN-LIMITATIONS,DECISIONS,TRACEABILITY,EXTENSIONS-PLAN}.md`, `docs/archive/S0-BESTANDS-AUFNAHME.md` |
| Offene TODOs im Code | keine (`grep -rn "TODO\|FIXME" app/src` leer) |

**Gesuchter Branch `freebuff/9cb8ef20a819e5be2cde53fe`: existiert nicht.**

```
git branch -a --list '*9cb8*'                                  → leer (lokal)
git ls-remote --heads https://github.com/vannon091118/Shinon_Agent.git
  → nur main, feat/notion-session-runner-scaffold (+ feat/scope-audit-and-docs
    nach dem Push dieser Arbeit)
```

Der Branch galt laut Auftrag als „nicht bestätigt" — er ist auch nicht vorhanden.
Es gibt **keinen** unbekannten lokalen S3-Arbeitsstand, auf den zugegriffen
werden müsste: die einzige unveröffentlichte Arbeit war der uncommittete
`gradlew`-Fix, der gesichert und committet ist.

### 1.2 shinon-forge (nur lesend geprüft)

| Punkt | Wert |
|---|---|
| Remote | `https://github.com/vannon091118/shinon-forge.git` |
| Leseklon | `.local/audit/shinon-forge` (`--depth 50`, **nicht** im Repo) |
| HEAD | `59a86a413ef0ad4caf1eefd6ca937e99abd0de6d` (`main`, 2026-10-14) |
| Remote-Branches | `main` `59a86a4`, `plan/mobile-first-prototype` `382f7b6` |
| Tags | `v0.2.0`, `v0.3.0` |
| Branch `develop` | **existiert nicht** (404; `ls-remote` kennt ihn nicht) |
| Commit `d7d38ce` | **existiert nicht** — der in `SetupActivity.SHINON_FORGE_PIN` hinterlegte „Pin" ist nicht belegbar |
| Workflows | nur `commit-guard.yml` — **kein** Build-/Test-Workflow, also keine prüfbaren Forge-CI-Läufe |
| Profile | `headless`, `shinon` — **kein `mobile`** |
| Manifest | `@shinon/forge` 0.4.0, `engines.node` `^22.19.0 \|\| >=24.0.0`, `bin.shinon` → `bin/shinon.mjs`, 31 Scripts, Deps `@deepseek-ai/dsh 0.2.1-alpha.1`, `@deepseek-ai/schemastery ~3.18.4` |
| Offene TODOs im Code | keine (`packages/`, `scripts/`, `bin/`: 0 Treffer) |
| Doku | 13 Dateien in `docs/`, u. a. `MOBILE-PLAN.md` (der Mobile-Plan — liegt **nicht** in diesem Repo) |

### 1.3 Sicherung

| Datei | Inhalt |
|---|---|
| `.local/backup/HEAD.txt` | Branch, HEAD `e78ca1a`, `origin/main` `e78ca1a`, Basis `be96f2b` |
| `.local/backup/uncommitted.patch` | der uncommittete Stand vor allen Änderungen (binärsicher, `--binary`) |
| `.local/backup/status.txt` | vollständiger Status zum Zeitpunkt der Sicherung |
| `.local/backup/stashes.txt` | leer — es gab keine Stashes |
| `.local/backup/untracked-list.txt` + `untracked.tgz` | leer — es gab keine untracked Dateien außer `.local/` |
| `.local/backup/refs.txt` | alle Refs |

Verifikation: `git apply --reverse --check .local/backup/uncommitted.patch` →
„PATCH OK" (der Patch entspricht exakt dem damaligen Arbeitsbaum).
Kein `reset --hard`, kein `clean -fd`, keine Force-Resets. Die Sicherung
dokumentiert den Stand **vor** den Änderungen; alles danach ist committet und
damit über Git gesichert.

### 1.4 Nicht überprüfbare Punkte (ausdrücklich offen)

| Punkt | Warum nicht überprüfbar |
|---|---|
| GitHub-Actions-Läufe im Detail | kein `gh`/Token-Zugriff; nur die öffentliche Actions-Oberfläche wurde beobachtet (24 Läufe, alle als fehlgeschlagen dargestellt, letzter `build` #10 am 2026-10-14) |
| Forge-CI-Läufe | es gibt keinen Forge-Build-Workflow, nur `commit-guard.yml` |
| Geräte-/Emulatornachweis | kein AVD, keine `system-images`, `/dev/kvm` (`root:kvm` 660) für diesen Benutzer nicht les-/schreibbar |
| Ausführung von DSH | `npm install @deepseek-ai/dsh@0.2.1-alpha.1` wurde zweimal vom OOM-Killer beendet (Exit 137) |
| Provider-Aufruf | keine Zugangsdaten, kein laufender Prozess |

## 2. Prüfpunkte (Auftrag §4) — verifiziert am aktuellen Code

| # | Prüfpunkt | Fundstelle | Beobachtetes Verhalten | Auswirkung | Reproduktion | Korrektur | Status |
|---|---|---|---|---|---|---|---|
| 1 | `ProcessBuilder`-Initialisierung + Env-Übergabe | `ShinonService.kt:144-152` (Kommando), `:168-172` (Builder), `:178` (`DSH_HOME`) | Builder wird explizit aufgebaut (`directory`, `redirectErrorStream`), danach `environment().putAll(env)` und `DSH_HOME`, dann `start()`. Kommando: `node <dsh> --profile mobile --no-open --trusted-host localhost --trusted-host 127.0.0.1 --port 0` | Startpfad kompiliert; **nie ausgeführt** | `grep -n "ProcessBuilder" app/src/main/java/com/vannon/shinon/ShinonService.kt`; Laufzeit: Gate 3 | keine im Code offen außer OPEN-001 (Profil) | **UNVERIFIED** |
| 2 | Node.js-Mindestversion erzwingen | `app/src`: **kein Treffer**; Gegenseite `shinon-forge/bin/shinon.mjs:51-59` | Die App prüft nichts und startet `node` direkt. Nur Forge prüft (`runningMajor < 22` → Re-Exec oder `exit 2`). Laut Forge-Kommentar sterben `node:sqlite`/`parseEnv` unter Node < 22 schon beim Import | Zu altes Node → Abbruch mit Exit ≠ 0, der in den generischen Reconnect läuft (siehe `N-3`) | `grep -rn "22\|engines" app/src \| grep -i node` → leer; `sed -n '45,60p' .local/audit/shinon-forge/bin/shinon.mjs` | `RT-NODE-001`: `node --version` vor Start prüfen, ≥ 22 erzwingen, Grund `node_version` melden | **PLANNED** |
| 3 | Vollständigkeit von `installRuntime()` | `SetupActivity.kt:56-57` (Aufruf), `:89-96` (Rumpf), `:70` (Flag), `:38` (Pin) | `mkdirs` + Log + `marker.exists()` → liefert `false`; der Rückgabewert wird ignoriert; `setup_done = true` wird trotzdem gesetzt. Der Pin `d7d38ce` existiert nicht | `startEngine()` endet **immer** in `runtime_missing` → Gate 3 strukturell unmöglich | `sed -n '50,72p;89,96p' app/src/main/java/com/vannon/shinon/SetupActivity.kt`; `git ls-remote https://github.com/vannon091118/shinon-forge.git` (kein `d7d38ce`) | `AND-SETUP-002`: echtes Bezugsartefakt + SHA256, Rückgabe auswerten, Flag erst nach Erfolg; Pin auf realen Stand (`59a86a4`/`v0.3.0`) | **BLOCKED** (Bezugsartefakt: `OPEN-002`) |
| 4 | Einbindung des entschlüsselten API-Schlüssels | `ShinonService.kt:154-171` (Env-Block), `ShinonApp.kt:60-101` | `env = System.getenv()` + leerer `if`-Zweig. Es gibt **kein** `storeSecret`/`readSecret`; `SetupActivity.kt:61` prüft nur die Alias-Existenz | Kein authentifizierter Provider-Aufruf möglich | `grep -n "storeSecret\|readSecret" app/src/main/java/com/vannon/shinon/ShinonApp.kt` → leer | `SEC-KEY-001/002` | **PLANNED** |
| 5 | Gültigkeit der Keystore-API-Nutzung | `ShinonApp.kt:60-88` (`ensureKey`), `:73` (`ENCRYPTION_PADDING_NONE`), `:76-80` (`KeyGenerator`), `:92-101` (`hasKey`) | Nach der Reparatur API-konform; kompiliert. Vorher: `PADDING_RSA_OAEP` und `setUnwrapAlgorithm` existierten nicht | Kein Compile-Blocker mehr; Laufzeitverhalten nur auf einem Gerät prüfbar (`AndroidKeyStore` existiert nicht auf dem Desktop) | `scripts/build.sh :app:assembleDebug` → grün | Geräteprüfung; optional Schlüsselrotation/`deleteAlias` | **UNVERIFIED** |
| 6 | Berechtigungen für Foreground Services | `AndroidManifest.xml:6-16` (Permissions), `:43-46` (`<service>`, `foregroundServiceType="dataSync"`); `MainActivity.kt:88-90,160-171` | `INTERNET`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`, `POST_NOTIFICATIONS`; `POST_NOTIFICATIONS` wird zur Laufzeit angefragt. `WAKE_LOCK` ist entfernt | Manifest ist mit dem Diensttyp konsistent; das tatsächliche Startverhalten ist ungeprüft | `aapt2 dump badging app-debug.apk \| grep uses-permission`; Gate 3 | Gerätetest auf API 34 | **PARTIAL** — die alte S0-Behauptung („Crash auf API 28–33") bleibt **UNVERIFIED** |
| 7 | Sichere Validierung des WebView-Hosts | `MainActivity.kt:118-127` (`shouldOverrideUrlLoading`), `:134` (Präfixprüfung in `loadUrl`) | Nur `http` + `127.0.0.1` bleibt in der WebView, alles andere geht per `ACTION_VIEW` in den Systembrowser; zusätzlich Präfixprüfung vor `loadUrl` | Doppelte Absicherung. Die Annahme „DSH druckt eine Loopback-URL" ist jetzt **belegt** (siehe §3) | `grep -n "startsWith\|shouldOverrideUrlLoading" …/MainActivity.kt` | keine im Code; Geräteverhalten prüfen | **IMPLEMENTED** (Code) / **UNVERIFIED** (Gerät) |
| 8 | APK-Content-Gates + Runtime-Artefakte | `build.yml:74-86` (Gate), `:51/:68/:84` (`exit 1`) | `unzip -l "$APK" \| grep -Ei 'node_modules\|shinon-forge\|/dsh\|profiles?/mobile'` → Treffer = Build rot. Am echten APK nachgefahren: kein Treffer; das APK enthält keine `.so` | Gate funktioniert; in der CI greift es nur auf dem **Release**-Artefakt (kein Debug-Job) | `unzip -l app/build/outputs/apk/debug/app-debug.apk \| grep -Ei 'node_modules\|shinon-forge\|/dsh\|profiles?/mobile'` | `CI-DEBUG-001`: Debug-Job + Hash dokumentieren | **IMPLEMENTED** (verifiziert) / `CI-DEBUG-001` **PLANNED** |
| 9 | Wrapper, JDK, Release-Signing, Debug-CI | `gradlew` (Fix), `gradle/wrapper/gradle-wrapper.properties` (8.7), `app/build.gradle.kts:8,12,13,34,43,48,59-63`, `gradle.properties:11-15`, `build.yml:16,72` | Wrapper lädt 8.7 selbst (verifiziert); JDK 17 erzwungen (`VERSION_17`, `jvmTarget 17`); Signing aus Env und fail-closed; Release minifiziert; CI baut **nur** Release und triggert nur auf `main` | Lokaler Build reproduzierbar; kein Debug-/Test-/Lint-Job in der CI | `./gradlew --version`; `:app:validateSigningRelease` → Exit 1; `grep -n "branches:" .github/workflows/build.yml` | `CI-DEBUG-001`; CI sollte `./gradlew` verwenden | **PARTIAL** |
| 10 | Native Abhängigkeiten unter Bionic | Registry (`npm view`) | `dsh-fs-local` → `koffi 3.1.1`; `dsh-subprocess-local` → `koffi 3.1.1` + `node-pty 1.2.0-beta.15`; `dsh-attachment-local` → `sharp ^0.35.3`; `dsh` → `node-addon-require-builtin ^0.1.6` | Ob diese Module unter Android/Bionic laden, ist **nicht untersucht** — sie werden üblicherweise gegen glibc gebaut | `npm view @deepseek-ai/dsh-subprocess-local@0.2.1-alpha.1 dependencies` | Bionic-Proof auf ARM64: `node` starten, `require('koffi')` ausführen | **BLOCKED** |
| 11 | Ladefähigkeit eines mobilen Forge-Profils | `shinon-forge/profiles/` (`headless`, `shinon`), `dsh`-README, `bin/shinon.mjs:107` | Die App ruft `--profile mobile`; das Profil existiert nicht. DSH löst Profile als **`$DSH_HOME/profiles/<name>`** auf — die App setzte `DSH_HOME` **nicht** (jetzt korrigiert, `ShinonService.kt:178`); Forge setzt es explizit auf den Repo-Root | Profilauflösung schlägt fehl → nie eine READY-Zeile | `ls -1 .local/audit/shinon-forge/profiles/`; `grep -n "DSH_HOME" .local/audit/shinon-forge/bin/shinon.mjs`; `grep -n "DSH_HOME" app/src/main/java/com/vannon/shinon/ShinonService.kt` | `OPEN-001` (Profil) + `DSH_HOME` (**erledigt**, siehe `DEC-010`) | **BLOCKED** (Profil) / teilweise korrigiert |
| 12 | Reproduzierbarkeit/Pinning des Runtime-Root-Dateisystems | in diesem Repo: **nichts** | Kein Artefakt, kein Bezugsskript, kein Hash, kein Build für ein Runtime-Paket | Gate 3 und das Release sind nicht reproduzierbar aufsetzbar | `git ls-files \| grep -Ei "runtime\|sha256"` → nur Dokumentation | `RT-PIN-001` (Artefakt bauen und pinnen) | **PLANNED** / **BLOCKED** (`OPEN-002`) |

## 3. READY-Zeilen-Vertrag — jetzt quellengestützt belegt

Die App sucht in `ShinonService.parseReadyUrl` die Zeile
`Regex("dsh web: (http://\\S+)")`. Bisher war das eine Annahme. Beleg aus der
DSH-Registry (Tarball-Inhalt, kein Installationsversuch):

```
@deepseek-ai/dsh-web-app@0.2.1-alpha.1  lib/index.js:211
  if (config.printUrl) console.log(`dsh web: ${authenticatedUrl}${lanUrl === void 0 ? "" : ` (LAN: ${lanUrl})`}`);

@deepseek-ai/dsh-web-app@0.2.1-alpha.1  README.md:56
  publicUrl | Unset | Advertised HTTP(S) application root; otherwise announce the listener's loopback URL
```

Damit gilt: die READY-Zeile beginnt mit `dsh web: `, trägt ohne `--public-url`
die **Loopback**-URL, und `\S+` erfasst sie ohne den optionalen ` (LAN: …)`-Teil.
Das passt zur Präfixprüfung `http://127.0.0.1` und zum Regex der App.

**Grenzen dieser Aussage:** Die Quelle belegt das **Format**, nicht den Lauf.
Der Ende-zu-Ende-Nachweis (Gate 3) bleibt offen. Ebenfalls offen: ob `--port 0`
(OS-gewählter Port) von DSH akzeptiert wird — in der DSH-Doku ist nur ein
expliziter Port belegt.

Reproduktion:

```bash
cd /tmp && mkdir dsh-pack && cd dsh-pack
npm pack @deepseek-ai/dsh-web-app@0.2.1-alpha.1
tar xzf deepseek-ai-dsh-web-app-*.tgz
grep -n "dsh web:" package/lib/index.js
```

## 4. Blockerbericht — Voraussetzung und Reproduktion

| Blocker | Fehlende Voraussetzung | Reproduktionsschritt (nach Behebung) | Erwartetes Ergebnis |
|---|---|---|---|
| **B-1** Runtime wird nie installiert | Bezugsartefakt (Node-Binary + Forge + `node_modules`) und dessen SHA256 | App installieren → Setup → `filesDir/runtime/` prüfen | `node` und `node_modules/.bin/dsh` existieren; `setup_done` erst dann |
| **B-2** Profil `mobile` fehlt | gewählte Option aus `OPEN-001` | `dsh --profile <name> --dump-config` | Profilbaum ohne ausgeschlossenen Layer |
| **B-3** API-Schlüssel erreicht den Prozess nicht | Implementierung `storeSecret`/`readSecret` + Setup-Dialog | Schlüssel eingeben, Prozess starten, `env` prüfen | Schlüssel nur im Environment, nie in `argv`/Logs |
| **B-4** native Addons ungeprüft | ARM64-Gerät | `node -e "require('koffi')"` im Runtime-Paket | kein `dlopen`-Fehler |
| **B-6** kein Gerät/Emulator | ARM64-Gerät **oder** Runner mit KVM-Zugriff | `adb install` + Start, Logcat auf READY-Zeile | `dsh web: http://127.0.0.1:<port>/?token=…` |
| **Gate 4** Provider-Test | gültige Zugangsdaten | Chat im WebView senden | echte Antwort; Auth-Fehler unterscheidbar |
| **Gate 5** signiertes Release | die vier `SHINON_KEYSTORE_*`-Secrets | CI-Workflow `build` auslösen | signiertes APK + Prüfsumme; ohne Secrets roter Lauf |
| **Lint** | mehr RAM als diese Umgebung bietet | `scripts/build.sh :app:lintDebug` | Report unter `app/build/reports/` |

## 5. Verbleibende Risiken

1. **Der wirksamste Hebel fehlt:** Ohne Runtime-Artefakt (`OPEN-002`) und ohne
   Profil (`OPEN-001`) ändert jede weitere App-Verbesserung nichts am
   Funktionsstand — sie bleibt eine Shell, die baut, aber nichts startet.
2. **Zwei Repos, ein Produkt:** Der Mobile-Fortschritt hängt an `shinon-forge`;
   aus diesem Repo sind die dortigen Planungsaussagen nicht prüfbar.
3. **Keine Tests:** jede Verhaltensaussage ist statisch oder gar nicht belegt —
   die ersten Testkandidaten stehen in [`TRACEABILITY.md`](TRACEABILITY.md) §4.
4. **Umgebungsgrenzen:** Lint und ein `npm install` von DSH scheitern hier am
   Speicherdruck der Cgroup; Gate 3/4 scheitern an fehlender Hardware.
5. **Nachweisdisziplin:** Ein grüner Compiler-Lauf, ein grünes README oder ein
   Agentenbericht sind **kein** Abnahmenachweis — dafür stehen die Gates in
   [`TESTING.md`](TESTING.md).
