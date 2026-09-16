import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/publish/wechat-article'))
import importlib.util
_spec=importlib.util.spec_from_file_location('standalone_evolink',ROOT/'skills/evolink-nano-banana-2/scripts/evolink_image.py')
evo=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(evo)
import article_html

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.out=Path(self.tmp.name)/'image.png'
        buf=io.BytesIO();Image.new('RGB',(20,12),'red').save(buf,format='PNG');self.data=buf.getvalue()
    def test_async_completion_resume_and_cost(self):
        calls=[]
        def api(key,method,path,body=None):
            calls.append((method,path))
            if method=='POST':return {'id':'task-test','status':'pending','usage':{'credits_reserved':5}}
            return {'id':'task-test','status':'completed','results':['https://example.test/image.png'],'usage':{'credits_used':4}}
        with patch.object(evo.urllib.request,'urlopen',return_value=io.BytesIO(self.data)):
            state=evo.generate('private-key','test',self.out,api=api)
        self.assertEqual(state['dimensions'],[20,12]);self.assertEqual(state['usage']['credits_used'],4)
        evo.generate('private-key','test',self.out,api=api)
        self.assertEqual(len(calls),2)
        self.assertNotIn('private-key',self.out.with_suffix('.generation.json').read_text())
    def test_unknown_submit_is_not_retried(self):
        calls=[]
        def api(*args):calls.append(args);raise RuntimeError('connection lost')
        for _ in range(2):
            with self.assertRaises(RuntimeError):evo.generate('key','test',self.out,api=api)
        self.assertEqual(len(calls),1)
    def test_known_task_resumes_without_submission(self):
        def api(key,method,path,body=None):
            if method=='POST':return {'id':'task-test','status':'pending'}
            return {'id':'task-test','status':'completed','result_data':[{'url':'https://example.test/image.png'}]}
        state=evo.generate('key','test',self.out,api=api,poll=False)
        self.assertEqual(state['task_id'],'task-test')
        def resume(key,method,path,body=None):
            self.assertEqual(method,'GET');return api(key,method,path,body)
        with patch.object(evo.urllib.request,'urlopen',return_value=io.BytesIO(self.data)):
            self.assertEqual(evo.generate('key','test',self.out,api=resume)['status'],'downloaded')
    def test_corrupt_result_not_success(self):
        def api(key,method,path,body=None):
            return {'id':'task-test','status':'completed','results':['https://example.test/bad.png']}
        # Initial completion still needs querying to acquire results (submission has results too).
        with patch.object(evo.urllib.request,'urlopen',return_value=io.BytesIO(b'bad')):
            with self.assertRaises(Exception):evo.generate('key','test',self.out,api=api)
        self.assertNotEqual(json.loads(self.out.with_suffix('.generation.json').read_text())['status'],'downloaded')
    def test_html_keeps_styles_uploadable_images_and_removes_active_content(self):
        self.out.write_bytes(self.data)
        soup,files=article_html.prepare_html('<h2 style="color:#a00">新内容</h2><script>alert(1)</script><pre>code</pre><img src="image.png" onerror="alert(1)"><a href="javascript:alert(1)">link</a>',self.out.parent)
        s=str(soup)
        self.assertIn('color:#a00',s);self.assertEqual(files['image.png'],self.out.resolve())
        for forbidden in ['<script','<pre','<code','onerror','javascript:']:self.assertNotIn(forbidden,s)
    def test_missing_images_fail_before_network(self):
        with self.assertRaises(ValueError):article_html.prepare_html('<img src="absent.png">',self.out.parent)

if __name__=='__main__':unittest.main()

class LayoutExtractionTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('layout_extract',ROOT/'skills/layout-clone/scripts/extract_wechat_layout.py')
        self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)
    def test_hidden_lazy_root_does_not_hide_child_styles(self):
        from bs4 import BeautifulSoup
        soup=BeautifulSoup('<div id="js_content" style="visibility:hidden;opacity:0"><p style="color: red">正文</p><script style="color:blue">ignored</script></div>','html.parser')
        rows,counts=self.mod.walk_collect_styles(soup.div,220)
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['style'],'color: red')
    def test_risk_page_detected(self):
        self.assertTrue(self.mod.looks_like_wechat_block('<h1>环境异常</h1>'))
        self.assertFalse(self.mod.looks_like_wechat_block('<p>正常正文</p>'))

