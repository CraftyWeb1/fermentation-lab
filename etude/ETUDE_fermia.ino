/*
 * FERMIA — FICHIER D ETUDE Arduino (examen)
 * Ce n est PAS le sketch a televerser pour le labo.
 * Le vrai sketch : arduino/fermentation_lab/fermentation_lab.ino
 *
 * Role de l Uno : capteurs + actionneurs en temps reel.
 * Le PC / Pi envoie des CMD;  et recoit des DATA;  a 9600 bauds.
 */

#include <OneWire.h>              // bus 1 fil pour la sonde DS18B20
#include <DallasTemperature.h>    // lecture de la temperature en C
#include <LiquidCrystal.h>        // LCD 1602 (16 colonnes, 2 lignes)

// Broches LCD : RS, E, D4, D5, D6, D7  ->  D8 a D13
LiquidCrystal lcd(8, 9, 10, 11, 12, 13);

// ---------- BROCHES (a reciter) ----------
const uint8_t PIN_DS18B20 = 2;     // sonde temperature (pull-up 4,7 kOhm)
const uint8_t PIN_BOUTON = 3;      // 1 seul bouton : court = profil, long = AUTO/MANUEL
const uint8_t PIN_LED_R = 4;       // LED RVB cathode commune : rouge
const uint8_t PIN_LED_G = A2;      // vert
const uint8_t PIN_LED_B = A3;      // bleu
const uint8_t PIN_BUZZER = A4;     // buzzer (tone)
const uint8_t PIN_POMPE = 5;       // relais pompe
const uint8_t PIN_VENTILO = 7;     // relais ventilos — le 12 V DOIT passer par ce relais
const uint8_t PIN_PELTIER_IN1 = 6; // L298N IN1 = CHAUD
const uint8_t PIN_PELTIER_IN2 = A1;// L298N IN2 = FROID
const uint8_t PIN_MQ = A0;         // MQ-135 air (analogique 0..1023)
const uint8_t PIN_EAU = A5;        // niveau d eau bain-marie

// ---------- SEUILS ----------
const int SEUIL_EAU_OK = 250;      // en dessous = eau trop basse, pompe interdite
const bool RELAIS_ACTIF_LOW = true; // beaucoup de modules relais : ON = pin LOW
const int SEUIL_AIR_BON = 250;     // MQ < 250  -> air BON
const int SEUIL_AIR_MAUV = 450;    // MQ >= 450 -> air MAUV
const float HYSTERESIS = 0.5;      // evite que le Peltier oscille autour de la consigne
const float TEMP_MAX_SECURITE = 45.0;
const float TEMP_MIN_SECURITE = 3.0;

const unsigned long INTERVALLE_SONDE_MS = 1000;   // lit capteurs 1 fois / s
const unsigned long INTERVALLE_LCD_MS = 400;
const unsigned long INTERVALLE_SERIE_MS = 10000;  // envoie DATA; toutes les 10 s
const unsigned long ANTIREBOND_MS = 40;           // ignore les rebonds du bouton
const unsigned long APPUI_LONG_MS = 800;          // 0,8 s = appui long

// Durees de fermentation (YAOURT 6 h, PATE 75 min, DEMO 20 s pour le jury)
const unsigned long DUREE_YAOURT_MS = 6UL * 3600UL * 1000UL;
const unsigned long DUREE_PATE_MS = 75UL * 60UL * 1000UL;
const unsigned long DUREE_DEMO_MS = 20UL * 1000UL;
const unsigned long BIERE_CALME_MS = 3UL * 60UL * 1000UL;
const unsigned long BIERE_MIN_MS = 60UL * 1000UL;
const unsigned long VIDANGE_MAX_MS = 90UL * 1000UL;

