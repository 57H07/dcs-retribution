# Spécification — Migration de l'interface vers le web (direction « Command view »)

- **Version :** brouillon 1, 2026-10-29
- **Décision d'architecture :** [ADR 0001](../../adr/0001-interface-web-locale.md)
- **Maquettes de référence :** canevas « Retribution UI Concepts », direction A (Command view, Air Wing, Base, Package, New campaign, Settings, After-action report). La direction B est écartée.
- **Branche cible :** `dev` du fork `57H07/dcs-retribution`.

## 0. Objet et conventions

Cette spécification découpe le passage de l'interface Qt Widgets (`qt_ui/`, ~20 000 lignes) à l'application web `client/` en lots livrables indépendamment. Chaque lot devient une ou plusieurs issues GitHub.

- **Identifiants :** `WEB-NN` pour un lot, `WEB-NN.M` pour un sous-lot. Priorités P1 (bloquant pour la suite) à P3 (confort).
- **Blocs :** chaque exigence suit le modèle de la spécification fonctionnelle : **Sources**, **Constat**, **Exigences**, **Critères d'acceptation**, **Dépend de**.
- **Règles communes à tous les lots :**
  1. Le moteur (`game/`) reste la seule source de vérité. Le client n'implémente aucune règle de jeu (coûts, capacités, validité d'une route) : il affiche ce que l'API renvoie et envoie des commandes.
  2. Toute modification de `Game` passe par une **commande** de l'API (§2.4), jamais par un appel direct depuis Qt une fois l'écran migré.
  3. Un écran migré **supprime** son équivalent Qt dans le même lot (ou le rend inaccessible et le marque à supprimer dans le lot suivant). Pas de double maintenance durable.
  4. Les sauvegardes existantes restent chargeables : aucun lot ne change la forme picklée de `Game` sans migration (`__setstate__` ou `game/migrator.py`).
  5. Les textes de l'interface restent en anglais (comme aujourd'hui) ; la traduction est hors périmètre.
  6. Chaque écran a des tests Jest/Testing Library sur ses états (chargement, vide, erreur, nominal) et chaque commande un test pytest côté serveur.
  7. Accessibilité de base : navigation au clavier, libellés sur les boutons-icônes, contraste 4,5:1 sur le texte.

## 1. État des lieux

| Élément | Constat |
|---|---|
| Client | CRA (`react-scripts` 5), React 18, TS 4.8, Redux Toolkit + RTK Query généré depuis l'OpenAPI (`client/src/api/_liberationApi.ts`), Leaflet. Electron déjà en dépendance de dev (`client/main.js`). |
| Intégration Qt | `qt_ui/widgets/map/QLiberationMap.py` charge `client/build/index.html` dans un `QWebEngineView`, paramètre `?server=host:port&theme=`. Pas de `QWebChannel`. |
| API | 14 routeurs, 38 routes ; 12 modifient le jeu (destinations de bases/TGO, points de navigation). 7 routes `/qt/*` ouvrent des dialogues Qt depuis la carte. `X-API-Key` défini (`game/server/security.py`) mais non utilisé. |
| Temps réel | WebSocket `/eventstream`, file `asyncio.Queue` partagée, alimentée par le signal Qt `sim_update` et par les routes. |
| Concurrence | Aucun verrou sur `Game` entre le thread Qt, le minuteur de simulation et le pool de threads FastAPI. `put_nowait` sur une `asyncio.Queue` depuis d'autres threads n'est pas sûr. |
| Qt à migrer | `windows/mission` 4 164 l., `windows/basemenu` 1 714, `windows/newgame` 1 696, `windows/groundobject` 819, `windows/settings` 758, `windows/preferences` 338, fenêtres isolées ~4 300 (dont `QLiberationWindow` 695), `widgets` 3 289. |

## 2. Fondations (WEB-00) · P1

### WEB-00.1 — Chaîne de build Vite + TypeScript 5 · P1

