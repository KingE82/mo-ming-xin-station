#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 解读服务：诗词 / 术数盘面 → DeepSeek 深度分析
统一封装，供小站各页面调用
"""
import os
import sys
import json
import http.client

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)


def _get_deepseek_key():
    """从 OpenClaw 密钥库读 DeepSeek key"""
    import sqlite3
    db = sqlite3.connect(os.path.expanduser("~/.openclaw/agents/main/agent/openclaw-agent.sqlite"))
    row = db.execute("SELECT store_json FROM auth_profile_store LIMIT 1").fetchone()
    d = json.loads(row[0])
    return d.get('profiles', {}).get('deepseek:default', {}).get('key', '')


# 不同场景的系统提示词
PROMPTS = {
    "poetry": """你是诗词鉴赏专家。对用户提供的诗词进行深度赏析：
1. 先给出核心主题一句话概括
2. 拆解意象与手法（用典、对仗、虚实等）
3. 结合诗人背景与创作心境
4. 点出这首诗的独特价值或与你的人生共鸣
要求：有洞察力，不堆砌术语，像一位懂诗的老友在解读""",

    "poetry_detail": """你是深谙中国古典文学的诗词专家。用户会提供一首诗词（含标题、作者、全文）。请输出一份完整的"诗词详情档案"，格式如下：

【作者生平】
概述作者的生平（约100-150字）：朝代、身份、主要经历、仕途/命运起伏、在文学史上的地位。若作者信息不可考（如佚名/诗经），则说明出处背景。

【写作背景】
这首诗的创作背景（约80-120字）：写于何时何地、当时作者处境与心境、与什么事件/人物相关。若史料无明确记载，则基于诗风与内容给出合理推测，并注明是推测。

【全诗赏析】
1. 核心主题：一句话概括
2. 意象与手法：拆解关键意象、用典、对仗、虚实等
3. 情感脉络：诗中情感的起伏与转折
4. 当代回响：这首诗在今天读来有什么意义，或与你的人生有何共鸣

要求：严谨有据、洞察深刻、不堆砌术语，像一位懂诗的老友娓娓道来。""",

    "jyotish": """你是精通印度占星（Jyotish）的命理分析师。对用户提供的印占盘面进行分析：
1. 先概述命盘整体格局（主要星曜落宫、宫主星）
2. 重点分析命宫/财帛/事业/婚姻/健康等关键宫位
3. 指出有利与需要注意的相位或格局
4. 给出可操作的人生建议
要求：专业但通俗，结合现代生活语境，不恐吓不迷信""",

    "bazi": """你是精通八字命理的命理师。对用户提供的八字排盘进行分析：
1. 先解读日主强弱与五行平衡
2. 分析格局（正官格/财格/食伤格等）
3. 看大运流年趋势
4. 结合性格特征给出人生建议
要求：专业、结构清晰，用现代语言解释命理概念""",

    "ziwei": """你是精通紫微斗数的命理分析师。对用户提供的紫微盘进行分析：
1. 先概述命宫主星格局（如紫微独坐/廉贞贪狼等）
2. 分析三方四正的星曜组合
3. 看四化（化禄/化权/化科/化忌）的落点
4. 结合十二宫位给出人生各领域建议
要求：专业准确，指出关键格局如火贪格、杀破狼等""",

    "qimen": """你是精通奇门遁甲的预测师。对用户提供的奇门盘进行分析：
1. 先确定用神与落宫
2. 分析值符值使、八门九星格局
3. 判断吉凶成败趋势
4. 给出行动建议（何时何方向有利）
要求：专业、实用，结合现代生活场景解释""",

    "liuyao": """你是精通六爻纳甲的预测师。对用户提供的卦象进行分析：
1. 先定用神与世应
2. 分析动爻、变卦、六亲关系
3. 判断吉凶与应期
4. 给出具体建议
要求：专业、清晰，用现代语言解释""",

    "liuren": """你是精通大六壬的预测师。对用户提供的课体进行分析：
1. 先定三传与课体（贼克/比用/涉害等）
2. 分析四课、天将、神煞
3. 判断事情的吉凶发展
4. 给出行动建议
要求：专业、严谨，结合现代场景解读""",

    "meihua": """你是精通梅花易数的占卜师。对用户提供的卦象进行分析：
1. 先解读本卦/互卦/变卦的体用关系
2. 分析五行生克与卦象含义
3. 结合所问之事断吉凶
4. 给出建议
要求：专业、灵活，语言亲切""",

    "xuanxue_general": """你是精通中国传统术数的分析师。对用户提供的排盘结果进行分析：
1. 先概述整体格局
2. 分析关键要素（星曜/干支/卦象）
3. 指出吉凶趋势
4. 给出人生建议
要求：专业、客观，结合现代生活语境""",
}


def ai_read(text, scene="xuanxue_general", max_len=6000):
    """AI 解读：text=原始结果, scene=场景, 返回解读文本"""
    prompt = PROMPTS.get(scene, PROMPTS["xuanxue_general"])
    key = _get_deepseek_key()
    if not key:
        return "AI 解读暂不可用（无 API key）"

    # 截断过长输入
    text = text[:max_len]
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"以下是{scene}结果，请分析：\n\n{text}"},
        ],
        "temperature": 0.6,
        "max_tokens": 3000,
    })

    conn = http.client.HTTPSConnection("api.deepseek.com", timeout=90)
    conn.request("POST", "/chat/completions", body=payload,
                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    resp = conn.getresponse()
    body = json.loads(resp.read().decode())
    conn.close()

    if resp.status == 200:
        return body['choices'][0]['message']['content']
    return f"AI 解读失败: {body.get('error', {}).get('message', 'unknown')}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 ai_reader.py <文本> [场景]")
        sys.exit(1)
    scene = sys.argv[2] if len(sys.argv) > 2 else "xuanxue_general"
    result = ai_read(sys.argv[1], scene)
    print(result)
