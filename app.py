#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心哥小站 · Flask 重装甲版 🌙
多线程 + 密码锁 + 全部原有功能
"""

import sys, os, json, hashlib, uuid
from datetime import timedelta

# 导入原本的完整小站
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xin_web_server import (
    HTML_PAGE, get_yunqi_data, search_knowledge_refs, ai_ask,
    _本地五运六气, DiagnoseHandler, _get_ai_key,
)

# Flask
from flask import Flask, request, jsonify, session, redirect, make_response
from waitress import serve

app = Flask(__name__)
app.secret_key = "mo-ming-xin-xiao-zhan-2026-07-26"
app.permanent_session_lifetime = timedelta(hours=4)

# ── 密码配置 ──
# 在运行目录下放一个 密码.json 文件，内容 {"密码": "你的密码"}
# 如果没有，默认密码是下面的 fallback
_PWD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "密码.json")
_LOGIN_PASSWORD = "123456"  # 默认密码，建议改掉

if os.path.isfile(_PWD_FILE):
    try:
        with open(_PWD_FILE, "r") as f:
            _PWD_FILE_DATA = json.load(f)
            if "密码" in _PWD_FILE_DATA and _PWD_FILE_DATA["密码"]:
                _LOGIN_PASSWORD = _PWD_FILE_DATA["密码"]
    except:
        pass


# ── 登录页面 HTML ──
_LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>莫名心 · 小站</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{
  font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;
  background:#f5f0eb;color:#2c2c2c;min-height:100vh;
  display:flex;align-items:center;justify-content:center;
}
body.dark{
  background:#16161a;color:#ece8dc;
}
.card{
  background:#fff;border-radius:18px;padding:40px 32px;
  width:340px;box-shadow:0 4px 24px rgba(0,0,0,0.08);
  text-align:center;
}
body.dark .card{
  background:#1e1e24;box-shadow:0 4px 24px rgba(0,0,0,0.3);
}
h1{font-size:22px;font-weight:600;margin-bottom:4px;}
.sub{font-size:13px;color:#888;margin-bottom:24px;}
input{
  width:100%;padding:14px 16px;border:2px solid #ddd;
  border-radius:12px;font-size:16px;outline:none;
  text-align:center;margin-bottom:14px;box-sizing:border-box;
  font-family:inherit;
}
body.dark input{
  background:#2a2a30;border-color:#3a3a40;color:#ece8dc;
}
input:focus{border-color:#b8453a;}
button{
  width:100%;padding:14px;background:#b8453a;color:white;
  border:none;border-radius:12px;font-size:16px;font-weight:500;
  cursor:pointer;transition:background 0.2s;
}
button:hover{background:#a03a30;}
.error{color:#c0392b;font-size:14px;margin-top:10px;display:none;}
</style>
</head>
<body>
<div class="card">
  <h1>🌙 莫名心 · 小站</h1>
  <div class="sub">你需要密码才能进入</div>
  <form method="post" action="/login" id="loginForm">
    <input type="password" name="password" placeholder="输入密码" autofocus>
    <button type="submit">进入</button>
  </form>
  <div class="error" id="errorMsg">密码错误，再试试</div>
</div>
<script>
document.getElementById('loginForm').onsubmit = async function(e){
  e.preventDefault();
  const pwd = this.querySelector('input').value;
  const res = await fetch('/login', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({password:pwd})
  });
  if(res.ok) { window.location.href = '/'; }
  else { document.getElementById('errorMsg').style.display = 'block'; }
};
// 跟小站一样的深色主题
if(window.matchMedia('(prefers-color-scheme:dark)').matches){
  document.body.classList.add('dark');
}
</script>
</body>
</html>"""


# ── 鉴权装饰器 ──
def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            # AJAX 请求返回 401，页面请求返回登录页
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"error": "未登录"}), 401
            return _LOGIN_HTML
        return f(*args, **kwargs)
    return wrapper


# ── 路由 ──

@app.route("/")
@login_required
def index():
    return HTML_PAGE


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    pwd = data.get("password", "") or request.form.get("password", "")
    if pwd == _LOGIN_PASSWORD:
        session.permanent = True
        session["logged_in"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "密码错误"}), 403


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect("/")


# ── 原有 API 接口 ──

