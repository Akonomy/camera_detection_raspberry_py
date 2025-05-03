import sys
import os

# Adaugă directorul "FINAL" în sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from SOURCES.TRASEU import find_tag
from SOURCES.TAG_RFID import  mfrc_reader

find_tag.load_data()

def request_cross():
    directions=None
    cross=None


    # Try reading with the MFRC522-based reader
    uid_mf, data_mf = mfrc_reader.read_mifare_data()
    if uid_mf is not None:
        print(f"MFRC522 - UID: {uid_mf}, Data: {data_mf}")
    else:
        return cross, directions
        

    if data_mf is not None:

        if "Z" in data_mf:
            data = data_mf.replace('[', '').replace(']', '')
            return data, "ZONA"

        tag_dictionar = next((t for t in find_tag._export_data.get("tags", []) if t.get("custom_id") == data_mf), None)
        if tag_dictionar is not None:
            cross = find_tag.getCross(tag_dictionar)
            directions = find_tag.getDirections(tag_dictionar)
            
        else:
            cross=None
            

    return cross ,directions



if __name__ == "__main__":
    cross,directions=request_cross()


    print (f"TAGUL  se afla la intersectia {cross} ");
    
    print(directions);




    
