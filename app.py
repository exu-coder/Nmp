from flask import Flask, request, jsonify, Response
import requests
import json
import re
from datetime import datetime

app = Flask(__name__)

# Store captured data
captured = []

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    """Capture and forward all requests"""
    
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
    if 'DrawSharedGacha' in request.url or 'PurchaseGacha' in request.url:
        packet['is_gacha'] = True
    
    # Save packet
    captured.append(packet)
    if len(captured) > 100:
        captured.pop(0)
    
    # Check if this is the dashboard
    if path == '' and request.method == 'GET':
        return render_dashboard()
    
    # Forward to real server
    try:
        real_url = f"https://clientbp.ggpolarbear.com/{path}" if path else "https://clientbp.ggpolarbear.com/"
        if request.args:
            from urllib.parse import urlencode
            real_url += f"?{urlencode(request.args)}"
        
        # Forward request
        resp = requests.request(
            method=request.method,
            url=real_url,
            headers={k: v for k, v in request.headers.items() if k.lower() not in ['host']},
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
        return jsonify({"error": str(e)}), 502

@app.route('/api/captured')
def get_captured():
    return jsonify({
        "count": len(captured),
        "data": captured
    })

@app.route('/api/clear', methods=['POST'])
def clear_captured():
    captured.clear()
    return jsonify({"success": True})

def render_dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🔥 Free Fire Packet Capture</title>
        <style>
            body { font-family: Arial; background: #0a0e1a; color: #c0d0e0; padding: 20px; }
            .header { background: #1a1f35; padding: 20px; border-radius: 10px; }
            .packet { background: #111a2e; border: 1px solid #2a3a5a; border-radius: 8px; padding: 10px; margin: 5px 0; cursor: pointer; }
            .packet:hover { border-color: #00d4ff; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 5px; }
            .badge-jwt { background: #1a4a2a; color: #60d080; }
            .badge-gacha { background: #4a1a2a; color: #e06080; }
            .badge-item { background: #4a3a1a; color: #e0c060; }
            .details { display: none; margin-top: 10px; padding: 10px; background: #0a0e1a; border-radius: 4px; font-size: 11px; word-break: break-all; }
            .details.show { display: block; }
            .stats { display: flex; gap: 20px; flex-wrap: wrap; margin: 15px 0; }
            .stats span { background: #1a253f; padding: 5px 15px; border-radius: 20px; }
            .stats .num { color: #00d4ff; font-weight: bold; }
            .hex { font-family: monospace; font-size: 10px; background: #0a0e1a; padding: 8px; border-radius: 4px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔥 Free Fire Packet Capture</h1>
            <div class="stats">
                <span>📦 Total: <span class="num" id="total">0</span></span>
                <span>🎯 Gacha: <span class="num" id="gacha">0</span></span>
                <span>🔑 JWT: <span class="num" id="jwt">0</span></span>
                <span>💎 Items: <span class="num" id="items">0</span></span>
            </div>
            <button onclick="clearData()" style="background:#4a1a1a;color:#e06060;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">🗑️ Clear</button>
        </div>
        <div id="packets"></div>
        <script>
            let allData = [];
            
            async function refresh() {
                try {
                    const r = await fetch('/api/captured');
                    const data = await r.json();
                    allData = data.data || [];
                    
                    // Update stats
                    document.getElementById('total').textContent = allData.length;
                    document.getElementById('gacha').textContent = allData.filter(p => p.is_gacha).length;
                    document.getElementById('jwt').textContent = allData.filter(p => p.has_jwt).length;
                    document.getElementById('items').textContent = allData.filter(p => p.item_ids && p.item_ids.length).length;
                    
                    // Render packets
                    let html = '';
                    allData.slice().reverse().forEach((p, i) => {
                        const time = p.timestamp ? new Date(p.timestamp).toLocaleTimeString() : '';
                        let badges = '';
                        if (p.has_jwt) badges += `<span class="badge badge-jwt">🔑 JWT</span>`;
                        if (p.is_gacha) badges += `<span class="badge badge-gacha">🎰 Gacha</span>`;
                        if (p.item_ids && p.item_ids.length) badges += `<span class="badge badge-item">💎 ${p.item_ids.join(', ')}</span>`;
                        
                        html += `<div class="packet" onclick="toggleDetails(${i})">
                            <div>${time} <strong>${p.method || 'UNKNOWN'}</strong> ${p.url || ''} ${badges}</div>
                            <div class="details" id="details-${i}">
                                <div><strong>UID:</strong> ${p.uid || 'N/A'}</div>
                                ${p.token ? `<div><strong>Token:</strong> ${p.token.substring(0, 50)}...</div>` : ''}
                                ${p.body ? `<div class="hex"><strong>Body:</strong> ${p.body.substring(0, 200)}</div>` : ''}
                                ${p.response_hex ? `<div class="hex"><strong>Response:</strong> ${p.response_hex.substring(0, 200)}</div>` : ''}
                                ${p.error ? `<div style="color:#e06060;"><strong>Error:</strong> ${p.error}</div>` : ''}
                            </div>
                        </div>`;
                    });
                    document.getElementById('packets').innerHTML = html || '<div style="text-align:center;padding:60px;color:#667a9a;">📡 Waiting for packets...</div>';
                } catch(e) {
                    console.error(e);
                }
            }
            
            function toggleDetails(id) {
                document.getElementById('details-' + id).classList.toggle('show');
            }
            
            async function clearData() {
                if (confirm('Clear all captured packets?')) {
                    await fetch('/api/clear', { method: 'POST' });
                    refresh();
                }
            }
            
            setInterval(refresh, 3000);
            refresh();
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
