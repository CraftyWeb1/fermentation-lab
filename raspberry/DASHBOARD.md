# Tableau de bord tactile Fermia (ecran Raspberry Pi)

Meme idee que le dashboard ALIVEcode, mais **sur l ecran du Pi** : gros boutons, pas besoin d internet.

## Ecran

N importe quel ecran **HDMI tactile** 7" (1024x600) ou l ecran officiel **DSI 7"** (800x480).  
Branche-le comme ecran principal du Pi (clavier/souris optionnels).

## Lancer

```bash
cd raspberry
python3 app.py
```

Puis sur le Pi, ouvre Chromium : `http://127.0.0.1:8765`

Plein ecran kiosque :

```bash
chmod +x kiosque.sh
./kiosque.sh
```

`FERMIA_KIOSQUE=1` cache la fenetre camera pour laisser l ecran au dashboard. Les commandes (boutons, ALIVEcode, voix) marchent toujours.

Depuis un telephone sur le meme Wi‑Fi : `http://IP-DU-PI:8765`

## Boutons = memes commandes

Yaourt / biere / pate / terre / demo, chaud, froid, stop, auto, ventilo, silence, ouvrir, fermer.

Les valeurs (T°, consigne, pompe, air, eau, ouvert…) se rafraichissent toutes les 0,8 s, comme les Labels ALIVEcode.
