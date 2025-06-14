from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import uid_generator_pb2
from AccountPersonalShow_pb2 import (
    AccountPersonalShowInfo, 
    MapRequest, 
    MapInfo, 
    CraftlandInfo,
    ExternalIconStatus,
    ExternalIconShowType,
    Gender,
    Language,
    TimeOnline,
    TimeActive,
    PlayerBattleTagID,
    SocialTag,
    ModePrefer,
    RankShow,
    RewardState
)
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
    user_info = AccountPersonalShowInfo()
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
    """Process AccountInfoBasic into the desired dictionary format"""
    if not account_info:
        return None
        
    result = {
        "accountId": str(account_info.account_id),
        "accountType": account_info.account_type,
        "nickname": account_info.nickname,
        "region": account_info.region,
        "level": account_info.level,
        "exp": account_info.exp,
        "bannerId": account_info.banner_id,
        "headPic": account_info.head_pic,
        "rank": account_info.rank,
        "rankingPoints": account_info.ranking_points,
        "role": account_info.role,
        "hasElitePass": account_info.has_elite_pass,
        "badgeCnt": account_info.badge_cnt,
        "badgeId": account_info.badge_id,
        "seasonId": account_info.season_id,
        "liked": account_info.liked,
        "lastLoginAt": str(account_info.last_login_at),
        "csRank": account_info.cs_rank,
        "csRankingPoints": account_info.cs_ranking_points,
        "weaponSkinShows": list(account_info.weapon_skin_shows),
        "maxRank": account_info.max_rank,
        "csMaxRank": account_info.cs_max_rank,
        "accountPrefers": {},
        "createAt": str(account_info.create_at),
        "title": account_info.title,
        "releaseVersion": account_info.release_version,
        "showBrRank": account_info.show_br_rank,
        "showCsRank": account_info.show_cs_rank,
        "socialHighLightsWithBasicInfo": {}
    }
    
    # Add external icon info if available
    if account_info.HasField("external_icon_info"):
        result["externalIconInfo"] = {
            "status": ExternalIconStatus.Name(account_info.external_icon_info.status),
            "showType": ExternalIconShowType.Name(account_info.external_icon_info.show_type)
        }
    
    # Add account preferences if available
    if account_info.HasField("account_prefers"):
        result["accountPrefers"] = {
            "hideMyLobby": account_info.account_prefers.hide_my_lobby,
            "pregameShowChoices": list(account_info.account_prefers.pregame_show_choices),
            "brPregameShowChoices": list(account_info.account_prefers.br_pregame_show_choices),
            "hidePersonalInfo": account_info.account_prefers.hide_personal_info,
            "disableFriendSpectate": account_info.account_prefers.disable_friend_spectate,
            "hideOccupation": account_info.account_prefers.hide_occupation
        }
    
    # Add clan info if available
    if account_info.clan_id:
        result["clanId"] = str(account_info.clan_id)
    if account_info.clan_name:
        result["clanName"] = account_info.clan_name
    
    # Add veteran info if available
    if account_info.HasField("veteran_leave_days_tag"):
        result["veteranLeaveDays"] = account_info.veteran_leave_days_tag
    
    return result

def process_profile_info(profile_info):
    """Process AvatarProfile into the desired dictionary format"""
    if not profile_info:
        return None
        
    result = {
        "avatarId": profile_info.avatar_id if profile_info.HasField("avatar_id") else None,
        "skinColor": profile_info.skin_color if profile_info.HasField("skin_color") else None,
        "clothes": list(profile_info.clothes),
        "equipedSkills": list(profile_info.equiped_skills),
        "isSelected": profile_info.is_selected if profile_info.HasField("is_selected") else None,
        "isSelectedAwaken": profile_info.is_selected_awaken if profile_info.HasField("is_selected_awaken") else None,
        "clothesTailorEffects": list(profile_info.clothes_tailor_effects)
    }
    
    # Add optional fields
    if profile_info.HasField("pve_primary_weapon"):
        result["pvePrimaryWeapon"] = profile_info.pve_primary_weapon
    if profile_info.HasField("is_marked_star"):
        result["isMarkedStar"] = profile_info.is_marked_star
    if profile_info.HasField("end_time"):
        result["endTime"] = profile_info.end_time
    if profile_info.HasField("unlock_type"):
        result["unlockType"] = profile_info.unlock_type
    if profile_info.HasField("unlock_time"):
        result["unlockTime"] = profile_info.unlock_time
    
    return result

