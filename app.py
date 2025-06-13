from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import sys
from google.protobuf import json_format

app = Flask(__name__)

# Try importing protobuf with better error handling
try:
    from CraflandMap_info_pb2 import MapRequest, MapInfo
    print("Successfully imported protobuf modules")
except Exception as e:
    print(f"Protobuf import error: {str(e)}", file=sys.stderr)
    raise

# ... (keep your existing helper functions)

@app.route('/map-info', methods=['GET'])
def get_map_info():
    try:
        # Validate inputs
        uid = request.args.get('uid')
        region = request.args.get('region')
        
        if not uid or not region:
            return jsonify({"error": "UID and region are required"}), 400

        # Get JWT token
        jwt_info = get_jwt_token(region)
        if not jwt_info or 'token' not in jwt_info:
            return jsonify({"error": "JWT token fetch failed"}), 500

        # Prepare MapRequest
        map_request = MapRequest()
        map_request.uid = uid
        
        try:
            protobuf_data = map_request.SerializeToString()
            print(f"Serialized protobuf: {protobuf_data}")
        except Exception as e:
            return jsonify({"error": f"Protobuf serialization failed: {str(e)}"}), 500

        # Encryption
        hex_data = protobuf_to_hex(protobuf_data)
        encrypted_hex = encrypt_aes(hex_data, key, iv)

        # API Request
        headers = {
            'Authorization': f'Bearer {jwt_info["token"]}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'YourApp/1.0'
        }

        try:
            response = requests.post(
                f"{jwt_info['serverUrl']}/GetMapInfo",
                headers=headers,
                data=bytes.fromhex(encrypted_hex),
                timeout=10
            )
            response.raise_for_status()
        except requests.RequestException as e:
            return jsonify({"error": f"API request failed: {str(e)}"}), 502

        # Process response
        try:
            map_info = MapInfo()
            map_info.ParseFromString(response.content)
            return jsonify({
                "status": "success",
                "data": json_format.MessageToDict(map_info),
                "credit": "@Ujjaiwal"
            })
        except Exception as e:
            return jsonify({"error": f"Response parsing failed: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)