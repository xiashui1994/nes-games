#!/usr/bin/env python3
import os
import json
import requests
import urllib.parse
import time
import re
from pathlib import Path

def encode_gb2312(text):
    """将中文文本转换为GB2312 URL编码"""
    try:
        gb2312_bytes = text.encode('gb2312')
        return urllib.parse.quote(gb2312_bytes)
    except:
        return urllib.parse.quote(text)

def parse_game_info(html_content):
    """解析HTML获取游戏信息"""
    info = {
        'found': False,
        'category': None,
        'cover_url': None,
        'game_id': None,
        'recommendation': 0
    }

    # 查找第一个游戏块（包含head和img两部分）
    game_block = re.search(r'<div class="game_ls_pic2">(.*?)<div class="game_ls_pic2_img">(.*?)</div>\s*</div>', html_content, re.DOTALL)

    if not game_block:
        return info

    # 获取头部信息和图片区域
    head_content = game_block.group(1)
    img_content = game_block.group(2)

    # 提取游戏ID
    id_match = re.search(r'\[ID：(\d+)\]', head_content)
    if id_match:
        info['game_id'] = id_match.group(1)

    # 提取类型
    type_match = re.search(r'\[类型：([^\]]+)\]', head_content)
    if type_match:
        category_raw = type_match.group(1)
        # 提取主要类型（第一个类型）
        categories = category_raw.split('-')
        if categories:
            info['category'] = categories[0].strip()

    # 提取推荐度（计算星星数量）
    recommend_match = re.search(r'\[推荐度：([★☆]+)\]', head_content)
    if recommend_match:
        stars = recommend_match.group(1)
        info['recommendation'] = stars.count('★')

    # 提取封面图片URL（第1张图片）
    img_matches = re.findall(r'<img src="([^"]+\.png)"', img_content)
    if img_matches:
        info['cover_url'] = 'https://game.nesbbs.com' + img_matches[0]  # 使用第1张

    if info['game_id'] and info['category']:
        info['found'] = True

    return info

def download_cover(cover_url, save_path):
    """下载封面图片"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://game.nesbbs.com/'
        }
        response = requests.get(cover_url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"    下载封面失败: {e}")
    return False

def fetch_game_info(game_name):
    """获取单个游戏的信息"""
    encoded_name = encode_gb2312(game_name)
    # 使用order1=good按推荐度排序
    url = f'https://game.nesbbs.com/Game.asp?jixin=24&sort1=%B5%A5%B8%F6&good1=1&name={encoded_name}&order2=desc&good2=5&order1=good'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'gb2312'

        if response.status_code == 200:
            return parse_game_info(response.text)
    except Exception as e:
        print(f"    请求失败: {e}")

    return {'found': False}

def main():
    # 读取games.json
    games_file = 'games.json'
    if not os.path.exists(games_file):
        print(f"错误: 找不到 {games_file}")
        return

    with open(games_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 创建covers目录（用于下载封面图片）
    covers_dir = Path('covers')
    covers_dir.mkdir(exist_ok=True)

    # 获取所有游戏
    games = data.get('games', [])
    total_games = len(games)

    print(f"共找到 {total_games} 个游戏")
    print("-" * 50)

    # 记录错误的游戏
    error_files = []
    success_count = 0
    skip_count = 0

    for idx, game in enumerate(games, 1):
        game_name = game['name']
        print(f"\n[{idx}/{total_games}] 正在处理: {game_name}")

        # 检查是否已经有category
        has_category = game.get('category') and game['category'].strip() != ''

        if has_category:
            print(f"  ✓ 已有类型信息，跳过")
            skip_count += 1
            continue

        # 获取游戏信息
        print(f"  正在获取游戏信息...")
        game_info = fetch_game_info(game_name)

        if game_info['found']:
            # 更新category
            if game_info['category']:
                game['category'] = game_info['category']
                print(f"  ✓ 类型: {game_info['category']}")
                success_count += 1

                # 立即保存更新
                with open(games_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

                # 下载封面图片到covers目录（但不更新cover字段）
                if game_info['cover_url']:
                    cover_filename = f"{game_name}.png"
                    local_cover_path = covers_dir / cover_filename

                    if not local_cover_path.exists():
                        print(f"  正在下载封面...")
                        if download_cover(game_info['cover_url'], local_cover_path):
                            print(f"  ✓ 封面已保存: covers/{cover_filename}")
                        else:
                            print(f"  ✗ 封面下载失败")
        else:
            print(f"  ✗ 获取失败: 未找到游戏信息")
            error_files.append(game_name)

        # 延时避免请求过快
        time.sleep(1.5)

    # 最终保存
    with open(games_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 写入错误文件
    if error_files:
        with open('error.txt', 'w', encoding='utf-8') as f:
            for game in error_files:
                f.write(f"{game}\n")

    print(f"\n" + "=" * 50)
    print(f"处理完成!")
    print(f"成功: {success_count} 个")
    print(f"跳过: {skip_count} 个 (已有完整信息)")
    print(f"失败: {len(error_files)} 个")

    if error_files:
        print(f"\n失败的游戏已写入 error.txt")
        print(f"失败列表:")
        for game in error_files[:10]:  # 只显示前10个
            print(f"  - {game}")
        if len(error_files) > 10:
            print(f"  ... 以及其他 {len(error_files)-10} 个")

if __name__ == "__main__":
    main()