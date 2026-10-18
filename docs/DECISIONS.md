# Entscheidungen (ADR) — Shinon Agent

> Stand: 2026-10-14 · Ausgangsstand `e78ca1a`
>
> Format je Eintrag: **Kontext → Entscheidung → Alternativen → Konsequenz → Beleg.**
> `BESTÄTIGT` = umgesetzt bzw. geprüft beibehalten. `OFFEN` = braucht eine
> Entscheidung des Eigentümers, blockiert aber Arbeit.
>
> Grundsatz: Abweichungen von bestehenden Entscheidungen werden hier begründet
> und mit Konsequenzen versehen — nicht still im Code vollzogen.

## DEC-001 — `gradlew` reparieren statt umgehen

- **Kontext:** Der handgeschriebene Wrapper (kein regulärer Gradle-Wrapper)
  entpackte das Archiv nach `…/dists/gradle-8.7/`, setzte `GRADLE_HOME` aber auf
  `…/dists/gradle-8.7-bin/gradle-8.7` → `exec: … not found`. Zusätzlich fehlte
  `set -e`, und die Prüfung `[ ! -d "$DIST_DIR" ]` legte den Zielordner **vor**
  dem Download an: nach einem Abbruch blockierte ein leerer Ordner jeden
  weiteren Lauf.
- **Entscheidung:** Wrapper korrigieren — Prüfung auf den Launcher-Binary,
  Entpacken nach `$DIST_DIR`, `set -e`, `curl --retry 3`, Zip nach Erfolg löschen.
- **Alternativen:** `gradle/actions/setup-gradle` auch lokal (verdeckt den
  Defekt weiter) oder den Wrapper durch einen generierten Standard-Wrapper
  ersetzen (größerer Eingriff, andere Dateien).
- **Konsequenz:** Lokaler Build über `./gradlew` möglich. **Die CI nutzt weiter
  `gradle` statt `./gradlew`** — dort fällt ein Wrapper-Defekt nach wie vor
  nicht auf; ein Prüfschritt dafür fehlt (siehe [`CI-AND-RELEASE.md`](CI-AND-RELEASE.md) §4).
- **Beleg:** `GRADLE_USER_HOME=/tmp/gw-test ./gradlew --version` → Gradle 8.7
  startet nach vollständigem Eigen-Download (Exit 0).

## DEC-002 — Toolchain benutzerlokal statt systemweit

- **Kontext:** Die Umgebung hat kein `sudo` (`no new privileges`), kein Java,
  kein Android SDK.
- **Entscheidung:** JDK 17 und Android SDK nach `.local/` installieren,
  reproduzierbar über `scripts/setup-toolchain.sh`; `local.properties` mit
  `sdk.dir` (von `.gitignore` gedeckt).
- **Alternativen:** Systeminstallation (nicht möglich), Versionen in CI pinnen
  (bereits gegeben).
- **Konsequenz:** `.local/` ist **nicht** versioniert und nach einem Restore
  leer. Das ist gewollt — dafür ist das Setup-Skript die eine Quelle.
- **Beleg:** [`TESTING.md`](TESTING.md) Gate 0.

## DEC-003 — Speicherdeckel im Build, `gradle.properties` unangetastet

- **Kontext:** `org.gradle.jvmargs=-Xmx2048m` in `gradle.properties` sprengt in
  dieser Umgebung die Memory-Cgroup; der Build stirbt mit Exit 137
  (`Memory cgroup out of memory`).
- **Entscheidung:** Die sparsamen Werte (`-Xmx768m`, `--max-workers=1`,
  Kotlin `in-process`, `vfs.watch=false`) stehen **nur** in `scripts/build.sh`,
  nicht im versionierten `gradle.properties`.
- **Alternativen:** `gradle.properties` dauerhaft senken — hätte die CI
  mitverändert und die dort reichlich vorhandene Reserve verschenkt.
