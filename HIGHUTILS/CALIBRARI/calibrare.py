# FILE: SOURCES/UTILS/calibration.py

import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from DATABASE import db
from SOURCES.UTILS.send_code_to_stm32 import send_encoded_directions
from SOURCES.USART_COM.serial_module import process_command
from SOURCES.TAG_RFID.mfrc_reader import read_mifare_data


def _read_response(timeout_sec=10):
    start = time.time()
    while time.time() - start < timeout_sec:
        data = process_command(30, 0, 0, [0])
        if data:
            return data
        time.sleep(0.5)
    return None

def _log_code_as_hex(code):
    print(f"STM32 HEX code: {code:#04x}")

def _read_tag_once():
    previous = None
    while True:
        tag_data = read_mifare_data()
        if tag_data and tag_data[1] and tag_data != previous:
            return tag_data
        time.sleep(0.2)

def calibrate_tag_position(directions=[4, 5], mode=1, response_timeout=120):
    print("🔄 Starting calibration...")

    result = send_encoded_directions(directions, mode=mode)
    if not result['success']:
        print("❌ STM32 failed to accept directions.")
        return {"success": False, "error": result['message']}

    print("📡 Waiting for tag scan...")
    tag = _read_tag_once()
    if not tag:
        print("❌ No tag read.")
        return {"success": False, "error": "No tag read"}

    print("📬 Waiting for STM32 confirmation...")
    response = _read_response(timeout_sec=response_timeout)
    if not response:
        print("❌ No response from STM32.")
        return {"success": False, "error": "No STM32 response"}

    code = response[0]
    _log_code_as_hex(code)

    if code == 0xFA:
        db.SET_VAR("tag", tag[1])
        db.SET_VAR("lastTimeUpdated", time.time())
        db.SET_FLAG("isTagAvailable", True)
        print("✅ Tag calibrated and saved.")
        return {"success": True, "tag": tag[1]}
    else:
        db.SET_FLAG("isDanger", hex(code))
        print("⚠️ Calibration failed with code:", hex(code))
        return {"success": False, "error": f"STM32 code: {hex(code)}"}
