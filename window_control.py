"""Windows placement for the HUD's isolated browser, never personal windows."""
from __future__ import annotations
import ctypes
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import sys
import threading
import time
import psutil

DEFAULTS = {'monitor': '', 'fullscreen': True, 'always_on_top': True}


def is_hud_title(title):
    # Chrome changes an app's title to its host when displaying a connection
    # error. Only accept these exact local titles in the dedicated HUD profile.
    return title in ('Deep Space · HDMI Telemetry', '127.0.0.1', 'localhost')


def validate_settings(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValueError('Unbekannte Fensteroption.')
    for key, item in value.items():
        if key == 'monitor':
            if not isinstance(item, str) or len(item) > 128:
                raise ValueError('Ungueltiger Bildschirm.')
        elif type(item) is not bool:
            raise ValueError('Fensteroption muss ein Wahrheitswert sein.')
    return value


def select_monitor(monitors, selected, current=None):
    return (next((m for m in monitors if m['id'] == selected), None)
            or next((m for m in monitors if not selected and m['id'] == current), None)
            or next((m for m in monitors if m['primary']), None)
            or (monitors[0] if monitors else None))


class Win32:
    FRAME = 0x00C40000  # WS_CAPTION | WS_THICKFRAME
    def __init__(self):
        self.u = ctypes.WinDLL('user32', use_last_error=True)
        self.enum_proc = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
        self.monitor_proc = ctypes.WINFUNCTYPE(W.BOOL, W.HANDLE, W.HDC, ctypes.POINTER(W.RECT), W.LPARAM)
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size', W.DWORD), ('rect', W.RECT), ('work', W.RECT),
                        ('flags', W.DWORD), ('device', W.WCHAR * 32)]
        self.MonitorInfo = MonitorInfo
        signatures = {
            'EnumWindows': ([self.enum_proc, W.LPARAM], W.BOOL),
            'EnumDisplayMonitors': ([W.HDC, ctypes.POINTER(W.RECT), self.monitor_proc, W.LPARAM], W.BOOL),
            'GetMonitorInfoW': ([W.HANDLE, ctypes.POINTER(MonitorInfo)], W.BOOL),
            'MonitorFromWindow': ([W.HWND, W.DWORD], W.HANDLE),
            'GetWindowThreadProcessId': ([W.HWND, ctypes.POINTER(W.DWORD)], W.DWORD),
            'GetWindowTextW': ([W.HWND, W.LPWSTR, ctypes.c_int], ctypes.c_int),
            'GetClassNameW': ([W.HWND, W.LPWSTR, ctypes.c_int], ctypes.c_int),
            'GetWindowRect': ([W.HWND, ctypes.POINTER(W.RECT)], W.BOOL),
            'GetWindowLongW': ([W.HWND, ctypes.c_int], W.LONG),
            'SetWindowLongW': ([W.HWND, ctypes.c_int, W.LONG], W.LONG),
            'SetWindowPos': ([W.HWND, W.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.UINT], W.BOOL),
            'ShowWindow': ([W.HWND, ctypes.c_int], W.BOOL),
            'IsIconic': ([W.HWND], W.BOOL), 'IsZoomed': ([W.HWND], W.BOOL),
            'IsWindowVisible': ([W.HWND], W.BOOL),
            'PostMessageW': ([W.HWND, W.UINT, W.WPARAM, W.LPARAM], W.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.u, name); fn.argtypes = args; fn.restype = result

    def dpi(self):
        # Use physical monitor coordinates, including mixed Windows scaling.
        fn = self.u.SetThreadDpiAwarenessContext
        fn.argtypes = [W.HANDLE]; fn.restype = W.HANDLE
        fn(W.HANDLE(-4))

    def monitors(self):
        self.dpi()
        result = []
        @self.monitor_proc
        def visit(handle, dc, rect, data):
            info = self.MonitorInfo(); info.size = ctypes.sizeof(info)
            if self.u.GetMonitorInfoW(handle, ctypes.byref(info)):
                r, w = info.rect, info.work
                number = info.device.replace('\\\\.\\DISPLAY', '')
                result.append({'id': info.device, 'label': f'Bildschirm {number} · {r.right-r.left} × {r.bottom-r.top}' + (' · Hauptbildschirm' if info.flags & 1 else ''),
                               'primary': bool(info.flags & 1), 'rect': [r.left, r.top, r.right, r.bottom],
                               'work': [w.left, w.top, w.right, w.bottom]})
            return True
        if not self.u.EnumDisplayMonitors(None, None, visit, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return sorted(result, key=lambda m: m['id'])

    def windows(self, profile):
        # An exact user-data-dir identifies the dedicated browser process.
        expected = os.path.normcase(os.path.abspath(profile))
        pids = set()
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            if process.info['name'] not in ('chrome.exe', 'msedge.exe'):
                continue
            args = process.info['cmdline'] or []
            if any(a.startswith('--user-data-dir=') and os.path.normcase(os.path.abspath(a.split('=', 1)[1])) == expected for a in args):
                pids.add(process.pid)
        result = []
        @self.enum_proc
        def visit(hwnd, data):
            pid = W.DWORD(); self.u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids:
                title = ctypes.create_unicode_buffer(512); kind = ctypes.create_unicode_buffer(128)
                self.u.GetWindowTextW(hwnd, title, len(title)); self.u.GetClassNameW(hwnd, kind, len(kind))
                if is_hud_title(title.value) and kind.value == 'Chrome_WidgetWin_1' and self.u.IsWindowVisible(hwnd):
                    result.append(hwnd)
            return True
        self.u.EnumWindows(visit, 0)
        return result

    def current_monitor(self, hwnd):
        info = self.MonitorInfo(); info.size = ctypes.sizeof(info)
        handle = self.u.MonitorFromWindow(hwnd, 2)
        return info.device if self.u.GetMonitorInfoW(handle, ctypes.byref(info)) else None

    def rect(self, hwnd):
        rect = W.RECT()
        if not self.u.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise ctypes.WinError(ctypes.get_last_error())
        return [rect.left, rect.top, rect.right, rect.bottom]

    def apply(self, hwnd, monitor, options, original):
        self.dpi()
        fullscreen = self.is_fullscreen(hwnd)
        if self.u.IsIconic(hwnd) or (self.u.IsZoomed(hwnd) and not fullscreen):
            # SW_SHOWNOACTIVATE restores without stealing keyboard focus.
            self.u.ShowWindow(hwnd, 4)
        if fullscreen and (not options['fullscreen'] or self.current_monitor(hwnd) != monitor['id']):
            self._fullscreen(hwnd, False)
            fullscreen = False
        if not fullscreen:
            x, y, r, b = monitor['work']
            width, height = min(1040, r-x), min(640, b-y)
            left, top = x+(r-x-width)//2, y+(b-y-height)//2
            right, bottom = left+width, top+height
            self._position(hwnd, [left, top, right, bottom], options['always_on_top'])
        if options['fullscreen']:
            if not fullscreen:
                self._fullscreen(hwnd, True)
            self._position(hwnd, monitor['rect'], options['always_on_top'])

    def is_fullscreen(self, hwnd):
        return not bool(self.u.GetWindowLongW(hwnd, -16) & self.FRAME)

    def _fullscreen(self, hwnd, enabled):
        # Chromium draws its own frame. Removing WS_CAPTION alone leaves insets.
        # Send its fullscreen accelerator only to the verified HUD window; never
        # inject a global keyboard event or activate a different app.
        self.u.PostMessageW(hwnd, 0x0100, 0x7A, 0x00570001)
        self.u.PostMessageW(hwnd, 0x0101, 0x7A, 0xC0570001)
        deadline = time.monotonic() + 2
        while self.is_fullscreen(hwnd) != enabled:
            if time.monotonic() >= deadline:
                raise OSError('Vollbildwechsel wurde vom HUD-Fenster nicht übernommen.')
            time.sleep(.025)

    def _position(self, hwnd, rect, topmost):
        left, top, right, bottom = rect
        # TOPMOST / NOTOPMOST, NOACTIVATE | SHOWWINDOW.
        if not self.u.SetWindowPos(hwnd, W.HWND(-1 if topmost else -2),
                                  left, top, right-left, bottom-top, 0x10 | 0x40):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self, hwnd):
        self.u.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE

    def reload(self, hwnd):
        self.u.PostMessageW(hwnd, 0x0100, 0x74, 0x003F0001)  # F5, this window only
        self.u.PostMessageW(hwnd, 0x0101, 0x74, 0xC03F0001)


class WindowController:
    def __init__(self, path, profile, enabled=True, api=None, on_closed=None):
        self.path, self.profile = Path(path), Path(profile)
        self.supported = enabled and (sys.platform == 'win32' or api is not None)
        self.api = api or (Win32() if self.supported else None)
        self.on_closed = on_closed
        self.lock = threading.RLock(); self.stop = threading.Event(); self.wake = threading.Event()
        self.settings = dict(DEFAULTS); self.handles = {}; self.applied = {}
        self.error = ''; self.effective = None; self.monitor_list = []
        self.seen = False; self.missing = 0; self.launch_pending_until = 0
        if self.path.exists():
            try:
                self.settings.update(validate_settings(json.loads(self.path.read_text(encoding='utf-8-sig'))))
            except (OSError, ValueError):
                self.error = 'Fensteroptionen konnten nicht gelesen werden; Standardwerte aktiv.'

    def _save(self, settings):
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf-8')
        temporary.replace(self.path)

    def update(self, patch):
        if not self.supported:
            raise ValueError('Bitte den eigenen HUD-Fenstermodus starten.')
        validate_settings(patch)
        with self.lock:
            options = {**self.settings, **patch}
            self._save(options)  # Do not report success if persistence fails.
            self.settings = options
            self.applied.clear(); self.wake.set()
        return self.snapshot()

    def snapshot(self):
        with self.lock:
            return {'app': 'deep-space-hud', 'supported': self.supported, 'attached': bool(self.handles),
                    'settings': dict(self.settings), 'monitors': list(self.monitor_list),
                    'effective_monitor': self.effective, 'error': self.error}

    def start(self):
        if self.supported:
            threading.Thread(target=self._run, daemon=True, name='hud-window').start()

    def ensure_window(self, opener, reload_existing=False):
        """One launch decision for startup and all concurrent show requests."""
        with self.lock:
            if self.stop.is_set():
                raise ValueError('HUD wird beendet. Bitte gleich noch einmal starten.')
            # Cached handles may be stale for one sampling interval. Query now.
            windows = self.api.windows(self.profile)
            if windows:
                keep = next((h for h in windows if h in self.handles), windows[0])
                for hwnd in windows:
                    if hwnd != keep:
                        self.api.close(hwnd)
                if reload_existing:
                    self.api.reload(keep)
                    self.launch_pending_until = time.monotonic() + 2
                self.missing = 0
                self.applied.clear(); self.wake.set()
                return True
            if time.monotonic() < self.launch_pending_until:
                return True
            self.launch_pending_until = time.monotonic() + 20
            try:
                opened = opener()
            except Exception:
                self.launch_pending_until = 0
                raise
            if not opened:
                self.launch_pending_until = 0
            self.wake.set()
            return opened

    def close(self):
        self.stop.set(); self.wake.set()
        if self.api:
            # Revalidate ownership before closing any window.
            for hwnd in self.api.windows(self.profile):
                self.api.close(hwnd)

    def _tick(self):
        monitors = self.api.monitors()
        windows = self.api.windows(self.profile)
        with self.lock:
            self.monitor_list = monitors
            self.handles = {h: state for h, state in self.handles.items() if h in windows}
            self.applied = {h: state for h, state in self.applied.items() if h in windows}
            for hwnd in windows:
                if hwnd not in self.handles:
                    self.handles[hwnd] = {'style': self.api.u.GetWindowLongW(hwnd, -16)}
                selected = select_monitor(monitors, self.settings['monitor'], self.api.current_monitor(hwnd))
                if not selected:
                    continue
                if not self.settings['monitor']:
                    options = {**self.settings, 'monitor': selected['id']}
                    self._save(options); self.settings = options
                # A manual browser F11 change is also remembered for next start.
                if hwnd in self.applied:
                    actual = self.api.is_fullscreen(hwnd)
                    if actual != self.settings['fullscreen']:
                        options = {**self.settings, 'fullscreen': actual}
                        self._save(options); self.settings = options
                signature = (tuple(self.settings.items()), tuple(selected['rect']), tuple(selected['work']))
                if self.applied.get(hwnd) != signature:
                    self.api.apply(hwnd, selected, self.settings, self.handles[hwnd])
                    self.applied[hwnd] = signature
                self.effective = selected['id']
            self.error = ''
            self.missing = 0 if windows else self.missing + 1
            if windows:
                self.seen = True
                self.launch_pending_until = 0
            should_stop = self.seen and self.missing >= 3 and time.monotonic() >= self.launch_pending_until
        if should_stop and self.on_closed:
            self.stop.set(); self.on_closed()

    def _run(self):
        while not self.stop.is_set():
            try:
                self._tick()
            except Exception as exc:
                with self.lock:
                    self.error = str(exc)
            self.wake.wait(1); self.wake.clear()
