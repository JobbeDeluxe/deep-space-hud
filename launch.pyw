"""Console-free setup/start. All diagnostics stay in launch.log and hud.log."""
from pathlib import Path
import ctypes
import json
import os
import subprocess
import sys
import traceback
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def notice(message):
    ctypes.windll.user32.MessageBoxW(None, message, 'Deep Space HUD', 0x10)


def active_hud(port):
    url = f'http://127.0.0.1:{port}'
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(url + '/api/window', timeout=2) as response:
            info = json.load(response)
        if info.get('app') != 'deep-space-hud' or not info.get('supported'):
            return False
        request = Request(url + '/api/window/show', data=b'{}',
                          headers={'Origin': url, 'Content-Type': 'application/json'})
        with opener.open(request, timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def main():
    os.chdir(ROOT)
    python = ROOT / '.venv/Scripts/python.exe'
    pythonw = ROOT / '.venv/Scripts/pythonw.exe'
    with (ROOT / 'launch.log').open('a', encoding='utf-8') as log:
        if not python.exists():
            source = Path(sys.executable)
            if source.name.lower() == 'pythonw.exe':
                source = source.with_name('python.exe')
            subprocess.run([str(source), '-m', 'venv', str(ROOT / '.venv')],
                           check=True, stdout=log, stderr=log, creationflags=NO_WINDOW)
        probe = subprocess.run([str(python), '-c', 'import psutil, pycaw'],
                               stdout=log, stderr=log, creationflags=NO_WINDOW)
        if probe.returncode:
            subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')],
                           check=True, stdout=log, stderr=log, creationflags=NO_WINDOW)
    if Path(sys.executable).resolve() != pythonw.resolve():
        subprocess.Popen([str(pythonw), str(ROOT / 'launch.pyw')], cwd=ROOT,
                         creationflags=NO_WINDOW)
        return
    config = json.loads((ROOT / 'config.json').read_text(encoding='utf-8-sig')) if (ROOT / 'config.json').exists() else {}
    if active_hud(int(config.get('port', 8765))):
        return
    log_path = ROOT / 'hud.log'
    if log_path.exists() and log_path.stat().st_size > 2_000_000:
        log_path.replace(ROOT / 'hud.previous.log')
    with log_path.open('a', encoding='utf-8', buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            import server
            sys.argv = ['server.py', '--app-window']
            if server.main():
                notice('HUD konnte nicht gestartet werden. Eventuell läuft noch eine alte Instanz.\nDetails stehen in hud.log im HUD-Ordner.')
        except Exception:
            traceback.print_exc()
            notice('HUD konnte nicht gestartet werden. Details stehen in hud.log im HUD-Ordner.')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        with (ROOT / 'launch.log').open('a', encoding='utf-8') as log:
            traceback.print_exc(file=log)
        notice('Einrichtung fehlgeschlagen. Bitte Python 3.10 oder neuer installieren und launch.log im HUD-Ordner prüfen.')
