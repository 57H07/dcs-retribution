# Spécification fonctionnelle — évolutions DCS Retribution

| | |
|---|---|
| **Statut** | Brouillon v0.1, à valider |
| **Date** | 2026-10-25 |
| **Base de code** | branche `dev` @ `49e8067f` (v1.6.0), dépôt officiel `dcs-retribution/dcs-retribution` |
| **Fork de travail** | `57H07/dcs-retribution` |
| **Documents liés** | `docs/dev/design/turnless.md` (feuille de route « temps réel »), `PRD_FEATURE_IDEAS.md` (brainstorm, non versionné) |

## 0. Objet et conventions

Ce document décrit les évolutions retenues pour le fork : correctifs de bugs, persistance et réalisme de la campagne, sauvetage des pilotes éjectés (CSAR), missions de transport et logistique, légende de la carte et refonte graphique de l'interface.

Chaque exigence porte un identifiant (`BUG-xx`, `PER-xx`, `CSAR-xx`, `TRN-xx`, `UI-xx`, `GFX-xx`) et contient :

- **Sources** : issue ou PR GitHub, ou référence au code (`chemin:ligne`, état de `dev` @ `49e8067f`).
- **Constat** : comportement actuel, vérifié dans le code.
- **Exigences** : comportement attendu, numéroté pour pouvoir être testé.
- **Critères d'acceptation**.
- **Priorité** : P1 (à faire en premier), P2, P3.

Règles communes à toutes les évolutions :

1. Toute nouvelle mécanique de jeu est **optionnelle** et pilotée par un réglage. Sa valeur par défaut doit reproduire le comportement actuel, sauf pour les correctifs de bugs.
2. Les sauvegardes existantes restent chargeables. Les nouveaux champs sont initialisés par `__setstate__` ou par la migration de `game/persistency.py` (même schéma que `game/squadrons/squadron.py:85-98`).
3. Chaque PR vise la branche `dev` (`CONTRIBUTING.md`), passe `pytest`, `black --check` et `mypy`, et ajoute une entrée dans `changelog.md`.
4. Quand une PR existe déjà en amont, on part de cette PR (revue, rebase, tests en vol) plutôt que de réécrire.

---

## 1. Correctifs de bugs

### BUG-01 — Les SEAD larguent leurs leurres TALD trop tôt · P1

