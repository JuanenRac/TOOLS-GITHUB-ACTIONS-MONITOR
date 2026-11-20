<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SOUNDS.md) | [🇪🇸 Español](SOUNDS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SOUNDS_ita.md) | [🇩🇪 Deutsch](SOUNDS_deu.md) | [🇨🇳 简体中文](SOUNDS_zho.md) | [🇯🇵 日本語](SOUNDS_jpn.md) | [🇵🇹 Português](SOUNDS_por.md)

# Sons

La page fait ses propres sons avec l'API Web Audio, un pour chaque type d'événement, afin de savoir à l'oreille ce qui s'est passé sans regarder. Il n'y a aucun fichier audio : les tons sont produits dans le navigateur, hors connexion, et rien n'est envoyé nulle part. Chaque son a aussi son avis visuel (les tuiles, les onglets, les pastilles) ; le son ne le remplace jamais.

| Type | Quand il retentit | Le son |
|---|---|---|
| Rouge | Un workflow qui n'était pas rouge passe au rouge (un nouvel échec). | Deux tons montants, le classique "bing bing". |
| Sécurité ou grave | Une nouvelle alerte de la sentinelle de sécurité, une alerte grave (erreur ou critique) de la sentinelle de collaboration, ou un compte devenu aveugle. | Trois pulsations graves. |
| Bloqué | Un build bloqué, une file fantôme ou un problème de runners. | Un long glissement descendant. |
| Score | Le score de la flotte baisse (`score.dropped`). | Trois notes descendantes. |
| Connexion | La connexion à GitHub, ou celle de cette page avec le moniteur, est perdue. | Deux notes graves et longues. |
| Avertissement | Une nouvelle alerte de niveau avertissement (une signature en attente, un ticket ancien, une pull request qui attend). | Deux tons moyens identiques. |
| Résolu | Un workflow rouge repasse au vert, ou une alerte grave disparaît. | Trois notes montantes. |
| Rapport | L'un des rapports facultatifs montre un constat qui n'y était pas. | Deux carillons doux, aigu puis plus grave. |
| Leçon | Les leçons des échecs montrent une nouvelle catégorie, ou une qui commence à se répéter ou à s'appliquer. | Trois notes aiguës rapides. |
| Info | Une nouvelle alerte de niveau info (la release de l'original d'un fork, par exemple). | Un petit signal doux. |
| De retour en ligne | La connexion à GitHub, ou de cette page avec le moniteur, revient après une coupure. | Quatre notes montantes. |

## Pourquoi un navigateur peut rester muet, et ce que fait la page

- Un navigateur ne laisse une page émettre du son qu'après un clic, un toucher ou une touche sur elle. Jusque-là, la barre affiche l'avis "Son bloqué par le navigateur : cliquez ici pour l'activer". Le premier clic n'importe où le débloque.
- Ce qui s'est passé pendant que le son était bloqué est conservé (dix minutes au plus) et retentit à la première occasion : le clic, la page qui revient au premier plan ou la vérification suivante, toutes les deux secondes. Rien ne se perd entre deux lectures ; ce qui a plus de dix minutes est une vieille nouvelle et n'est pas annoncé.
- Le premier regard de la page retient seulement ce qui est déjà là ; un rechargement dans les quelques heures le retient aussi, donc un échec arrivé page fermée est nouveau.
- Un onglet en arrière-plan garde son son tant que le navigateur garde la page éveillée ; certains navigateurs mettent en pause les onglets cachés au bout d'un moment. Mieux vaut laisser les écrans muraux et la page dans une fenêtre visible.

## Pas de spam

- Un type qui vient de retentir attend `sound.cooldown_seconds` (30 s par défaut) avant de retentir de nouveau.
- Plusieurs types dans un même regard font une seule salve : trois motifs au plus, le plus grave d'abord ; le reste attend la salve suivante. Deux salves ne se chevauchent jamais.
- Une alerte mise en sourdine (onglet Alertes) ne retentit jamais.

## La bibliothèque de sons

