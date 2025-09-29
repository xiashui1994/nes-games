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
    # 读取no.txt文件中的映射关系
    mapping_file = 'no.txt'
    if not os.path.exists(mapping_file):
        print(f"错误: 找不到 {mapping_file}")
        return

    name_mapping = {}
    with open(mapping_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '=' in line:
                real_name, query_name = line.split('=', 1)
                name_mapping[real_name.strip()] = query_name.strip()

    print(f"读取到 {len(name_mapping)} 个名称映射")
    print("-" * 50)

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

    # 记录处理结果
    success_count = 0
    skip_count = 0
    still_failed = []

    # 处理每个映射
    for idx, (real_name, query_name) in enumerate(name_mapping.items(), 1):
        print(f"\n[{idx}/{len(name_mapping)}] 处理: {real_name}")
        print(f"  查询名称: {query_name}")

        # 在games.json中找到对应的游戏
        game_found = False
        for game in data['games']:
            if game['name'] == real_name:
                game_found = True

                # 检查是否已经有category
                if game.get('category') and game['category'].strip():
                    print(f"  ✓ 已有类型信息: {game['category']}，跳过")
                    skip_count += 1
                    break

                # 使用映射的查询名称获取游戏信息
                print(f"  正在获取游戏信息...")
                game_info = fetch_game_info(query_name)

                if game_info['found']:
                    # 更新category
                    if game_info['category']:
                        game['category'] = game_info['category']
                        print(f"  ✓ 类型: {game_info['category']}")
                        success_count += 1

                        # 立即保存更新
                        with open(games_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=4)

                        # 下载封面图片
                        if game_info['cover_url']:
                            cover_filename = f"{real_name}.png"
                            local_cover_path = covers_dir / cover_filename

                            if not local_cover_path.exists():
                                print(f"  正在下载封面...")
                                if download_cover(game_info['cover_url'], local_cover_path):
                                    print(f"  ✓ 封面已保存: covers/{cover_filename}")
                                else:
                                    print(f"  ✗ 封面下载失败")
                else:
                    print(f"  ✗ 获取失败: 未找到游戏信息")
                    still_failed.append(f"{real_name}={query_name}")

                break

        if not game_found:
            print(f"  ✗ 在games.json中未找到游戏: {real_name}")
            still_failed.append(f"{real_name}={query_name} (not in games.json)")

        # 延时避免请求过快
        time.sleep(1.5)

    # 最终保存
    with open(games_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 写入仍然失败的游戏
    if still_failed:
        with open('still_failed.txt', 'w', encoding='utf-8') as f:
            for item in still_failed:
                f.write(f"{item}\n")

    print(f"\n" + "=" * 50)
    print(f"处理完成!")
    print(f"成功更新: {success_count} 个")
    print(f"已有信息跳过: {skip_count} 个")
    print(f"仍然失败: {len(still_failed)} 个")

    if still_failed:
        print(f"\n仍然失败的游戏已写入 still_failed.txt")
        print(f"失败列表:")
        for item in still_failed[:10]:  # 只显示前10个
            print(f"  - {item}")
        if len(still_failed) > 10:
            print(f"  ... 以及其他 {len(still_failed)-10} 个")

if __name__ == "__main__":
    main()