#include <OneWire.h>
#include <DallasTemperature.h>
#include <LiquidCrystal.h>

LiquidCrystal lcd(8, 9, 10, 11, 12, 13);

const uint8_t PIN_DS18B20 = 2;
const uint8_t PIN_BOUTON = 3;
const uint8_t PIN_LED_R = 4;
const uint8_t PIN_LED_G = A2;
const uint8_t PIN_LED_B = A3;
const uint8_t PIN_BUZZER = A4;
const uint8_t PIN_POMPE = 5;
const uint8_t PIN_VENTILO = 7;
const uint8_t PIN_PELTIER_IN1 = 6;
const uint8_t PIN_PELTIER_IN2 = A1;
const uint8_t PIN_MQ = A0;
const uint8_t PIN_EAU = A5;
const int SEUIL_EAU_OK = 250;
const bool RELAIS_ACTIF_LOW = true;
const int SEUIL_AIR_BON = 250;
const int SEUIL_AIR_MAUV = 450;
const float HYSTERESIS = 0.5;
const float TEMP_MAX_SECURITE = 45.0;
const float TEMP_MIN_SECURITE = 3.0;
const unsigned long INTERVALLE_SONDE_MS = 1000;
const unsigned long INTERVALLE_LCD_MS = 400;
const unsigned long INTERVALLE_SERIE_MS = 10000;
const unsigned long ANTIREBOND_MS = 40;
const unsigned long APPUI_LONG_MS = 800;
const unsigned long DUREE_YAOURT_MS = 6UL * 3600UL * 1000UL;
const unsigned long DUREE_PATE_MS = 75UL * 60UL * 1000UL;
const unsigned long DUREE_DEMO_MS = 20UL * 1000UL;
const unsigned long BIERE_CALME_MS = 3UL * 60UL * 1000UL;
const unsigned long BIERE_MIN_MS = 60UL * 1000UL;
const unsigned long VIDANGE_MAX_MS = 90UL * 1000UL;

enum Profile { PROF_YAOURT, PROF_BIERE, PROF_PATE, PROF_TERRE, PROF_DEMO };
const uint8_t NB_PROFILS = 5;
enum Peltier { PELT_OFF, PELT_HEAT, PELT_COOL };
enum RaisonLed {
  LED_FERME,
  LED_FINI,
  LED_SONDE,
  LED_EAU,
  LED_AIR,
  LED_CLIM,
  LED_PELT_OFF
};

OneWire oneWire(PIN_DS18B20);
DallasTemperature sonde(&oneWire);

Profile profil = PROF_YAOURT;
bool modeAuto = true;
Peltier peltier = PELT_OFF;
bool pompeOn = false;
bool ventiloOn = false;
bool buzzerOnFlag = false;
bool pompeManuel = false;
bool ventiloManuel = false;
bool buzzerManuel = false;
bool sondeOk = false;
bool labOuvert = true;
bool fermentationFinie = false;
bool vidangeEnCours = false;
bool airAEteActif = false;
bool bipFait = false;
int airBrut = 0;
int eauBrut = 0;
int phaseBip = 0;
float tempReelle = 20.0;
float tempSimu = 20.0;
float consigne = 42.0;
unsigned long tSonde = 0;
unsigned long tLcd = 0;
unsigned long tSerie = 0;
unsigned long tLed = 0;
unsigned long tSimu = 0;
unsigned long tDebutProfil = 0;
unsigned long tAirCalme = 0;
unsigned long tBip = 0;
unsigned long tVidange = 0;
bool boutonPrec = HIGH;
unsigned long tFrontBas = 0;
bool appuiLongFait = false;
String rx = "";

float consigneDuProfil(Profile p) {
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
  digitalWrite(PIN_LED_R, r ? HIGH : LOW);
  digitalWrite(PIN_LED_G, g ? HIGH : LOW);
  digitalWrite(PIN_LED_B, b ? HIGH : LOW);
}

void ecrireRelais(uint8_t pin, bool on) {
  if (RELAIS_ACTIF_LOW) {
    digitalWrite(pin, on ? LOW : HIGH);
  } else {
    digitalWrite(pin, on ? HIGH : LOW);
  }
}

bool profilBainMarie() {
  return profil == PROF_YAOURT || profil == PROF_BIERE || profil == PROF_DEMO;
}

bool eauOk() {
  if (!profilBainMarie()) return true;
  return eauBrut >= SEUIL_EAU_OK;
}