**Sources :** issue [#192](https://github.com/dcs-retribution/dcs-retribution/issues/192). Commentaire du mainteneur Raffson : le point INGRESS est celui où les tâches d'attaque sont définies, c'est lui qu'il faudrait rapprocher de la cible.

**Constat :**
- Toutes les tâches d'attaque IA d'une SEAD sont attachées au point **INGRESS** : `game/missiongenerator/aircraft/waypoints/seadingress.py:48-56`. La première tâche est un `AttackGroup(weapon_type=Decoy, expend=Expend.All, altitude=alt × 1,5)`.
- Le point INGRESS est placé au point d'entrée (IP) du package (`game/ato/flightplans/waypointbuilder.py:247-287`), qui se trouve entre 5 et 45 NM de la cible selon la doctrine (`game/data/doctrine.py:142-143, 186-187, 230-231`). L'IA peut donc lâcher ses 12 TALD dès l'IP, hors de leur portée de vol plané.
- La tâche « leurres » n'est pas conditionnée à l'emport réel de leurres. Le type `WeaponType.DECOY` existe (`game/data/weapons.py:211`, `resources/weapons/standoff/ADM-141A.yaml:4`) mais n'est lu nulle part.
- Charge par défaut F/A-18C « Retribution SEAD » : 12 × ADM-141A, sans HARM (`resources/customized_payloads/FA-18C_hornet.lua:97-141`).
- Un point « Search » existe déjà plus près de la menace (0,8 × la portée max du SAM si le package emporte des missiles anti-radar ; `waypointbuilder.py:522-574`), mais aucune tâche n'y est attachée.

**Exigences :**
1. La tâche de largage des leurres n'est générée que si au moins un appareil du vol emporte une arme de type `DECOY` (`Flight.any_member_has_weapon_of_type`, `game/ato/flight.py:287-290`).
2. La tâche « leurres » est déplacée de l'IP vers un point situé à une **distance de largage configurable** de la cible (par défaut, la portée utile du leurre moins une marge). Ce point peut être le point « Search » existant.
3. La montée forcée à 1,5 × l'altitude est conservée pour les leurres. Les missiles anti-radar restent sur INGRESS, avec `Expend.All` (comportement de la PR [#562](https://github.com/dcs-retribution/dcs-retribution/pull/562)).
4. Un réglage `Distance de largage des leurres (NM)` est ajouté dans la doctrine de campagne.

**Critères d'acceptation :**
- Test unitaire : un vol sans leurres ne reçoit aucune tâche `Decoy`. Un vol avec leurres reçoit la tâche sur le point de largage, pas sur INGRESS.
- Test en vol : un package F/A-18C « Retribution SEAD » contre un SA-6 largue ses TALD de sorte qu'ils atteignent la zone d'engagement du site, et le site tire sur au moins un leurre.

**Risque :** le comportement de largage de l'IA DCS n'est pas maîtrisé côté Retribution. Il faut valider en vol, et prévoir en repli une tâche `EngageTargetsInZone` centrée sur le SAM (précédent : `seadsweepingress.py:20-31`).

---

### BUG-02 — Des sites AAA reçoivent des radars inadaptés · P1

**Sources :** issue [#901](https://github.com/dcs-retribution/dcs-retribution/issues/901) (un radar Patriot STR placé sur un site de canons de 88 mm). PR [#902](https://github.com/dcs-retribution/dcs-retribution/pull/902) ouverte (classe `AAARadar` dédiée). PR [#951](https://github.com/dcs-retribution/dcs-retribution/pull/951), fermée sans fusion (`fill: false` seul).

**Constat :**
- `resources/layouts/anti_air/AAA_Site.yaml:8-13` : la place radar est `optional: true` avec `unit_classes: [SearchRadar]` et **sans** `fill`. `fill` vaut `True` par défaut (`game/layout/layoutmapping.py:49`), donc la place est remplie avec n'importe quel radar `SearchRadar` de la faction (`game/armedforces/forcegroup.py:70-98`).
- Les radars de SAM (Patriot STR, Hawk SR, 9S15, P-19…) et le radar de conduite de tir SON-9 « Fire Can » partagent la classe `SearchRadar` (`resources/units/ground_units/Fire Can radar.yaml`, `SON_9.yaml`).
- Même défaut probable dans `resources/layouts/anti_air/Cold_War_Flak_Site.yaml:6-11`.

**Exigences :**
1. Un site AAA générique ne reçoit jamais de radar de SAM.
2. Le SON-9 « Fire Can » n'apparaît qu'avec les canons qui l'exploitent (KS-19, presets `resources/groups/KS-19.yaml` et `KS-19_HDS.yaml`).
3. Les sites d'alerte avancée (EWR) ne sont pas affectés.

**Mise en œuvre retenue :** reprendre la PR #902 (classe `UnitClass.AAA_RADAR`, reclassement des deux Fire Can, `fill: false` sur la place radar). Ajouter le test de garde suggéré en revue (les presets KS-19 contiennent bien un Fire Can) et appliquer le même traitement à `Cold_War_Flak_Site.yaml`.

**Critères d'acceptation :** les tests de la PR #902 (`tests/data/test_aaa_radar.py`) passent. Sur une nouvelle campagne avec une faction équipée de Patriot et de canons AAA, aucun site AAA ne contient de radar de SAM.

---

### BUG-03 — Division par zéro dans `add_strike_tasks` · P1

**Sources :** issue [#948](https://github.com/dcs-retribution/dcs-retribution/issues/948). PR [#950](https://github.com/dcs-retribution/dcs-retribution/pull/950), fermée le 2026-09-02 **sans fusion**.

**Constat :** `game/missiongenerator/aircraft/waypoints/strikeingress.py:66` calcule `len(self.group.units) / len(self.waypoint.targets)`. Si une Strike vise un objectif dont toutes les cibles sont déjà détruites, la liste est vide et la génération de mission plante. La partie reste bloquée, car le replanning retombe sur le même objectif.

**Exigences :**
1. Un point de Strike sans cible ne génère aucune tâche d'attaque et ne bloque pas la génération (même garde que la fonction sœur `add_bombing_tasks`).
2. En amont, l'autoplanner ne planifie pas de Strike contre un objectif sans cible vivante. Le motif reste à confirmer : dans le rapport de l'issue, la cible était un dépôt de véhicules (motor pool) pourtant rempli.
3. Bug annexe signalé dans la même issue, à investiguer séparément : noms de pilotes en double dans un escadron après des transferts répétés, et capacité de base incohérente dans la boîte de dialogue de transfert.

**Critères d'acceptation :** un test de non-régression (repris de la PR #950) échoue avant le correctif et passe après. La sauvegarde jointe à #948 génère sa mission sans erreur.

---

### BUG-04 — Appareils qui apparaissent sur une place de parking déjà occupée · P2

**Sources :** issue [#734](https://github.com/dcs-retribution/dcs-retribution/issues/734) (v1.5.0, Golfe Persique : un CH-47 apparaît sur des AH-64 et des A-10 garés, et des hélicoptères s'écrasent juste après le décollage ; sauvegarde jointe). Le mainteneur Starfire13 soupçonne une surcharge du serveur. PR [#740](https://github.com/dcs-retribution/dcs-retribution/pull/740) (« Parking space information improvements »), fermée.

**Constat :** analyse de l'attribution des places en cours (voir l'annexe B, à compléter). Les causes à examiner sont :
- double attribution d'une même place entre les vols actifs et les appareils garés inactifs ;
- différences de gabarit entre hélicoptères et avions ;
- cas particuliers déjà présents dans `game/missiongenerator/aircraft/flightgroupspawner.py:128, 259, 270, 311, 318` (contournements pour Nevatim et Ramon).

**Exigences :**
1. Reproduire le problème avec la sauvegarde de l'issue, en solo puis sur un serveur.
2. Garantir qu'une place de parking n'est attribuée qu'à un seul appareil par mission. Ajouter un test qui vérifie l'unicité des places sur une base saturée.
3. Si la base n'a plus de place compatible, l'appareil démarre sur une autre place libre ou en vol, avec un avertissement dans le journal, plutôt que d'être superposé.
4. Si la cause « charge serveur » est confirmée, documenter les réglages de culling ou de performance qui l'atténuent, et clore l'issue avec ce diagnostic.

**Critères d'acceptation :** la sauvegarde #734 ne produit plus de superposition. Le test d'unicité passe.

---

## 2. Persistance et réalisme de la campagne

### PER-01 — Dégâts persistants sur les unités · P1

**Sources :** issue [#508](https://github.com/dcs-retribution/dcs-retribution/issues/508). TODO dans le code : `game/ato/flight.py:346` (« Support partial kills »).

**Constat :**
- Le script de mission ne remonte que les crashs, les pertes, les kills, les destructions et les captures de base (`resources/plugins/base/dcs_retribution.lua:169-212`, champs écrits aux lignes 42-50). Aucun événement de coup reçu ni niveau de vie n'est enregistré.
- Côté Python, les pertes sont binaires (`game/debriefing.py:112-168, 357-449`). Un appareil ou un véhicule endommagé mais non détruit revient intact au tour suivant.
- Il existe déjà un modèle de réparation à réutiliser : `RunwayStatus` (`game/theater/controlpoint.py:311-350`), avec un compteur de tours de réparation, un coût (`game/config.py:4`) et une réparation automatique (`game/procurement.py:98-125`).

**Exigences :**
1. **Collecte :** en fin de mission (et à chaque écriture périodique de `state.json`), le script enregistre pour chaque unité endommagée son identifiant et son pourcentage de vie restante (`Unit.getLife()` / `getLife0()`). Une nouvelle clé `damaged_units` est ajoutée à `state.json`, et `StateData` la lit.
2. **Paliers configurables** (valeurs par défaut reprises de l'issue) :

   | Dégâts | Effet sur un aéronef | Effet sur une unité au sol ou un navire |
   |---|---|---|
   | 0–19 % | disponible au tour suivant | disponible |
   | 20–49 % | indisponible 1 tour (en maintenance) | inopérante 1 tour |
   | 50–79 % | indisponible 2 tours | inopérante 2 tours |
   | ≥ 80 % | indisponible 3 tours, ou perte (réglage) | détruite, ou inopérante 3 tours (réglage) |

3. Un aéronef en maintenance reste dans l'inventaire de l'escadron, mais ne peut pas être affecté à un vol. Il est affiché comme « en maintenance (N tours) » dans la fenêtre de l'escadron et dans l'inventaire de l'Air Wing.
4. Une unité au sol inopérante apparaît en statique (ou désactivée) dans la mission suivante, avec le statut « endommagé » sur la carte (le symbole militaire SIDC `PRESENT_DAMAGED` existe déjà : `game/theater/theatergroundobject.py:93-102`).
5. La réparation est gratuite et automatique (décompte de tours). Une option permet une réparation accélérée payante, sur le modèle des pistes.
6. Le débriefing affiche une section « Unités endommagées » (camp, type, % de dégâts, indisponibilité).
7. Le réglage global `Dégâts persistants` est désactivé par défaut.

**Critères d'acceptation :**
- Un `state.json` contenant `damaged_units` est lu sans erreur. Un `state.json` ancien (sans cette clé) reste compatible.
- Un F-16 revenu à 35 % de dégâts est indisponible au tour N+1 et disponible au tour N+2.
- Une ancienne sauvegarde se charge avec la fonction désactivée.

**Point ouvert :** la fiabilité de `getLife()` pour les statiques et pour certains mods est à vérifier en vol.

---

### PER-02 — Réparation des infrastructures détruites · P1

**Sources :**
- issue [#247](https://github.com/dcs-retribution/dcs-retribution/issues/247) ;
- issue [#912](https://github.com/dcs-retribution/dcs-retribution/issues/912), fermée comme doublon : réparer après conquête ;
- PR [#680](https://github.com/dcs-retribution/dcs-retribution/pull/680) (réparation des bâtiments) et [#679](https://github.com/dcs-retribution/dcs-retribution/pull/679) (réparation des unités au sol par l'IA), toutes deux fermées le 2026-08-15 sans fusion, faute de rebase ;
- débat sur les délais dans #247 et #680 : Starfire13 juge 4 tours trop court pour une usine, l'auteur de #680 et juanjux préfèrent 4 tours avec une option.

**Constat :**
- Les revenus dépendent du nombre de statiques vivantes d'un bâtiment, multiplié par `REWARDS` (`game/income.py:13-52`, `game/config.py:6-19`).
- Le joueur ne peut réparer que des unités au sol, instantanément, au prix de l'unité (`qt_ui/windows/groundobject/QGroundObjectMenu.py:138-145, 269-284`). Les bâtiments n'ont aucune option de réparation (`theatergroup.py:144-146` exclut les statiques).
- Défaut probable dans `repair_unit` : les lignes 276-281 modifient la liste pendant son parcours (non vérifié à l'exécution).

**Exigences :**
1. Le joueur peut lancer la réparation d'un bâtiment détruit ou endommagé qu'il contrôle (y compris après une conquête, cf. #912), depuis sa fiche sur la carte.
2. Coût = revenu par tour du bâtiment × multiplicateur de coût. Délai = nombre de tours × multiplicateur de délai. Les deux multiplicateurs sont des réglages de campagne (proposition de #247).
3. Valeurs par défaut différenciées par catégorie : piste < dépôt de munitions ou de carburant < usine ou raffinerie. Cela répond à l'objection de Starfire13 dans #247.
4. Pendant la réparation, le bâtiment ne rapporte rien. S'il est frappé pendant les travaux, la réparation repart à zéro, comme `RunwayStatus.damage()`.
5. L'IA adverse répare selon une part configurable de son budget, en priorisant les bâtiments à forte valeur loin du front (logique de la PR #680). Pour les unités au sol (SAM, EWR), elle priorise les radars de recherche et de poursuite (logique de la PR #679).
6. La réparation d'unités au sol par le joueur passe aussi par un délai configurable (`0` = instantané, comportement actuel).
7. Les réglages de budget de réparation sont regroupés dans une section « Gestion de campagne avancée » (proposition de prokop7 dans #679).
8. Correction du parcours de liste dans `repair_unit`.

**Mise en œuvre retenue :** rebaser les PR #680 et #679, retirer les modifications sans rapport (remarque de Druss99), puis ajouter les exigences 2 à 4.

**Critères d'acceptation :** une usine détruite capturée peut être réparée. Elle ne rapporte rien pendant N tours, puis retrouve son revenu. Une frappe pendant les travaux remet le compteur à zéro.

---

### PER-03 — Carrière du pilote joueur · P2

**Sources :** issue [#965](https://github.com/dcs-retribution/dcs-retribution/issues/965). Son auteur, Cozak92, propose de l'implémenter : à contacter pour éviter un doublon. Voir aussi F-30 dans `PRD_FEATURE_IDEAS.md`.

**Constat :**
- `PilotRecord` ne contient que `missions_flown` (`game/squadrons/pilot.py:9-11`). `Pilot` porte un drapeau `player` (`pilot.py:24`).
- Les kills sont attribués aux vols et aux unités, jamais aux pilotes (`game/debriefing.py:150-155, 360-369`).
- La montée en niveau est calculée à partir du nombre de missions (`game/squadrons/squadron.py:121-149`).

**Exigences :**
1. Le joueur peut désigner ou créer son pilote. Les pilotes déjà marqués `player` sont repris.
2. Le carnet de vol enregistre : sorties, sorties de combat, kills air, sol et naval, éjections, sauvetages (lien avec CSAR-01), décès, temps de vol.
3. Les grades et les décorations sont **définis par des données** (YAML par pays ou période), sans valeur codée en dur, avec des conditions d'attribution (par exemple « As : 5 kills air »).
4. Une page « Carrière » est accessible depuis la fenêtre de l'escadron, avec un historique par mission.
5. Aucun effet sur le gameplay : pas de déblocage, pas de bonus, pas de restriction (périmètre de #965).
6. Le modèle de données accepte plusieurs carrières, même si une seule est exposée au départ.
7. Prérequis technique : attribuer les kills au pilote (l'événement KILL porte l'unité initiatrice, qu'il faut relier au pilote du vol).

**Critères d'acceptation :** après une mission où le joueur abat 2 avions, sa page Carrière affiche +1 sortie et +2 kills air. Les données survivent à une sauvegarde suivie d'un rechargement.

---

### PER-04 — Bloquer la reprise d'un appareil crashé · P3

**Sources :** issue [#506](https://github.com/dcs-retribution/dcs-retribution/issues/506). Commentaire de Raffson : `net.force_player_slot` ne fonctionnerait que sur serveur dédié, et le blocage semble impossible en solo.

**Constat :** un joueur qui crashe peut reprendre le même slot dans le même tour, ce qui lui donne des essais infinis pour un seul appareil acheté. Les pertes sont bien décomptées au tour suivant, au point que l'inventaire peut devenir négatif.

**Exigences :**
1. **Solo :** à l'écriture de `state.json`, les pertes d'un slot au-delà de l'inventaire réel sont plafonnées, pour ne plus produire d'inventaire négatif. Un message en vol prévient que l'appareil est perdu pour la campagne.
2. **Serveur dédié (optionnel) :** un script verrouille le slot d'un appareil détruit pour le reste de la mission.
3. Le réglage est désactivé par défaut.

**Note :** cette exigence touche au multijoueur, qui est hors périmètre (§7). Seul le volet solo (exigence 1) est proposé en priorité.

---

### PER-05 — Résolution automatique des combats plus crédible · P2

**Sources :** code `game/settings/settings.py:48-51, 873-884` (option « Resolving combat (WIP) », décrite comme « very rudimentary »). Feuille de route `docs/dev/design/turnless.md` (étapes d'auto-résolution et de simulation des combats gelés).

**Constat :**
- **Combat aérien** (`game/sim/combat/aircombat.py:70-115`) : le camp le plus nombreux gagne (pile ou face en cas d'égalité), tous les perdants sont détruits, et chaque gagnant a 50 % de risque d'être détruit.
- **SAM contre vol** (`defendingsam.py:40-66`) : 50 % de risque que le vol soit détruit, quels que soient le SAM et l'avion.

**Exigences :**
1. Le résultat d'un combat aérien est pondéré par : génération et rôle des appareils (chasseur ou attaque), emport air-air restant, niveau des pilotes (`squadron.py:121-149`), soutien AWACS.
2. Le résultat contre un SAM est pondéré par : type de SAM, présence de SEAD ou d'escorte dans le package, contre-mesures, altitude.
3. Les pertes sont **partielles**, sans élimination totale systématique d'un camp. Les dégâts éventuels alimentent PER-01.
4. Un pilote abattu en résolution automatique suit les règles CSAR-01 (éjection probable).
5. Les coefficients sont dans un fichier de données modifiable, et un test statistique vérifie la cohérence des résultats (par exemple, 4 F-15C contre 2 MiG-21 gagnent dans plus de 90 % des cas).

**Critères d'acceptation :** sur 1 000 tirages simulés, les taux de victoire et de perte respectent les tendances attendues, et les tests passent.

---

## 3. Sauvetage des pilotes éjectés (CSAR)

### CSAR-01 — Un pilote éjecté peut être récupéré avant d'être déclaré mort · P1

**Sources :**
- issue [#104](https://github.com/dcs-retribution/dcs-retribution/issues/104), avec la proposition détaillée de geofffranks du 2026-06-18 : package de sauvetage complet, script MOOSE CSAR, placement du pilote affiné à l'exécution ;
- PR [#929](https://github.com/dcs-retribution/dcs-retribution/pull/929) « Combat Search & Rescue (CSAR) » de Drexyl, ouverte (+5 389 / −46, 61 fichiers), en test par juanjux ;
- TODO `game/theater/controlpoint.py:1464`.

**Constat :**
- Le script de mission ne traite aucun événement d'éjection (`dcs_retribution.lua:170-202`). Les constantes existent dans MOOSE (`resources/plugins/base/Moose.lua:6865, 6898, 6964`).
- Toute perte d'appareil tue le pilote (`game/sim/missionresultsprocessor.py:58-66`), sauf un pilote joueur quand `invulnerable_player_pilots` est actif (`settings.py:130-139`, actif par défaut).
- `PilotStatus` ne connaît que Active, OnLeave et Dead (`game/squadrons/pilot.py:14-18`). Aucun type de mission CSAR n'existe.

**Exigences fonctionnelles :**
1. **Éjection détectée :** le script enregistre l'éjection (position, camp, pilote) dans `state.json`. L'appareil est perdu, mais le pilote n'est **pas** tué.
2. **Nouveaux statuts :** `Disparu (MIA)`, puis `Récupéré` (repos pendant N tours avant le retour en service) ou `Mort`. Prisonnier (`POW`) en option.
3. **Pilote au sol persistant :** le pilote éjecté apparaît sur la carte de campagne avec un compte à rebours de survie, plus court près du front ou en territoire ennemi. Il occupe sa place dans l'escadron tant qu'il est disparu.
4. **Éjection en zone sûre :** au-dessus d'un territoire ami, loin de toute menace, le pilote est récupéré automatiquement au tour suivant (réglage).
5. **Mission CSAR :**
   - nouveau type de mission planifiable par le joueur et par l'autoplanner, pour les deux camps ;
   - éligible pour tout hélicoptère disposant d'une cabine (`cabin_size > 0`) ;
   - escortes possibles : CAP, SEAD, CAS ;
   - l'autoplanner n'envoie pas d'hélicoptère dans une zone SAM active, et le nombre de CSAR par camp et par tour est plafonné.
6. **Jouable :** le vol de sauvetage peut être un slot joueur. En vol, le joueur dispose d'une balise, d'appels MAYDAY, d'un menu F10 et de fumigènes, avec récupération posée ou au treuil, et au treuil obligatoire en mer.
7. **Validation du sauvetage :** le pilote est déposé sur une base ou un FARP ami. L'événement remonte dans `state.json`, puis dans le statut de mission, le débriefing et la fenêtre de l'escadron.
8. **Échec :** si le compte à rebours expire, le pilote passe `Mort` (ou `POW` si l'option est active).
9. **Pilote joueur :** si `invulnerable_player_pilots` est actif, le comportement actuel est conservé. Sinon, le pilote joueur suit les mêmes règles.
10. **Réglages :** activation par camp, probabilité d'éjection, durée de survie, durée de repos, hélitreuillage, sauvetage des pilotes IA, porte cabine ouverte obligatoire, type de démarrage, nombre max de CSAR par camp. Ce sont ceux de la PR #929.
11. **Récompense :** une prime financière optionnelle est versée pour un sauvetage réussi (proposition de #104).
12. **Carrière :** sauvetages et éjections sont comptés dans PER-03.

**Mise en œuvre retenue :** partir de la PR #929, qui couvre déjà les exigences 1 à 3 et 5 à 10. Il faut la rebaser sur `dev`, la tester en vol (pilote joueur, IA, mer, territoire ennemi), puis ajouter les exigences 4, 11 et 12.

**Critères d'acceptation :**
- Un pilote IA abattu au-dessus de l'ennemi est affiché « MIA » sur la carte. Une mission CSAR jouable le récupère, et il reprend du service après N tours.
- Sans sauvetage, il passe « Mort » après le délai.
- Une ancienne sauvegarde se charge avec CSAR désactivé.

---

## 4. Transport et logistique

**Périmètre :** seules les missions de transport (troupes et fret) et la logistique sont retenues, notamment avec le C-130. L'implémentation complète des missions hélicoptère (élingage CTLD généralisé, JTAC transportable, issue [#590](https://github.com/dcs-retribution/dcs-retribution/issues/590)) est **hors périmètre**.

### TRN-01 — Missions de transport jouables · P1

**Sources :** issue [#715](https://github.com/dcs-retribution/dcs-retribution/issues/715). Starfire13 y indique que l'Air Assault et le transport fonctionnent, mais qu'il faut les configurer à la main, et que seules les campagnes 10.7 et 10.8 ont les zones nécessaires.

**Constat :**
- L'autoplanner ne planifie que des Air Assault, pour capturer des bases (`game/commander/tasks/compound/capturebases.py:11-16`, `primitive/airassault.py:12-26`). Aucune tâche ne produit de mission `TRANSPORT`.
- Les vols `TRANSPORT` ne sont créés que par `AirliftPlanner` (`game/transfers.py:271-392`), à la suite d'un transfert d'unités sans liaison routière ou maritime (`transfers.py:632-649`).
- Le joueur ne peut pas choisir `TRANSPORT` dans la liste des types de mission. Aucune cible ne le propose (`game/theater/missiontarget.py:31-47`, `controlpoint.py:1331-1338, 1751-1760`, `qt_ui/widgets/combos/QFlightTypeComboBox.py:24-31`).
- Il faut vérifier s'il est possible d'affecter un pilote joueur à un vol de transport créé par un transfert.
- La PR [#849](https://github.com/dcs-retribution/dcs-retribution/pull/849), ouverte, fait respecter les `mission_types` déclarés dans le YAML des escadrons. Aujourd'hui ils sont ignorés.

**Exigences :**
1. Le joueur peut créer une mission **Transport** depuis une base amie (onglet de la base ou clic droit sur la carte) : origine, destination, fret (unités au sol en réserve ou caisses CTLD) ou troupes.
2. Tout vol de transport généré par un transfert est **jouable** : le joueur peut s'y affecter dans l'ATO.
3. L'autoplanner peut générer des missions logistiques (voir TRN-03) quand l'option `Planifier les missions logistiques` est active.
4. Une mission Transport réussie (atterrissage, puis déchargement CTLD ou atterrissage à destination) livre réellement le fret à la base de destination au tour suivant. Si l'appareil est abattu, le fret est perdu.
5. Le kneeboard de la mission indique la zone d'embarquement, la zone de dépose, le fret et le créneau horaire.
6. Le type de mission respecte les `mission_types` de l'escadron (reprendre la PR #849).
7. Les campagnes sans zones CTLD reçoivent des zones d'embarquement et de dépose par défaut autour des bases et des FARP (zones nommées `<nom> CTLD` : `game/campaignloader/mizcampaignloader.py:735-739`). Sinon, un avertissement explique pourquoi la mission est indisponible.

**Critères d'acceptation :**
- Sur une campagne 10.8, le joueur crée une mission Transport UH-1H entre deux bases amies et la vole.
- Les unités livrées apparaissent à destination au tour suivant.
- Un CH-47 abattu en route fait perdre son fret.

---

### TRN-02 — Assaut aéroporté par C-130 (module officiel C-130J) · P1

**Sources :** PR [#884](https://github.com/dcs-retribution/dcs-retribution/pull/884), ouverte : parachutage CTLD pour les transports à voilure fixe, testé en vol avec le module C-130J. Druss99 et Starfire13 demandent des tests IA. Code : `resources/units/aircraft/C-130J-30.yaml:28` (« Air Assault » commenté, avec le TODO « proper support for paradrops »).

**Constat :** un Air Assault est planifiable pour un C-130J, mais seul le mod Hercules d'Anubis sait larguer des troupes en vol. Avec CTLD, le C-130J officiel et tous les transports IA à voilure fixe arrivent sur la zone sans pouvoir décharger.

**Exigences :**
1. Le C-130J-30 et tout transport à voilure fixe avec cabine peuvent mener un Air Assault par **parachutage**, en vol joueur comme en vol IA.
2. Le joueur largue depuis le menu F10 CTLD « Unload / Extract Troops » en vol. Le largage est refusé au-dessus d'une altitude configurable (3 000 ft AGL par défaut).
3. L'IA est planifiée en passe de largage à 1 000 ft AGL.
4. Le mod Hercules garde son propre système de largage, sans changement.
5. La priorité des C-130 en Air Assault reste inférieure à celle des hélicoptères d'assaut à portée.

**Mise en œuvre retenue :** reprendre la PR #884. La matrice de tests est la suivante (C-130 de base exclu, car non pilotable) :

| Appareil | Joueur | IA |
|---|---|---|
| C-130J-30 (module officiel) | déjà testé en vol | à tester |
| Hercules (mod Anubis) | à tester | à tester |

Vérifier aussi la compatibilité avec le C-47 (question de Starfire13).

---

### TRN-03 — Logistique aérienne C-130 et ravitaillement des bases · P2

**Sources :**
- code `game/transfers.py:242` (Airlift), `:271-392` (AirliftPlanner), `:276` (portée hélicoptère plafonnée à 100 NM), `:770-775, 828-862` (achat automatique d'appareils de transport) ;
- TODO `transfers.py:261` (« Move units to closest base ») et `game/procurement.py:148` (transfert depuis les réserves non tenté) ;
- capacités : `C-130J-30.yaml` (cabine 24, Transport 140), `Hercules.yaml` (cabine 24, Transport 140), `C-130.yaml` (Transport 130, pas de `cabin_size`).

**Constat :** le pont aérien ne sert qu'à exécuter des transferts demandés par le joueur. Il n'existe aucune logique de ravitaillement planifiée, et les C-130 d'une faction restent souvent inemployés.

**Exigences :**
1. **Ravitaillement des bases avancées :** l'autoplanner propose des vols logistiques vers les bases et FOB du front (renforts au sol, réserves), en priorité vers celles qui n'ont pas de liaison routière.
2. Le C-130 (et les autres transports à voilure fixe) est préféré aux hélicoptères au-delà de la portée hélicoptère (100 NM).
3. **Effet mesurable :** une base ravitaillée reçoit ses renforts au tour suivant. Si le vol est intercepté, les renforts sont perdus. Une base coupée de toute liaison est signalée sur la carte.
4. Le joueur peut voler ces missions (TRN-01, exigence 2).
5. Une limite configurable fixe la part de la flotte de transport consacrée à la logistique, pour garder des C-130 disponibles pour les Air Assault.

**Critères d'acceptation :** sur une campagne où une FOB n'a pas de route, l'autoplanner génère un vol C-130 de ravitaillement. Si le joueur le vole jusqu'au bout, les unités arrivent au tour suivant.

---

## 5. Interface et outils

### UI-01 — Légende de la carte de campagne · P1

**Sources :** issue [#54](https://github.com/dcs-retribution/dcs-retribution/issues/54) (jsharpcsa propose d'utiliser le panneau des calques pour une option « afficher la légende »).

**Constat :**
- Aucun composant de légende n'existe dans `client/src`.
- Les symboles militaires sont des codes SIDC générés par le backend (`game/sidc.py`) et rendus par `milsymbol` (`client/src/components/controlpoints/Icons.tsx:5-15`, `tgos/shared.tsx:7-13`, `aircraft/Aircraft.tsx:6-15`).
- Le sélecteur de calques est dans `client/src/components/liberationmap/LiberationMap.tsx:35-127`.

**Exigences :**
1. Un bouton « Légende » sur la carte ouvre un panneau repliable, et l'état ouvert ou fermé est mémorisé.
2. La légende couvre :
   - les symboles de bases (aérodrome, FOB, FARP, porte-avions, LHA) et des objectifs au sol (SAM, EWR, AAA, usine, dépôts…), avec affiliation (ami, ennemi, neutre) et état (intact, endommagé, détruit) ;
   - les vols ;
   - les cercles de menace (bleu `#0084ff`, rouge `#c85050`, `ThreatZone.tsx:10`) et de détection (`#bb89ff`, `#eee17b`, `AirDefenseRangeLayer.tsx:19-25`) ;
   - les routes de ravitaillement (`SupplyRoute.tsx:33-41` : terre ou mer, active au front) ;
   - la ligne de front (`#fe7d0a`) et les liaisons du réseau de défense aérienne (IADS) (`IadsNetwork.tsx:21`) ;
   - les plans de vol, les combats en cours et les mouvements.
3. La légende est générée à partir des **mêmes constantes** que les calques (couleurs et SIDC centralisés), pour ne pas diverger.
4. Elle n'affiche que les éléments des calques actifs.
5. Elle respecte le thème clair ou sombre (GFX-01).

**Critères d'acceptation :** chaque symbole et chaque couleur affichés sur la carte d'une campagne de test a une entrée dans la légende. Un test vérifie que chaque constante de couleur des calques est référencée par la légende.

---

## 6. Refonte graphique de l'interface

**Constat de départ :**
- **Interface bureau :** PySide6 **6.4.2** (`requirements.txt`), 137 fichiers et environ 18 900 lignes dans `qt_ui/`, environ 73 fenêtres ou widgets de premier niveau.
- **Fenêtre principale :** `qt_ui/windows/QLiberationWindow.py`, panneau ATO à gauche, carte et panneau d'info à droite.
- **Thèmes :** deux, « Vanilla » et « DCS World » (`qt_ui/liberation_theme.py:12-23`), en feuilles CSS appliquées au démarrage (`qt_ui/main.py:77-84`). Pas de mode sombre. `resources/stylesheets/style.css` semble inutilisé, et plusieurs widgets fixent leurs couleurs en dur (par exemple `qt_ui/widgets/QFrequencyWidget.py`).
- **Carte :** client web React 18, Leaflet 1.9, milsymbol, Redux Toolkit, TypeScript 4.8, construit avec Create React App, embarqué dans un `QWebEngineView` (`qt_ui/widgets/map/QLiberationMap.py:31-55`).
- **API :** FastAPI (`game/server`) n'expose que les données de carte. Il n'y a aucune route pour les escadrons, les pilotes, le budget ou les réparations.
- **Icônes :** 954 images dans `resources/ui`, dont 701 JPEG.
- **Position des mainteneurs :** une réécriture complète de l'interface en web est un objectif à long terme, coûteux (Raffson dans [#401](https://github.com/dcs-retribution/dcs-retribution/issues/401)).

**Approche retenue :** une modernisation **progressive** en gardant Qt, plutôt qu'une réécriture. On pose d'abord un socle commun (thème, composants, icônes), puis on refond les écrans les plus utilisés. La migration web complète (#401) reste hors périmètre, mais les choix faits ici ne doivent pas la bloquer.

### GFX-01 — Système de design et thèmes clair et sombre · P1

1. Les couleurs, typographies, espacements et rayons sont définis comme **jetons de design** dans une source unique, avec une variante claire et une variante sombre, utilisée à la fois par la feuille de style Qt et par le CSS de la carte web.
2. Le thème sombre est le thème par défaut des nouvelles installations. Les thèmes existants restent disponibles.
3. Le thème se change **sans redémarrage**.
4. Toutes les couleurs en dur dans les widgets sont remplacées par des jetons (inventaire à faire par recherche de `setStyleSheet` et `QColor`).
5. Une police d'interface moderne est intégrée et utilisée partout (pas de dépendance réseau), avec mise à l'échelle correcte en haute résolution.
6. Mise à jour de PySide6 vers une version 6.x récente maintenue, à vérifier avec PyInstaller (`pyinstaller.spec`).

### GFX-02 — Iconographie unifiée · P2

1. Un jeu d'icônes vectorielles (SVG) cohérent remplace les icônes bitmap des menus, barres d'outils et boutons, et se colore selon le thème.
2. Les vignettes d'unités (JPEG) sont conservées, mais affichées dans des cartes uniformes (taille, ratio, coins arrondis, placeholder commun).

### GFX-03 — Refonte des écrans principaux · P2

Les écrans sont refondus dans cet ordre, selon leur fréquence d'utilisation :

1. **Fenêtre principale :** barre supérieure (tour, date et heure, météo, budget, boutons « Prendre le tour » et « Lancer la mission » mis en avant), panneau ATO repliable, panneau d'info redimensionnable, et disposition mémorisée.
2. **ATO et édition de package ou de vol :** listes avec statut coloré, recherche et tri, et édition des waypoints plus lisible.
3. **Air Wing et escadron :** cartes d'escadron avec emblème, effectifs, appareils disponibles, en maintenance (PER-01) ou perdus, pilotes MIA (CSAR-01), et accès à la Carrière (PER-03).
4. **Fiche de base et d'objectif :** onglets homogènes, action « Réparer » visible avec coût et délai (PER-02).
5. **Débriefing :** synthèse visuelle (pertes, dégâts, sauvetages, revenus) au lieu d'une liste brute.
6. **Réglages :** recherche dans les réglages, regroupement « Avancé » repliable (déjà demandé dans la PR #679), description de chaque option.

**Règles pour tous ces écrans :**
- espacements cohérents ;
- états vides explicites ;
- infobulles sur les icônes ;
- navigation clavier ;
- contraste suffisant (WCAG AA).

### GFX-04 — Carte : lisibilité et mode hors ligne · P1

**Sources :** issue [#361](https://github.com/dcs-retribution/dcs-retribution/issues/361). Raffson y confirme que le fond de carte nécessite internet et envisage un fond de secours embarqué, à condition qu'il ne soit pas trop lourd. Tinchus2009 propose une carte basse résolution.

**Constat :** les fonds de carte (imagerie Clarity, Firefly et topographie, `LiberationMap.tsx:36-44`) sont des tuiles téléchargées en ligne (fournisseurs Esri, via `esri-leaflet`). Sans connexion, le fond est vide. Analyse détaillée en cours, voir l'annexe B.

**Exigences :**
1. **Fond de secours hors ligne :** sans réseau, la carte affiche automatiquement un fond embarqué léger, construit à partir des données de théâtre présentes localement (contours terre et mer, relief simplifié). Un bandeau discret indique le mode hors ligne.
2. Le poids ajouté au livrable reste limité. Objectif indicatif : moins de 50 Mo pour l'ensemble des théâtres, à confirmer.
3. Les tuiles consultées en ligne sont mises en **cache** localement et réutilisées hors ligne.
4. Les styles de la carte (sélecteur de calques, infobulles, menus contextuels) utilisent les jetons de GFX-01, en clair comme en sombre.
5. La taille des symboles s'adapte au zoom, et les libellés restent lisibles.
6. La légende (UI-01) fait partie de cette refonte.

**Critères d'acceptation :** application lancée sans réseau, sur une campagne Caucase, la carte affiche le contour des terres et tous les calques de jeu. Après une session en ligne, les zones déjà vues s'affichent hors ligne avec leurs tuiles.

### GFX-05 — Mise à jour technique du client web · P3

1. Migration du build de Create React App (abandonné) vers Vite, et passage à TypeScript 5.
2. Pas de changement fonctionnel. Les tests du client passent.

---

## 7. Hors périmètre

| Sujet | Sources | Raison |
|---|---|---|
| Multijoueur et joueur contre joueur (support OPFOR, opérations de front JcJ) | [#858](https://github.com/dcs-retribution/dcs-retribution/issues/858), [#597](https://github.com/dcs-retribution/dcs-retribution/issues/597) | non prioritaire |
| Missions hélicoptère complètes : élingage CTLD généralisé, JTAC transportable, FARP mobile | [#590](https://github.com/dcs-retribution/dcs-retribution/issues/590), [#238](https://github.com/dcs-retribution/dcs-retribution/issues/238) | seul le transport est retenu |
| Interface 100 % web | [#401](https://github.com/dcs-retribution/dcs-retribution/issues/401) | coût, à reconsidérer après GFX-03 |
| Doctrine IA, interception, BARCAP, naval, porte-avions, ravitailleurs | [#714](https://github.com/dcs-retribution/dcs-retribution/issues/714), [#682](https://github.com/dcs-retribution/dcs-retribution/issues/682), [#107](https://github.com/dcs-retribution/dcs-retribution/issues/107), [#864](https://github.com/dcs-retribution/dcs-retribution/issues/864)–[#866](https://github.com/dcs-retribution/dcs-retribution/issues/866) | non retenus à ce stade |

## 8. Ordonnancement proposé

1. **Lot 1, correctifs :** BUG-03, BUG-02, BUG-01, puis l'investigation BUG-04.
2. **Lot 2, reprise des PR existantes :** CSAR-01 (#929), TRN-02 (#884), PER-02 (#680 et #679), TRN-01 exigence 6 (#849).
3. **Lot 3, nouvelles mécaniques :** PER-01, TRN-01, TRN-03, PER-03.
4. **Lot 4, interface :** GFX-01, UI-01 et GFX-04, puis GFX-02, GFX-03, GFX-05.
5. **En fond :** PER-05 et PER-04.

## Annexe A — Index des sources GitHub

| Réf. | Type | État (2026-10-25) | Exigence |
|---|---|---|---|
| [#54](https://github.com/dcs-retribution/dcs-retribution/issues/54) | issue | ouverte | UI-01 |
| [#104](https://github.com/dcs-retribution/dcs-retribution/issues/104) | issue | ouverte | CSAR-01 |
| [#192](https://github.com/dcs-retribution/dcs-retribution/issues/192) | issue (bug) | ouverte | BUG-01 |
| [#247](https://github.com/dcs-retribution/dcs-retribution/issues/247) | issue | ouverte | PER-02 |
| [#361](https://github.com/dcs-retribution/dcs-retribution/issues/361) | issue (bug) | ouverte | GFX-04 |
| [#401](https://github.com/dcs-retribution/dcs-retribution/issues/401) | issue | ouverte | §6, §7 |
| [#506](https://github.com/dcs-retribution/dcs-retribution/issues/506) | issue | ouverte | PER-04 |
| [#508](https://github.com/dcs-retribution/dcs-retribution/issues/508) | issue | ouverte | PER-01 |
| [#562](https://github.com/dcs-retribution/dcs-retribution/pull/562) | PR | fusionnée | BUG-01 |
| [#679](https://github.com/dcs-retribution/dcs-retribution/pull/679) | PR | fermée, non fusionnée | PER-02 |
| [#680](https://github.com/dcs-retribution/dcs-retribution/pull/680) | PR | fermée, non fusionnée | PER-02 |
| [#715](https://github.com/dcs-retribution/dcs-retribution/issues/715) | issue | ouverte | TRN-01 |
| [#734](https://github.com/dcs-retribution/dcs-retribution/issues/734) | issue (bug) | ouverte | BUG-04 |
| [#740](https://github.com/dcs-retribution/dcs-retribution/pull/740) | PR | fermée | BUG-04 |
| [#849](https://github.com/dcs-retribution/dcs-retribution/pull/849) | PR | ouverte | TRN-01 |
| [#884](https://github.com/dcs-retribution/dcs-retribution/pull/884) | PR | ouverte | TRN-02 |
| [#901](https://github.com/dcs-retribution/dcs-retribution/issues/901) | issue (bug) | ouverte | BUG-02 |
| [#902](https://github.com/dcs-retribution/dcs-retribution/pull/902) | PR | ouverte | BUG-02 |
| [#912](https://github.com/dcs-retribution/dcs-retribution/issues/912) | issue | fermée (doublon de #247) | PER-02 |
| [#929](https://github.com/dcs-retribution/dcs-retribution/pull/929) | PR | ouverte | CSAR-01 |
| [#948](https://github.com/dcs-retribution/dcs-retribution/issues/948) | issue (bug) | ouverte | BUG-03 |
| [#950](https://github.com/dcs-retribution/dcs-retribution/pull/950) | PR | fermée, non fusionnée | BUG-03 |
| [#951](https://github.com/dcs-retribution/dcs-retribution/pull/951) | PR | fermée, non fusionnée | BUG-02 |
| [#965](https://github.com/dcs-retribution/dcs-retribution/issues/965) | issue | ouverte | PER-03 |

## Annexe B — Analyses en attente

- **BUG-04 :** analyse de l'attribution des places de parking (`flightgroupspawner.py`, appareils garés inactifs, hélipads et FARP).
- **GFX-04 :** inventaire des fournisseurs de tuiles et des données de théâtre locales utilisables comme fond hors ligne.
