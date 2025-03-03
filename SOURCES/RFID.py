import time
from TAG_RFID import mfrc_reader, TAG_PN532 as pn532_reader

def main():
    max_attempts = 10
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
        
        uid, raw_data = pn532_reader.read_pn532_table()
        if uid is None:
            print("No tag detected.")
        else:
            print(f"UID: {uid}")
            print("Raw data table:")
            pn532_reader.process_raw_data_table(raw_data, start_block=0)
        
            type_of_tag=pn532_reader.get_tag_type(raw_data)
            
            print(f"TYPE: { type_of_tag } \n")
            
            print(f"RAW DATA:\n {raw_data} \nEND OF RAW DATA  ")     
            
            
            
            #success = pn532_reader.write_raw_data_to_tag(test_data)
            success=0;
            if success:
                 print("Raw data written successfully.")
            else:
                 print("DATA CAPTURED \n")



        attempt += 1
        if attempt < max_attempts:
            print("...\n")
            time.sleep(3)
    
    print("Reached maximum number of attempts. Exiting.")

if __name__ == '__main__':
    main()
