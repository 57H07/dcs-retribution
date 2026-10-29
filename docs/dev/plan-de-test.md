# Plan de test en jeu (DCS) — branche `dev`

> **Suspendu (2026-10-29).** Ce plan reprendra quand l'interface web sera active par défaut, et sera alors complété avec ses écrans (décisions W10 et W19 de [la spécification de l'interface web](design/specification-interface-web.md)). Les cases qui citent des boutons ou fenêtres Qt devront être réécrites pour l'interface web.

Ce plan couvre tout ce que les tests automatiques ne peuvent pas vérifier : le rendu réel de l'application, et le comportement dans DCS. Chaque case renvoie à la PR qui a introduit le changement (`#NN` sur `57H07/dcs-retribution`). Si une case échoue, notez la PR, la campagne, le tour, et joignez `logs/retribution.log`, la sauvegarde et le `state.json`.

---

## 0. Préambule : lancer le programme

### 0.1 Une seule fois

Tout est déjà installé sur cette machine : le venv Python 3.11 dans `venv\` avec PySide6 6.11.2, et le client de la carte compilé dans `client\build`. Refaites ces deux étapes seulement après un `git pull` qui touche `requirements.txt` ou `client/` :

```powershell
cd F:\_Projets\Jeux\DcsRetribution
.\venv\Scripts\python.exe -m pip install -r requirements.txt
cd client; npm ci; npm run build; cd ..
```

### 0.2 À chaque lancement (depuis les sources)

```powershell
cd F:\_Projets\Jeux\DcsRetribution
git switch dev; git pull
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = "."
python qt_ui\main.py
```

- Lancez toujours depuis la racine du dépôt : les chemins `resources\`, `client\build` et `logs\` sont relatifs.
- Le journal est écrit dans `logs\retribution.log`. Gardez-le ouvert dans un éditeur pendant les tests.
- `--dev` sert seulement au développement de la carte : il charge `http://localhost:3000` au lieu de `client\build`. Ne l'utilisez pas pour ces tests.

### 0.3 Premier démarrage

