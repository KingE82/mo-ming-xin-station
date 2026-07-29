from flask import Blueprint

tools_bp = Blueprint('tools', __name__)

@tools_bp.route('/tools')
def tools_page():
    return """<html><body><h1>⚠️</h1><p>工具台已迁移到新版本</p><p><a href='/'>返回首页</a></p></body></html>"""</head><body>

<h1>🧩 工具台</h1>
<p class="sub">莫名心小站 · 全部功能</p>

<div class="section">
<div class="section-title">🏠 核心功能</div>
<div class="grid">
<a href="/" class="card"><div class="card-icon" style="background:#b8453a22;color:#b8453a">🏠</div><div class="card-info"><div class="card-name">首页 · 辨证食疗</div><div class="card-desc">中医辨证 + 食疗方案</div></div></a>
<a href="/phase-theory" class="card"><div class="card-icon" style="background:#8e44ad22;color:#8e44ad">🌀</div><div class="card-info"><div class="card-name">物态人论</div><div class="card-desc">冰·水·火·超临界相变</div></div></a>
<a href="/knowledge-search" class="card"><div class="card-icon" style="background:#2980b922;color:#2980b9">🔍</div><div class="card-info"><div class="card-name">界面查询</div><div class="card-desc">知识搜索 · 关联疾病</div></div></a>
<a href="/yunqi" class="card"><div class="card-icon" style="background:#16a08522;color:#16a085">🌀</div><div class="card-info"><div class="card-name">五运六气</div><div class="card-desc">岁运·六气·时位推算</div></div></a>
<a href="/yunqi-eval" class="card"><div class="card-icon" style="background:#27ae6022;color:#27ae60">🥣</div><div class="card-info"><div class="card-name">食疗评价</div><div class="card-desc">五维气候·脏腑·五味评分</div></div></a>
<a href="/philosophy" class="card"><div class="card-icon" style="background:#8b000022;color:#8b0000">📖</div><div class="card-info"><div class="card-name">哲思文库</div><div class="card-desc">SEP 102条 · 全文检索</div></div></a>
</div></div>

<div class="section">
<div class="section-title">🔮 玄学工具箱（NEW）</div>
<div class="grid">
<a href="/steward" class="card"><div class="card-icon" style="background:#8e44ad22;color:#8e44ad">🧙</div><div class="card-info"><div class="card-name">玄学管家</div><div class="card-desc">八字·紫微·奇门·六壬</div></div><span class="card-badge">NEW</span></a>
<a href="/classic-view/" class="card"><div class="card-icon" style="background:#d3540022;color:#d35400">📜</div><div class="card-info"><div class="card-name">经典古籍</div><div class="card-desc">素问50卷·灵枢</div></div></a>
<a href="/crawled-view/" class="card"><div class="card-icon" style="background:#7f8c8d22;color:#7f8c8d">🕳️</div><div class="card-info"><div class="card-name">求知虫</div><div class="card-desc">爬取内容查看</div></div></a>
<a href="/notes" class="card"><div class="card-icon" style="background:#2c3e5022;color:#2c3e50">📝</div><div class="card-info"><div class="card-name">学习笔记</div><div class="card-desc">个人知识记录</div></div></a>
</div></div>

<div class="section">
<div class="section-title">🏛️ 道归体系</div>
<div class="grid">
<a href="/gutenberg" class="card"><div class="card-icon" style="background:#1abc9c22;color:#1abc9c">📚</div><div class="card-info"><div class="card-name">古登堡经典</div><div class="card-desc">Project Gutenberg · 哲学经典</div></div></a>
<a href="/daogui3" class="card"><div class="card-icon" style="background:#8b000022;color:#8b0000">🏛️</div><div class="card-info"><div class="card-name">道归3.0</div><div class="card-desc">体系全貌·新兴学科</div></div></a>
<a href="/forge-destiny" class="card"><div class="card-icon" style="background:#e67e2222;color:#e67e22">⚒️</div><div class="card-info"><div class="card-name">锻因缘</div><div class="card-desc">命运之锤</div></div></a>
<a href="/upload" class="card"><div class="card-icon" style="background:#3498db22;color:#3498db">📤</div><div class="card-info"><div class="card-name">上传文件</div><div class="card-desc">DOCX/TXT/图片</div></div></a>
<a href="/ask" class="card"><div class="card-icon" style="background:#2c3e5022;color:#2c3e50">🤖</div><div class="card-info"><div class="card-name">AI问答</div><div class="card-desc">DeepSeek 驱动</div></div></a>
</div></div>

