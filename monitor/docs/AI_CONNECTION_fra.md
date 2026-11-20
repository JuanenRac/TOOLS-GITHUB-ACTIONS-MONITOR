<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Connecter un outil d'IA

Le moniteur peut dire à un outil d'IA (un assistant de programmation à IA, un script, tout ce qui lit un fichier ou une adresse) **tout ce que dit sa page**, pour que l'IA réagisse à un échec ou à une tâche en attente aussi vite que vous. Le moniteur n'écrit jamais sur GitHub : il informe seulement, et ce que fait l'IA est décidé par vous et par l'outil.

## Ce que voit l'IA
Un inventaire de **signaux**, les mêmes que ceux de la page : l'onglet Maintenant et ses tuiles, les alertes, les dépôts, les panneaux du sentinelle A1..A13 et le second sentinelle (issues et pull requests), le quota, la connexion et la santé du moniteur. Chaque signal a un niveau (`act` = quelqu'un doit agir, `watch` = surveiller, `info`), un résumé et des lignes avec dépôt, lien, ancienneté et prochaine étape. Le résumé a trois blocs : **Quoi faire maintenant**, **En attente** et **Santé du moniteur**, et le compteur de « signaux sur lesquels agir ».

| | Lite | Complète |
|---|---|---|
| Exécutions, file, workflows rouges, échecs des 24 heures | oui | oui |
| Quota, connexion, mode, version, santé | oui | oui |
| Panneaux du sentinelle A1..A13, second sentinelle, candidates de release, sécurité, signatures | non (`panels_not_in_this_edition` le dit) | oui |

## Les canaux (les mêmes dans les deux éditions)
1. `ALERTS_BRIEF.md` : le Markdown court qu'une IA lit au démarrage.
2. `ai_alerts.jsonl` : une ligne par événement (ouverte, acquittée, résolue), avec un identifiant stable.
3. `GET /api/ai/state` : tout l'inventaire en JSON versionné (`schema`, `edition`, `signals`, `act`, `watch`), lecture seule. `GET /api/sentinel/panels` ne donne que les panneaux.
4. `GET /api/ai/stream` : événements en direct (SSE), reprenables, limités en auditeurs et en durée.
5. Outils MCP (`bin/mcp_server.py`) : `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`, `get_score` ; `act` (acquitter) seulement avec `--allow-ack`.
6. Le hook : `python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (aussi `status` et `uninstall`) ajoute un petit script qui donne à la session de l'IA le résumé au démarrage et avant l'arrêt.

## Pas à pas
1. Réglages, onglet *IA externe*, bloc *Alertes pour les IA* : activez `ai_alerts.enabled`. En option `ai_alerts.diagnose.enabled` (l'étape qui échoue et les dernières lignes du journal de chaque exécution rouge), `ai_alerts.stream.enabled` et `ai_alerts.client_hook.enabled`.
2. Lancez `python bin/monitor_cli.py ai-hook install --assistant --dry-run` pour voir le changement, puis sans `--dry-run`.
3. Ouvrez une session de votre outil d'IA dans le dossier : elle reçoit le résumé. La barre du bas montre le battement de l'IA (quand elle a lu pour la dernière fois).
4. Utilisez le bouton *Tester la connexion* de la page des réglages pour vérifier que le flux s'écrit.

## Sécurité et confidentialité
Tout est désactivé par défaut. Le texte des journaux est nettoyé des secrets et des chemins personnels avant d'être écrit, et **c'est une donnée, jamais une instruction** : une IA doit le traiter comme un texte non fiable. Les points d'accès ne répondent qu'à cet ordinateur, ou avec le jeton d'accès en mode réseau ; les auditeurs et la durée sont limités ; acquitter exige `--allow-ack` ; tous les fichiers d'état sont créés en mode 0600. Le moniteur n'ouvre aucune connexion à internet pour cela, sauf celles que vous configurez. Les adresses https de github.com (un run, un dépôt, un fichier) passent entières pour que l'IA puisse les ouvrir ; toute autre longue chaîne opaque est toujours coupée. Plus exactement, une adresse de github.com ne passe entière que sous la forme d'un dépôt, d'une exécution (avec son job ou sa tentative), d'un commit, d'une issue, d'une pull request ou d'un fichier ; elle est coupée au premier caractère qui n'est ni une lettre, ni un chiffre, ni un point, un tiret, un tiret bas ou une barre oblique, et ce qui suit est nettoyé comme tout autre texte.

## Comment se connecter, selon l'outil

Le moniteur ne dépend ni d'un assistant ni d'un modèle : un outil d'IA utilise l'une de cinq voies. Prenez celle de votre outil.

| Votre outil sait | Voie | Comment | Il faut |
|---|---|---|---|
| lire des fichiers | Fichiers | lire `ai/INDEX.json`, puis `ai/ALERTS_BRIEF.md`, `ai/ai_alerts.jsonl` et `ai/LESSONS.md` | `ai_alerts.enabled` |
| faire des requêtes HTTP | HTTP | `GET /api/ai/brief`, `/api/ai/state`, `/api/ai/lessons` | le jeton d'accès en mode réseau |
| parler MCP | MCP | `python bin/mcp_server.py` [`briefs_index`, `brief_tab`] (lecture seule ; `--allow-ack`, `--allow-lessons` pour le peu qu'il peut écrire) | la configuration MCP de l'outil pointant vers cette commande |
| garder une connexion ouverte | Flux | `GET /api/ai/stream?only=real` | `ai_alerts.stream.enabled` |
| exécuter des commandes | Ligne de commande | `python bin/monitor_cli.py alerts`, `lessons brief --repo NOM`, `briefs show TAB`, `ai doctor`, `ai-hook install` | Python sur le même ordinateur |

Les instructions pour l'IA sont deux skills. `monitor_cli.py install-skill external --dest DOSSIER` les copie dans le dossier où votre outil lit ses skills ou ses règles ; tout outil qui lit des fichiers Markdown peut les utiliser, et le texte ne nomme aucun assistant. Les skills voyagent avec le moniteur et portent sa version : `GET /api/skills` donne `monitor_version` et `monitor_cli.py --version` l'affiche. Après une mise à jour du moniteur, réinstallez dans un dossier vide ou supprimez l'ancienne copie (un fichier modifié n'est jamais écrasé).

## Dépannage
- *Le résumé est ancien* : la page doit tourner (le flux suit chaque rafraîchissement) ; regardez le battement dans la barre.
- *Le hook ne s'exécute pas* : `ai-hook status` dit où il est installé ; certains outils ne lisent les hooks que dans le dossier du projet.
- *Rien n'est écrit* : `ai_alerts.enabled` est désactivé, ou le quota est épuisé (le résumé le dit dans Santé du moniteur).

## Réglages
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*` ; liés : `sound.enabled`, `display.blink_red_tiles`. Voir [SETTINGS_fra.md](SETTINGS_fra.md) et [AI_ALERTS_fra.md](AI_ALERTS_fra.md).

