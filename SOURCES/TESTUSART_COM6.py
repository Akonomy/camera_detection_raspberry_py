from USART_COM.serial_module import process_command
import time
# Exemplu: trimite o comandă de tip 1 (control_car)
process_command(1, 0,1, 130)
time.sleep(2)
process_command(1, 2,5, 130)
time.sleep(1)

# Exemplu: trimite o comandă de tip 3 (request_data)
sensor_data = process_command(3, 1)
print("Datele de la senzori:", sensor_data)


def send_loop_commands():
    """
    Trimite comanda de tip 1 cu parametrii:
      - data1: variază de la 0 la 20,
      - data2: 5,
      - data3: 130,
    la un interval de 2 secunde între fiecare trimitere.
    
    Exemplu de comenzi trimise:
      1 0 5 130
      1 1 5 130
      1 2 5 130
      ...
      1 20 5 130
    """
    for val in range(0, 21):
        try:
            print(f"Sending command: 1 {val} 5 130")
            process_command(1, val, 7, 130)
        except ValueError as e:
            print(f"Eroare pentru valoarea {val}: {e}")
        time.sleep(2)
        
       
       
       
send_loop_commands(); 
