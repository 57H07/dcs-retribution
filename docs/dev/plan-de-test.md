# Plan de test en jeu (DCS) — branche `dev`

Ce plan couvre ce que les tests automatiques ne peuvent pas vérifier : le rendu réel de l'application, et le comportement dans DCS. Il reprend après la migration vers l'interface web (décision W19 de [la spécification](design/specification-interface-web.md)).

Chaque case renvoie à la PR qui a introduit le changement (`#NN` sur `57H07/dcs-retribution`). Si une case échoue, notez la PR, la campagne et le tour, et joignez `logs\retribution.log`, la sauvegarde et le `state.json`.

**Par où commencer :** §1 valide le paquet en une vingtaine de minutes, sans voler. Faites-le en premier : s'il échoue, le reste du plan ne vous apprendra rien de plus.

---

## 0. Préambule : lancer le programme

### 0.1 Construire le paquet

Depuis la racine du dépôt, à refaire après chaque `git pull` :

```powershell
cd F:\_Projets\Jeux\DcsRetribution
cd client; npm run build; cd ..
.\venv\Scripts\python.exe -m PyInstaller pyinstaller.spec --noconfirm
```

Si le `git pull` touche `requirements.txt` ou `client/package.json`, lancez d'abord `.\venv\Scripts\python.exe -m pip install -r requirements.txt` et `cd client; npm ci; cd ..`.

### 0.2 Lancer

- **Paquet (à privilégier) :** double-cliquez sur `dist\dcs-retribution\retribution_main.exe`, ou lancez-le depuis son dossier. Le journal est alors dans `dist\dcs-retribution\logs\retribution.log`.
- **Depuis les sources :** à la racine du dépôt, `$env:PYTHONPATH = "."; .\venv\Scripts\python.exe qt_ui\main.py`. Le journal est alors dans `logs\retribution.log`.

