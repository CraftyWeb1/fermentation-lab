from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parent
CAPTURES = ROOT / "captures"
CAPTURES.mkdir(exist_ok=True)

etat = {
    "temp": None,
    "sp": None,
    "mode": "AUTO",
    "peltier": "OFF",
    "pump": 0,
    "fan": 0,
    "air": None,
    "aq": "--",
    "water": None,
    "wet": 1,
    "profile": "YAOURT",
    "ok": 0,
    "lock": 0,
    "done": 0,
    "buzz": 0,
    "lcd": "",
    "connected": False,
    "geste": "AUCUN",
    "geste_confirme": "AUCUN",
}
etat_lock = threading.Lock()
print_lock = threading.Lock()
arduino = None
arduino_lock = threading.Lock()
camera_kind = "sim"
camera = None
camera_lock = threading.Lock()
stop_event = threading.Event()
DUREE_GESTE = 2.0
GESTES_MAINS = {0: "POMPE OFF", 1: "POMPE ON", 2: "PELTIER COOL", 5: "PELTIER OFF"}
AFFICHE_TOUTES_LES_S = 10.0
_t_affichage = 0.0
_cle_etat = ""
ALIOT_OBJ = os.environ.get("ALIOT_OBJ", "fermia")
iot = None
iot_lock = threading.Lock()
PROFILS_CYCLE = ["YAOURT", "BIERE", "PATE", "TERRE", "DEMO"]
PELTIER_CYCLE = ["OFF", "HEAT", "COOL"]
CONSIGNES = {
    "YAOURT": 42.0,
    "BIERE": 19.0,
    "PATE": 27.0,
    "TERRE": 25.0,
    "DEMO": 18.0,
}
COMMANDES = {
    "yaourt": "CMD;PROFILE=YAOURT",
    "yogurt": "CMD;PROFILE=YAOURT",
    "biere": "CMD;PROFILE=BIERE",
    "bierre": "CMD;PROFILE=BIERE",
    "beer": "CMD;PROFILE=BIERE",
    "pate": "CMD;PROFILE=PATE",
    "terre": "CMD;PROFILE=TERRE",
    "demo": "CMD;PROFILE=DEMO",
    "chauffer": "CMD;PELTIER=HEAT",
    "heat": "CMD;PELTIER=HEAT",
    "refroidir": "CMD;PELTIER=COOL",
    "cool": "CMD;PELTIER=COOL",
    "stop": "CMD;PELTIER=OFF",
    "off": "CMD;PELTIER=OFF",
    "auto": "CMD;MODE=AUTO",
    "manuel": "CMD;MODE=MANUAL",
    "manual": "CMD;MODE=MANUAL",
    "ouvrir": "CMD;UNLOCK",
    "open": "CMD;UNLOCK",
    "fermer": "CMD;LOCK",
    "lock": "CMD;LOCK",
    "fini": "CMD;DONE",
    "von": "CMD;FAN=1",
    "voff": "CMD;FAN=0",
    "ventilo_on": "CMD;FAN=1",
    "ventilo_off": "CMD;FAN=0",
}
AIDE = """
Commandes :
  yaourt / biere / pate / terre / demo
  chauffer / refroidir / stop / auto
  von / voff
  photo
  ouvrir / fermer
  fini
  aide
  quit
Gestes (tenir 2 s) :
  poing = pompe off
  1 doigt = pompe on
  2 doigts = froid
  main ouverte = peltier off
"""


def log(message: str) -> None:
    with print_lock:
        print(message, flush=True)


def trouver_port() -> str | None:
    force = os.environ.get("ARDUINO_PORT")
    if force:
        return force
    for candidat in ("/dev/cu.usbmodem2101",):
        if os.path.exists(candidat):
            return candidat
    ignores = ("debug-console", "bluetooth", "incoming", "wlan")
    bons = []
    for port in list_ports.comports():
        nom = (port.device or "").lower()
        desc = (port.description or "").lower()
        if any(x in nom or x in desc for x in ignores):
            continue
        texte = f"{nom} {desc}"
        if any(x in texte for x in ("arduino", "ch340", "usbserial", "usbmodem", "wchusbserial", "cp210")):
            bons.append(port.device)
            continue
        if nom.startswith("/dev/ttyacm") or nom.startswith("/dev/ttyusb"):
            bons.append(port.device)
    if bons:
        return bons[0]
    return None


