import time
from TAG_RFID import mfrc_reader, TAG_PN532 as pn532_reader

def main():
    max_attempts = 3
    attempt = 0
    test_data = bytearray(b'\x01\x03\xa0\x0c4\x03&\xd1\x01"U\x04depozitautomat.shop/store/1234567\xfe\x00\x00')



    while attempt < max_attempts:
        print(f"Attempt {attempt+1} of {max_attempts}:")

        # Try reading with the MFRC522-based reader
        uid_mf, data_mf = mfrc_reader.read_mifare_data()
        if uid_mf is not None:
            print(f"MFRC522 - UID: {uid_mf}, Data: {data_mf}")
        else:
            print("MFRC522 - No card detected or data read failed.")

        # Try reading with the PN532-based reader
        uid_pn, data_pn = pn532_reader.read_pn532_data()
        if uid_pn is not None:
            print(f"PN532 - UID: {uid_pn} ")
            print(data_pn)
            
            
            
            #success = pn532_reader.write_raw_data_to_tag(test_data)
            success=0;
            if success:
                 print("Raw data written successfully.")
            else:
                 print("Failed to write raw data to tag.")

            # Use the extraction function to filter out and show the relevant ID.
            extracted_id = pn532_reader.extract_id_from_raw(data_pn)
            if extracted_id:
                print(f"PN532 - Extracted ID: {extracted_id}")
            else:
                print("PN532 - No valid ID found in the data.")
        else:
            print("PN532 - No card detected or data read failed.")

        attempt += 1
        if attempt < max_attempts:
            print("Pausing for 5 seconds before next attempt...\n")
            time.sleep(5)
    
    print("Reached maximum number of attempts. Exiting.")

if __name__ == '__main__':
    main()
