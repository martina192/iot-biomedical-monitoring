import bitalino
import sys
import time

# Utilitza la MAC del teu dispositiu sense prefix 'BTH'!
# (Exemple basat en la MAC que vas compartir abans)
MAC_ADDRESS = "98:D3:B1:FD:3D:BB" 

SAMPLING_RATE = 1000 
ACQUISITION_CHANNELS = [0, 1, 2, 3] # Canals Analògics 1-4 com a prova (A1, A2, A3, A4)

try:
    # 1. Connexió
    device = bitalino.BITalino(MAC_ADDRESS)
    print("Connectat a BITalino.")

    # 2. Configuració i Inici d'Adquisició
    device.start(SAMPLING_RATE, ACQUISITION_CHANNELS)
    print(f"Adquisició iniciada a {SAMPLING_RATE} Hz.")

    # 3. Lectura de dades (5 segons)
    num_frames = SAMPLING_RATE * 5
    data = device.read(num_frames)

    print("\nDades llegides (Primeres 5 files):")
    print(data[:5])

    # 4. Aturar i Desconnectar
    device.stop()
    device.close()
    print("\nDesconnexió completada.")

except Exception as e:
    print(f"ERROR: No s'ha pogut connectar o adquirir dades. Possiblement el dispositiu està apagat o l'adreça és incorrecta.")
    print(f"Detall de l'error: {e}")
    sys.exit()