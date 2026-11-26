<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FLEET_APIS.md) | [🇪🇸 Español](FLEET_APIS_spa.md) | [🇫🇷 Français](FLEET_APIS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](FLEET_APIS_deu.md) | [🇨🇳 简体中文](FLEET_APIS_zho.md) | [🇯🇵 日本語](FLEET_APIS_jpn.md) | [🇵🇹 Português](FLEET_APIS_por.md)

# Flotta per ruolo e gruppo, API di lettura e sito dimostrativo

## Ruoli e gruppi

In fondo alla scheda Flotta: il peggior stato di ogni gruppo (ecosistema) con il collegamento al suo schermo `/g/<chiave>`, e una colonna per ruolo di workflow (`fleet.roles`). Ciò che non è letto è `ignoto`, mai a posto.

## Disattivare

`fleet.disabled` accetta nomi, modelli o `group:<chiave>`; dal ciclo successivo non si leggono più, senza riavviare. Edizioni Complete e Full.

## API di lettura

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`. Tutte in sola lettura, con gli stessi controlli di accesso; anche sotto `/api/v1/` se l'API versionata è attiva. `fleet.cctray` fornisce il feed CCTray; `fleet.security_api` i conteggi degli avvisi di segreti e codice per repository (mai un segreto), nominando ciò che non si è potuto leggere. Entrambe spente di fabbrica.

## Impronta dei rapporti

Rapporti e brief dell'IA portano `report_digest`: SHA-256 dei fatti, della versione del monitor, di quella delle regole e del verdetto. Stessa impronta, stesso contenuto. Non è una firma.

## Sito dimostrativo

Una copia statica della dimostrazione (dati inventati, senza accesso, senza azioni, senza richieste altrove) e un controllo dei workflow nel browser con Pyodide (nulla viene caricato):

```
python tools/make_public_demo.py demo-site
```

Il workflow *Demo site* la conserva come artefatto. Pubblicarla è una decisione separata del proprietario del repository; nulla la pubblica da solo. Il controllo nel browser non è stato provato su un sito pubblicato.

## Tutte le impostazioni

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
