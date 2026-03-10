
import serial
import sys
import time
import numpy as np
import threading
import logging

# Importar mòduls propis
from collector import (
    connect_device, 
    start_acquisition, 
    read_frames, 
    stop_and_close, 
    CANAL_A1_INDEX,
    SAMPLING_RATE,
    toggle_actuator
)
from processor import (
    apply_filter, 
    check_arrhythmia, 
    calculate_bpm_and_rr
)
from transmitter import (
    create_tlv_payload, 
    send_data_to_arduino
)

# --- CONFIGURACIÓ SERIAL (RPi al Arduino) ---
SERIAL_PORT = '/dev/ttyACM0' 
#SERIAL_PORT = '/dev/pts/1'
BAUD_RATE = 9600 
# ---------------------------------------------

# --- CONFIGURACIÓ LORAWAN / DUTY CYCLE ---
LORA_SEND_INTERVAL_SECONDS = 180 
# ------------------------------------------

# Nom del fitxer de registre
LOG_FILENAME = 'biobridge.log'


def setup_logging():
    """Configura el sistema de registre per a fitxer i consola."""
    if logging.getLogger().handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILENAME),
            logging.StreamHandler(sys.stdout) # Mostrar a la consola/sortida del servei
        ]
    )

class DownlinkListener(threading.Thread):
    """Fil separat per escoltar comandes de Downlink (BUZZ_ON/OFF) des de l'Arduino."""
    
    def __init__(self, serial_conn, bitalino_device):
        threading.Thread.__init__(self, daemon=True, name="DownlinkThread") # Nom del fil
        self.serial_conn = serial_conn
        self.bitalino_device = bitalino_device
        self.running = True

    def run(self):
        logging.info("Downlink Listener Iniciat.")
        while self.running:
            # Comprovem si hi ha dades al buffer serial (no bloquejant)
            if self.serial_conn.in_waiting > 0:
                try:
                    # Llegeix la línia completa (p.ex., "BUZZ_ON\n" enviada per l'Arduino)
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    
                    # LÒGICA DE CONTROL D'ACTUADORS
                    #Buzzer ON
                    if line == "[DL] Downlink rebut: 00":
                        toggle_actuator(self.bitalino_device, 'BUZZER', "ON")
                    #Buzzer OFF
                    elif line == "[DL] Downlink rebut: 01":
                        toggle_actuator(self.bitalino_device, 'BUZZER', "OFF")
                    #Led ON
                    elif line == "[DL] Downlink rebut: 10":
                        toggle_actuator(self.bitalino_device, 'LED', "ON")
                    #Led OFF
                    elif line == "[DL] Downlink rebut: 11":
                        toggle_actuator(self.bitalino_device, 'LED', "OFF")
                    else:
                         logging.info(line)
                except Exception as e:
                     logging.warning(f"ALERTA FIL DOWNLINK: Error al llegir comanda. {e}")
            time.sleep(0.05) # Pausa per no saturar la CPU

    def stop(self):
        self.running = False




