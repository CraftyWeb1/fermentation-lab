"""
FERMIA — FICHIER D ETUDE Python (examen)
Ce n est PAS le programme a lancer pour le labo.
Le vrai fichier : raspberry/app.py

Role du Python : USB vers Arduino + ALIVEcode + camera + gestes.
L Arduino garde le controle temps reel (temperature, relais, securite).
"""

# =============================================================================
# PARTIE 1 — IMPORTS
# =============================================================================
import os
import re
import sys
import threading          # plusieurs taches en meme temps (USB + clavier + camera)
import time
from pathlib import Path

import cv2                # camera + fenetre image
import numpy as np
import serial             # pyserial : parle a l Arduino sur USB
from serial.tools import list_ports

# =============================================================================
# PARTIE 2 — ETAT PARTAGE
# =============================================================================
# Un dictionnaire = photo du labo. Tous les threads lisent / ecrivent ici.
# Un Lock evite que deux threads ecrivent en meme temps (donnees corrompues).

etat = {
    "temp": None,          # C, vient de DATA;temp=
    "sp": None,            # consigne (setpoint)
    "mode": "AUTO",
    "peltier": "OFF",      # OFF / HEAT / COOL
    "pump": 0,             # 0 ou 1
    "fan": 0,
    "profile": "YAOURT",
    "connected": False,
}
etat_lock = threading.Lock()
arduino = None
arduino_lock = threading.Lock()

# Table recette -> consigne (doit matcher l Arduino)
CONSIGNES = {"YAOURT": 42.0, "BIERE": 19.0, "PATE": 27.0, "TERRE": 25.0, "DEMO": 18.0}

# Mot tape au clavier -> ligne envoyee a l Uno
COMMANDES = {
    "yaourt": "CMD;PROFILE=YAOURT",
    "chauffer": "CMD;PELTIER=HEAT",
    "refroidir": "CMD;PELTIER=COOL",
    "stop": "CMD;PELTIER=OFF",
    "auto": "CMD;MODE=AUTO",
    "von": "CMD;FAN=1",
    "voff": "CMD;FAN=0",
    "silence": "CMD;BUZZER=0",
}

# Gestes : on ignore le pouce sauf "pouce seul = buzzer off"
# n = nombre de doigts LEVES parmi index, majeur, annulaire, auriculaire
#   0 = poing        -> pompe off
#   1 = index        -> pompe on
#   2 = victoire     -> froid
#   3                -> chaud
#   4 = main ouverte -> stop climat (Peltier + ventilo)


# =============================================================================
# PARTIE 3 — TROUVER LE PORT USB
# =============================================================================
def trouver_port():
    """Windows : COM3. Mac : /dev/cu.usbmodemXXXX. JAMAIS debug-console."""
    force = os.environ.get("ARDUINO_PORT")
    if force:
        return force
    for port in list_ports.comports():
        nom = (port.device or "").lower()
        if "debug-console" in nom:
            continue                      # faux port Mac, pas l Arduino
        if "usbmodem" in nom or "com" in nom or "arduino" in nom:
            return port.device
    return None


# =============================================================================
# PARTIE 4 — ENVOYER UNE COMMANDE A L ARDUINO
# =============================================================================
def envoyer(commande: str) -> bool:
    """Ecrit une ligne USB. True si l Uno est branche."""
    with arduino_lock:
        if arduino is None:
            return False
        # \n = fin de ligne : l Arduino attend ce caractere dans lireSerie()
        arduino.write((commande.strip() + "\n").encode("utf-8"))
        arduino.flush()
        return True


def envoyer_ou_simuler(serie: str) -> None:
    """S il n y a pas d Uno, on met a jour etat[] quand meme (demo sans carte)."""
    if envoyer(serie):
        print("Envoye :", serie)
    else:
        print("Pas d Arduino — simulation :", serie)