- **Konsequenz:** Der Standardaufruf `./gradlew …` kann hier weiterhin OOMen.
  Wer hier baut, nutzt `scripts/build.sh`.
- **Beleg:** `scripts/build.sh :app:assembleDebug` → `BUILD SUCCESSFUL in 26s`;
  die Überschreibung wurde am Daemon kontrolliert (`-Xmx768m` sichtbar).

## DEC-004 — AES-GCM mit `ENCRYPTION_PADDING_NONE`

- **Kontext:** `ShinonKeystore.ensureKey()` rief
  `setEncryptionPaddings(KeyProperties.PADDING_RSA_OAEP)` und
  `setUnwrapAlgorithm("AES")` auf. Beides existiert in der Android-API nicht
  (Compiler-Fehler; `PADDING_RSA_OAEP` heißt korrekt
  `ENCRYPTION_PADDING_RSA_OAEP` und gehört zu RSA).
- **Entscheidung:** `setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)`
  setzen, `setUnwrapAlgorithm` entfernen. Für einen AES-256-GCM-Schlüssel ist
  „kein Padding" fachlich korrekt.
- **Alternativen:** `ENCRYPTION_PADDING_RSA_OAEP` stehen lassen — würde bei
  einem AES-Schlüssel die Schlüsselerzeugung fehlschlagen lassen.
- **Konsequenz:** Die Schlüsselerzeugung ist API-konform. **Unverändert offen:**
  der Schlüssel wird weiterhin nur erzeugt, nie benutzt, um einen Wert zu
  speichern (SEC-KEY-001).
- **Beleg:** `:app:assembleDebug` kompiliert; `i: `-Fehler verschwunden.

## DEC-005 — Entkopplungsvertrag App ≠ Engine ≠ Vendor (BESTÄTIGT)

- **Kontext:** Engine (`shinon-forge`) und Vendor (`node_modules`) sollen
  aktualisierbar sein, ohne die App neu zu bauen; die APK soll keine
  Engine-Daten enthalten.
- **Entscheidung:** Beibehalten. Runtime liegt zur Laufzeit in
  `filesDir/runtime/`; die APK prüft ihren Inhalt selbst (CI-Inhaltsgate) und
  der Dienst prüft zur Laufzeit auf `runtime_missing` statt `ENOENT`.
- **Konsequenz:** Verifiziert am echten Artefakt (kein Treffer im APK).
- **Beleg:** [`TESTING.md`](TESTING.md) Gate 2.

## DEC-006 — Release-Signing bleibt fail-closed (BESTÄTIGT)

- **Kontext:** Ein Release-APK ohne gültige Signatur darf nicht entstehen.
- **Entscheidung:** Beibehalten. CI bricht ohne `SHINON_KEYSTORE_B64` ab;
  `signingConfigs.release` liest ausschließlich aus der Umgebung.
- **Konsequenz:** Ohne Secrets gibt es kein Release-Artefakt — auch keinen
  „Notbehelf" mit Debug-Signatur.
- **Beleg:** `:app:validateSigningRelease` → Exit 1 mit
  `Keystore file … not found for signing config 'release'`.

## DEC-007 — Prozessaufbau korrigiert statt Befehl umgangen

- **Kontext:** Zwei Compiler-Fehler mit Bedeutungsverlust:
  `.environment().putAll(env).redirectErrorStream(true)` hängt
  `redirectErrorStream` an das Ergebnis von `putAll` (`Unit`);
  `if (!proc.waitFor(…))` stand als Ausdruck am Ende eines `let`-Lambdas und
  braucht deshalb einen `else`-Zweig.
- **Entscheidung:** Builder explizit aufbauen (`ProcessBuilder(...)`
  → `directory` → `redirectErrorStream`, dann `environment().putAll(env)`,
  dann `start()`); `if`/`else` explizit ausschreiben und den Erfolgsfall
  (`SIGTERM` sauber) mitloggen.
