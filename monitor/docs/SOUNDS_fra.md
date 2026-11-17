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

## Pourquoi un navigateur peut rester muet, et ce que fait la page

- Un navigateur ne laisse une page émettre du son qu'après un clic, un toucher ou une touche sur elle. Jusque-là, la barre affiche l'avis "Son bloqué par le navigateur : cliquez ici pour l'activer". Le premier clic n'importe où le débloque.
- Ce qui s'est passé pendant que le son était bloqué est conservé (dix minutes au plus) et retentit à la première occasion : le clic, la page qui revient au premier plan ou la vérification suivante, toutes les deux secondes. Rien ne se perd entre deux lectures ; ce qui a plus de dix minutes est une vieille nouvelle et n'est pas annoncé.
- Le premier regard de la page retient seulement ce qui est déjà là ; un rechargement dans les quelques heures le retient aussi, donc un échec arrivé page fermée est nouveau.
- Un onglet en arrière-plan garde son son tant que le navigateur garde la page éveillée ; certains navigateurs mettent en pause les onglets cachés au bout d'un moment. Mieux vaut laisser les écrans muraux et la page dans une fenêtre visible.

## Pas de spam

- Un type qui vient de retentir attend `sound.cooldown_seconds` (30 s par défaut) avant de retentir de nouveau.
- Plusieurs types dans un même regard font une seule salve : trois motifs au plus, le plus grave d'abord ; le reste attend la salve suivante. Deux salves ne se chevauchent jamais.
- Une alerte mise en sourdine (onglet Alertes) ne retentit jamais.

## Réglages (Réglages, Son)

Tous sont dans le fichier de configuration et dans l'onglet Réglages ; le volume, le thème et les interrupteurs agissent aussitôt.

| Réglage | Ce qu'il fait |
|---|---|
| `sound.enabled` | Interrupteur général de tous les sons de la page. |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info` | Un interrupteur par type (tous activés par défaut). |
| `sound.theme` | `classic` (tons clairs) ou `soft` (tons plus graves, ronds et lents). Chaque type garde son rythme dans les deux. |
| `sound.volume` | De 1 à 100, modéré par défaut. |
| `sound.cooldown_seconds` | Pause entre deux sons du même type. |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | Heures de silence (désactivées par défaut) : entre les deux heures de cet ordinateur rien ne sonne ; elles peuvent passer minuit. |
| `sound.server_beep` | Désactivé par défaut. Un bip de cet ordinateur pour un nouveau rouge quand aucune page n'est ouverte (local uniquement). |

## Tester chaque son

Dans Réglages, Interface, le bouton "Tester le son" joue le bing bing classique et un bouton par type joue ce type avec le volume et le thème des réglages. La pastille "Son" de la barre du bas coupe tout dans ce navigateur.

## Écrans muraux

Les écrans muraux (`/screen/...`) utilisent les mêmes sons, avec le même thème, le même volume, les mêmes interrupteurs et les mêmes heures de silence. Ils sont désactivés par défaut : `screens.sound` doit être activé et la fenêtre a besoin de `?sound=on`. Un écran que personne ne touche ne peut pas recevoir le clic que demande le navigateur : lancez le navigateur de l'écran avec son option "autoriser l'audio sans geste" (dans Chromium, `--autoplay-policy=no-user-gesture-required`) ou cliquez une fois dans la fenêtre.

## Où c'est conservé

La pastille de sourdine est retenue par chaque navigateur ; ce que la page sait de son dernier regard reste aussi dans le navigateur. Rien sur les sons n'est envoyé à un serveur.
