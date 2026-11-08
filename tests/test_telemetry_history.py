import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import Telemetry


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.telemetry = Telemetry({'disk_path': 'C:\\', 'network_interface': ''})

    def test_history_survives_without_browser_and_keeps_last_minute(self):
        for second in range(100):
            now = 1000 + second
            with patch('server.time.time', return_value=now):
                self.telemetry.hardware = ({'gpu': 42}, {}, now)
                self.telemetry._publish_system({'timestamp': now, 'cpu': second,
                                                'up': 1000, 'down': 2000, 'gpu': None})
        with patch('server.time.time', return_value=1099):
            snapshot = self.telemetry.snapshot()
        self.assertEqual(len(snapshot['history']), 61)
        self.assertEqual(snapshot['history'][0]['timestamp'], 1039)
        self.assertEqual(snapshot['history'][-1]['cpu'], 99)
        self.assertEqual(snapshot['history'][-1]['gpu'], 42)
        self.assertLessEqual(len(self.telemetry.history), 65)
        snapshot['history'][-1]['cpu'] = -1
        self.assertEqual(self.telemetry.history[-1]['cpu'], 99)

    def test_expired_hardware_is_not_recorded_as_current(self):
        self.telemetry.hardware = ({'gpu': 90}, {}, 1000)
        with patch('server.time.time', return_value=1010):
            self.telemetry._publish_system({'timestamp': 1010, 'cpu': 15,
                                            'gpu': None, 'up': None, 'down': None})
            snapshot = self.telemetry.snapshot()
        self.assertIsNone(snapshot['gpu'])
        self.assertIsNone(snapshot['history'][-1]['gpu'])
        self.assertIsNone(snapshot['history'][-1]['down'])


if __name__ == '__main__':
    unittest.main()
