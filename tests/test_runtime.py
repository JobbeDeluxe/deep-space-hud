import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import LocalRequestHandler, Telemetry
from hud_window import browser_command, prepare_profile, open_hud_window


class RuntimeTests(unittest.TestCase):
    def test_disconnects_during_headers_body_and_finish_are_quiet(self):
        handler = object.__new__(LocalRequestHandler)
        for method in ('handle', 'finish'):
            for error in (ConnectionAbortedError(10053, 'aborted'),
                          ConnectionResetError(10054, 'reset'), BrokenPipeError(), TimeoutError()):
                with patch('server.BaseHTTPRequestHandler.' + method, side_effect=error):
                    getattr(handler, method)()
            # Unexpected errors must remain visible, not get swallowed.
            with patch('server.BaseHTTPRequestHandler.' + method, side_effect=ValueError('bug')):
                with self.assertRaises(ValueError):
                    getattr(handler, method)()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows CoreAudio worker')
    def test_blocked_audio_does_not_interrupt_real_sampling(self):
        telemetry = Telemetry({'disk_path': 'C:\\', 'network_interface': ''})
        entered, release = threading.Event(), threading.Event()
        def blocked_audio():
            entered.set()
            release.wait(10)
            return {'volume': 50, 'muted': False}
        with patch.object(telemetry, '_read_audio', side_effect=blocked_audio), \
             patch.object(telemetry, '_hardware_loop'):
            try:
                telemetry.start()
                self.assertTrue(entered.wait(3))
                time.sleep(4.3)
                snapshot = telemetry.snapshot()
                self.assertGreaterEqual(len(snapshot['history']), 4)
                self.assertIsNotNone(snapshot['cpu'])
                self.assertIsNone(snapshot['volume'])
                gaps = [b['timestamp'] - a['timestamp'] for a, b in
                        zip(snapshot['history'], snapshot['history'][1:])]
                self.assertLess(max(gaps), 2.2)
                self.assertLess(time.time() - snapshot['timestamp'], 1.5)
            finally:
                telemetry.stop.set()
                release.set()

    def test_audio_cache_expires_without_erasing_cpu(self):
        telemetry = Telemetry({'disk_path': 'C:\\', 'network_interface': ''})
        telemetry.data['cpu'] = 21
        telemetry.audio = ({'volume': 50, 'muted': False}, time.monotonic())
        self.assertEqual(telemetry.snapshot()['volume'], 50)
        telemetry.audio = (telemetry.audio[0], time.monotonic() - 9)
        self.assertIsNone(telemetry.snapshot()['volume'])
        self.assertEqual(telemetry.snapshot()['cpu'], 21)

    def test_isolated_browser_profile_and_safe_repeated_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp) / 'HUD profile'
            prepare_profile(profile)
            state = json.loads((profile / 'Local State').read_text())
            self.assertFalse(state['performance_tuning']['tab_freezing']['enabled'])
            self.assertEqual(state['performance_tuning']['battery_saver_mode']['state'], 0)
            (profile / 'Default/Preferences').write_text('{"user_setting":42}')
            prepare_profile(profile)
            self.assertEqual(json.loads((profile / 'Default/Preferences').read_text()), {'user_setting': 42})
            args = browser_command(Path('C:/Program Files/Chrome/chrome.exe'), profile, 'http://127.0.0.1:8765')
            self.assertIn(f'--user-data-dir={profile}', args)
            self.assertIn('--app=http://127.0.0.1:8765', args)
            self.assertIn('--disable-background-timer-throttling', args)
            self.assertIn('--disable-backgrounding-occluded-windows', args)
            self.assertNotIn('--no-sandbox', args)

    def test_store_python_profile_uses_shared_home_not_redirected_appdata(self):
        with patch('hud_window.find_browser', return_value=Path('chrome.exe')), \
             patch('hud_window.Path.home', return_value=Path('C:/Users/example')), \
             patch('hud_window.prepare_profile') as prepare, \
             patch('hud_window.subprocess.Popen') as launch, patch('builtins.print'):
            self.assertTrue(open_hud_window('http://127.0.0.1:8765'))
            profile = Path('C:/Users/example/.deep-space-hud/chrome')
            prepare.assert_called_once_with(profile)
            self.assertIn(f'--user-data-dir={profile}', launch.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