// enum = liste de constantes nommees (plus clair que 0, 1, 2)
enum Profile { PROF_YAOURT, PROF_BIERE, PROF_PATE, PROF_TERRE, PROF_DEMO };
enum Peltier { PELT_OFF, PELT_HEAT, PELT_COOL };
enum RaisonLed {
  LED_FERME, LED_FINI, LED_SONDE, LED_EAU, LED_AIR, LED_CLIM, LED_PELT_OFF
};

OneWire oneWire(PIN_DS18B20);
DallasTemperature sonde(&oneWire);

// ---------- ETAT DU LABO (variables globales) ----------
Profile profil = PROF_YAOURT;
bool modeAuto = true;          // true = Arduino decide chaud/froid tout seul
Peltier peltier = PELT_OFF;
bool pompeOn = false;
bool ventiloOn = false;
bool pompeManuel = false;      // true = Python a force la pompe, l auto ne l ecrase pas
bool ventiloManuel = false;
bool buzzerManuel = false;
bool buzzerOnFlag = false;
bool sondeOk = false;
bool labOuvert = true;         // false = LOCK, tout coupe
bool fermentationFinie = false;
int airBrut = 0;
int eauBrut = 0;
float tempReelle = 20.0;
float tempSimu = 20.0;         // fausse temperature pour le profil DEMO
float consigne = 42.0;
String rx = "";                // buffer des caracteres recus sur USB

float consigneDuProfil(Profile p) {
  // Chaque recette a sa consigne. TERRE = 25 C, pas de "fini" auto (jours).
  switch (p) {
    case PROF_YAOURT: return 42.0;
    case PROF_BIERE:  return 19.0;
    case PROF_PATE:   return 27.0;
    case PROF_TERRE:  return 25.0;
    case PROF_DEMO:   return 18.0;
  }
  return 42.0;
}

const char* nomProfil(Profile p) {
  switch (p) {
    case PROF_YAOURT: return "YAOURT";
    case PROF_BIERE:  return "BIERE";
    case PROF_PATE:   return "PATE";
    case PROF_TERRE:  return "TERRE";
    case PROF_DEMO:   return "DEMO";
  }
  return "YAOURT";
}

const char* nomPeltier(Peltier p) {
  if (p == PELT_HEAT) return "HEAT";
  if (p == PELT_COOL) return "COOL";
  return "OFF";
}

const char* etiquetteAir() {
  if (airBrut < SEUIL_AIR_BON) return "BON";
  if (airBrut < SEUIL_AIR_MAUV) return "MOY";
  return "MAUV";
}

void rgb(bool r, bool g, bool b) {
  // HIGH = allume (cathode commune : le + va a la pin, le - commun au GND)
  digitalWrite(PIN_LED_R, r ? HIGH : LOW);
  digitalWrite(PIN_LED_G, g ? HIGH : LOW);
  digitalWrite(PIN_LED_B, b ? HIGH : LOW);
}

void ecrireRelais(uint8_t pin, bool on) {
  // Relais actif bas : pour ALLUMER on met la pin a LOW
  if (RELAIS_ACTIF_LOW) digitalWrite(pin, on ? LOW : HIGH);
  else digitalWrite(pin, on ? HIGH : LOW);
}

bool profilBainMarie() {
  // Yaourt / biere / demo : il y a de l eau. Pate / terre : pas besoin.
  return profil == PROF_YAOURT || profil == PROF_BIERE || profil == PROF_DEMO;
}

bool eauOk() {
  if (!profilBainMarie()) return true;          // pas d eau requise
  return eauBrut >= SEUIL_EAU_OK;               // protection pompe a sec
}

void appliquerPontH(Peltier p) {
  // L298N = pont en H. On ne met JAMAIS IN1 et IN2 a 1 en meme temps (court-circuit).
  digitalWrite(PIN_PELTIER_IN1, LOW);
  digitalWrite(PIN_PELTIER_IN2, LOW);
  delay(5);                                     // petite pause = securite
  if (p == PELT_HEAT) digitalWrite(PIN_PELTIER_IN1, HIGH);      // courant dans un sens = chaud
  else if (p == PELT_COOL) digitalWrite(PIN_PELTIER_IN2, HIGH); // sens inverse = froid
}

