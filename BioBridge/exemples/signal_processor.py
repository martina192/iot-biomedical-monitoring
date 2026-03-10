import bitalino
import sys
import time
import numpy as np
from scipy import signal
from scipy.signal import find_peaks # Needed for R-peak detection
import matplotlib
import matplotlib.pyplot as plt 

# --- CONFIGURACIÓ ---
MAC_ADDRESS = "98:D3:B1:FD:3D:BB"
SAMPLING_RATE = 1000            # Freqüència vàlida (1000 Hz)
ACQUISITION_CHANNELS = [0]      # Canal Analògic A1 (índex 0)
ACQUISITION_DURATION = 5        # Segons de durada de la mostra

# ASSUMIM QUE: L'A1 és a l'índex 5
CANAL_A1_INDEX = 5              # L'índex de la dada A1 a l'array NumPy

# --- PARÀMETRES DE CALIBRACIÓ TÍPICA BITalino ---
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
nyquist_freq = SAMPLING_RATE / 2 # Ajustat a 500 Hz
normalized_low = LOW_CUTOFF_FREQ / nyquist_freq
normalized_high = HIGH_CUTOFF_FREQ / nyquist_freq

# Creació dels coeficients del filtre (Band-Pass Butterworth)
b, a = signal.butter(FILTER_ORDER, [normalized_low, normalized_high], btype='band', analog=False)
# ------------------------------------------------


def calculate_bpm(ecg_signal, fs):
    """
    Calcula el Ritme Cardíac (BPM) a partir d'una senyal ECG filtrada.
    """
    if len(ecg_signal) < fs * 2: # Necessitem almenys 2 segons de dades
        return 0,[0]

    # Normalitzem el senyal a 0-1 per estabilitzar la detecció de pics
    ecg_signal = ecg_signal - np.mean(ecg_signal)
    
    # Detecció de pics R simplificada 
    # Els paràmetres han de ser ajustats per l'usuari final.
    peaks, _ = find_peaks(ecg_signal, height=np.std(ecg_signal) * 0.8, distance=int(fs * 0.3)) # Distància mínima de 300ms

    if len(peaks) < 2:
        return 0 # No s'han trobat prou pics per calcular el BPM

    # Calcula l'interval R-R en mostres
    rr_intervals = np.diff(peaks)
    
    # Converteix l'interval R-R a temps (segons) i després a BPM
    mean_rr_interval_seconds = np.mean(rr_intervals) / fs
    
    # BPM = 60 / Temps_en_segons
    bpm = 60 / mean_rr_interval_seconds
    
    return int(round(bpm)),rr_intervals

def check_arrhythmia(rr_intervals):
    """
    Comprova si existeix arítmia analitzant la variabilitat extrema dels intervals R-R.
    Una desviació superior al 20% respecte a la mitjana es considera sospitosa d'arítmia.
    """
    # Necessitem almenys 3 intervals (4 pics R) per tenir una mitjana fiable
    if len(rr_intervals) < 3: 
        return 0 # 0 = No es pot determinar / No hi ha arítmia
        
    mean_rr = np.mean(rr_intervals)
    
    # Definim el llindar: 20% de desviació respecte a la mitjana
    # Aquesta és una mètrica clínica habitual per a la variabilitat significativa.
    threshold = mean_rr * 0.20 
    
    # Comprova si algun interval individual es desvia més enllà del llindar
    # np.abs(rr_intervals - mean_rr): calcula la diferència absoluta de cada interval respecte a la mitjana.
    # np.any(... > threshold): retorna True si alguna diferència supera el llindar.
    is_arrhythmic = np.any(np.abs(rr_intervals - mean_rr) > threshold)
    
    # Retorna 1 (Arítmia Detectada) o 0 (Ritme Normal)
    return 1 if is_arrhythmic else 0