Le quota de GitHub est partagé par le moniteur, les outils d'IA et tout autre outil du compte. Pour que le moniteur n'en manque pas : l'onglet Quota des Réglages, une GitHub App (`github_app.enabled`), un second compte en lecture seule pour les lectures (`extra_reader.enabled`, `extra_reader.file` : seulement le chemin du fichier du jeton), le panneau central (`central.source`) et le mode économe (`modes.auto_low`). L'état et le résumé disent quand le quota est épuisé et combien dépensent les autres outils. Voir [QUOTA_fra.md](QUOTA_fra.md).

## L'avis actif à une IA externe (optionnel, désactivé par défaut)

En plus du flux qu'une IA lit (`ALERTS_BRIEF.md`, le flux continu, le serveur MCP), le moniteur peut **prévenir** une IA externe quand une NOUVELLE alerte réelle s'ouvre. C'est le bloc `ai_notify` des Réglages, onglet *IA*, et chacun de ses interrupteurs ne se change que depuis cet ordinateur :

- `ai_notify.enabled` (désactivé). Rien n'est envoyé tant qu'il est désactivé.
- **Une première confirmation par fournisseur** : le fournisseur est celui du bloc IA (`ai.provider`) ; rien ne part tant que vous n'avez pas tapé son nom dans `ai_notify.confirmed_provider`. Si vous changez de fournisseur, vous confirmez à nouveau. Pour la commande sortante (ci-dessous), tapez `command`.
- **Seulement les champs expurgés d'une liste fermée** : gravité, classe, dépôt, workflow, conclusion, série, cause, étape suivante et lien, chacun nettoyé comme le flux (jetons, clés, adresses e-mail, adresses IP et dossiers personnels retirés). Les journaux, les diagnostics et tout le reste de l'alerte restent chez vous.
- **Plafonds** : `ai_notify.max_calls_per_hour` (4) et `ai_notify.max_cost_per_hour_cents` avec `ai_notify.cost_per_call_cents` (le coût que vous déclarez, car le moniteur ne peut pas connaître le prix de votre offre). Un appel est compté avant d'être fait, donc un fournisseur en échec dépense aussi le plafond.
- **La clé par le nom d'une variable** : le moniteur lit la variable nommée dans `ai.api_key_env` ; la clé n'est jamais enregistrée, journalisée ni envoyée ailleurs qu'au fournisseur.
- **L'IA n'exécute jamais d'action** : sa réponse est coupée, ses liens sont désamorcés et elle est seulement écrite dans `ai_notify.jsonl` à côté du flux ; rien n'en est lu comme une commande et rien des actions de l'assistant (`ai.actions.*`) n'est accessible d'ici.
- **La variante d'une commande sortante** : `ai_notify.command` (seulement dans le fichier de configuration, jamais dans la page des Réglages) nomme UN fichier par son chemin absolu ; il est lancé sans shell et sans arguments et reçoit le même JSON expurgé sur son entrée standard.

