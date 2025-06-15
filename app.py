from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import random
import uid_generator_pb2
from AccountPersonalShow_pb2 import CraftlandInfo, MapInfo
from secret import key, iv

app = Flask(__name__)

def hex_to_bytes(hex_string):
    return bytes.fromhex(hex_string)

def create_protobuf(akiru_, aditya):
    message = uid_generator_pb2.uid_generator()
    message.akiru_ = akiru_
    message.aditya = aditya
    return message.SerializeToString()

def protobuf_to_hex(protobuf_data):
    return binascii.hexlify(protobuf_data).decode()

def decode_hex(hex_string):
    byte_data = binascii.unhexlify(hex_string.replace(' ', ''))
    users = CSGetPlayerPersonalShowRes()
    users.ParseFromString(byte_data)
    return users

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

@app.route('/map-data', methods=['GET'])
def main():
    uid = request.args.get('uid')
    region = request.args.get('region')

    if not uid or not region:
        return jsonify({"error": "Missing 'uid' or 'region' query parameter"}), 400

    try:
        saturn_ = int(uid)
    except ValueError:
        return jsonify({"error": "Invalid UID"}), 400

    jwt_info = get_jwt_token(region)
    if not jwt_info or 'token' not in jwt_info:
        return jsonify({"error": "Failed to fetch JWT token"}), 500

    api = jwt_info['serverUrl']
    token = jwt_info['token']

    protobuf_data = create_protobuf(saturn_, 1)
    hex_data = protobuf_to_hex(protobuf_data)
    encrypted_hex = encrypt_aes(hex_data, key, iv)

    headers = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
        'Connection': 'Keep-Alive',
        'Expect': '100-continue',
        'Authorization': f'Bearer {token}',
        'X-Unity-Version': '2018.4.11f1',
        'X-GA': 'v1 1',
        'ReleaseVersion': 'OB49',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    try:
        response = requests.post(f"{api}/GetPlayerPersonalShow", headers=headers, data=bytes.fromhex(encrypted_hex))
        response.raise_for_status()
    except requests.RequestException:
        return jsonify({"error": "Failed to contact game server"}), 502

    hex_response = response.content.hex()

    try:
        users = decode_hex(hex_response)
    except Exception as e:
        return jsonify({"error": f"Failed to parse Protobuf: {str(e)}"}), 500

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