void appliquerPontH(Peltier p) {
  digitalWrite(PIN_PELTIER_IN1, LOW);
  digitalWrite(PIN_PELTIER_IN2, LOW);
  delay(5);
  if (p == PELT_HEAT) {
    digitalWrite(PIN_PELTIER_IN1, HIGH);
  } else if (p == PELT_COOL) {
    digitalWrite(PIN_PELTIER_IN2, HIGH);
  }
}

void appliquerPeltier(Peltier p) {
  peltier = p;
  appliquerPontH(p);
  if (!pompeManuel) {
    pompeOn = (p == PELT_HEAT) && profilBainMarie() && eauOk();
  }
  if (!ventiloManuel) {
    ventiloOn = (p != PELT_OFF);
  }
  ecrireRelais(PIN_POMPE, pompeOn);
  ecrireRelais(PIN_VENTILO, ventiloOn);
}

float temperatureUtile() {
  return (profil == PROF_DEMO) ? tempSimu : tempReelle;
}

void reguler() {
  if (!labOuvert || fermentationFinie) {
    appliquerPeltier(PELT_OFF);
    return;
  }

  float t = temperatureUtile();

  if (!sondeOk && profil != PROF_DEMO) {
    appliquerPeltier(PELT_OFF);
    return;
  }

  if (t >= TEMP_MAX_SECURITE) {
    appliquerPeltier(PELT_COOL);
    return;
  }
  if (t <= TEMP_MIN_SECURITE) {
    appliquerPeltier(PELT_HEAT);
    return;
  }

  if (!modeAuto) {
    appliquerPeltier(peltier);
    return;
  }

  if (t < consigne - HYSTERESIS) {
    appliquerPeltier(PELT_HEAT);
  } else if (t > consigne + HYSTERESIS) {
    appliquerPeltier(PELT_COOL);
  } else {
    appliquerPeltier(PELT_OFF);
  }
}

void resetCycle() {
  fermentationFinie = false;
  vidangeEnCours = false;
  airAEteActif = false;
  bipFait = false;
  phaseBip = 0;
  tDebutProfil = millis();
  tAirCalme = 0;
  digitalWrite(PIN_BUZZER, LOW);
}

void demarrerFin() {
  fermentationFinie = true;
  appliquerPeltier(PELT_OFF);
  if (profilBainMarie() && eauOk()) {
    vidangeEnCours = true;
    tVidange = millis();
    pompeOn = true;
    ecrireRelais(PIN_POMPE, true);
  } else {
    vidangeEnCours = false;
    phaseBip = 0;
    bipFait = false;
  }
}

void gererVidange() {
  if (!vidangeEnCours) return;
  appliquerPeltier(PELT_OFF);
  bool fini = !eauOk() || (millis() - tVidange >= VIDANGE_MAX_MS);
  if (fini) {
    vidangeEnCours = false;
    pompeOn = false;
    ecrireRelais(PIN_POMPE, false);
    phaseBip = 0;
    bipFait = false;
    return;
  }
  pompeOn = true;
  ecrireRelais(PIN_POMPE, true);
}

void changerProfil(Profile p) {
  profil = p;
  consigne = consigneDuProfil(p);
  modeAuto = true;
  pompeManuel = false;
  ventiloManuel = false;
  buzzerManuel = false;
  buzzerOnFlag = false;
  if (p == PROF_DEMO) {
    tempSimu = 20.0;
  }
  resetCycle();
}

void profilSuivant() {
  changerProfil((Profile)((profil + 1) % NB_PROFILS));
}

void gererBouton() {
  bool etat = digitalRead(PIN_BOUTON);
  unsigned long maintenant = millis();

  if (boutonPrec == HIGH && etat == LOW && (maintenant - tFrontBas) > ANTIREBOND_MS) {
    tFrontBas = maintenant;
    appuiLongFait = false;
  }

  if (etat == LOW && !appuiLongFait && (maintenant - tFrontBas) >= APPUI_LONG_MS) {
    appuiLongFait = true;
    modeAuto = !modeAuto;
    if (!modeAuto) {
      appliquerPeltier(PELT_OFF);
    }
  }

  if (boutonPrec == LOW && etat == HIGH) {
    unsigned long duree = maintenant - tFrontBas;
    if (!appuiLongFait && duree >= ANTIREBOND_MS && duree < APPUI_LONG_MS) {
      profilSuivant();
    }
  }

  boutonPrec = etat;
}

