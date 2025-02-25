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
    # Configure SPI connection
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # Adjust pin as necessary
    pn532 = PN532_SPI(spi, cs_pin, debug=False)

    # Configure PN532 to read NFC tags
    pn532.SAM_configuration()

    # Try once to detect and read a tag
    uid = pn532.read_passive_target(timeout=1.0)
    if uid is None:
        # No card detected
        return (None, None)

    uid_str = "".join(f"{i:02X}" for i in uid)

    # Read all relevant blocks
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

    # Decode raw data to a string, ignoring errors
    data_str = raw_data.decode('utf-8', errors='ignore')
    
    # Debug: print the decoded data to see what we are working with
    # print("Decoded data:", data_str)
    
    # Use regex to find the URL pattern and capture the ID
    # The pattern allows an optional dot between 'depozit' and 'automat'
    pattern = r'depozit\.?automat\.shop/store/(\w+)'
    match = re.search(pattern, data_str)
    if match:
        return match.group(1)
    return None

# Example usage in a main program
if __name__ == '__main__':
    uid, raw = read_pn532_data()
    if uid is None:
        print("PN532 - No card detected or data read failed.")
    else:
        print(f"PN532 - UID: {uid}")
        extracted_id = extract_id_from_raw(raw)
        if extracted_id:
            print(f"Extracted ID: {extracted_id}")
        else:
            print("No valid URL or ID found in the data.")
