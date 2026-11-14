import json
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from window_control import WindowController, select_monitor, validate_settings, is_hud_title

MONITORS = [
    {'id': 'main', 'primary': True, 'rect': [0, 0, 1920, 1080], 'work': [0, 0, 1920, 1040]},
    {'id': 'hdmi', 'primary': False, 'rect': [1920, 0, 2944, 600], 'work': [1920, 0, 2944, 552]},
]


class WindowTests(unittest.TestCase):
    def test_existing_window_is_reused_even_before_first_controller_tick(self):
        with tempfile.TemporaryDirectory() as directory:
            api = Mock(); api.windows.return_value = [123]
            controller = WindowController(Path(directory)/'window.json', 'private', api=api)
            self.assertFalse(controller.snapshot()['attached'])
            opener = Mock(return_value=True)
            controller.ensure_window(opener, reload_existing=True)
            opener.assert_not_called(); api.reload.assert_called_once_with(123)

    def test_simultaneous_show_requests_launch_once_while_window_is_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            api = Mock(); api.windows.return_value = []
            controller = WindowController(Path(directory)/'window.json', 'private', api=api)
            opener = Mock(return_value=True)
            with ThreadPoolExecutor(max_workers=8) as pool:
                self.assertTrue(all(pool.map(lambda _:controller.ensure_window(opener), range(16))))
            opener.assert_called_once()

    def test_duplicate_owned_hud_windows_are_collapsed_and_failed_open_can_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            api = Mock(); api.windows.return_value = [456,123]
            controller = WindowController(Path(directory)/'window.json', 'private', api=api)
            controller.handles = {123:{}}
            opener = Mock(return_value=False)
            controller.ensure_window(opener)
            api.close.assert_called_once_with(456); opener.assert_not_called()
            api.windows.return_value = []
            self.assertFalse(controller.ensure_window(opener))
            self.assertFalse(controller.ensure_window(opener))
            self.assertEqual(opener.call_count,2)

    def test_offline_hud_title_is_recognized_without_matching_other_pages(self):
        for title in ('Deep Space · HDMI Telemetry','127.0.0.1','localhost'):
            self.assertTrue(is_hud_title(title))
        for title in ('Settings','Google Chrome','127.0.0.1 - unrelated page',''):
            self.assertFalse(is_hud_title(title))

    def test_select_requested_monitor_and_fallback_on_disconnect(self):
        self.assertEqual(select_monitor(MONITORS, 'hdmi')['id'], 'hdmi')
        self.assertEqual(select_monitor(MONITORS, '', 'hdmi')['id'], 'hdmi')
        self.assertEqual(select_monitor(MONITORS, 'missing')['id'], 'main')
        self.assertIsNone(select_monitor([], 'hdmi'))

    def test_validate_settings_rejects_wrong_types_and_unknown_fields(self):
        for value in ([], None, {'fullscreen': 'false'}, {'always_on_top': 1},
                      {'monitor': 3}, {'monitor': 'x' * 129}, {'command': 'anything'}):
            with self.assertRaises(ValueError):
                validate_settings(value)

    def test_persistence_monitor_reconnect_and_no_repeated_focus_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            api = Mock()
            api.monitors.return_value = MONITORS
            api.windows.return_value = [123]
            api.current_monitor.return_value = 'hdmi'
            api.u.GetWindowLongW.return_value = 0x16CF0000
            api.is_fullscreen.return_value = True
            path = Path(directory) / 'window-settings.json'
            controller = WindowController(path, 'private-profile', api=api)
            controller._tick()
            self.assertEqual(controller.settings['monitor'], 'hdmi')
            self.assertEqual(json.loads(path.read_text())['monitor'], 'hdmi')
            controller._tick()
            api.apply.assert_called_once()  # No continuous focus/z-order forcing.
            controller.update({'fullscreen': False, 'always_on_top': False})
            api.is_fullscreen.return_value = False
            controller._tick()
            self.assertFalse(api.apply.call_args.args[2]['fullscreen'])
            restored = WindowController(path, 'private-profile', api=api)
            self.assertFalse(restored.settings['always_on_top'])
            api.monitors.return_value = MONITORS[:1]
            controller._tick()
            self.assertEqual(controller.snapshot()['effective_monitor'], 'main')
            self.assertEqual(controller.settings['monitor'], 'hdmi')
            api.monitors.return_value = MONITORS
            controller._tick()
            self.assertEqual(controller.snapshot()['effective_monitor'], 'hdmi')

    def test_failed_save_does_not_apply_and_close_revalidates_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            api = Mock(); api.windows.return_value = [456]
            controller = WindowController(Path(directory) / 'window.json', 'private', api=api)
            with patch.object(controller, '_save', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    controller.update({'always_on_top': False})
            self.assertTrue(controller.settings['always_on_top'])
            controller.handles = {123: {}}  # Stale/reused handle must not be closed.
            controller.close()
            api.close.assert_called_once_with(456)

    def test_closing_last_hud_stops_service_but_startup_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            api = Mock(); api.monitors.return_value = MONITORS; api.windows.return_value = []
            stopped = Mock()
            controller = WindowController(Path(directory) / 'window.json', 'private', api=api, on_closed=stopped)
            for _ in range(4):controller._tick()
            stopped.assert_not_called()
            controller.seen = True; controller._tick()
            stopped.assert_called_once()


if __name__ == '__main__':
    unittest.main()
