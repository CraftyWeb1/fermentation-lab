# Fermia — Document du laboratoire de fermentation

Itération actuelle : Arduino + Raspberry Pi (ou PC + webcam) + ALIVEcode + gestes + **accès RFID / voix**.  
L’IA (prédiction d’avancement et anomalies) est **prévue plus tard**, pas dans ce code.

---

## 1. C’est quoi Fermia

Fermia est un laboratoire de **fermentation intelligente** : il tient une **consigne de température** (yaourt, bière, pâte, terre, démo), **sécurise** (eau, T°, ventilo avec le Peltier), s’**ouvre et se ferme** (badge, voix + code, terminal), et se commande à distance (ALIVEcode, gestes, éventuellement ReSpeaker).

Ce n’est pas encore de l’IA : la régulation, ce sont des **seuils** et une hystérésis. L’IA s’ajoutera dans Python, sur les lignes `DATA;`.

| Carte                 | Rôle                                                                                    |
| --------------------- | --------------------------------------------------------------------------------------- |
| **Arduino Uno**       | Capteurs + actionneurs : T°, LCD, LED, bouton, relais, pompe. Régulation en temps réel. |
| **Raspberry Pi** (ou PC) | Caméra, Python, commandes. Sur le Pi : nappe CSI. Sur le PC : webcam. |

Le Pi **ne reçoit aucun capteur** sur ses GPIO. Tout le hardware 5 V / 12 V est sur l’**Arduino**. Le Pi parle à l’Uno en **USB**.

---

## 2. Branchement 100 % — qui se branche où

```
Alim officielle Pi 5 V ──► Raspberry Pi
                              │
                    nappe CSI │  USB-A
                              │    │
                    Caméra Pi ┘    │
                                   ▼
                             Arduino Uno 5 V (USB)
                                   │
                    5V / GND ──► breadboard
                                   │
         ┌─────────┬─────────┬─────┴──────┬──────────┬─────────┐
         ▼         ▼         ▼            ▼          ▼         ▼
      LCD 1602  DS18B20    LED+bouton   MQ-135    relais×2   L298N
         + pot     +4,7k                               │        │
                                                     12 V      12 V
                                                       │        │
                                                    pompe    Peltier
                                                             + 2 ventilos
```

**Deux alimentations, une seule masse 12 V ↔ Arduino GND.**  
Le Pi a **sa propre** alim USB-C. Ne l’alimente **pas** avec le 12 V.

### Inventaire 100 % (rien n’est oublié)

| # | Composant | Alim | Vers |
|---|---|---|---|
| 1 | **Raspberry Pi** 3/4/5 | Alim **USB-C officielle** 5 V | Carte SD, éventuellement HDMI + clavier |
| 2 | **Caméra Pi** (Module 2 ou 3) | via la nappe (pas de 5 V séparé) | Port **CSI** du Pi |
| 3 | **Câble USB** Pi (ou PC) → Uno | — | Port USB de l’Uno : 5 V plaque **+** série Python |
| 4 | **Arduino Uno** | USB du Pi/PC | Breadboard 5V / GND |
| 5 | **LCD 1602** + pot 10 kΩ | 5 V plaque | D8–D13 (couleurs § 4) |
| 6 | **DS18B20** + 4,7 kΩ | 5 V | D2 |
| 7 | **LED** + 220 Ω | D4 | GND |
| 8 | **Bouton** | D3 | GND |
| 9 | **MQ-135** | 5 V | A0 |
| 10 | **Relais 1** pompe | 5 V bobine, 12 V contact | IN **D5**, COM +12 V, NO pompe + |
| 11 | **Pompe 12 V** | 12 V via relais 1 | − pompe → −12 V |
| 12 | **Relais 2** ventilos | 5 V bobine, 12 V contact | IN **D7**, COM +12 V, NO = rouges des 2 ventilos |
| 13 | **2 ventilos** du bloc Peltier | 12 V via relais 2 | noirs → −12 V |
| 14 | **L298N** | 12 V vis VS, GND commun | IN1 **D6**, IN2 **A1**, OUT1/OUT2 = pastille |
| 15 | **Pastille Peltier** | 12 V via L298N | pas les ventilos |
| 16 | **Alim 12 V 5 A min** | secteur | +12 V pompe/L298N/relais COM ; −12 V = GND Arduino |
| 17 | **RC-522 RFID** | **3,3 V du Pi** (pas 5 V) | SPI du **Raspberry Pi** (pas l’Arduino) |
| 18 | **DEL RVB** cathode commune 5 mm | 5 V via D4/A2/A3 + 3× 220 Ω | 1 seule suffit |
| 19 | **Buzzer actif 5 V** | A4 | bip quand fermentation finie |
| 20 | **Capteur niveau d’eau** (analogique) | 5 V | **A5** — dans l’eau du bain-marie seulement |

---

## 2.1 Raspberry Pi 4 + caméra (nappe CSI)

Le Pi 4 n’a **aucun** fil GPIO vers le LCD, la pompe, le MQ, le Peltier. Seulement : **alim USB-C**, **nappe caméra**, **USB vers l’Arduino**. Le RC-522 (si tu l’as) va aussi sur le Pi, § 4.9.

```
Alim USB-C 5 V 3 A  ──►  Pi 4
Nappe CSI           ──►  port CAMERA (entre les 2 HDMI et le jack)
Câble USB-A         ──►  Arduino Uno
HDMI (option)       ──►  écran
```

### Alim et carte SD

- [ ] Carte microSD avec **Raspberry Pi OS** (Imager sur un PC)
- [ ] Alim **USB-C 5 V / 3 A** officielle ou équivalent. **Pas** le 12 V du Peltier, **pas** un chargeur de téléphone trop faible (le Pi coupe ou clignote)
- [ ] Pi **éteint** (USB-C débranché) avant de mettre la nappe

### Caméra — nappe, Pi éteint

Port **CAMERA** du Pi 4 : petite fente entre les **deux HDMI** et le **jack audio** (pas le port d’écran DSI de l’autre côté).