def process_clan_info(clan_info):
    """Process ClanInfoBasic into the desired dictionary format"""
    if not clan_info:
        return None
        
    result = {
        "clanId": str(clan_info.clan_id) if clan_info.HasField("clan_id") else None,
        "clanName": clan_info.clan_name if clan_info.HasField("clan_name") else None,
        "captainId": str(clan_info.captain_id) if clan_info.HasField("captain_id") else None,
        "clanLevel": clan_info.clan_level if clan_info.HasField("clan_level") else None,
        "capacity": clan_info.capacity if clan_info.HasField("capacity") else None,
        "memberNum": clan_info.member_num if clan_info.HasField("member_num") else None
    }
    
    # Add optional fields
    if clan_info.HasField("honor_point"):
        result["honorPoint"] = clan_info.honor_point
    
    return result

def process_pet_info(pet_info):
    """Process PetInfo into the desired dictionary format"""
    if not pet_info:
        return None
        
    result = {
        "id": pet_info.id if pet_info.HasField("id") else None,
        "name": pet_info.name if pet_info.HasField("name") else None,
        "level": pet_info.level if pet_info.HasField("level") else None,
        "exp": pet_info.exp if pet_info.HasField("exp") else None,
        "isSelected": pet_info.is_selected if pet_info.HasField("is_selected") else None,
        "skinId": pet_info.skin_id if pet_info.HasField("skin_id") else None,
        "selectedSkillId": pet_info.selected_skill_id if pet_info.HasField("selected_skill_id") else None,
        "actions": list(pet_info.actions),
        "isMarkedStar": pet_info.is_marked_star if pet_info.HasField("is_marked_star") else None,
        "endTime": pet_info.end_time if pet_info.HasField("end_time") else None
    }
    
    # Add skills if available
    if pet_info.skills:
        result["skills"] = []
        for skill in pet_info.skills:
            skill_data = {
                "skillId": skill.skill_id if skill.HasField("skill_id") else None,
                "skillLevel": skill.skill_level if skill.HasField("skill_level") else None
            }
            if skill.HasField("pet_id"):
                skill_data["petId"] = skill.pet_id
            result["skills"].append(skill_data)
    
    return result

def process_social_info(social_info):
    """Process SocialBasicInfo into the desired dictionary format"""
    if not social_info:
        return None
        
    result = {
        "accountId": str(social_info.account_id),
        "language": Language.Name(social_info.language),
        "modePrefer": ModePrefer.Name(social_info.mode_prefer),
        "signature": social_info.signature,
        "rankShow": RankShow.Name(social_info.rank_show)
    }
    
    # Add optional fields
    if social_info.gender != Gender.Gender_NONE:
        result["gender"] = Gender.Name(social_info.gender)
    if social_info.time_online != TimeOnline.TimeOnline_NONE:
        result["timeOnline"] = TimeOnline.Name(social_info.time_online)
    if social_info.time_active != TimeActive.TimeActive_NONE:
        result["timeActive"] = TimeActive.Name(social_info.time_active)
    
    # Add battle tags and social tags
    if social_info.battle_tag:
        result["battleTags"] = [PlayerBattleTagID.Name(tag) for tag in social_info.battle_tag]
    if social_info.social_tag:
        result["socialTags"] = [SocialTag.Name(tag) for tag in social_info.social_tag]
    
    # Add leaderboard titles if available
    if social_info.HasField("leaderboard_titles"):
        leaderboard = social_info.leaderboard_titles
        result["leaderboardTitles"] = {
            "weaponPowerTitles": [],
            "guildWarTitles": []
        }
        
        for weapon_title in leaderboard.weapon_power_title_info:
            result["leaderboardTitles"]["weaponPowerTitles"].append({
                "region": weapon_title.region,
                "titleCfgId": weapon_title.title_cfg_id,
                "weaponId": weapon_title.weapon_id,
                "rank": weapon_title.rank,
                "regionName": weapon_title.RegionName,
                "regionType": weapon_title.RegionType,
                "isBr": weapon_title.IsBr
            })
            
        for guild_title in leaderboard.guild_war_title_info:
            result["leaderboardTitles"]["guildWarTitles"].append({
                "region": guild_title.region,
                "clanId": str(guild_title.clan_id),
                "titleCfgId": guild_title.title_cfg_id,
                "rank": guild_title.rank,
                "clanName": guild_title.clan_name
            })
    
    return result