Les chemins `resources\`, `client\build` et `logs\` sont relatifs au dossier de lancement. Gardez le journal ouvert pendant les tests ; il se lit aussi dans **Help → Show logs**.

### 0.3 Avant de commencer

- **Copiez vos sauvegardes** (`Saved Games\DCS\Retribution\`) : une partie de ces tests modifie des campagnes.
- Retribution remplace `<DCS>\Scripts\MissionScripting.lua` au démarrage (nécessaire à l'export de `state.json`) et le restaure à la fermeture. Laissez-le ouvert pendant que DCS tourne, et quittez-le par sa fenêtre ou par **File → Exit**.

### 0.4 Boucle d'un tour

1. **File → New game** : l'assistant crée la campagne (théâtre, factions, options, générateur, résumé). **Generate campaign**, puis la configuration de l'air wing, puis **Start campaign**. Réglez ensuite **Campaign → Settings** (§2).
2. **Begin Campaign** lance le premier tour ; ensuite, **End turn** passe un tour sans voler.
3. Clic droit sur une cible de la carte pour planifier un package, puis **Take off**. Retribution génère `Saved Games\DCS\Missions\retribution_nextturn.miz` et ouvre l'écran d'attente.
4. Dans DCS : **Mission → ouvrir `retribution_nextturn.miz`**, volez, puis quittez la mission (Échap → Quitter). DCS écrit `state.json`.
5. De retour dans Retribution, l'écran d'attente détecte `state.json` et ouvre le rapport (**Review results** s'il ne s'ouvre pas seul, **Load state.json** si DCS l'a écrit ailleurs). **Accept results** valide le tour, **Continue** revient à la carte.
6. Sauvegardez souvent (**Ctrl+S** ou **File → Save**), surtout avant un test destructif.

> Astuce : pour les tests qui ne demandent pas de voler, utilisez l'avance rapide ou la résolution automatique. Pour aller vite dans DCS, passez en accéléré (Ctrl+Z) et activez l'invulnérabilité, sauf quand un test demande de l'éteindre.

---

## 1. Validation du paquet et de l'interface (sans voler)

Ces cases n'ont jamais été vérifiées à la main depuis le retrait de Qt.

### Coquille et paquet — #175, #176
- [x] Le `.exe` démarre : l'écran de démarrage s'affiche, puis la fenêtre avec le titre `DCS Retribution - v…`, sans fenêtre d'erreur.
- [x] La dernière sauvegarde se recharge seule, et le titre affiche la campagne et le fichier.
- [x] **File → Open…** : le dialogue Windows s'ouvre, une **ancienne sauvegarde** se charge et la carte se recentre sur son théâtre.
- [x] Un tour passe (**End turn**), puis la carte et la barre du haut se mettent à jour.
- [x] **Ctrl+S** enregistre sans dialogue quand la campagne a déjà un fichier. **File → Save as…** ouvre le dialogue Windows et le titre change.
- [x] **File → Exit** propose d'enregistrer : **Cancel** laisse l'application ouverte ; **No** la ferme sans écrire ; **Yes** enregistre puis ferme (vérifiez la date du fichier).
- [x] La croix de la fenêtre pose la même question.
- [ ] Après la fermeture, `MissionScripting.lua` est restauré dans l'installation DCS, et aucun processus `retribution_main.exe` ne reste dans le gestionnaire de tâches.
- [ ] Une fenêtre redimensionnée retrouve sa taille et sa position au lancement suivant.
- [ ] Un deuxième lancement pendant que le premier tourne n'ouvre pas de seconde fenêtre.
- [ ] **File → Preferences** : les boutons de choix de dossier ouvrent le dialogue Windows, et un changement de dossier est conservé après redémarrage.
- [ ] Une mise à l'échelle Windows de 100 %, 150 % et 200 % ne coupe aucun texte.
- [ ] Les liens du menu **Help** (Discord, GitHub, Online manual…) s'ouvrent dans le navigateur du système.
- [ ] Copié ailleurs (autre chemin, pas de venv actif), le dossier `dist\dcs-retribution` démarre aussi. Il pèse environ 540 Mo, et 270 Mo une fois compressé.

### Premier démarrage — #175
Renommez temporairement `%LOCALAPPDATA%\DCSRetribution\retribution_preferences.json`, puis remettez-le en place à la fin.
- [ ] L'écran web de premier démarrage demande les dossiers de DCS et le fichier `MissionScripting.lua` n'est remplacé qu'après acceptation.
- [ ] Une ancienne préférence `"web_ui": false` dans ce fichier est ignorée : l'interface web s'ouvre.

### Écrans web
Sur une campagne en cours, ouvrez chaque écran et notez ce qui manque ou s'affiche mal.
- [ ] **Barre du haut :** budget, météo, équilibre des forces, tour, **Begin Campaign** ou **End turn**, **Take off**.
- [ ] **Panneau Packages** et **Enemy ATO**, avec **Edit** et **Delete** ; **frise temporelle** en bas.
- [ ] **Inspecteur de carte :** un clic sur une base ou un site ouvre le panneau, et ses actions mènent aux bons écrans. (#175)
- [ ] **Écran de base :** Airfield command, Ground forces HQ, Intel, Departing convoys, **Actions**, **Set radios**.
- [ ] **Éditeur de package :** clic droit sur chaque type de cible (base, site, ligne de front, pilote abattu), **Auto-create**, **Add flight**, puis General, Route, Payload, Pilots, Radios & TACAN.
- [ ] **Air Wing :** liste, fiche d'escadron, onglet des pilotes, **Show enemy**. Avec « Enable Air Wing adjustments », **Air wing adjustments**.
- [ ] **Campaign :** Transfers, Stats, Notes, Reports (Intel, Stats, Finances), Info panel, Pilot career, Last debriefing.
- [ ] **Fiche de site** et **fiche d'unité**, avec **Buy / Replace** et **Disband**.
- [ ] **Tools :** Generate a Pretense campaign puis, sans recharger, un tour qui passe ; Import layouts. (#175)
- [ ] **Help :** Keyboard shortcuts (`?`), Show logs, About DCS Retribution.
- [ ] **Raccourcis :** `N`, `?`, Échap et les touches de couches. Ils ne se déclenchent pas pendant la saisie dans un champ.
- [ ] Cliquer sur un vol de la carte le sélectionne dans le panneau Packages. (#175)

### Simulation et fin de campagne — #175
Lancez en sources avec `--show-sim-speed-controls` pour la première case.
- [ ] Les boutons de vitesse font avancer l'horloge. Après **End turn**, l'horloge repart de la nouvelle heure de mission, en pause.
- [ ] Après un **Abort mission**, la vitesse et l'horloge repartent bien, et on peut relancer **Take off**.
- [ ] Sur une campagne où les motorpools sont activés et mal placés, la fenêtre **Campaign problems** les liste une seule fois.
- [ ] **Victoire ou défaite** (par exemple avec le cheat de capture de base) : la fenêtre **Victory!** ou **Defeat!** s'affiche. **New campaign** ouvre l'assistant. **Not now** laisse la carte visible, et **End turn** comme **Take off** sont alors refusés avec un message.

### Carte et légende — #61, #81, #88, #92
- [ ] Le bouton **Legend** ouvre le panneau. Cocher ou décocher une couche ajoute ou retire ses entrées. (#61)
- [ ] Chaque symbole et chaque couleur visible sur la carte a son entrée dans la légende. (#61)
- [ ] Le sélecteur de couches, les boutons zoom, règle et légende, les infobulles et le bandeau hors ligne ont un contraste suffisant. (#92)
- [ ] Du zoom théâtre au zoom aérodrome, les symboles restent lisibles et les étiquettes ne recouvrent pas le symbole. (#81)
- [ ] **Hors ligne, Caucase** (réseau coupé avant le lancement) : contours terre/mer, toutes les couches de jeu et le bandeau « hors ligne » sont visibles. (#81, #88)
- [ ] Après une session en ligne, les zones déjà vues s'affichent hors ligne, au mieux, grâce au cache HTTP. (#81)
- [ ] **Hors ligne, Malouines** : l'image précalculée s'affiche, alignée avec les couches de jeu (aérodromes sur la côte). (#88)

### Ligne de commande — #95
- [ ] `python qt_ui\main.py new-game resources\campaigns\TblisiGap.yaml --squadrons-start-full` crée une partie sans planter.

---

## 2. Campagne de test et réglages

Les nouvelles mécaniques sont **désactivées par défaut** (règle 1 de la spec), sauf la dépense du surplus par l'IA. Pour les tester, créez une campagne dédiée, par exemple **TblisiGap** (Bluefor Coldwar contre Russia 1975, avec hélicoptères et FARP) ou **WRL_Kutaisi2Vaziani** (USA 2005 contre Russia 1990), et activez dans **Campaign → Settings** (la recherche en haut de l'écran trouve chaque réglage) :

| Page / section | Réglage | Valeur de test |
|---|---|---|
| Campaign Management / General | Persistent damage | ✔ |
| Campaign Management / General | Persistent damage: write off heavily damaged aircraft | au choix |
| Campaign Management / General | Persistent damage: paid accelerated aircraft repair | ✔ |
| Campaign Management / General | Persistent damage: heavily damaged ground units are destroyed | ✔ (défaut) |
| Campaign Management / General | Persistent damage: allow paid accelerated repair of ground units | ✔ |
| Campaign Management / Pilots and Squadrons | Enable CSAR for the player coalition / enemy coalition | ✔ / ✔ |
| Campaign Management / Pilots and Squadrons | Recover pilots who come down in a safe zone | ✔ |
| Campaign Management / Pilots and Squadrons | CSAR rescue bounty ($M) | 50 |
| Campaign Management / Pilots and Squadrons | Unrescued pilots can be taken prisoner | selon le test |
| Campaign Management / Pilots and Squadrons | Turns a downed pilot survives | défaut |
| Campaign Management / Flight Planner Automation | CAS escort for CSAR near enemy ground forces | ✔ |
| Campaign Management / Repairs | Ground unit repair delay (turns) | 2 |
| Campaign Management / HQ Automation | Plan logistics missions | ✔ |
| Campaign Management / HQ Automation | AI spends its surplus budget filling squadrons | ✔ (défaut) |
| Advanced Campaign Management / Building Repairs | Enemy AI repairs buildings | ✔ |
| Advanced Campaign Management / Ground Unit Repairs | Enemy AI repairs SAM and EWR sites | ✔ |
| Mission Generator / Gameplay | CSAR rescues AI-controlled downed pilots | ✔ |
| Mission Generator / Gameplay | Decoy release distance (NM) | 15 (défaut) |
| LUA Plugins Options / CTLD | Create default pickup/drop zones at bases without CTLD zones | ✔ |
| LUA Plugins Options / CTLD | Max player paradrop altitude (ft AGL) | 3000, puis une autre valeur |

- [ ] Une sauvegarde **antérieure** à ces changements se charge, et un tour passe. (#77)
- [ ] Recharger une sauvegarde ne fait perdre aucun avion : comparez le nombre d'appareils dans l'Air Wing avant et après. (#97)

---

## 3. Corrections de bugs (lot 1)

### BUG-02 — Radars des sites AAA — #54
- [ ] Nouvelle campagne avec une faction qui a des Patriot et de l'AAA : aucun site AAA, Cold War Flak Site compris, ne contient de radar SAM.
- [ ] Les sites KS-19 / SON-9 gardent leur Fire Can.

### BUG-03 — Strike sans cible — #57
- [ ] Avec les motorpools activés, une Strike IA planifiée au tour 1 contre un motorpool ennemi a des cibles et attaque les véhicules garés.
- [ ] (Si vous avez la sauvegarde de `upstream#948`) sa mission se génère sans erreur.