- [ ] Sur le Pi : tire le **linguet noir** du connecteur CSI vers le haut
- [ ] Enfonce la nappe **à fond**, **contacts métalliques argentés vers les HDMI** (le dos bleu de la nappe vers le jack / l’USB)
- [ ] Re-pousse le linguet pour coincer
- [ ] Sur le **module caméra** : même geste, nappe bien droite, linguet refermé
- [ ] Objectif vers **l’intérieur du bac** (trou dans le couvercle)
- [ ] **Ne branche / débranche jamais** la nappe Pi allumé

### Allumer et activer la caméra

- [ ] USB-C du Pi
- [ ] HDMI + clavier si tu n’es pas en SSH
- [ ] Terminal :

```bash
sudo raspi-config
```

Interface Options → Camera (ou I2C si demandé) → Enable → Finish → reboot.

Test :

```bash
libcamera-hello
```

Une fenêtre 5 s = caméra OK. Sinon : nappe à l’envers ou mal enfoncée (Pi éteint, recommence).

### USB Arduino (le labo)

- [ ] USB-A **du Pi** → prise USB de l’**Uno**
- [ ] L’Uno s’allume (LED ON). Ça alimente aussi la plaque 5 V
- [ ] Port : souvent `/dev/ttyACM0`

```bash
ls /dev/ttyACM* /dev/ttyUSB*
cd ~/fermentation-lab/raspberry
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ARDUINO_PORT=/dev/ttyACM0
python app.py
```

Puis `photo` : image dans `captures/`.

Si tu as le **RC-522** : câble-le **après** (3,3 V pin 1 du Pi, § 4.9). SPI à activer dans `raspi-config`.

---

## 2.2 Arduino au PC (si pas de Pi)

Même USB, webcam du laptop à la place de la nappe CSI.

1. USB données PC → Uno (LED ON).
2. Arduino IDE : carte **Uno**, port **COMx** (driver CH340 si clone).
3. Téléverser le `.ino`.
4. **Fermer le Moniteur série** avant `python app.py`.
5. `$env:ARDUINO_PORT="COM3"` si Python ne trouve pas la carte.
6. Webcam : `$env:CAMERA=1` si `CAMERA=0` est noir.

USB = **5 V** plaque (LCD, sondes, LED, bouton, bobines relais) **et** liaison Python.

---

## 3. Matériel de cette itération

| Type | Composant | Rôle |
|---|---|---|
| Carte | Arduino Uno | Cerveau hardware |
| Carte | Raspberry Pi + caméra CSI | Cerveau logiciel + photos (`photo`) |
| Carte | *ou* PC + webcam | Remplace le Pi si tu n’en as pas |
| Capteur | DS18B20 | Température |
| Capteur | **MQ-135** (ou MQ-2) | Qualité de l’air (CO₂, alcool, NH₃) |
| Capteur | Bouton poussoir | Profil / AUTO-MAN |
| Actionneur | LCD 1602 | Affichage |
| Actionneur | LED rouge + 220 Ω | État |
| Actionneur | Module relais 5 V (2 canaux de préférence) | Coupe le 12 V pompe **et** ventilo |
| Actionneur | Pompe 12 V | Bain-marie (yaourt / bière) |
| Actionneur | Ventilo brushless 12 V | Air (pâte / terre, et mode FROID) |
| Actionneur | **L298N** + module Peltier 12 V | Chauffe (IN1) et froid (IN2) |
| Autre | Résistance 4,7 kΩ | Pull-up DATA DS18B20 |
| Autre | Potentiomètre 10 kΩ | Contraste LCD |
| Autre | Alim 12 V | Pompe **et** ventilo |

**Plus tard :** pH, densimètre. Le CO₂ / air est couvert par le MQ.

---

## 2.3 Ordre d’allumage (tout le labo)

1. Pi (ou PC) **éteint**, 12 V **éteint**
2. Nappe caméra enfoncée
3. USB Pi/PC → Arduino
4. Plaque 5 V déjà câblée (GND commun 12 V déjà tiré, 12 V encore OFF)
5. Allumer le **Pi / PC**, téléverser, LCD OK
6. Allumer le **12 V** en dernier (pompe, Peltier, ventilos)

Éteindre : 12 V d’abord, puis Pi.

---

## 3b. Schéma Arduino (détail pins)

```
Raspberry Pi (ou PC)
   nappe CSI → caméra Pi     USB → Arduino Uno
                                    |
                    5V / GND → rails plaque
                    D2  jaune DS18B20 (+ 4,7 kΩ vers 5V)
                    D3  bleu bouton → GND
                    D4  violet LED → 220 Ω → GND
                    D5  gris relais pompe IN
                    D6  L298N IN1 (chauffe)
                    D7  relais ventilos IN
                    D8–D13 LCD (voir couleurs § 4)
                    A0  MQ-135 AO
                    A1  L298N IN2 (froid)
```

---

## 4. Câblage breadboard (checklist)

**12 V éteint** jusqu’à la fin des tests LCD / Python.

Couleurs = **tes** fils (pour t’y retrouver). **PPL = violet.**

### Aide-mémoire couleurs

| Fil | D’où | Vers |
|---|---|---|
| Rouge | Arduino 5V, LCD 2 et 15, DS18B20 VCC | rail **5V** |
| Noir | Arduino GND, LCD 1 et 5, DS18B20 GND, LED −, bouton | rail **GND** |
| Rouge (pont) | rail 5V un côté | rail 5V l’autre côté |
| Noir (pont) | rail GND un côté | rail GND l’autre côté |
| Blanc | LCD 3 (contraste) | curseur du pot 10 kΩ |
| Bleu | LCD 4 (RS) | **D8** |
| Violet (PPL) | LCD 6 (E) | **D9** |
| Gris | LCD 11 (D4) | **D10** |
| Blanc | LCD 12 (D5) | **D11** |
| Brun | LCD 13 (D6) | **D12** |
| Vert | LCD 14 (D7) | **D13** |
| Orange | LCD 16 (K) | rail **GND** |
| Jaune | DS18B20 DATA | **D2** (+ 4,7 kΩ vers 5V) |
| Violet (PPL) | LED (avant 220 Ω) | **D4** |
| Bleu | Bouton | **D3** |
| Jaune | Relais pompe VCC | rail **5V** |
| Violet (PPL) | Relais pompe GND | rail **GND** |
| Gris | Relais pompe IN | **D5** |
| Rouge pompe | Relais NO | + pompe |
| Noir / − pompe | − pompe | **−12 V** |

