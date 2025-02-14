#!/usr/bin/env python3
import serial
import time

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

def send(*args):
    """
    Trimite un mesaj formatat între '<' și '>' prin portul serial.
    Se acceptă între 1 și 4 parametri.
    
    Exemple:
      send(1, 2, 3, 4)  => trimite "< 1 2 3 4 >"
      send(3, 2)        => trimite "< 3 2 >"
    """
    if not args:
        raise ValueError("Trebuie să specificați cel puțin un parametru!")
    if len(args) > 4:
        raise ValueError("Maxim 4 parametri sunt permisi!")
    
    message = "< " + " ".join(str(arg) for arg in args) + " >\n"
    ser.write(message.encode('utf-8'))
    ser.flush()
    print(f"[SENDING] {message.strip()}")

def receive():
    """
    Așteaptă primirea datelor de la portul serial.
    
    - Așteaptă maximum 3 secunde.
    - Dacă se primesc cel puțin 16 octeți (2 seturi a câte 8 biți), returnează imediat primele 16.
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

def process_command(cmd_type, data1=0, data2=0, data3=0):
    """
    Procesează o comandă pe baza parametrilor primiți și efectuează validările necesare.
    
    Formatul parametrilor:
      - cmd_type: tipul de comandă (1, 2, 3, 4 sau 5)
      - data1, data2, data3: valorile asociate comenzii.
      
    Validări:
      Tip 1 (control_car):
         * data1 (direcție) trebuie să fie ≤ 20.
         * data2 (tick) trebuie să fie ≤ 250.
         * data3 (speed) trebuie să fie ≤ 250.
         
      Tip 2 (control_servo):
         * data1 (servo_id) trebuie să fie între 180 și 190.
         * data2 (angle) trebuie să fie ≤ 180.
         * data3 trebuie să fie 0.
         
      Tip 3 (request_data):
         * data1 (sensor_type) trebuie să fie 1 sau 2.
         * data2 și data3 sunt ignorate (se recomandă 0).
         
      Tip 4 (save_next_cross_direction):
         * data1 (direcția) trebuie să fie între 0 și 4.
         * data2 și data3 sunt ignorate (se recomandă 0).
         
      Tip 5 (debug_mode):
         * data1, data2 și data3 trebuie să fie ≤ 250.
    
    După validări, comanda este transmisă prin funcția `send`.
    Dacă tipul comenzii este 3, se așteaptă un răspuns și se returnează rezultatul.
    Pentru celelalte tipuri, se returnează None.
    """
    # Conversie la int (în cazul în care sunt primite sub formă de string)
    try:
        cmd_type = int(cmd_type)
        data1 = int(data1)
        data2 = int(data2)
        data3 = int(data3)
    except ValueError:
        raise ValueError("Toți parametrii trebuie să fie numere întregi!")
    
    # Validări în funcție de tipul comenzii
    if cmd_type == 1:
        if data1 > 20:
            raise ValueError("Pentru tipul 1, direcția (data1) trebuie să fie ≤ 20.")
        if data2 > 250:
            raise ValueError("Pentru tipul 1, tick (data2) trebuie să fie ≤ 250.")
        if data3 > 250:
            raise ValueError("Pentru tipul 1, speed (data3) trebuie să fie ≤ 250.")
    elif cmd_type == 2:
        if data1 < 180 or data1 > 190:
            raise ValueError("Pentru tipul 2, servo_id (data1) trebuie să fie între 180 și 190.")
        if data2 > 180:
            raise ValueError("Pentru tipul 2, angle (data2) trebuie să fie ≤ 180.")
        if data3 != 0:
            raise ValueError("Pentru tipul 2, se acceptă doar doi parametri; data3 trebuie să fie 0.")
    elif cmd_type == 3:
        if data1 not in (1, 2):
            raise ValueError("Pentru tipul 3, sensor_type (data1) trebuie să fie 1 sau 2.")
        if data2 != 0 or data3 != 0:
            print("Avertisment: Pentru tipul 3 se utilizează doar data1; data2 și data3 vor fi ignorate.")
    elif cmd_type == 4:
        if data1 > 4:
            raise ValueError("Pentru tipul 4, direcția (data1) trebuie să fie între 0 și 4.")
        if data2 != 0 or data3 != 0:
            print("Avertisment: Pentru tipul 4 se utilizează doar data1; data2 și data3 vor fi ignorate.")
    elif cmd_type == 5:
        if data1 > 250 or data2 > 250 or data3 > 250:
            raise ValueError("Pentru tipul 5, valorile trebuie să fie ≤ 250.")
    else:
        raise ValueError("Tipul de comandă nu este valid!")
    
    # Transmiterea comenzii formatate
    send(cmd_type, data1, data2, data3)
    
    # Dacă se solicită date (tipul 3), așteptăm și returnăm răspunsul
    if cmd_type == 3:
        return receive()
    else:
        return None

# Exemplu de testare interactivă
if __name__ == '__main__':
    try:
        while True:
            user_input = input("Introdu comanda în formatul 'type data1 data2 data3' (sau 'exit' pentru ieșire): ").strip()
            if user_input.lower() == "exit":
                break
            if not user_input:
                continue
            
            tokens = user_input.split()
            try:
                # Convertim token-urile în int; dacă sunt mai puține de 4, completăm cu 0
                values = [int(tok) for tok in tokens]
            except ValueError:
                print("Toți parametrii trebuie să fie numere întregi!")
                continue
            while len(values) < 4:
                values.append(0)
            
            try:
                result = process_command(*values[:4])
                if result is not None:
                    print("Răspunsul primit:", result)
            except ValueError as ve:
                print("Eroare:", ve)
    except KeyboardInterrupt:
        print("\nProgram întrerupt de utilizator.")
