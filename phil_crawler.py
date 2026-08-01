#!/usr/bin/env python3
"""
道归 · 哲学爬虫
每天自动补充东西方哲学内容
一天扒 10 篇 SEP + 2 部中国经典
"""

import json, os, re, urllib.request, time, sys

BASE = os.path.dirname(os.path.abspath(__file__))
# 直接写小站的数据文件，爬完即用
SEP_FILE = os.path.join(BASE, 'data', 'sep_core.json')
PHIL_DIR = os.path.join(BASE, 'phil_texts')
LOG_FILE = os.path.join(BASE, 'seplib', 'crawl_log.json')

os.makedirs(os.path.join(BASE, 'seplib'), exist_ok=True)
os.makedirs(PHIL_DIR, exist_ok=True)

def log(msg):
    print(f"[{time.strftime('%H:%M')}] {msg}", flush=True)

# ===== SEP 待抓列表 =====
SEP_QUEUE = [
    # 古希腊
    ("heraclitus", "赫拉克利特"), ("parmenides", "巴门尼德"), ("epicurus", "伊壁鸠鲁"),
    ("stoicism", "斯多葛主义"), ("plotinus", "普罗提诺"),
    # 近代哲学
    ("locke", "洛克"), ("berkeley", "贝克莱"), ("hume", "休谟"),
    ("leibniz", "莱布尼茨"), ("spinoza", "斯宾诺莎"),
    ("rousseau", "卢梭"), ("schopenhauer", "叔本华"),
    # 现代哲学
    ("heidegger", "海德格尔"), ("wittgenstein", "维特根斯坦"),
    ("rawls", "罗尔斯"), ("foucault", "福柯"), ("derrida", "德里达"),
    ("camus", "加缪"), ("popper", "波普尔"), ("adorno", "阿多诺"),
    ("habermas", "哈贝马斯"), ("quine", "奎因"),
    # 新增 —— 时间、死亡、爱、记忆…
    ("time", "时间哲学"), ("death", "死亡"), ("love", "爱之哲学"),
    ("memory", "记忆"), ("imagination", "想象力"),
    ("identity-personal", "人格同一性"), ("life-meaning", "生命意义"),
    ("ethics-ai", "AI伦理"), ("chinese-phil", "中国哲学"),
    ("determinism-causal", "决定论"), ("moral-relativism", "道德相对主义"),
    ("science-philosophy", "科学哲学"), ("language-philosophy", "语言哲学"),
    ("religion-philosophy", "宗教哲学"),
    # 专题
    ("metaethics", "元伦理学"),
    ("political-philosophy", "政治哲学"), ("aesthetics", "美学"),
    ("pragmatism", "实用主义"),
    ("utilitarianism", "功利主义"), ("nihilism", "虚无主义"),
]

# ===== 中国经典列表 =====
CHINESE_CLASSICS = [
    ("诗经", "shijing"),
    ("尚书", "shangshu"),
    ("礼记", "liji"),
    ("周易", "zhouyi"),
    ("春秋", "chunqiu"),
    ("大学", "daxue"),
    ("中庸", "zhongyong"),
    ("墨子", "mozi"),
    ("韩非子", "hanfeizi"),
    ("孙子兵法", "sunzi"),
]

def fetch_sep(slug, name):
    """抓一篇 SEP 条目"""
    url = f"https://plato.stanford.edu/entries/{slug}/"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'PhilosophyBot/1.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode('utf-8', errors='ignore')
        tm = re.search(r'<title>([^<]+)', html)
        paras = re.findall(r'<p[^>]*>([^<]{50,})</p>', html)
        body = '\n\n'.join(p.strip() for p in paras[:10])
        return {'name': name, 'title': tm.group(1)[:80] if tm else name, 'body': body[:3000]}
    except Exception as e:
        return None

def load_sep():
    try:
        with open(SEP_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_sep(lib):
    with open(SEP_FILE, 'w', encoding='utf-8') as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)

def crawl_sep(daily_limit=999):
    """每天扒 daily_limit 篇 SEP"""
    lib = load_sep()
    crawled = 0
    for slug, name in SEP_QUEUE:
        if slug in lib:
            continue
        if crawled >= daily_limit:
            break
        log(f"SEP: {name}...")
        entry = fetch_sep(slug, name)
        if entry:
            lib[slug] = entry
            crawled += 1
            log(f"  ✅ {name}")
        else:
            log(f"  ❌ {name}")
        time.sleep(1.5)  # 礼貌间隔
    
    save_sep(lib)
    log(f"SEP: 今日新增 {crawled} 篇，共 {len(lib)} 篇")
    return crawled

