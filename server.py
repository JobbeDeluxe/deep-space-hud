"""Deep Space HUD: local telemetry, Windows 10/11, Python 3.10+."""
from __future__ import annotations

import argparse
from collections import deque
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener
import webbrowser

import psutil
from hud_window import open_hud_window

ROOT = Path(__file__).resolve().parent
KEYS = ('cpu', 'ram', 'disk', 'volume', 'cpu_temp', 'gpu', 'gpu_temp', 'vram', 'up', 'down')


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def lhm_sensors(tree):
    """Flatten LibreHardwareMonitor's /data.json, retaining stable SensorId paths."""
    result = []
    def walk(node):
        if not isinstance(node, dict):
            return
        sensor_id = node.get('SensorId', '')
        if sensor_id:
            raw = node.get('RawValue', node.get('Value', ''))
            # LHM formats strings with units; support comma decimals as well.
            value = number(str(raw).replace('\u00a0', ' ').split(' ')[0].replace(',', '.'))
            result.append((sensor_id.lower(), str(node.get('Text', '')).lower(), value))
        for child in node.get('Children', []):
            walk(child)
    walk(tree)
    return result


def parse_lhm(tree, gpu_index=0, overrides=None):
    sensors = lhm_sensors(tree)
    values = {}
    paths = {}
    gpu_roots = list(dict.fromkeys('/'.join(s.split('/')[:3]) for s, _, _ in sensors if s.startswith('/gpu-')))
    gpu_root = gpu_roots[gpu_index] if 0 <= gpu_index < len(gpu_roots) else None
    def find(key, predicate, preferred):
        matches = [(sid, name, val) for sid, name, val in sensors if val is not None and predicate(sid, name)]
        if not matches:
            return
        matches.sort(key=lambda item: next((i for i, p in enumerate(preferred) if p in item[1]), len(preferred)))
        sid, _, val = matches[0]
        values[key], paths[key] = val, sid
    find('cpu_temp', lambda s, n: s.startswith(('/intelcpu/', '/amdcpu/')) and '/temperature/' in s,
         ['cpu package', 'core (tctl/tdie)', 'core (tdie)', 'cores average', 'core average', 'cpu core'])
    if gpu_root:
        find('gpu', lambda s, n: s.startswith(gpu_root + '/') and '/load/' in s and n in ('gpu core', 'gpu d3d 3d'), ['gpu core'])
        find('gpu_temp', lambda s, n: s.startswith(gpu_root + '/') and '/temperature/' in s, ['gpu core'])
        find('vram', lambda s, n: s.startswith(gpu_root + '/') and '/load/' in s and n == 'gpu memory', ['gpu memory'])
    for key, sensor_id in (overrides or {}).items():
        if key not in ('cpu_temp', 'gpu', 'gpu_temp', 'vram'):
            continue
        match = next((v for s, _, v in sensors if s == str(sensor_id).lower()), None)
        values[key], paths[key] = match, sensor_id
    return values, paths