def ligne_etat() -> str:
    with etat_lock:
        t = etat["temp"]
        sp = etat["sp"]
        lien = "Arduino" if etat["connected"] else "SIMU"
        temp = f"{t:5.2f} C" if t is not None else "  --  C"
        cons = f"{sp:5.2f} C" if sp is not None else "  --  C"
        pompe = "ON " if etat["pump"] else "OFF"
        ventilo = "ON " if etat["fan"] else "OFF"
        porte = "OUVERT" if not etat["lock"] else "FERME "
        fini = " FINI" if etat.get("done") else ""
        return (
            f"[{lien}] {porte}{fini} | T={temp} | consigne={cons} | {etat['mode']:6} | "
            f"{etat['peltier']:4} | pompe={pompe} | ventilo={ventilo} | "
            f"air={etat['aq']} {etat['air'] if etat['air'] is not None else '--'} | "
            f"eau={'--' if etat.get('water') is None else ('OK' if etat.get('wet', 1) else 'BASSE')} "
            f"{etat['water'] if etat.get('water') is not None else 'NC'} | {etat['profile']}"
        )


def valeur_ou_nc(brut: str):
    t = brut.strip().lower()
    if t in ("nc", "--", "-1", ""):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def document_aliot() -> dict:
    with etat_lock:
        return {
            "/doc/temperature": etat["temp"],
            "/doc/consigne": etat["sp"],
            "/doc/profil": etat["profile"],
            "/doc/mode": etat["mode"],
            "/doc/peltier": etat["peltier"],
            "/doc/pompe": "ON" if etat["pump"] else "OFF",
            "/doc/ventilo": "ON" if etat["fan"] else "OFF",
            "/doc/air": etat["aq"],
            "/doc/air_brut": etat["air"],
            "/doc/eau": etat["water"],
            "/doc/eau_ok": "OK" if etat.get("wet") else "BASSE",
            "/doc/ok": etat["ok"],
            "/doc/ouvert": 0 if etat["lock"] else 1,
            "/doc/fini": etat["done"],
            "/doc/arduino": 1 if etat["connected"] else 0,
            "/doc/buzzer": 2700 if etat.get("buzz") else 0,
            "/doc/lcd_message": etat.get("lcd")
            or f"{etat['profile']} {etat['mode']} {etat['peltier']}",
            "/doc/geste": etat.get("geste", "AUCUN"),
            "/doc/geste_confirme": etat.get("geste_confirme", "AUCUN"),
        }


def pousser_aliot() -> None:
    with iot_lock:
        obj = iot
    if obj is None:
        return
    try:
        obj.update_doc(document_aliot())
    except Exception as exc:
        log(f"ALIVEcode update_doc : {exc}")


def parser_ligne(ligne: str) -> None:
    if not ligne.startswith("DATA;"):
        return
    parties = dict(re.findall(r"([a-z]+)=([^;]+)", ligne.lower()))
    with etat_lock:
        if "temp" in parties:
            etat["temp"] = valeur_ou_nc(parties["temp"])
        if "sp" in parties:
            etat["sp"] = valeur_ou_nc(parties["sp"])
        etat["mode"] = parties.get("mode", etat["mode"]).upper()
        etat["peltier"] = parties.get("peltier", etat["peltier"]).upper()
        etat["pump"] = int(parties.get("pump", etat["pump"]))
        etat["fan"] = int(parties.get("fan", etat.get("fan", 0)))
        if "air" in parties:
            air = valeur_ou_nc(parties["air"])
            etat["air"] = None if air is None else int(air)
        etat["aq"] = parties.get("aq", etat["aq"]).upper()
        if "water" in parties:
            w = valeur_ou_nc(parties["water"])
            etat["water"] = None if w is None else int(w)
        if "wet" in parties:
            wet = valeur_ou_nc(parties["wet"])
            etat["wet"] = 1 if wet is None else int(wet)
        etat["profile"] = parties.get("profile", etat["profile"]).upper()
        etat["ok"] = int(parties.get("ok", 1))
        etat["lock"] = int(parties.get("lock", etat.get("lock", 1)))
        etat["done"] = int(parties.get("done", etat.get("done", 0)))
        if "buzz" in parties:
            etat["buzz"] = int(valeur_ou_nc(parties["buzz"]) or 0)
        m_lcd = re.search(r";lcd=(.*)$", ligne, re.I)
        if m_lcd:
            etat["lcd"] = " ".join(m_lcd.group(1).split())
        etat["connected"] = True
        evenement = (
            f"{etat['profile']}|{etat['mode']}|{etat['peltier']}|{etat['pump']}|"
            f"{etat['fan']}|{etat['lock']}|{etat['done']}|{etat['aq']}|"
            f"{etat.get('wet', 1)}|{etat.get('buzz', 0)}"
        )
    global _t_affichage, _cle_etat
    maintenant = time.time()
    if evenement != _cle_etat or (maintenant - _t_affichage) >= AFFICHE_TOUTES_LES_S:
        _t_affichage = maintenant
        _cle_etat = evenement
        log(ligne_etat())
        pousser_aliot()


