# ADR 0001 — L'interface devient une application web locale

- **Statut :** accepté (revue du 2026-10-29, décisions W1 à W19 de la spécification)
- **Date :** 2026-10-29
- **Spécification liée :** [`docs/dev/design/specification-interface-web.md`](../dev/design/specification-interface-web.md)
- **Maquettes :** canevas « Retribution UI Concepts », direction A « Command view »

## Contexte

L'interface de Retribution est une application PySide6 d'environ 20 000 lignes (`qt_ui/`), dont la carte est déjà une application React/Leaflet (`client/`) affichée dans un `QWebEngineView` et alimentée par le serveur FastAPI local (`game/server/`, `[::1]:16880`) et son flux d'événements WebSocket.

La refonte graphique GFX-01 à GFX-04 a changé l'habillage des widgets Qt (thème sombre, police Inter, icônes) mais pas leur disposition : la fenêtre principale reste un empilement de panneaux et de fenêtres modales. L'objectif est une interface moderne et professionnelle, inspirée des RTS matures : carte plein écran, barre de ressources, panneaux contextuels, gros boutons d'action, frise temporelle. Qt Widgets permet difficilement ce rendu (superpositions translucides sur la carte, transitions, mise en page fluide) sans un effort disproportionné.

## Décision

1. **L'interface cible est l'application web `client/`** (React + TypeScript + RTK Query), qui grandit de « la carte » à « toute l'interface ».
2. **Le moteur reste en Python.** `Game`, la génération de mission, la sauvegarde et la simulation ne changent pas de langage. L'interface parle au moteur uniquement par l'API FastAPI (lectures et commandes) et le flux d'événements.
3. **Migration progressive (« strangler fig ») :** la vue web occupe toute la fenêtre Qt ; les écrans sont réécrits un par un ; tant qu'un écran n'est pas migré, la vue web ouvre l'ancien dialogue Qt par les routes `/qt/*` qui existent déjà.
4. **Coquille :** la fenêtre Qt reste la coquille pendant la migration (aucun changement d'installation pour les joueurs). Le remplacement de la coquille (Electron, déjà présent dans `client/`, ou navigateur) est une décision séparée prise en fin de migration.

## Conséquences

- **Positives :** un seul langage d'interface ; la carte et les écrans partagent l'état et le style ; les capacités CSS (superpositions, animations, mise en page fluide) sont disponibles ; les écrans deviennent testables avec Jest/Testing Library ; l'API devient la frontière nette entre moteur et interface.
- **Négatives / coûts :**
  - Il faut une API de commandes complète : aujourd'hui 12 routes seulement modifient le jeu, l'essentiel de la logique d'interface (achats, packages, réglages) vit dans `qt_ui/`.
  - **Accès concurrent à `Game` :** Qt, la simulation (`threading.Timer`) et les routes FastAPI (pool de threads) le touchent sans verrou. Ce risque existe déjà ; il devient central quand toutes les actions passent par l'API. Un mécanisme de sérialisation est un prérequis.
  - Deux interfaces coexistent pendant la migration ; chaque écran migré doit retirer son équivalent Qt pour ne pas maintenir les deux.
  - Les DTO de `game/server/*/models.py` et le client généré (`regenerate-api`) deviennent un contrat à versionner avec soin.

## Alternatives écartées

- **Continuer en Qt Widgets avec un thème plus poussé :** déjà tenté (GFX-01 à 04), le résultat reste « une application de bureau des années 2010 ».
- **Qt Quick / QML :** rendu moderne possible, mais un troisième langage d'interface (QML) en plus de Python et TypeScript, et la carte resterait web.
- **Réécriture complète dans un autre langage (C#, Rust, Godot…) :** coûte la réécriture du moteur ou un pont complexe vers Python, pour un gain visuel équivalent à la solution web.
- **Application web servie dans le navigateur dès maintenant :** possible techniquement, mais retire l'intégration de bureau (dialogues de fichiers, fenêtre unique) avant que l'interface web ne soit complète.
