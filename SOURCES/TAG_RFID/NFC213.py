import time
import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.spi import PN532_SPI

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

def write213tag(uri_str):
    """
    Constructs and writes an NDEF record (for a URL) to an NTAG213.
    
    For NTAG213, block 4 is reserved for the CC (e.g., 0x01 0x03 0xA0 0x0C) and the
    NDEF message starts at block 5.
    
    The NDEF record is built for a URI record with:
      - Record Header: 0xD1
      - Type Length: 0x01
      - Payload Length: 1 + len(uri_str)  (1 byte for the identifier code, then URI)
      - Type: 0x55 (for URI)
      - Payload: 0x00 (no abbreviation) + uri_str encoded in UTF-8
    The TLV structure for NDEF is:
      0x03, <length>, <NDEF record>, 0xFE
    A constant prefix byte 0x34 is assumed at the start of block 5.
    
    Returns True if writing was successful, False otherwise.
    """
    # Convert URI to bytes.
    uri_bytes = uri_str.encode('utf-8')
    # Calculate payload length: 1 for identifier code + len(uri_bytes)
    payload_length = 1 + len(uri_bytes)
    # Calculate NDEF record total length: header (1) + type length (1) + payload length field (1) + type (1) + payload (payload_length)
    ndef_length = 5 + len(uri_bytes)
    
    # Build NDEF record.
    ndef_record = bytearray()
    ndef_record.append(0xD1)              # Record header: MB, ME, SR, TNF = well-known
    ndef_record.append(0x01)              # Type length: 1 byte (for 'U')
    ndef_record.append(payload_length)    # Payload length
    ndef_record.append(0x55)              # Type: 'U'
    ndef_record.append(0x04)              # Identifier code: 0x00 (no abbreviation)
    ndef_record.extend(uri_bytes)         # URI string payload

    # Build the full data to write starting at block 5.
    data_to_write = bytearray()
    data_to_write.append(0x34)            # Constant prefix (observed in dumps)
    data_to_write.append(0x03)            # TLV tag for NDEF
    data_to_write.append(ndef_length)     # TLV length (total length of the NDEF record)
    data_to_write.extend(ndef_record)     # The NDEF record itself
    data_to_write.append(0xFE)            # Terminator TLV

    # Initialize PN532.
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # Ajustează pinul dacă e necesar.
    pn532 = PN532_SPI(spi, cs_pin, debug=False)
    pn532.SAM_configuration()

    # Așteaptă detectarea unui tag.
    uid = pn532.read_passive_target(timeout=1.0)
    if uid is None:
        return False

    # Scrie datele începând de la blocul 5.
    return _write_blocks(pn532, 5, data_to_write)

# Exemplu de utilizare:
if __name__ == '__main__':
    URL = "depozitautomat.shop/store/"
    ID = "123"
    URLCOMPLET = URL + ID
    success = write213tag(URLCOMPLET)
    if success:
        print("Tag written successfully!")
    else:
        print("Failed to write tag.")
