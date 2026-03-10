import bitalino
import serial
import sys
import time
import numpy as np
import struct 
from scipy import signal
from scipy.signal import find_peaks

# --- CONFIGURACIÓN SERIAL (RPi al Arduino) ---
# CAMBIE ESTO al puerto real del Arduino (e.g., /dev/ttyACM0 o /dev/ttyUSB0).
SERIAL_PORT = '/dev/ttyACM0' 
BAUD_RATE = 9600 # Debe coincidir con el Arduino
# ---------------------------------------------

# --- CONFIGURACIÓN LoRaWAN / DUTY CYCLE ---
# Intervalo MÍNIMO de envío para evitar la violación del Duty Cycle (ej. 30 segundos).
LORA_SEND_INTERVAL_SECONDS = 30 
# ------------------------------------------

# Adreça MAC del BITalino
MAC_ADDRESS = "98:D3:B1:FD:3D:BB" 
SAMPLING_RATE = 100 # Frecuencia de muestreo (Corregida a 100 Hz por compatibilidad).
ACQUISITION_CHANNELS = [0] # Canal Analógico A1 (Asumimos ECG)

# ÍNDICE DEL CANAL: Asumimos que A1 está en el índice 5 (si D1-D4 están comprimidos/omitidos).
CANAL_A1_INDEX = 5

# --- PARÁMETROS DE CALIBRACIÓN TÍPICA BITalino ---
VREF = 3.3 
BITS = 10 
MAX_RAW = 2**BITS - 1 # 1023

# --- CONFIGURACIÓN DEL FILTRO BAND-PASS (ECG) ---
# Filtro de banda pasante para aislar el complejo QRS (5-15 Hz)
LOW_CUTOFF_FREQ = 5   
HIGH_CUTOFF_FREQ = 15 
FILTER_ORDER = 4
nyquist_freq = SAMPLING_RATE / 2 # Ajustado a 50 Hz
normalized_low = LOW_CUTOFF_FREQ / nyquist_freq
normalized_high = HIGH_CUTOFF_FREQ / nyquist_freq

# Coeficientes del filtro Butterworth
b, a = signal.butter(FILTER_ORDER, [normalized_low, normalized_high], btype='band', analog=False)
# ------------------------------------------


def calculate_bpm(ecg_signal, fs):
    """
    Calcula el Ritmo Cardíaco (BPM) a partir de una señal ECG filtrada (método de detección de picos R).
    """
    if len(ecg_signal) < fs * 2: 
        return 0

    # Normalizar la señal para estabilizar la detección de picos
    ecg_signal = ecg_signal - np.mean(ecg_signal)
    
    # Detección de picos R: Usamos el 60% de la Desviación Estándar como altura mínima (sensibilidad).
    peaks, _ = find_peaks(ecg_signal, height=np.std(ecg_signal) * 0.6, distance=int(fs * 0.3)) # Distancia mínima de 300ms

    if len(peaks) < 2:
        return 0 

    # Calcular el intervalo R-R promedio y convertir a BPM
    rr_intervals = np.diff(peaks)
    mean_rr_interval_seconds = np.mean(rr_intervals) / fs
    bpm = 60 / mean_rr_interval_seconds
    
    return int(round(bpm))


def create_tlv_payload(bpm_value):
    """Crea el paquete binario TLV de 5 bytes para el valor BPM."""
    
    # Aseguramos que el BPM sea un valor que quepa en el formato (0-255 en este caso)
    final_value_int = int(round(bpm_value))
    if final_value_int < 0 or final_value_int > 255: 
        final_value_int = 0
        
    # Empaquetar el valor BPM en 2 bytes (Little Endian, Unsigned Short 'H')
    value_packed = struct.pack('<H', final_value_int) 

    payload_bytes = bytearray()
    
    # T (Type): 0x02 para Ritmo Cardíaco (BPM)
    payload_bytes.append(0x02) 
    
    # L (Length): 0x02 bytes para el valor
    payload_bytes.append(0x02) 
    
    # V (Value): Añadir los 2 bytes empaquetados
    payload_bytes.extend(value_packed) 

    # Separador: 0x0A ('\n')
    payload_bytes.append(0x0A) 
    
    return payload_bytes

def send_data_to_arduino(payload_bytes, serial_conn, value_sent):
    """Envía el paquete de bytes TLV (5 bytes) a través del puerto serial."""
    try:
        serial_conn.write(payload_bytes)
        print(f"ENVIADO -> TLV (5 bytes): BPM={value_sent} | Próximo envío en {LORA_SEND_INTERVAL_SECONDS}s.")
    except Exception as e:
        print(f"Error en el envío serial: {e}")


