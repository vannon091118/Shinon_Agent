# S0-Bestandsaufnahme — Shinon Forge × Shinon Agent

> ## ⚠️ ARCHIVIERT — historisches Dokument, nicht Projektstand
>
> Diese Bestandsaufnahme ist **überholt** und bleibt nur zur Nachvollziehbarkeit
> erhalten (nichts wurde gelöscht). Sie beschreibt F-1 bis F-3 als offen —
> diese Fehler sind im Code inzwischen behoben und durch einen Build bestätigt.
>
> - Gültige Fassungen: [`../SCOPE.md`](../SCOPE.md),
>   [`../KNOWN-LIMITATIONS.md`](../KNOWN-LIMITATIONS.md),
>   [`../TESTING.md`](../TESTING.md).
> - Der hier genannte Branch `shinon-forge/develop` **existiert nicht**, der
>   Commit `d7d38ce` **ebenfalls nicht** (geprüft per `git ls-remote`; GitHub
>   liefert 404). Der Pin war eine Annahme, kein Beleg.
> - `MOBILE-PLAN.md` liegt **nicht** in diesem Repo, sondern in
>   `shinon-forge/docs/MOBILE-PLAN.md` — alle Verweise darauf sind extern.
> - Die Aussage „Forge-Gate `gate:full` läuft grün“ bezieht sich auf einen
>   Commit, der nicht mehr belegbar ist.
>
> Zeitdokument · Stand: 2026-10-14 · ursprünglich zu `b87fb1d`

> Ursprünglicher Kopf: Branches `shinon-forge/develop`, `Shinon_Agent/main` ·
> Prüfer: S0 (Bestand und Risiken) · Keine Implementierung in diesem Slice

---

## A. Befunde mit Abhängigkeiten

Jeder Befund hat: **Status** (Fehler/Risiko/Annahme), **Betroffene Dateien**, **Beleg**, **Auswirkung**, **Nächster Slice**, **Blocker?**

---

### F-1 | Fehler — Build bricht wegen fehlendem Gradle-Property
| Feld | Wert |
|---|---|
| Status | **Fehler** (fail-closed, CI rot seit 2026-10-14) |
| Datei | `gradle.properties` (Zeilen 1–7, leer außer Kommentare) |
| Beleg | CI-Run 38509246399: `Configuration ':app:releaseRuntimeClasspath' contains AndroidX dependencies, but the android.useAndroidX property is not enabled` |
| Auswirkung | Release-Build untauglich. Debug-Build ebenfalls kaputt (AGP 8 zwingt AndroidX). Kein getestetes APK. |
| Nächster Slice | **S1** (Build-Fix, klein) |
| Blocker für v0.0.1 | **Ja** — ohne grünen Build kein Release-APK. |

### F-2 | Fehler — `SetupActivity` kompiliert nicht (fehlender Import)
| Feld | Wert |
|---|---|
| Status | **Fehler** (static analysis, compile-fail) |
| Datei | `app/src/main/java/com/vannon/shinon/SetupActivity.kt:26` |
| Beleg | `class SetupActivity : Activity()` — `import android.app.Activity` fehlt im Import-Block (Zeilen 1–15). Die anderen 3 Dateien importieren `Activity` explizit. |
| Auswirkung | Kotlin-Compiler wirft `Unresolved reference: Activity`. Build bricht vor jeder APK-Generierung. |
| Nächster Slice | **S1** |
| Blocker für v0.0.1 | **Ja** |

### F-3 | Fehler — Manifest deklariert `FOREGROUND_SERVICE_DATA_SYNC`, Permission fehlt
| Feld | Wert |
|---|---|
| Status | **Fehler** (API 28–33 Crashes) |
| Datei | `AndroidManifest.xml:35` (`foregroundServiceType="dataSync"`) |
| Beleg | `FOREGROUND_SERVICE_DATA_SYNC`-Permission ist in AndroidManifest **nicht** deklariert (nur `INTERNET`, `WAKE_LOCK`, `FOREGROUND_SERVICE`, `POST_NOTIFICATIONS`). AGP 8 + targetSdk 34 + `foregroundServiceType="dataSync"` → `InvalidServiceTypeException` auf API 28–33. |
| Auswirkung | App-crash beim Service-Start auf allen Geräten vor Android 14. Nur auf API 34+ funktioniert es (weil die Permission zur Laufzeit angefordert wird, aber sie steht nicht im Manifest). |
| Nächster Slice | **S1** (manifest-Korrektur) |
| Blocker für v0.0.1 | **Ja** (außer auf API 34-Only-Geräten) |

