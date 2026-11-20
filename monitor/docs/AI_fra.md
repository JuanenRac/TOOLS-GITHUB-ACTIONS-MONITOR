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


## Les icônes d'IA de la barre

La barre en haut à droite affiche deux icônes : la puce est l'IA intégrée au moniteur et les ondes sont un outil d'IA externe qui lit le moniteur. Un badge dit l'état sans dépendre de la couleur : une coche signifie active, une barre oblique (avec un dessin en pointillés) inactive et un triangle une erreur (l'IA intégrée est configurée mais ne répond pas). Survolez pour voir l'état exact ; cliquez sur l'icône, ou appuyez sur Entrée ou Espace quand elle a le focus, pour ouvrir la section IA des réglages.

## Ce qu'elle peut voir

- Toute entrée est nettoyée : caractères de contrôle retirés, secrets masqués par motif, longueur limitée, contenu placé entre des délimiteurs aléatoires et déclaré non fiable. La réponse est coupée et ses liens neutralisés.
- Le même nettoyeur unique (jetons, clés, identifiants dans les adresses, adresses e-mail, adresses IP, votre dossier personnel) sert cet assistant, le flux pour les IA, les points d'accès et le crochet. Il fonctionne par motifs : il réduit le risque, ce n'est pas une garantie. Un appel à un fournisseur ne suit jamais une redirection (la clé irait vers une autre adresse) et n'utilise pas les variables de proxy de l'environnement : un serveur de cet ordinateur est appelé directement, un serveur distant ne passe par le proxy qu'avec `network.use_proxy`.
- Dans l'onglet Réglages vous choisissez les types d'événement analysables (`build`, `codeql`, `report`), les dépôts visibles (vide = ceux que le moniteur surveille), la langue des réponses, la limite quotidienne d'appels et les limites de taille. Un bouton teste la connexion et la page montre les appels du jour.


## Proposer et exécuter des actions

- Niveau 3 (`ai.actions.enabled`) : une commande de la réponse n'est gardée que si elle correspond à la LISTE FERMÉE : `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` et `act -W FICHIER -j JOB` (cette dernière n'est que montrée). La commande affichée est reconstruite à partir des éléments vérifiés, jamais copiée du modèle ; le dépôt et le numéro de run ou d'issue doivent déjà être surveillés par le moniteur.
- Niveau 4 (`ai.actions.execute`, interrupteur propre, désactivé) : chaque proposition a un bouton de confirmation ; une boîte montre la commande entière et rien ne s'exécute avant votre accord. Elle s'exécute avec votre propre `gh`, sans shell, au plus `ai.actions.max_per_hour` par heure, chaque tentative va dans le journal local affiché par la page, et après deux échecs de suite les actions se verrouillent jusqu'à ce que vous les déverrouilliez.
- Absents de la liste, volontairement : supprimer des branches, fermer ou fusionner des pull requests, tout ce qui touche aux secrets ou aux réglages.

## Modèles du fournisseur

Le nom du modèle est un texte libre, mais le moniteur peut lire la liste des modèles auprès du fournisseur et y vérifier le nom. Les modèles et les versions changent souvent : le moniteur ne fournit donc aucune liste de modèles, et les exemples des préréglages peuvent être périmés.

