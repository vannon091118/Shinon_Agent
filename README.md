## 4. CI und Release-Signing (MOBILE-PLAN.md §5 W4-Gates)

| Gate / Job | Prüft | Wann blockierend |
|---|---|---|
| android-build | Release-/Debug-Build, Kotlin-Logik, Manifest/Permissions, reproduzierbare Runtime-Pins, SHA256-Verifikation | ab W4 |
| android-device-smoke | Install, Start, READY/Token, WebView, Prozessende, Offline-/Crash-Recovery, Display-Lock (Emulator/echtes Gerät) | nach stabiler Runner-Verfügbarkeit, schrittweise required |

Kein `android-device-smoke` als Required, bis ein reproduzierbarer Runner steht (MOBILE-PLAN.md §5 W3: „zunächst nicht required; nach stabiler Runner-Verfügbarkeit schrittweise required").

### Secrets-Vertrag: Release-Keystore NIE im Repo

Der `.jks`-Keystore liegt **nie** im Repository (`.gitignore`: `*.jks`, `keystore/`). Stattdessen:

1. **Lokale .jks-Datei erzeugen** (einmalig, lokal — kommt nicht ins Repo):
   ```bash
   keytool -genkeypair \
     -v -keystore keystore/release.jks \
     -alias shinon -keyalg RSA -keysize 4096 -validity 10000 \
     -storepass <PASSWORT> -keypass <PASSWORT> \
     -dname "CN=Shinon, OU=Vannon, O=Vannon, L=DE, ST=DE, C=DE"
   ```

2. **In GitHub Repository Secrets** (Settings → Secrets and variables → Actions):
   ```bash
   # Base64-Konvertierung (der String, nicht die Datei, ins Repo)
   base64 -w0 keystore/release.jks > keystore/release.jks.b64
   # Als Secrets setzen:
   #   SHINON_KEYSTORE_B64    = Inhalt von keystore/release.jks.b64
   #   SHINON_KEYSTORE_ALIAS  = shinon
   #   SHINON_KEYSTORE_PASS   = <PASSWORT>
   #   SHINON_KEY_ALIAS_PASS  = <PASSWORT>
   ```

3. **CI-Workflow** (`.github/workflows/build.yml`) dekodiert das Keystore temporär in der Runner-Umgebung:
   ```yaml
   - name: Decode Keystore from Secrets
     env:
       SHINON_KEYSTORE_B64: ${{ secrets.SHINON_KEYSTORE_B64 }}
     run: |
       mkdir -p keystore
       echo "${SHINON_KEYSTORE_B64}" | base64 -d > keystore/release.jks
       echo "SHINON_KEYSTORE_PATH=$(pwd)/keystore/release.jks" >> $GITHUB_ENV
   ```
   Die `.jks`-Datei bleibt **nur** in der Runner-Umgebung — nie als Artifact, nie in Logs.

4. **`app/build.gradle.kts`** liest die Signatur aus Environment-Variablen (`signingConfigs.release`):
   - `storeFile`: `SHINON_KEYSTORE_PATH` (in CI dekodiert)
   - `storePassword`: `SHINON_KEYSTORE_PASS`
   - `keyAlias`: `SHINON_KEYSTORE_ALIAS`
   - `keyPassword`: `SHINON_KEY_ALIAS_PASS`

**Fail-closed:** `SHINON_KEYSTORE_B64` fehlt → CI-Step `Decode Keystore` schlägt fehl, **kein** ungesigntes APK wird hochgeladen.

### Release-Flow (erster Live-Test, v0.0.1)

- **APK-Download:** Das signierte APK wird von der CI als [actions/upload-artifact](https://github.com/actions/upload-artifact) hochgeladen (`shinon-agent-v0.0.1.apk`) **und** an das [GitHub Release](https://github.com/vannon091118/Shinon_Agent/releases) `v0.0.1` gehängt (actions/release).
- **Live-Test-Quoten:** `android-device-smoke` läuft **nicht** required (MOBILE-PLAN.md §5 W3). Die Abnahme (Gate `android-build`) ist der erste, reproduzierbare Release-Lauf; das Live-Test-Device wird manuell installiert, nicht per CI-Emulator.

## 5. Integration mit shinon-forge

- **Git-Dependency:** `shinon-forge` als Submodule (pin: `develop`-Stand am 2026-10-14, `d7d38ce`) oder als gepinnte Git-URL im Gradle-Script. **Nicht** als npm-Paket — `shinon-forge` ist kein published NPM-Paket.
- **Profil-Override:** Der Android-Host startet DSH mit `--profile mobile` (explizit, ohne die `scripts.dev`-Konfiguration von `shinon-forge` anzufassen — `bin/shinon.mjs` und `scripts/open.mjs` tragen den `--profile`-Override).
- **Gate-Verdrahtung:** `shinon-forge` prüft das Mobile-Profil per `gate:full` (Zweig 10 in `commit-guard.yml`, fail-closed Verdikt).

## 6. Lizenz

MIT — wie `shinon-forge` (dritte Parteien: `@deepseek-ai/*`-Bundles, AndroidX). Third-Party-Notices im Release-Flow, nicht in v1.
