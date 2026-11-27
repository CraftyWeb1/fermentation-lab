1. Alimentation de la plaque 

Rail 5V : broche 5V de l'Arduino au rail rouge de la plaque.
Rail GND : broche GND de l'Arduino au rail bleu de la plaque.
Ponts : Faire un pont rouge (5V à 5V) et un pont noir (GND à GND) pour propager le courant de part et d'autre de la plaque.

2. Écran LCD 1602 
Pin 1 (VSS) : Rail GND
Pin 2 (VDD) : Rail 5V
Pin 3 (V0 - Contraste) : Curseur central du potentiomètre de 10 kΩ . les deux autres pattes du potentiomètre vont  au 5V et au GND
Pin 4 (RS) : Pin D8 de l'Arduino
Pin 5 (RW) : Rail GND
Pin 6 (E) : Pin D9 de l'Arduino
Pins 7 à 10 : rien
Pin 11 (D4) : Pin D10 de l'Arduino
Pin 12 (D5) : Pin D11 de l'Arduino
Pin 13 (D6) : Pin D12 de l'Arduino
Pin 14 (D7) : Pin D13 de l'Arduino
Pin 15 : Rail 5V
Pin 16 : Rail GND
3. Capteur de Température (DS18B20)
Fil Rouge (VCC) : Rail 5V
Fil Noir (GND) : Rail GND
Fil Jaune (DATA) : Pin D2 de l'Arduino
Résistance : une résistance de 4,7 kΩ entre le fil jaune (DATA) et le rail 5V.
4. LED d'état (Rouge)
Pin D4 de l'Arduino → Entrée d'une résistance de 220 Ω sur la plaque.
Sortie de la résistance → Anode (+) de la LED (patte longue).
Cathode (-) de la LED (patte courte ) → Rail GND.

5. Bouton Poussoir
Une patte du bouton → Pin D3 de l'Arduino.
L'autre patte du bouton → Rail GND

6. Pompe et Module Relais
Relais VCC : Rail 5V
Relais GND : Rail GND
Relais  : Pin D5 de l'Arduino
Alimentation externe 12V:
COM du relais → Borne +12V de l'alimentation externe.
NO du relais → Fil Rouge de la pompe.
Fil - de la pompe → Borne -12V / GND de l'alimentation externe.

