#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据connections.csv连接标签推断系统拓扑结构."""

import csv
import re
from pathlib import Path
from collections import defaultdict

def parse_connection_labels():
    """从连接标签中提取组件信息."""
    csv_file = Path("/home/engine/project/boiler-turbine_design_state/connections.csv")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        labels = [row.get('', '').strip() for row in reader if row.get('', '').strip()]
    
    print(f"总连接数: {len(labels)}\n")
    
    # 分析连接标签模式
    component_types = defaultdict(list)
    
    for label in labels:
        # 根据标签模式分类
        if '抽凝式汽轮机1_' in label:
            component_types['turbine'].append(label)
        elif '1#发电锅炉_' in label:
            component_types['boiler'].append(label)
        elif 'boiler1_' in label:
            component_types['fuel'].append(label)
        else:
            component_types['other'].append(label)
    
    print("=" * 100)
    print("汽轮机相关连接 (turbine)")
    print("=" * 100)
    for i, label in enumerate(component_types['turbine'], 1):
        print(f"{i:2d}. {label}")
    
    print(f"\n=" * 100)
    print("锅炉相关连接 (boiler)")
    print("=" * 100)
    for i, label in enumerate(component_types['boiler'], 1):
        print(f"{i:2d}. {label}")
    
    print(f"\n=" * 100)
    print("燃料相关连接 (fuel)")
    print("=" * 100)
    for i, label in enumerate(component_types['fuel'], 1):
        print(f"{i:2d}. {label}")
    
    print(f"\n=" * 100)
    print("其他连接 (other)")
    print("=" * 100)
    for i, label in enumerate(component_types['other'], 1):
        print(f"{i:2d}. {label}")
    
    return labels, component_types

def infer_components(labels):
    """从连接标签推断需要的组件."""
    components = set()
    
    for label in labels:
        # 提取组件名称（通常是标签的前缀或关键词）
        if '抽凝式汽轮机1_高压缸' in label and ('一段' in label or '二段' in label):
            components.add('高压缸一段')
            components.add('高压缸二段')
        if '抽凝式汽轮机1_低压缸' in label or '抽凝式汽轮机1_再热' in label:
            components.add('低压缸一段')
            components.add('低压缸二段')
            components.add('低压缸三段')
            components.add('低压缸四段')
            components.add('低压缸五段')
            components.add('低压缸六段')
            components.add('低压缸七段')
        if '蒸发器' in label or '上升管' in label or '下降管' in label or '汽包' in label:
            components.add('汽包')
            components.add('蒸发器上升管')
        if '省煤器' in label:
            components.add('下级省煤器')
            components.add('上级省煤器')
        if '低温过热器' in label or '蒸汽低过' in label:
            components.add('低温过热器')
        if '屏式过热器' in label or '蒸汽屏过' in label:
            components.add('屏式过热器')
        if '三级过热器' in label or '蒸汽三过' in label:
            components.add('三级过热器')
        if '末级过热器' in label or '末过' in label:
            components.add('末级过热器')
        if '再热' in label:
            components.add('低温再热器')
            components.add('末级再热器')
        if '给水泵' in label or '水泵' in label:
            components.add('给水泵')
        if '燃烧' in label or '煤气' in label or '焦炉' in label or '高炉' in label or '转炉' in label:
            components.add('燃烧室')
            components.add('高炉煤气源')
            components.add('转炉煤气源')
            components.add('焦炉煤气源')
        if '空气' in label:
            components.add('空气源')
            components.add('空气预热器')
        if '煤预' in label:
            components.add('煤气预热器')
    
    print(f"\n=" * 100)
    print("推断需要的组件")
    print("=" * 100)
    for i, comp in enumerate(sorted(components), 1):
        print(f"{i:2d}. {comp}")
    print(f"\n共 {len(components)} 个组件")
    
    return components

if __name__ == "__main__":
    labels, component_types = parse_connection_labels()
    components = infer_components(labels)
