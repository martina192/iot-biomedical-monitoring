/*
  Lora Send And Receive - EMULACIÓ DE DADES TLV
  Genera valors d'HR i Temperatura aleatoris, construeix el payload TLV binari
  i l'envia per LoRaWAN sense dependre del port Serial.
*/

#include <MKRWAN.h>

LoRaModem modem;

// Dades de Configuració LoRaWAN (es mantenen igual)
String appEui = "0000000000000000";
String appKey = "4B6F40C20F6C044E68C76FA304B1E5AC";

// Definició de TLV Tags
#define TYPE_HR     0x01

// Mida màxima del payload combinat (HR TLV 3 bytes + TEMP TLV 4 bytes = 7 bytes)
const int MAX_PAYLOAD_SIZE = 3; 

// --- CONFIGURACIÓ ---
const int SEND_INTERVAL_MS = 60000; // Envia un paquet cada 60 segons (1 minut)
unsigned long lastSendTime = 0;

void setup() {
  Serial.begin(9600);
  while (!Serial);
  
  // Inicialització del generador de nombres aleatoris
  randomSeed(analogRead(A0)); 

  // Configuració i Connexió LoRaWAN (es manté igual)
  if (!modem.begin(EU868)) {
    Serial.println("Failed to start module");
    while (1) {}
  };
  
  Serial.print("Your module version is: ");
  Serial.println(modem.version());
  
  int connected = modem.joinOTAA(appEui, appKey);
  if (!connected) {
    Serial.println("Something went wrong; are you indoor? Move near a window and retry");
    while (1) {}
  }
  Serial.println("LoRaWAN Joined!");
  modem.minPollInterval(60);
}

void loop() {
  if (millis() - lastSendTime > SEND_INTERVAL_MS) {
    lastSendTime = millis();
    
    // --- PAS 1: SIMULACIÓ DE LECTURES DE SENSOR ---
    
    // HR: Valor aleatori entre 60 i 110 BPM (cap en 1 byte)
    uint8_t hr_value = (uint8_t)random(60, 110); 
    
    // --- PAS 2: CONSTRUCCIÓ DEL PAYLOAD BINARI TLV (7 bytes) ---
    
    byte payloadBuffer[MAX_PAYLOAD_SIZE];
    int index = 0; // Index per escriure al buffer
    
    // 1. HR TLV (01 01 4B)
    payloadBuffer[index++] = TYPE_HR;     // T: 0x01
    payloadBuffer[index++] = 0x01;        // L: 1 byte
    payloadBuffer[index++] = hr_value;    // V: 1 byte (e.g., 0x4B)
    
    int bytesToSend = index; // Hauria de ser 3
    
    // --- PAS 3: ENVIAMENT PER LORAWAN I DEPURACIÓ ---

    Serial.println();
    Serial.print("Sending TLV Payload (");
    Serial.print(bytesToSend);
    Serial.print(" bytes): ");
    
    // Imprimeix el payload en HEXA per depuració
    for (int i = 0; i < bytesToSend; i++) {
      if (payloadBuffer[i] < 0x10) Serial.print("0"); 
      Serial.print(payloadBuffer[i], HEX);
      Serial.print(" ");
    }
    Serial.println();

    int err;
    modem.beginPacket();
    
    // Escriure el buffer BINARI directament al mòdem
    modem.write(payloadBuffer, bytesToSend); 
    
    err = modem.endPacket(true); // Enviament amb confirmació
    
    if (err > 0) {
      Serial.println("Message sent correctly!");
    } else {
      Serial.println("Error sending message :(");
    }
    
    // --- PAS 4: GESTIÓ DE DOWNLINK (es manté) ---
    delay(1000); 

    if (modem.available()) {
      byte rcv[64];
      int i = 0;
      while (modem.available() && i < 64) {
        rcv[i++] = (byte)modem.read();
      }
      Serial.print("Received Downlink (");
      Serial.print(i);
      Serial.print(" bytes): ");
      for (unsigned int j = 0; j < i; j++) {
        if (rcv[j] < 0x10) Serial.print("0");
        Serial.print(rcv[j], HEX);
        Serial.print(" ");
      }
      Serial.println();
    } else {
      Serial.println("No downlink message received at this time.");
    }
  }
}
