#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
道归文库 · 独立页面生成器
"""

import json
import os
import html as html_mod
from urllib.parse import quote

LIB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "道归")
INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daogui_index.json")


def generate_lib_page(category=None, doc_id=None):
    """生成文库HTML页面"""
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        index = json.load(f)

    if doc_id:
        return _render_doc(doc_id)
    if category:
        return _render_category(index, category)
    return _render_index(index)


def _render_index(index):
    """目录页"""
    cards = ""
    icon_map = {
        "道归核心": "🏛", "基准键定理": "🎯", "惧亡主义": "⚖️",
        "AI与硅基理论": "🤖", "治理与信任协议": "🏗", "认知与教育": "🧠",
        "方法论": "🔬", "基础理论": "🌱", "文学作品": "📝", "其他": "📄"
    }
    for cat_name, docs in index.items():
        total_wc = sum(d['chars'] for d in docs)
        icon = icon_map.get(cat_name, "📄")
        cards += f'''
        <a href="?cat={quote(cat_name)}" class="cat-card">
          <div class="cat-icon">{icon}</div>
          <div class="cat-name">{html_mod.escape(cat_name)}</div>
          <div class="cat-count">{len(docs)}篇 · {total_wc//1000}k字</div>
        </a>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🔥 道归文库 — 莫名心</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#16161a; color:#ece8dc; font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif; padding:20px; max-width:720px; margin:0 auto; }}
.header {{ text-align:center; padding:30px 0 10px; }}
.header h1 {{ font-size:24px; letter-spacing:2px; }}
.header .sub {{ font-size:13px; color:#8a7a62; margin-top:4px; }}
.back {{ display:inline-block; margin:8px 0 16px; color:#b0a898; text-decoration:none; font-size:14px; }}
.back:hover {{ color:#ece8dc; }}
.cat-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.cat-card {{ display:block; background:#1e1e24; border-radius:14px; padding:20px; text-decoration:none; color:#ece8dc; border:1px solid #2a2a30; transition:all 0.2s; }}
.cat-card:hover {{ background:#2a2a30; border-color:#d86050; transform:translateY(-2px); }}
.cat-icon {{ font-size:32px; margin-bottom:8px; }}
.cat-name {{ font-size:16px; font-weight:600; margin-bottom:4px; }}
.cat-count {{ font-size:12px; color:#8a7a62; }}
.doc-list {{ list-style:none; }}
.doc-item {{ display:block; padding:14px 16px; margin-bottom:8px; background:#1e1e24; border-radius:10px; text-decoration:none; color:#ece8dc; border:1px solid #2a2a30; transition:all 0.15s; }}
.doc-item:hover {{ background:#2a2a30; border-color:#d86050; }}
.doc-title {{ font-size:15px; font-weight:500; }}
.doc-meta {{ font-size:12px; color:#8a7a62; margin-top:4px; }}
.doc-content {{ background:#1a1a1e; border-radius:12px; padding:24px; line-height:1.8; font-size:15px; white-space:pre-wrap; word-wrap:break-word; }}
.doc-content h1 {{ font-size:20px; margin:20px 0 10px; color:#d86050; }}
.doc-content h2 {{ font-size:17px; margin:16px 0 8px; color:#d0b050; }}
.doc-content h3 {{ font-size:15px; margin:12px 0 6px; color:#5a9a6a; }}
.footer {{ text-align:center; font-size:12px; color:#5a5a5a; padding:30px 0; }}
@media(max-width:480px){{ .cat-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="header">
  <a href="/" class="back" style="margin-bottom:8px;display:inline-block;">← 返回小站</a>
  <h1>🔥 道归文库</h1>
  <div class="sub">莫名心的全部思想 · 守护与传递</div>
</div>
<div class="cat-grid">{cards}</div>
<div class="footer"><a href="/" style="color:#5a5a5a;text-decoration:none;">← 返回小站</a> · 🌙 此处可拆；此处可乐；此处可诗</div>
</body>
</html>'''


def _render_category(index, category):
    """分类页面"""
    docs = index.get(category, [])
    doc_list = ""
    for d in docs:
        title = d.get("title", "无标题") or "无标题"
        fname = d.get("file", "")
        # 直接传完整文件名（去掉 .md 后缀），保证 _render_doc 精确匹配，杜绝张冠李戴
        doc_key = fname[:-3] if fname.endswith('.md') else fname
        doc_list += f'''
        <a href="?cat={quote(category)}&doc={quote(doc_key)}" class="doc-item">
          <div class="doc-title">{html_mod.escape(title[:60])}</div>
          <div class="doc-meta">{d.get("chars", 0)}字</div>
        </a>'''
    if not doc_list:
        doc_list = '<div style="text-align:center;padding:40px;color:#8a7a62;">此分类暂无文档</div>'

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html_mod.escape(category)} — 道归文库</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#16161a; color:#ece8dc; font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif; padding:20px; max-width:720px; margin:0 auto; }}
.header {{ padding:20px 0 12px; }}
.back {{ color:#b0a898; text-decoration:none; font-size:14px; }}
.back:hover {{ color:#ece8dc; }}
h1 {{ font-size:20px; margin:8px 0; }}
.doc-list {{ margin-top:12px; }}
.doc-item {{ display:block; padding:14px 16px; margin-bottom:8px; background:#1e1e24; border-radius:10px; text-decoration:none; color:#ece8dc; border:1px solid #2a2a30; transition:all 0.15s; }}
.doc-item:hover {{ background:#2a2a30; border-color:#d86050; }}
.doc-title {{ font-size:15px; font-weight:500; }}
.doc-meta {{ font-size:12px; color:#8a7a62; margin-top:4px; }}
.footer {{ text-align:center; font-size:12px; color:#5a5a5a; padding:30px 0; }}
</style>
</head>
<body>
<div class="header">
  <a href="/daogui" class="back">← 目录</a>
  <span style="margin:0 8px;color:#5a5a5a;">|</span>
  <a href="/" class="back">← 小站</a>
  <h1>{html_mod.escape(category)}</h1>
  <div style="font-size:13px;color:#8a7a62;">{len(docs)}篇</div>
</div>
<div class="doc-list">{doc_list}</div>
<div class="footer"><a href="/" style="color:#5a5a5a;text-decoration:none;">← 返回小站</a> · 🌙 此处可拆；此处可乐；此处可诗</div>
</body>
</html>'''


from md_render_js import MD_RENDER_JS


def _render_doc(doc_id):
    """文档阅读页（mdRender 前端渲染，米白暖色）"""
    # 1) 优先精确匹配：doc_id 本身或 +.md
    fname = doc_id
    if not fname.endswith('.md'):
        fname += '.md'

    filepath = os.path.join(LIB_DIR, fname)

    # 2) 找不到精确文件时，才用模糊匹配（仅限“唯一命中”，有歧义不猜）
    if not os.path.isfile(filepath):
        base_key = doc_id.rsplit('_', 1)[0] if '_' in doc_id else doc_id
        base_key = base_key.replace('.md', '')
        # 精确文件名 == base_key（去掉日期/hash 后缀）优先
        exact_hits = []
        loose_hits = []
        for f in os.listdir(LIB_DIR):
            if f.endswith('.md'):
                stem = f[:-3]
                if stem == base_key:
                    exact_hits.append(f)
                elif base_key in f:
                    loose_hits.append(f)
        # 唯一精确命中 → 用它；否则若存在“唯一包含命中”才用，多义则放弃（避免点20批跳到9批）
        if len(exact_hits) == 1:
            filepath = os.path.join(LIB_DIR, exact_hits[0])
        elif len(loose_hits) == 1:
            filepath = os.path.join(LIB_DIR, loose_hits[0])
        # 否则保持 filepath 为不存在的精确路径（文档未找到）

    content = ""
    title = "文档未找到"
    if os.path.isfile(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.strip().split('\n')
        title = lines[0].strip('# \t\r')[:80] if lines else "无标题"

    import json as _json
    safe_title = html_mod.escape(title)
    body_json = _json.dumps(content, ensure_ascii=False)
    md_js = MD_RENDER_JS

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{safe_title} — 道归文库</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#f7f2ec; color:#3d3a36; font-family:'PingFang SC','Hiragino Sans GB','Noto Sans SC',system-ui,sans-serif; padding:20px; max-width:720px; margin:0 auto; line-height:1.8; }}
.header {{ padding:14px 0; border-bottom:1px solid #e8dfd3; margin-bottom:20px; }}
.back {{ color:#a0522d; text-decoration:none; font-size:14px; }}
.back:hover {{ text-decoration:underline; }}
h1 {{ font-size:20px; margin-top:8px; color:#a0522d; }}
.content {{ background:#fffdf9; border:1px solid #e8dfd3; border-radius:14px; padding:22px 24px; box-shadow:0 2px 10px rgba(160,82,45,.08); font-size:15px; }}
.content table {{ width:100%; border-collapse:collapse; }}
.footer {{ text-align:center; font-size:12px; color:#b0a89c; padding:24px 0; border-top:1px solid #e8dfd3; margin-top:24px; }}
</style>
</head>
<body>
<div class="header">
  <a href="javascript:history.back()" class="back">← 返回</a>
  <span style="margin:0 8px;color:#b0a89c;">|</span>
  <a href="/" class="back">← 小站</a>
  <span style="margin:0 4px;color:#b0a89c;">·</span>
  <a href="/daogui" class="back">目录</a>
</div>
<h1>{safe_title}</h1>
<div class="content" id="dgBody"></div>
<div class="footer">🌙 此处可拆；此处可乐；此处可诗</div>
<script>{md_js}
document.getElementById('dgBody').innerHTML = mdRender({body_json});
</script>
</body>
</html>'''