### 4.1 Alimentation 5 V (USB)

- [ ] Broche **5V** Uno → rail **rouge** (fil rouge)
- [ ] Broche **GND** Uno → rail **bleu** de la plaque (fil noir)
- [ ] Pont **rouge** : 5 V d’un côté de la plaque vers l’autre
- [ ] Pont **noir** : GND d’un côté vers l’autre
- [ ] **Pas de 12 V** sur ces rails

### 4.2 LCD 1602

Le pot **n’est pas** un sélecteur de recette. Il règle seulement le **contraste** (pin V0). Tourne-le jusqu’à voir `T:` et le nom du profil.

| Pin LCD | Rôle | Vers | Fil |
|---|---|---|---|
| 1 VSS | masse | rail GND | **noir** |
| 2 VDD | alim | rail 5V | **rouge** |
| 3 V0 | contraste | curseur du pot 10 kΩ (autres pattes : 5V et GND) | **blanc** |
| 4 RS | commande | **D8** | **bleu** |
| 5 RW | toujours GND | rail GND | **noir** |
| 6 E | enable | **D9** | **violet (PPL)** |
| 7–10 | inutilisés | rien | — |
| 11 D4 | data | **D10** | **gris** |
| 12 D5 | data | **D11** | **blanc** |
| 13 D6 | data | **D12** | **brun** |
| 14 D7 | data | **D13** | **vert** |
| 15 A | rétroéclairage + | rail 5V | **rouge** |
| 16 K | rétroéclairage − | rail GND | **orange** |

### 4.3 DS18B20

- [ ] VCC → rail 5V — fil **rouge**
- [ ] GND → rail GND — fil **noir**
- [ ] DATA → **D2** — fil **jaune**
- [ ] 4,7 kΩ entre le fil **jaune** et le rail 5V

### 4.4 DEL RVB cathode commune (1 suffit)

**Une seule** LED 4 pattes. Pas besoin de 3 LEDs.

```
    [ dôme LED ]
    |  |  |  |
    R GND G  B
       ↑
    patte la plus LONGUE = cathode → rail GND, SANS résistance
```

**Règle plaque :** une rangée de 5 trous (a–e ou f–j) = le même fil. Chaque 220 Ω (ou 270 Ω) a une patte **dans la rangée de la LED**, l’autre patte **une rangée plus loin**, et le Dupont dans cette 2ᵉ rangée. Les deux pattes d’une résistance **ne** sont **pas** dans la même rangée.

| Patte (gauche → droite) | Résistance | Fil vers |
|---|---|---|
| 1 **Rouge** | 220 Ω (ou 270 Ω) | **D4** (violet) |
| 2 **la plus longue = GND** | **aucune** | **noir** → rail **−** |
| 3 **Vert** | 220 Ω | **A2** |
| 4 **Bleu** | 220 Ω | **A3** |

Pas de résistance sur le **bouton**. Pas de 4,7 kΩ sur la LED (ça resterait éteinte).

**Couleurs (après téléversement) :**

| LED | LCD ligne 2 | Sens |
|---|---|---|
| **Orange** | `AUTO CHAUFFE 42C` / `FROID` | Peltier **ON** (régule) |
| **Rouge fixe** | `ROUGE: SONDE HS` | Sonde absente / HS |
| **Rouge fixe** | `ROUGE: AIR MAUV` | MQ air trop chargé |
| **Rouge fixe** | `ROUGE: PELT OFF` | Peltier **éteint** (`stop`, manuel, ou déjà à la consigne) — climat incomplet |
| **Vert clignote** + bips | `FERMENT. FINIE` | Cycle terminé |
| **Bleu clignote** | `FERMIA FERME` | Labo fermé (RFID ; désactivé en test) |

Le rouge a **plusieurs causes** : toujours lire le LCD. Priorité : sonde > air > Peltier off.

**Test LED (USB, pas de 12 V) :** yaourt AUTO trop froid → orange ; `stop` → rouge + `PELT OFF` ; débranche le jaune D2 → rouge + `SONDE HS`.

### 4.4b Buzzer (bip « c’est fini »)

Buzzer **actif** 5 V (2 pattes, pas un piezo passif).

- [ ] **+** du buzzer → **A4**
- [ ] **−** du buzzer → rail **GND**

3 bips quand la fermentation est détectée finie. Test immédiat : `ouvrir` puis `fini`.

### 4.5 Bouton

- [ ] Une patte → **D3** — fil **bleu**
- [ ] L’autre patte → rail GND — fil **noir**

### 4.6 Relais (module 1 canal, pins **+ − S**)

Le module bleu SRD-05VDC-SL-C a parfois **GND / IN / +5V**, parfois **+ / − / S**. C’est la même chose.

| Pin écrite | Sens | Relais ventilos (prioritaire) | Relais pompe (2ᵉ module) |
|---|---|---|---|
| **+** ou +5V / VCC | 5 V Arduino | rail **5 V** | rail **5 V** |
| **−** ou GND | masse | rail **GND** | rail **GND** |
| **S** ou IN | ordre | **D7** | **D5** |

**Vis :** **NC** = rien. **COM** = +12 V du bloc. **NO** = fil rouge de la charge.

Le **+** du relais = **5 V Arduino**, jamais le 12 V.

**Un seul relais pour l’instant :** branche-le en **ventilos D7** (le Peltier ne doit pas chauffer sans ventilo).

Test **sans 12 V** : yaourt AUTO → **clic** ; `stop` → **clic**. Si le clic est à l’envers : `RELAIS_ACTIF_LOW` à `false` dans le `.ino`.

**Pompe (2ᵉ relais, 12 V encore OFF) :**

- [ ] **+** → rail 5V
- [ ] **−** → rail GND
- [ ] **S** → **D5**
- [ ] **COM** → **+12 V**
- [ ] **NO** → fil **rouge** de la pompe
- [ ] **−** pompe → **−12 V**

### 4.6b Capteur d’eau (A5) — bain-marie seulement

La pompe **circule** l’eau, elle **ne vide pas** le bac. Pour vider : tuyau de sortie **hors** du bac à la main, ou verser. Si tu laisses tourner pour vider, le capteur coupe la pompe dès que l’eau est trop basse (**protection à sec**).