void appliquerPeltier(Peltier p) {
  peltier = p;
  appliquerPontH(p);
  // Pompe auto : seulement si on CHAUFFE un bain-marie ET qu il y a de l eau
  if (!pompeManuel) pompeOn = (p == PELT_HEAT) && profilBainMarie() && eauOk();
  // Ventilo auto : tourne des que le Peltier est ON (chaud OU froid), sinon ca grille
  if (!ventiloManuel) ventiloOn = (p != PELT_OFF);
  ecrireRelais(PIN_POMPE, pompeOn);
  ecrireRelais(PIN_VENTILO, ventiloOn);
}

float temperatureUtile() {
  // DEMO : on simule T pour le jury sans attendre 6 h
  return (profil == PROF_DEMO) ? tempSimu : tempReelle;
}

void reguler() {
  // Coeur du projet : decide CHAUD / FROID / OFF
  if (!labOuvert || fermentationFinie) { appliquerPeltier(PELT_OFF); return; }

  float t = temperatureUtile();
  if (!sondeOk && profil != PROF_DEMO) { appliquerPeltier(PELT_OFF); return; }

  // Securite d abord, avant l hysteresis
  if (t >= TEMP_MAX_SECURITE) { appliquerPeltier(PELT_COOL); return; }
  if (t <= TEMP_MIN_SECURITE) { appliquerPeltier(PELT_HEAT); return; }

  // Manuel : Python / geste a choisi, on ne recale pas
  if (!modeAuto) { appliquerPeltier(peltier); return; }

  // Hysteresis ±0,5 C : si consigne = 42
  //   T < 41,5  -> CHAUD
  //   T > 42,5  -> FROID
  //   entre les deux -> OFF (zone morte, pas d oscillation)
  if (t < consigne - HYSTERESIS) appliquerPeltier(PELT_HEAT);
  else if (t > consigne + HYSTERESIS) appliquerPeltier(PELT_COOL);
  else appliquerPeltier(PELT_OFF);
}

void resetCycle() {
  fermentationFinie = false;
  tDebutProfil = millis();   // millis() = temps depuis le boot, en millisecondes
  digitalWrite(PIN_BUZZER, LOW);
}

void changerProfil(Profile p) {
  profil = p;
  consigne = consigneDuProfil(p);
  modeAuto = true;           // un nouveau profil revient en AUTO
  pompeManuel = false;
  ventiloManuel = false;
  if (p == PROF_DEMO) tempSimu = 20.0;
  resetCycle();
}

void gererBouton() {
  // INPUT_PULLUP : non appuye = HIGH, appuye = LOW (bouton vers GND)
  bool etat = digitalRead(PIN_BOUTON);
  unsigned long maintenant = millis();
  static bool boutonPrec = HIGH;
  static unsigned long tFrontBas = 0;
  static bool appuiLongFait = false;

  // Front descendant = debut d appui
  if (boutonPrec == HIGH && etat == LOW && (maintenant - tFrontBas) > ANTIREBOND_MS) {
    tFrontBas = maintenant;
    appuiLongFait = false;
  }
  // Appui long : bascule AUTO <-> MANUEL
  if (etat == LOW && !appuiLongFait && (maintenant - tFrontBas) >= APPUI_LONG_MS) {
    appuiLongFait = true;
    modeAuto = !modeAuto;
    if (!modeAuto) appliquerPeltier(PELT_OFF);
  }
  // Relachement court : profil suivant
  if (boutonPrec == LOW && etat == HIGH) {
    unsigned long duree = maintenant - tFrontBas;
    if (!appuiLongFait && duree >= ANTIREBOND_MS && duree < APPUI_LONG_MS) {
      changerProfil((Profile)((profil + 1) % 5));
    }
  }
  boutonPrec = etat;
}

