#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五运六气计算器 · CLI 入口
用法：
    python3 calculator.py               # 今天
    python3 calculator.py 2026-07-26    # 指定日期
"""

import sys
from datetime import date

# 同目录下的模块
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from 五运六气 import 推算, 客气六步分时, 五行属性


def 输出(日期: date):
    result = 推算(日期)
    year, month, day = 日期.year, 日期.month, 日期.day
    tg, dz = result["天干"], result["地支"]
    运 = result["岁运"]
    气 = {
        "司天": result["司天"],
        "在泉": result["在泉"],
        "客气六步": {},
    }
    # 从客气六步列表重建dict格式
    步名全 = ["初之气", "二之气", "三之气（司天）", "四之气", "五之气", "终之气（在泉）"]
    步名简 = ["初之气", "二之气", "三之气", "四之气", "五之气", "终之气"]
    for i, 步 in enumerate(result["客气六步"]):
        气["客气六步"][步名全[i]] = 步["客气"]
    
    当前 = result["当前"]
    五 = result["五行"]

    print("=" * 52)
    print(f"   五运六气 · {year}年 {tg}{dz}年")
    print("=" * 52)
    print()

    print("── 岁运 ──────────────────────────────")
    print(f"  干支：{tg}{dz}年")
    print(f"  岁运：{运['岁运']}运 {运['太过不及']}")
    print(f"  对应：{五['季节']}  {运['岁运']}行  脏腑：{'、'.join(五['脏腑'])}  "
          f"气候：{五['气候']}  五味：{五['五味']}")
    print()

    print("── 六气 ──────────────────────────────")
    print(f"  司天：{气['司天']}")
    print(f"  在泉：{气['在泉']}")
    print()

    print("── 客气六步 ───────────────────────────")
    for 步 in result["客气六步"]:
        print(f"  {步['时段']:<12} 客气：{步['客气']:<8}  主气：{步['主气']:<8}{步['标记']}")
        print(f"   {'':<12} {步['日期']}")
    print()

    print("── 当前 ──────────────────────────────")
    print(f"  日期：{year}年{month}月{day}日")
    print(f"  时位：{当前['时段']}")
    print(f"  主气：{当前['主气']}")
    print(f"  客气：{当前['客气']}")
    print(f"  区间：{当前['区间']}")
    print()

    print("── 简版（一行） ──────────────────────")
    print(f"  {year}年 {tg}{dz}年 | {运['岁运']}运{运['太过不及']} | "
          f"司天{气['司天']} 在泉{气['在泉']}")
    print(f"  当前：{当前['时段']} | 主气{当前['主气']}  客气{当前['客气']}")
    print("=" * 52)


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        d = date(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
    elif len(sys.argv) == 2:
        d = date.fromisoformat(sys.argv[1])
    else:
        d = date.today()

    输出(d)
