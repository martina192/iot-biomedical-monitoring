# Simulador per al port serial (Simula l'Arduino)

import serial
import time
import sys

# **IMPORTANT: Utilitza el port RECEPTOR (RX) de socat (Exemple: /dev/pts/4)**
SERIAL_PORT = '/dev/pts/2' 
BAUD_RATE = 9600 

LORA_SEND_INTERVAL_SECONDS=30

def read_and_send_command():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(1)
        print(f"\n--- Simulador Arduino (Port: {SERIAL_PORT}) ---")
        print("Escoltant dades Uplink de la RPi...")

        # -- Primera Part: Prova Uplink (Recepció de BPM) --
        # Esperem el primer paquet de BPM (5 bytes)
        while ser.in_waiting < 5:
            print(".", end="", flush=True)
            time.sleep(0.5)

        # Llegeix el paquet binari (5 bytes)
        uplink_data = ser.read(5)
        
        # Descodificació dels bytes (per veure els valors)
        T = uplink_data[0] # Type (0x02)
        L = uplink_data[1] # Length (0x02)
        BPM = uplink_data[2] # BPM value
        FLAG = uplink_data[3] # Arrhythmia Flag
        
        print("\n\n[UPLINK REBUT]")
        print(f"BPM Binari: {BPM} (0-{LORA_SEND_INTERVAL_SECONDS}s)")
        print(f"Flag Arrítmia: {FLAG}")
        print("---")


        # -- Segona Part: Prova Downlink (Enviament de Comanda) --
        time.sleep(3) 
        command = "BUZZ_ON\n"
        ser.write(command.encode('utf-8'))
        print(f"\n[DOWNLINK ENVIAT] -> {command.strip()}")
        time.sleep(10)
        command = "BUZZ_OFF\n"
        ser.write(command.encode('utf-8'))
        print(f"\n[DOWNLINK ENVIAT] -> {command.strip()}")

        ser.close()

    except serial.SerialException as e:
        print(f"\nERROR SERIAL: No s'ha pogut obrir el port {SERIAL_PORT}. {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR INESPERAT: {e}")
        sys.exit(1)

if __name__ == "__main__":
    read_and_send_command()