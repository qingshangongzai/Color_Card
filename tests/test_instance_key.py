import sys
import unittest
from pathlib import Path

sys.path.insert(0, '.')


class TestComputeInstanceKey(unittest.TestCase):
    """测试单实例身份计算"""

    def test_ascii_case_is_ignored(self):
        """ASCII 大小写不影响实例键"""
        from instance_key import compute_instance_key

        self.assertEqual(
            compute_instance_key(Path('D:/Color_Card')),
            compute_instance_key(Path('d:/color_card')),
        )

    def test_non_ascii_case_is_preserved(self):
        """非 ASCII 字符不参与大小写折叠，保证与 C 启动器一致"""
        from instance_key import _normalize_path

        self.assertEqual(_normalize_path('D:/ÄPP'), 'd:/Äpp')
        self.assertNotEqual(_normalize_path('D:/ÄPP'), _normalize_path('D:/äpp'))

    def test_known_path_key_is_stable(self):
        """固定路径的实例键不得漂移，锁定与 C 启动器共用的算法约定"""
        from instance_key import compute_instance_key

        self.assertEqual(
            compute_instance_key(Path(r'C:\Program Files\Color Card')),
            'd2b3b671bf09f8e2',
        )
