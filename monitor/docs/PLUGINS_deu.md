<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PLUGINS.md) | [🇪🇸 Español](PLUGINS_spa.md) | [🇫🇷 Français](PLUGINS_fra.md) | [🇮🇹 Italiano](PLUGINS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](PLUGINS_zho.md) | [🇯🇵 日本語](PLUGINS_jpn.md) | [🇵🇹 Português](PLUGINS_por.md)

# Plugins und Geheimnisspeicher

Plugins ergänzen den Monitor um Prüfungen, ohne ihn zu ändern. Alles ist standardmäßig aus. Die Lite-Ausgabe hat keine Plugins.

## Einschalten

`plugins.enabled` einschalten, dann das gewünschte Plugin. Einstellungen > Erweiterungen zeigt jedes mit Berechtigungen, Schlüssel, Zustand und Isolierung. Funde sind Meldungen der Quelle `plugin` mit dem Plugin-Namen davor.

## Offizielle Plugins

Sie sind Teil der signierten Veröffentlichung und laufen im Monitor in einem eigenen Thread.

- **discussions** (`plugins.official.discussions.enabled`): Diskussionen ohne Kommentar seit mehr als `plugins.official.discussions.days` Tagen. Issues und Pull Requests gehören zu Collab.
- **packages** (`plugins.official.packages.enabled`): Container- oder npm-Pakete mit mehr Versionen als `plugins.official.packages.max_versions`. Braucht `read:packages`. Releases gehören zum Delivery-Wächter.

## Plugins von Dritten

`plugins.third_party.enabled` einschalten. Ein Paket ist ein ZIP mit `plugin.json` und einer separaten Signatur `NAME.zip.ed25519.sig`, vom Autor selbst erzeugt. Installiert wird nur, wenn ein Schlüssel **Ihres** Schlüsselbunds mit dem Bereich `plugins` signiert hat, und erst nach Wiederholen des Fingerabdrucks. Es kommt ausgeschaltet an. Die Signatur wird vor jedem Lauf geprüft; ein widerrufener Schlüssel oder eine geänderte Datei pausiert das Plugin.

**Signiert heißt nicht sicher.** Ein Manifest ist keine Sandbox.

```
python bin/monitor_cli.py plugin init --path my-plugin
python bin/monitor_cli.py plugin validate --path my-plugin
python bin/monitor_cli.py plugin pack --path my-plugin --out my-plugin.zip
python bin/monitor_cli.py keyring add --key-id author --public-key HEX --key-scope plugins
python bin/monitor_cli.py plugin verify --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip --fingerprint HEX
python bin/monitor_cli.py plugin enable --name my-plugin
python bin/monitor_cli.py plugin list
python bin/monitor_cli.py plugin audit
python bin/monitor_cli.py plugin uninstall --name my-plugin
```

## Was isoliert ist

| System | Eigener Prozess, leere Umgebung, kein Token | Ohne Netz | Speicher und Kindprozesse |
|---|---|---|---|
| Linux | ja | ja, wenn das System Benutzer-Namensräume erlaubt, sonst **ohne Netzisolierung** | Speicher- und CPU-Grenzen |
| Windows | ja | **nein**: **ohne Netzisolierung** | Job-Objekt: Speichergrenze, keine Kindprozesse |
| macOS | ja | **nein**: **ohne Netzisolierung** | CPU-Grenze; Speicher nicht garantiert |

Auf keinem System sind Ihre Dateien vor einem solchen Plugin verborgen: es läuft mit Ihrem Benutzer. Leeres `plugins.worker.platforms_ok` heißt: Fremd-Plugins laufen nie. GitHub-Lesezugriffe gehen über den Monitor, der nur die `get_paths` des Manifests auf beobachteten Repositorys erlaubt. `plugins.worker.timeout_s`, `max_output_kb` und `memory_mb` begrenzen jeden Lauf.

## Nicht vertrauenswürdige Ausgabe und Zustand

Titel werden bereinigt und gekürzt (`plugins.alert_title_max`), nur Links zu github.com bleiben, ein Fremd-Plugin kann keine kritische Meldung auslösen. Plugin-Text ist Daten, nie eine Anweisung an eine KI. Nach `plugins.breaker.failures` Fehlern in Folge wird pausiert, bis Sie fortsetzen; pausiert oder eingeschränkt heißt nicht „alles gut“. Die Doctor-Prüfung `plugins` und `plugin audit` melden widerrufene oder geänderte Pakete.

## Für Autoren

Der Vertrag ist Version 1 (`api_compat`). `run(ctx)` liefert `{"alerts": [{id, code, level, repo, url, title}]}`; `ctx` bietet `owner`, `now`, `options`, `repos()`, `get(path)`, `discussions()`, jeweils mit Berechtigung (`repos.list`, `gh.get`, `graphql.discussions`). `init` schreibt eine Vorlage mit Test. Der Monitor signiert nie.

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## Routen und pip-Pakete

Routen (Administrator, Änderungen nur von diesem Rechner): `/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`. Mit `plugins.entry_points` listet der Monitor mit pip installierte Pakete der Gruppe `gha_monitor.plugins` mit einer `*.plugin.zip`; ihr Code wird nie importiert, das ZIP wird wie jedes andere installiert.

## Das GitHub-Token aus einem anderen Programm lesen

`secrets.backend` liest das Token statt es im Monitor zu speichern (`github_token.enabled` muss an sein). Nur lesend. `vault` (HTTP, `secrets.vault.addr`, `path`, `field`, Vault-Token in der von `token_env` genannten Umgebungsvariable; https, http nur zu diesem Rechner), `sops` (`secrets.sops.file`, `field`; nur auf vertrauenswürdigen Rechnern), `bitwarden` (`bws`, `secrets.bitwarden.item`), `aws`, `azure`, `gcp` (deren Werkzeuge, `secrets.cloud.ref`). Mit `secrets.reload_on_rotate` wird alle `secrets.reload_seconds` neu gelesen. Gegen Attrappen und ein Vault im Entwicklungsmodus getestet; kein echtes Cloud-Konto.
