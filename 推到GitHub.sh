#!/bin/bash
# 一键同步到 GitHub · mo-ming-xin-station
# 用法: bash 推到GitHub.sh
# 需要先设置 token: export GH_TOKEN=你的完整token

REPO="KingE82/mo-ming-xin-station"
MSG="小站更新 $(date +%Y-%m-%d)"

cd "$(dirname "$0")"

upload() {
    local file="$1"
    local api_path="$2"
    
    # 获取 sha
    local sha=$(curl -s -H "Authorization: token $GH_TOKEN" \
        "https://api.github.com/repos/$REPO/contents/$api_path" 2>/dev/null \
        | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('sha',''))" 2>/dev/null)
    
    local data=$(python3 -c "
import json, base64
with open('$file', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
print(json.dumps({'message':'$MSG','content':b64,'sha':'$sha' if '$sha' else None}))
")
    
    curl -s -X PUT -H "Authorization: token $GH_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "https://api.github.com/repos/$REPO/contents/$api_path" > /dev/null \
        && echo "  ✅ $api_path" || echo "  ❌ $api_path"
}

echo "🌙 同步到 $REPO ..."

# 核心文件
upload "xin_web_server.py" "xin_web_server.py"
upload "app.py" "app.py"
upload "xin_claw_doctor.py" "xin_claw_doctor.py"
upload "phil_crawler.py" "phil_crawler.py"
upload "更新日志_2026-07-26.md" "更新日志_2026-07-26.md"

# 五运六气
upload "五运六气/__init__.py" "五运六气/__init__.py"
upload "五运六气/calculator.py" "五运六气/calculator.py"
upload "五运六气/eval.py" "五运六气/eval.py"

echo ""
echo "✅ 完成! https://github.com/$REPO"