@app.route("/yunqi", methods=["GET", "POST"])
@login_required
def yunqi():
    date_str = None
    if request.method == "POST":
        date_str = request.json.get("date") if request.json else None
    else:
        date_str = request.args.get("date")
    return jsonify(get_yunqi_data(date_str))


@app.route("/yunqi-v2", methods=["GET", "POST"])
@login_required
def yunqi_v2():
    date_str = None
    if request.method == "POST":
        date_str = request.json.get("date") if request.json else None
    else:
        date_str = request.args.get("date")
    try:
        from 五运六气 import 推算
        return jsonify(推算(date_str))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/yunqi-eval", methods=["GET", "POST"])
@login_required
def yunqi_eval():
    date_str = None
    plan = ""
    if request.method == "POST":
        date_str = request.json.get("date") if request.json else None
        plan = request.json.get("plan", "") if request.json else ""
    else:
        date_str = request.args.get("date")
        plan = request.args.get("plan", "")
    if plan:
        try:
            from 五运六气 import 推算
            from 五运六气.eval import 评价食疗方案
            r = 推算(date_str)
            ev = 评价食疗方案(r, plan)
            return jsonify({"success": True, "五运六气": r, "评价": ev})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "需要 plan 参数"}), 400


@app.route("/philosophy-fetch", methods=["POST"])
@login_required
def philosophy_fetch():
    from xin_web_server import handle_philosophy_fetch
    return jsonify(handle_philosophy_fetch(request.json or {}))


@app.route("/philosophy-translate", methods=["POST"])
@login_required
def philosophy_translate():
    from xin_web_server import handle_philosophy_translate
    return jsonify(handle_philosophy_translate(request.json or {}))


@app.route("/philosophy-concept", methods=["POST"])
@login_required
def philosophy_concept():
    from xin_web_server import handle_philosophy_concept
    return jsonify(handle_philosophy_concept(request.json or {}))


@app.route("/ask", methods=["POST"])
@login_required
def ask():
    data = request.json or {}
    question = data.get("question", "").strip()
    context = data.get("context", "")
    if not question:
        return jsonify({"success": False, "error": "需要 question 参数"}), 400
    result = ai_ask(question, context)
    # 自动检测概念问题，更新本地词条
    if result.get("success") and result.get("answer"):
        try:
            from xin_web_server import _本地词条_加载
            q_lower = question.lower()
            词条 = _本地词条_加载()
            for slug, entry in 词条.items():
                主名 = entry["主名"]
                if 主名.lower() in q_lower or 主名.lower() in result["answer"].lower():
                    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sep_core.json")
                    if os.path.isfile(sep_path):
                        with open(sep_path, "r", encoding="utf-8") as _sf:
                            sep_data = json.load(_sf)
                        if slug in sep_data:
                            old = sep_data[slug].get("_concept_zh", "").strip()
                            # 清理AI符号
                            import re as _re
                            new = result["answer"][:10000]
                            new = _re.sub(r'\*+|\#+|__|~~|```|``', '', new)
                            new = _re.sub(r'^>\s*', '', new, flags=_re.MULTILINE)
                            new = _re.sub(r'^[ \t]*[-*+]\s+', '', new, flags=_re.MULTILINE)
                            new = _re.sub(r'^\d+\.\s+', '', new, flags=_re.MULTILINE)
                            new = _re.sub(r'^[ \t]+', '', new, flags=_re.MULTILINE)
                            new = _re.sub(r'\n{3,}', '\n\n', new)
                            new = new.strip()
                            if old and len(old) > 50:
                                # 已有旧内容 → AI对比，智能补充
                                try:
                                    r = urllib.request.urlopen(urllib.request.Request(
                                        "https://api.deepseek.com/v1/chat/completions",
                                        data=json.dumps({
                                            "model": "deepseek-v4-flash",
                                            "messages": [
                                                {"role": "system", "content": "你帮用户完善哲学概念词条。旧内容和新回答都要保留精华。输出合并后的完整新版，不要加额外说明。"},
                                                {"role": "user", "content": f"旧版概念总结：\n{old[:2000]}\n\n新版AI回答：\n{new[:2000]}\n\n请合并两者的精华，输出一份更完整的版本。"}
                                            ],
                                            "max_tokens": 2000
                                        }).encode(),
                                        headers={"Content-Type": "application/json",
                                                 "Authorization": f"Bearer {_get_ai_key()}"}
                                    ), timeout=30).read().decode()
                                    merged = json.loads(r).get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                                    if merged and len(merged) > len(old):
                                        new = merged[:10000]
                                except Exception:
                                    pass  # 合并失败则用新回答
                            sep_data[slug]["_concept_zh"] = new
                            sep_data[slug]["_concept_name"] = 主名
                            with open(sep_path, "w", encoding="utf-8") as _sf:
                                json.dump(sep_data, _sf, ensure_ascii=False, indent=2)
                            result["concept_updated"] = 主名
                    break
        except Exception:
            pass
    return jsonify(result)