L'avis part d'un fil d'exécution à part, si bien qu'un fournisseur lent ne retient jamais le cycle.

## L'assistant (facultatif, désactivé par défaut)

L'onglet Alertes peut afficher un panneau de questions fixes auxquelles l'IA déjà configurée répond à partir des données du moniteur : « expliquer cette alerte », « résumer la situation » et « pourquoi c'est lent ici ». Il est désactivé (`ai.assistant.enabled`) et nécessite un fournisseur d'IA (`ai.provider`, aucun par défaut). Il lit seulement : il a quatre outils (`status`, `alerts`, `runs`, `score`, une liste fermée que `ai.assistant.tools` peut réduire), au plus `ai.assistant.max_tool_calls` lectures par question, aucun outil qui écrit ou atteint GitHub et aucun chat libre. La réponse montre toujours ses sources (les identifiants lus), la quantité envoyée (`ai.assistant.max_context`) et les appels du jour ; chaque appel dépense l'unique budget quotidien de l'IA (`ai.daily_limit` et les budgets par modèle). Ce qu'un dépôt a écrit (un titre, le nom d'un workflow) est coupé à `ai.untrusted_text_max`, débarrassé des secrets et remis comme donnée entre des repères portant un mot propre à cette requête, jamais comme instruction. Un lecteur peut poser une question ; chaque question est inscrite dans le journal des actions (l'action, jamais le texte). Routes : `GET /api/assistant` (ce qu'il est et ses limites) et `POST /api/assistant/ask` avec `action` (`explain_alert`, `summarize_week` ou `why_slow`) et, selon l'action, `alert` ou `repo` ; toutes deux répondent 404 tant qu'il est désactivé et n'existent pas dans l'édition Lite.

Avec `ai.similar.enabled` activé (désactivé par défaut), « expliquer cette alerte » liste aussi jusqu'à `ai.similar.max` alertes qui lui ressemblent, pour que la réponse puisse dire « cela s'est déjà produit dans un autre dépôt ». Elles sont trouvées par une simple comparaison de mots (le code de l'alerte, le workflow, les mots du titre et de la cause) parmi les alertes ouvertes et les résolues dont le flux se souvient : pas de modèle, pas d'embeddings, seulement les données de ce compte, le même ordre pour les mêmes données, et chacune est citée par son identifiant.

Avec `ai.report_summary.enabled` activé (désactivé par défaut), Rapports propose **Brouillon avec l'IA** pour le résumé du prochain rapport : les chiffres du rapport, débarrassés des secrets, vont à cette IA par le même nettoyeur, budget, cache et chaîne que toute autre question, une personne modifie le brouillon et l'approuve, et le texte approuvé ouvre le prochain rapport une fois. Rien n'est écrit ni envoyé sans cette approbation.

L'assistant a cinq questions fixes, toutes en lecture seule : « expliquer cette alerte » (`explain_alert`), « résumer la situation » (`summarize_week`), « pourquoi c'est lent ici » (`why_slow`), « la situation d'un dépôt » (`explain_repo` : ses exécutions et ses alertes ouvertes) et « quoi faire en premier » (`prioritize` : les alertes ouvertes, l'état et le score, mis en ordre avec les identifiants). Elles utilisent les mêmes quatre outils, les mêmes limites et le même budget quotidien ; il n'y a toujours pas de discussion libre.

