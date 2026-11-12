# Contribuer à GitHub Actions Monitor

## Pile technique
- **Langage** : Python 3.11 ou plus récent ; le cœur n'a besoin d'aucun paquet (la vue terminal, `tui.py`, utilise Rich, optionnel ; les tests ignorent ce qui en dépend s'il manque).
- **Interface** : une page web locale (`monitor/actions_monitor.html`) servie sur `127.0.0.1`, plus des outils en ligne de commande.
- **Source de données** : le client officiel en ligne de commande de GitHub, `gh` (appels en lecture seule par défaut).

## Consignes
1. **Les tests d'abord** : `python -m unittest discover -s monitor/tests` doit passer avant une pull request. Hors ligne : les tests n'appellent jamais GitHub. Pour essayer les services réels à la main, utilisez `python tools/manual_check_live.py`.
2. **Huit langues** : tout texte lisible par un utilisateur vit dans `monitor/locales/<lang>.json` pour en, es, de, fr, it, ja, zh et pt (portugais européen). Une nouvelle clé va dans les huit fichiers ; les tests vérifient qu'ils ont les mêmes clés.
3. **Pas de secrets** : par défaut le moniteur ne stocke aucun jeton (il le demande à `gh`) ; l'unique jeton optionnel vit seulement dans le coffre sécurisé du système (`secretstore.py`). N'ajoutez pas de code qui lit, affiche, journalise ou écrit des identifiants ailleurs, et ne commitez jamais un vrai `actions_monitor.json`.
4. **Sûr par défaut** : tout ce qui écrit sur GitHub, lance un programme, ouvre un port réseau ou envoie des données à l'extérieur est désactivé par défaut, a son propre interrupteur dans Réglages > Avancé, demande une confirmation propre et écoute sur `127.0.0.1` sauf si le mode réseau est activé. Une telle fonction vient avec des tests qui prouvent qu'elle refuse sans l'interrupteur, sans la confirmation et sans le jeton, et que rien ne fuit dans un journal.
5. **Petits pas** : une modification par pull request, avec la ligne correspondante dans `CHANGELOG.md`.
6. **Images** : modifiez `docs/architecture.json` ou `docs/structure.json` et lancez `python tools/make_architecture.py` / `python tools/make_structure.py` ; ne modifiez jamais le SVG à la main.
7. **Journal des modifications en huit langues** : chaque nouvelle entrée de `monitor/CHANGELOG.md` reçoit sa traduction dans `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` (mêmes versions et sections ; une entrée pas encore traduite garde le texte anglais sous un avis traduit). `python tools/make_help_index.py --check` et la porte de version échouent si une version manque dans une traduction.

## Rafraîchir un tableau d'état après chaque version

`.github/workflows/dashboard-dispatch.yml` s'exécute quand le workflow `CI` se termine au vert sur `main` (événements push seulement). Si le mainteneur définit le secret optionnel du dépôt `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, il demande à un dépôt de tableau de bord de rafraîchir sa table de versions ; sans le secret il se termine en silence, n'a aucune permission et ne modifie ni ne retarde jamais la CI. La version de `electro-hobby-3d.project.json` doit être égale à `tool_version.py` à chaque version ; un test le vérifie.

- Liste de contrôle de l'aide : l'aide des Réglages (`cfg.h.<clé>`) de chaque nouveau réglage, l'aide de l'onglet modifié, les guides de `monitor/docs/`, les huit langues, l'index d'aide (`python tools/make_help_index.py`) et le journal des modifications.