Le module (souvent 3 pins, plaques métalliques) va **dans l’eau** du yaourt/bière, **pas** dans pâte/terre, **pas** l’électronique immergée.

| Pin module | Vers |
|---|---|
| **VCC** | rail **5 V** |
| **GND** | rail **GND** |
| **AO** / A0 | **A5** Arduino |
| **DO** | rien |

- [ ] Plaques **verticales**, seulement le bas dans l’eau
- [ ] Fil vers A5 au sec
- [ ] AO → **A5**. Sans capteur, A5 donne un chiffre au hasard : laisse le module branché pour le test.

**Test :** yaourt + doigt / eau sur les plaques → `wet=1`, `eau=OK`. Sors le capteur → LCD `ROUGE: EAU BASSE`, pompe **coupée**.

Seuil : `SEUIL_EAU_OK = 250` (augmente si ça dit « basse » alors qu’il y a de l’eau).

### 4.7 Bloc Peltier + 2 ventilos (ce que tu as)

Ce n’est **pas** un ventilo PC tout seul. C’est un **sandwich** :

```
[ grand ventilo + gros radiateur ]  ← face CHAUDE, à l’EXTÉRIEUR du bac
[     pastille Peltier blanche     ]  ← 2 fils vers le L298N
[ petit ventilo + petit radiateur  ]  ← face FROIDE, vers l’INTÉRIEUR du bac
```

Les **deux** ventilos (gros + petit) sont déjà vissés sur les radiateurs. Ils doivent tourner **dès que le Peltier est ON** (chauffe **ou** froid), sinon le module grille.

**Fils : ne pas tout mélanger**

| Paires rouge / noir | Vers |
|---|---|
| Les 2 fils de la **pastille** (souvent plus courts, au milieu) | **L298N OUT1 et OUT2** (polarité inversable) |
| Gros ventilo (grille métallique) | relais **D7** : rouge → NO, noir → 12 V − |
| Petit ventilo | **même relais D7** (en parallèle du gros) : rouge avec rouge, noir avec noir |

Les ventilos vont au **relais**, pas au L298N. Le L298N inverse seulement le Peltier. Les ventilos, eux, restent toujours dans le même sens (rouge = +, noir = −).

- [ ] Relais 2 VCC → rail 5V
- [ ] Relais 2 GND → rail GND
- [ ] Relais 2 IN → **D7**
- [ ] Relais 2 COM → **+12 V**
- [ ] Relais 2 NO → **tous les rouges** des 2 ventilos
- [ ] Tous les **noirs** des ventilos → **−12 V**
- [ ] Gros côté (grille) **hors du bac** (chaleur qui part)
- [ ] Petit côté **dans / vers** le bac (froid vers la cassette)

### 4.7b L298N + Peltier — branchement pas à pas

Le Peltier **ne va jamais** sur une pin Arduino (ça crame l’Uno).  
Le **L298N** est le “pont” : l’Arduino dit seulement **chauffe** (D6) ou **froid** (A1), et le L298N envoie le **12 V** dans un sens ou dans l’autre.

**Alim 12 V débranchée** jusqu’à l’étape 6. USB Arduino = OK.

Schéma : `visuels/l298n-branchement-fermia.jpg`

| Sur le L298N | Tu mets |
|---|---|
| **OUT1** | 1 fil de la **pastille** |
| **OUT2** | l’autre fil de la pastille |
| **vis +12V** | **rouge** du bloc 12 V |
| **vis GND** | **noir** du bloc 12 V **+** fil vers **GND Arduino** (2 fils dans la vis) |
| **vis 5V** | **rien** (jumper 5V déjà en capuchon) |
| **ENA** | **capuchon noir** (pas un fil) |
| **IN1** | **D6** |
| **IN2** | **A1** |
| **IN3 IN4 ENB OUT3 OUT4** | **rien** |

Le Pi / PC **n’est pas** le bloc 12 V. Sans adaptateur 12 V 5 A : laisse vis +12V vide, teste le reste en USB.

```
Arduino D6 / A1  →  L298N IN1 / IN2  →  L298N OUT1 / OUT2  →  2 fils de la PASTILLE
                                                                      ↑
                                                         pas les ventilos
```

#### Reconnaître le L298N

Grande plaque verte, grosse puce noire + **radiateur**.  
3 vis d’alim d’un côté : **+12V** | **GND** | **5V**.  
De l’autre côté, 4 vis moteur : **OUT1 OUT2** (côté A) et **OUT3 OUT4** (côté B, on n’y touche pas).  
Petites broches : **ENA IN1 IN2** d’un côté, **IN3 IN4 ENB** de l’autre.

Un **jumper** = petit capuchon noir qui relie 2 pins. S’il n’y en a pas, un morceau de fil entre les 2 pins.

#### Étape 1 — Jumpers (ce ne sont PAS des fils)

Les jumpers sont les **petits capuchons noirs** déjà (souvent) enfichés sur le L298N. Tu n’ajoutes **aucun** fil ici.

- [ ] **ENA** : 2 petites pins à côté de IN1 / IN2, **capuchon noir dessus** (relie les 2 pins)
- [ ] **Jumper 5V** : 2 petites pins **entre** les vis GND et 5V, **capuchon noir dessus**
- [ ] Vis **5V** (la vis, pas le jumper) : **0 fil**. Si tu as un fil orange/jaune dans 5V → **enlève-le**

Tu n’as **pas** 3 fils d’alim sur +12V / GND / 5V. Seulement plus tard : +12V et GND. La vis 5V reste vide.

#### Étape 2 — Signaux Arduino (toujours 12 V OFF)

Fils **Dupont** vers les **petites broches** IN1 / IN2 (pas les vis).

- [ ] **IN1** → pin **D6** de l’Uno (chauffe)
- [ ] **IN2** → pin **A1** de l’Uno (froid)

**A1** = 2ᵉ trou analogique (juste après A0 du MQ).  
**Pas D7** : D7 c’est le relais des ventilos.

#### Étape 3 — Masse commune (obligatoire, 12 V encore OFF)

Sans ça, le L298N n’écoute pas l’Arduino.

- [ ] Vis **GND** du L298N → rail **GND** de la plaque (même GND que l’Uno)
- [ ] Le **−** (noir) de l’alim 12 V ira **aussi** sur cette vis GND (étape 6)