def bitalino_to_arduino_bridge():
    """Bucle principal que gestiona la adquisición, el procesamiento y el Duty Cycle."""
    setup_logging() # Configura el sistema de registro
    
    device = None
    serial_conn = None
    downlink_thread = None
    last_send_time = time.time() - LORA_SEND_INTERVAL_SECONDS 
    data_buffer = [] 
    stale_read_count = 0 # Contador per detectar la pèrdua de dades
    MAX_STALE_READS = 20 # Llindar per forçar la reconnexió (20 * 0.04s = 0.8s sense dades)
    
    
    try:
        # 1. Inicialización y Conexión Serial
        serial_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) 
        time.sleep(2) 
        logging.info(f"Connexió Serial USB establerta a {SERIAL_PORT} @ {BAUD_RATE} baud.")
        
        # 2. Conexión BITalino e Inicio de Adquisición
        device = connect_device()
        start_acquisition(device)
        
        # 3. Inicialitza i inicia el fil de Downlink
        downlink_thread = DownlinkListener(serial_conn, device)
        downlink_thread.start()
        
        READ_SIZE = 50 
        logging.info(f"Adquisició ECG en {SAMPLING_RATE} Hz. Enviament cada {LORA_SEND_INTERVAL_SECONDS}s.")

        # 4. Bucle Principal (Uplink)
        while True:
            current_time = time.time()
            
            # A) ADQUISICIÓN Y ACUMULACIÓN (Lectura d'alta freqüència)
            data_frames = read_frames(device, READ_SIZE)
            
            if len(data_frames) > 0:
                # Dades rebudes: omplim el buffer i reseteem el comptador d'inactivitat
                raw_data_a1 = data_frames[:, CANAL_A1_INDEX]
                data_buffer.extend(raw_data_a1.tolist())
                stale_read_count = 0
            else:
                # No s'han rebut dades: incrementem el comptador
                stale_read_count += 1
                logging.debug(f"Cap dada rebuda. Stale Count: {stale_read_count}")

            
            
            # B.1) LÒGICA DE RECONNEXIÓ
            if stale_read_count > MAX_STALE_READS:
                logging.warning("PÈRDUA DE CONNEXIÓ DETECTADA. Intentant reconnectar BITalino...")
                
                if downlink_thread:
                    downlink_thread.stop()
                    downlink_thread.join() # Espera que el fil s'aturi
                    logging.info("Fil Downlink aturat.")
                
                stop_and_close(device) # Tanca la connexió antiga
                time.sleep(3) # Pausa per alliberar el Bluetooth
                device = connect_device()
                start_acquisition(device)
                downlink_thread = DownlinkListener(serial_conn, device)
                downlink_thread.start()
                stale_read_count = 0 # Reseteja el comptador
                data_buffer = [] # Descartem les dades potencialment corruptes
                
            
            # B.2) CONTROL DEL DUTY CYCLE
            if (current_time - last_send_time) >= LORA_SEND_INTERVAL_SECONDS:
                
                # 1. Comprovació de buffer mínim
                if len(data_buffer) < SAMPLING_RATE * 5: # Mínim 5 segons de dades per a un càlcul estable
                    logging.warning(f"ALERTA: Buffer insuficient ({len(data_buffer)}). Saltant enviament.")
                    last_send_time = current_time 
                    time.sleep(1)
                    continue

                # --- PROCESSAMENT CIENTÍFIC ---
                data_np = np.array(data_buffer)
                filtered_data = apply_filter(data_np)
                
                # 2. Càlcul de BPM i Arrítmia
                bpm_value, rr_intervals = calculate_bpm_and_rr(filtered_data, SAMPLING_RATE)
                arrhythmia_flag = check_arrhythmia(rr_intervals)
                
                # 3. Empaquetament TLV i Enviament Serial
                tlv_payload = create_tlv_payload(bpm_value, arrhythmia_flag) 
                    
                if len(tlv_payload) > 0:
                    send_data_to_arduino(tlv_payload, serial_conn, bpm_value, arrhythmia_flag) 
                    data_buffer = [] 
                    logging.info("CICLE COMPLETADO. Buffer limpio.")

                last_send_time = current_time 
                
            else:
                # 5. Muestra el estado de espera
                time_remaining = LORA_SEND_INTERVAL_SECONDS - (current_time - last_send_time)
                sys.stdout.write(f"\r[ESPERA] Próximo envío en: {time_remaining:.1f}s | Buffer: {len(data_buffer)} muestras")
                sys.stdout.flush()
                
            # CORRECCIÓ: Si estem en el període d'espera llarga (Duty Cycle), dormir més (0.5s)
            if (current_time - last_send_time) < LORA_SEND_INTERVAL_SECONDS:
                 time.sleep(0.5) 
            else:
                 time.sleep(0.04) # Pausa mínima per al cicle de lectura ràpida.

    except serial.SerialException as se:
        logging.error(f"ERROR CRÍTICO SERIAL: No se puede abrir el puerto. {se}", exc_info=True)
    except Exception as e:
        logging.error(f"ERROR CRÍTICO INESPERADO. {e}", exc_info=True)
    finally:
        if downlink_thread:
            downlink_thread.stop()
        stop_and_close(device)
        if serial_conn and serial_conn.is_open:
            serial_conn.close()
            logging.info("Puerto serial cerrado.")
        sys.exit()

if __name__ == "__main__":
    bitalino_to_arduino_bridge()
