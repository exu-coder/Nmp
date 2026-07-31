import json
import time
import base64
import re
import os
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import requests
from flask import Flask, request, jsonify, Response, render_template_string, stream_with_context

# ================= CONFIG =================
REAL_SERVER = "https://clientbp.ggpolarbear.com"

# ================= HTML TEMPLATE =================
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Free Fire Packet Capture Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0a0e1a;
            color: #c0d0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #1a1f35, #0d1225);
            border: 1px solid #2a3a5a;
            border-radius: 12px;
            padding: 20px 30px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .header h1 {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(90deg, #00d4ff, #7b2ffc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .header .stats {
            display: flex;
            gap: 20px;
            font-size: 14px;
        }
        .header .stats span {
            background: #1a253f;
            padding: 6px 16px;
            border-radius: 20px;
            border: 1px solid #2a3a5a;
        }
        .header .stats .num {
            color: #00d4ff;
            font-weight: bold;
        }
        .filters {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .filters input, .filters select {
            background: #121a2e;
            border: 1px solid #2a3a5a;
            color: #c0d0e0;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 13px;
            flex: 1;
            min-width: 150px;
        }
        .filters input:focus, .filters select:focus {
            outline: none;
            border-color: #00d4ff;
        }
        .filters button {
            background: #00d4ff;
            border: none;
            color: #0a0e1a;
            padding: 8px 20px;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
        }
        .filters button:hover {
            background: #00e5ff;
            transform: scale(1.02);
        }
        .packet-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 15px;
        }
        .packet-card {
            background: #111a2e;
            border: 1px solid #1e2d4a;
            border-radius: 10px;
            padding: 15px;
            transition: 0.3s;
            cursor: pointer;
            position: relative;
        }
        .packet-card:hover {
            border-color: #00d4ff;
            transform: translateY(-3px);
            box-shadow: 0 8px 25px rgba(0, 212, 255, 0.1);
        }
        .packet-card .time {
            font-size: 11px;
            color: #667a9a;
        }
        .packet-card .method {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        }
        .method-get { background: #1a5a3a; color: #4ae0a0; }
        .method-post { background: #1a3a5a; color: #4ac0e0; }
        .method-put { background: #5a4a1a; color: #e0c040; }
        .method-delete { background: #5a1a1a; color: #e04040; }
        .packet-card .url {
            font-size: 13px;
            margin: 6px 0;
            word-break: break-all;
            color: #8ab0d0;
        }
        .packet-card .badge {
            display: inline-block;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 10px;
            margin-right: 5px;
        }
        .badge-ff { background: #2a1a5a; color: #b080e0; }
        .badge-jwt { background: #1a4a2a; color: #60d080; }
        .badge-gacha { background: #4a1a2a; color: #e06080; }
        .badge-item { background: #4a3a1a; color: #e0c060; }
        .packet-card .details {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #1a253f;
            display: none;
            font-size: 12px;
            color: #8aa0b0;
        }
        .packet-card .details.show { display: block; }
        .packet-card .details .hex {
            background: #0a0e1a;
            padding: 8px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 11px;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 150px;
            overflow-y: auto;
        }
        .packet-card .details .label {
            color: #667a9a;
            font-weight: bold;
            margin-top: 6px;
        }
        .empty {
            text-align: center;
            padding: 60px 20px;
            color: #3a4a5a;
        }
        .empty .icon { font-size: 48px; }
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
        }
        .auto-refresh input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: #00d4ff;
        }
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .modal-overlay.active { display: flex; }
        .modal {
            background: #111a2e;
            border: 1px solid #2a3a5a;
            border-radius: 12px;
            padding: 25px;
            max-width: 800px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal .close {
            float: right;
            background: none;
            border: none;
            color: #667a9a;
            font-size: 24px;
            cursor: pointer;
        }
        .modal .close:hover { color: #fff; }
        .modal .title { font-size: 18px; font-weight: bold; margin-bottom: 15px; }
        .modal .field { margin: 8px 0; }
        .modal .field .key { color: #667a9a; font-weight: bold; }
        .modal .field .value { color: #c0d0e0; word-break: break-all; }
        .modal .field .value .hex { font-family: monospace; font-size: 12px; background: #0a0e1a; padding: 8px; border-radius: 4px; display: block; max-height: 200px; overflow-y: auto; }
        .status-bar {
            display: flex;
            justify-content: space-between;
            padding: 10px 20px;
            background: #0d1225;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .status-bar .item { color: #667a9a; }
        .status-bar .item .val { color: #00d4ff; font-weight: bold; }
        .token-highlight { color: #7b2ffc; }
        @media (max-width: 600px) {
            .header { flex-direction: column; gap: 10px; }
            .header .stats { flex-wrap: wrap; }
            .packet-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 Free Fire Packet Capture</h1>
        <div class="stats">
            <span>📦 <span class="num" id="totalCount">0</span></span>
            <span>🎯 <span class="num" id="gachaCount">0</span></span>
            <span>🔑 <span class="num" id="tokenCount">0</span></span>
            <span>💎 <span class="num" id="itemCount">0</span></span>
        </div>
    </div>

    <div class="status-bar">
        <span class="item">🟢 Status: <span class="val" id="statusText">Connected</span></span>
        <span class="item">📡 Server: <span class="val">{{ server }}</span></span>
        <span class="item">🔄 Auto-refresh: <span class="val" id="refreshStatus">ON</span></span>
    </div>

    <div class="filters">
        <input type="text" id="searchInput" placeholder="🔍 Search URL, UID, token..." onkeyup="filterPackets()">
        <select id="methodFilter" onchange="filterPackets()">
            <option value="">All Methods</option>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
        </select>
        <select id="typeFilter" onchange="filterPackets()">
            <option value="">All Types</option>
            <option value="gacha">🎰 Gacha</option>
            <option value="switch">🔄 Switch</option>
            <option value="login">🔐 Login</option>
            <option value="jwt">🔑 JWT</option>
            <option value="item">💎 Item</option>
        </select>
        <button onclick="clearAll()">🗑️ Clear All</button>
        <button onclick="refreshData()">🔄 Refresh</button>
        <div class="auto-refresh">
            <input type="checkbox" id="autoRefresh" checked onchange="toggleAutoRefresh()">
            <label for="autoRefresh">Auto</label>
        </div>
    </div>

    <div id="packetsContainer">
        <div class="empty">
            <div class="icon">📡</div>
            <h3>Waiting for packets...</h3>
            <p>Open Free Fire and start playing. Packets will appear here.</p>
        </div>
    </div>

    <!-- Modal -->
    <div class="modal-overlay" id="modalOverlay">
        <div class="modal">
            <button class="close" onclick="closeModal()">✕</button>
            <div id="modalContent"></div>
        </div>
    </div>

    <script>
        let allPackets = [];
        let autoRefreshInterval = null;

        async function fetchData() {
            try {
                const response = await fetch('/api/captured');
                if (response.ok) {
                    const data = await response.json();
                    allPackets = data.data || [];
                    updateUI();
                }
            } catch (e) {
                console.error('Error fetching data:', e);
            }
        }

        function updateUI() {
            const container = document.getElementById('packetsContainer');
            const total = allPackets.length;
            
            // Update stats
            document.getElementById('totalCount').textContent = total;
            
            const gachaCount = allPackets.filter(p => p.is_gacha || p.type === 'gacha').length;
            document.getElementById('gachaCount').textContent = gachaCount;
            
            const tokenCount = allPackets.filter(p => p.token || p.type === 'jwt').length;
            document.getElementById('tokenCount').textContent = tokenCount;
            
            const itemCount = allPackets.filter(p => p.item_ids && p.item_ids.length > 0).length;
            document.getElementById('itemCount').textContent = itemCount;

            if (total === 0) {
                container.innerHTML = `
                    <div class="empty">
                        <div class="icon">📡</div>
                        <h3>Waiting for packets...</h3>
                        <p>Open Free Fire and start playing. Packets will appear here.</p>
                    </div>
                `;
                return;
            }

            let html = '<div class="packet-grid">';
            const filtered = getFilteredPackets();
            
            if (filtered.length === 0) {
                html += `<div class="empty"><div class="icon">🔍</div><h3>No matching packets</h3></div>`;
            } else {
                filtered.forEach((p, index) => {
                    html += createPacketCard(p, index);
                });
            }
            
            html += '</div>';
            container.innerHTML = html;
        }

        function getFilteredPackets() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            const method = document.getElementById('methodFilter').value;
            const type = document.getElementById('typeFilter').value;

            return allPackets.filter(p => {
                const url = (p.url || '').toLowerCase();
                const uid = String(p.uid || '');
                const token = (p.token || '').toLowerCase();
                const methodMatch = !method || p.method === method;
                const typeMatch = !type || p.type === type || p.is_gacha === (type === 'gacha');
                const searchMatch = !search || url.includes(search) || uid.includes(search) || token.includes(search);
                return methodMatch && typeMatch && searchMatch;
            });
        }

        function createPacketCard(packet, index) {
            const time = packet.timestamp ? new Date(packet.timestamp).toLocaleTimeString() : 'N/A';
            const method = packet.method || 'UNKNOWN';
            const url = packet.url || '';
            const isFF = packet.is_freefire || false;
            const hasToken = packet.token || false;
            const isGacha = packet.is_gacha || (packet.url && (packet.url.includes('DrawSharedGacha') || packet.url.includes('PurchaseGacha')));
            const isSwitch = packet.url && packet.url.includes('Switch');
            const itemIds = packet.item_ids || [];
            
            let badges = '';
            if (isFF) badges += `<span class="badge badge-ff">🔥 FF</span>`;
            if (hasToken) badges += `<span class="badge badge-jwt">🔑 JWT</span>`;
            if (isGacha) badges += `<span class="badge badge-gacha">🎰 Gacha</span>`;
            if (isSwitch) badges += `<span class="badge badge-gacha">🔄 Switch</span>`;
            if (itemIds.length > 0) badges += `<span class="badge badge-item">💎 ${itemIds.join(', ')}</span>`;
            
            const methodClass = `method-${method.toLowerCase()}`;
            
            return `
                <div class="packet-card" onclick="showModal(${index})">
                    <div class="time">${time}</div>
                    <span class="method ${methodClass}">${method}</span>
                    ${badges}
                    <div class="url">${url}</div>
                    ${packet.uid ? `<div style="font-size:11px;color:#667a9a;">👤 UID: ${packet.uid}</div>` : ''}
                    <div class="details show">
                        ${packet.body_text ? `<div class="label">📦 Body:</div><div class="hex">${escapeHtml(packet.body_text.substring(0, 500))}</div>` : ''}
                        ${packet.body_hex ? `<div class="label">🔢 Hex:</div><div class="hex">${packet.body_hex.substring(0, 200)}...</div>` : ''}
                    </div>
                </div>
            `;
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function filterPackets() {
            updateUI();
        }

        function showModal(index) {
            const packet = allPackets[index];
            if (!packet) return;
            
            const modal = document.getElementById('modalOverlay');
            const content = document.getElementById('modalContent');
            
            let html = `<div class="title">📦 Packet Details</div>`;
            html += `<div class="field"><span class="key">Time:</span> <span class="value">${packet.timestamp || 'N/A'}</span></div>`;
            html += `<div class="field"><span class="key">Method:</span> <span class="value">${packet.method || 'N/A'}</span></div>`;
            html += `<div class="field"><span class="key">URL:</span> <span class="value">${packet.url || 'N/A'}</span></div>`;
            html += `<div class="field"><span class="key">UID:</span> <span class="value">${packet.uid || 'N/A'}</span></div>`;
            if (packet.token) {
                html += `<div class="field"><span class="key">🔑 Token:</span> <span class="value" style="word-break:break-all;">${packet.token}</span></div>`;
            }
            if (packet.item_ids && packet.item_ids.length > 0) {
                html += `<div class="field"><span class="key">💎 Item IDs:</span> <span class="value">${packet.item_ids.join(', ')}</span></div>`;
            }
            if (packet.body_hex) {
                html += `<div class="field"><span class="key">📦 Body Hex:</span> <span class="value"><span class="hex">${packet.body_hex}</span></span></div>`;
            }
            if (packet.body_text) {
                html += `<div class="field"><span class="key">📝 Body Text:</span> <span class="value"><span class="hex">${escapeHtml(packet.body_text)}</span></span></div>`;
            }
            if (packet.response_hex) {
                html += `<div class="field"><span class="key">📥 Response Hex:</span> <span class="value"><span class="hex">${packet.response_hex}</span></span></div>`;
            }
            html += `<div class="field"><span class="key">📊 Headers:</span> <span class="value">${JSON.stringify(packet.headers || {}, null, 2)}</span></div>`;
            
            content.innerHTML = html;
            modal.classList.add('active');
        }

        function closeModal() {
            document.getElementById('modalOverlay').classList.remove('active');
        }

        function clearAll() {
            if (confirm('Clear all captured packets?')) {
                fetch('/api/clear', { method: 'POST' })
                    .then(() => {
                        allPackets = [];
                        updateUI();
                    });
            }
        }

        function refreshData() {
            fetchData();
        }

        function toggleAutoRefresh() {
            const checked = document.getElementById('autoRefresh').checked;
            document.getElementById('refreshStatus').textContent = checked ? 'ON' : 'OFF';
            
            if (checked) {
                autoRefreshInterval = setInterval(fetchData, 3000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        }

        // Auto refresh on load
        fetchData();
        autoRefreshInterval = setInterval(fetchData, 3000);

        // Click outside modal to close
        document.getElementById('modalOverlay').addEventListener('click', function(e) {
            if (e.target === this) closeModal();
        });
    </script>
</body>
</html>
'''

# ================= FLASK APP =================

app = Flask(__name__)

# In-memory storage for captured data
captured_packets = []
MAX_PACKETS = 500

# ================= HELPER FUNCTIONS =================

def add_packet(packet):
    """Add a packet to the captured list"""
    global captured_packets
    
    # Check if it's a gacha request
    if packet.get('url'):
        url = packet['url'].lower()
        packet['is_gacha'] = any(x in url for x in ['drawsharedgacha', 'purchasegacha'])
        packet['is_switch'] = 'switch' in url
        packet['is_login'] = 'getlogindata' in url or 'majorlogin' in url
    
    # Check for JWT token
    if packet.get('token'):
        packet['has_token'] = True
    
    # Extract item IDs from response
    if packet.get('response_text'):
        numbers = re.findall(r'\b(\d{9})\b', packet['response_text'])
        if numbers:
            packet['item_ids'] = list(set(numbers))
    
    # Add to list
    captured_packets.append(packet)
    
    # Keep only last MAX_PACKETS
    if len(captured_packets) > MAX_PACKETS:
        captured_packets = captured_packets[-MAX_PACKETS:]
    
    return packet

def decode_jwt_payload(token):
    """Decode JWT payload"""
    try:
        parts = token.split('.')
        if len(parts) == 3:
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
            return json.loads(decoded)
    except:
        pass
    return None

# ================= ROUTES =================

@app.route('/', methods=['GET'])
def dashboard():
    """Main dashboard page"""
    return render_template_string(DASHBOARD_HTML, server=REAL_SERVER)

@app.route('/api/captured', methods=['GET'])
def get_captured():
    """Get all captured packets"""
    return jsonify({
        "count": len(captured_packets),
        "data": captured_packets
    })

@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    """Get all captured JWT tokens"""
    tokens = []
    for p in captured_packets:
        if p.get('token'):
            tokens.append({
                "timestamp": p.get('timestamp'),
                "uid": p.get('uid'),
                "token": p.get('token'),
                "url": p.get('url')
            })
    return jsonify({"tokens": tokens})

@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all captured item IDs"""
    items = []
    for p in captured_packets:
        if p.get('item_ids'):
            items.append({
                "timestamp": p.get('timestamp'),
                "uid": p.get('uid'),
                "items": p.get('item_ids'),
                "url": p.get('url')
            })
    return jsonify({"items": items})

@app.route('/api/clear', methods=['POST'])
def clear_data():
    """Clear all captured data"""
    global captured_packets
    captured_packets = []
    return jsonify({"success": True, "message": "Cleared all packets"})

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "alive",
        "packets": len(captured_packets),
        "timestamp": datetime.now().isoformat()
    })

# ================= PROXY ROUTE =================

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    """Main proxy handler - captures all requests"""
    
    # Get request details
    method = request.method
    url = request.url
    headers = dict(request.headers)
    body = request.get_data()
    query = dict(request.args)
    
    # Extract UID
    uid = None
    if 'uid' in query:
        uid = query.get('uid')
    elif body:
        try:
            body_str = body.decode('utf-8', errors='ignore')
            if 'uid=' in body_str:
                uid = body_str.split('uid=')[1].split('&')[0]
        except:
            pass
    
    # Extract JWT token
    token = None
    auth = headers.get('Authorization', '')
    if auth and auth.startswith('Bearer '):
        token = auth.replace('Bearer ', '')
    
    # Build packet data
    packet = {
        "timestamp": datetime.now().isoformat(),
        "method": method,
        "url": url,
        "path": path,
        "headers": {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'cookie']},
        "query": query,
        "uid": uid,
        "token": token,
        "body_hex": body.hex() if body else None,
        "body_text": body.decode('utf-8', errors='ignore')[:1000] if body else None,
        "is_freefire": any(domain in url.lower() for domain in 
                          ['garena', 'ggpolarbear', 'freefire', 'ggblueshark'])
    }
    
    # Save packet
    add_packet(packet)
    
    # Forward request to real server
    try:
        # Build forward URL
        if path:
            forward_url = f"{REAL_SERVER}/{path}"
        else:
            forward_url = REAL_SERVER
        
        if query:
            from urllib.parse import urlencode
            forward_url = f"{forward_url}?{urlencode(query)}"
        
        # Forward headers (remove proxy headers)
        forward_headers = {k: v for k, v in headers.items() 
                          if k.lower() not in ['host', 'x-forwarded-for', 'x-real-ip', 'x-vercel-proxy']}
        
        # Forward request
        resp = requests.request(
            method=method,
            url=forward_url,
            headers=forward_headers,
            data=body,
            verify=False,
            timeout=30
        )
        
        # Capture response
        response_data = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "uid": uid,
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "response_hex": resp.content.hex() if resp.content else None,
            "response_text": resp.content.decode('utf-8', errors='ignore')[:1000] if resp.content else None
        }
        
        # Add to packet
        packet['response_status'] = resp.status_code
        packet['response_hex'] = response_data['response_hex']
        packet['response_text'] = response_data['response_text']
        
        # Extract item IDs from response
        if resp.content:
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
        return jsonify({
            "error": str(e),
            "captured": packet
        }), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)