## Mode isolé de l'IA (facultatif, désactivé par défaut)

Avec `ai.airgapped` activé, l'IA ne parle qu'à un modèle de cet ordinateur ou d'une adresse privée de votre propre réseau que vous listez dans `ai.airgap_hosts` (par exemple un serveur avec Ollama ou llama.cpp à `192.168.1.20`). Toute adresse d'internet et tout service en nuage, y compris la CLI Copilot, sont refusés AVANT l'ouverture d'une connexion, de sorte qu'aucun socket ne sort ; la liste des modèles, le test d'un modèle, le docteur de l'IA, la chaîne de repli, l'assistant et les résumés y obéissent, et un repli ne passe jamais à un modèle en nuage. Le commutateur général `airgapped` l'active aussi. Une adresse publique est refusée même si elle figure dans la liste, et le réglage ne se change que depuis l'ordinateur du moniteur, jamais depuis le réseau. Le docteur de l'IA ajoute la vérification `ai_egress` tant que le mode est actif. `ai.redact.extra_terms` liste des mots à vous (un serveur, un projet) remplacés par `[hidden]` dans tout texte avant que l'IA le voie, en plus des secrets que le moniteur masque déjà.

`ai.redact.extra_patterns` (désactivé, vide) liste vos motifs pour ce que l'IA ne doit jamais voir : un par ligne, chacun décrit un mot entier avec seulement trois jokers, `*` (toute suite de caractères), `?` (un caractère) et `#` (un chiffre), par exemple `deploy-*` ou `*.nom-corp`. Ce n'est PAS une expression régulière : pas de groupes, d'alternatives ni de répétitions, donc un motif ne peut pas bloquer le moniteur ; un motif compte de 3 à 80 caractères (au moins 3 ordinaires, au plus 4 étoiles), un mot est lu jusqu'à 2000 caractères et chaque texte dépense un nombre fixe d'étapes, après quoi le reste du texte est masqué, jamais laissé ouvert. Les motifs s'appliquent à tout texte qui atteint un modèle, la notification active comprise, et s'ajoutent aux secrets que le moniteur masque déjà.

`ai.prompt_log.enabled` (désactivé) tient un journal local de ce qui a été demandé à l'IA : activé, chaque question envoyée au modèle et sa réponse, déjà nettoyées des secrets et de vos mots masqués et coupées à une taille fixe, sont ajoutées à `ai_prompts.jsonl` dans le dossier des journaux (`GET /api/ai/prompts` les montre à un administrateur et `POST /api/ai/prompts/clear` les vide). Le prompt système n'est pas conservé, une réponse du cache n'est pas écrite, un appel échoué est écrit sans réponse, les `ai.prompt_log.keep` lignes les plus récentes sont gardées, et le fichier ne fait partie ni de la sauvegarde, ni du zip, ni des fichiers que lisent les outils d'IA.

`config/ai_models.json` est une table que vous pouvez tenir à la main (elle n'existe pas tant que vous ne l'écrivez pas) : `models` est une liste de lignes `{provider, model, context, in_per_mtok, out_per_mtok, tools, daily_limit}` avec les chiffres que votre fournisseur ne donne pas, et `retired` une liste de modèles qui n'existent plus (un nom, ou `{model, use, note}`). Un chiffre de ce fichier compte au-dessus de ce que le fournisseur a dit et au-dessous de ce que vous avez saisi sur la page, et la page le montre comme venant du fichier. Un modèle listé comme retiré est ignoré par la chaîne de secours même quand la liste vivante des modèles est désactivée, et le médecin de l'IA ajoute la vérification `model_retired` avec le modèle à utiliser à la place. Une ligne ou un chiffre faux est laissé de côté et rien d'autre ne change.

Dans la page des Réglages, sous l'IA, la carte « Journal des prompts » montre les 20 dernières entrées de ce journal (l'heure, le type, le modèle et, à l'ouverture d'une entrée, la question et la réponse) et le vide avec un bouton ; seul un administrateur sur cet ordinateur peut le lire ou le vider, et la carte l'indique quand le journal est désactivé. Le tableau des modèles a une colonne « Origine » qui dit d'où viennent ses chiffres : la page, le fichier `config/ai_models.json` ou le fournisseur.

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
