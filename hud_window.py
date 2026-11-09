"""An isolated Chrome/Edge window for the always-visible HDMI panel."""
import json
import os
from pathlib import Path
import subprocess


BACKGROUND_FLAGS = [
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    '--disable-features=CalculateNativeWinOcclusion',
]


def find_browser():
    for relative in ('Google/Chrome/Application/chrome.exe',
                     'Microsoft/Edge/Application/msedge.exe'):
        for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
            root = os.environ.get(variable)
            if root and (candidate := Path(root) / relative).is_file():
                return candidate
    return None


def prepare_profile(profile):
    """Seed only new files; never edit a running browser's preferences."""
    profile.mkdir(parents=True, exist_ok=True)
    defaults = {
        'Local State': {'performance_tuning': {
            'high_efficiency_mode': {'enabled': False, 'state': 0},
            'battery_saver_mode': {'state': 0},
            'tab_freezing': {'enabled': False},
        }},
        'Default/Preferences': {'performance_tuning': {
            'tab_discarding': {'exceptions': ['127.0.0.1', 'localhost']},
        }},
    }
    for name, settings in defaults.items():
        path = profile / name
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='utf-8') as output:
                json.dump(settings, output)
        except FileExistsError:
            pass


def browser_command(browser, profile, url):
    return [str(browser), f'--user-data-dir={profile}', f'--app={url}',
            '--no-first-run', '--no-default-browser-check', '--window-size=1040,640',
            *BACKGROUND_FLAGS]


def open_hud_window(url):
    browser = find_browser()
    if browser is None:
        print('Chrome/Edge nicht gefunden; normaler Browsermodus als Rueckfall.')
        return False
    # Separate user-data-dir is necessary: an existing personal browser process
    # would otherwise absorb this launch and ignore its background flags.
    # Microsoft Store Python redirects writes below LOCALAPPDATA into its package
    # cache; Chrome cannot see those seeded preferences. The user home is shared.
    profile = Path.home() / '.deep-space-hud' / browser.stem
    try:
        prepare_profile(profile)
        subprocess.Popen(browser_command(browser, profile, url),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        print(f'HUD-Fenster konnte nicht gestartet werden: {exc}')
        return False
    print('Eigenes HUD-Fenster aktiv. Einstellungen werden in diesem HUD-Profil gespeichert.')
    return True