RaisonLed raisonLed() {
  if (!labOuvert) return LED_FERME;
  if (vidangeEnCours) return LED_CLIM;
  if (fermentationFinie) return LED_FINI;
  if (!sondeOk && profil != PROF_DEMO) return LED_SONDE;
  if (profilBainMarie() && !eauOk()) return LED_EAU;
  if (airBrut >= SEUIL_AIR_MAUV) return LED_AIR;
  if (peltier == PELT_HEAT || peltier == PELT_COOL) return LED_CLIM;
  return LED_PELT_OFF;
}

void gererLed() {
  unsigned long maintenant = millis();
  bool clignote = (maintenant / 400) % 2;
  switch (raisonLed()) {
    case LED_FERME:
      rgb(false, false, clignote);
      break;
    case LED_FINI:
      rgb(false, clignote, false);
      break;
    case LED_CLIM:
      rgb(true, true, false);
      break;
    case LED_SONDE:
    case LED_EAU:
    case LED_AIR:
    case LED_PELT_OFF:
      rgb(true, false, false);
      break;
  }
}

void buzzerOff() {
  noTone(PIN_BUZZER);
  digitalWrite(PIN_BUZZER, LOW);
}

void buzzerOn(int hz) {
  tone(PIN_BUZZER, hz);
  digitalWrite(PIN_BUZZER, HIGH);
}

bool problemeLabo() {
  RaisonLed r = raisonLed();
  return r == LED_SONDE || r == LED_EAU || r == LED_AIR;
}

void gererBuzzer() {
  unsigned long maintenant = millis();

  if (buzzerManuel) {
    if (buzzerOnFlag) buzzerOn(2700);
    else buzzerOff();
    return;
  }

  if (vidangeEnCours) {
    buzzerOff();
    return;
  }

  if (fermentationFinie) {
    if (bipFait) {
      buzzerOff();
      return;
    }
    if (phaseBip == 0) {
      buzzerOn(2700);
      tBip = maintenant;
      phaseBip = 1;
      return;
    }
    if (phaseBip >= 1 && phaseBip <= 11) {
      unsigned long duree = (phaseBip % 2 == 1) ? 450 : 120;
      if (maintenant - tBip >= duree) {
        tBip = maintenant;
        phaseBip++;
        if (phaseBip % 2 == 1) buzzerOn(2700);
        else buzzerOff();
      }
    }
    if (phaseBip > 11) {
      buzzerOff();
      bipFait = true;
    }
    return;
  }

  if (!problemeLabo()) {
    buzzerOff();
    return;
  }
  unsigned long c = maintenant % 2500UL;
  if (c < 220 || (c >= 340 && c < 560)) buzzerOn(3200);
  else buzzerOff();
}

void verifierFin() {
  if (!labOuvert || fermentationFinie) return;
  unsigned long maintenant = millis();
  unsigned long age = maintenant - tDebutProfil;

  if (profil == PROF_YAOURT && age >= DUREE_YAOURT_MS) fermentationFinie = true;
  if (profil == PROF_PATE && age >= DUREE_PATE_MS) fermentationFinie = true;
  if (profil == PROF_DEMO && age >= DUREE_DEMO_MS) fermentationFinie = true;

  if (profil == PROF_BIERE && age >= BIERE_MIN_MS) {
    if (airBrut >= SEUIL_AIR_BON) {
      airAEteActif = true;
      tAirCalme = 0;
    } else if (airAEteActif) {
      if (tAirCalme == 0) tAirCalme = maintenant;
      if (maintenant - tAirCalme >= BIERE_CALME_MS) fermentationFinie = true;
    }
  }

  if (fermentationFinie) demarrerFin();
}

String padLcd(String s) {
  while (s.length() < 16) s += ' ';
  if (s.length() > 16) s = s.substring(0, 16);
  return s;
}

