<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | [🇪🇸 Español](SCREENS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SCREENS_ita.md) | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | [🇵🇹 Português](SCREENS_por.md)

# Écrans, tailles et orientation

La page s'adapte à la taille de sa fenêtre, du téléphone à la 4K, à la verticale ou à l'horizontale, et un même moniteur peut servir plusieurs écrans, chacun avec les onglets que vous choisissez. Rien n'est interrogé deux fois : tous les écrans lisent le même état.

## Adresses

- `/` - la page entière.
- `/screen/1`, `/screen/2`, `/screen/3` - les onglets définis pour cet écran (`ui.screen1_tabs` ...). Ouvrez chacune dans une fenêtre de son propre écran ou téléviseur.
- `?orient=portrait` ou `?orient=landscape` force la disposition d'une fenêtre ; `?tabs=now,charts` et `?rotate=30` fixent les onglets et les secondes entre eux pour une fenêtre.

## Réglages

| Réglage | Effet |
|---|---|
| `ui.orientation` | auto suit la fenêtre ; portrait empile les panneaux en une colonne ; landscape garde la disposition côte à côte. |
| `ui.rotate_seconds` | 0 = désactivé. Secondes entre les onglets d'un écran qui en a plusieurs. |
| `ui.screen1_tabs` | Onglets de /screen/1, séparés par des virgules : now, al, sent, charts, repos, hist, cfg. Vide = tous. |
| `ui.screen1_orientation` | auto, portrait ou landscape pour /screen/1 seulement. |
| `ui.screen2_tabs` | Onglets de /screen/2. |
| `ui.screen2_orientation` | Orientation de /screen/2. |
| `ui.screen3_tabs` | Onglets de /screen/3. |
| `ui.screen3_orientation` | Orientation de /screen/3. |
| `ui.now_sort` | Ordre de En cours pour qui n'a pas choisi : ecosystem, severity, age, newest, repo, event ou state. |
| `ui.alerts_sort` | Ordre de l'onglet Alertes pour qui n'a pas choisi : server, severity, streak, class, age, newest, repo, origin ou state. |

## Ordre des listes

La section **En cours** du premier onglet est triée par écosystème, avec un titre pour chacun. La liste au-dessus de la section le change : écosystème, gravité (d'abord les exécutions bloquées, puis celles avec un job en échec, puis en cours, puis en file), ancienneté (la plus longue d'abord), plus récent d'abord, dépôt, déclencheur (push, pull_request, schedule...) et état (en cours avant en file). Le choix est mémorisé pour chaque personne : en mode équipe le serveur le garde avec l'utilisateur (`GET` et `POST /api/auth/me/view`, il le suit donc dans un autre navigateur), sinon ce navigateur. Tant que personne ne choisit, l'ordre est `ui.now_sort` du fichier de configuration (écosystème s'il manque ou s'il est faux). Les boutons **Tout déplier** et **Tout replier** à côté de la liste déplient ou replient d'un coup tous les dépôts de la section, dans n'importe quel ordre ; le choix est mémorisé pour chaque personne au même endroit et survit à une actualisation (un dépôt que vous ouvrez ou fermez ensuite à la main garde votre choix).

La liste de l'onglet **Alertes** garde l'ordre envoyé par le moniteur tant que quelqu'un n'en choisit pas un autre avec la liste au-dessus : gravité (critique, erreur, avertissement, info), la plus longue série d'échecs consécutifs d'abord, classe (une alerte d'erreur ou critique est réelle et passe avant celles à surveiller), les plus anciennes d'abord, les plus récentes d'abord, dépôt, origine (la sentinelle qui l'a levée) et état (ouvertes avant mises en sourdine). Elle est mémorisée de la même façon ; tant que personne ne choisit, `ui.alerts_sort` du fichier de configuration s'applique (`server` s'il manque ou s'il est faux).

## Tailles testées

Un test de navigateur ouvre la page dans chacune de ces tailles, parcourt tous les onglets et échoue en cas de défilement latéral ou de texte qui sort de sa boîte. Les fenêtres de 2400 px ou plus reçoivent un texte plus grand (3200 px, plus grand encore) au lieu d'une disposition étirée ; une fenêtre plus haute que large empile les panneaux.

| Taille | Type |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Recette pour un poste de deux ou trois écrans

1. Sur l'ordinateur qui exécute le moniteur, mettez `ui.screen1_tabs` à `now,al`, `ui.screen2_tabs` à `charts,repos` et, pour un écran tourné, `ui.screen2_orientation` à `portrait`.
2. Ouvrez `http://cet-ordinateur:8765/screen/1` dans une fenêtre du premier écran et `/screen/2` sur le second ; F11 pour le plein écran. Depuis un autre ordinateur, utilisez le mode réseau avec son jeton d'accès.
3. Pour un écran mural que personne ne touche, donnez-lui plusieurs onglets et mettez `ui.rotate_seconds` à 20-30.

## Images

L'onglet Maintenant en quatre tailles, avec des données inventées (4K, un moniteur 21:9, un moniteur tourné, un téléphone) :

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultra-large 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![tourné 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![téléphone 390x844](../../docs/screenshots/web_size_phone_light.png)