### BUG-01 — Leurres TALD des SEAD — #59
- [ ] Un package F/A-18C « SEAD » avec TALD contre un SA-6 : les leurres atteignent la zone d'engagement, et le site tire au moins un missile sur un leurre.
- [ ] Le point « DECOY RELEASE » apparaît entre INGRESS et la cible pour ce vol, mais pas pour un vol SEAD qui n'emporte que des HARM.
- [ ] Si le résultat n'est pas bon, ajustez « Decoy release distance (NM) » et notez la valeur qui marche.

### BUG-04 — Parking occupé — #75
- [ ] Campagnes Guam (Olf Orote) et Operation Frostbite (Vuojarvi) : les hélicoptères sur hélipads ne chevauchent pas les avions garés, et aucun hélicoptère ne s'écrase au décollage.
- [ ] (Si vous avez la sauvegarde de `upstream#734`) plus aucun chevauchement.

### BUG-05 — Transferts d'escadron — #62
- [ ] Planifiez un transfert d'escadron dans sa fiche (Air Wing), puis rouvrez-la : la destination est toujours sélectionnable et affiche la même capacité.
- [ ] Endommagez la piste d'une base qui a un transfert planifié, cliquez sur **Take off**, puis **Abort mission** et réessayez : pas de pilote en double, et le nombre d'avions est inchangé.