- **Alternativen:** `env` gar nicht setzen (hätte die geplante
  Schlüssel-Übergabe entfernt) oder den `waitFor`-Pfad vereinfachen (hätte die
  3-Sekunden-Frist verändert).
- **Konsequenz:** Verhalten bleibt fachlich identisch; die Kette ist jetzt
  typkorrekt.
- **Beleg:** `:app:assembleDebug` → `BUILD SUCCESSFUL`.

## DEC-008 — Alte Bestandsaufnahme archiviert, Doku-Struktur neu

- **Kontext:** `docs/S0-BESTANDS-AUFNAHME.md` beschrieb F-1 bis F-3 noch als
  offen, obwohl sie im Code behoben sind, und referenzierte einen Branch
  `shinon-forge/develop`, den es nicht gibt. README begann mittendrin bei „## 4.".
- **Entscheidung:** Bestandsaufnahme nach `docs/archive/` verschieben und mit
  einem Kopfbanner als historisch kennzeichnen (nichts löschen). README und die
  Detaildokumente neu schreiben, mit Statusvokabular und Belegen.
- **Alternativen:** Datei löschen (verliert die Herleitung der Risiken) oder
  unverändert liegen lassen (zwei konkurrierende Wahrheiten).
- **Konsequenz:** Eine gültige Doku-Struktur; die historische Datei bleibt lesbar.
- **Beleg:** Diese Dokumente; [`README.md`](../README.md) Doku-Index.

## DEC-009 — N-4 bereinigt: ungenutzte Deklarationen entfernt statt dokumentiert

- **Kontext:** Befund N-4 listete vier Deklarationen ohne Wirkung und einen
  CI-Trigger auf einen nicht existierenden Branch. Das Dokument hielt sie als
  Kandidaten fest, statt sie zu ändern.
- **Entscheidung:**
  1. `WAKE_LOCK` entfernt — es gibt keinen `PowerManager`-Aufruf.
  2. `androidx.webkit:webkit` entfernt (nirgends importiert), dazu die nur
     darauf bezogene ProGuard-Regel `-keep class androidx.webkit.**`.
  3. `ACTION_STATUS` entfernt — die Konstante wurde in `onStartCommand` nie
     behandelt.
  4. `develop` aus den Push-Triggern entfernt — den Branch gibt es nicht.
  5. `POST_NOTIFICATIONS` **nicht** entfernt, sondern wirksam gemacht: die
     Manifest-Deklaration allein zeigt die Dienst-Benachrichtigung ab API 33
     nicht an. `MainActivity.requestNotificationPermissionIfNeeded()` fragt sie
     zur Laufzeit an (Löschen wäre eine Regression gegen SVC-NOTIF-001).
  6. Zusätzlich beim Prüfen gefunden und mitbereinigt: fünf ungenutzte Imports,
     das write-only Feld `urlReceived`, sowie
     `android.defaults.buildfeatures.buildconfig=true` (`BuildConfig` wird
     nirgends referenziert; AGP 8 meldet das Property als deprecated).
- **Alternativen:** Alles unverändert lassen — hätte wirkungslose Rechte und
  einen toten Trigger im Repo belassen. Oder `POST_NOTIFICATIONS` löschen — hätte
  eine dokumentierte Soll-Anforderung gebrochen.
- **Konsequenz:** Kleineres Berechtigungsprofil (kein `WAKE_LOCK`), kleinere APK
  (5.649.850 statt 5.702.163 Bytes), keine AGP-Deprecation-Warnung mehr.
  `-dontwarn org.webkit.**` bleibt bewusst stehen (harmlos; Entfernung nur mit
  vollem Release-Lauf belegbar). Die Sichtbarkeit der Benachrichtigung auf einem
  Gerät ist weiterhin **UNVERIFIED**.