- **Sources :** GFX-05 de la spécification fonctionnelle (absorbé ici).
- **Constat :** CRA n'est plus maintenu ; TS 4.8 limite les bibliothèques récentes.
- **Exigences :**
  1. Remplacer `react-scripts` par Vite ; TypeScript ≥ 5 ; Jest remplacé par Vitest (ou Jest conservé si la migration coûte trop, à trancher en revue, Q3).
  2. `npm run build` produit toujours `client/build/` chargé par `QLiberationMap` ; le mode dev reste `localhost:3000` (ou le port Vite, avec la même logique de bascule dans Qt).
  3. `regenerate-api` continue de fonctionner.
- **Critères d'acceptation :** build, tests et carte identiques à aujourd'hui ; temps de build mesuré avant/après dans la PR.

### WEB-00.2 — Système de design · P1

- **Sources :** maquettes direction A.
- **Exigences :**
  1. Jetons (couleurs, typographie, espacements, rayons) dans un fichier unique : fond `#0B0F12`, panneaux `#12181D`/`#1A2229`, filets `#263039`, texte `#E6EAED`/`#9AA6B0`, accent `#E8A33D`, ami `#7FB8EE`, hostile `#F08A5D`, succès `#6FCB8F`. Couleurs par tâche de mission (DEAD, BARCAP, CAS, CSAR, STRIKE, AEW&C…).
  2. Polices embarquées (pas de dépendance réseau au lancement) : Barlow Condensed (titres, libellés en capitales), Inter (texte), JetBrains Mono (chiffres, heures, coordonnées).
  3. Composants de base : bouton (primaire/secondaire/danger), onglets, interrupteur, champ numérique, curseur, étiquette de tâche, jauge, carte de liste, tableau, panneau latéral, fenêtre modale, notification, info-bulle.
  4. Symboles ami/hostile distincts par la forme (rectangle / losange, convention APP-6) et pas seulement par la couleur.
  5. Thème clair : hors périmètre de la v1 (Q4).
- **Critères d'acceptation :** une page « catalogue » de développement montre chaque composant dans ses états ; tests de rendu.

### WEB-00.3 — Coquille plein écran et navigation · P1

