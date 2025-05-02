# tag_reader/pn532_reader.py
import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.spi import PN532_SPI

def read_pn532_data():
    """
    Initialize the PN532 and attempt to read an NFC tag (NDEF).
    Returns:
        (uid_str, meaningful_data): A tuple with UID in hex string format and the extracted NDEF data.
                                    If no data or no card, returns (None, None).
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

    # Attempt to read and parse NDEF records
    start_block = 4
    max_blocks = 36
    ndef_data = bytearray()

    # Read all relevant blocks
    for block_number in range(start_block, start_block + max_blocks):
        try:
            block_data = pn532.ntag2xx_read_block(block_number)
            if block_data:
                ndef_data.extend(block_data)
            else:
                break
        except Exception:
            break

    # Parse and return meaningful data
    try:
        if ndef_data and ndef_data[0] == 0x01:
            payload_length = ndef_data[2]  # Length of the payload
            payload_start = 7  # Skip NDEF metadata
            payload = ndef_data[payload_start:payload_start + payload_length]
            decoded_payload = payload.decode('utf-8', errors='ignore').strip()

            # Skip the language code, typically 2 chars (e.g., "en")
            if len(decoded_payload) > 2:
                return (uid_str, decoded_payload[2:].strip())
            else:
                return (uid_str, None)
        else:
            return (uid_str, None)
    except Exception:
        return (uid_str, None)


print(read_pn532_data())