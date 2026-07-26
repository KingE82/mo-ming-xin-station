#!/bin/bash
# 一键同步到 GitHub
# 用法: bash 推到GitHub.sh
# 需要先设置 GitHub token: export GH_TOKEN=ghp_xxx

set -e

REPO="KingE82/daogui"
BRANCH="main"
MSG="小站更新 $(date +%Y-%m-%d)"

echo "🌙 同步到 $REPO ..."

# 确保在 workspace 目录
cd "$(dirname "$0")"

# 用 GitHub API 上传文件
upload() {
    local path="$1"
    local content="$2"
    local api_path="$3"

    # 先检查文件是否存在
    local sha=$(curl -s -H "Authorization: token $GH_TOKEN" \
        "https://api.github.com/repos/$REPO/contents/$api_path" \
        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null)

    # 上传
    local data=$(python3 -c "
import json, base64
with open('$path', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
print(json.dumps({'message': '$MSG', 'content': b64, 'sha': '$sha' if '$sha' else None}))
")

    curl -s -X PUT -H "Authorization: token $GH_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$data" \
        "https://api.github.com/repos/$REPO/contents/$api_path" > /dev/null
    
    echo "  ✅ $api_path"
}

# 上传文件列表
upload "更新日志_2026-07-26.md" "更新日志_2026-07-26.md"

# xin/ 目录下的核心文件
upload "xin_web_server.py" "xin/xin_web_server.py"
upload "app.py" "xin/app.py"
upload "xin_claw_doctor.py" "xin/xin_claw_doctor.py"
upload "phil_crawler.py" "xin/phil_crawler.py"

# 五运六气模块
upload "五运六气/__init__.py" "xin/五运六气/__init__.py"
upload "五运六气/calculator.py" "xin/五运六气/calculator.py"
upload "五运六气/eval.py" "xin/五运六气/eval.py"

echo ""
echo "✅ 同步完成！"
echo "   https://github.com/$REPO"