def boucle_serie() -> None:
    global arduino
    while True:
        port = trouver_port()
        if not port:
            with etat_lock:
                etat["connected"] = False
            time.sleep(2)
            continue
        try:
            ser = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)
            with arduino_lock:
                arduino = ser
            log(f"Arduino connecté sur {port}")
            while True:
                ligne = ser.readline().decode("utf-8", errors="ignore").strip()
                if ligne:
                    parser_ligne(ligne)
        except Exception as exc:
            log(f"Série : {exc}")
            with arduino_lock:
                arduino = None
            with etat_lock:
                etat["connected"] = False
            time.sleep(2)


def extraire_cmd_aliot(data) -> str:
    if data is None:
        return ""
    if isinstance(data, (bytes, bytearray)):
        data = data.decode("utf-8", errors="ignore")
    if isinstance(data, str):
        texte = data.strip()
        if texte.startswith("{") or texte.startswith("["):
            try:
                data = json.loads(texte)
            except json.JSONDecodeError:
                return texte.upper()
        else:
            return texte.upper()
    if isinstance(data, dict):
        for cle in ("cmd", "mode", "value", "data", "profil", "profile", "selection", "option"):
            if data.get(cle) not in (None, ""):
                return str(data[cle]).strip().upper()
        if len(data) == 1:
            return str(next(iter(data.values()))).strip().upper()
    return str(data).strip().upper()


def envoyer(commande: str) -> bool:
    with arduino_lock:
        if arduino is None:
            return False
        try:
            arduino.write((commande.strip() + "\n").encode("utf-8"))
            arduino.flush()
            return True
        except (serial.SerialException, OSError) as exc:
            log(f"Erreur envoi Arduino : {exc}")
            return False


def appliquer_local(commande: str) -> None:
    with etat_lock:
        if "PROFILE=" in commande:
            profil = commande.split("PROFILE=", 1)[1].strip()
            etat["profile"] = profil
            etat["sp"] = CONSIGNES.get(profil, etat["sp"])
            etat["mode"] = "AUTO"
        elif "PELTIER=" in commande:
            etat["peltier"] = commande.split("PELTIER=", 1)[1].strip()
            etat["mode"] = "MANUAL"
            etat["pump"] = 1 if etat["peltier"] == "HEAT" else 0
            etat["fan"] = 1 if etat["peltier"] == "COOL" else 0
        elif "MODE=AUTO" in commande:
            etat["mode"] = "AUTO"
        elif "MODE=MANUAL" in commande:
            etat["mode"] = "MANUAL"
            etat["peltier"] = "OFF"
            etat["pump"] = 0
            etat["fan"] = 0
        elif "UNLOCK" in commande:
            etat["lock"] = 0
        elif "LOCK" in commande:
            etat["lock"] = 1
        elif "DONE" in commande:
            etat["done"] = 1
        elif "PUMP=" in commande:
            etat["pump"] = 0 if "PUMP=0" in commande else 1
        elif "FAN=" in commande:
            etat["fan"] = 0 if "FAN=0" in commande else 1
        elif "BUZZER=" in commande:
            etat["buzz"] = 0 if "BUZZER=0" in commande else 1
        if etat["temp"] is None:
            etat["temp"] = 20.0


def envoyer_ou_simuler(serie: str) -> None:
    if envoyer(serie):
        log(f"Envoyé à l'Arduino : {serie}")
        return
    appliquer_local(serie)
    log(f"Pas d'Arduino — simulation : {serie}")
    log(ligne_etat())
    pousser_aliot()


def data_aliot(data=None, *args):
    if data is None and args:
        return args[0]
    return data


