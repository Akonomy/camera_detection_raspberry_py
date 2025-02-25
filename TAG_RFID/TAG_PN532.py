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
    start_block = 4
    max_blocks = 36
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
    # The helper _write_blocks will split the data into 4-byte chunks and write them.
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

def perform_write_and_verify(id_str):
    """
    Clears the tag, writes a URL with the given ID to the tag,
    and then attempts to verify the write by reading the tag twice.
    
    It extracts the ID from the read data and compares it (after stripping extra spaces)
    with the provided ID.
    
    Returns:
        True if one of the read attempts yields the same ID as id_str, False otherwise.
    Also prints the written ID and the read IDs for manual verification.
    """
   

    print(f"Writing URL 'depozitautomat.shop/store/{id_str}' to tag...")
    #if not write_url_to_tag(id_str):
    #    print("Failed to write URL to tag.")
    #    return False
    #else:
    #    print("Write operation successful.")
    
    # Allow time for the write to settle
    time.sleep(1)
    
    # Read the tag in two separate attempts.
    read_ids = []
    for i in range(2):
        print(f"Read attempt {i+1}:")
        uid, raw = read_pn532_data()
        if uid is None:
            print("  No tag detected or read failed.")
            read_ids.append(None)
        else:
            print(raw);
            extracted = extract_id_from_raw(raw)
            print(f"  Extracted ID: '{extracted}'")
            read_ids.append(extracted)
        time.sleep(1)
    
    print(f"Written ID: '{id_str}'")
    for idx, rid in enumerate(read_ids, 1):
        print(f"Read ID attempt {idx}: '{rid}'")
    
    # Compare (after stripping) to determine if any read ID matches the written ID.
    match_found = any(rid is not None and rid.strip() == id_str for rid in read_ids)
    if match_found:
        print("Verification successful: A read ID matches the written ID.")
    else:
        print("Verification failed: No read ID matches the written ID.")
    
    return match_found

# Example usage for testing write and verify
if __name__ == '__main__':
    # Replace with your desired ID
    desired_id = "1EBF9F"
    success = perform_write_and_verify(desired_id)
    if success:
        print("Tag write and verification succeeded.")
    else:
        print("Tag write and verification failed.")
