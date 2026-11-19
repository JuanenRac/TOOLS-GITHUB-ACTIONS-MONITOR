<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](KIOSK.md) | [🇪🇸 Español](KIOSK_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](KIOSK_ita.md) | [🇩🇪 Deutsch](KIOSK_deu.md) | [🇨🇳 简体中文](KIOSK_zho.md) | [🇯🇵 日本語](KIOSK_jpn.md) | [🇵🇹 Português](KIOSK_por.md)

# Kiosque : le moniteur sur une télévision ou un mur

Le profil kiosque est la page du moniteur pour un écran que personne ne touche : sans en-tête, sans onglets, avec un texte plus grand et, si vous le voulez, un contraste élevé et une rotation parmi quelques onglets. Il réutilise ce que la page sait déjà (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0` ; voir [SCREENS_fra.md](SCREENS_fra.md)) et ajoute deux paramètres. Il ne lit rien sur GitHub et n'écrit rien : il décide seulement de l'aspect de la page.

Il est **désactivé par défaut**. Avec `kiosk.enabled` désactivé, la page ignore `kiosk=1` dans l'adresse : un lien copié ailleurs ne change donc rien.

## L'adresse

`python bin/monitor_cli.py kiosk [PRÉRÉGLAGE] [--account ID]` l'affiche ; il n'a pas besoin d'un moniteur en marche. Par exemple, `kiosk ops` affiche :

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| Paramètre | Signification |
|---|---|
| `kiosk=1` | active le profil (seulement quand `kiosk.enabled` est activé) |
| `scale=%` | la taille du texte, de 100 à 400 (une valeur hors de la plage y est ramenée) |
| `contrast=1` / `contrast=0` | contraste élevé activé ou désactivé pour cette fenêtre (le réglage `kiosk.high_contrast` est la valeur par défaut) |
| `rotate=SECONDS` | parcourir les onglets de `tabs=` (le paramètre existant ; la commande ne l'ajoute que lorsque la rotation est activée) |
| `chrome=0`, `screen=`, `tabs=`, `account=` | les paramètres existants |

## Préréglages

| Préréglage | Onglets |
|---|---|
| `ops` | Maintenant, Alertes, Graphiques |
| `team` | Alertes, Santé de l'équipe |
| `release` | Maintenant, Dépôts, Rapports |
| `quiet` | Alertes seulement |

## Réglages (Réglages, Ligne de commande et Kiosque)

| Réglage | Défaut | Signification |
|---|---|---|
| `kiosk.enabled` | désactivé | active le profil |
| `kiosk.font_scale_percent` | 150 | la taille du texte, de 100 à 400 |
| `kiosk.high_contrast` | désactivé | fond noir et lignes blanches |
| `kiosk.rotate_views` | désactivé | un préréglage à plusieurs onglets change d'onglet tout seul ; désactivé, l'écran montre le premier onglet du préréglage |
| `kiosk.rotate_seconds` | 30 | la durée d'affichage de chaque onglet (de 5 à 600) |

La taille est appliquée avec le zoom de la page : chaque chiffre et chaque tableau grandissent ensemble. Une valeur hors de sa plage n'est pas une erreur : elle est remplacée par la valeur par défaut.
