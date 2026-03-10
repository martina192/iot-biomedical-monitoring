import serial
import struct
import time
import logging

# --- FORMAT DE PAQUET ---
# T (Type): 0x02 (BPM)
# L (Length): 0x02 (1 byte BPM + 1 byte Flag)
# V (Value): 2 bytes
# Separador: 1 byte ('\n')
# Total: 5 bytes per paquet TLV
# ------------------------

def create_tlv_payload(bpm_value, arrhythmia_flag):
    """Crea el paquet binari TLV de 5 bytes (T, L, BPM, Flag, \n) per a l'Arduino."""
    
    # 1. Empaquetament del BPM (1 byte)
    final_bpm = int(round(bpm_value))
    # Seguretat: Assegurem que el BPM càpiga en 1 byte (0-255)
    if final_bpm < 0 or final_bpm > 255: 
        final_bpm = 0
        logging.warning(f"BPM ({bpm_value}) fora de rang. S'ha enviat 0.")
        
    # El BPM es guarda en 1 byte ('B')
    value_packed = struct.pack('B', final_bpm) 
    #value_packed = [final_bpm]

    # --- Construcció del missatge binari (TLV: 4 bytes + 1 Separador) ---
    payload_bytes = bytearray()
    
    # T (Type): 0x02 per a Ritme Cardíac (BPM)
    payload_bytes.append(0x02) 
    
    # L (Length): 0x02 bytes (1 byte BPM + 1 byte Flag)
    payload_bytes.append(0x02) 
    #payload_bytes.append(0x01)

    # V1 (Value - BPM): Afegir 1 byte del BPM
    payload_bytes.extend(value_packed) 

    # V2 (Value - Flag): Afegir 1 byte del Flag d'Arrítmia
    payload_bytes.append(arrhythmia_flag) 
    
    # Separador: 0x0A ('\n')
    payload_bytes.append(0x0A) 
    
    return payload_bytes

def send_data_to_arduino(payload_bytes, serial_conn, bpm_value, arr_flag):
    """Envia el paquet de bytes TLV (5 bytes) a través del port serial."""
    try:
        serial_conn.write(payload_bytes)
        logging.info(f"ENVIAT -> TLV (BPM={bpm_value}, Arrítmia={arr_flag})")
    except Exception as e:
        logging.error(f"ERROR CRÍTIC: Ha fallat l'enviament serial. {e}")