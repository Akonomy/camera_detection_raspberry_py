# main.py
from TAG_RFID.mfrc_reader import read_mifare_data
from TAG_RFID.pn532_reader import read_pn532_data
import time

if __name__ == "__main__":
    print("Reading from MFRC522...")
    mifare_uid, mifare_data = read_mifare_data()
    print("MFRC522 UID:", mifare_uid, "Data:", mifare_data)

    time.sleep(2)

    print("Reading from PN532...")
    pn532_uid, pn532_data = read_pn532_data()
    print("PN532 UID:", pn532_uid, "Data:", pn532_data)
