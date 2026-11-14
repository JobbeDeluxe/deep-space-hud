"""Serialize local service startup and reconnect to an existing HUD service."""
import ctypes
from ctypes import wintypes as W
import json
import sys
import time
from urllib.request import Request, build_opener, ProxyHandler


class ServiceLease:
    def __init__(self, port):
        self.handle = None
        self.acquired = True
        if sys.platform == 'win32':
            self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            self.kernel.CreateMutexW.argtypes = [W.LPVOID, W.BOOL, W.LPCWSTR]
            self.kernel.CreateMutexW.restype = W.HANDLE
            self.kernel.CloseHandle.argtypes = [W.HANDLE]
            self.kernel.CloseHandle.restype = W.BOOL
            self.handle = self.kernel.CreateMutexW(None, False, f'Local\\DeepSpaceHUD-Service-{port}')
            error = ctypes.get_last_error()
            if not self.handle:
                raise ctypes.WinError(error)
            self.acquired = error != 183  # ERROR_ALREADY_EXISTS
            if not self.acquired:
                self.close()

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def show_existing_hud(port, timeout=0):
    url = f'http://127.0.0.1:{port}'
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while True:
        try:
            with opener.open(url + '/api/window', timeout=2) as response:
                info = json.load(response)
            if info.get('app') != 'deep-space-hud' or not info.get('supported'):
                return False
            request = Request(url + '/api/window/show', data=b'{}',
                              headers={'Origin': url, 'Content-Type': 'application/json'})
            with opener.open(request, timeout=4) as response:
                return response.status == 200
        except Exception:
            if time.monotonic() >= deadline:
                return False
            time.sleep(.2)