def get_data_and_process():
    """Adquireix dades, les filtra i les retorna per a la visualització."""
    device = None
    
    try:
        # 1. Connexió BITalino
        device = bitalino.BITalino(MAC_ADDRESS)
        print(f"Connectat a BITalino amb MAC: {MAC_ADDRESS}")
        print(f"Adquirint dades durant {ACQUISITION_DURATION} segons a {SAMPLING_RATE} Hz...")

        # 2. Configuració i Inici d'Adquisició
        total_frames = int(ACQUISITION_DURATION * SAMPLING_RATE)
        
        device.start(SAMPLING_RATE, ACQUISITION_CHANNELS)

        # 3. Lectura de dades
        data = device.read(total_frames)

        # 4. Aturar i Desconnectar
        device.stop()
        device.close()
        print("Adquisició completada i dispositiu desconnectat.")
        
        if len(data) == 0:
            print("ERROR: No s'han rebut dades.")
            return None, None, None, None, None

        # 5. Extreure i Processar la Senyal
        raw_signal_a1 = data[:, CANAL_A1_INDEX]
        
        # Aplicació del FILTRE de BAND-PASS
        filtered_signal = signal.lfilter(b, a, raw_signal_a1)

        # 6. Conversió a Volts (Per a la visualització)
        physical_signal_raw = (raw_signal_a1 / MAX_RAW) * VREF
        physical_signal_filtered = (filtered_signal / MAX_RAW) * VREF
        

        # 7. Càlcul del BPM
        bpm_result, rr_intervals = calculate_bpm(filtered_signal, SAMPLING_RATE)
        

        # 8. Càlcul de l'Arrítmia
        arrhythmia_flag = check_arrhythmia(rr_intervals)
        
        return physical_signal_raw, physical_signal_filtered, SAMPLING_RATE, bpm_result, arrhythmia_flag

    except Exception as e:
        print(f"ERROR DURANT L'ADQUISICIÓ O PROCESSAMENT: {e}")
        if device:
            device.close()
        return None, None, None, None, None


def plot_signals(raw_data, filtered_data, fs, bpm, arrhythmia_flag,filename='signal_analysis.png'):
    """
    Mostra un gràfic comparant la senyal en brut i la senyal filtrada i el guarda a un fitxer.
    Afegeix la informació de ECG y l'arítmia al títol.
    """
    if raw_data is None:
        print("No hi ha dades per mostrar.")
        return

    arrhythmia_text = "SÍ" if arrhythmia_flag == 1 else "NO"
    title_color = 'red' if arrhythmia_flag == 1 else 'black'


    time_vector = np.arange(len(raw_data)) / fs # Crea l'eix del temps

    plt.figure(figsize=(12, 6))
    
    # Gràfic de la senyal en brut (RAW)
    plt.plot(time_vector, raw_data, label='Senyal en Brut (RAW)', alpha=0.7, color='gray')
    
    # Gràfic de la senyal filtrada
    plt.plot(time_vector, filtered_data, label=f'Senyal Filtrada ({LOW_CUTOFF_FREQ}-{HIGH_CUTOFF_FREQ} Hz Band-Pass)', color='red', linewidth=2)
    
    plt.title(f'Senyal ECG (A1) | Mostreig: {fs} Hz | BPM Calculat: {bpm} | ARÍTMIA: {arrhythmia_text}', color=title_color)
    plt.xlabel('Temps (segons)')
    plt.ylabel('Voltatge (V)')
    plt.legend()
    plt.grid(True, linestyle='--')
    
    # --- GUARDAR A FITXER ---
    plt.savefig(filename)
    plt.close() # Tanca la figura per alliberar memòria
    # ------------------------------------
    print(f"\nIMATGE EXPORTADA amb èxit a: {filename}")


if __name__ == "__main__":
    # La teva MAC real ha de ser a la constant MAC_ADDRESS
    raw_sig, filtered_sig, fs, bpm_result, arrhythmia_flag = get_data_and_process()
    
    # Mostra el gràfic (això obrirà una finestra a l'entorn gràfic)
    plot_signals(raw_sig, filtered_sig, fs, bpm_result,arrhythmia_flag)