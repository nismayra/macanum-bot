# ble_advertising.py
from micropython import const
import struct
import bluetooth

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME_LOCAL_COMPLETE = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)
_ADV_TYPE_UUID128_COMPLETE = const(0x07)
_ADV_TYPE_UUID16_MORE = const(0x02)
_ADV_TYPE_APPEARANCE = const(0x19)

_ADV_DATA_APPEARANCE = const(0)

def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += struct.pack("BB", len(value) + 1, adv_type) + value

    _append(
        _ADV_TYPE_FLAGS,
        struct.pack("B", (0x02 if limited_disc else 0x06) + (0x00 if br_edr else 0x04)),
    )

    if name:
        _append(_ADV_TYPE_NAME_LOCAL_COMPLETE, name)

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)

    # See org.bluetooth.characteristic.gap.appearance.xml
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))

    return payload

def decode_field(payload, adv_type):
    i = 0
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            return payload[i + 2 : i + payload[i] + 1]
        i += 1 + payload[i]
    return None

def decode_name(payload):
    n = decode_field(payload, _ADV_TYPE_NAME_LOCAL_COMPLETE)
    return str(n, "utf-8") if n else ""

def decode_services(payload):
    services = []
    for u in decode_field(payload, _ADV_TYPE_UUID16_COMPLETE) or []:
        services.append(bluetooth.UUID(struct.unpack("<h", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID128_COMPLETE) or []:
        services.append(bluetooth.UUID(u))
    return services
