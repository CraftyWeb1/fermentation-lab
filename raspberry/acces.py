"""
Acces Fermia : badge RFID (RC-522 sur le Pi) et voix (ReSpeaker).
Les deux cles ouvrent la meme serrure : CMD;UNLOCK / CMD;LOCK.
L IA n est pas ici.
"""

from __future__ import annotations

import os
import re
import threading
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FICHIER_BADGES = ROOT / "badges.txt"
FICHIER_CODE = ROOT / "code_acces.txt"

CHIFFRES = {
    "zero": "0",
    "un": "1",
    "une": "1",
    "deux": "2",
    "trois": "3",
    "quatre": "4",
    "cinq": "5",
    "six": "6",
    "sept": "7",
    "huit": "8",
    "neuf": "9",
}

PHRASES_OUVRIR = (
    "ouvre le labo",
    "ouvrir le labo",
    "ouvre fermia",
    "ouvrir fermia",
    "ouvre",
    "ouvrir",
    "open",
)
PHRASES_FERMER = (
    "ferme le labo",
    "fermer le labo",
    "ferme fermia",
    "fermer fermia",
    "ferme",
    "fermer",
    "lock",
)
COMMANDES_VOIX = (
    ("yaourt", "yaourt"),
    ("yogurt", "yaourt"),
    ("biere", "biere"),
    ("bière", "biere"),
    ("pate", "pate"),
    ("pâte", "pate"),
    ("terre", "terre"),
    ("demo", "demo"),
    ("démo", "demo"),
    ("chauffe", "chauffer"),
    ("chauffer", "chauffer"),
    ("chaud", "chauffer"),
    ("froid", "refroidir"),
    ("refroidir", "refroidir"),
    ("stop", "stop"),
    ("arrete", "stop"),
    ("arrête", "stop"),
    ("silence", "silence"),
    ("auto", "auto"),
)


def _sans_accent(texte: str) -> str:
    nfd = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def charger_badges() -> set[str]:
    uids: set[str] = set()
    if not FICHIER_BADGES.exists():
        return uids
    for ligne in FICHIER_BADGES.read_text(encoding="utf-8").splitlines():
        ligne = ligne.split("#", 1)[0].strip().replace(" ", "").upper()
        if ligne:
            uids.add(ligne)
    return uids


def charger_code() -> str:
    env = os.environ.get("FERMIA_CODE", "").strip()
    if env:
        return env
    if FICHIER_CODE.exists():
        for ligne in FICHIER_CODE.read_text(encoding="utf-8").splitlines():
            ligne = ligne.split("#", 1)[0].strip()
            if ligne:
                return ligne
    return "4218"


def extraire_chiffres(texte: str) -> str:
    t = _sans_accent(texte)
    for mot, chiffre in CHIFFRES.items():
        t = re.sub(rf"\b{mot}\b", chiffre, t)
    return re.sub(r"\D", "", t)


def badge_autorise(uid: str, uids: set[str]) -> bool:
    return uid.replace(" ", "").upper() in uids


