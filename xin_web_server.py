#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心哥 · 辨证食疗 + 五运六气 + 中医知识小站 v2
莫名心的小站，今儿又胖了一圈
"""

import json
import os
import sys
import html
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote
from datetime import date

# 锻因缘引擎
import forge_engine

# 导入诊断引擎
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xin_claw_doctor import differentiate, get_dietary_plan, get_treatment_plan, nature_to_phase, assess_risk
from xin_claw_doctor import get_western_advice as wm_advice

# 五运六气引擎路径（插件库 — 全量数据）
WY_DIR = os.path.expanduser("~/.openclaw/plugin-skills/wuyun-liuqi")
WY_SCRIPTS = os.path.join(WY_DIR, "scripts")
WY_LIB = os.path.join(WY_SCRIPTS, "lib")
for p in [WY_SCRIPTS, WY_LIB]:
    if os.path.isdir(p):
        sys.path.insert(0, p)

# 本地五运六气模块（纯本地，兜底用）
_本地目录 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _本地目录)


def _本地五运六气(date_str: str) -> dict:
    """用本地模块计算结果，构造兼容前端的格式"""
    from 五运六气 import 推算
    r = 推算(date_str)
    年 = int(r["日期"][:4])
    岁 = r["岁运"]
    当 = r["当前"]

    # 客气步编号：初之气→1
    步序号 = {"初之气": 1, "二之气": 2, "三之气": 3, "四之气": 4, "五之气": 5, "终之气": 6}
    步relation_map = {}
    for 步 in r["客气六步"]:
        z, k = 步["主气"], 步["客气"]
        if z == k:
            步relation_map[步["时段"]] = "客主同气"
        elif z in ["厥阴风木"] and k in ["少阴君火"]:
            步relation_map[步["时段"]] = "主生客"
        elif k in ["厥阴风木"] and z in ["少阴君火"]:
            步relation_map[步["时段"]] = "客生主"
        else:
            步relation_map[步["时段"]] = "顺"

    # 解析区间 "7月22日 → 9月23日" 为起止日期
    def _解析区间(区间str, 基准年=年):
        parts = 区间str.split("→")
        def _转日期(s):
            s = s.strip()
            m = s.split("月")[0]
            d = s.split("月")[1].replace("日", "")
            return f"{基准年:04d}-{int(m):02d}-{int(d):02d}"
        start = _转日期(parts[0])
        end_parts = parts[1].strip().split("月")
        end_m = int(end_parts[0])
        end_d = int(end_parts[1].replace("日", ""))
        # 跨年（终之气11月→1月）
        end_year = 基准年 + 1 if end_m == 1 else 基准年
        end = f"{end_year:04d}-{end_m:02d}-{end_d:02d}"
        return start, end

    当前start, 当前end = _解析区间(当["区间"])

    return {
        "success": True,
        "date": r["日期"],
        "yunqi_year": 岁["年份"],
        "year_gz": r["干支"],
        "day_gz": "——",
        "shengxiao": {"子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔", "辰": "龙",
                       "巳": "蛇", "午": "马", "未": "羊", "申": "猴", "酉": "鸡",
                       "戌": "狗", "亥": "猪"}.get(r["地支"], ""),
        "sui_yun": {
            "name": 岁["岁运"] + "运",
            "element": 岁["岁运"],
            "status": 岁["太过不及"],
            "tiangan": 岁["天干"],
        },
        "si_tian": r["司天"],
        "zai_quan": r["在泉"],
        "current_step": {
            "step_number": 步序号.get(当["时段"], 0),
            "name": 当["时段"] + "(主" + 当["区间"] + ")",
            "zhu_qi": 当["主气"],
            "ke_qi": 当["客气"],
            "relation": 步relation_map.get(当["时段"], ""),
            "shun_ni": "相得（顺）",
            "date_range": {"start": 当前start, "end": 当前end},
            "keqi_is_sitian": 当["客气"] == r["司天"],
            "keqi_is_zaiquan": 当["客气"] == r["在泉"],
        },
        "ke_zhu_jia_lin": [
            {
                "step_number": 步序号[步["时段"]],
                "zhu_qi": 步["主气"],
                "ke_qi": 步["客气"],
                "relation": 步relation_map.get(步["时段"], ""),
                "shun_ni": "相得（顺）",
                "keqi_is_sitian": 步["客气"] == r["司天"],
                "keqi_is_zaiquan": 步["客气"] == r["在泉"],
            }
            for 步 in r["客气六步"]
        ],
        "ke_qi_six_steps": [
            {
                "step": 步序号[步["时段"]],
                "ke_qi": 步["客气"],
                "is_sitian": 步["客气"] == r["司天"],
                "is_zaiquan": 步["客气"] == r["在泉"],
            }
            for 步 in r["客气六步"]
        ],
        "tong_hua": {"tianfu": False, "suihui": False, "taiyi_tianfu": False, "pingqi": False},
        "zhu_yun": [],
        "ke_yun": [],
        "jieqi_dates": [],
    }


def get_yunqi_data(date_str=None):
    """获取五运六气数据。插件优先，本地模块兜底。"""
    if date_str is None:
        date_str = date.today().isoformat()

    # 方案 A：插件库（全量数据，含日干支/主客运/同化等）
    try:
        from calculate_yunqi_api import calculate_yunqi_api
        result = calculate_yunqi_api(date_str)
        return {
            'success': True,
            'date': result['date'],
            'yunqi_year': result['yunqi_year'],
            'year_gz': result['year_gz'],
            'day_gz': result['day_gz'],
            'shengxiao': result['shengxiao'],
            'sui_yun': result['sui_yun'],
            'si_tian': result['si_tian'],
            'zai_quan': result['zai_quan'],
            'current_step': result['current_step'],
            'tong_hua': result['tong_hua'],
            'zhu_yun': result['zhu_yun'],
            'ke_yun': result['ke_yun'],
            'ke_qi_six_steps': result['ke_qi_six_steps'],
            'ke_zhu_jia_lin': result['ke_zhu_jia_lin'],
            'jieqi_dates': result['jieqi_dates'],
        }
    except Exception:
        pass  # 插件不可用，走本地

    # 方案 B：本地模块
    try:
        return _本地五运六气(date_str)
    except Exception as e:
        return {'success': False, 'error': f'五运六气计算失败: {str(e)}'}

PORT = 8080

# ═══════════════════════════════════════════
# HTML 前端（内置，单文件）
# ═══════════════════════════════════════════

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>莫名心 · 中医小站</title>
<style>
:root {
  --bg: #f5f0eb;
  --card: #ffffff;
  --text: #2c2c2c;
  --text-light: #5a5a5a;
  --accent: #b8453a;
  --accent-light: #e8d5d0;
  --green: #4a7c59;
  --blue: #3a5a7c;
  --gold: #c9a84c;
  --tab-bg: #ddd4c8;
  --radius: 14px;
  --shadow: 0 2px 12px rgba(0,0,0,0.06);

/* 深色主题（全量覆盖） */
body.dark-theme {
  --bg: #16161a;
  --card: #1e1e24;
  --text: #ece8dc;
  --text-light: #b0a898;
  --accent: #d86050;
  --accent-light: #3a2824;
  --green: #5a9a6a;
  --blue: #5a8aba;
  --gold: #d0b050;
  --tab-bg: #2a2a30;
  --shadow: 0 2px 12px rgba(0,0,0,0.3);
}
body.dark-theme .symptom-item:hover { background: #2a2a30 !important; }
body.dark-theme .tag { background: #2a2a30; border-color: #3a3a40; }
body.dark-theme .tag.selected { background: #3a2824; border-color: #d86050; }
body.dark-theme .tag-small { background: #2a2a30; border-color: #3a3a40; }
body.dark-theme .recipe-card { background: #222228; }
body.dark-theme .yunqi-item { background: #222228; }
body.dark-theme .yunqi-header { background: linear-gradient(135deg, #2a3a4a, #1e2a36); }
body.dark-theme .step-card { background: #222228; }
body.dark-theme .tx-item { border-bottom-color: #2a2a30; }
body.dark-theme .error-msg { background: #2a1818; color: #d86050; }
body.dark-theme .card { border: 1px solid #2a2a30; }
body.dark-theme .herb-tag { background: var(--green); }
body.dark-theme .avoid-tag { background: #2a2018; color: #c07050; }
body.dark-theme .acupoint { background: var(--blue); }
body.dark-theme .custom-input input { background: #222228; border-color: #3a3a40; color: var(--text); }
body.dark-theme textarea { background: #222228; border-color: #3a3a40 !important; color: var(--text); }
body.dark-theme input[type="number"] { background: #222228; border-color: #3a3a40; color: var(--text); }
body.dark-theme select { background: #222228; border-color: #3a3a40; color: var(--text); }
body.dark-theme #westernAdviceCard { border-color: var(--blue) !important; }
body.dark-theme .kw-cat { background: #222228; }
body.dark-theme .kw-cat:hover { background: #2a2a30; }
body.dark-theme .date-input-row input { background: #222228; border-color: #3a3a40; color: var(--text); }
body.dark-theme .footer { color: #5a5a5a; }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, 'PingFang SC', 'Noto Sans SC', sans-serif;
  background: var(--bg);
  color: var(--text);
  padding: 16px;
  max-width: 640px;
  margin: 0 auto;
  min-height: 100vh;
}

/* 导航 */
.header {
  text-align: center;
  padding: 20px 0 12px;
}
.header h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 1px;
}
.header .sub {
  font-size: 13px;
  color: #5a5a5a;
  margin-top: 4px;
}
.tabs {
  display: flex;
  gap: 4px;
  background: var(--tab-bg);
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 16px;
}
.tab {
  flex: 1;
  text-align: center;
  padding: 10px 8px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  color: #5a5a5a;
  user-select: none;
}
.tab.active {
  background: var(--card);
  color: var(--text);
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.tab:hover:not(.active) { color: var(--text); }
.tab-content { display: none; }

.tab-content.active { display: block; }

/* 通用卡片 */
.card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 16px;
  box-shadow: var(--shadow);
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.symptom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
}
.symptom-section {
  grid-column: 1 / -1;
  font-size: 12px;
  font-weight: 600;
  color: #5a5a5a;
  letter-spacing: 1px;
  padding: 6px 0 2px;
  margin-top: 4px;
  border-bottom: 1px solid #f0ebe6;
}
.symptom-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  user-select: none;
}
.symptom-item:hover { background: #f0ebe6; }
.symptom-item input { accent-color: var(--accent); width: 16px; height: 16px; }
.custom-input {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.custom-input input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
  transition: border 0.2s;
}
.custom-input input:focus { border-color: var(--accent); }
.custom-input button {
  padding: 10px 16px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}
.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag {
  padding: 8px 14px;
  border-radius: 20px;
  font-size: 14px;
  cursor: pointer;
  border: 1.5px solid #ddd;
  background: white;
  transition: all 0.15s;
  user-select: none;
}
.tag.selected {
  background: var(--accent-light);
  border-color: var(--accent);
  color: var(--accent);
}
.tag-small {
  padding: 4px 12px;
  font-size: 13px;
  border-radius: 14px;
  border: 1px solid #e0d8d2;
  background: #faf7f4;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.btn-primary {
  width: 100%;
  padding: 14px;
  background: var(--accent);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-primary:active { opacity: 0.8; }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

/* 结果区 */
.result-section { display: none; }
.result-section.visible { display: block; }
.result-header {
  background: var(--accent);
  color: white;
  border-radius: var(--radius);
  padding: 18px 20px;
  margin-bottom: 12px;
}
.result-header .dx-name { font-size: 20px; font-weight: 700; }
.result-header .dx-sub { font-size: 13px; opacity: 0.85; margin-top: 4px; }
.section-block { margin-bottom: 14px; }
.section-block .label {
  font-size: 12px;
  font-weight: 600;
  color: #5a5a5a;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 6px;
}
.herb-tag {
  display: inline-block;
  padding: 6px 14px;
  background: var(--green);
  color: white;
  border-radius: 20px;
  font-size: 13px;
  margin: 3px 4px 3px 0;
}
.avoid-tag {
  display: inline-block;
  padding: 6px 14px;
  background: #f0e0d8;
  color: #a0523a;
  border-radius: 20px;
  font-size: 13px;
  margin: 3px 4px 3px 0;
}
.recipe-card {
  background: #faf7f4;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
  font-size: 14px;
}
.acupoint-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.acupoint {
  padding: 6px 14px;
  background: var(--blue);
  color: white;
  border-radius: 20px;
  font-size: 13px;
}
.tx-item {
  padding: 6px 0;
  font-size: 14px;
  line-height: 1.6;
  border-bottom: 1px solid #f0ebe6;
}
.tx-item:last-child { border: none; }
.loading {
  text-align: center;
  padding: 40px;
  color: #5a5a5a;
}
.loading .spinner {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid #eee;
  border-top: 3px solid var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg {
  background: #fef2f0;
  color: #b8453a;
  padding: 14px;
  border-radius: 10px;
  font-size: 14px;
}
.selected-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.selected-tags .tag-small .remove {
  cursor: pointer;
  margin-left: 4px;
  opacity: 0.6;
}
.selected-tags .tag-small .remove:hover { opacity: 1; }

/* 五运六气专用样式 */
.yunqi-header {
  background: linear-gradient(135deg, #3a5a7c, #2d4a66);
  color: white;
  border-radius: var(--radius);
  padding: 18px 20px;
  margin-bottom: 12px;
}
.yunqi-header .date { font-size: 13px; opacity: 0.8; }
.yunqi-header .gz { font-size: 24px; font-weight: 700; margin: 4px 0; }
.yunqi-header .year-info { font-size: 14px; opacity: 0.9; }
.yunqi-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.yunqi-item {
  background: #faf7f4;
  border-radius: 10px;
  padding: 12px;
  text-align: center;
}
.yunqi-item .label { font-size: 11px; color: #5a5a5a; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
.yunqi-item .value { font-size: 16px; font-weight: 600; }
.yunqi-item .value.accent { color: var(--accent); }
.yunqi-item .value.green { color: var(--green); }
.yunqi-item .value.blue { color: var(--blue); }
.yunqi-item .value.gold { color: var(--gold); }
.step-card {
  background: #f0ebe6;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 8px;
}
.step-card .step-title { font-weight: 600; font-size: 14px; }
.step-card .step-detail { font-size: 13px; color: #5a5a5a; margin-top: 4px; }
.date-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.date-input-row input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
}
.date-input-row input:focus { border-color: var(--blue); }
.date-input-row button {
  padding: 10px 20px;
  background: var(--blue);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}

/* 倪海厦知识 */
.kw-search-row {
  display: flex;
  gap: 8px;
}
.kw-search-row input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 10px;
  font-size: 14px;
  outline: none;
}
.kw-search-row input:focus { border-color: var(--green); }
.kw-search-row button {
  padding: 10px 20px;
  background: var(--green);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  font-weight: 500;
}
.kw-categories {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
}
.kw-cat {
  text-align: center;
  padding: 10px;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
  background: #faf7f4;
  transition: background 0.2s;
}
.kw-cat:hover { background: #e8ddd6; }
.kw-cat .cat-icon { font-size: 20px; display: block; margin-bottom: 4px; }

/* 通用 */
.footer {
  text-align: center;
  font-size: 12px;
  color: #5a5a5a;
  padding: 20px 0;
}
@media (max-width: 420px) {
  .symptom-grid { grid-template-columns: 1fr 1fr; }
  .yunqi-grid { grid-template-columns: 1fr; }
  .kw-categories { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 380px) {
  body { padding: 10px; }
  .header h1 { font-size: 19px; }
  .tab { font-size: 12px; padding: 8px 4px; }
  .card { padding: 14px; border-radius: 12px; }
  .symptom-item { font-size: 13px; padding: 6px; }
  .tag { font-size: 13px; padding: 6px 12px; }
}

/* 增大触摸区域 - 移动端友好 */
button, .tab, .tag, .symptom-item, .kw-cat { cursor: pointer; -webkit-tap-highlight-color: transparent; }
input, select, textarea { font-size: 16px !important; } /* 防止iOS自动缩放 */

/* Toast 通知 */
.toast-container {
  position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
  z-index: 9999; display: flex; flex-direction: column; gap: 8px;
  pointer-events: none; max-width: 360px; width: 90%;
}
.toast {
  background: var(--card); color: var(--text);
  padding: 12px 18px; border-radius: 12px;
  font-size: 14px; line-height: 1.5;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  animation: toastIn 0.25s ease-out;
  display: flex; align-items: center; gap: 8px;
  pointer-events: auto;
}
.toast.toast-error { border-left: 3px solid #d86050; }
.toast.toast-success { border-left: 3px solid var(--green); }
.toast.toast-info { border-left: 3px solid var(--blue); }
@keyframes toastIn {
  from { opacity: 0; transform: translateY(-12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 暗色模式开关样式 */
.theme-toggle {
  position: fixed; bottom: 20px; right: 20px;
  width: 44px; height: 44px;
  border-radius: 50%;
  background: var(--card);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  font-size: 20px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
  padding: 0;
}
.theme-toggle:hover { transform: scale(1.1); }
body.dark-theme .theme-toggle { border-color: #3a3a40; }

/* Tab 切换淡入 */
.tab-content { display: none; }
.tab-content.active {
  display: block;
  animation: tabFadeIn 0.2s ease-out;
}
@keyframes tabFadeIn {
  from { opacity: 0.4; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 更好的 loading */
.loading {
  text-align: center; padding: 40px 20px;
  font-size: 14px; color: var(--text-light);
}
.spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--tab-bg);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin: 0 auto 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Tab 控制 - 使用属性选择器达到最高优先级 */
/* tab-content display controlled by JS inline styles */
</style>
</head>
<body>

<div class="header">
  <h1>🌙 莫名心 · 中医小站</h1>
  <div class="sub">诊断 · 运气 · 经典 · 一个站就够了</div>
</div>

<!-- Toast 容器 -->
<div class="toast-container" id="toastContainer"></div>

<!-- 暗色模式开关 -->
<button class="theme-toggle" id="themeToggle" onclick="toggleDarkMode()" title="切换主题">🌙</button>

<!-- 导航标签 -->
<div class="tabs">
  <div class="tab active" onclick="switchTab('diagnose')">🩺 辨证食疗</div>
  <div class="tab" onclick="switchTab('yunqi')">🌀 五运六气</div>
  <div class="tab" onclick="switchTab('nihaisha')">📖 经典参考</div>
  <div class="tab" onclick="switchTab('phase')">🌀 物态人论</div>
  <div class="tab" onclick="switchTab('philosophy')">📖 哲思</div>
  <div class="tab" onclick="switchTab('ai')">🤖 AI 问答</div>
  <div class="tab" onclick="window.open('/daogui','_self')">🔥 道归文库</div>
</div>

<!-- ════════ TAB 1: 辨证食疗 ════════ -->
<div class="tab-content" id="tab-diagnose" style="display:block">
  <div id="inputArea">

    <!-- ====== 基础信息：年龄/身高/体重/性别 ====== -->
    <div class="card">
      <div class="card-title">👤 基础信息</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
        <div>
          <label style="font-size:13px;color:var(--text-light);">年龄</label>
          <input type="number" id="bioAge" placeholder="岁" min="0" max="150"
            style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-light);">性别</label>
          <select id="bioSex"
            style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;background:white;box-sizing:border-box;">
            <option value="">—</option>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-light);">身高 (cm)</label>
          <input type="number" id="bioHeight" placeholder="cm" min="50" max="250"
            style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-light);">体重 (kg)</label>
          <input type="number" id="bioWeight" placeholder="kg" min="10" max="400"
            style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;box-sizing:border-box;">
        </div>
      </div>
      <div style="margin-top:8px;font-size:12px;color:var(--text-light);" id="bmiDisplay"></div>
    </div>

    <!-- ====== 生活习惯（抽烟/饮酒/纵欲） ====== -->
    <div class="card">
      <div class="card-title">🚬 生活习惯</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:4px;">
        <div>
          <label style="font-size:13px;color:var(--text-light);">抽烟</label>
          <select id="bioSmoking"
            style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;background:white;box-sizing:border-box;">
            <option value="">—</option>
            <option value="从不">从不</option>
            <option value="偶尔">偶尔</option>
            <option value="每日<10支">每日 &lt;10支</option>
            <option value="每日10-20支">每日 10-20支</option>
            <option value="每日>20支">每日 &gt;20支</option>
            <option value="已戒">已戒</option>
          </select>
        </div>
        <div>
          <label style="font-size:13px;color:var(--text-light);">饮酒</label>
          <select id="bioAlcohol"
            style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;background:white;box-sizing:border-box;">
            <option value="">—</option>
            <option value="从不">从不</option>
            <option value="偶尔">偶尔社交</option>
            <option value="每周1-3次">每周 1-3次</option>
            <option value="每周>3次">每周 &gt;3次</option>
            <option value="每日">每日饮</option>
            <option value="已戒">已戒</option>
          </select>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:8px;">
        <div>
          <label style="font-size:12px;color:var(--text-light);">烟龄 (年)</label>
          <input type="number" id="bioSmokingYears" placeholder="年" min="0" max="80"
            style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:8px;font-size:13px;outline:none;box-sizing:border-box;">
        </div>
        <div>
          <label style="font-size:12px;color:var(--text-light);">酒龄 (年)</label>
          <input type="number" id="bioAlcoholYears" placeholder="年" min="0" max="80"
            style="width:100%;padding:8px 10px;border:1px solid #ddd;border-radius:8px;font-size:13px;outline:none;box-sizing:border-box;">
        </div>
      </div>
      <div style="margin-top:4px;">
        <label style="font-size:13px;color:var(--text-light);">房事劳损 / 节律</label>
        <select id="bioSexLife"
          style="width:100%;padding:10px 12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;background:white;box-sizing:border-box;">
          <option value="">—</option>
          <option value="正常">正常节律</option>
          <option value="频繁">偏频繁</option>
          <option value="过度">过度（可能有劳损）</option>
          <option value="节制">节欲/较少</option>
        </select>
      </div>
    </div>

    <!-- ====== 慢性病 + 家族病史 ====== -->
    <div class="card">
      <div class="card-title">📋 病史</div>
      <div style="margin-bottom:8px;">
        <label style="font-size:13px;color:var(--text-light);">个人慢性病/既往病史</label>
        <textarea id="bioHistory" rows="2"
          style="width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:14px;resize:vertical;font-family:inherit;outline:none;box-sizing:border-box;"
          placeholder="例如：高血压3年、2型糖尿病5年、慢性胃炎…"></textarea>
      </div>
      <div>
        <label style="font-size:13px;color:var(--text-light);">家族病史（直系亲属慢性病/遗传病）</label>
        <textarea id="bioFamilyHistory" rows="2"
          style="width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:14px;resize:vertical;font-family:inherit;outline:none;box-sizing:border-box;"
          placeholder="例如：父亲高血压、母亲糖尿病、祖父中风…"></textarea>
      </div>
      <div style="margin-top:6px;font-size:12px;color:var(--text-light);">💡 家族病史对遗传倾向评估很重要</div>
    </div>

    <div class="card">
      <div class="card-title">🫀 常见症状</div>
      <div class="symptom-grid" id="symptomGrid">
        <div class="symptom-section">❤️ 心系</div>
        <label class="symptom-item"><input type="checkbox" value="失眠"> 失眠</label>
        <label class="symptom-item"><input type="checkbox" value="嗜睡"> 嗜睡</label>
        <label class="symptom-item"><input type="checkbox" value="多梦"> 多梦</label>
        <label class="symptom-item"><input type="checkbox" value="心悸"> 心悸</label>
        <label class="symptom-item"><input type="checkbox" value="心烦"> 心烦</label>
        <label class="symptom-item"><input type="checkbox" value="胸闷"> 胸闷</label>
        <label class="symptom-item"><input type="checkbox" value="健忘"> 健忘</label>
        <div class="symptom-section">💚 肝系</div>
        <label class="symptom-item"><input type="checkbox" value="急躁易怒"> 急躁易怒</label>
        <label class="symptom-item"><input type="checkbox" value="情绪抑郁"> 情绪抑郁</label>
        <label class="symptom-item"><input type="checkbox" value="胁肋胀痛"> 胁肋胀痛</label>
        <label class="symptom-item"><input type="checkbox" value="头晕目眩"> 头晕目眩</label>
        <label class="symptom-item"><input type="checkbox" value="目赤"> 目赤</label>
        <label class="symptom-item"><input type="checkbox" value="手足麻木"> 手足麻木</label>
        <div class="symptom-section">🟡 脾系</div>
        <label class="symptom-item"><input type="checkbox" value="食欲不振"> 食欲不振</label>
        <label class="symptom-item"><input type="checkbox" value="消谷善饥"> 消谷善饥</label>
        <label class="symptom-item"><input type="checkbox" value="暴食"> 暴食</label>
        <label class="symptom-item"><input type="checkbox" value="腹胀"> 腹胀</label>
        <label class="symptom-item"><input type="checkbox" value="便溏"> 便溏</label>
        <label class="symptom-item"><input type="checkbox" value="便秘"> 便秘</label>
        <label class="symptom-item"><input type="checkbox" value="乏力"> 乏力</label>
        <div class="symptom-section">🤍 肺系</div>
        <label class="symptom-item"><input type="checkbox" value="咳嗽"> 咳嗽</label>
        <label class="symptom-item"><input type="checkbox" value="气喘"> 气喘</label>
        <label class="symptom-item"><input type="checkbox" value="气短"> 气短</label>
        <label class="symptom-item"><input type="checkbox" value="痰多"> 痰多</label>
        <label class="symptom-item"><input type="checkbox" value="自汗"> 自汗</label>
        <label class="symptom-item"><input type="checkbox" value="易感冒"> 易感冒</label>
        <div class="symptom-section">💙 肾系</div>
        <label class="symptom-item"><input type="checkbox" value="腰膝酸软"> 腰膝酸软</label>
        <label class="symptom-item"><input type="checkbox" value="畏寒"> 畏寒</label>
        <label class="symptom-item"><input type="checkbox" value="怕热"> 怕热</label>
        <label class="symptom-item"><input type="checkbox" value="五心烦热"> 五心烦热</label>
        <label class="symptom-item"><input type="checkbox" value="盗汗"> 盗汗</label>
        <label class="symptom-item"><input type="checkbox" value="夜尿多"> 夜尿多</label>
        <div class="symptom-section">🔘 全身/其他</div>
        <label class="symptom-item"><input type="checkbox" value="头痛"> 头痛</label>
        <label class="symptom-item"><input type="checkbox" value="口干"> 口干</label>
        <label class="symptom-item"><input type="checkbox" value="口苦"> 口苦</label>
        <label class="symptom-item"><input type="checkbox" value="面色淡白"> 面色淡白</label>
        <label class="symptom-item"><input type="checkbox" value="面色萎黄"> 面色萎黄</label>
        <label class="symptom-item"><input type="checkbox" value="浮肿"> 浮肿</label>
      </div>
      <div class="custom-input">
        <input type="text" id="customSymptom" placeholder="输入其他症状…" onkeydown="if(event.key==='Enter') addCustomSymptom()">
        <button onclick="addCustomSymptom()">添加</button>
      </div>
      <div class="selected-tags" id="customTags"></div>
    </div>

    <div class="card">
      <div class="card-title">💬 或者直接说说哪里不舒服</div>
      <textarea id="nlpInput" rows="3" style="width:100%;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:14px;resize:vertical;font-family:inherit;outline:none;box-sizing:border-box;" placeholder="例如：最近总睡不着，心慌，记性变差，还容易烦躁…"></textarea>
      <button class="btn-primary" id="nlpBtn" onclick="parseNLP()" style="margin-top:8px;background:var(--blue);font-size:14px;padding:10px;">🔍 自动识别症状</button>
      <div id="nlpResult" style="font-size:13px;color:var(--text-light);margin-top:6px;"></div>
    </div>

    <div class="card">
      <div class="card-title">👅 舌象</div>
      <div class="tag-group" id="tongueGroup">
        <span class="tag" data-val="舌淡">舌淡</span>
        <span class="tag" data-val="舌红">舌红</span>
        <span class="tag" data-val="舌暗">舌暗</span>
        <span class="tag" data-val="舌淡胖">舌淡胖</span>
        <span class="tag" data-val="舌红少苔">舌红少苔</span>
        <span class="tag" data-val="舌有齿痕">舌有齿痕</span>
        <span class="tag" data-val="舌苔白腻">舌苔白腻</span>
        <span class="tag" data-val="舌苔黄腻">舌苔黄腻</span>
        <span class="tag" data-val="舌苔薄白">舌苔薄白</span>
      </div>
    </div>

    <div class="card">
      <div class="card-title">🫘 脉象</div>
      <div class="tag-group" id="pulseGroup">
        <span class="tag" data-val="脉细">脉细</span>
        <span class="tag" data-val="脉数">脉数</span>
        <span class="tag" data-val="脉细数">脉细数</span>
        <span class="tag" data-val="脉弦">脉弦</span>
        <span class="tag" data-val="脉沉">脉沉</span>
        <span class="tag" data-val="脉弱">脉弱</span>
        <span class="tag" data-val="脉滑">脉滑</span>
        <span class="tag" data-val="脉浮">脉浮</span>
      </div>
    </div>
    <div style="font-size:12px;color:var(--text-light);margin-top:8px;">🔄 可多选</div>

    <button class="btn-primary" id="submitBtn" onclick="submitDiagnosis()">🩺 开始辨证 — 中医·西医·风险评估</button>
  </div>

  <div class="loading" id="loading">
    <div class="spinner"></div>
    <div>正在辨证…</div>
  </div>

  <div class="result-section" id="resultArea">

    <!-- ====== 风险预警区块（高危时显示） ====== -->
    <div id="riskAlerts" style="display:none;"></div>

    <div class="result-header" id="resultHeader">
      <div class="dx-name"></div>
      <div class="dx-sub"></div>
    </div>
    <div class="card"><div class="card-title">🥗 推荐食材</div><div id="herbTags"></div></div>
    <div class="card"><div class="card-title">🚫 忌口</div><div id="avoidTags"></div></div>
    <div class="card"><div class="card-title">🍲 食疗方</div><div id="recipeList"></div></div>
    <div class="card"><div class="card-title">📍 穴位按压</div><div id="acupointList"></div></div>
    <div class="card"><div class="card-title">📋 日常调护</div><div id="dailyCare"></div></div>
    <!-- ====== 西医建议区块 ====== -->
    <div class="card" id="westernAdviceCard" style="border-left:3px solid var(--blue);">
      <div class="card-title">💊 西医参考建议</div>
      <div id="westernAdviceContent"></div>
    </div>

    <div class="card"><div class="card-title">💚 情志与睡眠</div><div id="emotionCare"></div></div>
    <div class="card" id="traceCard">
      <details>
        <summary style="font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:8px;padding:4px 0;">
          🧠 推理路径 <span style="font-size:12px;font-weight:400;color:var(--text-light);margin-left:auto;">展开查看</span>
        </summary>
        <div id="traceContent" style="margin-top:12px;font-size:13px;line-height:1.7;"></div>
      </details>
    </div>
    <div class="card" id="knowledgeCard">
      <div class="card-title">🏛 知识图谱支撑</div>
      <div id="knowledgeInfo"></div>
    </div>
    <div class="card" id="errorCard">
      <div class="error-msg" id="errorMsg"></div>
    </div>
    <button class="btn-primary" onclick="resetAll()" style="background:var(--text-light)">🔄 重新辨证</button>
  </div>
</div>

<!-- ════════ TAB 2: 五运六气 ════════ -->
<div class="tab-content" id="tab-yunqi" style="display:none">
  <div class="card">
    <div class="card-title">📅 查询日期</div>
    <div class="date-input-row">
      <input type="date" id="yunqiDate">
      <button onclick="loadYunqi()">查询</button>
    </div>
    <div style="font-size:12px;color:var(--text-light);margin-top:6px;">💡 默认显示今天，也可选历史或未来日期</div>
  </div>

  <div class="loading" id="yunqiLoading">
    <div class="spinner"></div>
    <div>正在推算五运六气…</div>
  </div>

  <div id="yunqiResult">
    <div class="yunqi-header" id="yunqiHeader">
      <div class="date"></div>
      <div class="gz"></div>
      <div class="year-info"></div>
    </div>

    <div class="card"><div class="card-title">🎯 岁运格局</div>
      <div class="yunqi-grid" id="yunqiMainGrid"></div>
    </div>

    <div class="card"><div class="card-title">📌 当前步位</div>
      <div id="yunqiCurrentStep"></div>
    </div>

    <div class="card"><div class="card-title">🔄 客主加临六步</div>
      <div id="yunqiSteps"></div>
    </div>

    <div class="card" id="yunqiTonghua">
      <div class="card-title">🔗 运气同化</div>
      <div id="yunqiTonghuaContent"></div>
    </div>

    <div class="card" id="yunqiZhuKeYun">
      <div class="card-title">🏃 主运 / 客运</div>
      <div id="yunqiYunContent"></div>
    </div>

    <div class="card" id="yunqiErrorCard">
      <div class="error-msg" id="yunqiErrorMsg"></div>
    </div>
  </div>
</div>

<!-- ════════ TAB 3: 经典参考 ════════ -->
<div class="tab-content" id="tab-nihaisha" style="display:none">
  <div class="card">
    <div class="card-title">🔍 中医知识查询</div>
    <div class="kw-search-row">
      <input type="text" id="kwSearchInput" placeholder="搜索中药、方剂、证型、穴位…" onkeydown="if(event.key==='Enter') searchKnowledge()">
      <button onclick="searchKnowledge()">搜索</button>
    </div>
  </div>

  <div id="kwLoading" class="loading">
    <div class="spinner"></div>
    <div>搜索中…</div>
  </div>

  <div id="kwResult">
    <div class="card" id="kwResultCard">
      <div class="card-title">📚 查询结果</div>
      <div id="kwResultContent"></div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">📂 经典分类</div>
    <div class="kw-categories">
      <div class="kw-cat" onclick="quickSearch('伤寒论')">
        <span class="cat-icon">📜</span> 伤寒论
      </div>
      <div class="kw-cat" onclick="quickSearch('金匮要略')">
        <span class="cat-icon">📜</span> 金匮要略
      </div>
      <div class="kw-cat" onclick="quickSearch('神农本草')">
        <span class="cat-icon">🌿</span> 神农本草
      </div>
      <div class="kw-cat" onclick="quickSearch('黄帝内经')">
        <span class="cat-icon">☯️</span> 黄帝内经
      </div>
      <div class="kw-cat" onclick="quickSearch('针灸')">
        <span class="cat-icon">📍</span> 针灸大成
      </div>
      <div class="kw-cat" onclick="quickSearch('温病')">
        <span class="cat-icon">🔥</span> 温病条辨
      </div>
    </div>
  </div>

</div>

<!-- ════════ TAB 4: 物态人论 ════════ -->
<div class="tab-content" id="tab-phase" style="display:none">
  <div id="phaseContent">
    <div class="loading" id="phaseLoading">
      <div class="spinner"></div>
      <div>加载物态人论…</div>
    </div>
  </div>
</div>

<!-- ════════ TAB 5: 哲思 (SEP 哲学) ════════ -->
<div class="tab-content" id="tab-philosophy" style="display:none">
  <div id="philosophyContent">
    <div class="loading" id="philosophyLoading">
      <div class="spinner"></div>
      <div>加载哲思…</div>
    </div>
  </div>
</div>

  <div class="card" style="cursor:pointer;" onclick="toggleCollapse('notesWrap', this); if(!this._loaded){this._loaded=true;loadNotes();}">
    <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
      <span>📖 我们的笔记</span>
      <span id="notesArrow" style="font-size:12px;color:var(--text-light);transition:transform 0.2s;">▶</span>
    </div>
    <div id="notesWrap" class="collapse-wrap" style="display:none;margin-bottom:24px;">
      <div id="notesList" style="font-size:14px;line-height:1.6;">
        <div style="color:var(--text-light);">加载中…</div>
      </div>
    </div>
  </div>

  <div class="card" style="cursor:pointer;" onclick="toggleCollapse('crawledWrap', this); if(!this._loaded2){this._loaded2=true;loadCrawled();}">
    <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
      <span>🕷️ 求知虫</span>
      <span id="crawledArrow" style="font-size:12px;color:var(--text-light);transition:transform 0.2s;">▶</span>
    </div>
    <div id="crawledWrap" class="collapse-wrap" style="display:none;margin-bottom:24px;">
      <div id="crawledList" style="font-size:14px;line-height:1.6;">
        <div style="color:var(--text-light);">加载中…</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">📖 古籍资源</div>
    <div style="font-size:14px;line-height:1.8;">
      <div>📚 <strong>中医开源医典 (tcmoc)</strong> — 703部古籍整理中</div>
      <div style="font-size:12px;color:var(--text-light);margin:4px 0 8px 18px;">
        已收录《神农本草经》《伤寒论》《金匮要略》《黄帝内经》等30余部经典
      </div>
      <div>📖 <strong>王冰注本·黄帝内经素问</strong> — 50卷纯文本，可读可查</div>
      <div style="font-size:12px;color:var(--text-light);margin:4px 0 8px 18px;">
        正统道藏涵芬楼版，替代CTP乱码源
      </div>
      <div>🎓 <strong>倪海厦人纪课程</strong> — 伤寒·金匮·本草·针灸·内经</div>
      <div style="font-size:12px;color:var(--text-light);margin:4px 0 8px 18px;">
        已安装 OpenClaw Skill，完整方证索引 + 板书溯源
      </div>
      <div>🧮 <strong>五运六气推算引擎</strong> — 基于《素问》七篇大论</div>
      <div style="font-size:12px;color:var(--text-light);margin:4px 0 0 18px;">
        干支推算 · 岁运司天 · 客主加临 · 运气同化
      </div>
    </div>
  </div>
</div>

<!-- ════════ TAB 6: AI 问答 ════════ -->
<div class="tab-content" id="tab-ai" style="display:none">
  <div class="card">
    <div class="card-title" style="margin-bottom:8px;">🤖 AI 问答</div>
    <div style="font-size:13px;color:var(--text-light);margin-bottom:12px;">
      基于 DeepSeek V4 Flash · 随你问
    </div>
    <div style="display:flex;gap:8px;margin-bottom:12px;">
      <textarea id="aiQuestion" rows="3"
        style="flex:1;padding:12px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;resize:vertical;font-family:inherit;box-sizing:border-box;background:var(--card);color:var(--text);"
        placeholder="问点什么…"></textarea>
    </div>
    <button onclick="askAI()"
      style="width:100%;padding:12px;background:var(--accent);color:white;border:none;border-radius:10px;font-size:15px;font-weight:500;cursor:pointer;">
      问问 DeepSeek
    </button>
    <div id="aiLoading" style="display:none;text-align:center;padding:16px;color:var(--text-light);">⏳ 思考中…</div>
    <div id="aiAnswer" style="display:none;margin-top:12px;padding:16px;background:var(--bg);border-radius:10px;font-size:14px;line-height:1.8;white-space:pre-wrap;max-height:60vh;overflow-y:auto;"></div>
  </div>
</div>

<div class="footer">心哥 · 莫名心 · 本地中医小站 v2</div>

<script>
// ═════════════════════════════════
// 暗色模式 & Toast 系统
// ═════════════════════════════════

// 初始化：从 localStorage 恢复暗色模式
(function initTheme(){
  try {
    const saved = localStorage.getItem('xiaozhan_dark_mode');
    if (saved === 'true') {
      document.body.classList.add('dark-theme');
      document.getElementById('themeToggle').textContent = '☀️';
    }
  } catch(e){}
})();

function toggleDarkMode() {
  const body = document.body;
  const btn = document.getElementById('themeToggle');
  const isDark = body.classList.toggle('dark-theme');
  btn.textContent = isDark ? '☀️' : '🌙';
  try { localStorage.setItem('xiaozhan_dark_mode', isDark); } catch(e){}
}

// Toast 通知
function showToast(msg, type) {
  type = type || 'info';
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  const icons = {error:'❌', success:'✅', info:'💡'};
  toast.innerHTML = (icons[type] || '💡') + ' ' + msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// 简单的 Markdown 渲染（只处理常用格式）
function renderMarkdown(text) {
  if (!text) return '';
  let html = text
    // 转义 HTML
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // 代码块
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // 行内代码
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // 标题 (### → ## → #)
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    // 加粗
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // 无序列表
    .replace(/^\s*[-*+] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    // 有序列表
    .replace(/^\s*\d+\. (.+)$/gm, '<li>$1</li>')
    // 引用
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    // 换行
    .replace(/\n/g, '<br>');
  return html;
}

// ═════════════════════════════════
// Tab 切换
// ═════════════════════════════════
function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  // 硬开关：暴力操作所有tab-content的display
  const allContent = document.querySelectorAll('.tab-content');
  for (let i = 0; i < allContent.length; i++) {
    allContent[i].style.display = 'none';
  }
  const targetTab = document.querySelector(`.tab[onclick*="'${name}'"]`);
  const targetContent = document.getElementById(`tab-${name}`);
  if (targetTab) targetTab.classList.add('active');
  if (targetContent) {
    targetContent.style.display = 'block';
    targetContent.style.removeProperty('display');
    targetContent.style.display = 'block';
  }
  
  if (name === 'yunqi') {
    const dt = document.getElementById('yunqiDate');
    if (!dt.value) {
      dt.value = new Date().toISOString().split('T')[0];
    }
    // 有缓存就不重新加载
    if (!window._yunqiCached) loadYunqi();
  }
  if (name === 'nihaisha') {
    loadKnowledgeTab();
  }
  if (name === 'phase') {
    loadPhaseTheory();
  }
  if (name === 'philosophy') {
    loadPhilosophy();
  }
  if (name === 'ai') {
    document.getElementById('aiQuestion').focus();
  }
}

// 折叠展开
function toggleCollapse(id, card) {
  const wrap = document.getElementById(id);
  const arrow = card.querySelector('.card-title span:last-child');
  const isOpen = wrap.style.display !== 'none';
  wrap.style.display = isOpen ? 'none' : 'block';
  if (arrow) arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(90deg)';
}

// 加载数字中医笔记
async function loadNotes() {
  const el = document.getElementById('notesList');
  if (!el) return;
  el.innerHTML = '<div style="color:var(--text-light);">加载中…</div>';
  try {
    const res = await fetch('/notes');
    const data = await res.json();
    const cats = data.categories;
    if (cats && Object.keys(cats).length) {
      let html = '';
      for (const [cat, notes] of Object.entries(cats)) {
        html += '<div style="font-weight:600;font-size:14px;color:var(--text-light);margin:10px 0 4px;">📁 ' + cat + '</div>';
        html += notes.map(n => {
          const url = '/notes/' + encodeURIComponent(n.file);
          return '<div style="padding:6px 0;cursor:pointer;" onclick="window.open(\'' + url + '\')">' +
            '<span style="font-weight:500;font-size:14px;">' + n.title + '</span>' +
            '<span style="font-size:12px;color:var(--text-light);margin-left:8px;">' + n.date + ' ↗</span></div>';
        }).join('');
      }
      html += '<div style="margin-top:8px;font-size:13px;color:var(--text-light);text-align:center;">📖 持续更新中</div>';
      el.innerHTML = html;
    } else {
      el.innerHTML = '<div style="color:var(--text-light);text-align:center;padding:12px;">暂无笔记 📖</div>';
    }
  } catch (e) {
    el.innerHTML = '<div class="error-msg">加载失败: ' + e.message + '</div>';
  }
}

// 加载爬虫仓库
async function loadCrawled() {
  const el = document.getElementById('crawledList');
  el.innerHTML = '<div style="color:var(--text-light);">加载中…</div>';
  try {
    const res = await fetch('/crawled-books');
    const data = await res.json();
    if (data.by_category && Object.keys(data.by_category).length) {
      let html = '<div style="display:flex;gap:8px;margin-bottom:10px;">' +
        '<input type="text" id="crawledSearch" placeholder="搜索求知虫中的古籍…" ' +
        'style="flex:1;padding:8px 12px;background:#222228;border:1px solid #3a3a40;border-radius:8px;font-size:13px;color:#ece8dc;outline:none;" ' +
        'onkeyup="filterCrawled()"></div>';
      html += '<div id="crawledListInner">';
      for (const [cat, books] of Object.entries(data.by_category)) {
        const catTotal = books.reduce((a,b) => a + b.chars, 0);
        html += '<div class="crawled-cat" data-cat="' + cat + '">' +
          '<div style="font-weight:600;font-size:14px;color:var(--text-light);margin:10px 0 4px;">📁 ' + cat + ' (' + Math.round(catTotal/1000) + 'k字)</div>';
        html += books.map(b => {
          const title = b.title.replace(/[_\.]/g,' ').substring(0,35);
          const url = '/crawled-view/' + encodeURIComponent(b.title) + '.md';
          return '<div class="crawled-item" data-title="' + title + '" style="padding:5px 0;cursor:pointer;" onclick="window.open(\'' + url + '\')">' +
            '<span style="font-size:13px;">' + title + '</span>' +
            '<span style="font-size:11px;color:var(--text-light);margin-left:6px;">(' + Math.round(b.chars/100)/10 + 'k) ↗</span></div>';
        }).join('');
        html += '</div>';
      }
      html += '<div style="margin-top:8px;font-size:12px;color:var(--text-light);text-align:center;">📖 持续爬取中 &#183; 点击条目查看全文</div>';
      html += '</div>';
      el.innerHTML = html;
    } else {
      el.innerHTML = '<div style="color:var(--text-light);text-align:center;padding:12px;">暂无已爬数据</div>';
    }
  } catch (e) {
    el.innerHTML = '<div class="error-msg">加载失败: ' + e.message + '</div>';
  }
}

// 求知虫搜索过滤
let filterCrawledTimer = null;
function filterCrawled() {
  clearTimeout(filterCrawledTimer);
  filterCrawledTimer = setTimeout(() => {
    const q = document.getElementById('crawledSearch').value.trim().toLowerCase();
    document.querySelectorAll('.crawled-item').forEach(el => {
      el.style.display = (!q || el.dataset.title.includes(q)) ? '' : 'none';
    });
    document.querySelectorAll('.crawled-cat').forEach(el => {
      const visible = el.querySelectorAll('.crawled-item[style*="display: none"]').length < el.querySelectorAll('.crawled-item').length;
      el.style.display = visible ? '' : 'none';
    });
  }, 300);
}

// ═════════════════════════════════
// AI 问答
// ═════════════════════════════════
async function askAI() {
  const q = document.getElementById('aiQuestion').value.trim();
  if (!q) { showToast('请输入问题', 'error'); return; }
  document.getElementById('aiLoading').style.display = 'block';
  document.getElementById('aiAnswer').style.display = 'none';
  showToast('🤔 思考中…', 'info');
  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: q})
    });
    const d = await res.json();
    document.getElementById('aiLoading').style.display = 'none';
    if (d.success) {
      const answerDiv = document.getElementById('aiAnswer');
      answerDiv.innerHTML = renderMarkdown(d.answer);
      answerDiv.style.display = 'block';
      showToast('回答完成 ✓', 'success');
      // 如果更新了哲思词条，清除缓存
      if (d.concept_updated) {
        window._philosophyDirty = true;
        answerDiv.innerHTML += '<br><br>📝 <em>已自动更新词条：' + d.concept_updated + '（切哲思Tab可查看）</em>';
      }
    } else {
      document.getElementById('aiAnswer').innerHTML = '<div class="error-msg">❌ ' + (d.error || '未知错误') + '</div>';
      document.getElementById('aiAnswer').style.display = 'block';
      showToast('查询失败', 'error');
    }
  } catch (e) {
    document.getElementById('aiLoading').style.display = 'none';
    document.getElementById('aiAnswer').innerHTML = '<div class="error-msg">❌ 网络错误: ' + e.message + '</div>';
    document.getElementById('aiAnswer').style.display = 'block';
    showToast('网络错误', 'error');
  }
}

// 哲思折叠展开
// 哲思搜索过滤
function filterPhilosophy(ev) {
  if (ev.key === 'Enter') {
    fetchPhilosophy();
    return;
  }
  const q = document.getElementById('philSearch').value.trim().toLowerCase();
  document.querySelectorAll('.phil-item').forEach(el => {
    const key = el.dataset.key;
    const name = el.dataset.name;
    const match = !q || name.includes(q) || key.includes(q);
    el.style.display = match ? '' : 'none';
    // 隐藏的条目也收起详情
    if (!match) {
      const detail = el.nextElementSibling;
      if (detail && detail.style.display !== 'none') detail.style.display = 'none';
    }
  });
}

// 在线获取哲学家
async function fetchPhilosophy() {
  const q = document.getElementById('philSearch').value.trim();
  if (!q) return;
  const status = document.getElementById('philStatus');
  status.textContent = '⏳ 正在在线获取: ' + q + '…';
  try {
    const res = await fetch('/philosophy-fetch', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    const d = await res.json();
    if (d.success) {
      status.textContent = '✅ 已收录: ' + d.name + ' (' + d.slug + ')';
      // 刷新列表
      philosophyCached = null;
      loadPhilosophy();
      // 自动定位到对应词条并展开
      setTimeout(function(){
        autoLocatePhilosophy(d.name, d.slug);
      }, 200);
    } else if (d.already_have) {
      status.textContent = '✅ 已在本地:' + d.name;
      document.getElementById('philSearch').value = d.name;
      // 自动定位到已有词条
      setTimeout(function(){
        autoLocatePhilosophy(d.name, d.slug);
      }, 100);
    } else {
      status.textContent = '❌ ' + (d.error || '获取失败');
    }
  } catch (e) {
    status.textContent = '❌ 网络错误: ' + e.message;
  }
}

// 自动定位到哲思词条并展开
function autoLocatePhilosophy(name, slug) {
  // 先搜 data-name 匹配
  var items = document.querySelectorAll('.phil-item');
  var target = null;
  for (var i = 0; i < items.length; i++) {
    var n = items[i].getAttribute('data-name');
    var k = items[i].getAttribute('data-key');
    if (n === name || n === '★' + name || k === slug || k === '★' + name) {
      target = items[i];
      break;
    }
  }
  if (!target) return;
  // 滚动到可见区域
  target.scrollIntoView({behavior: 'smooth', block: 'center'});
  // 展开（如果还没展开）
  var detail = target.nextElementSibling;
  if (detail && detail.style.display !== 'block') {
    togglePhilosophy(target);
  }
  // 高亮闪烁
  target.style.transition = 'background 0.3s';
  target.style.background = 'var(--accent-light)';
  setTimeout(function(){ target.style.background = ''; }, 1500);
}

// 哲思中英文切换
function togglePhilLang(key) {
  var zh = document.getElementById('philZh_' + key);
  var en = document.getElementById('philEn_' + key);
  var tag = document.getElementById('philLang_' + key);
  if (!zh || !en || !tag) return;
  var showingZh = zh.style.display !== 'none';
  zh.style.display = showingZh ? 'none' : 'block';
  en.style.display = showingZh ? 'block' : 'none';
  tag.textContent = showingZh ? 'English' : '中文';
}

// 哲思查看中文版（弹窗展示完整中文内容）
// 生成概念总结
async function generateConceptArticle(domKey, slug, name) {
  var btn = document.querySelector('#philConcept_' + domKey + ' button');
  if (btn) { btn.textContent = '⏳ 生成中…'; btn.disabled = true; }
  try {
    var res = await fetch('/philosophy-concept', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({slug: slug, name: name})
    });
    var d = await res.json();
    if (d.success && d.article) {
      var area = document.getElementById('philConcept_' + domKey);
      if (area) {
        area.innerHTML = '<div style="font-size:12px;color:var(--accent);margin-bottom:6px;">📝 概念总结</div>' +
          '<div style="font-size:13px;line-height:1.8;">' + d.article.replace(/\n/g,'<br>') + '</div>';
      }
      philosophyCached = null;
    } else {
      if (btn) { btn.textContent = '❌ 生成失败'; btn.disabled = false; }
    }
  } catch(e) {
    if (btn) { btn.textContent = '❌ 错误'; btn.disabled = false; }
  }
}

function showPhilChinese(domKey, name, realSlug) {
  if (!realSlug) realSlug = domKey;
  var zhDiv = document.getElementById('philZh_' + domKey);
  if (!zhDiv) return;
  var content = zhDiv.textContent || zhDiv.innerText;
  var zhPage = '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>' + name + ' · 中文版</title>' +
    '<style>body{background:#16161a;color:#d8d0c0;padding:30px;font-family:"Noto Sans SC","PingFang SC",sans-serif;max-width:720px;margin:0 auto;line-height:2;font-size:15px;}' +
    'h1{font-size:20px;border-bottom:1px solid #2a2a30;padding-bottom:10px;}' +
    'a{color:#b0a898;}' +
    '</style></head><body>' +
    '<h1>🌐 ' + name + ' · 中文版</h1>' +
    '<div style="font-size:13px;color:#8a7a62;margin-bottom:20px;">来自 Stanford Encyclopedia of Philosophy · AI翻译</div>' +
    '<div>' + content.replace(/\n/g,'<br>') + '</div>' +
    '<div style="margin-top:30px;font-size:12px;color:#5a5a5a;text-align:center;">📡 本地缓存 · <a href="https://plato.stanford.edu/entries/' + realSlug + '/" target="_blank">查看英文原文</a></div>' +
    '</body></html>';
  var w = window.open('', '_blank', 'width=800,height=600,scrollbars=yes');
  if (w) { w.document.write(zhPage); w.document.close(); }
}

// 哲思AI翻译中文（slug=API用, domKey=页面元素ID用）
async function translatePhilosophy(slug, domKey) {
  if (!domKey) domKey = slug;
  var btn = document.querySelector('#philTranslate_' + domKey + ' button');
  if (btn) btn.textContent = '⏳ 翻译中…';
  try {
    var res = await fetch('/philosophy-translate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({slug: slug})
    });
    var d = await res.json();
    if (d.success && d.body_zh) {
      var zhDiv = document.getElementById('philZh_' + domKey);
      if (zhDiv) {
        zhDiv.innerHTML = '';
        zhDiv.appendChild(document.createTextNode(d.body_zh));
        zhDiv.style.whiteSpace = 'pre-wrap';
      }
      // 隐藏翻译按钮
      var wrapper = document.getElementById('philTranslate_' + domKey);
      if (wrapper) wrapper.style.display = 'none';
      // 重置缓存
      philosophyCached = null;
    } else {
      if (btn) btn.textContent = '❌ 翻译失败';
    }
  } catch(e) {
    if (btn) btn.textContent = '❌ ' + e.message;
  }
}

// 哲思折叠展开
function togglePhilosophy(el) {
  var detail = el.nextElementSibling;
  var arrow = el.querySelector('.phil-arrow');
  if (!detail) return;
  if (detail.style.display === 'none' || !detail.style.display) {
    detail.style.display = 'block';
    if (arrow) arrow.style.transform = 'rotate(90deg)';
  } else {
    detail.style.display = 'none';
    if (arrow) arrow.style.transform = 'rotate(0deg)';
  }
}

// ═════════════════════════════════
// 哲思 (SEP 哲学浏览)
// ═════════════════════════════════
let philosophyCached = null;
async function loadPhilosophy() {
  const container = document.getElementById('philosophyContent');
  // 如果AI问答更新了词条，清除缓存重新加载
  if (window._philosophyDirty) {
    philosophyCached = null;
    window._philosophyDirty = false;
  }
  if (philosophyCached) {
    container.innerHTML = philosophyCached;
    return;
  }
  container.innerHTML = '<div class="loading"><div class="spinner"></div><div>加载哲思…</div></div>';
  try {
    const res = await fetch('/philosophy');
    const data = await res.json();
    let html = '<div class="card" style="margin-bottom:16px;">';
    const totalEntries = Object.keys(data).length;
    html += '<div class="card-title" style="margin-bottom:8px;">📖 斯坦福哲学百科 · 精选 (' + totalEntries + ' 条目)</div>';
    // 搜索框
    html += '<div style="display:flex;gap:8px;margin-bottom:10px;">';
    html += '<input type="text" id="philSearch" placeholder="搜哲学家或概念…"';
    html += ' style="flex:1;padding:10px 14px;border:1px solid #ddd;border-radius:10px;font-size:14px;outline:none;background:var(--card);color:var(--text);"';
    html += ' onkeyup="filterPhilosophy(event)">';
    html += '<button onclick="fetchPhilosophy()" style="padding:10px 16px;background:var(--accent);color:white;border:none;border-radius:10px;font-size:13px;cursor:pointer;white-space:nowrap;">🔍 在线获取</button>';
    html += '</div>';
    html += '<div id="philStatus" style="font-size:12px;color:var(--text-light);margin-bottom:8px;"></div>';
    html += '<div id="philList">';
    // 过滤出哲学家 vs 概念
    const categories = {};
    for (const [key, entry] of Object.entries(data)) {
      const name = entry.name || key;
      const cat = ['justice','consciousness','freewill','truth','friendship'].includes(key) ? '概念' : '哲学家';
      if (!categories[cat]) categories[cat] = [];
      categories[cat].push({key, name, title: entry.title || '', body: entry.body || '', bodyEn: entry.body_en || entry.body || '', conceptZh: entry._concept_zh || '', _slug: entry._slug || ''});
    }
    for (const [cat, items] of Object.entries(categories)) {
      html += '<div class="card-title" style="font-size:15px;margin:12px 0 8px;">' + cat + '</div>';
      for (const item of items) {
        const titleClean = item.title.replace(/<[^>]+>/g,'').trim();
        const zhClean = item.body.replace(/<[^>]+>/g,'').trim();
        const enClean = (item.bodyEn || item.body || '').replace(/<[^>]+>/g,'').trim();
        const itemKey = item.key.replace(/^★/,'');
        html += '<div class="yunqi-item phil-item" style="cursor:pointer;margin-bottom:6px;" data-key="' + item.key + '" data-name="' + item.name + '" onclick="togglePhilosophy(this)">';
        html += '<div style="display:flex;justify-content:space-between;align-items:center;">';
        html += '<span><span style="font-weight:600;">' + item.name + '</span> <span style="font-size:12px;color:var(--text-light);">· ' + item.key + '</span></span>';
        html += '<span style="font-size:14px;color:var(--text-light);transition:transform 0.2s;" class="phil-arrow">▶</span>';
        html += '</div>';
        html += '<div style="font-size:12px;color:var(--text-light);margin-top:4px;">' + titleClean.slice(0, 100) + '</div>';
        html += '</div>';
        // 详情：中文 + 英文（可切换）+ 外链
        html += '<div class="phil-detail" style="display:none;padding:14px 16px;margin:-6px 0 10px;background:var(--bg);border-radius:10px;font-size:13px;line-height:1.8;">';
        // 语言切换: 始终有中/EN切换
        html += '<div style="display:flex;gap:8px;margin-bottom:8px;">';
        html += '<span id="philLang_' + item.key + '" style="font-size:11px;color:var(--accent);padding:2px 8px;border:1px solid var(--accent);border-radius:6px;">中文</span>';
        html += '<button onclick="togglePhilLang(\'' + item.key + '\')" style="font-size:11px;padding:2px 8px;border:1px solid var(--tab-bg);border-radius:6px;background:var(--card);color:var(--text-light);cursor:pointer;">EN</button>';
        html += '</div>';
        // 中文内容
        html += '<div id="philZh_' + item.key + '" style="color:var(--text);">';
        html += zhClean.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        html += '</div>';
        // 如果中文没翻译（中英文一样），显示翻译按钮
        if (zhClean === enClean) {
          html += '<div id="philTranslate_' + item.key + '" style="text-align:center;margin:6px 0;">';
          var apiSlug = item._slug || itemKey;
          html += '<button onclick="translatePhilosophy(\'' + apiSlug + '\',\'' + item.key + '\')" style="padding:6px 16px;background:var(--accent);color:white;border:none;border-radius:8px;font-size:12px;cursor:pointer;">🌐 AI翻译中文</button>';
          html += '</div>';
        }
        // 英文内容（隐藏）
        html += '<div id="philEn_' + item.key + '" style="color:var(--text);display:none;">';
        html += enClean.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        html += '</div>';
        html += '<div style="font-size:11px;color:var(--text-light);border-top:1px solid var(--tab-bg);padding-top:6px;margin-top:6px;display:flex;justify-content:center;gap:16px;">';
        if (item._slug) {
          // 本地词条：只留中文版（概念总结放弹窗里）
          html += '<a href="javascript:void(0)" onclick="showPhilChinese(\'' + item.key + '\',\'' + item.name.replace(/'/g,"\\'") + '\',\'' + itemKey + '\')" style="color:var(--green);text-decoration:none;">🌐 中文版</a>';
          if (!item.conceptZh) {
            html += '<span style="color:var(--text-light);">|</span>';
            html += '<a href="javascript:void(0)" onclick="generateConceptArticle(\'' + item.key + '\',\'' + (item._slug || itemKey) + '\',\'' + item.name.replace(/'/g,"\\'") + '\')" style="color:var(--accent);text-decoration:none;">✨ 生成总结</a>';
          }
        } else {
          // 普通SEP条目：SEP原文 + 中文版
          html += '<a href="https://plato.stanford.edu/entries/' + itemKey + '/" target="_blank" style="color:var(--accent);text-decoration:none;">📚 SEP原文</a>';
          var zhBody = (item.body_zh || item.body || '').replace(/<[^>]+>/g,'').trim();
          if (zhBody) {
            html += '<span style="color:var(--text-light);">|</span>';
            html += '<a href="javascript:void(0)" onclick="showPhilChinese(\'' + item.key + '\',\'' + item.name.replace(/'/g,"\\'") + '\',\'' + itemKey + '\')" style="color:var(--green);text-decoration:none;">🌐 中文版</a>';
          }
        }
        // 底部收起按钮
        html += '<div style="text-align:center;margin-top:10px;padding-top:8px;">';
        html += '<button onclick="togglePhilosophy(this.parentElement.parentElement.previousElementSibling)" style="padding:4px 16px;background:none;border:1px solid var(--tab-bg);border-radius:6px;color:var(--text-light);font-size:12px;cursor:pointer;">▲ 收起</button>';
        html += '</div>';
        html += '</div>';
        html += '</div>';
      }
    }
    html += '</div></div>';
    philosophyCached = html;
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<div class="card"><div class="error-msg">加载失败: ' + e.message + '</div></div>';
  }
}

// 物态人论（带缓存，切回来不重刷）
let phaseCached = null; // force fresh
async function loadPhaseTheory() {
  const container = document.getElementById('phaseContent');
  if (phaseCached) {
    container.innerHTML = phaseCached;
    return;
  }
  container.innerHTML = '<div class="loading"><div class="spinner"></div><div>加载物态人论…</div></div>';
  try {
    const res = await fetch('/phase-theory');
    const html = await res.text();
    phaseCached = html;
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = '<div class="card"><div class="error-msg">加载失败: ' + e.message + '</div></div>';
  }
}

// ═════════════════════════════════
// 五运六气
// ═════════════════════════════════
async function loadYunqi() {
  const dateInput = document.getElementById('yunqiDate');
  const dateVal = dateInput.value || new Date().toISOString().split('T')[0];
  
  document.getElementById('yunqiLoading').style.display = 'block';
  document.getElementById('yunqiResult').style.display = 'none';
  
  try {
    const res = await fetch('/yunqi', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({date: dateVal})
    });
    const data = await res.json();
    
    document.getElementById('yunqiLoading').style.display = 'none';
    
    if (!data.success) {
      document.getElementById('yunqiErrorMsg').textContent = data.error || '计算失败';
      document.getElementById('yunqiErrorCard').style.display = 'block';
      document.getElementById('yunqiResult').style.display = 'block';
      return;
    }
    
    // 缓存结果
    window._yunqiCached = data;
    window._yunqiCachedDate = dateVal;
    renderYunqi(data);
  } catch (e) {
    document.getElementById('yunqiLoading').style.display = 'none';
    document.getElementById('yunqiErrorMsg').textContent = '网络错误: ' + e.message;
    document.getElementById('yunqiErrorCard').style.display = 'block';
    document.getElementById('yunqiResult').style.display = 'block';
  }
}

// 知识搜索也加缓存
let _kwCached = null;
let _kwCachedQuery = '';

function renderYunqi(d) {
  document.getElementById('yunqiErrorCard').style.display = 'none';
  document.getElementById('yunqiResult').style.display = 'block';
  
  // Header
  const h = document.getElementById('yunqiHeader');
  h.querySelector('.date').textContent = `📆 ${d.date}`;
  h.querySelector('.gz').textContent = `${d.year_gz}年 · ${d.day_gz}日`;
  h.querySelector('.year-info').textContent = `丙午年 · 第${d.yunqi_year - 1984 + 1}甲子 · 岁${d.sui_yun.name}${d.sui_yun.status}`;
  
  // 主要格局
  const gridHtml = `
    <div class="yunqi-item">
      <div class="label">岁运</div>
      <div class="value ${d.sui_yun.status === '太过' ? 'accent' : 'gold'}">${d.sui_yun.name}${d.sui_yun.status}</div>
      <div style="font-size:11px;color:var(--text-light);">${d.sui_yun.element} · 天干${d.sui_yun.tiangan}</div>
    </div>
    <div class="yunqi-item">
      <div class="label">司天</div>
      <div class="value blue">${d.si_tian}</div>
      <div style="font-size:11px;color:var(--text-light);">上半年</div>
    </div>
    <div class="yunqi-item">
      <div class="label">在泉</div>
      <div class="value green">${d.zai_quan}</div>
      <div style="font-size:11px;color:var(--text-light);">下半年</div>
    </div>
    <div class="yunqi-item">
      <div class="label">日干支</div>
      <div class="value">${d.day_gz}</div>
      <div style="font-size:11px;color:var(--text-light);">生肖 ${d.shengxiao}</div>
    </div>
  `;
  document.getElementById('yunqiMainGrid').innerHTML = gridHtml;
  
  // 当前步位
  const step = d.current_step;
  const stepHtml = `
    <div class="step-card" style="background:linear-gradient(135deg,#f0ebe6,#e8ddd6);">
      <div class="step-title">${step.name}</div>
      <div style="display:flex;gap:12px;margin-top:8px;">
        <div style="flex:1;text-align:center;padding:8px;background:var(--blue);color:white;border-radius:8px;">
          <div style="font-size:11px;opacity:0.8;">主气</div>
          <div style="font-size:16px;font-weight:600;">${step.zhu_qi}</div>
        </div>
        <div style="display:flex;align-items:center;font-size:18px;color:var(--text-light);">↔</div>
        <div style="flex:1;text-align:center;padding:8px;background:var(--green);color:white;border-radius:8px;">
          <div style="font-size:11px;opacity:0.8;">客气</div>
          <div style="font-size:16px;font-weight:600;">${step.ke_qi}</div>
        </div>
      </div>
      <div style="margin-top:8px;text-align:center;">
        <span style="background:${step.shun_ni.includes('相得') ? 'var(--green)' : 'var(--accent)'};color:white;padding:4px 12px;border-radius:12px;font-size:12px;">
          ${step.relation} · ${step.shun_ni}
        </span>
      </div>
      <div style="font-size:12px;color:var(--text-light);margin-top:6px;text-align:center;">
        日期: ${step.date_range.start} ~ ${step.date_range.end}
      </div>
    </div>
  `;
  document.getElementById('yunqiCurrentStep').innerHTML = stepHtml;
  
  // 客主加临六步
  const stepsHtml = d.ke_zhu_jia_lin.map(s => {
    const tag = s.keqi_is_sitian ? ' (司天)' : s.keqi_is_zaiquan ? ' (在泉)' : '';
    return `<div class="step-card">
      <div class="step-title">第${s.step_number}步</div>
      <div style="display:flex;gap:8px;margin-top:4px;font-size:13px;">
        <span style="flex:1;">主: ${s.zhu_qi}</span>
        <span style="flex:1;">客: ${s.ke_qi}${tag}</span>
      </div>
      <div class="step-detail">${s.relation} · ${s.shun_ni}</div>
    </div>`;
  }).join('');
  document.getElementById('yunqiSteps').innerHTML = stepsHtml;
  
  // 运气同化
  const th = d.tong_hua;
  const thParts = [];
  if (th.tianfu) thParts.push('天符');
  if (th.suihui) thParts.push('岁会');
  if (th.taiyi_tianfu) thParts.push('太乙天符');
  if (th.pingqi) thParts.push('平气');
  if (thParts.length) {
    document.getElementById('yunqiTonghua').style.display = 'block';
    document.getElementById('yunqiTonghuaContent').innerHTML =
      `<span style="font-size:16px;font-weight:600;color:var(--gold);">${thParts.join('、')}</span>
       <div style="font-size:13px;color:var(--text-light);margin-top:4px;">${th.taiyi_tianfu ? '⚠ 太乙天符之年，气候变动剧烈' : ''}</div>`;
  } else {
    document.getElementById('yunqiTonghua').style.display = 'none';
  }
  
  // 主运/客运
  if (d.zhu_yun && d.zhu_yun.length) {
    document.getElementById('yunqiZhuKeYun').style.display = 'block';
    const zhuHtml = d.zhu_yun.map(s =>
      `<div style="display:flex;gap:8px;padding:4px 0;font-size:13px;border-bottom:1px solid #f0ebe6;">
        <span style="width:60px;color:var(--text-light);">${s.step}运</span>
        <span>${s.tai_shao}${s.element}</span>
      </div>`
    ).join('');
    const keHtml = d.ke_yun.map(s =>
      `<div style="display:flex;gap:8px;padding:4px 0;font-size:13px;border-bottom:1px solid #f0ebe6;">
        <span style="width:60px;color:var(--text-light);">${s.step}运</span>
        <span>${s.tai_shao}${s.element}</span>
      </div>`
    ).join('');
    document.getElementById('yunqiYunContent').innerHTML = `
      <div style="font-weight:600;font-size:14px;margin-bottom:8px;">主运</div>
      ${zhuHtml}
      <div style="font-weight:600;font-size:14px;margin:12px 0 8px;">客运</div>
      ${keHtml}
    `;
  }
}

// ═════════════════════════════════
// 经典参考搜索
// ═════════════════════════════════
async function searchKnowledge() {
  const q = document.getElementById('kwSearchInput').value.trim();
  if (!q) return;
  
  document.getElementById('kwLoading').style.display = 'block';
  document.getElementById('kwResult').style.display = 'none';
  
  try {
    const res = await fetch('/knowledge-search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    const data = await res.json();
    
    document.getElementById('kwLoading').style.display = 'none';
    document.getElementById('kwResult').style.display = 'block';
    
    if (data.results && data.results.length) {
      const html = data.results.map(r => {
        const originLink = r.source_path ? ' · <a href="/classic-view/' + encodeURIComponent(r.source_path) + '" target="_blank" style="color:var(--green);">📖 查看原文 ↗</a>' : '';
        return `<div style="padding:8px 0;border-bottom:1px solid #f0ebe6;">
          <div style="font-weight:600;font-size:14px;">${r.title}</div>
          <div style="font-size:13px;color:var(--text-light);margin-top:2px;">${r.snippet}</div>
          <div style="font-size:11px;color:var(--text-light);margin-top:2px;">📁 ${r.source}${originLink}</div>
        </div>`;
      }).join('');
      document.getElementById('kwResultContent').innerHTML = html;
      // 缓存搜索结果
      _kwCached = html;
      _kwCachedQuery = q;
    } else {
      document.getElementById('kwResultContent').innerHTML =
        '<div style="font-size:14px;color:var(--text-light);padding:12px;text-align:center;">未找到相关结果，试试其他关键词 📖</div>';
      _kwCached = null;
      _kwCachedQuery = '';
    }
  } catch (e) {
    document.getElementById('kwLoading').style.display = 'none';
    document.getElementById('kwResult').style.display = 'block';
    document.getElementById('kwResultContent').innerHTML =
      `<div class="error-msg">搜索出错: ${e.message}</div>`;
  }
}

// 切到经典参考Tab时，有缓存就直接显示
let _kwTabInitialized = false;
function loadKnowledgeTab() {
  loadNotes();
  loadCrawled();
  if (_kwCached) {
    document.getElementById('kwResult').style.display = 'block';
    document.getElementById('kwResultContent').innerHTML = _kwCached;
    document.getElementById('kwSearchInput').value = _kwCachedQuery;
  }
}

function quickSearch(q) {
  document.getElementById('kwSearchInput').value = q;
  searchKnowledge();
}

// ═════════════════════════════════
// 辨证食疗（原版）
// ═════════════════════════════════
// ====== BMI 实时计算 ======
function calcBMI() {
  const h = parseFloat(document.getElementById('bioHeight').value);
  const w = parseFloat(document.getElementById('bioWeight').value);
  const el = document.getElementById('bmiDisplay');
  if (h > 0 && w > 0) {
    const bmi = (w / ((h / 100) ** 2)).toFixed(1);
    let status = '', color = '';
    if (bmi < 18.5) { status = '过轻'; color = '#c9a84c'; }
    else if (bmi < 24) { status = '正常'; color = '#4a7c59'; }
    else if (bmi < 28) { status = '超重'; color = '#d4a530'; }
    else if (bmi < 32) { status = '肥胖'; color = '#d86050'; }
    else { status = '重度肥胖'; color = '#b8453a'; }
    el.innerHTML = `📊 BMI = <strong>${bmi}</strong> <span style="color:${color};font-weight:600;">（${status}）</span>`;
  } else {
    el.textContent = '';
  }
}

// 绑定输入事件
document.addEventListener('DOMContentLoaded', function() {
  ['bioHeight','bioWeight'].forEach(id => {
    document.getElementById(id).addEventListener('input', calcBMI);
  });
});

const customSymptoms = new Set();

function addCustomSymptom() {
  const inp = document.getElementById('customSymptom');
  const val = inp.value.trim();
  if (!val || customSymptoms.has(val)) return;
  customSymptoms.add(val);
  inp.value = '';
  renderCustomTags();
}

function removeCustomSymptom(val) {
  customSymptoms.delete(val);
  renderCustomTags();
}

function renderCustomTags() {
  const el = document.getElementById('customTags');
  el.innerHTML = '';
  for (const s of customSymptoms) {
    const tag = document.createElement('span');
    tag.className = 'tag-small';
    tag.innerHTML = `${s} <span class="remove" onclick="removeCustomSymptom('${s}')">✕</span>`;
    el.appendChild(tag);
  }
}

document.querySelectorAll('.tag').forEach(t => {
  t.addEventListener('click', () => { t.classList.toggle('selected'); });
});

const SYMPTOM_KEYWORDS = {
  '失眠': ['失眠','睡不着','不寐','入睡困难','难入睡'],
  '嗜睡': ['嗜睡','困倦','昏昏欲睡','总想睡','睡不醒'],
  '多梦': ['多梦','梦多','噩梦','梦魇'],
  '心悸': ['心悸','心慌','心跳','心怦怦','心跳快','心乱'],
  '心烦': ['心烦','烦躁','心躁','坐立不安'],
  '胸闷': ['胸闷','胸堵','胸口','憋气','气堵','胸痛'],
  '健忘': ['健忘','记性差','忘事','记忆力','忘性大'],
  '急躁易怒': ['急躁','易怒','爱发火','暴脾气','脾气大','点火就着'],
  '情绪抑郁': ['抑郁','心情差','低落','消沉','悲观','想哭','不开心','郁闷'],
  '胁肋胀痛': ['胁肋','肋痛','两侧痛','胁痛','胸胁'],
  '头晕目眩': ['头晕','眩晕','天旋地转','头昏','眼花'],
  '目赤': ['目赤','眼红','红眼','眼睛红'],
  '手足麻木': ['麻木','手脚麻','手麻','肢麻'],
  '食欲不振': ['食欲不振','没胃口','不想吃','吃不下','纳呆','纳差','厌食'],
  '消谷善饥': ['消谷善饥','容易饿','总想吃','饿得快','善饥','胃火'],
  '暴食': ['暴食','暴饮暴食','吃得多','贪食','过量吃','不撑不停'],
  '腹胀': ['腹胀','肚子胀','腹满','胀气','胃胀','鼓胀'],
  '便溏': ['便溏','拉稀','腹泻','稀便','不成形','大便稀'],
  '便秘': ['便秘','大便干','排便难','拉不出','羊粪'],
  '乏力': ['乏力','没劲','疲劳','疲倦','累','没力气','虚弱','精疲力尽'],
  '咳嗽': ['咳嗽','咳','咳喘'],
  '气喘': ['气喘','喘','上气不接下气','喘息','呼吸困难'],
  '气短': ['气短','气不够用','上不来气','短气'],
  '痰多': ['痰多','痰','咳痰','白痰','黄痰'],
  '自汗': ['自汗','出汗','汗多','一动就出汗','虚汗'],
  '易感冒': ['易感冒','总感冒','爱感冒','常感冒','反复感冒'],
  '腰膝酸软': ['腰膝酸软','腰酸','腰痛','膝盖软','腿软','腰疼'],
  '畏寒': ['畏寒','怕冷','怕风','冷','手脚凉','怕寒'],
  '怕热': ['怕热','怕热','爱出汗','热得慌'],
  '五心烦热': ['五心烦热','手心热','脚心热','心口热','发烧感'],
  '盗汗': ['盗汗','睡着出汗','晚上出汗','睡觉出汗'],
  '夜尿多': ['夜尿多','起夜','夜尿频','尿多'],
  '头痛': ['头痛','头疼','偏头痛','头胀痛'],
  '口干': ['口干','口渴','嘴干','咽干','想喝水'],
  '口苦': ['口苦','嘴苦','苦味'],
  '面色淡白': ['面色淡白','脸白','脸色差'],
  '面色萎黄': ['面色萎黄','面色黄','脸黄','萎黄'],
  '浮肿': ['浮肿','水肿','肿','眼皮肿','腿肿'],
  '恶寒': ['恶寒','发冷','寒战','打寒战','浑身冷'],
  '发热': ['发热','发烧','体温高'],
  '无汗': ['无汗','不出汗','汗不出'],
  '鼻塞': ['鼻塞','鼻子不通','堵鼻子','流鼻涕'],
  '流清涕': ['流清涕','清鼻涕','稀鼻涕'],
  '咽痛': ['咽痛','嗓子疼','喉咙痛','咽疼'],
  '恶心': ['恶心','想吐','干呕','反胃'],
  '鼻燥': ['鼻燥','鼻子干','鼻腔干'],
  '身热不扬': ['身热不扬','潮热','一阵热'],
  '头重如裹': ['头重','头沉','头蒙','脑袋重'],
  '干咳': ['干咳','干咳无痰'],
};

function parseNLP() {
  const text = document.getElementById('nlpInput').value.trim();
  if (!text) { document.getElementById('nlpResult').textContent = '⚠️ 请先输入不舒服的症状'; return; }
  document.getElementById('nlpResult').textContent = '正在识别…';
  
  const matchedSymptoms = new Set();
  for (const [symptom, keywords] of Object.entries(SYMPTOM_KEYWORDS)) {
    for (const kw of keywords) {
      if (text.includes(kw)) { matchedSymptoms.add(symptom); break; }
    }
  }
  if (matchedSymptoms.size === 0) { document.getElementById('nlpResult').textContent = '😅 没识别出常见症状，请手动勾选或直接输入'; return; }
  
  document.querySelectorAll('#symptomGrid input[type="checkbox"]').forEach(cb => {
    if (matchedSymptoms.has(cb.value)) cb.checked = true;
  });
  document.getElementById('nlpResult').innerHTML = '✅ 已识别症状：<strong>' + Array.from(matchedSymptoms).join('、') + '</strong>';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function submitDiagnosis() {
  const symptoms = [];
  document.querySelectorAll('#symptomGrid input:checked').forEach(e => symptoms.push(e.value));
  for (const s of customSymptoms) symptoms.push(s);
  if (symptoms.length === 0) { showToast('请至少选择或输入一个症状', 'error'); return; }
  
  const tongue = Array.from(document.querySelectorAll('#tongueGroup .selected')).map(e => e.dataset.val).join(',');
  const pulse = Array.from(document.querySelectorAll('#pulseGroup .selected')).map(e => e.dataset.val).join(',');
  
  // 收集生物信息
  const bio = {
    age: parseInt(document.getElementById('bioAge').value) || 0,
    sex: document.getElementById('bioSex').value || '',
    height: parseFloat(document.getElementById('bioHeight').value) || 0,
    weight: parseFloat(document.getElementById('bioWeight').value) || 0,
    medical_history: document.getElementById('bioHistory').value.trim(),
    family_history: document.getElementById('bioFamilyHistory').value.trim(),
    smoking: document.getElementById('bioSmoking').value || '',
    smoking_years: parseInt(document.getElementById('bioSmokingYears').value) || 0,
    alcohol: document.getElementById('bioAlcohol').value || '',
    alcohol_years: parseInt(document.getElementById('bioAlcoholYears').value) || 0,
    sex_life: document.getElementById('bioSexLife').value || '',
  };
  
  document.getElementById('inputArea').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  document.getElementById('resultArea').classList.remove('visible');
  
  try {
    const res = await fetch('/diagnose', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ symptoms, tongue, pulse, bio })
    });
    const data = await res.json();
    document.getElementById('loading').style.display = 'none';
    showResult(data);
  } catch (e) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('inputArea').style.display = 'block';
    showToast('网络错误: ' + e.message, 'error');
  }
}

function showResult(data) {
  document.getElementById('resultArea').classList.add('visible');
  if (data.error) { document.getElementById('errorCard').style.display = 'block'; document.getElementById('errorMsg').textContent = data.error; return; }
  
  // ====== 风险预警 ======
  const riskEl = document.getElementById('riskAlerts');
  if (data.risks && data.risks.length) {
    const html = data.risks.map(r => {
      const urgencyColors = {
        'emergency': { bg: '#fef2f0', border: '#d86050', text: '#b8453a', icon: '🚨' },
        'urgent': { bg: '#fff8e6', border: '#d4a530', text: '#8a6a1a', icon: '⚠️' },
        'non_urgent': { bg: '#f0f5fa', border: '#3a5a7c', text: '#2a4a66', icon: '💡' },
      };
      const c = urgencyColors[r.urgency] || urgencyColors.non_urgent;
      return `<div style="background:${c.bg};border:1.5px solid ${c.border};border-radius:12px;padding:16px 18px;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
          <span style="font-size:20px;">${c.icon}</span>
          <span style="font-weight:600;font-size:15px;color:${c.text};">${r.label}</span>
        </div>
        <div style="font-size:14px;line-height:1.7;color:${c.text};">${(r.advice || '').replace(/\\n/g, '<br>')}</div>
        <div style="margin-top:6px;font-size:13px;">
          <span style="background:${c.border};color:white;padding:3px 10px;border-radius:10px;font-size:12px;">🏥 ${r.department}</span>
        </div>
      </div>`;
    }).join('');
    riskEl.innerHTML = html;
    riskEl.style.display = 'block';
    // 紧急情况滚动到风险提示
    const hasEmergency = data.risks.some(r => r.urgency === 'emergency');
    if (hasEmergency) {
      riskEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  } else {
    riskEl.style.display = 'none';
  }
  
  // ====== 西医参考建议 ======
  if (data.western_advice && data.western_advice.length) {
    const wEl = document.getElementById('westernAdviceCard');
    const wContent = document.getElementById('westernAdviceContent');
    wEl.style.display = 'block';
    wContent.innerHTML = data.western_advice.map(a =>
      `<div style="margin-bottom:10px;">
        <div style="font-weight:600;font-size:14px;color:var(--blue);margin-bottom:4px;">🩺 ${a.symptom}</div>
        ${a.advice.map(t => `<div style="font-size:13px;line-height:1.6;padding:2px 0;">• ${t}</div>`).join('')}
      </div>`
    ).join('');
  } else {
    document.getElementById('westernAdviceCard').style.display = 'none';
  }
  
  const h = document.getElementById('resultHeader');
  h.querySelector('.dx-name').textContent = data.syndrome || '未确定';
  h.querySelector('.dx-sub').textContent = `${data.organ} · ${data.nature} · ${data.principle}`;
  
  if (data.special_pattern) {
    const sp = document.createElement('div');
    sp.style.cssText = 'font-size:13px;opacity:0.9;margin-top:6px;background:rgba(255,255,255,0.2);padding:6px 10px;border-radius:8px;';
    sp.textContent = `⚠ ${data.special_pattern}: ${data.special_desc || ''}`;
    h.appendChild(sp);
  }
  
  if (data.recommended_ingredients && data.recommended_ingredients.length)
    document.getElementById('herbTags').innerHTML = data.recommended_ingredients.map(h => `<span class="herb-tag">${h}</span>`).join('');
  if (data.foods_to_avoid && data.foods_to_avoid.length)
    document.getElementById('avoidTags').innerHTML = data.foods_to_avoid.map(f => `<span class="avoid-tag">${f}</span>`).join('');
  if (data.recipes && data.recipes.length)
    document.getElementById('recipeList').innerHTML = data.recipes.map(r => `<div class="recipe-card">${r}</div>`).join('');
  if (data.acupoints && data.acupoints.length)
    document.getElementById('acupointList').innerHTML = `<div class="acupoint-list">${data.acupoints.map(a => `<span class="acupoint">${a}</span>`).join('')}</div>`;
  if (data.daily_care && data.daily_care.length)
    document.getElementById('dailyCare').innerHTML = data.daily_care.map(d => `<div class="tx-item">🟢 ${d}</div>`).join('');
  
  const emotion = [];
  if (data.emotional_care) { Array.isArray(data.emotional_care) ? data.emotional_care.forEach(e => emotion.push(e)) : emotion.push(data.emotional_care); }
  if (data.sleep_advice) emotion.push(data.sleep_advice);
  if (emotion.length) document.getElementById('emotionCare').innerHTML = emotion.map(e => `<div class="tx-item">🌙 ${e}</div>`).join('');
  
  if (data.reasoning_trace && data.reasoning_trace.length) {
    document.getElementById('traceCard').style.display = 'block';
    document.getElementById('traceContent').innerHTML = data.reasoning_trace.map((t, i) => {
      const scorePct = Math.round(t.匹配度 * 100);
      return `<div style="padding:10px 0;${i > 0 ? 'border-top:1px solid #f0ebe6;' : ''}${i === 0 ? 'background:#faf7f4;border-radius:10px;padding:12px;margin:-4px 0 0;' : ''}">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-weight:600;font-size:14px;">${i === 0 ? '🏆 ' : ''}${t.证型}</span>
          <span style="font-size:12px;background:${i === 0 ? 'var(--accent)' : '#e8d5d0'};color:${i === 0 ? 'white' : 'var(--accent)'};padding:2px 8px;border-radius:10px;">${scorePct}%</span>
          <span style="font-size:12px;color:var(--text-light);margin-left:auto;">${t.病位} · ${t.病性}</span>
        </div>
        <div style="margin-top:4px;color:var(--text-light);">匹配: ${t.匹配详情} · 症状: ${Array.isArray(t.匹配症状) ? t.匹配症状.join('、') : t.匹配症状 || '-'}</div>
        <div style="color:var(--text-light);font-size:12px;">治则: ${t.治则}</div>
      </div>`;
    }).join('');
  }
  
  if (data.knowledge && data.knowledge.herb_props && data.knowledge.herb_props.length) {
    document.getElementById('knowledgeCard').style.display = 'block';
    document.getElementById('knowledgeInfo').innerHTML = `
      <div style="font-size:13px;color:var(--text-light);margin-bottom:8px;">
        🏛 TCM-MKG · ${data.knowledge.herbs || '?'}味药 / ${data.knowledge.medicines || '?'}方
        <div style="font-size:11px;opacity:0.6;margin-top:4px;">📅 数据版本: ${data.knowledge.version || '初次部署'} · 每月1日自动更新</div>
      </div>
      ${data.knowledge.herb_props.slice(0,8).map(h => `<div style="font-size:13px;padding:4px 0;">· ${h.name}${h.info ? ' — ' + h.info : ''}</div>`).join('')}
    `;
  }
  
  // 滚动到顶部或紧急提示
  const hasEmergency = data.risks && data.risks.some(r => r.urgency === 'emergency');
  if (!hasEmergency) {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function resetAll() {
  // 清空症状勾选
  document.querySelectorAll('#symptomGrid input[type="checkbox"]').forEach(cb => cb.checked = false);
  // 清空自定义症状
  customSymptoms.clear();
  renderCustomTags();
  // 清空舌脉选中
  document.querySelectorAll('#tongueGroup .selected, #pulseGroup .selected').forEach(t => t.classList.remove('selected'));
  // 清空 NLP 输入
  document.getElementById('nlpInput').value = '';
  document.getElementById('nlpResult').textContent = '';
  document.getElementById('customSymptom').value = '';
  // 清空新加入的基本信息
  document.getElementById('bioAge').value = '';
  document.getElementById('bioSex').value = '';
  document.getElementById('bioHeight').value = '';
  document.getElementById('bioWeight').value = '';
  document.getElementById('bioHistory').value = '';
  document.getElementById('bioFamilyHistory').value = '';
  document.getElementById('bioSmoking').value = '';
  document.getElementById('bioSmokingYears').value = '';
  document.getElementById('bioAlcohol').value = '';
  document.getElementById('bioAlcoholYears').value = '';
  document.getElementById('bioSexLife').value = '';
  document.getElementById('bmiDisplay').textContent = '';
  // 恢复界面
  document.getElementById('resultArea').classList.remove('visible');
  document.getElementById('riskAlerts').style.display = 'none';
  document.getElementById('errorCard').style.display = 'none';
  document.getElementById('inputArea').style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════
# HTTP 服务
# ═══════════════════════════════════════════

class DiagnoseHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 统一导入（避免 Python 3.12 分支级 import 导致局部变量作用域泄露）
        import glob as _cg
        import traceback as _tb
        from daogui_lib import generate_lib_page
        
        if self.path == '/' or self.path == '/index.html' or self.path.startswith('/?'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        elif self.path.startswith('/daogui'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            cat = params.get('cat', [None])[0]
            doc = params.get('doc', [None])[0]
            dao_html = generate_lib_page(category=cat, doc_id=doc)
            self.wfile.write(dao_html.encode('utf-8'))
        elif self.path == '/crawled-books':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            clean_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xin_sources', 'cleaned')
            index_path = os.path.join(clean_dir, '_index.json')
            if os.path.isfile(index_path):
                with open(index_path, 'r', encoding='utf-8') as _f:
                    self.wfile.write(_f.read().encode('utf-8'))
            else:
                self.wfile.write(json.dumps({'total':0,'by_category':{}}, ensure_ascii=False).encode('utf-8'))
        elif self.path == '/notes':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            import glob, re
            # 中文数字 → 阿拉伯数字
            _cn_num = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
            def _卷次排序key(fpath):
                bn = os.path.basename(fpath).replace('.md', '')
                m = re.search(r'篇第([一二三四五六七八九十]+)', bn)
                if m:
                    return sum(_cn_num.get(c, 0) for c in m.group(1))
                # 也认卷号："卷第三" 之类
                m2 = re.search(r'卷([一二三四五六七八九十]+)', bn)
                if m2:
                    total = 0
                    for ch in m2.group(1):
                        total += _cn_num.get(ch, 0)
                    return total
                # fallback：用文件名拼音排序
                return 0
            notes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '数字中医有感')
            categories = {}
            if os.path.isdir(notes_dir):
                for sub in sorted(os.listdir(notes_dir)):
                    subpath = os.path.join(notes_dir, sub)
                    if not os.path.isdir(subpath):
                        continue
                    md_files = glob.glob(os.path.join(subpath, '*.md'))
                    md_files.sort(key=_卷次排序key)
                    notes_in_cat = []
                    for f in md_files:
                        with open(f, 'r', encoding='utf-8') as nf:
                            first_line = nf.readline().strip().lstrip('# ')
                        rel_path = sub + '/' + os.path.basename(f)
                        notes_in_cat.append({
                            'title': first_line or os.path.basename(f).replace('.md', ''),
                            'file': rel_path,
                            'date': '2026-07-23'
                        })
                    if notes_in_cat:
                        categories[sub] = notes_in_cat
            self.wfile.write(json.dumps({'categories': categories}, ensure_ascii=False).encode('utf-8'))
        elif self.path.startswith('/classic-view/'):
            self._handle_classic_view()
        elif self.path.startswith('/crawled-view/'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            import glob as _cg
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            page = int(params.get('page', ['1'])[0])
            page = max(1, page)
            clean_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xin_sources', 'cleaned')
            file_rel = unquote(parsed.path[len('/crawled-view/'):])
            found = None
            for f in _cg.glob(os.path.join(clean_dir, '**', '*.md'), recursive=True):
                if file_rel in f or os.path.basename(f) == file_rel:
                    found = f; break
            if found and os.path.isfile(found):
                with open(found, 'r', encoding='utf-8') as vf:
                    raw = vf.read()
                # 提取正文（跳过yaml头）
                body_start = raw.find('\n---\n', raw.find('---')) if raw.startswith('---') else 0
                if body_start > 0:
                    body = raw[body_start+5:]
                else:
                    body = raw
                mode = params.get('mode', ['simp'])[0]
                if mode == 'trad':
                    trad_rel = file_rel.replace('.md', '.trad.md')
                    for _tf in _cg.glob(os.path.join(clean_dir, '**', '*.trad.md'), recursive=True):
                        if os.path.basename(_tf) == trad_rel:
                            with open(_tf, 'r', encoding='utf-8') as vf:
                                raw2 = vf.read()
                            bs2 = raw2.find('\n---\n', raw2.find('---')) if raw2.startswith('---') else 0
                            if bs2 > 0:
                                body = raw2[bs2+5:]
                                break
                ppc = 5000
                total = max(1, (len(body) + ppc - 1) // ppc)
                page = min(page, total)
                start = (page - 1) * ppc
                end = min(start + ppc, len(body))
                chunk = body[start:end]
                safe = html.escape(chunk)
                nav = '<div style="text-align:center;padding:12px;border-top:1px solid #2a2a30;">'
                if page > 1:
                    nav += f'<a href="?page={page-1}" style="color:#b0a898;text-decoration:none;margin-right:16px;">‹ 上一页</a>'
                nav += f'<span style="color:#5a5a5a;font-size:13px;">第 {page}/{total} 页</span>'
                if page < total:
                    nav += f'<a href="?page={page+1}" style="color:#b0a898;text-decoration:none;margin-left:16px;">下一页 ›</a>'
                nav += '</div>'
                mode = params.get('mode', ['simp'])[0]
                if mode == 'trad':
                    trad_rel = file_rel.replace('.md', '.trad.md')
                    for _tf in _cg.glob(os.path.join(clean_dir, '**', '*.trad.md'), recursive=True):
                        if os.path.basename(_tf) == trad_rel:
                            with open(_tf, 'r', encoding='utf-8') as vf:
                                raw = vf.read()
                            break
                # 繁简切换链接（手动拼接避免引号转义问题）
                q_simp = '?page=' + str(page) + '&mode=simp'
                q_trad = '?page=' + str(page) + '&mode=trad'
                simp_a = '<a href="' + q_simp + '" style="color:#b0a898;text-decoration:none;">简体</a>'
                trad_a = '<a href="' + q_trad + '" style="color:#b0a898;text-decoration:none;">繁体</a>'
                mode_switch = '<span style="margin-left:12px;">[ ' + simp_a + ' | ' + trad_a + ' ]</span>'
                self.wfile.write(f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html.escape(os.path.basename(file_rel))}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: #16161a; color: #d8d0c0; font-family: 'Noto Sans SC','PingFang SC',sans-serif; }}
.nav {{ padding:14px 20px; border-bottom:1px solid #2a2a30; }}
.nav a {{ color:#b0a898; text-decoration:none; font-size:14px; }}
.info {{ padding:10px 20px; font-size:12px; color:#8a7a62; }}
.content {{ padding:20px; max-width:720px; margin:0 auto; font-size:15px; line-height:2; white-space:pre-wrap; word-wrap:break-word; }}
</style></head><body>
<div class="nav"><a href="/">← 返回小站</a> <span style="color:#5a5a5a;margin-left:12px;">{html.escape(os.path.basename(file_rel))}</span>{mode_switch}</div>
<div class="info">📖 {mode} · 已清洗 · 第{page}页</div>
<div class="content">{safe}</div>
{nav}
</body></html>'''.encode('utf-8'))
            else:
                self.wfile.write('<h1>未找到</h1>'.encode())
        elif self.path.startswith('/notes/'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            rel_path = unquote(self.path[len('/notes/'):]).lstrip('/')
            notes_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '数字中医有感')
            filename = os.path.basename(rel_path)
            filepath = os.path.join(notes_dir, rel_path)
            if os.path.isfile(filepath):
                with open(filepath, 'r', encoding='utf-8') as nf:
                    content_md = nf.read()
                # Simple md-to-html (no markdown dependency)
                lines = content_md.split('\n')
                html_parts = []
                in_bq = False
                for line in lines:
                    s = line.strip()
                    if s.startswith('# '):
                        html_parts.append(f'<h1>{html.escape(s[2:])}</h1>')
                    elif s.startswith('## '):
                        html_parts.append(f'<h2>{html.escape(s[3:])}</h2>')
                    elif s.startswith('> '):
                        if not in_bq:
                            html_parts.append('<blockquote>')
                            in_bq = True
                        html_parts.append(f'<p>{html.escape(s[2:])}</p>')
                    else:
                        if in_bq:
                            html_parts.append('</blockquote>')
                            in_bq = False
                        if s.startswith('- ') or s.startswith('* '):
                            html_parts.append(f'<li>{html.escape(s[2:])}</li>')
                        elif s == '---':
                            html_parts.append('<hr>')
                        elif s:
                            html_parts.append(f'<p>{html.escape(s)}</p>')
                        else:
                            html_parts.append('<br>')
                if in_bq:
                    html_parts.append('</blockquote>')
                html_body = '\n'.join(html_parts)
                self.wfile.write(f'''<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{html.escape(filename)}</title>
<style>
body {{ font-family: -apple-system, 'PingFang SC', sans-serif; background: #1a1a1e; color: #ece8dc; padding: 20px; max-width: 720px; margin: 0 auto; line-height: 1.8; }}
h1 {{ border-bottom: 1px solid #333; padding-bottom: 10px; }}
code {{ background: #2a2a30; padding: 2px 6px; border-radius: 4px; }}
blockquote {{ border-left: 3px solid #d86050; margin: 16px 0; padding: 8px 16px; background: #222228; }}
pre {{ background: #222228; padding: 16px; border-radius: 8px; overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ border: 1px solid #333; padding: 8px; }}
a {{ color: #d0a050; }}
.nav {{ margin-bottom: 20px; }}
.nav a {{ color: #b0a898; text-decoration: none; font-size: 14px; }}
</style></head><body>
<div class="nav"><a href="/#nihaisha">← 返回小站</a></div>
{html_body}
</body></html>'''.encode('utf-8'))
            else:
                self.wfile.write('<h1>笔记未找到</h1>'.encode('utf-8'))
        elif self.path.startswith('/forge-destiny'):
            import sys as _fds
            print('FORGE GET:', self.path, file=_fds.stderr)
            _fds.stderr.flush()
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            code = params.get('code', [None])[0]
            user = params.get('user', [None])[0]
            print(f'FORGE code={code} user={user}', file=_fds.stderr)
            _fds.stderr.flush()
            if code and user:
                try:
                    r = forge_engine.handle_result(code, int(user))
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(r, ensure_ascii=False).encode('utf-8'))
                except Exception as e:
                    import traceback
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success':False,'error':str(e),'trace':traceback.format_exc()}, ensure_ascii=False).encode('utf-8'))
                return
            forge_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '锻因缘', 'index.html')
            try:
                with open(forge_path, 'r', encoding='utf-8') as f:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f.read().encode('utf-8'))
            except FileNotFoundError:
                self._json_response(404, {'error': 'not found'})
        elif self.path == '/phase-theory':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            phase_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'xin_phase_theory.html')
            try:
                with open(phase_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            except FileNotFoundError:
                self.wfile.write('<h1>物态人论页面未找到</h1>'.encode())
        elif self.path == '/skills':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            skills_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'skills.json')
            try:
                with open(skills_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            except FileNotFoundError:
                self.wfile.write(json.dumps({'error': '技能注册表未找到'}).encode('utf-8'))
        elif self.path == '/upload':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write((
                '<!DOCTYPE html><html><head><meta charset="UTF-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
                '<title>上传文件到莫名心</title>'
                '<style>body{background:#1a1a1e;color:#ece8dc;padding:20px;font-family:sans-serif;max-width:600px;margin:0 auto;}'
                '.card{background:#222228;border-radius:14px;padding:20px;margin-bottom:16px;}'
                'h1{font-size:20px;margin-bottom:16px;}'
                'input,textarea{width:100%;padding:12px;border:1px solid #3a3a40;border-radius:10px;background:#2a2a30;color:#ece8dc;font-size:14px;margin-bottom:12px;box-sizing:border-box;}'
                'button{width:100%;padding:14px;background:#d86050;color:white;border:none;border-radius:12px;font-size:16px;cursor:pointer;}'
                '#result{margin-top:12px;font-size:14px;color:#b0a898;}'
                '</style></head><body>'
                '<h1>📤 上传文件到莫名心</h1>'
                '<div class="card">'
                '<p style="color:#b0a898;margin-bottom:12px;">选择文件，我会把它存到工作目录里并读取。</p>'
                '<input type="file" id="fileInput" multiple>'
                '<button onclick="uploadAll()">上传</button>'
                '<div id="result"></div>'
                '</div>'
                '<script>'
                'async function uploadAll(){'
                'const r=document.getElementById("result");'
                'const files=document.getElementById("fileInput").files;'
                'if(!files.length){r.textContent="请先选择文件";return;}'
                'r.textContent="上传中 0/"+files.length+"...";'
                'let ok=0,err=0;'
                'for(let i=0;i<files.length;i++){'
                'const f=files[i];'
                'r.textContent="上传中 "+i+"/"+files.length+": "+f.name;'
                'try{'
                'const b64=await new Promise((res,rej)=>{const r2=new FileReader();r2.onload=e=>res(e.target.result.split(",")[1]);r2.onerror=rej;r2.readAsDataURL(f)});'
                'const d=await(await fetch("/upload",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filename:f.name,content:b64})})).json();'
                'if(d.error)err++;else ok++;'
                '}catch(e){err++}'
                '}'
                'r.textContent="✅ 完成: "+ok+" 成功, "+err+" 失败";'
                '}'
                '</script></body></html>'
            ).encode('utf-8'))
        elif self.path == '/yunqi' or self.path.startswith('/yunqi?'):
            # GET /yunqi?date=2026-07-26 — 五运六气（前端兼容格式）
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            date_val = params.get('date', [None])[0]
            self._json_response(200, get_yunqi_data(date_val))
        elif self.path.startswith('/yunqi-eval'):
            # GET /yunqi-eval?date=2026-07-26&plan=养生方案 — 食疗评价 API
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            date_val = params.get('date', [None])[0]
            plan = params.get('plan', [''])[0]
            try:
                from 五运六气 import 推算
                from 五运六气.eval import 评价食疗方案
                if plan:
                    r = 推算(date_val)
                    ev = 评价食疗方案(r, plan)
                    self._json_response(200, {"success": True, "五运六气": r, "评价": ev})
                else:
                    self._json_response(200, {"success": False, "error": "需要 plan 参数（食疗方案）"})
            except Exception as e:
                self._json_response(200, {"success": False, "error": str(e)})
        elif self.path.startswith('/yunqi-v2'):
            # GET /yunqi-v2?date=2026-07-26 — 五运六气（精简 API 格式，供外引）
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            date_val = params.get('date', [None])[0]
            try:
                from 五运六气 import 推算
                self._json_response(200, 推算(date_val))
            except Exception as e:
                self._json_response(200, {'error': str(e)})
        elif self.path == '/philosophy' or self.path.startswith('/philosophy?'):
            # GET /philosophy — 合并 SEP + 本地词条
            sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
            sep_data = {}
            if os.path.isfile(sep_path):
                with open(sep_path, 'r', encoding='utf-8') as _sf:
                    sep_data = json.load(_sf)
            # 把本地词条合并进去，用 "★" 前缀标识
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
            self._json_response(200, sep_data)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404')

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        
        try:
            data = json.loads(body)
        except:
            data = {}
        
        if self.path == '/diagnose':
            self._handle_diagnose(data)
        elif self.path == '/yunqi':
            self._handle_yunqi(data)
        elif self.path == '/yunqi-v2':
            date_str = data.get('date', None)
            try:
                from 五运六气 import 推算
                self._json_response(200, 推算(date_str))
            except Exception as e:
                self._json_response(200, {'error': str(e)})
        elif self.path == '/yunqi-eval':
            date_str = data.get('date', None)
            plan = data.get('plan', '')
            try:
                from 五运六气 import 推算
                from 五运六气.eval import 评价食疗方案
                if plan:
                    r = 推算(date_str)
                    ev = 评价食疗方案(r, plan)
                    self._json_response(200, {"success": True, "五运六气": r, "评价": ev})
                else:
                    self._json_response(200, {"success": False, "error": "需要 plan 参数（食疗方案）"})
            except Exception as e:
                self._json_response(200, {"success": False, "error": str(e)})
        elif self.path == '/ask':
            question = data.get('question', '').strip()
            context = data.get('context', '')
            if question:
                result = ai_ask(question, context)
                # AI回答后自动检测是否匹配本地词条，更新概念总结
                if result.get('success') and result.get('answer'):
                    try:
                        q_lower = question.lower()
                        词条 = _本地词条_加载()
                        for slug, entry in 词条.items():
                            主名 = entry["主名"]
                            if 主名.lower() in q_lower or 主名.lower() in result['answer'].lower():
                                # 匹配到本地词条，更新概念总结
                                sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
                                if os.path.isfile(sep_path):
                                    with open(sep_path, 'r', encoding='utf-8') as _sf:
                                        sep_data = json.load(_sf)
                                    if slug in sep_data:
                                        sep_data[slug]['_concept_zh'] = result['answer'][:10000]
                                        sep_data[slug]['_concept_name'] = 主名
                                        with open(sep_path, 'w', encoding='utf-8') as _sf:
                                            json.dump(sep_data, _sf, ensure_ascii=False, indent=2)
                                        result['concept_updated'] = 主名
                                break
                    except Exception:
                        pass
                self._json_response(200, result)
            else:
                self._json_response(200, {"success": False, "error": "需要 question 参数"})
        elif self.path == '/philosophy-fetch':
            self._json_response(200, handle_philosophy_fetch(data))
        elif self.path == '/philosophy-translate':
            self._json_response(200, handle_philosophy_translate(data))
        elif self.path == '/philosophy-concept':
            self._json_response(200, handle_philosophy_concept(data))
        elif self.path == '/knowledge-search':
            self._handle_knowledge_search(data)
        elif self.path == '/forge-destiny':
            self._handle_forge(data)
        elif self.path == '/upload':
            self._handle_upload(data)
        else:
            self._json_response(404, {'error': 'not found'})

    def _handle_classic_view(self):
        """查看经典原文（修复：加HTTP头 + 改fallback文案）"""
        try:
            from urllib.parse import urlparse, parse_qs, unquote
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            page = int(params.get('page', ['1'])[0])
            page = max(1, page)
            file_rel = unquote(parsed.path[len('/classic-view/'):])
            base = os.path.expanduser('~/.openclaw/workspace/xin_sources')
            filepath = os.path.join(base, file_rel)
            if os.path.isfile(filepath) and filepath.startswith(base):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                with open(filepath, 'r', encoding='utf-8') as vf:
                    raw = vf.read()
                import re as remod, html as hmod
                from urllib.parse import urlencode
                cleaned = remod.sub(r'<pb:[^>]+>', '', raw)
                cleaned = remod.sub('\u00b6', '', cleaned)
                cleaned = remod.sub(r'#.*', '', cleaned)
                cleaned = remod.sub('\n{3,}', '\n\n', cleaned)
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
                    simp = convert(chunk, 'zh-cn')
                except:
                    simp = chunk
                simp_html = hmod.escape(simp)
                nav = '<div style="text-align:center;padding:16px 20px;border-top:1px solid #2a2a30;">'
                if page > 1:
                    nav += '<a href="?page=' + str(page-1) + '" style="color:#b0a898;text-decoration:none;margin-right:20px;">\u2039 \u4e0a\u4e00\u9875</a>'
                nav += '<span style="color:#5a5a5a;font-size:13px;">\u7b2c ' + str(page) + '/' + str(total) + ' \u9875</span>'
                if page < total:
                    nav += '<a href="?page=' + str(page+1) + '" style="color:#b0a898;text-decoration:none;margin-left:20px;">\u4e0b\u4e00\u9875 \u203a</a>'
                nav += '</div>'
                basename = os.path.basename(file_rel)
                self.wfile.write((
                    '<!DOCTYPE html><html><head><meta charset="UTF-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
                    '<title>' + hmod.escape(basename) + ' \u7b2c' + str(page) + '\u9875</title>'
                    '<style>body{background:#16161a;color:#d8d0c0;padding:20px;font-family:sans-serif;max-width:800px;margin:0 auto;}'
                    'a{color:#b0a898}a:hover{color:#ece8dc}.nav{padding:10px 0;border-bottom:1px solid #2a2a30;margin-bottom:16px}'
                    '.cols{display:flex;gap:20px}.col{flex:1;font-size:15px;line-height:2;white-space:pre-wrap;word-wrap:break-word}'
                    '.col-left{font-family:"Noto Serif SC",serif}.col-right{font-family:"Noto Sans SC",sans-serif}'
                    '.col-hdr{font-size:11px;color:#6a5a4a;letter-spacing:2px;border-bottom:1px solid #2a2a30;padding-bottom:6px;margin-bottom:8px}'
                    '@media(max-width:640px){.cols{flex-direction:column}}</style></head><body>'
                    '<div class="nav"><a href="/">\u2190 \u8fd4\u56de\u5c0f\u7ad9</a> <span style="color:#5a5a5a;margin-left:12px;">'
                    + hmod.escape(basename) + '</span></div>'
                    '<div style="color:#8a7a62;font-size:12px;margin-bottom:10px;">\u7b2c' + str(page) + '\u9875</div>'
                    '<div class="cols">'
                    '<div class="col col-left"><div class="col-hdr">\u5b8b\u4f53</div>' + orig + '</div>'
                    '<div class="col col-right"><div class="col-hdr">\u7b80\u4f53</div>' + simp_html + '</div>'
                    '</div>' + nav + '</body></html>'
                ).encode('utf-8'))
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write((
                    '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>\u6587\u4ef6\u672a\u627e\u5230</title>'
                    '<style>body{background:#16161a;color:#d8d0c0;padding:40px;font-family:sans-serif;max-width:600px;margin:0 auto;text-align:center;}'
                    'h1{font-size:60px;margin:0;color:#3a2a1a;}p{color:#6a5a4a;}a{color:#d8d0c0;}</style></head><body>'
                    '<h1>\U0001F4D6</h1><p>\u6587\u6863\u672a\u627e\u5230\uff0c\u53ef\u80fd\u5df2\u88ab\u79fb\u52a8\u6216\u540d\u79f0\u53d1\u751f\u4e86\u53d8\u5316\u3002</p>'
                    '<p><a href="/">\u2190 \u8fd4\u56de\u5c0f\u7ad9</a></p></body></html>'
                ).encode('utf-8'))
        except Exception as exc:
            import traceback
            print(f'[classic-view error] {exc}', flush=True)
            traceback.print_exc()
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(('<h1>\u62b1\u6b49\uff0c\u670d\u52a1\u5668\u51fa\u9519\u4e86</h1><pre>' + str(exc) + '</pre>').encode('utf-8'))
            except:
                pass

    def _handle_diagnose(self, data):
        try:
            symptoms = data.get('symptoms', [])
            tongue = data.get('tongue', '')
            pulse = data.get('pulse', '')
            bio = data.get('bio', {})
            result = run_diagnosis(symptoms, tongue, pulse, bio)
            self._json_response(200, result)
        except Exception as e:
            self._json_response(200, {'error': f'诊断出错: {str(e)}'})

    def _handle_yunqi(self, data):
        try:
            date_str = data.get('date', None)
            result = get_yunqi_data(date_str)
            self._json_response(200, result)
        except Exception as e:
            self._json_response(200, {'success': False, 'error': str(e)})

    def _handle_forge(self, data):
        try:
            action = data.get('action', '')
            if action == 'create':
                result = forge_engine.handle_create(data.get('user1', {}))
            elif action == 'join':
                result = forge_engine.handle_join(data.get('code', ''), data.get('user2', {}))
            else:
                result = {'success': False, 'error': '未知操作'}
            self._json_response(200, result)
        except Exception as e:
            self._json_response(200, {'success': False, 'error': str(e)})
    
    def _handle_knowledge_search(self, data):
        try:
            query = data.get('query', '').strip()
            results = search_knowledge_refs(query)
            self._json_response(200, {'results': results})
        except Exception as e:
            self._json_response(200, {'results': [], 'error': str(e)})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def _handle_upload(self, data):
        """接收文件上传（base64 JSON）"""
        try:
            filename = data.get('filename', '')
            content_b64 = data.get('content', '')
            if not filename or not content_b64:
                self._json_response(400, {'error': '需要 filename 和 content'})
                return
            import base64
            safe_name = os.path.basename(filename)
            save_dir = os.path.expanduser('~/.openclaw/workspace/uploads')
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, safe_name)
            decoded = base64.b64decode(content_b64)
            with open(filepath, 'wb') as f:
                f.write(decoded)
            size_kb = len(decoded) / 1024
            print(f'[上传] {safe_name} ({size_kb:.1f} KB) -> {filepath}', flush=True)
            self._json_response(200, {
                'message': f'{safe_name} 已保存（{size_kb:.1f} KB）',
                'path': filepath,
                'size': len(decoded)
            })
        except Exception as e:
            self._json_response(500, {'error': str(e)})

    def log_message(self, format, *args):
        print(f"[心哥小站] {args[0]} {args[1]} {args[2]}")


def run_diagnosis(symptoms, tongue, pulse, bio=None):
    """执行辨证 + 风险预警 + 西医建议，返回结构化结果"""
    symptoms = [s for s in symptoms if s.strip()]
    dx = differentiate(symptoms, tongue, pulse)

    # ====== 风险预警 ======
    try:
        from xin_claw_doctor import (
            assess_risk,
            get_western_advice as wm_advice,
        )
        risks = assess_risk(symptoms, bio or {})
        western_advice = wm_advice(symptoms)
    except ImportError:
        risks = []
        western_advice = []

    result = {
        'syndrome': dx.get('syndrome', '未确定'),
        'organ': dx.get('organ', ''),
        'nature': dx.get('nature', ''),
        'confidence': dx.get('confidence', '低'),
        'principle': dx.get('principle', ''),
        'match_detail': dx.get('match_detail', ''),
        'special_pattern': dx.get('special_pattern', ''),
        'special_desc': dx.get('special_desc', ''),
        'phase_desc': dx.get('phase_state', {}).get('desc', ''),
        'phase_action': dx.get('phase_state', {}).get('action', ''),
        'reasoning_trace': dx.get('reasoning_trace', []),
        'risks': risks,
        'western_advice': western_advice,
    }

    if dx.get('syndrome') != '无法确定':
        diet = get_dietary_plan(dx)
        result['recommended_ingredients'] = diet.get('recommended_ingredients', [])
        result['foods_to_avoid'] = diet.get('foods_to_avoid', [])
        result['recipes'] = [r['name'] for r in diet.get('recipes', [])]

        tx = get_treatment_plan(dx.get('syndrome', ''))
        if tx:
            result['acupoints'] = tx.get('acupoints', [])
            result['daily_care'] = tx.get('daily_care', []) if isinstance(tx.get('daily_care'), list) else [tx.get('daily_care', '')]
            result['emotional_care'] = tx.get('emotional_care', '')
            result['sleep_advice'] = tx.get('sleep_advice', '')
    else:
        result['recommended_ingredients'] = []
        result['foods_to_avoid'] = []
        result['recipes'] = []

    # 知识图谱补充
    try:
        from xin_knowledge import (knowledge_base_status, get_herb_properties,
                                   get_herb_flavors, get_herb_nature, lookup_herb)
        kb = knowledge_base_status()
        herb_props = []
        for h in result.get('recommended_ingredients', [])[:8]:
            herb = lookup_herb(h)
            if herb:
                flavors = get_herb_flavors(h)
                natures = get_herb_nature(h)
                info_parts = []
                if flavors: info_parts.append('味:' + '/'.join(flavors))
                if natures: info_parts.append('气:' + '/'.join(natures))
                herb_props.append({'name': h, 'info': ' · '.join(info_parts) if info_parts else '✓'})
        result['knowledge'] = {
            'version': kb.get('version', '未知'),
            'herbs': kb.get('herbs', 0),
            'medicines': kb.get('medicines', 0),
            'herb_props': herb_props,
        }
    except Exception:
        result['knowledge'] = {}

    return result


def _score_search_match(query, filename):
    """给搜索匹配打分：文件名含查询词 > 文件名含相关核心词 > 其他"""
    score = 0
    fname_lower = filename.lower()
    q_lower = query.lower()
    if q_lower in fname_lower:
        score += 100
    # 常见相关核心词：同名核心意象也算高权重
    core_words = {
        '伤寒': ['伤寒', '伤寒论'],
        '金匮': ['金匮', '金匮要略'],
        '神农': ['神农', '神农本草', '本经'],
        '黄帝': ['黄帝', '素问', '灵枢', '内经'],
        '针灸': ['针灸', '针', '灸', '大成'],
        '温病': ['温病', '条辨', '温热'],
        '难经': ['难经', '八十一难'],
        '脉': ['脉经', '脉诀'],
    }
    for core, keywords in core_words.items():
        if q_lower in core or core in q_lower:
            if any(kw in fname_lower for kw in keywords):
                score += 80
                break
    return score


# ============================================================
# DeepSeek AI 问答
# ============================================================

_ai_api_key = None

def _get_ai_key():
    """从 OpenClaw auth store 读取 DeepSeek API key"""
    global _ai_api_key
    if _ai_api_key:
        return _ai_api_key
    try:
        import sqlite3
        db = os.path.expanduser('~/.openclaw/agents/main/agent/openclaw-agent.sqlite')
        if os.path.isfile(db):
            conn = sqlite3.connect(db)
            c = conn.cursor()
            rows = c.execute('SELECT store_json FROM auth_profile_store WHERE store_key=?', ('primary',)).fetchall()
            conn.close()
            if rows:
                d = json.loads(rows[0][0])
                profs = d.get('profiles', {})
                for key, val in profs.items():
                    if 'deepseek' in key and val.get('type') == 'api_key':
                        _ai_api_key = val['key']
                        return _ai_api_key
    except Exception:
        pass
    return ''


def ai_ask(question: str, context: str = "") -> dict:
    """调 DeepSeek 问答"""
    key = _get_ai_key()
    if not key:
        return {"success": False, "error": "AI 密钥不可用"}
    
    messages = []
    if context:
        messages.append({"role": "system", "content": context})
    messages.append({"role": "user", "content": question})
    
    try:
        import urllib.request
        body = json.dumps({
            "model": "deepseek-v4-flash",
            "messages": messages,
            "max_tokens": 5000,
            "temperature": 0.7,
        }).encode('utf-8')
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        choice = result.get('choices', [{}])[0].get('message', {})
        return {
            "success": True,
            "answer": choice.get('content', '').strip(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _sep_fetch(slug: str) -> tuple:
    """从 SEP 抓取完整条目，返回 (title, body) 或 None"""
    import urllib.request, re
    from urllib.parse import quote
    try:
        url = f"https://plato.stanford.edu/entries/{quote(slug)}/"
        req = urllib.request.Request(url, headers={'User-Agent': 'PhilosophyBot/1.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')
        tm = re.search(r'<title>([^<]+)', html)
        paras = re.findall(r'<p[^>]*>([^<]{50,})</p>', html)
        body = '\n\n'.join(p.strip() for p in paras)  # 全部段落，不截断
        if body:
            return (tm.group(1)[:80] if tm else slug, body)
    except Exception:
        pass
    return None


def _sep_save(slug: str, name_cn: str, title: str, body_en: str, body_zh: str = ""):
    """保存到本地缓存（中英双语）"""
    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
    lib = {}
    if os.path.isfile(sep_path):
        with open(sep_path, 'r', encoding='utf-8') as f:
            lib = json.load(f)
    # 保留旧字段兼容，同时存双语
    existing = lib.get(slug, {})
    # 兼容旧数据：如果有旧 body 字段，移到 body_en
    if 'body' in existing and 'body_en' not in existing:
        existing['body_en'] = existing.pop('body')
    lib[slug] = {
        "name": name_cn,
        "title": title,
        "body_en": body_en,
        "body_zh": body_zh or existing.get('body_zh', ''),
        "body": body_zh or body_en,  # 兼容旧前端（默认中文）
    }
    os.makedirs(os.path.dirname(sep_path), exist_ok=True)
    with open(sep_path, 'w', encoding='utf-8') as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)


# 本地词条路径
_词条路径 = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '本地词条.json')


def _本地词条_加载() -> dict:
    """加载本地词条。结构: {slug: {"主名": "...", "别名": ["..."]}}"""
    if os.path.isfile(_词条路径):
        try:
            with open(_词条路径, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}


def _本地词条_保存(slug: str, 主名: str):
    """保存/更新一个本地词条的主名"""
    d = _本地词条_加载()
    if slug not in d:
        d[slug] = {"主名": 主名, "别名": []}
    else:
        d[slug]["主名"] = 主名
    os.makedirs(os.path.dirname(_词条路径), exist_ok=True)
    with open(_词条路径, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def _本地词条_新增别名(slug: str, 别名: str):
    """给已有词条加别名（不重复）"""
    d = _本地词条_加载()
    if slug in d and 别名 not in d[slug]["别名"] and 别名 != d[slug]["主名"]:
        d[slug]["别名"].append(别名)
        with open(_词条路径, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)


def _本地词条_查找(query: str) -> tuple:
    """查找query是否匹配已有词条。返回(slug, 主名)或None"""
    q = query.lower()
    d = _本地词条_加载()
    for slug, entry in d.items():
        if q == entry["主名"].lower() or q in entry["主名"].lower():
            return (slug, entry["主名"])
        for alias in entry.get("别名", []):
            if q == alias.lower() or q in alias.lower():
                return (slug, entry["主名"])
    return None


def handle_philosophy_fetch(data: dict) -> dict:
    """在线获取哲学条目（支持模糊/错字输入，自动叠本地词条）"""
    query = data.get('query', '').strip().lower()
    if not query:
        return {"success": False, "error": "需要查询内容"}
    
    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
    lib = {}
    if os.path.isfile(sep_path):
        with open(sep_path, 'r', encoding='utf-8') as f:
            lib = json.load(f)
    
    # 1. 查本地词条（主名+别名模糊匹配，归一到同一slug）
    match = _本地词条_查找(query)
    if match:
        slug, 主名 = match
        if slug in lib:
            return {"success": True, "already_have": True, "slug": slug, "name": 主名}
    
    # 2. 精确匹配本地 SEP 缓存
    for slug, entry in lib.items():
        if query in slug or query in entry.get('name', '').lower() or query in entry.get('title', '').lower():
            return {"success": True, "already_have": True, "slug": slug, "name": entry.get('name', slug)}
    
    # 3. 已知 SEP slug 映射
    sep_en_map = {
        "plato":"plato", "aristotle":"aristotle", "socrates":"socrates",
        "confucius":"confucius", "kant":"kant", "nietzsche":"nietzsche",
        "heraclitus":"heraclitus", "parmenides":"parmenides", "epicurus":"epicurus",
        "stoicism":"stoicism", "plotinus":"plotinus",
        "locke":"locke", "berkeley":"berkeley", "hume":"hume",
        "leibniz":"leibniz", "spinoza":"spinoza", "rousseau":"rousseau",
        "schopenhauer":"schopenhauer", "heidegger":"heidegger",
        "wittgenstein":"wittgenstein", "foucault":"foucault", "derrida":"derrida",
        "rawls":"rawls", "camus":"camus", "popper":"popper",
        "adorno":"adorno", "habermas":"habermas", "russell":"bertrand-russell",
        "quine":"quine", "hegel":"hegel", "marx":"marx", "freud":"freud",
        "ethics":"ethics", "aesthetics":"aesthetics", "justice":"justice",
        "consciousness":"consciousness", "freewill":"freewill", "truth":"truth",
    }
    
    # 辅助：AI 英文译中文
    def _ai_zh(body_en):
        try:
            r = ai_ask(f"把以下英文翻译成中文，保留专业术语和哲学概念：\n\n{body_en[:3000]}", "你是专业哲学翻译。译文要通顺准确，不要添加解释。")
            return r.get('answer', '')[:10000] if r.get('success') else ''
        except:
            return ''
    
    slug = sep_en_map.get(query)
    if slug:
        result = _sep_fetch(slug)
        if result:
            title, body_en = result
            name_cn = query.title()
            body_zh = _ai_zh(body_en)
            _sep_save(slug, name_cn, title, body_en, body_zh)
            return {"success": True, "slug": slug, "name": name_cn}
    
    # 4. 模糊输入 → 让 DeepSeek AI 猜最接近的 SEP 条目
    search_term = data.get('query', '').strip()  # 保留原始输入大小写
    try:
        ai_result = ai_ask(
            f"用户想查哲学内容，搜索词是「{query}」。"
            f"请判断它最可能对应Stanford Encyclopedia of Philosophy的哪个条目slug"
            f"（如 hegel, nietzsche, plato, kant, socrates, heidegger, wittgenstein 等）。"
            f"只回复一个slug单词，不要任何其他文字。",
            "你是一个哲学知识助手。只回复一个英文slug，不要标点、不要解释。"
        )
        if ai_result.get('success'):
            ai_slug = ai_result['answer'].strip().lower().split()[0].strip('.,!?;:') if ai_result['answer'] else ''
            if ai_slug and len(ai_slug) > 1:
                result = _sep_fetch(ai_slug)
                if result:
                    title, body_en = result
                    body_zh = _ai_zh(body_en)
                    _sep_save(ai_slug, query.title(), title, body_en, body_zh)
                    # ★ 本地词条逻辑
                    本地 = _本地词条_加载()
                    is_concept = ai_slug not in sep_en_map.values() and len(search_term) > 6
                    if ai_slug in 本地:
                        _本地词条_新增别名(ai_slug, search_term)
                        主名 = 本地[ai_slug]["主名"]
                    else:
                        _本地词条_保存(ai_slug, search_term)
                        主名 = search_term
                    
                    # ★ 概念词条：如果是自定义概念（非标准哲学家名），AI生成原创中文归纳
                    if is_concept:
                        try:
                            concept_article = ai_ask(
                                f"用户搜索的概念是「{search_term}」。以下是与它相关的哲学条目原文：\n\n"
                                f"{body_en[:4000]}\n\n"
                                f"请写一篇关于「{search_term}」的中文文章，"
                                f"综合上述内容，介绍这个概念在哲学中的含义、来源和重要性。"
                                f"用中文写，500-800字，通俗易懂但保留学术深度。",
                                "你是哲学作家。用中文写出有深度的概念解析文章。不要写'根据以上内容'这类话。"
                            )
                            if concept_article.get('success') and concept_article.get('answer'):
                                # 存为独立概念条目
                                if slug not in lib:
                                    lib[slug] = {}
                                lib[slug]["_concept"] = True
                                lib[slug]["_concept_zh"] = concept_article['answer'][:10000]
                                with open(sep_path, 'w', encoding='utf-8') as f:
                                    json.dump(lib, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                    
                    return {"success": True, "slug": ai_slug, "name": 主名}
    except Exception:
        pass
    
    return {"success": False, "error": f"无法找到与「{query}」对应的哲学条目"}


def handle_philosophy_translate(data: dict) -> dict:
    """按需AI翻译哲学条目为中文"""
    slug = (data.get('slug') or '').strip().lower()
    if not slug:
        return {"success": False, "error": "需要 slug 参数"}
    
    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
    if not os.path.isfile(sep_path):
        return {"success": False, "error": "数据不存在"}
    
    with open(sep_path, 'r', encoding='utf-8') as f:
        lib = json.load(f)
    
    if slug not in lib:
        return {"success": False, "error": f"条目 {slug} 不存在"}
    
    entry = lib[slug]
    body_en = entry.get('body_en', '') or entry.get('body', '')
    body_zh = entry.get('body_zh', '')
    
    # 如果已经有中文翻译且不是英文，直接返回
    if body_zh and body_zh != body_en:
        return {"success": True, "already_translated": True, "body_zh": body_zh[:3000]}
    
    # 调用AI翻译
    try:
        result = ai_ask(
            f"把以下英文翻译成中文，保留专业术语和哲学家名字，译文通顺：\n\n{body_en[:1500]}",
            "你是专业哲学翻译。只输出译文，不要添加解释或额外文字。"
        )
        if result.get('success') and result.get('answer'):
            body_zh_new = result['answer'][:3000]
            # 保存
            entry['body_zh'] = body_zh_new
            entry['body'] = body_zh_new  # 兼容旧前端
            with open(sep_path, 'w', encoding='utf-8') as f:
                json.dump(lib, f, ensure_ascii=False, indent=2)
            return {"success": True, "body_zh": body_zh_new}
        return {"success": False, "error": "AI翻译失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_philosophy_concept(data: dict) -> dict:
    """生成概念词条的AI总结文章"""
    slug = (data.get('slug') or '').strip().lower()
    concept_name = (data.get('name') or slug).strip()
    if not slug:
        return {"success": False, "error": "需要 slug 参数"}
    
    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
    if not os.path.isfile(sep_path):
        return {"success": False, "error": "数据不存在"}
    
    with open(sep_path, 'r', encoding='utf-8') as f:
        lib = json.load(f)
    
    if slug not in lib:
        return {"success": False, "error": f"条目 {slug} 不存在"}
    
    entry = lib[slug]
    body_en = entry.get('body_en', '') or entry.get('body', '')
    body_zh = entry.get('body_zh', '') or body_en
    
    # 调用AI生成概念总结
    try:
        result = ai_ask(
            f"用户搜索的概念是「{concept_name}」。"
            f"以下是与它相关的哲学原文：\n\n{body_en[:4000]}\n\n"
            f"请写一篇专门关于「{concept_name}」的中文文章（500~800字），"
            f"综合原文中与该概念相关的内容，介绍这个概念在哲学中的含义、来源和重要性。"
            f"不要写成人物生平，要聚焦于概念本身。",
            "你是哲学作家。用中文写出有深度的概念解析。直接写正文，不需要开头语。"
        )
        if result.get('success') and result.get('answer'):
            article = result['answer'][:10000]
            import re as _re
            article = _re.sub(r'\*+|\#+|__|~~|```|``', '', article)
            article = _re.sub(r'^>\s*', '', article, flags=_re.MULTILINE)
            article = _re.sub(r'^[ \t]*[-*+]\s+', '', article, flags=_re.MULTILINE)
            article = _re.sub(r'^\d+\.\s+', '', article, flags=_re.MULTILINE)
            article = _re.sub(r'^[ \t]+', '', article, flags=_re.MULTILINE)
            article = _re.sub(r'\n{3,}', '\n\n', article)
            article = article.strip()
            entry['_concept_zh'] = article
            entry['_concept_name'] = concept_name
            with open(sep_path, 'w', encoding='utf-8') as f:
                json.dump(lib, f, ensure_ascii=False, indent=2)
            return {"success": True, "article": article}
        return {"success": False, "error": "AI生成失败"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_knowledge_refs(query):
    """在已安装的经典资源中搜索并排序"""
    results = []
    
    def add_result(title, snippet, source, source_path, score):
        results.append({
            'title': title,
            'snippet': snippet,
            'source': source,
            'source_path': source_path,
            '_score': score,
        })
    
    base_sources = os.path.expanduser('~/.openclaw/workspace/xin_sources')
    
    # 1. 搜索王冰注本素问（永远是素问内容，得分按文件名卷次）
    kanripo_dir = os.path.join(base_sources, 'kanripo_suwen')
    for root, dirs, files in os.walk(kanripo_dir):
        for f in sorted(files):
            if not f.endswith('.txt'):
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    for i, line in enumerate(fh):
                        if query in line:
                            title = f.replace('.txt', '').replace('KR5d0040_', '素问卷')
                            snippet = line.strip()[:120]
                            score = 60 if query in ('黄帝', '内经', '素问') else 10
                            add_result(f'{title} (第{i+1}行)', snippet,
                                       '王冰注本·黄帝内经素问',
                                       os.path.relpath(fp, base_sources), score)
                            break  # 每个文件只取1条，避免重复噪音
            except:
                continue
    
    # 2. 搜索tcmoc古籍（带文件名打分）
    tcmoc_dir = os.path.join(base_sources, 'tcmoc')
    skip_files = {'README.md', 'Catelog.md', '.gitignore'}
    for root, dirs, files in os.walk(tcmoc_dir):
        for f in sorted(files):
            if not (f.endswith('.md') or f.endswith('.txt')):
                continue
            if f in skip_files:
                continue
            if '识典' in f:
                continue  # 识典数据需登录，爬回来的是垃圾
            fp = os.path.join(root, f)
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                    if query not in content:
                        continue
                    title = f.replace('.md', '').replace('.txt', '')
                    score = _score_search_match(query, title)
                    idx = content.find(query)
                    start = max(0, idx - 60)
                    end = min(len(content), idx + len(query) + 60)
                    snippet = content[start:end].replace('\n', ' ').strip()[:150]
                    add_result(title, snippet, '中医开源医典 (tcmoc)',
                               os.path.relpath(fp, base_sources), score)
            except:
                continue
    
    # 3. 搜索 cleaned 目录（已清洗的笈成经典，文件名中标明了经名）
    clean_dir = os.path.join(base_sources, 'cleaned')
    for root, dirs, files in os.walk(clean_dir):
        for f in sorted(files):
            if not f.endswith('.md') or f.endswith('copyright.md') or f.endswith('privacy.md'):
                continue
            if '识典' in f:
                continue  # 识典数据需登录，爬回来的是垃圾
            fp = os.path.join(root, f)
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                    if query not in content:
                        continue
                    title = f.replace('.md', '').replace('.trad', '')
                    score = _score_search_match(query, title) + 5  # cleaned 稍微加分
                    idx = content.find(query)
                    start = max(0, idx - 60)
                    end = min(len(content), idx + len(query) + 60)
                    snippet = content[start:end].replace('\n', ' ').strip()[:150]
                    add_result(title, snippet, '笈成古籍 (已清洗)',
                               os.path.relpath(fp, base_sources), score)
            except:
                continue

    # 4. 搜索 SEP 哲学知识库（天下文章一大抄 🌙）
    sep_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
    if os.path.isfile(sep_path):
        try:
            with open(sep_path, 'r', encoding='utf-8') as _sf:
                sep_data = json.load(_sf)
            for key, entry in sep_data.items():
                name_cn = entry.get('name', '')
                title = entry.get('title', '')
                body = entry.get('body', '')
                if query in name_cn or query in title or query in body or query.lower() in key:
                    # 从 body 中截取包含 query 的片段
                    candidates = [name_cn, title, body]
                    best_snippet = title[:200]
                    for c in candidates:
                        if query in c or query.lower() in c:
                            idx = c.find(query)
                            start = max(0, idx - 60)
                            end = min(len(c), idx + len(query) + 60)
                            best_snippet = c[start:end].replace('\n', ' ').strip()
                            break
                    score = 30 if (query in name_cn or query.lower() in key) else 15
                    add_result(f"{name_cn} · {key}", best_snippet[:180],
                               'Stanford Encyclopedia of Philosophy (SEP)',
                               'data/sep_core.json', score)
        except Exception:
            pass

    # 按得分排序
    results.sort(key=lambda r: -r['_score'])
    # 去掉内部得分字段
    for r in results:
        del r['_score']
    return results[:12]


if __name__ == '__main__':
    print(f"\n{'═' * 50}")
    print("🌙 莫名心 · 中医小站 v2")
    print(f"{'═' * 50}")
    print(f"  三个 Tab 齐了:")
    print(f"    🩺 辨证食疗 — 原版诊断+食疗")
    print(f"    🌀 五运六气 — 干支·岁运·司天·客主加临")
    print(f"    📖 经典参考 — 古籍搜索·倪海厦索引")
    print(f"{'═' * 50}")
    print(f"  打开浏览器访问:")
    print(f"  → http://localhost:{PORT}")
    print(f"  → http://<本机IP>:{PORT}  (同局域网可用)")
    print(f"{'═' * 50}\n")
    server = HTTPServer(('0.0.0.0', PORT), DiagnoseHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  小站已关闭。心哥回头见 🌙")
        server.server_close()
