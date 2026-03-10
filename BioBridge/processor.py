import numpy as np
from scipy import signal
from scipy.signal import find_peaks
import logging


# --- PARÀMETRES DE CALIBRACIÓ TÍPICA BITalino ---
SAMPLING_RATE = 1000
VREF = 3.3                      # Voltatge de Referència
BITS = 10                       # Resolució
MAX_RAW = 2**BITS - 1           # 1023
SENSOR_GAIN = 1000              # Guany típic de l'amplificador de la placa
# ------------------------------------------------

# --- CONFIGURACIÓ DEL FILTRE BAND-PASS (ECG) ---
# Filtre de banda passant per aïllar el complex QRS (Ideal per a BPM)
LOW_CUTOFF_FREQ = 5             # Hz
HIGH_CUTOFF_FREQ = 15           # Hz
FILTER_ORDER = 4
nyquist_freq = SAMPLING_RATE / 2 
normalized_low = LOW_CUTOFF_FREQ / nyquist_freq
normalized_high = HIGH_CUTOFF_FREQ / nyquist_freq

# Creació dels coeficients del filtre (Band-Pass Butterworth)
b, a = signal.butter(FILTER_ORDER, [normalized_low, normalized_high], btype='band', analog=False)
# ------------------------------------------------



def apply_filter(raw_signal):
    """Aplica el filtre Band-Pass Butterworth a la senyal."""
    filtered_signal = signal.lfilter(b, a, raw_signal)
    logging.debug("Filtre Band-Pass aplicat correctament.")
    return filtered_signal

def check_arrhythmia(rr_intervals):
    """
    Comprova si existeix arítmia analitzant la variabilitat extrema dels intervals R-R.
    """
    # Necessitem almenys 3 intervals (4 pics R) per tenir una mitjana fiable
    if len(rr_intervals) < 3: 
        logging.info("Arítmia: No es pot determinar (mostra massa curta).")
        return 0 
        
    mean_rr = np.mean(rr_intervals)
    
    # Llindar de desviació del 35%
    threshold = mean_rr * 0.35
    
    # Comprova si algun interval individual es desvia més enllà del llindar
    is_arrhythmic = np.any(np.abs(rr_intervals - mean_rr) > threshold)
    
    result = 1 if is_arrhythmic else 0
    if result == 1:
        logging.warning(f"DETECCIÓ D'ARRÍTMIA: Irregularitat R-R > 20% (Umbral: {threshold:.2f} mostres)")
    else:
        logging.debug("Ritme cardíac regular detectat.")

    # Retorna 1 (Arítmia Detectada) o 0 (Ritme Normal)
    return result

def calculate_bpm_and_rr(ecg_signal, fs):
    """
    Calcula el Ritme Cardíac (BPM) i retorna els intervals R-R.
    """
    # Verificació de longitud mínima de la senyal (2 segons de dades)
    if len(ecg_signal) < fs * 2: 
        logging.warning("Càlcul BPM: Senyal massa curta per estabilitat.")
        return 0, np.array([]) 
    
    # 1. Normalització i detecció de pics
    ecg_signal = ecg_signal - np.mean(ecg_signal)
    
    # Paràmetres ajustats per a sensibilitat (60% de la desviació estàndard)
    peaks, _ = find_peaks(ecg_signal, height=np.std(ecg_signal) * 0.6, distance=int(fs * 0.3)) 

    if len(peaks) < 2:
        logging.warning(f"Càlcul BPM: Només s'han trobat {len(peaks)} pics. Retornant 0 BPM.")
        return 0, np.array([]) 

    # 2. Càlcul de l'interval R-R i BPM
    rr_intervals = np.diff(peaks)
    
    # Converteix l'interval R-R a temps (segons) i després a BPM
    mean_rr_interval_seconds = np.mean(rr_intervals) / fs
    
    bpm = 60 / mean_rr_interval_seconds
    
    logging.info(f"BPM Calculat: {int(round(bpm))} (Basat en {len(peaks)} pics R)")
    
    # Retorna el BPM calculat i l'array d'intervals R-R
    return int(round(bpm)), rr_intervals
