import os
import sys
import json
import socket
import subprocess
import psutil
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

class ServerManager:
    def __init__(self):
        self.servers = {}
        self.next_id = 1
        
    def launch_server(self, name, template, port, cwd, html_file=None):
        """Launch a new server based on template"""
        server_id = str(self.next_id)
        self.next_id += 1
        
        try:
            if template == "py-http":
                cmd = [sys.executable, "-m", "http.server", str(port)]
            elif template == "node-index":
                # Create simple Node.js server
                server_script = self._create_node_server_script(port)
                script_path = os.path.join(cwd, "server.js")
                with open(script_path, 'w') as f:
                    f.write(server_script)
                cmd = ["node", "server.js"]
            else:
                cmd = [sys.executable, "-m", "http.server", str(port)]
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            server_info = {
                "id": server_id,
                "name": name,
                "template": template,
                "port": port,
                "cwd": cwd,
                "pid": process.pid,
                "process": process,
                "start_time": datetime.now().isoformat(),
                "status": "running"
            }
            
            self.servers[server_id] = server_info
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_server,
                args=(server_id, process),
                daemon=True
            )
            monitor_thread.start()
            
            return {"ok": True, "server_id": server_id, "pid": process.pid}
            
        except Exception as e:
            return {"ok": False, "error": f"Failed to launch server: {str(e)}"}
    
    def _create_node_server_script(self, port):
        """Create a basic Node.js server script"""
        return f'''
const http = require('http');
const fs = require('fs');
const path = require('path');

const server = http.createServer((req, res) => {{
    let filePath = '.' + req.url;
    if (filePath === './') filePath = './index.html';
    
    const extname = path.extname(filePath);
    let contentType = 'text/html';
    
    switch (extname) {{
        case '.js': contentType = 'text/javascript'; break;
        case '.css': contentType = 'text/css'; break;
        case '.json': contentType = 'application/json'; break;
        case '.png': contentType = 'image/png'; break;
        case '.jpg': contentType = 'image/jpg'; break;
    }}
    
    fs.readFile(filePath, (error, content) => {{
        if (error) {{
            res.writeHead(404);
            res.end('File not found');
        }} else {{
            res.writeHead(200, {{ 'Content-Type': contentType }});
            res.end(content, 'utf-8');
        }}
    }});
}});

server.listen({port}, () => {{
    console.log('Server running at http://localhost:{port}/');
}});
'''
    
    def _monitor_server(self, server_id, process):
        """Monitor server process and update status"""
        process.wait()
        if server_id in self.servers:
            self.servers[server_id]["status"] = "stopped"
    
    def stop_server(self, server_id):
        """Stop a running server"""
        if server_id in self.servers:
            server = self.servers[server_id]
            try:
                process = server["process"]
                process.terminate()
                process.wait(timeout=5)
                server["status"] = "stopped"
                return {"ok": True}
            except Exception as e:
                return {"ok": False, "error": f"Failed to stop server: {str(e)}"}
        return {"ok": False, "error": "Server not found"}
    
    def list_servers(self):
        """Get list of all servers"""
        servers_list = []
        for server_id, server in self.servers.items():
            servers_list.append({
                "id": server_id,
                "name": server["name"],
                "template": server["template"],
                "port": server["port"],
                "pid": server["pid"],
                "status": server["status"],
                "start_time": server["start_time"]
            })
        return {"ok": True, "servers": servers_list}

