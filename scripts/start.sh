#!/bin/bash
# 小说一键启动脚本
# 用法: bash start.sh [命令]

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$BASE_DIR/scripts"

show_help() {
    echo ""
    echo "📚 小说创作工具"
    echo "=================="
    echo ""
    echo "用法: bash start.sh <命令>"
    echo ""
    echo "命令:"
    echo "  status         查看章节发布状态"
    echo "  export <章号>  导出指定章节为独立文件（默认导出最新）"
    echo "  export-all     批量导出全部章节"
    echo "  publish <章号> 发布指定章节（保存草稿）"
    echo "  write <章号>   用AI辅助写指定章节"
    echo "  feishu         同步到飞书文档"
    echo ""
    echo "示例:"
    echo "  bash start.sh status         # 查看状态"
    echo "  bash start.sh export 1       # 导出第1章"
    echo "  bash start.sh export-all     # 导出全部章节"
    echo "  bash start.sh publish 1      # 发布第1章"
    echo ""
}

case "$1" in
    status)
        python3 "$SCRIPTS_DIR/publisher.py" --status
        ;;
    export)
        if [ -z "$2" ]; then
            echo "请指定章节号: bash start.sh export <章号>"
            exit 1
        fi
        python3 "$SCRIPTS_DIR/publisher.py" --chapter="$2" --platform=local
        ;;
    export-all)
        python3 "$SCRIPTS_DIR/publisher.py" --export-all
        ;;
    publish)
        if [ -z "$2" ]; then
            echo "请指定章节号: bash start.sh publish <章号>"
            exit 1
        fi
        python3 "$SCRIPTS_DIR/publisher.py" --chapter="$2" --platform=fanqie --dry-run
        ;;
    feishu)
        echo "📄 同步到飞书..."
        echo "请在飞书文档中直接查看，或联系AI处理同步"
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "未知命令: $1"
        show_help
        ;;
esac
