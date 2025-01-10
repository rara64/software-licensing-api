import random
import string
import base64
import json
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from config import config

"""
Get a new unique license key
"""
def get_license():
    a = ''.join(random.choices(string.ascii_uppercase, k=5))
    b = ''.join(random.choices(string.ascii_uppercase, k=5))

    c = ''.join(random.choices(string.digits, k=5))
    d = ''.join(random.choices(string.digits, k=5))

    return f"{a}-{b}-{c}-{d}"

"""
Generate hardware identifier based on unique information about the machine on which the machine runs on
"""
def get_hardware_id(hardware_spec1, hardware_spec2, hardware_spec3, hardware_spec4, hardware_spec5):
    hardware_specs = f"{hardware_spec1}|{hardware_spec2}|{hardware_spec3}|{hardware_spec4}|{hardware_spec5}"
    return base64.b64encode(hardware_specs.encode("utf-8")).decode("utf-8")

"""
Generate and sign the final license used by the software
"""
def get_signed_license(license_key, hardware_id):
    private_key = serialization.load_pem_private_key(
        config.LICENSE_PRIVATE_KEY.encode("utf-8"),
        password=None
    )

    license_data = hardware_id + license_key

    license_file_signed = private_key.sign(
        license_data.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=32
        ),
        hashes.SHA256()
    )

    license_signature = base64.b64encode(license_file_signed).decode("utf-8")

    return license_signature
