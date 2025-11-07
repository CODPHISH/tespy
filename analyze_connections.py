#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析 connections.csv 并比对 stage2_detailed_model.py 的连接关系."""

import csv
import re
from pathlib import Path

def extract_connections_from_csv():
    """从 connections.csv 提取所有连接定义."""
    csv_file = Path("/home/engine/project/boiler-turbine_design_state/connections.csv")
    
    connections = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for i, row in enumerate(reader):
            label = row.get('', '')  # 第一列没有名字，用空字符串作为键
            if label and label.strip():
                connections.append({
                    'index': i + 1,
                    'label': label.strip(),
                    'm': row.get('m', ''),
                    'p': row.get('p', ''),
                    'T': row.get('T', ''),
                    'H2O': row.get('H2O', ''),
                    'N2': row.get('N2', ''),
                    'O2': row.get('O2', ''),
                    'CO2': row.get('CO2', ''),
                })
    
    return connections

def extract_connections_from_model():
    """从 stage2_detailed_model.py 提取所有连接定义."""
    model_file = Path("/home/engine/project/stage2_detailed_model.py")
    
    content = model_file.read_text(encoding='utf-8')
    
    # 提取所有 Connection 定义（包含 label 参数）
    pattern = r'(\w+)\s*=\s*Connection\(([^,]+),\s*["\'](out\d+)["\'],\s*([^,]+),\s*["\'](in\d+)["\'],\s*label=["\']([^"\']+)["\']\)'
    matches = re.findall(pattern, content)
    
    connections = []
    for match in matches:
        var_name, src_comp, src_port, tgt_comp, tgt_port, label = match
        connections.append({
            'var_name': var_name,
            'label': label.strip(),
            'src_comp': src_comp.strip(),
            'src_port': src_port,
            'tgt_comp': tgt_comp.strip(),
            'tgt_port': tgt_port,
        })
    
    return connections

def main():
    print("=" * 100)
    print("连接关系对比分析")
    print("=" * 100)
    
    # 提取 CSV 连接
    csv_conns = extract_connections_from_csv()
    print(f"\n[1] connections.csv 定义的连接总数: {len(csv_conns)}")
    print("\nCSV 连接列表（前20个）:")
    for i, conn in enumerate(csv_conns[:20], 1):
        print(f"  {i:2d}. {conn['label']}")
    if len(csv_conns) > 20:
        print(f"  ... 还有 {len(csv_conns) - 20} 个连接")
    
    # 提取模型连接
    model_conns = extract_connections_from_model()
    print(f"\n[2] stage2_detailed_model.py 实现的连接总数: {len(model_conns)}")
    print("\n模型连接列表:")
    for i, conn in enumerate(model_conns, 1):
        print(f"  {i:2d}. {conn['var_name']:20s} -> {conn['label']}")
    
    # 对比分析
    csv_labels = {conn['label'] for conn in csv_conns}
    model_labels = {conn['label'] for conn in model_conns}
    
    print(f"\n[3] 对比分析:")
    print(f"  CSV 定义连接数: {len(csv_labels)}")
    print(f"  模型实现连接数: {len(model_labels)}")
    
    # 缺失的连接
    missing = csv_labels - model_labels
    if missing:
        print(f"\n  ⚠️ 缺失的连接 ({len(missing)} 个):")
        for label in sorted(missing):
            print(f"    - {label}")
    else:
        print("\n  ✓ 没有缺失的连接")
    
    # 多余的连接
    extra = model_labels - csv_labels
    if extra:
        print(f"\n  ⚠️ 多余的连接 ({len(extra)} 个):")
        for label in sorted(extra):
            print(f"    - {label}")
    else:
        print("\n  ✓ 没有多余的连接")
    
    # 匹配的连接
    matched = csv_labels & model_labels
    if matched:
        print(f"\n  ✓ 匹配的连接: {len(matched)} 个")
    
    print("\n" + "=" * 100)
    
    # 返回连接列表以便进一步分析
    return csv_conns, model_conns

if __name__ == "__main__":
    main()