@app.route("/knowledge-search", methods=["GET", "POST"])
@login_required
def knowledge_search():
    query = ""
    if request.method == "POST":
        query = request.json.get("query", "") if request.json else ""
    else:
        query = request.args.get("query", "")
    results = search_knowledge_refs(query)
    return jsonify({"results": results})


@app.route("/philosophy")
@login_required
def philosophy():
    from xin_web_server import _本地词条_加载
    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sep_core.json")
    sep_data = {}
    if os.path.isfile(sep_path):
        with open(sep_path, "r", encoding="utf-8") as f:
            sep_data = json.load(f)
    # 合并本地词条
    词条 = _本地词条_加载()
    for slug, entry in 词条.items():
        主名 = entry["主名"]
        if slug in sep_data:
            alias_key = f"★{主名}"
            if alias_key not in sep_data:
                cz = sep_data[slug].get('_concept_zh', '')
                sep_data[alias_key] = {
                    "name": 主名,
                    "title": f"本地词条 → {slug}" + (f" · 别名: {'、'.join(entry['别名'])}" if entry.get('别名') else ""),
                    "body": cz or sep_data[slug].get('body_zh', '') or sep_data[slug].get('body', '')[:3000],
                    "body_en": sep_data[slug].get('body_en', '') or sep_data[slug].get('body', '')[:3000],
                    "_slug": slug,
                    "_concept_zh": cz,
                }
    return jsonify(sep_data)


@app.route("/notes")
@login_required
def notes():
    """笔记列表（修正了卷次排序）"""
    import glob, re
    _cn_num_2 = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    def _sort_key(fpath):
        bn = os.path.basename(fpath).replace(".md", "")
        m = re.search(r"篇第([一二三四五六七八九十]+)", bn)
        if m:
            return sum(_cn_num_2.get(c, 0) for c in m.group(1))
        m2 = re.search(r"卷([一二三四五六七八九十]+)", bn)
        if m2:
            return sum(_cn_num_2.get(c, 0) for c in m2.group(1))
        return 0
    notes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "数字中医有感")
    categories = {}
    if os.path.isdir(notes_dir):
        for sub in sorted(os.listdir(notes_dir)):
            subpath = os.path.join(notes_dir, sub)
            if not os.path.isdir(subpath):
                continue
            md_files = glob.glob(os.path.join(subpath, "*.md"))
            md_files.sort(key=_sort_key)
            notes_in_cat = []
            for f in md_files:
                with open(f, "r", encoding="utf-8") as nf:
                    first_line = nf.readline().strip().lstrip("# ")
                rel_path = sub + "/" + os.path.basename(f)
                notes_in_cat.append({
                    "title": first_line or os.path.basename(f).replace(".md", ""),
                    "file": rel_path,
                    "date": "2026-07-23",
                })
            if notes_in_cat:
                categories[sub] = notes_in_cat
    return jsonify({"categories": categories})


@app.route("/crawled-books")
@login_required
def crawled_books():
    clean_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xin_sources", "cleaned")
    index_path = os.path.join(clean_dir, "_index.json")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"total": 0, "by_category": {}})


# ── 简单页面路由（不走 catch-all） ──

