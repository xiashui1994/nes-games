#!/usr/bin/env python3

import json
from typing import List, Dict, Any


def update_categories(json_file_path: str) -> None:
    """
    更新JSON文件中的categories字段
    从games数组中提取所有唯一的category，去重后排序
    并在最前面加上'全部'
    """

    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 从games中提取所有的category
    categories = set()
    for game in data.get('games', []):
        if 'category' in game and game['category']:
            categories.add(game['category'])

    # 转换为列表并排序
    categories_list = sorted(list(categories))

    # 在最前面加上'全部'
    categories_list.insert(0, '全部')

    # 更新categories字段
    data['categories'] = categories_list

    # 写回JSON文件
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"已成功更新categories字段！")
    print(f"共找到 {len(categories_list) - 1} 个不同的分类")
    print(f"更新后的categories: {categories_list}")


if __name__ == "__main__":
    json_file_path = "./games.json"
    update_categories(json_file_path)