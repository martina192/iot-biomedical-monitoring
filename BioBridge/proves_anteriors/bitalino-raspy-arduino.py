import bitalino
import serial
import sys
import time
import numpy as np # Importem numpy per al tractament de dades

# --- CONFIGURACIÓ SERIAL (RPi al Arduino) ---
# IMPORTANTE: Canvia '/dev/ttyACM0' pel port serial real de l'Arduino.
# Utilitza 'ls /dev/tty*' per trobar-lo. Podria ser ttyUSB0 o ttyACM0.
SERIAL_PORT = '/dev/pts/2' 
BAUD_RATE = 9600 # La velocitat ha de coincidir amb la de l'Arduino
# ---------------------------------------------

# Adreça MAC del BITalino
MAC_ADDRESS = "98:D3:B1:FD:3D:BB" 
SAMPLING_RATE = 1000 
ACQUISITION_CHANNELS = [0, 1, 2, 3] # Canals Analògics A1-A4 (columnes 6 a 9 de l'array)

def send_data_to_arduino(data_frame, serial_conn):
    """Processa un frame de dades i l'envia per serial."""
    # EXEMPLE DE PROCESSAMENT:
    # 1. Selecciona només les columnes de les dades (columnes 6 en endavant)
    #    BITalino retorna: [NSeq, BATT, CHK, Digital_1, Digital_2, Digital_3, A1, A2, A3, A4, ...]
    
    # 2. Converteix les dades del sensor (columnes 6 a 9) a un valor sencer (o flotant)
    #    Aquí usem només el valor del primer canal analògic (columna 6).
    sensor_value = int(data_frame[6])

    # 3. Format per enviar: Usarem un format CSV simple amb una marca de final (newline)
    payload = f"{sensor_value}\n"
    #print(payload)
    
    try:
        # Envia la cadena de bytes a l'Arduino
        serial_conn.write(payload.encode('utf-8'))
        # print(f"Enviat: {payload.strip()}") # Descomenta per depurar
    except Exception as e:
        print(f"Error en l'enviament serial: {e}")

def bitalino_to_arduino_bridge():
    """Conecta el BITalino i envia les dades al port serial."""
    device = None
    serial_conn = None
    
    try:
        # 1. Conexió Serial USB a l'Arduino
        serial_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Espera a la inicialització de l'Arduino
        print(f"Connexió Serial USB establerta a {SERIAL_PORT} @ {BAUD_RATE} baud.")
        
        # 2. Connexió BITalino
        device = bitalino.BITalino(MAC_ADDRESS)
        print("Connectat a BITalino.")

        # 3. Configuració i Inici d'Adquisició
        device.start(SAMPLING_RATE, ACQUISITION_CHANNELS)
        print(f"Adquisició iniciada a {SAMPLING_RATE} Hz. Enviament de dades...")

        # 4. Bucle Continu de Lectura i Enviament
        while True:
            # Llegeix 10 frames per iteració per no saturar el serial
            data_frames = device.read(10)
            
            for frame in data_frames:
                # Cada frame es processa i s'envia
                send_data_to_arduino(frame, serial_conn)
                
            # Petit retard per no col·lapsar el processador
            time.sleep(0.01)

    except serial.SerialException as se:
        print(f"ERROR SERIAL: No es pot obrir el port {SERIAL_PORT}. Assegura't que l'Arduino estigui connectat i que el port sigui correcte.")
        print(f"Detall: {se}")
    except Exception as e:
        print(f"\nERROR CRÍTIC. {e}")
    finally:
        if device:
            device.stop()
            device.close()
            print("\nBITalino desconnectat.")
        if serial_conn and serial_conn.is_open:
            serial_conn.close()
            print("Port serial tancat.")
        sys.exit()

if __name__ == "__main__":
    bitalino_to_arduino_bridge()