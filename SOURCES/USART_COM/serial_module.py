#!/usr/bin/env python3
import serial
import time
import struct

# Configurare port serial – actualizează portul și viteza după necesitate
SERIAL_PORT = '/dev/ttyS0'  # Exemplu: '/dev/ttyUSB0' sau '/dev/serial0'
BAUD_RATE = 38400
TIMEOUT = 0.5

# Inițializare conexiune serială
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
    print("Serial port opened:", ser.name)
except Exception as e:
    print("Eroare la deschiderea portului serial:", e)
    raise


def send(cmd_type, val2, val1, vector):
    # Deschide portul serial (verifică ce port este activ pe sistemul tău)


        
    packet = bytearray()
    packet.append(0xAA)  # Marker de început
    packet.append(cmd_type & 0xFF)
    packet.append(val1 & 0xFF)
    packet.append(val2 & 0xFF)
    packet.append(len(vector) & 0xFF)  # Lungimea vectorului
    
    for item in vector:
        packet.append(item & 0xFF)
    
    packet.append(0xBB)  # Marker de sfârșit

    ser.write(packet)
    print("Pachet trimis:", list(packet))


    
    
        
        
    ser.flush()
  


    print("[END] Debug fixed message bytes:")
    
 

def receive():
    """
    Așteaptă primirea datelor de la portul serial.
    
    - Așteaptă maximum 3 secunde.
    - Dacă se primesc cel puțin 16 octeți, returnează primele 16.
    - Altfel, returnează datele disponibile.
    
    Returnează o listă de numere întregi.
    """
    start_time = time.time()
    data_buffer = bytearray()
    
    while True:
        if len(data_buffer) >= 16:
            return list(data_buffer[:16])
        
        if time.time() - start_time > 3:
            break
        
        bytes_to_read = 16 - len(data_buffer)
        new_data = ser.read(bytes_to_read)
        if new_data:
            data_buffer.extend(new_data)
        else:
            time.sleep(0.1)
    
    return list(data_buffer)

def process_command(cmd_type, val1, val2, vector):
    """
    Procesează o comandă pe baza parametrilor primiți.
    
    Această funcție primește:
      - cmd_type: tipul comenzii
      - val1: primul parametru (value1)
      - val2: al doilea parametru (value2)
      - vector: vectorul de date (listă; poate avea 1 sau 4 elemente)
      
    Mesajul transmis va fi:
        < cmd_type val1 val2 [ vector ] >
        
    Exemplu:
      - Dacă vectorul este [255], se va trimite: "< 1 10 20 [ 255 ] >"
      - Dacă vectorul este [100, 150, 200, 250], se va trimite: "< 1 10 20 [ 100 150 200 250 ] >"
      
    Dacă cmd_type este 3, se așteaptă un răspuns de la portul serial.
    """
    try:
        cmd_type = int(cmd_type)
        val1 = int(val1)
        val2 = int(val2)
        vector = [int(v) for v in vector]
    except ValueError:
        raise ValueError("Toți parametrii trebuie să fie numere întregi!")
    
    send(cmd_type, val1, val2, vector)
    
    if cmd_type == 3:
        return receive()
    else:
        return None

# Exemplu de testare interactivă
if __name__ == '__main__':
    try:
        while True:
            user_input = input("Introdu comanda în formatul 'type val1 val2 v1 [v2 v3 v4]' (sau 'exit' pentru ieșire): ").strip()
            if user_input.lower() == "exit":
                break
            if not user_input:
                continue
            
            tokens = user_input.split()
            try:
                # Primul token: cmd_type, al doilea: val1, al treilea: val2, restul: vector
                cmd_type = int(tokens[0])
                val1 = int(tokens[1])
                val2 = int(tokens[2])
                vector = [int(tok) for tok in tokens[3:]]
                if len(vector) < 1:
                    print("Trebuie să specificați cel puțin un element pentru vector!")
                    continue
            except ValueError:
                print("Toți parametrii trebuie să fie numere întregi!")
                continue
            
            try:
                result = process_command(cmd_type, val1, val2, vector)
                if result is not None:
                    print("Răspunsul primit:", result)
            except ValueError as ve:
                print("Eroare:", ve)
    except KeyboardInterrupt:
        print("\nProgram întrerupt de utilizator.")
