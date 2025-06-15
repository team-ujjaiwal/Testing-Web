from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import AccountPersonalShow_pb2
from secret import key, iv

app = Flask(__name__)

def encrypt_aes(data, key, iv):
    cipher = AES.new(key.encode()[:16], AES.MODE_CBC, iv.encode()[:16])
    padded_data = pad(data, AES.block_size)
    return cipher.encrypt(padded_data)

def get_jwt_token(region):
    # Your existing JWT token implementation
    pass

@app.route('/get-map-data', methods=['GET'])
def get_map_data():
    try:
        # 1. Prepare the request protobuf
        req = AccountPersonalShow_pb2.MapRequest()
        req.map_code = "default_map"  # Set appropriate map code
        
        # 2. Encrypt the request
        encrypted_data = encrypt_aes(req.SerializeToString(), key, iv)
        
        # 3. Get JWT token
        jwt_info = get_jwt_token(request.args.get('region', 'IND'))
        if not jwt_info:
            return jsonify({"error": "Authentication failed"}), 401
            
        # 4. Make the API call
        headers = {
            'Authorization': f'Bearer {jwt_info["token"]}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Unity-Version': '2018.4.11f1'
        }
        
        response = requests.post(
            f"{jwt_info['serverUrl']}/GetPlayerPersonalShow",
            headers=headers,
            data=encrypted_data
        )
        response.raise_for_status()
        
        # 5. Decrypt and parse response
        cipher = AES.new(key.encode()[:16], AES.MODE_CBC, iv.encode()[:16])
        decrypted = cipher.decrypt(response.content)
        
        player_data = AccountPersonalShow_pb2.AccountPersonalShowInfo()
        player_data.ParseFromString(decrypted)
        
        # 6. Extract map and craftland data
        result = {}
        
        if player_data.HasField('basic_info'):
            basic_info = player_data.basic_info
            
            # Craftland Info
            if hasattr(basic_info, 'craftland_info'):
                craftland = basic_info.craftland_info
                result['craftland'] = {
                    'name': craftland.CraftlandName,
                    'code': craftland.CraftlandCode,
                    'title': craftland.CraftlandTitle,
                    'description': craftland.CraftlandDescription
                }
            
            # Map Info
            if hasattr(basic_info, 'map_info'):
                map_info = basic_info.map_info
                result['map'] = {
                    'code': map_info.MapCode,
                    'title': map_info.MapTitle,
                    'description': map_info.description
                }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": "Failed to get map data",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)