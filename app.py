#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心哥小站 · Flask 重装甲版 🌙
多线程 + 密码锁 + 全部原有功能
"""

import sys, os, json, hashlib, uuid, html
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

# ── 防滥用限流 ──
import time as _time
from collections import defaultdict
from functools import wraps

_RATE_MIN = 15   # 每分钟最多15次（防滥用但不误伤正常使用）
_RATE_DAY = 300  # 每天最多300次
_rate_min_buckets = defaultdict(list)
_rate_day_buckets = defaultdict(list)

def _client_ip():
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or 'unknown'

def rate_limit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method != 'POST':
            return f(*args, **kwargs)
        ip = _client_ip()
        now = _time.time()
        _rate_min_buckets[ip] = [t for t in _rate_min_buckets[ip] if now - t < 60]
        _rate_day_buckets[ip] = [t for t in _rate_day_buckets[ip] if now - t < 86400]
        if len(_rate_day_buckets[ip]) >= _RATE_DAY:
            return jsonify({"error": "今日调用次数已达上限，明天再来吧"}), 429
        if len(_rate_min_buckets[ip]) >= _RATE_MIN:
            return jsonify({"error": "操作太频繁了，歇一分钟再试"}), 429
        _rate_min_buckets[ip].append(now)
        _rate_day_buckets[ip].append(now)
        return f(*args, **kwargs)
    return wrapper



app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = False
app.config["TRAP_HTTP_EXCEPTIONS"] = False
# 工具台 Blueprint（隔离路由注册）
try:
    from tools_blueprint import tools_bp
    app.register_blueprint(tools_bp)
except Exception:
    pass
# KX 神迹（跨领域融合档案）
try:
    from kxwonders_route import kx_bp
    app.register_blueprint(kx_bp)
except Exception as e:
    print(f"kxwonders 注册失败: {e}")


def ping():
    return "pong"

app.secret_key = "mo-ming-xin-xiao-zhan-2026-07-26"
app.permanent_session_lifetime = timedelta(hours=4)

# ── 密码配置 ──
# 在运行目录下放一个 密码.json 文件，内容 {"密码": "你的密码"}
# 如果没有，默认密码是下面的 fallback
_PWD_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "密码.json")
# ── 2026-08-05 小站翻新 · 公共样式（米白暖色系 · 简洁大气）──
_SITE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#f7f2ec;--card:#fffdf9;--ink:#3d3a36;--ink-2:#8a827a;--accent:#a0522d;--accent-2:#c68a5d;--line:#e8dfd3;--shadow:0 2px 10px rgba(160,82,45,.08)}
html{-webkit-text-size-adjust:100%}
body{font-family:"PingFang SC","Hiragino Sans GB","Noto Sans SC",system-ui,sans-serif;background:var(--bg);color:var(--ink);line-height:1.75;min-height:100vh;padding:24px 16px}
.wrap{max-width:880px;margin:0 auto}
h1{font-size:1.55rem;font-weight:600;color:var(--accent);margin-bottom:6px;letter-spacing:.5px}
h2{font-size:1.15rem;color:var(--accent);margin:22px 0 10px}
.sub{color:var(--ink-2);font-size:.88rem;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:14px;box-shadow:var(--shadow);text-decoration:none;color:var(--ink);display:block;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-1px);box-shadow:0 4px 16px rgba(160,82,45,.14)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:22px}
.nav a{display:inline-block;padding:7px 14px;background:var(--card);border:1px solid var(--line);border-radius:999px;color:var(--accent);font-size:.85rem;transition:background .15s}
.nav a:hover{background:var(--accent);color:#fff;text-decoration:none}
.btn{display:inline-block;padding:9px 20px;background:var(--accent);color:#fff;border:none;border-radius:999px;font-size:.92rem;cursor:pointer;transition:background .15s}
.btn:hover{background:var(--accent-2)}
input[type=text],input[type=password],textarea,select{width:100%;padding:11px 14px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--ink);font-size:.95rem;margin-bottom:12px;outline:none}
input:focus,textarea:focus,select:focus{border-color:var(--accent-2)}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.9rem}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left}
th{background:#f3ece2;color:var(--accent);font-weight:600}
tr:nth-child(even){background:#faf6ef}
.footer{text-align:center;color:var(--ink-2);font-size:.8rem;margin-top:34px;padding-top:16px;border-top:1px solid var(--line)}
.poem-full,.content{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:26px 28px;box-shadow:var(--shadow);white-space:pre-wrap;line-height:2}
pre{background:#f3ece2;border:1px solid var(--line);border-radius:10px;padding:14px;overflow-x:auto;font-size:.88rem}
.tag{display:inline-block;padding:4px 12px;border:1px solid var(--line);border-radius:999px;background:var(--card);cursor:pointer;font-size:.82rem;margin:3px;user-select:none}
.tag.selected{background:var(--accent);color:#fff;border-color:var(--accent)}
"""

def _site_head(title="莫名心 · 小站"):
    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>{_SITE_CSS}</style>
</head><body><div class="wrap">"""

def _site_nav(links=None):
    """统一顶部导航：返回首页 + 指定链接"""
    base = '<a href="/tools">🧩 工具台</a><a href="/">🏠 首页</a>'
    extra = ''.join(f'<a href="{h}">{t}</a>' for h, t in (links or []))
    return '<div class="nav">' + base + extra + '</div>'

def _site_foot():
    return '<div class="footer">🌙 莫名心 · 小站 · 米白暖色 · 温婉如初</div></div></body></html>'

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
var savedDark = localStorage.getItem('xiaozhan_dark_mode');
if(savedDark === 'true' || (savedDark === null && window.matchMedia('(prefers-color-scheme:dark)').matches)){
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


# ── 百宝囊（工具集）挂载：ConvertAgent/SnapOtter 思路的手搓轻量版 ──
from toolbox_routes import register_toolbox_routes
register_toolbox_routes(app)
# 理论体系总览
from theory_routes import register_theory_routes
register_theory_routes(app)
for _rule in [r for r in app.url_map.iter_rules() if r.endpoint in ("theory_page", "theory_api")]:
    _view = app.view_functions[_rule.endpoint]
    app.view_functions[_rule.endpoint] = login_required(_view)
# 给百宝囊路由加上登录保护（手动替换视图）
for _rule in [r for r in app.url_map.iter_rules() if r.endpoint in ("toolbox_page", "toolbox_api", "toolbox_download")]:
    _view = app.view_functions[_rule.endpoint]
    app.view_functions[_rule.endpoint] = login_required(_view)


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
    data = get_yunqi_data(date_str)
    # 浏览器访问 -> 可视化HTML（带滑动+AJAX实时更新）
    if "text/html" in request.headers.get("Accept", ""):
        from datetime import datetime, date
        today_d = date.today()
        today_str = date_str or today_d.isoformat()
        today_ts = int(datetime.strptime(today_str[:10], "%Y-%m-%d").timestamp())
        default_date = date_str or today_d.isoformat()
        
        # 输出骨架HTML（含初始数据）+ JS处理
        html = f'''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>五运六气 · 莫名心</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto;padding-bottom:60px}}

/* 控制栏 */
.controls{{background:#fff;border-radius:14px;padding:16px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,0.05)}}
.controls .top-row{{display:flex;gap:8px;align-items:center;margin-bottom:10px}}
.controls .top-row input[type=date]{{flex:1;padding:10px 12px;border:2px solid #ddd;border-radius:10px;font-size:16px;outline:none;font-family:inherit}}
.controls .top-row input[type=date]:focus{{border-color:#b8453a}}
.controls .top-row .date-label{{font-size:18px;font-weight:700;color:#2c2c2c;min-width:100px;text-align:center}}

/* 滑动条 */
.slider-row{{display:flex;gap:10px;align-items:center}}
.slider-row input[type=range]{{flex:1;-webkit-appearance:none;appearance:none;height:6px;border-radius:3px;background:#ddd;outline:none;cursor:pointer}}
.slider-row input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;appearance:none;width:22px;height:22px;border-radius:50%;background:#b8453a;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.2);cursor:pointer;transition:transform 0.15s}}
.slider-row input[type=range]::-webkit-slider-thumb:hover{{transform:scale(1.15)}}
.slider-row input[type=range]::-moz-range-thumb{{width:22px;height:22px;border-radius:50%;background:#b8453a;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,0.2);cursor:pointer}}
.slider-row .play-btn{{width:40px;height:40px;border-radius:50%;background:#b8453a;color:#fff;border:none;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:background 0.2s}}
.slider-row .play-btn:hover{{background:#a03a30}}
.slider-row .play-btn.playing{{background:#e74c3c}}

/* 内容区 - AJAX更新 */
#yqContent{{opacity:1;transition:opacity 0.2s}}
#yqContent.loading{{opacity:0.4}}
.card{{background:#fff;border-radius:14px;padding:18px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,0.05);transition:opacity 0.2s}}
.card-title{{font-size:14px;font-weight:600;color:#888;margin-bottom:10px;letter-spacing:0.5px}}
.error{{background:#fef2f0;color:#b8453a;padding:14px;border-radius:10px;margin-bottom:14px}}
.banner{{background:linear-gradient(135deg,#3a5a7c,#2c3e50);color:#fff;border-radius:14px;padding:20px;margin-bottom:14px;text-align:center}}
.banner .ganzhi{{font-size:26px;font-weight:700;letter-spacing:2px}}
.banner .sub{{font-size:13px;opacity:0.8;margin-top:4px}}
.banner .tags{{display:flex;justify-content:center;gap:8px;margin-top:10px;flex-wrap:wrap}}
.banner .tags span{{padding:4px 12px;border-radius:16px;font-size:13px;background:rgba(255,255,255,0.15);backdrop-filter:blur(2px)}}
.info-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.info-item{{padding:10px 12px;background:#faf7f4;border-radius:10px;font-size:13px}}
.info-item .lbl{{color:#888;font-size:12px}}
.info-item .val{{font-weight:600;margin-top:2px}}
.now-card{{border-left:4px solid #e67e22}}
.now-card .now-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.now-item{{text-align:center;padding:8px}}
.now-item .lbl{{font-size:11px;color:#888;margin-bottom:2px}}
.now-item .val{{font-size:16px;font-weight:600}}
.timeline{{position:relative;padding:0}}
.tl-item{{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #f0ebe6;align-items:center}}
.tl-item:last-child{{border:none}}
.tl-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:3px}}
.tl-body{{flex:1;font-size:13px}}
.tl-body .tl-shiduan{{font-weight:600;font-size:14px}}
.tl-body .tl-detail{{color:#888;margin-top:1px}}
.tl-tag{{font-size:11px;padding:2px 8px;border-radius:10px;margin-left:6px;color:#fff}}
.tl-active{{background:#ede7e0;border-radius:10px;margin:-4px -8px;padding:4px 8px}}
.wuxing-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.wx-item{{text-align:center;padding:10px;background:#faf7f4;border-radius:10px;font-size:12px}}
.wx-item .lbl{{color:#888}}
.wx-item .val{{font-weight:600;margin-top:2px;font-size:14px}}
.footer{{text-align:center;font-size:12px;color:#888;padding:16px 0}}
a{{color:#a0522d;text-decoration:none}}
@media(max-width:420px){{.info-grid{{grid-template-columns:1fr}}.wuxing-grid{{grid-template-columns:1fr 1fr}}.controls .top-row .date-label{{font-size:15px;min-width:80px}}}}
</style></head>
<body>

<div class="controls">
  <div class="top-row">
    <input type="date" id="yqDate" value="{default_date}" onchange="syncFromDate()">
    <div class="date-label" id="dateLabel">{default_date}</div>
  </div>
  <div class="slider-row">
    <input type="range" id="yqSlider" min="1767139200" max="1893427200" step="86400" oninput="syncFromSlider()">
    <button class="play-btn" id="playBtn" onclick="togglePlay()">▶</button>
  </div>
</div>

<div id="yqContent">
  <div id="yqInner">
    <div class="loading" id="initialLoading" style="text-align:center;padding:40px;color:#888">⏳ 加载中…</div>
  </div>
</div>

<div class="footer"><a href="/tools">← 工具台</a> · 五运六气 · 莫名心</div>

<script>
// ═══════════════════════════
// 五运六气 AJAX 滑动引擎
// ═══════════════════════════

var _playing = false;
var _playTimer = null;

// 日期 ↔ slider值转换
function dateToVal(d) {{
  return Math.floor(new Date(d).getTime() / 1000);
}}
function valToDate(v) {{
  var d = new Date(parseInt(v) * 1000);
  return d.toISOString().split('T')[0];
}}

// 同步：输入日期 → 更新滑块 + 加载数据
function syncFromDate() {{
  var d = document.getElementById('yqDate').value;
  if (!d) return;
  document.getElementById('dateLabel').textContent = d;
  var val = dateToVal(d);
  document.getElementById('yqSlider').value = Math.max(1767139200, Math.min(1893427200, val));
  loadYunqi(d);
}}

// 同步：拖动滑块 → 更新日期 + 加载数据
function syncFromSlider() {{
  var val = parseInt(document.getElementById('yqSlider').value);
  var d = valToDate(val);
  document.getElementById('yqDate').value = d;
  document.getElementById('dateLabel').textContent = d;
  loadYunqi(d);
}}

// AJAX 加载五运六气
async function loadYunqi(dateStr) {{
  var content = document.getElementById('yqContent');
  content.classList.add('loading');
  try {{
    var res = await fetch('/yunqi?date=' + dateStr, {{
      headers: {{'Accept': 'application/json'}}
    }});
    var data = await res.json();
    renderYunqi(data);
  }} catch(e) {{
    document.getElementById('yqInner').innerHTML = '<div class="card error">加载失败: ' + e.message + '</div>';
  }}
  content.classList.remove('loading');
}}

// 渲染五运六气数据
function renderYunqi(data) {{
  if (data.error) {{
    document.getElementById('yqInner').innerHTML = '<div class="card error">' + data.error + '</div>';
    return;
  }}
  
  function s(obj, key, fb) {{ return (obj && obj[key]) ? String(obj[key]) : (fb || ''); }}
  function ss(obj) {{
    for (var i = 1; i < arguments.length; i++) {{
      var v = obj[arguments[i]];
      if (v) return String(v);
    }}
    return '';
  }}
  
  var ganzhi = s(data, '干支', '');
  var tiang = s(data, '天干', '');
  var dizhi = s(data, '地支', '');
  var sitian = s(data, '司天', '');
  var zaiquan = s(data, '在泉', '');
  var desc = s(data, '描述', '');
  
  var sy = data['岁运'] || {{}};
  var syName = s(sy, '岁运', '');
  var taiBu = s(sy, '太过不及', '');
  var zangfu = sy['脏腑'] || [];
  var wuji = s(sy, '季节', '');
  var whou = s(sy, '气候', '');
  var wwei = s(sy, '五味', '');
  
  var dq = data['当前'] || {{}};
  var dqSd = s(dq, '时段', '');
  var dqZq = s(dq, '主气', '');
  var dqKq = s(dq, '客气', '');
  var dqQj = s(dq, '区间', '');
  
  var wx = data['五行'] || {{}};
  var wxZf = wx['脏腑'] || [];
  var wxJj = s(wx, '季节', '');
  var wxQh = s(wx, '气候', '');
  var wxWw = s(wx, '五味', '');
  
  var liubu = data['客气六步'] || [];
  
  // 五行配色
  var _colors = {{
    '木':'#27ae60','火':'#e67e22','土':'#d4a84b','金':'#8e44ad','水':'#2980b9',
    '寒':'#2980b9','热':'#e74c3c','暑':'#e67e22','湿':'#d4a84b','燥':'#8e44ad','风':'#27ae60'
  }};
  function wc(name) {{
    for (var k in _colors) {{ if (name.indexOf(k) >= 0) return _colors[k]; }}
    return '#3a5a7c';
  }}
  
  // 构建HTML
  var html = '';
  
  // Banner
  html += '<div class="banner">' +
    '<div class="ganzhi">' + ganzhi + '年</div>' +
    '<div class="sub">' + tiang + '·' + dizhi + ' | ' + desc.substring(0, 60) + '</div>' +
    '<div class="tags">' +
      '<span>🌊 ' + syName + '运' + taiBu + '</span>' +
      '<span>☀️ 司天 ' + sitian + '</span>' +
      '<span>🌍 在泉 ' + zaiquan + '</span>' +
    '</div></div>';
  
  // 岁运
  html += '<div class="card"><div class="card-title">🌊 岁运</div><div class="info-grid">' +
    '<div class="info-item"><div class="lbl">天干</div><div class="val">' + tiang + '</div></div>' +
    '<div class="info-item"><div class="lbl">岁运</div><div class="val">' + syName + ' ⭐</div></div>' +
    '<div class="info-item"><div class="lbl">太过不及</div><div class="val">' + taiBu + '</div></div>' +
    '<div class="info-item"><div class="lbl">对应脏腑</div><div class="val">' + (zangfu.length ? zangfu.join('、') : '—') + '</div></div>' +
    '<div class="info-item"><div class="lbl">季节</div><div class="val">' + wuji + '</div></div>' +
    '<div class="info-item"><div class="lbl">气候</div><div class="val">' + whou + '</div></div>' +
    '<div class="info-item"><div class="lbl">五味</div><div class="val">' + wwei + '</div></div>' +
    '</div></div>';
  
  // 当前时位
  html += '<div class="card now-card"><div class="card-title">🕐 当前时位</div><div class="now-grid">' +
    '<div class="now-item"><div class="lbl">时段</div><div class="val">' + dqSd + '</div></div>' +
    '<div class="now-item"><div class="lbl">区间</div><div class="val" style="font-size:13px">' + dqQj + '</div></div>' +
    '<div class="now-item"><div class="lbl">主气</div><div class="val" style="color:' + wc(dqZq) + '">' + dqZq + '</div></div>' +
    '<div class="now-item"><div class="lbl">客气</div><div class="val" style="color:' + wc(dqKq) + '">' + dqKq + '</div></div>' +
    '</div></div>';
  
  // 客气六步时间线
  html += '<div class="card"><div class="card-title">📊 客气六步</div><div class="timeline">';
  for (var i = 0; i < liubu.length; i++) {{
    var step = liubu[i];
    var sd = s(step, '时段', '');
    var ke = s(step, '客气', '');
    var zhu = s(step, '主气', '');
    var qu = s(step, '日期', '');
    var tag = s(step, '标记', '');
    var isActive = (sd === dqSd);
    var actCls = isActive ? ' tl-active' : '';
    var mark = isActive ? ' ← 当前' : '';
    var tagH = tag ? '<span class="tl-tag" style="background:' + wc(tag) + '">' + tag + '</span>' : '';
    html += '<div class="tl-item' + actCls + '">' +
      '<div class="tl-dot" style="background:' + wc(ke) + '"></div>' +
      '<div class="tl-body">' +
      '<div class="tl-shiduan">' + sd + mark + tagH + '</div>' +
      '<div class="tl-detail">客气 · ' + ke + ' ｜ 主气 · ' + zhu + '</div>' +
      '<div class="tl-detail" style="font-size:12px">' + qu + '</div>' +
      '</div></div>';
  }}
  html += '</div></div>';
  
  // 五行
  html += '<div class="card"><div class="card-title">🔄 五行</div><div class="wuxing-grid">' +
    '<div class="wx-item"><div class="lbl">脏腑</div><div class="val">' + (wxZf.length ? wxZf.join('、') : '—') + '</div></div>' +
    '<div class="wx-item"><div class="lbl">季节</div><div class="val">' + wxJj + '</div></div>' +
    '<div class="wx-item"><div class="lbl">气候</div><div class="val">' + wxQh + '</div></div>' +
    '<div class="wx-item"><div class="lbl">五味</div><div class="val">' + wxWw + '</div></div>' +
    '</div></div>';
  
  document.getElementById('yqInner').innerHTML = html;
  applyDarkMode();
}}

// 自动播放
function togglePlay() {{
  _playing = !_playing;
  var btn = document.getElementById('playBtn');
  if (_playing) {{
    btn.textContent = '⏸';
    btn.classList.add('playing');
    _playTimer = setInterval(function() {{
      var slider = document.getElementById('yqSlider');
      var v = parseInt(slider.value) + 86400; // +1天
      if (v > 1893427200) v = 1767139200; // 循环
      slider.value = v;
      syncFromSlider();
    }}, 500); // 每500ms滑动一天
  }} else {{
    btn.textContent = '▶';
    btn.classList.remove('playing');
    clearInterval(_playTimer);
  }}
}}

// 暗色模式
function applyDarkMode() {{
  try {{
    if (localStorage.getItem('xiaozhan_dark_mode') === 'true') {{
      document.body.style.background = '#16161a';
      document.body.style.color = '#ece8dc';
      var cards = document.querySelectorAll('.card, .info-item, .wx-item, .now-item, .controls');
      for (var i = 0; i < cards.length; i++) {{
        cards[i].style.background = '#1e1e24';
        cards[i].style.color = '#ece8dc';
      }}
      var inputs = document.querySelectorAll('.controls input');
      for (var i = 0; i < inputs.length; i++) {{
        inputs[i].style.background = '#222228';
        inputs[i].style.borderColor = '#3a3a40';
        inputs[i].style.color = '#ece8dc';
      }}
      var sliders = document.querySelectorAll('input[type=range]');
      for (var i = 0; i < sliders.length; i++) {{
        sliders[i].style.background = '#3a3a40';
      }}
    }}
  }} catch(e){{}}
}}

// 初始化：设置滑块初始值 + 加载数据
(function init(){{
  var d = document.getElementById('yqDate').value;
  if (d) {{
    var val = dateToVal(d);
    document.getElementById('yqSlider').value = Math.max(1767139200, Math.min(1893427200, val));
    loadYunqi(d);
  }}
  applyDarkMode();
}})();

</script>
</body></html>'''
        return html
    return jsonify(data)


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
    if request.method == "GET":
        tmpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "yunqi_eval.html")
        if os.path.isfile(tmpl):
            with open(tmpl, encoding="utf-8") as _tf:
                return _tf.read()
        return "<h1>模板未找到</h1>", 404
    plan = request.json.get("plan", "") if request.json else ""
    if not plan:
        return jsonify({"success": False, "error": "需要 plan 参数"}), 400
    date_str = request.json.get("date") if request.json else None
    try:
        from 五运六气 import 推算
        from 五运六气.eval import 评价食疗方案
        r = 推算(date_str)
        ev = 评价食疗方案(r, plan)
        return jsonify({"success": True, "五运六气": r, "评价": ev})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/diagnose", methods=["POST"])
@login_required
def diagnose():
    from xin_web_server import run_diagnosis
    d = request.json or {}
    return jsonify(run_diagnosis(
        d.get("symptoms", []),
        d.get("tongue", ""),
        d.get("pulse", "")
    ))


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


@app.route("/ask", methods=["GET", "POST"])
@login_required
@rate_limit
def ask():
    if request.method == "GET":
        return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>AI问答 · 莫名心小站</title>
<style>
:root{--bg:#f5f0eb;--card:#fff;--text:#2c2c2c;--text-l:#888;--accent:#b8453a}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);padding:16px;max-width:640px;margin:0 auto;padding-bottom:60px}
body.dark{--bg:#16161a;--card:#1e1e24;--text:#ece8dc;--text-l:#b0a898;--accent:#d86050}
h1{font-size:20px;margin-bottom:4px}
.sub{color:var(--text-l);font-size:.8rem;margin-bottom:16px}
.card{background:var(--card);border-radius:14px;padding:16px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,0.05)}
textarea{width:100%;padding:12px;border:2px solid #ddd;border-radius:12px;font-size:16px !important;outline:none;font-family:inherit;resize:vertical;transition:border 0.2s;background:var(--card);color:var(--text)}
textarea:focus{border-color:var(--accent)}
body.dark textarea{background:#222228;border-color:#3a3a40;color:var(--text)}
button{width:100%;padding:14px;background:var(--accent);color:white;border:none;border-radius:12px;font-size:16px;cursor:pointer;font-weight:500;transition:opacity 0.2s}
button:active{opacity:0.8}
button:disabled{opacity:0.5;cursor:not-allowed}
.result-box{display:none;background:var(--card);border-radius:14px;padding:16px;font-size:14px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,0.05)}
.loading{display:none;text-align:center;padding:16px;color:var(--text-l)}
.spinner{display:inline-block;width:24px;height:24px;border:3px solid #eee;border-top:3px solid var(--accent);border-radius:50%;animation:spin 0.7s linear infinite;margin-right:8px;vertical-align:middle}
@keyframes spin{to{transform:rotate(360deg)}}
.footer{text-align:center;font-size:12px;color:var(--text-l);padding:16px 0}
a{color:#a0522d;text-decoration:none}
</style></head><body>
<h1>🤖 AI问答</h1>
<p class="sub">DeepSeek V4 Flash 驱动</p>
<div class="card">
<textarea id="q" rows="4" placeholder="输入你的问题…"></textarea>
<button id="sendBtn" onclick="askAI()">发送</button>
</div>
<div class="loading" id="loading"><span class="spinner"></span>思考中…</div>
<div class="result-box" id="result"></div>
<div class="footer"><a href="/tools">← 工具台</a></div>
<script>
function askAI() {
  var q = document.getElementById('q').value.trim();
  if (!q) return;
  var btn = document.getElementById('sendBtn');
  var loading = document.getElementById('loading');
  var result = document.getElementById('result');
  btn.disabled = true;
  loading.style.display = 'block';
  result.style.display = 'none';
  fetch('/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: q})
  }).then(function(r) { return r.json(); })
    .then(function(d) {
      loading.style.display = 'none';
      btn.disabled = false;
      if (d.success) {
        result.innerHTML = renderMD(d.answer);
        result.style.display = 'block';
      } else {
        result.innerHTML = '<div style="color:#d86050">❌ ' + (d.error || '未知错误') + '</div>';
        result.style.display = 'block';
      }
    }).catch(function(e) {
      loading.style.display = 'none';
      btn.disabled = false;
      result.innerHTML = '<div style="color:#d86050">❌ 网络错误</div>';
      result.style.display = 'block';
    });
}
function renderMD(t) {
  if (!t) return '';
  return t
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/```(\\w*)\\n([\\s\\S]*?)```/g,'<pre><code>$2</code></pre>')
    .replace(/\\`([^']+)\\`/g,'<code>$1</code>')
    .replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^# (.+)$/gm,'<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/^\s*[-*+] (.+)$/gm,'<li>$1</li>').replace(/(<li>.*<\/li>\\n?)+/g,'<ul>$&</ul>')
    .replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>').replace(/\\n/g,'<br>');
}
// 暗色同步
(function(){
  try {
    if (localStorage.getItem('xiaozhan_dark_mode') === 'true')
      document.body.classList.add('dark');
  } catch(e){}
})();
</script>
</body></html>"""
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    context = data.get("context", "")
    # 接受表单POST
    if not question:
        question = request.form.get("question", "").strip()
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
    # 浏览器表单提交 -> 返回 HTML 页面
    if request.content_type and "form" in request.content_type:
        html = """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>AI问答 · 结果 · 莫名心小站</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}
h1{font-size:20px;margin-bottom:4px}
.sub{color:#888;font-size:.8rem;margin-bottom:16px}
.card{background:#fff;border-radius:12px;padding:16px;margin-bottom:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.answer{font-size:14px;line-height:1.7;white-space:pre-wrap}
.error{background:#fef2f0;color:#b8453a;padding:14px;border-radius:10px;font-size:14px}
.footer{text-align:center;margin-top:20px;color:#888;font-size:.8rem}
a{color:#a0522d;text-decoration:none}
.btn{display:block;text-align:center;padding:12px;background:#b8453a;color:white;border-radius:10px;text-decoration:none;margin:16px 0}
</style></head><body><h1>🤖 AI问答</h1>
<p class="sub">提问: """ + str(question[:100]) + """</p>"""
        if result.get("success") and result.get("answer"):
            html += """<div class="card"><div class="answer">""" + result["answer"] + """</div></div>"""
        else:
            html += """<div class="card"><div class="error">""" + result.get("error", "未知错误") + """</div></div>"""
        html += """<a href="/ask" class="btn">继续提问</a>"""
        html += """<div class="footer"><a href="/tools">← 工具台</a></div></body></html>"""
        return html
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
    # 浏览器访问 -> HTML 搜索结果页
    if request.method == "GET" and "text/html" in request.headers.get("Accept", ""):
        html = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>搜索结果 · 莫名心小站</title><style>'
        html += '*{margin:0;padding:0;box-sizing:border-box}'
        html += 'body{font-family:system-ui,sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}'
        html += 'h1{font-size:20px;margin-bottom:4px}'
        html += '.sub{color:#888;font-size:.8rem;margin-bottom:16px}'
        html += '.card{background:#fff;border-radius:12px;padding:14px;margin-bottom:10px;text-decoration:none;color:#2c2c2c;display:block;box-shadow:0 1px 4px rgba(0,0,0,.06)}'
        html += '.name{font-weight:600;font-size:14px}'
        html += '.desc{color:#666;font-size:.8rem;margin-top:2px}'
        html += '.footer{text-align:center;margin-top:20px}'
        html += 'a{color:#a0522d;text-decoration:none}'
        html += 'input{width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:14px;margin-bottom:12px}'
        html += '</style></head><body>'
        html += '<form method="get" action="/knowledge-search"><input type="text" name="query" placeholder="搜索哲学概念…"></form>'
        if query:
            html += f'<p class="sub">搜索 "{query}" 的结果:</p>'
            for r in results:
                name = str(r.get('name', r.get('slug', '')))[:60]
                title = str(r.get('title', ''))[:120]
                html += f'<a class="card" href="/philosophy/{slug}"><div class="name">{name}</div><div class="desc">{title}</div><div style="font-size:11px;color:#6a5a4a;margin-top:4px">🔗 SEP原文</div></a>'
            if not results:
                html += '<p style="color:#888;text-align:center">未找到匹配结果</p>'
        else:
            html += '<p style="color:#888;text-align:center">输入关键词开始搜索</p>'
        html += '<div class="footer"><a href="/tools">← 工具台</a></div></body></html>'
        return html
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
    # 浏览器访问 -> HTML 哲思列表
    if "text/html" in request.headers.get("Accept", ""):
        html = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>哲思文库 · 莫名心小站</title><style>'
        html += '*{margin:0;padding:0;box-sizing:border-box}'
        html += 'body{font-family:"PingFang SC","Hiragino Sans GB","Noto Sans SC",system-ui,sans-serif;background:#f7f2ec;color:#3d3a36;padding:24px 16px;max-width:720px;margin:0 auto;line-height:1.75}'
        html += 'h1{font-size:1.5rem;color:#a0522d;margin-bottom:4px}'
        html += '.sub{color:#8a827a;font-size:.85rem;margin-bottom:18px}'
        html += '.card{background:#fffdf9;border:1px solid #e8dfd3;border-radius:14px;padding:16px 18px;margin-bottom:12px;text-decoration:none;color:#3d3a36;display:block;box-shadow:0 2px 10px rgba(160,82,45,.08);transition:transform .15s,box-shadow .15s}'
        html += '.card:hover{transform:translateY(-1px);box-shadow:0 4px 16px rgba(160,82,45,.14)}'
        html += '.name{font-weight:600;font-size:14px;color:#a0522d}'
        html += '.desc{color:#8a827a;font-size:.8rem;margin-top:2px}'
        html += '.footer{text-align:center;margin-top:24px;color:#8a827a;font-size:.8rem}'
        html += 'a{color:#a0522d;text-decoration:none}'
        html += 'input{width:100%;padding:12px 14px;border:1px solid #e8dfd3;border-radius:10px;font-size:14px;margin-bottom:12px;background:#fff;color:#3d3a36;outline:none}'
        html += 'input:focus{border-color:#c68a5d}'
        html += '.nav{display:flex;gap:8px;margin-bottom:18px}'
        html += '.nav a{display:inline-block;padding:6px 14px;background:#fffdf9;border:1px solid #e8dfd3;border-radius:999px;color:#a0522d;font-size:.84rem}'
        html += '.nav a:hover{background:#a0522d;color:#fff;text-decoration:none}'
        html += '.alpha-nav{display:flex;flex-wrap:wrap;gap:4px;margin:12px 0 16px}'
        html += '.alpha{display:inline-block;min-width:26px;text-align:center;padding:4px 6px;background:#fffdf9;border:1px solid #e8dfd3;border-radius:6px;color:#a0522d;font-size:.78rem;text-decoration:none}'
        html += '.alpha:hover{background:#a0522d;color:#fff}'
        html += '.alpha-group{margin-bottom:6px;border:1px solid #e8dfd3;border-radius:10px;background:#fffdf9;overflow:hidden}'
        html += '.alpha-title{padding:9px 14px;cursor:pointer;font-weight:600;font-size:.9rem;color:#a0522d;background:#faf6ef;user-select:none}'
        html += '.alpha-title .cnt{color:#b0a89c;font-weight:400;font-size:.75rem}'
        html += '.alpha-items{display:none;padding:8px}'
        html += '.alpha-group.open .alpha-items{display:block}'
        html += '.alpha-group.open .alpha-title{background:#a0522d;color:#fff}'
        html += '</style></head><body>'
        html += '<div class="nav"><a href="/tools">🧩 工具台</a><a href="/arsenal">🎯 弹药弹夹</a><a href="/">🏠 首页</a></div>'
        html += '<h1>📖 哲思文库</h1>'
        html += '<form method="get" action="/knowledge-search"><input type="text" name="query" placeholder="搜索概念…"></form>'
        # 按首字母分组（A-Z 索引折叠）
        from collections import defaultdict
        import re as _re
        def _sep_name(entry, slug):
            if isinstance(entry, dict):
                return str(entry.get('name', slug))[:60]
            return slug[:60]
        def _sep_preview(entry, slug):
            if isinstance(entry, dict):
                return str(entry.get('title', '') or entry.get('body', ''))[:90]
            return _re.sub(r'<[^>]+>', ' ', entry)[:90]
        groups = defaultdict(list)
        for slug in sorted(sep_data.keys()):
            entry = sep_data[slug]
            name = _sep_name(entry, slug)
            first = (name[0].upper() if name and name[0].isalpha() else '#')
            groups[first].append((slug, name))
        html += f'<p class="sub">共 {len(sep_data)} 条 · 点击字母展开</p>'
        html += '<div class="alpha-nav">' + ''.join(
            f'<a href="#g-{ch}" class="alpha">{ch}</a>' for ch in sorted(groups.keys())) + '</div>'
        for ch in sorted(groups.keys()):
            items = groups[ch]
            toggle_fn = 'this.parentNode.classList.toggle(\'open\')'
            html += f'<div class="alpha-group" id="g-{ch}"><div class="alpha-title" onclick="{toggle_fn}">▸ {ch} <span class="cnt">({len(items)})</span></div><div class="alpha-items">'
            for slug, name in items:
                title = _sep_preview(sep_data[slug], slug)
                html += f'<a class="card" href="/philosophy/{slug}"><div class="name">{name}</div><div class="desc">{title}</div></a>'
            html += '</div></div>'
        html += '<div class="footer"><a href="/tools">← 工具台</a></div></body></html>'
        return html
    # 合并本地词条
    词条 = _本地词条_加载()
    for slug, entry in 词条.items():
        主名 = entry["主名"]
        if slug in sep_data:
            alias_key = f"★{主名}"
            if alias_key not in sep_data:
                src = sep_data[slug]
                if isinstance(src, dict):
                    cz = src.get('_concept_zh', '')
                    body_src = src.get('body_zh', '') or src.get('body', '') or ''
                    body_en = src.get('body_en', '') or src.get('body', '') or ''
                else:
                    cz, body_src, body_en = '', str(src), ''
                sep_data[alias_key] = {
                    "name": 主名,
                    "title": f"本地词条 → {slug}" + (f" · 别名: {'、'.join(entry['别名'])}" if entry.get('别名') else ""),
                    "body": cz or body_src[:3000],
                    "body_en": body_en[:3000],
                    "_slug": slug,
                    "_concept_zh": cz,
                }
    return jsonify(sep_data)


