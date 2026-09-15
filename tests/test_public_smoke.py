import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('public_smoke',Path(__file__).resolve().parents[1]/'scripts/public_smoke.py')
smoke=importlib.util.module_from_spec(spec);spec.loader.exec_module(smoke)

class ReadbackNormalizationTests(unittest.TestCase):
    def test_wechat_data_src_resize_is_same_asset(self):
        original='http://mmbiz.qpic.cn/sz_mmbiz_png/asset-one/0?from=appmsg'
        html='<section><img data-src="https://mmbiz.qpic.cn/sz_mmbiz_png/asset-one/640?from=appmsg"></section>'
        sources=smoke.image_sources(html)
        self.assertEqual(len(sources),1)
        self.assertTrue(smoke.same_wechat_asset(sources[0],original))

    def test_other_image_and_other_host_are_rejected(self):
        original='https://mmbiz.qpic.cn/sz_mmbiz_png/asset-one/0'
        for candidate in ['https://mmbiz.qpic.cn/sz_mmbiz_png/asset-two/640','https://example.com/sz_mmbiz_png/asset-one/0']:
            self.assertFalse(smoke.same_wechat_asset(candidate,original))

    def test_img_count_and_actual_data_source(self):
        self.assertEqual(smoke.image_sources('<img src="fallback" data-src="actual"><img src="second">'),['actual','second'])

if __name__=='__main__':unittest.main()
