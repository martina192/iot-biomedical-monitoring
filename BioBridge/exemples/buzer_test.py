# Script de control del Buzzer del BITalino (Assumeix que el Buzzer està al pin D4)

import bitalino
import sys
import time

# --- Parámetros de Conexión ---
# IMPORTANTE: Sustituir por la MAC real de su dispositivo BITalino
MAC_ADDRESS = "98:D3:B1:FD:3D:BB" 

# Configuración del Pin Digital (D4 es el cuarto elemento en la lista [D1, D2, D3, D4])
D4_INDEX = 3 # Índice 3 para D4
TRIGGER_ON = [False, False, False, True] # Activamos solo D4 (Índice 3)
TRIGGER_OFF = [False, False, False, False] # Apagamos todos los pines

def buzz(device, duration):
    """Activa el buzzer por la duración especificada."""
    try:
        # Enciende el Buzzer (D4 = True)
        device.trigger([0,1])
        print("Buzzer: ON")
        time.sleep(duration)
        
        # Apaga el Buzzer (D4 = False)
        device.trigger([0,0])
        print("Buzzer: OFF")
        time.sleep(duration)
        
    except Exception as e:
        print(f"Error durante el control del Buzzer: {e}")

def buzzer_test():
    """Conecta al BITalino y realiza una secuencia de 3 bips cortos."""
    device = None
    
    try:
        device = bitalino.BITalino(MAC_ADDRESS)
        print(f"Conectado a la MAC: {MAC_ADDRESS}. Iniciando prueba del Buzzer...")

        # Secuencia de 3 bips cortos (utilizando el mismo pin D4)
        for i in range(3):
            buzz(device, 0.2) # 0.2 segundos ON, 0.2 segundos OFF
            
        print("Prueba de Buzzer completada. Desconectando...")

        device.close()

    except Exception as e:
        print(f"\nERROR: Falló la conexión o la prueba del Buzzer.")
        print(f"Detalle: {e}")
        if device:
            device.close()
        sys.exit()

if __name__ == "__main__":
    buzzer_test()