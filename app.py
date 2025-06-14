from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import random
import uid_generator_pb2
from AccountPersonalShow_pb2 import AccountPersonalShowInfo  # Changed from a_pb2
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
    user_info = AccountPersonalShowInfo()  # Changed from CSGetPlayerPersonalShowRes
    user_info.ParseFromString(byte_data)
    return user_info

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

def process_account_info(account_info):
    """Helper function to process AccountInfoBasic into a dictionary"""
    if not account_info:
        return None
        
    return {
        'account_id': account_info.account_id,
        'nickname': account_info.nickname,
        'level': account_info.level,
        'exp': account_info.exp,
        'rank': account_info.rank,
        'ranking_points': account_info.ranking_points,
        'max_rank': account_info.max_rank,
        'max_ranking_points': account_info.max_ranking_points,
        'last_login_at': account_info.last_login_at,
        'clan_name': account_info.clan_name,
        'clan_id': account_info.clan_id,
        'title': account_info.title,
        'has_elite_pass': account_info.has_elite_pass,
        'is_deleted': account_info.is_deleted,
        'show_rank': account_info.show_rank,
        'show_br_rank': account_info.show_br_rank,
        'show_cs_rank': account_info.show_cs_rank,
        'weapon_skin_shows': list(account_info.weapon_skin_shows),
        'account_prefers': {
            'hide_my_lobby': account_info.account_prefers.hide_my_lobby,
            'hide_personal_info': account_info.account_prefers.hide_personal_info,
            'disable_friend_spectate': account_info.account_prefers.disable_friend_spectate,
            'hide_occupation': account_info.account_prefers.hide_occupation
        } if account_info.HasField("account_prefers") else None,
        'external_icon_info': {
            'external_icon': account_info.external_icon_info.external_icon,
            'status': account_info.external_icon_info.status,
            'show_type': account_info.external_icon_info.show_type
        } if account_info.HasField("external_icon_info") else None
    }

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
        user_info = decode_hex(hex_response)
    except Exception as e:
        return jsonify({"error": f"Failed to parse Protobuf: {str(e)}"}), 500

    result = {}

    # Process basic account info
    if user_info.HasField("basic_info"):
        result['basic_info'] = process_account_info(user_info.basic_info)

    # Process profile info
    if user_info.HasField("profile_info"):
        profile = user_info.profile_info
        result['profile_info'] = {
            'avatar_id': profile.avatar_id if profile.HasField("avatar_id") else None,
            'skin_color': profile.skin_color if profile.HasField("skin_color") else None,
            'clothes': list(profile.clothes),
            'equiped_skills': list(profile.equiped_skills),
            'is_selected': profile.is_selected if profile.HasField("is_selected") else None,
            'pve_primary_weapon': profile.pve_primary_weapon if profile.HasField("pve_primary_weapon") else None
        }

    # Process clan info
    if user_info.HasField("clan_basic_info"):
        clan = user_info.clan_basic_info
        result['clan_info'] = {
            'clan_id': clan.clan_id if clan.HasField("clan_id") else None,
            'clan_name': clan.clan_name if clan.HasField("clan_name") else None,
            'clan_level': clan.clan_level if clan.HasField("clan_level") else None,
            'member_num': clan.member_num if clan.HasField("member_num") else None
        }

    # Process social info
    if user_info.HasField("social_info"):
        social = user_info.social_info
        result['social_info'] = {
            'account_id': social.account_id,
            'gender': social.gender,
            'language': social.language,
            'signature': social.signature,
            'battle_tags': [tag for tag in social.battle_tag],
            'social_tags': [tag for tag in social.social_tag],
            'mode_prefer': social.mode_prefer
        }

    # Process pet info
    if user_info.HasField("pet_info"):
        pet = user_info.pet_info
        result['pet_info'] = {
            'id': pet.id if pet.HasField("id") else None,
            'name': pet.name if pet.HasField("name") else None,
            'level': pet.level if pet.HasField("level") else None,
            'is_selected': pet.is_selected if pet.HasField("is_selected") else None,
            'skills': [{
                'skill_id': skill.skill_id if skill.HasField("skill_id") else None,
                'skill_level': skill.skill_level if skill.HasField("skill_level") else None
            } for skill in pet.skills]
        }

    # Add CraftlandMapService endpoint if needed
    result['craftland_map_service'] = {
        'endpoint': '/CraftlandMapService/GetMapInfo',
        'description': 'Use this endpoint to get map information'
    }

    result['credit'] = '@Ujjaiwal'
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)