class Telemetry:
    def __init__(self, config):
        self.config = config
        self.lock = threading.Lock()
        self.data = {key: None for key in KEYS}
        self.data.update(timestamp=0, sources={}, disk_path=config['disk_path'], network_interface=config['network_interface'])
        self.stop = threading.Event()
        self.hardware = ({}, {}, 0)
        self.audio = ({}, 0)
        self.history = deque(maxlen=65)

    def start(self):
        threading.Thread(target=self._hardware_loop, daemon=True).start()
        threading.Thread(target=self._audio_loop, daemon=True).start()
        threading.Thread(target=self._system_loop, daemon=True).start()

    def snapshot(self):
        with self.lock:
            result = dict(self.data)
            audio, audio_updated = self.audio
            if time.monotonic() - audio_updated < 8:
                result.update(audio)
            advanced, sources, updated = self.hardware
            if time.time() - updated < 8:
                result.update(advanced)
                result['sources'] = dict(sources)
            cutoff = time.time() - 60
            result['history'] = [dict(row) for row in self.history if row['timestamp'] >= cutoff]
            return result

    def _publish_system(self, row):
        # Collect history independently of browser visibility and animation frames.
        with self.lock:
            self.data = row
            advanced, _, updated = self.hardware
            sample = dict(row)
            if time.time() - updated < 8:
                sample.update(advanced)
            self.history.append({key: sample.get(key) for key in ('timestamp', 'cpu', 'gpu', 'up', 'down')})

    def _net(self):
        per_nic = psutil.net_io_counters(pernic=True)
        selected = self.config['network_interface']
        if selected:
            return {selected: per_nic[selected]} if selected in per_nic else {}
        stats = psutil.net_if_stats()
        return {name: val for name, val in per_nic.items()
                if name in stats and stats[name].isup and not name.lower().startswith(('lo', 'loopback'))}

    def _system_loop(self):
        psutil.cpu_percent(None)
        old_net, old_time = self._net(), time.monotonic()
        deadline = old_time + 1
        while not self.stop.wait(max(0, deadline - time.monotonic())):
            now = time.monotonic()
            row = {key: None for key in KEYS}
            try:
                row['cpu'] = psutil.cpu_percent(None)
                row['ram'] = psutil.virtual_memory().percent
            except (OSError, psutil.Error):
                pass
            try:
                row['disk'] = psutil.disk_usage(self.config['disk_path']).percent
            except (OSError, psutil.Error):
                pass
            try:
                current = self._net()
                common = current.keys() & old_net.keys()
                if common:
                    elapsed = max(now - old_time, 0.001)
                    row['up'] = sum(max(0, current[n].bytes_sent - old_net[n].bytes_sent) for n in common) / elapsed
                    row['down'] = sum(max(0, current[n].bytes_recv - old_net[n].bytes_recv) for n in common) / elapsed
                old_net, old_time = current, now
            except (OSError, psutil.Error):
                pass
            row.update(timestamp=time.time(), sources={}, disk_path=self.config['disk_path'], network_interface=self.config['network_interface'])
            self._publish_system(row)
            # Fixed cadence, without a burst of invented catch-up samples after a stall.
            deadline += 1
            if deadline < time.monotonic():
                deadline = time.monotonic() + 1

    @staticmethod
    def _read_audio():
        from pycaw.pycaw import AudioUtilities
        # Resolve the default device again so output changes are reflected.
        endpoint = AudioUtilities.GetSpeakers().EndpointVolume
        return {'volume': endpoint.GetMasterVolumeLevelScalar() * 100,
                'muted': bool(endpoint.GetMute())}

    def _audio_loop(self):
        # CoreAudio/COM can block during device changes or games. It must never
        # hold the sampling thread or the shared lock while calling Windows.
        if sys.platform != 'win32':
            return
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            return
        try:
            while not self.stop.is_set():
                try:
                    audio = self._read_audio()
                except Exception:
                    audio = {'volume': None, 'muted': None}
                with self.lock:
                    self.audio = (audio, time.monotonic())
                self.stop.wait(1)
        finally:
            comtypes.CoUninitialize()

    def _hardware_loop(self):
        # Bypass environment proxy configuration for loopback requests.
        opener = build_opener(ProxyHandler({}))
        smi = shutil.which('nvidia-smi')
        if not smi and sys.platform == 'win32':
            candidate = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'System32' / 'nvidia-smi.exe'
            smi = str(candidate) if candidate.exists() else None
        while not self.stop.is_set():
            values, sources = {}, {}
            try:
                with opener.open(self.config['lhm_url'], timeout=1.5) as response:
                    tree = json.loads(response.read(2_000_000))
                values, paths = parse_lhm(tree, self.config['gpu_index'], self.config.get('sensor_overrides'))
                sources = {k: 'LibreHardwareMonitor: ' + str(v) for k, v in paths.items()}
            except Exception:
                pass
            # NVIDIA fallback: use only when LHM supplies no GPU values, to avoid mixing adapters.
            if smi and not any(values.get(k) is not None for k in ('gpu', 'gpu_temp', 'vram')):
                try:
                    output = subprocess.run(
                        [smi, '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'],
                        capture_output=True, text=True, timeout=2,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), check=True)
                    fields = output.stdout.strip().splitlines()[self.config['gpu_index']].split(',')
                    gpu, temp, used, total = map(number, fields)
                    values.update(gpu=gpu, gpu_temp=temp, vram=(used / total * 100 if used is not None and total else None))
                    sources.update({k: 'NVIDIA / nvidia-smi' for k in ('gpu', 'gpu_temp', 'vram')})
                except (OSError, subprocess.SubprocessError, IndexError, ValueError):
                    pass
            with self.lock:
                self.hardware = (values, sources, time.time())
            self.stop.wait(2)