- **Sources :** `qt_ui/windows/QLiberationWindow.py`, `qt_ui/widgets/map/QLiberationMap.py`.
- **Exigences :**
  1. Derrière une option (préférence ou variable d'environnement), la vue web occupe toute la fenêtre Qt ; barre de menus et barres d'outils Qt masquées.
  2. Le client gère la navigation entre écrans (routeur) : `/` vue de commandement, `/air-wing`, `/bases/:id`, `/packages/:id`, `/new-game`, `/settings`, `/debrief`.
  3. Tant qu'un écran n'est pas migré, son entrée ouvre le dialogue Qt existant via une route `/qt/*` (généralisation de l'existant).
  4. L'option est désactivée par défaut jusqu'à WEB-01 inclus, puis activée par défaut.
- **Critères d'acceptation :** basculer l'option ne casse ni la carte ni les dialogues Qt ; tous les menus actuels restent atteignables.

### WEB-00.4 — Accès sérialisé à `Game` · P1

- **Constat :** voir §1 « Concurrence ».
- **Exigences :**
  1. Un point d'entrée unique exécute toute lecture-écriture de `Game` venant de l'API sur un seul fil (verrou global ou exécution sur le thread propriétaire, Q1).
  2. Les événements vers `/eventstream` sont publiés de façon sûre entre threads (`loop.call_soon_threadsafe` ou équivalent).
  3. La simulation (avance rapide) et les commandes ne s'exécutent pas en même temps.
- **Critères d'acceptation :** test de charge pytest (commandes concurrentes pendant un tick de simulation) sans exception ni état incohérent.

### WEB-00.5 — Conventions de l'API de commandes · P1

- **Exigences :**
  1. Lectures en `GET` renvoyant des DTO ; commandes en `POST /commands/<domaine>/<action>` (ou REST par ressource, Q2) renvoyant le résultat ou une erreur métier `4xx` avec message lisible.
  2. Chaque commande publie les événements nécessaires pour que tous les écrans ouverts se mettent à jour (budget, ATO, base…), sans rechargement complet.
  3. Les commandes passent par la même logique métier que les dialogues Qt actuels (extraction de cette logique hors de `qt_ui/` quand elle y vit, par exemple les modèles de `qt_ui/models.py`).
  4. Le client généré est régénéré dans chaque PR qui change l'API.
- **Critères d'acceptation :** un guide court dans `docs/dev/` ; un exemple de commande de bout en bout (test serveur + test client).

### WEB-00.6 — Sécurité de l'API locale · P2

- **Exigences :** activer `X-API-Key` (clé générée au lancement, passée au client par l'URL ou le pont Qt) sur toutes les commandes ; écoute limitée à `::1`/`127.0.0.1`.
- **Critères d'acceptation :** une commande sans clé renvoie 401 ; la carte fonctionne sans configuration manuelle.

### WEB-00.7 — Pont natif · P2

- **Exigences :** les actions qui demandent le système (choisir un fichier de sauvegarde, ouvrir un dossier, ouvrir un lien externe, quitter) passent par un pont unique (`QWebChannel` ou routes dédiées, Q5), remplaçable plus tard par Electron.
- **Critères d'acceptation :** Nouvelle partie, Ouvrir, Enregistrer, Enregistrer sous fonctionnent depuis l'interface web.

## 3. Écrans

### WEB-01 — Vue de commandement (écran principal) · P1

- **Sources :** `QLiberationWindow`, `widgets/QTopPanel.py`, `QBudgetBox`, `QConditionsWidget`, `QIntelBox`, `QFactionsInfos`, `widgets/ato.py`, `simspeedcontrols.py`, `clientslots.py` ; maquette « A · Command view ».
- **Exigences :**
  1. **Barre supérieure :** nom de campagne et théâtre, factions, tour, heure de début de mission, météo (infobulle base des nuages), budget et revenu par tour, équilibre des forces air/sol (ami/ennemi), accès Air Wing, Transfers, Intel, Settings, menu fichier.
  2. **Panneau Packages (gauche) :** onglets « Packages » et « Enemy ATO » ; filtre ; création ; cartes de package (tâche, cible, TOT, vols, alerte pilote manquant) ; sélection synchronisée avec la carte.
  3. **Carte :** la carte actuelle, avec boutons de calques en surimpression (lignes de front, menaces, plans de vol, routes de ravitaillement, portées).
  4. **Inspecteur contextuel :** clic sur une base → fiche flottante (état piste, parking, dépôts, actions Acheter / Unités au sol / Réparer) menant à WEB-02 ; clic sur un TGO → fiche équivalente.
  5. **Frise temporelle :** packages sur l'axe du temps de mission, TOT visibles, curseur d'heure de simulation.
  6. **Actions de tour :** « Begin Campaign » / « End turn » et « Take off » en bas à droite, avec les mêmes confirmations qu'aujourd'hui (pas de pilote joueur, pilotes manquants, TOT dans le passé avec correction automatique) ; contrôles de vitesse de simulation si activés.
- **Commandes à créer :** créer/supprimer un package, passer le tour, lancer la mission (génération du `.miz`), régler la vitesse de simulation, corriger les TOT.
- **Critères d'acceptation :** une partie complète (nouveau tour, planification, génération de mission, attente de résultat) sans ouvrir la fenêtre principale Qt ; parité fonctionnelle listée dans la PR avec `QTopPanel` et le panneau ATO.
- **Dépend de :** WEB-00.1 à 00.5.

### WEB-02 — Gestion de base · P1

- **Sources :** `windows/basemenu/` (onglets Airfield Command, Ground Forces HQ, Intel, Departing Convoys), `UnitTransactionFrame.py`, `NewUnitTransferDialog.py` ; maquette « Base management ».
- **Exigences :** état de la base (piste, parking, dépôts, défense antiaérienne) ; réparations avec coût et délai ; achats par escadron (−/+, coût unitaire, possédés/max) avec récapitulatif (total, budget restant, parking après livraison) ; achats d'unités au sol ; création d'escadron ; convois au départ ; transferts.
- **Commandes :** commander/annuler des appareils ou unités, réparer, créer un transfert.
- **Critères d'acceptation :** mêmes limites qu'aujourd'hui (parking, budget, taille maximale d'escadron) imposées par le serveur, l'interface affichant le refus.
- **Dépend de :** WEB-01.

### WEB-03 — Air Wing · P2

- **Sources :** `AirWingDialog.py`, `SquadronDialog.py` ; maquette « Air Wing ».
- **Exigences :** escadrons groupés par base ; fiche escadron (appareils, pilotes prêts, sorties, pertes, arrivées au prochain tour, tâches autorisées) ; tableau des pilotes avec statut (prêt, abattu en attente de CSAR, prisonnier, blessé, retour prévu), case « joueur » ; transfert d'escadron ; vues Aircraft et Pilots.
- **Commandes :** marquer un pilote joueur, changer les tâches autorisées, transférer, acheter.
- **Dépend de :** WEB-02 (commandes d'achat).

### WEB-04 — Éditeur de package et de vol · P1

- **Sources :** `windows/mission/` (4 164 l. : `QPackageDialog`, `QEditFlightDialog`, `flight/QFlightCreator`, `flight/payload`, `flight/waypoints`, `flight/settings`, `QAutoCreateDialog`), `QRadioFrequencyDialog`, `QTacanDialog`, `QICLSDialog`, `QCallsignDialog` ; maquette « Package and flight editor ».
- **Sous-lots :**
  - **WEB-04.1 Package :** tâche, cible, TOT (saisie et « Earliest TOT »), liste des vols, ajout/suppression, création automatique.
  - **WEB-04.2 Vol — général et pilotes :** type, escadron, taille, démarrage (froid, chaud, piste, air), pilotes et joueurs, indicatif.
  - **WEB-04.3 Emport :** choix de l'emport par défaut ou personnalisé, pylône par pylône, filtrage par date si l'option est active.
  - **WEB-04.4 Route :** carte et tableau des points (altitude, heure, carburant), ajout/suppression/déplacement, recréation, alerte de point dans une zone de menace.
  - **WEB-04.5 Radios, TACAN, ICLS, Link 16 :** les dialogues actuels deviennent des sections du vol.
- **Critères d'acceptation :** les plans de vol générés sont identiques (même mission `.miz`) pour une même saisie avant et après migration, vérifié par un test de comparaison sur une campagne de référence.
- **Dépend de :** WEB-01.

### WEB-05 — Attente de résultat et rapport de fin de mission · P1

- **Sources :** `QWaitingForMissionResultWindow.py`, `QDebriefingWindow.py`, `widgets/QDebriefingInformation.py` ; maquette « After-action report ».
- **Exigences :** écran d'attente (état de la détection de `state.json`, rechargement manuel) ; rapport : verdict, victoires air/sol, pilotes secourus/prisonniers, budget du tour suivant, résultat par package, journal horodaté ; « Accept results ».
- **Critères d'acceptation :** les résultats appliqués sont identiques à ceux du chemin Qt pour un même `state.json`.
- **Dépend de :** WEB-01.

### WEB-06 — Assistant de nouvelle campagne · P2

- **Sources :** `windows/newgame/` (Theater configuration, Faction selection, Campaign options, Generator settings, Introduction/Conclusion), `AirWingConfigurationDialog.py`, `QLiberationCalendar.py` ; maquette « New campaign wizard ».
- **Exigences :** étapes Theater → Factions → Campaign options → Generator → Summary ; liste filtrable des campagnes (théâtre, époque) avec aperçu de carte et description issue du YAML ; choix des factions (recommandées par défaut) ; options et date ; configuration de l'escadre aérienne ; récapitulatif avant génération.
- **Commandes :** générer la partie (paramètres complets), ce qui remplace le chemin de `qt_ui/main.py::create_game`.
- **Dépend de :** WEB-00.7 (fichiers), WEB-03 (composants d'escadron).

### WEB-07 — Réglages et préférences · P2

- **Sources :** `windows/settings/QSettingsWindow.py`, `plugins.py`, `windows/preferences/` ; maquette « Settings ».
- **Exigences :** pages générées depuis les métadonnées de `game/settings/settings.py` (page, section, libellé, aide, type, bornes) plutôt que codées à la main ; recherche sur tous les réglages ; marqueur des valeurs modifiées et réinitialisation par page ; options des plugins Lua ; préférences d'installation (dossiers DCS et Saved Games) et premier lancement.
- **Critères d'acceptation :** tout réglage visible dans Qt l'est dans le web ; un réglage ajouté dans `settings.py` apparaît sans code client.
- **Dépend de :** WEB-00.5.

### WEB-08 — Écrans secondaires · P3

- **Sources :** `PendingTransfersDialog.py`, `windows/intel.py`, `windows/finances`, `windows/stats`, `windows/notes`, `windows/logs`, `windows/infos`, `QUnitInfoWindow.py`, `CareerDialog.py`, `windows/groundobject/` (infos, achat et remplacement de TGO), à propos, liens externes, import de gabarits, Pretense.
- **Exigences :** un écran ou panneau web par fonction, même style ; regroupement possible (Intel + Stats + Finances dans un écran « Rapports », Q6).
- **Dépend de :** WEB-01.

### WEB-09 — Retrait de Qt Widgets · P3

- **Exigences :**
  1. Quand WEB-01 à WEB-08 sont livrés, supprimer `qt_ui/windows` et `qt_ui/widgets` restants ; la coquille Qt ne garde que la fenêtre, la vue web et le pont natif.
  2. Décider (nouvelle ADR) si la coquille reste Qt, passe à Electron, ou si le navigateur suffit, selon le poids de l'installation et l'intégration Windows.
- **Critères d'acceptation :** `qt_ui/` réduit à la coquille ; le test de bout en bout passe sur 4 campagnes.

## 4. Hors périmètre

- Changement du moteur de jeu, des règles ou du format de sauvegarde.
- Traduction de l'interface.
- Thème clair (Q4).
- Jeu à plusieurs commandants simultanés dans le navigateur.
- Envoi de quoi que ce soit au dépôt amont `dcs-retribution/dcs-retribution`.

## 5. Ordonnancement proposé

1. WEB-00.1, 00.2, 00.4, 00.5 en parallèle (fichiers distincts), puis 00.3.
2. WEB-01 (vue de commandement), puis WEB-05 (boucle de tour complète).
3. WEB-04 (le plus gros, en sous-lots parallélisables 04.2 à 04.5 après 04.1) et WEB-02 en parallèle.
4. WEB-03, WEB-07, WEB-00.6, WEB-00.7, puis WEB-06.
5. WEB-08, puis WEB-09.

## 6. Questions ouvertes (à trancher en revue)

| # | Question | Proposition |
|---|---|---|
| Q1 | Sérialisation de `Game` : verrou global réentrant, ou exécution de toutes les commandes sur le thread Qt ? | Verrou global réentrant, simple et indépendant de la coquille (utile pour WEB-09). |
| Q2 | Forme de l'API de commandes : `POST /commands/...` ou REST par ressource ? | REST par ressource, cohérent avec les routes existantes. |
| Q3 | Vitest ou garder Jest après Vite ? | Vitest. |
| Q4 | Thème clair en v1 ? | Non, sombre seulement. |
| Q5 | Pont natif : `QWebChannel` ou routes HTTP ? | Routes HTTP, réutilisables avec Electron. |
| Q6 | Regrouper Intel, Stats et Finances dans un écran « Rapports » ? | Oui. |
| Q7 | Bibliothèque de composants (Radix/Headless UI) ou composants maison ? | Primitives Radix (accessibilité gratuite) habillées par nos jetons. |
| Q8 | Option « interface web » : quand l'activer par défaut ? | Après WEB-01 et WEB-05 (boucle de tour complète). |
| Q9 | Faut-il garder l'interface Qt en secours pendant toute la migration ? | Non : chaque lot retire son écran Qt (règle 3). |