def crawl_chinese(daily_limit=2):
    """每天扒 daily_limit 部中国经典（占位，待接入古登堡或 GitHub 数据源）"""
    log(f"中国经典: 待扩展数据源")
    return 0

if __name__ == '__main__':
    log("=" * 30)
    log("哲学爬虫启动")
    sep_count = crawl_sep(999)
    ch_count = crawl_chinese(2)
    log(f"今日完成: SEP {sep_count} 篇 + 中国经典 {ch_count} 部")
    log("=" * 30)

# ===== 自动发现模式：爬完队列后自动找新条目 =====
AUTO_KEYWORDS = [
    "trust", "cooperation", "game", "social", "political", "justice",
    "rights", "freedom", "democracy", "equality", "power", "authority",
    "mind", "consciousness", "cognition", "perception", "knowledge",
    "science", "information", "technology", "reason", "logic",
    "ethics", "moral", "value", "virtue", "good", "evil",
    "emotion", "feeling", "passion", "desire", "will",
    "identity", "self", "person", "agency", "action",
    "language", "meaning", "truth", "reality", "existence",
    "history", "culture", "society", "community", "institution",
    "evolution", "biology", "life", "death", "nature",
    "religion", "god", "faith", "reason", "spirit",
]

def discover_new_slugs(existing_slugs, max_new=200):
    """从 SEP 目录页发现新条目"""
    url = "https://plato.stanford.edu/contents.html"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')
        # 提取所有 /entries/xxx/ 链接
        slugs = set(re.findall(r'/entries/([a-z0-9-]+)/', html))
        # 过滤掉已存在的
        new = [s for s in slugs if s not in existing_slugs and len(s) > 2]
        # 按关键词排序——有关键词匹配的优先
        def priority(slug):
            words = slug.replace('-', ' ')
            return -sum(1 for kw in AUTO_KEYWORDS if kw in words), slug
        new.sort(key=priority)
        log(f"发现 {len(new)} 个可抓取的新条目")
        return new[:max_new]
    except Exception as e:
        log(f"自动发现失败: {e}")
        return []

def crawl_auto(lib, batch_size=999):
    """自动模式：从 SEP 目录发现并抓取新的条目"""
    existing = set(lib.keys())
    new_slugs = discover_new_slugs(existing, max_new=200)
    if not new_slugs:
        log("没有新条目需要抓取")
        return 0
    
    crawled = 0
    for slug in new_slugs:
        if slug in lib:
            continue
        if crawled >= batch_size:
            break
        # 跳过已知会404的
        if slug in ('ethics', 'science', 'feminism', 'philosophy', 'love', 'death', 'meaning'):
            continue
        log(f"自动发现: {slug}...")
        url = f"https://plato.stanford.edu/entries/{slug}/"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=8)
            html = resp.read().decode('utf-8', errors='ignore')
            if '<title>Document Not Found</title>' in html or 'Not Yet Available' in html:
                log(f"  ❌ {slug}: 不可用")
                continue
            tm = re.search(r'<title>([^<]+)', html)
            ps = re.findall(r'<p[^>]*>([^<]{30,})</p>', html)
            body = '\n'.join(p.strip() for p in ps[:15])[:5000]
            if len(body) < 100:
                log(f"  ❌ {slug}: 内容过短")
                continue
            lib[slug] = {
                'name': slug.replace('-', ' ').title(),
                'title': tm.group(1)[:100] if tm else slug,
                'body': body
            }
            crawled += 1
            log(f"  ✅ {slug} ({len(body)}字)")
        except:
            log(f"  ❌ {slug}")
        time.sleep(2)
    
    return crawled


# 修改主流程：队列抓完后进入自动发现模式
if __name__ == '__main__':
    log("=" * 30)
    log("哲学爬虫 · 自动发现模式")
    lib = load_sep()
    
    # 第一阶段：队列抓取
    sep_count = crawl_sep(999)
    
    # 第二阶段：自动发现
    if sep_count < 10:
        auto_count = crawl_auto(lib, batch_size=999)
        sep_count += auto_count
    
    save_sep(lib)
    ch_count = crawl_chinese(2)
    log(f"今日完成: SEP {sep_count} 篇 + 自动发现 + 中国经典 {ch_count} 部")
    log(f"文库总计: {len(lib)} 条")
    log("=" * 30)
