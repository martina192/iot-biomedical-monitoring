/*
  BITalino → LoRaWAN Bridge
  TLV binary packets from serial → Uplink via LoRaWAN
  Receives Downlink after each uplink
*/

#include <MKRWAN.h>

LoRaModem modem;

// ---- CONFIGURACIÓ SERIAL ----
#define SERIAL_BAUD 9600
const int PACKET_SIZE = 5;   // T(1) + L(1) + V(2) + \n(1)
byte receivedBuffer[PACKET_SIZE];

// ---- Dades LoRaWAN ----
String appEui = "0000000000000000";
String appKey = "4B6F40C20F6C044E68C76FA304B1E5AC"; // substitueix per la teva

void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial);  // esperem port per debug

  Serial.println("--- BITalino LoRaWAN Bridge ---");

  // Inicialitza LoRaWAN
  if (!modem.begin(EU868)) {
    Serial.println("Failed to start LoRa module");
    while (1) {}
  }

  Serial.print("Version: ");
  Serial.println(modem.version());
  Serial.print("Device EUI: ");
  Serial.println(modem.deviceEUI());

  Serial.println("Joining LoRaWAN network (OTAA)...");
  int connected = modem.joinOTAA(appEui, appKey);

  if (connected) {
    Serial.println("Joined successfully!");
  } else {
    Serial.println("Failed to join.");
    while (1) {}
  }

  modem.minPollInterval(60);
}

void loop() {

  // Esperem paquet TLV (5 bytes incloent \n)
  if (Serial.available() >= PACKET_SIZE) {

    int bytesRead = Serial.readBytes(receivedBuffer, PACKET_SIZE);

    if (bytesRead == PACKET_SIZE && receivedBuffer[4] == 0x0A) {

      byte type = receivedBuffer[0];
      byte length = receivedBuffer[1];
      unsigned int sensorValue = (receivedBuffer[3] << 8) | receivedBuffer[2];

      Serial.print("\n[R] Valor Rebut: ");
      Serial.print(sensorValue);
      Serial.print(" | Tipus: 0x");
      Serial.println(type, HEX);

      // ---------- UPLINK ----------
      modem.beginPacket();
      modem.write(type);          // T
      modem.write(length);        // L
      modem.write(receivedBuffer[2]); // Low byte V
      modem.write(receivedBuffer[3]); // High byte V

      int err = modem.endPacket(true);  // true = confirmat (RX1/RX2 activades)

      if (err > 0) {
        Serial.println("[L] Uplink enviat correctament.");
      } else {
        Serial.println("[L] Error enviant uplink.");
      }

      // ---------- DOWNLINK ----------
      delay(150);  // temps perquè MKR processi RX1/RX2

      if (modem.available()) {
        Serial.print("[DL] Downlink rebut: ");

        while (modem.available()) {
          byte b = modem.read();
          Serial.print(b >> 4, HEX);
          Serial.print(b & 0xF, HEX);
          Serial.print(" ");
        }

        Serial.println();

      } else {
        Serial.println("[DL] No hi ha downlink.");
      }

    } else {
      Serial.println("[R] Error de paquet. Netejant buffer.");

      while (Serial.available()) {
        Serial.read();
      }
    }
  }
}