Deux fils dans la vis GND, c’est normal : un vers l’Arduino, un vers le −12 V.

#### Étape 4 — Pastille Peltier seulement

Sur le sandwich, 3 paires de fils. Tu prends **uniquement** les 2 fils du **milieu** (la pastille blanche, souvent plus courts, parfois pas rouge/noir).

- [ ] Un fil pastille → vis **OUT1**
- [ ] L’autre fil pastille → vis **OUT2**
- [ ] Serrer les vis. **OUT3 / OUT4** : vides

Les ventilos (rouge + noir, une paire sur le gros, une paire sur le petit) → **relais D7**, § 4.7. **Pas** sur le L298N.

#### Étape 5 — Placement du sandwich

- [ ] **Gros** radiateur + **grand** ventilo = **dehors** du bac (chaleur qui part)
- [ ] **Petit** radiateur + **petit** ventilo = **dedans** (vers la cassette)
- [ ] Radiateur bien vissé sur la **puce** du L298N aussi

#### Étape 6 — Alim 12 V (2 fils du bloc, pas 3)

Le bloc 12 V a **2 fils** : rouge = +, noir = −.  
La vis **5V** du L298N ne reçoit **rien**.

USB Arduino allumé, LCD OK, Python `stop`, **bloc 12 V encore éteint**.

- [ ] Fil **rouge** du bloc → vis **+12V**
- [ ] Fil **noir** du bloc → vis **GND** (en plus du fil GND Arduino déjà là)
- [ ] Vis **5V** : toujours **vide**
- [ ] Allumer le 12 V

Sur GND tu as **2 fils** dans la même vis : Arduino + noir du 12 V. C’est normal.  
Ce n’est **pas** : un fil par vis (+12V, GND, 5V).

#### Étape 7 — Test (10 secondes max)

Python (Moniteur fermé) :

```text
chauffer
```

- Les **2 ventilos** doivent tourner (relais D7).
- Le **petit** côté (intérieur) doit **chauffer** (tiède, pas brûlant).
- LCD / terminal : `peltier=HEAT`.

```text
stop
```

Tout s’arrête. Puis :

```text
refroidir
```

Le **petit** côté doit **refroidir**. Puis `stop` tout de suite.

**Si `chauffer` refroidit le petit côté** : 12 V OFF, inverse seulement **OUT1 ↔ OUT2**.  
Ne inverse **pas** les fils des ventilos (rouge = +, noir = −).

**Si rien ne bouge** : jumper ENA oublié, ou GND Arduino pas sur le L298N, ou 12 V pas sur la vis **+12V**.

**Si le L298N sent le chaud tout de suite** : `stop`, 12 V OFF. Les ventilos doivent tourner dès que le Peltier est ON.

### 4.8 MQ-135 qualité de l’air (5 V, pas le 12 V)

Module 4 broches en général : VCC, GND, **AO** (analogique), DO (digital, on ne s’en sert pas).

Le petit tube **chauffe** (normal). Attends **2–3 min** après la mise sous USB avant de lire ; pour une mesure “labo” il faudrait 24 h, inutile pour le cours.

- [ ] MQ **VCC** → rail 5V (pas le 12 V)
- [ ] MQ **GND** → rail GND
- [ ] MQ **AO** (parfois A0 / AOUT) → **A0** de l’Arduino (côté analogique gauche)
- [ ] MQ **DO** → rien
- [ ] Place le module **dans le bac** (air de la chambre), pas dans l’eau

| Lecture analogique | LCD / terminal | Sens |
|---|---|---|
| &lt; 250 | AIR **BON** | Air calme |
| 250–449 | AIR **MOY** | Fermentation active (CO₂, alcool) |
| ≥ 450 | AIR **MAUV** | Air chargé → le **ventilo** s’allume tout seul |

### 4.9 RC-522 — ouvrir le labo avec une carte (sur le Pi)

**Pas sur l’Arduino.** Le LCD utilise déjà D10–D13 (SPI). Le RC-522 va sur le **Raspberry Pi**.

Le module est en **3,3 V**. Le 5 V le grille.

| Broche RC-522 | Pin Raspberry Pi (BOARD physique) | GPIO |
|---|---|---|
| **3.3V** / VCC | pin **1** (3.3 V) | — |
| **GND** | pin **6** | — |
| **SDA** (SS / NSS) | pin **24** | GPIO8 CE0 |
| **SCK** | pin **23** | GPIO11 |
| **MOSI** | pin **19** | GPIO10 |
| **MISO** | pin **21** | GPIO9 |
| **RST** | pin **22** | GPIO25 |
| IRQ | rien | — |

Sur le Pi : `sudo raspi-config` → Interface → SPI → Enable, puis :

```bash
pip install mfrc522 spidev
```

1. Lance `python app.py`
2. Approche une carte : le terminal affiche l’UID
3. Copie l’UID dans `raspberry/badges.txt`
4. Relance : la carte **ouvre** (LCD `T:...`) ou **ferme** (LCD `FERMIA FERME` / `BADGEZ CARTE`)
5. Sans Pi / sans module : tape `ouvrir` ou `fermer`

Fermé = Peltier, pompe, ventilos **coupés**. Tu peux quand même changer le profil au bouton.

### 4.10 Capteur de niveau d’eau — pas obligatoire

**Non, ce n’est pas nécessaire** pour l’itération 1 ni pour la démo.

| Cassette | Eau ? | Capteur niveau ? |
|---|---|---|
| Yaourt / bière (bain-marie) | oui | utile **plus tard** (pompe à sec) |
| Pâte / terre | non | inutile |

Tu regardes le niveau à l’œil avant d’allumer le 12 V. L’Uno n’a plus d’entrée analogique libre (A0 = MQ, A1 = L298N). Un flotteur, ce serait un autre projet (Mega, ou LCD en I2C).

Pins Arduino :