void texteLcd(String& l1, String& l2) {
  if (!labOuvert) {
    l1 = padLcd("FERMIA FERME");
    l2 = padLcd("BADGEZ CARTE");
    return;
  }
  if (vidangeEnCours) {
    l1 = padLcd("VIDANGE EAU");
    l2 = padLcd("TUYAU DEHORS");
    return;
  }
  if (fermentationFinie) {
    l1 = padLcd("FERMENT. FINIE");
    l2 = padLcd(String(nomProfil(profil)) + "  BIP!");
    return;
  }

  float t = temperatureUtile();
  String haut = "T:";
  if (t < 10) haut += ' ';
  haut += String(t, 1);
  haut += "C ";
  haut += nomProfil(profil);
  l1 = padLcd(haut);

  switch (raisonLed()) {
    case LED_SONDE:
      l2 = padLcd("ROUGE: SONDE HS");
      return;
    case LED_EAU:
      l2 = padLcd("ROUGE: EAU BASSE");
      return;
    case LED_AIR:
      l2 = padLcd("ROUGE: AIR MAUV");
      return;
    case LED_PELT_OFF:
      l2 = padLcd("ROUGE: PELT OFF");
      return;
    case LED_CLIM: {
      String bas = modeAuto ? "AUTO " : "MAN  ";
      bas += (peltier == PELT_HEAT) ? "CHAUFFE" : "FROID  ";
      bas += " ";
      bas += String((int)consigne);
      bas += "C";
      l2 = padLcd(bas);
      return;
    }
    default:
      break;
  }
  if ((millis() / 2000) % 2 == 1) {
    String bas = "AIR ";
    bas += etiquetteAir();
    bas += " ";
    bas += String(airBrut);
    l2 = padLcd(bas);
    return;
  }
  String bas = modeAuto ? "AUTO " : "MAN  ";
  bas += "OK ";
  bas += String((int)consigne);
  bas += "C";
  l2 = padLcd(bas);
}

void actualiserLcd() {
  String l1, l2;
  texteLcd(l1, l2);
  lcd.setCursor(0, 0);
  lcd.print(l1);
  lcd.setCursor(0, 1);
  lcd.print(l2);
}

void envoyerData() {
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
  Serial.print(";aq=");
  Serial.print(etiquetteAir());
  Serial.print(";water=");
  Serial.print(eauBrut);
  Serial.print(";wet=");
  Serial.print(eauOk() ? 1 : 0);
  Serial.print(";profile=");
  Serial.print(nomProfil(profil));
  Serial.print(";ok=");
  Serial.print((sondeOk || profil == PROF_DEMO) ? 1 : 0);
  Serial.print(";lock=");
  Serial.print(labOuvert ? 0 : 1);
  Serial.print(";done=");
  Serial.print(fermentationFinie ? 1 : 0);
  Serial.print(";buzz=");
  Serial.print(buzzerOnFlag ? 1 : 0);
  String l1, l2;
  texteLcd(l1, l2);
  l1.replace(';', ' ');
  l2.replace(';', ' ');
  Serial.print(";lcd=");
  Serial.print(l1);
  Serial.print(" | ");
  Serial.println(l2);
}

Profile profilDepuisNom(const String& n) {
  if (n == "BIERE" || n == "BIERRE" || n == "BEER") return PROF_BIERE;
  if (n == "PATE") return PROF_PATE;
  if (n == "TERRE") return PROF_TERRE;
  if (n == "DEMO") return PROF_DEMO;
  return PROF_YAOURT;
}

