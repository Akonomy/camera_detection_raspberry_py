#!/usr/bin/env python3
import serial
import time
import struct
from USART_COM import usart  # Dacă folosiți și obiectul din acest modul

def main():
    # Configurare port serial (actualizați portul și viteza după necesitate)
    port = '/dev/ttyS0'  # de ex., '/dev/ttyUSB0' sau '/dev/serial0'
    baud_rate = 38400
    ser = serial.Serial(port, baud_rate, timeout=0.5)
    print("Serial port opened:", ser.name)
    
    while True:
        # Citim comanda de la utilizator (ex.: "1 5 3 100")
        user_cmd = input("USER CMD: ")
        if not user_cmd.strip():
            continue

        # Adăugăm newline-ul dacă protocolul o cere
        command_str = user_cmd.strip() + "\n"
        print(f"[SENDING] {command_str.strip()}")

        # Trimiterea comenzii prin portul serial
        ser.write(command_str.encode('utf-8'))
        
        # După trimitere, așteptăm răspunsul timp de 5 secunde
        print("Aștept răspuns pentru 5 secunde...")
        start_time = time.time()
        received_any = False
        
        while time.time() - start_time < 1:
            # Dacă există date în buffer-ul de recepție
            if True:
                data = ser.read(8)
              
                # Dacă se primește cel puțin un octet și toate valorile sunt 1, ignorăm mesajul.
                if data:
                    print("Received:", list(data))
                    received_any = True
            time.sleep(0.1)  # Mică întârziere pentru a evita bucla tight

        if not received_any:
            print("Nu s-au primit date relevante în 5 secunde.\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram întrerupt de utilizator.")
