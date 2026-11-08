# Feuille de route

Des idées qui n'ont pas tenu dans la version actuelle, sans ordre promis. Ce sont des directions, pas des engagements ; une issue ou une pull request est la meilleure façon d'en faire avancer une.

## Fait dans la 1.6.4

Tests d'isolation de l'édition lite et de la démo, aucune requête réseau quand la vérification de version est désactivée ou l'installation isolée, un README qui commence par le choix du lanceur, `--doctor --json`, une barre persistante pour le mode réseau, l'aide et ses documents en huit langues, et les fonctions optionnelles (mode réseau, un jeton conservé par le moniteur, actions sur GitHub, `act`, copie locale des artefacts, runners auto-hébergés, OpenTelemetry, FinOps par étiquettes de job) ; voir le journal des modifications et `ADVANCED.md`.

## Prochainement

Ce que la 1.6.4 n'a pas atteint, et pourquoi :

- **Plusieurs propriétaires dans une page** : le moniteur identifie un dépôt par son seul nom (exécutions, sentinelle, cache, exports) ; deux propriétaires ayant un dépôt du même nom se mélangeraient. Les organisations sont listées et chacune est surveillée par son propre moniteur (`github_owner`). Le faire dans une page demande le propriétaire dans chaque identifiant.
- **Le rapport de facturation avec un compte qui peut le lire** : la vraie réponse pour un compte sans la portée `user` est « introuvable » et le moniteur retombe sur l'estimation (vérifié) ; les chiffres eux-mêmes n'ont pas été comparés à un compte de facturation.
- **Les prix des gros runners** de `quotas.json` viennent de la mémoire de la grille tarifaire publique et sont marqués non vérifiés ; comparez-les à la page de facturation de GitHub et modifiez le fichier.
- **`gh copilot`** : ses options se vérifient avec `gh copilot -- --help`, qui exige la ligne de commande Copilot ; elle n'est pas installée ici, donc elles restent non vérifiées.
- **Notifications, webhook, Enterprise Server et exemples de service** face à des services réels : `tools/manual_check_live.py` les vérifie à la main ; ils demandent vos canaux et hôtes, ils n'ont donc pas été lancés ici.
- **L'application de terminal** modifie les réglages simples et montre l'état de l'IA ; l'explication d'un workflow rouge précis et l'édition des listes et tables restent dans la page.
- **Une vérification de nouvelle version qui télécharge ou installe** : jamais ; le moniteur ne fait que le dire.

## Plus tard

- **Plus d'adaptateurs de notification** : ntfy, Microsoft Teams et e-mail via un relais local.
- **Plusieurs comptes dans une page** : aujourd'hui chaque compte tourne dans son propre moniteur.
- **Télémétrie matérielle des runners** via un agent : aujourd'hui seul un point d'accès optionnel de node exporter est lu.

## Idées qui demandent d'abord une décision

- Un écran de connexion pour la page, afin que le mode réseau n'exige plus de saisir une fois le jeton d'accès. Aujourd'hui la réponse est le jeton d'accès et, pour Internet, un reverse proxy avec authentification (voir `monitor/docs/DEPLOYMENT.md`).
- Lire dans la page les journaux d'une étape en échec, avec le même nettoyage que l'assistant IA.