def cycle_liste(actuel: str, liste: list[str]) -> str:
    actuel = (actuel or liste[0]).upper()
    try:
        return liste[(liste.index(actuel) + 1) % len(liste)]
    except ValueError:
        return liste[0]


def recevoir_cmd_mode(data=None, *args, **kwargs) -> None:
    data = data_aliot(data, *args)
    valeur = extraire_cmd_aliot(data)
    with etat_lock:
        actuel = (etat["mode"] or "AUTO").upper()
    if valeur in ("AUTO", "MODE=AUTO"):
        suivant = "AUTO"
    elif valeur in ("MANUAL", "MANUEL", "MODE=MANUAL"):
        suivant = "MANUAL"
    else:
        suivant = "MANUAL" if actuel != "MANUAL" else "AUTO"
    log(f"ALIVEcode mode : {actuel} -> {suivant}")
    envoyer_ou_simuler(f"CMD;MODE={suivant}")


def recevoir_cmd_profil(data=None, *args, **kwargs) -> None:
    data = data_aliot(data, *args)
    valeur = extraire_cmd_aliot(data)
    if valeur not in PROFILS_CYCLE:
        return
    with etat_lock:
        actuel = (etat["profile"] or "YAOURT").upper()
    if valeur == actuel:
        return
    log(f"ALIVEcode profil : {actuel} -> {valeur}")
    envoyer_ou_simuler(f"CMD;PROFILE={valeur}")


def recevoir_cmd_peltier(data=None, *args, **kwargs) -> None:
    data = data_aliot(data, *args)
    valeur = extraire_cmd_aliot(data)
    with etat_lock:
        actuel = (etat["peltier"] or "OFF").upper()
    if valeur in PELTIER_CYCLE:
        suivant = valeur
    elif valeur in ("CHAUFFER", "ON"):
        suivant = "HEAT"
    elif valeur in ("REFROIDIR",):
        suivant = "COOL"
    elif valeur in ("STOP",):
        suivant = "OFF"
    else:
        suivant = cycle_liste(actuel, PELTIER_CYCLE)
    log(f"ALIVEcode peltier : {actuel} -> {suivant}")
    envoyer_ou_simuler(f"CMD;PELTIER={suivant}")


def vers_01(data) -> int | None:
    if data is None:
        return None
    if isinstance(data, bool):
        return 1 if data else 0
    if isinstance(data, (int, float)):
        return 1 if data else 0
    s = extraire_cmd_aliot(data)
    if s in ("1", "TRUE", "ON", "OUI"):
        return 1
    if s in ("0", "FALSE", "OFF", "NON"):
        return 0
    if s in ("", "{}", "NONE", "[]"):
        return None
    try:
        return 1 if float(s) else 0
    except ValueError:
        return None


def recevoir_onoff(nom_etat: str, cmd: str, data=None, *args, **kwargs) -> None:
    data = data_aliot(data, *args)
    voulu = vers_01(data)
    with etat_lock:
        actuel = int(etat.get(nom_etat) or 0)
    suivant = (0 if actuel else 1) if voulu is None else voulu
    if suivant == actuel:
        return
    log(f"ALIVEcode {nom_etat} : {actuel} -> {suivant}")
    envoyer_ou_simuler(f"CMD;{cmd}={suivant}")


def recevoir_cmd_pompe(data=None, *args, **kwargs) -> None:
    recevoir_onoff("pump", "PUMP", data, *args, **kwargs)


def recevoir_cmd_ventilo(data=None, *args, **kwargs) -> None:
    recevoir_onoff("fan", "FAN", data, *args, **kwargs)


def recevoir_cmd_buzzer(data=None, *args, **kwargs) -> None:
    recevoir_onoff("buzz", "BUZZER", data, *args, **kwargs)


def recevoir_cmd_ventilo_on(data=None, *args, **kwargs) -> None:
    envoyer_ou_simuler("CMD;FAN=1")


def recevoir_cmd_ventilo_off(data=None, *args, **kwargs) -> None:
    envoyer_ou_simuler("CMD;FAN=0")


def recevoir_cmd_chaud(data=None, *args, **kwargs) -> None:
    envoyer_ou_simuler("CMD;PELTIER=HEAT")


def recevoir_cmd_froid(data=None, *args, **kwargs) -> None:
    envoyer_ou_simuler("CMD;PELTIER=COOL")


def recevoir_cmd_stop_peltier(data=None, *args, **kwargs) -> None:
    envoyer_ou_simuler("CMD;PELTIER=OFF")