RaisonLed raisonLed() {
  // Priorite : ferme > fini > sonde > eau > air > climat > peltier off
  if (!labOuvert) return LED_FERME;
  if (fermentationFinie) return LED_FINI;
  if (!sondeOk && profil != PROF_DEMO) return LED_SONDE;
  if (profilBainMarie() && !eauOk()) return LED_EAU;
  if (airBrut >= SEUIL_AIR_MAUV) return LED_AIR;
  if (peltier == PELT_HEAT || peltier == PELT_COOL) return LED_CLIM;
  return LED_PELT_OFF;
}

void gererLed() {
  bool clignote = (millis() / 400) % 2;   // 0/1 toutes les 400 ms
  switch (raisonLed()) {
    case LED_FERME:    rgb(false, false, clignote); break; // bleu clignote
    case LED_FINI:     rgb(false, clignote, false); break; // vert clignote
    case LED_CLIM:     rgb(true, true, false); break;      // jaune = Peltier ON
    default:           rgb(true, false, false); break;     // rouge = probleme
  }
}

void gererBuzzer() {
  if (buzzerManuel) {
    if (buzzerOnFlag) tone(PIN_BUZZER, 2700);
    else noTone(PIN_BUZZER);
    return;
  }
  if (fermentationFinie) {
    // sequence de bips puis silence (voir le vrai .ino pour le detail)
    return;
  }
  // Probleme labo : bips aigus periodiques
}

void envoyerData() {
  // Une ligne texte vers Python. Exemple :
  // DATA;temp=17.31;sp=42.00;mode=AUTO;peltier=HEAT;pump=1;fan=1;...
  Serial.print("DATA;temp=");
  Serial.print(temperatureUtile(), 2);
  Serial.print(";sp=");
  Serial.print(consigne, 2);
  Serial.print(";mode=");
  Serial.print(modeAuto ? "AUTO" : "MANUAL");
  Serial.print(";peltier=");
  Serial.print(nomPeltier(peltier));
  Serial.print(";pump=");
  Serial.print(pompeOn ? 1 : 0);
  Serial.print(";fan=");
  Serial.print(ventiloOn ? 1 : 0);
  Serial.print(";air=");
  Serial.print(airBrut);
  Serial.print(";profile=");
  Serial.println(nomProfil(profil));
}

void traiterCommande(String ligne) {
  // Python envoie : CMD;PELTIER=HEAT   ou   CMD;PROFILE=BIERE
  ligne.trim();
  ligne.toUpperCase();
  if (!ligne.startsWith("CMD;")) return;   // ignore tout le reste

  if (ligne.indexOf("UNLOCK") >= 0) { labOuvert = true; resetCycle(); return; }
  if (ligne.indexOf("LOCK") >= 0)   { labOuvert = false; appliquerPeltier(PELT_OFF); return; }

  if (ligne.indexOf("PROFILE=") >= 0) {
    // substring apres "PROFILE="
  }

  if (ligne.indexOf("MODE=AUTO") >= 0) {
    modeAuto = true;
    pompeManuel = false;
    ventiloManuel = false;
  } else if (ligne.indexOf("MODE=MANUAL") >= 0) {
    modeAuto = false;
    appliquerPeltier(PELT_OFF);
  }

  // Chaud / froid / stop : passe en MANUEL pour que AUTO ne rallume pas
  if (ligne.indexOf("PELTIER=HEAT") >= 0) {
    modeAuto = false;
    appliquerPeltier(PELT_HEAT);
  } else if (ligne.indexOf("PELTIER=COOL") >= 0) {
    modeAuto = false;
    appliquerPeltier(PELT_COOL);
  } else if (ligne.indexOf("PELTIER=OFF") >= 0) {
    modeAuto = false;
    appliquerPeltier(PELT_OFF);
  }

  if (ligne.indexOf("PUMP=") >= 0) {
    pompeManuel = true;                              // l auto ne touche plus la pompe
    pompeOn = ligne.indexOf("PUMP=0") < 0;           // PUMP=0 -> off, sinon on
    ecrireRelais(PIN_POMPE, pompeOn);
  }
  if (ligne.indexOf("FAN=") >= 0) {
    ventiloManuel = true;
    ventiloOn = ligne.indexOf("FAN=0") < 0;
    ecrireRelais(PIN_VENTILO, ventiloOn);
  }
  if (ligne.indexOf("BUZZER=") >= 0) {
    buzzerManuel = true;
    buzzerOnFlag = ligne.indexOf("BUZZER=0") < 0;
  }
}

