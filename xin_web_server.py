#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
心哥 · 辨证食疗 Web 服务 v1
出门帮人用的诊断小站
"""

import json
import os
import sys
import html
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request

# 导入诊断引擎
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xin_claw_doctor import differentiate, get_dietary_plan, get_treatment_plan, nature_to_phase, SYNDROME_KNOWLEDGE

PORT = 8080

# ═══════════════════════════════════════════
# HTML 前端（内置，单文件）
# ═══════════════════════════════════════════

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>心哥 · 辨证食疗</title>
<style>
:root {
  --bg: #f5f0eb;
  --card: #ffffff;
  --text: #2c2c2c;
  --text-light: #6b6b6b;
  --accent: #b8453a;
  --accent-light: #e8d5d0;
  --green: #4a7c59;
  --blue: #3a5a7c;
  --gold: #c9a84c;
  --radius: 14px;
  --shadow: 0 2px 12px rgba(0,0,0,0.06);
}

/* 深色主题 */
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
  --shadow: 0 2px 12px rgba(0,0,0,0.3);
}
body.dark-theme .symptom-item:hover { background: #2a2a30 !important; }
body.dark-theme .tag { background: #2a2a30; border-color: #3a3a40; }
body.dark-theme .tag.selected { background: #3a2824; border-color: #d86050; }
body.dark-theme .recipe-card { background: #222228; }
body.dark-theme .error-msg { background: #2a1818; color: #d86050; }
body.dark-theme .card { border: 1px solid #2a2a30; }
body.dark-theme .herb-tag { background: var(--green); }
body.dark-theme .avoid-tag { background: #2a2018; color: #c07050; }
body.dark-theme .acupoint { background: var(--blue); }
body.dark-theme .custom-input input { background: #222228; border-color: #3a3a40; color: var(--text); }
body.dark-theme textarea { background: #222228; border-color: #3a3a40 !important; color: var(--text); }
body.dark-theme input[type="number"] { background: #222228; border-color: #3a3a40; color: var(--text); }
body.dark-theme select { background: #222228; border-color: #3a3a40; color: var(--text); }
body.dark-theme .tag-small { background: #2a2a30; border-color: #3a3a40; }
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
.header {
  text-align: center;
  padding: 20px 0 16px;
}
.header h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 1px;
}
.header .sub {
  font-size: 13px;
  color: var(--text-light);
  margin-top: 4px;
}
.card {
  background: var(--card);
  border-radius: var(--radius);
  padding: 20px;
  margin-bottom: 12px;
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
  color: var(--text-light);
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
  color: var(--text-light);
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
  color: var(--text-light);
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
.footer {
  text-align: center;
  font-size: 12px;
  color: var(--text-light);
  padding: 20px 0;
}
@media (max-width: 420px) {
  .symptom-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 380px) {
  body { padding: 10px; }
  .header h1 { font-size: 19px; }
  .card { padding: 14px; border-radius: 12px; }
  .symptom-item { font-size: 13px; padding: 6px; }
  .tag { font-size: 13px; padding: 6px 12px; }
}

/* 增大触摸区域 - 移动端友好 */
button, .tag, .symptom-item { cursor: pointer; -webkit-tap-highlight-color: transparent; }
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

/* 暗色模式开关 */
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
</style>
</head>
<body>

<!-- Toast 容器 -->
<div class="toast-container" id="toastContainer"></div>

<!-- 暗色模式开关 -->
<button class="theme-toggle" id="themeToggle" onclick="toggleDarkMode()" title="切换主题">🌙</button>

<div class="header">
  <nav style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;font-size:.85rem">
    <a href="/" style="color:#4a7dff;text-decoration:none">🏠 首页</a>
    <a href="/tools" style="color:#4a7dff;text-decoration:none">🧩 工具台</a>
    <a href="/daogui3" style="color:#4a7dff;text-decoration:none">🏛️ 道归3.0</a>
    <a href="/extensions" style="color:#4a7dff;text-decoration:none">🧩 扩展</a>
  </nav>
  <h1>🌙 莫名心 · 辨证食疗</h1>
  <div class="sub">填入症状，获得中医食疗与日常调理建议</div>
</div>

<!-- 输入区 -->
<div id="inputArea">
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
      <span class="tag" data-val="舌有裂纹">舌有裂纹</span>
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

  <button class="btn-primary" id="submitBtn" onclick="submitDiagnosis()">🩺 开始辨证</button>
</div>

<!-- 加载 -->
<div class="loading" id="loading" style="display:none">
  <div class="spinner"></div>
  <div>正在辨证…</div>
</div>

<!-- 结果区 -->
<div class="result-section" id="resultArea">
  <div class="result-header" id="resultHeader">
    <div class="dx-name"></div>
    <div class="dx-sub"></div>
  </div>

  <div class="card">
    <div class="card-title">🥗 推荐食材</div>
    <div id="herbTags"></div>
  </div>

  <div class="card">
    <div class="card-title">🚫 忌口</div>
    <div id="avoidTags"></div>
  </div>

  <div class="card">
    <div class="card-title">🍲 食疗方</div>
    <div id="recipeList"></div>
  </div>

  <div class="card">
    <div class="card-title">📍 穴位按压</div>
    <div id="acupointList"></div>
  </div>

  <div class="card">
    <div class="card-title">📋 日常调护</div>
    <div id="dailyCare"></div>
  </div>

  <div class="card">
    <div class="card-title">💚 情志与睡眠</div>
    <div id="emotionCare"></div>
  </div>

  <div class="card" id="traceCard" style="display:none">
    <details>
      <summary style="font-size:15px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:8px;padding:4px 0;">
        🧠 推理路径
        <span style="font-size:12px;font-weight:400;color:var(--text-light);margin-left:auto;">展开查看</span>
      </summary>
      <div id="traceContent" style="margin-top:12px;font-size:13px;line-height:1.7;"></div>
    </details>
  </div>

  <div class="card" id="westernCard" style="display:none">
    <div class="card-title">🏥 西医参考</div>
    <div id="westernInfo" style="font-size:14px;line-height:1.6;"></div>
  </div>

  <div class="card" id="knowledgeCard" style="display:none">
    <div class="card-title">🏛 知识图谱支撑</div>
    <div id="knowledgeInfo"></div>
  </div>

  <div class="card" id="errorCard" style="display:none">
    <div class="error-msg" id="errorMsg"></div>
  </div>

  <!-- ══════ 追加症状输入（对话式迭代） ══════ -->
  <div class="card" id="appendCard" style="display:none">
    <div class="card-title">💬 还有没有其他不舒服？</div>
    <div id="accumulatedSymptoms" style="font-size:13px;color:var(--text-light);margin-bottom:8px;"></div>
    <div style="display:flex;gap:8px;">
      <input type="text" id="appendInput"
        style="flex:1;padding:12px;border:2px solid #ddd;border-radius:10px;font-size:16px;outline:none;font-family:inherit;background:var(--card);color:var(--text);"
        placeholder="例如：最近还有点咳嗽…"
        onkeydown="if(event.key==='Enter') doAppend()">
      <button onclick="doAppend()"
        style="padding:12px 18px;background:var(--accent);color:#fff;border:none;border-radius:10px;font-size:15px;cursor:pointer;font-weight:500;white-space:nowrap;">追加</button>
    </div>
    <button id="appendSubmitBtn" onclick="finalSubmit()" style="display:none;width:100%;margin-top:10px;padding:12px;background:#4a7c59;color:#fff;border:none;border-radius:10px;font-size:14px;cursor:pointer;font-weight:500;">🔄 拿到全部症状了，重新辨证</button>
  </div>

  <button class="btn-primary" onclick="resetAll()" style="background:var(--text-light)">🔄 重新辨证</button>
</div>

<div class="footer">心哥 · 莫名心 · 本地辨证食疗</div>

<script>
// ═════════════════════════════════
// 暗色模式 & Toast 系统
// ═════════════════════════════════

(function initTheme(){
  try {
    const saved = localStorage.getItem('xiaozhan_dark_mode');
    if (saved === 'true') {
      document.body.classList.add('dark-theme');
      var btn = document.getElementById('themeToggle');
      if (btn) btn.textContent = '☀️';
    }
  } catch(e){}
})();

function toggleDarkMode() {
  var body = document.body;
  var btn = document.getElementById('themeToggle');
  if (!btn) return;
  var isDark = body.classList.toggle('dark-theme');
  btn.textContent = isDark ? '☀️' : '🌙';
  try { localStorage.setItem('xiaozhan_dark_mode', isDark); } catch(e){}
}

function showToast(msg, type) {
  type = type || 'info';
  var container = document.getElementById('toastContainer');
  if (!container) return;
  var toast = document.createElement('div');
  toast.className = 'toast toast-' + type;
  var icons = {error:'❌', success:'✅', info:'💡'};
  toast.innerHTML = (icons[type] || '💡') + ' ' + msg;
  container.appendChild(toast);
  setTimeout(function(){
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(function(){ toast.remove(); }, 300);
  }, 3000);
}

function renderMarkdown(text) {
  if (!text) return '';
  var html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^\s*[-*+] (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/^\s*\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/\n/g, '<br>');
  return html;
}

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

// 舌脉多选（可同时选多个）
document.querySelectorAll('.tag').forEach(t => {
  t.addEventListener('click', () => {
    t.classList.toggle('selected');
  });
});

// 症状关键词库（用于自然语言解析）
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
  '身热不扬': ['身热不扬','潮热','一阵热'],
  '头重如裹': ['头重','头沉','头蒙','脑袋重'],
  '脘痞': ['脘痞','胃堵','胃胀','堵得慌'],
  '纳呆': ['纳呆','不饿','没食欲'],
  '干咳': ['干咳','干咳无痰'],
  '鼻燥': ['鼻燥','鼻子干','鼻腔干'],
  '口舌生疮': ['口舌生疮','口腔溃疡','长口疮','嘴破','舌疮'],
  '下肢冷': ['下肢冷','腿冷','脚凉','下半身冷'],
  '颧红': ['颧红','颧骨红','脸红'],
};

function parseNLP() {
  const text = document.getElementById('nlpInput').value.trim();
  if (!text) {
    document.getElementById('nlpResult').textContent = '⚠️ 请先输入不舒服的症状';
    return;
  }
  
  // 清除上次的结果
  document.getElementById('nlpResult').textContent = '正在识别…';
  
  // 遍历关键词库，匹配症状
  const matchedSymptoms = new Set();
  for (const [symptom, keywords] of Object.entries(SYMPTOM_KEYWORDS)) {
    for (const kw of keywords) {
      if (text.includes(kw)) {
        matchedSymptoms.add(symptom);
        break;
      }
    }
  }
  
  if (matchedSymptoms.size === 0) {
    document.getElementById('nlpResult').textContent = '😅 没识别出常见症状，请手动勾选或直接输入';
    return;
  }
  
  // 勾选匹配的复选框
  const checkboxes = document.querySelectorAll('#symptomGrid input[type="checkbox"]');
  checkboxes.forEach(cb => {
    if (matchedSymptoms.has(cb.value)) {
      cb.checked = true;
    }
  });
  
  const matchList = Array.from(matchedSymptoms).join('、');
  document.getElementById('nlpResult').innerHTML = '✅ 已识别症状：<strong>' + matchList + '</strong>';
  
  // 滚动到输入区
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function submitDiagnosis() {
  // 收集症状
  const symptomEls = document.querySelectorAll('#symptomGrid input:checked');
  const symptoms = [];
  symptomEls.forEach(e => symptoms.push(e.value));
  for (const s of customSymptoms) symptoms.push(s);

  if (symptoms.length === 0) {
    showToast('请至少选择或输入一个症状', 'error');
    return;
  }

  // 舌脉（多选→逗号分隔）
  const tongueEls = document.querySelectorAll('#tongueGroup .selected');
  const pulseEls = document.querySelectorAll('#pulseGroup .selected');
  const tongue = tongueEls.length ? Array.from(tongueEls).map(e => e.dataset.val).join(',') : '';
  const pulse = pulseEls.length ? Array.from(pulseEls).map(e => e.dataset.val).join(',') : '';

  // 显示加载
  document.getElementById('inputArea').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  document.getElementById('resultArea').classList.remove('visible');

  try {
    const body = JSON.stringify({
      symptoms: symptoms,
      tongue: tongue,
      pulse: pulse
    });

    const res = await fetch('/diagnose', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
      body: body
    });
    const data = await res.json();

    document.getElementById('loading').style.display = 'none';
    showResult(data);
    initAppend(symptoms, tongue, pulse);
  } catch (e) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('inputArea').style.display = 'block';
    alert('网络错误: ' + e.message);
  }
}

// ═════════════════════════════════
// 追加症状 — 对话式迭代
// ═════════════════════════════════

var _allSymptoms = [];  // 累积症状
var _lastTongue = '';
var _lastPulse = '';
var _submitting = false;

function initAppend(symptoms, tongue, pulse) {
  _allSymptoms = symptoms.slice();
  _lastTongue = tongue;
  _lastPulse = pulse;
  document.getElementById('appendCard').style.display = 'block';
  updateAccumulated();
}

function updateAccumulated() {
  var el = document.getElementById('accumulatedSymptoms');
  if (_allSymptoms.length) {
    el.innerHTML = '<span style="font-weight:600">已收集症状：</span>' +
      _allSymptoms.map(function(s,i){ return '<span style="display:inline-block;padding:2px 8px;margin:2px;background:var(--accent-light);border-radius:12px;font-size:12px;">' + s + '</span>'; }).join('') +
      ' <span style="font-size:11px;color:var(--text-light);">(' + _allSymptoms.length + '项)</span>';
  } else {
    el.innerHTML = '';
  }
}

function doAppend() {
  var inp = document.getElementById('appendInput');
  var text = inp.value.trim();
  if (!text) return;
  // 智能分词：支持逗号/顿号/分号分隔
  var newSymptoms = text.split(/[，,、；;]/).map(function(s){ return s.trim(); }).filter(function(s){ return s.length >= 2; });
  if (!newSymptoms.length) { showToast('请描述不舒服的感觉', 'error'); return; }
  for (var i = 0; i < newSymptoms.length; i++) {
    if (_allSymptoms.indexOf(newSymptoms[i]) === -1) {
      _allSymptoms.push(newSymptoms[i]);
    }
  }
  inp.value = '';
  updateAccumulated();
  showToast('已追加 ' + newSymptoms.length + ' 项症状', 'success');
  showAppendBtn();
}

function showAppendBtn() {
  document.getElementById('appendSubmitBtn').style.display = 'block';
}

function finalSubmit() {
  if (_submitting) return;
  _submitting = true;
  var btn = document.getElementById('appendSubmitBtn');
  btn.textContent = '⏳ 重新辨证中…';
  btn.disabled = true;
  
  document.getElementById('inputArea').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  
  fetch('/diagnose', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      symptoms: _allSymptoms,
      tongue: _lastTongue,
      pulse: _lastPulse
    })
  }).then(function(r) { return r.json(); })
    .then(function(data) {
      document.getElementById('loading').style.display = 'none';
      _submitting = false;
      btn.textContent = '🔄 重新辨证';
      btn.disabled = false;
      showResult(data);
    }).catch(function(e) {
      document.getElementById('loading').style.display = 'none';
      _submitting = false;
      btn.textContent = '🔄 重新辨证';
      btn.disabled = false;
      showToast('网络错误: ' + e.message, 'error');
    });
}

function showResult(data) {
  document.getElementById('resultArea').classList.add('visible');

  if (data.error) {
    document.getElementById('errorCard').style.display = 'block';
    document.getElementById('errorMsg').textContent = data.error;
    return;
  }

  // 头部
  const h = document.getElementById('resultHeader');
  h.querySelector('.dx-name').textContent = data.syndrome || '未确定';
  h.querySelector('.dx-sub').textContent = `${data.organ} · ${data.nature} · ${data.principle}`;

  // 特殊模式
  if (data.special_pattern) {
    const sp = document.createElement('div');
    sp.style.cssText = 'font-size:13px;opacity:0.9;margin-top:6px;background:rgba(255,255,255,0.2);padding:6px 10px;border-radius:8px;';
    sp.textContent = `⚠ ${data.special_pattern}: ${data.special_desc || ''}`;
    h.appendChild(sp);
  }

  // 兼夹证展示
  if (data.concurrent_syndrome) {
    var cs = data.concurrent_syndrome;
    var csDiv = document.createElement('div');
    csDiv.style.cssText = 'margin-top:8px;padding:8px 10px;background:rgba(232,213,208,0.4);border-radius:8px;border-left:3px solid #b8453a;';
    csDiv.innerHTML = '<div style="font-size:12px;font-weight:600;color:#b8453a;">➕ 兼夹证</div>' +
      '<div style="font-size:14px;font-weight:500;margin-top:2px;">' + cs.syndrome + '</div>' +
      '<div style="font-size:12px;color:#888;">' + cs.match_detail + '</div>';
    h.appendChild(csDiv);
  }

  // 推荐食材
  if (data.recommended_ingredients && data.recommended_ingredients.length) {
    document.getElementById('herbTags').innerHTML = data.recommended_ingredients.map(h =>
      `<span class="herb-tag">${h}</span>`
    ).join('');
  }

  // 忌口
  if (data.foods_to_avoid && data.foods_to_avoid.length) {
    document.getElementById('avoidTags').innerHTML = data.foods_to_avoid.map(f =>
      `<span class="avoid-tag">${f}</span>`
    ).join('');
  }

  // 食疗方
  if (data.recipes && data.recipes.length) {
    document.getElementById('recipeList').innerHTML = data.recipes.map(r =>
      `<div class="recipe-card">${r}</div>`
    ).join('');
  }

  // 穴位
  if (data.acupoints && data.acupoints.length) {
    document.getElementById('acupointList').innerHTML =
      `<div class="acupoint-list">${data.acupoints.map(a =>
        `<span class="acupoint">${a}</span>`
      ).join('')}</div>`;
  }

  // 日常调护
  if (data.daily_care && data.daily_care.length) {
    document.getElementById('dailyCare').innerHTML = data.daily_care.map(d =>
      `<div class="tx-item">🟢 ${d}</div>`
    ).join('');
  }

  // 情志睡眠
  const emotion = [];
  if (data.emotional_care) {
    if (Array.isArray(data.emotional_care)) {
      data.emotional_care.forEach(e => emotion.push(e));
    } else {
      emotion.push(data.emotional_care);
    }
  }
  if (data.sleep_advice) emotion.push(data.sleep_advice);
  if (emotion.length) {
    document.getElementById('emotionCare').innerHTML = emotion.map(e =>
      `<div class="tx-item">🌙 ${e}</div>`
    ).join('');
  }

  // 推理路径
  if (data.reasoning_trace && data.reasoning_trace.length) {
    document.getElementById('traceCard').style.display = 'block';
    const traceHtml = data.reasoning_trace.map((t, i) => {
      const isTop = i === 0;
      const scorePct = Math.round(t.匹配度 * 100);
      const matched = Array.isArray(t.匹配症状) ? t.匹配症状.join('、') : t.匹配症状;
      return `<div style="padding:10px 0;${i > 0 ? 'border-top:1px solid #f0ebe6;' : ''}${isTop ? 'background:#faf7f4;border-radius:10px;padding:12px;margin:-4px 0 0;' : ''}">
        <div style="display:flex;align-items:center;gap:8px;">
          <span style="font-weight:600;font-size:14px;">${isTop ? '🏆 ' : ''}${t.证型}</span>
          <span style="font-size:12px;background:${isTop ? 'var(--accent)' : '#e8d5d0'};color:${isTop ? 'white' : 'var(--accent)'};padding:2px 8px;border-radius:10px;">${scorePct}%</span>
          <span style="font-size:12px;color:var(--text-light);margin-left:auto;">${t.病位} · ${t.病性}</span>
        </div>
        <div style="margin-top:4px;color:var(--text-light);">
          匹配: ${t.匹配详情} · 症状: ${matched || '-'}
        </div>
        <div style="color:var(--text-light);font-size:12px;">治则: ${t.治则}</div>
      </div>`;
    }).join('');
    document.getElementById('traceContent').innerHTML = traceHtml;
  }

  // 西医建议
  var westHtml = '';
  
  // 证型→西医疾病对照
  if (data.western_diseases && data.western_diseases.length) {
    westHtml += '<div style="margin-bottom:6px;font-weight:500">🏥 根据辨证，建议排查：</div>';
    data.western_diseases.forEach(function(d) {
      westHtml += '<div style="padding:3px 0;font-size:13px">· ' + d + '</div>';
    });
  }
  
  if (data.knowledge && data.knowledge.symmap && data.knowledge.symmap.diseases && data.knowledge.symmap.diseases.length) {
    westHtml += '<div style="margin-top:8px;font-weight:500">🔬 关联西医疾病（SymMap）：</div>';
    data.knowledge.symmap.diseases.slice(0,6).forEach(function(d) {
      westHtml += '<div style="padding:4px 0;border-bottom:1px solid #f0ebe6">';
      westHtml += '· ' + (d.name || '');
      if (d.icd10) westHtml += ' <span style="font-size:11px;color:#888">(' + d.icd10 + ')</span>';
      westHtml += '</div>';
    });
  }
  
  if (westHtml) {
    document.getElementById('westernCard').style.display = 'block';
    document.getElementById('westernAdviceContent').innerHTML = westHtml;
  }
    if (data.knowledge.symmap.matched_symptoms && data.knowledge.symmap.matched_symptoms.length) {
      wHtml += '<div style="margin-top:8px;font-weight:500">📊 症状库匹配：</div>';
      data.knowledge.symmap.matched_symptoms.slice(0,3).forEach(function(s) {
        wHtml += '<div style="padding:2px 0;font-size:13px">· ' + (s.name || '') + (s.definition ? ' — ' + s.definition.slice(0,60) : '') + '</div>';
      });
    }
    // 西医疾病名称中英对照
    var DISEASE_ZH = {
      'Insomnia': '失眠症',
      'Fatal Familial Insomnia': '致死性家族性失眠症',
      'Anxiety': '焦虑症',
      'Depression': '抑郁症',
      'Hypertension': '高血压',
      'Diabetes': '糖尿病',
      'Coronary heart disease': '冠心病',
      'Stroke': '脑冢中',
      'Gastritis': '胃炎',
      'Insomnia disorder': '失眠症',
      'Liver disease': '肝病',
      'Kidney disease': '肾病',
      'Anemia': '贫血',
      'Headache': '头痛',
      'Migraine': '偏头痛',
      'Dizziness': '头晕',
      'Fatigue': '疲劳',
      'Constipation': '便秘',
      'Diarrhea': '腹泻',
      'Palpitation': '心悸',
      'Allergic rhinitis': '过敏性鼻炎',
      'Asthma': '哮喘',
      'Tinnitus': '耳鸣',
      'Shoulder pain': '肩痛',
      'Low back pain': '腰痛',
    };
    var wHtml = '<div style="margin-bottom:8px;font-weight:500">\U0001f52c 可能关联的西医疾病：</div>';
    data.knowledge.symmap.diseases.slice(0,6).forEach(function(d) {
      var enName = d.name || '';
      var zhName = DISEASE_ZH[enName] || enName;
      wHtml += '<div style="padding:4px 0;border-bottom:1px solid #f0ebe6">';
      wHtml += '\u00b7 ' + zhName;
      if (enName && DISEASE_ZH[enName]) wHtml += ' <span style="font-size:11px;color:#888">(' + enName + ')</span>';
      if (d.icd10) wHtml += ' <span style="font-size:11px;color:#888">ICD10: ' + d.icd10 + '</span>';
      wHtml += '</div>';
    });
    if (data.knowledge.symmap.matched_symptoms && data.knowledge.symmap.matched_symptoms.length) {
      wHtml += '<div style="margin-top:8px;font-weight:500">\U0001f4ca 症状库匹配：</div>';
      data.knowledge.symmap.matched_symptoms.slice(0,3).forEach(function(s) {
        wHtml += '<div style="padding:2px 0;font-size:13px">\u00b7 ' + (s.name || '') + (s.definition ? ' \u2014 ' + s.definition.slice(0,60) : '') + '</div>';
      });
    }
    document.getElementById('westernInfo').innerHTML = wHtml;
  }

  // 知识图谱信息
  if (data.knowledge && data.knowledge.herb_props && data.knowledge.herb_props.length) {
    document.getElementById('knowledgeCard').style.display = 'block';
    document.getElementById('knowledgeInfo').innerHTML = `
      <div style="font-size:13px;color:var(--text-light);margin-bottom:8px;">
        🏛 TCM-MKG · ${data.knowledge.herbs || '?'}味药 / ${data.knowledge.medicines || '?'}方
        <div style="font-size:11px;opacity:0.6;margin-top:4px;">📅 数据版本: ${data.knowledge.version || '初次部署'} · 每月1日自动更新</div>
        ${data.knowledge.symmap ? `
        <div style="margin-top:8px;padding-top:8px;border-top:1px solid #e8ddd6;">
          <div style="font-size:12px;font-weight:600;color:var(--text-light);margin-bottom:4px;">📊 SymMap 中西医关联</div>
          <div style="font-size:12px;color:var(--text-light);">🔬 ${data.knowledge.symmap.total_diseases || '?'}种疾病 / ${data.knowledge.symmap.total_compounds || '?'}种化合物</div>
          ${data.knowledge.symmap.diseases && data.knowledge.symmap.diseases.length ? `
          <div style="font-size:12px;font-weight:500;margin-top:6px;color:var(--blue);">关联西医疾病:</div>
          ${data.knowledge.symmap.diseases.slice(0,4).map(d =>
            `<div style="font-size:12px;padding:2px 0;">· ${d.name}${d.icd10 ? ' (ICD10: ' + d.icd10 + ')' : ''}</div>`
          ).join('')}
          ` : ''}
          ${data.knowledge.symmap.matched_symptoms && data.knowledge.symmap.matched_symptoms.length ? `
          <div style="font-size:12px;font-weight:500;margin-top:6px;color:var(--green);">SymMap 症状库匹配:</div>
          ${data.knowledge.symmap.matched_symptoms.slice(0,3).map(s =>
            `<div style="font-size:12px;padding:2px 0;">· ${s.name}${s.definition ? ': ' + s.definition : ''}</div>`
          ).join('')}
          ` : ''}
        </div>
        ` : ''}
      </div>
      ${data.knowledge.herb_props.slice(0,8).map(h => `
        <div style="font-size:13px;padding:4px 0;">
          · ${h.name}${h.info ? ' — ' + h.info : ''}
        </div>
      `).join('')}
    `;
  }

  // 滚动到结果顶部
  window.scrollTo({ top: 0, behavior: 'smooth' });

function resetAll() {
  document.getElementById('resultArea').classList.remove('visible');
  document.getElementById('errorCard').style.display = 'none';
  document.getElementById('inputArea').style.display = 'block';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
</script>
<script>
(function(){
  var b=document.createElement('div');
  b.innerHTML='🔊 朗读';
  b.style.cssText='position:fixed;bottom:24px;right:24px;z-index:9999;background:#4a7dff;color:#fff;border:none;border-radius:20px;padding:10px 18px;font-size:14px;cursor:pointer;box-shadow:0 2px 12px rgba(74,125,255,.4);display:none;font-family:sans-serif';
  document.body.appendChild(b);
  var a=false;
  b.onclick=function(){
    if(a){window.speechSynthesis.cancel();a=false;b.innerHTML='🔊 朗读';b.style.background='#4a7dff';return}
    var c=document.querySelector('article,.content,.markdown-body,main');
    var t=c?c.innerText:document.body.innerText;
    t=t.replace(/\\s+/g,' ').trim();
    if(t.length<10){b.innerHTML='❌ 无内容';setTimeout(function(){b.innerHTML='🔊 朗读'},1500);return}
    var u=new SpeechSynthesisUtterance(t);
    u.lang='zh-CN';u.rate=1.0;
    u.onend=function(){a=false;b.innerHTML='🔊 朗读';b.style.background='#4a7dff'};
    window.speechSynthesis.speak(u);a=true;b.innerHTML='⏹ 停止';b.style.background='#e74c3c'
  };
  if(document.querySelector('article,.content,.markdown-body,main'))b.style.display='flex'
})();
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════
# HTTP 服务
# ═══════════════════════════════════════════

class DiagnoseHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'404')

    def do_POST(self):
        if self.path == '/diagnose':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            try:
                data = json.loads(body)
                symptoms = data.get('symptoms', [])
                tongue = data.get('tongue', '')
                pulse = data.get('pulse', '')
                result = run_diagnosis(symptoms, tongue, pulse)
                self._json_response(200, result)
            except Exception as e:
                self._json_response(200, {'error': f'诊断出错: {str(e)}'})
        else:
            self._json_response(404, {'error': 'not found'})

    def _json_response(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        # 安静日志
        print(f"[心哥小站] {args[0]} {args[1]} {args[2]}")


def run_diagnosis(symptoms, tongue, pulse):
    """执行辨证并返回结构化结果"""
    # 排除空字符串
    symptoms = [s for s in symptoms if s.strip()]

    dx = differentiate(symptoms, tongue, pulse)

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

        # ════════ 兼夹证合并 ════════
        concurrent = dx.get('兼夹证')
        result['concurrent_syndrome'] = concurrent
        if concurrent:
            cs_name = concurrent.get('syndrome', '')
            cs_info = SYNDROME_KNOWLEDGE.get(cs_name) if cs_name else None
            if cs_info:
                # 合并食材（去重）
                for ing in cs_info.get('recommended', []):
                    if ing not in result['recommended_ingredients']:
                        result['recommended_ingredients'].append(ing)
                # 合并忌口（去重）
                for av in cs_info.get('avoid', []):
                    if av not in result['foods_to_avoid']:
                        result['foods_to_avoid'].append(av)
                # 合并食疗方
                for r in cs_info.get('foods', []):
                    r_name = r if isinstance(r, str) else r.get('name', r)
                    if r_name not in result['recipes']:
                        result['recipes'].append(r_name)
            # 合并穴位/调护（去重）
            cs_tx = get_treatment_plan(cs_name) if cs_name else None
            if cs_tx and tx:
                for ap in cs_tx.get('acupoints', []):
                    if ap not in result.get('acupoints', []):
                        result['acupoints'].append(ap)
                for dc in cs_tx.get('daily_care', []):
                    if dc not in result.get('daily_care', []):
                        result['daily_care'].append(dc)
    else:
        result['recommended_ingredients'] = []
        result['foods_to_avoid'] = []
        result['recipes'] = []
        result['concurrent_syndrome'] = None

    # ══════ 证型→西医疾病对照 ══════
    try:
        from xin_claw_doctor import SYNDROME_WESTERN_MAP
        syn = result.get('syndrome', '')
        refs = SYNDROME_WESTERN_MAP.get(syn, [])
        result['western_diseases'] = refs
        # 兼证也加进去
        cs = result.get('concurrent_syndrome')
        if cs:
            cs_name = cs.get('syndrome', '')
            for d in SYNDROME_WESTERN_MAP.get(cs_name, []):
                if d not in refs:
                    refs.append(d)
            result['western_diseases'] = refs
    except Exception:
        result['western_diseases'] = []

    # 知识图谱补充（TCM-MKG + SymMap 双源）
    try:
        from xin_knowledge import (knowledge_base_status, get_herb_properties,
                                   get_herb_flavors, get_herb_nature, lookup_herb,
                                   symmap_enrich)
        
        # TCM-MKG 性味归经
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
        
        # SymMap 补充
        sym = symmap_enrich(
            syndrome_name=result.get('syndrome', ''),
            symptoms=[s for s in symptoms if s.strip()]
        )
        
        sym_diseases = sym.get('related_diseases', [])
        sym_syndromes = sym.get('syndromes', [])
        sym_matched_symptoms = sym.get('matched_symptoms', [])
        sym_status = sym.get('status', {})
        
        result['knowledge'] = {
            'version': kb.get('version', '未知'),
            'herbs': kb.get('herbs', 0),
            'medicines': kb.get('medicines', 0),
            'herb_props': herb_props,
            'symmap': {
                'diseases': sym_diseases[:5],
                'matched_symptoms': sym_matched_symptoms[:5],
                'total_diseases': sym_status.get('diseases', 0),
                'total_compounds': sym_status.get('compounds', 0),
            },
        }
    except Exception as e:
        result['knowledge'] = {}

    return result


if __name__ == '__main__':
    print(f"\n{'═' * 50}")
    print("🌙 心哥 · 辨证食疗小站")
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


# ===== 七月二十六日模块 · 快速重建 =====
import requests, hashlib, uuid, re, time

# 五运六气相关
def get_yunqi_data(date_str=None):
    """获取五运六气数据，支持日期字符串 '2026-07-29'"""
    from datetime import date, datetime
    try:
        from 五运六气 import 推算
        if date_str:
            try:
                d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
            except:
                d = date(int(date_str), 1, 1) if str(date_str).isdigit() else date.today()
        else:
            d = date.today()
        return 推算(d)
    except Exception as e:
        return {"error": f"五运六气：{str(e)}"}

def _本地五运六气():
    """本地五运六气推算"""
    from 五运六气 import 推算
    return 推算()

# AI问答
def _get_ai_key():
    """获取DeepSeek API密钥（从OpenClaw auth配置读取）"""
    import json as _j
    try:
        auth_file = os.path.expanduser('~/.openclaw/agents/main/agent/auth-profiles.json')
        with open(auth_file) as _fj:
            c = _j.load(_fj)
        return c.get('profiles',{}).get('deepseek:default',{}).get('key', '')
    except:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '密码.json')) as _fj:
                c = _j.load(_fj)
            return c.get('api_key', '')
        except:
            return ''

def ai_ask(question, context=""):
    """AI问答（直接调用DeepSeek API）"""
    if not question.strip():
        return {"success": False, "error": "问题不能为空"}
    
    import json as _j
    api_key = _get_ai_key()
    if not api_key:
        return {"success": False, "error": "未配置API密钥"}
    
    messages = [{"role": "system", "content": "你是莫名心，心哥小站的AI助手。回答简洁、有深度、中文。"}]
    if context:
        messages.append({"role": "user", "content": context})
    messages.append({"role": "user", "content": question})
    
    try:
        import urllib.request as _ur
        payload = _j.dumps({
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 2000
        }).encode()
        req = _ur.Request("https://api.deepseek.com/chat/completions",
                         data=payload,
                         headers={
                             "Content-Type": "application/json",
                             "Authorization": "Bearer " + api_key
                         })
        resp = _ur.urlopen(req, timeout=30)
        result = _j.loads(resp.read())
        answer = result["choices"][0]["message"]["content"]
        return {"success": True, "answer": answer}
    except Exception as e:
        return {"success": False, "error": str(e)}

# 哲思搜索
def search_knowledge_refs(keyword):
    """搜索哲思知识库"""
    import json as _j
    sep_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
    results = []
    try:
        with open(sep_file) as _sf:
            lib = _j.load(_sf)
        k = keyword.lower()
        for slug, entry in lib.items():
            if k in slug.lower() or k in entry.get('name', '').lower():
                results.append({"slug": slug, "name": entry.get('name', slug), "title": entry.get('title', '')})
        return results[:20]
    except:
        return []

# 本地词条
def _本地词条_加载():
    """加载本地词条系统"""
    import json as _j
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', '本地词条.json')
    try:
        with open(p) as _f:
            return _j.load(_f)
    except:
        return {}

# 哲学处理函数
def handle_philosophy_fetch(data):
    """在线抓取SEP哲学条目并存入本地库"""
    slug = data.get("slug", "").strip().lower()
    if not slug:
        return {"success": False, "error": "需要 slug 参数"}
    
    url = f"https://plato.stanford.edu/entries/{slug}/"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode('utf-8', errors='ignore')
        
        tm = re.search(r'<title>([^<]+)', html)
        ps = re.findall(r'<p[^>]*>([^<]{30,})</p>', html)
        body = '\n'.join(p.strip() for p in ps[:20])[:5000]
        
        if not body:
            return {"success": False, "error": "条目内容为空"}
        
        # 写入本地库
        sep_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
        import json as _j
        try:
            with open(sep_file) as _sf:
                lib = _j.load(_sf)
        except:
            lib = {}
        
        lib[slug] = {
            'name': data.get("name", slug.replace('-', ' ').title()),
            'title': tm.group(1)[:100] if tm else slug,
            'body': body
        }
        
        with open(sep_file, 'w', encoding='utf-8') as _sf:
            _j.dump(lib, _sf, ensure_ascii=False, indent=2)
        
        return {"success": True, "slug": slug, "chars": len(body), "total": len(lib)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_philosophy_translate(data):
    """哲思翻译——将SEP英文条目转为中文摘要"""
    slug = data.get("slug", "").strip().lower()
    content = data.get("content", "")
    
    sep_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sep_core.json')
    import json as _j
    
    try:
        with open(sep_file) as _sf:
            lib = _j.load(_sf)
    except:
        lib = {}
    
    # 如果提供了slug但没给content，从库里取
    if slug and slug in lib and not content:
        content = lib[slug].get('body', '')
        name = lib[slug].get('name', slug)
    else:
        name = slug
    
    if not content:
        return {"success": False, "error": "需要 content 或有效的 slug"}
    
    # AI摘要翻译（走本地Gateway）
    try:
        payload = _j.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": f"你是一位精通中西哲学的翻译家。请将以下关于「{name}」的英文哲学条目翻译为中文摘要，保留核心论点、术语和逻辑结构。语言精炼准确。"},
                {"role": "user", "content": content[:3000]}
            ],
            "max_tokens": 1500
        }).encode()
        req = urllib.request.Request("http://localhost:18789/v1/chat/completions",
                                     data=payload,
                                     headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=30)
        result = _j.loads(resp.read())
        answer = result["choices"][0]["message"]["content"]
        
        return {"success": True, "translation": answer, "slug": slug}
    except Exception as e:
        return {"success": False, "error": str(e), "fallback": content[:500]}


def handle_philosophy_concept(data):
    """概念词条生成——为哲学概念AI生成原创中文总结"""
    concept = data.get("concept", "").strip()
    context = data.get("context", "")
    
    if not concept:
        return {"success": False, "error": "需要 concept 参数"}
    
    prompt = f"请用中文为哲学概念「{concept}」写一篇精炼的总结（300-500字）。包括：核心定义、主要主张、历史影响、与当代生活的关联。"
    if context:
        prompt += f"\n\n参考上下文：{context[:1000]}"
    
    try:
        import json as _j
        payload = _j.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是莫名心。为心哥小站的哲思系统撰写概念词条。语言简洁有力，有深度但不晦涩。"},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 2000
        }).encode()
        req = urllib.request.Request("http://localhost:18789/v1/chat/completions",
                                     data=payload,
                                     headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = _j.loads(resp.read())
            answer = result["choices"][0]["message"]["content"]
        except:
            # 降级：尝试用api key直连deepseek
            ds_payload = _j.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000
            }).encode()
            ds_req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                                           data=ds_payload,
                                           headers={"Content-Type": "application/json",
                                                   "Authorization": "Bearer " + _get_ai_key()})
            ds_resp = urllib.request.urlopen(ds_req, timeout=30)
            result = _j.loads(ds_resp.read())
            answer = result["choices"][0]["message"]["content"]
        
        return {"success": True, "concept": concept, "summary": answer}
    except Exception as e:
        return {"success": False, "error": str(e)}

# TTS端点
def _tts_endpoint(text, lang="zh-CN"):
    if not text or not text.strip():
        return {"success": False, "error": "需要文本内容"}
    max_len = 2000
    segments = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    return {"success": True, "segments": segments, "lang": lang, "total_chars": len(text), "total_segments": len(segments)}
