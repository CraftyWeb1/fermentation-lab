from __future__ import annotations

import cv2
import numpy as np

INDEX_POUCE = 4
INDEX_INDEX = 8
INDEX_MAJEUR = 12
INDEX_ANNULAIRE = 16
INDEX_AURICULAIRE = 20


class DetecteurMains:
    def __init__(self, confiance: float = 0.5):
        self.ok = False
        self._mains = None
        self._dessin = None
        self._liens = None
        try:
            import mediapipe as mp

            self._mp = mp
            self._mains = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=confiance,
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
        vide = {"geste": None, "doigts": 0, "main": False}
        if not self.ok or frame_bgr is None:
            return vide
        rgb = np.ascontiguousarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        res = self._mains.process(rgb)
        if not res.multi_hand_landmarks:
            return vide
        lm = res.multi_hand_landmarks[0]
        label = "Right"
        if res.multi_handedness:
            label = res.multi_handedness[0].classification[0].label
        doigts = self.doigts_leves(lm, label)
        geste = self.reconnaitre(doigts)
        return {
            "geste": geste,
            "doigts": sum(doigts),
            "leves": doigts,
            "main": True,
            "landmarks": lm,
        }

    def doigts_leves(self, lm, label: str) -> list[bool]:
        pts = lm.landmark
        if label == "Right":
            pouce = pts[INDEX_POUCE].x < pts[INDEX_POUCE - 1].x
        else:
            pouce = pts[INDEX_POUCE].x > pts[INDEX_POUCE - 1].x
        index = pts[INDEX_INDEX].y < pts[INDEX_INDEX - 2].y
        majeur = pts[INDEX_MAJEUR].y < pts[INDEX_MAJEUR - 2].y
        annulaire = pts[INDEX_ANNULAIRE].y < pts[INDEX_ANNULAIRE - 2].y
        auriculaire = pts[INDEX_AURICULAIRE].y < pts[INDEX_AURICULAIRE - 2].y
        return [pouce, index, majeur, annulaire, auriculaire]

    def reconnaitre(self, doigts: list[bool]) -> str | None:
        pouce, index, majeur, annulaire, auriculaire = doigts
        autres = [index, majeur, annulaire, auriculaire]
        n = sum(autres)
        if n == 0:
            return "POING"
        if n == 1 and index:
            return "1"
        if n == 2 and index and majeur:
            return "2"
        if n == 3 and index and majeur and annulaire:
            return "3"
        if n >= 4 or (n >= 3 and pouce):
            return "OUVERTE"
        return None

    def dessiner(self, frame_bgr: np.ndarray, info: dict) -> np.ndarray:
        if info.get("landmarks") is not None and self._dessin is not None:
            self._dessin.draw_landmarks(
                frame_bgr,
                info["landmarks"],
                self._liens,
            )
        return frame_bgr