class ArticleWorkflowTests(unittest.TestCase):
    def test_markdown_blocks_table_local_image_and_code(self):
        import publish
        from bs4 import BeautifulSoup
        html=publish.markdown_to_html('## 标题\n\n正文 **加粗**\n\n|列|值|\n|---|---|\n|A|1|\n\n```text\nhello\nworld\n```')
        soup,_=article_html.prepare_html(html,'.')
        self.assertIsNotNone(soup.h2);self.assertIsNotNone(soup.table)
        self.assertIn('hello\nworld',soup.get_text());self.assertIsNone(soup.pre);self.assertIsNone(soup.code)
    def test_html_receipt_rerun_never_recreates(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);im=root/'im.png';Image.new('RGB',(20,12),'red').save(im)
            source=root/'article.html';source.write_text('<p style="color:#333">新的文章</p><img src="im.png">')
            args=SimpleNamespace(html=str(source),cover=str(im),title='测试',author='测试',account='buyer-hash',receipt=str(root/'receipt.json'))
            calls=[];holder={}
            def create(*a):calls.append('create');holder.update(a[-1]);return {'media_id':'draft1'}
            def api(*a):return {'news_item':[holder]}
            publisher=SimpleNamespace(upload_body_image=lambda *a:'https://mmbiz.qpic.cn/mmbiz_png/asset/0',upload_cover=lambda *a:'cover1',create_draft=create,api_post=api)
            with patch.dict('os.environ',{'WECHAT_MP_API_BASE_URL':'https://example.test'}):
                a=article_html.run(args,publisher);b=article_html.run(args,publisher)
            self.assertEqual(calls,['create']);self.assertEqual(a['status'],'verified');self.assertEqual(b['image_count'],1)

class AgentImageHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.md=self.root/'article.md'
        self.md.write_text('---\ntitle: 周末读书\n---\n一本书，一段安静的时间。')
        self.env={'WECHAT_MP_CREDENTIAL_MODE':'request','WECHAT_MP_APP_ID':'wx'+'a'*16,
                  'WECHAT_MP_APP_SECRET':'b'*32,'WECHAT_MP_API_BASE_URL':'https://example.test'}
    def test_missing_cover_hands_off_even_if_old_provider_key_exists(self):
        import publish
        output=io.StringIO()
        with patch.dict('os.environ',{**self.env,'EVOLINK_API_KEY':'unused-old-key'},clear=True), \
             patch.object(sys,'argv',['publish.py','-m',str(self.md),'--cover-prompt','书与茶杯，暖色摄影，无文字']), \
             patch.object(publish,'load_env'), patch.object(publish.urllib.request,'urlopen') as network, \
             patch('sys.stdout',output):
            with self.assertRaises(SystemExit) as ex: publish.main()
        self.assertEqual(ex.exception.code,2);network.assert_not_called()
        result=json.loads(output.getvalue()[output.getvalue().index('{'):])
        self.assertEqual(result['status'],'needs_image')
        self.assertEqual(result['prompt'],'书与茶杯，暖色摄影，无文字')
        self.assertFalse(self.md.with_suffix('.cover.png').exists())
        self.assertFalse(self.md.with_suffix('.draft.json').exists())
    def test_agent_image_resumes_publication_without_provider_key(self):
        import publish
        image=self.root/'agent-cover.png';Image.new('RGB',(20,12),'green').save(image)
        with patch.dict('os.environ',self.env,clear=True), \
             patch.object(sys,'argv',['publish.py','-m',str(self.md),'--cover',str(image)]), \
             patch.object(publish,'load_env'), patch.object(article_html,'run') as run, \
             patch('sys.stdout',io.StringIO()):
            publish.main()
        self.assertEqual(run.call_count,1)
        self.assertEqual(Path(run.call_args.args[0].cover),image.resolve())
        self.assertTrue(Path(run.call_args.args[0].html).is_file())
