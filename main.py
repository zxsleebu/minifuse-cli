import ctypes
import sys
import struct
import os

DLL_PATH = r"C:\Program Files\Arturia\MiniFuseAudioDriver\x64\arturiaminifuseusbaudioapi_x64.dll"

SELECTOR_INSTRUMENT    = 0
SELECTOR_PHANTOM_POWER = 4
SELECTOR_DIRECT_MONO   = 5

def set_minifuse_param(target_selector, turn_on, channel=0):
    if not os.path.exists(DLL_PATH):
        print(f"[-] Error: DLL not found at {DLL_PATH}")
        return

    try:
        lib = ctypes.CDLL(DLL_PATH)
    except OSError as e:
        print(f"[-] Error loading DLL: {e}")
        return

    print("[+] Arturia API Loaded.")

    if hasattr(lib, 'TUSBAUDIO_EnumerateDevices'):
        lib.TUSBAUDIO_EnumerateDevices()

    lib.TUSBAUDIO_OpenDeviceByIndex.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    lib.TUSBAUDIO_OpenDeviceByIndex.restype = ctypes.c_int
    
    handle = ctypes.c_void_p()
    res = lib.TUSBAUDIO_OpenDeviceByIndex(0, ctypes.byref(handle))
    
    if res != 0 or not handle:
        print(f"[-] Failed to open device. Error Code: {res}")
        return

    # Based on tusbaudioapi.h
    # https://github.com/mattgonzalez/ProductionTest/blob/5e85e334bc83d0486a2a22cf67c52ffc23ad0af4/Source/win32/usb/win/tusbaudioapi.h#L570
    # https://github.com/lilltroll77/DCF/blob/e390673629f4d2548e638d4760e328cd2112f6af/tusbaudioapi.h#L1389
    # 
    # TUsbAudioStatus TUSBAUDIO_AudioControlRequestSet(
    #    TUsbAudioHandle deviceHandle,
    #    unsigned char entityID,
    #    unsigned char request,
    #    unsigned char controlSelector,
    #    unsigned char channelOrMixerControl,
    #    const void* paramBlock,
    #    unsigned int paramBlockLength,
    #    unsigned int* bytesTransferred,
    #    unsigned int timeoutMillisecs
    # );
    
    send_req = lib.TUSBAUDIO_AudioControlRequestSet
    send_req.argtypes = [
        ctypes.c_void_p,        # Handle
        ctypes.c_ubyte,         # EntityID
        ctypes.c_ubyte,         # Request
        ctypes.c_ubyte,         # ControlSelector
        ctypes.c_ubyte,         # Channel
        ctypes.c_void_p,        # Buffer Pointer
        ctypes.c_uint,          # Buffer Length
        ctypes.c_void_p,        # Bytes Transferred (Optional Pointer)
        ctypes.c_uint           # Timeout
    ]
    send_req.restype = ctypes.c_int

    # https://github.com/mattgonzalez/ProductionTest/blob/5e85e334bc83d0486a2a22cf67c52ffc23ad0af4/Source/win32/usb/win/ehw.cpp#L1690

    val = 1 if turn_on else 0
    data = struct.pack('<H', val)
    buf = ctypes.create_string_buffer(data)

    target_name = "Unknown"
    if target_selector == SELECTOR_PHANTOM_POWER:
        target_name = "Phantom Power"
    elif target_selector == SELECTOR_DIRECT_MONO:
        target_name = "Direct Mono"
    elif target_selector == SELECTOR_INSTRUMENT:
        target_name = f"Instrument (Channel {channel + 1})"

    print(f"[*] Setting {target_name} to {'ON' if turn_on else 'OFF'}...")
    
    res = send_req(handle, 0, 34, target_selector, channel, buf, 2, None, 1000)

    if res == 0:
        print(f"[+] SUCCESS! {target_name} toggled.")
    else:
        print(f"[-] Command failed with Error Code: {res}")

    if hasattr(lib, 'TUSBAUDIO_CloseDevice'):
        lib.TUSBAUDIO_CloseDevice(handle)

if __name__ == "__main__":
    args = [a.lower() for a in sys.argv]
    
    if len(args) < 2:
        print("Usage: python main.py [power|mono|inst] [on/off] (optional: channel number for inst [1-2])")
        sys.exit(1)

    selector = SELECTOR_PHANTOM_POWER
    channel = 0
    
    if "inst" in args or "instrument" in args:
        selector = SELECTOR_INSTRUMENT
        if "2" in args:
            channel = 1
    elif "mono" in args or "direct" in args:
        selector = SELECTOR_DIRECT_MONO
    
    state = True
    if "off" in args:
        state = False

    set_minifuse_param(selector, state, channel)
