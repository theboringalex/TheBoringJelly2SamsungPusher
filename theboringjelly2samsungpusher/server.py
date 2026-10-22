#!/usr/bin/env python3
"""Kleine Ingress-Oberfläche für TheBoringJelly2SamsungPusher (nur Standardbibliothek)."""
import json
import os
import re
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    # eigene Variante: ThreadingHTTPServer gibt es erst ab Python 3.7
    daemon_threads = True

OPTIONS_FILE = os.environ.get("OPTIONS_FILE", "/data/options.json")
INSTALL_SCRIPT = os.environ.get("INSTALL_SCRIPT", "/app/install.sh")
BIND = os.environ.get("BIND", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8099"))
# Ingress-Anfragen kommen ausschließlich vom Supervisor (172.30.32.2).
ALLOWED_CLIENTS = {
    c.strip()
    for c in os.environ.get("ALLOWED_CLIENTS", "172.30.32.2,127.0.0.1").split(",")
    if c.strip()
}
MAX_LOG_LINES = 2000

VARIANTS = [
    ("Jellyfin", "Jellyfin – neueste stabile Web-Version"),
    ("Jellyfin-10.11.z", "Jellyfin-10.11.z – für Server 10.11.x"),
    ("Jellyfin-12.z", "Jellyfin-12.z – für Server 12.x"),
    ("Jellyfin-master", "Jellyfin-master – Entwicklungsstand (instabil)"),
    ("Jellyfin-prerelease", "Jellyfin-prerelease – Vorabversion"),
    ("Jellyfin-secondary", "Jellyfin-secondary – zweite App mit eigener App-ID (zweites Konto)"),
    ("Jellyfin-OblongIcon", "Jellyfin-OblongIcon – Querformat-Icon für TVs, die es verlangen"),
    ("Jellyfin-SmartHub", "Jellyfin-SmartHub – Samsung Smart Hub Preview"),
    ("Jellyfin-OSA", "Jellyfin-OSA – OblongIcon + SmartHub + experimenteller AVPlay-Player"),
    ("Jellyfin-TrailerFix", "Jellyfin-TrailerFix – YouTube-Trailer (Fehler 153) auf neuen Tizen-Versionen"),
    ("Jellyfin-GrayFix", "Jellyfin-GrayFix – graue Balken über/unter dem Video"),
    ("Jellyfin-10.11.z-OSA", "10.11.z + OSA"),
    ("Jellyfin-10.11.z-TrailerFix", "10.11.z + TrailerFix"),
    ("Jellyfin-12.z-OSA", "12.z + OSA"),
    ("Jellyfin-12.z-TrailerFix", "12.z + TrailerFix"),
]

IP_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
VARIANT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
TAG_RE = re.compile(r"^[A-Za-z0-9._-]{0,64}$")
URL_RE = re.compile(r"^https?://[^\s\"'<>]{1,200}$")


def load_options():
    try:
        with open(OPTIONS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        data = {}
    return {
        "tv_ip": (data.get("tv_ip") or "").strip(),
        "build_variant": data.get("build_variant") or "Jellyfin",
        "jellyfin_url": (data.get("jellyfin_url") or "").strip(),
        "release_tag": (data.get("release_tag") or "").strip(),
        "uninstall_first": bool(data.get("uninstall_first", False)),
        "launch_after_install": bool(data.get("launch_after_install", True)),
        "auto_install": bool(data.get("auto_install", False)),
        "certificate_password": data.get("certificate_password") or "",
        "distributor_password": data.get("distributor_password") or "",
    }


def valid_ip(value):
    m = IP_RE.match(value or "")
    return bool(m) and all(int(g) <= 255 for g in m.groups())


class Job:
    """Führt genau einen Installationslauf zur Zeit aus und puffert die Log-Zeilen."""

    def __init__(self):
        self.lock = threading.Lock()
        self.lines = []
        self.running = False
        self.exit_code = None
        self.started = None
        self.secrets = []

    def _append(self, line):
        for secret in self.secrets:
            if secret:
                line = line.replace(secret, "***")
        with self.lock:
            self.lines.append(line)
            if len(self.lines) > MAX_LOG_LINES:
                del self.lines[: len(self.lines) - MAX_LOG_LINES]
        print(line, flush=True)

    def start(self, params, secrets):
        with self.lock:
            if self.running:
                return False, "Es läuft bereits eine Installation."
            self.running = True
            self.exit_code = None
            self.lines = []
            self.started = time.time()
            self.secrets = [s for s in secrets if s]
        env = dict(os.environ)
        env.update(
            {
                "TV_IP": params["tv_ip"],
                "BUILD_VARIANT": params["build_variant"],
                "RELEASE_TAG": params["release_tag"],
                "JELLYFIN_URL": params["jellyfin_url"],
                "UNINSTALL_FIRST": "true" if params["uninstall_first"] else "false",
                "LAUNCH_AFTER": "true" if params["launch_after_install"] else "false",
                "CERT_PASSWORD": secrets[0],
                "DISTRIBUTOR_PASSWORD": secrets[1],
            }
        )
        threading.Thread(target=self._run, args=(env,), daemon=True).start()
        return True, ""

    def _run(self, env):
        code = 1
        try:
            proc = subprocess.Popen(
                ["bash", INSTALL_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
            )
            for raw in proc.stdout:
                self._append(raw.decode("utf-8", "replace").rstrip("\r\n"))
            code = proc.wait()
        except Exception as exc:  # noqa: BLE001 - jede Störung soll im Log landen
            self._append("FEHLER: Installationsskript konnte nicht gestartet werden: %s" % exc)
        finally:
            with self.lock:
                self.exit_code = code
                self.running = False

    def snapshot(self):
        with self.lock:
            return {
                "running": self.running,
                "exit_code": self.exit_code,
                "log": "\n".join(self.lines),
                "started": self.started,
            }


JOB = Job()


def parse_params(payload, defaults):
    """Prüft die Formulareingaben strikt, bevor sie an das Skript gehen."""
    tv_ip = str(payload.get("tv_ip", "")).strip()
    variant = str(payload.get("build_variant", defaults["build_variant"])).strip()
    tag = str(payload.get("release_tag", "")).strip()
    url = str(payload.get("jellyfin_url", "")).strip()
    if not valid_ip(tv_ip):
        return None, "Bitte eine gültige IPv4-Adresse des TV eingeben."
    if not VARIANT_RE.match(variant):
        return None, "Ungültige Build-Variante."
    if not TAG_RE.match(tag):
        return None, "Ungültiger Release-Tag."
    if url and not URL_RE.match(url):
        return None, "Ungültige Jellyfin-URL (z. B. http://192.168.1.10:8096)."
    return {
        "tv_ip": tv_ip,
        "build_variant": variant,
        "release_tag": tag,
        "jellyfin_url": url,
        "uninstall_first": bool(payload.get("uninstall_first", False)),
        "launch_after_install": bool(payload.get("launch_after_install", True)),
    }, ""


def build_page():
    options = "\n".join(
        '<option value="%s">%s</option>' % (value, label) for value, label in VARIANTS
    )
    return PAGE.replace("%%VARIANT_OPTIONS%%", options)


PAGE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TheBoringJelly2SamsungPusher</title>
<style>
:root{color-scheme:light dark;--bg:#fff;--fg:#1b1f23;--muted:#59636e;--card:#f6f8fa;--line:#d1d9e0;--accent:#0b7fb0;--ok:#1a7f37;--err:#cf222e;--logbg:#0d1117;--logfg:#d0d7de}
@media (prefers-color-scheme:dark){:root{--bg:#111418;--fg:#e6edf3;--muted:#9198a1;--card:#1a1f26;--line:#30363d;--accent:#3fb6e8;--ok:#3fb950;--err:#f85149}}
*{box-sizing:border-box}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:760px;margin:0 auto}
h1{font-size:1.3rem;margin:0 0 4px}
p.sub{margin:0 0 16px;color:var(--muted)}
form{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;display:grid;gap:14px}
label{display:grid;gap:4px;font-weight:600}
label small{font-weight:400;color:var(--muted)}
input[type=text],select{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);font:inherit}
.check{display:flex;gap:8px;align-items:flex-start;font-weight:400}
.check input{margin-top:4px}
button{padding:10px 16px;border:0;border-radius:8px;background:var(--accent);color:#fff;font:inherit;font-weight:600;cursor:pointer}
button:disabled{opacity:.55;cursor:not-allowed}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.badge{padding:3px 10px;border-radius:999px;border:1px solid var(--line);font-size:.85rem}
.badge.run{color:var(--accent);border-color:var(--accent)}
.badge.ok{color:var(--ok);border-color:var(--ok)}
.badge.err{color:var(--err);border-color:var(--err)}
#msg{color:var(--err);min-height:1.2em}
pre{margin:16px 0 0;padding:12px;background:var(--logbg);color:var(--logfg);border-radius:10px;overflow:auto;max-height:55vh;font:12.5px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}
details{margin-top:4px}
summary{cursor:pointer;color:var(--muted)}
</style>
</head>
<body>
<main>
<h1>Jellyfin auf Samsung-TV installieren</h1>
<p class="sub">Developer Mode am TV muss aktiv sein und als „Host PC IP“ die IP deines Home-Assistant-Hosts enthalten.</p>
<form id="f">
  <label>IP-Adresse des TV
    <input type="text" id="tv_ip" inputmode="decimal" autocomplete="off" placeholder="192.168.1.50" required>
  </label>
  <label>Build-Variante
    <select id="build_variant">%%VARIANT_OPTIONS%%</select>
    <small>Die Web-Version muss zur Jellyfin-Server-Version passen. Mit der Server-URL unten wählt der Installer automatisch.</small>
  </label>
  <details>
    <summary>Erweitert</summary>
    <div style="display:grid;gap:14px;margin-top:12px">
      <label>Jellyfin-Server-URL (optional)
        <input type="text" id="jellyfin_url" autocomplete="off" placeholder="http://192.168.1.10:8096">
        <small>Wird nur zum Auslesen der Server-Version genutzt (öffentlicher Endpunkt /System/Info/Public).</small>
      </label>
      <label>Release-Tag (optional)
        <input type="text" id="release_tag" autocomplete="off" placeholder="leer = neuester Release, z. B. 2026-10-17-1707">
      </label>
      <label class="check"><input type="checkbox" id="uninstall_first"><span>Vorhandene Jellyfin-Installation vorher entfernen (löscht die Anmeldung in der App)</span></label>
      <label class="check"><input type="checkbox" id="launch_after_install" checked><span>App nach der Installation starten</span></label>
    </div>
  </details>
  <div class="row">
    <button type="submit" id="go">Installieren</button>
    <span class="badge" id="badge">Bereit</span>
  </div>
  <div id="msg"></div>
</form>
<pre id="log" aria-live="polite">Noch keine Ausgabe.</pre>
</main>
<script>
const $ = id => document.getElementById(id);
let filled = false;

async function getJSON(path, opts) {
  const r = await fetch(path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
  return data;
}

function fill(d) {
  $("tv_ip").value = d.tv_ip || "";
  $("build_variant").value = d.build_variant;
  $("jellyfin_url").value = d.jellyfin_url || "";
  $("release_tag").value = d.release_tag || "";
  $("uninstall_first").checked = !!d.uninstall_first;
  $("launch_after_install").checked = !!d.launch_after_install;
}

function render(s) {
  const badge = $("badge");
  badge.className = "badge";
  if (s.running) { badge.textContent = "Läuft …"; badge.classList.add("run"); }
  else if (s.exit_code === null) { badge.textContent = "Bereit"; }
  else if (s.exit_code === 0) { badge.textContent = "Erfolgreich"; badge.classList.add("ok"); }
  else { badge.textContent = "Fehlgeschlagen"; badge.classList.add("err"); }
  $("go").disabled = s.running;
  const log = $("log");
  const stick = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
  if (s.log) log.textContent = s.log;
  if (stick) log.scrollTop = log.scrollHeight;
}

async function poll() {
  try {
    const s = await getJSON("api/state");
    if (!filled) { fill(s.defaults); filled = true; }
    render(s);
  } catch (e) { /* Verbindung kurz weg, nächster Versuch folgt */ }
}

$("f").addEventListener("submit", async ev => {
  ev.preventDefault();
  $("msg").textContent = "";
  const body = {
    tv_ip: $("tv_ip").value,
    build_variant: $("build_variant").value,
    jellyfin_url: $("jellyfin_url").value,
    release_tag: $("release_tag").value,
    uninstall_first: $("uninstall_first").checked,
    launch_after_install: $("launch_after_install").checked,
  };
  try {
    await getJSON("api/start", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
    $("log").textContent = "Starte …";
    poll();
  } catch (e) { $("msg").textContent = e.message; }
});

poll();
setInterval(poll, 1500);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "JellyfinTizenInstaller/0.1"

    def log_message(self, fmt, *args):  # Zugriffslog nicht in das Add-on-Log schreiben
        pass

    def _client_ok(self):
        if self.client_address[0] in ALLOWED_CLIENTS:
            return True
        self._send(403, "text/plain; charset=utf-8", b"Forbidden")
        return False

    def _send(self, status, ctype, body):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status, obj):
        self._send(status, "application/json; charset=utf-8", json.dumps(obj).encode("utf-8"))

    def do_GET(self):
        if not self._client_ok():
            return
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", build_page().encode("utf-8"))
        elif path == "/api/state":
            state = JOB.snapshot()
            opts = load_options()
            state["defaults"] = {
                k: opts[k]
                for k in (
                    "tv_ip",
                    "build_variant",
                    "jellyfin_url",
                    "release_tag",
                    "uninstall_first",
                    "launch_after_install",
                )
            }
            self._json(200, state)
        else:
            self._json(404, {"error": "Nicht gefunden"})

    def do_POST(self):
        if not self._client_ok():
            return
        if self.path.split("?", 1)[0] != "/api/start":
            self._json(404, {"error": "Nicht gefunden"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 4096:
            self._json(400, {"error": "Ungültige Anfrage."})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError
        except ValueError:
            self._json(400, {"error": "Ungültiges JSON."})
            return
        opts = load_options()
        params, err = parse_params(payload, opts)
        if err:
            self._json(400, {"error": err})
            return
        ok, msg = JOB.start(params, [opts["certificate_password"], opts["distributor_password"]])
        if not ok:
            self._json(409, {"error": msg})
            return
        self._json(202, {"started": True})


def main():
    opts = load_options()
    server = ThreadingHTTPServer((BIND, PORT), Handler)
    print("[addon] Weboberfläche auf Port %d (nur Ingress erlaubt: %s)" % (PORT, ", ".join(sorted(ALLOWED_CLIENTS))), flush=True)
    if opts["auto_install"]:
        if valid_ip(opts["tv_ip"]) and VARIANT_RE.match(opts["build_variant"]):
            print("[addon] auto_install aktiv: starte Installation für %s" % opts["tv_ip"], flush=True)
            params = {
                "tv_ip": opts["tv_ip"],
                "build_variant": opts["build_variant"],
                "release_tag": opts["release_tag"] if TAG_RE.match(opts["release_tag"]) else "",
                "jellyfin_url": opts["jellyfin_url"] if URL_RE.match(opts["jellyfin_url"] or "") else "",
                "uninstall_first": opts["uninstall_first"],
                "launch_after_install": opts["launch_after_install"],
            }
            JOB.start(params, [opts["certificate_password"], opts["distributor_password"]])
        else:
            print("[addon] auto_install aktiv, aber tv_ip/build_variant ungültig – übersprungen.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
