# Bekannte Einschränkungen — Shinon Agent

> Stand: 2026-10-18 · Sortiert nach Blockierkraft. Jeder Punkt nennt Beleg,
> Auswirkung und den konkreten nächsten Schritt.
>
> Belegquellen: `app/src/main/java/com/vannon/shinon/…` (Repo),
> `.local/audit/shinon-forge` (Leseklon von `shinon-forge` main `59a86a4`),
> `npm view` und `npm pack` (Registry), sowie die in [`TESTING.md`](TESTING.md)
> genannten Kommandos. Die vollständige Belegschicht — je Befund Fundstelle,
> beobachtetes Verhalten, Auswirkung, Reproduktion und Korrektur — liegt in
> [`AUDIT.md`](AUDIT.md).
>
> **2026-10-18-Update:** B-1, B-2 und B-3 wurden in der W4-Shell geschlossen
> (proot-Debian-Rootfs-Strategie + API-Key-Keystore). Die drei Punkte bleiben
> als Verweisziele, der Status ist jetzt `RESOLVED` bzw. `IMPLEMENTED` —
> nicht „gelöscht". Die Kompilierung ist auf den CI-Run abgestützt (lokal
> kein Android-SDK, Gate-1b-OOM), die Live-Verifikation bleibt Gate 3.

## B-1 — Die Runtime wird nie installiert (Blocker für alles): **RESOLVED**

**Beleg (altes Verhalten, 2026-10-14):** `SetupActivity.installRuntime()`
legte `filesDir/runtime/` an und lieferte
`runtimeDir.resolve(".shinon-runtime-$SHINON_FORGE_PIN").exists()` —
dieser Marker wurde **nirgends** erzeugt.

**Auflösung (2026-10-18):** `installRuntime()` installiert die Runtime jetzt
ECHT (proot-Debian-Rootfs-Strategie, OPEN-002-Entscheidung):
1. Download des gepinnten Runtime-Tarballs (`RUNTIME_TARBALL_URL`)
2. **SHA256-Prüfung fail-closed** (`RUNTIME_SHA256`) — bei Mismatch `false`
3. Extraktion nach `filesDir/runtime/`
4. **Marker NUR nach Erfolg** erzeugt — `ShinonService` prüft genau diesen
5. Existenzprobe `node + shinon-forge/node_modules/.bin/dsh`

Der `SHINON_FORGE_PIN` ist von `d7d38ce` (nicht existierender develop-Branch)
auf `9118bc8` (main, DSH `0.2.1-rc.2`) gezogen — der Stand, der
`profiles/mobile` enthält (B-2).

**Offener Rest:** `RUNTIME_SHA256` ist ein Platzhalter
(`AUSGEWICHSEN-ERSETZEN-DURCH-DEN-IM-CI-ERRECHNETEN-WERT`) und die
`RUNTIME_TARBALL_URL` zeigt auf einen **noch nicht existierenden**
Forge-Release-Endpunkt. Die SHA256-+URL-Kopplung wird mit dem ersten
Forge-CI-Run befüllt (B-5 → [`DECISIONS.md`](DECISIONS.md) DEC-011). Bis
dahin ist Gate 3 `BLOCKED`, nicht `FAIL` — die Struktur ist korrekt, der
einzige fehlende Wert ist der CI-erzeugte Prüfsummen-Paar.

**Nächster Schritt:** Forge-CI baut den Runtime-Tarball, hängt ihn als
Release `runtime/9118bc8/` an `shinon-forge`, liefert SHA256; App-Flow
trägt beide Werte ein (1 Zeile in `SetupActivity.kt`).

## B-2 — Das Profil `mobile` existiert nicht: **RESOLVED**

**Beleg (alter Stand, 2026-10-14):** `ShinonService.startEngine()` startete
mit `--profile mobile`; im Leseklon `shinon-forge` main `59a86a4` enthielt
`profiles/` nur `shinon` und `headless`.

