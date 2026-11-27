# Acces Fermia : RFID + voix ReSpeaker

Meme serrure Arduino : `CMD;UNLOCK` / `CMD;LOCK`.
Deux cles : **badge** ou **voix + code**. L IA n est pas dans cette iteration.

**Rien de tout ca sur l Uno** (plus de pin libre, SPI deja pris par le LCD). ReSpeaker + RC-522 = **Raspberry Pi**. Le Pi envoie `UNLOCK` / `LOCK` en USB.

## RFID (RC-522 sur le Raspberry Pi, 3,3 V)

Voir le tableau de broches dans FERMIA.md § 4.9.

```bash
sudo raspi-config   # Interface → SPI → Enable
pip install mfrc522 spidev
python app.py
```

1. Approche une carte : le terminal affiche l UID
2. Colle l UID dans `badges.txt` (une ligne, sans espaces)
3. Relance. Badge autorise = **toggle** ouvrir / fermer

Sans module : `ouvrir` / `fermer` au clavier.

## Voix (ReSpeaker sur le Pi)

HAT I2S, **pas** sur l Arduino, **pas** sur le Mac.

**Piece OK :** Keyestudio / Seeed **ReSpeaker 2 micros** pour Pi 3/4 (chapeau GPIO, LEFT/RIGHT, jack casque). Clone Keyestudio du HAT officiel = bon pour Fermia.

**Pas un remplacement :**
- **JQ6500** = lecteur MP3 serie. Il **joue** un fichier, il **n ecoute pas**.
- **ISD1820** (plaque rouge micro + mini HP) = 10 s d enregistrement, pas de reconnaissance.
- **L293D** (plaque verte) = pont H moteur, tu as deja le L298N.

Sans ReSpeaker : micro USB (ou micro du Mac pour tester). `RECO_DEVICE=1 python app.py`

```bash
pip install SpeechRecognition pyaudio pyttsx3
python app.py
```

Dialogue :

1. « **Fermia, ouvre le labo** »
2. Fermia : « Code d acces ? »
3. Toi : « 4 2 1 8 » (chiffres, ou quatre deux un huit)
4. Si le code = `code_acces.txt` → labo **ouvert**
5. « **Fermia, ferme le labo** » → ferme (pas de code)

Autres phrases (labo ouvert) : chauffe, froid, stop, yaourt, biere, pate, terre, demo, silence.

Fichier `code_acces.txt` (copie de `code_acces.txt.exemple`). Defaut **4218**.
Ou : `FERMIA_CODE=1234`

Micro pas le ReSpeaker : `RECO_DEVICE=1 python app.py`

Sans micro / sans RFID, Python continue (gestes, ALIVEcode, terminal).
