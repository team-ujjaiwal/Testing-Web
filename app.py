from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
from AccountPersonalShow_pb2 import AccountPersonalShowInfo
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

@app.route('/player-map-info', methods=['GET'])
def get_player_map_info():
    uid = request.args.get('uid')
    region = request.args.get('region')

    if not uid or not region:
        return jsonify({"error": "Missing 'uid' or 'region' parameter"}), 400

    jwt_info = get_jwt_token(region)
    if not jwt_info or 'token' not in jwt_info:
        return jsonify({"error": "Failed to fetch JWT token"}), 500

    api = jwt_info['serverUrl']
    token = jwt_info['token']

    # Create a simple request protobuf with the UID
    request_data = f'08{int(uid):02x}'.encode()  # Field 1, value = UID

    # Encrypt the request
    encrypted_hex = encrypt_aes(request_data.hex(), key, iv)

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Unity-Version': '2018.4.11f1'
    }

    try:
        response = requests.post(f"{api}/GetPlayerPersonalShow", 
                               headers=headers, 
                               data=bytes.fromhex(encrypted_hex))
        response.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to contact game server: {str(e)}"}), 502

    # Parse the response
    try:
        # Decrypt the response
        cipher = AES.new(key.encode()[:16], AES.MODE_CBC, iv.encode()[:16])
        decrypted_data = cipher.decrypt(response.content)
        
        # Parse the protobuf
        account_info = AccountPersonalShowInfo()
        account_info.ParseFromString(decrypted_data)
        
        # Prepare response data - only Craftland and Map info
        result = {}
        
        # Check if we have basic info which contains the map data
        if account_info.HasField('basic_info'):
            basic_info = account_info.basic_info
            
            # Check for Craftland info if available
            if hasattr(basic_info, 'craftland_info'):
                craftland = basic_info.craftland_info
                result['craftland_info'] = {
                    'craftland_name': craftland.CraftlandName,
                    'craftland_code': craftland.CraftlandCode,
                    'craftland_title': craftland.CraftlandTitle,
                    'craftland_description': craftland.CraftlandDescription
                }
            
            # Check for Map info if available
            if hasattr(basic_info, 'map_info'):
                map_info = basic_info.map_info
                result['map_info'] = {
                    'map_code': map_info.MapCode,
                    'map_title': map_info.MapTitle,
                    'description': map_info.description
                }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"error": f"Failed to parse response: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)