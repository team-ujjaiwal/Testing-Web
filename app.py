from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import random
import uid_generator_pb2
from AccountPersonalShow_pb2 import AccountPersonalShowInfo
from prime_level_pb2 import Users, prime, info
from secret import key, iv

app = Flask(__name__)

def hex_to_unwieldy(hex_string):
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
    users = AccountPersonalShowInfo()
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
    jwt_url = f"https://fd-jwt-ob50.vercel.app/token?uid={uid}&password={password}"
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
        'ReleaseVersion': 'OB50',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    try:
        response = requests.post(f"{api}/GetPlayerPersonalShow", headers=headers, data=bytes.fromhex(encrypted_hex))
        response.raise_for_status()
    except requests.RequestException:
        return jsonify({"error": "Failed to contact game server"}), 502

    hex_response = response.content.hex()

    try:
        account_info = decode_hex(hex_response)
    except Exception as e:
        return jsonify({"error": f"Failed to parse Protobuf: {str(e)}"}), 500

    # Extract username and prime_level dynamically
    username = "Unknown"
    prime_level_value = 0  # Default value if prime_level is not available

    if account_info.HasField("basic_info"):
        username = account_info.basic_info.nickname  # Fetch username from basic_info.nickname
        # Derive prime_level (example logic: based on has_elite_pass)
        if account_info.basic_info.has_elite_pass:
            prime_level_value = 8  # Example: Set to 8 if elite pass is present
        # If prime_level is available in another field (e.g., diamond_cost_res or another Protobuf field),
        # adjust the logic here. For example:
        # if account_info.HasField("diamond_cost_res"):
        #     prime_level_value = account_info.diamond_cost_res.some_field_indicating_prime_level

    # Create prime level info dynamically
    prime_info = prime(prime_level=prime_level_value)
    user_info = info(username=username, prime_level=prime_info)
    users_data = Users(basicinfo=[user_info])

    result = {}

    # Basic Info
    if account_info.HasField("basic_info"):
        basic_info = account_info.basic_info
        result["basicInfo"] = {
            "accountId": str(basic_info.account_id),
            "accountType": basic_info.account_type,
            "nickname": basic_info.nickname,
            "region": basic_info.region,
            "level": basic_info.level,
            "exp": basic_info.exp,
            "bannerId": basic_info.banner_id,
            "headPic": basic_info.head_pic,
            "rank": basic_info.rank,
            "rankingPoints": basic_info.ranking_points,
            "role": basic_info.role,
            "hasElitePass": basic_info.has_elite_pass,
            "badgeCnt": basic_info.badge_cnt,
            "badgeId": basic_info.badge_id,
            "seasonId": basic_info.season_id,
            "liked": basic_info.liked,
            "lastLoginAt": str(basic_info.last_login_at),
            "csRank": basic_info.cs_rank,
            "csRankingPoints": basic_info.cs_ranking_points,
            "weaponSkinShows": list(basic_info.weapon_skin_shows),
            "maxRank": basic_info.max_rank,
            "csMaxRank": basic_info.cs_max_rank,
            "accountPrefers": {},
            "createAt": str(basic_info.create_at),
            "title": basic_info.title,
            "externalIconInfo": {
                "status": "ExternalIconStatus_NOT_IN_USE",
                "showType": "ExternalIconShowType_FRIEND"
            },
            "releaseVersion": basic_info.release_version,
            "showBrRank": basic_info.show_br_rank,
            "showCsRank": basic_info.show_cs_rank,
            "socialHighLightsWithBasicInfo": {}
        }

    # Profile Info
    if account_info.HasField("profile_info"):
        profile_info = account_info.profile_info
        result["profileInfo"] = {
            "avatarId": profile_info.avatar_id,
            "skinColor": profile_info.skin_color,
            "clothes": list(profile_info.clothes),
            "equipedSkills": list(profile_info.equiped_skills),
            "isSelected": profile_info.is_selected,
            "isSelectedAwaken": profile_info.is_selected_awaken
        }

    # Clan Basic Info
    if account_info.HasField("clan_basic_info"):
        clan_info = account_info.clan_basic_info
        result["clanBasicInfo"] = {
            "clanId": str(clan_info.clan_id),
            "clanName": clan_info.clan_name,
            "captainId": str(clan_info.captain_id),
            "clanLevel": clan_info.clan_level,
            "capacity": clan_info.capacity,
            "memberNum": clan_info.member_num
        }

    # Captain Basic Info
    if account_info.HasField("captain_basic_info"):
        captain_info = account_info.captain_basic_info
        result["captainBasicInfo"] = {
            "accountId": str(captain_info.account_id),
            "accountType": captain_info.account_type,
            "nickname": captain_info.nickname,
            "region": captain_info.region,
            "level": captain_info.level,
            "exp": captain_info.exp,
            "bannerId": captain_info.banner_id,
            "headPic": captain_info.head_pic,
            "rank": captain_info.rank,
            "rankingPoints": captain_info.ranking_points,
            "role": captain_info.role,
            "hasElitePass": captain_info.has_elite_pass,
            "badgeCnt": captain_info.badge_cnt,
            "badgeId": captain_info.badge_id,
            "seasonId": captain_info.season_id,
            "liked": captain_info.liked,
            "lastLoginAt": str(captain_info.last_login_at),
            "csRank": captain_info.cs_rank,
            "csRankingPoints": captain_info.cs_ranking_points,
            "weaponSkinShows": list(captain_info.weapon_skin_shows),
            "maxRank": captain_info.max_rank,
            "csMaxRank": captain_info.cs_max_rank,
            "accountPrefers": {},
            "createAt": str(captain_info.create_at),
            "title": captain_info.title,
            "externalIconInfo": {
                "status": "ExternalIconStatus_NOT_IN_USE",
                "showType": "ExternalIconShowType_FRIEND"
            },
            "releaseVersion": captain_info.release_version,
            "showBrRank": captain_info.show_br_rank,
            "showCsRank": captain_info.show_cs_rank,
            "socialHighLightsWithBasicInfo": {}
        }

    # Pet Info
    if account_info.HasField("pet_info"):
        pet_info = account_info.pet_info
        result["petInfo"] = {
            "id": pet_info.id,
            "name": pet_info.name,
            "level": pet_info.level,
            "exp": pet_info.exp,
            "isSelected": pet_info.is_selected,
            "skinId": pet_info.skin_id,
            "selectedSkillId": pet_info.selected_skill_id
        }

    # Social Info
    if account_info.HasField("social_info"):
        social_info = account_info.social_info
        result["socialInfo"] = {
            "accountId": str(social_info.account_id),
            "language": "Language_EN",  # Map from social_info.language
            "modePrefer": "ModePrefer_BR",  # Map from social_info.mode_prefer
            "signature": social_info.signature,
            "rankShow": "RankShow_CS"  # Map from social_info.rank_show
        }

    # Diamond Cost Res
    if account_info.HasField("diamond_cost_res"):
        diamond_cost = account_info.diamond_cost_res
        result["diamondCostRes"] = {
            "diamondCost": diamond_cost.diamond_cost,
            "primeLevel": prime_level_value  # Use dynamically fetched prime_level
        }

    # Credit Score Info
    if account_info.HasField("credit_score_info"):
        credit_info = account_info.credit_score_info
        result["creditScoreInfo"] = {
            "creditScore": credit_info.credit_score,
            "rewardState": "REWARD_STATE_UNCLAIMED",  # Map from credit_info.reward_state
            "periodicSummaryEndTime": str(credit_info.periodic_summary_end_time)
        }

    result['credit'] = '@Ujjaiwal'
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)