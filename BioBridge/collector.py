import bitalino
import numpy as np
import sys
import time
import logging


# --- CONFIGURACIÓ ---
MAC_ADDRESS = "98:D3:B1:FD:3D:BB"
SAMPLING_RATE = 1000            # Freqüència vàlida (1000 Hz)
ACQUISITION_CHANNELS = [1]      # Canal Analògic A1 (índex 0)
ACQUISITION_DURATION = 5        # Segons de durada de la mostra
CANAL_A1_INDEX = 5               # L'índex de la dada A1 a l'array NumPy

# Pins Digitals del BITalino (O1=D1, O2=D2)
BUZZER_PIN_INDEX = 1 # D2 (O2)
LED_PIN_INDEX = 0    # D1 (O1)

# Estats de Trigger para el mètode device.trigger([D1, D2])
TRIGGER_OFF = [0, 0]
TRIGGER_BUZZ_ON = list(TRIGGER_OFF)
TRIGGER_BUZZ_ON[BUZZER_PIN_INDEX] = 1
TRIGGER_LED_ON = list(TRIGGER_OFF)
TRIGGER_LED_ON[LED_PIN_INDEX] = 1
# -----------------------------


# def connect_device():
#     """Estableix i retorna la connexió al dispositiu BITalino."""
#     try:
#         device = bitalino.BITalino(MAC_ADDRESS)
#         logging.info(f"Connectat a BITalino amb MAC: {MAC_ADDRESS}")
#         return device
#     except Exception as e:
#         logging.error(f"ERROR: Ha fallat la connexió inicial de Bluetooth. {e}")
#         sys.exit(1)
def connect_device(max_retries=5):
    """Estableix i retorna la connexió al dispositiu BITalino, gestionant errors de codificació."""
    for attempt in range(max_retries):
        try:
            device = bitalino.BITalino(MAC_ADDRESS)
            logging.info(f"Connectat a BITalino amb MAC: {MAC_ADDRESS} (Intent {attempt + 1}/{max_retries})")
            return device
        except UnicodeDecodeError as e:
            # Captura errors de la llibreria quan el Bluetooth és inestable (dades binàries invàlides)
            logging.warning(f"AVÍS: Error de codificació (UnicodeDecodeError) durant la connexió (Intent {attempt + 1}/{max_retries}). Reintentant en 1 segon.")
            time.sleep(1)
        except Exception as e:
            logging.error(f"ERROR: Ha fallat la connexió inicial de Bluetooth. {e}")
            if attempt == max_retries - 1:
                logging.error("ERROR CRÍTIC: El dispositiu BITalino no s'ha pogut connectar després de múltiples intents.")
                sys.exit(1)
            time.sleep(1)
    
    # Només s'executa si el bucle falla i s'esgoten els intents per errors no UnicodeDecodeError
    logging.error("ERROR CRÍTIC: El dispositiu BITalino no s'ha pogut connectar després de múltiples intents (Esgotament de retries).")
    sys.exit(1)

def start_acquisition(device):
    """Configura i inicia l'adquisició de dades del BITalino."""
    try:
        device.start(SAMPLING_RATE, ACQUISITION_CHANNELS)
        logging.info(f"Adquisició iniciada a {SAMPLING_RATE} Hz en el Canal A1.")
    except Exception as e:
        logging.error(f"ERROR: Ha fallat en iniciar l'adquisició (Paràmetre invàlid?). {e}")
        device.close()
        sys.exit(1)

def read_frames(device, read_size):
    """Llegeix un bloc de frames del dispositiu."""
    try:
        data = device.read(read_size)
        return data
    except Exception as e:
        # En el bucle principal, és millor gestionar aquesta excepció per no aturar el programa.
        return np.array([]) # Retorna un array buit per indicar fallada en la lectura.

def stop_and_close(device):
    """Atura l'adquisició i tanca la connexió Bluetooth."""
    if device:
        device.stop()
        device.close()
        logging.info("BITalino desconnectat.")

def toggle_actuator(device, actuator, state):
    """
    Controla el Buzzer o LED del BITalino a través de Bluetooth.
    actuator = 'BUZZER' o 'LED'
    state = 'ON' o 'OFF'
    """
    try:
        if actuator == 'BUZZER':
            trigger = TRIGGER_BUZZ_ON if state == "ON" else TRIGGER_OFF
            device.trigger(trigger)
            logging.info(f"Buzzer (D2): {state}")
        elif actuator == 'LED':
            trigger = TRIGGER_LED_ON if state == "ON" else TRIGGER_OFF
            device.trigger(trigger)
            logging.info(f"LED (D1): {state}")
    except bitalino.BitalinoError as e:
        # Captura errors de hardware (p.ex., pin no connectat)
        logging.warning(f"ALERTA BITALINO: No s'ha pogut activar l'actuador {actuator}. {e}")
    except Exception as e:
        logging.error(f"ERROR: Ha fallat el toggle de l'actuador. {e}")