def process_news(news_list):
    """Process AccountNews list into the desired dictionary format"""
    if not news_list:
        return []
    
    processed_news = []
    for news in news_list:
        news_data = {
            "type": NewsType.Name(news.type) if news.HasField("type") else None,
            "updateTime": str(news.update_time) if news.HasField("update_time") else None
        }
        
        if news.HasField("content"):
            content = news.content
            news_data["content"] = {
                "itemIds": list(content.item_ids),
                "rank": content.rank if content.HasField("rank") else None,
                "matchMode": content.match_mode if content.HasField("match_mode") else None,
                "mapId": content.map_id if content.HasField("map_id") else None,
                "gameMode": content.game_mode if content.HasField("game_mode") else None,
                "groupMode": content.group_mode if content.HasField("group_mode") else None,
                "treasureboxId": content.treasurebox_id if content.HasField("treasurebox_id") else None,
                "commodityId": content.commodity_id if content.HasField("commodity_id") else None,
                "storeId": content.store_id if content.HasField("store_id") else None
            }
        
        processed_news.append(news_data)
    
    return processed_news

def process_ep_info(ep_info_list):
    """Process BasicEPInfo list into the desired dictionary format"""
    if not ep_info_list:
        return []
    
    processed_ep = []
    for ep in ep_info_list:
        ep_data = {
            "epEventId": ep.ep_event_id if ep.HasField("ep_event_id") else None,
            "ownedPass": ep.owned_pass if ep.HasField("owned_pass") else None,
            "epBadge": ep.ep_badge if ep.HasField("ep_badge") else None,
            "badgeCnt": ep.badge_cnt if ep.HasField("badge_cnt") else None,
            "bpIcon": ep.bp_icon if ep.HasField("bp_icon") else None,
            "maxLevel": ep.max_level if ep.HasField("max_level") else None,
            "eventName": ep.event_name if ep.HasField("event_name") else None
        }
        processed_ep.append(ep_data)
    
    return processed_ep

def process_equipped_ach(ach_list):
    """Process EquipAchInfo list into the desired dictionary format"""
    if not ach_list:
        return []
    
    return [{"achId": ach.ach_id, "level": ach.level} for ach in ach_list]

def get_craftland_map_info(map_code):
    """Get Craftland map information (mock implementation)"""
    return {
        "MapCode": map_code,
        "MapTitle": "NEXXERA-4PLAYER",
        "description": "MAP BY - [B][00FF00]RUSHKEY\n\n[FF00FF]SUBSCRIBE AND SUPPORT US"
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

    # Prepare the response structure
    response_data = {}

    # Process basic info
    if user_info.HasField("basic_info"):
        response_data["basicInfo"] = process_account_info(user_info.basic_info)

    # Process profile info
    if user_info.HasField("profile_info"):
        response_data["profileInfo"] = process_profile_info(user_info.profile_info)

    # Process clan info
    if user_info.HasField("clan_basic_info"):
        response_data["clanBasicInfo"] = process_clan_info(user_info.clan_basic_info)

    # Process captain info (if different from basic info)
    if user_info.HasField("captain_basic_info"):
        response_data["captainBasicInfo"] = process_account_info(user_info.captain_basic_info)

    # Process pet info
    if user_info.HasField("pet_info"):
        response_data["petInfo"] = process_pet_info(user_info.pet_info)

    # Process social info
    if user_info.HasField("social_info"):
        response_data["socialInfo"] = process_social_info(user_info.social_info)

    # Process diamond cost
    if user_info.HasField("diamond_cost_res"):
        response_data["diamondCostRes"] = {
            "diamondCost": user_info.diamond_cost_res.diamond_cost if user_info.diamond_cost_res.HasField("diamond_cost") else None
        }

    # Process credit score info
    if user_info.HasField("credit_score_info"):
        credit_info = user_info.credit_score_info
        response_data["creditScoreInfo"] = {
            "creditScore": credit_info.credit_score if credit_info.HasField("credit_score") else None,
            "rewardState": RewardState.Name(credit_info.reward_state) if credit_info.HasField("reward_state") else None,
            "periodicSummaryEndTime": str(credit_info.periodic_summary_end_time) if credit_info.HasField("periodic_summary_end_time") else None
        }

    # Process news
    if user_info.news:
        response_data["news"] = process_news(user_info.news)

    # Process EP history
    if user_info.history_ep_info:
        response_data["historyEpInfo"] = process_ep_info(user_info.history_ep_info)

    # Process equipped achievements
    if user_info.equipped_ach:
        response_data["equippedAch"] = process_equipped_ach(user_info.equipped_ach)

    # Add Craftland map info
    map_code = "#FREEFIRECD617CF79A9C169DB18DB2AD2952A29D4805"  # Example map code
    response_data.update(get_craftland_map_info(map_code))

    # Add credit
    response_data["credit"] = "@Ujjaiwal"
    
    return jsonify(response_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)