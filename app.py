from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import uid_generator_pb2
from GetPlayerPersonalShow_pb2 import GetPlayerPersonalShow
from AccountPersonalShow_pb2 import AccountPersonalShowInfo
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

def decode_hex_player(hex_string):
    byte_data = binascii.unhexlify(hex_string.replace(' ', ''))
    users = GetPlayerPersonalShow()
    users.ParseFromString(byte_data)
    return users

def decode_hex_account(hex_string):
    byte_data = binascii.unhexlify(hex_string.replace(' ', ''))
    account = AccountPersonalShowInfo()
    account.ParseFromString(byte_data)
    return account

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

@app.route('/player-info', methods=['GET'])
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

    # Initialize result dictionary
    result = {
        'player_data': {},
        'account_data': {},
        'craftland_data': {},
        'credit': '@Ujjaiwal'
    }

    try:
        # Get Player Personal Show data
        player_response = requests.post(f"{api}/GetPlayerPersonalShow", headers=headers, data=bytes.fromhex(encrypted_hex))
        player_response.raise_for_status()
        
        # Get Account Personal Show data
        account_response = requests.post(f"{api}/AccountPersonalShow", headers=headers, data=bytes.fromhex(encrypted_hex))
        account_response.raise_for_status()
        
        # Get Craftland Map Info (if needed)
        map_response = requests.post(f"{api}/GetMapInfo", headers=headers, data=bytes.fromhex(encrypted_hex))
        if map_response.status_code == 200:
            map_hex = map_response.content.hex()
            map_info = decode_hex_account(map_hex)
            if map_info.HasField("MapCode"):
                result['craftland_data'] = {
                    'map_code': map_info.MapCode,
                    'map_title': map_info.MapTitle,
                    'description': map_info.description
                }
        
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to contact game server: {str(e)}"}), 502

    # Process Player Personal Show data
    player_hex = player_response.content.hex()
    try:
        player_data = decode_hex_player(player_hex)
        
        # Process player data (same as before)
        if player_data.players:
            result['player_data']['players'] = []
            for p in player_data.players:
                player_info = {
                    'user_id': p.user_id,
                    'account_status': p.account_status,
                    'username': p.username,
                    # Add all other player fields...
                }
                # Add nested objects as before
                result['player_data']['players'].append(player_info)
        
        # Add other player data sections (clans, titles, etc.)
        
    except Exception as e:
        return jsonify({"error": f"Failed to parse Player Protobuf: {str(e)}"}), 500

    # Process Account Personal Show data
    account_hex = account_response.content.hex()
    try:
        account_data = decode_hex_account(account_hex)
        
        if account_data.HasField("basic_info"):
            basic = account_data.basic_info
            result['account_data']['basic_info'] = {
                'account_id': basic.account_id,
                'nickname': basic.nickname,
                'level': basic.level,
                'rank': basic.rank,
                # Add all other basic info fields...
            }
            
            # Add account preferences if available
            if basic.HasField("account_prefers"):
                result['account_data']['preferences'] = {
                    'hide_my_lobby': basic.account_prefers.hide_my_lobby,
                    # Add other preference fields
                }
        
        # Process profile info
        if account_data.HasField("profile_info"):
            profile = account_data.profile_info
            result['account_data']['profile'] = {
                'avatar_id': profile.avatar_id,
                'skin_color': profile.skin_color,
                # Add other profile fields
            }
        
        # Process other account sections (clan info, pet info, etc.)
        
    except Exception as e:
        return jsonify({"error": f"Failed to parse Account Protobuf: {str(e)}"}), 500

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)