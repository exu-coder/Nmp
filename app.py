import os
import sys
import json
import time
import socket
import threading
import requests
import base64
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# =============================================================================
# COLORS
# =============================================================================

class Colors:
    CYAN = '\033[1;96m'
    GREEN = '\033[1;92m'
    YELLOW = '\033[1;93m'
    RED = '\033[1;91m'
    END = '\033[0m'
    WHITE = '\033[1;97m'
    PURPLE = '\033[1;95m'
    PINK = '\033[1;91m'
    BLUE = '\033[1;94m'

# =============================================================================
# CONFIG
# =============================================================================

CAPTURE_DIR = "captured_data"
os.makedirs(CAPTURE_DIR, exist_ok=True)

# Dynamic endpoint storage
ENDPOINTS = {
    "discovered": [],
    "by_type": {
        "gacha": [],
        "login": [],
        "switch": [],
        "auth": [],
        "unknown": []
    },
    "seen": set()
}

# =============================================================================
# CAPTURE LOG
# =============================================================================

def log(message, color=Colors.WHITE):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")

def save_capture(packet):
    """Save captured packet to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{CAPTURE_DIR}/packet_{timestamp}_{packet['id']}.json"
    
    with open(filename, 'w') as f:
        json.dump(packet, f, indent=2, default=str)
    
    return filename

def save_endpoints():
    """Save discovered endpoints to file"""
    with open(f"{CAPTURE_DIR}/discovered_endpoints.json", 'w') as f:
        json.dump(ENDPOINTS, f, indent=2)

def save_token(token, url, uid=None):
    """Save captured JWT token"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{CAPTURE_DIR}/jwt_{timestamp}.txt"
    
    with open(filename, 'w') as f:
        f.write(f"JWT: {token}\n")
        f.write(f"URL: {url}\n")
        f.write(f"UID: {uid}\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
    
    # Also append to tokens file
    with open(f"{CAPTURE_DIR}/all_tokens.txt", 'a') as f:
        f.write(f"{datetime.now().isoformat()} | UID: {uid} | URL: {url} | Token: {token}\n")
    
    return filename

def save_payload(payload, url, uid=None):
    """Save captured payload"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{CAPTURE_DIR}/payload_{timestamp}.bin"
    
    with open(filename, 'wb') as f:
        f.write(payload if isinstance(payload, bytes) else bytes.fromhex(payload))
    
    # Save metadata
    meta_file = filename.replace('.bin', '_meta.txt')
    with open(meta_file, 'w') as f:
        f.write(f"URL: {url}\n")
        f.write(f"UID: {uid}\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
    
    return filename

# =============================================================================
# ENDPOINT DISCOVERY
# =============================================================================

def discover_endpoint(url, method, path):
    """Discover and categorize endpoint"""
    
    # Check if we've seen this endpoint before
    endpoint_key = f"{method}:{path}"
    if endpoint_key in ENDPOINTS["seen"]:
        return
    
    ENDPOINTS["seen"].add(endpoint_key)
    
    # Determine endpoint type
    endpoint_type = "unknown"
    
    # Gacha/Spin endpoints
    if any(keyword in path.lower() for keyword in ['gacha', 'draw', 'spin', 'purchase']):
        endpoint_type = "gacha"
    # Login/Auth endpoints
    elif any(keyword in path.lower() for keyword in ['login', 'auth', 'token', 'grant', 'oauth']):
        endpoint_type = "auth"
    # Switch endpoints
    elif 'switch' in path.lower():
        endpoint_type = "switch"
    # Data endpoints
    elif any(keyword in path.lower() for keyword in ['data', 'info', 'profile']):
        endpoint_type = "data"
    
    # Add to discovered list
    endpoint_info = {
        "method": method,
        "url": url,
        "path": path,
        "type": endpoint_type,
        "discovered_at": datetime.now().isoformat(),
        "headers": None,
        "body": None
    }
    
    ENDPOINTS["discovered"].append(endpoint_info)
    ENDPOINTS["by_type"][endpoint_type].append(endpoint_info)
    
    # Save to file
    save_endpoints()
    
    # Log discovery
    log(f"🎯 New Endpoint Discovered: {method} {path} [{endpoint_type}]", Colors.GREEN)
    
    return endpoint_info

# =============================================================================
# PROXY HANDLER
# =============================================================================

class DynamicProxyHandler(BaseHTTPRequestHandler):
    """Dynamic proxy that discovers and captures all endpoints"""
    
    packet_counter = 0
    
    def log_message(self, format, *args):
        pass
    
    def do_CONNECT(self):
        """Handle HTTPS CONNECT tunnel"""
        self.send_response(200)
        self.end_headers()
        
        try:
            host, port = self.path.split(':')
            port = int(port)
            
            target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_sock.connect((host, port))
            
            client_sock = self.connection
            
            # Forward data both ways
            threading.Thread(target=self._forward_data, args=(client_sock, target_sock), daemon=True).start()
            threading.Thread(target=self._forward_data, args=(target_sock, client_sock), daemon=True).start()
            
            while True:
                time.sleep(0.1)
        except Exception as e:
            pass
    
    def _forward_data(self, src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.send(data)
        except:
            pass
    
    def do_GET(self):
        self._handle_request()
    
    def do_POST(self):
        self._handle_request()
    
    def do_PUT(self):
        self._handle_request()
    
    def do_DELETE(self):
        self._handle_request()
    
    def do_PATCH(self):
        self._handle_request()
    
    def do_OPTIONS(self):
        self._handle_request()
    
    def _handle_request(self):
        """Handle all HTTP requests dynamically"""
        try:
            parsed = urlparse(self.path)
            host = self.headers.get('Host', '')
            
            # Construct full URL
            if self.path.startswith('http'):
                url = self.path
            else:
                url = f"https://{host}{self.path}"
            
            # Get request body
            body = None
            if self.command in ['POST', 'PUT', 'PATCH']:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    body = self.rfile.read(content_length)
            
            # Extract UID
            uid = None
            if 'uid' in parsed.query:
                uid = parsed.query.split('uid=')[1].split('&')[0]
            elif body:
                try:
                    body_str = body.decode('utf-8', errors='ignore')
                    if 'uid=' in body_str:
                        uid = body_str.split('uid=')[1].split('&')[0]
                except:
                    pass
            
            # Extract path for discovery
            path = parsed.path
            
            # Discover endpoint
            endpoint_info = discover_endpoint(url, self.command, path)
            
            # Check for JWT token
            auth = self.headers.get('Authorization', '')
            token = None
            if auth and auth.startswith('Bearer '):
                token = auth.replace('Bearer ', '')
                log(f"🔑 JWT Token Captured from: {path}", Colors.PURPLE)
                save_token(token, url, uid)
            
            # Create packet
            self.packet_counter += 1
            packet = {
                "id": self.packet_counter,
                "timestamp": datetime.now().isoformat(),
                "method": self.command,
                "url": url,
                "path": path,
                "host": host,
                "uid": uid,
                "token": token if token else None,
                "headers": dict(self.headers),
                "body_hex": body.hex() if body else None,
                "body_text": body.decode('utf-8', errors='ignore') if body else None,
                "endpoint_type": endpoint_info['type'] if endpoint_info else "unknown",
                "is_freefire": self._is_freefire(url)
            }
            
            # Save packet
            save_capture(packet)
            
            # Save payload for gacha/switch
            if body and (packet['endpoint_type'] in ['gacha', 'switch']):
                save_payload(body, url, uid)
                log(f"📦 Payload saved for: {path}", Colors.BLUE)
            
            # Log
            log(f"📡 [{packet['id']}] {self.command} {path} [{packet['endpoint_type']}]", Colors.CYAN)
            
            # Forward request
            self._forward_request(url, body, uid)
            
        except Exception as e:
            log(f"❌ Error: {e}", Colors.RED)
            self.send_error(500)
    
    def _is_freefire(self, url):
        """Check if URL is from Free Fire"""
        domains = ['garena', 'ggpolarbear', 'freefire', 'ggblueshark', 'connect.garena']
        return any(domain in url.lower() for domain in domains)
    
    def _forward_request(self, url, body, uid):
        """Forward request to actual server"""
        try:
            # Build headers
            headers = {k: v for k, v in self.headers.items()}
            headers.pop('Host', None)
            headers.pop('Proxy-Connection', None)
            
            # Forward request
            response = requests.request(
                method=self.command,
                url=url,
                headers=headers,
                data=body,
                verify=False,
                timeout=30,
                allow_redirects=False
            )
            
            # Log response
            log(f"📥 Response: {response.status_code} ({len(response.content)} bytes)", Colors.GREEN)
            
            # Check for item IDs in response
            if response.content:
                try:
                    text = response.content.decode('utf-8', errors='ignore')
                    numbers = re.findall(r'\b(\d{9})\b', text)
                    if numbers:
                        log(f"💎 Found Item IDs: {numbers}", Colors.YELLOW)
                        with open(f"{CAPTURE_DIR}/item_ids.txt", 'a') as f:
                            f.write(f"{datetime.now().isoformat()} | {url}\n")
                            for num in numbers:
                                f.write(f"  - {num}\n")
                            f.write("\n")
                except:
                    pass
            
            # Send response back
            self.send_response(response.status_code)
            for key, value in response.headers.items():
                if key.lower() not in ['content-encoding', 'transfer-encoding', 'content-length']:
                    self.send_header(key, value)
            self.end_headers()
            
            if response.content:
                self.wfile.write(response.content)
                
        except Exception as e:
            log(f"❌ Forward error: {e}", Colors.RED)
            self.send_error(502)

# =============================================================================
# DASHBOARD
# =============================================================================

def start_dashboard():
    """Start the dashboard server"""
    from flask import Flask, jsonify
    
    dash_app = Flask(__name__)
    
    @dash_app.route('/')
    def dashboard():
        return render_dashboard()
    
    @dash_app.route('/api/endpoints')
    def get_endpoints():
        return jsonify(ENDPOINTS)
    
    @dash_app.route('/api/captured')
    def get_captured():
        # Get recent captures
        files = os.listdir(CAPTURE_DIR)
        packets = []
        for f in sorted(files, reverse=True)[:50]:
            if f.endswith('.json') and f.startswith('packet_'):
                try:
                    with open(f"{CAPTURE_DIR}/{f}", 'r') as file:
                        packets.append(json.load(file))
                except:
                    pass
        return jsonify({
            "count": len(packets),
            "data": packets
        })
    
    def render_dashboard():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🔥 Free Fire Endpoint Discovery</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: 'Segoe UI', Arial; background: #0a0e1a; color: #c0d0e0; padding: 20px; }
                .header { background: #1a1f35; padding: 20px; border-radius: 12px; border: 1px solid #2a3a5a; margin-bottom: 20px; }
                .header h1 { background: linear-gradient(90deg, #00d4ff, #7b2ffc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
                .card { background: #111a2e; border: 1px solid #1e2d4a; border-radius: 8px; padding: 15px; }
                .card h3 { color: #00d4ff; margin-bottom: 10px; }
                .endpoint { background: #0a0e1a; padding: 8px; border-radius: 4px; margin: 4px 0; font-size: 12px; }
                .method { display: inline-block; padding: 1px 8px; border-radius: 3px; font-size: 10px; font-weight: bold; margin-right: 6px; }
                .method-GET { background: #1a4a3a; color: #4ae0a0; }
                .method-POST { background: #1a3a5a; color: #4ac0e0; }
                .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px; margin-left: 4px; }
                .badge-gacha { background: #4a1a2a; color: #e06080; }
                .badge-auth { background: #2a1a4a; color: #d080e0; }
                .badge-switch { background: #1a4a4a; color: #60e0e0; }
                .badge-data { background: #1a2a4a; color: #6080e0; }
                .badge-unknown { background: #3a3a3a; color: #888; }
                .stats { display: flex; gap: 15px; flex-wrap: wrap; margin: 10px 0; }
                .stats span { background: #1a253f; padding: 4px 14px; border-radius: 16px; font-size: 12px; }
                .stats .num { color: #00d4ff; font-weight: bold; }
                .auto-refresh { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔥 Free Fire Endpoint Discovery</h1>
                <div class="stats" id="stats"></div>
                <div class="auto-refresh">
                    <span>Auto-refresh: <span id="autoStatus">ON</span></span>
                    <span id="packetCount">📦 Packets: 0</span>
                </div>
            </div>
            <div class="grid">
                <div class="card">
                    <h3>🎯 Discovered Endpoints</h3>
                    <div id="endpoints"></div>
                </div>
                <div class="card">
                    <h3>📦 Recent Packets</h3>
                    <div id="packets"></div>
                </div>
            </div>
            <script>
                let autoRefresh = true;
                
                async function refresh() {
                    try {
                        // Get endpoints
                        const e = await fetch('/api/endpoints');
                        const endpoints = await e.json();
                        
                        // Get packets
                        const p = await fetch('/api/captured');
                        const packets = await p.json();
                        
                        updateUI(endpoints, packets);
                    } catch(e) { console.error(e); }
                }
                
                function updateUI(endpoints, packets) {
                    // Stats
                    const stats = document.getElementById('stats');
                    const counts = endpoints.by_type || {};
                    stats.innerHTML = `
                        <span>🎯 Total: <span class="num">${endpoints.discovered?.length || 0}</span></span>
                        <span>🎰 Gacha: <span class="num">${counts.gacha?.length || 0}</span></span>
                        <span>🔑 Auth: <span class="num">${counts.auth?.length || 0}</span></span>
                        <span>🔄 Switch: <span class="num">${counts.switch?.length || 0}</span></span>
                        <span>📦 Packets: <span class="num">${packets.count || 0}</span></span>
                    `;
                    
                    // Endpoints
                    const epDiv = document.getElementById('endpoints');
                    const eps = endpoints.discovered || [];
                    if (eps.length === 0) {
                        epDiv.innerHTML = '<div style="color:#667a9a;font-size:13px;">No endpoints discovered yet...</div>';
                    } else {
                        epDiv.innerHTML = eps.slice().reverse().slice(0, 20).map(ep => `
                            <div class="endpoint">
                                <span class="method method-${ep.method}">${ep.method}</span>
                                ${ep.path}
                                <span class="badge badge-${ep.type}">${ep.type}</span>
                            </div>
                        `).join('');
                    }
                    
                    // Packets
                    const pDiv = document.getElementById('packets');
                    const pkts = packets.data || [];
                    if (pkts.length === 0) {
                        pDiv.innerHTML = '<div style="color:#667a9a;font-size:13px;">Waiting for packets...</div>';
                    } else {
                        pDiv.innerHTML = pkts.slice(0, 15).map(p => `
                            <div class="endpoint" style="font-size:11px;">
                                ${p.method} ${p.path}
                                ${p.token ? '🔑' : ''}
                                ${p.endpoint_type ? `<span class="badge badge-${p.endpoint_type}">${p.endpoint_type}</span>` : ''}
                            </div>
                        `).join('');
                    }
                }
                
                setInterval(() => { if(autoRefresh) refresh(); }, 2000);
                refresh();
            </script>
        </body>
        </html>
        '''
    
    dash_app.run(host='0.0.0.0', port=5001)

# =============================================================================
# MAIN PROXY
# =============================================================================

def start_proxy():
    """Start the dynamic proxy server"""
    log("🚀 Starting Dynamic Free Fire Proxy...", Colors.CYAN)
    log(f"📁 Captures saved to: {CAPTURE_DIR}", Colors.GREEN)
    log("🌐 Discovering endpoints automatically...", Colors.YELLOW)
    
    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"
    
    log(f"📡 Proxy running on: {local_ip}:8080", Colors.PURPLE)
    log(f"📊 Dashboard: http://localhost:5001", Colors.BLUE)
    log("", Colors.WHITE)
    log("📱 Set Android proxy to:", Colors.YELLOW)
    log(f"   Host: {local_ip}", Colors.WHITE)
    log("   Port: 8080", Colors.WHITE)
    log("", Colors.WHITE)
    log("🔍 Waiting for Free Fire traffic...", Colors.CYAN)
    log("Press Ctrl+C to stop", Colors.RED)
    
    try:
        server = HTTPServer(('0.0.0.0', 8080), DynamicProxyHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        log("👋 Stopping proxy...", Colors.RED)
    except Exception as e:
        log(f"❌ Error: {e}", Colors.RED)

# =============================================================================
# MAIN
# =============================================================================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════════╗
{Colors.CYAN}║                                                                   ║
{Colors.CYAN}║  {Colors.PINK}██████╗ ██╗   ██╗███╗   ██╗ █████╗ ███╗   ███╗██╗ ██████╗{Colors.CYAN}   ║
{Colors.CYAN}║  {Colors.PINK}██╔══██╗╚██╗ ██╔╝████╗  ██║██╔══██╗████╗ ████║██║██╔════╝{Colors.CYAN}   ║
{Colors.CYAN}║  {Colors.PINK}██║  ██║ ╚████╔╝ ██╔██╗ ██║███████║██╔████╔██║██║██║     {Colors.CYAN}   ║
{Colors.CYAN}║  {Colors.PINK}██║  ██║  ╚██╔╝  ██║╚██╗██║██╔══██║██║╚██╔╝██║██║██║     {Colors.CYAN}   ║
{Colors.CYAN}║  {Colors.PINK}██████╔╝   ██║   ██║ ╚████║██║  ██║██║ ╚═╝ ██║██║╚██████╗{Colors.CYAN}   ║
{Colors.CYAN}║  {Colors.PINK}╚═════╝    ╚═╝   ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝ ╚═════╝{Colors.CYAN}   ║
{Colors.CYAN}║                                                                   ║
{Colors.CYAN}╠═══════════════════════════════════════════════════════════════════╣
{Colors.CYAN}║  {Colors.PINK}🔥 FREE FIRE ENDPOINT DISCOVERY PROXY 🔥             {Colors.CYAN}║
{Colors.CYAN}║  {Colors.PURPLE}📡 Auto-discovers ALL Free Fire endpoints           {Colors.CYAN}║
{Colors.CYAN}║  {Colors.PURPLE}🎯 No hardcoded endpoints needed                     {Colors.CYAN}║
{Colors.CYAN}╚═══════════════════════════════════════════════════════════════════╝{Colors.END}
    """)
    
    # Start dashboard in a separate thread
    dash_thread = threading.Thread(target=start_dashboard, daemon=True)
    dash_thread.start()
    
    # Start proxy (main thread)
    start_proxy()

if __name__ == '__main__':
    main()
