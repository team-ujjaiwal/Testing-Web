from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
from AccountPersonalShow_pb2 import CraftlandInfo, MapInfo  # Using the protobuf definitions you provided
from secret import key, iv

app = Flask(__name__)

def hex_to_bytes(hex_string):
    return bytes.fromhex(hex_string)

def encrypt_aes(hex_data, key, iv):
    key = key.encode()[:16]
    iv = iv.encode()[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(bytes.fromhex(hex_data), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return binascii.hexlify(encrypted_data).decode()

def get_credentials(region):
    region = region.upper()
    if region == "IND":
        return "3942040791", "EDD92B8948F4453F544C9432DFB4996D02B4054379A0EE083D8459737C50800B"
    elif region in ["NA", "BR", "SAC", "US"]:
        return "uid", "password"
    else:
        return "uid", "password"

def get_jwt_token(region):
    uid, password = get_credentials(region)
    jwt_url = f"https://jwt-aditya.vercel.app/token?uid={uid}&password={password}"
    response = requests.get(jwt_url)
    if response.status_code != 200:
        return None
    return response.json()

@app.route('/map-info', methods=['GET'])
def get_map_info():
    # Create sample CraftlandMap and MapInfo data
    craftland_info = CraftlandInfo(
        CraftlandName="Sample Craftland",
        CraftlandCode="CL123",
        CraftlandTitle="Adventure Zone",
        CraftlandDescription="A sample craftland description"
    )

    map_info = MapInfo(
        MapCode="MAP456",
        MapTitle="Sample Map",
        description="This is a sample map description"
    )

    # Create the response with only CraftlandMap and MapInfo
    result = {
        "craftland_info": {
            "craftland_name": craftland_info.CraftlandName,
            "craftland_code": craftland_info.CraftlandCode,
            "craftland_title": craftland_info.CraftlandTitle,
            "craftland_description": craftland_info.CraftlandDescription
        },
        "map_info": {
            "map_code": map_info.MapCode,
            "map_title": map_info.MapTitle,
            "description": map_info.description
        }
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)