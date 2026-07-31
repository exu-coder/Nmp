"""
FREE FIRE CAPTURE PROXY - BACKEND
Handles all endpoints, captures traffic, serves API
"""

from flask import Flask, request, jsonify, Response, send_from_directory
import requests
import json
import re
import base64
import os
from datetime import datetime

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Real servers
REAL_SERVERS = {
    "default": "https://clientbp.ggpolarbear.com",
    "login": "https://loginbp.ggpolarbear.com",
    "connect": "https://100067.connect.garena.com",
    "us": "https://client.us.freefiremobile.com",
    "ind": "https://client.ind.freefiremobile.com"
}

captured = []
packet_counter = 0

# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def index():
    """Serve the dashboard HTML"""
    return send_from_directory('static', 'index.html')

@app.route('/api/captured')
def get_captured():
    """Get all captured packets"""
    return jsonify({
        "count": len(captured),
        "data": captured
    })

@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    return jsonify({
        "total": len(captured),
        "gacha": len([p for p in captured if p.get('is_gacha')]),
        "jwt": len([p for p in captured if p.get('has_jwt')]),
        "login": len([p for p in captured if p.get('is_login')]),
        "switch": len([p for p in captured if p.get('is_switch')]),
        "items": sum([len(p.get('item_ids', [])) for p in captured])
    })

@app.route('/api/clear', methods=['POST'])
def clear_captured():
    """Clear all captured data"""
    global captured
    captured = []
    return jsonify({"success": True, "message": "Cleared all packets"})

@app.route('/api/health')
def health():
    """Health check"""
    return jsonify({
        "status": "ok",
        "packets": len(captured),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/tokens')
def get_tokens():
    """Get all captured tokens"""
    tokens = []
    for p in captured:
        if p.get('token'):
            tokens.append({
                "timestamp": p.get('timestamp'),
                "uid": p.get('uid'),
                "token": p.get('token')
            })
    return jsonify({"tokens": tokens})

@app.route('/api/items')
def get_items():
    """Get all captured items"""
    items = []
    for p in captured:
        if p.get('item_ids'):
            items.append({
                "timestamp": p.get('timestamp'),
                "uid": p.get('uid'),
                "items": p.get('item_ids')
            })
    return jsonify({"items": items})

# =============================================================================
# PROXY ROUTE - Captures ALL traffic
# =============================================================================

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    """Main proxy - captures and forwards all requests"""
    global packet_counter
    
    # Skip API routes
    if path.startswith('api/') or path.startswith('static/'):
        return None  # Handled by other routes
    
    # For root path with GET, serve index
    if path == '' and request.method == 'GET':
        return send_from_directory('static', 'index.html')
    
    # Build packet
    packet = {
        "id": packet_counter + 1,
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "url": request.url,
        "path": f"/{path}" if path else "/",
        "headers": dict(request.headers),
        "query": dict(request.args),
        "body_hex": None,
        "body_text": None,
        "uid": None,
        "token": None,
        "has_jwt": False,
        "endpoint_type": "unknown",
        "is_gacha": False,
        "is_switch": False,
        "is_login": False,
        "is_auth": False,
        "item_ids": [],
        "response_hex": None,
        "status": None,
        "error": None
    }
    
    # Get body
    body = request.get_data()
    if body:
        packet['body_hex'] = body.hex()
        packet['body_text'] = body.decode('utf-8', errors='ignore')[:1000]
        
        # Extract UID from body
        try:
            text = body.decode('utf-8', errors='ignore')
            if 'uid=' in text:
                uid = text.split('uid=')[1].split('&')[0]
                if uid.isdigit():
                    packet['uid'] = uid
        except:
            pass
    
    # Extract JWT
    auth = request.headers.get('Authorization', '')
    if auth and auth.startswith('Bearer '):
        packet['token'] = auth.replace('Bearer ', '')
        packet['has_jwt'] = True
        
        # Decode JWT to get UID
        try:
            parts = packet['token'].split('.')
            if len(parts) == 3:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
                jwt_data = json.loads(decoded)
                packet['uid'] = jwt_data.get('account_id') or packet['uid']
                packet['account_id'] = jwt_data.get('account_id')
                packet['external_id'] = jwt_data.get('external_id')
        except:
            pass
    
    # Detect endpoint type
    path_lower = path.lower()
    if any(x in path_lower for x in ['drawsharedgacha', 'purchasegacha', 'drawgacha', 'gachadraw']):
        packet['is_gacha'] = True
        packet['endpoint_type'] = 'gacha'
    elif 'switch' in path_lower:
        packet['is_switch'] = True
        packet['endpoint_type'] = 'switch'
    elif any(x in path_lower for x in ['getlogindata', 'majorlogin', 'login']):
        packet['is_login'] = True
        packet['endpoint_type'] = 'login'
    elif any(x in path_lower for x in ['token', 'grant', 'oauth']):
        packet['is_auth'] = True
        packet['endpoint_type'] = 'auth'
    
    # Save packet
    packet_counter += 1
    captured.append(packet)
    if len(captured) > 200:
        captured.pop(0)
    
    # Determine which server to forward to
    if 'MajorLogin' in path or 'GetLoginData' in path:
        forward_url = f"https://loginbp.ggpolarbear.com/{path}"
    elif 'connect.garena' in request.url or 'token' in path or 'grant' in path:
        forward_url = f"https://100067.connect.garena.com/{path}"
    elif 'client.ind' in request.url:
        forward_url = f"https://client.ind.freefiremobile.com/{path}"
    elif 'client.us' in request.url:
        forward_url = f"https://client.us.freefiremobile.com/{path}"
    else:
        forward_url = f"https://clientbp.ggpolarbear.com/{path}"
    
    # Add query parameters
    if request.args:
        from urllib.parse import urlencode
        forward_url += f"?{urlencode(request.args)}"
    
    try:
        # Forward request
        resp = requests.request(
            method=request.method,
            url=forward_url,
            headers={k: v for k, v in request.headers.items() 
                    if k.lower() not in ['host', 'x-forwarded-for', 'x-real-ip']},
            data=body,
            verify=False,
            timeout=30,
            allow_redirects=False
        )
        
        # Capture response
        packet['status'] = resp.status_code
        if resp.content:
            packet['response_hex'] = resp.content.hex()
            
            # Extract item IDs (9-digit numbers)
            text = resp.content.decode('utf-8', errors='ignore')
            numbers = re.findall(r'\b(\d{9})\b', text)
            if numbers:
                packet['item_ids'] = list(set(numbers))
        
        # Return response
        return Response(
            response=resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
        
    except Exception as e:
        packet['error'] = str(e)
        return jsonify({"error": str(e), "captured": True}), 502

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Create static folder if it doesn't exist
    os.makedirs('static', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