### Dotations — #100, #102
- [ ] Campagne guerre froide (TblisiGap, Russia 1975) : `logs\retribution.log` ne contient aucune ligne « cannot equip ».
- [ ] Dans l'éditeur de mission DCS, les dotations MiG-29A CAS/STRIKE et SA342M ANTISHIP montrent les emports attendus.
- [ ] Les dotations AJS37 Rb 15 et Mirage F1 Belouga se chargent et tirent.

---

## 4. Reprises de l'amont (lot 2)

### TRN-01.6 — `mission_types` des escadrons — #55
- [ ] Un escadron de transport dont le YAML ne liste pas Transport ne reçoit jamais de vol de transport aérien. Un escadron qui le liste (par ex. `globemaster/15th-Airlift`) en reçoit.

### TRN-02 — Assaut aéroporté par parachutage — #56
- [ ] C-130J-30 (module officiel), joueur : le largage fonctionne.
- [ ] C-130J-30, IA : les troupes sont larguées sur la zone.
- [ ] Hercules (mod Anubis), joueur, puis IA.
- [ ] C-47 : compatible, ou noté comme non supporté.
- [ ] Le saut du joueur est refusé au-dessus du plafond (3 000 ft AGL par défaut), et une autre valeur réglée dans LUA Plugins Options / CTLD est respectée.

### PER-02 — Réparations — #77
- [ ] Détruisez une usine, capturez sa base et réparez-la depuis la fiche du site (bouton **Repair**). Elle reste détruite pendant les 5 missions suivantes, puis est intacte à la 7e, et son revenu revient.
- [ ] Frappez un autre bâtiment d'un site en réparation : le compteur de réparation de la fiche du site repart au délai complet.
- [ ] Avec « Enemy AI repairs SAM and EWR sites » activé, détruisez le radar de recherche et des lanceurs d'un SA-3 : le radar est reconstruit en premier et réapparaît vivant à la mission suivante.
- [ ] Réparez une unité SAM détruite avec le délai par défaut : elle réapparaît vivante, sans épave sous elle.

