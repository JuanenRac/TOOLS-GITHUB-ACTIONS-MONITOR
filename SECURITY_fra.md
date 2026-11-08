# Politique de sécurité

## Signaler une vulnérabilité

Signalez les problèmes de sécurité en privé à `electrohobby3d@gmail.com` (ou par un avis de sécurité privé de ce dépôt) et n'ouvrez pas d'issue publique.
Les signalements utiles sont : un moyen d'atteindre la page web locale depuis une autre machine, un moyen de faire écrire le moniteur hors de son propre dossier, un moyen de lire un jeton
ou un fichier privé via la page ou le point d'accès des métriques, ou une injection par un nom de dépôt, un nom de workflow ou une ligne de journal.

## Points de conception sur lesquels vous pouvez compter
- La page web et le point d'accès optionnel des métriques n'écoutent que sur `127.0.0.1` et refusent les requêtes dont l'`Host` ou l'`Origin` n'est pas local. Le mode réseau optionnel (désactivé par défaut) ajoute un jeton d'accès pour chaque requête, une liste de noms d'hôte acceptés et un avertissement persistant.
- Par défaut le moniteur ne stocke ni n'affiche de jetons ; il appelle votre propre client `gh` authentifié. Le jeton optionnel conservé par le moniteur vit dans le coffre sécurisé du système et n'est jamais écrit dans un réglage, un journal ni une réponse.
- Tout ce qui écrit sur GitHub ou lance un programme est désactivé par défaut, chaque action est confirmée séparément avec un jeton à usage unique, et l'assistant IA ne peut en lancer aucune.
- La page de configuration n'écrit qu'une liste fixe de clés, validées, après avoir enregistré une copie de sauvegarde.