class ControleAcces:
    def __init__(self, log, executer, noter):
        self.log = log
        self.executer = executer
        self.noter = noter
        self.stop = threading.Event()
        self.attente_code = False
        self.essais = 0
        self.lock = threading.Lock()
        self._labo_ouvert = True

    def dire(self, message: str) -> None:
        self.log(f"Fermia : {message}")
        try:
            import pyttsx3

            moteur = pyttsx3.init()
            moteur.say(message)
            moteur.runAndWait()
        except Exception:
            pass

    def ouvrir(self, source: str) -> None:
        self._labo_ouvert = True
        self.noter(source)
        self.executer("ouvrir")
        self.attente_code = False
        self.essais = 0
        self.dire("Labo ouvert")

    def fermer(self, source: str) -> None:
        self._labo_ouvert = False
        self.noter(source)
        self.executer("fermer")
        self.attente_code = False
        self.dire("Labo ferme")

    def traiter_badge(self, uid: str) -> None:
        uid = uid.replace(" ", "").upper()
        uids = charger_badges()
        if not uids:
            self.log(f"RFID UID (ajoute-le dans badges.txt) : {uid}")
            return
        if not badge_autorise(uid, uids):
            self.log(f"RFID refuse : {uid}")
            self.dire("Badge refuse")
            return
        self.log(f"RFID OK : {uid}")
        if getattr(self, "_labo_ouvert", True):
            self._labo_ouvert = False
            self.fermer("RFID")
        else:
            self._labo_ouvert = True
            self.ouvrir("RFID")

    def traiter_parole(self, brut: str) -> None:
        texte = _sans_accent(brut.strip())
        if not texte:
            return
        self.log(f"Voix : {brut}")

        if self.attente_code:
            code = extraire_chiffres(texte)
            attendu = charger_code()
            if code and code == attendu:
                self.ouvrir("VOIX")
            else:
                self.essais += 1
                self.dire("Code refuse")
                if self.essais >= 3:
                    self.attente_code = False
                    self.essais = 0
                    self.dire("Trop d essais")
            return

        if "fermia" in texte or os.environ.get("FERMIA_VOIX_SANS_NOM") == "1":
            corps = texte.replace("fermia", " ").strip()
        else:
            corps = texte
            if not any(p in texte for p in PHRASES_OUVRIR + PHRASES_FERMER):
                return

        if any(p in corps or p in texte for p in PHRASES_OUVRIR):
            self.attente_code = True
            self.essais = 0
            self.dire("Code d acces ?")
            return
        if any(p in corps or p in texte for p in PHRASES_FERMER):
            self.fermer("VOIX")
            return
        for mot, cmd in COMMANDES_VOIX:
            if mot in corps or mot in texte:
                self.executer(cmd)
                return

    def boucle_rfid(self) -> None:
        try:
            from mfrc522 import SimpleMFRC522
        except Exception as exc:
            self.log(f"RFID inactif ({exc}). pip install mfrc522 spidev  (sur le Pi)")
            return
        lecteur = SimpleMFRC522()
        self.log("RFID : approche un badge")
        dernier = ""
        t_dernier = 0.0
        while not self.stop.is_set():
            try:
                uid = None
                if hasattr(lecteur, "read_id_no_block"):
                    uid = lecteur.read_id_no_block()
                else:
                    ident, _texte = lecteur.read()
                    uid = ident
                if uid:
                    texte_uid = hex(int(uid))[2:].upper() if isinstance(uid, int) else str(uid).upper()
                    maintenant = time.monotonic()
                    if texte_uid != dernier or (maintenant - t_dernier) > 3:
                        dernier = texte_uid
                        t_dernier = maintenant
                        self.traiter_badge(texte_uid)
                else:
                    time.sleep(0.25)
            except Exception as exc:
                self.log(f"RFID : {exc}")
                time.sleep(1)

    def boucle_voix(self) -> None:
        try:
            import speech_recognition as sr
        except Exception as exc:
            self.log(f"Voix inactive ({exc}). pip install SpeechRecognition pyaudio")
            return
        reco = sr.Recognizer()
        index = os.environ.get("RECO_DEVICE")
        kwargs = {}
        if index is not None:
            kwargs["device_index"] = int(index)
        try:
            micro = sr.Microphone(**kwargs)
        except Exception as exc:
            self.log(f"ReSpeaker / micro introuvable ({exc})")
            return
        self.log("Voix : dis  Fermia ouvre le labo")
        with micro as source:
            try:
                reco.adjust_for_ambient_noise(source, duration=0.6)
            except Exception:
                pass
        while not self.stop.is_set():
            try:
                with micro as source:
                    audio = reco.listen(source, timeout=4, phrase_time_limit=6)
                try:
                    texte = reco.recognize_google(audio, language="fr-FR")
                except Exception:
                    continue
                self.traiter_parole(texte)
            except Exception:
                continue


def demarrer_acces(log, executer, noter, stop_event) -> ControleAcces:
    ctrl = ControleAcces(log, executer, noter)
    ctrl.stop = stop_event
    threading.Thread(target=ctrl.boucle_rfid, daemon=True, name="rfid").start()
    threading.Thread(target=ctrl.boucle_voix, daemon=True, name="voix").start()
    return ctrl