### F-4 | Fehler — `ShinonService.startEngine()` startet niemals mit einem funktionalen Runtime-Paket
| Feld | Wert |
|---|---|
| Status | **Fehler** (logischer Dead-Code-Pfad, nicht nur Build) |
| Datei | `SetupActivity.kt:88–95`, `ShinonService.kt:127–132` |
| Beleg | `SetupActivity.installRuntime()` ist ein Platzhalter: erstellt `filesDir/runtime/` und setzt einen Marker `.shinon-runtime-<PIN>`, der **niemals gesetzt wird**. Daraus folgt: `node` und `node_modules/.bin/dsh` existieren nicht. `ShinonService.startEngine()` gibt sofort `runtime_missing` zurück. Die App startet nie einen DSH-Prozess. |
| Auswirkung | **W4-Abnahme ist nicht erfüllbar.** Die W4-Definition erfordert „eine kompatible Shinon-Runtime startet". Hier wird keine gestartet. |
| Nächster Slice | **S2** (Runtime-Installer) |
| Blocker für v0.0.1 | **Ja** — Blocker aller folgenden Slices (S3–S6), da diese auf einem laufenden DSH aufsetzen. |

### F-5 | Fehler — `ShinonKeystore` speichert keinen API-Key
| Feld | Wert |
|---|---|
| Status | **Fehler** (funktionaler Mangel, Security-Lücke) |
| Datei | `ShinonApp.kt:55–79` |
| Beleg | `ensureKey()` erzeugt nur den AES-256-GCM-Schlüssel. Es gibt **keine** `storeSecret()`- oder `encrypt()`-Methode. `hasKey()` prüft nur Existenz. Der API-Key-Wert kommt nirgends im Keystore an. |
| Auswirkung | Der AGNES_API_KEY wird nie im Keystore gespeichert → der Node-Prozess erhält kein Environment → DSH kann keine Provider aufrufen. Mobile-Profil läuft tot. |
| Nächster Slice | **S2** (Setup-Flow erweitern) |
| Blocker für v0.0.1 | **Ja** (wenn mobile-Dashboard mit echtem Provider arbeiten soll) |

### R-1 | Risiko — `shouldOverrideUrlLoading` lässt `https://127.0.0.1` durch
| Feld | Wert |
|---|---|
| Status | **Statisches Risiko** (Security-Contract-Verstoß) |
| Datei | `MainActivity.kt:123` |
| Beleg | Der Filter erlaubt `scheme == "https" && host == "127.0.0.1"` — das gibt privilegierten WebView-Zugriff (JS, DOM, localStorage) an eine fremde HTTPS-Seite auf Loopback. Die Mobilerlaubnis erlaubt nur `http://127.0.0.1`. |
| Auswirkung | Theoretisch: XSS-Exploit über ein MITM-befähigtes Zertifikat auf demselben Gerät. Praktisch bei einem lokalen DSH kaum relevant, aber der Security-Vertrag (README §5 W4) wird formal verletzt. |
| Nächster Slice | **S1** (einfacher Fix, 1 Zeile) |
| Blocker für v0.0.1 | Nein (Kosmetik, aber sollte vor Release behoben werden) |