def brancher_action(obj, action_id: str, callback) -> None:
    for nom in ("on_action_recv", "on_recv"):
        fn = getattr(obj, nom, None)
        if fn is None:
            continue
        essais = (
            lambda: fn(action_id, callback),
            lambda: fn(action_id=action_id, callback=callback),
            lambda: fn(action_id)(callback),
        )
        for essai in essais:
            try:
                essai()
                return
            except TypeError:
                continue


def brancher_doc(obj, chemin: str, callback) -> None:
    fn = getattr(obj, "listen_doc", None)
    if fn is None:
        return
    essais = (
        lambda: fn(chemin, callback),
        lambda: fn(path=chemin, callback=callback),
        lambda: fn(chemin)(callback),
    )
    for essai in essais:
        try:
            essai()
            return
        except TypeError:
            continue


def demarrer_aliot() -> None:
    global iot
    try:
        from aliot.aliot_obj import AliotObj
    except Exception:
        log("aliot-py absent : terminal seulement.")
        return

    obj = AliotObj(ALIOT_OBJ)

    def start() -> None:
        global iot
        with iot_lock:
            iot = obj
        log(f"ALIVEcode : objet {ALIOT_OBJ} connecté")
        pousser_aliot()

    obj.on_start(callback=start)
    brancher_action(obj, "cmd", recevoir_cmd_mode)
    brancher_action(obj, "change_button", recevoir_cmd_mode)
    brancher_action(obj, "mode", recevoir_cmd_mode)
    brancher_action(obj, "profil", recevoir_cmd_profil)
    brancher_action(obj, "change_selection", recevoir_cmd_profil)
    brancher_doc(obj, "/doc/profil", recevoir_cmd_profil)
    brancher_action(obj, "peltier", recevoir_cmd_peltier)
    brancher_action(obj, "chaud", recevoir_cmd_chaud)
    brancher_action(obj, "froid", recevoir_cmd_froid)
    brancher_action(obj, "heat", recevoir_cmd_chaud)
    brancher_action(obj, "cool", recevoir_cmd_froid)
    brancher_action(obj, "stop", recevoir_cmd_stop_peltier)
    brancher_action(obj, "pompe", recevoir_cmd_pompe)
    brancher_action(obj, "ventilo", recevoir_cmd_ventilo)
    brancher_action(obj, "ventilo_on", recevoir_cmd_ventilo_on)
    brancher_action(obj, "ventilo_off", recevoir_cmd_ventilo_off)
    brancher_action(obj, "buzzer", recevoir_cmd_buzzer)
    brancher_doc(obj, "/doc/pompe", recevoir_cmd_pompe)
    brancher_doc(obj, "/doc/ventilo", recevoir_cmd_ventilo)
    brancher_doc(obj, "/doc/buzzer", recevoir_cmd_buzzer)
    threading.Thread(target=obj.run, daemon=True, name="aliot").start()


def ouvrir_camera():
    global camera_kind, camera
    try:
        from picamera2 import Picamera2  # type: ignore[import-not-found]

        cam = Picamera2()
        try:
            cam.configure(cam.create_preview_configuration(main={"size": (640, 480)}))
        except Exception:
            cam.configure(cam.create_still_configuration(main={"size": (640, 480)}))
        cam.start()
        time.sleep(0.4)
        camera_kind, camera = "pi", cam
        log("Caméra Pi : OK")
        return
    except Exception as exc:
        log(f"Picamera2 indisponible ({exc})")

    index = int(os.environ.get("CAMERA", "0"))
    if sys.platform == "win32":
        backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]
    elif sys.platform == "darwin":
        backends = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
    else:
        backends = [cv2.CAP_ANY]
    for backend in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera_kind, camera = "cv", cap
            log(f"Caméra OpenCV : OK (index {index})")
            return
        cap.release()

    camera_kind, camera = "sim", None
    log("Caméra absente : photos simulées")


