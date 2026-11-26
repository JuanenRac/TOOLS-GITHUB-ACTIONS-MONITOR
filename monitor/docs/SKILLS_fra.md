<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SKILLS.md) | [🇪🇸 Español](SKILLS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SKILLS_ita.md) | [🇩🇪 Deutsch](SKILLS_deu.md) | [🇨🇳 简体中文](SKILLS_zho.md) | [🇯🇵 日本語](SKILLS_jpn.md) | [🇵🇹 Português](SKILLS_por.md)

# Skills pour les IA

Le moniteur contient deux skills : de courts guides, en anglais, qui disent à une IA comment travailler avec lui. Elles sont dans le dossier `skills/` du paquet, dans la page (Réglages, onglet IA) et une commande les installe.

## Les deux skills

- `skills/internal` : pour l'IA intégrée au moniteur, locale (Ollama, un serveur llama.cpp, LM Studio) ou externe (l'API d'un fournisseur). Elle dit ce qu'est le moniteur et ce qu'il voit, ce qu'elle peut lire, ce qu'elle ne doit jamais faire, comment diagnostiquer un rouge, quand se taire et comment utiliser et proposer des leçons. Son cœur (`SKILL.md`) est ajouté à chaque prompt de cette IA, coupé à `ai.skill_max_chars`, quand `ai.skill` est activé.
- `skills/external` : pour les IA qui parlent au moniteur de l'extérieur, dans tous les sens : lire (`/api/ai/*`, les fichiers de `ai/`), être prévenues (le flux ou le résumé toutes les quelques minutes), écrire (acquitter, leçons, échecs, préférences de notification) avec les permissions qui conviennent, le lien entre le moniteur et une session, le résumé avant un push et tout le cycle d'auto-apprentissage. Elle couvre une IA en ligne de commande, une IA avec seulement HTTP ou des fichiers, une IA avec MCP et une IA sur le flux.

## Contenu

Chaque skill est un `SKILL.md` court (le cœur) et un dossier `references/` lu seulement au besoin, de sorte qu'un modèle à petit contexte puisse ne prendre que le cœur : des scénarios pas à pas (un rouge réel, un rouge passager, quota bas, un moniteur dégradé, un échec répété, une nouvelle leçon, sans réseau, plusieurs écrans), le cycle d'auto-apprentissage, les fournisseurs et leurs limites, la sécurité (injection d'instructions depuis les journaux, secrets, permissions minimales, audit de ce qu'écrit une IA) et les références générées depuis le code.

## Rien n'est oublié

Les références (`api.md`, `cli.md`, `settings.md`, `files.md`, `roles.md`, `tabs.md`) et `skills/COVERAGE.md` sont GÉNÉRÉES depuis le code par `python tools/make_skill_refs.py` : chaque endpoint avec le rôle minimal qui peut l'appeler, chaque commande et option, chaque réglage avec sa valeur par défaut, chaque fichier écrit par le moniteur, chaque rôle et chaque onglet. Un test lit les mêmes listes dans le code et échoue si quelque chose n'est pas nommé dans les skills : un endpoint, une commande, un réglage ou un fichier nouveau ne peut pas apparaître sans être décrit aux IA (et le générateur s'arrête tant que sa note n'est pas écrite).

## Installer

Copiez la skill dans le dossier où votre outil d'IA lit ses skills :

```
python bin/monitor_cli.py install-skill internal --dest /path/to/the/skills/folder
python bin/monitor_cli.py install-skill external --dest /path/to/the/skills/folder
```

## Sécurité de l'installateur

Il écrit `github-actions-monitor-internal` ou `github-actions-monitor-external` dans le dossier indiqué et rien d'autre. Il n'écrase jamais un fichier qui diffère de celui du paquet (il garde le vôtre et dit lequel) et refuse le disque D: et les chemins réseau. Une seconde exécution ne change rien.

## Dans la page et en HTTP

Dans les Réglages, onglet IA, le bloc **Skills pour les IA** a Copier (le cœur de la skill) et Télécharger (la skill entière avec ses références en un fichier) pour chacune. `GET /api/skills` les liste et `GET /api/skills?name=internal|external[&file=references/api.md][&all=1]` renvoie le texte ; c'est en lecture seule.

## Réglages

`ai.skill` (activé) et `ai.skill_max_chars` (3000 ; 1500 pour un petit modèle local). Enregistrer des échecs depuis l'extérieur se fait par `POST /api/ai/failures` et demande `lessons.allow_write` et un administrateur, comme écrire une leçon.

## Publication dans un registre de skills

`python tools/prepare_skill_bundle.py --out DIR` prépare le dossier de la skill externe (SKILL.md, références, `bundle.json` avec la version du moniteur et la licence, `SHA256SUMS`) ; les mêmes sources donnent les mêmes octets. Rien n'est publié : l'envoi vers ClawHub se fait à la main, avec le compte du mainteneur, après lecture des conditions.

## Assistants

Seul ce qui a vraiment été essayé est dit testé.

| Assistant ou voie | Ligne de commande | HTTP et fichiers | MCP |
|---|---|---|---|
| Claude Code | testé | testé | compatible par protocole, non testé |
| Autres assistants | compatible par protocole, non testé | compatible par protocole, non testé | compatible par protocole, non testé |
