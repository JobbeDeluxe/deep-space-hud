from pathlib import Path
import subprocess
import sys
import unittest
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from instance import ServiceLease


class InstanceTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform=='win32','Windows instance mutex')
    def test_service_lease_blocks_another_process_and_is_released(self):
        key='test-'+uuid.uuid4().hex
        lease=ServiceLease(key)
        self.assertTrue(lease.acquired)
        code='from instance import ServiceLease;import sys;x=ServiceLease(sys.argv[1]);print(int(x.acquired));x.close()'
        def attempt():
            return subprocess.check_output([sys.executable,'-c',code,key],
                cwd=Path(__file__).resolve().parents[1],text=True,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).strip()
        try:self.assertEqual(attempt(),'0')
        finally:lease.close()
        self.assertEqual(attempt(),'1')


if __name__=='__main__':unittest.main()