### R-2 | Risiko — `maskSecrets` maskiert nicht alle Secrets-Muster im DSH-stdout
| Feld | Wert |
|---|---|
| Status | **Statisches Risiko** (Log-Leck) |
| Datei | `ShinonService.kt:222–225` |
| Beleg | Drei Regex-Muster (`token=`, `apikey=`, `AGNES_API_KEY`). DSH kann weitere Tokens ausgeben (Bearer-Token, Session-ID, Request-ID). |
| Auswirkung | Logs enthalten potenziell authentifizierende Tokens. Security-Vertrag (§5 W4: „App-Logs enthalten keine Schlüssel und keine tokenisierte URL") wird nicht vollständig erfüllt. |
| Nächster Slice | **S2** (Maskierungs-Update) |
| Blocker für v0.0.1 | Nein |

### R-3 | Risiko — Receiver-Registration auf API 34 ohne Flag
| Feld | Wert |
|---|---|
| Status | **Statisches Risiko** (API-34-Crash) |
| Datei | `MainActivity.kt:89–90` |
| Beleg | `registerReceiver(urlReadyReceiver, IntentFilter(...))` ohne `Context.RECEIVER_NOT_EXPORTED`-Flag. Ab API 34 crasht das mit `IllegalArgumentException`. |
| Auswirkung | Auf Android 14+ Geräten startet die MainActivity nicht. Nur auf API < 34 funktioniert es. |
| Nächster Slice | **S1** (einfacher Flag-Add) |
| Blocker für v0.0.1 | Ja (auf API 34+ Geräten, die 2026 Mainstream sind) |

### A-1 | Unbewiesene Annahme — DSH-native-Addons laufen auf Bionic
| Feld | Wert |
|---|---|
| Status | **Unbewiesen** (technisches Risiko) |
| Datei | `MOBILE-PLAN.md:30–31`, `docs/EXTENSIONS-PLAN.md` |
| Beleg | `@deepseek-ai/dsh-attachment-local` zieht `sharp`, `dsh-fs-local` zieht `koffi 3.1.1`, `dsh-subprocess-local` zieht `koffi 3.1.1 + node-pty`. Alle drei sind native Addons, die glibc brauchen. Das Root-Manifest verlangt Node `^22.19.0`. |
| Vergleich mit Referenzen | `dsh-io/dsh-mobile` (Stand 2026-10-14): Pin `dsh-arm64-0.1.0-rc.6`, Node v22.16.0, proot Debian-Rootfs (glibc im chroot). `nakiostudio/nodejs-mobile`: letzte Version 18.20.4 (Node < 22). `termux/proot-distro`: Symlink-/Execute-Probleme dokumentiert. |
| Auswirkung | Der Plan „Runtime in `filesDir/runtime/` installieren" ist theoretisch gültig, aber die konkrete Strategie (welches Binary, welche Userland, wie proot?) ist noch nicht gewählt. Ohne W0-Proof kann kein Release-APK garantieren, dass DSH tatsächlich startet. |
| Nächster Slice | **S1.5** (W0-Proof als separates Gate) |
| Blocker für v0.0.1 | **Ja** (MOBILE-PLAN.md §5 W0: „keine Annahme wird als Erfolg verkauft") |

### A-2 | Unbewiesene Annahme — dsh-mobile kann als Referenz für Shinon dienen
| Feld | Wert |
|---|---|
| Status | **Unbewiesen** (Integration-Unklarheit) |
| Datei | `MOBILE-PLAN.md:53`, `README.md:§5.2` |
| Beleg | `dsh-io/dsh-mobile` ist ein eigenständiges Projekt mit eigenem Rust-JNI-Stack, eigenem Rootfs-Builder und eigenem `dsh-arm64`-Paket. Es **lädt kein** `shinon-forge`-Profil und unterstützt kein `--profile`-Override. Die Einbindung von Shinon-spezifischem Code (`@shinon/mobile`, Mobile-Allowlist, cordis.patch.yml) ist nicht dokumentiert. |
| Auswirkung | Der W4-Plan verweist auf dsh-mobile als Referenz, aber der Integrationspfad (wie wird Shinon-forge in die Shell geladen?) ist offen. Zwei Optionen: (a) Eigenständiger Kotlin-Bau mit selbst-gebaute proot-Strategie (wie dsh-mobile), oder (b) Adaptierung des dsh-mobile-Quellcodes (Lizenzprüfung nötig). |
| Nächster Slice | **S1.5** (Architektur-Entscheidung: eigenständiger Bau vs. Integration von dsh-mobile) |
| Blocker für v0.0.1 | Ja (die Technologie-Entscheidung muss vor S2 fallen) |

### A-3 | Unbewiesene Annahme — Proot-Rootfs-Pinning ist deterministisch reproduzierbar
| Feld | Wert |
|---|---|
| Status | **Unbewiesen** (CI-/Release-Reproduzierbarkeit) |
| Datei | `README.md:§3.1`, `docs/EXTENSIONS-PLAN.md:§4` |
| Beleg | Der Plan beschreibt „SHA256-Prüfung + validierte Version + Rollback". Kein konkretes Build-Script für das proot-Rootfs existiert im Repo. dsh-mobile baut das Rootfs im CI mit debootstrap und lädt ein fixiertes Node v22.16.0-Deb Paket. Was passiert, wenn die Node.js-Version von v22.16.0 auf v22.19.0 (Root-Manifest-Pin) wechselt? |
| Auswirkung | Ein Release-APK kann nicht reproduzierbar gebaut werden, wenn das Runtime-Paket nicht deterministisch ist. |
| Nächster Slice | **S1.5** (Runtime-Pinning + CI-Rootfs-Build) |
| Blocker für v0.0.1 | Ja (Release-Flow erfordert reproduzierbare Runtime) |

---

## B. Blocker-Matrix (was muss vor einem Release-APK gelöst sein)

| Blocker | Slice | Warum blockierend |
|---|---|---|
| F-1: `gradle.properties`-Fix | **S1** | Build bricht sofort. Kein APK ohne Build. |
| F-2: SetupActivity-Import | **S1** | Build bricht sofort. |
| F-3: Manifest-DataSync-Permission | **S1** | Service-Crash auf API 28–33. |
| F-4: Runtime-Installer (echter Download) | **S2** | W4-Abnahme: „Engine startet nicht". |
| F-5: Keystore storeSecret() | **S2** | Provider kann keine Aufrufe machen. |
| R-3: Receiver-Flag API 34 | **S1** | App-Start-Crash auf Android 14+. |
| A-1: Native-Addon-Proof (Bionic) | **S1.5** | MOBILE-PLAN §5 W0: „keine Annahme als Erfolg". |
| A-2: Architektur-Entscheidung (eigen vs. dsh-mobile) | **S1.5** | Unklar, ob die App überhaupt eine proot-Strategie braucht. |
| A-3: Runtime-Pinning (deterministisch) | **S1.5** | Release-Flow kann nicht reproduzierbar sein. |

---

## C. Offene Fragen (müssen vor S1 beantwortet werden)

| # | Frage | Warum kritisch |
|---|---|---|
| Q-1 | Sollen wir einen **eigenständigen Kotlin-Bau** machen (proot + Rootfs im App-Storage, wie dsh-mobile) oder die **dsh-mobile-App adaptieren** und Shinon-Erweiterungen einhängen? | Bestimmt den gesamten Umfang von S2–S6. Eigenständiger Bau = 3–4 Wochen; Adaptierung = Lizenzprüfung + weniger eigene Codebasis. |
| Q-2 | Welche **Node.js-Version** verwenden wir für das Runtime-Paket? Root-Manifest verlangt `^22.19.0 || >=24.0.0`. dsh-mobile pinnt `v22.16.0`. Sind die Unterschiede für DSH relevant? | Bestimmt die proot-Rootfs-Konfiguration. |
| Q-3 | Wird `--profile mobile` von DSH auch außerhalb eines Shinon-forge-Repos funktionieren (also wenn die App das Runtime-Paket als isoliertes Archiv extrahiert)? | Wenn nein, müssen wir die Repo-Struktur (`.dsh/`, `profiles/`) im Runtime-Archiv konservieren. |
| Q-4 | Soll das Release-APK (`v0.0.1`) einen **Live-Provider-Test** auf einem echten Gerät durchführen (AGNES_API_KEY eingeben, einen Chat senden), oder reicht der CLI-Start (EXIT-Code 0 + READY-URL)? | Wenn Live-Test: müssen wir F-5 (Keystore storeSecret) und einen Setup-Dialog implementieren, bevor wir ein Release bauen. |
| Q-5 | Was ist mit dem bestehenden Release-Keystore (`keystore/release.jks`, alias `shinon`, lokal auf dem Arbeitsrechner)? Soll er beibehalten oder neu generiert werden? | Bestimmt, ob der vorhandene `SHINON_KEYSTORE_B64`-Secret wieder taugt. |

---

## D. Empfohlene Slice-Reihenfolge

```
S0 (dieser Slice)
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│ S1.5 — Strategie-Entscheidung (Q-1 bis Q-4 beantworten)  │
│        Blocker A-1, A-2, A-3                            │
│        Output: ADR (Architecture Decision Record)       │
│        + W0-Proof-Plan                                   │
└──────────────────────────────────────────────────────────┘
    │
    ▼ (alle Blocker gelöst)
┌──────────────────────────────────────────────────────────┐
│ S1 — Build-Fix + Safety-First                           │
│        F-1, F-2, F-3, R-1, R-3 fixen                    │
│        Blocker für: Build wird grün                      │
└──────────────────────────────────────────────────────────┘
    │
    ▼ (Build grün)
┌──────────────────────────────────────────────────────────┐
│ S2 — Runtime-Installer + Setup-Flow                     │
│        F-4, F-5 beheben                                  │
│        Runtime-Paket (Node + shinon-forge + node_modules │
│        als gepinntes Archive) installieren + SHA256-Check │
│        + API-Key-Dialog (Keystore storeSecret)           │
└──────────────────────────────────────────────────────────┘
    │
    ▼ (Installer läuft)
┌──────────────────────────────────────────────────────────┐
│ S3 — W0-Proof auf echtem ARM64-Gerät                    │
│        DSH startet, READY-URL kommt, Provider-Aufruf    │
│        mobiler Smoke (keine Regression)                 │
└──────────────────────────────────────────────────────────┘
    │
    ▼ (W0 proof grün)
┌──────────────────────────────────────────────────────────┐
│ S4 — Release-Flow (v0.0.1-APK)                          │
│        CI: Rootfs-Build (falls proot) + APK-Build       │
│        Release-Tag + GitHub-Release                     │
│        + Third-Party-Notices                              │
└──────────────────────────────────────────────────────────┘
```

**Warum S1.5 vor S1:** Weil S1 einen funktionierenden Build macht, aber ohne Strategie-Entscheidung bauen wir eine App, die am W0-Proof scheitert (weil die Runtime-Strategie falsch ist). S1.5 kostet einen Commit (ADR-Datei + Entscheidungs-Doku), kann aber die gesamte weitere Arbeit verhindern.

**Warum S2 vor S3:** S3 ist ein Proof-of-Concept auf einem echten Gerät. S2 liefert das Runtime-Paket, das der Proof benötigt. Ohne S2 ist S3 nur ein manueller Test (keine CI-Integration).

**Warum S3 vor S4:** Release-Flow (S4) ist nur dann value, wenn vorher ein W0-Proof zeigt, dass DSH auf Android tatsächlich startet. Sonst ist das Release ein blindes APK.

---

## E. Aktueller CI-Stand (zum Vergleich)

| Repo | Letzter CI-Lauf | Status | Letzter Fehler |
|---|---|---|---|
| `shinon-forge` | `d7d38ce` → Gate `gate:full` | ✅ PASS (22/22) | — |
| `Shinon_Agent` | `b87fb1d` (Push) → Run 38509246399 | ❌ FAILURE | `android.useAndroidX=true` fehlt |

Forge-Gate `gate:full` läuft grün (W1 + W2 bereits gebaut). Agent-CI bleibt rot, bis F-1 behoben ist.

---

*Handshake abgeschlossen. Warte auf Freigabe für S1.5 (Strategie-Entscheidung).*
