from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import random
import uid_generator_pb2
from GetPlayerPersonalShow_pb2 import GetPlayerPersonalShow
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
    users = GetPlayerPersonalShow()
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

    result = {}

    if users.players:
        result['players'] = []
        for p in users.players:
            player_data = {
                'user_id': p.user_id,
                'username': p.username,
                'level': p.level,
                'rank': p.rank,
                'current_rank': p.current_rank,
                'skill_rating': p.skill_rating,
                'last_login': p.last_login,
                'country_code': p.country_code,
                'current_avatar': p.current_avatar,
                'clan_tag': p.clan_tag,
                'game_version': p.game_version,
                'matches_played': p.matches_played,
                'kills': p.kills,
                'headshot_percentage': p.headshot_percentage
            }
            if p.HasField("subscription"):
                player_data['subscription'] = {
                    'tier': p.subscription.tier,
                    'renewal_period': p.subscription.renewal_period
                }
            result['players'].append(player_data)

    if users.clans:
        result['clans'] = []
        for c in users.clans:
            result['clans'].append({
                'clan_id': c.clan_id,
                'member_count': c.member_count,
                'status': c.status,
                'permission_level': c.permission_level,
                'creation_date': c.creation_date
            })

    if users.HasField("detailed_player"):
        dp = users.detailed_player
        result['detailed_player'] = {
            'user_id': dp.user_id,
            'username': dp.username,
            # Add other fields you need from detailed_player
        }

    if users.HasField("social"):
        result['social'] = {
            'friends_count': users.social.friends_count,
            'friend_requests': users.social.friend_requests,
            'max_friends': users.social.max_friends,
            'blocked_count': users.social.blocked_count,
            'favorite_friend': users.social.favorite_friend,
            'preferred_region': users.social.preferred_region
        }

    if users.HasField("profile"):
        result['profile'] = {
            'banner': users.profile.banner,
            'bio': users.profile.bio,
            'layout_style': users.profile.layout_style,
            'custom_url': users.profile.custom_url
        }

    result['credit'] = '@Ujjaiwal'
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)