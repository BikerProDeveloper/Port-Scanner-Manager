from flask import Flask, request, jsonify
import psutil
import socket
import threading
import subprocess
import time
import os

app = Flask(__name__)

# --------- CORS (no external package needed) ---------
@app.after_request
def add_cors_headers(resp):
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

# --------- Helpers ---------
def port_ranges(label: str):
    if label == "common":
        return range(1, 1025)
    if label == "extended":
        return range(1, 10001)
    return range(1, 65536)

def collect_port_owners():
    owners = {}
    try:
        for c in psutil.net_connections(kind='inet'):
            try:
                laddr = c.laddr
            except Exception:
                continue
            if not laddr:
                continue
            port = getattr(laddr, "port", None) if hasattr(laddr, "port") else (laddr[1] if isinstance(laddr, tuple) and len(laddr) > 1 else None)
            if port is None:
                continue
            owners.setdefault(port, [])
            owners[port].append({"pid": c.pid, "status": c.status})
    except Exception:
        # Not fatal; may require admin privileges on some systems
        pass
    return owners

def try_connect(host: str, port: int, timeout: float = 0.2):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

# --------- Routes ---------
@app.route("/scan-ports", methods=["POST"])
def scan_ports():
    data = request.get_json(force=True) or {}
    rng = data.get("range", "common")
    scan_type = data.get("type", "tcp")  # UDP not implemented in this minimal server

    # Resolve range safely
    ports_to_scan = list(port_ranges(rng))

    # Guardrail: prevent huge scans from locking UI
    # Cap to first 2000 ports unless explicitly 'all'
    if rng != "all":
        ports_to_scan = ports_to_scan[:2000]

    owners = collect_port_owners()
    found = []
    lock = threading.Lock()

    def worker(p):
        if try_connect("127.0.0.1", p, timeout=0.15):
            info = {"port": p, "protocol": "TCP", "status": "OPEN", "pid": None, "processName": None}
            # Try to enrich with psutil
            cand = owners.get(p, [])
            pid = next((x["pid"] for x in cand if x.get("pid")), None)
            if pid:
                info["pid"] = pid
                try:
                    info["processName"] = psutil.Process(pid).name()
                except Exception:
                    pass
            with lock:
                found.append(info)

    threads = []
    for p in ports_to_scan:
        t = threading.Thread(target=worker, args=(p,), daemon=True)
        threads.append(t)
        t.start()
        if len(threads) % 200 == 0:
            for tt in threads[-200:]:
                tt.join()

    for t in threads:
        t.join()

    return jsonify({"ports": sorted(found, key=lambda x: x["port"])}), 200

@app.route("/kill-process", methods=["POST"])
def kill_process():
    data = request.get_json(force=True) or {}
    pid = data.get("pid")
    if not pid:
        return jsonify({"error": "pid required"}), 400
    try:
        p = psutil.Process(int(pid))
        p.terminate()
        try:
            p.wait(timeout=3)
        except psutil.TimeoutExpired:
            p.kill()
        return jsonify({"status": "terminated", "pid": pid}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/start-server", methods=["POST"])
def start_server():
    data = request.get_json(force=True) or {}
    typ = data.get("type")
    port = int(data.get("port", 0))
    directory = data.get("directory") or os.getcwd()
    file_ = data.get("file")

    try:
        if typ == "static":
            # Python simple HTTP server in chosen directory
            cmd = f'cmd /c "cd /d {directory} && python -m http.server {port}"'
        elif typ == "node":
            # Basic Node server; assumes file exists
            cmd = f'cmd /c "node {file_}"'
        elif typ == "python":
            # Flask app; assumes app file exists and binds to given port
            # You can customize app to read PORT env var
            env = os.environ.copy()
            env["PORT"] = str(port)
            subprocess.Popen(["python", file_], env=env)
            return jsonify({"status": "started", "type": typ, "port": port}), 200
        elif typ == "php":
            cmd = f'cmd /c "cd /d {directory} && php -S localhost:{port}"'
        else:
            return jsonify({"error": "unknown type"}), 400

        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        return jsonify({"status": "started", "type": typ, "port": port}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/launch-server", methods=["POST"])
def launch_server():
    # For parity with front-end, delegate to start-server
    return start_server()

@app.route("/system-stats", methods=["GET"])
def system_stats():
    try:
        cpu = psutil.cpu_percent(interval=0.2)
        mem = psutil.virtual_memory().percent
        active = 0
        try:
            active = sum(1 for c in psutil.net_connections(kind='inet') if getattr(getattr(c, "laddr", None), "port", None))
        except Exception:
            pass
        return jsonify({"cpu_usage": int(cpu), "memory_usage": int(mem), "active_ports": int(active)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Bind on all interfaces for localhost use and future LAN access
    app.run(host="0.0.0.0", port=5002)  # ← Change 5502 to 5002
