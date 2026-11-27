# Fermia — fermentation intelligente

Fermia est un laboratoire de fermentation intelligente. Un Arduino régule la température du bain-marie (yaourt, bière, pâte, terre) avec une pastille Peltier, des ventilos, une pompe et des capteurs, pendant qu’un Raspberry Pi gère la caméra, le tableau de bord, les gestes, le badge RFID et la voix. Le labo s’ouvre avec un badge ou « Fermia, ouvre le labo » + code ; on le commande aussi depuis ALIVEcode.

L’IA (prédiction de fin + anomalies) vient **plus tard**.

Guide : **[FERMIA.md](FERMIA.md)** (présentation, câblage ventilos/Peltier, pins Uno pleines) · accès : **[raspberry/VOIX_RFID.md](raspberry/VOIX_RFID.md)** · écran Pi : **[raspberry/DASHBOARD.md](raspberry/DASHBOARD.md)**

- Arduino : `arduino/fermentation_lab/fermentation_lab.ino`
- Python : `raspberry/app.py`
