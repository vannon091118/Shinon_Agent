# Case-File: vannon0911 — verifiziertes OSINT-Dossier v2

> Stand: 11.08.2026 · Alle Kernaussagen mit Evidenzgrad (✅ direkt verifiziert · ⚠️ nur Suchtreffer · ❌ widerlegt).
> **Vertraulich** — enthält personenbezogene Daten des Skill-Besitzers. Nicht teilen/publizieren.

---

## 1. Steckbrief

```
Handle-Kern:  vannon0911      (überall wiederverwendet)
Alias:        Vannon · vannon091118 (GitHub-Account #2) · casinoausnutzt-prog (GitHub-Account #3)
Plattformen:  8 Konten auf 7 Diensten
Klarname:     Felix Schneider              🔴 ÖFFENTLICH via Git-Commit-Historie
Geburt:       ~1993                        ✅ konsistent mit Selbstangabe „32yo" (2025)
Wohnort:      Herten, Nordrhein-Westfalen  ✅ Steam + TikTok
Alter:        32 (Stand 2025)              ✅ Reddit-Thread-Titel
Telefon:      nicht gefunden
Adresse:      nur Stadt, keine Straße
Leaks:        keine Pastebin-/Breach-Hits (Stand 08/2026)
```

## 2. Plattform-Matrix (8 Konten)

| Plattform | Handle | Stats | Fremde Sicht | Evidenz |
|---|---|---|---|---|
| Steam | `Vannon0911` | Lvl 14, 49 Spiele, 600 Achv., 68 Freunde, SteamID 76561198069919600 | Live „In-Game", NRW, Online-Status, Freundesliste | ✅ Profil geladen |
| GitHub | `Vannon0911` + `vannon091118` | Dev Program Member | LifeGameLab, SeedWorld, SyxBridge, SyxEconomyMod, Rimconemy, karma, DOKI, LLM_Core_V1 | ✅ Profil/Repos geladen |
| GitHub #3 | `casinoausnutzt-prog` (ID 271493451) | — | Committet in LifeGameLab | ✅ Commit-API |
| Twitch | `vannon0911` | seit 2012, VODs | „GGPoker NL2 \| Bankroll-Aufbau", Streams ab ~7 Uhr | ✅ Kanal geladen |
| YouTube | `@Vannon0911` (UC--SmLDcendXX3HQ6c7WeFQ) | ~126 Subs, ~110 Videos | Poker-Grind, VALORANT, EA FC, Helldivers 2; „Kein Fake-Graph" | ✅ Kanal geladen |
| TikTok | `@vannon0911` | 3.972 Followers, 30,4K Likes | **Herten**, „Twitch since 2012", Spiele-Katalog | ⚠️ Researcher |
| Reddit | `u/vannon0911` | Konto seit 23.08.2019, 1,6K Karma | Bio „Gamer Xbox Ps5"; r/songsofsyx, r/IndieDev, r/gameswap, r/KeineDummenFragen | ✅ old.reddit geladen |
| PSN | `Vannon0911` | — | Delta-Force-Squad-Posts („32yo") | ⚠️ Researcher / ✅ Thread |

## 3. Emails (4 gefunden)

| Email | Fundort | Für Fremde sichtbar? |
|---|---|---|
| `schneider.felix1993@gmail.com` | **GitHub-Commits** (Author „Felix Schneider") + SSH-Key `id_ed25519.pub` + zsh-History + Evolution | 🔴 **Ja — öffentlich in Commit-Historie** |
| `vannon858@gmail.com` | Repo-README (Kontakt/Bugreport) | 🔴 Ja — öffentlich |
| `casinoausnutzt@gmail.com` | GitHub-Commits (Account casinoausnutzt-prog) | 🔴 Ja — öffentlich |
| `felixappleusa@gmail.com` | Freebuff-DB `~/.freebuff/desktop-v2.db` (lokal) | 🟢 Nur lokal (online 0 Treffer) |

## 4. Die kritische Fund-Kette (Commit-Historie)

```
GitHub-API vannon091118/Syx_Bridge-Auto-Translate-Mods/commits:
  Author: "Felix Schneider" <schneider.felix1993@gmail.com>   ← 06.07.2026
GitHub-API Vannon0911/LifeGameLab/commits:
  Author: "casinoausnutzt-prog" <casinoausnutzt@gmail.com>    ← 01.04.2026
  Author: "Vannon" <vannon0911@users.noreply.github.com>       ← gut (anonymisiert)

→ Identitätskette ist OHNE Leak geschlossen:
  Felix Schneider ← schneider.felix1993@gmail.com ← Git-Commits
  ← vannon091118 ← vannon0911 ← Steam/Twitch/Reddit/YouTube/TikTok/PSN
```

## 5. Verknüpfungskette (wie ein Fremder sie baut)

```
vannon858@gmail.com (öffentlich im Repo)
      │
      ▼
vannon0911 ──┬── Steam  ──→ NRW · Project Zomboid · Live-Status · Freunde
             ├── Reddit ──→ 32yo · r/gameswap (Spieletausch = Adressen in DMs)
             ├── GitHub ──→ 3 Accounts · Commit-Emails mit Klarnamen
             ├── Twitch ──→ Bankroll-Aufbau · Streams ab ~7 Uhr
             ├── YouTube ─→ Poker-Grind · 110 Videos
             ├── TikTok ──→ Herten · „Twitch since 2012"
             └── PSN ─────→ PS5 + Xbox (Reddit-Bio)
```

## 6. Timeline

```
2012  Twitch-Konto (TikTok-Bio „Twitch Since 2012")
2018  Streaming-Ära: PRISMLiveStudio, VALORANT, EA FC, CoD
2019  Reddit-Konto (23.08.2019) · PSN aktiv
2021  Monster Hunter World · r/de
2024  r/gameswap (FF7 Rebirth, FF16, Dragon's Dogma)
2025  Poker-Pivot: NL2-Streams + YouTube-Kanal · „32yo"-Post
2026  In Project Zomboid (Steam) · SyxBridge v0.26 · Klarname in Commits
```

## 7. Risiko-Bilanz v2

| Kategorie | Ampel | Begründung |
|---|---|---|
| Handle-Reuse | 🔴 | 1 Name = 8 Konten, 1 Suche verbindet alles |
| **Klarname** | 🔴 | **Öffentlich via Git-Commit-Historie** (v1-Einschätzung „gut geschützt" war FALSCH) |
| Emails | 🔴 | 4 Stück, 3 davon öffentlich erreichbar |
| Live-Sichtbarkeit | 🟡 | Steam zeigt aktuelles Spiel + Online-Status |
| Geleakte Daten | 🟢 | Keine Breach-/Pastebin-Treffer |
| Kontakt-Email im Repo | 🟡 | Tor für Social Engineering |

## 8. Nicht gefunden (auch nach Tiefensuche)

- Twitter/X-Konto (✅ kein indexiertes Konto)
- Facebook-Konto (✅ kein indexiertes Konto)
- Instagram-Konto (❌ angeblicher „2018-Reel" gehört `execute_official` — widerlegt)
- Telefonnummer, exakte Adresse, Passwörter, API-Key-Werte
- Pastebin-/Leak-Treffer für beide bekannten Emails

## 9. Fehlinterpretationen (korrigiert)

- „Familie zockt mit" aus SyxBridge-README → ❌ **widerlegt** (nicht als Familiendatum wertbar)
- „Beruf: Büro/Office" aus Reddit-Kommentar → ❌ **widerlegt** (nicht belastbar zugeordnet)
- „Klarname online nicht verknüpft" → ❌ **widerrufen** (Commit-Historie übersehen)