def frame_simulation() -> np.ndarray:
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (22, 36, 28)
    with etat_lock:
        t = etat["temp"]
        pelt = etat["peltier"]
        profil = etat["profile"]
    cv2.putText(img, "Simulation camera", (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (180, 220, 190), 2)
    txt = f"{profil}  T={t:.1f}C  {pelt}" if t is not None else f"{profil}  pas de sonde"
    cv2.putText(img, txt, (40, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    return img


def capturer() -> np.ndarray:
    if camera_kind == "pi":
        with camera_lock:
            rgb = camera.capture_array()
        frame = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    elif camera_kind == "cv":
        with camera_lock:
            ok, frame = camera.read()
        if not ok:
            frame = frame_simulation()
    else:
        frame = frame_simulation()

    with etat_lock:
        t = etat["temp"]
        sp = etat["sp"]
        pelt = etat["peltier"]
        profil = etat["profile"]
        mode = etat["mode"]
    ligne = f"{profil} {mode}"
    ligne += f"  T={t:.1f}C" if t is not None else "  T=--"
    if sp is not None:
        ligne += f"  consigne={sp:.0f}C"
    ligne += f"  Peltier={pelt}"
    cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (0, 0, 0), -1)
    cv2.putText(frame, ligne, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 255, 230), 2)
    return frame


def prendre_photo() -> None:
    frame = capturer()
    nom = CAPTURES / f"camera_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    cv2.imwrite(str(nom), frame)
    log(f"Photo enregistrée : {nom}")


def executer(saisie: str) -> bool:
    cmd = saisie.strip().lower()
    if not cmd:
        return True
    if cmd in ("quit", "q", "exit"):
        return False
    if cmd in ("aide", "help", "?"):
        log(AIDE)
        return True
    if cmd == "photo":
        prendre_photo()
        return True
    if cmd.startswith("sp "):
        try:
            valeur = float(cmd.split()[1])
        except (IndexError, ValueError):
            log("Usage : sp 19")
            return True
        serie = f"CMD;SP={valeur}"
    else:
        serie = COMMANDES.get(cmd)
        if not serie:
            log("Commande inconnue. Tape : aide")
            return True

    if envoyer(serie):
        log(f"Envoyé à l'Arduino : {serie}")
    else:
        appliquer_local(serie)
        log(f"Pas d'Arduino — simulation : {serie}")
        log(ligne_etat())
        pousser_aliot()
    return True


class DetecteurInline:
    def __init__(self):
        self.ok = False
        self._mains = None
        try:
            import mediapipe as mp

            self._mp = mp
            self._mains = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.6,
            )
            self._dessin = mp.solutions.drawing_utils
            self._liens = mp.solutions.hands.HAND_CONNECTIONS
            self.ok = True
        except Exception:
            self.ok = False

    def fermer(self) -> None:
        if self._mains is not None:
            self._mains.close()

    def analyser(self, frame_bgr: np.ndarray) -> dict:
        vide = {"doigts": 0, "main": False, "landmarks": None}
        if not self.ok or frame_bgr is None:
            return vide
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self._mains.process(rgb)
        rgb.flags.writeable = True
        if not res.multi_hand_landmarks:
            return vide
        lm = res.multi_hand_landmarks[0]
        label = "Right"
        if res.multi_handedness:
            label = res.multi_handedness[0].classification[0].label
        pts = lm.landmark
        if label == "Right":
            pouce = pts[4].x < pts[3].x
        else:
            pouce = pts[4].x > pts[3].x
        doigts = [
            pouce,
            pts[8].y < pts[6].y,
            pts[12].y < pts[10].y,
            pts[16].y < pts[14].y,
            pts[20].y < pts[18].y,
        ]
        return {"doigts": sum(doigts), "main": True, "landmarks": lm}

    def dessiner(self, frame_bgr: np.ndarray, info: dict) -> np.ndarray:
        if info.get("landmarks") is not None:
            self._dessin.draw_landmarks(frame_bgr, info["landmarks"], self._liens)
        return frame_bgr


def creer_detecteur():
    try:
        from detection_mains import DetecteurMains

        det = DetecteurMains()
        if det.ok:
            log("MediaPipe : DetecteurMains")
            return "cours", det
    except Exception:
        pass
    try:
        from quickhands import HandDetector

        log("MediaPipe : quickhands")
        return "quickhands", HandDetector(maxHands=1)
    except Exception:
        pass
    det = DetecteurInline()
    if det.ok:
        log("MediaPipe : integre dans app.py")
        return "cours", det
    log("MediaPipe absent : pip install mediapipe")
    return None, None


def lire_main(kind, det, image):
    if kind == "cours":
        info = det.analyser(image)
        image = det.dessiner(image, info)
        if not info.get("main"):
            return None, None, image
        return info.get("doigts"), GESTES_MAINS.get(info.get("doigts")), image
    mains, image = det.findHands(image)
    if not mains:
        return None, None, image
    n = det.fingersUp(mains[0]).count(1)
    return n, GESTES_MAINS.get(n), image