class PortScanner:
    @staticmethod
    def scan_ports():
        """Scan for active ports and their processes"""
        active_ports = []
        
        try:
            # Get all network connections
            connections = psutil.net_connections()
            
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr:
                    port_info = {
                        "port": conn.laddr.port,
                        "protocol": "TCP",
                        "status": "listening",
                        "pid": conn.pid,
                        "processName": "",
                        "service": PortScanner._get_service_name(conn.laddr.port, conn.pid)
                    }
                    
                    # Get process info
                    if conn.pid:
                        try:
                            process = psutil.Process(conn.pid)
                            port_info["processName"] = process.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            port_info["processName"] = "Unknown"
                    
                    active_ports.append(port_info)
            
            return {"ok": True, "ports": active_ports}
            
        except Exception as e:
            return {"ok": False, "error": f"Scan error: {str(e)}"}
    
    @staticmethod
    def _get_service_name(port, pid):
        """Get better service names based on port and process"""
        service_map = {
            80: "HTTP Web Server", 
            443: "HTTPS Web Server", 
            21: "FTP Server",
            22: "SSH Server", 
            23: "Telnet Server",
            25: "SMTP Email Server", 
            53: "DNS Server", 
            110: "POP3 Email",
            143: "IMAP Email", 
            993: "IMAPS Secure Email",
            995: "POP3S Secure Email", 
            3306: "MySQL Database",
            5432: "PostgreSQL Database", 
            27017: "MongoDB Database",
            6379: "Redis Cache", 
            9200: "Elasticsearch",
            3000: "Node.js Development", 
            5000: "Python Flask Development",
            8000: "Development Server", 
            8080: "Web Proxy/Alternative HTTP",
            8443: "Alternative HTTPS", 
            5502: "Port Scanner API"
        }
        
        # Default names based on common patterns
        default_names = {
            "python.exe": "Python Application",
            "node.exe": "Node.js Server", 
            "java.exe": "Java Application",
            "nginx.exe": "Nginx Web Server",
            "apache.exe": "Apache Web Server",
            "mysql.exe": "MySQL Database",
            "postgres.exe": "PostgreSQL Database",
            "steam.exe": "Steam Gaming",
            "discord.exe": "Discord App"
        }
        
        # Try to get service name from port first
        service_name = service_map.get(port, "Network Service")
        
        # If unknown, try to guess from process name
        if service_name == "Network Service" and pid:
            try:
                process = psutil.Process(pid)
                process_name = process.name().lower()
                for proc_pattern, service_desc in default_names.items():
                    if proc_pattern.replace('.exe', '') in process_name:
                        service_name = service_desc
                        break
            except:
                pass
                
        return service_name
    
    @staticmethod
    def kill_process(pid):
        """Kill a process by PID"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)
            return {"ok": True}
        except psutil.NoSuchProcess:
            return {"ok": False, "error": "Process not found"}
        except psutil.AccessDenied:
            return {"ok": False, "error": "Access denied. Run as administrator."}
        except Exception as e:
            return {"ok": False, "error": f"Failed to kill process: {str(e)}"}

class APIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.scanner = PortScanner()
        self.server_manager = ServerManager()
        super().__init__(*args, **kwargs)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_cors_headers()
        self.send_response(200)
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-PSM-Token')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def do_GET(self):
        """Handle GET requests"""
        path = self.path
        
        try:
            if path == '/health':
                self.send_json_response({"status": "ok", "service": "Port Scanner & Server Manager"})
            
            elif path == '/api/ports/scan':
                result = self.scanner.scan_ports()
                self.send_json_response(result)
            
            elif path == '/api/servers/list':
                result = self.server_manager.list_servers()
                self.send_json_response(result)
            
            elif path == '/' or path == '/index.html' or path == '':
                # Serve the HTML file
                self.serve_html()
            
            else:
                self.send_error(404, "Endpoint not found")
                
        except Exception as e:
            self.send_json_response({"ok": False, "error": str(e)}, 500)
    
    def do_POST(self):
        """Handle POST requests"""
        path = self.path
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8')) if content_length > 0 else {}
            
            if path == '/api/ports/kill':
                pid = data.get('pid')
                if not pid:
                    self.send_json_response({"ok": False, "error": "PID required"}, 400)
                    return
                
                result = self.scanner.kill_process(pid)
                self.send_json_response(result)
            
            elif path == '/api/servers/launch':
                required_fields = ['name', 'template', 'cwd']
                for field in required_fields:
                    if field not in data:
                        self.send_json_response({"ok": False, "error": f"Missing required field: {field}"}, 400)
                        return
                
                result = self.server_manager.launch_server(
                    name=data['name'],
                    template=data['template'],
                    port=data.get('port', 8000),
                    cwd=data['cwd'],
                    html_file=data.get('htmlFile')
                )
                self.send_json_response(result)
            
            elif path == '/api/servers/stop':
                server_id = data.get('id')
                if not server_id:
                    self.send_json_response({"ok": False, "error": "Server ID required"}, 400)
                    return
                
                result = self.server_manager.stop_server(server_id)
                self.send_json_response(result)
            
            else:
                self.send_error(404, "Endpoint not found")
                
        except Exception as e:
            self.send_json_response({"ok": False, "error": str(e)}, 500)
    
    def serve_html(self):
        """Serve the HTML file"""
        try:
            with open('index.html', 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
    
    def send_json_response(self, data, status=200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        return

def main():
    host = '127.0.0.1'
    port = 5502
    
    print(f"🚀 Starting Port Scanner & Server Manager...")
    print(f"📍 Full Application: http://{host}:{port}")
    print(f"📊 Open this URL in your browser: http://{host}:{port}")
    print(f"⚡ Features: Port scanning, process management, server deployment")
    print(f"💡 Run as Administrator for full process control")
    print("Press Ctrl+C to stop the server")
    
    try:
        server = HTTPServer((host, port), APIHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == '__main__':
    main()