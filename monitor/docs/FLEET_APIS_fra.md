<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FLEET_APIS.md) | [🇪🇸 Español](FLEET_APIS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](FLEET_APIS_ita.md) | [🇩🇪 Deutsch](FLEET_APIS_deu.md) | [🇨🇳 简体中文](FLEET_APIS_zho.md) | [🇯🇵 日本語](FLEET_APIS_jpn.md) | [🇵🇹 Português](FLEET_APIS_por.md)

# Flotte par rôle et groupe, API de lecture et site de démonstration

## Rôles et groupes

À la fin de l'onglet Flotte : le pire état de chaque groupe (écosystème) avec un lien vers son écran `/g/<clé>`, et une colonne par rôle de workflow (`fleet.roles`). Ce qui n'est pas lu est `inconnu`, jamais correct.

## Désactiver

`fleet.disabled` accepte noms, motifs ou `group:<clé>` ; le moniteur cesse de les lire au cycle suivant, sans redémarrer. Éditions Complete et Full.

## API de lecture

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`. Toutes en lecture seule, avec les mêmes contrôles d'accès ; aussi sous `/api/v1/` si l'API versionnée est active. `fleet.cctray` sert le flux CCTray ; `fleet.security_api` sert des décomptes d'alertes de secrets et de code par dépôt (jamais un secret), en nommant ce qui n'a pas été lu. Les deux désactivées par défaut.

## Empreinte des rapports

Rapports et briefs IA portent `report_digest` : SHA-256 des faits, de la version du moniteur, de celle des règles et du verdict. Même empreinte, même contenu. Ce n'est pas une signature.

## Site de démonstration

Une copie statique de la démo (données inventées, sans connexion, sans action, sans requête ailleurs) et une vérification de workflow dans le navigateur avec Pyodide (rien n'est envoyé) :

```
python tools/make_public_demo.py demo-site
```

Le workflow *Demo site* la conserve en artefact. La publier est une décision séparée du propriétaire du dépôt ; rien ne la publie seul. La vérification dans le navigateur n'a pas été essayée sur un site publié.

## Tous les réglages

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
