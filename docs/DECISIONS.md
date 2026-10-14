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
  nicht auf; ein Prüfschritt dafür fehlt (siehe [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) N-4).
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

---

# Offene Entscheidungen

## OPEN-001 — Wie wird das Profil `mobile` gelöst? (BLOCKIEREND)

Die App startet `--profile mobile`; in `shinon-forge` main `59a86a4` existiert
dieses Profil nicht (nur `shinon`, `headless`), es ist in
`shinon-forge/docs/MOBILE-PLAN.md` als W1-Plan beschrieben.

| Option | Konsequenz |
|---|---|
| A — Profil upstream in `shinon-forge` bauen | Sauber, aber Arbeit liegt im anderen Repo; die App bleibt bis dahin unverändert blockiert |
| B — App auf ein vorhandenes Profil umstellen | Sofort lauffähig, ändert aber das Produktverhalten (das `shinon`-Profil ist der Desktop-Zuschnitt) |
| C — Profilname konfigurierbar machen | Entkoppelt die App, braucht aber eine Quelle für den Wert (Setup-Feld oder Build-Config) |

**Bis zur Entscheidung bleibt `RT-PROF-001` BLOCKED.** Es wurde bewusst keine
Option still umgesetzt.

## OPEN-002 — Welche Runtime-Strategie? (BLOCKIEREND)

Node `< 22` ist ausgeschlossen (`engines.node`), native Addons brauchen
plattformgeprüfte Binaries (B-4). Offen ist, ob proot mit glibc-Rootfs, ein
eigenständig gebautes Bionic-Binary oder die Anlehnung an ein bestehendes
Mobile-Projekt der Weg ist. Ohne diese Wahl gibt es kein Runtime-Artefakt und
damit keinen Punkt, an dem Gate 3 überhaupt greifen kann.

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