@app.route("/philosophy/<slug>")
@login_required
def philosophy_detail(slug=""):
    """查看单条哲思条目"""
    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "sep_core.json")
    if os.path.isfile(sep_path):
        with open(sep_path, "r", encoding="utf-8") as f:
            sep_data = json.load(f)
        slug = slug.strip().lower()
        if slug in sep_data:
            entry = sep_data[slug]
            import re as _re
            if isinstance(entry, dict):
                name = str(entry.get("name", slug))
                title = str(entry.get("title", ""))
                body_zh = entry.get("body_zh", "") or entry.get("body", "") or ""
                body_en = entry.get("body_en", "") or ""
                body = body_zh or body_en
                if not body:
                    body = str(entry.get("body", "") or "")
            else:
                name, title, body = slug, "", str(entry)
                body = _re.sub(r'<[^>]+>', ' ', body)
            body = body[:10000]
            import html as hmod
            title_safe = hmod.escape(title)
            name_safe = hmod.escape(name)
            body_json = json.dumps(body, ensure_ascii=False)
            return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>{name_safe} · 哲思文库</title>
<style>
:root{{--bg:#f5f0eb;--card:#fff;--text:#2c2c2c;--text-l:#888;--accent:#b8453a}}
body.dark{{--bg:#16161a;--card:#1e1e24;--text:#ece8dc;--text-l:#b0a898;--accent:#d86050}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);padding:16px;max-width:640px;margin:0 auto}}
h1{{font-size:18px;margin-bottom:4px}}
.sub{{color:#888;font-size:.8rem;margin-bottom:16px;word-wrap:break-word}}
.content{{background:#fff;border-radius:12px;padding:16px;font-size:14px;line-height:1.8;word-wrap:break-word}}
blockquote{{margin:8px 0;padding:8px 12px;background:#faf5f0;border-left:3px solid #b8453a;color:#555;border-radius:0 8px 8px 0}}
hr{{border:none;border-top:1px dashed #e0d8d2;margin:16px 0}}
.footer{{text-align:center;margin-top:20px;font-size:.8rem;color:#888}}
a{{color:#a0522d;text-decoration:none}}
</style></head><body>
<h1>{name_safe}</h1>
<p class="sub">{title_safe}</p>
<div class="content" id="phBody"></div>
<div class="footer"><a href="https://plato.stanford.edu/entries/{slug}/" target="_blank" style="color:#2980b9">🔗 查看SEP原文</a> · <a href="/philosophy">← 哲思文库</a></div>
<script>{_MD_RENDER_JS}
document.getElementById('phBody').innerHTML = mdRender({body_json});
</script>
<script>try{{if(localStorage.getItem('xiaozhan_dark_mode')==='true')document.body.classList.add('dark')}}catch(e){{}}</script>
</body></html>"""
    return "<h1>未找到</h1><p><a href='/philosophy'>← 返回</a></p>", 404


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
    # 浏览器访问 -> HTML
    if "text/html" in request.headers.get("Accept", ""):
        h = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>学习笔记 / 莫名心小站</title><style>'
        h += '*{margin:0;padding:0;box-sizing:border-box}'
        h += 'body{font-family:"PingFang SC","Hiragino Sans GB","Noto Sans SC",system-ui,sans-serif;background:#f7f2ec;color:#3d3a36;padding:24px 16px;max-width:720px;margin:0 auto;line-height:1.75}'
        h += 'h1{font-size:1.5rem;color:#a0522d;margin-bottom:4px}'
        h += '.sub{color:#8a827a;font-size:.85rem;margin-bottom:18px}'
        h += '.sect{margin-bottom:18px}'
        h += '.stitle{font-weight:600;font-size:.9rem;color:#a0522d;margin-bottom:8px;padding-left:10px;border-left:3px solid #c68a5d}'
        h += '.card{background:#fffdf9;border:1px solid #e8dfd3;border-radius:12px;padding:14px 16px;margin-bottom:10px;box-shadow:0 2px 8px rgba(160,82,45,.06);transition:box-shadow .15s}'
        h += '.card:hover{box-shadow:0 4px 14px rgba(160,82,45,.12)}'
        h += '.card a{text-decoration:none;color:#3d3a36;display:block}'
        h += '.card-title{font-weight:500;font-size:14px;color:#3d3a36}'
        h += '.card-meta{color:#8a827a;font-size:.75rem;margin-top:2px}'
        h += '.footer{text-align:center;margin-top:24px;font-size:.8rem;color:#8a827a}'
        h += 'a{color:#a0522d;text-decoration:none}'
        h += '.empty{color:#8a827a;text-align:center;padding:40px}'
        h += '.nav{display:flex;gap:8px;margin-bottom:16px}'
        h += '.nav a{display:inline-block;padding:6px 14px;background:#fffdf9;border:1px solid #e8dfd3;border-radius:999px;color:#a0522d;font-size:.84rem}'
        h += '.nav a:hover{background:#a0522d;color:#fff;text-decoration:none}'
        h += '</style></head><body>'
        h += '<h1>📝 学习笔记</h1><p class="sub">数字中医有感</p>'
        if not categories:
            h += '<div class="empty">暂无笔记</div>'
        for cat, items in categories.items():
            h += f'<div class="sect"><div class="stitle">{cat}</div>'
            for n in items:
                fpath = n["file"]
                h += f'<div class="card"><a href="/note-view/{fpath}"><div class="card-title">{n["title"]}</div><div class="card-meta">{n["date"]}</div></a></div>'
            h += '</div>'
        h += '<div class="footer"><a href="/tools">← 工具台</a></div></body></html>'
        return h
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





@app.route("/gutenberg")
@login_required
def gutenberg():
    """古登堡计划经典搜索"""
    query = request.args.get("q", "").strip()
    results = []
    if query:
        try:
            from skills.philosophy import search_gutenberg
            results = search_gutenberg(query)
        except:
            pass
    
    h = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
    h += '<title>古登堡经典 / 莫名心小站</title><style>'
    h += '*{margin:0;padding:0;box-sizing:border-box}'
    h += 'body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}'
    h += 'h1{font-size:20px;margin-bottom:2px}'
    h += '.sub{color:#888;font-size:.8rem;margin-bottom:16px}'
    h += 'input{width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:14px;margin-bottom:12px;box-sizing:border-box}'
    h += '.card{background:#fff;border-radius:12px;padding:14px;margin-bottom:10px;box-shadow:0 1px 4px rgba(0,0,0,.06);text-decoration:none;color:#2c2c2c;display:block}'
    h += '.ctitle{font-weight:600;font-size:14px}'
    h += '.cauthor{color:#666;font-size:.8rem;margin-top:2px}'
    h += '.clink{color:#2980b9;font-size:.75rem;margin-top:4px}'
    h += '.footer{text-align:center;margin-top:20px;font-size:.8rem;color:#888}'
    h += 'a{color:#a0522d;text-decoration:none}'
    h += '</style></head><body>'
    h += '<h1>📚 古登堡经典</h1>'
    h += '<p class="sub">Project Gutenberg · 免费哲学经典搜索</p>'
    safe_q = html.escape(query)
    h += '<form method="get" action="/gutenberg"><input type="text" name="q" placeholder="搜索作者或书名…" value="' + safe_q + '"></form>'

    if not query and not results:
        h += '<p class="sub">推荐经典 · 点击阅读</p>'
        recs = [
            ("柏拉图 · 理想国", "Plato — The Republic", "https://www.gutenberg.org/ebooks/1497"),
            ("亚里士多德 · 形而上学", "Aristotle — Metaphysics", "https://www.gutenberg.org/ebooks/50504"),
            ("亚里士多德 · 尼各马可伦理学", "Aristotle — Nicomachean Ethics", "https://www.gutenberg.org/ebooks/8438"),
            ("康德 · 纯粹理性批判", "Kant — Critique of Pure Reason", "https://www.gutenberg.org/ebooks/4280"),
            ("笛卡尔 · 第一哲学沉思集", "Descartes — Meditations on First Philosophy", "https://www.gutenberg.org/ebooks/59"),
            ("休谟 · 人性论", "Hume — A Treatise of Human Nature", "https://www.gutenberg.org/ebooks/4705"),
            ("尼采 · 查拉图斯特拉如是说", "Nietzsche — Thus Spake Zarathustra", "https://www.gutenberg.org/ebooks/1998"),
            ("马克思 · 资本论", "Marx — Das Kapital", "https://www.gutenberg.org/ebooks/30107"),
        ]
        for title, author, url in recs:
            h += '<a class="card" href="' + url + '" target="_blank"><div class="ctitle">' + title + '</div><div class="cauthor">' + author + '</div><div class="clink">🔗 古登堡计划</div></a>'
    
    if results:
        for r in results[:20]:
            title = html.escape(str(r.get("title", ""))[:80])
            author = html.escape(str(r.get("author", ""))[:40])
            ebook_id = r.get("ebook_id", "")
            url = f"https://www.gutenberg.org/ebooks/{ebook_id}" if ebook_id else ""
            if url:
                h += '<a class="card" href="' + url + '" target="_blank"><div class="ctitle">' + title + '</div><div class="cauthor">' + author + '</div><div class="clink">🔗 古登堡计划</div></a>'
            else:
                h += '<div class="card"><div class="ctitle">' + title + '</div><div class="cauthor">' + author + '</div></div>'
    elif query:
        h += '<p style="text-align:center;color:#888">未找到相关结果</p>'
    
    h += '<div class="footer"><a href="/tools">← 工具台</a></div></body></html>'
    return h


@app.route("/note-view/<path:filepath>")
@login_required
def note_view(filepath=""):
    """查看单篇笔记"""
    from urllib.parse import unquote
    import html as hmod
    fp = unquote(filepath)
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "数字中医有感")
    full = os.path.join(base, fp)
    if os.path.isfile(full):
        with open(full, "r", encoding="utf-8") as f:
            md = f.read()
        lines = md.split("\n")
        title = hmod.escape(lines[0].lstrip("# ")) if lines else "笔记"
        body_md = "\n".join(lines[1:]).strip()
        body_json = json.dumps(body_md, ensure_ascii=False)
        return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}}
h1{{font-size:20px;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #e0d8d2}}
.content{{font-size:14px;line-height:1.8;word-wrap:break-word}}
blockquote{{margin:8px 0;padding:8px 12px;background:#faf5f0;border-left:3px solid #b8453a;color:#555;border-radius:0 8px 8px 0}}
hr{{border:none;border-top:1px dashed #e0d8d2;margin:16px 0}}
.footer{{text-align:center;margin-top:24px;font-size:.8rem;color:#888}}
a{{color:#a0522d;text-decoration:none}}
</style></head><body><h1>{title}</h1>
<div class="content" id="mdBody"></div>
<div class="footer"><a href="/notes">← 学习笔记</a></div>
<script>{_MD_RENDER_JS}
document.getElementById('mdBody').innerHTML = mdRender({body_json});
</script></body></html>"""
    return "<h1>未找到</h1><p><a href='/notes'>← 返回</a></p>", 404

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


@app.route("/voice-bookmarklet-v2")
def voice_bookmarklet_v2():
    """语音输入书签脚本 v2（本地 Vosk）下载"""
    return open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_bookmarklet_v2.txt"), encoding="utf-8").read(), 200, {
        "Content-Type": "text/plain; charset=utf-8",
    }


@app.route("/voice-guide")
def voice_guide():
    """语音输入安装指南"""
    return open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice_guide.html"), encoding="utf-8").read()


@app.route("/voice-script")
def voice_script():
    """语音输入用户脚本下载"""
    return open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "openclaw_voice_v2.user.js"), encoding="utf-8").read(), 200, {
        "Content-Type": "application/javascript; charset=utf-8",
        "Content-Disposition": "attachment; filename=openclaw_voice_v2.user.js",
    }


@app.route("/voice-check", methods=["GET"])
def voice_check():
    """语音能力检测页：确认浏览器 SpeechRecognition 支持情况"""
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>语音能力检测 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:560px;margin:0 auto;padding:20px}
h1{font-size:22px;color:#8e44ad}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
.item{padding:10px 0;border-bottom:1px solid #f0f0f0;font-size:14px}
.item:last-child{border:none}
.ok{color:#27ae60;font-weight:600}
.no{color:#c0392b;font-weight:600}
.btn{width:100%;padding:14px;background:#8e44ad;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:10px}
#micTest{display:none;margin-top:12px;padding:16px;background:#f8f4ff;border-radius:12px;text-align:center}
#micText{font-size:18px;color:#8e44ad;min-height:30px;margin:8px 0}
</style></head><body>
<h1>🎤 语音能力检测</h1>
<div class="card">
  <div class="item">SpeechRecognition: <span id="sr">检测中…</span></div>
  <div class="item">webkitSpeechRecognition: <span id="wsr">检测中…</span></div>
  <div class="item">SpeechRecognition.install: <span id="inst">检测中…</span></div>
  <div class="item">SpeechSynthesis: <span id="syn">检测中…</span></div>
  <div class="item">麦克风权限: <span id="mic">未测试</span></div>
  <button class="btn" id="testBtn" onclick="testMic()">🎙️ 测试麦克风 + 语音识别</button>
</div>
<div id="micTest">
  <div>请对着麦克风说一句话…</div>
  <div id="micText">…</div>
  <div id="micHint" style="font-size:12px;color:#999"></div>
</div>
<script>
var S = window.SpeechRecognition;
var WS = window.webkitSpeechRecognition;
document.getElementById('sr').innerHTML = S ? '<span class="ok">✅ 支持</span>' : '<span class="no">❌ 不支持</span>';
document.getElementById('wsr').innerHTML = WS ? '<span class="ok">✅ 支持</span>' : '<span class="no">❌ 不支持</span>';
document.getElementById('inst').innerHTML = (S && S.install) ? '<span class="ok">✅ ' + typeof S.install + '</span>' : '<span class="no">❌ 无</span>';
document.getElementById('syn').innerHTML = window.speechSynthesis ? '<span class="ok">✅ 支持</span>' : '<span class="no">❌ 不支持</span>';

function testMic() {
  var R = S || WS;
  if (!R) { document.getElementById('mic').innerHTML = '<span class="no">❌ 浏览器不支持语音识别</span>'; return; }
  try {
    var rec = new R();
    rec.lang = 'zh-CN';
    rec.interimResults = true;
    document.getElementById('mic').innerHTML = '<span class="ok">✅ 请求权限中…</span>';
    document.getElementById('micTest').style.display = 'block';
    rec.onresult = function(e) {
      var t = '';
      for (var i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
      document.getElementById('micText').textContent = t;
    };
    rec.onerror = function(e) {
      document.getElementById('mic').innerHTML = '<span class="no">❌ ' + e.error + '</span>';
      document.getElementById('micHint').textContent = '错误: ' + e.error;
    };
    rec.onend = function() {
      document.getElementById('micHint').textContent = '（已停止）';
    };
    rec.start();
  } catch(e) {
    document.getElementById('mic').innerHTML = '<span class="no">❌ 启动失败: ' + e.message + '</span>';
  }
}
</script></body></html>"""


@app.route("/kx", methods=["GET"])
@login_required
def kx_page():
    """知识库问答"""
    _html = """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>知识库问答 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f7f2ec;color:#3d3a36;max-width:720px;margin:0 auto;padding:24px 16px;line-height:1.75}
h1{font-size:1.5rem;color:#a0522d}
.sub{color:#8a827a;font-size:13px;margin-bottom:16px}
.card{background:#fffdf9;border:1px solid #e8dfd3;border-radius:14px;padding:18px 20px;box-shadow:0 2px 10px rgba(160,82,45,.08);margin-bottom:12px}
label{font-size:13px;font-weight:600;color:#555;display:block;margin:8px 0 4px}
input{width:100%;padding:12px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px;outline:none;box-sizing:border-box}
input:focus{border-color:#a0522d}
.btn{width:100%;padding:13px;background:#a0522d;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:12px}
.btn:disabled{opacity:.5}
#loading{display:none;text-align:center;padding:16px;color:#a0522d}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #eee;border-top-color:#a0522d;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#result{margin-top:12px}
.hit{background:#fff;border-radius:10px;padding:14px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05);font-size:14px;line-height:1.8}
.hit .t{font-weight:700;font-size:15px;color:#a0522d;margin-bottom:8px}
.src{display:inline-block;background:#a0522d11;color:#a0522d;padding:3px 10px;border-radius:8px;font-size:12px;margin:4px 4px 0 0}
.badge{display:inline-block;background:#a0522d11;color:#a0522d;border:1px solid #a0522d44;padding:2px 10px;border-radius:10px;font-size:11px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#a0522d;text-decoration:none}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px}
</style></head><body>
<h1>📚 知识库问答</h1>
<p class="sub">本地检索（bge embedding）· DeepSeek 回答 · 来源可追溯</p>
<div class="card">
  <label>问题</label>
  <input type="text" id="q" placeholder="如：道归是什么？素问怎么论述阴阳？" value="道归是什么">
  <button class="btn" id="goBtn" onclick="run()">🔍 提问</button>
</div>
<div id="loading"><div class="spinner"></div><p>检索知识库中…</p></div>
<div id="result"></div>
<p class="note">🔒 知识库含道归体系 · 医书经典 · 哲学典籍（74篇文档）</p>
<p class="footer"><a href="/tools">← 返回工具台</a></p>
<script>__MD_RENDER_JS__
async function run(){
  var b=document.getElementById('goBtn');b.disabled=true;
  document.getElementById('loading').style.display='block';
  document.getElementById('result').innerHTML='';
  var body={q:document.getElementById('q').value};
  try{
    var r=await fetch('/kx',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify(body)});
    var d=await r.json();
    document.getElementById('loading').style.display='none';
    if(d.error){document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ '+d.error+'</div>';b.disabled=false;return}
    var raw = d.answer.replace(/<br\s*\/?>/gi, '\\n').replace(/&quot;/g, '"').replace(/&amp;/g, '&');
    var h='<div class="hit"><div class="t">📚 回答</div>'+mdRender(raw)+'</div>';
    if(d.sources&&d.sources.length){
      h+='<div class="hit"><div class="t">📎 引用来源</div>';
      d.sources.forEach(function(s){
        h+='<div style="margin-bottom:10px">';
        h+='<span class="src">'+s.title+' ('+s.score+')</span>';
        if(s.text){h+='<blockquote style="margin:6px 0 0;padding:6px 10px;border-left:3px solid #a0522d55;background:#a0522d0a;font-size:13px;color:#555">'+s.text+'…</blockquote>'}
        h+='</div>';
      });
      h+='</div>';
    }
    document.getElementById('result').innerHTML=h;
  }catch(e){
    document.getElementById('loading').style.display='none';
    document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ 请求失败: '+e.message+'</div>';
  }
  b.disabled=false;
}
</script></body></html>"""
    return _html.replace("__MD_RENDER_JS__", _MD_RENDER_JS)


@app.route("/kx", methods=["POST"])
@login_required
@rate_limit
def kx_api():
    """知识库问答 API"""
    data = request.get_json(silent=True) or {}
    q = (data.get("q", "") or "").strip()[:200]
    if not q:
        return jsonify({"error": "问题不能为空"}), 400
    try:
        import kx_ask as _kx
        result = _kx.ask(q, top_k=3)
        answer = html.escape(result.get("answer", ""))[:6000]
        sources = [
            {"title": s["title"][:80], "score": s["score"], "path": s.get("path", "")[:120],
             "text": s.get("text", "")[:200]}
            for s in result.get("sources", [])
        ]
        return jsonify({"answer": answer.replace("\n", "<br>"), "sources": sources})
    except Exception as e:
        return jsonify({"error": f"问答失败: {str(e)[:200]}"}), 500


@app.route("/ai-read", methods=["POST"])
@login_required
@rate_limit
def ai_read_api():
    """AI 解读 API（诗词/术数盘面 → DeepSeek 分析）"""
    data = request.get_json(silent=True) or {}
    text = (data.get("text", "") or "").strip()[:8000]
    scene = (data.get("scene", "xuanxue_general") or "xuanxue_general").strip()
    if not text:
        return jsonify({"error": "内容不能为空"}), 400
    try:
        import ai_reader as _ar
        result = _ar.ai_read(text, scene)
        return jsonify({"answer": result})
    except Exception as e:
        return jsonify({"error": f"AI 解读失败: {str(e)[:150]}"}), 500


@app.route("/poetry", methods=["GET"])
@login_required
def poetry_page():
    """诗词查询页（31万诗词+诗经+论语）"""
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>诗词查询 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f8f5f0;color:#2c2c2c;max-width:720px;margin:0 auto;padding:16px}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.topbar a{color:#b8860b;text-decoration:none;font-size:14px}
h1{font-size:22px;color:#b8860b;margin:0}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.search{display:flex;gap:8px;margin-bottom:16px}
.search input{flex:1;padding:12px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px;outline:none}
.search button{padding:12px 20px;background:#b8860b;color:#fff;border:none;border-radius:10px;font-size:15px;cursor:pointer}
.tabs{display:flex;gap:8px;margin-bottom:12px}
.tabs button{padding:6px 14px;border:2px solid #e0d8d2;border-radius:20px;background:#fff;font-size:13px;cursor:pointer;color:#666}
.tabs button.on{background:#b8860b;color:#fff;border-color:#b8860b}
.result{background:#fff;border-radius:12px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:12px}
.result h3{margin:0 0 6px;font-size:16px;color:#8b6914}
.result .meta{color:#999;font-size:12px;margin-bottom:8px}
.result pre{white-space:pre-wrap;font-family:"Kaiti SC",KaiTi,serif;font-size:15px;line-height:1.8;margin:0;color:#333}
.empty{color:#999;text-align:center;padding:30px}
.footer{text-align:center;color:#aaa;font-size:12px;margin-top:20px}
.footer a{color:#b8860b;text-decoration:none}
</style></head><body>
<div class="topbar"><a href="/tools">🧰 返回工作台</a></div>
<h1>🏮 诗词查询</h1>
<p class="sub">31万首诗词 · 诗经305篇 · 论语 · 本地检索</p>
<div class="search">
<input id="kw" placeholder="输入关键词/诗句/作者…（支持简体）" value="明月">
<button onclick="go()">搜索</button>
</div>
<div class="tabs">
<button class="on" onclick="setTab(this,'all')">全部</button>
<button onclick="setTab(this,'poem')">正文</button>
<button onclick="setTab(this,'title')">标题</button>
<button onclick="setTab(this,'author')">作者</button>
<button onclick="setTab(this,'shijing')">诗经</button>
</div>
<div id="out"></div>
<p class="footer"><a href="/tools">← 返回工具台</a> · 🌙 莫名心</p>
<script>
let mode='all';
function setTab(el,m){document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('on'));el.classList.add('on');mode=m;go();}
async function go(){
  const kw=document.getElementById('kw').value.trim();
  if(!kw){document.getElementById('out').innerHTML='<div class="empty">请输入关键词</div>';return;}
  const out=document.getElementById('out');
  out.innerHTML='<div class="empty">搜索中…</div>';
  try{
    const r=await fetch('/poetry',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({q:kw,mode})});
    const d=await r.json();
    if(d.error){out.innerHTML='<div class="empty">'+d.error+'</div>';return;}
    if(!d.items||!d.items.length){out.innerHTML='<div class="empty">未找到相关诗词</div>';return;}
    out.innerHTML=d.items.map(x=>'<div class="result" style="cursor:pointer" data-t="'+x.title+'" data-a="'+x.author+'" data-tp="'+x.type+'" data-rid="'+(x.rowid||'')+'" onclick="goDetail(this)"><h3>'+x.title+'</h3><div class="meta">['+x.type+'] '+x.author+'</div><pre>'+x.content+'</pre><div class="hint" style="color:#b8860b;font-size:12px;text-align:right;margin-top:6px">点击查看详情 →</div></div>').join('');
  }catch(e){out.innerHTML='<div class="empty">请求失败</div>';}
}
async function goDetail(el){
  const t=el.dataset.t, a=el.dataset.a, tp=el.dataset.tp, rid=el.dataset.rid;
  location.href='/poetry-view?title='+encodeURIComponent(t)+'&author='+encodeURIComponent(a)+'&type='+encodeURIComponent(tp)+'&rid='+encodeURIComponent(rid);
}
async function aiRead(btn,ev){
  ev.stopPropagation();
  const box=btn.parentNode.querySelector('.ai-out');
  const pre=btn.parentNode.querySelector('pre');
  if(box.innerHTML){box.innerHTML='';return}
  box.innerHTML='<div class="empty">AI 解读中…</div>';
  try{
    const r=await fetch('/ai-read',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({text:pre.textContent.slice(0,800),scene:'poetry'})});
    const d=await r.json();
    box.innerHTML=d.error?'<div class="empty">'+d.error+'</div>':'<div class="ai-body">'+mdRender(d.answer)+'</div>';
  }catch(e){box.innerHTML='<div class="empty">请求失败</div>';}
}
go();


function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}

async function aiXuan(btn){
  var out=document.getElementById('aiOut');
  if(!out){out=document.createElement('div');out.id='aiOut';btn.parentNode.appendChild(out)}
  if(out.innerHTML){out.innerHTML='';return}
  out.innerHTML='<div style="padding:12px;color:#888">AI 分析中…（约30秒）</div>';
  var _t=setTimeout(function(){out.innerHTML='<div style="padding:12px;color:#c0392b">⏱ AI 响应超时，请重试</div>';},30000);
  var hit=btn.parentNode.querySelector('.hit');
  var report=hit?hit.innerText:'';
  if(!report) report=btn.parentNode.innerText;
  try{
    var r=await fetch('/ai-read',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({text:report.slice(0,6000),scene:'xuanxue_general'})});
    var d=await r.json();clearTimeout(_t);
    out.innerHTML=d.error?'<div style="padding:12px;color:#c0392b">'+d.error+'</div>':'<div style="padding:14px;background:#fff8e6;border-radius:10px;margin-top:10px;line-height:1.7">'+mdRender(d.answer)+'</div>';
  }catch(e){clearTimeout(_t);out.innerHTML='<div style="padding:12px;color:#c0392b">请求失败</div>';}
}
</script></body></html>"""


@app.route("/poetry-view", methods=["GET"])
@login_required
def poetry_view_page():
    """诗词详情页：完整原文 + AI 生成作者生平/写作背景/赏析"""
    title = request.args.get("title", "")[:80]
    author = request.args.get("author", "")[:40]
    typ = request.args.get("type", "")[:10]
    rid = request.args.get("rid", "")[:12]
    if not title:
        return redirect("/poetry")
    import poetry_query as _pq
    poem = _pq.get_poem_full(title, author, typ, rid or None)
    if not poem:
        return redirect("/poetry")
    t = html.escape(poem["title"])
    a = html.escape(poem["author"])
    tp = html.escape(poem["type"])
    content = html.escape(poem["content"])
    # 拼一个带 id 的原始内容（给前端取原文用，避免转义干扰）
    return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{t} · 诗词详情 · 莫名心小站</title>
<style>
body{{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f8f5f0;color:#2c2c2c;max-width:720px;margin:0 auto;padding:16px}}
h1{{font-size:24px;color:#8b6914;margin-bottom:4px}}
.sub{{color:#888;font-size:13px;margin-bottom:16px}}
.back{{display:inline-block;margin-bottom:14px;color:#b8860b;text-decoration:none;font-size:14px}}
.poem{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:16px}}
.poem pre{{white-space:pre-wrap;font-family:"Kaiti SC",KaiTi,serif;font-size:16px;line-height:1.9;margin:0;color:#333}}
.ai-box{{background:#fff;border-radius:12px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}
.ai-box h2{{font-size:17px;color:#b8860b;margin:0 0 10px}}
.ai-body{{font-size:14px;line-height:1.8;color:#333;white-space:pre-wrap}}
.loading{{color:#999;font-size:13px;padding:10px 0}}
.err{{color:#c0392b;font-size:13px;padding:10px 0}}
.footer{{text-align:center;color:#aaa;font-size:12px;margin-top:20px}}
.footer a{{color:#b8860b;text-decoration:none}}
</style></head><body>
<a class="back" href="/tools">🧰 返回工作台</a> &nbsp;·&nbsp; <a class="back" href="/poetry">← 返回诗词查询</a>
<h1>{t}</h1>
<p class="sub">[{tp}] {a}</p>
<div class="poem"><pre>{content}</pre></div>
<div class="ai-box">
<h2>📜 AI 详情档案（作者生平 · 写作背景 · 赏析）</h2>
<div id="aiBody" class="loading">AI 正在翻阅典籍，生成中…（约30秒）</div>
</div>
<p class="footer"><a href="/poetry">← 返回诗词查询</a> · 🌙 莫名心</p>
<script>
const poemRaw = {json.dumps(poem["content"], ensure_ascii=False)};
const metaText = '【诗词详情】\\n标题：' + {json.dumps(poem["title"], ensure_ascii=False)} + '\\n作者：' + {json.dumps(poem["author"], ensure_ascii=False)} + '\\n\\n' + poemRaw;
async function loadAI(){{
  try{{
    const r=await fetch('/ai-read',{{method:'POST',headers:{{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'}},body:JSON.stringify({{text:metaText.slice(0,3000),scene:'poetry_detail'}})}});
    const d=await r.json();
    document.getElementById('aiBody').innerHTML=d.error?'<div class="err">'+d.error+'</div>':'<div class="ai-body">'+d.answer.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>')+'</div>';
  }}catch(e){{document.getElementById('aiBody').innerHTML='<div class="err">请求失败，请稍后重试</div>';}}
}}
loadAI();
</script></body></html>"""


@app.route("/poetry", methods=["POST"])
@login_required
@rate_limit
def poetry_api():
    """诗词查询 API"""
    data = request.get_json(silent=True) or {}
    q = (data.get("q", "") or "").strip()[:100]
    mode = (data.get("mode", "all") or "all").strip()
    if not q:
        return jsonify({"error": "关键词不能为空"}), 400
    try:
        import poetry_query as _pq
        items = []
        if mode in ("all", "poem"):
            items += _pq.search_poem(q, top=5)
        if mode in ("all", "title"):
            items += _pq.search_poem_by_title(q, top=5)
        if mode in ("all", "author"):
            items += _pq.search_by_author(q, top=5)
        if mode in ("all", "shijing"):
            items += _pq.search_shijing(q, top=5)
        if mode in ("all", "lunyu"):
            items += _pq.search_lunyu(q, top=3)
        # 去重（按 类型+标题+内容前30）
        seen, uniq = set(), []
        for it in items:
            k = it["type"] + it["title"] + it["content"][:30]
            if k not in seen:
                seen.add(k)
                uniq.append(it)
        out = []
        for it in uniq[:8]:
            out.append({
                "type": it["type"],
                "title": it["title"][:60],
                "author": it["author"][:40],
                "content": it["content"][:600],
                "rowid": it.get("rowid"),
            })
        return jsonify({"items": out})
    except Exception as e:
        return jsonify({"error": f"查询失败: {str(e)[:150]}"}), 500


@app.route("/jyotish", methods=["GET"])
@login_required
def jyotish_page():
    """印占+太乙+梅花"""
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>印占·太乙·梅花 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:680px;margin:0 auto;padding:16px}
h1{font-size:22px;color:#d35400}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
label{font-size:13px;font-weight:600;color:#555;display:block;margin:8px 0 4px}
input,select{width:100%;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px;outline:none;box-sizing:border-box}
input:focus,select:focus{border-color:#d35400}
.row{display:flex;gap:10px}
.row>div{flex:1}
.btn{width:100%;padding:13px;background:#d35400;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:12px}
.btn:disabled{opacity:.5}
#loading{display:none;text-align:center;padding:16px;color:#d35400}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #eee;border-top-color:#d35400;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#result{margin-top:12px}
.hit{background:#fff;border-radius:10px;padding:14px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05);font-size:13px;white-space:pre-wrap;line-height:1.8;overflow-x:auto}
.hit .t{font-weight:700;font-size:15px;color:#d35400;margin-bottom:8px}
.badge{display:inline-block;background:#d3540011;color:#d35400;border:1px solid #d3540044;padding:2px 10px;border-radius:10px;font-size:11px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#d35400;text-decoration:none}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px}
</style></head><body>
<h1>🌏 星盘术数</h1>
<p class="sub">印占 · 太乙 · 梅花 · 西洋占星（一次选一个体系）</p>
<div class="card">
  <label>体系</label>
  <select id="sys">
    <option value="jyotish">🕉️ 印占 Jyotish（吠陀星盘）</option>
    <option value="taiyi">☯️ 太乙神数</option>
    <option value="meihua">🌸 梅花易数</option>
    <option value="western">🌟 西洋占星</option>
  </select>
  <label>出生日期</label>
  <input type="date" id="bdate" value="2006-09-22">
  <div class="row">
    <div><label>时间</label><input type="time" id="btime" value="07:56"></div>
    <div><label>性别</label><select id="gender"><option value="male">男</option><option value="female">女</option></select></div>
  </div>
  <label>经度（可选）</label>
  <input type="text" id="lon" placeholder="如 114.88">
  <label>纬度（可选）</label>
  <input type="text" id="lat" placeholder="如 40.82">
  <button class="btn" id="goBtn" onclick="run()">🌏 起盘</button>
</div>
<div id="loading"><div class="spinner"></div><p>排盘中…</p></div>
<div id="result"></div>
<p class="note">🔒 纯本地计算</p>
<p class="footer"><a href="/tools">← 返回工具台</a></p>
<script>
async function run(){
  var b=document.getElementById('goBtn');b.disabled=true;
  document.getElementById('loading').style.display='block';
  document.getElementById('result').innerHTML='';
  var body={date:document.getElementById('bdate').value,time:document.getElementById('btime').value,gender:document.getElementById('gender').value,lon:document.getElementById('lon').value,lat:document.getElementById('lat').value,system:document.getElementById('sys').value};
  try{
    var r=await fetch('/jyotish',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify(body)});
    var d=await r.json();
    document.getElementById('loading').style.display='none';
    if(d.error){document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ '+d.error+'</div>';b.disabled=false;return}
    var names={jyotish:'🕉️ 印占星盘',taiyi:'☯️ 太乙神数',meihua:'🌸 梅花易数',western:'🌟 西洋占星'};
    var sysName=names[document.getElementById('sys').value]||'星盘';
    var h='<div class="hit"><div class="t">'+sysName+'</div>'+mdRender(d.report)+'</div><button class="btn" style="background:#d35400" onclick="aiXuan(this)">🔮 AI 深度分析</button><div id="aiOut"></div>';
    document.getElementById('result').innerHTML=h;
  }catch(e){
    document.getElementById('loading').style.display='none';
    document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ 请求失败: '+e.message+'</div>';
  }
  b.disabled=false;
}
function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}

async function aiXuan(btn){
  var out=document.getElementById('aiOut');
  if(!out){out=document.createElement('div');out.id='aiOut';btn.parentNode.appendChild(out)}
  if(out.innerHTML){out.innerHTML='';return}
  out.innerHTML='<div style="padding:12px;color:#888">AI 分析中…（约30秒）</div>';
  var _t=setTimeout(function(){out.innerHTML='<div style="padding:12px;color:#c0392b">⏱ AI 响应超时，请重试</div>';},30000);
  var hit=btn.parentNode.querySelector('.hit');
  var report=hit?hit.innerText:'';
  if(!report) report=btn.parentNode.innerText;
  try{
    var r=await fetch('/ai-read',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({text:report.slice(0,6000),scene:'xuanxue_general'})});
    var d=await r.json();clearTimeout(_t);
    out.innerHTML=d.error?'<div style="padding:12px;color:#c0392b">'+d.error+'</div>':'<div style="padding:14px;background:#fff8e6;border-radius:10px;margin-top:10px;line-height:1.7">'+mdRender(d.answer)+'</div>';
  }catch(e){clearTimeout(_t);out.innerHTML='<div style="padding:12px;color:#c0392b">请求失败</div>';}
}
</script></body></html>"""


@app.route("/jyotish", methods=["POST"])
@login_required
@rate_limit
def jyotish_api():
    """印占/太乙/梅花/西洋占星 API（拆开，一次算一个体系）"""
    data = request.get_json(silent=True) or {}
    date_str = data.get("date", "") or ""
    time_str = data.get("time", "12:00") or "12:00"
    gender = data.get("gender", "male")
    lon = data.get("lon", "")
    lat = data.get("lat", "")
    system = (data.get("system", "jyotish") or "jyotish").strip()[:20]
    import re as _re
    if not _re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return jsonify({"error": "日期格式应为 YYYY-MM-DD"}), 400
    try:
        import jyotish_steward as _js
        lon_f = float(lon) if lon else None
        lat_f = float(lat) if lat else None
        if system == "taiyi":
            try:
                d = _js.cast_taiyi(date_str, time_str, gender, lat_f, lon_f)
                return jsonify({"report": html.escape("【太乙神数】\n" + _js._fmt_taiyi(d))[:9000]})
            except Exception as e:
                return jsonify({"report": html.escape(f"【太乙】错误: {e}")[:150]})
        if system == "meihua":
            try:
                d = _js.cast_suimei(date_str, time_str, gender, lat_f, lon_f)
                return jsonify({"report": html.escape("【梅花易数】\n" + _js._fmt_suimei(d))[:9000]})
            except Exception as e:
                return jsonify({"report": html.escape(f"【梅花】错误: {e}")[:150]})
        if system == "western":
            try:
                d = _js.cast_astrology(date_str, time_str, gender, lat_f, lon_f)
                return jsonify({"report": html.escape("【西洋占星】\n" + _js._fmt_astrology(d))[:9000]})
            except Exception as e:
                return jsonify({"report": html.escape(f"【西洋】错误: {e}")[:150]})
        # 默认：印占
        try:
            d = _js.cast_jyotish(date_str, time_str, gender, lat_f, lon_f)
            return jsonify({"report": html.escape("【印占 Jyotish】\n" + _js._fmt_jyotish(d))[:9000]})
        except Exception as e:
            return jsonify({"report": html.escape(f"【印占】错误: {e}")[:150]})
    except Exception as e:
        return jsonify({"error": f"排盘失败: {str(e)[:200]}"}), 500


@app.route("/liuyao", methods=["GET"])
@login_required
def liuyao_page():
    """六爻纳甲"""
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>六爻 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:680px;margin:0 auto;padding:16px}
h1{font-size:22px;color:#27ae60}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
label{font-size:13px;font-weight:600;color:#555;display:block;margin:8px 0 4px}
input,select{width:100%;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px;outline:none;box-sizing:border-box}
input:focus,select:focus{border-color:#27ae60}
.row{display:flex;gap:10px}
.row>div{flex:1}
.btn{width:100%;padding:13px;background:#27ae60;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:12px}
.btn:disabled{opacity:.5}
#loading{display:none;text-align:center;padding:16px;color:#27ae60}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #eee;border-top-color:#27ae60;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#result{margin-top:12px}
.hit{background:#fff;border-radius:10px;padding:14px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05);font-size:13px;white-space:pre-wrap;line-height:1.8;overflow-x:auto}
.hit .t{font-weight:700;font-size:15px;color:#27ae60;margin-bottom:8px}
.badge{display:inline-block;background:#27ae6011;color:#27ae60;border:1px solid #27ae6044;padding:2px 10px;border-radius:10px;font-size:11px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#27ae60;text-decoration:none}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px}
</style></head><body>
<h1>⚡ 六爻纳甲</h1>
<p class="sub">三币摇卦 · 四柱 · 六亲 · 神煞 · 变卦</p>
<div class="card">
  <label>所占之事</label>
  <input type="text" id="subject" placeholder="如：事业发展、找东西、感情…" value="事业发展">
  <label>意图</label>
  <select id="intent">
    <option>通用</option><option>求财</option><option>官运</option><option>学业</option>
    <option>感情</option><option>健康</option><option>孕产</option><option>出行</option>
    <option>失物</option><option>词讼</option><option>天气</option>
  </select>
  <label>手动六爻（可选，6位1-4自下而上，留空=三币随机）</label>
  <input type="text" id="yao" placeholder="如 112211">
  <button class="btn" id="goBtn" onclick="run()">⚡ 起卦</button>
</div>
<div id="loading"><div class="spinner"></div><p>摇卦中…</p></div>
<div id="result"></div>
<p class="note">🔒 纯本地计算</p>
<p class="footer"><a href="/tools">← 返回工具台</a></p>
<script>
async function run(){
  var b=document.getElementById('goBtn');b.disabled=true;
  document.getElementById('loading').style.display='block';
  document.getElementById('result').innerHTML='';
  var body={subject:document.getElementById('subject').value,intent:document.getElementById('intent').value,yao:document.getElementById('yao').value};
  try{
    var r=await fetch('/liuyao',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify(body)});
    var d=await r.json();
    document.getElementById('loading').style.display='none';
    if(d.error){document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ '+d.error+'</div>';b.disabled=false;return}
    var h='<div class="hit"><div class="t">⚡ 六爻卦</div>'+mdRender(d.report)+'</div><button class="btn" style="background:#27ae60" onclick="aiXuan(this)">🔮 AI 深度分析</button><div id="aiOut"></div>';
    document.getElementById('result').innerHTML=h;
  }catch(e){
    document.getElementById('loading').style.display='none';
    document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ 请求失败: '+e.message+'</div>';
  }
  b.disabled=false;
}
function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}

async function aiXuan(btn){
  var out=document.getElementById('aiOut');
  if(!out){out=document.createElement('div');out.id='aiOut';btn.parentNode.appendChild(out)}
  if(out.innerHTML){out.innerHTML='';return}
  out.innerHTML='<div style="padding:12px;color:#888">AI 分析中…（约30秒）</div>';
  var _t=setTimeout(function(){out.innerHTML='<div style="padding:12px;color:#c0392b">⏱ AI 响应超时，请重试</div>';},30000);
  var hit=btn.parentNode.querySelector('.hit');
  var report=hit?hit.innerText:'';
  if(!report) report=btn.parentNode.innerText;
  try{
    var r=await fetch('/ai-read',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({text:report.slice(0,6000),scene:'xuanxue_general'})});
    var d=await r.json();clearTimeout(_t);
    out.innerHTML=d.error?'<div style="padding:12px;color:#c0392b">'+d.error+'</div>':'<div style="padding:14px;background:#fff8e6;border-radius:10px;margin-top:10px;line-height:1.7">'+mdRender(d.answer)+'</div>';
  }catch(e){clearTimeout(_t);out.innerHTML='<div style="padding:12px;color:#c0392b">请求失败</div>';}
}
</script></body></html>"""


@app.route("/liuyao", methods=["POST"])
@login_required
@rate_limit
def liuyao_api():
    """六爻 API"""
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject", "") or "占事").strip()[:30]
    intent = (data.get("intent", "") or "通用").strip()[:10]
    yao = (data.get("yao", "") or "").strip()
    try:
        import liuyao_steward as _ls
        result = _ls.cast_liuyao(subject, intent, yao=yao or None)
        report = _ls._fmt_liuyao(result)
        return jsonify({"report": html.escape(report)[:9000]})
    except Exception as e:
        return jsonify({"error": f"起卦失败: {str(e)[:200]}"}), 500


@app.route("/qimen", methods=["GET"])
@login_required
def qimen_page():
    """奇门遁甲"""
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>奇门遁甲 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:680px;margin:0 auto;padding:16px}
h1{font-size:22px;color:#2980b9}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
label{font-size:13px;font-weight:600;color:#555;display:block;margin:8px 0 4px}
input,select{width:100%;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px;outline:none;box-sizing:border-box}
input:focus,select:focus{border-color:#2980b9}
.row{display:flex;gap:10px}
.row>div{flex:1}
.btn{width:100%;padding:13px;background:#2980b9;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:12px}
.btn:disabled{opacity:.5}
#loading{display:none;text-align:center;padding:16px;color:#2980b9}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #eee;border-top-color:#2980b9;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#result{margin-top:12px}
.hit{background:#fff;border-radius:10px;padding:14px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05);font-size:13px;white-space:pre-wrap;line-height:1.8;overflow-x:auto}
.hit .t{font-weight:700;font-size:15px;color:#2980b9;margin-bottom:8px}
.badge{display:inline-block;background:#2980b911;color:#2980b9;border:1px solid #2980b944;padding:2px 10px;border-radius:10px;font-size:11px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#2980b9;text-decoration:none}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px}
</style></head><body>
<h1>🗺️ 奇门遁甲</h1>
<p class="sub">拆补法定局 · 天文节气 · 九宫格局判定</p>
<div class="card">
  <div style="background:#eaf4fb;border:1px solid #2980b944;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:12px;color:#1a5276">⏰ <b>已自动填当下时间</b>：奇门测事以当下时辰起盘（不是生辰！）。直接点起盘即可；确有需要可手动改时间。</div>
  <label>求测目的</label>
  <select id="purpose">
    <option value="考试学业">📚 考试学业</option>
    <option value="事业工作">💼 事业工作</option>
    <option value="感情婚姻">❤️ 感情婚姻</option>
    <option value="健康疾病">🏥 健康疾病</option>
    <option value="财运求财">💰 财运求财</option>
    <option value="出行寻人">🚶 出行寻人</option>
    <option value="官司诉讼">⚖️ 官司诉讼</option>
    <option value="其他">❓ 其他</option>
  </select>
  <label>日期</label>
  <input type="date" id="bdate">
  <div class="row">
    <div><label>时辰</label><select id="hour">
      <option value="0">子时(23-1)</option><option value="2">丑时(1-3)</option><option value="4">寅时(3-5)</option>
      <option value="6">卯时(5-7)</option><option value="8">辰时(7-9)</option><option value="10">巳时(9-11)</option>
      <option value="12">午时(11-13)</option><option value="14">未时(13-15)</option><option value="16">申时(15-17)</option>
      <option value="18">酉时(17-19)</option><option value="20">戌时(19-21)</option><option value="22">亥时(21-23)</option>
    </select></div>
  </div>
  <button class="btn" id="goBtn" onclick="run()">🗺️ 起盘</button>
</div>
<div id="loading"><div class="spinner"></div><p>奇门排盘中…</p></div>
<div id="result"></div>
<p class="note">🔒 纯本地计算 · 拆补法</p>
<p class="footer"><a href="/tools">← 返回工具台</a></p>
<script>
// 自动填当下时间（奇门测事以当下时辰起盘，不是生辰）
(function(){
  var now=new Date();
  var pad=function(n){return (n<10?'0':'')+n};
  document.getElementById('bdate').value = now.getFullYear()+'-'+pad(now.getMonth()+1)+'-'+pad(now.getDate());
  var h=now.getHours();
  var sh = (h===23||h===0)?0:(h===1||h===2)?2:(h===3||h===4)?4:(h===5||h===6)?6:(h===7||h===8)?8:(h===9||h===10)?10:(h===11||h===12)?12:(h===13||h===14)?14:(h===15||h===16)?16:(h===17||h===18)?18:(h===19||h===20)?20:22;
  document.getElementById('hour').value = String(sh);
})();
async function run(){
  var b=document.getElementById('goBtn');b.disabled=true;
  document.getElementById('loading').style.display='block';
  document.getElementById('result').innerHTML='';
  var body={date:document.getElementById('bdate').value,hour:document.getElementById('hour').value,purpose:document.getElementById('purpose').value};
  try{
    var r=await fetch('/qimen',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify(body)});
    var d=await r.json();
    document.getElementById('loading').style.display='none';
    if(d.error){document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ '+d.error+'</div>';b.disabled=false;return}
    var h='<div class="hit"><div class="t">🗺️ 奇门盘</div>'+mdRender(d.report)+'</div><button class="btn" style="background:#2980b9" onclick="aiXuan(this)">🔮 AI 深度分析</button><div id="aiOut"></div>';
    document.getElementById('result').innerHTML=h;
  }catch(e){
    document.getElementById('loading').style.display='none';
    document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ 请求失败: '+e.message+'</div>';
  }
  b.disabled=false;
}
function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}

async function aiXuan(btn){
  var out=document.getElementById('aiOut');
  if(!out){out=document.createElement('div');out.id='aiOut';btn.parentNode.appendChild(out)}
  if(out.innerHTML){out.innerHTML='';return}
  out.innerHTML='<div style="padding:12px;color:#888">AI 分析中…（约30秒）</div>';
  var _t=setTimeout(function(){out.innerHTML='<div style="padding:12px;color:#c0392b">⏱ AI 响应超时，请重试</div>';},30000);
  var hit=btn.parentNode.querySelector('.hit');
  var report=hit?hit.innerText:'';
  if(!report) report=btn.parentNode.innerText;
  try{
    var r=await fetch('/ai-read',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({text:report.slice(0,6000),scene:'xuanxue_general'})});
    var d=await r.json();clearTimeout(_t);
    out.innerHTML=d.error?'<div style="padding:12px;color:#c0392b">'+d.error+'</div>':'<div style="padding:14px;background:#fff8e6;border-radius:10px;margin-top:10px;line-height:1.7">'+mdRender(d.answer)+'</div>';
  }catch(e){clearTimeout(_t);out.innerHTML='<div style="padding:12px;color:#c0392b">请求失败</div>';}
}
</script></body></html>"""


@app.route("/qimen", methods=["POST"])
@login_required
@rate_limit
def qimen_api():
    """奇门遁甲 API"""
    data = request.get_json(silent=True) or {}
    date_str = data.get("date", "") or ""
    hour = data.get("hour", "8")
    purpose = (data.get("purpose", "") or "").strip()[:20]
    import re as _re
    if not _re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        # 没传/传错日期 → 自动用当下时间（奇门测事以当下时辰起盘）
        from datetime import datetime as _dt
        date_str = _dt.now().strftime("%Y-%m-%d")
    try:
        import qimen_steward as _qs
        y, m, d = [int(x) for x in date_str.split("-")]
        h = int(hour)
        if not (0 <= h <= 23):
            h = _dt.now().hour
            h = (h // 2) * 2  # 归入时辰
        result = _qs.cast_qimen(y, m, d, h)
        report = _qs._fmt_pan(result)
        if purpose:
            report = f"🎯 求测目的: {purpose}\n" + report
        return jsonify({"report": html.escape(report)[:9000]})
    except Exception as e:
        return jsonify({"error": f"排盘失败: {str(e)[:200]}"}), 500


@app.route("/bazi-ziwei", methods=["GET"])
@login_required
def bazi_ziwei_page():
    """八字 + 紫微综合印证"""
    html = """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>八字+紫微印证 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:680px;margin:0 auto;padding:16px}
h1{font-size:22px;color:#b8453a}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
label{font-size:13px;font-weight:600;color:#555;display:block;margin:8px 0 4px}
input,select{width:100%;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px;outline:none;box-sizing:border-box}
input:focus,select:focus{border-color:#b8453a}
.row{display:flex;gap:10px}
.row>div{flex:1}
.btn{width:100%;padding:13px;background:#b8453a;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:12px}
.btn:disabled{opacity:.5}
#loading{display:none;text-align:center;padding:16px;color:#b8453a}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #eee;border-top-color:#b8453a;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#result{margin-top:12px}
.hit{background:#fff;border-radius:10px;padding:14px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05);font-size:13px;white-space:pre-wrap;line-height:1.8;overflow-x:auto}
.hit .t{font-weight:700;font-size:15px;color:#b8453a;margin-bottom:8px}
.badge{display:inline-block;background:#b8453a11;color:#b8453a;border:1px solid #b8453a44;padding:2px 10px;border-radius:10px;font-size:11px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#b8453a;text-decoration:none}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px}
/* 喜忌卡片样式 */
.sec{background:#fff;border-radius:14px;padding:16px 18px;margin-top:10px;box-shadow:0 2px 10px rgba(0,0,0,.06)}
.sec h3{margin:0 0 10px;font-size:15px;color:#333;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.pill{display:inline-block;padding:3px 12px;border-radius:12px;font-size:12px;font-weight:600;margin-right:6px}
.pill-red{background:#e74c3c22;color:#e74c3c;border:1px solid #e74c3c55}
.pill-green{background:#27ae6022;color:#27ae60;border:1px solid #27ae6055}
.pill-gold{background:#f39c1222;color:#d68910;border:1px solid #f39c1255}
.pill-gray{background:#7f8c8d22;color:#7f8c8d;border:1px solid #7f8c8d55}
.xj-grid{display:flex;gap:8px;flex-wrap:wrap}
.xj-box{flex:1;min-width:120px;background:#faf7f3;border-radius:10px;padding:10px 12px}
.xj-box .lb{font-size:11px;color:#888;margin-bottom:6px}
.xj-box .val{font-weight:700;font-size:14px}
.xi-chips span{display:inline-block;background:#27ae6022;color:#27ae60;border:1px solid #27ae6055;padding:2px 10px;border-radius:10px;font-size:12px;margin:2px}
.ji-chips span{display:inline-block;background:#e74c3c22;color:#e74c3c;border:1px solid #e74c3c55;padding:2px 10px;border-radius:10px;font-size:12px;margin:2px}
.reason{background:#fdfaf5;border-left:3px solid #b8453a;border-radius:0 8px 8px 0;padding:8px 12px;font-size:12px;color:#555;line-height:1.8;margin-top:10px}
.reason b{color:#b8453a}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.grid2 .mini{background:#faf7f3;border-radius:10px;padding:10px 12px}
.grid2 .lb{font-size:11px;color:#888;margin-bottom:4px}
.table{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px}
.table td{padding:5px 8px;border-bottom:1px solid #f0ebe5}
.table td:first-child{color:#888;width:110px}
/* 岁运卡样式 */
.dy-row{display:flex;align-items:center;gap:8px;padding:7px 4px;border-bottom:1px solid #f0ebe5;font-size:13px}
.dy-row:last-child{border-bottom:none}
.dy-tag{flex:none;min-width:52px;text-align:center;padding:3px 8px;border-radius:8px;font-size:12px;font-weight:700}
.dy-green{background:#27ae6022;color:#27ae60;border:1px solid #27ae6055}
.dy-red{background:#e74c3c22;color:#e74c3c;border:1px solid #e74c3c55}
.dy-gray{background:#7f8c8d22;color:#7f8c8d;border:1px solid #7f8c8d55}
.dy-cur{background:#b8453a;color:#fff;padding:1px 6px;border-radius:6px;font-size:10px}
.dy-info{flex:1;color:#333}
.dy-info .age{color:#888;font-size:11px}
.dy-keys{font-size:11px;color:#888;margin-top:2px}
.dy-keys .gk{color:#27ae60}
.dy-keys .xk{color:#e74c3c}

/* 紫微宫位网格 */
.zw-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:10px}
.zw-cell{background:#faf7f3;border-radius:10px;padding:8px 10px;border:1px solid #f0ebe5}
.zw-head{display:flex;align-items:baseline;gap:6px;margin-bottom:4px}
.zw-gn{font-weight:700;font-size:13px;color:#b8453a}
.zw-gz{font-size:11px;color:#999}
.zw-stars{display:flex;flex-wrap:wrap;gap:3px}
.zw-star{background:#b8453a11;color:#b8453a;border:1px solid #b8453a33;padding:1px 7px;border-radius:8px;font-size:11px}
.zw-empty{color:#bbb;font-size:11px}
.zw-auxs{display:flex;flex-wrap:wrap;gap:3px;margin-top:3px}
.zw-aux{background:#7f8c8d11;color:#7f8c8d;padding:1px 6px;border-radius:6px;font-size:10px}
.zw-shs{margin-top:3px}
.zw-sh{background:#f39c1222;color:#d68910;padding:1px 7px;border-radius:8px;font-size:10px}
</style></head><body>
<h1>⚖️ 八字 + 紫微印证</h1>
<p class="sub">双体系交叉对账 · 算法精准排盘（不靠 LLM 猜）</p>
<div class="card">
  <label>出生日期（年/月/日）</label>
  <div class="row" style="margin-bottom:14px">
    <div><select id="byear"></select></div>
    <div><select id="bmonth"></select></div>
    <div><select id="bday"></select></div>
  </div>
  <div class="row">
    <div><label>时间</label><input type="time" id="btime" value="07:56"></div>
    <div><label>性别</label><select id="gender"><option value="male">男</option><option value="female">女</option></select></div>
  </div>
  <button class="btn" id="goBtn" onclick="run()">⚖️ 排盘印证</button>
</div>
<script>
// 初始化年月日下拉框 (1900-今年)
(function(){
  var ySel=document.getElementById('byear'), mSel=document.getElementById('bmonth'), dSel=document.getElementById('bday');
  var now=new Date(), y;
  for(y=now.getFullYear(); y>=1900; y--){ var o=document.createElement('option'); o.value=y; o.text=y+'年'; if(y===2006)o.selected=true; ySel.appendChild(o); }
  for(var m=1;m<=12;m++){ var o=document.createElement('option'); o.value=m; o.text=m+'月'; if(m===9)o.selected=true; mSel.appendChild(o); }
  function fillDays(){
    var y=+ySel.value, m=+mSel.value, dim=new Date(y,m,0).getDate();
    dSel.innerHTML='';
    for(var d=1;d<=dim;d++){ var o=document.createElement('option'); o.value=d; o.text=d+'日'; if(d===22)o.selected=true; dSel.appendChild(o); }
  }
  ySel.onchange=fillDays; mSel.onchange=fillDays; fillDays();
})();
</script>
<div id="loading"><div class="spinner"></div><p>双引擎排盘中…</p></div>
<div id="result"></div>
<p class="note">🔒 纯本地计算 · 八字+紫微两套独立体系交叉对账</p>
<p class="footer"><a href="/tools">← 返回工具台</a></p>
<script>
function run(){
  var b=document.getElementById('goBtn');b.disabled=true;
  document.getElementById('loading').style.display='block';
  document.getElementById('result').innerHTML='';
  var date=document.getElementById('byear').value+'-'+('00'+document.getElementById('bmonth').value).slice(-2)+'-'+('00'+document.getElementById('bday').value).slice(-2);
  var body={date:date,time:document.getElementById('btime').value,gender:document.getElementById('gender').value};
  // 15秒超时
  var timer=setTimeout(function(){
    document.getElementById('loading').style.display='none';
    document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ 请求超时，请重试</div>';
    b.disabled=false;
  },15000);
  fetch('/bazi-ziwei',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify(body)})
  .then(function(r){ return r.json(); })
  .then(function(d){
    clearTimeout(timer);
    document.getElementById('loading').style.display='none';
    if(d.error){document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ '+d.error+'</div>';b.disabled=false;return}
    var h='<div id="cards"></div><button class="btn" style="margin-top:6px" onclick="aiXuan(this)">🔮 AI 深度分析</button><div id="aiOut"></div>';
    document.getElementById('result').innerHTML=h;
    renderCards(d.report);
    b.disabled=false;
  })
  .catch(function(e){
    clearTimeout(timer);
    document.getElementById('loading').style.display='none';
    document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ 请求失败: '+e.message+'</div>';
    b.disabled=false;
  });
}
function renderCards(raw){
  var c=document.getElementById('cards'); if(!c)return;
  c.innerHTML='';
  var seg={};
  var parts=raw.split(/═══\s*([^═]+?)\s*═══/);
  for(var i=1;i<parts.length;i+=2){seg[parts[i].trim()]=parts[i+1]||'';}
  // ---- 四柱 卡 ----
  if(seg['八字']||seg['八字 ']||seg[' 八字 ']){
    var lines=(seg['八字']||'').split('\\n').map(function(s){return s.trim()}).filter(Boolean);
    var map={}; lines.forEach(function(l){var j=l.indexOf(':');if(j>0)map[l.slice(0,j).trim()]=l.slice(j+1).trim()});
    var dm=map['日主']||'?', ss=map['十神']||'', ny=map['纳音']||'—';
    var html='<div class="sec"><h3>🌳 四柱 <span class="pill pill-gold">'+dm+' 日主</span></h3>';
    html+='<div class="xj-grid">';
    [['year','年'],['month','月'],['day','日'],['hour','时']].forEach(function(p){
      html+='<div class="xj-box"><div class="lb">'+p[1]+'柱</div><div class="val" style="font-size:18px;letter-spacing:2px">'+map[p[0]]+'</div></div>'; });
    html+='</div><table class="table"><tr><td>纳音</td><td>'+ny.replace(/year/g,'年').replace(/month/g,'月').replace(/day/g,'日').replace(/hour/g,'时')+'</td></tr>';
    if(ss) html+='<tr><td>十神</td><td>'+ss.replace(/year/g,'年').replace(/month/g,'月').replace(/day/g,'日').replace(/hour/g,'时')+'</td></tr>';
    var kwKey=Object.keys(seg).filter(function(k){return k.indexOf('空亡')>=0})[0];
    if(kwKey){
      var kwLine=seg[kwKey].split('\\n').map(function(s){return s.trim()}).filter(Boolean)[0]||'';
      var kwTip=seg[kwKey].split('\\n').map(function(s){return s.trim()}).filter(Boolean)[1]||'';
      if(kwLine) html+='<tr><td>空亡</td><td>'+kwLine.replace(/；.*/, '')+'</td></tr>';
    }
    html+='</table></div>';
    c.innerHTML+=html;
  }
  // ---- 格局 卡 ----
  var gName=null,gBasis='',gConf='';
  var gjKey=Object.keys(seg).filter(function(k){return k.indexOf('格局')>=0})[0];
  if(gjKey){ seg[gjKey].split('\\n').forEach(function(l){ l=l.trim();
      var m=l.match(/格局[:：]\s*([^\s(（]+)/); if(m)gName=m[1];
      m=l.match(/置信度(高|中|低)/); if(m)gConf=m[1];
      m=l.match(/依据[:：]\s*(.+)/); if(m)gBasis=m[1]; });
    if(gName){ var html='<div class="sec"><h3>🏛 格局 <span class="pill pill-gold">'+gName+'</span>'+(gConf?'<span class="pill pill-gray">'+gConf+'</span>':'')+'</h3>';
      if(gBasis) html+='<div class="reason">'+gBasis+'</div>';
      c.innerHTML+=html+'</div>'; } }
  // ---- 喜忌神 核心卡 ----
  var mode='?',wangTxt='',yong='',xi='',ji='',reasons=[];
  var xjKey=Object.keys(seg).filter(function(k){return k.indexOf('喜忌')>=0})[0];
  if(xjKey){ seg[xjKey].split('\\n').forEach(function(l){ l=l.trim(); if(!l)return;
      var m=l.match(/身态[:：]\s*([^|]+)/); if(m)mode=m[1].trim();
      m=l.match(/旺衰[:：]\s*([^|(（]+)/); if(m)wangTxt=m[1].trim();
      m=l.match(/用神[:：]\s*(.+)/); if(m)yong=m[1].trim();
      m=l.match(/喜神[:：]\s*(.+)/); if(m)xi=m[1].trim();
      m=l.match(/忌神[:：]\s*(.+)/); if(m)ji=m[1].trim();
      m=l.match(/^[·•]\s*(.+)/); if(m)reasons.push(m[1]); });
    var modeColor=(mode.indexOf('弱')>=0)?'pill-red':((mode.indexOf('强')>=0)?'pill-gold':'pill-gray');
    var modeTxt=mode+(wangTxt&&wangTxt!==mode?(' · '+wangTxt):'');
    var html='<div class="sec" style="border-top:3px solid #b8453a"><h3>⚖️ 喜忌 · 用神 <span class="pill '+modeColor+'">'+modeTxt+'</span></h3>';
    html+='<div class="xj-grid"><div class="xj-box"><div class="lb">用神</div><div class="val" style="color:#d68910;font-size:13px">'+(yong||'—')+'</div></div></div>';
    html+='<div style="margin-top:8px"><div class="lb" style="font-size:11px;color:#888;margin-bottom:4px">喜神 · 宜</div><div class="xi-chips">'+((xi)?xi.split(/[、,，]/).map(function(s){return '<span>'+s+'</span>'}).join(''):'<span>—</span>')+'</div></div>';
    html+='<div style="margin-top:8px"><div class="lb" style="font-size:11px;color:#888;margin-bottom:4px">忌神 · 忌</div><div class="ji-chips">'+((ji)?ji.split(/[、,，]/).map(function(s){return '<span>'+s+'</span>'}).join(''):'<span>—</span>')+'</div></div>';
    if(reasons.length) html+='<div class="reason">'+reasons.map(function(r){return '<div>· '+r+'</div>'}).join('')+'</div>';
    c.innerHTML+=html+'</div>'; }
  // ---- 紫微 卡 ----
  if(seg['紫微']||seg['紫微 ']||seg[' 紫微 ']){
    var zw=seg['紫微']||seg['紫微 ']||seg[' 紫微 '];
    var zwL=zw.trim().split('\\n').map(function(s){return s.trim()}).filter(Boolean);
    var wx='?',mg='?',sg='?'; zwL.forEach(function(l){
      if(l.indexOf('五行局')>=0){var i=l.indexOf(':'); if(i>0)wx=l.slice(i+1).trim();}
      if(/^命宫:/.test(l)&&l.indexOf('身宫')>=0){var i=l.indexOf(':'); if(i>0){var a=l.slice(i+1).split('|'); mg=(a[0]||'?').trim(); sg=((a[1]||'').replace('身宫:','')).trim();}}
      else if(/^命宫:/.test(l)){var i=l.indexOf(':'); if(i>0)mg=l.slice(i+1).trim();}
    });
    // 命宫/身宫: 拆干支 + 主星标签
    function fmtMG(s){
      var pi=s?s.indexOf('('):-1;
      if(pi<=0)return s||'?';
      var gz=s.slice(0,pi).trim(), stars=s.slice(pi+1, s.lastIndexOf(')'));
      var sh=stars?stars.split(',').map(function(x){return '<span class="zw-star">'+x+'</span>'}).join(''):'<span class="zw-empty">空</span>';
      return '<b style="font-size:15px">'+gz+'</b> '+sh;
    }
    var html='<div class="sec"><h3>🔮 紫微斗数 <span class="pill pill-gray">'+wx+'</span></h3>';
    html+='<div class="grid2"><div class="mini"><div class="lb">命宫</div><div style="margin-top:2px">'+fmtMG(mg)+'</div></div><div class="mini"><div class="lb">身宫</div><div style="margin-top:2px">'+fmtMG(sg)+'</div></div></div>';
    // 十二宫网格卡片
    var gs=zwL.filter(function(l){return /^(命宫|兄弟|夫妻|子女|财帛|疾厄|迁移|交友|官禄|田宅|福德|父母)/.test(l)});
    if(gs.length){
      var grid='<div class="zw-grid">';
      gs.forEach(function(l){
        var m=l.match(/^([^\s]+)\s+([^\s]+):\s*主星\[([^\]]*)\]\s*辅星\[([^\]]*)\]\s*四化\[([^\]]*)\]/);
        if(!m)return;
        var gn=m[1], gz=m[2], stars=m[3], aux=m[4], sh=m[5];
        var starHtml=stars?stars.split(',').map(function(x){return '<span class="zw-star">'+x+'</span>'}).join(''):'<span class="zw-empty">空</span>';
        var auxHtml=aux&&aux!=='—'&&aux!=='-'?aux.split(',').map(function(x){return '<span class="zw-aux">'+x+'</span>'}).join(''):'';
        var shHtml=sh&&sh!=='—'&&sh!=='-'?'<span class="zw-sh">'+sh+'</span>':'';
        grid+='<div class="zw-cell"><div class="zw-head"><span class="zw-gn">'+gn+'</span><span class="zw-gz">'+gz+'</span></div><div class="zw-stars">'+starHtml+'</div>'+(auxHtml?'<div class="zw-auxs">'+auxHtml+'</div>':'')+(shHtml?'<div class="zw-shs">'+shHtml+'</div>':'')+'</div>';
      });
      grid+='</div>';
      html+=grid;
    } else {
      html+='<div class="hit" style="margin-top:6px">'+zw.trim()+'</div>';
    }
    html+='</div>';
    c.innerHTML+=html;
  }
// ---- 岁运十神 卡 ----
  var syKey=Object.keys(seg).filter(function(k){return k.indexOf('岁运')>=0})[0];
  if(syKey){
    var syLines=seg[syKey].split('\\n').map(function(s){return s.trim()}).filter(Boolean);
    var rows=syLines.map(function(l){
      var m=l.match(/^([^\s(]+)\s*\(([^-]+)-([^)]+)岁\)\s*(吉运|逆运|平运|偏吉|偏逆)[(\[]([^)\]]+)/);
      if(!m)return null;
      var gz=m[1], a1=m[2], a2=m[3], label=m[4], lv=m[5];
      var cur=l.indexOf('◀当前')>=0;
      var gk='', xk='';
      var gm=l.match(/吉年:([^\s]*)/); if(gm)gk=gm[1];
      var xm=l.match(/凶年:([^\s]*)/); if(xm)xk=xm[1];
      var cls=lv==='上'?'dy-green':(lv==='下'?'dy-red':'dy-gray');
      var lab=label||lv;
      return '<div class="dy-row"><span class="dy-tag '+cls+'">'+lab+'</span><div class="dy-info"><b>'+gz+'</b> <span class="age">'+a1+'-'+a2+'岁</span>'+(cur?' <span class="dy-cur">当前</span>':'')+'</div><div class="dy-keys">'+(gk?'<span class="gk">吉:'+gk+'</span> ':'')+(xk?'<span class="xk">凶:'+xk+'</span>':'')+'</div></div>';
    }).filter(Boolean);
    if(rows.length){
      var html='<div class="sec"><h3>🌊 岁运十神 <span class="pill pill-gray">按喜忌评吉凶</span></h3>'+rows.join('')+'</div>';
      c.innerHTML+=html;
    }
  }
  if(!c.innerHTML){c.innerHTML='<div class="hit"><div class="t">⚖️ 交叉印证结果</div>'+raw+'</div>';}
}
// 轻量 Markdown 渲染 (AI 分析用)
function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}

function aiXuan(btn){
  var out=document.getElementById('aiOut');
  if(!out){out=document.createElement('div');out.id='aiOut';btn.parentNode.appendChild(out)}
  if(out.innerHTML){out.innerHTML='';return}
  out.innerHTML='<div style="padding:12px;color:#888">AI 分析中…（约30秒）</div>';
  var _t=setTimeout(function(){out.innerHTML='<div style="padding:12px;color:#c0392b">⏱ AI 响应超时，请重试</div>';},30000);
  var hit=btn.parentNode.querySelector('.hit');
  var report=hit?hit.innerText:'';
  if(!report) report=btn.parentNode.innerText;
  fetch('/ai-read',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({text:report.slice(0,6000),scene:'xuanxue_general'})})
  .then(function(r){return r.json();})
  .then(function(d){
    clearTimeout(_t);
    out.innerHTML=d.error?'<div style="padding:12px;color:#c0392b">'+d.error+'</div>':'<div style="padding:14px;background:#fff8e6;border-radius:10px;margin-top:10px;line-height:1.7">'+mdRender(d.answer)+'</div>';
  })
  .catch(function(){clearTimeout(_t);out.innerHTML='<div style="padding:12px;color:#c0392b">请求失败</div>';});
}
</script></body></html>"""

    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp



@app.route("/bazi-ziwei", methods=["POST"])
@login_required
@rate_limit
def bazi_ziwei_api():
    """八字+紫微交叉印证 API"""
    data = request.get_json(silent=True) or {}
    date_str = data.get("date", "") or ""
    time_str = data.get("time", "12:00") or "12:00"
    gender = data.get("gender", "male")
    import re as _re
    if not _re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return jsonify({"error": "日期格式应为 YYYY-MM-DD"}), 400
    try:
        import bazi_ziwei_steward as _bzs
        y, m, d = [int(x) for x in date_str.split("-")]
        hh, mm = [int(x) for x in time_str.split(":")]
        bazi, ziwei = _bzs.run_chart(y, m, d, hh, mm, gender)
        report = _bzs.format_report(bazi, ziwei)
        return jsonify({"report": html.escape(report, quote=False)[:9000]})
    except Exception as e:
        return jsonify({"error": f"排盘失败: {str(e)[:200]}"}), 500


@app.route("/steward-new", methods=["GET"])
@login_required
def steward_new_page():
    """新术数：七政四余 + 铁板神数"""
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>七政四余·铁板神数 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:640px;margin:0 auto;padding:16px}
h1{font-size:22px;color:#8e44ad}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
label{font-size:13px;font-weight:600;color:#555;display:block;margin:8px 0 4px}
input,select{width:100%;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px;outline:none;box-sizing:border-box}
input:focus,select:focus{border-color:#8e44ad}
.row{display:flex;gap:10px}
.row>div{flex:1}
.btn{width:100%;padding:13px;background:#8e44ad;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:12px}
.btn:disabled{opacity:.5}
#loading{display:none;text-align:center;padding:16px;color:#8e44ad}
.spinner{display:inline-block;width:22px;height:22px;border:3px solid #eee;border-top-color:#8e44ad;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
#result{margin-top:12px}
.hit{background:#fff;border-radius:10px;padding:12px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05);font-size:13px;white-space:pre-wrap;line-height:1.7}
.hit .t{font-weight:700;font-size:14px;color:#8e44ad;margin-bottom:6px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#8e44ad;text-decoration:none}
.note{font-size:11px;color:#999;text-align:center;margin-top:14px}
</style></head><body>
<h1>🪐 七政四余 · 铁板神数</h1>
<p class="sub">真实天文学排盘（Swiss Ephemeris 验证）· 纯本地计算</p>
<div class="card">
  <label>出生日期</label>
  <input type="date" id="bdate" value="2006-09-22">
  <div class="row">
    <div><label>时间</label><input type="time" id="btime" value="07:56"></div>
    <div><label>性别</label><select id="gender"><option value="male">男</option><option value="female">女</option></select></div>
  </div>
  <label>经度（可选，默认120）</label>
  <input type="text" id="lon" placeholder="如 114.88（张家口）">
  <label>纬度（可选）</label>
  <input type="text" id="lat" placeholder="如 40.82">
  <button class="btn" id="goBtn" onclick="run()">🔮 起盘</button>
</div>
<div id="loading"><div class="spinner"></div><p>排盘中…</p></div>
<div id="result"></div>
<p class="note">🔒 纯本地计算，生日不会上传任何外部服务</p>
<p class="footer"><a href="/tools">← 返回工具台</a></p>
<script>
async function run(){
  var b=document.getElementById('goBtn');b.disabled=true;
  document.getElementById('loading').style.display='block';
  document.getElementById('result').innerHTML='';
  var body={date:document.getElementById('bdate').value,time:document.getElementById('btime').value,gender:document.getElementById('gender').value,lon:document.getElementById('lon').value,lat:document.getElementById('lat').value};
  try{
    var r=await fetch('/steward-new',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify(body)});
    var d=await r.json();
    document.getElementById('loading').style.display='none';
    if(d.error){document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ '+d.error+'</div>';b.disabled=false;return}
    var h='';
    if(d.qizheng)h+='<div class="hit"><div class="t">🪐 七政四余</div>'+mdRender(d.qizheng)+'</div>';
    if(d.tieban)h+='<div class="hit"><div class="t">📜 铁板神数</div>'+mdRender(d.tieban)+'</div>';
    if(!h)h='<div class="hit">无结果</div>';
    h+='<button class="btn" style="background:#8e44ad" onclick="aiXuan(this)">🔮 AI 深度分析</button><div id="aiOut"></div>';
    document.getElementById('result').innerHTML=h;
  }catch(e){
    document.getElementById('loading').style.display='none';
    document.getElementById('result').innerHTML='<div class="hit" style="color:#c0392b">❌ 请求失败: '+e.message+'</div>';
  }
  b.disabled=false;
}
function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}

async function aiXuan(btn){
  var out=document.getElementById('aiOut');
  if(!out){out=document.createElement('div');out.id='aiOut';btn.parentNode.appendChild(out)}
  if(out.innerHTML){out.innerHTML='';return}
  out.innerHTML='<div style="padding:12px;color:#888">AI 分析中…（约30秒）</div>';
  var _t=setTimeout(function(){out.innerHTML='<div style="padding:12px;color:#c0392b">⏱ AI 响应超时，请重试</div>';},30000);
  var report=document.getElementById('result').innerText;
  try{
    var r=await fetch('/ai-read',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'XMLHttpRequest'},body:JSON.stringify({text:report.slice(0,6000),scene:'xuanxue_general'})});
    var d=await r.json();clearTimeout(_t);
    out.innerHTML=d.error?'<div style="padding:12px;color:#c0392b">'+d.error+'</div>':'<div style="padding:14px;background:#fff8e6;border-radius:10px;margin-top:10px;line-height:1.7">'+mdRender(d.answer)+'</div>';
  }catch(e){clearTimeout(_t);out.innerHTML='<div style="padding:12px;color:#c0392b">请求失败</div>';}
}
</script></body></html>"""


@app.route("/steward-new", methods=["POST"])
@login_required
@rate_limit
def steward_new_api():
    """七政四余 + 铁板神数 API"""
    data = request.get_json(silent=True) or {}
    date_str = data.get("date", "") or ""
    time_str = data.get("time", "12:00") or "12:00"
    gender = data.get("gender", "male")
    lon = data.get("lon", "")
    lat = data.get("lat", "")
    # 输入校验
    import re as _re
    if not _re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return jsonify({"error": "日期格式应为 YYYY-MM-DD"}), 400
    if not _re.match(r'^\d{1,2}:\d{2}$', time_str):
        return jsonify({"error": "时间格式应为 HH:MM"}), 400
    y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
    if not (1 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        return jsonify({"error": "日期超出范围"}), 400
    try:
        import new_tools_steward as _nts
        lon_f = float(lon) if lon else None
        lat_f = float(lat) if lat else None
        out = {}
        try:
            q = _nts.cast_qizheng(date_str, time_str, gender, lat=lat_f, lon=lon_f)
            out["qizheng"] = html.escape(_nts._fmt_qizheng(q))[:4000]
        except Exception as e:
            out["qizheng"] = f"<span style='color:#c0392b'>七政四余: {html.escape(str(e))[:150]}</span>"
        try:
            t = _nts.cast_tieban(date_str, time_str, gender, lat=lat_f, lon=lon_f)
            out["tieban"] = html.escape(_nts._fmt_tieban(t))[:4000]
        except Exception as e:
            out["tieban"] = f"<span style='color:#c0392b'>铁板神数: {html.escape(str(e))[:150]}</span>"
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": f"排盘失败: {str(e)[:200]}"}), 500


@app.route("/local-vision", methods=["GET"])
@login_required
def local_vision_page():
    """本地识图：纯本地 CLIP 识别，图片不上传任何外部服务器"""
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>本地识图 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:640px;margin:0 auto;padding:16px}
h1{font-size:22px;color:#27ae60}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
#drop{width:100%;padding:30px 0;text-align:center;border:2px dashed #27ae6066;border-radius:12px;color:#27ae60;cursor:pointer;background:#f4fdf7}
#drop.drag{background:#e0f7e9;border-color:#27ae60}
#imgPreview{max-width:100%;max-height:260px;border-radius:10px;margin-top:10px;display:none}
.btn{width:100%;padding:14px;background:#27ae60;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:10px}
.btn:disabled{opacity:.5}
#result{margin-top:12px}
.kw{display:inline-block;background:#27ae6022;color:#27ae60;padding:4px 10px;border-radius:8px;font-size:12px;margin:4px 4px 0 0}
.score-bar{height:6px;background:#eee;border-radius:4px;margin-top:4px;overflow:hidden}
.score-bar>div{height:100%;background:#27ae60;border-radius:4px}
.hit{background:#fff;border-radius:10px;padding:12px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05)}
.hit .t{font-weight:600;font-size:14px}
.hit .s{font-size:13px;color:#666;margin-top:4px}
.badge{display:inline-block;background:#27ae6011;color:#27ae60;border:1px solid #27ae6044;padding:2px 10px;border-radius:10px;font-size:11px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#27ae60;text-decoration:none}
#loading{display:none;text-align:center;padding:20px;color:#27ae60}
.spinner{display:inline-block;width:24px;height:24px;border:3px solid #eee;border-top-color:#27ae60;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style></head><body>
<h1>🔍 本地识图</h1>
<p class="sub">纯本地 CLIP 识别 · 图片不出服务器 · 免费无限量</p>
<div class="card">
  <div id="drop" onclick="document.getElementById('file').click()">
    <div style="font-size:32px">🖼️</div>
    <div>点击选择图片，或拖拽到这里</div>
    <input type="file" id="file" accept="image/*" style="display:none">
  </div>
  <img id="imgPreview">
  <button class="btn" id="goBtn" disabled onclick="analyze()">🔍 本地识别</button>
</div>
<div id="loading"><div class="spinner"></div><p>本地 CLIP 正在看这张图…</p></div>
<div id="result"></div>
<p class="footer"><a href="/tools">← 返回工具台</a></p>
<script>
var file = document.getElementById('file');
var drop = document.getElementById('drop');
var preview = document.getElementById('imgPreview');
var goBtn = document.getElementById('goBtn');
drop.addEventListener('dragover', function(e){e.preventDefault();drop.classList.add('drag')});
drop.addEventListener('dragleave', function(){drop.classList.remove('drag')});
drop.addEventListener('drop', function(e){e.preventDefault();drop.classList.remove('drag');if(e.dataTransfer.files[0])setFile(e.dataTransfer.files[0])});
file.addEventListener('change', function(){if(file.files[0])setFile(file.files[0])});
function setFile(f){
  if(!f.type.startsWith('image/')){alert('请选择图片文件');return}
  goBtn.disabled = false;
  preview.src = URL.createObjectURL(f);
  preview.style.display = 'block';
  window._imgFile = f;
}
async function analyze(){
  var f = window._imgFile;
  if(!f) return;
  goBtn.disabled = true;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('result').innerHTML = '';
  var fd = new FormData();
  fd.append('image', f);
  try{
    var res = await fetch('/local-vision', {method:'POST', body:fd, headers:{'X-Requested-With':'XMLHttpRequest'}});
    var data = await res.json();
    document.getElementById('loading').style.display = 'none';
    if(data.error){document.getElementById('result').innerHTML = '<div class="hit" style="color:#c0392b">❌ ' + data.error + '</div>';goBtn.disabled=false;return}
    var h = '<div class="hit"><div class="t">🔒 本地识别结果</div><div class="s">耗时 ' + (data.elapsed||0) + 's · 图片已在本地处理，未上传任何外部服务器</div>'; 
    data.results.forEach(function(r){
      var pct = Math.round(r.score * 100);
      h += '<div style="margin-top:10px"><div style="display:flex;justify-content:space-between;font-size:13px"><span>' + r.label + '</span><span style="color:#888">' + pct + '%</span></div><div class="score-bar"><div style="width:' + pct + '%"></div></div></div>';
    });
    h += '</div>';
    document.getElementById('result').innerHTML = h;
  }catch(e){
    document.getElementById('loading').style.display = 'none';
    document.getElementById('result').innerHTML = '<div class="hit" style="color:#c0392b">❌ 请求失败: ' + e.message + '</div>';
  }
  goBtn.disabled = false;
}
</script></body></html>"""


@app.route("/local-vision", methods=["POST"])
@login_required
def local_vision_api():
    """本地识图 API：纯本地 CLIP 识别，返回 top 结果"""
    import base64 as _b64
    img_b64 = ''
    if request.json and request.json.get('image'):
        img_b64 = request.json['image']
    elif 'image' in request.files:
        f = request.files['image']
        img_b64 = _b64.b64encode(f.read()).decode()
    if not img_b64:
        return jsonify({'error': '未收到图片'}), 400

    import time as _t
    t0 = _t.time()
    try:
        import sys as _sys
        _sys.path.insert(0, '/home/honor/.openclaw/workspace/vision-lab')
        import cn_recognizer as _cnr
        _pool = [
            "古籍书页", "药方", "穴位图", "人体经络图", "舌象", "书法作品", "人物肖像",
            "山水画", "草药", "针灸", "医疗笔记", "五行图", "太极图", "人体器官图",
            "骨骼图", "名言", "海报", "书籍封面", "风景照片", "二维码", "建筑", "植物",
            "诊室", "药丸", "茶叶", "佛像", "印章", "星空", "美食", "动物", "画作",
        ]
        tmp_path = '/tmp/local_vision_tmp.jpg'
        with open(tmp_path, 'wb') as fh:
            fh.write(_b64.b64decode(img_b64))
        top = _cnr.recognize(tmp_path, _pool, top_k=5)
        import os as _os2
        try:
            _os2.remove(tmp_path)
        except Exception:
            pass
        elapsed = round(_t.time() - t0, 1)
        results = [{'label': cn, 'score': round(sc, 3)} for cn, _, sc in top]
        return jsonify({'results': results, 'elapsed': elapsed})
    except Exception as e:
        return jsonify({'error': '本地识别失败: ' + str(e)[:150]}), 500


@app.route("/philosophy-image", methods=["GET"])
@login_required
def philosophy_image_page():
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>以图搜哲医 · 莫名心小站</title>
<style>
body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;max-width:640px;margin:0 auto;padding:16px}
h1{font-size:22px;color:#8e44ad}
.sub{color:#888;font-size:13px;margin-bottom:16px}
.card{background:#fff;border-radius:14px;padding:18px;box-shadow:0 2px 10px rgba(0,0,0,.06);margin-bottom:12px}
#drop{width:100%;padding:30px 0;text-align:center;border:2px dashed #8e44ad66;border-radius:12px;color:#8e44ad;cursor:pointer;background:#faf7ff}
#drop.drag{background:#f0e6ff;border-color:#8e44ad}
#imgPreview{max-width:100%;max-height:260px;border-radius:10px;margin-top:10px;display:none}
.btn{width:100%;padding:14px;background:#8e44ad;color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer;margin-top:10px}
.btn:disabled{opacity:.5}
#result{margin-top:12px}
.kw{display:inline-block;background:#8e44ad22;color:#8e44ad;padding:4px 10px;border-radius:8px;font-size:12px;margin:4px 4px 0 0}
.hit{background:#fff;border-radius:10px;padding:12px;margin-top:8px;box-shadow:0 1px 6px rgba(0,0,0,.05)}
.hit .t{font-weight:600;font-size:14px}
.hit .l{font-size:11px;color:#8e44ad}
.hit .s{font-size:13px;color:#666;margin-top:4px}
.footer{text-align:center;margin-top:20px;font-size:12px;color:#999}
a{color:#8e44ad;text-decoration:none}
#loading{display:none;text-align:center;padding:20px;color:#8e44ad}
.spinner{display:inline-block;width:24px;height:24px;border:3px solid #eee;border-top-color:#8e44ad;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
</style></head><body>
<h1>📷 以图搜哲医</h1>
<p class="sub">上传一张图片（医书页、药方、症状笔记、名言、海报…），AI 识别后自动匹配医书/东哲/西哲/道归</p>
<div class="card">
  <div id="drop" onclick="document.getElementById('file').click()">
    <div style="font-size:32px">🖼️</div>
    <div>点击选择图片，或拖拽到这里</div>
    <input type="file" id="file" accept="image/*" style="display:none">
  </div>
  <img id="imgPreview">
  <button class="btn" id="goBtn" disabled onclick="analyze()">🔍 识别并搜索</button>
</div>
<div id="loading"><div class="spinner"></div><p>GLM-4V 正在看这张图…</p></div>
<div id="result"></div>
<p class="footer"><a href="/">← 返回小站</a></p>
<script>
var file = document.getElementById('file');
var drop = document.getElementById('drop');
var preview = document.getElementById('imgPreview');
var goBtn = document.getElementById('goBtn');
drop.addEventListener('dragover', function(e){e.preventDefault();drop.classList.add('drag')});
drop.addEventListener('dragleave', function(){drop.classList.remove('drag')});
drop.addEventListener('drop', function(e){e.preventDefault();drop.classList.remove('drag');if(e.dataTransfer.files[0])setFile(e.dataTransfer.files[0])});
file.addEventListener('change', function(){if(file.files[0])setFile(file.files[0])});
function setFile(f){
  if(!f.type.startsWith('image/')){alert('请选择图片文件');return}
  goBtn.disabled = false;
  preview.src = URL.createObjectURL(f);
  preview.style.display = 'block';
  window._imgFile = f;
}
async function analyze(){
  var f = window._imgFile;
  if(!f) return;
  goBtn.disabled = true;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('result').innerHTML = '';
  var fd = new FormData();
  fd.append('image', f);
  try{
    var res = await fetch('/philosophy-image', {method:'POST', body:fd, headers:{'X-Requested-With':'XMLHttpRequest'}});
    var data = await res.json();
    document.getElementById('loading').style.display = 'none';
    if(data.error){document.getElementById('result').innerHTML = '<div class="hit" style="color:#c0392b">❌ ' + data.error + '</div>';goBtn.disabled=false;return}
    var h = '<div class="hit"><div class="t">🤖 AI 识别</div><div class="s">' + (data.text_content || data.vision_text || '') + '</div><div style="margin-top:6px">' + (data.keywords||[]).map(function(k){return '<span class="kw">' + k + '</span>'}).join('') + '</div></div>';
    if(data.degraded){
      h = '<div class="hit" style="border-left:3px solid #e67e22"><div class="t">⚠️ 本地兑底模式</div><div class="s">GLM-4V 暂时不可用，以下为本地 CLIP 识别的图片类别（未做文字提取）</div><div style="margin-top:6px">' + (data.local_hints||[]).map(function(k){return '<span class="kw" style="background:#e67e2222;color:#e67e22">' + k + '</span>'}).join('') + '</div></div>';
    }
    if(data.local_hints && data.local_hints.length && !data.degraded){
      h += '<div class="hit"><div class="t">🔒 本地识别（纯本地CLIP）</div><div style="margin-top:6px">' + data.local_hints.map(function(k){return '<span class="kw" style="background:#27ae6022;color:#27ae60">' + k + '</span>'}).join('') + '</div></div>';
    }
    h += '<div class="hit"><div class="t">📚 匹配结果 (' + data.results.length + ')</div></div>';
    data.results.forEach(function(r){
      h += '<div class="hit"><div class="t">' + r.title + '</div><div class="l">' + r.label + ' · 命中:' + r.kw + '</div><div class="s">' + r.snippet + '</div></div>';
    });
    document.getElementById('result').innerHTML = h;
  }catch(e){
    document.getElementById('loading').style.display = 'none';
    document.getElementById('result').innerHTML = '<div class="hit" style="color:#c0392b">❌ 请求失败: ' + e.message + '</div>';
  }
  goBtn.disabled = false;
}
</script></body></html>"""


@app.route("/philosophy-image", methods=["POST"])
@login_required
def philosophy_image():
    """以图搜哲医：上传图片 → 本地CLIP预判 + GLM-4V 识别 → 匹配医书/东哲/西哲/道归"""
    import base64, io, json as _json
    from urllib.request import Request, urlopen

    # 1. 接收图片（base64 或 multipart file）
    img_b64 = ''
    if request.json and request.json.get('image'):
        img_b64 = request.json['image']
    elif 'image' in request.files:
        f = request.files['image']
        import base64 as _b64
        img_b64 = _b64.b64encode(f.read()).decode()
    else:
        return jsonify({'error': '未收到图片'}), 400

    if not img_b64:
        return jsonify({'error': '图片为空'}), 400

    # 2. 本地 CLIP 预判（纯本地、免费、无限量）——识别图片类别，作为关键词增强
    local_hints = []
    local_err = ''
    try:
        import sys as _sys
        _sys.path.insert(0, '/home/honor/.openclaw/workspace/vision-lab')
        import cn_recognizer as _cnr
        # 标签池：中医/哲学/通用类别
        _pool = [
            "古籍书页", "药方", "穴位图", "人体经络图", "舌象", "书法作品", "人物肖像",
            "山水画", "草药", "针灸", "医疗笔记", "五行图", "太极图", "人体器官图",
            "骨骼图", "名言", "海报", "书籍封面", "风景照片", "二维码", "建筑", "植物",
            "诊室", "药丸", "茶叶", "佛像", "印章", "星空", "美食", "动物", "画作",
        ]
        img_bytes = base64.b64decode(img_b64)
        tmp_path = '/tmp/philosophy_image_tmp.jpg'
        with open(tmp_path, 'wb') as fh:
            fh.write(img_bytes)
        top = _cnr.recognize(tmp_path, _pool, top_k=3)
        local_hints = [cn for cn, _, sc in top if sc > 0.18]
        import os as _os2
        try:
            _os2.remove(tmp_path)
        except Exception:
            pass
    except Exception as e:
        local_err = str(e)[:120]

    # 2b. 读 Z.ai API Key
    import os as _os
    key = _os.environ.get('ZAI_API_KEY', '')
    if not key:
        try:
            cfg = _json.load(open('/home/honor/.openclaw/openclaw.json', encoding='utf-8'))
            key = cfg.get('models', {}).get('profiles', {}).get('zai:default', {}).get('key', '')
        except Exception:
            pass
    if not key:
        return jsonify({'error': 'Z.ai API Key 未配置'}), 500

    # 3. 调 GLM-4V 识别图片 → 提取哲学关键词
    prompt = ('请仔细分析这张图片。如果图片包含文字（书籍页、名言、书法、海报、药方、症状记录、穴位图等），'
              '请提取其中的文字内容。然后用 3-6 个关键词概括这张图片最可能关联的主题，'
              '可以涵盖哲学（存在主义、虚无、自由、道德、尼采、道家、儒家等）'
              '或中医/医学（证型、脏腑、药名、穴位、病名、方剂、五行等）。'
              '输出格式：先给"文字内容："，再给"关键词："，关键词用顿号分隔。')

    data_url = 'data:image/jpeg;base64,' + img_b64
    vision_text = ''
    vision_err = ''
    # 多模型轮询：flash → thinking → plus
    for model in ['glm-4v-flash', 'glm-4.1v-thinking-flash', 'glm-4v-plus']:
        payload = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': data_url}},
                    {'type': 'text', 'text': prompt}
                ]}
            ]
        }
        try:
            req = Request('https://open.bigmodel.cn/api/paas/v4/chat/completions',
                          data=_json.dumps(payload).encode(),
                          headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
            resp = urlopen(req, timeout=90)
            out = _json.loads(resp.read().decode())
            vision_text = out['choices'][0]['message']['content']
            if vision_text and len(vision_text.strip()) > 2:
                break
        except Exception as e:
            vision_err = str(e)[:120]
            continue
    if not vision_text:
        # GLM 失败时：用本地 CLIP 预判兑底，让功能在无 API 时也能工作
        if local_hints:
            return jsonify({
                'vision_text': '⚠️ GLM-4V 识别失败（' + (vision_err or '未知错误') + '），已用本地 CLIP 类别识别兑底',
                'text_content': '',
                'keywords': local_hints,
                'results': [],
                'local_hints': local_hints,
                'local_err': vision_err if vision_err else None,
                'degraded': True,
            }), 200
        return jsonify({'error': '视觉识别失败: ' + vision_err}), 500

    # 4. 解析关键词（顿号/逗号/空格分隔）
    import re as _re
    kw_match = _re.search(r'关键词[：:]\s*(.+)', vision_text)
    kw_text = kw_match.group(1) if kw_match else vision_text
    keywords = [k.strip() for k in _re.split(r'[、，,;；\s]+', kw_text) if k.strip() and len(k.strip()) < 20][:6]
    text_part = vision_text.split('关键词')[0].replace('文字内容：', '').strip()
    # 兜底：如果关键词没解析出来，从全文提取短词
    if not keywords:
        words = _re.findall(r'[\u4e00-\u9fff]{2,8}', vision_text)
        keywords = list(dict.fromkeys(words))[:6]

    # 4b. 本地 CLIP 预判关键词：仅展示用，不混入搜索关键词（避免类别词污染医书搜索结果）
    #     搜索仍以 GLM 提取的词为主
    if local_hints:
        # 保留原有搜索关键词逻辑，本地词只返回给前端展示
        pass

    # 5. 用关键词搜哲学库（东哲古籍 + 西哲SEP + 道归）
    base = '/home/honor/.openclaw/workspace'
    hits = []
    seen = set()
    search_dirs = [
        (base + '/xin_sources/cleaned/素问', '医书·素问'),
        (base + '/xin_sources/cleaned/灵枢', '医书·灵枢'),
        (base + '/xin_sources/cleaned/伤寒', '医书·伤寒'),
        (base + '/xin_sources/cleaned/金匮', '医书·金匮'),
        (base + '/xin_sources/cleaned/本草', '医书·本草'),
        (base + '/xin_sources/cleaned/综合', '医书·综合'),
        (base + '/xin_sources/tcmoc', '医书·TCM'),
        (base + '/xin_sources/cleaned', '东哲古籍'),
        (base + '/道归', '道归'),
        (base + '/phil_texts', '西哲文本'),
    ]
    for dpath, label in search_dirs:
        if not os.path.isdir(dpath):
            continue
        for root, _, files in os.walk(dpath):
            for f in files:
                if not (f.endswith('.md') or f.endswith('.txt')):
                    continue
                if 'copyright' in f or 'privacy' in f:
                    continue
                fp = os.path.join(root, f)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read(3000)
                    for kw in keywords:
                        if kw in content:
                            title = f.replace('.md', '').replace('.txt', '').replace('_', ' ')[:50]
                            if title in seen:
                                break
                            seen.add(title)
                            idx = content.find(kw)
                            s = max(0, idx - 60)
                            e = min(len(content), idx + len(kw) + 100)
                            snippet = content[s:e].replace('\n', ' ').strip()
                            hits.append({'title': title, 'label': label, 'snippet': snippet[:300], 'kw': kw})
                            break
                except Exception:
                    continue
                if len(hits) >= 10:
                    break
            if len(hits) >= 10:
                break
        if len(hits) >= 10:
            break

    return jsonify({
        'vision_text': vision_text[:500],
        'text_content': text_part[:300],
        'keywords': keywords,
        'results': hits[:10],
        'local_hints': local_hints,
        'local_err': local_err if local_err else None,
    })


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        filename = data.get("filename", "")
        content_b64 = data.get("content", "")
        if not filename or not content_b64:
            return jsonify({"error": "需要 filename 和 content"}), 400
        import base64
        safe_name = os.path.basename(filename)
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, safe_name)
        decoded = base64.b64decode(content_b64)
        with open(filepath, "wb") as f:
            f.write(decoded)
        size_kb = len(decoded) / 1024
        return jsonify({"message": f"{safe_name} 已保存（{size_kb:.1f} KB）", "path": filepath, "size": len(decoded)})
    # GET: 显示上传页面
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
    import glob
    
    page = request.args.get("page", 1, type=int)
    page = max(1, page)
    file_rel = unquote(filepath)
    base = os.path.expanduser("~/.openclaw/workspace/xin_sources/cleaned")
    fp = os.path.join(base, file_rel)
    
    # 根路径 -> 显示古籍列表
    if not file_rel or file_rel == "/":
        html = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>经典古籍 / 莫名心小站</title><style>'
        html += '*{margin:0;padding:0;box-sizing:border-box}'
        html += 'body{font-family:system-ui,sans-serif;background:#16161a;color:#d8d0c0;padding:16px;max-width:640px;margin:0 auto}'
        html += 'h1{font-size:20px;margin-bottom:4px}'
        html += '.sub{color:#8a7a6a;font-size:.8rem;margin-bottom:16px}'
        html += '.card{background:#1e1e24;border-radius:12px;padding:14px;margin-bottom:10px;text-decoration:none;color:#d8d0c0;display:block}'
        html += '.card:hover{background:#2a2a30}'
        html += '.card-title{font-weight:600;font-size:14px}'
        html += '.card-desc{color:#6a5a4a;font-size:.75rem;margin-top:2px}'
        html += '.footer{text-align:center;margin-top:20px;font-size:.8rem;color:#6a5a4a}'
        html += 'a{color:#b0a898;text-decoration:none}'
        html += '</style></head><body>'
        html += '<h1>📜 经典古籍</h1><p class="sub">素问50卷 / 灵枢 / 神农本草经</p>'
        dirs = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])
        for d in dirs:
            md_files = [f for f in glob.glob(os.path.join(base, d, "*.md")) if "_______copyright" not in f and "_______privacy" not in f]
            if md_files:
                html += f'<a class="card" href="/classic-view/{d}"><div class="card-title">{d}</div><div class="card-desc">{len(md_files)} 篇</div></a>'
        html += '<div class="footer"><a href="/tools">← 工具台</a></div></body></html>'
        return html
    
    if not (os.path.isfile(fp) and fp.startswith(base)):
        # 路径是目录 -> 列出文件
        if os.path.isdir(fp):
            html = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>' + file_rel + ' / 经典古籍</title><style>'
            html += '*{margin:0;padding:0;box-sizing:border-box}'
            html += 'body{font-family:system-ui,sans-serif;background:#16161a;color:#d8d0c0;padding:16px;max-width:640px;margin:0 auto}'
            html += 'h1{font-size:18px;margin-bottom:12px}'
            html += '.card{background:#1e1e24;border-radius:10px;padding:12px;margin-bottom:8px;text-decoration:none;color:#d8d0c0;display:block}'
            html += '.card-title{font-size:14px;font-weight:500}'
            html += '.footer{text-align:center;margin-top:20px;font-size:.8rem;color:#6a5a4a}'
            html += 'a{color:#b0a898;text-decoration:none}'
            html += '</style></head><body>'
            html += f'<h1>📜 {file_rel}</h1>'
            files = sorted([f for f in os.listdir(fp) if f.endswith('.md') and '_______copyright' not in f and '_______priv' not in f])
            for f in files:
                html += f'<a class="card" href="/classic-view/{file_rel}/{f}"><div class="card-title">{f.replace(".md","")}</div></a>'
            html += '<div class="footer"><a href="/classic-view/">← 上级</a></div></body></html>'
            return html
        page404 = '<!DOCTYPE html><html><meta charset="UTF-8"><title>未找到</title>'
        page404 += '<style>body{background:#16161a;color:#d8d0c0;padding:40px;font-family:sans-serif;text-align:center;}'
        page404 += 'h1{font-size:60px;margin:0;color:#3a2a1a;}p{color:#6a5a4a;}a{color:#d8d0c0;}</style>'
        page404 += '<body><h1>📖</h1><p>文档未找到，可能已被移动或名称发生了变化。</p>'
        page404 += '<p><a href="/">← 返回小站</a></p></body></html>'
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
    from urllib.parse import unquote
    import fnmatch
    file_rel = unquote(filepath)
    clean_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xin_sources", "cleaned")
    if not file_rel or file_rel == "/":
        # 按目录分组收集文件
        groups = {}
        for root, dirs, files in os.walk(clean_dir):
            for f in files:
                if not f.endswith(".md") or f.endswith(".trad.md"):
                    continue
                if "_______copyright" in f or "_______privacy" in f:
                    continue
                cat = os.path.basename(root)
                if cat not in groups:
                    groups[cat] = []
                groups[cat].append((os.path.join(root, f), f.replace(".md", "")))
        for cat in groups:
            groups[cat].sort(key=lambda x: x[1])
        
        # 名称清洗
        def clean_name(n):
            n = n.replace("笈_", "").replace("_", " ").strip()
            return n[:40]
        
        html = '<!DOCTYPE html><html lang=zh-CN><head><meta charset=UTF-8><meta name=viewport content="width=device-width,initial-scale=1.0">'
        html += '<title>求知虫 / 莫名心小站</title><style>'
        html += '*{margin:0;padding:0;box-sizing:border-box}'
        html += 'body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#16161a;color:#d8d0c0;padding:12px;max-width:640px;margin:0 auto}'
        html += 'h1{font-size:22px;margin-bottom:2px}'
        html += '.sub{font-size:13px;color:#6a5a4a;margin-bottom:16px}'
        html += '.section{margin-bottom:20px}'
        html += '.stitle{font-size:14px;font-weight:600;color:#8a7a6a;padding-left:4px;border-left:3px solid #b8453a;margin-bottom:8px}'
        html += '.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}'
        html += '@media(max-width:480px){.grid{grid-template-columns:1fr}}'
        html += '.card{background:#1e1e24;border-radius:14px;padding:14px;text-decoration:none;color:#d8d0c0;display:block;transition:.2s;box-shadow:0 1px 4px rgba(0,0,0,.2)}'
        html += '.card:active{background:#2a2a30;transform:scale(0.97)}'
        html += '.card-title{font-size:14px;font-weight:500;line-height:1.4;word-break:break-all}'
        html += '.footer{text-align:center;padding:20px 0 10px;font-size:13px;color:#6a5a4a}'
        html += 'a{color:#b0a898;text-decoration:none}'
        html += '</style></head><body>'
        html += '<h1>🕳️ 求知虫</h1><p class="sub">古籍数据库 · 点击查看详情</p>'
        
        for cat in sorted(groups.keys()):
            items = groups[cat]
            html += '<div class="section"><div class="stitle">' + cat + '</div><div class="grid">'
            for fp, nm in items:
                rel = os.path.relpath(fp, clean_dir)
                cname = clean_name(nm)
                html += '<a class="card" href="/crawled-view/' + rel + '"><div class="card-title">' + cname + '</div></a>'
            html += '</div></div>'
        
        html += '<div class="footer"><a href="/tools">← 工具台</a></div></body></html>'
        return html
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    found = None
    for root, dirs, files in os.walk(clean_dir):
        for f in files:
            if f.endswith(".md"):
                fp = os.path.join(root, f)
                if file_rel in fp or os.path.basename(fp) == file_rel:
                    found = fp
                    break
        if found:
            break
    if not found or not os.path.isfile(found):
        return "<h1>未找到</h1>", 404
    with open(found, encoding="utf-8") as vf:
        raw = vf.read()
    body = raw.split("---", 2)[-1] if raw.startswith("---") else raw
    ppc = 5000
    total = max(1, (len(body) + ppc - 1) // ppc)
    if page > total:
        page = total
    s = (page - 1) * ppc
    chunk = body[s:s+ppc]
    bn = os.path.basename(file_rel)
    import html as hmod
    return "<!DOCTYPE html><html lang=zh-CN><head><meta charset=UTF-8><title>" + bn + "</title>" +         "<style>body{background:#16161a;color:#d8d0c0;padding:20px;font-family:sans-serif;line-height:2;white-space:pre-wrap;max-width:720px;margin:0 auto}" +         "a{color:#b0a898;text-decoration:none}.nav{padding:10px 0;border-bottom:1px solid #333}" +         ".pager{text-align:center;padding:14px}</style><body><div class=nav><a href=/crawled-view/>返回</a></div>" +         "<div>" + hmod.escape(chunk) + "</div><div class=pager>第" + str(page) + "/" + str(total) + "页</div></body></html>" 
@app.route("/daogui")
@login_required
def daogui():
    """道归文库"""
    from daogui_lib import generate_lib_page
    cat = request.args.get('cat')
    doc = request.args.get('doc')
    return generate_lib_page(category=cat, doc_id=doc)


@app.route("/forge-destiny", methods=["GET", "POST"])
@login_required
def forge_destiny():
    """锻因缘（v2：相变 + 真排盘合盘）"""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        action = data.get("action")
        # 动态导入 forge_engine（可热重启，不依赖启动时路径）
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "锻因缘"))
        try:
            import forge_engine as _fe
        except Exception as _fe_err:
            return {"success": False, "error": f"锻因缘引擎加载失败: {_fe_err}"}
        try:
            if action == "create":
                return _fe.handle_create(data.get("user1") or {})
            if action == "join":
                return _fe.handle_join(data.get("code", ""), data.get("user2") or {})
            return {"success": False, "error": "未知 action"}
        except Exception as _e2:
            return {"success": False, "error": str(_e2)}

    # GET：静态页面 或 结果接口
    code = request.args.get("code")
    if code:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "锻因缘"))
        import forge_engine as _fe
        user = request.args.get("user", "1")
        return _fe.handle_result(code, int(user))
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "锻因缘", "index.html")
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>锻因缘页面未找到</h1>", 404


@app.route("/daogui3")
@login_required
def daogui3():
    """道归3.0 · 未来展望"""
    BASE = os.path.dirname(os.path.abspath(__file__))
    pages = [
        ("道归体系全貌v30整合版", "🏛️ 体系全貌"),
        ("道归体系全貌v30优化版", "📜 体系全貌·简版"),
        ("新兴学科预测优化版", "🔮 新兴学科"),
        ("灵魂稳定学第九支柱优化版", "💎 灵魂稳定学"),
    ]
    html = '''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>道归3.0 · 未来展望</title>
<style>
body{font-family:"PingFang SC","Hiragino Sans GB","Noto Sans SC",system-ui,sans-serif;max-width:800px;margin:0 auto;padding:24px 16px;line-height:1.75;background:#f7f2ec;color:#3d3a36}
h1{color:#a0522d;border-bottom:2px solid #c68a5d;padding-bottom:10px}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.nav a{display:inline-block;margin:0;padding:6px 16px;background:#fffdf9;border:1px solid #e8dfd3;color:#a0522d;text-decoration:none;border-radius:999px;font-size:13px;transition:background .15s}
.nav a:hover{background:#a0522d;color:#fff}
.content{background:#fffdf9;border:1px solid #e8dfd3;padding:26px 28px;border-radius:14px;box-shadow:0 2px 10px rgba(160,82,45,.08);margin-top:20px;white-space:pre-wrap;line-height:1.9}
hr{border:none;border-top:1px solid #ddd;margin:24px 0}
blockquote{border-left:3px solid #8b0000;margin:16px 0;padding:8px 16px;background:#fff5f5;border-radius:4px}
</style></head><body>
'''
    html += '<h1>🌙 道归3.0 · 未来展望</h1>\n<div class="nav">'
    for slug, label in pages:
        html += f'<a href="?p={slug}">{label}</a> '
    html += '<a href="/" style="background:#8b0000">← 返回小站</a></div>\n'
    
    p = request.args.get('p', '道归体系全貌v30整合版')
    found = False
    for slug, label in pages:
        if p == slug:
            filepath = os.path.join(BASE, '道归3.0', f'{slug}.md')
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Remove YAML-like header
                import re
                content = re.sub(r'^---.*?---', '', content, flags=re.DOTALL)
                content = content.strip()
                content_json = json.dumps(content, ensure_ascii=False)
                html += f'<h2>{label}</h2>\n<div class="content" id="dgContent"></div>'
                html += f'<script>{_MD_RENDER_JS}\ndocument.getElementById("dgContent").innerHTML = mdRender({content_json});</script>'
                found = True
                break
    if not found:
        html += '<p>页面未找到</p>'
    
    html += '</body></html>'
    return html


# ── 启动 ──

def _error_page(code, msg):
    return f'<!DOCTYPE html><html lang=zh-CN><head><meta charset=UTF-8><title>{code}</title><style>body{{font-family:system-ui,sans-serif;background:#16161a;color:#ece8dc;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center;padding:20px}}a{{color:#a0522d}}</style></head><body><h1>{code}</h1><p>{msg}</p><a href=/>返回首页</a></body></html>', code

@app.errorhandler(500)
def handle_500(e):
    return _error_page(500, '服务器内部错误')

@app.errorhandler(404)
def handle_404(e):
    return _error_page(404, '页面未找到')



@app.route("/arsenal")
@login_required
def arsenal():
    """弹药弹夹 · 哲学吞噬计划 + 新旧哲学对撞合集（2026-08-05）"""
    import os
    import urllib.parse as _up
    BASE = os.path.dirname(os.path.abspath(__file__))
    DG = os.path.join(BASE, '道归')
    import html as hmod

    # 扫描两类文档
    docs = []  # (类型, 标题, 相对路径)
    if os.path.isdir(DG):
        for f in sorted(os.listdir(DG)):
            if f.startswith('哲学吞噬_') and f.endswith('.md'):
                title = f.replace('哲学吞噬_', '吞噬·').replace('_2026-07-26.md','').replace('_2026-07-27.md','').replace('.md','')
                docs.append(('吞噬','# '+title, f))
            elif f.startswith('哲学对撞_') and f.endswith('.md'):
                title = f.replace('哲学对撞_','对撞·').replace('_2026-08-05.md','').replace('.md','')
                docs.append(('对撞','# '+title, f))
        for f in os.listdir(DG):
            if f.startswith('哲学交叉分析_') and f.endswith('.md'):
                docs.append(('交叉', '# 哲学交叉分析', f))

    html = _site_head("弹药弹夹 · 莫名心小站")
    html += _site_nav(links=[('/philosophy','📖 哲思文库')])
    html += '<h1>🎯 弹药弹夹</h1>'
    html += '<p class="sub">哲学吞噬计划 · 新旧哲学对撞 · 心哥体系火力库</p>'

    html += '<div style="margin-bottom:8px">💥 <b>对撞文档</b>（用你的六大理论撞哲学家）：</div>'
    for typ, title, f in docs:
        if typ == '对撞':
            html += f'<a class="card" href="/arsenal/doc?f={_up.quote(f)}"><div class="name" style="color:#a0522d;font-weight:600">{title.replace("# ","")}</div><div class="desc" style="color:#8a827a;font-size:.8rem">扫描 {f}</div></a>'

    html += '<div style="margin:16px 0 8px">🦞 <b>吞噬计划</b>（用相变语言消化哲学家，第1层）：</div>'
    for typ, title, f in docs:
        if typ == '吞噬':
            html += f'<a class="card" href="/arsenal/doc?f={_up.quote(f)}"><div class="name" style="color:#3d3a36;font-weight:600">{title.replace("# ","")}</div><div class="desc" style="color:#8a827a;font-size:.8rem">{f}</div></a>'

    html += '<div style="margin:16px 0 8px">🔍 <b>交叉分析</b>：</div>'
    for typ, title, f in docs:
        if typ == '交叉':
            html += f'<a class="card" href="/arsenal/doc?f={_up.quote(f)}"><div class="name" style="color:#3d3a36;font-weight:600">哲学交叉分析</div><div class="desc" style="color:#8a827a;font-size:.8rem">{f}</div></a>'

    html += '<div style="margin:20px 0 8px">🧠 <b>SEP 哲思文库</b>（新弹药 · 持续入库中）：</div>'
    html += '<a class="card" href="/philosophy"><div class="name" style="color:#a0522d;font-weight:600">📖 进入哲思文库</div><div class="desc" style="color:#8a827a;font-size:.8rem">斯坦福哲学百科全量词条</div></a>'

    html += _site_foot()
    return html


@app.route("/arsenal/doc")
@login_required
def arsenal_doc():
    """渲染弹药弹夹里的单篇文档"""
    import os
    BASE = os.path.dirname(os.path.abspath(__file__))
    DG = os.path.join(BASE, '道归')
    import html as hmod
    f = request.args.get('f','')
    fp = os.path.join(DG, os.path.basename(f))
    if not os.path.isfile(fp):
        return '<h1>未找到</h1>', 404
    raw = open(fp, encoding='utf-8').read()
    body = raw.split('---',2)[-1] if raw.startswith('---') else raw
    body = body[:60000]
    body_json = json.dumps(body, ensure_ascii=False)
    title = os.path.basename(f).replace('.md','')
    html = _site_head(f"{title} · 弹药弹夹")
    html += _site_nav(links=[('/arsenal','🎯 弹药弹夹'),('/philosophy','📖 哲思文库')])
    html += f'<h1>{hmod.escape(title)}</h1>'
    html += '<div class="content" id="b"></div>'
    # 用 mdRender 渲染 markdown
    js = _MD_RENDER_JS
    html += f'<script>{js}\ndocument.getElementById("b").innerHTML = mdRender({body_json});</script>'
    html += _site_foot()
    return html


@app.route("/poems")
@login_required
def poems():
    """即兴创作 · 心哥的诗"""
    import os
    BASE = os.path.dirname(os.path.abspath(__file__))
    POEM_DIR = os.path.join(BASE, '心哥的诗')

    def esc(t):
        return str(t)[:300000]

    poems_list = []
    # 短篇小说（叙事体，区别于诗）
    STORY_FILES = {'计程车伴小时维德电台_论一颗心的死去.txt', '石竹.md', '灰烬认得归路.md', '灰城.md',
                  '七处改血.md', '太空情书.md', '捕获协议.md', '朝问道.md', '此处.md', '笼中乡.md', '终产者的终产.md'}
    if os.path.isdir(POEM_DIR):
        for f in sorted(os.listdir(POEM_DIR)):
            if f.endswith('.txt') or f.endswith('.md'):
                if f in ('读后记.md',):
                    continue  # 阅读笔记不是作品
                title = f.rsplit('.', 1)[0]
                try:
                    with open(os.path.join(POEM_DIR, f), encoding='utf-8') as fh:
                        content = fh.read()
                    cat = '小说' if f in STORY_FILES else '诗'
                    poems_list.append({'title': title, 'file': f, 'content': content, 'cat': cat})
                except Exception:
                    pass

    poems_list.sort(key=lambda p: len(p['content']))
    p = request.args.get('p', '')
    html = """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>即兴创作 / 莫名心小站</title>
<style>
body{font-family:"KaiTi","STKaiti","PingFang SC",serif;background:#f7f2ec;color:#3d3a36;max-width:800px;margin:0 auto;padding:24px 16px;line-height:2}
h1{color:#a0522d;border-bottom:2px solid #c68a5d;padding-bottom:10px;font-family:"PingFang SC",system-ui,sans-serif;letter-spacing:.5px}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.nav a{display:inline-block;margin:0;padding:6px 16px;background:#fffdf9;border:1px solid #e8dfd3;color:#a0522d;text-decoration:none;border-radius:999px;font-family:"PingFang SC",system-ui,sans-serif;font-size:13px;transition:background .15s}
.nav a:hover{background:#a0522d;color:#fff}
.poem-card{background:#fffdf9;border:1px solid #e8dfd3;padding:16px 22px;border-radius:14px;box-shadow:0 2px 10px rgba(160,82,45,.08);margin-top:12px;cursor:pointer;display:block;text-decoration:none;color:inherit;transition:transform .15s,box-shadow .15s}
.poem-card:hover{border-left:4px solid #a0522d;transform:translateY(-1px);box-shadow:0 4px 16px rgba(160,82,45,.14)}
.poem-title{font-size:18px;font-weight:bold;color:#a0522d}
.poem-preview{color:#8a827a;font-size:14px;margin-top:6px;white-space:pre-wrap}
.cat-tag{display:inline-block;font-size:11px;padding:1px 10px;border-radius:8px;margin-left:8px;font-family:"PingFang SC",system-ui,sans-serif}
.cat-poem{background:#a0522d11;color:#a0522d;border:1px solid #c68a5d44}
.cat-story{background:#8b000011;color:#8b0000;border:1px solid #8b000022}
.poem-full{background:#fffdf9;border:1px solid #e8dfd3;padding:34px 38px;border-radius:14px;box-shadow:0 2px 12px rgba(160,82,45,.08);margin-top:20px;font-size:17px;white-space:pre-wrap;line-height:2.1}
.poem-full .pt{font-size:22px;font-weight:bold;color:#a0522d;margin-bottom:18px;text-align:center;letter-spacing:2px}
.back{display:inline-block;margin-top:16px;color:#a0522d;text-decoration:none;border-bottom:1px solid #c68a5d44}
</style></head><body>
<h1>🔥 即兴创作</h1>
<div class="nav"><a href="/">← 返回小站</a></div>
"""
    if p:
        poem = next((x for x in poems_list if x['file'] == p), None)
        if poem:
            import re as _re
            content = _re.sub(r'^---.*?---', '', poem['content'], flags=_re.DOTALL).strip()
            content_json = json.dumps(content, ensure_ascii=False)
            html += f'<div class="poem-full"><div class="pt">《{esc(poem["title"])}》</div><div id="pfBody"></div></div>'
            html += f'<script>{_MD_RENDER_JS}\ndocument.getElementById("pfBody").innerHTML = mdRender({content_json});</script>'
            html += '<a class="back" href="/poems">← 返回诗列表</a>'
        else:
            html += '<p>未找到这首诗</p><a class="back" href="/poems">← 返回</a>'
    else:
        html += f'<p style="color:#888;font-family:system-ui,sans-serif">共 {len(poems_list)} 篇 · 心哥的即兴（诗 · 短篇小说）</p>'
        # 分类标签
        html += '''<div style="margin:12px 0;font-family:system-ui,sans-serif">
<a href="?cat=诗" style="display:inline-block;margin:4px;padding:8px 16px;background:#1a1a2e;color:#faf8f5;text-decoration:none;border-radius:6px;font-size:14px">📜 诗</a>
<a href="?cat=小说" style="display:inline-block;margin:4px;padding:8px 16px;background:#8b0000;color:#faf8f5;text-decoration:none;border-radius:6px;font-size:14px">📖 短篇小说</a>
<a href="/poems" style="display:inline-block;margin:4px;padding:8px 16px;background:#555;color:#fff;text-decoration:none;border-radius:6px;font-size:14px">全部</a>
</div>'''
        # 按 cat 筛选
        cat = request.args.get('cat', '')
        if cat:
            poems_list = [x for x in poems_list if x['cat'] == cat]
        # 分类标题
        if cat == '诗':
            html += '<p style="color:#888;font-family:system-ui,sans-serif">📜 诗歌 ' + str(len(poems_list)) + ' 首</p>'
        elif cat == '小说':
            html += '<p style="color:#888;font-family:system-ui,sans-serif">📖 短篇小说 ' + str(len(poems_list)) + ' 篇</p>'
        for poem in poems_list:
            preview = poem['content'].replace('\n', ' ')[:80]
            tag_cls = 'cat-story' if poem.get('cat') == '小说' else 'cat-poem'
            tag_txt = '📖 小说' if poem.get('cat') == '小说' else '📜 诗'
            html += f'<a class="poem-card" href="/poems?p={poem["file"]}"><div class="poem-title">《{esc(poem["title"])}》<span class="cat-tag {tag_cls}">{tag_txt}</span></div><div class="poem-preview">{esc(preview)}...</div></a>'
    html += '</body></html>'
    return html


@app.route("/extensions")
@login_required
def extensions():
    """扩展管理 —— 灵感来自 Firefox about:addons"""
    html = '''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>扩展管理 · 莫名心小站</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;max-width:900px;margin:0 auto;padding:20px;background:#f5f5f5;color:#222}
h1{font-size:1.5rem;margin-bottom:4px}
.sub{color:#666;font-size:.85rem;margin-bottom:20px}
.nav-bar{display:flex;gap:4px;margin-bottom:24px;border-bottom:2px solid #ddd;padding-bottom:0}
.nav-bar a{padding:8px 16px;text-decoration:none;color:#555;font-size:.9rem;border-radius:6px 6px 0 0}
.nav-bar a.active{background:#fff;color:#222;font-weight:600;border:1px solid #ddd;border-bottom-color:#fff;margin-bottom:-2px}
.ext-list{display:flex;flex-direction:column;gap:12px}
.ext-card{background:#fff;border-radius:10px;padding:16px;display:flex;align-items:center;gap:14px;box-shadow:0 1px 4px rgba(0,0,0,.08);transition:.2s}
.ext-card:hover{box-shadow:0 2px 8px rgba(0,0,0,.12)}
.ext-icon{width:40px;height:40px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.3rem;flex-shrink:0}
.ext-info{flex:1}
.ext-name{font-weight:600;font-size:.95rem}
.ext-desc{color:#666;font-size:.82rem;margin-top:2px}
.ext-toggle{position:relative;width:44px;height:24px;flex-shrink:0}
.ext-toggle input{opacity:0;width:0;height:0}
.ext-toggle .slider{position:absolute;cursor:pointer;top:0;left:0;right:0;bottom:0;background:#ccc;border-radius:12px;transition:.3s}
.ext-toggle .slider::before{content:"";position:absolute;height:18px;width:18px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.3s}
.ext-toggle input:checked+.slider{background:#a0522d}
.ext-toggle input:checked+.slider::before{transform:translateX(20px)}
.ext-more{color:#999;cursor:pointer;padding:4px;font-size:1.1rem}
.search-bar{display:flex;gap:8px;margin-bottom:20px}
.search-bar input{flex:1;padding:10px 14px;border:1px solid #ddd;border-radius:8px;font-size:.9rem;outline:none}
.search-bar input:focus{border-color:#a0522d}
.empty-state{text-align:center;padding:60px 20px;color:#999}
</style></head><body>
<h1>🧩 扩展管理</h1>
<p class="sub">管理小站的功能扩展 — 灵感来自 Firefox about:addons · 莫名心小站</p>

<div class="nav-bar">
<a href="#" class="active">已启用</a>
<a href="#">推荐</a>
<a href="#">主题</a>
</div>

<div class="search-bar">
<input type="text" placeholder="搜索扩展…" oninput="filterExts(this.value)">
</div>

<div class="ext-list" id="extList"></div>

<p style="text-align:center;margin-top:24px;color:#999;font-size:.8rem">
<a href="/" style="color:#a0522d;text-decoration:none">← 返回首页</a>
</p>

<script>
const EXTENSIONS = [
    {
        icon: "🎤", name: "文本语音朗读", desc: "朗读SEP文库、哲学报告与道归文档。支持40+语言，一键播放。",
        on: true, color: "#e74c3c"
    },
    {
        icon: "🎨", name: "Stylus 主题管理", desc: "小站外观自定义。切换白天/夜间模式、字号、字体。",
        on: true, color: "#27ae60"
    },
    {
        icon: "📷", name: "以图搜哲学", desc: "上传图片 → AI识别 → 匹配东哲/西哲/道归。GLM-4V 驱动。",
        on: true, color: "#8e44ad"
    },
    {
        icon: "🔍", name: "哲思增强搜索", desc: "SEP 102条全文检索 + 模糊匹配 + AI 推荐。",
        on: true, color: "#2980b9"
    },
    {
        icon: "📜", name: "古籍对照", desc: "素问50卷、灵枢、神农本草经对照阅读。",
        on: true, color: "#d35400"
    },
    {
        icon: "🧮", name: "五运六气计算器", desc: "客主加临六步推算、食疗评价、时位分析。",
        on: true, color: "#16a085"
    },
    {
        icon: "🤖", name: "AI 问答", desc: "DeepSeek V4 Flash 驱动，上下文1M tokens。",
        on: true, color: "#2c3e50"
    },
    {
        icon: "📊", name: "八字排盘", desc: "八套术数·纯本地运行·免费",
        on: true, color: "#c0392b"
    },
    {
        icon: "🔮", name: "小六壬起卦", desc: "道传体系，数字/时间/宫位三种起卦法。",
        on: true, color: "#7f8c8d"
    },
    {
        icon: "🗂️", name: "道归3.0文库", desc: "完整理论体系 + 宇宙学假说 + 哲学吞噬报告。",
        on: true, color: "#8b0000"
    },
];

function renderExts(list) {
    const el = document.getElementById('extList');
    el.innerHTML = list.map(e => `
        <div class="ext-card">
            <div class="ext-icon" style="background:${e.color}22;color:${e.color}">${e.icon}</div>
            <div class="ext-info">
                <div class="ext-name">${e.name}</div>
                <div class="ext-desc">${e.desc}</div>
            </div>
            <label class="ext-toggle">
                <input type="checkbox" ${e.on ? 'checked' : ''}>
                <span class="slider"></span>
            </label>
            <span class="ext-more">⋯</span>
        </div>
    `).join('');
}

function filterExts(q) {
    const f = EXTENSIONS.filter(e => e.name.includes(q) || e.desc.includes(q));
    renderExts(f);
}

renderExts(EXTENSIONS);
</script>
</body></html>'''
    return html

@app.route("/api/tts", methods=["POST"])
@login_required
def api_tts():
    """语音朗读接口"""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    lang = data.get("lang", "zh-CN")
    result = _tts_endpoint(text, lang)
    return jsonify(result)


_STEWARD_HTML = """<!DOCTYPE html><html lang=\"zh-CN\"><head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no\">\n<title>玄学管家 / 莫名心小站</title>\n<style>\n*{margin:0;padding:0;box-sizing:border-box}\nbody{font-family:system-ui,-apple-system,\"PingFang SC\",sans-serif;background:#f7f2ec;color:#3d3a36;padding:16px;max-width:640px;margin:0 auto;min-height:100vh}\nh1{font-size:22px;margin-bottom:2px}\n.sub{color:#888;font-size:13px;margin-bottom:16px}\n.card{background:#fffdf9;border-radius:16px;padding:20px;box-shadow:0 2px 12px rgba(0,0,0,.06);margin-bottom:12px}\nlabel{font-size:14px;font-weight:500;display:block;margin-bottom:6px;color:#555}\ninput,select{width:100%;padding:14px;border:2px solid #e0d8d2;border-radius:12px;font-size:16px;outline:none;background:#fffdf9;box-sizing:border-box}\ninput:focus,select:focus{border-color:#b8453a}\ninput{margin-bottom:14px}\nselect{margin-bottom:14px;appearance:none}\n.btn{width:100%;padding:14px;background:#b8453a;color:white;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer}\n.btn:active{opacity:.8}\n.tag{display:inline-block;padding:4px 10px;border-radius:8px;font-size:12px;margin-right:4px;margin-bottom:4px}\n.tag-bazi{background:#e74c3c22;color:#e74c3c}\n.tag-ziwei{background:#8e44ad22;color:#8e44ad}\n.tag-qimen{background:#2980b922;color:#2980b9}\n.tag-meihua{background:#27ae6022;color:#27ae60}\n.tag-liuren{background:#d3540022;color:#d35400}\n.footer{text-align:center;margin-top:20px;font-size:13px;color:#888}\na{color:#a0522d;text-decoration:none}\n#loading{display:none;text-align:center;padding:20px}\n.spinner{display:inline-block;width:24px;height:24px;border:3px solid #eee;border-top-color:#b8453a;border-radius:50%;animation:spin .8s linear infinite}\n@keyframes spin{to{transform:rotate(360deg)}}\n</style></head><body>\n<h1>🧙 玄学管家</h1>\n<p class=\"sub\">术数总入口 · 命理用生辰 / 测事用当下</p>\n<div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">\n<a href="/steward" class="tag" style="background:#b8453a;color:#fff;font-size:13px;padding:6px 14px">🧙 管家·八套术数</a>\n<a href="/jyotish" class="tag" style="background:#d35400;color:#fff;font-size:13px;padding:6px 14px">🌏 星盘术数</a>\n<a href="/liuyao" class="tag" style="background:#27ae60;color:#fff;font-size:13px;padding:6px 14px">⚡ 六爻纳甲</a>\n<a href="/qimen" class="tag" style="background:#2980b9;color:#fff;font-size:13px;padding:6px 14px">🗺️ 奇门遁甲</a>\n<a href="/bazi-ziwei" class="tag" style="background:#8e44ad;color:#fff;font-size:13px;padding:6px 14px">⚖️ 八字紫微印证</a>\n<a href="/steward-new" class="tag" style="background:#e67e22;color:#fff;font-size:13px;padding:6px 14px">🪐 七政铁板</a>\n</div>\n<div style="background:#e8f5e9;border:1px solid #4caf50;border-radius:10px;padding:10px 14px;margin:10px 0 14px;font-size:13px;color:#2e7d32">🔒 <b>纯本地运行</b>：排盘全部在本服务器计算，你的生日完全不会上传到任何外部服务器。数据不出这台机器。</div>
<div style="background:#eaf4fb;border:1px solid #2980b944;border-radius:10px;padding:10px 14px;margin:10px 0 14px;font-size:12px;color:#1a5276">⏰ <b>时家类（奇门/六壬/梅花/金口诀/小六壬）自动用当下时辰起盘</b>，生辰字段可留空；八字/紫微才需填生辰。</div></p>\n<div class=\"card\">\n<form method=\"post\" action=\"/steward\" onsubmit=\"if(!packDates())return false;document.getElementById('loading').style.display='block';document.getElementById('submitBtn').disabled=true\">\n<label>生达</label>\n<div style="display:flex;gap:8px"><div style="flex:1"><label>\u65e5\u671f</label><div style="display:flex;gap:6px"><select name="bdate_year" style="flex:1.4;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px"></select><select name="bdate_month" style="flex:1;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px"></select><select name="bdate_day" style="flex:1;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px"></select><input type="hidden" name="bdate" value="2026-07-28"></div></div><div style="flex:none;width:120px"><label>\u65f6\u95f4</label><input type=\"time\" name=\"btime\" value=\"12:00\" step=\"60\"></div></div>\n<div style="margin-top:10px"><label>经度（真太阳时校正，默认120，可留空）</label><input type="text" name="longitude" placeholder="如 114.7（张家口坝上）" value=""></div>\n<div style="margin-top:6px"><label>纬度（七政四余/印占定宫位必需，默认30，可留空）</label><input type="text" name="latitude" placeholder="如 40.8（张家口）" value=""></div>\n<div style="margin-bottom:14px">
<label>模式</label>
<div style="display:flex;gap:10px;margin-top:4px">
<label style="display:flex;align-items:center;gap:4px;font-size:14px;font-weight:400;cursor:pointer">
<input type="radio" name="dual" value="single" checked onclick="var p=document.getElementById('person2');if(p)p.style.display='none'"> 单人
</label>
<label style="display:flex;align-items:center;gap:4px;font-size:14px;font-weight:400;cursor:pointer">
<input type="radio" name="dual" value="double" onclick="var p=document.getElementById('person2');if(p)p.style.display='block'"> 双人
</label>
</div>
</div>
<div id="person2" style="display:none;margin-bottom:14px;padding:14px;background:#f8f4f0;border-radius:12px">
<div style="font-size:13px;font-weight:600;color:#b8453a;margin-bottom:10px">🧑‍🧑 第二人</div>
<div style="display:flex;gap:8px;margin-bottom:10px">
<div style="flex:1">
<label style="font-size:12px">日期</label>
<div style="display:flex;gap:6px"><select name="bdate2_year" style="flex:1.4;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px"></select><select name="bdate2_month" style="flex:1;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px"></select><select name="bdate2_day" style="flex:1;padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:15px"></select><input type="hidden" name="bdate2" value="2026-07-28"></div>
</div>
<div style="flex:none;width:100px">
<label style="font-size:12px">时间</label>
<input type="time" name="btime2" value="12:00">
</div>
</div>
<div>
<label style="font-size:12px">性别</label>
<div style="display:flex;gap:10px;margin-top:4px">
<label style="display:flex;align-items:center;gap:4px;font-size:13px;font-weight:400;cursor:pointer"><input type="radio" name="sex2" value="1" checked> 男</label>
<label style="display:flex;align-items:center;gap:4px;font-size:13px;font-weight:400;cursor:pointer"><input type="radio" name="sex2" value="0"> 女</label>
</div>
</div>
<div style="margin-top:8px">
<label style="font-size:12px">关系类型</label>
<select name="relation" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:8px;font-size:13px">
<option value="marriage">夫妻 / 合婚</option>
<option value="love">男女情侣</option>
<option value="friend">朋友 / 合伙</option>
<option value="brother">兄弟</option>
<option value="sister">姐妹</option>
<option value="brosis">兄妹 / 姐弟</option>
<option value="colleague">同事 / 上下级</option>
</select>
</div>
</div>

<div style="margin-bottom:14px">
<label>性别</label>
<div style="display:flex;gap:10px;margin-top:4px">
<label style="display:flex;align-items:center;gap:4px;font-size:14px;font-weight:400;cursor:pointer">
<input type="radio" name="sex" value="1" checked> 男
</label>
<label style="display:flex;align-items:center;gap:4px;font-size:14px;font-weight:400;cursor:pointer">
<input type="radio" name="sex" value="0"> 女
</label>
</div>
</div>
<label>术数</label>\n<label>术数（可多选，勾几个算几个）</label>\n<div style="margin-bottom:8px;font-size:13px;color:#8e6b4a;font-weight:600;border-bottom:1px solid #eee;padding-bottom:4px">🌱 先天生辰（命盘，填生辰）</div>\n<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px">\n<label class="chk"><input type="checkbox" name="mode" value="bazi" checked> 八字</label>\n<label class="chk"><input type="checkbox" name="mode" value="ziwei"> 紫微</label>\n<label class="chk"><input type="checkbox" name="mode" value="qizheng"> 七政四余</label>\n<label class="chk"><input type="checkbox" name="mode" value="tieban"> 铁板神数</label>\n<label class="chk"><input type="checkbox" name="mode" value="wuyunliuqi"> 五运六气</label>\n</div>\n<div style="margin-bottom:8px;font-size:13px;color:#8e6b4a;font-weight:600;border-bottom:1px solid #eee;padding-bottom:4px">⏰ 当下测算（起卦，用当下时辰）</div>\n<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px">\n<label class="chk"><input type="checkbox" name="mode" value="qimen"> 奇门</label>\n<label class="chk"><input type="checkbox" name="mode" value="liuren"> 大六壬</label>\n<label class="chk"><input type="checkbox" name="mode" value="meihua"> 梅花</label>\n<label class="chk"><input type="checkbox" name="mode" value="jinkoujue"> 金口诀</label>\n<label class="chk"><input type="checkbox" name="mode" value="xiaoliuren"> 小六壬</label>\n</div>\n<div id="purposeBox" style="display:none;background:#fff8f0;border:1px solid #e8c9a0;border-radius:10px;padding:12px;margin-bottom:12px">\n<label style="font-size:13px;font-weight:600;color:#8e6b4a">🎯 求测目的（当下测算必填）</label>\n<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px">\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'学业考试')">📚 学业考试</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'事业工作')">💼 事业工作</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'姻缘感情')">❤️ 姻缘感情</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'人际关系')">🤝 人际关系</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'财运')">💰 财运</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'健康')">🏥 健康</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'出行')">🚶 出行</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'寻物')">🔍 寻物</button>\n<button type="button" class="purpose-btn" onclick="pickPurpose(this,'官司')">⚖️ 官司</button>\n</div>\n<input type="text" id="purposeCustom" placeholder="或自己输入想测的事…" style="width:100%;padding:10px;border:2px solid #e8c9a0;border-radius:10px;font-size:14px;box-sizing:border-box">\n<input type="hidden" id="purpose" name="purpose" value="">\n<div style="font-size:11px;color:#b08a5a;margin-top:4px">点上面的标签快速选，或自己输入；最终以输入框内容为准</div>\n</div>\n<input type="hidden" id="modeStr" name="modeStr">\n<label style=\"display:flex;align-items:center;gap:8px;margin:10px 0 4px;font-size:13px;color:#555;font-weight:500\">\n<input type=\"checkbox\" name=\"full_stars\" value=\"1\" style=\"width:17px;height:17px;margin:0;accent-color:#b8453a\"> 紫微全星图（含红鸾/咸池/寡宿等杂曜）\n</label>\n<label style=\"display:block;margin:8px 0 4px;font-size:13px;color:#555;font-weight:500\">日界流派（晚子时23-24点出生才影响）</label>\n<select name=\"sect\" style=\"padding:10px;border:2px solid #e0d8d2;border-radius:10px;font-size:14px;margin-bottom:14px\">\n<option value=\"1\">子正换日（默认：晚子时算当日）</option>\n<option value=\"2\">子初换日（iztro 流派：晚子时按次日排盘）</option>\n</select>\n<button type=\"submit\" class=\"btn\" id=\"submitBtn\">起盘</button>\n</form>\n</div>\n<div id=\"loading\" class=\"card\" style=\"display:none;text-align:center\"><div class=\"spinner\"></div><p style=\"margin-top:8px;color:#888\">计算中...</p></div>\n<p style=\"text-align:center;margin-top:12px\">\n<span class=\"tag tag-bazi\">八字</span>\n<span class=\"tag tag-ziwei\">紫微</span>\n<span class=\"tag tag-qimen\">奇门</span>\n<span class=\"tag tag-liuren\">六壬</span>\n<span class=\"tag tag-meihua\">梅花</span>\n<span class=\"tag tag-jinkoujue\" style=\"background:#e67e2222;color:#e67e22\">金口诀</span>\n<span class=\"tag tag-wuyun\" style=\"background:#1abc9c22;color:#1abc9c\">五运六气</span>\n</p>\n<div class=\"footer\"><a href=\"/tools\">← 工具台</a></div>\n
<div style="background:#fff8e1;border:1px solid #ffd54f;border-radius:10px;padding:10px 14px;margin-top:16px;font-size:12px;color:#8d6e63;line-height:1.7">
⚠️ <b>免责声明</b>：本站所有术数排盘结果（八字/紫微/奇门/六壬/梅花/金口诀/五运六气/小六壬）仅供<b>娱乐与传统文化研究</b>，不构成任何医疗、投资、法律、婚恋或重大决策建议。排盘为纯本地计算，数据不出本机；AI 解读由大模型生成，可能存在误差。请理性看待，一切以现实为准，风险自担。
</div></body><script>
(function(){
  function initDate(y,m,d,defY,defM,defD){
    var now=new Date(),i;
    for(i=now.getFullYear();i>=1900;i--){var o=document.createElement('option');o.value=i;o.text=i+'年';if(i===defY)o.selected=true;y.appendChild(o);}
    for(i=1;i<=12;i++){var o=document.createElement('option');o.value=i;o.text=i+'月';if(i===defM)o.selected=true;m.appendChild(o);}
    function fillDays(){
      var yy=+y.value,mm=+m.value,dim=new Date(yy,mm,0).getDate();
      d.innerHTML='';
      for(var dd=1;dd<=dim;dd++){var o=document.createElement('option');o.value=dd;o.text=dd+'日';if(dd===defD)o.selected=true;d.appendChild(o);}
    }
    y.onchange=fillDays;m.onchange=fillDays;fillDays();
  }
  var SHI_JIA=['qimen','liuren','meihua','jinkoujue','xiaoliuren'];
  function refreshPurposeBox(){
    var ms=document.getElementsByName('mode'), anyShi=false;
    for(var i=0;i<ms.length;i++){ if(ms[i].checked && SHI_JIA.indexOf(ms[i].value)>=0){ anyShi=true; break; } }
    var box=document.getElementById('purposeBox');
    if(box){ box.style.display = anyShi ? 'block' : 'none'; }
    return anyShi;
  }
  window.pickPurpose=function(btn,val){
    var inp=document.getElementById('purposeCustom');
    var hidden=document.getElementById('purpose');
    if(inp){ inp.value=val; }
    if(hidden){ hidden.value=val; }
    var btns=document.querySelectorAll('.purpose-btn');
    for(var i=0;i<btns.length;i++){ btns[i].style.outline = (btns[i]===btn) ? '2px solid #d35400' : 'none'; }
  };
  (function(){
    var ms=document.getElementsByName('mode');
    for(var i=0;i<ms.length;i++){ ms[i].addEventListener('change',refreshPurposeBox); }
  })();
  function packDates(){
    function pack(ys,ms,ds,hid){
      hid.value=ys.value+'-'+('00'+ms.value).slice(-2)+'-'+('00'+ds.value).slice(-2);
    }
    pack(document.getElementsByName('bdate_year')[0],document.getElementsByName('bdate_month')[0],document.getElementsByName('bdate_day')[0],document.getElementsByName('bdate')[0]);
    if(document.getElementsByName('bdate2')[0]){
      pack(document.getElementsByName('bdate2_year')[0],document.getElementsByName('bdate2_month')[0],document.getElementsByName('bdate2_day')[0],document.getElementsByName('bdate2')[0]);
    }
    var ms=document.getElementsByName('mode'), sel=[];
    for(var mi=0;mi<ms.length;mi++){ if(ms[mi].checked) sel.push(ms[mi].value); }
    if(!sel.length) sel.push('bazi');
    var msEl=document.getElementById('modeStr');
    if(msEl) msEl.value=sel.join(',');
    var pc=document.getElementById('purposeCustom');
    var ph=document.getElementById('purpose');
    if(ph && pc && pc.value){ ph.value=pc.value; }
    return true;
  }
  window.packDates=packDates;
  initDate(document.getElementsByName('bdate_year')[0],document.getElementsByName('bdate_month')[0],document.getElementsByName('bdate_day')[0],2006,9,22);
  if(document.getElementsByName('bdate2_year')[0]){initDate(document.getElementsByName('bdate2_year')[0],document.getElementsByName('bdate2_month')[0],document.getElementsByName('bdate2_day')[0],2006,9,22);}
})();
</script>
</html>"""



# AI 分析 Markdown 渲染 (steward 等页面共用)
_MD_RENDER_JS = """
function mdEsc(t){
  return (t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function mdInline(t){
  t = mdEsc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  t = t.replace(/`([^`]+)`/g, '<code style="background:#f0ebe5;padding:1px 5px;border-radius:4px;font-size:12px">$1</code>');
  return t;
}
function mdRender(text){
  var olIdx = 0;
  if(!text) return '';
  text = text.replace(/^#{1,6}\s+(#{1,6}\s+)/gm, '$1');
  var lines = text.split('\\n');
  var html = '', inList = false, i, m, l;
  function closeList(){ if(inList){ html += (inList==='ol'?'</ol>':'</ul>'); inList = false; } }
  for(i=0;i<lines.length;i++){
    l = lines[i];
    // ==== Markdown 表格 ====
    if(/^\s*\|/.test(l)){
      var tbl = [l.trim()];
      while(i+1 < lines.length && /^\s*\|/.test(lines[i+1])){
        if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(lines[i+1].trim())){
          i++; continue;  // 跳过重复分隔行（ASCII 框线转来的）
        }
        tbl.push(lines[i+1].trim()); i++;
      }
      if(tbl.length >= 2 && /^\|[\s:\-|]+\|$/.test(tbl[1])){
        closeList();
        var hdr = tbl[0].split('|').slice(1,-1);
        html += '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:13px">';
        html += '<thead><tr>' + hdr.map(function(c){return '<th style="background:#b8453a11;color:#b8453a;padding:6px 8px;border:1px solid #e0d8d2;text-align:left">'+mdInline(c.trim())+'</th>'}).join('') + '</tr></thead><tbody>';
        for(var r=2;r<tbl.length;r++){
          var cells = tbl[r].split('|').slice(1,-1);
          html += '<tr>' + cells.map(function(c){return '<td style="padding:6px 8px;border:1px solid #e0d8d2;vertical-align:top">'+mdInline(c.trim())+'</td>'}).join('') + '</tr>';
        }
        html += '</tbody></table>';
        continue;
      }
    }
    // ==== 引用块 ====
    if(/^\s*&gt;/.test(l) || /^\s*>\s?/.test(l)){
      var q = [l.replace(/^\s*>\s?/, '')];
      while(i+1 < lines.length && (/^\s*>\s?/.test(lines[i+1]) || /^\s*&gt;/.test(lines[i+1]))){
        i++; q.push(lines[i].replace(/^\s*>\s?/, '').replace(/^\s*&gt;/, ''));
      }
      closeList();
      html += '<blockquote style="margin:8px 0;padding:8px 12px;background:#faf5f0;border-left:3px solid #b8453a;color:#555;border-radius:0 8px 8px 0">' + q.map(function(x){return mdInline(x.trim())}).join('<br>') + '</blockquote>';
      continue;
    }
    // ==== 分隔线 ====
    if(/^\s*([-*_])\s*\\1\s*\\1+\s*$/.test(l)){ closeList(); html += '<hr style="border:none;border-top:1px dashed #e0d8d2;margin:16px 0">'; continue; }
    // ==== 标题 ====
    if(m = l.match(/^###\s+(.*)/)){ closeList(); html += '<h4 style="margin:14px 0 6px;color:#b8453a;font-size:14px">'+mdInline(m[1])+'</h4>'; }
    else if(m = l.match(/^##\s+(.*)/)){ closeList(); html += '<h3 style="margin:16px 0 6px;color:#b8453a;font-size:15px">'+mdInline(m[1])+'</h3>'; }
    else if(m = l.match(/^#\s+(.*)/)){ closeList(); html += '<h2 style="margin:18px 0 8px;color:#b8453a;font-size:17px;border-bottom:2px solid #b8453a33;padding-bottom:4px">'+mdInline(m[1])+'</h2>'; }
    // ==== 列表 ====
    else if(m = l.match(/^[-*]\s+(.*)/)){ if(!inList){ html += '<ul style="margin:6px 0;padding-left:20px">'; inList = 'ul'; } html += '<li style="margin:3px 0">'+mdInline(m[1])+'</li>'; }
    else if(m = l.match(/^\d+\.\s+(.*)/)){ if(!inList){ html += '<ol style="margin:6px 0;padding-left:20px;list-style:none">'; inList = 'ol'; } olIdx++; html += '<li style="margin:3px 0"><b style="color:#b8453a">'+olIdx+'.</b> '+mdInline(m[1])+'</li>'; }
    // ==== 空行/段落 ====
    else if(l.trim()===''){ closeList(); }
    else { closeList(); html += '<p style="margin:6px 0;line-height:1.8">'+mdInline(l)+'</p>'; }
  }
  closeList();
  return html;
}
"""

@app.route("/steward", methods=["GET", "POST"])
@login_required
@rate_limit
def steward():
    """赛博玄学管家"""
    import subprocess as _sp
    steward_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                  "skills", "metaphysics-steward", "scripts", "steward.py")
    
    def esc(t):
        return html.escape(str(t)[:5000])
    
    import markdown as _mk
    _md_style = '<style>table{border-collapse:collapse;margin:8px 0;width:100%;font-size:13px}th,td{border:1px solid #e0d8d2;padding:6px 8px;text-align:left}th{background:#b8453a11;color:#b8453a}blockquote{margin:8px 0;padding:8px 12px;background:#faf5f0;border-left:3px solid #b8453a;color:#555;border-radius:0 8px 8px 0}hr{border:none;border-top:1px dashed #e0d8d2;margin:16px 0}</style>'
    def _md_to_html(t):
        """服务端 markdown → HTML（不依赖浏览器 JS）"""
        t = str(t or '')
        # 框线图（紫微宫格等）必须等宽字体显示，否则错位
        if '┌' in t or '└' in t or '│' in t:
            return '<pre style="font-family:monospace;font-size:13px;line-height:1.5;background:#faf8f5;padding:12px;border-radius:8px;overflow-x:auto;white-space:pre">' + esc(t[:8000]) + '</pre>'
        try:
            return _mk.markdown(t, extensions=['tables', 'fenced_code'])
        except Exception:
            return '<pre>' + esc(t[:5000]) + '</pre>'
    
    def _fmt_wuyun(wu):
        """五运六气 dict → 可读文本（不再显示原始 JSON）"""
        try:
            _w = wu or {}
            _lines = []
            _lines.append(f"日期: {_w.get('日期','')}  干支: {_w.get('干支','')} ({_w.get('天干','')}年 {_w.get('地支','')})")
            _sd = _w.get('岁运', {})
            if _sd:
                _lines.append(f"岁运: {_sd.get('天干','')}年 → {_sd.get('岁运','')}运（{_sd.get('太过不及','')}）")
                _lines.append(f"  脏腑: {'、'.join(str(x) for x in _sd.get('脏腑',[]))} | 季节: {_sd.get('季节','')} | 气候: {_sd.get('气候','')} | 五味: {_sd.get('五味','')}")
                _lines.append(f"  描述: {_sd.get('描述','')}")
            if _w.get('司天'):
                _lines.append(f"司天: {_w.get('司天','')} | 在泉: {_w.get('在泉','')}")
            _cur = _w.get('当前', {})
            if _cur:
                _lines.append(f"当前: {_cur.get('时段','')}（主气 {_cur.get('主气','')} / 客气 {_cur.get('客气','')}，{_cur.get('区间','')}）")
            _steps = _w.get('客气六步', [])
            if _steps:
                _lines.append('')
                _lines.append('客气六步:')
                _lines.append('| 时段 | 客气 | 主气 | 日期 | 标记 |')
                _lines.append('|---|---|---|---|---|')
                for _s in _steps:
                    _mk2 = _s.get('标记','') or ''
                    _lines.append(f"| {_s.get('时段','')} | {_s.get('客气','')} | {_s.get('主气','')} | {_s.get('日期','')} | {_mk2} |")
            return '\n'.join(_lines)[:6000]
        except Exception:
            return json.dumps(wu, ensure_ascii=False, indent=2)[:6000]
    
    import re as _mdre
    def _clean_md(raw):
        """排盘原始文本 → 可渲染 markdown：ASCII表格补分隔行、====转---、去英文头"""
        raw = str(raw or "")
        # 英文头清理
        raw = raw.replace("(Metaphysics Steward)", "").replace("Metaphysics Steward", "")
        raw = raw.replace("steward.py:", "")
        # 长分隔线 → markdown hr
        raw = _mdre.sub(r'^[=]{3,}\s*$', '---', raw, flags=_mdre.M)
        raw = _mdre.sub(r'^[-]{3,}\s*$', '---', raw, flags=_mdre.M)
        # 全角制表符表格 → markdown 表格
        # 1) 全角竖线 → 半角
        raw = raw.replace('│', '|')
        # 2) 顶/底边框行（┌──┐ └──┘）→ 删除
        raw = _mdre.sub(r'^[┌└╔╚][─━┬┴╦╩]*[┐┘╗╝]\s*$', '', raw, flags=_mdre.M)
        # 3) 中间框线行（├──┼──┤）→ markdown 分隔行
        def _box_to_sep(m):
            line = m.group(0)
            n = line.count('┼') + 1
            if n <= 1:
                n = max(1, line.count('─') // 6 + 1)
            return '|' + '---|' * n
        raw = _mdre.sub(r'^[├╠][─━┼╬]*[┤╣]\s*$', _box_to_sep, raw, flags=_mdre.M)
        # 4) 残留的全角框线字符清理
        raw = raw.replace('─', '').replace('━', '').replace('┼', '|').replace('┬', '|').replace('┴', '|')
        # 键值行加粗（"键: 值" → "**键**: 值"），两空格缩进项 → markdown 列表项
        _kv_lines = []
        for _ln in raw.split('\n'):
            _s = _ln.rstrip()
            if _s.startswith('|') or not _s.strip():
                # 表格行前若上一行非空且非表格行，补空行让 markdown 识别表格
                if _s.startswith('|') and _kv_lines and _kv_lines[-1].strip() and not _kv_lines[-1].strip().startswith('|'):
                    _kv_lines.append('')
                _kv_lines.append(_ln)
                continue
            _stripped = _s.strip()
            if _s.startswith('  '):
                # 缩进项（如星曜列表）→ markdown 列表项；列表前需空行
                if _kv_lines and _kv_lines[-1].strip() and not _kv_lines[-1].startswith('- '):
                    _kv_lines.append('')
                _kv_lines.append('- ' + _stripped)
            else:
                _m = _mdre.match(r'^([\u4e00-\u9fa5A-Za-z0-9（()）\s]+?):\s?(.*)$', _stripped)
                if _m and len(_m.group(1)) <= 20 and '://' not in _stripped:
                    _key = _m.group(1).strip()
                    _val = _m.group(2).strip()
                    _kv_lines.append(f"**{_key}**: {_val}")
                else:
                    _kv_lines.append(_ln)
        raw = '\n'.join(_kv_lines)
        # 空格对齐表格（如八字四柱）→ markdown 表格
        # 规则：数据行列数必须完全一致(N)；表头行允许 N-1 列且缩进更大 → 前面补空
        # 列数参差（如紫微宫格盘）→ 不转换，保持原样
        lines0 = raw.split('\n')
        out0 = []
        i0 = 0
        while i0 < len(lines0):
            l0 = lines0[i0]
            c0 = [c for c in _mdre.split(r'\s{2,}', l0.strip()) if c]
            if len(c0) >= 2 and not l0.strip().startswith('|'):
                # 收集块
                blk = [(l0, c0)]
                j0 = i0 + 1
                while j0 < len(lines0):
                    cj = [c for c in _mdre.split(r'\s{2,}', lines0[j0].strip()) if c]
                    if len(cj) >= 2 and not lines0[j0].strip().startswith('|') and not _mdre.match(r'^[-=]{3,}$', lines0[j0].strip()):
                        blk.append((lines0[j0], cj)); j0 += 1
                    else:
                        break
                if len(blk) >= 2:
                    # 数据行（blk[1:]）列数必须全部一致，且至少 4 行（防紫微宫格误转）
                    _data_lens = set(len(x[1]) for x in blk[1:])
                    if len(_data_lens) == 1 and len(blk[1:]) >= 4:
                        _N = _data_lens.pop()
                        _hdr_c = len(blk[0][1])
                        _rows = []
                        if _hdr_c == _N:
                            _rows.append(blk[0][1])
                        elif _hdr_c == _N - 1:
                            # 表头缩进更大（右对齐）→ 前面补空列
                            _rows.append([''] + blk[0][1])
                        else:
                            _rows = None
                        if _rows is not None:
                            for _, cj in blk[1:]:
                                _rows.append(cj)
                            out0.append('|' + '|'.join(_rows[0]) + '|')
                            out0.append('|' + '---|' * _N)
                            for _r in _rows[1:]:
                                out0.append('|' + '|'.join(_r) + '|')
                            i0 = j0
                            continue
            out0.append(l0); i0 += 1
        raw = '\n'.join(out0)
        # 连续 | 行块：第二行非分隔行则补分隔行
        lines = raw.split('\n')
        out = []
        i = 0
        while i < len(lines):
            l = lines[i]
            if l.strip().startswith('|'):
                block = [l.strip()]
                j = i + 1
                while j < len(lines) and lines[j].strip().startswith('|'):
                    block.append(lines[j].strip()); j += 1
                if len(block) >= 2 and not _mdre.match(r'^\|[\s:\-|]+\|$', block[1]):
                    ncols = max(1, block[0].count('|') - 1)
                    sep = '|' + '---|' * ncols
                    out.extend(block[:1] + [sep] + block[1:])
                else:
                    out.extend(block)
                i = j
            else:
                out.append(l); i += 1
        return '\n'.join(out)
    
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form or {}
        birthdate = data.get("birthdate", "") or (data.get("bdate","") + " " + (data.get("btime","") or "12:00")).strip()
        # mode 读取：优先 modeStr（多选逗号分隔），否则表单 getlist 合并
        if data.get("modeStr"):
            mode = str(data["modeStr"]).strip().rstrip(",")
        elif isinstance(data, dict) and "mode" in request.form and hasattr(request.form, "getlist"):
            _ml = request.form.getlist("mode")
            mode = ",".join(_ml)
        else:
            mode = str(data.get("mode", "bazi") or "bazi")
        # 时家术数（奇门/六壬/梅花/金口诀/小六壬）以当下时辰起盘，生辰只用于命理类
        SHI_JIA = {"qimen", "liuren", "meihua", "jinkoujue", "xiaoliuren"}
        _mode_list = [m.strip() for m in str(mode).split(",") if m.strip()]
        if _mode_list and all(m in SHI_JIA for m in _mode_list):
            birthdate = ""  # 全为时家 → 不传 → 脚本自动用当前时间
        elif any(m in SHI_JIA for m in _mode_list) and _mode_list:
            # 混合（时家+命理）：时家部分需用当下时间，命理用生辰 → 交给主引擎时按需处理
            pass
        is_form = request.content_type and "form" in request.content_type
        
        try:
            dual = data.get("dual", "single")
            relation = data.get("relation", "love")
            full_stars = data.get("full_stars") in ("1", "true", "True", True, 1)
            extra = ["--full"] if full_stars else []
            sect = data.get("sect", "1")
            if sect in ("1", "2"):
                extra += ["--sect", sect]
            
            if mode == "wuyunliuqi":
                try:
                    from 五运六气 import 推算 as _wuyun
                    wu = _wuyun(birthdate[:10] if len(birthdate) >= 10 else None)
                    raw = _fmt_wuyun(wu)
                except Exception as _we:
                    raw = f"五运六气计算错误: {_we}"
            elif mode == "xiaoliuren":
                try:
                    from datetime import datetime as _xlnow
                    _n = _xlnow.now()
                    xl_args = [str(_n.month), str(_n.day), str((_n.hour + 1) // 2)]
                    xl_r = _sp.run(["xiaoliuren", "--time"] + xl_args, capture_output=True, text=True, timeout=10)
                    raw = (xl_r.stdout or "")[:5000] or (xl_r.stderr or "")[:2000] or "暂无输出"
                except Exception as _xe:
                    raw = f"小六壬调用错误: {_xe}"
            elif mode in ("qizheng", "tieban"):
                # 七政四余 / 铁板神数（命理类，用生辰）——并入玄学管家
                try:
                    import new_tools_steward as _nts
                    _dt2 = (data.get("bdate","") + " " + (data.get("btime","") or "12:00")).strip()
                    _d2, _t2 = _dt2.split() if " " in _dt2 else (_dt2, "12:00")
                    _lon2 = float(data.get("longitude", "120") or 120)
                    _lat2 = float(data.get("latitude", "30") or 30)
                    if mode == "qizheng":
                        _res = _nts.cast_qizheng(_d2, _t2, data.get("sex", "1"), lon=_lon2, lat=_lat2)
                        raw = "【七政四余】\n" + _nts._fmt_qizheng(_res)
                    else:
                        _res = _nts.cast_tieban(_d2, _t2, data.get("sex", "1"), lon=_lon2, lat=_lat2)
                        raw = "【铁板神数】\n" + _nts._fmt_tieban(_res)
                except Exception as _ne:
                    raw = f"七政/铁板调用错误: {_ne}"
            elif dual == "double":
                # 双人模式：算两个人的盘
                bd2 = (data.get("bdate2","") + " " + (data.get("btime2","") or "12:00")).strip()
                sex2 = data.get("sex2", "1")
                raw_p1 = ""
                raw_p2 = ""
                try:
                    r1 = _sp.run(["python3", steward_script, "--birthdate", birthdate, "--sex", data.get("sex","1"), "--birthplace", data.get("longitude","120"), "--mode", mode] + extra, capture_output=True, text=True, timeout=20)
                    raw_p1 = (r1.stdout or "")[:5000]
                except:
                    raw_p1 = f"第一人排盘错误"
                try:
                    r2 = _sp.run(["python3", steward_script, "--birthdate", bd2, "--sex", sex2, "--birthplace", data.get("longitude","120"), "--mode", mode] + extra, capture_output=True, text=True, timeout=20)
                    raw_p2 = (r2.stdout or "")[:5000]
                except:
                    raw_p2 = f"第二人排盘错误"
                raw = f"第一人：\n{raw_p1}\n\n第二人：\n{raw_p2}"
            else:
                # 多选支持：mode 可为逗号分隔（如 "bazi,ziwei"），逐个跑并累加
                _modes = [m.strip() for m in mode.split(",") if m.strip()]
                if not _modes:
                    _modes = ["bazi"]
                _raw_parts = []
                for _m in _modes:
                    if _m == "xiaoliuren":
                        # 小六壬不走 steward.py（不支持该 mode），单独调用
                        try:
                            from datetime import datetime as _xlnow
                            _n = _xlnow.now()
                            _xl_args = [str(_n.month), str(_n.day), str((_n.hour + 1) // 2)]
                            _xl_r = _sp.run(["xiaoliuren", "--time"] + _xl_args, capture_output=True, text=True, timeout=10)
                            _out = (_xl_r.stdout or "").strip()[:6000] or (_xl_r.stderr or "")[:2000] or "暂无输出"
                        except Exception as _xe:
                            _out = f"小六壬调用错误: {_xe}"
                        _raw_parts.append(f"【{_m}】\n{_out}")
                        continue
                    if _m in ("qizheng", "tieban"):
                        # 七政四余/铁板神数：走 new_tools_steward（steward.py 不支持）
                        try:
                            import new_tools_steward as _nts
                            _dt2 = birthdate or (str(data.get("bdate","")) + " " + str(data.get("btime","") or "12:00")).strip()
                            _d2, _t2 = _dt2.split() if " " in _dt2 else (_dt2, "12:00")
                            _lon2 = float(data.get("longitude", "120") or 120)
                            _lat2 = float(data.get("latitude", "30") or 30)
                            if _m == "qizheng":
                                _res = _nts.cast_qizheng(_d2, _t2, data.get("sex", "1"), lon=_lon2, lat=_lat2)
                                _out = _nts._fmt_qizheng(_res)[:6000]
                            else:
                                _res = _nts.cast_tieban(_d2, _t2, data.get("sex", "1"), lon=_lon2)
                                _out = _nts._fmt_tieban(_res)[:6000]
                        except Exception as _ne:
                            _out = f"{_m}调用错误: {_ne}"
                        _raw_parts.append(f"【{_m}】\n{_out}")
                        continue
                    if _m == "wuyunliuqi":
                        # 五运六气：走专属推算
                        try:
                            from 五运六气 import 推算 as _wuyun
                            _d3 = (birthdate or (str(data.get("bdate","")) + " " + str(data.get("btime","") or "12:00")).strip())[:10]
                            _out = _fmt_wuyun(_wuyun(_d3 or None))
                        except Exception as _we:
                            _out = f"五运六气计算错误: {_we}"
                        _raw_parts.append(f"【{_m}】\n{_out}")
                        continue
                    try:
                        _r = _sp.run(["python3", steward_script,
                                    "--birthdate", birthdate,
                                    "--sex", data.get("sex", "1"),
                                    "--birthplace", data.get("longitude", "120"),
                                    "--mode", _m] + extra,
                                   capture_output=True, text=True, timeout=20)
                        _out = (_r.stdout or "").strip()[:6000]
                        if not _out:
                            _out = (_r.stderr or "")[:2000] or "暂无输出"
                        _raw_parts.append(f"【{_m}】\n{_out}")
                    except Exception as _me:
                        _raw_parts.append(f"【{_m}】错误: {_me}")
                raw = "\n\n".join(_raw_parts)[:9000]
            # 当下测算带目的 → 注入盘面开头
            _purpose = str(data.get("purpose", "") or "").strip()[:30]
            if _purpose and any(m in SHI_JIA for m in _mode_list):
                raw = f"🎯 求测目的: {_purpose}\n" + raw
            
            # AI 解读
            interpretation = ""
            try:
                import urllib.request as _ur
                import json as _jm
                # 密钥从 密钥.json 读取（不入库），无则用环境变量，不再硬编码
                _ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
                _key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "密钥.json")
                if not _ds_key and os.path.isfile(_key_path):
                    try:
                        with open(_key_path, "r", encoding="utf-8") as _kf:
                            _ds_key = json.load(_kf).get("deepseek_api_key", "")
                    except Exception:
                        _ds_key = ""
                if _ds_key:
                    p = _jm.dumps({
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "你是一位玄学命理师。根据用户提供的排盘数据做深度解读。单人模式：提炼5-8条要点，把盘面关键信息（格局、星曜、五行、宫位、大运等）尽量解读完整，通俗易懂。双人模式：分析两人五行匹配度、性格互补性，结合关系类型给出具体建议。语气平和理性，解读要完整，不要草草收尾。"},
                            {"role": "user", "content": f"{'双人合盘(' + relation + ')' if dual == 'double' else '这是'} {mode}排盘结果：\n{raw[:10000]}"}
                        ],
                        "max_tokens": 3000
                    }).encode()
                    req = _ur.Request("https://api.deepseek.com/chat/completions",
                                     data=p,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + _ds_key})
                    resp = _ur.urlopen(req, timeout=20).read()
                    interpretation = _jm.loads(resp).get("choices", [{}])[0].get("message", {}).get("content", "")
            except:
                pass
            
            # \u6784\u5efa\u7ed3\u679c\u9875\u9762
            def _html():
                h = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
                h += '<title>\u7384\u5b66\u7ba1\u5bb6 / ' + esc(mode) + '</title>'
                h += '<style>*{margin:0;padding:0;box-sizing:border-box}'
                h += 'body{font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}'
                h += 'h1{font-size:20px;margin-bottom:2px}.sub{color:#888;font-size:.8rem;margin-bottom:16px}'
                h += '.card{background:#fff;border-radius:14px;padding:18px;margin-bottom:12px;box-shadow:0 2px 8px rgba(0,0,0,.06)}'
                h += '.ctitle{font-size:14px;font-weight:600;color:#b8453a;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #f0ebe6}'
                h += '.intro{font-size:15px;line-height:1.7;word-wrap:break-word}'
                h += '.intro table{border-collapse:collapse;margin:8px 0;width:100%;font-size:13px}'
                h += '.intro th,.intro td{border:1px solid #e0d8d2;padding:6px 8px;text-align:left}'
                h += '.intro th{background:#b8453a11;color:#b8453a}'
                h += '.intro blockquote{margin:8px 0;padding:8px 12px;background:#faf5f0;border-left:3px solid #b8453a;color:#555;border-radius:0 8px 8px 0}'
                h += '.intro hr{border:none;border-top:1px dashed #e0d8d2;margin:16px 0}'
                h += '.raw-box{font-size:12px;font-family:monospace;color:#555;white-space:pre-wrap;word-wrap:break-word}'
                h += '.tog{font-size:12px;color:#a0522d;cursor:pointer;text-align:center;margin:4px auto;display:block}'
                h += '.btn{display:block;padding:12px;background:#b8453a;color:#fff;border-radius:10px;text-align:center;text-decoration:none}'
                h += '.footer{text-align:center;margin-top:14px;color:#888;font-size:.8rem}'
                h += 'a{color:#a0522d;text-decoration:none}'
                h += '</style></head><body>'
                h += '<h1>\U0001f9d9 ' + esc(mode) + '</h1>'
                h += '<p class="sub">' + esc(birthdate) + '</p>'
                # 多选：按 【xxx】 分段，每个术数一个卡片直接展开；单选保持原样
                import re as _seg
                _multi = ',' in str(mode)
                if _multi:
                    _NAME = {"bazi":"八字","ziwei":"紫微","qizheng":"七政四余","tieban":"铁板神数","wuyunliuqi":"五运六气","qimen":"奇门遁甲","liuren":"大六壬","meihua":"梅花易数","jinkoujue":"金口诀","xiaoliuren":"小六壬"}
                    _segs = _seg.split(r'【', raw)
                    _seg_payload = []
                    for _s in _segs:
                        if not _s.strip():
                            continue
                        if '】' in _s:
                            _nm, _body = _s.split('】', 1)
                            _nm2 = _NAME.get(_nm.strip(), _nm.strip())
                            _seg_payload.append({"t": _nm2, "b": _clean_md(_body.strip())[:6000]})
                        else:
                            _seg_payload.append({"t": "", "b": _clean_md(_s.strip())[:6000]})
                    for _sp in _seg_payload:
                        _tpart = ('<div class="ctitle">' + esc(_sp["t"]) + '</div>') if _sp["t"] else ''
                        h += '<div class="card">' + _tpart + '<div class="intro">' + _md_to_html(_sp["b"]) + '</div></div>'
                    _seg_json = [x["b"] for x in _seg_payload]
                else:
                    # 单选：解读 + 排盘数据都走服务端 markdown 渲染
                    _single_payload = []
                    if interpretation:
                        h += '<div class="card"><div class="ctitle">\U0001f4ac \u89e3\u8bfb</div><div class="intro">' + _md_to_html(interpretation) + '</div></div>'
                        _single_payload.append(interpretation)
                    h += '<div class="card"><div class="ctitle">\U0001f4cb \u6392\u76d8\u6570\u636e</div><div class="intro">' + _md_to_html(_clean_md(raw)[:6000]) + '</div></div>'
                    _single_payload.append(_clean_md(raw)[:6000])
                    h += '<span class="tog" onclick="var r=document.getElementById(\'r\');r.style.display=r.style.display==\'none\'?\'block\':\'none\'">\U0001f50d \u67e5\u770b\u539f\u59cb\u6570\u636e</span>'
                    h += '<div id="r" class="card" style="display:none"><div class="raw-box">' + esc(raw[:5000]) + '</div></div>'
                    _seg_json = _single_payload
                h += '<button class="btn" style="margin-bottom:12px" onclick="aiDeep()">\U0001f52e AI \u6df1\u5ea6\u5206\u6790</button><div id="aiOut"></div>'
                h += '<a class="btn" href="/steward">\u518d\u7b97\u4e00\u6b21</a>'
                h += '<div class="footer"><a href="/tools">\u2190 \u5de5\u5177\u53f0</a></div>'
                h += '<script>' + _MD_RENDER_JS + '</script>'
                if '_seg_json' in locals() or '_seg_json' in globals():
                    h += '<script>var segArr=' + json.dumps(locals().get('_seg_json', []), ensure_ascii=False) + ';'
                    h += "var segEls=document.querySelectorAll('[id^=\"segmd\"]');"
                    h += 'for(var si=0;si<segArr.length && si<segEls.length;si++){segEls[si].innerHTML=mdRender(segArr[si]);}</script>'
                h += '<script>var aiRaw=' + json.dumps(_clean_md(raw)[:6000], ensure_ascii=False) + ';'
                h += 'async function aiDeep(){var out=document.getElementById(\'aiOut\');if(out.innerHTML){out.innerHTML=\'\';return}'
                h += 'out.innerHTML=\'<div style="padding:12px;color:#888">AI 分析中…（约30秒）</div>\';'
                h += 'var _t=setTimeout(function(){out.innerHTML=\'<div style="padding:12px;color:#c0392b">⏱ AI 响应超时，请重试</div>\';},30000);'
                h += 'try{var r=await fetch(\'/ai-read\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\',\'X-Requested-With\':\'XMLHttpRequest\'},body:JSON.stringify({text:aiRaw.slice(0,6000),scene:\'xuanxue_general\'})});var d=await r.json();clearTimeout(_t);'
                h += 'out.innerHTML=d.error?\'<div style="padding:12px;color:#c0392b">\'+d.error+\'</div>\':\'<div style="padding:14px;background:#fff8e6;border-radius:10px;margin-top:10px;line-height:1.7">\'+mdRender(d.answer)+\'</div>\';}'
                h += 'catch(e){out.innerHTML=\'<div style="padding:12px;color:#c0392b">请求失败</div>\';}}</script>'
                h += '</body></html>'
                return h
            
            if is_form:
                return _html()
            return jsonify({"success": True, "output": raw, "interpretation": interpretation})
        except Exception as e:
            err = str(e)
            if is_form:
                h = '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>\u7384\u5b66\u7ba1\u5bb6 / \u9519\u8bef</title>'
                h += '<style>*{margin:0;padding:0;box-sizing:border-box}'
                h += 'body{font-family:system-ui,sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}'
                h += 'h1{font-size:18px;margin-bottom:12px}'
                h += '.error{background:#fef2f0;color:#b8453a;padding:14px;border-radius:10px;font-size:14px}'
                h += '.btn{display:block;padding:12px;background:#a0522d;color:#fff;border-radius:10px;text-align:center;text-decoration:none;margin-top:16px}'
                h += 'a{color:#a0522d;text-decoration:none}'
                h += '</style></head><body>'
                h += '<h1>\U0001f9d9 \u9519\u8bef</h1>'
                h += '<div class="error">' + html.escape(err) + '</div>'
                h += '<a class="btn" href="/steward">\u91cd\u8bd5</a>'
                h += '<div class="footer"><a href="/tools">\u2190 \u5de5\u5177\u53f0</a></div></body></html>'
                return h
            return jsonify({"success": False, "error": err}), 500
    
    return _STEWARD_HTML
@app.route("/tools")
@login_required
def tools():
    """工具台 · 移动端适配"""
    return '''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>工具台 · 莫名心小站</title>
<style>
:root{--bg:#f7f2ec;--card:#fffdf9;--text:#3d3a36;--text-l:#8a827a;--accent:#a0522d;--accent-2:#c68a5d;--line:#e8dfd3;--shadow:0 2px 10px rgba(160,82,45,.08)}
body.dark{--bg:#16161a;--card:#1e1e24;--text:#ece8dc;--text-l:#b0a898;--accent:#c68a5d;--line:#3a3a40;--shadow:0 2px 10px rgba(0,0,0,.3)}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);padding:20px 16px;max-width:100%;margin:0 auto;padding-bottom:60px}
h1{font-size:1.35rem;color:var(--accent);margin-bottom:4px}
.sub{color:var(--text-l);font-size:.84rem;margin-bottom:20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:480px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 14px;box-shadow:var(--shadow);text-decoration:none;color:var(--text);transition:.2s;display:flex;flex-direction:column;align-items:center;text-align:center}
.card:hover{box-shadow:0 4px 16px rgba(160,82,45,.14);transform:translateY(-1px);border-color:var(--accent-2)}
.card-icon{font-size:2rem;margin-bottom:8px}
.card-name{font-weight:600;font-size:.95rem;margin-bottom:4px;color:var(--text)}
.card-desc{color:var(--text-l);font-size:.78rem;line-height:1.4}
.card .badge{font-size:.7rem;padding:2px 8px;border-radius:10px;margin-top:6px}
.badge-new{background:#a0522d22;color:#a0522d}
.badge-ok{background:#27ae6022;color:#27ae60}
.footer{text-align:center;color:var(--text-l);font-size:.78rem;margin-top:28px}
.footer a{color:var(--accent);text-decoration:none}
.nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px}
.nav a{display:inline-block;padding:6px 14px;background:var(--card);border:1px solid var(--line);border-radius:999px;color:var(--accent);font-size:.84rem;text-decoration:none}
.nav a:hover{background:var(--accent);color:#fff}
</style></head><body>
<script>
(function(){try{if(localStorage.getItem('xiaozhan_dark_mode')==='true')document.body.classList.add('dark')}catch(e){}})();
</script>
<div class="nav"><a href="/">🏠 首页</a><a href="/steward">🧙 玄学管家</a><a href="/arsenal">🎯 弹药弹夹</a></div>
<h1>🧩 莫名心·工具台</h1>
<p class="sub">小站全部工具 — 移动端适配</p>

<div class="grid">

<a href="/" class="card">
<div class="card-icon">🏠</div>
<div class="card-name">首页</div>
<div class="card-desc">辨证食疗 · 中医科普</div>
</a>

<a href="/extensions" class="card">
<div class="card-icon">🧩</div>
<div class="card-name">扩展管理</div>
<div class="card-desc">启停功能开关</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/yunqi" class="card">
<div class="card-icon">🌀</div>
<div class="card-name">五运六气</div>
<div class="card-desc">岁运·六气·时位推算</div>
</a>

<a href="/notes" class="card">
<div class="card-icon">📝</div>
<div class="card-name">学习笔记</div>
<div class="card-desc">素问笔记·数字中医有感</div>
</a>

<a href="/yunqi-eval" class="card">
<div class="card-icon">🥣</div>
<div class="card-name">食疗评价</div>
<div class="card-desc">五维评分·膳食方案</div>
</a>

<a href="/philosophy" class="card">
<div class="card-icon">📖</div>
<div class="card-name">哲思文库</div>
<div class="card-desc">SEP斯坦福哲学百科·1864词条</div>
</a>

<a href="/daogui" class="card">
<div class="card-icon">🏛️</div>
<div class="card-name">道归文库</div>
<div class="card-desc">全体系文档 · 哲学对撞10场</div>
</a>

<a href="/gutenberg" class="card">
<div class="card-icon">📚</div>
<div class="card-name">古登堡经典</div>
<div class="card-desc">柏拉图·亚里士多德·康德·尼采</div>
</a>

<a href="/daogui3" class="card">
<div class="card-icon">🏛️</div>
<div class="card-name">道归3.0</div>
<div class="card-desc">体系全貌·新兴学科</div>
</a>

<a href="/steward" class="card">
<div class="card-icon">🧙</div>
<div class="card-name">玄学管家</div>
<div class="card-desc">术数总入口 · 八字紫微奇门六爻星盘七政</div>
<span class="badge badge-new">算命台</span>
</a>

<a href="/poetry" class="card">
<div class="card-icon">🏮</div>
<div class="card-name">诗词查询</div>
<div class="card-desc">31万诗词·诗经·论语·本地检索</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/kx" class="card">
<div class="card-icon">📚</div>
<div class="card-name">知识库问答</div>
<div class="card-desc">道归·医书·哲学RAG</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/meddocs" class="card">
<div class="card-icon">🪡</div>
<div class="card-name">中西医结合推论</div>
<div class="card-desc">总纲·辨证·经络·本草</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/kxwonders" class="card">
<div class="card-icon">⚡</div>
<div class="card-name">KX 神迹</div>
<div class="card-desc">跨领域超级融合档案</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/theory" class="card">
<div class="card-icon">🏛️</div>
<div class="card-name">理论体系</div>
<div class="card-desc">六套理论·修正版</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/classic-view/" class="card">
<div class="card-icon">📜</div>
<div class="card-name">经典古籍</div>
<div class="card-desc">素问50卷·灵枢·本草</div>
</a>

<a href="/philosophy-image" class="card">
<div class="card-icon">📷</div>
<div class="card-name">以图搜哲医</div>
<div class="card-desc">识图匹配医书·哲思·道归</div>
<span class="badge badge-ok">本地+AI</span>
</a>

<a href="/local-vision" class="card">
<div class="card-icon">🔍</div>
<div class="card-name">本地识图</div>
<div class="card-desc">纯本地CLIP·免费无限量</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/toolbox" class="card">
<div class="card-icon">🧰</div>
<div class="card-name">百宝囊</div>
<div class="card-desc">图片·PDF·文本·纯本地工具</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/ask" class="card">
<div class="card-icon">🤖</div>
<div class="card-name">AI问答</div>
<div class="card-desc">DeepSeek V4 驱动</div>
</a>

<a href="/crawled-view/" class="card">
<div class="card-icon">[虫]</div>
<div class="card-name">求知虫</div>
<div class="card-desc">爬取内容查看器</div>
</a>

<a href="/forge-destiny" class="card">
<div class="card-icon">⚒️</div>
<div class="card-name">锻因缘</div>
<div class="card-desc">平行世界·命运之锤</div>
</a>

<a href="/poems" class="card">
<div class="card-icon">🔥</div>
<div class="card-name">即兴创作</div>
<div class="card-desc">心哥的诗 · 火苍龙骨</div>
</a>

<a class="card" style="background:#1a1a2e;color:#fff">
<div class="card-icon" style="font-size:1.2rem">🌙</div>
<div class="card-name">系统命令</div>
<div class="card-desc" style="color:#aaa;font-size:.72rem">
bazi / xiaoliuren / steward / phil
</div>
</a>

</div>

<div class="footer">
<a href="/">← 返回首页</a> · 🌙 莫名心小站 v3
</div>

</body></html>'''


# ── 启动（必须在所有路由之后） ──

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", "8080"))
    print(f"\n{'═' * 50}")
    print("🌙 莫名心 · 小站 v3 (Flask 重装甲版)")
    print(f"{'═' * 50}")
    print(f"  所有路由已注册")
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
