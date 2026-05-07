#!/usr/bin/env python3
"""
小说自动发布脚本
支持：番茄小说(fanqie) | 本地备份 | 飞书同步
用法：
  python3 publisher.py                  # 发布下一章（默认保存本地草稿）
  python3 publisher.py --platform=fanqie   # 发布到番茄小说
  python3 publisher.py --chapter=2       # 发布指定章节
  python3 publisher.py --sync-feishu     # 同步到飞书文档
  python3 publisher.py --status          # 查看发布状态
"""

import json
import os
import sys
import argparse
import re
from datetime import datetime

# ---------- 路径配置 ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOLUMES_DIR = os.path.join(BASE_DIR, "volumes", "volume-01")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_chapters():
    """获取所有章节文件，按编号排序"""
    files = [f for f in os.listdir(VOLUMES_DIR) if f.startswith("chapter-") and f.endswith(".md")]
    files.sort()
    return files


def get_chapter_info(filename):
    """解析章节编号和标题"""
    match = re.match(r'chapter-(\d+)\.md', filename)
    if not match:
        return None, None
    num = int(match.group(1))
    # 读取标题
    filepath = os.path.join(VOLUMES_DIR, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    title = first_line.lstrip("#").strip() if first_line.startswith("#") else f"第{num}章"
    return num, title


def count_words(filepath):
    """统计正文字数（汉字）"""
    import re as regex
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # 去掉标题行
    lines = content.split("\n")
    body_lines = [l for l in lines if not l.startswith("# ")]
    body = "\n".join(body_lines)
    chinese = len(regex.findall(r'[\u4e00-\u9fff]', body))
    return chinese


def export_markdown(chapter_num):
    """导出单章为独立的Markdown文件"""
    filename = f"chapter-{chapter_num:03d}.md"
    src = os.path.join(VOLUMES_DIR, filename)
    if not os.path.exists(src):
        print(f"❌ 章节文件不存在: {filename}")
        return None

    num, title = get_chapter_info(filename)
    out_name = f"{num:03d}-{title}.md"
    # 文件名规范处理
    safe_title = re.sub(r'[\/:*?"<>|]', '', title)
    out_name = f"{num:03d}-{safe_title}.md"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    with open(src, "r", encoding="utf-8") as f:
        content = f.read()

    # 添加发布元信息头
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"""---
title: {title}
chapter: {num}
author: {load_config()['novel']['author']}
created: {now}
status: draft
---

"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header + content)

    word_count = count_words(src)
    print(f"📝 已导出: {out_name} ({word_count}汉字)")
    return out_path


def publish_to_fanqie(chapter_num, dry_run=True):
    """
    发布到番茄小说
    注：番茄小说没有公开的API，这里生成发布草稿 + 打开浏览器
    dry_run=True 时只生成文件不打开浏览器
    """
    config = load_config()
    platform = config["publish"]["platform"]

    out_path = export_markdown(chapter_num)
    if not out_path:
        return

    word_count = count_words(os.path.join(VOLUMES_DIR, f"chapter-{chapter_num:03d}.md"))

    print(f"\n📤 发布到【{platform}】")
    print(f"   章节: 第{chapter_num}章")
    print(f"   字数: {word_count}汉字")
    print(f"   文件: {out_path}")

    if dry_run:
        print(f"\n   ✅ 草稿已保存到 output/ 目录")
        print(f"   手动发布步骤：")
        print(f"     1. 打开 {config['publish']['fanqie_dashboard_url']}")
        print(f"     2. 登录作者后台")
        print(f"     3. 新建章节，粘贴 output/{os.path.basename(out_path)} 的内容")
        print(f"     4. 设置章节号为第{chapter_num}章")
        print(f"     5. 发布或保存草稿")
    else:
        # 尝试自动打开浏览器
        try:
            import webbrowser
            webbrowser.open(config["publish"]["fanqie_dashboard_url"])
            print(f"\n   🌐 已打开番茄作者后台")
        except:
            print(f"\n   ⚠️ 无法自动打开浏览器，请手动访问：{config['publish']['fanqie_dashboard_url']}")

    # 更新发布记录
    if not dry_run:
        config["publish"]["last_published_chapter"] = chapter_num
        config["publish"]["auto_publish"] = True
        save_config(config)

    return out_path


def show_status():
    """显示所有章节的发布状态"""
    config = load_config()
    chapters = get_chapters()

    print(f"\n📚 【{config['novel']['title']}】发布状态")
    print(f"   作者: {config['novel']['author']}")
    print(f"   平台: {config['publish']['platform']}")
    print(f"   最后发布章节: 第{config['publish']['last_published_chapter']}章")
    print()

    print(f"   {'章节':<10} {'标题':<25} {'字数':<8} {'状态':<10}")
    print(f"   {'-'*53}")
    for f in chapters:
        num, title = get_chapter_info(f)
        words = count_words(os.path.join(VOLUMES_DIR, f))
        if num and num <= config["publish"]["last_published_chapter"]:
            status = "✅ 已发布"
        elif num:
            status = "📝 待发布"
        else:
            status = "❓ 未知"
        print(f"   {'第' + str(num) + '章':<10} {title:<25} {str(words) + '字':<8} {status:<10}")

    # 下一章推荐
    next_chapter = config["publish"]["last_published_chapter"] + 1
    next_file = f"chapter-{next_chapter:03d}.md"
    if os.path.exists(os.path.join(VOLUMES_DIR, next_file)):
        print(f"\n   ▶️  下一章可发布: 第{next_chapter}章")
    else:
        print(f"\n   ⏳ 第{next_chapter}章尚未创作")


def batch_export_all():
    """导出全部章节到output目录"""
    chapters = get_chapters()
    print(f"\n📦 批量导出全部章节到 {OUTPUT_DIR}/")
    total_words = 0
    for f in chapters:
        num, title = get_chapter_info(f)
        if num:
            path = export_markdown(num)
            words = count_words(os.path.join(VOLUMES_DIR, f))
            total_words += words
    print(f"\n   ✅ 共导出 {len(chapters)} 章，总字数约{total_words}汉字")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="小说自动发布脚本")
    parser.add_argument("--chapter", type=int, help="指定章节号（默认：最后发布章+1）")
    parser.add_argument("--platform", choices=["fanqie", "local"], default="local", help="发布平台")
    parser.add_argument("--publish", action="store_true", help="实际发布（默认只保存草稿）")
    parser.add_argument("--sync-feishu", action="store_true", help="同步到飞书文档")
    parser.add_argument("--status", action="store_true", help="查看发布状态")
    parser.add_argument("--export-all", action="store_true", help="批量导出全部章节")
    parser.add_argument("--dry-run", action="store_true", default=True, help=argparse.SUPPRESS)

    args = parser.parse_args()

    # 没有参数时显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        print("\n常用命令：")
        print("  python3 publisher.py              # 导出下一章草稿")
        print("  python3 publisher.py --status      # 查看发布状态")
        print("  python3 publisher.py --export-all  # 批量导出全部章节")
        print("  python3 publisher.py --chapter=2 --publish  # 实际发布第2章")
        sys.exit(0)

    if args.status:
        show_status()
        sys.exit(0)

    if args.export_all:
        batch_export_all()
        sys.exit(0)

    if args.sync_feishu:
        print("📄 同步到飞书文档...")
        print("   请在飞书文档中使用同步功能，或联系AI处理")
        sys.exit(0)

    # 默认：发布指定章节或下一章
    config = load_config()
    chapter_num = args.chapter or (config["publish"]["last_published_chapter"] + 1)

    dry_run = not args.publish
    platform = args.platform or config["publish"]["platform"]

    if platform == "fanqie":
        publish_to_fanqie(chapter_num, dry_run=dry_run)
    else:
        export_markdown(chapter_num)