void lireSerie() {
  // On lit caractere par caractere. Un \n = fin de commande.
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') { traiterCommande(rx); rx = ""; }
    else if (c != '\r') { if (rx.length() < 80) rx += c; }
  }
}

void setup() {
  // setup() = UNE fois au boot
  pinMode(PIN_BOUTON, INPUT_PULLUP);
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_POMPE, OUTPUT);
  pinMode(PIN_VENTILO, OUTPUT);
  pinMode(PIN_PELTIER_IN1, OUTPUT);
  pinMode(PIN_PELTIER_IN2, OUTPUT);
  pinMode(PIN_MQ, INPUT);
  pinMode(PIN_EAU, INPUT);

  appliquerPeltier(PELT_OFF);     // fail-safe : rien ne tourne au demarrage
  Serial.begin(9600);             // meme vitesse que Python (pyserial 9600)
  sonde.begin();
  lcd.begin(16, 2);
  changerProfil(PROF_YAOURT);
}

void loop() {
  // loop() = tourne sans arret. On ne met PAS delay(10000) ici :
  // sinon le bouton et la securite seraient bloques 10 s.
  unsigned long maintenant = millis();

  gererBouton();
  lireSerie();

  if (maintenant - tSonde >= INTERVALLE_SONDE_MS) {
    // Non-bloquant : on lit seulement si 1 s s est ecoulee
    tSonde = maintenant;
    sonde.requestTemperatures();
    float lu = sonde.getTempCByIndex(0);
    sondeOk = (lu > -50 && lu < 80);
    if (sondeOk) tempReelle = lu;
    airBrut = analogRead(PIN_MQ);   // 0 = propre, grand = charge
    eauBrut = analogRead(PIN_EAU);
  }

  if (profil == PROF_DEMO) {
    // Fausse T qui monte/descend pour montrer le Peltier au jury
    if (peltier == PELT_HEAT) tempSimu += 0.25;
    else if (peltier == PELT_COOL) tempSimu -= 0.25;
  }

  reguler();
  gererLed();
  gererBuzzer();

  if (maintenant - tSerie >= INTERVALLE_SERIE_MS) {
    tSerie = maintenant;
    envoyerData();                // Python parse cette ligne
  }
}

unsigned long tSonde = 0;
unsigned long tSerie = 0;

/*
 * QUESTIONS D EXAMEN TYPES
 *
 * Q : Pourquoi hysteresis 0,5 C ?
 * R : Sans zone morte, a 42,00 le Peltier bascule chaud/froid en continu.
 *
 * Q : Pourquoi ventilo avec le Peltier ?
 * R : La pastille dissipe de la chaleur. Sans ventilo elle grille. Les ventilos
 *     ne changent PAS de sens. Chaud/froid = polarite L298N.
 *
 * Q : Pourquoi le 12 V du ventilo passe par le relais D7 ?
 * R : Si le chargeur 12 V va direct au moteur, Arduino ne peut pas l arreter.
 *
 * Q : Serial Monitor ET Python en meme temps ?
 * R : Non. Un seul programme a le droit d ouvrir le port COM / usbmodem.
 *
 * Q : Qui decide la temperature, le Pi ou l Uno ?
 * R : L Uno. Le Pi n a aucun capteur 5 V sur ses GPIO. Il commande par USB.
 */
