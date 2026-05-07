#!/usr/bin/env python3
"""
自动化小说写稿引擎
自动读取 MOD 设定 → 调用 AI 生成章节 → 存储到 volumes/
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

# 配置路径
BASE_DIR = Path("/root/.openclaw/workspace/novel")
CONFIG_PATH = BASE_DIR / "config.json"
MODS_DIR = BASE_DIR / "mods"
VOLUMES_DIR = BASE_DIR / "volumes"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_mods():
    """加载所有 MOD 设定文件"""
    mods = {}
    for f in MODS_DIR.glob("*.json"):
        with open(f, "r", encoding="utf-8") as fh:
            mods[f.stem] = json.load(fh)
    # 也加载 markdown 文件
    for f in MODS_DIR.glob("*.md"):
        with open(f, "r", encoding="utf-8") as fh:
            mods[f.stem] = fh.read()
    return mods

def get_last_chapter_info():
    """获取上次写到的章节信息"""
    volumes = sorted(VOLUMES_DIR.glob("volume-*"))
    if not volumes:
        return {"volume": 1, "chapter": 0}
    
    last_vol = volumes[-1]
    chapters = sorted(last_vol.glob("chapter-*.md"))
    if not chapters:
        return {"volume": int(last_vol.name.split("-")[1]), "chapter": 0}
    
    last_ch = chapters[-1]
    ch_num = int(last_ch.stem.split("-")[1])
    return {
        "volume": int(last_vol.name.split("-")[1]),
        "chapter": ch_num
    }

def build_chapter_prompt(config, mods, last_info):
    """构建写稿提示词"""
    characters = mods.get("characters", {})
    outline = mods.get("outline", "")
    
    next_chapter = last_info["chapter"] + 1
    
    prompt = f"""你是一个小说写作助手。请根据以下设定，写出下一章小说内容。

【小说基本信息】
- 书名：{config['novel']['title']}
- 类型：{config['novel']['genre']}
- 风格：{config['writing']['style']}
- 语调：{config['writing']['tone']}
- 每章字数：约{config['writing']['words_per_chapter']}字

【世界观设定】
{json.dumps(characters.get('world', {}), ensure_ascii=False, indent=2)}

【主要人物】
{json.dumps(characters.get('main_characters', []), ensure_ascii=False, indent=2)}

【配角】
{json.dumps(characters.get('side_characters', []), ensure_ascii=False, indent=2)}

【反派/对手】
{json.dumps(characters.get('antagonists', []), ensure_ascii=False, indent=2)}

【当前进度】
- 第 {last_info['volume']} 卷
- 下一章：第 {next_chapter} 章
- 已有章节数：{last_info['chapter']}

【大纲参考】
{outline[:2000] if outline else "无大纲，自由发挥"}

【写作要求】
1. 每章结尾留钩子（悬念/反转/期待）
2. 对话和描写并重
3. {config['writing']['style']}风格
4. 用{characters.get('writing_style', {}).get('perspective', '第三人称')}
5. 节奏{characters.get('writing_style', {}).get('pacing', '快')}
6. 字数控制在{config['writing']['words_per_chapter']}字左右

请直接输出小说正文，不要输出思考过程。"""
    
    return prompt, next_chapter

def save_chapter(text, volume_num, chapter_num, config):
    """保存章节到文件"""
    vol_dir = VOLUMES_DIR / f"volume-{volume_num:02d}"
    vol_dir.mkdir(parents=True, exist_ok=True)
    
    # 生成带格式的章节文件名
    chapter_file = vol_dir / f"chapter-{chapter_num:03d}.md"
    
    # 格式化内容
    title_num = chapter_num
    if config['novel'].get('current_chapter_title'):
        chapter_title = config['novel']['current_chapter_title']
    else:
        chapter_title = f"第{to_chinese_number(title_num)}章"
    
    formatted = f"""# {chapter_title}

> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 卷：第{to_chinese_number(volume_num)}卷
> 字数：{len(text)}

---

{text.strip()}

---

*【{config['novel'].get('title', '')}】{config['novel'].get('author', '')} 著*
"""
    
    with open(chapter_file, "w", encoding="utf-8") as f:
        f.write(formatted)
    
    print(f"✅ 章节已保存：{chapter_file}")
    return chapter_file

def to_chinese_number(n):
    """数字转中文数字"""
    chn = "零一二三四五六七八九"
    if n <= 9:
        return chn[n]
    digits = list(str(n))
    result = ""
    for d in digits:
        result += chn[int(d)]
    return result

def get_chapter_summary(chapter_file):
    """从已保存的章节提取摘要（供下一章参考）"""
    with open(chapter_file, "r", encoding="utf-8") as f:
        content = f.read()
    # 提取正文部分（去掉标题和元数据）
    body = re.sub(r'^# .+\n> .+\n> .+\n> .+\n\n---\n\n', '', content)
    body = re.sub(r'\n---\n\n\*.*\*$', '', body)
    # 取最后500字作为下一章的承接
    return body[-500:] if len(body) > 500 else body

def update_config_after_write(config, volume_num, chapter_num):
    """写完后更新配置中的进度"""
    config['novel']['last_volume'] = volume_num
    config['novel']['last_chapter'] = chapter_num
    config['novel']['last_write_time'] = datetime.now().isoformat()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def main():
    config = load_config()
    mods = load_mods()
    last_info = get_last_chapter_info()
    
    prompt, next_chapter = build_chapter_prompt(config, mods, last_info)
    
    # 输出提示词（实际使用时传递给 LLM）
    with open(BASE_DIR / "output" / "current_prompt.md", "w", encoding="utf-8") as f:
        f.write(prompt)
    
    print(f"📝 准备写作：第{last_info['volume']}卷 第{next_chapter}章")
    print(f"📄 提示词已保存：output/current_prompt.md")
    print("=" * 50)
    print(prompt[:500] + "...\n（提示词完整内容见 output/current_prompt.md）")

if __name__ == "__main__":
    main()
