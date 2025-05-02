from UTILS.ENCODER import encode_message
from USART_COM.serial_module import process_command
import time

# Vectorul cu direcții (2=right, 3=left, 4=back)
directions = [3,1,4,2,4,2,1]

# Codificare
cmd_type, val1, val2, data_bytes = encode_message(directions)



print(cmd_type, val1, val2, data_bytes)




#directie unica [right]
#process_command(4, 2, 1, [0])


# Trimitere
process_command(cmd_type, val1, val2, data_bytes)

time.sleep(1)

process_command(5 ,1, 1, [0])





