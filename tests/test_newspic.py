import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/publish/wechat-article'))
import newspic
import publish as article_publish


class PictureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.paths = [self.root/'1.png', self.root/'2.jpg']
        for path, color in zip(self.paths, ['red', 'blue']):
            Image.new('RGB', (8, 8), color).save(path)
        self.images = newspic.prepare('测试', '第一行\n第二行', self.paths)
        self.receipt = self.root/'receipt.json'
        self.calls = []

    def api(self, base, token, endpoint, payload):
        self.calls.append((endpoint, payload))
        if endpoint.endswith('add_material'):
            return {'media_id': 'img' + str(len(self.calls))}
        if endpoint.endswith('/add'):
            self.article = payload['articles'][0]
            return {'media_id': 'draft1'}
        return {'news_item': [self.article]}

    def run_publish(self, api=None):
        return newspic.publish(api or self.api, 'https://example.test', 'secret', 'default',
                               '测试', '第一行\n第二行', self.images, self.receipt)

    def test_success_and_second_run_is_read_only(self):
        result = self.run_publish()
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(self.article['image_info']['image_list'],
                         [{'image_media_id': 'img1'}, {'image_media_id': 'img2'}])
        self.assertNotIn('thumb_media_id', self.article)
        self.assertEqual(result['verification']['image_count'], 2)
        self.run_publish()
        self.assertEqual([e for e, _ in self.calls].count('/wechat/draft/add'), 1)
        self.assertEqual(len(self.calls), 5)
        self.assertNotIn('secret', self.receipt.read_text())

    def test_bad_input_before_network(self):
        cases = [('','text',self.paths), ('字'*33,'text',self.paths),
                 ('ok','字'*683,self.paths), ('ok','<p>html</p>',self.paths),
                 ('ok','text',[]), ('ok','text',self.paths*11),
                 ('ok','text',[self.paths[0]]*2)]
        for title, content, paths in cases:
            with self.subTest(title=title, count=len(paths)), self.assertRaises(ValueError):
                newspic.prepare(title, content, paths)

    def test_invalid_and_truncated_image(self):
        bad = self.root/'bad.png'
        for data in [b'not an image', self.paths[0].read_bytes()[:40]]:
            bad.write_bytes(data)
            with self.assertRaises(Exception):
                newspic.prepare('ok', 'text', [bad])

    def test_oversize_and_wrong_format(self):
        bad = self.root/'bad.gif'
        Image.new('RGB', (8, 8)).save(bad)
        with self.assertRaises(ValueError):
            newspic.prepare('ok', 'text', [bad])
        with bad.open('wb') as f:
            f.truncate(10*1024*1024)
        with self.assertRaises(ValueError):
            newspic.prepare('ok', 'text', [bad])

    def test_upload_error_never_creates_partial_draft(self):
        mock = Mock(side_effect=[{'media_id':'one'}, {'errcode':40009, 'errmsg':'do not log'}])
        with self.assertRaises(RuntimeError):
            self.run_publish(mock)
        self.assertEqual(mock.call_count, 2)
        self.assertEqual(json.loads(self.receipt.read_text())['image_media_ids'], ['one'])
        with self.assertRaises(RuntimeError):
            self.run_publish(mock)
        self.assertEqual(mock.call_count, 2)

    def test_create_timeout_blocks_resubmission(self):
        mock = Mock(side_effect=[{'media_id':'one'}, {'media_id':'two'}, TimeoutError()])
        with self.assertRaises(TimeoutError):
            self.run_publish(mock)
        self.assertEqual(json.loads(self.receipt.read_text())['status'], 'creating_or_unknown')
        with self.assertRaises(RuntimeError):
            self.run_publish(mock)
        self.assertEqual(mock.call_count, 3)

    def test_read_failure_can_resume_without_creating(self):
        def fail_read(*args):
            if args[2].endswith('/get'):
                raise TimeoutError()
            return self.api(*args)
        with self.assertRaises(TimeoutError):
            self.run_publish(fail_read)
        self.assertEqual(json.loads(self.receipt.read_text())['status'], 'created_unverified')
        self.run_publish()
        self.assertEqual(len(self.calls), 4)

    def test_verification_rejects_type_content_title_and_order(self):
        for field, value in [('article_type','news'), ('content','wrong'), ('title','wrong'),
                             ('image_info', {'image_list':[{'image_media_id':'two'}, {'image_media_id':'one'}]})]:
            with self.subTest(field=field):
                item={'article_type':'newspic','title':'t','content':'c',
                      'image_info':{'image_list':[{'image_media_id':'one'}, {'image_media_id':'two'}]}}
                item[field]=value
                with self.assertRaises(RuntimeError):
                    newspic.verify_draft(Mock(return_value={'news_item':[item]}), '', '', '', '', 't','c',['one','two'])

    def test_receipt_cannot_change_account(self):
        self.run_publish()
        with self.assertRaises(ValueError):
            newspic.publish(self.api,'https://example.test','secret','other','测试','第一行\n第二行',self.images,self.receipt)
        self.assertEqual(len(self.calls), 4)

    def test_lock_blocks_concurrent_request(self):
        self.receipt.with_name('receipt.json.lock').touch()
        with self.assertRaises(RuntimeError):
            self.run_publish()
        self.assertEqual(self.calls, [])

    def test_upstream_error_is_not_success(self):
        for result in [{'errcode':40007}, {'ok':False}, []]:
            with self.assertRaises(RuntimeError):
                newspic.checked(result)

    def test_cli_refuses_unbound_account(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {'WECHAT_MP_CREDENTIAL_MODE':'legacy'}, clear=True), patch.object(article_publish, 'load_env'), \
             patch.object(sys, 'argv', ['publish.py', '--type', 'newspic']), \
             patch('newspic.run') as run:
            with self.assertRaises(SystemExit) as error:
                article_publish.main()
            self.assertEqual(error.exception.code, 2)
            run.assert_not_called()

    def test_cli_uses_buyer_account_config_and_explicit_override(self):
        import os
        from unittest.mock import patch
        for extra, expected in [([], 'buyer-account'), (['--account', 'second-account'], 'second-account')]:
            with self.subTest(expected=expected), \
                 patch.dict(os.environ, {'WECHAT_MP_API_ACCOUNT_DEFAULT':'buyer-account', 'WECHAT_MP_CREDENTIAL_MODE':'legacy'}, clear=True), \
                 patch.object(article_publish, 'load_env'), \
                 patch.object(sys, 'argv', ['publish.py', '--type', 'newspic'] + extra), \
                 patch('newspic.run') as run:
                article_publish.main()
                self.assertEqual(run.call_args.args[0].account, expected)

    def test_buyer_credentials_sent_only_as_headers(self):
        import io, os
        from unittest.mock import patch
        values = {'WECHAT_MP_APP_ID':'wx'+'A'*16, 'WECHAT_MP_APP_SECRET':'a'*32}
        opener = Mock()
        opener.open.side_effect = [io.BytesIO(b'{"credential_mode":"request"}'), io.BytesIO(b'{"media_id":"draft"}')]
        with patch.dict(os.environ, values, clear=True), patch.object(article_publish.urllib.request, 'build_opener', return_value=opener):
            article_publish.api_post('https://service.example','proxy-token','/wechat/draft/add',{'account':'default','articles':[]})
        req = opener.open.call_args_list[1].args[0]
        self.assertEqual(req.get_header('X-wechat-appid'), values['WECHAT_MP_APP_ID'])
        self.assertEqual(req.get_header('X-wechat-appsecret'), values['WECHAT_MP_APP_SECRET'])
        self.assertIsNone(req.get_header('Authorization'))
        self.assertNotIn('account', json.loads(req.data))
        self.assertNotIn(values['WECHAT_MP_APP_SECRET'], req.full_url)
        self.assertNotIn(values['WECHAT_MP_APP_SECRET'], req.data.decode())

    def test_buyer_client_refuses_legacy_server_before_sending_secrets(self):
        import io, os
        from unittest.mock import patch
        opener = Mock()
        opener.open.return_value = io.BytesIO(b'{"ok":true,"accounts":["default"]}')
        with patch.dict(os.environ, {'WECHAT_MP_APP_ID':'wx'+'A'*16,'WECHAT_MP_APP_SECRET':'a'*32}, clear=True), \
             patch.object(article_publish.urllib.request, 'build_opener', return_value=opener):
            with self.assertRaises(RuntimeError):
                article_publish.api_post('https://service.example','token','/wechat/draft/add',{})
        self.assertEqual(opener.open.call_count, 1)
        self.assertIsInstance(opener.open.call_args.args[0], str)

    def test_buyer_client_refuses_http_and_redirects(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            article_publish.api_post('http://service.example','token','/wechat/draft/add',{})
        with self.assertRaises(RuntimeError):
            article_publish.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example')

    def test_buyer_mode_identity_comes_from_local_appid(self):
        import os
        from unittest.mock import patch
        identities = []
        for character in ['A', 'B']:
            with patch.dict(os.environ, {'WECHAT_MP_APP_ID':'wx'+character*16,'WECHAT_MP_APP_SECRET':'a'*32}, clear=True), \
                 patch.object(article_publish, 'load_env'), \
                 patch.object(sys, 'argv', ['publish.py','--type','newspic']), patch('newspic.run') as run:
                article_publish.main()
                identities.append(run.call_args.args[0].account)
        self.assertNotEqual(*identities)
        self.assertTrue(all(value.startswith('appid-sha256:') for value in identities))

    def test_explicit_local_env_overrides_previous_account(self):
        import os
        from unittest.mock import patch
        env_file = self.root / 'buyer.env'
        env_file.write_text('WECHAT_MP_APP_ID=wx' + 'B'*16 + '\nWECHAT_MP_APP_SECRET=' + 'b'*32 + '\n')
        with patch.dict(os.environ, {'WECHAT_MP_APP_ID':'wx'+'A'*16,'WECHAT_MP_APP_SECRET':'a'*32}, clear=True):
            article_publish.load_env(env_file)
            self.assertEqual(article_publish.request_credentials(), ('wx'+'B'*16, 'b'*32))
            with self.assertRaises(ValueError):
                article_publish.load_env(self.root/'missing.env')

    def test_article_path_preserved(self):
        from unittest.mock import patch
        with patch.object(article_publish, 'api_post', return_value={'media_id':'article'}) as mock:
            article = {'title':'文章', 'content':'<p>正文</p>', 'thumb_media_id':'cover'}
            self.assertEqual(article_publish.create_draft('https://example.test','secret','default',article), {'media_id':'article'})
            self.assertEqual(mock.call_args.args[3], {'account':'default','articles':[article]})
        meta, body = article_publish.parse_frontmatter('---\ntitle: 测试\n---\n## 标题')
        self.assertEqual(meta['title'], '测试')
        self.assertIn('<h2>标题</h2>', article_publish.markdown_to_html(body))

if __name__ == '__main__':
    unittest.main()