# =============================================================================
# PARTIE 5 — PARSER UNE LIGNE DATA;
# =============================================================================
def parser_ligne(ligne: str) -> None:
    """
    Exemple recu :
    DATA;temp=17.31;sp=42.00;mode=AUTO;peltier=HEAT;pump=1;fan=1;profile=YAOURT
    regex ([a-z]+)=([^;]+)  ->  { 'temp': '17.31', 'sp': '42.00', ... }
    """
    if not ligne.startswith("DATA;"):
        return
    parties = dict(re.findall(r"([a-z]+)=([^;]+)", ligne.lower()))
    with etat_lock:
        etat["temp"] = float(parties["temp"]) if "temp" in parties else etat["temp"]
        etat["mode"] = parties.get("mode", etat["mode"]).upper()
        etat["peltier"] = parties.get("peltier", etat["peltier"]).upper()
        etat["pump"] = int(parties.get("pump", etat["pump"]))
        etat["fan"] = int(parties.get("fan", etat["fan"]))
        etat["profile"] = parties.get("profile", etat["profile"]).upper()
        etat["connected"] = True
    # Ensuite on pousse vers ALIVEcode (update_doc)


# =============================================================================
# PARTIE 6 — THREAD SERIE (tourne en arriere-plan)
# =============================================================================
def boucle_serie():
    """
    daemon=True : si tu quittes Python, ce thread meurt aussi.
    timeout=1 : readline n attend pas eternelleement.
    time.sleep(2) apres Serial() : l Uno reboot quand on ouvre le port.
    """
    global arduino
    while True:
        port = trouver_port()
        if not port:
            time.sleep(2)
            continue
        try:
            ser = serial.Serial(port, 9600, timeout=1)   # 9600 = comme Serial.begin
            time.sleep(2)
            with arduino_lock:
                arduino = ser
            print("Arduino connecte sur", port)
            while True:
                ligne = ser.readline().decode("utf-8", errors="ignore").strip()
                if ligne:
                    parser_ligne(ligne)
        except Exception as exc:
            print("Serie :", exc)
            arduino = None
            time.sleep(2)


# =============================================================================
# PARTIE 7 — ALIVEcode (un seul objet : fermia)
# =============================================================================
def document_aliot():
    """
    JSON envoye au tableau de bord.
    /doc/temperature  = champ que tu accroches a un Label / Gauge
    Un seul objet fermia, PAS un objet par LED.
    """
    with etat_lock:
        return {
            "/doc/temperature": etat["temp"],
            "/doc/consigne": etat["sp"],
            "/doc/profil": etat["profile"],
            "/doc/mode": etat["mode"],
            "/doc/peltier": etat["peltier"],
            "/doc/pompe": "ON" if etat["pump"] else "OFF",
            "/doc/ventilo": "ON" if etat["fan"] else "OFF",
            "/doc/geste": etat.get("geste", "AUCUN"),
        }


def demarrer_aliot():
    """
    config.ini DOIT etre a cote de app.py :

        [fermia]
        obj_id = ...
        auth_token = ...

    [fermia] = nom de l objet, PAS le nom du fichier Python.
    AliotObj("fermia") lit cette section.
    """
    from aliot.aliot_obj import AliotObj
    obj = AliotObj("fermia")

    def start():
        global iot
        iot = obj
        obj.update_doc(document_aliot())   # envoie les valeurs

    obj.on_start(callback=start)
    obj.on_action_recv("peltier", lambda data=None, *a, **k: envoyer_ou_simuler("CMD;PELTIER=HEAT"))
    # Dans le vrai app.py : mode, profil, pompe, ventilo, buzzer, chaud, froid, stop
    threading.Thread(target=obj.run, daemon=True).start()


iot = None


# =============================================================================
# PARTIE 8 — CAMERA
# =============================================================================
def ouvrir_camera():
    """
    Ordre : Picamera2 (Pi CSI) -> sinon OpenCV webcam.
    Windows : CAP_DSHOW. Mac : CAP_AVFOUNDATION.
    picamera2 absent sur PC/Mac = NORMAL.
    opencv-python-headless = PAS de webcam. Il faut opencv-python.
    """
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        return "cv", cap
    return "sim", None


