# tag_reader/mfrc_reader.py
import RPi.GPIO as GPIO
import mfrc522 as MFRC522
import time

def uidToString(uid):
    return "".join(format(x, '02X') for x in uid)

def read_mifare_data():
    """
    Initialize the MFRC522 and attempt to read a MIFARE tag.
    Returns:
        (uid_str, extracted_data): A tuple with UID in hex string format and the extracted substring.
                                   If no data or no card, returns (None, None).
    """
    MIFAREReader = MFRC522.MFRC522(dev=1)

    # Try once to detect and read a card
    (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)
    if status == MIFAREReader.MI_OK:
        # Card detected
        (status, uid) = MIFAREReader.MFRC522_SelectTagSN()
        if status == MIFAREReader.MI_OK:
            uid_str = uidToString(uid)
            # Read multiple pages (4 bytes per page, 16 bytes per read call)
            all_data = []
            for page in range(4, 16, 4):
                block_data = MIFAREReader.MFRC522_Read(page)
                if block_data is not None:
                    all_data.extend(block_data)
                else:
                    break

            # Convert all_data to text, non-printable chars to '.'
            text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in all_data)

            # Extract substring starting from "en" up to the next "."
            start_index = text.find("en")
            if start_index != -1:
                end_index = text.find('.', start_index)
                if end_index != -1:
                    # Extract the substring after 'en' and before '.'
                    extracted = text[start_index+2:end_index].strip()
                    return (uid_str, extracted)
                else:
                    # No '.' found after 'en'
                    return (uid_str, None)
            else:
                # No 'en' found
                return (uid_str, None)
        else:
            # Could not select the tag
            return (None, None)
    else:
        # No card detected
        return (None, None)