- **Beleg:** `:app:assembleDebug` → `BUILD SUCCESSFUL in 32s` (APK-SHA256
  `e315cbb4…e2d6`), `:app:minifyReleaseWithR8` → `BUILD SUCCESSFUL in 2m 5s`,
  `:app:dependencies` ohne `webkit`, Permission-Liste im APK ohne `WAKE_LOCK`.

## DEC-010 — `DSH_HOME` explizit setzen (Prozessstart-Korrektur)

- **Kontext:** DSH löst Profile als **`$DSH_HOME/profiles/<name>`** auf
  (dsh-README: „`--profile <name>` = the profile under `$DSH_HOME/profiles` to
  boot"). Belegt in der Registry: `@deepseek-ai/dsh@0.2.1-alpha.1`
  `README.md:11` und `lib/bin.js:105` („the profile under $DSH_HOME/profiles to
  boot“). Der Forge-Einstieg `bin/shinon.mjs:107` setzt `DSH_HOME` deshalb
  explizit auf den Repo-Root. `ShinonService.startEngine()` setzte es **nicht**.
- **Entscheidung:** `DSH_HOME` im Builder-Environment auf das Runtime-Verzeichnis
  setzen (`builder.environment()["DSH_HOME"] = dshDir.absolutePath`), passend zum
  ohnehin gesetzten `cwd = dshDir`.
- **Alternativen:** `DSH_HOME` aus `System.getenv()` erben — auf Android nicht
  gesetzt, also wirkungslos. Auf das `cwd` vertrauen — nicht belegt, dass DSH
  daraus das Home ableitet.
**Konsequenz:** Der Prozessstart entspricht den realen Anforderungen der
Engine. **Damit ist B-2 nicht gelöst:** das Profil `mobile` selbst fehlt
weiterhin (`OPEN-001`), und ein Lauf ist ohne Gerät nicht nachweisbar.
- **Beleg:** `scripts/build.sh :app:assembleDebug` → `BUILD SUCCESSFUL in 46s`,
APK-SHA256 `e315cbb4…e2d6`, Entkopplungsgate `PASS`. Der Laufzeitnachweis
bleibt Gate 3 (`BLOCKED`).

## DEC-011 — proot-Debian-Rootfs-Strategie (OPEN-002-Entscheidung)

- **Kontext:** `OPEN-002` fragt, welche Runtime-Strategie: proot mit
  glibc-Rootfs, eigenständiges Bionic-Binary oder Anlehnung an ein
  bestehendes Mobile-Projekt. Die native Addons (koffi/node-pty/sharp,
  B-4) sind gegen glibc gebaut und unter Bionic nicht nativ ladbar.
- **Entscheidung (2026-10-18):** **proot-Debian-Rootfs** — dasselbe
  Modell, das die Hermes-App (Android, `hermes.agent.mobile`) einsetzt:
  ein Debian-glibc-Userland, das den Node-Prozess + `shinon-forge` +
  `node_modules` enthält und in der App-`filesDir/runtime/` liegt. Die
  native Addons laufen in der glibc-Userland, NIE nativ unter Bionic.
- **Alternativen:** (a) Eigenständiges Bionic-Node-Binary — die
  native Addons müssten alle gegen Bionic neu gebaut werden (aufwändig,
  nicht belegbar hier). (b) Anlehnung an `dsh-io/dsh-mobile` — ein
  Fork-Basis-Kandidat, aber die Runtime-Pins/Verträge/Sicherheit/Lizenz
  müssten separat geprüft werden (MOBILE-PLAN.md §3) und es ist eine
  Abhängigkeit von einem externen Projekt.
- **Konsequenz:** B-1 (Runtime-Installation), B-4 (Bionic-Addons) und
  B-5 (Bezugsquelle) sind damit architektonisch gelöst. Der Runtime-
  Tarball wird von der Forge-CI gebaut und als Release `runtime/9118bc8/`
  an `shinon-forge` gehängt; die App lädt ihn per `RUNTIME_TARBALL_URL`
  und prüft `RUNTIME_SHA256` (fail-closed). Die Kompilierung +
  Live-Verifikation bleiben Gate 1 (CI) und Gate 3 (Device).
- **Beleg:** `SetupActivity.kt` (proot-Tarball-Download + SHA256 + Marker),
  `ShinonApp.kt` (API-Key-Keystore), `ShinonService.kt` (DSH_HOME +
  AGNES_API_KEY-Env). `profiles/mobile` auf `shinon-forge` main `34163aa`.

---

# Offene Entscheidungen

## OPEN-001 — Wie wird das Profil `mobile` gelöst? (BLOCKIEREND)

Die App startet `--profile mobile`; in `shinon-forge` main `59a86a4`
existierte dieses Profil nicht (nur `shinon`, `headless`), es war in
`shinon-forge/docs/MOBILE-PLAN.md` als W1-Plan beschrieben.

**Status (2026-10-18): RESOLVED — Option A (Profil upstream gebaut).**
`profiles/mobile` existiert jetzt auf `shinon-forge` main (`34163aa`).
Die App pinnt den neuen Stand `SHINON_FORGE_PIN = "9118bc8"` (main,
DSH `0.2.1-rc.2`), der `profiles/mobile` enthält (11 Bundles).
`dsh --profile mobile --dump-config` liefert gegen den gemergten Stand
einen sauberen DSH-Stack. B-2 ist damit RESOLVED.

## OPEN-002 — Welche Runtime-Strategie? (BLOCKIEREND)

Node `< 22` ist ausgeschlossen (`engines.node`), native Addons brauchen
plattformgeprüfte Binaries (B-4). Offen war, ob proot mit glibc-Rootfs,
ein eigenständig gebautes Bionic-Binary oder die Anlehnung an ein
bestehendes Mobile-Projekt der Weg ist.

**Status (2026-10-18): RESOLVED — proot-Debian-Rootfs (DEC-011).**
Die Runtime-Strategie ist festgelegt: ein Debian-glibc-Userland
(proot), das den Node-Prozess + `shinon-forge` + `node_modules` enthält.
Die native Addons laufen in der glibc-Userland (B-4 gelöst). Der
Runtime-Tarball wird von der Forge-CI gebaut und als Release
`runtime/9118bc8/shinon-runtime-arm64.tar.zst` an `shinon-forge`
gehängt; die App lädt ihn per `RUNTIME_TARBALL_URL` und prüft
`RUNTIME_SHA256` (fail-closed, B-1/B-5 gelöst). Der Rest (Gate 3
Device-Smoke, B-6) bleibt ein Laufzeitnachweis, nicht eine
Architekturfrage.

## OPEN-003 — Fehlertrennung und Diagnose

Falsche Node-Fassung, fehlendes Modul, nativer Ladefehler und Auth-Fehler sind
heute nicht unterscheidbar (N-3). Vorschlag: Exit-Code-/Stderr-Muster
klassifizieren und in getrennte Broadcast-Gründe abbilden
(`node_version`, `module_missing`, `native_failed`, `auth_failed`).

## OPEN-004 — Runner für Gate 3

Es fehlt eine Ausführungsumgebung mit KVM oder ein echtes ARM64-Gerät (B-6).
Zu entscheiden ist, ob Gate 3 dauerhaft manuell bleibt (wie bisher geplant)
oder ein Runner beschafft wird — davon hängt ab, ob `android-device-smoke`
je `required` werden kann.

## OPEN-005 — Doku über zwei Repos konsolidieren

`MOBILE-PLAN.md` und die Mobile-Gates liegen in `shinon-forge`, die App-Doku
hier. Es gibt dadurch Verweise, die aus diesem Repo nicht auflösbar sind
(N-6). Zu entscheiden: Verweise mit Quellenangabe beibehalten, Plan kopieren
(Drift-Risiko) oder ein gemeinsames Index-Dokument führen.