@app.route("/phase-theory")
@login_required
def phase_theory():
    phase_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xin_phase_theory.html")
    if os.path.isfile(phase_path):
        with open(phase_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>物态人论页面未找到</h1>", 404


@app.route("/skills")
@login_required
def skills():
    skills_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills.json")
    if os.path.isfile(skills_path):
        with open(skills_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({}), 200


@app.route("/upload")
@login_required
def upload():
    """上传页面"""
    return '''<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>上传文件到莫名心</title>
<style>body{background:#1a1a1e;color:#ece8dc;padding:20px;font-family:sans-serif;max-width:600px;margin:0 auto;}
.card{background:#222228;border-radius:14px;padding:20px;margin-bottom:16px;}
h1{font-size:20px;margin-bottom:16px;}
input,textarea{width:100%;padding:12px;border:1px solid #3a3a40;border-radius:10px;background:#2a2a30;color:#ece8dc;font-size:14px;margin-bottom:12px;box-sizing:border-box;}
button{width:100%;padding:14px;background:#d86050;color:white;border:none;border-radius:12px;font-size:16px;cursor:pointer;}
#result{margin-top:12px;font-size:14px;color:#b0a898;}
</style></head><body>
<h1>📤 上传文件到莫名心</h1>
<div class="card">
<p style="color:#b0a898;margin-bottom:12px;">选择文件，我会把它存到工作目录里并读取。</p>
<input type="file" id="fileInput" multiple>
<button onclick="uploadAll()">上传</button>
<div id="result"></div>
<script>
async function uploadAll(){const r=document.getElementById("result");const files=document.getElementById("fileInput").files;if(!files.length){r.textContent="请先选择文件";return;}r.textContent="上传中 0/"+files.length+"...";let ok=0,err=0;for(let i=0;i<files.length;i++){const f=files[i];r.textContent="上传中 "+i+"/"+files.length+": "+f.name;try{const b64=await new Promise((res,rej)=>{const r2=new FileReader();r2.onload=e=>res(e.target.result.split(",")[1]);r2.onerror=rej;r2.readAsDataURL(f)});const d=await(await fetch("/upload",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filename:f.name,content:b64})})).json();if(d.error)err++;else ok++;}catch(e){err++}}r.textContent="✅ 完成: "+ok+" 成功, "+err+" 失败";}
</script></body></html>'''


# ── 经典查看器 ──

@app.route("/classic-view/")
@app.route("/classic-view/<path:filepath>")
@login_required
def classic_view(filepath=""):
    """查看经典原文（默认繁体，单栏可切换简体）"""
    import re, html as hmod
    from urllib.parse import unquote
    
    page = request.args.get("page", 1, type=int)
    page = max(1, page)
    file_rel = unquote(filepath)
    base = os.path.expanduser("~/.openclaw/workspace/xin_sources")
    fp = os.path.join(base, file_rel)
    
    if not (os.path.isfile(fp) and fp.startswith(base)):
        page404 = """<!DOCTYPE html><html><meta charset="UTF-8"><title>未找到</title>
<style>body{background:#16161a;color:#d8d0c0;padding:40px;font-family:sans-serif;text-align:center;}
h1{font-size:60px;margin:0;color:#3a2a1a;}p{color:#6a5a4a;}a{color:#d8d0c0;}</style>
<body><h1>📖</h1><p>文档未找到，可能已被移动或名称发生了变化。</p>
<p><a href="/">← 返回小站</a></p></body></html>"""
        return page404, 404
    
    with open(fp, "r", encoding="utf-8") as f:
        raw = f.read()
    
    cleaned = re.sub(r"<pb:[^>]+>", "", raw)
    cleaned = re.sub("\u00b6", "", cleaned)
    cleaned = re.sub(r"#.*", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    
    cpp = 8000
    total = max(1, (len(cleaned) + cpp - 1) // cpp)
    page = min(page, total)
    s = (page - 1) * cpp
    e = min(s + cpp, len(cleaned))
    chunk = cleaned[s:e]
    orig = hmod.escape(chunk)
    
    try:
        from zhconv import convert
        simp = hmod.escape(convert(chunk, "zh-cn"))
    except ImportError:
        simp = orig
    
    basename = hmod.escape(os.path.basename(file_rel))
    
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{basename} 第{page}页</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#16161a;color:#d8d0c0;font-family:"Noto Sans SC","PingFang SC",sans-serif;padding:0;}}
.nav{{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid #2a2a30;font-size:14px;flex-wrap:wrap;}}
.nav a{{color:#b0a898;text-decoration:none;white-space:nowrap;}}
.nav .title{{color:#5a5a5a;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.toggle{{padding:6px 14px;border-radius:8px;border:1px solid #3a3a40;background:#2a2a30;color:#ece8dc;font-size:13px;cursor:pointer;white-space:nowrap;transition:all 0.2s;}}
.toggle:hover{{background:#3a3a40;}}
.toggle.active{{background:#4a3020;border-color:#d86050;color:#d86050;}}
.pager{{display:flex;justify-content:center;align-items:center;gap:16px;padding:14px 16px;border-top:1px solid #2a2a30;font-size:14px;}}
.pager a{{color:#b0a898;text-decoration:none;padding:6px 14px;border:1px solid #3a3a40;border-radius:8px;font-size:13px;}}
.pager a:hover{{background:#2a2a30;}}
.pager span{{color:#5a5a5a;font-size:13px;}}
.content{{padding:20px;max-width:720px;margin:0 auto;font-size:15px;line-height:2;white-space:pre-wrap;word-wrap:break-word;}}
.lang-tag{{font-size:11px;color:#6a5a4a;padding:4px 10px;border:1px solid #2a2a30;border-radius:6px;display:inline-block;margin-bottom:10px;}}
@media(max-width:480px){{.nav{{font-size:13px;padding:10px 12px;}}.content{{padding:14px;font-size:14px;}}.pager{{gap:8px;font-size:13px;}}}}
</style></head><body>
<div class="nav">
  <a href="/">←</a>
  <span class="title">{basename} 第{page}页</span>
  <span id="langLabel" class="lang-tag">繁体</span>
  <button class="toggle" onclick="switchLang()" id="langBtn">切换简体</button>
</div>
<div id="contentFan" class="content">{orig}</div>
<div id="contentJian" class="content" style="display:none">{simp}</div>
<div class="pager">
  {"""<a href="?page=""" + str(page-1) + """">‹ 上一页</a>""" if page > 1 else """<span></span>"""}
  <span>第 {page} / {total} 页</span>
  {"""<a href="?page=""" + str(page+1) + """">下一页 ›</a>""" if page < total else """<span></span>"""}
</div>
<script>
var isFan = true;
function switchLang(){{
  isFan = !isFan;
  document.getElementById('contentFan').style.display = isFan ? 'block' : 'none';
  document.getElementById('contentJian').style.display = isFan ? 'none' : 'block';
  document.getElementById('langLabel').textContent = isFan ? '繁体' : '简体';
  var btn = document.getElementById('langBtn');
  btn.textContent = isFan ? '切换简体' : '显示繁体';
}}
</script>
</body></html>'''


# ── 求知虫查看器 ──

@app.route("/crawled-view/")
@app.route("/crawled-view/<path:filepath>")
@login_required
def crawled_view(filepath=""):
    """查看已爬取的古籍（默认繁体，单栏可切换简体）"""
    from urllib.parse import unquote
    import glob
    file_rel = unquote(filepath)
    clean_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xin_sources", "cleaned")
    page = request.args.get("page", 1, type=int)
    page = max(1, page)
    
    found = None
    for f in glob.glob(os.path.join(clean_dir, "**", "*.md"), recursive=True):
        if file_rel in f or os.path.basename(f) == file_rel:
            found = f
            break
    
    if not (found and os.path.isfile(found)):
        return "<h1>未找到</h1>", 404
    
    with open(found, "r", encoding="utf-8") as f:
        raw = f.read()
    body_start = raw.find("\n---\n", raw.find("---")) if raw.startswith("---") else 0
    body = raw[body_start + 5:] if body_start > 0 else raw
    
    ppc = 5000
    total = max(1, (len(body) + ppc - 1) // ppc)
    page = min(page, total)
    start = (page - 1) * ppc
    end = min(start + ppc, len(body))
    chunk_fan = body[start:end]
    fan = html.escape(chunk_fan)
    
    # 找 trad 版本
    simp = fan
    trad_rel = file_rel.replace(".md", ".trad.md")
    for tf in glob.glob(os.path.join(clean_dir, "**", "*.trad.md"), recursive=True):
        if os.path.basename(tf) == trad_rel:
            with open(tf, "r", encoding="utf-8") as vf:
                raw2 = vf.read()
            bs2 = raw2.find("\n---\n", raw2.find("---")) if raw2.startswith("---") else 0
            body2 = raw2[bs2 + 5:] if bs2 > 0 else raw2
            s2 = (page - 1) * ppc
            e2 = min(s2 + ppc, len(body2))
            simp = html.escape(body2[s2:e2])
            break
    
    basename = html.escape(os.path.basename(file_rel))
    left_arrow = """<a href="?page=""" + str(page-1) + """">‹ 上一页</a>""" if page > 1 else """<span></span>"""
    right_arrow = """<a href="?page=""" + str(page+1) + """">下一页 ›</a>""" if page < total else """<span></span>"""
    
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{basename} 第{page}页</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#16161a;color:#d8d0c0;font-family:"Noto Sans SC","PingFang SC",sans-serif;padding:0;}}
.nav{{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid #2a2a30;font-size:14px;flex-wrap:wrap;}}
.nav a{{color:#b0a898;text-decoration:none;white-space:nowrap;}}
.nav .title{{color:#5a5a5a;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}}
.toggle{{padding:6px 14px;border-radius:8px;border:1px solid #3a3a40;background:#2a2a30;color:#ece8dc;font-size:13px;cursor:pointer;white-space:nowrap;transition:all 0.2s;}}
.toggle:hover{{background:#3a3a40;}}
.lang-tag{{font-size:11px;color:#6a5a4a;padding:4px 10px;border:1px solid #2a2a30;border-radius:6px;display:inline-block;}}
.content{{padding:20px;max-width:720px;margin:0 auto;font-size:15px;line-height:2;white-space:pre-wrap;word-wrap:break-word;}}
.pager{{display:flex;justify-content:center;align-items:center;gap:16px;padding:14px 16px;border-top:1px solid #2a2a30;font-size:14px;}}
.pager a{{color:#b0a898;text-decoration:none;padding:6px 14px;border:1px solid #3a3a40;border-radius:8px;font-size:13px;}}
.pager a:hover{{background:#2a2a30;}}
.pager span{{color:#5a5a5a;font-size:13px;}}
@media(max-width:480px){{.nav{{font-size:13px;padding:10px 12px;}}.content{{padding:14px;font-size:14px;}}.pager{{gap:8px;font-size:13px;}}}}
</style></head><body>
<div class="nav">
  <a href="/">←</a>
  <span class="title">{basename}</span>
  <span class="lang-tag" id="clangLabel">繁体</span>
  <button class="toggle" onclick="switchCrawledLang()" id="clangBtn">切换简体</button>
</div>
<div id="cfan" class="content">{fan}</div>
<div id="cj" class="content" style="display:none">{simp}</div>
<div class="pager">
  {left_arrow}
  <span>第 {page} / {total} 页</span>
  {right_arrow}
</div>
<script>
var isFan = true;
function switchCrawledLang(){{
  isFan = !isFan;
  document.getElementById('cfan').style.display = isFan ? 'block' : 'none';
  document.getElementById('cj').style.display = isFan ? 'none' : 'block';
  document.getElementById('clangLabel').textContent = isFan ? '繁体' : '简体';
  document.getElementById('clangBtn').textContent = isFan ? '切换简体' : '显示繁体';
}}
</script>
</body></html>'''


# ── 兜底路由（只有上面没匹配到的才到这里） ──
@app.route("/daogui")
@login_required
def daogui():
    """道归文库"""
    from daogui_lib import generate_lib_page
    cat = request.args.get('cat')
    doc = request.args.get('doc')
    return generate_lib_page(category=cat, doc_id=doc)


@app.route("/forge-destiny")
@login_required
def forge_destiny():
    """锻因缘"""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "锻因缘", "index.html")
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>锻因缘页面未找到</h1>", 404


# ── 启动 ──
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", "8080"))
    print(f"\n{'═' * 50}")
    print("🌙 莫名心 · 小站 v3 (Flask 重装甲版)")
    print(f"{'═' * 50}")
    print(f"  6 个 Tab + AI 问答 + 密码保护")
    if _PWD_FILE and os.path.isfile(_PWD_FILE):
        print(f"  密码: 来自 密码.json")
    else:
        print(f"  密码: {_LOGIN_PASSWORD} (在 密码.json 中修改)")
    print(f"{'═' * 50}")
    print(f"  → http://localhost:{PORT}")
    print(f"  → http://<本机IP>:{PORT}  (同局域网可用)")
    print(f"{'═' * 50}\n")
    
    serve(app, host="0.0.0.0", port=PORT, threads=8)