def publier_geste() -> None:
    with iot_lock:
        obj = iot
    if obj is None:
        return
    with etat_lock:
        doc = {
            "/doc/geste": etat.get("geste", "AUCUN"),
            "/doc/geste_confirme": etat.get("geste_confirme", "AUCUN"),
        }
    try:
        obj.update_doc(doc)
    except Exception as exc:
        log(f"ALIVEcode geste : {exc}")


def commander_geste(geste: str) -> None:
    commandes = {
        "POMPE ON": "CMD;PUMP=1",
        "POMPE OFF": "CMD;PUMP=0",
        "PELTIER COOL": "CMD;PELTIER=COOL",
        "PELTIER OFF": "CMD;PELTIER=OFF",
    }
    commande = commandes[geste]
    if envoyer(commande):
        log(f"Geste -> Arduino : {commande}")
    else:
        appliquer_local(commande)
        log(f"Geste -> simulation : {commande}")
        pousser_aliot()
    with etat_lock:
        etat["geste_confirme"] = geste
    publier_geste()


def boucle_gestes() -> None:
    if camera_kind == "sim":
        log("Camera absente : pas de gestes")
        return
    kind, det = creer_detecteur()
    if det is None:
        return
    dernier = None
    debut = time.monotonic()
    deja_execute = False
    log("Mains : 0=pompe off  1=pompe on  2=froid  5=peltier off  (tenir 2 s)")
    log("Q ferme la fenetre camera")
    try:
        while not stop_event.is_set():
            image = capturer()
            image = cv2.flip(image, 1)
            nombre, geste, image = lire_main(kind, det, image)
            if geste != dernier:
                dernier = geste
                debut = time.monotonic()
                deja_execute = False
            nouveau = geste or "AUCUN"
            maintenant = time.monotonic()
            changer = False
            with etat_lock:
                if nouveau != etat.get("geste"):
                    etat["geste"] = nouveau
                    changer = True
            if changer:
                publier_geste()
            if geste and not deja_execute and (maintenant - debut) >= DUREE_GESTE:
                commander_geste(geste)
                deja_execute = True
            with etat_lock:
                pompe = "ON" if etat["pump"] else "OFF"
                peltier = etat["peltier"]
                confirme = etat.get("geste_confirme", "AUCUN")
                connecte = etat["connected"]
            cv2.rectangle(image, (0, 42), (image.shape[1], 190), (25, 25, 25), -1)
            lignes = [
                f"FERMIA - {'ARDUINO' if connecte else 'SIMULATION'}",
                f"Doigts: {nombre if nombre is not None else '-'}  Geste: {nouveau}",
                f"Pompe: {pompe}  Peltier: {peltier}",
                f"Confirme: {confirme}",
            ]
            for i, ligne in enumerate(lignes):
                cv2.putText(
                    image,
                    ligne,
                    (10, 65 + i * 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.57,
                    (230, 255, 230),
                    2,
                )
            if geste and not deja_execute:
                reste = max(0, DUREE_GESTE - (maintenant - debut))
                cv2.putText(
                    image,
                    f"Maintenir: {reste:.1f}s",
                    (10, 235),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 200, 255),
                    2,
                )
            cv2.imshow("Fermia - mains", image)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                log("Fenetre camera fermee. Tape quit pour arreter.")
                break
    finally:
        if kind == "cours" and hasattr(det, "fermer"):
            det.fermer()
        cv2.destroyAllWindows()


def boucle_terminal() -> None:
    while not stop_event.is_set():
        try:
            saisie = input("> ")
        except (EOFError, KeyboardInterrupt):
            stop_event.set()
            return
        if not executer(saisie):
            stop_event.set()
            return


def main() -> None:
    log("Fermia")
    log(AIDE)
    ouvrir_camera()
    demarrer_aliot()
    threading.Thread(target=boucle_serie, daemon=True, name="arduino").start()
    threading.Thread(target=boucle_terminal, daemon=True, name="terminal").start()
    time.sleep(0.3)
    log("Pret. Tape les commandes ici. Fenetre camera = gestes.")
    try:
        boucle_gestes()
        while not stop_event.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        log("\nArret.")
    finally:
        stop_event.set()
        log("Termine.")


if __name__ == "__main__":
    main()