# =============================================================================
# PARTIE 9 — GESTES (MediaPipe)
# =============================================================================
def leves_depuis_pts(pts, label="Right"):
    """
    21 points de la main. On compare des coordonnees NORMALISEES (0..1).
    Doigt leve si le bout (tip) est plus HAUT que l articulation (PIP)
    -> coord y plus PETITE (y=0 en haut de l image).

    Pouce : on compare x (gauche/droite), et ca depend de Right/Left.
    """
    pouce = pts[4].x < pts[3].x if label == "Right" else pts[4].x > pts[3].x
    index = pts[8].y < pts[6].y
    majeur = pts[12].y < pts[10].y
    annulaire = pts[16].y < pts[14].y
    auriculaire = pts[20].y < pts[18].y
    return [pouce, index, majeur, annulaire, auriculaire]


def commande_depuis_leves(leves):
    pouce, index, majeur, annulaire, auriculaire = leves
    n = int(index) + int(majeur) + int(annulaire) + int(auriculaire)
    if n == 0 and pouce:
        return "BUZZER OFF"          # pouce seul
    if n == 0:
        return "POMPE OFF"           # poing
    if n == 1 and index:
        return "POMPE ON"
    if n == 2 and index and majeur:
        return "PELTIER COOL"        # froid
    if n == 3:
        return "PELTIER HEAT"        # chaud
    if n >= 4:
        return "PELTIER OFF"         # stop : aussi FAN=0
    return None


def commander_geste(geste: str) -> None:
    table = {
        "POMPE ON": "CMD;PUMP=1",
        "POMPE OFF": "CMD;PUMP=0",
        "PELTIER COOL": "CMD;PELTIER=COOL",
        "PELTIER HEAT": "CMD;PELTIER=HEAT",
        "PELTIER OFF": "CMD;PELTIER=OFF",   # + MODE=MANUAL + FAN=0 dans le vrai code
        "BUZZER OFF": "CMD;BUZZER=0",
    }
    envoyer_ou_simuler(table[geste])


# Detection : on tient le geste FRAMES_GESTE images d affilee (~0,3 s)
# sinon un doigt mal compte enverrait une commande par erreur.
FRAMES_GESTE = 6

# MediaPipe :
#   anciennes versions : mp.solutions.hands.Hands  (detection_mains.py)
#   nouvelles versions : plus de "solutions" -> API tasks + fichier .task
# pip : python -m pip install mediapipe   (le python de TON venv)


# =============================================================================
# PARTIE 10 — ARCHITECTURE DES THREADS
# =============================================================================
def main():
    """
    Thread Arduino  : lit DATA; en boucle
    Thread terminal : input("> ")
    Thread ALIVEcode: obj.run()
    Thread principal: cv2.imshow  (OBLIGATOIRE sur Mac : fenetre dans le main)

    On ne lance PAS app.py et un autre script en meme temps (2 USB / 2 objets).
    """
    threading.Thread(target=boucle_serie, daemon=True).start()
    # boucle_gestes()  -> capturer, MediaPipe, imshow, waitKey
    # input() dans un autre thread


if __name__ == "__main__":
    print("Fichier d ETUDE. Pour le labo : python app.py")


# =============================================================================
# QUESTIONS D EXAMEN TYPES
# =============================================================================
# Q : Pourquoi threading ?
# R : USB + clavier + camera en meme temps. readline bloquerait le clavier.
#
# Q : Pourquoi Lock ?
# R : Deux threads ne doivent pas modifier etat[] ensemble.
#
# Q : Pourquoi 9600 ?
# R : Doit etre identique a Serial.begin(9600) cote Arduino.
#
# Q : Pourquoi un seul objet ALIVEcode "fermia" ?
# R : Un labo = un systeme. Temperature, pompe, Peltier bougent ensemble.
#
# Q : [fermia] dans config.ini c est app.py ?
# R : Non. C est le NOM DE L OBJET. On lance python app.py.
#
# Q : Ventilo branche direct sur chargeur 12 V ?
# R : Le code ne peut pas l eteindre. 12 V + -> relais COM, NO -> rouge, IN=D7.
#
# Q : Picamera2 sur Mac ?
# R : Module du Raspberry Pi seulement. Sur Mac/PC : OpenCV.
#
# Q : Qui fait la regulation ?
# R : Arduino (reguler + hysteresis). Python envoie des ordres, n a pas la sonde.