| Pin | Composant | Fil (plaque) |
|---|---|---|
| 5V / GND | Rails plaque | rouge / noir |
| D2 | DS18B20 DATA | **jaune** |
| D3 | Bouton | **bleu** |
| D4 | DEL RVB rouge | **violet (PPL)** + 220 Ω |
| D5 | Relais pompe IN | **gris** |
| D6 | L298N IN1 (chauffe) | (vers L298N) |
| D7 | Relais ventilos IN | (vers 2e relais) |
| D8 | LCD RS | **bleu** |
| D9 | LCD E | **violet (PPL)** |
| D10 | LCD D4 | **gris** |
| D11 | LCD D5 | **blanc** |
| D12 | LCD D6 | **brun** |
| D13 | LCD D7 | **vert** |
| A0 | MQ-135 AO | (vers MQ) |
| A1 | L298N IN2 (froid) | (vers L298N) |
| A2 | DEL RVB vert | + 220 Ω |
| A3 | DEL RVB bleu | + 220 Ω |
| A4 | Buzzer + | − du buzzer au GND |

---

## 5. Rôle de chaque fonctionnalité

### Bouton (D3)

| Appui | Durée | Effet |
|---|---|---|
| Court | < 0,8 s | Profil suivant |
| Long | ≥ 0,8 s | AUTO ↔ MAN |

Ordre des profils : **YAOURT → BIERE → PATE → TERRE → DEMO → YAOURT**

Un changement de profil remet **AUTO**.  
En **MAN**, la pompe s’arrête ; tu commandes depuis le PC (`chauffer`, `stop`).

### Le labo ne détecte pas tout seul ce que tu as mis

Ni la caméra, ni le MQ, ni la sonde T° ne reconnaissent « c’est du yaourt » ou « c’est de la pâte ».

C’est comme un four : tu mets le plat **et** tu règles la température. Fermia ne devine pas.

| Tu changes | Rôle |
|---|---|
| **Cassette** (bocal, seau, bol, pot) | La **matière** à fermenter |
| **Profil** (bouton ou Python) | Le **climat** (consigne, pompe, ventilo) |

Les deux vont ensemble, **à la main**.

**Comment tu annonces le profil**

| Moyen | Action |
|---|---|
| Bouton, appui **court** | YAOURT → BIERE → PATE → TERRE → DEMO |
| Bouton, appui **long** | AUTO ↔ MAN |
| Terminal Python | `yaourt` / `biere` / `pate` / `terre` / `demo` |

Phrase pour la démo : *« L’utilisateur choisit la recette ; le système régule la température et l’air. »*

Le **RFID** ouvre le **labo** (accès), il ne choisit **pas** le profil yaourt/bière. Pour détecter la cassette plus tard : QR, aimant, ou un UID RFID **par insert**.

### Profils (consignes)

| Profil | Consigne | Usage |
|---|---|---|
| YAOURT | 42 °C | Incubation yaourt |
| BIERE | 19 °C | Fermentation bière |
| PATE | 27 °C | Pousse de la pâte |
| TERRE | 25 °C | Sol / compost doux |
| DEMO | 18 °C simulé | T° qui bouge en quelques secondes (vidéo, sans attendre une vraie fermentation) |

En AUTO : T° trop basse → CHAUFFE. Trop haute → FROID. Dans ±0,5 °C → tout OFF.

| | CHAUFFE | FROID |
|---|---|---|
| Peltier (L298N) | IN1 (D6) | IN2 (A1) |
| 2 ventilos du bloc | **ON** (relais D7) | **ON** (relais D7) |
| Yaourt / bière / demo | **Pompe ON** (bain-marie) | pompe OFF |
| Pâte / terre | pompe OFF | pompe OFF |

| Profil | Consigne | Temps utile à montrer | info                                                                                          |
| ------ | -------- | --------------------- | --------------------------------------------------------------------------------------------- |
| Yaourt | 42 °C    | 6–8 h                 | 4 h minimum, souvent une nuit. Le lait doit être pris (gélifié).                              |
| Bière  | 19 °C    | 7–14 jours (ale)      | Bulles qui calment, densité qui baisse. Trop long pour un labo de cours.                      |
| Pâte   | 27 °C    | 45–90 min (1 pousse)  | Volume ~×2. Levain / 2e pousse : 2–4 h.                                                       |
| Terre  | 25 °C    | jours à semaines      | Humidité + T° stables. Compost / vie du sol : jours à semaines. Rien de spectaculaire en 2 h. |
|        |          |                       |                                                                                               |

### LCD

Ligne 1 : `T:16.4C YAOURT`  
Ligne 2 = **pourquoi** la LED, ou l’état de régulation :

| Ligne 2 | LED | Sens |
|---|---|---|
| `ROUGE: SONDE HS` | Rouge | Sonde HS / débranchée |
| `ROUGE: EAU BASSE` | Rouge | Bain-marie sans assez d’eau → pompe coupée |
| `ROUGE: AIR MAUV` | Rouge | Air trop chargé |
| `ROUGE: PELT OFF` | Rouge | Peltier éteint → climat du profil **incomplet** |
| `AUTO CHAUFFE 42C` | Orange | Régule (chauffe) |
| `AUTO FROID 19C` | Orange | Régule (froid) |
| `FERMENT. FINIE` | Vert clignote | Cycle terminé |
| `FERMIA FERME` / `BADGEZ CARTE` | Bleu clignote | RFID (désactivé en test : labo ouvert au boot) |

**Potentiomètre 10 kΩ :** contraste uniquement (LCD pin 3 V0). Ce n’est pas un bouton de profil. Écran vide ou noir = tourner le pot.

### DEL RVB — rappel

Branchement détaillé : **§ 4.4**. Rouge = plusieurs raisons → **lire le LCD**.

### Comment le labo sait que c’est fini (automatique)

Ce n’est **pas** une caméra qui « voit » le yaourt pris. Combinaison **temps + air (MQ)** :

| Profil | Détection de fin |
|---|---|
| **Yaourt** | **6 h** après l’ouverture / le changement de profil |
| **Pâte** | **75 min** (une pousse) |
| **Bière** | l’air est passé **MOY/MAUV** (CO₂), puis **BON** pendant **3 min** (bulles qui calment). Minimum 1 min de cycle. |
| **Terre** | **pas** de « fini » auto (jours/semaines) |
| **DEMO** | **20 s** (pour la vidéo / le bip) |

Puis : Peltier/pompe OFF, LCD `FERMENT. FINIE`, 3 bips, LED verte clignote.