<div class="section">
<div class="section-title">💻 CLI 系统命令</div>
<div class="cli-box">
<span>bazi</span> 2006 9 22 7 &nbsp;&nbsp;# 八字排盘<br>
<span>xiaoliuren</span> 3 5 7 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 小六壬起卦<br>
<span>steward</span> --birthdate "2006-09-22 07:58" --mode bazi &nbsp;&nbsp;# 七套术数<br>
<span>phil</span> search "free will" &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 学术论文搜索<br>
<span>phil</span> gutenberg "plato" &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# 古登堡经典<br>
<span>phil</span> sep "daoism" &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# SEP 条目
</div></div>

<div class="footer">
<a href="/extensions">🧩 扩展管理</a> · 🌙 莫名心小站
</div>

</body></html>"""

@tools_bp.route('/extensions')
def ext_page():
    return """<!DOCTYPE html><html lang="zh-CN"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>扩展管理 · 莫名心小站</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;max-width:800px;margin:auto;padding:16px;background:#f5f0eb;color:#2c2c2c}
h1{font-size:1.3rem;margin-bottom:4px}
.sub{color:#888;font-size:.82rem;margin-bottom:16px}
.list{display:flex;flex-direction:column;gap:8px}
.item{background:#fff;border-radius:12px;padding:12px 16px;display:flex;align-items:center;gap:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.item-icon{font-size:1.3rem}
.item-info{flex:1}
.item-name{font-weight:600;font-size:.9rem}
.item-desc{color:#888;font-size:.8rem}
.tag{font-size:.7rem;padding:2px 8px;border-radius:8px;background:#27ae6022;color:#27ae60}
.tag-new{background:#4a7dff22;color:#4a7dff}
.footer{text-align:center;color:#999;font-size:.78rem;margin-top:20px}
a{color:#4a7dff;text-decoration:none}
</style></head><body>
<h1>🧩 扩展管理</h1>
<p class="sub">已安装功能 · 共12项</p>
<div class="list">
<div class="item"><div class="item-icon">🏠</div><div class="item-info"><div class="item-name">辨证食疗</div><div class="item-desc">首页核心功能</div></div><span class="tag">内置</span></div>
<div class="item"><div class="item-icon">🌀</div><div class="item-info"><div class="item-name">物态人论</div><div class="item-desc">相变理论 · 冰水火超临界</div></div><span class="tag">内置</span></div>
<div class="item"><div class="item-icon">🔍</div><div class="item-info"><div class="item-name">界面查询</div><div class="item-desc">SymMap中西医关联</div></div><span class="tag">内置</span></div>
<div class="item"><div class="item-icon">🌀</div><div class="item-info"><div class="item-name">五运六气</div><div class="item-desc">本地推算引擎</div></div><span class="tag">内置</span></div>
<div class="item"><div class="item-icon">🥣</div><div class="item-info"><div class="item-name">食疗评价</div><div class="item-desc">五维评分</div></div><span class="tag">内置</span></div>
<div class="item"><div class="item-icon">📖</div><div class="item-info"><div class="item-name">哲思文库</div><div class="item-desc">102条SEP全文</div></div><span class="tag">内置</span></div>
<div class="item"><div class="item-icon">📜</div><div class="item-info"><div class="item-name">经典古籍</div><div class="item-desc">素问灵枢</div></div><span class="tag">内置</span></div>
<div class="item"><div class="item-icon">🧙</div><div class="item-info"><div class="item-name">玄学管家</div><div class="item-desc">七套术数引擎</div></div><span class="tag tag-new">NEW</span></div>
<div class="item"><div class="item-icon">🎴</div><div class="item-info"><div class="item-name">八字排盘</div><div class="item-desc">CLI: bazi</div></div><span class="tag tag-new">NEW</span></div>
<div class="item"><div class="item-icon">🔮</div><div class="item-info"><div class="item-name">小六壬起卦</div><div class="item-desc">CLI: xiaoliuren</div></div><span class="tag tag-new">NEW</span></div>
<div class="item"><div class="item-icon">📚</div><div class="item-info"><div class="item-name">哲思MCP</div><div class="item-desc">CLI: phil</div></div><span class="tag tag-new">NEW</span></div>
<div class="item"><div class="item-icon">🏛️</div><div class="item-info"><div class="item-name">道归3.0文库</div><div class="item-desc">体系全貌</div></div><span class="tag tag-new">NEW</span></div>
</div>
<div class="footer"><a href="/tools">← 返回工具台</a></div>
</body></html>"""

def steward_page():
    from flask import redirect
    return redirect('/tools')
