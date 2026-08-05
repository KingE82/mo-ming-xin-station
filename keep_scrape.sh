#!/bin/bash
# 西医资料抓取进程 · 保活脚本（2026-08-05）
# 守护两个任务：
#   1) scrape_biology_FULL.py —— 生物学全量抓取
#   2) scrape_west_queue.py   —— 后续教材接力队列（微生物/化学/心理）
# 判断"任务是否完成"：生物学日志出现第47章 或 汇总行
cd /home/honor/.openclaw/workspace

bio_complete() {
    # 完成标志：日志包含"完成"汇总 或 跑到第47章
    grep -q "共下.*页" /tmp/scrape_biology_full.log 2>/dev/null && return 0
    grep -q "\[第47章\]" /tmp/scrape_biology_full.log 2>/dev/null && return 0
    return 1
}

while true; do
    # 生物学还没跑完但进程死了 → 重启（feed_vault 覆盖写同名文件，安全）
    if ! bio_complete && ! pgrep -f "scrape_biology_FULL" > /dev/null 2>&1; then
        echo "[$(date)] 生物学抓取停止且未完成，重启" >> /tmp/keep_scrape.log
        setsid nohup python3 -u rebuild_env/scrape_biology_FULL.py >> /tmp/scrape_biology_full.log 2>&1 < /dev/null &
        echo "[$(date)] 已重启 PID $!" >> /tmp/keep_scrape.log
    fi

    # 队列器：生物学完成后它才真正干活；它死了且生物学还在跑（意味着队列器等着接力）→ 重启
    if ! pgrep -f "scrape_west_queue" > /dev/null 2>&1; then
        if ! bio_complete; then
            # 生物学还在跑，队列器应该在场等待接力
            echo "[$(date)] 队列器停止（生物学未完），重启" >> /tmp/keep_scrape.log
            setsid nohup python3 -u rebuild_env/scrape_west_queue.py > /tmp/scrape_west_queue.log 2>&1 < /dev/null &
            echo "[$(date)] 已重启 PID $!" >> /tmp/keep_scrape.log
        fi
    fi

    # SEP 哲学词条爬取：没完成(1858词条)但进程死 → 重启（断点续传，安全）
    sep_done=$(python3 -c "
import json,os
try:
    d=json.load(open('/home/honor/.openclaw/workspace/data/sep_core.json',encoding='utf-8'))
    print(len(d)>=1800)
except: print('False')
")
    if [ "$sep_done" = "False" ] && ! pgrep -f "sep_fetch_full" > /dev/null 2>&1; then
        echo "[$(date)] SEP爬取停止且未完成，重启" >> /tmp/keep_scrape.log
        setsid nohup python3 -u data/sep_fetch_full.py >> /tmp/sep_fetch.log 2>&1 < /dev/null &
        echo "[$(date)] 已重启 PID $!" >> /tmp/keep_scrape.log
    fi

    sleep 45
done