Pour la démo sans attendre 6 h : `ouvrir` puis `fini` (ou profil `demo` 20 s).

Changer de profil ou rebadger **relance** le chrono.

### Pompe

Bain-marie seulement (yaourt / bière / demo en chauffe). Jamais dans la nourriture.

### Ventilos du bloc Peltier

Deux brushless 12 V déjà montés (grand + petit). Ils partent avec le Peltier (`chauffer` **et** `refroidir`) via le relais D7. Le grand évacue la chaleur **dehors** ; le petit souffle vers le bac. Sans eux, le Peltier fond.

### Python (PC \Raspberry Pi)

- Affiche chaque seconde : `T=`, consigne, mode, pompe, ventilo, **air BON/MOY/MAUV**, profil  
- Envoie des commandes à l’Arduino  
- `photo` : webcam → `raspberry/captures/`

### Sécurité Arduino

- T° > 45 °C → force froid / coupe chauffe  
- Sonde HS → tout OFF (sauf mode DEMO)  
- Air **MAUV** (MQ ≥ 450) → ventilo ON (évacuer CO₂ / odeurs)

---

## 6. Logiciel Arduino

1. IDE : **Croquis → Inclure une bibliothèque → Gérer** → installer **OneWire** et **DallasTemperature**.
2. Ouvrir

   `travaux/fermentation-lab/arduino/fermentation_lab/fermentation_lab.ino`
3. Carte **Arduino Uno**, port **COMx**.
4. **Téléverser** (flèche).
5. LCD : `T:xx.xC YAOURT` et `AUTO OK 42C`.
6. Tester le bouton (court = profils, long = MAN).
7. **Fermer le Moniteur série.**

---

## 7. Logiciel Python (PC)

PowerShell :

```powershell
cd C:\Users\iouahid\Desktop\Projet-3-main\travaux\fermentation-lab\raspberry
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Si l’Arduino n’est pas trouvé (remplace COM3 par **ton** port) :

```powershell
$env:ARDUINO_PORT="COM3"
python app.py
```

Si la webcam ne marche pas :

```powershell
$env:CAMERA=1
python app.py
```

Attendu :

```
Arduino connecté sur COMx
Caméra OpenCV : OK (index 0)
[Arduino] T=20.50 C | consigne=42.00 C | AUTO | Peltier=OFF | pompe=OFF | YAOURT
```

Commandes (puis Entrée) :

| Commande                                | Effet                 |
| --------------------------------------- | --------------------- |
| `yaourt` `bierre` `pate` `terre` `demo` | Change le profil      |
| `chauffer` `refroidir` `stop`           | Manuel (pompe ON/OFF) |
| `auto`                                  | Retour AUTO           |
| `photo`                                 | Capture webcam        |
| `ouvrir` / `fermer`                     | Badge RFID (accès labo) |
| `fini`                                  | Simuler la fin (bip + LED verte) |
| `aide`                                  | Liste                 |
| `quit`                                  | Quitter               |

---

## 8. Ordre des tests (labo)

1. USB seul, **12 V OFF** : LCD + T° + bouton + LED.
2. Python : lignes `T=...`, commandes `demo` puis `stop`. Serial Monitor fermé.
3. `photo` → fichier dans `raspberry\captures\`.
4. Allumer le **12 V**.
5. `chauffer` → pompe tourne ; `stop` → pompe stop.

Si la pompe tourne tout le temps : inverse COM/NO, ou dans le `.ino` mets `RELAIS_ACTIF_LOW` à `false` et retéléverse.

---

## 9. Démo

1. LCD allumé, T° yaourt.
2. Bouton court : YAOURT → BIERE → PATE → TERRE → DEMO.
3. DEMO : T° et LED bougent tout de suite.
4. Terminal Python collé à l’Arduino.
5. `chauffer` : relais + pompe (12 V).
6. `photo` : image webcam.

---

## 10. Fichiers du projet

| Fichier | Contenu |
|---|---|
| `arduino/fermentation_lab/fermentation_lab.ino` | Code Arduino |
| `raspberry/app.py` | Code Python (terminal + caméra) |
| `raspberry/requirements.txt` | `pyserial`, `opencv`, `numpy` |
| `raspberry/captures/` | Photos `photo` |
| `FERMIA.md` | Ce document |

---

## 11. Itération 2 (après, ALIVEcode)

Pas encore dans ces codes :

- Base **JSON** sur ALIVEcode
- Python `get_doc()` / `update_doc()`
- Interface IoT pour voir et modifier en direct
- Stats (moyenne T°, temps pompe, historique des profils)

---

## 12. Dépannage

| Problème | Piste |
|---|---|
| Pas de port COM | Câble USB données, driver CH340, autre port PC |
| LCD vide / noir | Tourner le **pot 10 kΩ** (contraste). Pin 5 RW au GND. Pas un sélecteur de recette. |
| Mauvais climat (ex. pâte à 42 °C) | Le labo ne détecte pas la cassette. Choisir le profil au **bouton** ou en Python. |
| `SONDE HS` / T° = -127 | 4,7 kΩ DATA–5V, fil jaune sur D2 |
| Air toujours MAUV / 1023 | MQ sur **5 V** (pas 12 V), AO bien sur **A0**, attendre 2–3 min (chauffe) |
| Python : accès COM refusé | Fermer le Moniteur série, bon `ARDUINO_PORT` |
| Caméra absente | `$env:CAMERA=1` |
| Pompe toujours ON | Polarité relais / `RELAIS_ACTIF_LOW` |
| Rien après `chauffer` | Arduino bien connecté, ligne `Envoyé à l'Arduino` |

---

## 12b. Dedans / dehors le bac

Le **labo** = l’air (ou l’eau) dans le bac. L’électronique reste **dehors**.

**Dedans :** cassette ; **petit** ventilo + petit radiateur (face intérieure du Peltier) ; **MQ** dans l’**air** (pas dans l’eau) ; pointe de la **sonde** ; **capteur d’eau** (plaques dans l’eau du bain-marie seulement) ; tuyaux de pompe (eau seulement) ; objectif **caméra** vers l’intérieur.

**Dehors :** **gros** ventilo + gros radiateur ; Arduino, plaque, LCD, bouton, LED, buzzer, relais, L298N ; moteur de la pompe ; Pi / PC ; **bloc 12 V**.

