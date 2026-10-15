# Bekannte Einschränkungen — Shinon Agent

> Stand: 2026-10-14 · Sortiert nach Blockierkraft. Jeder Punkt nennt Beleg,
> Auswirkung und den konkreten nächsten Schritt.
>
> Belegquellen: `app/src/main/java/com/vannon/shinon/…` (Repo),
> `.local/audit/shinon-forge` (Leseklon von `shinon-forge` main `59a86a4`),
> `npm view` und `npm pack` (Registry), sowie die in [`TESTING.md`](TESTING.md)
> genannten Kommandos. Die vollständige Belegschicht — je Befund Fundstelle,
> beobachtetes Verhalten, Auswirkung, Reproduktion und Korrektur — liegt in
> [`AUDIT.md`](AUDIT.md).

## B-1 — Die Runtime wird nie installiert (Blocker für alles)

**Beleg:** `SetupActivity.installRuntime()` legt `filesDir/runtime/` an und
liefert `runtimeDir.resolve(".shinon-runtime-$SHINON_FORGE_PIN").exists()` —
dieser Marker wird **nirgends** erzeugt. Der Rückgabewert wird von
`onCreate()` nicht ausgewertet; `setup_done` wird trotzdem gesetzt.

**Auswirkung:** `ShinonService.startEngine()` findet `node` und
`node_modules/.bin/dsh` nie → immer `runtime_missing`. Gate 3 ist damit
strukturell unmöglich, nicht nur ungetestet.

**Nächster Schritt:** Bezugsartefakt definieren (siehe OPEN-002), dann
Download + SHA256-Prüfung implementieren und `setup_done` erst nach Erfolg setzen.

## B-2 — Das Profil `mobile` existiert nicht

**Beleg:** `ShinonService.startEngine()` startet mit `--profile mobile`.
Im Leseklon von `shinon-forge` (main `59a86a4`) enthält `profiles/` nur
`shinon` und `headless`. `--profile mobile` erscheint dort ausschließlich in
`docs/MOBILE-PLAN.md` als **Plan** (W1, „Startkandidat") und in
`docs/CI.md` als geplanter Gate `mobile-profile-boot`.

**Zusätzlich (im Zuge dieses Audits gefunden und behoben):** DSH löst Profile als
`$DSH_HOME/profiles/<name>` auf (dsh-README Zeile 11, `lib/bin.js:105`), und der
Forge-Einstieg setzt `DSH_HOME` explizit (`bin/shinon.mjs:107`).
`ShinonService.startEngine()` setzte es **nicht** — die App hätte also selbst mit
vorhandenem Profil im falschen Wurzelverzeichnis gesucht. Das ist korrigiert
(`ShinonService.kt:178`, siehe [`DECISIONS.md`](DECISIONS.md) DEC-010).

**Auswirkung:** Selbst mit installierter Runtime würde DSH das Profil nicht
auflösen; der READY-Handshake kann so nicht zustandekommen.

**Was jetzt belegt ist:** Der READY-Zeilen-Vertrag der App passt zur Wirklichkeit —
DSH druckt `dsh web: <url>` und ohne `--public-url` die Loopback-URL
(`dsh-web-app@0.2.1-alpha.1` `lib/index.js:211`, `README.md:56`). Die Regex
`dsh web: (http://\S+)` erfasst das. Der **Lauf** ist damit weiterhin nicht
belegt, nur das Format.

**Nächster Schritt:** Entscheidung OPEN-001 (Profil upstream bauen **oder** die
App auf ein vorhandenes Profil umstellen). Beides ist eine Architekturentscheidung,
keine stille Codeänderung.

## B-3 — Der API-Schlüssel erreicht den Prozess nicht

**Beleg:** `ShinonApp.ShinonKeystore` hat `ensureKey`, `hasKey`,
`getKeyAliasForProvider` — aber **keine** Methode, um den Schlüsselwert zu
speichern oder zu lesen. `SetupActivity` zeigt keinen Eingabedialog (nur
`Log.w`). In `ShinonService.startEngine()` enthält die `env`-Map den Schlüssel
nicht (Kommentar: „In v1: nur die Existenz").

**Auswirkung:** Kein authentifizierter Provider-Aufruf möglich → Gate 4 BLOCKED.

**Nächster Schritt:** `storeSecret()`/`readSecret()` (AES-GCM über den
Keystore-Schlüssel), Eingabedialog im Setup, Env-Injektion im Service.

## B-4 — Native Addons der Engine: Android/Bionic nicht geprüft

**Beleg (Registry, `npm view`):**

| Paket | Native Abhängigkeit |
|---|---|
| `@deepseek-ai/dsh-fs-local@0.2.1-alpha.1` | `koffi 3.1.1` (FFI, vorkompilierte Binaries) |
| `@deepseek-ai/dsh-subprocess-local@0.2.1-alpha.1` | `koffi 3.1.1`, `node-pty 1.2.0-beta.15` |
| `@deepseek-ai/dsh-attachment-local@0.2.1-alpha.1` | `sharp ^0.35.3` (libvips) |
| `@deepseek-ai/dsh@0.2.1-alpha.1` | `node-addon-require-builtin ^0.1.6` |

**Auswirkung:** Diese Module werden üblicherweise gegen glibc gebaut. Ob sie
unter Android/Bionic überhaupt ladbar sind, ist **nicht untersucht**. Ein
Node-Binary allein genügt nicht.

**Status:** `UNVERIFIED` / `BLOCKED` (`RT-BIONIC-001`). Ohne Gerät nicht
entscheidbar.

**Nächster Schritt:** kleinster Proof auf echter Hardware: `node` starten und
`require('koffi')` in einem Modul-Test ausführen; Ergebnis dokumentieren, statt
es anzunehmen.

## B-5 — Kein Node-Binary und keine Runtime-Bezugsquelle

**Beleg:** Es gibt im Repo kein Runtime-Artefakt, kein Bezugsskript, keine
SHA256-Liste. `.gitignore` schließt `app/src/main/assets/runtime/` bewusst aus.
`engines.node` der Engine verlangt `^22.19.0 || >=24.0.0`.

**Auswirkung:** Auch ohne B-1/B-2 fehlt das Material, das installiert werden soll.
Das ist die offene Architekturfrage OPEN-002 (proot-Rootfs, eigenständiges
Bionic-Binary oder Anlehnung an ein bestehendes Mobile-Projekt).

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
