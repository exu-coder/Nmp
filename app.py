"""
FREE FIRE CAPTURE PROXY - COMPLETE WITH DASHBOARD
Handles all endpoints including server config
Professional UI with real-time packet viewer
"""

from flask import Flask, request, jsonify, Response, render_template_string
import requests
import json
import re
import base64
from datetime import datetime

app = Flask(__name__)

# Real servers
SERVERS = {
    "default": "https://clientbp.ggpolarbear.com",
    "login": "https://loginbp.ggpolarbear.com", 
    "connect": "https://100067.connect.garena.com"
}

captured = []

# =============================================================================
# DASHBOARD HTML
# =============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Free Fire Packet Capture</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0a0e1a;
            color: #c8d6e5;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #111a2e, #0d1225);
            border: 1px solid #1e2d4a;
            border-radius: 16px;
            padding: 24px 30px;
            margin-bottom: 24px;
        }
        .header-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        .header h1 {
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(90deg, #00d4ff, #7b2ffc, #00d4ff);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: shimmer 3s ease-in-out infinite;
        }
        @keyframes shimmer {
            0% { background-position: 0% center; }
            100% { background-position: 200% center; }
        }
        .header .subtitle {
            color: #667a9a;
            font-size: 14px;
            margin-top: 4px;
        }
        .status-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00ff88;
            box-shadow: 0 0 12px rgba(0, 255, 136, 0.4);
            animation: pulse 1.5s ease-in-out infinite;
            margin-right: 8px;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.8); }
        }
        
        /* Stats */
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
            margin-top: 18px;
        }
        .stat-card {
            background: #111a2e;
            border: 1px solid #1e2d4a;
            border-radius: 10px;
            padding: 12px 16px;
            text-align: center;
            transition: 0.3s;
        }
        .stat-card:hover { border-color: #00d4ff; }
        .stat-card .number {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(90deg, #00d4ff, #7b2ffc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .stat-card .label {
            font-size: 11px;
            color: #667a9a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 2px;
        }
        
        /* Controls */
        .controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .controls input, .controls select {
            background: #111a2e;
            border: 1px solid #1e2d4a;
            color: #c8d6e5;
            padding: 10px 16px;
            border-radius: 10px;
            font-size: 13px;
            flex: 1;
            min-width: 150px;
            transition: 0.3s;
        }
        .controls input:focus, .controls select:focus {
            outline: none;
            border-color: #00d4ff;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.05);
        }
        .controls input::placeholder { color: #3a4a5a; }
        .btn {
            padding: 10px 24px;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: 0.3s;
        }
        .btn-primary {
            background: linear-gradient(90deg, #00d4ff, #7b2ffc);
            color: #fff;
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0, 212, 255, 0.2); }
        .btn-danger {
            background: linear-gradient(90deg, #ff0040, #ff0066);
            color: #fff;
        }
        .btn-danger:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(255, 0, 64, 0.2); }
        
        /* Packets */
        .packet {
            background: #111a2e;
            border: 1px solid #1e2d4a;
            border-radius: 10px;
            padding: 14px 18px;
            margin-bottom: 6px;
            transition: 0.3s;
            cursor: pointer;
        }
        .packet:hover {
            border-color: #00d4ff;
            transform: translateX(4px);
            box-shadow: 0 4px 20px rgba(0, 212, 255, 0.05);
        }
        .packet-header {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
        }
        .packet-time {
            font-size: 11px;
            color: #3a4a5a;
            font-weight: 600;
            min-width: 150px;
        }
        .packet-method {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .method-GET { background: #0a2a1a; color: #4ae0a0; }
        .method-POST { background: #0a1a2a; color: #4ac0e0; }
        .method-PUT { background: #2a2a0a; color: #e0c040; }
        .method-DELETE { background: #2a0a0a; color: #e04040; }
        
        .packet-url {
            font-size: 13px;
            word-break: break-all;
            flex: 1;
            min-width: 150px;
            color: #8ab0d0;
        }
        
        .badges { display: flex; flex-wrap: wrap; gap: 4px; }
        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.3px;
            text-transform: uppercase;
        }
        .badge-jwt { background: #0a2a1a; color: #60d080; }
        .badge-gacha { background: #2a0a1a; color: #e06080; }
        .badge-switch { background: #0a1a2a; color: #60b0e0; }
        .badge-login { background: #1a0a2a; color: #b080d0; }
        .badge-item { background: #2a2a0a; color: #e0c060; }
        
        .packet-details {
            display: none;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #1a253f;
            font-size: 12px;
        }
        .packet-details.open { display: block; }
        .detail-row {
            display: flex;
            padding: 4px 0;
            gap: 8px;
        }
        .detail-row .key {
            color: #667a9a;
            min-width: 80px;
            font-weight: 600;
        }
        .detail-row .value {
            word-break: break-all;
            color: #c8d6e5;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            background: #0a0e1a;
            padding: 4px 8px;
            border-radius: 4px;
            flex: 1;
            max-height: 150px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        .item-ids {
            color: #e0c060;
            font-weight: bold;
        }
        
        .empty-state {
            text-align: center;
            padding: 80px 20px;
            color: #3a4a5a;
        }
        .empty-state .icon { font-size: 64px; margin-bottom: 16px; }
        .empty-state h2 { font-size: 22px; color: #667a9a; }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.85);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        .modal-overlay.active { display: flex; }
        .modal {
            background: #111a2e;
            border: 1px solid #1e2d4a;
            border-radius: 16px;
            padding: 30px;
            max-width: 800px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #1a253f;
        }
        .modal-header h2 { font-size: 20px; }
        .modal-close {
            background: none;
            border: none;
            color: #667a9a;
            font-size: 28px;
            cursor: pointer;
        }
        .modal-close:hover { color: #fff; }
        .modal-body .field {
            margin: 8px 0;
            padding: 6px 0;
        }
        .modal-body .field .label {
            color: #667a9a;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .modal-body .field .content {
            font-family: 'Courier New', monospace;
            font-size: 12px;
            background: #0a0e1a;
            padding: 10px 12px;
            border-radius: 6px;
            margin-top: 4px;
            word-break: break-all;
            max-height: 200px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0a0e1a; }
        ::-webkit-scrollbar-thumb { background: #1e2d4a; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #2a3a5a; }
        
        @media (max-width: 600px) {
            .header { padding: 16px 20px; }
            .header h1 { font-size: 20px; }
            .stats { grid-template-columns: repeat(3, 1fr); }
            .stat-card .number { font-size: 20px; }
            .packet { padding: 10px 14px; }
            .packet-time { min-width: 100px; }
            .controls { flex-direction: column; }
            .controls input, .controls select { min-width: auto; }
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="header-top">
            <div>
                <h1>🔥 Free Fire Packet Capture</h1>
                <div class="subtitle">Real-time network traffic analyzer</div>
            </div>
            <div style="display:flex;align-items:center;color:#667a9a;font-size:14px;">
                <span class="status-dot"></span>
                <span id="statusText">Live</span>
                <span style="margin:0 8px;">|</span>
                <span>Server: clientbp.ggpolarbear.com</span>
            </div>
        </div>
        <div class="stats">
            <div class="stat-card"><div class="number" id="statTotal">0</div><div class="label">Total Packets</div></div>
            <div class="stat-card"><div class="number" id="statGacha">0</div><div class="label">🎰 Gacha</div></div>
            <div class="stat-card"><div class="number" id="statJWT">0</div><div class="label">🔑 JWT</div></div>
            <div class="stat-card"><div class="number" id="statLogin">0</div><div class="label">🔐 Login</div></div>
            <div class="stat-card"><div class="number" id="statItems">0</div><div class="label">💎 Items</div></div>
        </div>
    </div>

    <div class="controls">
        <input type="text" id="searchInput" placeholder="🔍 Search URL, UID, Token, Item ID..." oninput="filterPackets()">
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
            <option value="login">🔐 Login</option>
            <option value="jwt">🔑 JWT</option>
            <option value="item">💎 Item</option>
        </select>
        <button class="btn btn-primary" onclick="refreshData()">🔄 Refresh</button>
        <button class="btn btn-danger" onclick="clearData()">🗑️ Clear</button>
        <div style="display:flex;align-items:center;gap:8px;color:#3a4a5a;font-size:13px;margin-left:auto;">
            <span>Auto</span>
            <input type="checkbox" id="autoRefresh" checked onchange="toggleAutoRefresh()" style="accent-color:#00d4ff;width:18px;height:18px;">
        </div>
    </div>

    <div id="packetsContainer">
        <div class="empty-state">
            <div class="icon">📡</div>
            <h2>Waiting for packets...</h2>
            <p style="color:#3a4a5a;margin-top:8px;">Open Free Fire and start playing. All requests will appear here.</p>
        </div>
    </div>
</div>

<div class="modal-overlay" id="modalOverlay" onclick="if(event.target===this)closeModal()">
    <div class="modal">
        <div class="modal-header">
            <h2 id="modalTitle">📦 Packet Details</h2>
            <button class="modal-close" onclick="closeModal()">✕</button>
        </div>
        <div class="modal-body" id="modalContent"></div>
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
                updateStats();
            }
        } catch (e) {
            console.error('Fetch error:', e);
        }
    }

    function updateStats() {
        document.getElementById('statTotal').textContent = allPackets.length;
        document.getElementById('statGacha').textContent = allPackets.filter(p => p.is_gacha).length;
        document.getElementById('statJWT').textContent = allPackets.filter(p => p.has_jwt).length;
        document.getElementById('statLogin').textContent = allPackets.filter(p => p.is_login).length;
        document.getElementById('statItems').textContent = allPackets.filter(p => p.item_ids && p.item_ids.length > 0).length;
    }

    function filterPackets() {
        updateUI();
    }

    function getFilteredPackets() {
        const search = document.getElementById('searchInput').value.toLowerCase();
        const method = document.getElementById('methodFilter').value;
        const type = document.getElementById('typeFilter').value;

        return allPackets.filter(p => {
            const url = (p.url || '').toLowerCase();
            const uid = String(p.uid || '').toLowerCase();
            const token = (p.token || '').toLowerCase();
            const items = (p.item_ids || []).join(' ').toLowerCase();
            
            const methodMatch = !method || p.method === method;
            const typeMatch = !type || 
                (type === 'gacha' && p.is_gacha) ||
                (type === 'login' && p.is_login) ||
                (type === 'jwt' && p.has_jwt) ||
                (type === 'item' && p.item_ids && p.item_ids.length > 0);
            const searchMatch = !search || 
                url.includes(search) || 
                uid.includes(search) || 
                token.includes(search) ||
                items.includes(search);

            return methodMatch && typeMatch && searchMatch;
        });
    }

    function updateUI() {
        const container = document.getElementById('packetsContainer');
        const filtered = getFilteredPackets();

        if (allPackets.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="icon">📡</div>
                    <h2>Waiting for packets...</h2>
                    <p style="color:#3a4a5a;margin-top:8px;">Open Free Fire and start playing.</p>
                </div>
            `;
            return;
        }

        if (filtered.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="icon">🔍</div>
                    <h2>No matching packets</h2>
                    <p style="color:#3a4a5a;margin-top:8px;">Try adjusting your search filters.</p>
                </div>
            `;
            return;
        }

        let html = '';
        filtered.slice().reverse().forEach((p, idx) => {
            const time = p.timestamp ? new Date(p.timestamp).toLocaleString() : '';
            const method = p.method || 'UNKNOWN';
            const url = p.url || '';
            
            let badges = '';
            if (p.has_jwt) badges += `<span class="badge badge-jwt">🔑 JWT</span>`;
            if (p.is_gacha) badges += `<span class="badge badge-gacha">🎰 Gacha</span>`;
            if (p.is_login) badges += `<span class="badge badge-login">🔐 Login</span>`;
            if (p.is_switch) badges += `<span class="badge badge-switch">🔄 Switch</span>`;
            if (p.item_ids && p.item_ids.length > 0) {
                badges += `<span class="badge badge-item">💎 ${p.item_ids.join(', ')}</span>`;
            }

            let detailsHtml = '';
            if (p.token) {
                detailsHtml += `<div class="detail-row"><span class="key">🔑 Token:</span><span class="value">${p.token}</span></div>`;
            }
            if (p.body_hex) {
                detailsHtml += `<div class="detail-row"><span class="key">📦 Body:</span><span class="value">${p.body_hex.substring(0, 200)}${p.body_hex.length > 200 ? '...' : ''}</span></div>`;
            }
            if (p.item_ids && p.item_ids.length > 0) {
                detailsHtml += `<div class="detail-row"><span class="key">💎 Items:</span><span class="value"><span class="item-ids">${p.item_ids.join(', ')}</span></span></div>`;
            }
            if (p.uid) {
                detailsHtml += `<div class="detail-row"><span class="key">👤 UID:</span><span class="value">${p.uid}</span></div>`;
            }

            html += `
                <div class="packet" onclick="showModal(${allPackets.indexOf(p)})">
                    <div class="packet-header">
                        <span class="packet-time">${time}</span>
                        <span class="packet-method method-${method}">${method}</span>
                        <span class="packet-url">${url}</span>
                        <div class="badges">${badges}</div>
                    </div>
                    <div class="packet-details" id="details-${idx}">${detailsHtml}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    function showModal(index) {
        const p = allPackets[index];
        if (!p) return;

        const modal = document.getElementById('modalOverlay');
        const content = document.getElementById('modalContent');
        
        let html = '';
        html += `<div class="field"><div class="label">🕐 Timestamp</div><div class="content">${p.timestamp || 'N/A'}</div></div>`;
        html += `<div class="field"><div class="label">📡 Request</div><div class="content">${p.method || 'UNKNOWN'} ${p.url || 'N/A'}</div></div>`;
        if (p.uid) html += `<div class="field"><div class="label">👤 UID</div><div class="content">${p.uid}</div></div>`;
        if (p.token) html += `<div class="field"><div class="label">🔑 JWT Token</div><div class="content" style="font-size:11px;">${p.token}</div></div>`;
        if (p.body_hex) html += `<div class="field"><div class="label">📦 Body (Hex)</div><div class="content" style="font-size:11px;">${p.body_hex}</div></div>`;
        if (p.item_ids && p.item_ids.length > 0) {
            html += `<div class="field"><div class="label">💎 Item IDs</div><div class="content" style="color:#e0c060;">${p.item_ids.join(', ')}</div></div>`;
        }
        if (p.error) html += `<div class="field"><div class="label">❌ Error</div><div class="content" style="color:#e06080;">${p.error}</div></div>`;

        content.innerHTML = html;
        document.getElementById('modalTitle').textContent = `📦 Packet #${allPackets.length - index}`;
        modal.classList.add('active');
    }

    function closeModal() {
        document.getElementById('modalOverlay').classList.remove('active');
    }

    async function refreshData() {
        await fetchData();
    }

    async function clearData() {
        if (confirm('🗑️ Clear all captured packets?')) {
            try {
                await fetch('/api/clear', { method: 'POST' });
                allPackets = [];
                updateUI();
                updateStats();
            } catch (e) {
                console.error('Clear error:', e);
            }
        }
    }

    function toggleAutoRefresh() {
        const checked = document.getElementById('autoRefresh').checked;
        if (checked) {
            autoRefreshInterval = setInterval(fetchData, 3000);
        } else {
            clearInterval(autoRefreshInterval);
        }
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
        if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            refreshData();
        }
    });

    // Initial load
    fetchData();
    autoRefreshInterval = setInterval(fetchData, 3000);
</script>
</body>
</html>
"""

# =============================================================================
# PROXY ROUTE
# =============================================================================

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    """Main proxy - captures and forwards"""
    
    # For root path with GET, show dashboard
    if path == '' and request.method == 'GET' and not request.args:
        return render_template_string(DASHBOARD_HTML)
    
    # For API routes
    if path.startswith('api/'):
        if path == 'api/captured':
            return jsonify({"count": len(captured), "data": captured})
        elif path == 'api/clear' and request.method == 'POST':
            captured.clear()
            return jsonify({"success": True})
    
    # Build packet
    packet = {
        "timestamp": datetime.now().isoformat(),
        "method": request.method,
        "url": request.url,
        "path": f"/{path}" if path else "/",
        "headers": dict(request.headers),
        "body_hex": request.get_data().hex() if request.get_data() else None,
        "uid": None,
        "token": None,
        "has_jwt": False,
        "is_gacha": False,
        "is_login": False,
        "is_switch": False,
        "item_ids": []
    }
    
    # Extract JWT
    auth = request.headers.get('Authorization', '')
    if auth and auth.startswith('Bearer '):
        packet['token'] = auth.replace('Bearer ', '')
        packet['has_jwt'] = True
        
        # Try to decode JWT to get UID
        try:
            parts = packet['token'].split('.')
            if len(parts) == 3:
                payload = parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
                jwt_data = json.loads(decoded)
                packet['uid'] = jwt_data.get('account_id')
        except:
            pass
    
    # Detect endpoint type
    if any(x in path.lower() for x in ['drawsharedgacha', 'purchasegacha', 'drawgacha']):
        packet['is_gacha'] = True
    elif 'switch' in path.lower():
        packet['is_switch'] = True
    elif any(x in path.lower() for x in ['getlogindata', 'majorlogin', 'login']):
        packet['is_login'] = True
    
    # Save packet
    captured.append(packet)
    if len(captured) > 200:
        captured.pop(0)
    
    # Determine which server to forward to
    if 'MajorLogin' in path or 'GetLoginData' in path:
        forward_url = f"https://loginbp.ggpolarbear.com/{path}"
    elif 'connect.garena' in request.url or 'token' in path:
        forward_url = f"https://100067.connect.garena.com/{path}"
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
            data=request.get_data(),
            verify=False,
            timeout=30
        )
        
        # Extract item IDs from response
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

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