La **pastille** est dans le **mur** du bac (un côté dedans, un côté dehors), pas dans l’eau.

Le **bloc 12 V** = adaptateur secteur **12 V 5 A** (comme un chargeur). **Pas** l’USB du Pi ni du PC (5 V, trop faible). Sans ce bloc, LCD / sonde / Python marchent, mais Peltier / pompe / ventilos **ne bougent pas**.

RFID + voix : détail dans `raspberry/VOIX_RFID.md`. Au boot le labo est **ouvert** (`labOuvert = true`) pour les tests. Un badge autorisé **ferme** puis **rouvre**. La voix : « Fermia, ouvre le labo » → code (`code_acces.txt`, défaut 4218) → `UNLOCK`.

**Plus tard (pas encore dans le code)** : une IA prédit l’avancement / la fin ; une autre détecte les anomalies et alerte. Les deux liront `DATA;` dans `app.py`, sans remplacer l’Arduino.

---

## 13. Boîte labo fixe + cassette interchangeable

Le bac actuel reste le **labo**. On n’y touche plus (Arduino, LCD, relais, pompe, câbles).  
Ce qui change, c’est un **insert** (cassette) de même taille, posé dans le bac, avec la matière à fermenter.

```
+---------------- bac Fermia (fixe) ------------------+
|  Arduino, LCD, LED, bouton, relais, pompe, webcam   |
|  Trou couvercle : sonde + (option) airlock          |
|                                                     |
|   +---------- cassette (on l'enlève) ------------+  |
|   |  yaourt  OU  bière  OU  pâte  OU  terre      |  |
|   +----------------------------------------------+  |
+-----------------------------------------------------+
```

Empreinte identique pour les 4 cassettes (même longueur / largeur).  
La sonde DS18B20 se clipse dans un **trou standard** du couvercle : elle mesure l’air de la chambre, ou l’eau du bain-marie, pas forcément le yaourt lui-même.

**Deux types d’inserts :**

| Insert | Pour | Principe |
|---|---|---|
| **Bain-marie** (eau + pompe) | Yaourt, bière | La cassette est un bac d’eau. Le bocal / fermentateur flotte ou pose dedans. La pompe circule l’eau, pas la nourriture. |
| **Chambre sèche** (pas d’eau) | Pâte, terre | Plateau vide + éventuellement un petit bol d’eau à côté (humidité). Pompe **éteinte**. |

---

### Yaourt — 42 °C

**Entourage :** chaud, stable, propre, bocal couvert. Pas besoin d’airlock. Lumière inutile.

| Besoin        | Détail                                                         |
| ------------- | -------------------------------------------------------------- |
| Température   | 42 °C (lait + ferments)                                        |
| Humidité      | Faible enjeu si le pot est fermé                               |
| Air           | Couvercle : évite la contamination, pas étanche comme la bière |
| Cassette      | Bain-marie + **bocal en verre** alimentaire                    |
| Dans le bocal | Lait + yaourt nature (ferments)                                |
| Pompe         | ON en chauffe : circule **l’eau** autour du bocal              |
| Ventilo       | ON en froid                                                    |
|               |                                                                |

---

### Bière — 19 °C

**Entourage :** plus **frais**, **sombre**, **sans oxygène** après le démarrage, CO₂ qui doit sortir.

| Besoin      | Détail                                                                                  |
| ----------- | --------------------------------------------------------------------------------------- |
| Température | 19 °C (bière type ale). Si la pièce est à 22 °C, tu refroidis ; tu ne “cuis” pas.       |
| Humidité    | Peu important (liquide dans un seau)                                                    |
| Air         | **Anaérobie** : airlock (barboteur) sur le couvercle. Le gaz sort, l’air ne rentre pas. |
| Lumière     | Obscurité (bac opaque ou carton)                                                        |
| Cassette    | Bain-marie + **seau / bonbonne alimentaire** + airlock dans le trou du couvercle        |
| Pompe       | ON en chauffe autour du seau, **jamais** dans la bière                                  |
| Ventilo     | ON en froid                                                                             |
|             |                                                                                         |

---

### Pâte — 27 °C

**Entourage :** tiède et **humide**, de l’air, **surtout pas noyée**.

| Besoin      | Détail                                                                   |
| ----------- | ------------------------------------------------------------------------ |
| Température | 27 °C (pousse / levain)                                                  |
| Humidité    | Haute (~70–80 %) sinon croûte sèche                                      |
| Air         | Oui, bol non hermétique                                                  |
| Cassette    | **Chambre sèche** : saladier + linge humide, ou petit verre d’eau à côté |
| Pompe       | **OFF** (pas de bain-marie)                                              |
| Ventilo     | **ON** dès qu’il faut réguler (mélange l’air tiède)                      |
|             |                                                                          |

---

### Terre — 25 °C

**Entourage :** tiède, **humide mais pas détrempé**, **aéré** (microbes du sol respirent).

| Besoin      | Détail                                                                     |
| ----------- | -------------------------------------------------------------------------- |
| Température | 25 °C (sol vivant / compost doux, pas un compost à 55 °C)                  |
| Humidité    | Terre **froissable**, pas une soupe                                        |
| Air         | Trous dans la cassette ou couvercle légèrement ouvert                      |
| Cassette    | **Pot / barquette drainante**, éventuellement une soucoupe. Chambre sèche. |
| Pompe       | **OFF**                                                                    |
| Ventilo     | **ON** pour aérer la chambre                                               |
|             |                                                                            |

---

### Ce qui reste toujours sur le labo

Arduino, LCD, bouton, LED, relais, DS18B20 (clip), webcam, trou de sonde au couvercle.

### Ce que tu changes (4 cassettes)

1. Plateau bain-marie + bocal yaourt
2. Plateau bain-marie + seau + airlock bière
3. Plateau sec + bol + linge pâte
4. Plateau sec + pot drainant terre

Même rectangle, poignées, tu sors l’insert, tu rinces, tu mets l’autre. Le labo ne se démonte pas.

**Ensuite** tu sélectionnes le profil (bouton ou `yaourt` / `biere` / `pate` / `terre`). Changer la cassette **sans** changer le profil laisse l’ancienne consigne (ex. pâte encore à 42 °C yaourt).
