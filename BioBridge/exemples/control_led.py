# Script de prueba para controlar un LED conectado al canal D3 del BITalino

import bitalino
import sys
import time

MAC_ADDRESS = "98:D3:B1:FD:3D:BB" 

def control_led(duration=5):
    """Conecta, enciende el LED D3 y luego lo apaga."""
    device = None
    
    try:
        device = bitalino.BITalino(MAC_ADDRESS)
        print(f"Conectado. Controlando LED D3 durante {duration} segundos...")
        
        # 1. ENCIENDE EL LED (D1=False, D2=False, D3=True, D4=False)
        # El tercer elemento de la lista controla D3.
        device.trigger([1, 0])
        print("LED D3: ON")
        
        time.sleep(duration)
        
        # 2. APAGA EL LED
        device.trigger([0, 0])
        print("LED D3: OFF. Desconectando...")

        device.close()

    except Exception as e:
        print(f"ERROR al controlar el LED: {e}")
        if device:
            device.close()
        sys.exit()

if __name__ == "__main__":
    control_led()