- **La liste.** Réglages, onglet *IA externe*, bloc *Modèles et données par modèle* : *Charger les modèles du fournisseur* lit la liste (`/models` d'un serveur de style OpenAI, la liste équivalente de l'API d'Anthropic, `/api/tags` d'Ollama) par une requête en lecture seule. La clé passe dans un en-tête, est lue dans sa variable d'environnement et n'est jamais enregistrée. Cherchez dans la liste et choisissez un modèle avec *Utiliser ce modèle*. La liste est conservée et bornée par `ai.catalog.ttl_minutes` et `ai.catalog.max_requests_per_day`. Avec `ai.catalog.enabled` activé (désactivé par défaut), le moniteur prévient aussi quand le modèle configuré n'apparaît plus dans la liste (retiré ou renommé) ; désactivé, vous seul déclenchez la lecture.
- **Données par modèle.** La fenêtre de contexte, le prix d'entrée et de sortie par million de jetons et la prise en charge des outils ne sont renseignés qu'avec ce que le fournisseur renvoie ; ce qu'il ne dit pas reste *inconnu* (aucun chiffre n'est inventé). Vous pouvez saisir vos propres valeurs ; elles l'emportent. Avec `ai.catalog.fit_context` activé (désactivé par défaut), la limite d'entrée est adaptée à la fenêtre de contexte quand elle est connue.
- **Tester un modèle.** *Tester ce modèle* ou `monitor_cli.py ai test --provider NOM --model NOM` interroge le modèle sur un échec SYNTHÉTIQUE (jamais des données de vos dépôts) et affiche la latence, les jetons, le coût estimé et un exemple de réponse. Cela compte comme un appel du plafond quotidien, et le résultat (« testé », avec la date locale) est conservé dans le tableau.
- **Commandes.** `monitor_cli.py ai models [--refresh]` affiche les modèles et les données ; `ai doctor` explique pourquoi une IA ne répond pas (variable de la clé non définie, modèle inconnu, quota, réseau) et n'affiche jamais une clé.
- **Routes.** `GET /api/ai/models` (la liste conservée, la vérification et le tableau ; lecture seule) et, depuis cet ordinateur uniquement, `POST /api/ai/models/refresh`, `POST /api/ai/models/test`, `POST /api/ai/models/data` et `POST /api/ai/doctor`.

## IA compatibles

Services hébergés et serveurs locaux dont le moniteur parle déjà le protocole (`openai-compatible`, `anthropic` ou `ollama`). Cette liste est un tableau neutre, pas une recommandation : aucune n'est active par défaut, la clé est TOUJOURS lue dans une variable d'environnement dont vous indiquez le nom (jamais saisie dans un réglage, ni dans un journal, un rapport ou l'API) et le préréglage ne remplit que l'adresse, le nom de cette variable et un modèle d'exemple (modifiable ; rien n'est téléchargé et aucun poids de modèle n'est fourni). Dans les réglages de l'IA, choisissez un préréglage, appuyez sur le bouton de remplissage, vérifiez, enregistrez, puis « Tester la connexion ». La liste est une donnée (`ai_presets.json`) servie en lecture seule sur `GET /api/ai/presets`.

| Nom | Type | Fournisseur | Adresse | Variable de la clé | Modèles d'exemple | Confidentialité | État |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | hébergé | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Anthropic | hébergé | `anthropic` | `adresse par défaut` | `ANTHROPIC_API_KEY` | — | envoyé par internet | compatible par protocole, non testé avec cet outil |
| Google Gemini | hébergé | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| xAI Grok | hébergé | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Mistral | hébergé | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| DeepSeek | hébergé | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Groq | hébergé | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| OpenRouter | hébergé | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Together AI | hébergé | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Fireworks AI | hébergé | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Perplexity | hébergé | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Cohere | hébergé | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | envoyé par internet | adresse lue dans la documentation publique ; compatible par protocole, non testé avec cet outil |
| Ollama | local | `ollama` | `http://127.0.0.1:11434` | aucune (serveur local) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | reste sur cet ordinateur | compatible par protocole, non testé avec cet outil |
| LM Studio | local | `openai-compatible` | `http://127.0.0.1:1234/v1` | aucune (serveur local) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | reste sur cet ordinateur | compatible par protocole, non testé avec cet outil |
| llama.cpp server | local | `openai-compatible` | `http://127.0.0.1:8080/v1` | aucune (serveur local) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | reste sur cet ordinateur | compatible par protocole, non testé avec cet outil |
| vLLM | local | `openai-compatible` | `http://127.0.0.1:8000/v1` | aucune (serveur local) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | reste sur cet ordinateur | compatible par protocole, non testé avec cet outil |
| LocalAI | local | `openai-compatible` | `http://127.0.0.1:8081/v1` | aucune (serveur local) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | reste sur cet ordinateur | compatible par protocole, non testé avec cet outil |
| Jan | local | `openai-compatible` | `http://127.0.0.1:1337/v1` | aucune (serveur local) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | reste sur cet ordinateur | compatible par protocole, non testé avec cet outil |
