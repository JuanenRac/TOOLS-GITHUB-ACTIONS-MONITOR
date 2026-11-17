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
| `ui.screen1_tabs` | Onglets de /screen/1, séparés par des virgules : now, al, charts, sent, sci, scol, ssec, team, fleet, repos, rep, trep, les, hist, cfg. Vide = tous. |
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

## Écrans muraux : vue d'ensemble, en ce moment et sentinelles

Trois pages pour un moniteur ou un téléviseur que personne ne touche. Elles n'ont ni menu latéral ni navigation, montrent tout en une seule vue avec de grands caractères, animent ce qui est vivant et font clignoter doucement les échecs. Elles ne font que lire : aucun bouton ne modifie quoi que ce soit, et elles n'appellent jamais GitHub (elles montrent ce que le moniteur détient déjà).

| Adresse | Ce qu'elle montre |
|---|---|
| `/screen/overview` | Anneau et lettre du score ; le parc (verts, rouges, bloqués, en attente) ; les dernières 24 heures et 7 jours en graphiques en aires ; une carte thermique des dépôts par heure ; ce qui est rouge depuis le plus longtemps ; runners et minutes ; les derniers événements ; le quota GitHub sous forme de jauge. |
| `/screen/now` | Ce qui se passe cette minute : exécutions en cours avec progression et durée, la file, les exécutions en attente d'approbation, les échecs récents, les fusions et versions publiées, les versions à venir et une ligne en direct des deux dernières heures. |
| `/screen/sentinels` | Une carte par sentinelle (A1 à A12) avec son niveau, les constats ouverts, si ses sources sont lisibles, le dernier balayage et un anneau qui suit le balayage ; un radar animé qui marque ce qui ne va pas et les alertes par gravité. |

### Paramètres de l'adresse

Une adresse par moniteur. Un paramètre peut rendre une fenêtre plus calme ou plus petite que ne le permettent les réglages, jamais plus bruyante.

| Paramètre | Effet |
|---|---|
| `?monitor=1` à `9` | Le numéro affiché à côté du titre. |
| `?theme=dark`, `light` ou `contrast` | Couleurs ; contrast est blanc sur noir, pour un écran vu de loin. |
| `?density=compact`, `normal` ou `large` | Taille du texte. `?scale=1.5` agrandit tout (de 0,5 à 3). |
| `?refresh=10` | Secondes entre les mises à jour (de 5 à 120). |
| `?lang=de` | Langue (en, es, de, fr, it, ja, zh, pt). |
| `?rotate=30` | La fenêtre passe toute seule par vue d'ensemble, en ce moment et sentinelles toutes les 30 secondes (au moins 5 ; 0 = pas de rotation). |
| `?blink=off` | Les échecs gardent un halo fixe au lieu de clignoter. Il ne peut pas activer ce que `screens.blink` laisse désactivé. |
| `?sound=on` | Un bip court pour un nouvel échec, seulement si `screens.sound` l'autorise. Désactivé par défaut. |

### Langue des écrans

La langue d'un écran se décide dans cet ordre : `?lang=xx` dans l'adresse ; puis la langue choisie sur la page principale du même navigateur (elle y est enregistrée, et un écran ouvert dans ce navigateur la lit, si bien que l'écran suit la page sans aucun paramètre) ; puis la langue du moniteur (`MONITOR_LANG`, ou celle configurée). Un écran dont la langue enregistrée diffère de celle dans laquelle il a été servi se recharge une fois, avant de dessiner, avec `?lang=` ajouté et les autres paramètres (dont `?rotate=`) conservés. Les huit langues (en, es, de, fr, it, ja, zh, pt) sont celles de la page : titres, libellés, états, gravités, unités et temps relatifs (« il y a 5 min ») viennent du catalogue, et l'heure, la date et les nombres s'écrivent avec les paramètres régionaux de la langue (en-GB, es-ES, de-DE, fr-FR, it-IT, ja-JP, zh-CN, pt-PT). Le lien « Ouvrir l'écran » des Réglages porte déjà `?lang=` avec la langue de la page. Un ordinateur qui ne choisit pas de langue reste en anglais : la langue du navigateur ne décide pas.

### Réglages des écrans muraux

| Réglage | Ce qu'il fait |
|---|---|
| `screens.enabled` | Active les trois pages. Désactivé : toutes les adresses répondent 404. Désactivé par défaut. |
| `screens.default_theme` | dark (par défaut), light ou contrast. |
| `screens.default_density` | compact, normal (par défaut) ou large. |
| `screens.refresh_seconds` | Secondes entre les mises à jour d'une fenêtre (10 par défaut). Les pages lisent le moniteur, jamais GitHub : un délai court ne consomme pas de quota. |
| `screens.rotate_seconds` | 0 (par défaut) = pas de rotation ; à partir de 5, une fenêtre parcourt les trois pages. |
| `screens.blink` | Les échecs clignotent doucement (activé par défaut). |
| `screens.blink_calm_minutes` | Minutes après lesquelles un échec dont personne ne s'est occupé garde un halo fixe au lieu de clignoter (30 par défaut ; 0 = il clignote jusqu'à sa résolution). |
| `screens.sound` | Un bip pour un nouvel échec (désactivé par défaut). |
| `screens.burn_in_protection` | Déplace tout de quelques pixels chaque minute (activé par défaut). |
| `screens.night_dim` | Atténue les écrans entre `screens.night_dim_from_hour` (22) et `screens.night_dim_to_hour` (7) ; désactivé par défaut. |
| `screens.show_repo_names` | all, public (par défaut : les dépôts privés apparaissent comme private-1, private-2...) ou none (tous les noms sont masqués). Utilisez public ou none pour un écran que d'autres personnes peuvent voir. |