**Auflösung (2026-10-18):** `profiles/mobile` existiert jetzt auf `shinon-forge`
main (`34163aa`, „feat(mobile): establish an isolated, testable DSH profile").
Die App pinnt den neuen Stand `SHINON_FORGE_PIN = "9118bc8"` (main,
DSH `0.2.1-rc.2`), der `profiles/mobile` enthält (11 Bundles:
dsh-base, dsh-web-app, persona, core, events, locale-de, better-errors,
token-usage, prompter, narrative, mobile). `dsh --profile mobile
--dump-config` liefert gegen den gemergten Stand einen sauberen DSH-Stack.

**Zusätzlich (im Zuge dieses Audits gefunden und behoben):** DSH löst Profile
als `$DSH_HOME/profiles/<name>` auf; `ShinonService` setzt `DSH_HOME`
explizit (`ShinonService.kt:178`, DEC-010).

**Rest:** Der `dsh --profile mobile`-Lauf bleibt als Gate 3 `BLOCKED`
(kein Gerät/KVM, B-6) — nur das Format (READY-Regex, Provider-Block) ist
hier belegt, nicht der Lauf.

## B-3 — Der API-Schlüssel erreicht den Prozess nicht: **IMPLEMENTED**

**Beleg (altes Verhalten, 2026-10-14):** `ShinonApp.ShinonKeystore` hatte
`ensureKey`, `hasKey`, `getKeyAliasForProvider` — aber **keine** Methode,
um den Schlüsselwert zu speichern oder zu lesen. `SetupActivity` zeigte
keinen Eingabedialog (nur `Log.w`). In `ShinonService.startEngine()`
enthielt die `env`-Map den Schlüssel nicht („In v1: nur die Existenz").

**Auflösung (2026-10-18):**
- `ShinonKeystore` hat jetzt `storeSecret(alias, plaintext)` /
  `readSecret(alias)` / `getApiKeyForProcess(provider)` — AES-256-GCM
  über den Android-Keystore-Schlüssel, Ciphertext + IV (12 B) in der
  App-internen `SharedPreferences`-Datei `shinon_secrets`, **nie im
  Klartext**. `SEC-KEY-001/002` sind damit `IMPLEMENTED`.
- `SetupActivity` zeigt einen echten API-Key-Dialog (PASSWORD-EditText),
  speichert sofort verschlüsselt.
- `ShinonService.startEngine()` injiziert `AGNES_API_KEY` +
  `PROMPTER_API_KEY` per Environment in den Node-Prozess — **nie** in
  argv, Logs oder die URL.

**Rest:** Keine Code-Lücke mehr. Gate 4 (authentifizierter Provider-Aufruf)
bleibt `BLOCKED`, solange kein Device-Smoke gelaufen ist (B-6) — die
Struktur ist aber vollständig.

## B-4 — Native Addons der Engine: Android/Bionic nicht geprüft

**Beleg (Registry, `npm view`):**

| Paket | Native Abhängigkeit |
|---|---|
| `@deepseek-ai/dsh-fs-local@0.2.1-alpha.1` | `koffi 3.1.1` (FFI, vorkompilierte Binaries) |
| `@deepseek-ai/dsh-subprocess-local@0.2.1-alpha.1` | `koffi 3.1.1`, `node-pty 1.2.0-beta.15` |
| `@deepseek-ai/dsh-attachment-local@0.2.1-alpha.1` | `sharp ^0.35.3` (libvips) |
| `@deepseek-ai/dsh@0.2.1-alpha.1` | `node-addon-require-builtin ^0.1.6` |

**Status (2026-10-18):** Die proot-Debian-Rootfs-Strategie (B-1/OPEN-002)
lädt die native Addons in der glibc-Userland, NIE nativ unter Bionic —
die Addons laufen im proot-glibc-Kontext, nicht im Android-Bionic-Kontext.
Das ist dieselbe Strategie, die die Hermes-App (das Android-Shell, auf
der diese Arbeit ausgeführt wird) erfolgreich einsetzt.

**Rest:** Der Gerät-Smoke (Gate 3, B-6) bleibt `BLOCKED` — der Nachweis,
dass die Addons im proot-Debian-Kontext auf dem echten ARM64-Device laden,
braucht einen Live-Lauf. Bis dahin: `UNVERIFIED` (keine Annahme, kein
still „gut gehen lassen").

**Nächster Schritt:** Gate-3-Live-Lauf auf echtem ARM64-Device (manuell
oder Runner mit KVM), `require('koffi')`-Modul-Test in der proot-
Umgebung, Ergebnis in `docs/TESTING.md` Gate 3 dokumentieren.

## B-5 — Kein Node-Binary und keine Runtime-Bezugsquelle

**Beleg:** Es gibt im Repo kein Runtime-Artefakt, kein Bezugsskript, keine
SHA256-Liste. `.gitignore` schließt `app/src/main/assets/runtime/` bewusst
aus. `engines.node` der Engine verlangt `^22.19.0 || >=24.0.0`.

**Status (2026-10-18):** Die Bezugsquelle ist jetzt definiert
(B-1-Auflösung): `RUNTIME_TARBALL_URL` + `RUNTIME_SHA256` in
`SetupActivity.kt`. Der Endpunkt zeigt auf den **noch nicht existierenden**
Forge-Release-Flow (`runtime/9118bc8/shinon-runtime-arm64.tar.zst`), den
die Forge-CI baut (parallel laufend, [`DECISIONS.md`](DECISIONS.md)
DEC-011). Die SHA256 wird vom CI errechnet und in die App eingetragen
(1 Zeile). Bis dahin bleibt Gate 3 `BLOCKED` (falscher SHA256-Platzhalter
= fail-closed, kein Download).

**Nächster Schritt:** Forge-CI-Flow (b) baut den Runtime-Tarball +
hängt ihn als Release an `shinon-forge` + liefert die SHA256; App-Flow
(a) trägt beide Werte in `SetupActivity.kt` ein.

## B-6 — Emulator fehlt und KVM ist gesperrt

**Beleg:** `avdmanager list avd` → leer; `sdkmanager --list_installed` → keine
`system-images`; `/dev/kvm` ist `root:kvm 660` und für diesen Benutzer nicht
les- oder schreibbar.

**Auswirkung:** Gate 3 kann in dieser Umgebung **nicht** ausgeführt werden —
auch nicht nach Installation eines System-Images (Hardwarebeschleunigung fehlt).

**Nächster Schritt:** Prüfung auf einem echten ARM64-Gerät (manuell) oder auf
einem Runner mit KVM-Zugriff.

## N-1 — Lint ist hier nicht ausführbar

`:app:lintDebug` wurde begonnen und vom OOM-Killer beendet (Exit 137,
`Memory cgroup out of memory`). Es entstand kein Report — es liegt **keine**
Aussage über Lint-Verstöße vor. Auszuführen auf einem Runner mit mehr RAM.

## N-2 — Keine automatisierten Tests

`app/src/test` und `app/src/androidTest` existieren nicht. Jede Verhaltensaussage
ist damit statisch oder gar nicht belegt. Vorschläge für die ersten Tests:
[`TRACEABILITY.md`](TRACEABILITY.md) §4.

## N-3 — Fehlertrennung ist grob

Falsche Node-Fassung, fehlendes Modul, nativer Ladefehler und Auth-Fehler
landen alle im generischen Reconnect-Pfad (`Exit ≠ 0` → 3 Versuche → `crash`).
Zielbild Punkt 9 („Fehler sauber unterscheiden") ist offen.

## N-4 — Ungenutzte Deklarationen: **BEREINIGT**

Alle fünf Punkte sind entfernt bzw. aufgelöst. Die Nummer bleibt als
Verweisziel erhalten, der Befund ist geschlossen.

| Deklaration | Auflösung | Beleg |
|---|---|---|
| `WAKE_LOCK` | entfernt — es gab keinen `PowerManager`-Aufruf | Permission-Liste der APK enthält sie nicht; `unzip -p … AndroidManifest.xml \| strings \| grep -c WAKE_LOCK` → `0` |
| `androidx.webkit:webkit:1.11.0` | Dependency entfernt, dazu die nur darauf bezogene Regel `-keep class androidx.webkit.**` in `app/proguard-rules.pro` | `:app:dependencies` zeigt kein `webkit` mehr im Runtime-Classpath; `:app:minifyReleaseWithR8` → `BUILD SUCCESSFUL in 2m 5s`, kein „Missing class“ |
| `POST_NOTIFICATIONS` | **nicht gelöscht**, sondern wirksam gemacht: Laufzeitabfrage in `MainActivity.requestNotificationPermissionIfNeeded()` (API 33+). Löschen hätte SVC-NOTIF-001 gebrochen | Code vorhanden; APK-Deklaration unverändert — Sichtbarkeit auf Gerät **UNVERIFIED** |
| `ACTION_STATUS` | Konstante entfernt (wurde in `onStartCommand` nie behandelt) | `grep -rn ACTION_STATUS app/src/` leer |
| `develop` in `.github/workflows/build.yml` | aus den Push-Triggern entfernt — den Branch gibt es nicht | `on.push.branches: [ main ]` |

**Zusätzlich bereinigt** (dieselbe Kategorie, beim Prüfen gefunden): fünf
ungenutzte Imports in `MainActivity.kt` (`Uri`, `FrameLayout`, `ProgressBar`,
`TextView`, `WebSettings`), das write-only Feld `urlReceived` (nur geschrieben,
nie gelesen) und `android.defaults.buildfeatures.buildconfig=true` in
`gradle.properties` — `BuildConfig` wird nirgends referenziert, und AGP 8 meldet
das Property als deprecated (die Warnung ist seither aus dem Build-Log
verschwunden).

**Verblieben und bewusst nicht geändert:** `-dontwarn org.webkit.**` in
`app/proguard-rules.pro`. Die Regel war an `androidx.webkit` gekoppelt; ihre
Entfernung ist nur mit einem vollständigen Release-Lauf belegbar. Sie ist
harmlos, wird aber erst mit einem signierten Release geprüft.

**Gesamtnachweis:** `scripts/build.sh :app:assembleDebug` → `BUILD SUCCESSFUL
in 32s`, APK 5.649.850 Bytes, SHA256 `e315cbb4…e2d6`, Entkopplungsgate `PASS`,
keine Kotlin-Warnung über ungenutzte Symbole.

## N-5 — `RECEIVER_NOT_EXPORTED` ohne Versionsweiche

`MainActivity` registriert beide Receiver mit `Context.RECEIVER_NOT_EXPORTED`.
Die Konstante existiert erst ab API 33; `minSdk` ist 26. Auf API 26–32 ist das
Verhalten **UNVERIFIED** (möglicher Laufzeitfehler beim Registrieren).
Fix-Skizze: Weiche auf `Build.VERSION.SDK_INT >= 33`, sonst
`registerReceiver(receiver, filter)`.

## N-6 — Doku-Referenzen zeigen in ein anderes Repo

`docs/EXTENSIONS-PLAN.md` und `docs/archive/S0-BESTANDS-AUFNAHME.md` verweisen
auf `MOBILE-PLAN.md`. Diese Datei liegt **nicht** in diesem Repo, sondern in
`shinon-forge/docs/MOBILE-PLAN.md`. Die Verweise sind jetzt als extern
gekennzeichnet; ein Konsolidierungsentscheid steht aus.
