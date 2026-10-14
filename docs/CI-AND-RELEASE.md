# CI und Release — Shinon Agent

> Stand: 2026-10-14 · Workflow: `.github/workflows/build.yml`

## 1. Workflow-Struktur

Ein Job `android-build` auf `ubuntu-latest` (`timeout-minutes: 45`), ausgelöst
durch Push auf `main` und `workflow_dispatch` (optional mit `tag`).

| # | Schritt | Fail-closed? |
|---|---|---|
| 1 | Checkout | — |
| 2 | JDK 17 (temurin) | — |
| 3 | Gradle 8.7 über `gradle/actions/setup-gradle` | — |
| 4 | Keystore aus `SHINON_KEYSTORE_B64` dekodieren | **ja** — fehlt das Secret, `exit 1` vor jedem Build |
| 5 | Signing-Env prüfen (`PASS`/`ALIAS`) | **ja** — `exit 1` bei Lücke |
| 6 | `gradle assembleRelease` | — |
| 7 | APK-Inhaltsgate (Entkopplung) | **ja** — Treffer → `exit 1` |
| 8 | APK als Artefakt `shinon-agent-v0.0.1.apk` | `if-no-files-found: error` |
| 9 | `gh release create` (nur `workflow_dispatch` mit Tag) | — |
| 10 | Keystore löschen | `if: always()` |

## 2. Signing-Vertrag

`app/build.gradle.kts` liest die Signatur aus der Umgebung:

| Feld | Quelle |
|---|---|
| `storeFile` | `SHINON_KEYSTORE_PATH` (in CI dekodiert), Fallback `keystore/release.jks` |
| `storePassword` | `SHINON_KEYSTORE_PASS` bzw. `SHINON_KEYSTORE_PASS_DEFAULT` |
| `keyAlias` | `SHINON_KEYSTORE_ALIAS` |
| `keyPassword` | `SHINON_KEY_ALIAS_PASS`, Fallback = `storePassword` |

Benötigte Repository-Secrets: `SHINON_KEYSTORE_B64`, `SHINON_KEYSTORE_ALIAS`,
`SHINON_KEYSTORE_PASS`, `SHINON_KEY_ALIAS_PASS`.
Der Keystore (`.jks`) liegt **nie** im Repo (`.gitignore`: `*.jks`, `keystore/`).

**Belegtes Verhalten (lokal nachgestellt):**
`:app:validateSigningRelease` schlägt ohne Keystore mit
`Keystore file '…/app/keystore/release.jks' not found for signing config 'release'`
fehl (Exit 1). Es entsteht dabei **kein** Artefakt.

## 3. APK-Inhaltsgate (Entkopplung)

```bash
unzip -l "$APK" | grep -Ei 'node_modules|shinon-forge|/dsh|profile[s]?/mobile'
```

Ein einziger Treffer macht den Lauf rot. Sinn: App, Engine und Vendor sind
getrennte Schichten ([`ARCHITECTURE.md`](ARCHITECTURE.md) §1); Runtime-Daten,
`node_modules` und Forge-Profile gehören in das Runtime-Paket, nicht in die APK.

**Verifiziert:** Die Gate-Logik wurde am erzeugten Debug-APK
(`b83615ae…cd6f`, 889 Einträge, keine `.so`) nachgefahren — kein Treffer.

**Einschränkung:** Im Workflow greift das Gate nur auf dem **Release**-Artefakt.
Ein Debug-Build wird von der CI derzeit **nicht** erzeugt (`CI-DEBUG-001` ist
`PLANNED`).

## 4. Bekannte CI-Schwächen

1. **Der Workflow nutzt `./gradlew` nicht**, sondern `gradle assembleRelease` mit
   `gradle/actions/setup-gradle`. Genau deshalb blieb der Defekt im
   handgeschriebenen `gradlew` unbemerkt — lokal war kein Build möglich, in der
   CI fiel es nicht auf. Behoben in [`DECISIONS.md`](DECISIONS.md) DEC-001;
   ein CI-Schritt, der `./gradlew` prüft, fehlt weiterhin.
2. **Keine Unit-Test- und keine Lint-Stufe** im Workflow (`CI-DEBUG-001`, Gate 1b).
3. **Kein Podest für Gate 3/4:** es gibt keinen `android-device-smoke`-Job. Der
   frühere `develop`-Trigger ist entfernt — den Branch gibt es im Remote nicht
   (siehe [`KNOWN-LIMITATIONS.md`](KNOWN-LIMITATIONS.md) N-4).
4. **Alle beobachteten Läufe waren rot** (GitHub-Actions-Oberfläche: 24 Läufe,
   letzter `build` #10 am 2026-10-14). Diese Beobachtung ist nicht in dieser
   Umgebung nachgemessen; ein grüner Lauf ist damit **nicht** belegt.

## 5. Release-Gates (verbindlich)

Ein Release ist erst zulässig, wenn:

1. Gate 1 grün ist (`:app:assembleDebug` baut);
2. Gate 2 grün ist (APK existiert, Inhaltsgate leer, SHA256 dokumentiert);
3. Gate 3 auf einem echten Gerät grün ist (Runtime startet, READY-URL erscheint);
4. Gate 4 grün ist (echter Provider-Aufruf, Erfolg **und** Auth-Fehler getrennt);
5. die Signing-Secrets gesetzt sind (sonst fail-closed, kein ungesigniertes APK);
6. die Prüfsumme des Artefakts veröffentlicht ist.

**Belegt:** Release-Kompilierung und R8 laufen durch (`:app:minifyReleaseWithR8`
→ `BUILD SUCCESSFUL in 2m 5s`), und ohne Signing-Secrets bricht der Lauf ab.
**Nicht belegt:** ein signiertes Release-APK.

**Heute ist Punkt 3 und 4 BLOCKED** und Punkt 5 nicht durchgeführt — also ist
**kein Release freigegeben**.
