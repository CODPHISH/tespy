#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试博士模型整合功能

快速验证所有新增的工具和模型是否正常工作。
"""

import sys
import subprocess
from pathlib import Path


def run_test(test_name, command):
    """运行测试."""
    print(f"\n{'=' * 80}")
    print(f"测试: {test_name}")
    print('=' * 80)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"✓ {test_name} 成功")
            return True
        else:
            print(f"✗ {test_name} 失败")
            print(f"错误信息:\n{result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ {test_name} 超时")
        return False
    except Exception as e:
        print(f"✗ {test_name} 出错: {e}")
        return False


def check_files():
    """检查必要的文件是否存在."""
    print(f"\n{'=' * 80}")
    print("检查文件")
    print('=' * 80)
    
    required_files = [
        'boiler-turbine_design_state/connections.csv',
        'boiler-turbine_design_state/busses.json',
        'boiler-turbine_design_state/components/HeatExchanger.csv',
        'analyze_phd_design_data.py',
        'stage2_improved_phd_params.py',
        'README_PHD_MODEL_INTEGRATION.md',
        'STAGE2_PHD_INTEGRATION_SUMMARY.md',
    ]
    
    all_exists = True
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} 缺失")
            all_exists = False
    
    return all_exists


def check_generated_files():
    """检查生成的文件."""
    print(f"\n{'=' * 80}")
    print("检查生成的文件")
    print('=' * 80)
    
    generated_files = [
        'phd_model_parameters.json',
        'stage2_improved_phd_design.json',
        'stage2_improved_original_design.json',
    ]
    
    for file in generated_files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file} ({path.stat().st_size} bytes)")
        else:
            print(f"⚠ {file} 未生成（可能还未运行）")


def main():
    """主函数."""
    print("\n" + "=" * 80)
    print("博士模型整合功能测试")
    print("=" * 80)
    
    # 检查文件
    files_ok = check_files()
    
    if not files_ok:
        print("\n✗ 部分必要文件缺失，无法继续测试")
        sys.exit(1)
    
    # 测试结果
    test_results = []
    
    # 测试1：数据分析工具
    test_results.append(
        run_test(
            "数据分析工具",
            "python analyze_phd_design_data.py > /dev/null 2>&1"
        )
    )
    
    # 测试2：改进模型
    test_results.append(
        run_test(
            "改进模型",
            "python stage2_improved_phd_params.py > /dev/null 2>&1"
        )
    )
    
    # 检查生成的文件
    check_generated_files()
    
    # 总结
    print(f"\n{'=' * 80}")
    print("测试总结")
    print('=' * 80)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n通过: {passed}/{total}")
    
    if passed == total:
        print("\n✓ 所有测试通过！")
        print("\n博士模型整合功能正常，可以使用以下命令：")
        print("  1. 分析数据: python analyze_phd_design_data.py")
        print("  2. 运行模型: python stage2_improved_phd_params.py")
        print("  3. 查看文档: cat README_PHD_MODEL_INTEGRATION.md")
        sys.exit(0)
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
