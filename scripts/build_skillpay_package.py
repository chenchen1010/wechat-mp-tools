#!/usr/bin/env python3
"""Build a self-contained buyer package from an explicit, secret-free allowlist."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / 'skills/publish/wechat-article'
SLUG = 'wechat-content-studio'


def build(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = output / SLUG
    package.mkdir(exist_ok=False)
    for name in ['publish.py', 'article_html.py', 'newspic.py', 'requirements.txt', 'references/image-prompts.md']:
        dest = package / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PUBLISH / name, dest)
    (package / 'scripts').mkdir()
    shutil.copy2(ROOT / 'skills/layout-clone/scripts/extract_wechat_layout.py', package / 'scripts/extract_wechat_layout.py')
    shutil.copy2(ROOT / '.env.example', package / '.env.example')
    (package / '.gitignore').write_text('.env\n.env.local\n.venv/\n__pycache__/\noutput/\n*.draft.json\n*.lock\n')

    skill = (PUBLISH / 'SKILL.md').read_text()
    skill = skill.replace('name: wechat-article-publish', 'name: ' + SLUG).replace('slug: wechat-article-publish', 'slug: ' + SLUG)
    skill = skill.replace('displayName: 微信公众号文章与贴图发布', 'displayName: 公众号排版配图发布助手')
    skill = skill.replace('version: 1.4.1', 'version: 1.0.0')
    skill = skill.replace('description: 适用于微信公众号文章或贴图', 'description: 适用于微信公众号参考排版复刻、文章或贴图')
    marker = '## 本机运行环境'
    skill = skill.replace(marker, '''## 一次完成排版、配图和草稿

- 用户要 Copy 参考文章排版时，读取 [排版复刻](references/layout-clone.md)，运行本包 `scripts/extract_wechat_layout.py`。根据提取样式归纳主题、应用到新文章，再用本包 `publish.py --html` 推送。
- 用户要封面、插图或贴图时，读取 [配图流程](references/image-prompts.md)，让当前 Agent 生成真实图片；无法生图时按说明引导安装指定 Image2 Skill。
- 用户要推送文章或贴图时，按下方本地凭证、预检、上传和回读流程执行。文章与贴图都只进入草稿箱，公开发布另需用户授权。

'''+marker)
    # Buyer package keeps only buyer operations, not server administration guidance.
    start = skill.index('## 服务方运行要求')
    end = skill.index('## Before Creating Or Updating Drafts', start)
    skill = skill[:start] + skill[end:]
    skill = skill.replace('本地回归：在仓库根目录运行 `python3 -m unittest discover -s tests -v` 和 `node --test tests/request-credentials.test.mjs`。', '')
    (package / 'SKILL.md').write_text(skill)

    layout = (ROOT / 'skills/layout-clone/SKILL.md').read_text().split('---', 2)[2].lstrip()
    layout = layout.replace('/path/to/wechat-layout-clone', '/path/to/wechat-content-studio')
    layout = layout.replace('本 skill 目录', '本技能包根目录')
    (package / 'references/layout-clone.md').write_text(layout)
    (package / 'README.md').write_text('''# 公众号排版配图发布助手

一次购买完整 Skill，帮你把参考版式、新文章和配图整理成可预览的公众号草稿。

## 包含什么

- Copy 参考公众号文章的版式，归纳可复用主题，应用到自己的新内容。
- 准备封面、正文插图和贴图的提示词，由当前 Agent 可用的生图能力出图。
- Markdown / HTML 文章、本地正文图片、封面和多张贴图上传到你自己的公众号草稿箱，并回读检查。
- 当前 Agent 无法生图时，引导安装 Image2生图【星元科技·Firefly·出品】：@user_34e6449f/xy-image2-1k。

## 首次使用

1. 将整个文件夹安装到当前 Agent 实际使用的 skills 目录，重新加载后让 Agent 读取 SKILL.md。
2. 需要 Python3.10+。在本包根目录创建虚拟环境并安装 requirements.txt。
3. 将 .env.example 复制为本机私有 .env，填写你自己公众号的 AppID、AppSecret，以及服务方提供的服务访问凭证。保持文件仅自己可读写，不上传到 Git。
4. 在自己公众号的开发配置中，将服务器公网 IP 8.153.207.214 追加到白名单。账号须具备微信对应素材和草稿权限。
5. 告诉 Agent：“参考这篇文章的排版，为我的新文章准备配图，并推送到我的公众号草稿箱。”

## 使用范围

售价9.99元，买断完整 Skill 文件。当前 Agent 或第三方生图工具的额度、订阅和生成费用不包含在本 Skill 售价内。图片能力以当前环境实际可用的工具为准。

公众号凭证保留在你本机，每次请求经 HTTPS 临时发送给固定 IP 服务使用。服务器不保存买家公众号凭证，不需要卖家绑定你的公众号。服务访问凭证与公众号 AppSecret 是两回事，不包含在此公共交付包内。

排版是根据可提取样式近似还原，微信可能过滤部分样式。遇到参考链接无法读取时可使用已保存的本地 HTML。推送成功仅表示草稿已核验，不代表文章已公开发布或群发。
''')
    files = sorted(p for p in package.rglob('*') if p.is_file())
    forbidden = {'.env', '.env.local', '.DS_Store'}
    assert all(p.name not in forbidden and '.venv' not in p.parts and '__pycache__' not in p.parts for p in files)
    archive = output / (SLUG + '-1.0.0.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, str(Path(SLUG) / p.relative_to(package)))
    manifest = {'package': archive.name, 'bytes': archive.stat().st_size,
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'files': [str(p.relative_to(package)) for p in files]}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    build(parser.parse_args().output)
