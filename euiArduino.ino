#include "MKRWAN.h"

LoRaModem modem;

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  while(!Serial);

  if(!modem.begin(EU868)){
    Serial.println("FAILED TO START MODULE ");
    while(1);
  }
  
  Serial.println("EUI is: ");
  Serial.println(modem.deviceEUI());

}

void loop() {
  // put your main code here, to run repeatedly:

}
