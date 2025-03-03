import time
import board
import busio
import re
from digitalio import DigitalInOut
from adafruit_pn532.spi import PN532_SPI

def read_pn532_data():
    """
    Initialize the PN532 and attempt to read an NFC tag.
    Returns:
        (uid_str, raw_data): A tuple with UID in hex string format and the raw bytearray of all read blocks.
                             If no card is detected, returns (None, None).
    """
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # Adjust pin as necessary
    pn532 = PN532_SPI(spi, cs_pin, debug=False)
    pn532.SAM_configuration()
    uid = pn532.read_passive_target(timeout=1.0)
    if uid is None:
        return (None, None)
    uid_str = "".join(f"{i:02X}" for i in uid)
    # Start reading from block 0 to get the complete memory dump
    start_block = 0
    max_blocks = 20
    raw_data = bytearray()
    for block_number in range(start_block, start_block + max_blocks):
        try:
            block_data = pn532.ntag2xx_read_block(block_number)
            if block_data:
                raw_data.extend(block_data)
            else:
                break
        except Exception:
            break
    return (uid_str, raw_data)

def extract_id_from_raw(raw_data):
    """
    Decode the raw data and extract the ID from the URL.
    Expected URL format: 'depozit.automat.shop/store/ID' (the dot between 'depozit' and 'automat' is optional)
    
    Returns:
        The extracted ID (string) if found, or None otherwise.
    """
    if not raw_data:
        return None
    data_str = raw_data.decode('utf-8', errors='ignore')
    pattern = r'depozit\.?automat\.shop/store/(\w+)'
    match = re.search(pattern, data_str)
    if match:
        return match.group(1)
    return None

def _write_blocks(pn532, start_block, data_bytes):
    """
    Helper function to write data_bytes to the tag starting at start_block.
    Splits data_bytes into 4-byte chunks (padding if necessary) and writes each block.
    
    Returns:
        True if all blocks are written successfully, False otherwise.
    """
    # Pad data_bytes to a multiple of 4 bytes.
    remainder = len(data_bytes) % 4
    if remainder != 0:
        data_bytes += b'\x00' * (4 - remainder)
    total_blocks = len(data_bytes) // 4
    for i in range(total_blocks):
        block = data_bytes[i*4:(i+1)*4]
        success = pn532.ntag2xx_write_block(start_block + i, list(block))
        if not success:
            return False
    return True
    
def write_raw_data_to_tag(raw_data):
    """
    Write the provided raw data (bytes or bytearray) exactly to the NFC tag,
    starting at block 4.
    
    Args:
        raw_data: A bytes or bytearray object representing the exact data to write.
        
    Returns:
        True if the write operation is successful, False otherwise.
    """
    # Initialize PN532 connection.
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)
    pn532 = PN532_SPI(spi, cs_pin, debug=False)
    pn532.SAM_configuration()
    
    # Wait for a tag to be present.
    uid = pn532.read_passive_target(timeout=1.0)
    if uid is None:
        return False

    # Write the raw data starting at block 4.
    return _write_blocks(pn532, 4, raw_data)
    
def clear_tag():
    """
    Clear the tag's user memory by writing zeros from block 4 up to block 39.
    Returns:
        True if successful, False otherwise.
    """
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)
    pn532 = PN532_SPI(spi, cs_pin, debug=False)
    pn532.SAM_configuration()
    uid = pn532.read_passive_target(timeout=1.0)
    if uid is None:
        return False
    # Clear 36 blocks (4 to 39): 36 blocks * 4 bytes each = 144 zero bytes.
    clear_data = b'\x00' * (36 * 4)
    return _write_blocks(pn532, 4, clear_data)

def write_url_to_tag(id_str):
    """
    Construct a URL in the format 'depozitautomat.shop/store/ID' using the provided ID
    and write it to the NFC tag starting at block 4.
    
    Returns:
        True if writing was successful, False otherwise.
    """
    url = f"depozitautomat.shop/store/{id_str}"
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)
    pn532 = PN532_SPI(spi, cs_pin, debug=False)
    pn532.SAM_configuration()
    uid = pn532.read_passive_target(timeout=1.0)
    if uid is None:
        return False
    data_bytes = url.encode('utf-8')
    return _write_blocks(pn532, 4, data_bytes)

def read_pn532_table():
    """
    Read the NFC tag and return the UID and raw data.
    This function is similar to read_pn532_data but is intended to be used 
    in conjunction with process_raw_data_table() to display a table view.
    
    Returns:
        (uid_str, raw_data) tuple.
    """
    uid_str, raw_data = read_pn532_data()
    return uid_str, raw_data

def process_raw_data_table(raw_data, start_block=0):
    """
    Process raw_data and print a table with the following columns:
    - Block number (starting from 0)
    - Address in decimal and hex (block number + start_block)
    - 4 bytes in hex
    - ASCII representation (non-printable characters are replaced with '.')
    
    Args:
        raw_data: bytearray containing the data read from the tag.
        start_block: The starting block number corresponding to the first block in raw_data.
    """
    if not raw_data:
        print("No raw data to display.")
        return

    num_blocks = len(raw_data) // 4
    print("{:<6} {:<12} {:<20} {}".format("Block", "Address", "Hex bytes", "ASCII"))
    print("-" * 60)
    for block in range(num_blocks):
        block_bytes = raw_data[block*4:(block+1)*4]
        address_dec = start_block + block
        address_hex = f"{address_dec:02X}"
        hex_bytes = " ".join(f"{b:02X}" for b in block_bytes)
        ascii_repr = "".join(chr(b) if 32 <= b < 127 else '.' for b in block_bytes)
        print("{:<6} {:<12} {:<20} {}".format(block, f"{address_dec}/{address_hex}", hex_bytes, ascii_repr))
        
        
        
        

def get_tag_type(raw_data):
    """
    Determină tipul tagului pe baza datelor brute.
    Se presupune că:
      - Pentru NTAG213, blocul 4 (octeții 16-19) este CC-ul: b'\x01\x03\xa0\x0c'
      - Pentru NTAG215, blocul 4 începe cu 0x03 și conține NDEF direct
    Returnează:
      "NTAG213", "NTAG215" sau "Unknown" dacă nu se poate determina.
    """
    # Verificăm dacă raw_data are cel puțin 20 de octeți
    if raw_data is None or len(raw_data) < 20:
        return "Unknown"
    
    # Extragem blocul 4 (de la index 16 la 19)
    block4 = raw_data[16:20]
    
    # Dacă blocul 4 este exact CC-ul NTAG213:
    if block4 == bytearray(b'\x01\x03\xa0\x0c'):
        return "NTAG213"
    # Dacă începe cu 0x03, presupunem că este NTAG215 (pentru tag scris, de exemplu "03 25 D1 01")
    elif block4[0] == 0x03:
        return "NTAG215"
    else:
        return "Unknown"
        
        
        
                
# Exemplu de utilizare:
if __name__ == '__main__':
    uid, raw_data = read_pn532_table()
    if uid is None:
        print("No tag detected.")
    else:
        print(f"UID: {uid}")
        print("Raw data table:")
        process_raw_data_table(raw_data, start_block=0)