### Ce qu'elles montrent et ce qu'elles cachent

Les données viennent de `/api/screens/data?screen=overview` (ou `now`, `sentinels`) : une liste fermée de champs construite à partir du dernier cycle, de l'instantané des sentinelles, des alertes et du score. Elle ne contient jamais de lien, de titre de commit, de nom de job, de nom d'utilisateur ni de chemin de cet ordinateur, et les noms de workflow des dépôts masqués sont masqués aussi. En mode réseau, les pages exigent le même jeton d'accès que le reste du moniteur et la réponse est en lecture seule.

### Leur comportement

- Les échecs clignotent moins de deux fois par seconde (jamais de stroboscope) ; un nouvel échec provoque un seul éclair ; un échec dont personne ne s'est occupé pendant `screens.blink_calm_minutes` minutes garde un halo fixe. Avec le réglage du système pour réduire les animations, ou avec `?blink=off`, rien ne clignote ni ne bouge. Un échec n'est jamais signalé par la seule couleur : il porte un symbole et un mot.
- Quand le moniteur ne répond pas, la page le dit, s'atténue et réessaie après 5, 10, 20... secondes (jusqu'à 60).
- Un écran toujours allumé est protégé contre la rémanence : tout se déplace de quelques pixels chaque minute et la page peut s'atténuer la nuit.

### Installer plusieurs moniteurs

1. Choisissez une adresse par moniteur, par exemple `/screen/overview?monitor=1`, `/screen/now?monitor=2` et `/screen/sentinels?monitor=3` ; ou ouvrez une seule fenêtre avec `?rotate=20`.
2. Ouvrez chacune dans Chrome ou Edge en mode kiosque : `msedge --kiosk "http://cet-ordinateur:8765/screen/now?monitor=2" --edge-kiosk-type=fullscreen` ou `chrome --kiosk "http://cet-ordinateur:8765/screen/now?monitor=2"` ; avec `--app=ADRESSE` au lieu de `--kiosk`, la fenêtre n'a pas de barres. Sans mode kiosque, le bouton discret en bas de page demande le plein écran.
3. Depuis un autre ordinateur, utilisez le mode réseau : le jeton d'accès d'un lecteur suffit, car ces pages n'écrivent jamais.

## Images

L'onglet Maintenant en quatre tailles, avec des données inventées (4K, un moniteur 21:9, un moniteur tourné, un téléphone) :

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultra-large 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![tourné 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![téléphone 390x844](../../docs/screenshots/web_size_phone_light.png)

Les trois écrans muraux en 4K et sur un moniteur tourné, avec des données inventées :

![Vue d'ensemble 4K 3840x2160](../../docs/screenshots/web_screen_overview_4k.png)

![Vue d'ensemble 1080x1920](../../docs/screenshots/web_screen_overview_portrait.png)

![En ce moment 4K 3840x2160](../../docs/screenshots/web_screen_now_4k.png)

![En ce moment 1080x1920](../../docs/screenshots/web_screen_now_portrait.png)

![Sentinelles 4K 3840x2160](../../docs/screenshots/web_screen_sentinels_4k.png)

![Sentinelles 1080x1920](../../docs/screenshots/web_screen_sentinels_portrait.png)