1. La fenêtre de configuration demande le dossier d'installation de DCS et le dossier `Saved Games\DCS` (ou `DCS.openbeta`).
2. Retribution modifie `<DCS>\Scripts\MissionScripting.lua` (désassainissement nécessaire à l'export de `state.json`), puis le restaure à la fermeture. Laissez Retribution ouvert pendant que DCS tourne.

### 0.4 Boucle d'un tour

1. **New Game** : l'assistant crée la campagne. Choisissez la campagne, les factions et les options, puis réglez les **Settings** (§2).
2. Planifiez, puis cliquez sur **Take off**. Retribution génère `Saved Games\DCS\Missions\retribution_nextturn.miz` et ouvre la fenêtre d'attente des résultats.
3. Dans DCS : **Mission → ouvrir `retribution_nextturn.miz`**, volez, puis quittez la mission (Échap → Quitter). DCS écrit `state.json`.
4. De retour dans Retribution, la fenêtre d'attente des résultats détecte `state.json` et affiche le bilan. **Accept results** valide le tour, et le tour suivant est planifié.
5. Sauvegardez souvent (**File → Save**), surtout avant un test destructif.

> Astuce : pour les tests qui ne demandent pas de voler, utilisez l'avance rapide ou la résolution automatique. Pour aller vite dans DCS, passez en accéléré (Ctrl+Z) et activez l'invulnérabilité, sauf quand un test demande de l'éteindre.

### 0.5 (Optionnel) Paquet exécutable

À faire une fois à la fin, pour vérifier le paquet distribué (#82, #89) :

```powershell
.\venv\Scripts\Activate.ps1
$env:PYTHONPATH = ".;./pydcs"
pip install pyinstaller   # s'il n'est pas déjà présent
pyinstaller pyinstaller.spec
.\dist\dcs-retribution\dcs-retribution.exe
```

---

## 1. Démarrage, interface et carte (sans voler)

### Application (PySide6, thèmes, police) — #82, #89, #94, #96
- [ ] L'application démarre, charge une campagne, la carte s'affiche, un tour passe et une mission se génère. (#82, #96)
- [ ] Aucune régression visuelle : feuilles de style, icônes, listes. (#82)
- [ ] Installation neuve : renommez temporairement `%LOCALAPPDATA%\DCSRetribution\retribution_preferences.json` et `liberation_theme.json`. L'application démarre en thème **Dark**, pour Qt et pour la carte. Remettez ensuite les fichiers en place. (#89)
- [ ] Installation existante : le thème choisi est conservé. Vanilla, DCS World, Dark et Light sont tous sélectionnables dans **Preferences**. (#89)
- [ ] Changement à chaud : passez de Dark à Light puis à Dark, avec la fenêtre principale, une fenêtre non modale ouverte (Logs) et la carte. Les trois suivent sans redémarrage. (#94)
- [ ] Les icônes de la barre d'outils et du panneau du haut changent avec le thème. (#94)
- [ ] Les fréquences en double ou de garde s'affichent en couleur d'avertissement ou de danger dans les 4 thèmes. (#94)
- [ ] Police Inter, réseau coupé, avec une mise à l'échelle Windows de 100 %, 150 % et 200 % : pas de texte coupé. Vérifiez depuis les sources et depuis le paquet. (#89)

### Carte et légende — #61, #81, #88, #92
- [ ] Le bouton **Legend** ouvre le panneau. Cocher ou décocher une couche ajoute ou retire ses entrées. (#61)
- [ ] Chaque symbole et chaque couleur visible sur la carte a son entrée dans la légende. (#61)
- [ ] Dans les deux thèmes, le sélecteur de couches, les boutons zoom, règle et légende, les infobulles et le bandeau hors ligne suivent le thème, avec un contraste suffisant. (#92)
- [ ] Changer le thème depuis Qt restyle la légende sans recharger la page. (#92)
- [ ] Du zoom théâtre au zoom aérodrome, les symboles restent lisibles et les étiquettes ne recouvrent pas le symbole. (#81)
- [ ] **Hors ligne, Caucase** (réseau coupé avant le lancement) : contours terre/mer, toutes les couches de jeu et le bandeau « hors ligne » sont visibles. (#81)
- [ ] Après une session en ligne, les zones déjà vues s'affichent hors ligne, au mieux, grâce au cache HTTP. (#81)
- [ ] **Hors ligne, Malouines** : l'image précalculée s'affiche, alignée avec les couches de jeu (aérodromes sur la côte). (#88)
- [ ] **Hors ligne, Caucase** : rendu inchangé, toujours avec des polygones. (#88)

### Ligne de commande — #95
- [ ] `python qt_ui\main.py new-game resources\campaigns\TblisiGap.yaml --squadrons-start-full` crée une partie sans planter.

---

## 2. Campagne de test et réglages

Les nouvelles mécaniques sont **désactivées par défaut** (règle 1 de la spec), sauf la dépense du surplus par l'IA. Pour les tester, créez une campagne dédiée, par exemple **TblisiGap** (Bluefor Coldwar contre Russia 1975, avec hélicoptères et FARP) ou **Kutaisi2Vaziani** (USA 2005 contre Russia 1990), et activez dans **Settings** :

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
- [ ] Planifiez un transfert d'escadron, puis rouvrez la fenêtre : la destination est toujours sélectionnable et affiche la même capacité.
- [ ] Endommagez la piste d'une base qui a un transfert planifié, cliquez sur **Take off**, puis annulez ou réessayez : pas de pilote en double, et le nombre d'avions est inchangé.

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
- [ ] Détruisez une usine, capturez sa base et réparez-la depuis le panneau du bâtiment. Elle reste détruite pendant les 5 missions suivantes, puis est intacte à la 7e, et son revenu revient.
- [ ] Frappez un autre bâtiment d'un site en réparation : le compteur « Repairing (N turns) » repart au délai complet.
- [ ] Avec « Enemy AI repairs SAM and EWR sites » activé, détruisez le radar de recherche et des lanceurs d'un SA-3 : le radar est reconstruit en premier et réapparaît vivant à la mission suivante.
- [ ] Réparez une unité SAM détruite avec le délai par défaut : elle réapparaît vivante, sans épave sous elle.

### CSAR-01 — Sauvetage des pilotes — #79, #85, #87, #93, #98, #99
**Bases**
- [ ] Un pilote IA abattu en territoire ennemi apparaît sur la carte comme pilote abattu. Une mission CSAR jouable le récupère, et il reprend du service après N tours. (#79)
- [ ] Les éjections, les sauvetages et les dégâts arrivent ensemble dans `state.json` : vérifiez le fichier après une mission. (#79)
- [ ] Clic droit sur un pilote **ennemi** abattu : aucune fenêtre de package ne s'ouvre. (#95)
- [ ] Aucun Gazelle, AH-64 ou Ka-50 n'est affecté à un vol CSAR. (#99)

**Statut des pilotes** (#87)
- [ ] Option prisonnier désactivée : laissez expirer le compte à rebours d'un pilote IA. Les messages et le débriefing le déclarent mort, et l'escadron le liste comme mort.
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
- [ ] Le débriefing liste les unités endommagées. (#84)
- [ ] La fenêtre d'escadron, la liste de l'Air Wing et l'inventaire affichent « N in maintenance (T turns) ». (#84)
- [ ] Avec la réparation payante activée, **Repair N aircraft now** (fenêtre d'escadron) déduit le coût et libère l'avion. (#84)
- [ ] Un lanceur SAM inopérant ne tire pas à la mission suivante : il apparaît comme un objet statique. (#80)
- [ ] Une unité EWR ou SAM inopérante ne casse pas le script Skynet IADS. (#80)
- [ ] Une unité inopérante (statique) touchée de nouveau voit ses dégâts correctement enregistrés. (#80)
- [ ] `getLife()` est fiable pour les objets statiques et les mods courants. (#84)

### TRN-01 — Missions de transport jouables — #74, #86
- [ ] Avec « Create default pickup/drop zones » activé, sur une campagne sans zones CTLD : un transport aérien en UH-1H joueur a ses zones de chargement et de dépose à côté de l'aérodrome ou de la FARP, en terrain dégagé, et le chargement/déchargement CTLD y fonctionne. (#74)
- [ ] Option désactivée : une campagne qui a ses propres zones CTLD fonctionne comme avant. (#74)
- [ ] Créez une mission Transport en UH-1H entre deux bases amies, par le bouton du menu de base puis par le clic droit sur la carte. En vol : le vol est un slot client, les zones et caisses CTLD apparaissent, et le kneeboard a la page Transport. (#86)
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
- [ ] **New player pilot** dans la fenêtre d'escadron ajoute un pilote joueur, qu'on peut affecter à un vol. (#76)
- [ ] Abattez 2 avions ennemis : `state.json` contient 2 entrées `kill_attributions` avec votre unité comme initiateur, et le pilote a 2 victoires air. (#58)
- [ ] Détruisez une unité au sol et un navire : ils sont crédités en victoires sol et navale. (#58)
- [ ] Après la mission, la page **Career** montre +1 sortie, +1 sortie de combat, les victoires et une ligne d'historique. (#76, #83)
- [ ] Après 2 missions, la page Career montre les totaux et les 2 missions. (#83)
- [ ] Atteindre 5 victoires air donne un message « Ace » après le débriefing, et la décoration apparaît sur la page Career. (#83)
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
- [ ] (Optionnel) Le paquet PyInstaller (§0.5) refait les tests du §1.
