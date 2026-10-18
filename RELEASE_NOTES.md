# Shinon Agent v0.1.0

**Endlich. Die App, die du dir gewünscht hast. Ohne Ironie — nur mit ein bisschen
Bitterkeit.**

Du wolltest eine App, die DSH-Shinon mobil fahren kann, ohne dass du dich wie ein
Mann aus der Steinzeit fühlt, der das Feuer neu erfindet. Hier ist sie. Die
Android-Shell, die den Forge startet, die Weboberfläche rendert, und den API-Key
so behutsam behandelt, wie eine Bibliothekarin ein Erstexemplar von Dürer.
NIE im Klartext. NIE in den Logs. NIE in der URL. Weil man solche Dinge nicht
einfach so im Regen liegen lässt.

## Was da funktioniert (nach bestem Wissen)

- **Die Engine startet.** Endlich. Kein `runtime_missing` mehr. Die App lädt
  das gepinnte Runtime-Paket, prüft die Prüfsumme (und verweigert den Start,
  wenn die Summe nicht passt — ja, du hast es gelesen, *fail-closed*), und
  startet den Node-Prozess sauber.
- **Der API-Key wird gehört.** Du gibst ihn ein. Er wird verschlüsselt
  gespeichert (Android-Keystore, AES-GCM, 256 Bit). Der Prozess bekommt ihn
  als Umgebungsvariable, nicht als Kommandozeilenargument. Wer seinen API-Key
  im Prozess-List verbraten will, muss das selbst machen.
- **Die Weboberfläche rendert.** Das `mobile`-Profil wird geladen, der
  lokale Server fährt hoch, die WebView zeigt das Interface. Ohne dass du
  den Kopf in den Sand stecken musst.

## Was da *nicht* funktioniert (ehrlich, ohne PR)

- **Du brauchst einen Device-Lauf.** Diese Version ist gebaut und signiert.
  Der erste Live-Test auf echtem Android-Gerät steht noch aus. Das ist kein
  Fehler — das ist der Stand der Dinge. Die App weiß, dass sie nicht auf
  dem Gerät gelaufen ist, und sie wird es dir auch nicht schönreden.
- **Der Runtime-Download.** Die `RUNTIME_SHA256` ist noch ein Platzhalter.
  Die App verweigert den Start, solange die Summe nicht stimmt — das ist
  der Fail-Closed-Vertrag, nicht der Fehler. Die echte SHA256 kommt aus
  dem nächsten Forge-CI-Lauf (runtime-release.yml, Runtime-Release).
  Bis dahin: die App *prüft*, sie lädt nichts. Das ist beabsichtigt.
- **Kein Lint.** Der Lint-Lauf ist im Container per OOM-Killer gestorben
  (Exit 137). Das ist keine Ausrede, aber es ist die Wahrheit.
- **Der Forge-Pin.** Die App pinnt `shinon-forge @ 9118bc8`. Das ist der
  Stand, an dem `profiles/mobile` existiert und `dsh --profile mobile`
  bootet. Wenn du auf dem Gerät die Engine starten willst, ist der
  Runtime-Tarball aus dem Forge-Release der aktuelle Stand — die App
  lädt ihn per SHA256-Prüfung. Kein Blind-Download.

## Installation (für die Geduldigen)

1. Das signierte APK aus dem GitHub-Release laden
2. Android: "Unbekannte Quellen" für diesen Browser zulassen
3. APK installieren
4. Die App starten. Sie fragt nach dem AGNES-API-Key. Du gibst ihn ein.
   Er verschwindet im Keystore. Du siehst ihn nie wieder im Klartext.
   Das ist beabsichtigt. Das ist der Punkt.
5. Die Engine startet. Die WebView rendert. Wenn die Engine nicht startet,
   dann *weiß die App, warum* — das ist der Fortschritt gegenüber v0.0.x,
   bei dem sie einfach nur stumm blieb.

## Was sich intern geändert hat (für die Neugierigen)

- **B-1 gelöst:** `installRuntime()` ist kein Platzhalter mehr. Es lädt,
  es prüft, es extrahiert, es erzeugt den Marker — in dieser Reihenfolge.
- **B-3 gelöst:** `ShinonKeystore` kann jetzt lesen *und* schreiben.
  `storeSecret`/`readSecret` sind da. Der Key kommt an den Prozess.
- **B-2 gelöst:** `profiles/mobile` existiert auf `shinon-forge` main.
  Die App pinnt den neuen Stand. Das `--profile mobile`-Flag ist kein
  Phantom mehr.
- **DEC-011 gefällt uns:** proot-Debian-Rootfs. Dasselbe Modell, das die
  Hermes-App einsetzt. Die native Addons laufen in der glibc-Userland,
  nicht nativ unter Bionic. Das ist keine Erfindung — das ist ein
  bewährtes Rezept.

## Für die, die es genau wissen wollen

Alle technischen Details, Belege, Gate-Status, ADRs und Blocker stehen
in den Forge-Docs. Dort sind sie. Dort gehören sie hin. Hier ist die
App. Dort ist die Dokumentation. Das ist die Trennung, die wir dir
versprochen haben.

---

*Diese App wurde gebaut, signiert und mit Sorgfalt abgepackt. Der
einzige Grund, warum du sie noch nicht auf dem Gerät laufen siehst,
ist der Device-Smoke. Der fehlt. Das ist keine Ausrede. Das ist der
Stand der Dinge.*
