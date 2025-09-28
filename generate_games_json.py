#!/usr/bin/env python3
import json
import os
from pathlib import Path

def parse_metadata():
    """解析metadata.pegasus.txt文件，提取游戏描述信息"""
    metadata_file = Path("metadata.pegasus.txt")
    games_metadata = {}

    if not metadata_file.exists():
        print("警告：metadata.pegasus.txt文件不存在，将跳过描述信息")
        return games_metadata

    with open(metadata_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_game = None
    current_file = None
    current_description = None

    for line in lines:
        line = line.strip()

        if line.startswith("game:"):
            # 保存前一个游戏的信息
            if current_file and current_description:
                # 将文件名中的空格替换为-，以匹配实际文件名
                normalized_file = current_file.replace(" ", "-")
                games_metadata[normalized_file] = current_description

            # 开始新的游戏记录
            current_game = line[5:].strip()
            current_file = None
            current_description = None

        elif line.startswith("file:"):
            current_file = line[5:].strip()

        elif line.startswith("description:"):
            current_description = line[12:].strip()

    # 保存最后一个游戏的信息
    if current_file and current_description:
        normalized_file = current_file.replace(" ", "-")
        games_metadata[normalized_file] = current_description

    return games_metadata

def generate_games_json():
    # 基础配置
    base_url = "https://ghfast.top/raw.githubusercontent.com/xiashui1994/nes-games/main"
    roms_dir = Path("roms")

    # 解析metadata获取描述信息
    games_metadata = parse_metadata()
    print(f"从metadata中解析到{len(games_metadata)}个游戏的描述信息")

    # 获取所有zip文件并排序
    zip_files = sorted(roms_dir.glob("*.zip"))

    # 构建games列表
    games = []
    matched_count = 0

    for zip_file in zip_files:
        # 获取文件名（不含后缀）
        game_name = zip_file.stem

        # 从metadata中查找对应的描述
        description = games_metadata.get(zip_file.name, "")
        if description:
            matched_count += 1

        # 构建游戏对象
        game = {
            "name": game_name,
            "category": "",
            "rom": f"/roms/{zip_file.name}",
            "cover": f"/covers/{game_name}.png",
            "description": description
        }

        games.append(game)

    # 构建最终的JSON结构
    result = {
        "baseUrl": base_url,
        "games": games
    }

    # 写入文件（格式化输出）
    with open("games.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"成功生成games.json，包含{len(games)}个游戏")
    print(f"其中{matched_count}个游戏匹配到了描述信息")

    # 显示前几个游戏作为示例
    print("\n前5个游戏示例：")
    for game in games[:5]:
        has_desc = "✓" if game["description"] else "✗"
        print(f"  - {game['name']} (描述: {has_desc})")

if __name__ == "__main__":
    generate_games_json()