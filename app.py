"""
FREE FIRE CAPTURE PROXY - VERCEL DEPLOYMENT
Deploys successfully with proper entrypoint
"""

from flask import Flask, request, jsonify, Response
import requests
import json
import re
import time
from datetime import datetime

app = Flask(__name__)

# Store captured data (in-memory, resets on each function invocation)
captured = []
REAL_SERVER = "https://clientbp.ggpolarbear.com"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    """Main proxy handler - captures and forwards requests"""
    
    # Build packet data
    packet = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "url": request.url,
        "path": path,
        "headers": dict(request.headers),
        "query": dict(request.args),
        "body": request.get_data().hex() if request.get_data() else None,
        "uid": request.args.get('uid') or None
    }
    
    # Check for JWT token
    auth = request.headers.get('Authorization', '')
    if auth and auth.startswith('Bearer '):
        packet['token'] = auth.replace('Bearer ', '')
        packet['has_jwt'] = True
    
    # Check if it's a gacha request
    if 'DrawSharedGacha' in path or 'PurchaseGacha' in path:
        packet['is_gacha'] = True
        packet['endpoint_type'] = 'gacha'
    elif 'Switch' in path:
        packet['is_switch'] = True
        packet['endpoint_type'] = 'switch'
    elif 'GetLoginData' in path or 'MajorLogin' in path:
        packet['is_login'] = True
        packet['endpoint_type'] = 'login'
    else:
        packet['endpoint_type'] = 'unknown'
    
    # Save packet
    captured.append(packet)
    if len(captured) > 100:
        captured.pop(0)
    
    # If it's the root path with GET, show dashboard
    if path == '' and request.method == 'GET' and not request.args:
        return render_dashboard()
    
    # Forward to real server
    try:
        # Build forward URL
        if path:
            forward_url = f"{REAL_SERVER}/{path}"
        else:
            forward_url = REAL_SERVER
        
        if request.args:
            from urllib.parse import urlencode
            forward_url += f"?{urlencode(request.args)}"
        
        # Forward request
        resp = requests.request(
            method=request.method,
            url=forward_url,
            headers={k: v for k, v in request.headers.items() 
                    if k.lower() not in ['host', 'x-forwarded-for', 'x-real-ip']},
            data=request.get_data(),
            verify=False,
            timeout=30
        )
        
        # Save response
        packet['response_status'] = resp.status_code
        packet['response_hex'] = resp.content.hex() if resp.content else None
        
        # Extract item IDs
        if resp.content:
            text = resp.content.decode('utf-8', errors='ignore')
            numbers = re.findall(r'\b(\d{9})\b', text)
            if numbers:
                packet['item_ids'] = list(set(numbers))
        
        return Response(
            response=resp.content,
            status=resp.status_code,
            headers=dict(resp.headers)
        )
        
    except Exception as e:
        packet['error'] = str(e)
        return jsonify({"error": str(e), "packet": packet}), 502

@app.route('/api/captured')
def get_captured():
    """Get all captured packets"""
    return jsonify({
        "count": len(captured),
        "data": captured
    })

@app.route('/api/clear', methods=['POST'])
def clear_captured():
    """Clear all captured data"""
    captured.clear()
    return jsonify({"success": True})

@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    return jsonify({
        "total": len(captured),
        "gacha": len([p for p in captured if p.get('is_gacha')]),
        "jwt": len([p for p in captured if p.get('has_jwt')]),
        "login": len([p for p in captured if p.get('is_login')]),
        "switch": len([p for p in captured if p.get('is_switch')])
    })

def render_dashboard():
    """Simple dashboard HTML"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔥 Free Fire Packet Capture</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0a0e1a; color: #c0d0e0; padding: 20px; }
            .header { background: #1a1f35; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
            h1 { color: #00d4ff; }
            .stats { display: flex; gap: 20px; flex-wrap: wrap; margin: 15px 0; }
            .stats span { background: #1a253f; padding: 5px 15px; border-radius: 20px; }
            .stats .num { color: #00d4ff; font-weight: bold; }
            .packet { background: #111a2e; border: 1px solid #2a3a5a; padding: 10px; margin: 5px 0; border-radius: 5px; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 5px; }
            .badge-jwt { background: #1a4a2a; color: #60d080; }
            .badge-gacha { background: #4a1a2a; color: #e06080; }
            .badge-switch { background: #1a4a4a; color: #60e0e0; }
            .badge-login { background: #2a2a4a; color: #8080e0; }
            .refresh-btn { background: #1a253f; border: 1px solid #2a3a5a; color: #c0d0e0; padding: 8px 16px; border-radius: 5px; cursor: pointer; }
            .refresh-btn:hover { background: #2a3a5a; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔥 Free Fire Packet Capture</h1>
            <div class="stats">
                <span>📦 Total: <span class="num" id="total">0</span></span>
                <span>🎰 Gacha: <span class="num" id="gacha">0</span></span>
                <span>🔑 JWT: <span class="num" id="jwt">0</span></span>
                <span>🔄 Switch: <span class="num" id="switch">0</span></span>
                <span>🔐 Login: <span class="num" id="login">0</span></span>
            </div>
            <button class="refresh-btn" onclick="refresh()">🔄 Refresh</button>
            <button class="refresh-btn" onclick="clearData()" style="background:#4a1a1a;border-color:#6a2a2a;">🗑️ Clear</button>
        </div>
        <div id="packets"><p>Waiting for packets...</p></div>
        <script>
            async function refresh() {
                try {
                    const r = await fetch('/api/captured');
                    const data = await r.json();
                    const packets = data.data || [];
                    
                    document.getElementById('total').textContent = packets.length;
                    document.getElementById('gacha').textContent = packets.filter(p => p.is_gacha).length;
                    document.getElementById('jwt').textContent = packets.filter(p => p.has_jwt).length;
                    document.getElementById('switch').textContent = packets.filter(p => p.is_switch).length;
                    document.getElementById('login').textContent = packets.filter(p => p.is_login).length;
                    
                    let html = '';
                    packets.slice().reverse().forEach(p => {
                        let badges = '';
                        if (p.has_jwt) badges += `<span class="badge badge-jwt">🔑 JWT</span>`;
                        if (p.is_gacha) badges += `<span class="badge badge-gacha">🎰 Gacha</span>`;
                        if (p.is_switch) badges += `<span class="badge badge-switch">🔄 Switch</span>`;
                        if (p.is_login) badges += `<span class="badge badge-login">🔐 Login</span>`;
                        
                        html += `<div class="packet">
                            <div><strong>${p.method || 'UNKNOWN'}</strong> ${p.path || ''} ${badges}</div>
                            <div style="font-size:11px;color:#667a9a;">${p.timestamp || ''} ${p.uid ? '👤 UID: '+p.uid : ''}</div>
                            ${p.token ? `<div style="font-size:11px;word-break:break-all;">🔑 ${p.token.substring(0, 50)}...</div>` : ''}
                        </div>`;
                    });
                    document.getElementById('packets').innerHTML = html || '<p>No packets yet...</p>';
                } catch(e) { console.error(e); }
            }
            
            async function clearData() {
                if (confirm('Clear all captured packets?')) {
                    await fetch('/api/clear', { method: 'POST' });
                    refresh();
                }
            }
            
            refresh();
            setInterval(refresh, 3000);
        </script>
    </body>
    </html>
    '''

# This is the entrypoint Vercel looks for
# 'app' is the top-level variable
