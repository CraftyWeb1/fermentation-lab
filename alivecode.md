Le site du cours, c’est **ALIVEcode** → **tableau de bord IoT** ([alivecode.ca](https://alivecode.ca)). Fermia n’y est **pas encore branché** dans `app.py` (c’est l’itération 2). Voici les étapes **exactes du cours**, avec les noms Fermia.

Le cours sépare **objet IoT** (ton Pi / PC) et **projet IoT** (le dossier JSON + interface).

---

## A. Sur le site — créer l’objet (IoT-1)

1. Connecte-toi sur [https://alivecode.ca](https://alivecode.ca).
2. Menu gauche : **Tableau de bord IoT**.
3. Section **Objets IoT** → **Créer un nouvel Objet IoT**.
4. Nom : **Fermia** (description optionnelle : labo fermentation Arduino + Pi).
5. Sur la ligne de l’objet, copie :
   - icône **presse-papiers** = `obj_id` de3bd603-1643-434c-a3a3-02d8416fe392
   - icône **clé** = `auth_token`  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoiRGVmYXVsdCBBdXRoVG9rZW4iLCJvYmplY3RJZCI6ImRlM2JkNjAzLTE2NDMtNDM0Yy1hM2EzLTAyZDg0MTZmZTM5MiIsImlhdCI6MTc5NDM2NTk5MSwiZXhwIjo0OTQ3OTY1OTkxfQ.UXpRuhZLm83vYQx52IJdyG8WJSHpqEHUCcqI0YczKTc
   **Pas** ceux d’un autre objet.

L’objet reste **rouge / déconnecté** tant que Python ne tourne pas. Normal.

---

## B. Sur le PC — aliot-py (IoT-1)

PowerShell, dossier neuf (pas obligatoire dans `fermentation-lab`) :

```powershell
mkdir C:\Users\iouahid\Desktop\Objets-aliot
cd C:\Users\iouahid\Desktop\Objets-aliot
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install aliot-py
aliot init
aliot new fermia
```

Quand on demande le template : **normal**.

Tu dois avoir `config.ini` + dossier `fermia\fermia.py`.

Dans `config.ini`, section `[fermia]` :

```ini
[DEFAULT]
ws_url = wss://alivecode.ca/iotgateway/
api_url = https://alivecode.ca/api

[fermia]
obj_id = COLLE_ICI
auth_token = COLLE_ICI
main = fermia.py
```

Puis :

```powershell
aliot run fermia
```

Tu dois voir `Connected Object 'fermia'`.  
Rafraîchis le tableau de bord : objet **vert** « Connecté à ALIVEcode ».

---

## C. Sur le site — créer le projet (IoT-2)

1. Tableau de bord IoT → **Projets IoT** → **Nouveau Projet IoT**.
2. Nom : **Fermia**  
   Description : surveillance T°, profil, pompe, Peltier.  
   Visibilité : **Private**.  
   Interface : **Créateur uniquement** (pour l’instant).  
   Puis **Créer projet IoT**.
3. Dans le projet : onglet **Objets IoT** → **+** / **Ajouter un Objet IoT**.
4. Choisis **Fermia** → Ajouter.

Sans ça, `update_doc` n’a pas de document où écrire.

Invite Imane : **Paramètres** / collaborateurs (module IoT-2).

---

## D. Premier test JSON (IoT-2)

Dans le dossier `fermia`, fichier `test_projet.py` :

```python
from aliot.aliot_obj import AliotObj
from time import sleep

fermia = AliotObj("fermia")

def start():
    fermia.update_doc({
        "/doc/temperature": 16.2,
        "/doc/consigne": 42,
        "/doc/profil": "YAOURT",
        "/doc/peltier": "HEAT",
        "/doc/pompe": 0,
        "/doc/air": "BON",
    })
    sleep(5)
    fermia.stop()

fermia.on_start(callback=start)
fermia.run()
```

Dans `config.ini` : `main = test_projet.py`  
Puis `aliot run fermia`.

Sur le projet : **Document temps réel** → tu dois voir ces champs (pastille **EN DIRECT**).

Remets `main = fermia.py` après le test si tu veux.

Docs : [https://alivecode.ca/docs/aliot](https://alivecode.ca/docs/aliot)

---

## E. Plus tard : vraies valeurs Arduino

Là, `app.py` **n’envoie rien** à ALIVEcode. Quand tu voudras, on brancherait `update_doc({"/doc/temperature": etat["temp"], ...})` sur les lignes `DATA;...`. Passe en **Agent mode** si tu veux que je l’ajoute dans le code.

---

**Piège du cours :** `obj_id` / `auth_token` = **ton** objet Fermia, pas un exemple « Serre ». `AliotObj("fermia")` = le **nom de section** dans `config.ini`, pas le nom affiché sur le site.