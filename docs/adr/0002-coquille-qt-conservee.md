# ADR 0002 — La coquille reste Qt, sans Electron ni navigateur

- **Statut :** accepté (WEB-09.2)
- **Date :** 2026-11-02
- **Décision précédente :** [ADR 0001](0001-interface-web-locale.md), décision 4
- **Spécification liée :** [`docs/dev/design/specification-interface-web.md`](../dev/design/specification-interface-web.md), WEB-09

## Contexte

Depuis WEB-09.1, `qt_ui/` ne contient plus que la coquille : la fenêtre, la vue web et le pont natif (918 lignes). L'ADR 0001 avait reporté à la fin de la migration le choix de la coquille définitive : garder Qt, passer à Electron ou laisser le navigateur du joueur afficher l'interface. Les critères fixés sont le poids de l'installation, le démarrage et l'intégration à Windows.

## Décision

1. **La coquille reste Qt** (`QWebEngineView` dans une `QMainWindow`).
2. **Le paquet est allégé** des modules Qt que la coquille ne charge pas, ce qui lui retire son principal défaut.
3. **Le reste d'Electron dans `client/` est retiré** : il n'a plus de cas d'usage et il entretient l'idée d'une migration en cours.

Qt n'est pas le meilleur sur chaque critère, mais c'est le seul candidat qui ne demande aucun nouveau développement et aucun nouveau processus. Une fois allégé, son poids rejoint celui d'Electron, et quelques secondes de démarrage ne pèsent pas pour une application lancée avant une session de jeu. Electron et le navigateur coûteraient un travail réel sans rien apporter au joueur.

## Mesures

Paquet `pyinstaller` de `dev` après WEB-09.1, sur Windows 11, avec Qt 6.11.2 (Chromium 140) et Electron 39.8.7 (Chromium 142). Temps médian de 3 lancements après un lancement à froid écarté, de la création du processus à l'affichage de la barre d'application.

| | Qt actuel | Qt allégé | Electron | Navigateur |
|---|---|---|---|---|
| Sur disque | 805 Mo | **542 Mo** | ≈ 594 Mo (estimé) | 268 Mo (estimé), sans le navigateur |
| Archive `.zip` | 356 Mo | **271 Mo** | ≈ 288 Mo (estimé) | 158 Mo (estimé) |
| Démarrage jusqu'à l'interface | 3,4 s | 3,4 s | moteur 1,6 s, vue 0,5 à 0,8 s | moteur 1,6 s, vue non mesurée |
| Mémoire (RSS cumulée) | 446 Mo | 445 Mo | ≈ 540 Mo | ≈ 170 Mo, plus l'onglet |
| Nouveau code et chaîne de build | aucun | filtre du `.spec` | important | moyen |

Limites de ces chiffres, à garder en tête :

- **Le démarrage n'est pas strictement comparable.** Les colonnes Qt mesurent le paquet complet. Le moteur a été mesuré seul dans le venv, et la vue Electron seule face à un serveur déjà lancé (3,4 s lors de son lancement à froid). Aucun paquet Electron complet n'a été construit.
- **Les poids Electron et navigateur sont des sommes.** Ils additionnent le paquet sans PySide6 (268 Mo, 158 Mo compressés) et, pour Electron, sa distribution non allégée (326 Mo, 130 Mo compressés).
- **Les mesures sont faites hors écran**, sans mesure de l'affichage réel. La RSS cumulée compte plusieurs fois la mémoire partagée entre processus.
- **Le Qt allégé a été vérifié à l'écran** une fois construit depuis `pyinstaller.spec` : la fenêtre, l'interface, le dialogue de dossier et le dialogue de fermeture s'affichent. Les chiffres de temps et de mémoire viennent d'une copie allégée équivalente.

## Options écartées

### Electron

Le gain de démarrage est réel mais faible à l'échelle d'une session de jeu, et le poids allégé est équivalent. En contrepartie :

- **Deux processus à faire vivre ensemble** : Electron et le moteur Python doivent se lancer, se surveiller et s'arrêter ensemble, y compris en cas de plantage. Aujourd'hui, un seul processus les contient.
- **Le pont natif s'inverse** : le moteur appelle `NativeBridge` directement. Avec Electron, il faudrait un canal de Python vers Electron pour chaque dialogue de fichier, attendre la réponse sans tenir le verrou du jeu, et réécrire `qt_ui/nativebridge.py` en JavaScript.
- **Deux chaînes de build** : `pyinstaller` et un empaqueteur Electron, à synchroniser à chaque version.
- **Un langage de plus côté bureau**, alors que l'ADR 0001 visait à en réduire le nombre.

Le `client/main.js` existant ne réduit pas ce travail : il ne lance pas le moteur, ne fournit ni la clé d'API ni l'adresse du serveur, et n'implémente aucun pont natif.

### Navigateur du joueur

C'est de loin le plus léger, mais il retire ce qu'une page web ne peut pas faire et que le jeu exige :

- **Fermeture non maîtrisée :** fermer l'onglet n'arrête pas le moteur, et une page ne peut pas proposer « Enregistrer, ne pas enregistrer, annuler » avant de se fermer. Or c'est à l'arrêt propre de l'application que `MissionScripting.lua` est restauré dans l'installation DCS du joueur. Sans fenêtre, il faudrait au minimum une icône de zone de notification, donc garder une partie de la boîte à outils native.
- **Dialogues de fichiers :** le moteur lit et écrit des sauvegardes par chemin. Une page web n'obtient pas le chemin d'un fichier choisi, donc ces dialogues devraient être affichés par un autre moyen côté Python.
- **Serveur à compléter :** le client est aujourd'hui chargé depuis le disque. Le serveur devrait le servir lui-même et la politique CORS changerait.
- **Plusieurs onglets et navigateurs :** deux onglets piloteraient la même campagne, et l'interface devrait être testée sur plusieurs moteurs de rendu au lieu d'un seul.

## Conséquences

- **Positives :** rien à migrer pour les joueurs, un seul processus, un démarrage et un pont natif déjà en place. La carte garde son cache de tuiles persistant (GFX-04.3).
- **Négatives :**
  - La vue web suit le Chromium embarqué par Qt, ici en retard de deux versions majeures sur Electron. Le client ne doit donc pas dépendre de fonctions web très récentes.
  - PySide6 reste la plus grosse dépendance du paquet, même allégé (274 Mo sur 542 Mo).
  - L'allégement devra être revérifié à chaque mise à jour de Qt, car une DLL retirée à tort ne se voit qu'au lancement du paquet.
- **Réversibilité :** cette décision reste peu coûteuse à revoir. Le moteur ne connaît la coquille que par `NativeBridge` et `gamesession`, et la coquille tient en moins de 1 000 lignes.

## Quand rouvrir cette décision

- Le retard de Chromium dans Qt bloque une fonction dont le client a besoin, ou pose un problème de sécurité.
- Retribution doit tourner sans fenêtre, par exemple sur un serveur dédié avec l'interface sur une autre machine. Le navigateur redeviendrait alors le bon candidat.

## Mise en œuvre

Faite avec cette décision : `pyinstaller.spec` filtre les modules Qt inutiles, et `client/main.js`, le script `npm run electron` et les dépendances `electron`, `electron-is-dev`, `electron-window-state` et `wait-on` sont retirés.
