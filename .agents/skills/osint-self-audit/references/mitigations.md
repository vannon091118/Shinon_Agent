# Mitigations — De-Risiko-Checkliste (priorisiert nach Hebel/Aufwand)

> Alle Maßnahmen sind **User-Aktionen**. Der Agent kann anleiten, aber nicht eigenmächtig ausführen (kein Force-Push, keine Profiländerungen ohne Freigabe).

## 🔴 1. Git-Commit-Historie bereinigen (größter Hebel)

Situation: Klarname + Email liegen ungeschützt in öffentlicher Commit-Historie.

```bash
# ACHTUNG: Umschreibt History — erst vollständiges Backup/Clone, dann auf frischem Clone arbeiten!
git clone --mirror <repo-url> repo.git && cd repo.git
# filter-repo verweigert auf nicht-frischen Clones den Start → ggf. --force anfügen
# (--mailmap mit Prozess-Substitution <(...) erfordert bash/zsh — nicht sh!)

# filter-repo installieren (falls fehlt): pip install git-filter-repo  (einmalig, lokal)

# 1) Email im Author/Committer ersetzen (alle Repos einzeln)
git filter-repo --mailmap <(echo "Felix Schneider <schneider.felix1993@gmail.com> == Vannon <vannon0911@users.noreply.github.com>")
# oder pauschal:
git filter-repo --email-callback 'return email.replace("schneider.felix1993@gmail.com", "vannon0911@users.noreply.github.com").replace("casinoausnutzt@gmail.com", "vannon0911@users.noreply.github.com")'
```

Danach:
- `user.name` / `user.email` in `~/.gitconfig` oder pro Repo auf anonymisierte Adresse setzen:
  `git config user.email "vannon0911@users.noreply.github.com"` (GitHub-Noreply-Format: `<id>+<handle>@users.noreply.github.com`)
- Neuen History **Force-Push**: `git push --force --all origin` (+ `--tags`)
- **Risiken:** Forks/Clones behalten alte History; GitHub-Caches (Commit-Ansicht) können altes Material noch tage-/wochenlang zeigen; veröffentlichte Commit-SHAs ändern sich; verlinkte Issues/PRs können brechen. Abwägen: bei sehr jungem Repo (wenige Wochen) ist Umschreiben schmerzfrei.
- **Kontrollieren:** `git log --format='%an|%ae' | sort -u` vor/nach.

## 🔴 2. Klarname-Email aus allen Konten lösen

- GitHub → Settings → Emails: `schneider.felix1993@gmail.com` abwählen als Commit-Adresse; „Keep my email addresses private" aktivieren.
- SSH-Key neu erzeugen ohne Klarname-Kommentar: `ssh-keygen -t ed25519 -C "vannon0911@users.noreply.github.com"` → alten Key aus GitHub/Servern entfernen.

## 🟡 3. Steam-Profil privatisieren

Steam → Profil → Privatsphäre-Einstellungen: „Mein Profil", „Spieleliste", „Freundesliste", „**Spielstatus (aktuell spielt)**", „Inventar" auf „Nur ich"/„Freunde". Danach sieht ein Fremder weder Live-Aktivität noch Freundesnetzwerk.

## 🟡 4. Soziale Profile entschärfen

- TikTok: Ort (Herten) aus Bio entfernen
- Twitch/YouTube: Bio ohne Finanz-/Tagesablauf-Details („Streams ab 7 Uhr" entfernen)
- Reddit-Bio „Gamer Xbox Ps5" neutralisieren; alte Posts mit persönlichen Details (r/gameswap!) löschen oder Konto archivieren

## 🟡 5. Öffentliche Kontakt-Email ersetzen

`vannon858@gmail.com` in Repo-Readmes/CODEOWNERS durch Alias ersetzen (z.B. Proton/SimpleLogin-Alias), alte Adresse aus Git-Historie via filter-repo.

## 🟢 6. Datenleck-Frühwarnung (User macht es selbst)

- HaveIBeenPwned (`haveibeenpwned.com`) für alle 4 Emails
- Firefox Monitor / Google Alerts auf `vannon0911`, `vannon858`, `felixappleusa`
- 2FA überall aktivieren (mindestens Steam + GitHub + Gmail)

## 🟢 7. Lokale Hygiene

- `~/.env`-Dateien: `chmod 600` (vorher oft 664 = gruppenlesbar)
- `GITHUB_TOKEN` + API-Keys rotieren, wenn sie je in Repo-Readme/Commits auftauchten (Leak-Scan: `grep -r` nach Token-Präfixen in allen Repos)
- machine-id/Netz-Fingerprint: nicht änderbar ohne root — theoretisch