En plus des onze sons que chaque type d'événement a toujours eus, le moniteur embarque une bibliothèque de 54 sons (65 au total) que vous pouvez attribuer à n'importe quel type d'événement. Ils sont fabriqués dans le navigateur (et, pour le bip de cet ordinateur, avec les mêmes notes) : aucun fichier audio à télécharger. Les sons des types sont les onze premiers ; les autres s'attribuent librement : `bell`, `chime`, `ding_dong`, `doorbell`, `ding`, `ping_high`, `ping_low`, `tick_soft`, `tock_soft`, `double_tick`, `tick_tock`, `knock`, `knock_three`, `blip`, `bloop`, `bubble`, `drop`, `droplet`, `arpeggio_up`, `arpeggio_down`, `minor_up`, `minor_down`, `fanfare`, `level_up`, `coin`, `harp_up`, `harp_down`, `marimba`, `xylophone`, `pluck`, `cascade`, `sparkle`, `ascend`, `descend`, `notify_a`, `notify_b`, `notify_c`, `sweep_up`, `sweep_down`, `whistle_up`, `whistle_down`, `zap`, `laser`, `radar`, `sonar`, `beacon`, `heartbeat`, `alarm_fast`, `siren`, `klaxon`, `buzzer`, `gong`, `phone`, `cuckoo`.

Pour donner à un type un autre son, écrivez des paires `type=son` séparées par des virgules dans `sound.voices`, par exemple `new_red=coin,warning=drop`. Les types sont `new_red`, `sentinel`, `stuck`, `score_drop`, `connection_lost`, `warning`, `resolved`, `report`, `lesson`, `info`, `live_recovered`. Un nom absent de la bibliothèque est ignoré et le type garde son propre son. Les écrans muraux peuvent ajouter leur propre liste dans `screens.sound_voices` et leur propre volume dans `screens.sound_volume`. Aucun son ne dure plus d'une seconde et tous sont différents.

Deux fonds optionnels, tous deux désactivés par défaut : `sound.ambient` (deux notes graves très douces, calmes tant que rien n'est rouge, plus rugueuses dès que quelque chose l'est) et `sound.tick` (un clic sec très bref toutes les `sound.tick_seconds`, pour qu'un écran figé s'entende). Les deux suivent la pastille de sourdine, l'interrupteur principal et les heures de silence.

## Réglages (Réglages, Son)

Tous sont dans le fichier de configuration et dans l'onglet Réglages ; le volume, le thème et les interrupteurs agissent aussitôt.

| Réglage | Ce qu'il fait |
|---|---|
| `sound.enabled` | Interrupteur général de tous les sons de la page. |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info`, `sound.on_live_recovered` | Un interrupteur par type (tous activés par défaut). |
| `sound.theme` | `classic` (tons clairs) ou `soft` (tons plus graves, ronds et lents). Chaque type garde son rythme dans les deux. |
| `sound.volume` | De 1 à 100, modéré par défaut. |
| `sound.cooldown_seconds` | Pause entre deux sons du même type. |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | Heures de silence (désactivées par défaut) : entre les deux heures de cet ordinateur rien ne sonne ; elles peuvent passer minuit. |
| `sound.server_beep` | Désactivé par défaut. Le moniteur lui-même émet un son sur cet ordinateur quand aucune page n’est ouverte ou que le navigateur bloque le son : un motif pour chaque type d’événement du tableau ci-dessus (tons de Windows, sons système de macOS, événements canberra sous Linux), avec les mêmes interrupteurs et heures calmes que la page, en une rafale d’au plus trois types à la fois ; local uniquement. |
| `sound.voices` | Donne à un type d'événement un autre son de la bibliothèque (paires `type=son` séparées par des virgules). Vide par défaut. |
| `sound.ambient`, `sound.ambient_volume` | Ambiance sonore (désactivée par défaut) et son volume, de 1 à 50. |
| `sound.tick`, `sound.tick_seconds` | Tic-tac d'horloge (désactivé par défaut) et secondes entre les tics, de 1 à 60. |
| `screens.sound_voices`, `screens.sound_volume` | Comme `sound.voices`, seulement pour les écrans muraux, et leur propre volume (0 = celui de `sound.volume`). |

## Tester chaque son

Dans Réglages, Interface, le bouton "Tester le son" joue le bing bing classique et un bouton par type joue ce type avec le volume et le thème des réglages. La pastille "Son" de la barre du bas coupe tout dans ce navigateur.

## Écrans muraux

Les écrans muraux (`/screen/...`) utilisent les mêmes sons, avec le même thème, le même volume, les mêmes interrupteurs et les mêmes heures de silence. Ils sont désactivés par défaut : `screens.sound` doit être activé et la fenêtre a besoin de `?sound=on`. Un écran que personne ne touche ne peut pas recevoir le clic que demande le navigateur : lancez le navigateur de l'écran avec son option "autoriser l'audio sans geste" (dans Chromium, `--autoplay-policy=no-user-gesture-required`) ou cliquez une fois dans la fenêtre.

## Où c'est conservé

La pastille de sourdine est retenue par chaque navigateur ; ce que la page sait de son dernier regard reste aussi dans le navigateur. Rien sur les sons n'est envoyé à un serveur.