def load_config():
    config = dict(port=8765, disk_path=(os.environ.get('SystemDrive', 'C:') + '\\' if sys.platform == 'win32' else '/'),
                  network_interface='', lhm_url='http://127.0.0.1:8085/data.json', gpu_index=0, sensor_overrides={})
    path = ROOT / 'config.json'
    if path.exists():
        config.update(json.loads(path.read_text(encoding='utf-8-sig')))
    parsed = urlsplit(config['lhm_url'])
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('lhm_url muss eine lokale http://127.0.0.1-Adresse sein.')
    return config


class LocalRequestHandler(BaseHTTPRequestHandler):
    """A browser disconnect is normal, including Windows socket error 10053."""
    def handle(self):
        try:
            super().handle()
        except (ConnectionError, TimeoutError):
            self.close_connection = True

    def finish(self):
        try:
            super().finish()
        except (ConnectionError, TimeoutError):
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--app-window', action='store_true',
                        help='Eigenes Chrome/Edge-HUD-Fenster fuer Hintergrundbetrieb')
    parser.add_argument('--browser', dest='app_window', action='store_false',
                        help='Normalen Standardbrowser statt HUD-Fenster verwenden')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    config = load_config()
    port = args.port or int(config['port'])
    telemetry = Telemetry(config)
    html = (ROOT / 'Deep-Space-HUD.html').read_bytes()

    class Handler(LocalRequestHandler):
        def do_GET(self):
            # Reject foreign Host headers and cross-site browser fetches.
            if self.headers.get('Host', '') not in (f'127.0.0.1:{port}', f'localhost:{port}'):
                self.send_error(403)
                return
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                self.send_error(403)
                return
            path = urlsplit(self.path).path
            if path == '/api/events':
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self.close_connection = True
                self.connection.settimeout(5)
                try:
                    self.wfile.write(b'retry: 2000\n\n')
                    self.wfile.flush()
                    while not telemetry.stop.is_set():
                        body = json.dumps(telemetry.snapshot(), allow_nan=False).encode('utf-8')
                        self.wfile.write(b'data: ' + body + b'\n\n')
                        self.wfile.flush()
                        if telemetry.stop.wait(1):
                            break
                except (ConnectionError, TimeoutError):
                    pass
                return
            if path == '/api/telemetry':
                body, mime = json.dumps(telemetry.snapshot(), allow_nan=False).encode(), 'application/json'
            elif path in ('/', '/Deep-Space-HUD.html'):
                body, mime = html, 'text/html; charset=utf-8'
            elif path == '/favicon.ico':
                self.send_response(204)
                self.end_headers()
                return
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src data:; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    except OSError as exc:
        print(f'Port {port} kann nicht geoeffnet werden: {exc}\nLaeuft das HUD schon? Sonst port in config.json aendern.')
        return 1
    telemetry.start()
    url = f'http://127.0.0.1:{port}'
    print(f'\nDEEP SPACE // HDMI HUD\n{url}\n\nFenster auf das HDMI-Display verschieben, dann F oder F11.\nDieses Fenster offen lassen. Beenden: Strg+C.\n')
    if not args.no_browser:
        if not args.app_window or not open_hud_window(url):
            webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        telemetry.stop.set()
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
