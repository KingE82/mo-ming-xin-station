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

app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = False
app.config["TRAP_HTTP_EXCEPTIONS"] = False

# 工具台 Blueprint（隔离路由注册）
try:
    from tools_blueprint import tools_bp
    app.register_blueprint(tools_bp)
except Exception:
    pass


def ping():
    return "pong"

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
a{{color:#4a7dff;text-decoration:none}}
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
a{color:#4a7dff;text-decoration:none}
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
    .replace(/\`([^']+)\`/g,'<code>$1</code>')
    .replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^# (.+)$/gm,'<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/\*(.+?)\*/g,'<em>$1</em>')
    .replace(/^\s*[-*+] (.+)$/gm,'<li>$1</li>').replace(/(<li>.*<\/li>\\n?)+/g,'<ul>$&</ul>')
    .replace(/^> (.+)$/gm,'<blockquote>$1</blockquote>').replace(/\n/g,'<br>');
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
a{color:#4a7dff;text-decoration:none}
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
        html += 'a{color:#4a7dff;text-decoration:none}'
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
        html += 'body{font-family:system-ui,sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}'
        html += 'h1{font-size:20px;margin-bottom:4px}'
        html += '.sub{color:#888;font-size:.8rem;margin-bottom:16px}'
        html += '.card{background:#fff;border-radius:12px;padding:14px;margin-bottom:10px;text-decoration:none;color:#2c2c2c;display:block;box-shadow:0 1px 4px rgba(0,0,0,.06)}'
        html += '.name{font-weight:600;font-size:14px}'
        html += '.desc{color:#666;font-size:.8rem;margin-top:2px}'
        html += '.footer{text-align:center;margin-top:20px}'
        html += 'a{color:#4a7dff;text-decoration:none}'
        html += 'input{width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:14px;margin-bottom:12px}'
        html += '</style></head><body>'
        html += '<h1>📖 哲思文库</h1>'
        html += '<p class="sub">斯坦福哲学百科 · 102条</p>'
        html += '<form method="get" action="/knowledge-search"><input type="text" name="query" placeholder="搜索概念…"></form>'
        count = 0
        for slug, entry in sorted(sep_data.items()):
            if count >= 60:
                if len(sep_data) > 60:
                    html += '<p style="color:#888;text-align:center;font-size:.8rem">…还有' + str(len(sep_data)-60) + '条，搜索查看</p>'
                break
            name = str(entry.get('name', slug))[:60]
            title = str(entry.get('title', ''))[:100]
            html += f'<a class="card" href="/philosophy/{slug}"><div class="name">{name}</div><div class="desc">{title}</div></a>'
            count += 1
        html += '<div class="footer"><a href="/tools">← 工具台</a></div></body></html>'
        return html
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
            name = str(entry.get("name", slug))
            title = str(entry.get("title", ""))
            body_zh = entry.get("body_zh", "") or entry.get("body", "") or ""
            body_en = entry.get("body_en", "") or ""
            body = body_zh or body_en
            if not body:
                body = str(entry.get("body", "") or "")
            body = body[:10000]
            import html as hmod
            title_safe = hmod.escape(title)
            name_safe = hmod.escape(name)
            body_safe = hmod.escape(body)
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
.content{{background:#fff;border-radius:12px;padding:16px;font-size:14px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word}}
.footer{{text-align:center;margin-top:20px;font-size:.8rem;color:#888}}
a{{color:#4a7dff;text-decoration:none}}
</style></head><body>
<h1>{name_safe}</h1>
<p class="sub">{title_safe}</p>
<div class="content">{body_safe}</div>
<div class="footer"><a href="https://plato.stanford.edu/entries/{slug}/" target="_blank" style="color:#2980b9">🔗 查看SEP原文</a> · <a href="/philosophy">← 哲思文库</a></div>
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
        h += 'body{font-family:system-ui,sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}'
        h += 'h1{font-size:20px;margin-bottom:4px}'
        h += '.sub{color:#888;font-size:.8rem;margin-bottom:16px}'
        h += '.sect{margin-bottom:16px}'
        h += '.stitle{font-weight:600;font-size:.9rem;color:#b8453a;margin-bottom:8px;padding-left:4px;border-left:3px solid #b8453a}'
        h += '.card{background:#fff;border-radius:10px;padding:12px;margin-bottom:8px;box-shadow:0 1px 3px rgba(0,0,0,.06)}'
        h += '.card a{text-decoration:none;color:#2c2c2c;display:block}'
        h += '.card-title{font-weight:500;font-size:14px}'
        h += '.card-meta{color:#888;font-size:.75rem;margin-top:2px}'
        h += '.footer{text-align:center;margin-top:20px;font-size:.8rem;color:#888}'
        h += 'a{color:#4a7dff;text-decoration:none}'
        h += '.empty{color:#888;text-align:center;padding:40px}'
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
    h += 'a{color:#4a7dff;text-decoration:none}'
    h += '</style></head><body>'
    h += '<h1>📚 古登堡经典</h1>'
    h += '<p class="sub">Project Gutenberg · 免费哲学经典搜索</p>'
    safe_q = html.escape(query)
    h += '<form method="get" action="/gutenberg"><input type="text" name="q" placeholder="搜索作者或书名…" value="' + safe_q + '"></form>'
    
    if results:
        h += '<p class="sub">找到 ' + str(len(results)) + ' 条结果</p>'
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
        body = hmod.escape("\n".join(lines[1:]).strip())
        return f"""<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:system-ui,sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto}}
h1{{font-size:20px;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid #e0d8d2}}
.content{{font-size:14px;line-height:1.8;white-space:pre-wrap;word-wrap:break-word}}
.footer{{text-align:center;margin-top:24px;font-size:.8rem;color:#888}}
a{{color:#4a7dff;text-decoration:none}}
</style></head><body><h1>{title}</h1>
<div class="content">{body}</div>
<div class="footer"><a href="/notes">← 学习笔记</a></div></body></html>"""
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
    return "<!DOCTYPE html><html lang=zh-CN><head><meta charset=UTF-8><title>" + bn + "</title>" +         "<style>body{background:#16161a;color:#d8d0c0;padding:20px;font-family:sans-serif;line-height:2;white-space:pre-wrap;max-width:720px;margin:0 auto}" +         "a{color:#b0a898;text-decoration:none}.nav{padding:10px 0;border-bottom:1px solid #333}" +         ".pager{text-align:center;padding:14px}</style><body><div class=nav><a href=/crawled-view/>返回</a></div>" +         "<div>" + html.escape(chunk) + "</div><div class=pager>第" + str(page) + "/" + str(total) + "页</div></body></html>" 
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


@app.route("/daogui3")
@login_required
def daogui3():
    """道归3.0 · 未来展望"""
    BASE = os.path.dirname(os.path.abspath(__file__))
    pages = [
        ("道归体系全貌_v3.0_优化版", "🏛️ 体系全貌"),
        ("新兴学科预测_优化版", "🔮 新兴学科"),
        ("灵魂稳定学（第九支柱）_优化版", "💎 灵魂稳定学"),
    ]
    html = '''<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>道归3.0 · 未来展望</title>
<style>
body{font-family:system-ui,sans-serif;max-width:800px;margin:0 auto;padding:20px;line-height:1.7;background:#faf8f5;color:#1a1a2e}
h1{color:#8b0000;border-bottom:2px solid #8b0000;padding-bottom:8px}
.nav a{display:inline-block;margin:4px;padding:8px 16px;background:#1a1a2e;color:#faf8f5;text-decoration:none;border-radius:6px}
.nav a:hover{background:#8b0000}
.content{background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-top:20px;white-space:pre-wrap}
hr{border:none;border-top:1px solid #ddd;margin:24px 0}
blockquote{border-left:3px solid #8b0000;margin:16px 0;padding:8px 16px;background:#fff5f5;border-radius:4px}
</style></head><body>
'''
    html += '<h1>🌙 道归3.0 · 未来展望</h1>\n<div class="nav">'
    for slug, label in pages:
        html += f'<a href="?p={slug}">{label}</a> '
    html += '</div>\n'
    
    p = request.args.get('p', '道归体系全貌_v3.0_优化版')
    found = False
    for slug, label in pages:
        if p == slug:
            filepath = os.path.join(BASE, '道归', f'{slug}.md')
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Remove YAML-like header
                import re
                content = re.sub(r'^---.*?---', '', content, flags=re.DOTALL)
                content = content.strip()
                html += f'<h2>{label}</h2>\n<div class="content">{content}</div>'
                found = True
                break
    if not found:
        html += '<p>页面未找到</p>'
    
    html += '</body></html>'
    return html


# ── 启动 ──

def _error_page(code, msg):
    return f'<!DOCTYPE html><html lang=zh-CN><head><meta charset=UTF-8><title>{code}</title><style>body{{font-family:system-ui,sans-serif;background:#16161a;color:#ece8dc;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center;padding:20px}}a{{color:#4a7dff}}</style></head><body><h1>{code}</h1><p>{msg}</p><a href=/>返回首页</a></body></html>', code

@app.errorhandler(500)
def handle_500(e):
    return _error_page(500, '服务器内部错误')

@app.errorhandler(404)
def handle_404(e):
    return _error_page(404, '页面未找到')



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
.ext-toggle input:checked+.slider{background:#4a7dff}
.ext-toggle input:checked+.slider::before{transform:translateX(20px)}
.ext-more{color:#999;cursor:pointer;padding:4px;font-size:1.1rem}
.search-bar{display:flex;gap:8px;margin-bottom:20px}
.search-bar input{flex:1;padding:10px 14px;border:1px solid #ddd;border-radius:8px;font-size:.9rem;outline:none}
.search-bar input:focus{border-color:#4a7dff}
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
<a href="/" style="color:#4a7dff;text-decoration:none">← 返回首页</a>
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
        icon: "📷", name: "以图搜哲学", desc: "上传图片，自动搜索相关哲思条目与概念。",
        on: false, color: "#8e44ad"
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
        icon: "📊", name: "八字排盘", desc: "fortune-skill 引擎，排大运、起运、十神。",
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


_STEWARD_HTML = """<!DOCTYPE html><html lang=\"zh-CN\"><head>\n<meta charset=\"UTF-8\">\n<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no\">\n<title>玄学管家 / 莫名心小站</title>\n<style>\n*{margin:0;padding:0;box-sizing:border-box}\nbody{font-family:system-ui,-apple-system,\"PingFang SC\",sans-serif;background:#f5f0eb;color:#2c2c2c;padding:16px;max-width:640px;margin:0 auto;min-height:100vh}\nh1{font-size:22px;margin-bottom:2px}\n.sub{color:#888;font-size:13px;margin-bottom:16px}\n.card{background:#fff;border-radius:16px;padding:20px;box-shadow:0 2px 12px rgba(0,0,0,.06);margin-bottom:12px}\nlabel{font-size:14px;font-weight:500;display:block;margin-bottom:6px;color:#555}\ninput,select{width:100%;padding:14px;border:2px solid #e0d8d2;border-radius:12px;font-size:16px;outline:none;background:#fff;box-sizing:border-box}\ninput:focus,select:focus{border-color:#b8453a}\ninput{margin-bottom:14px}\nselect{margin-bottom:14px;appearance:none}\n.btn{width:100%;padding:14px;background:#b8453a;color:white;border:none;border-radius:12px;font-size:16px;font-weight:600;cursor:pointer}\n.btn:active{opacity:.8}\n.tag{display:inline-block;padding:4px 10px;border-radius:8px;font-size:12px;margin-right:4px;margin-bottom:4px}\n.tag-bazi{background:#e74c3c22;color:#e74c3c}\n.tag-ziwei{background:#8e44ad22;color:#8e44ad}\n.tag-qimen{background:#2980b922;color:#2980b9}\n.tag-meihua{background:#27ae6022;color:#27ae60}\n.tag-liuren{background:#d3540022;color:#d35400}\n.footer{text-align:center;margin-top:20px;font-size:13px;color:#888}\na{color:#4a7dff;text-decoration:none}\n#loading{display:none;text-align:center;padding:20px}\n.spinner{display:inline-block;width:24px;height:24px;border:3px solid #eee;border-top-color:#b8453a;border-radius:50%;animation:spin .8s linear infinite}\n@keyframes spin{to{transform:rotate(360deg)}}\n</style></head><body>\n<h1>🧙 玄学管家</h1>\n<p class=\"sub\">七套术数引擎 · 输入生达即可起盘</p>\n<div class=\"card\">\n<form method=\"post\" action=\"/steward\" onsubmit=\"document.getElementById('loading').style.display='block';document.getElementById('submitBtn').disabled=true\">\n<label>生达</label>\n<div style="display:flex;gap:8px"><div style="flex:1"><label>\u65e5\u671f</label><input type=\"date\" name=\"bdate\" value=\"2026-07-28\" required></div><div style="flex:none;width:120px"><label>\u65f6\u95f4</label><input type=\"time\" name=\"btime\" value=\"12:00\" step=\"60\"></div></div>\n<div style="margin-bottom:14px">
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
<input type="date" name="bdate2" value="2026-07-28" required>
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
<label>术数</label>\n<select name=\"mode\">\n<option value=\"bazi\">八字 — 子平八字排盘</option>\n<option value=\"ziwei\">紫微斗数 — 紫微课盘</option>\n<option value=\"qimen\">奇门道甲 — 时家奇门盘</option>\n<option value=\"liuren\">大六壬 — 六壬课经</option>\n<option value=\"meihua\">梅花易数 — 梅花起卦</option><option value="jinkoujue">金口诀 — 金口诀课经</option><option value="wuyunliuqi">五运六气 — 岁运客主加临</option><option value="xiaoliuren">小六壬 — 道传起卦</option>\n<option value=\"all\">全量 — 所有术数</option>\n</select>\n<button type=\"submit\" class=\"btn\" id=\"submitBtn\">起盘</button>\n</form>\n</div>\n<div id=\"loading\" class=\"card\" style=\"display:none;text-align:center\"><div class=\"spinner\"></div><p style=\"margin-top:8px;color:#888\">计算中...</p></div>\n<p style=\"text-align:center;margin-top:12px\">\n<span class=\"tag tag-bazi\">八字</span>\n<span class=\"tag tag-ziwei\">紫微</span>\n<span class=\"tag tag-qimen\">奇门</span>\n<span class=\"tag tag-liuren\">六壬</span>\n<span class=\"tag tag-meihua\">梅花</span>\n<span class=\"tag tag-jinkoujue\" style=\"background:#e67e2222;color:#e67e22\">金口诀</span>\n<span class=\"tag tag-wuyun\" style=\"background:#1abc9c22;color:#1abc9c\">五运六气</span>\n</p>\n<div class=\"footer\"><a href=\"/tools\">← 工具台</a></div>\n</body></html>"""

@app.route("/steward", methods=["GET", "POST"])
@login_required
def steward():
    """赛博玄学管家"""
    import subprocess as _sp
    steward_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                  "skills", "metaphysics-steward", "scripts", "steward.py")
    
    def esc(t):
        return html.escape(str(t)[:5000])
    
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form or {}
        birthdate = data.get("birthdate", "") or (data.get("bdate","") + " " + (data.get("btime","") or "12:00")).strip()
        mode = data.get("mode", "bazi")
        is_form = request.content_type and "form" in request.content_type
        
        try:
            dual = data.get("dual", "single")
            relation = data.get("relation", "love")
            
            if mode == "wuyunliuqi":
                try:
                    from 五运六气 import 推算 as _wuyun
                    wu = _wuyun(birthdate[:10] if len(birthdate) >= 10 else None)
                    raw = json.dumps(wu, ensure_ascii=False, indent=2)[:6000]
                except Exception as _we:
                    raw = f"五运六气计算错误: {_we}"
            elif mode == "xiaoliuren":
                try:
                    parts = birthdate.replace("-"," ").replace(":"," ").split()
                    if len(parts) >= 4:
                        xl_args = [str(int(parts[1])), str(int(parts[2])), str(int(parts[3]))]
                        xl_r = _sp.run(["xiaoliuren", "--time"] + xl_args, capture_output=True, text=True, timeout=10)
                    else:
                        xl_r = _sp.run(["xiaoliuren", "3", "5", "7"], capture_output=True, text=True, timeout=10)
                    raw = (xl_r.stdout or "")[:5000] or (xl_r.stderr or "")[:2000] or "暂无输出"
                except Exception as _xe:
                    raw = f"小六壬调用错误: {_xe}"
            elif dual == "double":
                # 双人模式：算两个人的盘
                bd2 = (data.get("bdate2","") + " " + (data.get("btime2","") or "12:00")).strip()
                sex2 = data.get("sex2", "1")
                raw_p1 = ""
                raw_p2 = ""
                try:
                    r1 = _sp.run(["python3", steward_script, "--birthdate", birthdate, "--sex", data.get("sex","1"), "--mode", mode], capture_output=True, text=True, timeout=20)
                    raw_p1 = (r1.stdout or "")[:5000]
                except:
                    raw_p1 = f"第一人排盘错误"
                try:
                    r2 = _sp.run(["python3", steward_script, "--birthdate", bd2, "--sex", sex2, "--mode", mode], capture_output=True, text=True, timeout=20)
                    raw_p2 = (r2.stdout or "")[:5000]
                except:
                    raw_p2 = f"第二人排盘错误"
                raw = f"第一人：\n{raw_p1}\n\n第二人：\n{raw_p2}"
            else:
                r = _sp.run(["python3", steward_script,
                            "--birthdate", birthdate,
                            "--sex", data.get("sex", "1"),
                            "--mode", mode],
                           capture_output=True, text=True, timeout=20)
                raw = (r.stdout or "")[:6000]
                if not raw:
                    raw = (r.stderr or "")[:2000] or "暂无输出"
            
            # AI \u89e3\u8bfb
            interpretation = ""
            try:
                import urllib.request as _ur
                import json as _jm
                _ds_key = "sk-ccb1ffae67ba4f46a9dcad04302243d9"
                if _ds_key:
                    p = _jm.dumps({
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "system", "content": "你是一位玄学命理师。根据用户提供的排盘数据做解读。单人模式：提炼3-5条要点，通俗易懂。双人模式：分析两人五行匹配度、性格互补性，结合关系类型给出具体建议。语气平和理性，不超过500字。"},
                            {"role": "user", "content": f"{'双人合盘(' + relation + ')' if dual == 'double' else '这是'} {mode}排盘结果：\n{raw[:10000]}"}
                        ],
                        "max_tokens": 800
                    }).encode()
                    req = _ur.Request("https://api.deepseek.com/chat/completions",
                                     data=p,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer sk-ccb1ffae67ba4f46a9dcad04302243d9"})
                    resp = _ur.urlopen(req, timeout=20).read()
                    interpretation = _jm.loads(resp).get("choices", [{}])[0].get("message", {}).get("content", "")
            except:
                pass
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
                h += '.intro{font-size:15px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word}'
                h += '.raw-box{font-size:12px;font-family:monospace;color:#555;white-space:pre-wrap;word-wrap:break-word}'
                h += '.tog{font-size:12px;color:#4a7dff;cursor:pointer;text-align:center;margin:4px auto;display:block}'
                h += '.btn{display:block;padding:12px;background:#b8453a;color:#fff;border-radius:10px;text-align:center;text-decoration:none}'
                h += '.footer{text-align:center;margin-top:14px;color:#888;font-size:.8rem}'
                h += 'a{color:#4a7dff;text-decoration:none}'
                h += '</style></head><body>'
                h += '<h1>\U0001f9d9 ' + esc(mode) + '</h1>'
                h += '<p class="sub">' + esc(birthdate) + '</p>'
                if interpretation:
                    h += '<div class="card"><div class="ctitle">\U0001f4ac \u89e3\u8bfb</div><div class="intro">' + esc(interpretation) + '</div></div>'
                else:
                    h += '<div class="card"><div class="ctitle">\U0001f4cb \u6392\u76d8\u6570\u636e</div><div class="intro">' + esc(raw[:2000]) + '</div></div>'
                h += '<span class="tog" onclick="var r=document.getElementById(\'r\');r.style.display=r.style.display==\'none\'?\'block\':\'none\'">\U0001f50d \u67e5\u770b\u539f\u59cb\u6570\u636e</span>'
                h += '<div id="r" class="card" style="display:none"><div class="raw-box">' + esc(raw[:5000]) + '</div></div>'
                h += '<a class="btn" href="/steward">\u518d\u7b97\u4e00\u6b21</a>'
                h += '<div class="footer"><a href="/tools">\u2190 \u5de5\u5177\u53f0</a></div></body></html>'
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
                h += '.btn{display:block;padding:12px;background:#4a7dff;color:#fff;border-radius:10px;text-align:center;text-decoration:none;margin-top:16px}'
                h += 'a{color:#4a7dff;text-decoration:none}'
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
:root{--bg:#f5f5f5;--card:#fff;--text:#222;--text-l:#666;--shadow:0 1px 4px rgba(0,0,0,.08)}
body.dark{--bg:#16161a;--card:#1e1e24;--text:#ece8dc;--text-l:#b0a898;--shadow:0 1px 4px rgba(0,0,0,.3)}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);padding:16px;max-width:100%;margin:0 auto;padding-bottom:60px}
h1{font-size:1.3rem;margin-bottom:4px}
.sub{color:var(--text-l);font-size:.82rem;margin-bottom:16px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:480px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border-radius:12px;padding:16px;box-shadow:var(--shadow);text-decoration:none;color:var(--text);transition:.2s;display:flex;flex-direction:column;align-items:center;text-align:center}
.card:hover{box-shadow:0 3px 12px rgba(0,0,0,.12);transform:translateY(-1px)}
.card-icon{font-size:2rem;margin-bottom:8px}
.card-name{font-weight:600;font-size:.95rem;margin-bottom:4px}
.card-desc{color:var(--text-l);font-size:.78rem;line-height:1.4}
.card .badge{font-size:.7rem;padding:2px 8px;border-radius:10px;margin-top:6px}
.badge-new{background:#4a7dff22;color:#4a7dff}
.badge-ok{background:#27ae6022;color:#27ae60}
.footer{text-align:center;color:var(--text-l);font-size:.78rem;margin-top:24px}
.footer a{color:#4a7dff;text-decoration:none}
</style></head><body>
<script>
(function(){try{if(localStorage.getItem('xiaozhan_dark_mode')==='true')document.body.classList.add('dark')}catch(e){}})();
</script>
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

<a href="/yunqi-eval" class="card">
<div class="card-icon">🥣</div>
<div class="card-name">食疗评价</div>
<div class="card-desc">五维评分·膳食方案</div>
</a>

<a href="/philosophy" class="card">
<div class="card-icon">📖</div>
<div class="card-name">哲思文库</div>
<div class="card-desc">102条SEP全文检索</div>
</a>

<a href="/philosophy-fetch" class="card">
<div class="card-icon">🌐</div>
<div class="card-name">在线哲思</div>
<div class="card-desc">抓取新SEP条目</div>
</a>

<a href="/daogui3" class="card">
<div class="card-icon">🏛️</div>
<div class="card-name">道归3.0</div>
<div class="card-desc">体系全貌·新兴学科</div>
</a>

<a href="/steward" class="card">
<div class="card-icon">🧙</div>
<div class="card-name">玄学管家</div>
<div class="card-desc">八字·紫微·奇门·六壬</div>
<span class="badge badge-new">NEW</span>
</a>

<a href="/classic-view/" class="card">
<div class="card-icon">📜</div>
<div class="card-name">经典古籍</div>
<div class="card-desc">素问50卷·灵枢·本草</div>
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
