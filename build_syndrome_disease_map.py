#!/usr/bin/env python3
"""
心哥 · 自动证型→西医疾病映射生成器
基于 TCM-MKG 知识图谱 + 症状匹配 + CPM链路

数据流:
  D1术语(证型) → 关联治法/病机
  → D3/D5 CPM→ICD11链 → D18疾病名
  + 症状关键词匹配D1疾病术语
"""

import csv, json, re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path.home() / '.xin_knowledge' / 'tcm_mkg'
OUTPUT = Path.home() / '.openclaw' / 'workspace' / 'auto_syndrome_disease_map.json'

# ── 加载数据 ──
def load_tsv(filename, key_field=None):
    rows = []
    with open(DATA_DIR / filename, 'r', encoding='utf-8') as f:
        r = csv.DictReader(f, delimiter='\t')
        for row in r:
            rows.append(row)
    return rows

print("📂 加载 TCM-MKG 数据...")
d1 = load_tsv('D1_TCM_terminology.tsv')
d3 = load_tsv('D3_CPM_TCMT.tsv')
d5 = load_tsv('D5_CPM_ICD11.tsv')
d18 = load_tsv('D18_ICD11.tsv')
print(f"  D1: {len(d1)} 术语")
print(f"  D3: {len(d3)} CPM→TCMT")
print(f"  D5: {len(d5)} CPM→ICD11")
print(f"  D18: {len(d18)} ICD11编码")

# ── 索引 ──
# D1: Chinese_term → TCMT_ID
d1_term_to_id = {row['Chinese_term']: row['TCMT_ID'] for row in d1}

# D1: TCMT_ID → 术语信息
d1_id_to_info = {row['TCMT_ID']: row for row in d1}

# D3: TCMT_ID → set of CPM_IDs
tcmt_to_cpms = defaultdict(set)
for row in d3:
    tcmt_to_cpms[row['TCMT_ID']].add(row['CPM_ID'])

# D3: CPM_ID → set of TCMT_IDs
cpm_to_tcmts = defaultdict(set)
for row in d3:
    cpm_to_tcmts[row['CPM_ID']].add(row['TCMT_ID'])

# D5: CPM_ID → set of ICD11 codes
cpm_to_icd = defaultdict(set)
for row in d5:
    cpm_to_icd[row['CPM_ID']].add(row['ICD11_code'])

# D18: ICD11_code → Chinese_term
icd_to_name = {row['ICD11_code']: row['Chinese_term'] for row in d18 if row['ICD11_code']}

# ── D1疾病术语索引 ──
# 按关键词索引D1中所有疾病名
disease_terms = [row for row in d1 if '疾病' in row.get('Chinese_group', '')]
print(f"\n📋 D1 中疾病相关术语: {len(disease_terms)} 条")

# ── 从 xin_claw_doctor 导入现有证型 ──
import sys
sys.path.insert(0, str(Path.home() / '.openclaw' / 'workspace'))
from xin_claw_doctor import SYNDROME_KNOWLEDGE

our_syndromes = list(SYNDROME_KNOWLEDGE.keys())
print(f"\n🏥 待匹配证型: {len(our_syndromes)} 个")

# ── 构建映射 ──
result_map = {}

for syn_name in our_syndromes:
    diseases = set()
    
    # 通道1：CPM链接的ICD11疾病
    tcmt_id = d1_term_to_id.get(syn_name)
    if tcmt_id:
        for cpm_id in tcmt_to_cpms.get(tcmt_id, set()):
            for icd_code in cpm_to_icd.get(cpm_id, set()):
                name = icd_to_name.get(icd_code)
                if name:
                    diseases.add(name)
    
    # 通道2：通过共享症状匹配D1疾病术语
    syn_info = SYNDROME_KNOWLEDGE.get(syn_name, {})
    symptoms = syn_info.get('symptoms', [])
    
    # 过滤掉纯舌脉诊描述（西医学无对应）
    tcm_only = {'舌淡', '舌红', '舌暗', '舌淡胖', '舌红少苔', '舌有齿痕',
                '苔白腻', '苔黄腻', '苔薄白', '苔白', '舌红少津',
                '脉细', '脉数', '脉细数', '脉弦', '脉沉', '脉弱', '脉滑', '脉浮',
                '脉沉迟', '脉沉弱', '脉缓弱', '脉弦数', '脉浮紧', '脉浮数',
                '脉滑数', '脉涩', '脉濡', '脉虚', '脉洪数', '脉沉细',
                '脉濡缓', '脉迟', '脉微弱', '脉沉迟弱'}
    real_symptoms = [s for s in symptoms if s not in tcm_only]
    
    for symptom in real_symptoms:
        # 在D1疾病术语中搜索
        for dt in disease_terms:
            dt_name = dt['Chinese_term']
            if len(dt_name) < 2: continue
            # 精确包含匹配
            if symptom in dt_name or dt_name in symptom:
                diseases.add(dt_name)
            # 字符重叠匹配（>=2即可）
            common = set(symptom) & set(dt_name)
            if len(common) >= 2:
                # 验证：症状中的每个字至少出现在疾病名或反之
                score = sum(1 for c in symptom if c in dt_name)
                if score >= 2 and score / max(len(symptom), 1) >= 0.4:
                    diseases.add(dt_name)
    
    # 通道3：D1中直接搜索关联疾病
    if tcmt_id:
        # 看这个证型对应的TCMT有没有关联其他疾病术语
        # D3中同一CPM下的其他TCMT可能有疾病信息
        for cpm_id in tcmt_to_cpms.get(tcmt_id, set()):
            for other_tcmt in cpm_to_tcmts.get(cpm_id, set()):
                other_info = d1_id_to_info.get(other_tcmt, {})
                other_group = other_info.get('Chinese_group', '')
                if '疾病' in other_group:
                    diseases.add(other_info['Chinese_term'])
    
    # 去重 + 排序
    clean = [d for d in diseases if d and len(d) >= 2]
    clean = list(dict.fromkeys(clean))  # 有序去重
    result_map[syn_name] = clean

# ── 统计 ──
with_diseases = sum(1 for v in result_map.values() if v)
total_diseases = sum(len(v) for v in result_map.values())
print(f"\n📊 结果统计:")
print(f"  有疾病映射的证型: {with_diseases}/{len(our_syndromes)}")
print(f"  总疾病关联数: {total_diseases}")

print("\n📋 映射详情:")
for syn, diseases in sorted(result_map.items()):
    status = '✅' if diseases else '❌'
    print(f"  {status} {syn}: {diseases[:6] if diseases else '(无匹配)'}")
    if len(diseases) > 6:
        print(f"     ... +{len(diseases)-6} 个")

# ── 保存 ──
with open(OUTPUT, 'w', encoding='utf-8') as f:
    json.dump(result_map, f, ensure_ascii=False, indent=2)
print(f"\n💾 已保存到: {OUTPUT}")
print(f"\n建议: 检查结果后，可以替代 xin_claw_doctor.py 中手动写的 SYNDROME_WESTERN_MAP")