def bitalino_to_arduino_bridge():
    """Conecta BITalino, aplica filtro y envía BPM al Arduino respetando el Duty Cycle."""
    device = None
    serial_conn = None
    last_send_time = time.time() - LORA_SEND_INTERVAL_SECONDS 
    data_buffer = [] # Buffer para acumular los valores raw de A1
    
    try:
        # 1. Conexión Serial USB a Arduino
        serial_conn = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) 
        print(f"Conexión Serial USB establecida a {SERIAL_PORT} @ {BAUD_RATE} baud.")
        
        # 2. Conexión BITalino (Bluetooth)
        device = bitalino.BITalino(MAC_ADDRESS)
        print("Conectado a BITalino.")

        # 3. Configuración y Adquisición
        READ_SIZE = 100 # Leemos 1 segundo de datos cada vez (100 frames a 100Hz)
        device.start(SAMPLING_RATE, ACQUISITION_CHANNELS)
        print(f"Adquisición ECG iniciada a {SAMPLING_RATE} Hz. Enviará BPM cada {LORA_SEND_INTERVAL_SECONDS} segundos.")

        # 4. Bucle Principal de Lectura y Control de Tiempo
        while True:
            data_frames = device.read(READ_SIZE)
            current_time = time.time()
            
            if len(data_frames) == 0:
                time.sleep(0.1) 
                continue 
            
            # --- ACUMULACIÓN DE DATOS AL BUFFER ---
            try:
                raw_data_a1 = data_frames[:, CANAL_A1_INDEX]
                data_buffer.extend(raw_data_a1.tolist())
            except (TypeError, IndexError):
                print("Alerta: Error de lectura de data_frames. Ignorando muestras.")
                time.sleep(0.1)
                continue
            # ------------------------------------


            # 5. Control de Duty Cycle (Envío solo cada 30 segundos)
            if (current_time - last_send_time) >= LORA_SEND_INTERVAL_SECONDS:
                
                # Verificación de Buffer Mínimo (Necesitamos 5 segundos de datos para un BPM estable)
                if len(data_buffer) < SAMPLING_RATE * 5: # 500 frames necesarios (5s * 100Hz)
                    print("Alerta: Buffer insuficiente para BPM (necesita >5s de datos). Saltando envío.")
                    last_send_time = current_time 
                    time.sleep(1)
                    continue

                # --- PROCESAMIENTO: FILTRADO Y CÁLCULO DE BPM ---
                
                # 1. Aplicar el filtro al buffer de datos
                data_np = np.array(data_buffer)
                filtered_data = signal.lfilter(b, a, data_np)
                
                # 2. Calcular el BPM
                bpm_value = calculate_bpm(filtered_data, SAMPLING_RATE)
                
                # --- PREPARACIÓN DEL PAQUETE ---
                tlv_payload = create_tlv_payload(bpm_value) 
                    
                # --- ENVÍO SERIAL ---
                if len(tlv_payload) > 0:
                    send_data_to_arduino(tlv_payload, serial_conn, bpm_value) 
                    
                    # Limpiar el buffer para el próximo intervalo
                    data_buffer = [] 
                    print(f"CICLE COMPLETADO. Buffer limpiado.")

                # Actualizar el marcador de tiempo
                last_send_time = current_time 
                
            else:
                # 6. Muestra el estado de espera en la terminal
                time_remaining = LORA_SEND_INTERVAL_SECONDS - (current_time - last_send_time)
                sys.stdout.write(f"\r[ESPERA] Próximo envío en: {time_remaining:.1f}s | Buffer: {len(data_buffer)} muestras")
                sys.stdout.flush()
                
            time.sleep(0.1) 

    except serial.SerialException as se:
        print(f"ERROR SERIAL: No se puede abrir el puerto {SERIAL_PORT}. Asegúrese de que el Arduino esté conectado y tenga permisos.")
        print(f"Detalle: {se}")
    except Exception as e:
        print(f"\nERROR CRÍTICO. {e}")
    finally:
        if device:
            device.stop()
            device.close()
            print("\nBITalino desconectado.")
        if serial_conn and serial_conn.is_open:
            serial_conn.close()
            print("Puerto serial cerrado.")
        sys.exit()

if __name__ == "__main__":
    bitalino_to_arduino_bridge()