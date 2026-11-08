import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.parse
import webbrowser

from litewin import iso
from litewin import image
from litewin import packages
from litewin import privacy
from litewin import builder
from litewin import qemu
from litewin import version

LOG_BUFFER = []
BUILD_STATE = {
    "active": False,
    "progress": 0,
    "status": "Ready",
    "result": None,
    "error": None,
}


def add_log(msg):
    ts = time.strftime("%H:%M:%S")
    LOG_BUFFER.append(f"[{ts}] {msg}")


HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LiteWin — Windows, without the baggage</title>
  <style>
    :root {
      --bg: #121417;
      --card: #1c2026;
      --border: #2a313d;
      --primary: #0078d4;
      --primary-hover: #106ebe;
      --text: #e1e4e8;
      --muted: #8b949e;
      --accent: #2ea043;
      --danger: #da3633;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    .container { max-width: 960px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    .brand h1 { font-size: 26px; font-weight: 700; color: #fff; }
    .brand span { color: var(--muted); font-size: 14px; margin-left: 8px; }
    .version { background: var(--border); padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
    
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .card h2 { font-size: 16px; font-weight: 600; margin-bottom: 14px; color: #fff; }
    
    .row { display: flex; gap: 12px; margin-bottom: 12px; }
    input[type="text"], select {
      flex: 1;
      background: #0f1216;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 10px 14px;
      border-radius: 6px;
      font-size: 14px;
    }
    input[type="text"]:focus, select:focus { outline: none; border-color: var(--primary); }
    
    button {
      background: var(--primary);
      color: #fff;
      border: none;
      padding: 10px 18px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
      transition: background 0.15s;
    }
    button:hover { background: var(--primary-hover); }
    button.secondary { background: #28303d; color: var(--text); }
    button.secondary:hover { background: #353f4f; }
    button.action { background: var(--accent); padding: 12px 24px; font-size: 15px; }
    button.action:hover { background: #2c974b; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }

    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .box { background: #13171d; border: 1px solid var(--border); border-radius: 6px; padding: 14px; max-height: 280px; overflow-y: auto; }
    .item-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; }
    .item-row input[type="checkbox"] { accent-color: var(--primary); }
    .tag { font-size: 11px; padding: 2px 6px; border-radius: 4px; margin-left: 6px; }
    .tag-safe { background: rgba(46, 160, 67, 0.15); color: #3fb950; }
    .tag-essential { background: rgba(56, 139, 253, 0.15); color: #58a6ff; }

    #console {
      background: #0a0c0e;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 14px;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      font-size: 12px;
      height: 200px;
      overflow-y: auto;
      color: #7ee787;
      white-space: pre-wrap;
    }
    .status-msg { font-size: 13px; color: var(--muted); margin-top: 6px; }
    .success-msg { color: #3fb950; }
    .error-msg { color: #f85149; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <h1>LiteWin <span>Windows, without the baggage</span></h1>
      </div>
      <div class="version">v""" + version + """</div>
    </header>

    <div class="card">
      <h2>1. Source Windows 11 ISO</h2>
      <div class="row">
        <input type="text" id="isoPath" placeholder="/path/to/Windows11.iso" />
        <button onclick="inspectIso()">Inspect ISO</button>
      </div>
      <div class="status-msg" id="isoStatus">Select a Windows 11 installation ISO.</div>
      
      <div class="row" style="margin-top: 14px;">
        <select id="editionsList" disabled>
          <option>Select edition after inspecting ISO...</option>
        </select>
        <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer;">
          <input type="checkbox" id="singleEdition" /> Trim other editions
        </label>
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h2>2. Bloatware & App Removal</h2>
        <div class="row">
          <select id="profileSelect" onchange="applyProfile()">
            <option value="standard">Standard Profile (Recommended)</option>
            <option value="minimal">Minimal Profile (Only Third-Party Ads)</option>
          </select>
        </div>
        <div class="box" id="appsBox">Loading app catalog...</div>
      </div>

      <div class="card">
        <h2>3. Privacy & Telemetry</h2>
        <div class="box" id="privacyBox">Loading privacy rules...</div>
      </div>
    </div>

    <div class="card">
      <h2>4. Firefox-First Experience</h2>
      <div class="item-row">
        <input type="checkbox" id="ffEnable" checked />
        <label for="ffEnable"><strong>Install Mozilla Firefox silently during Windows Setup</strong></label>
      </div>
      <p style="font-size: 13px; color: var(--muted); margin-top: 4px;">
        Enforces telemetry opt-out policies and associates Firefox as default browser via OEM AppAssoc.xml.
      </p>
    </div>

    <div class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
        <h2>5. Build & Output</h2>
        <button class="action" id="buildBtn" onclick="startBuild()">Start LiteWin Build</button>
      </div>
      <div id="console">Ready to customize. Click 'Start LiteWin Build' to begin.</div>
      <div style="margin-top: 12px; display: flex; gap: 10px;">
        <button class="secondary" id="vmBtn" onclick="launchVm()" disabled>Test in QEMU VM</button>
      </div>
    </div>
  </div>

  <script>
    let appsData = [];
    let privacyData = [];
    let lastIsoInfo = null;

    async function init() {
      const resp = await fetch('/api/catalog');
      const data = await resp.json();
      appsData = data.apps || [];
      privacyData = data.privacy || [];
      if (data.default_iso) {
        document.getElementById('isoPath').value = data.default_iso;
      }
      renderApps();
      renderPrivacy();
      setInterval(pollLogs, 800);
    }

    function renderApps() {
      const box = document.getElementById('appsBox');
      box.innerHTML = '';
      appsData.forEach(app => {
        const row = document.createElement('div');
        row.className = 'item-row';
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.id = 'app_' + app.id;
        chk.checked = !!app['safe to remove'];
        chk.disabled = !app['safe to remove'];

        const lbl = document.createElement('label');
        lbl.htmlFor = chk.id;
        lbl.innerHTML = `${app.name} <span class="tag ${app['safe to remove'] ? 'tag-safe' : 'tag-essential'}">${app['safe to remove'] ? 'Safe' : 'Essential'}</span>`;
        row.appendChild(chk);
        row.appendChild(lbl);
        box.appendChild(row);
      });
    }

    function applyProfile() {
      const prof = document.getElementById('profileSelect').value;
      const minimalTargets = ["Clipchamp.Clipchamp", "Microsoft.BingNews", "Microsoft.MicrosoftSolitaireCollection", "Microsoft.MicrosoftOfficeHub", "Microsoft.Getstarted", "Microsoft.549981C3F5F10"];
      appsData.forEach(app => {
        const el = document.getElementById('app_' + app.id);
        if (el && !el.disabled) {
          if (prof === 'minimal') {
            el.checked = minimalTargets.includes(app.id);
          } else {
            el.checked = true;
          }
        }
      });
    }

    function renderPrivacy() {
      const box = document.getElementById('privacyBox');
      box.innerHTML = '';
      privacyData.forEach((rule, idx) => {
        const row = document.createElement('div');
        row.className = 'item-row';
        const chk = document.createElement('input');
        chk.type = 'checkbox';
        chk.id = 'priv_' + idx;
        chk.checked = true;

        const lbl = document.createElement('label');
        lbl.htmlFor = chk.id;
        lbl.innerHTML = `<strong>${rule.name}</strong><br><span style="color:#8b949e; font-size:11px;">${rule.description}</span>`;
        row.appendChild(chk);
        row.appendChild(lbl);
        box.appendChild(row);
      });
    }

    async function inspectIso() {
      const path = document.getElementById('isoPath').value.trim();
      const statusEl = document.getElementById('isoStatus');
      if (!path) {
        statusEl.textContent = 'Please enter an ISO path.';
        statusEl.className = 'status-msg error-msg';
        return;
      }
      statusEl.textContent = 'Inspecting ISO and querying editions...';
      statusEl.className = 'status-msg';

      const res = await fetch('/api/inspect', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({iso: path})
      });
      const data = await res.json();
      if (!data.valid) {
        statusEl.textContent = 'Error: ' + (data.error || 'Invalid Windows ISO');
        statusEl.className = 'status-msg error-msg';
        return;
      }

      lastIsoInfo = data;
      statusEl.textContent = `Valid Windows 11 ISO (${data.mb} MB, ${data.image_type.toUpperCase()}). Found ${data.editions.length} editions.`;
      statusEl.className = 'status-msg success-msg';

      const sel = document.getElementById('editionsList');
      sel.innerHTML = '';
      sel.disabled = false;
      data.editions.forEach(ed => {
        const opt = document.createElement('option');
        opt.value = ed.index;
        opt.textContent = `[${ed.index}] ${ed.name} (${ed.edition}) - ${ed.architecture}`;
        if (ed.name.toLowerCase().includes('pro')) opt.selected = true;
        sel.appendChild(opt);
      });
    }

    async function startBuild() {
      const path = document.getElementById('isoPath').value.trim();
      const edIndex = parseInt(document.getElementById('editionsList').value) || 1;
      const single = document.getElementById('singleEdition').checked;
      const prof = document.getElementById('profileSelect').value;

      document.getElementById('buildBtn').disabled = true;
      document.getElementById('console').textContent = 'Starting build...\\n';

      const res = await fetch('/api/build', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          iso: path,
          edition: edIndex,
          single_edition: single,
          profile: prof
        })
      });
      const data = await res.json();
      if (!data.started) {
        alert('Build failed to start: ' + data.error);
        document.getElementById('buildBtn').disabled = false;
      }
    }

    async function pollLogs() {
      const res = await fetch('/api/status');
      const data = await res.json();
      const con = document.getElementById('console');
      if (data.logs && data.logs.length > 0) {
        con.textContent = data.logs.join('\\n');
        con.scrollTop = con.scrollHeight;
      }
      if (data.active) {
        document.getElementById('buildBtn').disabled = true;
      } else {
        document.getElementById('buildBtn').disabled = false;
        if (data.result) {
          document.getElementById('vmBtn').disabled = false;
        }
      }
    }

    async function launchVm() {
      const res = await fetch('/api/vm', {method: 'POST'});
      const data = await res.json();
      if (data.launched) {
        alert('Launched QEMU VM (PID ' + data.pid + ')');
      } else {
        alert('Failed to launch VM: ' + data.error);
      }
    }

    window.onload = init;
  </script>
</body>
</html>
"""


class WebHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress standard HTTP terminal spam

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
        elif parsed.path == "/api/catalog":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            dl_iso = os.path.expanduser("~/Downloads/Windows11_Client_x64_en-us_26300_9457.iso")
            payload = {
                "apps": packages.loadapps(),
                "privacy": privacy.loadprivacy(),
                "default_iso": dl_iso if os.path.isfile(dl_iso) else "",
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        elif parsed.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = dict(BUILD_STATE)
            resp["logs"] = LOG_BUFFER[-100:]
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        clen = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(clen)
        data = json.loads(body.decode("utf-8")) if body else {}

        if parsed.path == "/api/inspect":
            iso_p = data.get("iso", "").strip()
            if not iso_p or not os.path.isfile(iso_p):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"valid": False, "error": "file not found"}).encode("utf-8"))
                return

            v = iso.verify(iso_p)
            if not v.get("valid"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"valid": False, "error": str(v.get("error") or v.get("missing files"))}).encode("utf-8"))
                return

            eds = image.editions(iso_p)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "valid": True,
                "mb": v["mb"],
                "image_type": v["image type"],
                "editions": eds,
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif parsed.path == "/api/build":
            if BUILD_STATE["active"]:
                self.send_response(400)
                self.end_headers()
                return

            BUILD_STATE["active"] = True
            BUILD_STATE["error"] = None
            BUILD_STATE["result"] = None
            LOG_BUFFER.clear()

            iso_p = data.get("iso")
            ed_idx = data.get("edition", 1)
            single = data.get("single_edition", False)
            prof = data.get("profile", "standard")

            def worker():
                try:
                    add_log(f"Starting LiteWin build from: {iso_p}")
                    res = builder.build(
                        src_iso=iso_p,
                        profile=prof,
                        edition_idx=ed_idx,
                        single_edition=single,
                    )
                    add_log("Build completed successfully!")
                    add_log(f"Output ISO: {res['iso path']}")
                    add_log(f"Audit report: {res['audit report']}")
                    BUILD_STATE["result"] = res
                except Exception as ex:
                    add_log(f"Build failed: {ex}")
                    BUILD_STATE["error"] = str(ex)
                finally:
                    BUILD_STATE["active"] = False

            t = threading.Thread(target=worker, daemon=True)
            t.start()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"started": True}).encode("utf-8"))

        elif parsed.path == "/api/vm":
            target = None
            if BUILD_STATE.get("result"):
                target = BUILD_STATE["result"]["iso path"]
            if not target:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"launched": False, "error": "No built ISO ready"}).encode("utf-8"))
                return

            try:
                vm_res = qemu.testrun(target, ram="4G", cpus=4, dry=False)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"launched": True, "pid": vm_res["pid"]}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"launched": False, "error": str(e)}).encode("utf-8"))


def launch(port=5000):
    server = socketserver.TCPServer(("127.0.0.1", port), WebHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"[*] LiteWin GUI running at: {url}")
    threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
