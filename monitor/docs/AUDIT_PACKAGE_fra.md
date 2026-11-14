<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_PACKAGE.md) | [🇪🇸 Español](AUDIT_PACKAGE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](AUDIT_PACKAGE_ita.md) | [🇩🇪 Deutsch](AUDIT_PACKAGE_deu.md) | [🇨🇳 简体中文](AUDIT_PACKAGE_zho.md) | [🇯🇵 日本語](AUDIT_PACKAGE_jpn.md) | [🇵🇹 Português](AUDIT_PACKAGE_por.md)

# Dossier pour l'auditeur

Ce dont un auditeur a besoin pour vérifier le mode équipe, l'exposition réseau et la gestion des secrets de cet outil : une liste de contrôle, les constats des revues précédentes avec leur correction et le test qui la maintient, comment lancer les tests et ce qui reste connu.

## Liste de contrôle de sécurité du mode équipe

- Le mode équipe (`auth.enabled`) est désactivé par défaut ; ne l'activez que derrière HTTPS ou un proxy de confiance (`listen.trusted_proxy`).
- Avec le mode équipe actif et le réseau ouvert, le moniteur ne démarre pas avant l'existence du premier administrateur.
- D'ici là seul l'ordinateur lui-même entre (le premier administrateur y est créé).
- Les jetons pour scripts (`auth.allow_bearer`) sont désactivés par défaut ; une session a besoin du jeton CSRF pour écrire.
- Le processus de chaque compte ne répond qu'à son superviseur (une clé reçue au démarrage).
- Aucun secret n'est écrit dans le journal ni dans les réponses de l'API ; le fichier des réglages est enregistré sous verrou.
- Toute requête qui sort du moniteur (notifications, OpenTelemetry, exporteurs de runners) suit la même règle : aucune adresse privée, aucune redirection vers une adresse privée.

## Constats, corrections et tests

| Constat | Correction | Test |
|---|---|---|
| Avec le mode équipe et sans utilisateur, toutes les routes étaient ouvertes au réseau | Seul l'ordinateur lui-même entre jusqu'au premier administrateur, et le mode réseau ne démarre pas sans lui | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| Le processus d'un compte contournait les contrôles du mode équipe | Il exige la clé de son superviseur à chaque requête | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| L'enregistrement des réglages continuait sans le verrou du fichier après un délai | L'enregistrement est refusé avec un message si le verrou reste pris dix secondes | `test_184_audit_hardening.py::ConfigurationLock` |
| La commande de la sentinelle pouvait être un interpréteur avec des arguments | La commande est une liste dont le premier mot est le chemin complet d'un programme qui n'est pas un interpréteur, sans caractères de contrôle | `test_184_audit_hardening.py::NotifyCommand` |
| Les jetons pour scripts (bearer) étaient actifs par défaut | Désactivés par défaut ; seul un vrai true les active | `test_184_audit_hardening.py::ScriptTokens` |
| Le flux pour les IA était partagé entre les comptes, et actualisation, acquittement et plafond d'avis pouvaient se dépasser | Un flux par compte ; actualisation, acquittement et état prennent le même verrou ; le plafond est réservé en une étape verrouillée | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| La pause du hook d'un outil d'IA n'était pas réservée en une étape ; un exporteur de runner pouvait rediriger le moniteur ; les appels à GitHub qui ne reviennent pas s'accumulaient | La pause est tenue sous verrou ; les redirections sont vérifiées et limitées ; les appels abandonnés sont comptés et plafonnés (`watchdog_max_abandoned`) | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| Un nom terminé par un saut de ligne passait les contrôles des identifiants, dépôts et clés | Chaque contrôle se termine à la fin du texte (`\Z`) | `test_184_audit_anchors.py` |
| L'export OpenTelemetry n'obéissait pas à la règle des requêtes sortantes ; le proxy n'était pas présenté comme une frontière de confiance ; l'échappement de la page n'avait pas de test | L'export passe par la même garde (aucune adresse privée, aucune redirection) ; la frontière est documentée dans l'aide ; un test garde échappé chaque texte de l'API | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| Deux moniteurs pouvaient écouter sur un port ; l'openssl de Git for Windows n'était pas trouvé ; les échecs avalés volontairement ne laissaient aucune trace de leur origine | Le port est pris en exclusivité et un second moniteur refuse de démarrer ; openssl est cherché là où Git for Windows le range ; chaque échec avalé écrit une ligne avec son type et son lieu | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| Les exécutions sans durée (lues par GraphQL) faisaient échouer la sentinelle à chaque cycle | Une durée absente compte pour zéro | `test_186_unfinished_rows.py` |

## Lancer les tests

Depuis le dossier `monitor/` : `python -m unittest discover -s tests`. Les tests n'ont besoin ni du réseau ni d'un jeton GitHub. Les tests de navigateur s'exécutent si Edge, Chrome ou Chromium est installé (ou avec `MONITOR_BROWSER_TESTS=1`). Les fichiers du tableau sont dans `monitor/tests/`.

## Limites connues

- Le proxy de l'environnement (`network.use_proxy`, désactivé par défaut) résout les noms de son côté : la vérification du nom a lieu avant. La garantie forte doit venir du réseau (un pare-feu qui refuse les adresses privées).
- Windows ne peut pas rendre un fichier privé par les seules permissions : les secrets sont chiffrés avec la clé de l'utilisateur là où le système le permet.
- Les tests ne prouvent rien sur un vrai GitHub, un vrai proxy ou un vrai serveur de courrier : ils utilisent des doublures locales.
