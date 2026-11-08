<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | [🇨🇳 简体中文](AI_zho.md) | [🇯🇵 日本語](AI_jpn.md) | [🇵🇹 Português](AI_por.md)

# L'assistant IA de la sentinelle

Optionnel et **désactivé par défaut**. Un modèle de langage peut résumer le rapport quotidien, trier des alertes, expliquer un run échoué, rédiger des notes de release et répondre à une question sur un dépôt. Tout ce qu'il écrit est présenté comme une proposition non vérifiée.

## Fournisseurs

- `ollama` : un modèle sur cet ordinateur (`127.0.0.1` seulement ; rien ne quitte l'ordinateur).
- `openai-compatible` : tout service avec un point d'accès de chat de style OpenAI. Cela sert aussi pour Gemini (son point d'accès compatible OpenAI) et pour OpenAI : indiquez `base_url`, `model` et le NOM de la variable qui contient la clé.
- `anthropic` : l'API Messages d'Anthropic (`https://api.anthropic.com`, en-têtes `x-api-key` et `anthropic-version`). Vous choisissez le modèle ; aucun n'est intégré.
- `copilot` : `gh copilot` avec votre propre connexion GitHub (aucune clé dans le moniteur), réponse texte seulement et sans outils. Il consomme des requêtes premium de votre offre Copilot. Lancez `gh copilot` une fois à la main pour installer la CLI.
- La clé n'est jamais enregistrée : vous indiquez le NOM d'une variable d'environnement. Les trois fournisseurs distants ENVOIENT des données de vos dépôts à un tiers.


## Ce qu'elle peut voir

- Toute entrée est nettoyée : caractères de contrôle retirés, secrets masqués par motif, longueur limitée, contenu placé entre des délimiteurs aléatoires et déclaré non fiable. La réponse est coupée et ses liens neutralisés.
- Dans l'onglet Réglages vous choisissez les types d'événement analysables (`build`, `codeql`, `report`), les dépôts visibles (vide = ceux que le moniteur surveille), la langue des réponses, la limite quotidienne d'appels et les limites de taille. Un bouton teste la connexion et la page montre les appels du jour.


## Proposer et exécuter des actions

- Niveau 3 (`ai.actions.enabled`) : une commande de la réponse n'est gardée que si elle correspond à la LISTE FERMÉE : `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` et `act -W FICHIER -j JOB` (cette dernière n'est que montrée). La commande affichée est reconstruite à partir des éléments vérifiés, jamais copiée du modèle ; le dépôt et le numéro de run ou d'issue doivent déjà être surveillés par le moniteur.
- Niveau 4 (`ai.actions.execute`, interrupteur propre, désactivé) : chaque proposition a un bouton de confirmation ; une boîte montre la commande entière et rien ne s'exécute avant votre accord. Elle s'exécute avec votre propre `gh`, sans shell, au plus `ai.actions.max_per_hour` par heure, chaque tentative va dans le journal local affiché par la page, et après deux échecs de suite les actions se verrouillent jusqu'à ce que vous les déverrouilliez.
- Absents de la liste, volontairement : supprimer des branches, fermer ou fusionner des pull requests, tout ce qui touche aux secrets ou aux réglages.
