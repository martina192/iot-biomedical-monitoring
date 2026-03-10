# Script de prueba mínima para conexión y adquisición de datos con BITalino

import bitalino
import sys
import time

# --- Parámetros de Conexión ---
MAC_ADDRESS = "98:D3:B1:FD:3D:BB" 

# Configuración de Adquisición
SAMPLING_RATE = 100       # Frecuencia de muestreo (100 Hz es un valor seguro y compatible)
ACQUISITION_CHANNELS = [0] # Canal Analógico 1 (A1). Índice 0 es el primer canal analógico.
READ_FRAMES = 100          # Número de frames a leer (1 segundo de datos a 100 Hz)

def test_bitalino_connection():
    """Establece conexión, adquiere una muestra y se desconecta."""
    device = None
    
    try:
        # 1. Conexión al dispositivo a través de Bluetooth
        device = bitalino.BITalino(MAC_ADDRESS)
        print(f"Intento de conexión a la MAC: {MAC_ADDRESS}...")

        # 2. Configuración e Inicio de Adquisición
        device.start(SAMPLING_RATE, ACQUISITION_CHANNELS)
        print(f"Adquisición iniciada a {SAMPLING_RATE} Hz en el Canal A1.")

        # 3. Lectura de un bloque de prueba (1 segundo de datos)
        data = device.read(READ_FRAMES)
        
        # 4. Finalización y Desconexión
        device.stop()
        device.close()
        print("Adquisición de prueba completada.")
        
        # 5. Muestra de los datos recibidos
        if len(data) > 0:
            print("\n--- Datos de Prueba (Primer Frame) ---")
            print(data[0])
            print("--------------------------------------")
        else:
            print("Éxito en la conexión, pero no se recibieron datos.")

    except Exception as e:
        print(f"\nERROR: Falló la conexión o la adquisición.")
        print(f"Detalle: {e}")
        if device:
            device.close()
        sys.exit()

if __name__ == "__main__":
    test_bitalino_connection()
