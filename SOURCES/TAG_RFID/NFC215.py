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

def write215tag(uri_str):
    """
    Constructs and writes an NDEF URI record to an NTAG215.
    
    For NTAG215, the NDEF message is written starting at block 4.
    The NDEF record is constructed for a URI record with:
      - Record Header: 0xD1 (MB, ME, SR set, TNF = well-known)
      - Type Length: 0x01 (for the URI type, "U")
      - Payload Length: 1 + len(uri_str) (1 byte for the URI identifier code + bytes for the URI)
      - Type: 0x55 (ASCII for "U")
      - Payload: 0x00 (no abbreviation) followed by the URI string (UTF-8 encoded)
      
    The TLV structure for NDEF is:
      0x03, <NDEF record length>, <NDEF record>, 0xFE
      
    Returns True if writing was successful, False otherwise.
    """
    # Convert the URI string into bytes.
    uri_bytes = uri_str.encode('utf-8')
    # Calculate payload length: 1 for the identifier code + len(uri_bytes)
    payload_length = 1 + len(uri_bytes)
    
    # Construct the NDEF record.
    ndef_record = bytearray()
    ndef_record.append(0xD1)              # Record header: MB, ME, SR, TNF=well-known
    ndef_record.append(0x01)              # Type length: 1 byte ('U')
    ndef_record.append(payload_length)    # Payload length
    ndef_record.append(0x55)              # Type: 'U'
    ndef_record.append(0x04)              # Identifier code: 0x00 (no abbreviation)
    ndef_record.extend(uri_bytes)         # URI string payload

    # Calculate the overall length of the NDEF record.
    ndef_length = len(ndef_record)
    
    # Build the full TLV data to write.
    data_to_write = bytearray()
    data_to_write.append(0x03)            # TLV tag indicating NDEF message.
    data_to_write.append(ndef_length)     # Length of the NDEF record.
    data_to_write.extend(ndef_record)     # The NDEF record.
    data_to_write.append(0xFE)            # Terminator TLV.

    # Initialize the PN532 connection.
    spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
    cs_pin = DigitalInOut(board.D8)  # Ajustează pinul dacă este necesar.
    pn532 = PN532_SPI(spi, cs_pin, debug=False)
    pn532.SAM_configuration()

    # Wait for a tag to be present.
    uid = pn532.read_passive_target(timeout=1.0)
    if uid is None:
        return False

    # Write the TLV data starting at block 4.
    return _write_blocks(pn532, 4, data_to_write)

def main():
    # Combină URL-ul și ID-ul.
    URL = "depozitautomat.shop/store/"
    ID = "123"
    full_url = URL + ID
    print(f"Writing URL: {full_url}")
    success = write215tag(full_url)
    if success:
        print("Tag written successfully!")
    else:
        print("Failed to write tag.")

if __name__ == '__main__':
    main()
