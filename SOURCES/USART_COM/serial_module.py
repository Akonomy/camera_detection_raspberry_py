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

def send(cmd_type, val1, val2, vector):
    """
    Trimite un mesaj binar format din octeți prin portul serial.
    
    Formatul mesajului:
        [start_marker, cmd_type, val2, val1, vector[0], vector[1], vector[2], vector[3], end_marker]
    
    Unde:
      - start_marker este de ex. 0x02,
      - end_marker este de ex. 0x03,
      - vectorul trebuie să aibă fie 1 element (care se replică pe cele 4 poziții), fie 4 elemente.
    """
    # Validăm că vectorul este o listă și îl convertim la int
    if not isinstance(vector, list):
        raise ValueError("Vectorul trebuie să fie o listă!")
    try:
        cmd_type = int(cmd_type)
        val1 = int(val1)
        val2 = int(val2)
        vector = [int(v) for v in vector]
    except ValueError:
        raise ValueError("Toți parametrii trebuie să fie numere întregi!")
    
    # Verificăm dacă vectorul are 1 sau 4 elemente
    if len(vector) not in (1, 4):
        raise ValueError("Vectorul trebuie să aibă fie 1 fie 4 elemente!")
    
    # Dacă avem un singur element, replicăm pe toate cele 4 poziții
    if len(vector) == 1:
        vector = vector * 4
    
    # Asigură-te că valorile sunt în intervalul 0-255
    for v in [cmd_type, val1, val2] + vector:
        if not (0 <= v <= 255):
            raise ValueError("Valorile trebuie să fie între 0 și 255!")
    
    # Definim markerii de început și sfârșit
    START_MARKER = 0x02
    END_MARKER = 0x03
    
    # Construim mesajul binar: 1 octet pentru markerul de început, 1 octet pentru fiecare valoare,
    # 4 octeți pentru vector și 1 octet pentru markerul de sfârșit, total 9 octeți.
    message = struct.pack('9B',
                          START_MARKER,
                          cmd_type,
                          val2,     # Urmând ordinea din vechiul protocol: cmd_type, val2, val1
                          val1,
                          vector[0],
                          vector[1],
                          vector[2],
                          vector[3],
                          END_MARKER)
    
    ser.write(message)
    ser.flush()
    print("[SENDING] Message bytes:", list(message))

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