### CSAR-01 — Sauvetage des pilotes — #79, #85, #87, #93, #98, #99
**Bases**
- [ ] Un pilote IA abattu en territoire ennemi apparaît sur la carte comme pilote abattu. Une mission CSAR jouable le récupère, et il reprend du service après N tours. (#79)
- [ ] Les éjections, les sauvetages et les dégâts arrivent ensemble dans `state.json` : vérifiez le fichier après une mission. (#79)
- [ ] Clic droit sur un pilote **ennemi** abattu : aucun package n'est créé. Sur un pilote ami, l'éditeur de package s'ouvre. (#95, #175)
- [ ] Aucun Gazelle, AH-64 ou Ka-50 n'est affecté à un vol CSAR. (#99)

**Statut des pilotes** (#87)
- [ ] Option prisonnier désactivée : laissez expirer le compte à rebours d'un pilote IA. Les messages et le débriefing le déclarent mort, et l'onglet des pilotes de l'Air Wing le liste comme mort.
- [ ] Option prisonnier activée : un pilote qui expire près d'une base ennemie apparaît « Prisoner of war » dans l'escadron. Sa place est **libérée** (décision du 29/10, #101), et capturer la base le libère.
- [ ] Avec « CSAR rescues AI-controlled downed pilots » désactivé, un pilote IA éjecté n'apparaît pas sur la carte. Un pilote joueur (invulnérabilité coupée) y apparaît.
- [ ] Un pilote abattu ce tour-ci est toujours sur la carte au tour suivant, et on peut planifier un CSAR vers lui.

**Zones sûres et prime** (#85)
- [ ] Un pilote IA abattu loin dans le territoire ami, avec la récupération en zone sûre activée, n'apparaît pas sur la carte. Il est « Recovering » dans l'escadron au tour suivant.
- [ ] Un pilote abattu près du front apparaît sur la carte.
- [ ] Un sauvetage CSAR avec une prime non nulle augmente le budget de ce montant, et le débriefing l'affiche.

**Planification et sauvetage** (#93)
- [ ] Un CSAR IA près du front a une escorte CAS, qui tient au-dessus du point de récupération et engage les unités au sol.
- [ ] Hélicoptère joueur, pilote **dans l'eau** : se poser à côté ne récupère personne et affiche le message de vol stationnaire. Le treuillage en stationnaire récupère le pilote.
- [ ] Hélicoptère joueur, pilote **à terre** : la récupération posé et la récupération en stationnaire fonctionnent toutes les deux.
- [ ] Un CSAR IA en mode atterrissage, puis en mode stationnaire, récupère le pilote et se pose sur une base amie : le sauvetage apparaît au débriefing.
- [ ] Un CSAR IA abattu après avoir récupéré un pilote ne le sauve pas.
- [ ] Un pilote tué au sol près d'un hélicoptère de sauvetage n'est pas sauvé. Dans le journal, `S_EVENT_DEAD` se déclenche pour lui, et aucun événement de mort ne se déclenche quand DCS l'embarque.

**Volumes** (#98)
- [ ] Après un tour résolu automatiquement avec de lourdes pertes, la plupart des pilotes abattus ne sont **pas** prisonniers : ils sont récupérés, ou en attente de sauvetage.

---

## 5. Nouvelles mécaniques (lot 3)

### PER-01 — Dégâts persistants — #60, #78, #80, #84
- [ ] Les avions, véhicules et objets statiques endommagés apparaissent dans `damaged_units` (`state.json`) avec des ratios plausibles. Testez aussi un ou deux mods. (#60)
- [ ] Les unités détruites n'apparaissent pas dans `damaged_units`. (#60)
- [ ] Endommagez un F-16 IA à 30 % ou plus : son escadron a un avion disponible de moins au tour suivant, puis il revient. (#78)
- [ ] Les noms d'unités de `damaged_units` correspondent à ceux des avions, slots clients compris. (#78)
- [ ] Le rapport (section **Damaged units**) liste les unités endommagées. (#84)
- [ ] La fiche d'escadron et la liste de l'Air Wing affichent les avions en maintenance et le nombre de tours. (#84)
- [ ] Avec la réparation payante activée, **Repair N aircraft** (fiche d'escadron) déduit le coût et libère l'avion. (#84)
- [ ] Un lanceur SAM inopérant ne tire pas à la mission suivante : il apparaît comme un objet statique. (#80)
- [ ] Une unité EWR ou SAM inopérante ne casse pas le script Skynet IADS. (#80)
- [ ] Une unité inopérante (statique) touchée de nouveau voit ses dégâts correctement enregistrés. (#80)
- [ ] `getLife()` est fiable pour les objets statiques et les mods courants. (#84)

### TRN-01 — Missions de transport jouables — #74, #86
- [ ] Avec « Create default pickup/drop zones » activé, sur une campagne sans zones CTLD : un transport aérien en UH-1H joueur a ses zones de chargement et de dépose à côté de l'aérodrome ou de la FARP, en terrain dégagé, et le chargement/déchargement CTLD y fonctionne. (#74)
- [ ] Option désactivée : une campagne qui a ses propres zones CTLD fonctionne comme avant. (#74)
- [ ] Créez une mission Transport en UH-1H entre deux bases amies, par le transfert de l'écran de base (**Actions**, type **Airlift**) puis par un clic droit sur la carte et **Add flight**. En vol : le vol est un slot client, les zones et caisses CTLD apparaissent, et le kneeboard a la page Transport. (#86)
- [ ] Les unités livrées sont à destination au tour suivant. (#86)
- [ ] Un CH-47 de transport abattu en route perd sa cargaison. (#86)
- [ ] Un vol de transport généré par un transfert, réaffecté à un autre escadron et passé en Player, devient un slot client, et ses unités sont livrées. (#86)
- [ ] Supprimer un package de transport joueur rend les unités à la base de départ. (#86)

### TRN-03 — Logistique C-130 — #91
Sur TblisiGap, le camp rouge planifie déjà un vol logistique (Mi-8) à chaque tour. Pour le C-130, il faut une campagne où un camp a des C-130, des réserves à l'arrière et une FOB sans route.
- [ ] Avec « Plan logistics missions » activé, l'ATO du tour contient un package Transport de logistique vers la base qui en a besoin.
- [ ] Le joueur vole ce C-130 jusqu'au bout, passage de largage au-dessus de la FOB compris : les unités sont à la FOB au tour suivant.
- [ ] Un C-130 IA fait le passage à 1 000 ft AGL au-dessus de la FOB, puis rentre sans essayer de s'y poser.
- [ ] Un vol logistique IA abattu en route perd sa cargaison.
- [ ] Une base sans route, sans accès maritime et sans liaison aérienne affiche l'anneau rouge pointillé et la ligne « Cut off » dans l'infobulle.

### PER-03 — Carrière du pilote joueur — #58, #76, #83, #90
- [ ] **New player pilot** dans la fiche d'escadron ajoute un pilote joueur, qu'on peut affecter à un vol. (#76)
- [ ] Abattez 2 avions ennemis : `state.json` contient 2 entrées `kill_attributions` avec votre unité comme initiateur, et le pilote a 2 victoires air. (#58)
- [ ] Détruisez une unité au sol et un navire : ils sont crédités en victoires sol et navale. (#58)
- [ ] Après la mission, **Campaign → Pilot career** montre +1 sortie, +1 sortie de combat, les victoires et une ligne d'historique. (#76, #83)
- [ ] Après 2 missions, l'écran de carrière montre les totaux et les 2 missions. (#83)
- [ ] Atteindre 5 victoires air donne un message « Ace » après le débriefing, et la décoration apparaît sur l'écran de carrière. (#83)
- [ ] Éjectez-vous (invulnérabilité coupée, CSAR activé) : +1 éjection et +1 abattu, et la ligne d'historique indique « Ejected ». (#90)
- [ ] Sauvez ce pilote avec un CSAR joueur : il gagne +1 « Rescued by CSAR », et la sortie du sauveteur affiche Rescues = 1. (#90)

---

## 6. IA et budget — #101, #103
- [ ] Sur quelques tours d'une campagne où le camp rouge est riche (type Kutaisi), les escadrons rouges sont complétés, et le budget rouge reste proche de la réserve (300 par défaut).
- [ ] Avec l'automatisation des achats d'avions activée pour le camp bleu, le message « ordered N aircraft to bring our squadrons up to strength » apparaît, et le budget bleu garde au moins la réserve.
- [ ] Note : en Syrie Nord, le budget rouge continue de monter. C'est accepté, car ses escadrons sont pleins ou sans parking.

---

## 7. Fin de campagne de test
- [ ] Après 5 tours ou plus avec toutes les options activées : pas de pilote en double, pas d'inventaire ni de budget négatif, aucun avion bloqué en maintenance, et pas d'erreur dans `logs\retribution.log`.
- [ ] Après tout cela, une sauvegarde de cette campagne se recharge, et un tour passe.