void traiterCommande(String ligne) {
  ligne.trim();
  ligne.toUpperCase();
  if (!ligne.startsWith("CMD;")) return;

  if (ligne.indexOf("UNLOCK") >= 0) {
    labOuvert = true;
    resetCycle();
    return;
  }
  if (ligne.indexOf("LOCK") >= 0) {
    labOuvert = false;
    appliquerPeltier(PELT_OFF);
    return;
  }
  if (ligne.indexOf("DONE") >= 0) {
    if (labOuvert) demarrerFin();
    return;
  }

  if (ligne.indexOf("PROFILE=") >= 0) {
    int i = ligne.indexOf("PROFILE=") + 8;
    String n = ligne.substring(i);
    int sep = n.indexOf(';');
    if (sep >= 0) n = n.substring(0, sep);
    n.trim();
    changerProfil(profilDepuisNom(n));
  }

  if (ligne.indexOf("SP=") >= 0) {
    int i = ligne.indexOf("SP=") + 3;
    consigne = ligne.substring(i).toFloat();
    if (consigne < 4) consigne = 4;
    if (consigne > 45) consigne = 45;
  }

  if (ligne.indexOf("MODE=AUTO") >= 0) {
    modeAuto = true;
    pompeManuel = false;
    ventiloManuel = false;
    buzzerManuel = false;
    buzzerOnFlag = false;
  } else if (ligne.indexOf("MODE=MANUAL") >= 0) {
    modeAuto = false;
    pompeManuel = false;
    ventiloManuel = false;
    appliquerPeltier(PELT_OFF);
  }

  if (ligne.indexOf("PELTIER=HEAT") >= 0) {
    if (!labOuvert) return;
    modeAuto = false;
    pompeManuel = false;
    ventiloManuel = false;
    appliquerPeltier(PELT_HEAT);
  } else if (ligne.indexOf("PELTIER=COOL") >= 0) {
    if (!labOuvert) return;
    modeAuto = false;
    pompeManuel = false;
    ventiloManuel = false;
    appliquerPeltier(PELT_COOL);
  } else if (ligne.indexOf("PELTIER=OFF") >= 0) {
    modeAuto = false;
    pompeManuel = false;
    ventiloManuel = false;
    appliquerPeltier(PELT_OFF);
  }

  if (ligne.indexOf("PUMP=") >= 0) {
    pompeManuel = true;
    if (ligne.indexOf("PUMP=TOGGLE") >= 0) pompeOn = !pompeOn;
    else pompeOn = ligne.indexOf("PUMP=0") < 0;
    ecrireRelais(PIN_POMPE, pompeOn);
  }
  if (ligne.indexOf("FAN=") >= 0) {
    ventiloManuel = true;
    if (ligne.indexOf("FAN=TOGGLE") >= 0) ventiloOn = !ventiloOn;
    else ventiloOn = ligne.indexOf("FAN=0") < 0;
    ecrireRelais(PIN_VENTILO, ventiloOn);
  }
  if (ligne.indexOf("BUZZER=") >= 0) {
    buzzerManuel = true;
    if (ligne.indexOf("BUZZER=TOGGLE") >= 0) buzzerOnFlag = !buzzerOnFlag;
    else buzzerOnFlag = ligne.indexOf("BUZZER=0") < 0;
    if (buzzerOnFlag) buzzerOn(2700);
    else buzzerOff();
  }
}

void lireSerie() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      traiterCommande(rx);
      rx = "";
    } else if (c != '\r') {
      if (rx.length() < 80) rx += c;
    }
  }
}

void setup() {
  pinMode(PIN_BOUTON, INPUT_PULLUP);
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_LED_G, OUTPUT);
  pinMode(PIN_LED_B, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_POMPE, OUTPUT);
  pinMode(PIN_VENTILO, OUTPUT);
  pinMode(PIN_PELTIER_IN1, OUTPUT);
  pinMode(PIN_PELTIER_IN2, OUTPUT);
  pinMode(PIN_MQ, INPUT);
  pinMode(PIN_EAU, INPUT);

  appliquerPeltier(PELT_OFF);
  rgb(false, false, false);
  digitalWrite(PIN_BUZZER, LOW);

  Serial.begin(9600);
  sonde.begin();
  sonde.setResolution(12);

  lcd.begin(16, 2);
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("FERMIA  5 profils");
  lcd.setCursor(0, 1);
  lcd.print("YAOURT BIERE...");
  delay(1500);

  changerProfil(PROF_YAOURT);
  lcd.clear();
}

void loop() {
  unsigned long maintenant = millis();

  gererBouton();
  lireSerie();

  if (maintenant - tSonde >= INTERVALLE_SONDE_MS) {
    tSonde = maintenant;
    sonde.requestTemperatures();
    float lu = sonde.getTempCByIndex(0);
    sondeOk = (lu > -50 && lu < 80 && lu != DEVICE_DISCONNECTED_C);
    if (sondeOk) tempReelle = lu;
    airBrut = analogRead(PIN_MQ);
    eauBrut = analogRead(PIN_EAU);
  }

  if (profil == PROF_DEMO && maintenant - tSimu >= 300) {
    tSimu = maintenant;
    if (peltier == PELT_HEAT) tempSimu += 0.25;
    else if (peltier == PELT_COOL) tempSimu -= 0.25;
    if (tempSimu > 50) tempSimu = 50;
    if (tempSimu < 2) tempSimu = 2;
  }

  verifierFin();
  reguler();
  gererVidange();
  if (modeAuto && !ventiloManuel && airBrut >= SEUIL_AIR_MAUV && labOuvert && !fermentationFinie) {
    ventiloOn = true;
    ecrireRelais(PIN_VENTILO, true);
  }
  gererLed();
  gererBuzzer();

  if (maintenant - tLcd >= INTERVALLE_LCD_MS) {
    tLcd = maintenant;
    actualiserLcd();
  }

  if (maintenant - tSerie >= INTERVALLE_SERIE_MS) {
    tSerie = maintenant;
    envoyerData();
  }
}
